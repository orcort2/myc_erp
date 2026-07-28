"""Proyecciones de lectura consolidadas; nunca son fuente de verdad."""

from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import String, and_, case, cast, func, or_, select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.user import User
from app.resolution_center.schemas import (
    ResolutionCollection,
    ResolutionCenterIndicators,
    ResolutionDetail,
    ResolutionListItem,
    TimelineEntry,
)
from app.resolution_engine.infrastructure.persistence import (
    Resolution,
    ResolutionAnalysis,
    ResolutionAuditEvent,
    ResolutionAuthorizationDecision,
    ResolutionAuthorizationRequest,
    ResolutionCompensationExecution,
    ResolutionCompensationPlan,
    ResolutionContextSnapshot,
    ResolutionEvidenceReference,
    ResolutionExecution,
    ResolutionPlan,
    ResolutionPlanStep,
    ResolutionResult,
    ResolutionRevalidation,
    ResolutionSecurityDecision,
    ResolutionSimulation,
    ResolutionStepExecution,
    ResolutionWorkEvent,
    ResolutionWorkItem,
)
from app.resolution_public_api.cursor import (
    CURSOR_DIRECTION,
    CursorPosition,
    CursorQueryIdentity,
    CursorValidationError,
    PublicCursorCodec,
)


ACTIVE_STATES = frozenset(
    {
        "draft",
        "context_ready",
        "analyzed",
        "plan_ready",
        "simulated",
        "pending_authorization",
        "authorized",
        "revalidating",
        "ready_for_execution",
        "executing",
    }
)


class ResolutionCenterNotFoundError(LookupError):
    pass


class ResolutionCenterCursorError(ValueError):
    pass


