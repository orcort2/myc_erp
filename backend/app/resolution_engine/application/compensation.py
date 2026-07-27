"""Planificación y ejecución síncrona de compensaciones autorizadas."""

from __future__ import annotations

from dataclasses import replace

from app.resolution_engine.application.compensation_runner import (
    CompensationRunner,
)
from app.resolution_engine.contracts.compensation import (
    CompensationStore,
    ExecuteCompensationCommand,
    PrepareCompensationCommand,
)
from app.resolution_engine.contracts.runtime import Clock, IdentifierFactory
from app.resolution_engine.domain.canonical import canonical_sha256
from app.resolution_engine.domain.compensation import (
    CompensationActionRequest,
    CompensationEngine,
    CompensationOutcome,
)
from app.resolution_engine.domain.enums import CompensationStatus
from app.resolution_engine.domain.exceptions import (
    CompensationHandlerNotFoundError,
    CompensationInvocationUncertainError,
    CompensationNotAllowedError,
    ExecutionLockLostError,
)
from app.resolution_engine.domain.execution import (
    ActionCertainty,
    DomainActionResult,
)
from app.resolution_engine.domain.lifecycle import (
    CompensationEvidence,
    LifecycleAction,
    ResolutionStateMachine,
)


class CompensationPlanner:
    """Construye y persiste un plan compensatorio sin ejecutar acciones."""

    def __init__(
        self,
        *,
        store: CompensationStore,
        engine: CompensationEngine,
        clock: Clock,
    ) -> None:
        self._store = store
        self._engine = engine
        self._clock = clock

    def prepare(
        self,
        command: PrepareCompensationCommand,
        /,
    ):
        created_at = self._clock.now()
        violations = command.actor.validate_at(created_at)
        if violations:
            raise CompensationNotAllowedError(
                "actor context is not valid: " + ", ".join(violations)
            )
        source = self._store.load_source(
            command.resolution_id,
            command.source_execution_id,
        )
        if source is None:
            raise CompensationNotAllowedError(
                "source execution is not compensable"
            )
        plan = self._engine.build_plan(
            source,
            strategy=command.strategy,
            reason=command.reason,
            selected_step_execution_ids=(
                command.selected_step_execution_ids
            ),
        )
        return self._store.save_plan(
            command,
            plan,
            created_at=created_at,
        )


