"""Planes e intentos de compensación vinculados a una ejecución original."""

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


class ResolutionCompensationPlan(
    ResolutionRecordMixin,
    CreatedAtMixin,
    Base,
):
    """Plan compensatorio inmutable, autorizado y hashado."""

    __tablename__ = "resolution_compensation_plans"
    __table_args__ = (
        UniqueConstraint(
            "id",
            "resolution_id",
            name="uq_resolution_compensation_plans_id_resolution",
        ),
        UniqueConstraint(
            "plan_key",
            name="uq_resolution_compensation_plans_key",
        ),
        ForeignKeyConstraint(
            ["source_execution_id", "resolution_id"],
            [
                "resolution_executions.id",
                "resolution_executions.resolution_id",
            ],
            name="fk_resolution_compensation_plans_source",
            ondelete="RESTRICT",
        ),
        CheckConstraint(
            "strategy IN ('total','partial')",
            name="ck_resolution_compensation_plans_strategy",
        ),
        CheckConstraint(
            "length(plan_hash) = 64",
            name="ck_resolution_compensation_plans_hash",
        ),
        Index(
            "ix_resolution_compensation_plans_source",
            "source_execution_id",
            "id",
        ),
    )

    resolution_id: Mapped[int] = mapped_column(
        BIGINT_ID,
        ForeignKey("resolutions.id", ondelete="RESTRICT"),
        nullable=False,
    )
    source_execution_id: Mapped[int] = mapped_column(BIGINT_ID, nullable=False)
    security_decision_id: Mapped[int] = mapped_column(
        BIGINT_ID,
        ForeignKey("resolution_security_decisions.id", ondelete="RESTRICT"),
        nullable=False,
    )
    strategy: Mapped[str] = mapped_column(String(32), nullable=False)
    reason: Mapped[str] = mapped_column(Text, nullable=False)
    plan_key: Mapped[str] = mapped_column(String(240), nullable=False)
    plan_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    created_by_actor_id: Mapped[str] = mapped_column(
        String(160), nullable=False
    )
    correlation_id: Mapped[str] = mapped_column(
        String(120), nullable=False
    )
    metadata_json: Mapped[dict[str, Any]] = mapped_column(
        "metadata",
        JSON_DOCUMENT,
        server_default=text("'{}'"),
        nullable=False,
    )


class ResolutionCompensationPlanStep(
    ResolutionRecordMixin,
    CreatedAtMixin,
    Base,
):
    """Operación compensatoria declarativa vinculada al paso confirmado."""

    __tablename__ = "resolution_compensation_plan_steps"
    __table_args__ = (
        UniqueConstraint(
            "id",
            "plan_id",
            name="uq_resolution_compensation_plan_steps_id_plan",
        ),
        UniqueConstraint(
            "plan_id",
            "sequence",
            name="uq_resolution_compensation_plan_steps_sequence",
        ),
        UniqueConstraint(
            "source_step_execution_id",
            name="uq_resolution_compensation_source_step_once",
        ),
        ForeignKeyConstraint(
            ["source_step_execution_id", "source_execution_id"],
            [
                "resolution_step_executions.id",
                "resolution_step_executions.execution_id",
            ],
            name="fk_resolution_compensation_steps_source",
            ondelete="RESTRICT",
        ),
        CheckConstraint(
            "sequence >= 1",
            name="ck_resolution_compensation_plan_steps_sequence",
        ),
        CheckConstraint(
            "length(step_hash) = 64",
            name="ck_resolution_compensation_plan_steps_hash",
        ),
    )

    plan_id: Mapped[int] = mapped_column(
        BIGINT_ID,
        ForeignKey("resolution_compensation_plans.id", ondelete="RESTRICT"),
        nullable=False,
    )
    source_execution_id: Mapped[int] = mapped_column(BIGINT_ID, nullable=False)
    source_plan_step_id: Mapped[int] = mapped_column(
        BIGINT_ID,
        ForeignKey("resolution_plan_steps.id", ondelete="RESTRICT"),
        nullable=False,
    )
    source_step_execution_id: Mapped[int] = mapped_column(
        BIGINT_ID, nullable=False
    )
    source_step_key: Mapped[str] = mapped_column(String(160), nullable=False)
    sequence: Mapped[int] = mapped_column(Integer, nullable=False)
    operation_key: Mapped[str] = mapped_column(String(200), nullable=False)
    owner_module: Mapped[str] = mapped_column(String(100), nullable=False)
    input_payload: Mapped[dict[str, Any]] = mapped_column(
        JSON_DOCUMENT, nullable=False
    )
    dependency_source_step_ids: Mapped[list[Any]] = mapped_column(
        JSON_DOCUMENT, server_default=text("'[]'"), nullable=False
    )
    step_hash: Mapped[str] = mapped_column(String(64), nullable=False)


