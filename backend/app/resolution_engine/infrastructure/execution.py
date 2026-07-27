"""Runtime SQL transaccional para la ejecución controlada."""

from __future__ import annotations

from collections.abc import Callable
from datetime import datetime

from sqlalchemy import func, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.resolution_engine.contracts.execution import (
    ExecuteResolutionCommand,
    StartExecutionResult,
    StepStartResult,
)
from app.resolution_engine.domain.canonical import canonical_sha256
from app.resolution_engine.domain.enums import (
    ExecutionStatus,
    IdempotencyScope,
    ResolutionStatus,
)
from app.resolution_engine.domain.exceptions import (
    ExecutionAlreadyInProgressError,
    ExecutionIdempotencyConflictError,
    ExecutionLockUnavailableError,
    ExecutionNotReadyError,
)
from app.resolution_engine.domain.execution import (
    DomainActionResult,
    ExecutionCandidate,
    ExecutionOutcome,
    ExecutionPlanStep,
    ExecutionReservation,
    ExecutionSummary,
)
from app.resolution_engine.domain.lifecycle import LifecycleTransition
from app.resolution_engine.domain.security import ActorContext
from app.resolution_engine.domain.value_objects import ComponentKey
from app.resolution_engine.infrastructure.execution_control import (
    SqlAlchemyExecutionControl,
)
from app.resolution_engine.infrastructure.lifecycle import (
    SqlAlchemyLifecycleStore,
)
from app.resolution_engine.infrastructure.outbox import (
    enqueue_outbox_event,
)
from app.resolution_engine.infrastructure.persistence import (
    Resolution,
    ResolutionAuditEvent,
    ResolutionEntityReference,
    ResolutionExecution,
    ResolutionIdempotencyRecord,
    ResolutionPlan,
    ResolutionPlanStep,
    ResolutionPlanStepDependency,
    ResolutionRevalidation,
    ResolutionResult as ResolutionResultModel,
    ResolutionStepExecution,
)
from app.resolution_engine.infrastructure.security_decisions import (
    SecurityDecisionExpectation,
    SqlAlchemySecurityDecisionVerifier,
)
from app.resolution_engine.infrastructure.repositories import (
    ResolutionRepository,
)


