"""Persistencia SQL de planes y ejecución compensatoria síncrona."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import replace
from datetime import datetime

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.resolution_engine.contracts.compensation import (
    ExecuteCompensationCommand,
    PrepareCompensationCommand,
    StartCompensationResult,
    compensation_security_operation_payload,
)
from app.resolution_engine.domain.canonical import canonical_sha256
from app.resolution_engine.domain.compensation import (
    CompensableAction,
    ConfirmedEffect,
    CompensationOutcome,
    CompensationPlan,
    CompensationPlanStep,
    CompensationReservation,
    CompensationSource,
    CompensationSummary,
    PreparedCompensation,
)
from app.resolution_engine.domain.enums import (
    CompensationStatus,
    ResolutionLockType,
    ResolutionStatus,
)
from app.resolution_engine.domain.exceptions import (
    CompensationIdempotencyConflictError,
    CompensationNotAllowedError,
    ExecutionAlreadyInProgressError,
    ExecutionLockUnavailableError,
)
from app.resolution_engine.domain.execution import DomainActionResult
from app.resolution_engine.domain.lifecycle import (
    CompensationEvidence,
    LifecycleTransition,
)
from app.resolution_engine.domain.security import (
    ActorContext,
    SecurityDecisionUseMode,
)
from app.resolution_engine.domain.value_objects import ComponentKey
from app.resolution_engine.infrastructure.execution_control import (
    SqlAlchemyExecutionControl,
)
from app.resolution_engine.infrastructure.lifecycle import (
    SqlAlchemyLifecycleStore,
)
from app.resolution_engine.infrastructure.outbox import enqueue_outbox_event
from app.resolution_engine.infrastructure.security_decisions import (
    SecurityDecisionExpectation,
    SqlAlchemySecurityDecisionVerifier,
)
from app.resolution_engine.infrastructure.persistence import (
    Resolution,
    ResolutionAuditEvent,
    ResolutionCompensationExecution,
    ResolutionCompensationPlan,
    ResolutionCompensationPlanStep,
    ResolutionCompensationStepExecution,
    ResolutionExecution,
    ResolutionPlanStep,
    ResolutionPlanStepDependency,
    ResolutionSecurityDecision,
    ResolutionStepExecution,
)


class SqlAlchemyCompensationStore:
    """Implementa planes inmutables y checkpoints en transacciones cortas."""

    def __init__(self, session_factory: Callable[[], Session]) -> None:
        self._session_factory = session_factory
        self._control = SqlAlchemyExecutionControl()
        self._security = SqlAlchemySecurityDecisionVerifier()

    def load_source(
        self,
        resolution_id: int,
        source_execution_id: int,
        /,
    ) -> CompensationSource | None:
        with self._session_factory() as session:
            lifecycle = SqlAlchemyLifecycleStore(session).load(resolution_id)
            execution = session.scalar(
                select(ResolutionExecution).where(
                    ResolutionExecution.id == source_execution_id,
                    ResolutionExecution.resolution_id == resolution_id,
                    ResolutionExecution.status.in_(
                        (
                            "completed",
                            "partially_completed",
                            "failed",
                        )
                    ),
                )
            )
            if lifecycle is None or execution is None:
                return None
            if lifecycle.status not in {
                ResolutionStatus.COMPLETED,
                ResolutionStatus.PARTIALLY_COMPLETED,
                ResolutionStatus.FAILED,
            }:
                return None
            completed_rows = tuple(
                session.scalars(
                    select(ResolutionStepExecution)
                    .where(
                        ResolutionStepExecution.execution_id
                        == source_execution_id,
                        ResolutionStepExecution.status == "completed",
                    )
                    .order_by(ResolutionStepExecution.id)
                )
            )
            if not completed_rows:
                return None
            compensated_step_ids = set(
                session.scalars(
                    select(
                        ResolutionCompensationStepExecution
                        .source_step_execution_id
                    ).where(
                        ResolutionCompensationStepExecution
                        .source_step_execution_id.in_(
                            row.id for row in completed_rows
                        ),
                        ResolutionCompensationStepExecution.status
                        == CompensationStatus.COMPENSATED.value,
                    )
                )
            )
            active_rows = tuple(
                row
                for row in completed_rows
                if row.id not in compensated_step_ids
            )
            if not active_rows:
                return None
            plan_step_ids = {
                row.plan_step_id for row in active_rows
            }
            plan_steps = {
                row.id: row
                for row in session.scalars(
                    select(ResolutionPlanStep).where(
                        ResolutionPlanStep.id.in_(plan_step_ids)
                    )
                )
            }
            dependencies: dict[int, list[int]] = {}
            for edge in session.scalars(
                select(ResolutionPlanStepDependency).where(
                    ResolutionPlanStepDependency.plan_id
                    == execution.plan_id
                )
            ):
                dependencies.setdefault(edge.step_id, []).append(
                    edge.depends_on_step_id
                )
            confirmed_effects = tuple(
                ConfirmedEffect(
                    plan_step_id=plan_steps[row.plan_step_id].id,
                    step_execution_id=row.id,
                    step_key=plan_steps[row.plan_step_id].step_key,
                    original_sequence=(
                        plan_steps[row.plan_step_id].sequence
                    ),
                    dependency_step_ids=tuple(
                        sorted(
                            dependencies.get(
                                plan_steps[row.plan_step_id].id,
                                (),
                            )
                        )
                    ),
                )
                for row in active_rows
            )
            if any(
                plan_steps[row.plan_step_id].point_of_no_return
                for row in active_rows
            ):
                return CompensationSource(
                    lifecycle=lifecycle,
                    execution_id=execution.id,
                    actions=(),
                    completed_step_execution_ids=tuple(
                        row.id for row in active_rows
                    ),
                    non_compensable_step_execution_ids=tuple(
                        row.id for row in active_rows
                    ),
                    confirmed_effects=confirmed_effects,
                )
            actions = []
            non_compensable = []
            for row in active_rows:
                step = plan_steps[row.plan_step_id]
                if (
                    not step.is_compensable
                    or not step.compensation_operation_key
                ):
                    non_compensable.append(row.id)
                    continue
                actions.append(
                    CompensableAction(
                        plan_step_id=step.id,
                        step_execution_id=row.id,
                        step_key=step.step_key,
                        original_sequence=step.sequence,
                        operation_key=step.operation_key,
                        compensation_operation_key=(
                            step.compensation_operation_key
                        ),
                        owner_module=step.owner_module,
                        compensation_payload=step.compensation_payload,
                        dependency_step_ids=tuple(
                            sorted(dependencies.get(step.id, ()))
                        ),
                    )
                )
            return CompensationSource(
                lifecycle=lifecycle,
                execution_id=execution.id,
                actions=tuple(actions),
                completed_step_execution_ids=tuple(
                    row.id for row in active_rows
                ),
                non_compensable_step_execution_ids=tuple(non_compensable),
                confirmed_effects=confirmed_effects,
            )

    def save_plan(
        self,
        command: PrepareCompensationCommand,
        plan: CompensationPlan,
        *,
        created_at: datetime,
    ) -> CompensationPlan:
        try:
            with self._session_factory() as session:
                with session.begin():
                    self._validate_security_decision(
                        session,
                        command,
                        occurred_at=created_at,
                        claim=True,
                    )
                    existing = session.scalar(
                        select(ResolutionCompensationPlan).where(
                            ResolutionCompensationPlan.plan_key
                            == command.idempotency_key
                        )
                    )
                    if existing is not None:
                        if (
                            existing.plan_hash != plan.plan_hash
                            or existing.resolution_id
                            != command.resolution_id
                            or existing.source_execution_id
                            != command.source_execution_id
                            or existing.security_decision_id
                            != command.security_decision_id
                            or existing.created_by_actor_id
                            != command.actor.identity.actor_id
                        ):
                            raise CompensationIdempotencyConflictError(
                                "compensation plan key has another request"
                            )
                        return self._domain_plan(session, existing)
                    row = ResolutionCompensationPlan(
                        resolution_id=plan.resolution_id,
                        source_execution_id=plan.source_execution_id,
                        security_decision_id=command.security_decision_id,
                        strategy=plan.strategy.value,
                        reason=plan.reason,
                        plan_key=command.idempotency_key,
                        plan_hash=plan.plan_hash,
                        created_by_actor_id=(
                            command.actor.identity.actor_id
                        ),
                        correlation_id=(
                            command.actor.authentication.correlation_id
                        ),
                        created_at=created_at,
                        metadata_json={
                            "selected_step_execution_ids": list(
                                command.selected_step_execution_ids
                            )
                        },
                    )
                    session.add(row)
                    session.flush()
                    for step in plan.steps:
                        session.add(
                            ResolutionCompensationPlanStep(
                                plan_id=row.id,
                                source_execution_id=plan.source_execution_id,
                                source_plan_step_id=(
                                    step.source_plan_step_id
                                ),
                                source_step_execution_id=(
                                    step.source_step_execution_id
                                ),
                                source_step_key=step.source_step_key,
                                sequence=step.sequence,
                                operation_key=step.operation_key,
                                owner_module=step.owner_module,
                                input_payload=dict(step.input_payload),
                                dependency_source_step_ids=list(
                                    step.dependency_source_step_ids
                                ),
                                step_hash=canonical_sha256(
                                    step.snapshot()
                                ),
                                created_at=created_at,
                            )
                        )
                    self._append_audit(
                        session,
                        resolution_id=plan.resolution_id,
                        event_type="resolution.compensation_plan_prepared",
                        actor_id=command.actor.identity.actor_id,
                        actor_type=(
                            command.actor.identity.actor_type.value
                        ),
                        source=command.actor.authentication.source,
                        correlation_id=(
                            command.actor.authentication.correlation_id
                        ),
                        occurred_at=created_at,
                        payload={
                            "compensation_plan_id": row.id,
                            "source_execution_id": plan.source_execution_id,
                            "strategy": plan.strategy.value,
                            "reason": plan.reason,
                            "plan_hash": plan.plan_hash,
                            "security_decision_id": (
                                command.security_decision_id
                            ),
                        },
                    )
                    session.flush()
                    return self._domain_plan(session, row)
        except IntegrityError as exc:
            raise CompensationNotAllowedError(
                "compensation plan conflicts with existing evidence"
            ) from exc

    def load_prepared(
        self,
        compensation_plan_id: int,
        actor: ActorContext,
        /,
    ) -> PreparedCompensation | None:
        with self._session_factory() as session:
            row = session.get(
                ResolutionCompensationPlan,
                compensation_plan_id,
            )
            if row is None:
                return None
            self._validate_execution_actor(
                session,
                plan=row,
                actor=actor,
            )
            lifecycle = SqlAlchemyLifecycleStore(session).load(
                row.resolution_id
            )
            if lifecycle is None:
                return None
            return PreparedCompensation(
                lifecycle=lifecycle,
                plan=self._domain_plan(session, row),
            )

    def find_outcome(
        self,
        *,
        idempotency_key: str,
        request_hash: str,
    ) -> CompensationOutcome | None:
        execution_key = self._execution_key(idempotency_key)
        with self._session_factory() as session:
            return self._existing_outcome(
                session,
                execution_key=execution_key,
                request_hash=request_hash,
            )

    def start(
        self,
        *,
        command: ExecuteCompensationCommand,
        prepared: PreparedCompensation,
        transition: LifecycleTransition,
        execution_key: str,
        lock_token: str,
        request_hash: str,
        occurred_at: datetime,
    ) -> StartCompensationResult:
        try:
            with self._session_factory() as session:
                with session.begin():
                    previous = self._existing_outcome(
                        session,
                        execution_key=execution_key,
                        request_hash=request_hash,
                    )
                    if previous is not None:
                        return StartCompensationResult(
                            previous_outcome=previous
                        )
                    current = session.get(
                        ResolutionCompensationPlan,
                        prepared.plan.id,
                    )
                    if (
                        current is None
                        or current.plan_hash != prepared.plan.plan_hash
                        or current.resolution_id
                        != transition.resolution_id
                    ):
                        raise CompensationNotAllowedError(
                            "prepared compensation plan changed"
                        )
                    self._validate_execution_actor(
                        session,
                        plan=current,
                        actor=command.actor,
                        occurred_at=occurred_at,
                    )
                    self._control.acquire_lock(
                        session,
                        resolution_id=current.resolution_id,
                        lock_key=f"resolution:{current.resolution_id}",
                        owner=command.lock_owner,
                        token=lock_token,
                        acquired_at=occurred_at,
                        expires_at=occurred_at + command.lock_ttl,
                        lock_type=ResolutionLockType.COMPENSATION,
                    )
                    execution = ResolutionCompensationExecution(
                        resolution_id=current.resolution_id,
                        plan_id=current.id,
                        source_execution_id=current.source_execution_id,
                        status=CompensationStatus.RUNNING.value,
                        execution_key=execution_key,
                        request_hash=request_hash,
                        lock_token=lock_token,
                        executed_by_actor_id=(
                            command.actor.identity.actor_id
                        ),
                        executed_by_actor_type=(
                            command.actor.identity.actor_type.value
                        ),
                        actor_source=command.actor.authentication.source,
                        correlation_id=(
                            command.actor.authentication.correlation_id
                        ),
                        started_at=occurred_at,
                    )
                    session.add(execution)
                    session.flush()
                    rows = {}
                    for step in prepared.plan.steps:
                        row = ResolutionCompensationStepExecution(
                            execution_id=execution.id,
                            plan_id=current.id,
                            plan_step_id=step.id,
                            source_step_execution_id=(
                                step.source_step_execution_id
                            ),
                            status="pending",
                            step_execution_key=canonical_sha256(
                                {
                                    "execution_key": execution_key,
                                    "source_step_execution_id": (
                                        step.source_step_execution_id
                                    ),
                                }
                            ),
                            request_payload={},
                        )
                        session.add(row)
                        rows[step.source_step_execution_id] = row
                    session.flush()
                    lifecycle = SqlAlchemyLifecycleStore(session).apply(
                        transition
                    )
                    lifecycle = replace(
                        lifecycle,
                        evidence=replace(
                            lifecycle.evidence,
                            compensation=CompensationEvidence(
                                plan_id=current.id,
                                execution_id=execution.id,
                                source_execution_id=(
                                    current.source_execution_id
                                ),
                                status=CompensationStatus.RUNNING.value,
                                total_steps=len(prepared.plan.steps),
                                compensated_steps=0,
                                failed_steps=0,
                                blocked_steps=0,
                            ),
                        ),
                    )
                    enqueue_outbox_event(
                        session,
                        resolution_id=current.resolution_id,
                        event_key=(
                            f"resolution.compensation_started:"
                            f"{execution.id}"
                        ),
                        event_type="resolution.compensation_started",
                        aggregate_id=str(current.resolution_id),
                        payload={
                            "compensation_plan_id": current.id,
                            "compensation_execution_id": execution.id,
                            "source_execution_id": (
                                current.source_execution_id
                            ),
                        },
                        occurred_at=occurred_at,
                        correlation_id=execution.correlation_id,
                    )
                    reservation = CompensationReservation(
                        plan=prepared.plan,
                        execution_id=execution.id,
                        execution_key=execution_key,
                        lock_token=lock_token,
                        lifecycle=lifecycle,
                        step_execution_ids={
                            key: value.id for key, value in rows.items()
                        },
                    )
                return StartCompensationResult(reservation=reservation)
        except IntegrityError as exc:
            raise ExecutionLockUnavailableError(
                "concurrent compensation rejected"
            ) from exc

    def renew_lock(
        self,
        reservation: CompensationReservation,
        *,
        expires_at: datetime,
        occurred_at: datetime,
    ) -> None:
        with self._session_factory() as session:
            with session.begin():
                self._control.renew_lock(
                    session,
                    resolution_id=reservation.plan.resolution_id,
                    token=reservation.lock_token,
                    occurred_at=occurred_at,
                    expires_at=expires_at,
                    lock_type=ResolutionLockType.COMPENSATION,
                )

    def assert_lock(
        self,
        reservation: CompensationReservation,
        *,
        occurred_at: datetime,
    ) -> None:
        with self._session_factory() as session:
            self._control.assert_lock(
                session,
                resolution_id=reservation.plan.resolution_id,
                token=reservation.lock_token,
                occurred_at=occurred_at,
                lock_type=ResolutionLockType.COMPENSATION,
            )

    def start_step(
        self,
        reservation: CompensationReservation,
        step: CompensationPlanStep,
        *,
        request_hash: str,
        occurred_at: datetime,
    ) -> DomainActionResult | None:
        row_id = reservation.step_execution_ids[
            step.source_step_execution_id
        ]
        with self._session_factory() as session:
            with session.begin():
                row = session.get(
                    ResolutionCompensationStepExecution,
                    row_id,
                )
                if row is None:
                    raise CompensationNotAllowedError(
                        "compensation checkpoint is missing"
                    )
                if row.request_hash is not None:
                    if row.request_hash != request_hash:
                        raise CompensationIdempotencyConflictError(
                            "compensation step has another request"
                        )
                    if row.result_payload is not None:
                        return DomainActionResult.from_snapshot(
                            row.result_payload
                        )
                    raise ExecutionAlreadyInProgressError(
                        "compensation step is already running"
                    )
                if row.status != "pending":
                    raise ExecutionAlreadyInProgressError(
                        "compensation step is not pending"
                    )
                row.status = "running"
                row.started_at = occurred_at
                row.request_hash = request_hash
                row.request_payload = step.snapshot()
                execution = session.get(
                    ResolutionCompensationExecution,
                    reservation.execution_id,
                )
                self._append_audit(
                    session,
                    resolution_id=reservation.plan.resolution_id,
                    event_type="resolution.compensation_step_started",
                    actor_id=(
                        execution.executed_by_actor_id
                        if execution else None
                    ),
                    actor_type=(
                        execution.executed_by_actor_type
                        if execution else "system"
                    ),
                    source=(
                        execution.actor_source
                        if execution else "resolution_engine"
                    ),
                    correlation_id=(
                        execution.correlation_id if execution else None
                    ),
                    occurred_at=occurred_at,
                    payload={
                        "compensation_plan_id": reservation.plan.id,
                        "compensation_execution_id": (
                            reservation.execution_id
                        ),
                        "source_step_execution_id": (
                            step.source_step_execution_id
                        ),
                        "operation_key": step.operation_key,
                    },
                )
                return None

    def record_step_result(
        self,
        reservation: CompensationReservation,
        step: CompensationPlanStep,
        result: DomainActionResult,
        *,
        occurred_at: datetime,
        require_active_lock: bool = True,
    ) -> None:
        row_id = reservation.step_execution_ids[
            step.source_step_execution_id
        ]
        with self._session_factory() as session:
            with session.begin():
                if require_active_lock:
                    self._control.assert_lock(
                        session,
                        resolution_id=reservation.plan.resolution_id,
                        token=reservation.lock_token,
                        occurred_at=occurred_at,
                        for_update=True,
                        lock_type=ResolutionLockType.COMPENSATION,
                    )
                row = session.get(
                    ResolutionCompensationStepExecution,
                    row_id,
                )
                if row is None or row.status != "running":
                    raise ExecutionAlreadyInProgressError(
                        "compensation step cannot be completed"
                    )
                row.status = (
                    "compensated"
                    if result.success
                    else (
                        "blocked"
                        if result.certainty.value == "uncertain"
                        else "failed"
                    )
                )
                row.completed_at = occurred_at
                row.result_payload = result.snapshot()
                row.domain_transaction_reference = (
                    result.domain_transaction_reference
                )
                row.error_code = result.error_code
                row.error_message = result.error_message
                payload = {
                    "compensation_plan_id": reservation.plan.id,
                    "compensation_execution_id": reservation.execution_id,
                    "source_step_execution_id": (
                        step.source_step_execution_id
                    ),
                    "result": result.snapshot(),
                }
                event_type = (
                    "resolution.compensation_step_completed"
                    if result.success
                    else (
                        "resolution.compensation_step_blocked"
                        if row.status == "blocked"
                        else "resolution.compensation_step_failed"
                    )
                )
                execution = session.get(
                    ResolutionCompensationExecution,
                    reservation.execution_id,
                )
                self._append_audit(
                    session,
                    resolution_id=reservation.plan.resolution_id,
                    event_type=event_type,
                    actor_id=(
                        execution.executed_by_actor_id
                        if execution else None
                    ),
                    actor_type=(
                        execution.executed_by_actor_type
                        if execution else "system"
                    ),
                    source=(
                        execution.actor_source
                        if execution else "resolution_engine"
                    ),
                    correlation_id=(
                        execution.correlation_id if execution else None
                    ),
                    occurred_at=occurred_at,
                    payload=payload,
                )
                enqueue_outbox_event(
                    session,
                    resolution_id=reservation.plan.resolution_id,
                    event_key=f"{event_type}:{row.id}",
                    event_type=event_type,
                    aggregate_id=str(reservation.plan.resolution_id),
                    payload=payload,
                    occurred_at=occurred_at,
                    correlation_id=(
                        execution.correlation_id if execution else None
                    ),
                )

    def finish(
        self,
        reservation: CompensationReservation,
        summary: CompensationSummary,
        transition: LifecycleTransition,
        *,
        outcome: CompensationOutcome,
        completed_at: datetime,
    ) -> CompensationOutcome:
        with self._session_factory() as session:
            with session.begin():
                execution = session.get(
                    ResolutionCompensationExecution,
                    reservation.execution_id,
                )
                if execution is None or execution.status != "running":
                    raise CompensationNotAllowedError(
                        "compensation is not running"
                    )
                execution.status = summary.status.value
                execution.completed_at = completed_at
                lifecycle = SqlAlchemyLifecycleStore(session).apply(
                    transition
                )
                final = replace(
                    outcome,
                    idempotent_replay=False,
                )
                execution.outcome_payload = final.snapshot()
                self._control.release_lock(
                    session,
                    resolution_id=reservation.plan.resolution_id,
                    token=reservation.lock_token,
                    released_at=completed_at,
                    required=(
                        summary.status is not CompensationStatus.BLOCKED
                    ),
                    lock_type=ResolutionLockType.COMPENSATION,
                )
                event_type = {
                    CompensationStatus.COMPENSATED:
                        "resolution.compensation_completed",
                    CompensationStatus.PARTIALLY_COMPENSATED:
                        "resolution.compensation_partially_completed",
                    CompensationStatus.FAILED:
                        "resolution.compensation_failed",
                    CompensationStatus.BLOCKED:
                        "resolution.compensation_blocked",
                }[summary.status]
                enqueue_outbox_event(
                    session,
                    resolution_id=reservation.plan.resolution_id,
                    event_key=f"{event_type}:{execution.id}",
                    event_type=event_type,
                    aggregate_id=str(reservation.plan.resolution_id),
                    payload={
                        **final.snapshot(),
                        "resolution_status": lifecycle.status.value,
                    },
                    occurred_at=completed_at,
                    correlation_id=execution.correlation_id,
                )
                return final

    def _validate_security_decision(
        self,
        session: Session,
        command: PrepareCompensationCommand,
        *,
        occurred_at: datetime,
        claim: bool = False,
    ) -> None:
        expectation = SecurityDecisionExpectation(
                decision_id=command.security_decision_id,
                action="resolution.compensate",
                resource_type="resolution_execution",
                resource_id=str(command.source_execution_id),
                actor=command.actor,
                required_permissions=(
                    ComponentKey("resolution.compensate"),
                ),
                occurred_at=occurred_at,
                use_mode=SecurityDecisionUseMode.SINGLE_OPERATION,
                operation_id=command.idempotency_key,
                operation_payload=compensation_security_operation_payload(
                    resolution_id=command.resolution_id,
                    source_execution_id=command.source_execution_id,
                    strategy=command.strategy.value,
                    reason=command.reason,
                    selected_step_execution_ids=(
                        command.selected_step_execution_ids
                    ),
                    actor_id=command.actor.identity.actor_id,
                    organization_id=(
                        command.actor.identity.organization_id
                    ),
                ),
                resolution_id=command.resolution_id,
                context={},
            )
        if claim:
            _, reasons = self._security.claim(session, expectation)
        else:
            reasons = self._security.verify(session, expectation)
        if reasons:
            raise CompensationNotAllowedError(
                "exact compensation authorization is invalid: "
                + ", ".join(reasons)
            )

    def _validate_execution_actor(
        self,
        session: Session,
        *,
        plan: ResolutionCompensationPlan,
        actor: ActorContext,
        occurred_at: datetime | None = None,
    ) -> None:
        root = session.get(Resolution, plan.resolution_id)
        decision = session.get(
            ResolutionSecurityDecision,
            plan.security_decision_id,
        )
        identity = actor.identity
        if (
            root is None
            or decision is None
            or decision.resolution_id != plan.resolution_id
            or decision.outcome != "allowed"
            or decision.action != "resolution.compensate"
            or decision.resource_type != "resolution_execution"
            or decision.resource_id != str(plan.source_execution_id)
            or plan.created_by_actor_id != identity.actor_id
            or decision.actor_id != identity.actor_id
            or decision.organization_id != identity.organization_id
            or root.organization_id != identity.organization_id
        ):
            raise CompensationNotAllowedError(
                "compensation execution actor is not authorized"
            )
        if occurred_at is not None:
            reasons = self._security.verify(
                session,
                SecurityDecisionExpectation(
                    decision_id=plan.security_decision_id,
                    action="resolution.compensate",
                    resource_type="resolution_execution",
                    resource_id=str(plan.source_execution_id),
                    actor=actor,
                    required_permissions=(
                        ComponentKey("resolution.compensate"),
                    ),
                    occurred_at=occurred_at,
                    use_mode=SecurityDecisionUseMode.SINGLE_OPERATION,
                    operation_id=plan.plan_key,
                    operation_payload=(
                        compensation_security_operation_payload(
                            resolution_id=plan.resolution_id,
                            source_execution_id=(
                                plan.source_execution_id
                            ),
                            strategy=plan.strategy,
                            reason=plan.reason,
                            selected_step_execution_ids=tuple(
                                plan.metadata_json.get(
                                    "selected_step_execution_ids",
                                    (),
                                )
                            ),
                            actor_id=plan.created_by_actor_id,
                            organization_id=identity.organization_id,
                        )
                    ),
                    resolution_id=plan.resolution_id,
                    context={},
                ),
            )
            if reasons:
                raise CompensationNotAllowedError(
                    "compensation execution authorization is invalid: "
                    + ", ".join(reasons)
                )

    @staticmethod
    def _domain_plan(
        session: Session,
        row: ResolutionCompensationPlan,
    ) -> CompensationPlan:
        step_rows = tuple(
            session.scalars(
                select(ResolutionCompensationPlanStep)
                .where(
                    ResolutionCompensationPlanStep.plan_id == row.id
                )
                .order_by(
                    ResolutionCompensationPlanStep.sequence,
                    ResolutionCompensationPlanStep.id,
                )
            )
        )
        return CompensationPlan(
            id=row.id,
            resolution_id=row.resolution_id,
            source_execution_id=row.source_execution_id,
            strategy=row.strategy,
            reason=row.reason,
            security_decision_id=row.security_decision_id,
            plan_hash=row.plan_hash,
            steps=tuple(
                CompensationPlanStep(
                    id=step.id,
                    sequence=step.sequence,
                    source_plan_step_id=step.source_plan_step_id,
                    source_step_execution_id=(
                        step.source_step_execution_id
                    ),
                    source_step_key=step.source_step_key,
                    operation_key=step.operation_key,
                    owner_module=step.owner_module,
                    input_payload=step.input_payload,
                    dependency_source_step_ids=tuple(
                        step.dependency_source_step_ids
                    ),
                )
                for step in step_rows
            ),
        )

    @staticmethod
    def _existing_outcome(
        session: Session,
        *,
        execution_key: str,
        request_hash: str,
    ) -> CompensationOutcome | None:
        row = session.scalar(
            select(ResolutionCompensationExecution).where(
                ResolutionCompensationExecution.execution_key
                == execution_key
            )
        )
        if row is None:
            return None
        if row.request_hash != request_hash:
            raise CompensationIdempotencyConflictError(
                "compensation execution key has another request"
            )
        if row.outcome_payload is None:
            raise ExecutionAlreadyInProgressError(
                "compensation execution is in progress"
            )
        return CompensationOutcome.from_snapshot(
            row.outcome_payload,
            idempotent_replay=True,
        )

    @staticmethod
    def _execution_key(idempotency_key: str) -> str:
        return canonical_sha256(
            {
                "scope": "compensation_execution",
                "idempotency_key": idempotency_key,
            }
        )

    @staticmethod
    def _append_audit(
        session: Session,
        *,
        resolution_id: int,
        event_type: str,
        actor_id: str | None,
        actor_type: str,
        source: str,
        correlation_id: str | None,
        occurred_at: datetime,
        payload: dict,
    ) -> None:
        sequence = session.scalar(
            select(func.max(ResolutionAuditEvent.sequence)).where(
                ResolutionAuditEvent.resolution_id == resolution_id
            )
        )
        session.add(
            ResolutionAuditEvent(
                resolution_id=resolution_id,
                sequence=(sequence or 0) + 1,
                event_type=event_type,
                actor_type=actor_type,
                actor_id=actor_id,
                occurred_at=occurred_at,
                correlation_id=correlation_id,
                source=source,
                payload=payload,
                payload_hash=canonical_sha256(payload),
                metadata_json={},
            )
        )
