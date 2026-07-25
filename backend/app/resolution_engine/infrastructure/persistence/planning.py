"""Planes, dependencias y simulaciones como evidencia versionada."""

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


class ResolutionPlan(ResolutionRecordMixin, MutableTimestampMixin, Base):
    """Versión exacta y hashable de un plan declarativo."""

    __tablename__ = "resolution_plans"
    __table_args__ = (
        UniqueConstraint(
            "id",
            "resolution_id",
            name="uq_resolution_plans_id_resolution",
        ),
        UniqueConstraint(
            "id",
            "resolution_id",
            "plan_hash",
            name="uq_resolution_plans_id_resolution_hash",
        ),
        UniqueConstraint(
            "resolution_id",
            "version",
            name="uq_resolution_plans_version",
        ),
        ForeignKeyConstraint(
            ["strategy_selection_id", "resolution_id"],
            [
                "resolution_strategy_selections.id",
                "resolution_strategy_selections.resolution_id",
            ],
            name="fk_resolution_plans_strategy_same_resolution",
            ondelete="RESTRICT",
        ),
        ForeignKeyConstraint(
            ["context_snapshot_id", "resolution_id"],
            [
                "resolution_context_snapshots.id",
                "resolution_context_snapshots.resolution_id",
            ],
            name="fk_resolution_plans_context_same_resolution",
            ondelete="RESTRICT",
        ),
        CheckConstraint(
            "status IN ('draft','ready','simulated','pending_authorization',"
            "'authorized','invalidated','executing','executed','failed',"
            "'superseded','cancelled')",
            name="ck_resolution_plans_status",
        ),
        CheckConstraint(
            "version >= 1",
            name="ck_resolution_plans_version_positive",
        ),
        CheckConstraint(
            "length(plan_hash) = 64",
            name="ck_resolution_plans_hash_length",
        ),
        Index(
            "uq_resolution_plans_active",
            "resolution_id",
            unique=True,
            postgresql_where=text("is_active"),
            sqlite_where=text("is_active = 1"),
        ),
        Index("ix_resolution_plans_status", "status"),
    )

    resolution_id: Mapped[int] = mapped_column(
        BIGINT_ID,
        ForeignKey("resolutions.id", ondelete="RESTRICT"),
        nullable=False,
    )
    strategy_selection_id: Mapped[int] = mapped_column(BIGINT_ID, nullable=False)
    context_snapshot_id: Mapped[int] = mapped_column(BIGINT_ID, nullable=False)
    version: Mapped[int] = mapped_column(Integer, nullable=False)
    schema_version: Mapped[str] = mapped_column(String(32), nullable=False)
    status: Mapped[str] = mapped_column(
        String(32), server_default="draft", nullable=False
    )
    summary: Mapped[str] = mapped_column(String(500), nullable=False)
    rationale: Mapped[str | None] = mapped_column(Text)
    expected_impact: Mapped[dict[str, Any]] = mapped_column(
        JSON_DOCUMENT, server_default=text("'{}'"), nullable=False
    )
    preserved_entities: Mapped[list[Any]] = mapped_column(
        JSON_DOCUMENT, server_default=text("'[]'"), nullable=False
    )
    warnings: Mapped[list[Any]] = mapped_column(
        JSON_DOCUMENT, server_default=text("'[]'"), nullable=False
    )
    blockers: Mapped[list[Any]] = mapped_column(
        JSON_DOCUMENT, server_default=text("'[]'"), nullable=False
    )
    authorization_requirements: Mapped[dict[str, Any]] = mapped_column(
        JSON_DOCUMENT, server_default=text("'{}'"), nullable=False
    )
    plan_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    created_by_user_id: Mapped[int | None] = mapped_column(
        Integer,
        ForeignKey("users.id", ondelete="RESTRICT"),
    )
    activated_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True)
    )
    invalidated_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True)
    )
    invalidation_reason: Mapped[str | None] = mapped_column(Text)
    is_active: Mapped[bool] = mapped_column(
        Boolean, server_default=text("true"), nullable=False
    )