class SqlAlchemyExecutionStore:
    """Implementa checkpoints durables mediante sesiones cortas."""

    def __init__(self, session_factory: Callable[[], Session]) -> None:
        self._session_factory = session_factory
        self._control = SqlAlchemyExecutionControl()
        self._security = SqlAlchemySecurityDecisionVerifier()

    def load_candidate(
        self,
        resolution_id: int,
        /,
    ) -> ExecutionCandidate | None:
        with self._session_factory() as session:
            lifecycle = SqlAlchemyLifecycleStore(session).load(resolution_id)
            if lifecycle is None:
                return None
            record = ResolutionRepository(session).load_record(resolution_id)
            if record is None:
                return None
            plan = next(
                (
                    item
                    for item in record.plans
                    if item.id == record.resolution.current_plan_id
                ),
                None,
            )
            if plan is None:
                raise ExecutionNotReadyError("current plan is missing")
            revalidations = [
                item
                for item in record.revalidations
                if item.plan_id == plan.id
            ]
            if not revalidations:
                raise ExecutionNotReadyError(
                    "current plan has no revalidation"
                )
            revalidation = revalidations[-1]
            dependencies: dict[int, list[int]] = {}
            for edge in record.plan_step_dependencies:
                if edge.plan_id == plan.id:
                    dependencies.setdefault(edge.step_id, []).append(
                        edge.depends_on_step_id
                    )
            steps = tuple(
                ExecutionPlanStep(
                    id=item.id,
                    step_key=item.step_key,
                    sequence=item.sequence,
                    operation_key=item.operation_key,
                    owner_module=item.owner_module,
                    input_payload=item.input_payload,
                    preconditions=tuple(item.preconditions),
                    dependency_ids=tuple(
                        sorted(dependencies.get(item.id, ()))
                    ),
                )
                for item in record.plan_steps
                if item.plan_id == plan.id
            )
            context = lifecycle.evidence.context
            if context is None:
                raise ExecutionNotReadyError("current context is missing")
            return ExecutionCandidate(
                lifecycle=lifecycle,
                plan_id=plan.id,
                plan_version=plan.version,
                plan_hash=plan.plan_hash,
                revalidation_id=revalidation.id,
                revalidation_hash=revalidation.revalidation_hash,
                initial_context_hash=context.context_hash,
                steps=steps,
            )

    def verify_security(
        self,
        command: ExecuteResolutionCommand,
        candidate: ExecutionCandidate,
        *,
        occurred_at: datetime,
    ) -> None:
        with self._session_factory() as session:
            self._validate_execution_security(
                session,
                command=command,
                plan_id=candidate.plan_id,
                revalidation_id=candidate.revalidation_id,
                occurred_at=occurred_at,
            )

    def find_outcome(
        self,
        *,
        idempotency_key: str,
        request_hash: str,
    ) -> ExecutionOutcome | None:
        return self._existing_execution_in_new_session(
            key=idempotency_key,
            request_hash=request_hash,
        )

    def start(
        self,
        *,
        command: ExecuteResolutionCommand,
        steps: tuple[ExecutionPlanStep, ...],
        transition: LifecycleTransition,
        execution_key: str,
        lock_token: str,
        request_hash: str,
        occurred_at: datetime,
    ) -> StartExecutionResult:
        try:
            with self._session_factory() as session:
                with session.begin():
                    prepared_plan_id, prepared_revalidation_id = (
                        self._validate_prepared_evidence(
                            session,
                            transition=transition,
                        )
                    )
                    self._validate_execution_security(
                        session,
                        command=command,
                        plan_id=prepared_plan_id,
                        revalidation_id=prepared_revalidation_id,
                        occurred_at=occurred_at,
                    )
                    previous = self._existing_execution(
                        session,
                        key=command.idempotency_key,
                        request_hash=request_hash,
                    )
                    if previous is not None:
                        return StartExecutionResult(
                            previous_outcome=previous
                        )
                    lock_key = f"resolution:{command.resolution_id}"
                    self._control.acquire_lock(
                        session,
                        resolution_id=command.resolution_id,
                        lock_key=lock_key,
                        owner=command.lock_owner,
                        token=lock_token,
                        acquired_at=occurred_at,
                        expires_at=occurred_at + command.lock_ttl,
                    )
                    execution = ResolutionExecution(
                        resolution_id=command.resolution_id,
                        plan_id=prepared_plan_id,
                        revalidation_id=prepared_revalidation_id,
                        security_decision_id=(
                            command.security_decision_id
                        ),
                        attempt_number=1,
                        status=ExecutionStatus.RUNNING.value,
                        execution_key=execution_key,
                        started_at=occurred_at,
                        executed_by_actor_id=(
                            command.actor.identity.actor_id
                        ),
                        lock_token=lock_token,
                        initial_context_hash=(
                            self._required_context_hash(
                                session,
                                transition.resolution_id,
                            )
                        ),
                        correlation_id=(
                            command.actor.authentication.correlation_id
                        ),
                        metadata_json={},
                    )
                    session.add(execution)
                    session.flush()
                    step_rows = self._create_step_rows(
                        session,
                        execution=execution,
                        steps=steps,
                        execution_key=execution_key,
                    )
                    self._control.create_idempotency(
                        session,
                        scope=IdempotencyScope.RESOLUTION_EXECUTION,
                        key=command.idempotency_key,
                        operation_key="resolution.execute",
                        request_hash=request_hash,
                        resolution_id=command.resolution_id,
                        execution_id=execution.id,
                    )
                    lifecycle = SqlAlchemyLifecycleStore(session).apply(
                        transition
                    )
                    self._enqueue_execution_event(
                        session,
                        resolution=record_root(session, command.resolution_id),
                        execution=execution,
                        event_type="resolution.execution_started",
                        occurred_at=occurred_at,
                        payload={
                            "execution_id": execution.id,
                            "plan_id": execution.plan_id,
                            "revalidation_id": execution.revalidation_id,
                            "step_count": len(steps),
                        },
                    )
                    reservation = ExecutionReservation(
                        execution_id=execution.id,
                        resolution_id=execution.resolution_id,
                        plan_id=execution.plan_id,
                        plan_version=(
                            lifecycle.evidence.plan.version
                            if lifecycle.evidence.plan
                            else 0
                        ),
                        plan_hash=(
                            lifecycle.evidence.plan.plan_hash
                            if lifecycle.evidence.plan
                            else ""
                        ),
                        revalidation_id=execution.revalidation_id,
                        revalidation_hash=(
                            self._required_revalidation_hash(
                                session,
                                execution.revalidation_id,
                            )
                        ),
                        security_decision_id=(
                            command.security_decision_id
                        ),
                        execution_key=execution.execution_key,
                        lock_token=lock_token,
                        actor_id=command.actor.identity.actor_id,
                        actor_type=command.actor.identity.actor_type.value,
                        actor_source=command.actor.authentication.source,
                        correlation_id=(
                            execution.correlation_id or ""
                        ),
                        lifecycle=lifecycle,
                        steps=steps,
                        step_execution_ids={
                            step_id: row.id
                            for step_id, row in step_rows.items()
                        },
                    )
                return StartExecutionResult(reservation=reservation)
        except (
            ExecutionAlreadyInProgressError,
            ExecutionIdempotencyConflictError,
            ExecutionLockUnavailableError,
        ):
            raise
        except IntegrityError as exc:
            previous = self._existing_execution_in_new_session(
                key=command.idempotency_key,
                request_hash=request_hash,
            )
            if previous is not None:
                return StartExecutionResult(previous_outcome=previous)
            raise ExecutionLockUnavailableError(
                f"Concurrent execution rejected for "
                f"resolution {command.resolution_id}"
            ) from exc

    def renew_lock(
        self,
        reservation: ExecutionReservation,
        *,
        expires_at: datetime,
        occurred_at: datetime,
    ) -> None:
        with self._session_factory() as session:
            with session.begin():
                self._control.renew_lock(
                    session,
                    resolution_id=reservation.resolution_id,
                    token=reservation.lock_token,
                    occurred_at=occurred_at,
                    expires_at=expires_at,
                )

    def assert_lock(
        self,
        reservation: ExecutionReservation,
        *,
        occurred_at: datetime,
    ) -> None:
        with self._session_factory() as session:
            self._control.assert_lock(
                session,
                resolution_id=reservation.resolution_id,
                token=reservation.lock_token,
                occurred_at=occurred_at,
            )

    def start_step(
        self,
        reservation: ExecutionReservation,
        step: ExecutionPlanStep,
        *,
        request_hash: str,
        occurred_at: datetime,
    ) -> StepStartResult:
        key = self._step_key(reservation.execution_key, step.step_key)
        with self._session_factory() as session:
            with session.begin():
                previous = self._control.find_idempotency(
                    session,
                    scope=IdempotencyScope.STEP_EXECUTION,
                    key=key,
                )
                if previous is not None:
                    payload = self._control.validate_idempotency(
                        previous,
                        request_hash=request_hash,
                    )
                    return StepStartResult(
                        step_execution_id=(
                            previous.step_execution_id or 0
                        ),
                        previous_result=(
                            DomainActionResult.from_snapshot(payload)
                            if payload
                            else None
                        ),
                    )
                step_execution_id = reservation.step_execution_ids[step.id]
                result = session.execute(
                    update(ResolutionStepExecution)
                    .where(
                        ResolutionStepExecution.id == step_execution_id,
                        ResolutionStepExecution.execution_id
                        == reservation.execution_id,
                        ResolutionStepExecution.status == "pending",
                    )
                    .values(
                        status="running",
                        started_at=occurred_at,
                        request_payload=step.request_snapshot(),
                    )
                )
                if result.rowcount != 1:
                    raise ExecutionAlreadyInProgressError(
                        f"Step is not pending: {step.step_key}"
                    )
                self._control.create_idempotency(
                    session,
                    scope=IdempotencyScope.STEP_EXECUTION,
                    key=key,
                    operation_key=step.operation_key,
                    request_hash=request_hash,
                    resolution_id=reservation.resolution_id,
                    execution_id=reservation.execution_id,
                    step_execution_id=step_execution_id,
                )
                self._append_audit(
                    session,
                    reservation=reservation,
                    event_type="resolution.step_started",
                    occurred_at=occurred_at,
                    payload={
                        "step_id": step.id,
                        "step_key": step.step_key,
                        "operation_key": step.operation_key,
                    },
                )
                return StepStartResult(
                    step_execution_id=step_execution_id
                )

    def record_step_result(
        self,
        reservation: ExecutionReservation,
        step: ExecutionPlanStep,
        result: DomainActionResult,
        *,
        occurred_at: datetime,
    ) -> None:
        self._record_step_result(
            reservation,
            step,
            result,
            occurred_at=occurred_at,
            require_active_lock=True,
        )

    def record_uncertain_lock_loss(
        self,
        reservation: ExecutionReservation,
        step: ExecutionPlanStep,
        result: DomainActionResult,
        *,
        occurred_at: datetime,
    ) -> None:
        if result.success or result.step_status.value != "blocked":
            raise ExecutionNotReadyError(
                "lock loss requires an uncertain blocked result"
            )
        self._record_step_result(
            reservation,
            step,
            result,
            occurred_at=occurred_at,
            require_active_lock=False,
        )

    def _record_step_result(
        self,
        reservation: ExecutionReservation,
        step: ExecutionPlanStep,
        result: DomainActionResult,
        *,
        occurred_at: datetime,
        require_active_lock: bool,
    ) -> None:
        key = self._step_key(reservation.execution_key, step.step_key)
        with self._session_factory() as session:
            with session.begin():
                if require_active_lock:
                    self._control.assert_lock(
                        session,
                        resolution_id=reservation.resolution_id,
                        token=reservation.lock_token,
                        occurred_at=occurred_at,
                        for_update=True,
                    )
                step_execution_id = reservation.step_execution_ids[step.id]
                row = session.get(
                    ResolutionStepExecution,
                    step_execution_id,
                )
                if (
                    row is None
                    or row.execution_id != reservation.execution_id
                    or row.status != "running"
                ):
                    raise ExecutionAlreadyInProgressError(
                        f"Step cannot be completed: {step.step_key}"
                    )
                row.status = result.step_status.value
                row.completed_at = occurred_at
                row.response_payload = dict(result.response_payload)
                row.error_code = result.error_code
                row.error_message = result.error_message
                row.error_details = dict(result.error_details)
                row.retryable = False
                row.retry_count = 0
                row.domain_transaction_reference = (
                    result.domain_transaction_reference
                )
                idempotency = self._control.find_idempotency(
                    session,
                    scope=IdempotencyScope.STEP_EXECUTION,
                    key=key,
                )
                if idempotency is None:
                    raise ExecutionNotReadyError(
                        f"Step idempotency is missing: {step.step_key}"
                    )
                self._control.finish_idempotency(
                    idempotency,
                    succeeded=result.success,
                    response_payload=result.snapshot(),
                    completed_at=occurred_at,
                )
                for effect in result.entity_effects:
                    session.add(
                        ResolutionEntityReference(
                            resolution_id=reservation.resolution_id,
                            execution_id=reservation.execution_id,
                            step_execution_id=step_execution_id,
                            relationship_type=effect.relationship.value,
                            entity_type=effect.entity_type,
                            entity_id=effect.entity_id,
                            public_identifier=effect.public_identifier,
                            module=effect.module,
                            before_snapshot=(
                                dict(effect.before_snapshot)
                                if effect.before_snapshot is not None
                                else None
                            ),
                            after_snapshot=(
                                dict(effect.after_snapshot)
                                if effect.after_snapshot is not None
                                else None
                            ),
                            metadata_json=dict(effect.metadata),
                        )
                    )
                event_type = (
                    "resolution.step_completed"
                    if result.success
                    else (
                        "resolution.step_blocked"
                        if result.step_status.value == "blocked"
                        else "resolution.step_failed"
                    )
                )
                payload = {
                    "step_id": step.id,
                    "step_key": step.step_key,
                    "operation_key": step.operation_key,
                    "result": result.snapshot(),
                }
                self._append_audit(
                    session,
                    reservation=reservation,
                    event_type=event_type,
                    occurred_at=occurred_at,
                    payload=payload,
                )
                enqueue_outbox_event(
                    session,
                    resolution_id=reservation.resolution_id,
                    event_key=(
                        f"{event_type}:{reservation.execution_id}:"
                        f"{step_execution_id}"
                    ),
                    event_type=event_type,
                    aggregate_id=str(reservation.resolution_id),
                    payload=payload,
                    occurred_at=occurred_at,
                    correlation_id=reservation.correlation_id,
                )

    def finish(
        self,
        reservation: ExecutionReservation,
        summary: ExecutionSummary,
        transition: LifecycleTransition,
        *,
        outcome: ExecutionOutcome,
        completed_at: datetime,
        actor: ActorContext,
    ) -> ExecutionOutcome:
        with self._session_factory() as session:
            with session.begin():
                execution = session.get(
                    ResolutionExecution,
                    reservation.execution_id,
                )
                if execution is None or execution.status != "running":
                    raise ExecutionNotReadyError(
                        "execution is not running"
                    )
                execution.status = summary.execution_status.value
                execution.completed_at = completed_at
                execution.retryable = False
                execution.retry_after = None
                if summary.failed_step_keys:
                    execution.error_code = (
                        "action_result_uncertain"
                        if summary.execution_status
                        is ExecutionStatus.BLOCKED
                        else "action_failed"
                    )
                    execution.error_message = (
                        "Execution stopped at: "
                        + ", ".join(summary.failed_step_keys)
                    )
                if summary.resolution_result is not None:
                    context_id = session.scalar(
                        select(Resolution.current_context_snapshot_id).where(
                            Resolution.id == reservation.resolution_id
                        )
                    )
                    session.add(
                        ResolutionResultModel(
                            resolution_id=reservation.resolution_id,
                            execution_id=reservation.execution_id,
                            status=summary.resolution_result.value,
                            summary=self._result_summary(summary),
                            created_entities=self._effects(
                                summary,
                                "created",
                            ),
                            modified_entities=self._effects(
                                summary,
                                "modified",
                            ),
                            preserved_entities=self._effects(
                                summary,
                                "preserved",
                            ),
                            failed_steps=list(summary.failed_step_keys),
                            warnings=list(summary.warnings),
                            follow_up_actions=[],
                            final_context_snapshot_id=context_id,
                            completed_at=completed_at,
                            completed_by_actor_id=actor.identity.actor_id,
                            result_hash=outcome.result_hash,
                            metadata_json={},
                        )
                    )
                lifecycle = SqlAlchemyLifecycleStore(session).apply(
                    transition
                )
                idempotency = self._control.find_idempotency(
                    session,
                    scope=IdempotencyScope.RESOLUTION_EXECUTION,
                    key=outcome.idempotency_key,
                )
                if idempotency is None:
                    raise ExecutionNotReadyError(
                        "execution idempotency is missing"
                    )
                final_outcome = ExecutionOutcome(
                    execution_id=outcome.execution_id,
                    resolution_id=outcome.resolution_id,
                    execution_status=outcome.execution_status,
                    resolution_status=lifecycle.status.value,
                    idempotency_key=outcome.idempotency_key,
                    idempotent_replay=False,
                    completed_steps=outcome.completed_steps,
                    failed_steps=outcome.failed_steps,
                    blocked_steps=outcome.blocked_steps,
                    total_steps=outcome.total_steps,
                    result_hash=outcome.result_hash,
                )
                self._control.finish_idempotency(
                    idempotency,
                    succeeded=summary.execution_status in {
                        ExecutionStatus.COMPLETED,
                        ExecutionStatus.PARTIALLY_COMPLETED,
                    },
                    response_payload=final_outcome.snapshot(),
                    completed_at=completed_at,
                )
                self._control.release_lock(
                    session,
                    resolution_id=reservation.resolution_id,
                    token=reservation.lock_token,
                    released_at=completed_at,
                    required=(
                        summary.execution_status
                        is not ExecutionStatus.BLOCKED
                    ),
                )
                event_type = {
                    ExecutionStatus.COMPLETED:
                        "resolution.execution_completed",
                    ExecutionStatus.PARTIALLY_COMPLETED:
                        "resolution.execution_partially_completed",
                    ExecutionStatus.FAILED:
                        "resolution.execution_failed",
                    ExecutionStatus.BLOCKED:
                        "resolution.execution_blocked",
                }[summary.execution_status]
                self._enqueue_execution_event(
                    session,
                    resolution=record_root(
                        session,
                        reservation.resolution_id,
                    ),
                    execution=execution,
                    event_type=event_type,
                    occurred_at=completed_at,
                    payload=final_outcome.snapshot(),
                )
            return final_outcome

    def _existing_execution(
        self,
        session: Session,
        *,
        key: str,
        request_hash: str,
    ) -> ExecutionOutcome | None:
        record = self._control.find_idempotency(
            session,
            scope=IdempotencyScope.RESOLUTION_EXECUTION,
            key=key,
        )
        if record is None:
            return None
        payload = self._control.validate_idempotency(
            record,
            request_hash=request_hash,
        )
        if payload is None:
            raise ExecutionAlreadyInProgressError(
                f"Execution has no reusable result: {key}"
            )
        return ExecutionOutcome.from_snapshot(
            payload,
            idempotent_replay=True,
        )

    def _existing_execution_in_new_session(
        self,
        *,
        key: str,
        request_hash: str,
    ) -> ExecutionOutcome | None:
        with self._session_factory() as session:
            return self._existing_execution(
                session,
                key=key,
                request_hash=request_hash,
            )

    @staticmethod
    def _create_step_rows(
        session: Session,
        *,
        execution: ResolutionExecution,
        steps: tuple[ExecutionPlanStep, ...],
        execution_key: str,
    ) -> dict[int, ResolutionStepExecution]:
        rows = {}
        for step in steps:
            row = ResolutionStepExecution(
                execution_id=execution.id,
                plan_id=execution.plan_id,
                plan_step_id=step.id,
                status="pending",
                attempt_number=1,
                step_execution_key=SqlAlchemyExecutionStore._step_key(
                    execution_key,
                    step.step_key,
                ),
                request_payload={},
                response_payload={},
                error_details={},
                retryable=False,
                retry_count=0,
                metadata_json={},
            )
            session.add(row)
            rows[step.id] = row
        session.flush()
        return rows

    @staticmethod
    def _validate_prepared_evidence(
        session: Session,
        *,
        transition: LifecycleTransition,
    ) -> tuple[int, int]:
        metadata = transition.event.payload["metadata"]
        plan_id = metadata.get("plan_id")
        revalidation_id = metadata.get("revalidation_id")
        if plan_id is None or revalidation_id is None:
            raise ExecutionNotReadyError(
                "start transition does not identify exact evidence"
            )
        lifecycle = SqlAlchemyLifecycleStore(session).load(
            transition.resolution_id
        )
        plan = lifecycle.evidence.plan if lifecycle else None
        revalidation = (
            lifecycle.evidence.revalidation if lifecycle else None
        )
        if plan is None or plan.id != int(plan_id):
            raise ExecutionNotReadyError(
                "prepared plan is no longer current"
            )
        if (
            revalidation is None
            or revalidation.id != int(revalidation_id)
            or revalidation.plan_id != int(plan_id)
        ):
            raise ExecutionNotReadyError(
                "prepared revalidation is no longer current"
            )
        return int(plan_id), int(revalidation_id)

    @staticmethod
    def _required_context_hash(
        session: Session,
        resolution_id: int,
    ) -> str:
        lifecycle = SqlAlchemyLifecycleStore(session).load(resolution_id)
        evidence = lifecycle.evidence.context if lifecycle else None
        if evidence is None:
            raise ExecutionNotReadyError("context evidence is missing")
        return evidence.context_hash

    @staticmethod
    def _required_revalidation_hash(
        session: Session,
        revalidation_id: int,
    ) -> str:
        value = session.scalar(
            select(ResolutionRevalidation.revalidation_hash).where(
                ResolutionRevalidation.id == revalidation_id
            )
        )
        if value is None:
            raise ExecutionNotReadyError(
                "revalidation evidence is missing"
            )
        return value

    def _validate_execution_security(
        self,
        session: Session,
        *,
        command: ExecuteResolutionCommand,
        plan_id: int,
        revalidation_id: int,
        occurred_at: datetime,
    ) -> None:
        plan = session.get(ResolutionPlan, plan_id)
        revalidation = session.get(
            ResolutionRevalidation,
            revalidation_id,
        )
        if plan is None or revalidation is None:
            raise ExecutionNotReadyError(
                "execution authorization evidence is incomplete"
            )
        reasons = self._security.verify(
            session,
            SecurityDecisionExpectation(
                decision_id=command.security_decision_id,
                action="resolution.execute",
                resource_type="resolution_plan",
                resource_id=str(plan.id),
                actor=command.actor,
                required_permissions=(
                    ComponentKey("resolution.execute"),
                ),
                occurred_at=occurred_at,
                resolution_id=command.resolution_id,
                plan_id=plan.id,
                plan_version=plan.version,
                plan_hash=plan.plan_hash,
                revalidation_id=revalidation.id,
                revalidation_hash=revalidation.revalidation_hash,
                context={
                    "resolution_status": (
                        ResolutionStatus.READY_FOR_EXECUTION.value
                    ),
                },
            ),
        )
        if reasons:
            raise ExecutionNotReadyError(
                "exact execution authorization is invalid: "
                + ", ".join(reasons)
            )

    @staticmethod
    def _step_key(execution_key: str, step_key: str) -> str:
        return "step:" + canonical_sha256(
            {"execution_key": execution_key, "step_key": step_key}
        )

    @staticmethod
    def _append_audit(
        session: Session,
        *,
        reservation: ExecutionReservation,
        event_type: str,
        occurred_at: datetime,
        payload: dict,
    ) -> None:
        sequence = session.scalar(
            select(func.max(ResolutionAuditEvent.sequence)).where(
                ResolutionAuditEvent.resolution_id
                == reservation.resolution_id
            )
        )
        session.add(
            ResolutionAuditEvent(
                resolution_id=reservation.resolution_id,
                sequence=(sequence or 0) + 1,
                event_type=event_type,
                actor_id=reservation.actor_id,
                actor_type=reservation.actor_type,
                occurred_at=occurred_at,
                previous_state=ResolutionStatus.EXECUTING.value,
                new_state=ResolutionStatus.EXECUTING.value,
                plan_id=reservation.plan_id,
                plan_version=reservation.plan_version,
                execution_id=reservation.execution_id,
                correlation_id=reservation.correlation_id,
                source=reservation.actor_source,
                payload=payload,
                payload_hash=canonical_sha256(payload),
                metadata_json={},
            )
        )

    @staticmethod
    def _enqueue_execution_event(
        session: Session,
        *,
        resolution: Resolution,
        execution: ResolutionExecution,
        event_type: str,
        occurred_at: datetime,
        payload: dict,
    ) -> None:
        enqueue_outbox_event(
            session,
            resolution_id=resolution.id,
            event_key=f"{event_type}:{execution.id}",
            event_type=event_type,
            aggregate_id=str(resolution.id),
            payload=payload,
            occurred_at=occurred_at,
            correlation_id=execution.correlation_id,
        )

    @staticmethod
    def _effects(
        summary: ExecutionSummary,
        relationship: str,
    ) -> list[dict]:
        return [
            item.snapshot()
            for item in summary.effects
            if item.relationship.value == relationship
        ]

    @staticmethod
    def _result_summary(summary: ExecutionSummary) -> str:
        if summary.execution_status is ExecutionStatus.COMPLETED:
            return "Execution completed successfully"
        if summary.execution_status is ExecutionStatus.PARTIALLY_COMPLETED:
            return "Execution completed with partial effects"
        return "Execution failed without confirmed completed steps"


def record_root(session: Session, resolution_id: int) -> Resolution:
    root = session.get(Resolution, resolution_id)
    if root is None:
        raise ExecutionNotReadyError(
            f"Resolution not found: {resolution_id}"
        )
    return root