class CompensationExecutor:
    """Coordina acciones compensatorias mediante checkpoints durables."""

    def __init__(
        self,
        *,
        store: CompensationStore,
        runner: CompensationRunner,
        engine: CompensationEngine,
        state_machine: ResolutionStateMachine,
        clock: Clock,
        identifiers: IdentifierFactory,
    ) -> None:
        self._store = store
        self._runner = runner
        self._engine = engine
        self._state_machine = state_machine
        self._clock = clock
        self._identifiers = identifiers

    def execute(
        self,
        command: ExecuteCompensationCommand,
        /,
    ) -> CompensationOutcome:
        started_at = self._clock.now()
        violations = command.actor.validate_at(started_at)
        if violations:
            raise CompensationNotAllowedError(
                "actor context is not valid: " + ", ".join(violations)
            )
        prepared = self._store.load_prepared(
            command.compensation_plan_id,
            command.actor,
        )
        if prepared is None or prepared.plan.id is None:
            raise CompensationNotAllowedError(
                "compensation plan is not prepared"
            )
        request_hash = canonical_sha256(
            {
                "compensation_plan_id": prepared.plan.id,
                "plan_hash": prepared.plan.plan_hash,
                "resolution_id": prepared.plan.resolution_id,
                "source_execution_id": prepared.plan.source_execution_id,
                "steps": [
                    step.snapshot() for step in prepared.plan.steps
                ],
            }
        )
        previous = self._store.find_outcome(
            idempotency_key=command.idempotency_key,
            request_hash=request_hash,
        )
        if previous is not None:
            return previous
        execution_key = canonical_sha256(
            {
                "scope": "compensation_execution",
                "idempotency_key": command.idempotency_key,
            }
        )
        prospective = replace(
            prepared.lifecycle,
            evidence=replace(
                prepared.lifecycle.evidence,
                compensation=CompensationEvidence(
                    plan_id=prepared.plan.id,
                    execution_id=None,
                    source_execution_id=(
                        prepared.plan.source_execution_id
                    ),
                    status=CompensationStatus.PREPARED.value,
                    total_steps=len(prepared.plan.steps),
                    compensated_steps=0,
                    failed_steps=0,
                    blocked_steps=0,
                ),
            ),
        )
        actor = command.actor
        start_transition = self._state_machine.transition(
            prospective,
            LifecycleAction.START_COMPENSATION,
            occurred_at=started_at,
            actor_id=actor.identity.actor_id,
            actor_type=actor.identity.actor_type.value,
            actor_function=None,
            source=actor.authentication.source,
            correlation_id=actor.authentication.correlation_id,
            metadata={
                "compensation_plan_id": prepared.plan.id,
                "source_execution_id": prepared.plan.source_execution_id,
                "plan_hash": prepared.plan.plan_hash,
            },
        )
        started = self._store.start(
            command=command,
            prepared=prepared,
            transition=start_transition,
            execution_key=execution_key,
            lock_token=self._identifiers.new_id(),
            request_hash=request_hash,
            occurred_at=started_at,
        )
        if started.previous_outcome is not None:
            return started.previous_outcome
        reservation = started.reservation
        if reservation is None:
            raise RuntimeError(
                "compensation store returned no reservation"
            )

        results: dict[int, DomainActionResult] = {}
        for step in reservation.plan.steps:
            now = self._clock.now()
            self._store.renew_lock(
                reservation,
                expires_at=now + command.lock_ttl,
                occurred_at=now,
            )
            step_execution_id = reservation.step_execution_ids[
                step.source_step_execution_id
            ]
            request = CompensationActionRequest(
                resolution_id=reservation.plan.resolution_id,
                source_execution_id=(
                    reservation.plan.source_execution_id
                ),
                compensation_execution_id=reservation.execution_id,
                compensation_step_execution_id=step_execution_id,
                compensation_plan_id=reservation.plan.id or 0,
                plan_hash=reservation.plan.plan_hash,
                step=step,
                idempotency_key=canonical_sha256(
                    {
                        "execution_key": reservation.execution_key,
                        "source_step_execution_id": (
                            step.source_step_execution_id
                        ),
                    }
                ),
                actor_id=actor.identity.actor_id,
                correlation_id=actor.authentication.correlation_id,
            )
            previous_result = self._store.start_step(
                reservation,
                step,
                request_hash=request.request_hash,
                occurred_at=now,
            )
            result = previous_result or self._run(request)
            if previous_result is None:
                result = self._record_result(
                    reservation,
                    step,
                    result,
                )
            results[step.source_step_execution_id] = result
            if not result.success:
                break

        completed_at = self._clock.now()
        summary = self._engine.summarize(reservation.plan, results)
        final_action = {
            CompensationStatus.COMPENSATED:
                LifecycleAction.COMPLETE_COMPENSATION,
            CompensationStatus.PARTIALLY_COMPENSATED:
                LifecycleAction.COMPLETE_PARTIAL_COMPENSATION,
            CompensationStatus.FAILED:
                LifecycleAction.FAIL_COMPENSATION,
            CompensationStatus.BLOCKED:
                LifecycleAction.FAIL_COMPENSATION,
        }[summary.status]
        final_evidence = CompensationEvidence(
            plan_id=reservation.plan.id or 0,
            execution_id=reservation.execution_id,
            source_execution_id=reservation.plan.source_execution_id,
            status=summary.status.value,
            total_steps=summary.total_steps,
            compensated_steps=summary.compensated_steps,
            failed_steps=summary.failed_steps,
            blocked_steps=summary.blocked_steps,
        )
        final_case = replace(
            reservation.lifecycle,
            evidence=replace(
                reservation.lifecycle.evidence,
                compensation=final_evidence,
            ),
        )
        transition = self._state_machine.transition(
            final_case,
            final_action,
            occurred_at=completed_at,
            actor_id=actor.identity.actor_id,
            actor_type=actor.identity.actor_type.value,
            actor_function=None,
            source=actor.authentication.source,
            correlation_id=actor.authentication.correlation_id,
            metadata={
                "compensation_plan_id": reservation.plan.id,
                "compensation_execution_id": reservation.execution_id,
                "source_execution_id": (
                    reservation.plan.source_execution_id
                ),
            },
        )
        outcome = CompensationOutcome(
            compensation_plan_id=reservation.plan.id or 0,
            compensation_execution_id=reservation.execution_id,
            resolution_id=reservation.plan.resolution_id,
            source_execution_id=reservation.plan.source_execution_id,
            status=summary.status,
            idempotency_key=command.idempotency_key,
            idempotent_replay=False,
            compensated_steps=summary.compensated_steps,
            failed_steps=summary.failed_steps,
            blocked_steps=summary.blocked_steps,
            total_steps=summary.total_steps,
        )
        return self._store.finish(
            reservation,
            summary,
            transition,
            outcome=outcome,
            completed_at=completed_at,
        )

    def _run(
        self,
        request: CompensationActionRequest,
    ) -> DomainActionResult:
        try:
            return self._runner.run(request)
        except (
            CompensationHandlerNotFoundError,
            CompensationInvocationUncertainError,
        ) as exc:
            return DomainActionResult(
                success=False,
                certainty=ActionCertainty.UNCERTAIN,
                error_code="compensation_result_uncertain",
                error_message=str(exc),
            )

    def _record_result(
        self,
        reservation,
        step,
        result: DomainActionResult,
    ) -> DomainActionResult:
        try:
            self._store.assert_lock(
                reservation,
                occurred_at=self._clock.now(),
            )
            self._store.record_step_result(
                reservation,
                step,
                result,
                occurred_at=self._clock.now(),
            )
            return result
        except ExecutionLockLostError as exc:
            uncertain = DomainActionResult(
                success=False,
                certainty=ActionCertainty.UNCERTAIN,
                error_code="compensation_lock_lost_after_action",
                error_message=str(exc),
                error_details={
                    "reported_action_result": result.snapshot(),
                },
            )
            self._store.record_step_result(
                reservation,
                step,
                uncertain,
                occurred_at=self._clock.now(),
                require_active_lock=False,
            )
            return uncertain
