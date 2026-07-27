"""Servicio síncrono de ejecución controlada, sin retries ni compensación."""

from __future__ import annotations

from dataclasses import replace

from app.resolution_engine.application.action_runner import ActionRunner
from app.resolution_engine.application.lifecycle import LifecycleActor
from app.resolution_engine.contracts.execution import (
    ExecuteResolutionCommand,
    ExecutionStore,
)
from app.resolution_engine.contracts.runtime import Clock, IdentifierFactory
from app.resolution_engine.domain.canonical import canonical_sha256
from app.resolution_engine.domain.enums import (
    ExecutionStatus,
    ResolutionStatus,
)
from app.resolution_engine.domain.exceptions import (
    ActionHandlerNotFoundError,
    ActionInvocationUncertainError,
    ExecutionLockLostError,
    ExecutionNotReadyError,
)
from app.resolution_engine.domain.execution import (
    ActionCertainty,
    DomainActionRequest,
    DomainActionResult,
    ExecutionEngine,
    ExecutionOutcome,
    ExecutionPlanStep,
    ExecutionReservation,
)
from app.resolution_engine.domain.lifecycle import (
    ExecutionEvidence,
    LifecycleAction,
    ResolutionStateMachine,
)


class ResolutionExecutor:
    """Coordina cada acción y checkpoint; no implementa reglas propietarias."""

    def __init__(
        self,
        *,
        store: ExecutionStore,
        action_runner: ActionRunner,
        engine: ExecutionEngine,
        state_machine: ResolutionStateMachine,
        clock: Clock,
        identifiers: IdentifierFactory,
    ) -> None:
        self._store = store
        self._action_runner = action_runner
        self._engine = engine
        self._state_machine = state_machine
        self._clock = clock
        self._identifiers = identifiers

    def execute(
        self,
        command: ExecuteResolutionCommand,
        /,
    ) -> ExecutionOutcome:
        started_at = self._clock.now()
        self._validate_command(command, started_at=started_at)
        candidate = self._store.load_candidate(command.resolution_id)
        if candidate is None:
            raise ExecutionNotReadyError(
                f"Resolution not found: {command.resolution_id}"
            )
        ordered_steps = self._engine.ordered_steps(candidate)
        self._store.verify_security(
            command,
            candidate,
            occurred_at=started_at,
        )
        execution_key = self._execution_key(command.idempotency_key)
        request_hash = canonical_sha256(
            {
                "resolution_id": command.resolution_id,
                "plan_id": candidate.plan_id,
                "plan_version": candidate.plan_version,
                "plan_hash": candidate.plan_hash,
                "revalidation_id": candidate.revalidation_id,
                "revalidation_hash": candidate.revalidation_hash,
                "security_decision_id": command.security_decision_id,
                "actor_id": command.actor.identity.actor_id,
                "organization_id": (
                    command.actor.identity.organization_id
                ),
                "steps": [
                    step.request_snapshot() for step in ordered_steps
                ],
            }
        )
        previous = self._store.find_outcome(
            idempotency_key=command.idempotency_key,
            request_hash=request_hash,
        )
        if previous is not None:
            return previous
        lifecycle_actor = self._lifecycle_actor(command)
        start_transition = self._state_machine.transition(
            candidate.lifecycle,
            LifecycleAction.START_EXECUTION,
            occurred_at=started_at,
            actor_id=lifecycle_actor.actor_id,
            actor_type=lifecycle_actor.actor_type,
            actor_function=lifecycle_actor.actor_function,
            source=lifecycle_actor.source,
            correlation_id=lifecycle_actor.correlation_id,
            metadata={
                "execution_key": execution_key,
                "plan_id": candidate.plan_id,
                "revalidation_id": candidate.revalidation_id,
            },
        )
        start = self._store.start(
            command=command,
            steps=ordered_steps,
            transition=start_transition,
            execution_key=execution_key,
            lock_token=self._identifiers.new_id(),
            request_hash=request_hash,
            occurred_at=started_at,
        )
        if start.previous_outcome is not None:
            return start.previous_outcome
        reservation = start.reservation
        if reservation is None:
            raise RuntimeError("execution store returned no reservation")

        results: dict[int, DomainActionResult] = {}
        for step in reservation.steps:
            now = self._clock.now()
            self._store.renew_lock(
                reservation,
                expires_at=now + command.lock_ttl,
                occurred_at=now,
            )
            step_execution_id = reservation.step_execution_ids[step.id]
            action_request = DomainActionRequest(
                resolution_id=reservation.resolution_id,
                execution_id=reservation.execution_id,
                step_execution_id=step_execution_id,
                plan_id=reservation.plan_id,
                plan_version=reservation.plan_version,
                plan_hash=reservation.plan_hash,
                step=step,
                idempotency_key=self._step_key(
                    reservation.execution_key,
                    step.step_key,
                ),
                actor_id=command.actor.identity.actor_id,
                correlation_id=reservation.correlation_id,
            )
            step_start = self._store.start_step(
                reservation,
                step,
                request_hash=action_request.request_hash,
                occurred_at=now,
            )
            if step_start.previous_result is not None:
                result = step_start.previous_result
            else:
                result = self._run_action(action_request)
                result = self._record_action_result(
                    reservation=reservation,
                    step=step,
                    result=result,
                )
            results[step.id] = result
            if not result.success:
                break

        completed_at = self._clock.now()
        summary = self._engine.summarize(
            steps=reservation.steps,
            results=results,
        )
        final_action, resolution_status = self._final_state(summary.execution_status)
        execution_evidence = ExecutionEvidence(
            id=reservation.execution_id,
            plan_id=reservation.plan_id,
            revalidation_id=reservation.revalidation_id,
            status=summary.execution_status.value,
            total_steps=summary.total_steps,
            completed_steps=summary.completed_steps,
            failed_steps=summary.failed_steps,
            blocked_steps=summary.blocked_steps,
        )
        prospective = replace(
            reservation.lifecycle,
            evidence=replace(
                reservation.lifecycle.evidence,
                execution=execution_evidence,
            ),
        )
        finish_transition = self._state_machine.transition(
            prospective,
            final_action,
            occurred_at=completed_at,
            actor_id=lifecycle_actor.actor_id,
            actor_type=lifecycle_actor.actor_type,
            actor_function=lifecycle_actor.actor_function,
            source=lifecycle_actor.source,
            correlation_id=lifecycle_actor.correlation_id,
            metadata={"execution_id": reservation.execution_id},
        )
        result_hash = (
            self._engine.result_hash(
                resolution_id=reservation.resolution_id,
                execution_id=reservation.execution_id,
                summary=summary,
                completed_at=completed_at,
            )
            if summary.resolution_result is not None
            else None
        )
        outcome = ExecutionOutcome(
            execution_id=reservation.execution_id,
            resolution_id=reservation.resolution_id,
            execution_status=summary.execution_status,
            resolution_status=resolution_status.value,
            idempotency_key=command.idempotency_key,
            idempotent_replay=False,
            completed_steps=summary.completed_steps,
            failed_steps=summary.failed_steps,
            blocked_steps=summary.blocked_steps,
            total_steps=summary.total_steps,
            result_hash=result_hash,
        )
        return self._store.finish(
            reservation,
            summary,
            finish_transition,
            outcome=outcome,
            completed_at=completed_at,
            actor=command.actor,
        )

    def _record_action_result(
        self,
        *,
        reservation: ExecutionReservation,
        step: ExecutionPlanStep,
        result: DomainActionResult,
    ) -> DomainActionResult:
        validation_at = self._clock.now()
        try:
            self._store.assert_lock(
                reservation,
                occurred_at=validation_at,
            )
            checkpoint_at = self._clock.now()
            self._store.record_step_result(
                reservation,
                step,
                result,
                occurred_at=checkpoint_at,
            )
            return result
        except ExecutionLockLostError as exc:
            uncertain_at = self._clock.now()
            uncertain = DomainActionResult(
                success=False,
                certainty=ActionCertainty.UNCERTAIN,
                error_code="execution_lock_lost_after_action",
                error_message=str(exc),
                error_details={
                    "reported_action_result": result.snapshot(),
                },
            )
            self._store.record_uncertain_lock_loss(
                reservation,
                step,
                uncertain,
                occurred_at=uncertain_at,
            )
            return uncertain

    def _run_action(
        self,
        request: DomainActionRequest,
    ) -> DomainActionResult:
        try:
            return self._action_runner.run(request)
        except (
            ActionHandlerNotFoundError,
            ActionInvocationUncertainError,
        ) as exc:
            return DomainActionResult(
                success=False,
                certainty=ActionCertainty.UNCERTAIN,
                error_code="action_result_uncertain",
                error_message=str(exc),
            )

    @staticmethod
    def _validate_command(
        command: ExecuteResolutionCommand,
        *,
        started_at,
    ) -> None:
        violations = command.actor.validate_at(started_at)
        if violations:
            raise ExecutionNotReadyError(
                "actor context is not valid: " + ", ".join(violations)
            )
        if command.resolution_id <= 0:
            raise ExecutionNotReadyError("resolution_id must be positive")
        if command.security_decision_id <= 0:
            raise ExecutionNotReadyError(
                "security_decision_id must be positive"
            )
        if not command.idempotency_key.strip():
            raise ExecutionNotReadyError("idempotency_key is required")
        if not command.lock_owner.strip():
            raise ExecutionNotReadyError("lock_owner is required")
        if command.lock_ttl.total_seconds() <= 0:
            raise ExecutionNotReadyError("lock_ttl must be positive")

    @staticmethod
    def _lifecycle_actor(
        command: ExecuteResolutionCommand,
    ) -> LifecycleActor:
        return LifecycleActor(
            context=command.actor,
        )

    @staticmethod
    def _execution_key(idempotency_key: str) -> str:
        digest = canonical_sha256({"idempotency_key": idempotency_key})
        return f"execution:{digest}"

    @staticmethod
    def _step_key(execution_key: str, step_key: str) -> str:
        digest = canonical_sha256(
            {"execution_key": execution_key, "step_key": step_key}
        )
        return f"step:{digest}"

    @staticmethod
    def _final_state(
        status: ExecutionStatus,
    ) -> tuple[LifecycleAction, ResolutionStatus]:
        values = {
            ExecutionStatus.COMPLETED: (
                LifecycleAction.COMPLETE_EXECUTION,
                ResolutionStatus.COMPLETED,
            ),
            ExecutionStatus.PARTIALLY_COMPLETED: (
                LifecycleAction.COMPLETE_PARTIAL_EXECUTION,
                ResolutionStatus.PARTIALLY_COMPLETED,
            ),
            ExecutionStatus.FAILED: (
                LifecycleAction.FAIL_EXECUTION,
                ResolutionStatus.FAILED,
            ),
            ExecutionStatus.BLOCKED: (
                LifecycleAction.BLOCK_EXECUTION,
                ResolutionStatus.BLOCKED,
            ),
        }
        return values[status]