class ResolutionOperationsQueryService:
    """Construye lista, expediente y timeline desde proyecciones SQL."""

    def __init__(self, session: Session) -> None:
        self._session = session
        self._cursor = PublicCursorCodec(settings.secret_key)
        self._actor_cache: dict[str, str] = {}

    def list(
        self,
        *,
        organization_id: str,
        actor_id: str,
        can_read_all: bool,
        search: str | None = None,
        requester: str | None = None,
        authorizer: str | None = None,
        resolution_type: str | None = None,
        subject_type: str | None = None,
        subject_id: str | None = None,
        lifecycle_status: str | None = None,
        distributed_status: str | None = None,
        result: str | None = None,
        created_from: datetime | None = None,
        created_to: datetime | None = None,
        has_retries: bool | None = None,
        blocked: bool | None = None,
        compensated: bool | None = None,
        cursor: str | None = None,
        limit: int = 50,
    ) -> ResolutionCollection:
        filters = {
            "search": search,
            "requester": requester,
            "authorizer": authorizer,
            "resolution_type": resolution_type,
            "subject_type": subject_type,
            "subject_id": subject_id,
            "lifecycle_status": lifecycle_status,
            "distributed_status": distributed_status,
            "result": result,
            "created_from": created_from.isoformat() if created_from else None,
            "created_to": created_to.isoformat() if created_to else None,
            "has_retries": str(has_retries) if has_retries is not None else None,
            "blocked": str(blocked) if blocked is not None else None,
            "compensated": (
                str(compensated) if compensated is not None else None
            ),
            "can_read_all": str(can_read_all),
        }
        identity = CursorQueryIdentity.build(
            contract_version="resolution-center-v1",
            consumer_key=actor_id,
            organization_id=organization_id,
            filters=filters,
            sort="created_at_desc",
            direction=CURSOR_DIRECTION,
            page_size=limit,
        )
        latest_work = (
            select(
                ResolutionWorkItem.resolution_id.label("resolution_id"),
                func.max(ResolutionWorkItem.id).label("work_id"),
            )
            .group_by(ResolutionWorkItem.resolution_id)
            .subquery()
        )
        statement = (
            select(Resolution)
            .outerjoin(
                latest_work,
                latest_work.c.resolution_id == Resolution.id,
            )
            .outerjoin(
                ResolutionWorkItem,
                ResolutionWorkItem.id == latest_work.c.work_id,
            )
            .outerjoin(
                ResolutionResult,
                ResolutionResult.resolution_id == Resolution.id,
            )
            .where(Resolution.organization_id == organization_id)
        )
        if not can_read_all:
            statement = statement.where(
                Resolution.requested_by_actor_id == actor_id
            )
        if search:
            term = f"%{search.strip()}%"
            matching_actor_ids = [
                f"user:{user_id}"
                for user_id in self._session.scalars(
                    select(User.id).where(
                        or_(
                            User.full_name.ilike(term),
                            User.email.ilike(term),
                        )
                    )
                )
            ]
            statement = statement.where(
                or_(
                    Resolution.public_id.ilike(term),
                    Resolution.title.ilike(term),
                    Resolution.subject_id.ilike(term),
                    Resolution.description.ilike(term),
                    Resolution.reason.ilike(term),
                    cast(Resolution.metadata_json, String).ilike(term),
                    Resolution.requested_by_actor_id.in_(
                        matching_actor_ids
                    ),
                )
            )
        if requester:
            statement = statement.where(
                Resolution.requested_by_actor_id.in_(
                    self._matching_actor_ids(requester)
                )
            )
        for column, value in (
            (Resolution.resolution_type, resolution_type),
            (Resolution.subject_type, subject_type),
            (Resolution.subject_id, subject_id),
            (Resolution.status, lifecycle_status),
            (ResolutionWorkItem.status, distributed_status),
            (ResolutionResult.status, result),
        ):
            if value:
                statement = statement.where(column == value)
        if authorizer:
            statement = statement.where(
                Resolution.id.in_(
                    select(ResolutionAuthorizationRequest.resolution_id)
                    .join(
                        ResolutionAuthorizationDecision,
                        ResolutionAuthorizationDecision.authorization_request_id
                        == ResolutionAuthorizationRequest.id,
                    )
                    .where(
                        ResolutionAuthorizationDecision.approver_actor_id.in_(
                            self._matching_actor_ids(authorizer)
                        )
                    )
                )
            )
        if created_from:
            statement = statement.where(Resolution.created_at >= created_from)
        if created_to:
            statement = statement.where(Resolution.created_at <= created_to)
        if has_retries is not None:
            predicate = func.coalesce(ResolutionWorkItem.attempt_count, 0) > 1
            statement = statement.where(predicate if has_retries else ~predicate)
        if blocked is not None:
            predicate = or_(
                Resolution.status == "blocked",
                func.coalesce(ResolutionWorkItem.status, "") == "blocked",
            )
            statement = statement.where(predicate if blocked else ~predicate)
        if compensated is not None:
            predicate = Resolution.status.in_(
                ("compensated", "partially_compensated")
            )
            statement = statement.where(
                predicate if compensated else ~predicate
            )
        order_column = Resolution.created_at
        if cursor:
            try:
                position = self._cursor.decode(
                    cursor,
                    expected_identity=identity,
                )
            except CursorValidationError as exc:
                raise ResolutionCenterCursorError(exc.reason) from None
            statement = statement.where(
                or_(
                    order_column < position.created_at,
                    and_(
                        order_column == position.created_at,
                        Resolution.id < position.internal_id,
                    ),
                )
            )
        roots = tuple(
            self._session.scalars(
                statement.distinct()
                .order_by(order_column.desc(), Resolution.id.desc())
                .limit(limit + 1)
            )
        )
        page = roots[:limit]
        items = self._summaries(page)
        next_cursor = (
            self._cursor.encode(
                identity=identity,
                position=CursorPosition(
                    created_at=_aware(page[-1].created_at),
                    internal_id=page[-1].id,
                ),
            )
            if len(roots) > limit and page
            else None
        )
        return ResolutionCollection(
            items=items,
            next_cursor=next_cursor,
            limit=limit,
        )

    def indicators(
        self,
        *,
        organization_id: str,
        actor_id: str,
        can_read_all: bool,
    ) -> ResolutionCenterIndicators:
        """Calcula el tablero operativo íntegramente en backend."""

        latest_work = (
            select(
                ResolutionWorkItem.resolution_id.label("resolution_id"),
                func.max(ResolutionWorkItem.id).label("work_id"),
            )
            .group_by(ResolutionWorkItem.resolution_id)
            .subquery()
        )
        scoped = (
            select(
                Resolution.id.label("resolution_id"),
                Resolution.status.label("lifecycle_status"),
                ResolutionWorkItem.status.label("work_status"),
                func.coalesce(ResolutionWorkItem.attempt_count, 0).label(
                    "attempt_count"
                ),
            )
            .outerjoin(
                latest_work,
                latest_work.c.resolution_id == Resolution.id,
            )
            .outerjoin(
                ResolutionWorkItem,
                ResolutionWorkItem.id == latest_work.c.work_id,
            )
            .where(Resolution.organization_id == organization_id)
        )
        if not can_read_all:
            scoped = scoped.where(
                Resolution.requested_by_actor_id == actor_id
            )
        projection = scoped.subquery()
        row = self._session.execute(
            select(
                func.count().label("total"),
                func.sum(
                    case(
                        (
                            projection.c.lifecycle_status.in_(
                                tuple(ACTIVE_STATES - {"authorized", "executing"})
                            ),
                            1,
                        ),
                        else_=0,
                    )
                ).label("pending"),
                func.sum(
                    case(
                        (
                            projection.c.lifecycle_status.in_(
                                ("authorized", "ready_for_execution")
                            ),
                            1,
                        ),
                        else_=0,
                    )
                ).label("authorized"),
                func.sum(
                    case(
                        (
                            or_(
                                projection.c.lifecycle_status == "executing",
                                projection.c.work_status == "claimed",
                            ),
                            1,
                        ),
                        else_=0,
                    )
                ).label("executing"),
                func.sum(
                    case(
                        (
                            projection.c.lifecycle_status.in_(
                                ("completed", "compensated")
                            ),
                            1,
                        ),
                        else_=0,
                    )
                ).label("completed"),
                func.sum(
                    case(
                        (
                            or_(
                                projection.c.lifecycle_status == "failed",
                                projection.c.work_status == "failed",
                            ),
                            1,
                        ),
                        else_=0,
                    )
                ).label("failed"),
                func.sum(
                    case(
                        (
                            or_(
                                projection.c.lifecycle_status == "blocked",
                                projection.c.work_status == "blocked",
                            ),
                            1,
                        ),
                        else_=0,
                    )
                ).label("blocked"),
                func.sum(
                    case(
                        (
                            projection.c.lifecycle_status.in_(
                                ("compensated", "partially_compensated")
                            ),
                            1,
                        ),
                        else_=0,
                    )
                ).label("compensated"),
                func.sum(
                    case(
                        (projection.c.attempt_count > 1, 1),
                        else_=0,
                    )
                ).label("with_retries"),
            ).select_from(projection)
        ).one()
        return ResolutionCenterIndicators(
            **{
                key: int(getattr(row, key) or 0)
                for key in (
                    "total",
                    "pending",
                    "authorized",
                    "executing",
                    "completed",
                    "failed",
                    "blocked",
                    "compensated",
                    "with_retries",
                )
            }
        )

    def get(
        self,
        public_id: str,
        *,
        organization_id: str,
        actor_id: str,
        can_read_all: bool,
        include_technical: bool,
        include_audit: bool = False,
    ) -> ResolutionDetail:
        root = self._root(
            public_id,
            organization_id=organization_id,
            actor_id=actor_id,
            can_read_all=can_read_all,
        )
        plan = (
            self._session.get(ResolutionPlan, root.current_plan_id)
            if root.current_plan_id
            else None
        )
        simulation = (
            self._session.scalar(
                select(ResolutionSimulation)
                .where(ResolutionSimulation.resolution_id == root.id)
                .order_by(ResolutionSimulation.id.desc())
            )
            if plan
            else None
        )
        result = self._session.scalar(
            select(ResolutionResult).where(
                ResolutionResult.resolution_id == root.id
            )
        )
        work = self._latest_work(root.id)
        analysis = self._session.scalar(
            select(ResolutionAnalysis)
            .where(ResolutionAnalysis.resolution_id == root.id)
            .order_by(ResolutionAnalysis.analysis_version.desc())
        )
        executions = tuple(
            self._session.scalars(
                select(ResolutionExecution)
                .where(ResolutionExecution.resolution_id == root.id)
                .order_by(ResolutionExecution.attempt_number)
            )
        )
        execution_ids = tuple(item.id for item in executions)
        step_executions = (
            tuple(
                self._session.scalars(
                    select(ResolutionStepExecution)
                    .where(
                        ResolutionStepExecution.execution_id.in_(execution_ids)
                    )
                    .order_by(
                        ResolutionStepExecution.execution_id,
                        ResolutionStepExecution.id,
                    )
                )
            )
            if execution_ids
            else ()
        )
        compensation_plans = tuple(
            self._session.scalars(
                select(ResolutionCompensationPlan)
                .where(ResolutionCompensationPlan.resolution_id == root.id)
                .order_by(ResolutionCompensationPlan.id)
            )
        )
        compensation_executions = tuple(
            self._session.scalars(
                select(ResolutionCompensationExecution)
                .where(
                    ResolutionCompensationExecution.resolution_id == root.id
                )
                .order_by(ResolutionCompensationExecution.id)
            )
        )
        recovery_events = tuple(
            self._session.scalars(
                select(ResolutionWorkEvent)
                .where(
                    ResolutionWorkEvent.resolution_id == root.id,
                    ResolutionWorkEvent.event_type.in_(
                        (
                            "lease_expired",
                            "recovered",
                            "retry_scheduled",
                            "retry_exhausted",
                        )
                    ),
                )
                .order_by(ResolutionWorkEvent.id)
            )
        )
        steps = (
            tuple(
                self._session.scalars(
                    select(ResolutionPlanStep)
                    .where(ResolutionPlanStep.plan_id == plan.id)
                    .order_by(ResolutionPlanStep.sequence)
                )
            )
            if plan
            else ()
        )
        decisions = tuple(
            self._session.scalars(
                select(ResolutionSecurityDecision)
                .where(ResolutionSecurityDecision.resolution_id == root.id)
                .order_by(ResolutionSecurityDecision.id)
            )
        )
        snapshots = tuple(
            self._session.scalars(
                select(ResolutionContextSnapshot)
                .where(ResolutionContextSnapshot.resolution_id == root.id)
                .order_by(ResolutionContextSnapshot.sequence)
            )
        )
        revalidations = tuple(
            self._session.scalars(
                select(ResolutionRevalidation)
                .where(ResolutionRevalidation.resolution_id == root.id)
                .order_by(ResolutionRevalidation.id)
            )
        )
        evidence_references = tuple(
            self._session.scalars(
                select(ResolutionEvidenceReference)
                .where(ResolutionEvidenceReference.resolution_id == root.id)
                .order_by(ResolutionEvidenceReference.id)
            )
        )
        snapshots_by_id = {item.id: item for item in snapshots}
        requires_new_plan = bool(
            revalidations
            and revalidations[-1].status
            in {"requires_new_plan", "no_longer_resolvable", "blocked"}
        )
        capabilities = (
            ()
            if root.status == "plan_ready" and requires_new_plan
            else _capabilities_for_status(root.status)
        )
        return ResolutionDetail(
            summary=self._summary(root),
            description=root.description,
            reason=root.reason,
            priority=root.priority,
            definition_version=root.definition_version,
            correlation_id=root.correlation_id,
            subject={
                "type": root.subject_type,
                "id": root.subject_id,
                "label": root.metadata_json.get("subject_label"),
                "route": root.metadata_json.get("subject_route"),
            },
            parameters=dict(root.metadata_json.get("parameters", {})),
            analysis=(
                {
                    "version": analysis.analysis_version,
                    "status": analysis.status,
                    "is_resolvable": analysis.is_resolvable,
                    "findings": analysis.findings,
                    "blockers": analysis.blockers,
                    "warnings": analysis.warnings,
                    "available_strategies": analysis.available_strategies,
                    "analyzed_at": _aware(analysis.analyzed_at),
                    "analyzed_by": self._actor_name(analysis.analyzed_by),
                }
                if analysis
                else None
            ),
            lifecycle=self.timeline(
                root,
                include_technical=include_technical,
            ),
            distributed=(
                {
                    "status": work.status,
                    "attempt_count": work.attempt_count,
                    "max_attempts": work.max_attempts,
                    "worker": work.claimed_by if include_technical else None,
                    "lease_expires_at": (
                        _aware(work.lease_expires_at)
                        if include_technical and work.lease_expires_at
                        else None
                    ),
                    "effect_started_at": (
                        _aware(work.effect_started_at)
                        if include_technical and work.effect_started_at
                        else None
                    ),
                    "last_error_code": work.last_error_code,
                    "last_error_message": work.last_error_message,
                }
                if work
                else None
            ),
            plan=(
                {
                    "version": plan.version,
                    "status": plan.status,
                    "summary": plan.summary,
                    "rationale": plan.rationale,
                    "expected_impact": plan.expected_impact,
                    "warnings": plan.warnings,
                    "blockers": plan.blockers,
                    "authorization_requirements": (
                        plan.authorization_requirements
                    ),
                    "steps": [
                        {
                            "sequence": step.sequence,
                            "description": step.description,
                            "owner_module": step.owner_module,
                            "criticality": step.criticality,
                            "is_compensable": step.is_compensable,
                        }
                        for step in steps
                    ],
                    **(
                        {"plan_hash": plan.plan_hash}
                        if include_technical
                        else {}
                    ),
                }
                if plan
                else None
            ),
            simulation=(
                {
                    "status": simulation.status,
                    "expected_actions": simulation.expected_actions,
                    "expected_changes": simulation.expected_changes,
                    "preserved_entities": simulation.preserved_entities,
                    "warnings": simulation.warnings,
                    "blockers": simulation.blockers,
                    "required_authorizations": (
                        simulation.required_authorizations
                    ),
                }
                if simulation
                else None
            ),
            result=(
                {
                    "status": result.status,
                    "summary": result.summary,
                    "created_entities": result.created_entities,
                    "modified_entities": result.modified_entities,
                    "preserved_entities": result.preserved_entities,
                    "failed_steps": result.failed_steps,
                    "warnings": result.warnings,
                    "follow_up_actions": result.follow_up_actions,
                    "generated_files": result.metadata_json.get(
                        "generated_files", []
                    ),
                    "emitted_events": result.metadata_json.get(
                        "emitted_events", []
                    ),
                    "compensations": result.metadata_json.get(
                        "compensations", []
                    ),
                }
                if result
                else None
            ),
            attempts=tuple(
                {
                    "attempt_number": item.attempt_number,
                    "status": item.status,
                    "started_at": (
                        _aware(item.started_at) if item.started_at else None
                    ),
                    "completed_at": (
                        _aware(item.completed_at) if item.completed_at else None
                    ),
                    "worker": item.worker_id if include_technical else None,
                    "retryable": item.retryable,
                    "retry_after": (
                        _aware(item.retry_after) if item.retry_after else None
                    ),
                    "error_code": item.error_code,
                    "error_message": item.error_message,
                    "steps": [
                        {
                            "status": step.status,
                            "attempt_number": step.attempt_number,
                            "retry_count": step.retry_count,
                            "error_code": step.error_code,
                        }
                        for step in step_executions
                        if step.execution_id == item.id
                    ],
                }
                for item in executions
            ),
            recovery=tuple(
                {
                    "event_type": item.event_type,
                    "occurred_at": _aware(item.occurred_at),
                    "attempt_number": item.attempt_number,
                    "details": (
                        dict(item.payload) if include_technical else {}
                    ),
                }
                for item in recovery_events
            ),
            compensations=tuple(
                {
                    "plan_id": plan.id,
                    "strategy": plan.strategy,
                    "reason": plan.reason,
                    "created_at": _aware(plan.created_at),
                    "execution": next(
                        (
                            {
                                "status": execution.status,
                                "started_at": _aware(execution.started_at),
                                "completed_at": (
                                    _aware(execution.completed_at)
                                    if execution.completed_at
                                    else None
                                ),
                            }
                            for execution in compensation_executions
                            if execution.plan_id == plan.id
                        ),
                        None,
                    ),
                }
                for plan in compensation_plans
            ),
            evidence={
                "security_decisions": [
                    {
                        "action": item.action,
                        "outcome": item.outcome,
                        "evaluated_at": _aware(item.evaluated_at),
                        **(
                            {
                                "evidence_hash": item.evidence_hash,
                                "operation_hash": item.operation_hash,
                            }
                            if include_technical
                            else {}
                        ),
                    }
                    for item in decisions if include_audit
                ],
                "context_snapshots": [
                    {
                        "snapshot_type": item.snapshot_type,
                        "sequence": item.sequence,
                        "version": item.context_version,
                        "captured_at": _aware(item.captured_at),
                        "captured_by": self._actor_name(
                            item.captured_by_actor_id
                        ),
                        **(
                            {
                                "context_hash": item.context_hash,
                                "facts": item.facts,
                            }
                            if include_technical
                            else {}
                        ),
                    }
                    for item in snapshots if include_audit
                ],
                "revalidations": [
                    {
                        "outcome": item.status,
                        "revalidated_at": _aware(item.revalidated_at),
                        **(
                            {
                                "revalidation_hash": item.revalidation_hash,
                                "authorized_context_hash": snapshots_by_id[
                                    item.previous_context_snapshot_id
                                ].context_hash,
                                "current_context_hash": snapshots_by_id[
                                    item.current_context_snapshot_id
                                ].context_hash,
                            }
                            if include_technical
                            else {}
                        ),
                    }
                    for item in revalidations if include_audit
                ],
                "references": [
                    {
                        "evidence_type": item.evidence_type,
                        "uploaded_at": _aware(item.uploaded_at),
                        "uploaded_by": self._actor_name(
                            item.uploaded_by_actor_id
                        ),
                        **(
                            {
                                "storage_reference": item.storage_reference,
                                "checksum": item.checksum,
                            }
                            if include_technical
                            else {}
                        ),
                    }
                    for item in evidence_references if include_audit
                ],
                "append_only": True,
            },
            capabilities=capabilities,
        )

    def timeline(
        self,
        root: Resolution,
        *,
        include_technical: bool,
    ) -> tuple[TimelineEntry, ...]:
        items: list[TimelineEntry] = []
        audit = self._session.scalars(
            select(ResolutionAuditEvent)
            .where(ResolutionAuditEvent.resolution_id == root.id)
            .order_by(ResolutionAuditEvent.occurred_at, ResolutionAuditEvent.id)
        )
        for event in audit:
            items.append(
                TimelineEntry(
                    occurred_at=_aware(event.occurred_at),
                    category="lifecycle",
                    event_type=event.event_type,
                    label=_event_label(event.event_type),
                    status=event.new_state,
                    actor=self._actor_name(event.actor_id),
                    details=(
                        dict(event.payload)
                        if include_technical
                        else {
                            key: value
                            for key, value in event.payload.items()
                            if key not in {"security_decision_id"}
                        }
                    ),
                    technical=False,
                )
            )
        work_events = self._session.scalars(
            select(ResolutionWorkEvent)
            .where(ResolutionWorkEvent.resolution_id == root.id)
            .order_by(ResolutionWorkEvent.occurred_at, ResolutionWorkEvent.id)
        )
        for event in work_events:
            details = dict(event.payload)
            if include_technical:
                details.update(
                    {
                        "node": event.node_id,
                        "attempt": event.attempt_number,
                        "lease_version": event.lease_version,
                    }
                )
            items.append(
                TimelineEntry(
                    occurred_at=_aware(event.occurred_at),
                    category="distributed",
                    event_type=event.event_type,
                    label=_event_label(event.event_type),
                    status=None,
                    actor=event.node_id if include_technical else None,
                    details=details,
                    technical=True,
                )
            )
        return tuple(
            sorted(items, key=lambda item: (item.occurred_at, item.event_type))
        )

    def _root(
        self,
        public_id: str,
        *,
        organization_id: str,
        actor_id: str,
        can_read_all: bool,
    ) -> Resolution:
        statement = select(Resolution).where(
            Resolution.public_id == public_id,
            Resolution.organization_id == organization_id,
        )
        if not can_read_all:
            statement = statement.where(
                Resolution.requested_by_actor_id == actor_id
            )
        root = self._session.scalar(statement)
        if root is None:
            raise ResolutionCenterNotFoundError(public_id)
        return root

    def _summary(self, root: Resolution) -> ResolutionListItem:
        work = self._latest_work(root.id)
        execution = self._session.scalar(
            select(ResolutionExecution)
            .where(ResolutionExecution.resolution_id == root.id)
            .order_by(ResolutionExecution.id.desc())
        )
        result = self._session.scalar(
            select(ResolutionResult).where(
                ResolutionResult.resolution_id == root.id
            )
        )
        authorization = self._session.scalar(
            select(ResolutionAuthorizationDecision)
            .join(
                ResolutionAuthorizationRequest,
                ResolutionAuthorizationRequest.id
                == ResolutionAuthorizationDecision.authorization_request_id,
            )
            .where(
                ResolutionAuthorizationRequest.resolution_id == root.id,
                ResolutionAuthorizationDecision.decision == "approved",
            )
            .order_by(ResolutionAuthorizationDecision.id.desc())
        )
        return self._summary_from(
            root,
            work=work,
            execution=execution,
            result=result,
            authorization=authorization,
        )

    def _summaries(
        self,
        roots: tuple[Resolution, ...],
    ) -> tuple[ResolutionListItem, ...]:
        if not roots:
            return ()
        resolution_ids = tuple(root.id for root in roots)
        works = {}
        for item in self._session.scalars(
            select(ResolutionWorkItem)
            .where(ResolutionWorkItem.resolution_id.in_(resolution_ids))
            .order_by(ResolutionWorkItem.id)
        ):
            works[item.resolution_id] = item
        executions = {}
        for item in self._session.scalars(
            select(ResolutionExecution)
            .where(ResolutionExecution.resolution_id.in_(resolution_ids))
            .order_by(ResolutionExecution.id)
        ):
            executions[item.resolution_id] = item
        results = {
            item.resolution_id: item
            for item in self._session.scalars(
                select(ResolutionResult).where(
                    ResolutionResult.resolution_id.in_(resolution_ids)
                )
            )
        }
        authorizations = {}
        for resolution_id, item in self._session.execute(
            select(
                ResolutionAuthorizationRequest.resolution_id,
                ResolutionAuthorizationDecision,
            )
            .join(
                ResolutionAuthorizationDecision,
                ResolutionAuthorizationDecision.authorization_request_id
                == ResolutionAuthorizationRequest.id,
            )
            .where(
                ResolutionAuthorizationRequest.resolution_id.in_(
                    resolution_ids
                ),
                ResolutionAuthorizationDecision.decision == "approved",
            )
            .order_by(ResolutionAuthorizationDecision.id)
        ):
            authorizations[resolution_id] = item
        actor_ids = {
            actor_id
            for actor_id in (
                *(root.requested_by_actor_id for root in roots),
                *(
                    item.approver_actor_id
                    for item in authorizations.values()
                ),
            )
            if actor_id and actor_id.startswith("user:")
        }
        user_ids = [
            int(actor_id.split(":", 1)[1])
            for actor_id in actor_ids
            if actor_id.split(":", 1)[1].isdigit()
        ]
        for user in self._session.scalars(
            select(User).where(User.id.in_(user_ids))
        ):
            self._actor_cache[f"user:{user.id}"] = user.full_name
        return tuple(
            self._summary_from(
                root,
                work=works.get(root.id),
                execution=executions.get(root.id),
                result=results.get(root.id),
                authorization=authorizations.get(root.id),
            )
            for root in roots
        )

    def _summary_from(
        self,
        root: Resolution,
        *,
        work: ResolutionWorkItem | None,
        execution: ResolutionExecution | None,
        result: ResolutionResult | None,
        authorization: ResolutionAuthorizationDecision | None,
    ) -> ResolutionListItem:
        authorized_at = authorization.decided_at if authorization else None
        started_at = execution.started_at if execution else None
        completed_at = root.completed_at or (
            execution.completed_at if execution else None
        )
        duration = (
            int((_aware(completed_at) - _aware(started_at)).total_seconds())
            if started_at and completed_at
            else None
        )
        return ResolutionListItem(
            public_id=root.public_id,
            resolution_type=root.resolution_type,
            title=root.title,
            subject_type=root.subject_type,
            subject_id=root.subject_id,
            subject_label=root.metadata_json.get("subject_label"),
            requester=self._actor_name(root.requested_by_actor_id),
            authorizer=self._actor_name(
                authorization.approver_actor_id if authorization else None
            ),
            lifecycle_status=root.status,
            execution_status=execution.status if execution else None,
            distributed_status=work.status if work else None,
            result=result.status if result else None,
            created_at=_aware(root.created_at),
            authorized_at=_aware(authorized_at) if authorized_at else None,
            started_at=_aware(started_at) if started_at else None,
            completed_at=_aware(completed_at) if completed_at else None,
            duration_seconds=duration,
            attempt_count=work.attempt_count if work else 0,
            has_retries=bool(work and work.attempt_count > 1),
            is_blocked=root.status == "blocked"
            or bool(work and work.status == "blocked"),
            is_compensated=root.status
            in {"compensated", "partially_compensated"},
        )

    def _latest_work(self, resolution_id: int) -> ResolutionWorkItem | None:
        return self._session.scalar(
            select(ResolutionWorkItem)
            .where(ResolutionWorkItem.resolution_id == resolution_id)
            .order_by(ResolutionWorkItem.id.desc())
        )

    def _actor_name(self, actor_id: str | None) -> str | None:
        if not actor_id:
            return None
        if actor_id in self._actor_cache:
            return self._actor_cache[actor_id]
        if actor_id.startswith("user:"):
            try:
                user = self._session.get(User, int(actor_id.split(":", 1)[1]))
            except ValueError:
                user = None
            if user:
                self._actor_cache[actor_id] = user.full_name
                return user.full_name
        return actor_id

    def _matching_actor_ids(self, value: str) -> tuple[str, ...]:
        normalized = value.strip()
        if normalized.startswith("user:"):
            return (normalized,)
        term = f"%{normalized}%"
        matches = tuple(
            f"user:{user_id}"
            for user_id in self._session.scalars(
                select(User.id).where(
                    or_(
                        User.full_name.ilike(term),
                        User.email.ilike(term),
                    )
                )
            )
        )
        return matches or (normalized,)


def _aware(value: datetime) -> datetime:
    return value if value.tzinfo else value.replace(tzinfo=timezone.utc)


def _event_label(event_type: str) -> str:
    return event_type.removeprefix("resolution.lifecycle.").removeprefix(
        "work."
    ).replace("_", " ").replace(".", " · ").capitalize()


def _capabilities_for_status(status: str) -> tuple[str, ...]:
    mapping = {
        "draft": ("prepare-context",),
        "context_ready": ("analyze",),
        "analyzed": ("build-plan",),
        "plan_ready": ("simulate",),
        "simulated": ("authorize",),
        "pending_authorization": ("authorize",),
        "ready_for_execution": ("execute",),
    }
    return mapping.get(status, ())