class ResolutionPlanStep(ResolutionRecordMixin, CreatedAtMixin, Base):
    """Operación declarativa estable dentro de una versión de plan."""

    __tablename__ = "resolution_plan_steps"
    __table_args__ = (
        UniqueConstraint(
            "id",
            "plan_id",
            name="uq_resolution_plan_steps_id_plan",
        ),
        UniqueConstraint(
            "plan_id",
            "step_key",
            name="uq_resolution_plan_steps_key",
        ),
        UniqueConstraint(
            "plan_id",
            "sequence",
            name="uq_resolution_plan_steps_sequence",
        ),
        CheckConstraint(
            "criticality IN ('low','normal','high','irreversible')",
            name="ck_resolution_plan_steps_criticality",
        ),
        CheckConstraint(
            "sequence >= 1",
            name="ck_resolution_plan_steps_sequence_positive",
        ),
        CheckConstraint(
            "length(step_hash) = 64",
            name="ck_resolution_plan_steps_hash_length",
        ),
        CheckConstraint(
            "is_compensable OR compensation_operation_key IS NULL",
            name="ck_resolution_plan_steps_compensation_operation",
        ),
        Index("ix_resolution_plan_steps_operation", "operation_key"),
    )

    plan_id: Mapped[int] = mapped_column(
        BIGINT_ID,
        ForeignKey("resolution_plans.id", ondelete="RESTRICT"),
        nullable=False,
    )
    step_key: Mapped[str] = mapped_column(String(160), nullable=False)
    sequence: Mapped[int] = mapped_column(Integer, nullable=False)
    operation_key: Mapped[str] = mapped_column(String(200), nullable=False)
    owner_module: Mapped[str] = mapped_column(String(100), nullable=False)
    description: Mapped[str] = mapped_column(String(500), nullable=False)
    input_payload: Mapped[dict[str, Any]] = mapped_column(
        JSON_DOCUMENT, server_default=text("'{}'"), nullable=False
    )
    expected_output: Mapped[dict[str, Any]] = mapped_column(
        JSON_DOCUMENT, server_default=text("'{}'"), nullable=False
    )
    preconditions: Mapped[list[Any]] = mapped_column(
        JSON_DOCUMENT, server_default=text("'[]'"), nullable=False
    )
    criticality: Mapped[str] = mapped_column(
        String(20), server_default="normal", nullable=False
    )
    retry_policy: Mapped[dict[str, Any]] = mapped_column(
        JSON_DOCUMENT, server_default=text("'{}'"), nullable=False
    )
    timeout_policy: Mapped[dict[str, Any]] = mapped_column(
        JSON_DOCUMENT, server_default=text("'{}'"), nullable=False
    )
    is_compensable: Mapped[bool] = mapped_column(
        Boolean, server_default=text("false"), nullable=False
    )
    compensation_operation_key: Mapped[str | None] = mapped_column(String(200))
    compensation_payload: Mapped[dict[str, Any]] = mapped_column(
        JSON_DOCUMENT, server_default=text("'{}'"), nullable=False
    )
    point_of_no_return: Mapped[bool] = mapped_column(
        Boolean, server_default=text("false"), nullable=False
    )
    requires_separate_authorization: Mapped[bool] = mapped_column(
        Boolean, server_default=text("false"), nullable=False
    )
    step_hash: Mapped[str] = mapped_column(String(64), nullable=False)


class ResolutionPlanStepDependency(ResolutionRecordMixin, Base):
    """Arista relacional entre pasos; evita dependencias ocultas en JSON."""

    __tablename__ = "resolution_plan_step_dependencies"
    __table_args__ = (
        UniqueConstraint(
            "plan_id",
            "step_id",
            "depends_on_step_id",
            name="uq_resolution_plan_step_dependencies_edge",
        ),
        ForeignKeyConstraint(
            ["step_id", "plan_id"],
            ["resolution_plan_steps.id", "resolution_plan_steps.plan_id"],
            name="fk_resolution_step_dependencies_step_same_plan",
            ondelete="RESTRICT",
        ),
        ForeignKeyConstraint(
            ["depends_on_step_id", "plan_id"],
            ["resolution_plan_steps.id", "resolution_plan_steps.plan_id"],
            name="fk_resolution_step_dependencies_parent_same_plan",
            ondelete="RESTRICT",
        ),
        CheckConstraint(
            "step_id <> depends_on_step_id",
            name="ck_resolution_plan_step_dependencies_not_self",
        ),
        Index(
            "ix_resolution_plan_step_dependencies_parent",
            "depends_on_step_id",
        ),
    )

    plan_id: Mapped[int] = mapped_column(
        BIGINT_ID,
        ForeignKey("resolution_plans.id", ondelete="RESTRICT"),
        nullable=False,
    )
    step_id: Mapped[int] = mapped_column(BIGINT_ID, nullable=False)
    depends_on_step_id: Mapped[int] = mapped_column(BIGINT_ID, nullable=False)


