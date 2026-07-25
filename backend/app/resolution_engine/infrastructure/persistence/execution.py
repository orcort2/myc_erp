"""Intentos, pasos, entidades relacionadas y resultados persistentes."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import (
    Boolean,
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


class ResolutionExecution(
    ResolutionRecordMixin,
    MutableTimestampMixin,
    Base,
):
    """Intento de ejecución persistido; no contiene lógica ejecutora."""

    __tablename__ = "resolution_executions"
    __table_args__ = (
        UniqueConstraint(
            "id",
            "resolution_id",
            name="uq_resolution_executions_id_resolution",
        ),
        UniqueConstraint(
            "id",
            "plan_id",
            name="uq_resolution_executions_id_plan",
        ),
        UniqueConstraint(
            "resolution_id",
            "attempt_number",
            name="uq_resolution_executions_attempt",
        ),
        UniqueConstraint(
            "execution_key",
            name="uq_resolution_executions_key",
        ),
        ForeignKeyConstraint(
            ["plan_id", "resolution_id"],
            ["resolution_plans.id", "resolution_plans.resolution_id"],
            name="fk_resolution_executions_plan_same_resolution",
            ondelete="RESTRICT",
        ),
        ForeignKeyConstraint(
            ["revalidation_id", "plan_id", "resolution_id"],
            [
                "resolution_revalidations.id",
                "resolution_revalidations.plan_id",
                "resolution_revalidations.resolution_id",
            ],
            name="fk_resolution_executions_exact_revalidation",
            ondelete="RESTRICT",
        ),
        CheckConstraint(
            "status IN ('pending','running','completed','partially_completed',"
            "'failed','blocked','cancelled','compensating','compensated')",
            name="ck_resolution_executions_status",
        ),
        CheckConstraint(
            "attempt_number >= 1",
            name="ck_resolution_executions_attempt_positive",
        ),
        CheckConstraint(
            "initial_context_hash IS NULL "
            "OR length(initial_context_hash) = 64",
            name="ck_resolution_executions_initial_hash_length",
        ),
        CheckConstraint(
            "final_context_hash IS NULL OR length(final_context_hash) = 64",
            name="ck_resolution_executions_final_hash_length",
        ),
        Index(
            "ix_resolution_executions_status_retry",
            "status",
            "retry_after",
        ),
    )

    resolution_id: Mapped[int] = mapped_column(
        BIGINT_ID,
        ForeignKey("resolutions.id", ondelete="RESTRICT"),
        nullable=False,
    )
    plan_id: Mapped[int] = mapped_column(BIGINT_ID, nullable=False)
    revalidation_id: Mapped[int] = mapped_column(BIGINT_ID, nullable=False)
    attempt_number: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[str] = mapped_column(
        String(32), server_default="pending", nullable=False
    )
    execution_key: Mapped[str] = mapped_column(String(200), nullable=False)
    started_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True)
    )
    completed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True)
    )
    executed_by_actor_id: Mapped[str | None] = mapped_column(String(160))
    worker_id: Mapped[str | None] = mapped_column(String(160))
    lock_token: Mapped[str | None] = mapped_column(String(160))
    initial_context_hash: Mapped[str | None] = mapped_column(String(64))
    final_context_hash: Mapped[str | None] = mapped_column(String(64))
    error_code: Mapped[str | None] = mapped_column(String(160))
    error_message: Mapped[str | None] = mapped_column(Text)
    error_details: Mapped[dict[str, Any]] = mapped_column(
        JSON_DOCUMENT, server_default=text("'{}'"), nullable=False
    )
    retryable: Mapped[bool] = mapped_column(
        Boolean, server_default=text("false"), nullable=False
    )
    retry_after: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True)
    )
    correlation_id: Mapped[str | None] = mapped_column(
        String(120), index=True
    )
    metadata_json: Mapped[dict[str, Any]] = mapped_column(
        "metadata",
        JSON_DOCUMENT,
        server_default=text("'{}'"),
        nullable=False,
    )


class ResolutionStepExecution(
    ResolutionRecordMixin,
    MutableTimestampMixin,
    Base,
):
    """Intento persistido de un paso exacto de un plan."""

    __tablename__ = "resolution_step_executions"
    __table_args__ = (
        UniqueConstraint(
            "id",
            "execution_id",
            name="uq_resolution_step_executions_id_execution",
        ),
        UniqueConstraint(
            "execution_id",
            "plan_step_id",
            "attempt_number",
            name="uq_resolution_step_executions_attempt",
        ),
        UniqueConstraint(
            "step_execution_key",
            name="uq_resolution_step_executions_key",
        ),
        ForeignKeyConstraint(
            ["execution_id", "plan_id"],
            ["resolution_executions.id", "resolution_executions.plan_id"],
            name="fk_resolution_step_executions_execution_plan",
            ondelete="RESTRICT",
        ),
        ForeignKeyConstraint(
            ["plan_step_id", "plan_id"],
            ["resolution_plan_steps.id", "resolution_plan_steps.plan_id"],
            name="fk_resolution_step_executions_step_plan",
            ondelete="RESTRICT",
        ),
        CheckConstraint(
            "status IN ('pending','running','completed','skipped','failed',"
            "'blocked','compensating','compensated','compensation_failed')",
            name="ck_resolution_step_executions_status",
        ),
        CheckConstraint(
            "attempt_number >= 1",
            name="ck_resolution_step_executions_attempt_positive",
        ),
        CheckConstraint(
            "retry_count >= 0",
            name="ck_resolution_step_executions_retry_count",
        ),
        Index(
            "ix_resolution_step_executions_execution_status",
            "execution_id",
            "status",
        ),
    )

    execution_id: Mapped[int] = mapped_column(BIGINT_ID, nullable=False)
    plan_id: Mapped[int] = mapped_column(BIGINT_ID, nullable=False)
    plan_step_id: Mapped[int] = mapped_column(BIGINT_ID, nullable=False)
    status: Mapped[str] = mapped_column(
        String(32), server_default="pending", nullable=False
    )
    attempt_number: Mapped[int] = mapped_column(Integer, nullable=False)
    step_execution_key: Mapped[str] = mapped_column(String(200), nullable=False)
    started_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True)
    )
    completed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True)
    )
    request_payload: Mapped[dict[str, Any]] = mapped_column(
        JSON_DOCUMENT, server_default=text("'{}'"), nullable=False
    )
    response_payload: Mapped[dict[str, Any]] = mapped_column(
        JSON_DOCUMENT, server_default=text("'{}'"), nullable=False
    )
    error_code: Mapped[str | None] = mapped_column(String(160))
    error_message: Mapped[str | None] = mapped_column(Text)
    error_details: Mapped[dict[str, Any]] = mapped_column(
        JSON_DOCUMENT, server_default=text("'{}'"), nullable=False
    )
    retryable: Mapped[bool] = mapped_column(
        Boolean, server_default=text("false"), nullable=False
    )
    retry_count: Mapped[int] = mapped_column(
        Integer, server_default="0", nullable=False
    )
    domain_transaction_reference: Mapped[str | None] = mapped_column(
        String(240)
    )
    compensation_status: Mapped[str | None] = mapped_column(String(32))
    compensation_execution_id: Mapped[int | None] = mapped_column(
        BIGINT_ID,
        ForeignKey("resolution_step_executions.id", ondelete="RESTRICT"),
    )
    metadata_json: Mapped[dict[str, Any]] = mapped_column(
        "metadata",
        JSON_DOCUMENT,
        server_default=text("'{}'"),
        nullable=False,
    )


class ResolutionEntityReference(ResolutionRecordMixin, CreatedAtMixin, Base):
    """Vínculo append-only con entidades propiedad de otros módulos."""

    __tablename__ = "resolution_entity_references"
    __table_args__ = (
        ForeignKeyConstraint(
            ["execution_id", "resolution_id"],
            ["resolution_executions.id", "resolution_executions.resolution_id"],
            name="fk_resolution_entity_refs_execution_same_resolution",
            ondelete="RESTRICT",
        ),
        ForeignKeyConstraint(
            ["step_execution_id", "execution_id"],
            [
                "resolution_step_executions.id",
                "resolution_step_executions.execution_id",
            ],
            name="fk_resolution_entity_refs_step_same_execution",
            ondelete="RESTRICT",
        ),
        CheckConstraint(
            "relationship_type IN ('subject','input','created','modified',"
            "'preserved','cancelled','superseded','linked','referenced')",
            name="ck_resolution_entity_references_relationship",
        ),
        CheckConstraint(
            "step_execution_id IS NULL OR execution_id IS NOT NULL",
            name="ck_resolution_entity_references_step_requires_execution",
        ),
        Index(
            "ix_resolution_entity_references_entity",
            "entity_type",
            "entity_id",
        ),
        Index(
            "ix_resolution_entity_references_resolution_relationship",
            "resolution_id",
            "relationship_type",
        ),
    )

    resolution_id: Mapped[int] = mapped_column(
        BIGINT_ID,
        ForeignKey("resolutions.id", ondelete="RESTRICT"),
        nullable=False,
    )
    execution_id: Mapped[int | None] = mapped_column(BIGINT_ID)
    step_execution_id: Mapped[int | None] = mapped_column(BIGINT_ID)
    relationship_type: Mapped[str] = mapped_column(String(32), nullable=False)
    entity_type: Mapped[str] = mapped_column(String(100), nullable=False)
    entity_id: Mapped[str] = mapped_column(String(160), nullable=False)
    public_identifier: Mapped[str | None] = mapped_column(String(200))
    module: Mapped[str] = mapped_column(String(100), nullable=False)
    before_snapshot: Mapped[dict[str, Any] | None] = mapped_column(JSON_DOCUMENT)
    after_snapshot: Mapped[dict[str, Any] | None] = mapped_column(JSON_DOCUMENT)
    metadata_json: Mapped[dict[str, Any]] = mapped_column(
        "metadata",
        JSON_DOCUMENT,
        server_default=text("'{}'"),
        nullable=False,
    )


class ResolutionResult(ResolutionRecordMixin, Base):
    """Conclusión consolidada append-only de una resolución."""

    __tablename__ = "resolution_results"
    __table_args__ = (
        ForeignKeyConstraint(
            ["execution_id", "resolution_id"],
            ["resolution_executions.id", "resolution_executions.resolution_id"],
            name="fk_resolution_results_execution_same_resolution",
            ondelete="RESTRICT",
        ),
        ForeignKeyConstraint(
            ["final_context_snapshot_id", "resolution_id"],
            [
                "resolution_context_snapshots.id",
                "resolution_context_snapshots.resolution_id",
            ],
            name="fk_resolution_results_context_same_resolution",
            ondelete="RESTRICT",
        ),
        CheckConstraint(
            "status IN ('success','partial_success','failed','cancelled',"
            "'superseded','no_action_required')",
            name="ck_resolution_results_status",
        ),
        CheckConstraint(
            "length(result_hash) = 64",
            name="ck_resolution_results_hash_length",
        ),
    )

    resolution_id: Mapped[int] = mapped_column(
        BIGINT_ID,
        ForeignKey("resolutions.id", ondelete="RESTRICT"),
        unique=True,
        nullable=False,
    )
    execution_id: Mapped[int | None] = mapped_column(BIGINT_ID)
    status: Mapped[str] = mapped_column(String(32), nullable=False)
    summary: Mapped[str] = mapped_column(Text, nullable=False)
    created_entities: Mapped[list[Any]] = mapped_column(
        JSON_DOCUMENT, server_default=text("'[]'"), nullable=False
    )
    modified_entities: Mapped[list[Any]] = mapped_column(
        JSON_DOCUMENT, server_default=text("'[]'"), nullable=False
    )
    preserved_entities: Mapped[list[Any]] = mapped_column(
        JSON_DOCUMENT, server_default=text("'[]'"), nullable=False
    )
    failed_steps: Mapped[list[Any]] = mapped_column(
        JSON_DOCUMENT, server_default=text("'[]'"), nullable=False
    )
    warnings: Mapped[list[Any]] = mapped_column(
        JSON_DOCUMENT, server_default=text("'[]'"), nullable=False
    )
    follow_up_actions: Mapped[list[Any]] = mapped_column(
        JSON_DOCUMENT, server_default=text("'[]'"), nullable=False
    )
    final_context_snapshot_id: Mapped[int | None] = mapped_column(BIGINT_ID)
    completed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    completed_by_actor_id: Mapped[str | None] = mapped_column(String(160))
    result_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    metadata_json: Mapped[dict[str, Any]] = mapped_column(
        "metadata",
        JSON_DOCUMENT,
        server_default=text("'{}'"),
        nullable=False,
    )
