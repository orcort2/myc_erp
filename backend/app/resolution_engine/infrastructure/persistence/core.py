"""Raíz, problema, contexto, análisis y estrategia persistentes."""

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


class Resolution(ResolutionRecordMixin, MutableTimestampMixin, Base):
    """Raíz persistente del agregado del Motor."""

    __tablename__ = "resolutions"
    __table_args__ = (
        CheckConstraint(
            "status IN ('draft','context_ready','analyzed','plan_ready',"
            "'simulated','pending_authorization','authorized','revalidating',"
            "'ready_for_execution','executing','completed',"
            "'partially_completed','failed','blocked','rejected','cancelled',"
            "'superseded','no_action_required','compensating','compensated',"
            "'partially_compensated','compensation_failed')",
            name="ck_resolutions_status",
        ),
        CheckConstraint(
            "priority IN ('low','normal','high','critical')",
            name="ck_resolutions_priority",
        ),
        CheckConstraint(
            "source IN ('user','module','system','sync','mobile_app',"
            "'scheduled_process','administrator')",
            name="ck_resolutions_source",
        ),
        CheckConstraint("version >= 1", name="ck_resolutions_version_positive"),
        CheckConstraint(
            "parent_resolution_id IS NULL OR parent_resolution_id <> id",
            name="ck_resolutions_parent_not_self",
        ),
        CheckConstraint(
            "superseded_by_resolution_id IS NULL "
            "OR superseded_by_resolution_id <> id",
            name="ck_resolutions_superseded_not_self",
        ),
        ForeignKeyConstraint(
            ["current_context_snapshot_id", "id"],
            [
                "resolution_context_snapshots.id",
                "resolution_context_snapshots.resolution_id",
            ],
            name="fk_resolutions_current_context_same_resolution",
            use_alter=True,
            ondelete="RESTRICT",
        ),
        ForeignKeyConstraint(
            ["current_plan_id", "id"],
            ["resolution_plans.id", "resolution_plans.resolution_id"],
            name="fk_resolutions_current_plan_same_resolution",
            use_alter=True,
            ondelete="RESTRICT",
        ),
        ForeignKeyConstraint(
            ["current_strategy_selection_id", "id"],
            [
                "resolution_strategy_selections.id",
                "resolution_strategy_selections.resolution_id",
            ],
            name="fk_resolutions_current_strategy_same_resolution",
            use_alter=True,
            ondelete="RESTRICT",
        ),
        Index(
            "ix_resolutions_subject",
            "subject_type",
            "subject_id",
        ),
        Index(
            "ix_resolutions_type_status_created",
            "resolution_type",
            "status",
            "created_at",
        ),
    )

    public_id: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    resolution_type: Mapped[str] = mapped_column(
        String(160), index=True, nullable=False
    )
    definition_version: Mapped[str] = mapped_column(String(32), nullable=False)
    status: Mapped[str] = mapped_column(
        String(40), server_default="draft", index=True, nullable=False
    )
    priority: Mapped[str] = mapped_column(
        String(20), server_default="normal", nullable=False
    )
    source: Mapped[str] = mapped_column(String(32), nullable=False)
    subject_type: Mapped[str] = mapped_column(String(100), nullable=False)
    subject_id: Mapped[str] = mapped_column(String(160), nullable=False)
    parent_resolution_id: Mapped[int | None] = mapped_column(
        BIGINT_ID,
        ForeignKey("resolutions.id", ondelete="RESTRICT"),
        index=True,
    )
    superseded_by_resolution_id: Mapped[int | None] = mapped_column(
        BIGINT_ID,
        ForeignKey("resolutions.id", ondelete="RESTRICT"),
        index=True,
    )
    requested_by_actor_id: Mapped[str | None] = mapped_column(
        String(160), index=True
    )
    assigned_to_actor_id: Mapped[str | None] = mapped_column(
        String(160), index=True
    )
    assigned_function: Mapped[str | None] = mapped_column(String(100))
    organization_id: Mapped[str | None] = mapped_column(String(160), index=True)
    branch_id: Mapped[str | None] = mapped_column(String(160), index=True)
    correlation_id: Mapped[str | None] = mapped_column(
        String(120), index=True
    )
    request_key: Mapped[str | None] = mapped_column(
        String(200), unique=True
    )
    title: Mapped[str] = mapped_column(String(240), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    reason: Mapped[str | None] = mapped_column(Text)
    current_plan_id: Mapped[int | None] = mapped_column(BIGINT_ID)
    current_context_snapshot_id: Mapped[int | None] = mapped_column(BIGINT_ID)
    current_strategy_selection_id: Mapped[int | None] = mapped_column(BIGINT_ID)
    risk_level: Mapped[str | None] = mapped_column(String(30))
    requires_authorization: Mapped[bool] = mapped_column(
        Boolean, server_default=text("false"), nullable=False
    )
    completed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True)
    )
    cancelled_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True)
    )
    rejected_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True)
    )
    version: Mapped[int] = mapped_column(
        Integer, server_default="1", nullable=False
    )
    metadata_json: Mapped[dict[str, Any]] = mapped_column(
        "metadata",
        JSON_DOCUMENT,
        server_default=text("'{}'"),
        nullable=False,
    )


