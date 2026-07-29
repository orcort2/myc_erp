"""Adaptador público hacia Lifecycle, seguridad y auditoría canónicos."""

from __future__ import annotations

from dataclasses import replace
from datetime import datetime, timezone

from sqlalchemy import and_, func, or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.db import SessionLocal
from app.resolution_engine.application.audit import AuditQueryService
from app.resolution_engine.application.lifecycle import ResolutionLifecycleService
from app.resolution_engine.application.registry import ResolutionRegistry
from app.resolution_engine.application.security import (
    ResolutionAuthorizationService,
    SecurityPolicyEvaluator,
)
from app.resolution_engine.contracts.audit import (
    AUDIT_READ_ACTION,
    AuditQuery,
    audit_security_operation_payload,
)
from app.resolution_engine.contracts.lifecycle import (
    CreateResolutionCommand,
    ResolutionProblemInput,
)
from app.resolution_engine.domain.canonical import canonical_sha256
from app.resolution_engine.domain.enums import ResolutionPriority, ResolutionSource
from app.resolution_engine.domain.exceptions import ResolutionEngineError
from app.resolution_engine.domain.lifecycle import ResolutionStateMachine
from app.resolution_engine.domain.security import (
    SecurityDecisionOutcome,
    SecurityDecisionUseMode,
    SecurityRequest,
    SecurityResource,
)
from app.resolution_engine.domain.value_objects import ComponentKey
from app.resolution_engine.infrastructure.audit import (
    SqlAlchemyAuditAccessVerifier,
    SqlAlchemyAuditRecordStore,
)
from app.resolution_engine.infrastructure.lifecycle import SqlAlchemyLifecycleStore
from app.resolution_engine.infrastructure.persistence import (
    Resolution,
    ResolutionSecurityDecision,
)
from app.resolution_engine.infrastructure.runtime import (
    SystemClock,
    UuidIdentifierFactory,
)
from app.resolution_engine.infrastructure.security import (
    SqlAlchemySecurityEvidenceStore,
    SqlAlchemySecurityResourceVerifier,
)
from app.resolution_integrations.installed import (
    build_installed_resolution_integrations,
)
from app.resolution_public_api.errors import PublicApiError
from app.resolution_public_api.cursor import (
    CURSOR_CONTRACT_VERSION,
    CURSOR_DIRECTION,
    CursorPosition,
    CursorQueryIdentity,
    CursorValidationError,
    PublicCursorCodec,
)
from app.resolution_public_api.security import PublicApiConsumerContext
from myc_resolution_contracts.v1 import (
    ApiCapabilities,
    CreateResolutionRequest,
    ResolutionCollection,
    ResolutionResource,
    TimelineEntry,
)