class ResolutionCompensationExecution(
    ResolutionRecordMixin,
    MutableTimestampMixin,
    Base,
):
    """Intento único y durable de ejecutar un plan compensatorio."""

    __tablename__ = "resolution_compensation_executions"
    __table_args__ = (
        UniqueConstraint(
            "id",
            "resolution_id",
            name="uq_resolution_compensation_executions_id_resolution",
        ),
        UniqueConstraint(
            "id",
            "plan_id",
            name="uq_resolution_compensation_executions_id_plan",
        ),
        UniqueConstraint(
            "plan_id",
            name="uq_resolution_compensation_executions_plan",
        ),
        UniqueConstraint(
            "execution_key",
            name="uq_resolution_compensation_executions_key",
        ),
        ForeignKeyConstraint(
            ["plan_id", "resolution_id"],
            [
                "resolution_compensation_plans.id",
                "resolution_compensation_plans.resolution_id",
            ],
            name="fk_resolution_compensation_executions_plan",
            ondelete="RESTRICT",
        ),
        CheckConstraint(
            "status IN ('running','compensated','partially_compensated',"
            "'failed','blocked')",
            name="ck_resolution_compensation_executions_status",
        ),
        Index(
            "ix_resolution_compensation_executions_status",
            "status",
            "id",
        ),
    )

    resolution_id: Mapped[int] = mapped_column(
        BIGINT_ID,
        ForeignKey("resolutions.id", ondelete="RESTRICT"),
        nullable=False,
    )
    plan_id: Mapped[int] = mapped_column(BIGINT_ID, nullable=False)
    source_execution_id: Mapped[int] = mapped_column(
        BIGINT_ID,
        ForeignKey("resolution_executions.id", ondelete="RESTRICT"),
        nullable=False,
    )
    status: Mapped[str] = mapped_column(String(32), nullable=False)
    execution_key: Mapped[str] = mapped_column(String(240), nullable=False)
    request_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    lock_token: Mapped[str] = mapped_column(String(160), nullable=False)
    executed_by_actor_id: Mapped[str] = mapped_column(
        String(160), nullable=False
    )
    executed_by_actor_type: Mapped[str] = mapped_column(
        String(40), nullable=False
    )
    actor_source: Mapped[str] = mapped_column(String(40), nullable=False)
    correlation_id: Mapped[str] = mapped_column(
        String(120), nullable=False
    )
    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    completed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True)
    )
    outcome_payload: Mapped[dict[str, Any] | None] = mapped_column(
        JSON_DOCUMENT
    )


class ResolutionCompensationStepExecution(
    ResolutionRecordMixin,
    MutableTimestampMixin,
    Base,
):
    """Checkpoint compensatorio separado del hecho original."""

    __tablename__ = "resolution_compensation_step_executions"
    __table_args__ = (
        UniqueConstraint(
            "execution_id",
            "plan_step_id",
            name="uq_resolution_compensation_step_executions_step",
        ),
        UniqueConstraint(
            "step_execution_key",
            name="uq_resolution_compensation_step_executions_key",
        ),
        ForeignKeyConstraint(
            ["execution_id", "plan_id"],
            [
                "resolution_compensation_executions.id",
                "resolution_compensation_executions.plan_id",
            ],
            name="fk_resolution_compensation_step_execution",
            ondelete="RESTRICT",
        ),
        ForeignKeyConstraint(
            ["plan_step_id", "plan_id"],
            [
                "resolution_compensation_plan_steps.id",
                "resolution_compensation_plan_steps.plan_id",
            ],
            name="fk_resolution_compensation_step_plan",
            ondelete="RESTRICT",
        ),
        CheckConstraint(
            "status IN ('pending','running','compensated','failed','blocked')",
            name="ck_resolution_compensation_step_executions_status",
        ),
        Index(
            "ix_resolution_compensation_steps_execution_status",
            "execution_id",
            "status",
        ),
    )

    execution_id: Mapped[int] = mapped_column(BIGINT_ID, nullable=False)
    plan_id: Mapped[int] = mapped_column(BIGINT_ID, nullable=False)
    plan_step_id: Mapped[int] = mapped_column(BIGINT_ID, nullable=False)
    source_step_execution_id: Mapped[int] = mapped_column(
        BIGINT_ID,
        ForeignKey("resolution_step_executions.id", ondelete="RESTRICT"),
        nullable=False,
    )
    status: Mapped[str] = mapped_column(
        String(24), server_default="pending", nullable=False
    )
    step_execution_key: Mapped[str] = mapped_column(
        String(240), nullable=False
    )
    request_hash: Mapped[str | None] = mapped_column(String(64))
    request_payload: Mapped[dict[str, Any]] = mapped_column(
        JSON_DOCUMENT, server_default=text("'{}'"), nullable=False
    )
    result_payload: Mapped[dict[str, Any] | None] = mapped_column(JSON_DOCUMENT)
    domain_transaction_reference: Mapped[str | None] = mapped_column(
        String(240)
    )
    error_code: Mapped[str | None] = mapped_column(String(160))
    error_message: Mapped[str | None] = mapped_column(Text)
    started_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True)
    )
    completed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True)
    )
