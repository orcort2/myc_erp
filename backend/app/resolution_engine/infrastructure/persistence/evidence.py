"""Auditoría, idempotencia, locks, outbox y evidencia referenciada."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    ForeignKeyConstraint,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base
from app.resolution_engine.infrastructure.persistence.base import (
    BIGINT_ID,
    JSON_DOCUMENT,
    CreatedAtMixin,
    MutableTimestampMixin,
    ResolutionRecordMixin,
)


class ResolutionAuditEvent(ResolutionRecordMixin, Base):
    """Evento append-only que ordena cronológicamente el agregado."""

    __tablename__ = "resolution_audit_events"
    __table_args__ = (
        UniqueConstraint(
            "resolution_id",
            "sequence",
            name="uq_resolution_audit_events_sequence",
        ),
        ForeignKeyConstraint(
            ["plan_id", "resolution_id"],
            ["resolution_plans.id", "resolution_plans.resolution_id"],
            name="fk_resolution_audit_events_plan_same_resolution",
            ondelete="RESTRICT",
        ),
        ForeignKeyConstraint(
            ["execution_id", "resolution_id"],
            ["resolution_executions.id", "resolution_executions.resolution_id"],
            name="fk_resolution_audit_events_execution_same_resolution",
            ondelete="RESTRICT",
        ),
        CheckConstraint(
            "sequence >= 1",
            name="ck_resolution_audit_events_sequence_positive",
        ),
        CheckConstraint(
            "length(payload_hash) = 64",
            name="ck_resolution_audit_events_hash_length",
        ),
        Index(
            "ix_resolution_audit_events_resolution_time",
            "resolution_id",
            "occurred_at",
        ),
        Index("ix_resolution_audit_events_type", "event_type"),
    )

    resolution_id: Mapped[int] = mapped_column(
        BIGINT_ID,
        ForeignKey("resolutions.id", ondelete="RESTRICT"),
        nullable=False,
    )
    sequence: Mapped[int] = mapped_column(BIGINT_ID, nullable=False)
    event_type: Mapped[str] = mapped_column(String(160), nullable=False)
    actor_type: Mapped[str] = mapped_column(String(40), nullable=False)
    actor_id: Mapped[str | None] = mapped_column(String(160))
    actor_function: Mapped[str | None] = mapped_column(String(100))
    occurred_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    previous_state: Mapped[str | None] = mapped_column(String(40))
    new_state: Mapped[str | None] = mapped_column(String(40))
    plan_id: Mapped[int | None] = mapped_column(BIGINT_ID)
    plan_version: Mapped[int | None] = mapped_column(Integer)
    execution_id: Mapped[int | None] = mapped_column(BIGINT_ID)
    correlation_id: Mapped[str | None] = mapped_column(
        String(120), index=True
    )
    source: Mapped[str] = mapped_column(String(40), nullable=False)
    payload: Mapped[dict[str, Any]] = mapped_column(
        JSON_DOCUMENT, server_default=text("'{}'"), nullable=False
    )
    payload_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    actor_ip: Mapped[str | None] = mapped_column(String(64))
    actor_device: Mapped[str | None] = mapped_column(String(240))
    metadata_json: Mapped[dict[str, Any]] = mapped_column(
        "metadata",
        JSON_DOCUMENT,
        server_default=text("'{}'"),
        nullable=False,
    )


class ResolutionSecurityDecision(ResolutionRecordMixin, Base):
    """Concesión o denegación append-only con entradas reproducibles."""

    __tablename__ = "resolution_security_decisions"
    __table_args__ = (
        ForeignKeyConstraint(
            ["authorization_request_id", "resolution_id"],
            [
                "resolution_authorization_requests.id",
                "resolution_authorization_requests.resolution_id",
            ],
            name="fk_resolution_security_decisions_authorization",
            ondelete="RESTRICT",
        ),
        ForeignKeyConstraint(
            ["plan_id", "resolution_id", "plan_hash"],
            [
                "resolution_plans.id",
                "resolution_plans.resolution_id",
                "resolution_plans.plan_hash",
            ],
            name="fk_resolution_security_decisions_exact_plan",
            ondelete="RESTRICT",
        ),
        ForeignKeyConstraint(
            ["simulation_id", "plan_id", "resolution_id"],
            [
                "resolution_simulations.id",
                "resolution_simulations.plan_id",
                "resolution_simulations.resolution_id",
            ],
            name="fk_resolution_security_decisions_exact_simulation",
            ondelete="RESTRICT",
        ),
        ForeignKeyConstraint(
            ["simulation_id", "resolution_id", "simulation_hash"],
            [
                "resolution_simulations.id",
                "resolution_simulations.resolution_id",
                "resolution_simulations.simulation_hash",
            ],
            name="fk_resolution_security_decisions_simulation_hash",
            ondelete="RESTRICT",
        ),
        CheckConstraint(
            "outcome IN ('allowed','denied')",
            name="ck_resolution_security_decisions_outcome",
        ),
        CheckConstraint(
            "actor_type IN ('human','service','worker','integration',"
            "'mobile_app','system')",
            name="ck_resolution_security_decisions_actor_type",
        ),
        CheckConstraint(
            "length(evidence_hash) = 64",
            name="ck_resolution_security_decisions_evidence_hash",
        ),
        CheckConstraint(
            "(plan_id IS NULL AND plan_version IS NULL AND plan_hash IS NULL) "
            "OR (plan_id IS NOT NULL AND plan_version IS NOT NULL "
            "AND plan_hash IS NOT NULL)",
            name="ck_resolution_security_decisions_plan_complete",
        ),
        CheckConstraint(
            "(simulation_id IS NULL AND simulation_hash IS NULL) "
            "OR (simulation_id IS NOT NULL AND simulation_hash IS NOT NULL "
            "AND plan_id IS NOT NULL)",
            name="ck_resolution_security_decisions_simulation_complete",
        ),
        Index(
            "ix_resolution_security_decisions_resolution_time",
            "resolution_id",
            "evaluated_at",
        ),
        Index(
            "ix_resolution_security_decisions_actor_time",
            "actor_id",
            "evaluated_at",
        ),
        Index(
            "ix_resolution_security_decisions_outcome",
            "outcome",
        ),
    )

    resolution_id: Mapped[int | None] = mapped_column(
        BIGINT_ID,
        ForeignKey("resolutions.id", ondelete="RESTRICT"),
    )
    authorization_request_id: Mapped[int | None] = mapped_column(BIGINT_ID)
    plan_id: Mapped[int | None] = mapped_column(BIGINT_ID)
    plan_version: Mapped[int | None] = mapped_column(Integer)
    plan_hash: Mapped[str | None] = mapped_column(String(64))
    simulation_id: Mapped[int | None] = mapped_column(BIGINT_ID)
    simulation_hash: Mapped[str | None] = mapped_column(String(64))
    actor_id: Mapped[str] = mapped_column(String(160), nullable=False)
    actor_type: Mapped[str] = mapped_column(String(40), nullable=False)
    organization_id: Mapped[str] = mapped_column(String(160), nullable=False)
    action: Mapped[str] = mapped_column(String(200), nullable=False)
    resource_type: Mapped[str] = mapped_column(String(100), nullable=False)
    resource_id: Mapped[str] = mapped_column(String(200), nullable=False)
    outcome: Mapped[str] = mapped_column(String(20), nullable=False)
    policy_results: Mapped[list[Any]] = mapped_column(
        JSON_DOCUMENT, nullable=False
    )
    required_permissions: Mapped[list[Any]] = mapped_column(
        JSON_DOCUMENT, nullable=False
    )
    reason_codes: Mapped[list[Any]] = mapped_column(
        JSON_DOCUMENT, nullable=False
    )
    actor_snapshot: Mapped[dict[str, Any]] = mapped_column(
        JSON_DOCUMENT, nullable=False
    )
    authentication_snapshot: Mapped[dict[str, Any]] = mapped_column(
        JSON_DOCUMENT, nullable=False
    )
    context_snapshot: Mapped[dict[str, Any]] = mapped_column(
        JSON_DOCUMENT, nullable=False
    )
    evaluated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    correlation_id: Mapped[str] = mapped_column(
        String(120), nullable=False, index=True
    )
    evidence_hash: Mapped[str] = mapped_column(String(64), nullable=False)


class ResolutionIdempotencyRecord(
    ResolutionRecordMixin,
    MutableTimestampMixin,
    Base,
):
    """Resultado durable de una clave de idempotencia."""

    __tablename__ = "resolution_idempotency_records"
    __table_args__ = (
        UniqueConstraint(
            "scope",
            "idempotency_key",
            name="uq_resolution_idempotency_scope_key",
        ),
        ForeignKeyConstraint(
            ["execution_id", "resolution_id"],
            ["resolution_executions.id", "resolution_executions.resolution_id"],
            name="fk_resolution_idempotency_execution_same_resolution",
            ondelete="RESTRICT",
        ),
        ForeignKeyConstraint(
            ["step_execution_id", "execution_id"],
            [
                "resolution_step_executions.id",
                "resolution_step_executions.execution_id",
            ],
            name="fk_resolution_idempotency_step_same_execution",
            ondelete="RESTRICT",
        ),
        CheckConstraint(
            "scope IN ('resolution_request','resolution_execution',"
            "'step_execution','domain_operation','offline_sync')",
            name="ck_resolution_idempotency_records_scope",
        ),
        CheckConstraint(
            "status IN ('in_progress','completed','failed','expired')",
            name="ck_resolution_idempotency_records_status",
        ),
        CheckConstraint(
            "length(request_hash) = 64",
            name="ck_resolution_idempotency_records_hash_length",
        ),
        CheckConstraint(
            "step_execution_id IS NULL OR execution_id IS NOT NULL",
            name="ck_resolution_idempotency_step_requires_execution",
        ),
        CheckConstraint(
            "execution_id IS NULL OR resolution_id IS NOT NULL",
            name="ck_resolution_idempotency_execution_requires_resolution",
        ),
        Index(
            "ix_resolution_idempotency_records_expiration",
            "status",
            "expires_at",
        ),
    )

    scope: Mapped[str] = mapped_column(String(40), nullable=False)
    idempotency_key: Mapped[str] = mapped_column(String(240), nullable=False)
    resolution_id: Mapped[int | None] = mapped_column(
        BIGINT_ID,
        ForeignKey("resolutions.id", ondelete="RESTRICT"),
    )
    execution_id: Mapped[int | None] = mapped_column(BIGINT_ID)
    step_execution_id: Mapped[int | None] = mapped_column(BIGINT_ID)
    operation_key: Mapped[str] = mapped_column(String(200), nullable=False)
    status: Mapped[str] = mapped_column(
        String(24), server_default="in_progress", nullable=False
    )
    request_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    response_payload: Mapped[dict[str, Any] | None] = mapped_column(JSON_DOCUMENT)
    completed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True)
    )
    expires_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True)
    )
    metadata_json: Mapped[dict[str, Any]] = mapped_column(
        "metadata",
        JSON_DOCUMENT,
        server_default=text("'{}'"),
        nullable=False,
    )


class ResolutionLock(ResolutionRecordMixin, Base):
    """Registro estructural de bloqueo; su operación pertenece a Fase 5."""

    __tablename__ = "resolution_locks"
    __table_args__ = (
        CheckConstraint(
            "lock_type IN ('planning','authorization','execution',"
            "'compensation','subject_entity')",
            name="ck_resolution_locks_type",
        ),
        CheckConstraint(
            "expires_at > acquired_at",
            name="ck_resolution_locks_expiration",
        ),
        UniqueConstraint("token", name="uq_resolution_locks_token"),
        Index(
            "uq_resolution_locks_active_key",
            "lock_type",
            "lock_key",
            unique=True,
            postgresql_where=text("released_at IS NULL"),
            sqlite_where=text("released_at IS NULL"),
        ),
        Index("ix_resolution_locks_expiration", "expires_at"),
    )

    resolution_id: Mapped[int] = mapped_column(
        BIGINT_ID,
        ForeignKey("resolutions.id", ondelete="RESTRICT"),
        nullable=False,
    )
    lock_type: Mapped[str] = mapped_column(String(32), nullable=False)
    lock_key: Mapped[str] = mapped_column(String(240), nullable=False)
    owner: Mapped[str] = mapped_column(String(200), nullable=False)
    token: Mapped[str] = mapped_column(String(160), nullable=False)
    acquired_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    expires_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    released_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True)
    )
    metadata_json: Mapped[dict[str, Any]] = mapped_column(
        "metadata",
        JSON_DOCUMENT,
        server_default=text("'{}'"),
        nullable=False,
    )


class ResolutionOutboxEvent(
    ResolutionRecordMixin,
    MutableTimestampMixin,
    Base,
):
    """Outbox estructural; no publica eventos ni implementa workers."""

    __tablename__ = "resolution_outbox_events"
    __table_args__ = (
        UniqueConstraint("event_key", name="uq_resolution_outbox_events_key"),
        CheckConstraint(
            "status IN ('pending','published','failed')",
            name="ck_resolution_outbox_events_status",
        ),
        CheckConstraint(
            "attempts >= 0",
            name="ck_resolution_outbox_events_attempts",
        ),
        CheckConstraint(
            "length(payload_hash) = 64",
            name="ck_resolution_outbox_events_hash_length",
        ),
        Index(
            "ix_resolution_outbox_events_dispatch",
            "status",
            "available_at",
            "id",
        ),
    )

    resolution_id: Mapped[int] = mapped_column(
        BIGINT_ID,
        ForeignKey("resolutions.id", ondelete="RESTRICT"),
        nullable=False,
    )
    event_key: Mapped[str] = mapped_column(String(200), nullable=False)
    event_type: Mapped[str] = mapped_column(String(160), nullable=False)
    aggregate_type: Mapped[str] = mapped_column(String(100), nullable=False)
    aggregate_id: Mapped[str] = mapped_column(String(160), nullable=False)
    payload: Mapped[dict[str, Any]] = mapped_column(JSON_DOCUMENT, nullable=False)
    payload_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    status: Mapped[str] = mapped_column(
        String(24), server_default="pending", nullable=False
    )
    occurred_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    available_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    published_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True)
    )
    failed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True)
    )
    attempts: Mapped[int] = mapped_column(
        Integer, server_default="0", nullable=False
    )
    last_error: Mapped[str | None] = mapped_column(Text)
    correlation_id: Mapped[str | None] = mapped_column(
        String(120), index=True
    )


class ResolutionEvidenceReference(
    ResolutionRecordMixin,
    CreatedAtMixin,
    Base,
):
    """Referencia append-only a evidencia almacenada fuera de JSON."""

    __tablename__ = "resolution_evidence_references"
    __table_args__ = (
        CheckConstraint(
            "checksum IS NULL OR length(checksum) = 64",
            name="ck_resolution_evidence_references_checksum",
        ),
        Index(
            "ix_resolution_evidence_references_resolution_type",
            "resolution_id",
            "evidence_type",
        ),
    )

    resolution_id: Mapped[int] = mapped_column(
        BIGINT_ID,
        ForeignKey("resolutions.id", ondelete="RESTRICT"),
        nullable=False,
    )
    evidence_type: Mapped[str] = mapped_column(String(100), nullable=False)
    controlled_document_id: Mapped[int | None] = mapped_column(
        Integer,
        ForeignKey("controlled_documents.id", ondelete="RESTRICT"),
    )
    storage_reference: Mapped[str | None] = mapped_column(String(500))
    checksum: Mapped[str | None] = mapped_column(String(64))
    uploaded_by_actor_id: Mapped[str | None] = mapped_column(String(160))
    uploaded_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    metadata_json: Mapped[dict[str, Any]] = mapped_column(
        "metadata",
        JSON_DOCUMENT,
        server_default=text("'{}'"),
        nullable=False,
    )