class ResolutionPublicApi:
    """Único punto de composición de la interfaz pública v1."""

    def __init__(self, session: Session) -> None:
        self._session = session
        self._clock = SystemClock()
        self._cursor_codec = PublicCursorCodec(settings.secret_key)

    def capabilities(self) -> ApiCapabilities:
        integrations = build_installed_resolution_integrations(SessionLocal)
        return ApiCapabilities(
            supported_resolution_types=tuple(
                str(item.definition.resolution_type)
                for item in integrations
            ),
            operations=("resolution.create", "resolution.get", "resolution.list"),
        )

    def create(
        self,
        request: CreateResolutionRequest,
        *,
        context: PublicApiConsumerContext,
        idempotency_key: str,
    ) -> ResolutionResource:
        request_hash = canonical_sha256(request.model_dump(mode="json"))
        request_key = self._request_key(context, idempotency_key)
        existing = self._session.scalar(
            select(Resolution).where(Resolution.request_key == request_key)
        )
        if existing is not None:
            if existing.metadata_json.get("public_request_hash") != request_hash:
                raise self._error(
                    context, 409, "idempotency_conflict",
                    "The idempotency key was already used with another request.",
                )
            return self._inspect(existing, context=context, include_timeline=True)

        registry = ResolutionRegistry()
        for item in build_installed_resolution_integrations(SessionLocal):
            item.integration.register(registry)
        registry.freeze()
        try:
            definition = registry.resolve(
                request.resolution_type,
                request.definition_version,
            )
        except ResolutionEngineError as exc:
            raise self._error(
                context, 422, "unsupported_resolution_definition", str(exc)
            ) from exc
        problem = ResolutionProblemInput(
            problem_code=request.problem.code,
            summary=request.problem.summary,
            detected_by=request.problem.detected_by,
            detected_at=request.problem.detected_at,
            description=request.problem.description,
            source_payload=request.problem.source_payload,
            external_reference=request.problem.external_reference,
            severity=ResolutionPriority(request.problem.severity),
            observed_state=request.problem.observed_state,
            evidence=tuple(request.problem.evidence),
        )
        provisional = CreateResolutionCommand(
            resolution_type=request.resolution_type,
            definition_version=request.definition_version,
            source=ResolutionSource.SYSTEM,
            subject_type=request.subject_type,
            subject_id=request.subject_id,
            title=request.title,
            description=request.description,
            reason=request.reason,
            priority=ResolutionPriority(request.priority),
            requires_authorization=request.requires_authorization,
            problem=problem,
            actor=context.actor,
            security_decision_id=1,
            request_key=request_key,
            metadata={
                **request.metadata,
                "public_contract_version": "1.0",
                "public_consumer_key": context.consumer.consumer_key,
                "public_request_hash": request_hash,
            },
        )
        operation_id = request_key
        decision = self._authorize(
            context=context,
            action="resolution.create",
            resource=SecurityResource(
                resource_type="resolution_definition",
                resource_id=(
                    f"{definition.resolution_type}@{definition.version}"
                ),
                organization_id=context.consumer.organization_id,
            ),
            use_mode=SecurityDecisionUseMode.SINGLE_OPERATION,
            operation_id=operation_id,
            operation_payload=provisional.security_operation_payload(definition),
            security_context={"source": provisional.source.value},
        )
        if decision.outcome is SecurityDecisionOutcome.DENIED:
            self._session.commit()
            raise self._error(
                context, 403, "authorization_denied",
                "The consumer is not authorized for this operation.",
                {"reason_codes": list(decision.reason_codes)},
            )
        self._session.flush()
        evidence = self._session.scalar(
            select(ResolutionSecurityDecision)
            .where(ResolutionSecurityDecision.evidence_hash == decision.evidence_hash)
            .order_by(ResolutionSecurityDecision.id.desc())
        )
        assert evidence is not None
        command = replace(provisional, security_decision_id=evidence.id)
        try:
            lifecycle = ResolutionLifecycleService(
                registry=registry,
                store=SqlAlchemyLifecycleStore(self._session),
                state_machine=ResolutionStateMachine(),
                clock=self._clock,
                identifiers=UuidIdentifierFactory(),
            ).create(command)
            self._session.commit()
        except IntegrityError:
            self._session.rollback()
            winner = self._session.scalar(
                select(Resolution).where(Resolution.request_key == request_key)
            )
            if winner is None:
                raise
            if winner.metadata_json.get("public_request_hash") != request_hash:
                raise self._error(
                    context, 409, "idempotency_conflict",
                    "The idempotency key was concurrently used with another request.",
                )
            return self._inspect(
                winner, context=context, include_timeline=True
            )
        root = self._session.get(Resolution, lifecycle.resolution_id)
        assert root is not None
        return self._inspect(root, context=context, include_timeline=True)

    def get(
        self,
        public_id: str,
        *,
        context: PublicApiConsumerContext,
    ) -> ResolutionResource:
        root = self._session.scalar(
            select(Resolution).where(
                Resolution.public_id == public_id,
                Resolution.organization_id == context.consumer.organization_id,
            )
        )
        if root is None:
            raise self._error(context, 404, "resolution_not_found", "Resolution not found.")
        return self._inspect(root, context=context, include_timeline=True)

    def list(
        self,
        *,
        context: PublicApiConsumerContext,
        status: str | None,
        resolution_type: str | None,
        subject_type: str | None,
        subject_id: str | None,
        cursor: str | None,
        limit: int,
        sort: str,
    ) -> ResolutionCollection:
        cursor_identity = self._cursor_identity(
            context=context,
            status=status,
            resolution_type=resolution_type,
            subject_type=subject_type,
            subject_id=subject_id,
            limit=limit,
            sort=sort,
        )
        statement = select(Resolution).where(
            Resolution.organization_id == context.consumer.organization_id
        )
        for column, value in (
            (Resolution.status, status),
            (Resolution.resolution_type, resolution_type),
            (Resolution.subject_type, subject_type),
            (Resolution.subject_id, subject_id),
        ):
            if value is not None:
                statement = statement.where(column == value)
        sqlite = self._session.get_bind().dialect.name == "sqlite"
        order_column = (
            func.datetime(Resolution.created_at)
            if sqlite
            else Resolution.created_at
        )
        if cursor:
            try:
                position = self._cursor_codec.decode(
                    cursor,
                    expected_identity=cursor_identity,
                )
            except CursorValidationError as exc:
                raise self._error(
                    context,
                    422,
                    "invalid_cursor",
                    "Cursor is invalid for this query.",
                    {"reason": exc.reason},
                ) from None
            created_at = position.created_at
            order_value = (
                created_at.strftime("%Y-%m-%d %H:%M:%S")
                if sqlite
                else created_at
            )
            if sort == "created_at_desc":
                statement = statement.where(
                    or_(
                        order_column < order_value,
                        and_(
                            order_column == order_value,
                            Resolution.id < position.internal_id,
                        ),
                    )
                )
            else:
                statement = statement.where(
                    or_(
                        order_column > order_value,
                        and_(
                            order_column == order_value,
                            Resolution.id > position.internal_id,
                        ),
                    )
                )
        ordering = (
            (order_column.desc(), Resolution.id.desc())
            if sort == "created_at_desc"
            else (order_column.asc(), Resolution.id.asc())
        )
        roots = tuple(
            self._session.scalars(
                statement.order_by(*ordering).limit(limit + 1)
            )
        )
        page = roots[:limit]
        items = tuple(
            self._inspect(root, context=context, include_timeline=False)
            for root in page
        )
        next_cursor = (
            self._cursor_codec.encode(
                identity=cursor_identity,
                position=CursorPosition(
                    created_at=page[-1].created_at,
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
            sort=sort,
        )

    def _inspect(
        self,
        root: Resolution,
        *,
        context: PublicApiConsumerContext,
        include_timeline: bool,
    ) -> ResolutionResource:
        query_context = {
            "contract_version": "1.0",
            "consumer_key": context.consumer.consumer_key,
        }
        operation_id = (
            f"public:v1:audit:{context.consumer.consumer_key}:{root.public_id}"
        )
        decision = self._authorize(
            context=context,
            action=AUDIT_READ_ACTION,
            resource=SecurityResource(
                resource_type="resolution",
                resource_id=str(root.id),
                organization_id=context.consumer.organization_id,
                resolution_id=root.id,
                resolution_public_id=root.public_id,
            ),
            use_mode=SecurityDecisionUseMode.REUSABLE_READ,
            operation_id=operation_id,
            operation_payload=audit_security_operation_payload(
                resolution_id=root.id,
                context=query_context,
            ),
        )
        self._session.flush()
        evidence = self._session.scalar(
            select(ResolutionSecurityDecision)
            .where(ResolutionSecurityDecision.evidence_hash == decision.evidence_hash)
            .order_by(ResolutionSecurityDecision.id.desc())
        )
        if decision.outcome is SecurityDecisionOutcome.DENIED or evidence is None:
            self._session.commit()
            raise self._error(
                context, 403, "authorization_denied",
                "The consumer is not authorized to inspect this resolution.",
                {"reason_codes": list(decision.reason_codes)},
            )
        report = AuditQueryService(
            store=SqlAlchemyAuditRecordStore(self._session),
            access_verifier=SqlAlchemyAuditAccessVerifier(self._session),
        ).inspect(
            AuditQuery(
                resolution_id=root.id,
                security_decision_id=evidence.id,
                actor=context.actor,
                requested_at=self._clock.now(),
                operation_id=operation_id,
                context=query_context,
            )
        )
        self._session.commit()
        self._session.refresh(root)
        return ResolutionResource(
            id=root.public_id,
            resolution_type=root.resolution_type,
            definition_version=root.definition_version,
            status=root.status,
            priority=root.priority,
            source=root.source,
            subject_type=root.subject_type,
            subject_id=root.subject_id,
            title=root.title,
            description=root.description,
            reason=root.reason,
            version=root.version,
            correlation_id=root.correlation_id,
            created_at=_as_utc(root.created_at),
            updated_at=_as_utc(root.updated_at),
            audit_valid=report.is_valid,
            record_hash=report.record_hash,
            timeline=(
                tuple(
                    TimelineEntry(
                        sequence=item.sequence,
                        kind=item.kind,
                        occurred_at=item.occurred_at,
                        actor_id=item.actor_id,
                        correlation_id=item.correlation_id,
                        summary=item.summary,
                        integrity=item.integrity.value,
                    )
                    for item in report.timeline
                )
                if include_timeline
                else ()
            ),
        )

    def _authorize(
        self,
        *,
        context,
        action,
        resource,
        use_mode,
        operation_id,
        operation_payload,
        security_context=None,
    ):
        return ResolutionAuthorizationService(
            evaluator=SecurityPolicyEvaluator(()),
            evidence_store=SqlAlchemySecurityEvidenceStore(self._session),
            resource_verifier=SqlAlchemySecurityResourceVerifier(self._session),
            clock=self._clock,
        ).authorize(
            SecurityRequest(
                actor=context.actor,
                action=ComponentKey(action),
                resource=resource,
                required_permissions=(ComponentKey(action),),
                use_mode=use_mode,
                operation_id=operation_id,
                operation_payload=operation_payload,
                context=security_context
                or {
                    "contract_version": "1.0",
                    "consumer_key": context.consumer.consumer_key,
                },
            )
        )

    def _request_key(self, context, idempotency_key: str) -> str:
        digest = canonical_sha256(
            {
                "contract": "1.0",
                "consumer": context.consumer.consumer_key,
                "organization": context.consumer.organization_id,
                "idempotency_key": idempotency_key,
            }
        )
        return f"public-v1:{digest}"

    @staticmethod
    def _cursor_identity(
        *,
        context,
        status,
        resolution_type,
        subject_type,
        subject_id,
        limit,
        sort,
    ) -> CursorQueryIdentity:
        return CursorQueryIdentity.build(
            contract_version=CURSOR_CONTRACT_VERSION,
            consumer_key=context.consumer.consumer_key,
            organization_id=context.consumer.organization_id,
            filters={
                "status": status,
                "resolution_type": resolution_type,
                "subject_type": subject_type,
                "subject_id": subject_id,
            },
            sort=sort,
            direction=CURSOR_DIRECTION,
            page_size=limit,
        )

    @staticmethod
    def _error(context, status, code, message, details=None):
        return PublicApiError(
            status_code=status,
            code=code,
            message=message,
            correlation_id=context.correlation_id,
            details=details,
        )


def _as_utc(value: datetime) -> datetime:
    return (
        value.replace(tzinfo=timezone.utc)
        if value.tzinfo is None
        else value.astimezone(timezone.utc)
    )