class ResolutionSimulation(ResolutionRecordMixin, Base):
    """Resultado inmutable de simular plan y contexto exactos."""

    __tablename__ = "resolution_simulations"
    __table_args__ = (
        UniqueConstraint(
            "id",
            "resolution_id",
            name="uq_resolution_simulations_id_resolution",
        ),
        UniqueConstraint(
            "id",
            "plan_id",
            "resolution_id",
            name="uq_resolution_simulations_id_plan_resolution",
        ),
        UniqueConstraint(
            "id",
            "resolution_id",
            "simulation_hash",
            name="uq_resolution_simulations_id_resolution_hash",
        ),
        UniqueConstraint(
            "plan_id",
            "simulation_version",
            name="uq_resolution_simulations_version",
        ),
        ForeignKeyConstraint(
            ["plan_id", "resolution_id"],
            ["resolution_plans.id", "resolution_plans.resolution_id"],
            name="fk_resolution_simulations_plan_same_resolution",
            ondelete="RESTRICT",
        ),
        ForeignKeyConstraint(
            ["context_snapshot_id", "resolution_id"],
            [
                "resolution_context_snapshots.id",
                "resolution_context_snapshots.resolution_id",
            ],
            name="fk_resolution_simulations_context_same_resolution",
            ondelete="RESTRICT",
        ),
        CheckConstraint(
            "status IN ('valid','valid_with_warnings','invalid','blocked',"
            "'expired')",
            name="ck_resolution_simulations_status",
        ),
        CheckConstraint(
            "simulation_version >= 1",
            name="ck_resolution_simulations_version_positive",
        ),
        CheckConstraint(
            "length(simulation_hash) = 64",
            name="ck_resolution_simulations_hash_length",
        ),
        Index("ix_resolution_simulations_plan", "plan_id"),
    )

    resolution_id: Mapped[int] = mapped_column(
        BIGINT_ID,
        ForeignKey("resolutions.id", ondelete="RESTRICT"),
        nullable=False,
    )
    plan_id: Mapped[int] = mapped_column(BIGINT_ID, nullable=False)
    context_snapshot_id: Mapped[int] = mapped_column(BIGINT_ID, nullable=False)
    simulation_version: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False)
    is_valid: Mapped[bool] = mapped_column(Boolean, nullable=False)
    expected_actions: Mapped[list[Any]] = mapped_column(
        JSON_DOCUMENT, server_default=text("'[]'"), nullable=False
    )
    expected_creations: Mapped[list[Any]] = mapped_column(
        JSON_DOCUMENT, server_default=text("'[]'"), nullable=False
    )
    expected_changes: Mapped[list[Any]] = mapped_column(
        JSON_DOCUMENT, server_default=text("'[]'"), nullable=False
    )
    preserved_entities: Mapped[list[Any]] = mapped_column(
        JSON_DOCUMENT, server_default=text("'[]'"), nullable=False
    )
    warnings: Mapped[list[Any]] = mapped_column(
        JSON_DOCUMENT, server_default=text("'[]'"), nullable=False
    )
    blockers: Mapped[list[Any]] = mapped_column(
        JSON_DOCUMENT, server_default=text("'[]'"), nullable=False
    )
    required_authorizations: Mapped[dict[str, Any]] = mapped_column(
        JSON_DOCUMENT, server_default=text("'{}'"), nullable=False
    )
    estimated_scope: Mapped[dict[str, Any]] = mapped_column(
        JSON_DOCUMENT, server_default=text("'{}'"), nullable=False
    )
    simulation_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    simulated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    simulated_by: Mapped[str] = mapped_column(String(200), nullable=False)
    expires_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True)
    )