class ResolutionProblem(ResolutionRecordMixin, CreatedAtMixin, Base):
    """Problema original inmutable; describe la situación, no la solución."""

    __tablename__ = "resolution_problems"
    __table_args__ = (
        CheckConstraint(
            "severity IN ('low','normal','high','critical')",
            name="ck_resolution_problems_severity",
        ),
    )

    resolution_id: Mapped[int] = mapped_column(
        BIGINT_ID,
        ForeignKey("resolutions.id", ondelete="RESTRICT"),
        unique=True,
        nullable=False,
    )
    problem_code: Mapped[str] = mapped_column(
        String(160), index=True, nullable=False
    )
    summary: Mapped[str] = mapped_column(String(500), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    detected_by: Mapped[str] = mapped_column(String(100), nullable=False)
    detected_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    reported_by_actor_id: Mapped[str | None] = mapped_column(String(160))
    source_payload: Mapped[dict[str, Any]] = mapped_column(
        JSON_DOCUMENT, server_default=text("'{}'"), nullable=False
    )
    external_reference: Mapped[str | None] = mapped_column(String(240))
    severity: Mapped[str] = mapped_column(
        String(20), server_default="normal", nullable=False
    )
    observed_state: Mapped[dict[str, Any]] = mapped_column(
        JSON_DOCUMENT, server_default=text("'{}'"), nullable=False
    )
    evidence: Mapped[list[Any]] = mapped_column(
        JSON_DOCUMENT, server_default=text("'[]'"), nullable=False
    )


class ResolutionContextSnapshot(ResolutionRecordMixin, Base):
    """Fotografía inmutable y versionada de hechos observados."""

    __tablename__ = "resolution_context_snapshots"
    __table_args__ = (
        UniqueConstraint(
            "id",
            "resolution_id",
            name="uq_resolution_context_snapshots_id_resolution",
        ),
        UniqueConstraint(
            "resolution_id",
            "sequence",
            name="uq_resolution_context_snapshots_sequence",
        ),
        CheckConstraint(
            "snapshot_type IN ('initial','analysis','simulation',"
            "'authorization','revalidation','pre_execution',"
            "'post_execution','final')",
            name="ck_resolution_context_snapshots_type",
        ),
        CheckConstraint(
            "sequence >= 1",
            name="ck_resolution_context_snapshots_sequence_positive",
        ),
        CheckConstraint(
            "length(context_hash) = 64",
            name="ck_resolution_context_snapshots_hash_length",
        ),
        Index(
            "ix_resolution_context_snapshots_resolution_captured",
            "resolution_id",
            "captured_at",
        ),
    )

    resolution_id: Mapped[int] = mapped_column(
        BIGINT_ID,
        ForeignKey("resolutions.id", ondelete="RESTRICT"),
        nullable=False,
    )
    snapshot_type: Mapped[str] = mapped_column(String(32), nullable=False)
    sequence: Mapped[int] = mapped_column(Integer, nullable=False)
    context_version: Mapped[str] = mapped_column(String(32), nullable=False)
    context_hash: Mapped[str] = mapped_column(String(64), index=True, nullable=False)
    schema_version: Mapped[str] = mapped_column(String(32), nullable=False)
    captured_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    captured_by_actor_id: Mapped[str | None] = mapped_column(String(160))
    captured_by_actor: Mapped[dict[str, Any]] = mapped_column(
        JSON_DOCUMENT, server_default=text("'{}'"), nullable=False
    )
    facts: Mapped[dict[str, Any]] = mapped_column(JSON_DOCUMENT, nullable=False)
    entity_versions: Mapped[dict[str, Any]] = mapped_column(
        JSON_DOCUMENT, server_default=text("'{}'"), nullable=False
    )
    missing_facts: Mapped[list[Any]] = mapped_column(
        JSON_DOCUMENT, server_default=text("'[]'"), nullable=False
    )
    warnings: Mapped[list[Any]] = mapped_column(
        JSON_DOCUMENT, server_default=text("'[]'"), nullable=False
    )
    source_references: Mapped[list[Any]] = mapped_column(
        JSON_DOCUMENT, server_default=text("'[]'"), nullable=False
    )


class ResolutionAnalysis(ResolutionRecordMixin, Base):
    """Resultado inmutable de analizar un snapshot exacto."""

    __tablename__ = "resolution_analyses"
    __table_args__ = (
        UniqueConstraint(
            "id",
            "resolution_id",
            name="uq_resolution_analyses_id_resolution",
        ),
        UniqueConstraint(
            "resolution_id",
            "analysis_version",
            name="uq_resolution_analyses_version",
        ),
        ForeignKeyConstraint(
            ["context_snapshot_id", "resolution_id"],
            [
                "resolution_context_snapshots.id",
                "resolution_context_snapshots.resolution_id",
            ],
            name="fk_resolution_analyses_context_same_resolution",
            ondelete="RESTRICT",
        ),
        CheckConstraint(
            "status IN ('resolvable','not_resolvable',"
            "'requires_information','blocked','already_resolved')",
            name="ck_resolution_analyses_status",
        ),
        CheckConstraint(
            "analysis_version >= 1",
            name="ck_resolution_analyses_version_positive",
        ),
        CheckConstraint(
            "length(analysis_hash) = 64",
            name="ck_resolution_analyses_hash_length",
        ),
    )

    resolution_id: Mapped[int] = mapped_column(
        BIGINT_ID,
        ForeignKey("resolutions.id", ondelete="RESTRICT"),
        nullable=False,
    )
    context_snapshot_id: Mapped[int] = mapped_column(BIGINT_ID, nullable=False)
    analysis_version: Mapped[int] = mapped_column(Integer, nullable=False)
    is_resolvable: Mapped[bool] = mapped_column(Boolean, nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False)
    findings: Mapped[list[Any]] = mapped_column(
        JSON_DOCUMENT, server_default=text("'[]'"), nullable=False
    )
    constraints_json: Mapped[list[Any]] = mapped_column(
        "constraints",
        JSON_DOCUMENT,
        server_default=text("'[]'"),
        nullable=False,
    )
    blockers: Mapped[list[Any]] = mapped_column(
        JSON_DOCUMENT, server_default=text("'[]'"), nullable=False
    )
    warnings: Mapped[list[Any]] = mapped_column(
        JSON_DOCUMENT, server_default=text("'[]'"), nullable=False
    )
    missing_information: Mapped[list[Any]] = mapped_column(
        JSON_DOCUMENT, server_default=text("'[]'"), nullable=False
    )
    immutable_entities: Mapped[list[Any]] = mapped_column(
        JSON_DOCUMENT, server_default=text("'[]'"), nullable=False
    )
    available_strategies: Mapped[list[Any]] = mapped_column(
        JSON_DOCUMENT, server_default=text("'[]'"), nullable=False
    )
    analyzed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    analyzed_by: Mapped[str] = mapped_column(String(200), nullable=False)
    analysis_hash: Mapped[str] = mapped_column(String(64), nullable=False)


class ResolutionStrategySelection(
    ResolutionRecordMixin,
    MutableTimestampMixin,
    Base,
):
    """Selección versionada; las selecciones sustituidas se preservan."""

    __tablename__ = "resolution_strategy_selections"
    __table_args__ = (
        UniqueConstraint(
            "id",
            "resolution_id",
            name="uq_resolution_strategy_selections_id_resolution",
        ),
        ForeignKeyConstraint(
            ["analysis_id", "resolution_id"],
            ["resolution_analyses.id", "resolution_analyses.resolution_id"],
            name="fk_resolution_strategies_analysis_same_resolution",
            ondelete="RESTRICT",
        ),
        CheckConstraint(
            "selection_mode IN ('automatic','user_selected',"
            "'policy_selected','system_recommended')",
            name="ck_resolution_strategy_selections_mode",
        ),
        Index(
            "uq_resolution_strategy_selections_active",
            "resolution_id",
            unique=True,
            postgresql_where=text("is_active"),
            sqlite_where=text("is_active = 1"),
        ),
    )

    resolution_id: Mapped[int] = mapped_column(
        BIGINT_ID,
        ForeignKey("resolutions.id", ondelete="RESTRICT"),
        nullable=False,
    )
    analysis_id: Mapped[int] = mapped_column(BIGINT_ID, nullable=False)
    strategy_key: Mapped[str] = mapped_column(String(200), nullable=False)
    strategy_version: Mapped[str] = mapped_column(String(32), nullable=False)
    selection_mode: Mapped[str] = mapped_column(String(32), nullable=False)
    selected_by_actor_id: Mapped[str | None] = mapped_column(String(160))
    selected_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    justification: Mapped[str | None] = mapped_column(Text)
    alternatives: Mapped[list[Any]] = mapped_column(
        JSON_DOCUMENT, server_default=text("'[]'"), nullable=False
    )
    is_active: Mapped[bool] = mapped_column(
        Boolean, server_default=text("true"), nullable=False
    )
    superseded_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True)
    )
