"""Solicitudes, decisiones y revalidaciones persistentes."""

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
    MutableTimestampMixin,
    ResolutionRecordMixin,
)


class ResolutionAuthorizationRequest(
    ResolutionRecordMixin,
    MutableTimestampMixin,
    Base,
):
    """Solicitud mutable vinculada a plan y simulación exactos."""

    __tablename__ = "resolution_authorization_requests"
    __table_args__ = (
        UniqueConstraint(
            "id",
            "resolution_id",
            name="uq_resolution_authorization_requests_id_resolution",
        ),
        ForeignKeyConstraint(
            ["plan_id", "resolution_id", "plan_hash"],
            [
                "resolution_plans.id",
                "resolution_plans.resolution_id",
                "resolution_plans.plan_hash",
            ],
            name="fk_resolution_authorizations_exact_plan",
            ondelete="RESTRICT",
        ),
        ForeignKeyConstraint(
            ["simulation_id", "plan_id", "resolution_id"],
            [
                "resolution_simulations.id",
                "resolution_simulations.plan_id",
                "resolution_simulations.resolution_id",
            ],
            name="fk_resolution_authorizations_exact_simulation",
            ondelete="RESTRICT",
        ),
        ForeignKeyConstraint(
            ["simulation_id", "resolution_id", "simulation_hash"],
            [
                "resolution_simulations.id",
                "resolution_simulations.resolution_id",
                "resolution_simulations.simulation_hash",
            ],
            name="fk_resolution_authorizations_simulation_hash",
            ondelete="RESTRICT",
        ),
        CheckConstraint(
            "status IN ('pending','partially_approved','approved','rejected',"
            "'expired','cancelled','invalidated')",
            name="ck_resolution_authorization_requests_status",
        ),
        CheckConstraint(
            "required_approvals >= 1",
            name="ck_resolution_authorization_requests_approvals_positive",
        ),
        CheckConstraint(
            "length(plan_hash) = 64",
            name="ck_resolution_authorization_requests_plan_hash_length",
        ),
        CheckConstraint(
            "length(simulation_hash) = 64",
            name="ck_resolution_authorization_requests_sim_hash_length",
        ),
        Index("ix_resolution_authorization_requests_status", "status"),
    )

    resolution_id: Mapped[int] = mapped_column(
        BIGINT_ID,
        ForeignKey("resolutions.id", ondelete="RESTRICT"),
        nullable=False,
    )
    plan_id: Mapped[int] = mapped_column(BIGINT_ID, nullable=False)
    simulation_id: Mapped[int] = mapped_column(BIGINT_ID, nullable=False)
    policy_key: Mapped[str] = mapped_column(String(200), nullable=False)
    policy_version: Mapped[str] = mapped_column(String(32), nullable=False)
    status: Mapped[str] = mapped_column(
        String(32), server_default="pending", nullable=False
    )
    requested_by_user_id: Mapped[int | None] = mapped_column(
        Integer,
        ForeignKey("users.id", ondelete="RESTRICT"),
    )
    requested_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    expires_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True)
    )
    required_approvals: Mapped[int] = mapped_column(Integer, nullable=False)
    authorization_scope: Mapped[dict[str, Any]] = mapped_column(
        JSON_DOCUMENT, nullable=False
    )
    plan_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    simulation_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    invalidated_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True)
    )


class ResolutionAuthorizationDecision(ResolutionRecordMixin, Base):
    """Decisión individual append-only con snapshot de autoridad."""

    __tablename__ = "resolution_authorization_decisions"
    __table_args__ = (
        CheckConstraint(
            "decision IN ('approved','rejected','abstained','revoked')",
            name="ck_resolution_authorization_decisions_decision",
        ),
        Index(
            "ix_resolution_authorization_decisions_request_approver",
            "authorization_request_id",
            "approver_user_id",
        ),
    )

    authorization_request_id: Mapped[int] = mapped_column(
        BIGINT_ID,
        ForeignKey(
            "resolution_authorization_requests.id",
            ondelete="RESTRICT",
        ),
        nullable=False,
    )
    decision: Mapped[str] = mapped_column(String(24), nullable=False)
    approver_user_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False,
    )
    approver_role: Mapped[str] = mapped_column(String(100), nullable=False)
    approver_area: Mapped[str | None] = mapped_column(String(120))
    decided_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    comment: Mapped[str | None] = mapped_column(Text)
    reason_code: Mapped[str | None] = mapped_column(String(160))
    signature_reference: Mapped[str | None] = mapped_column(String(500))
    permission_snapshot: Mapped[dict[str, Any]] = mapped_column(
        JSON_DOCUMENT, nullable=False
    )
    actor_ip: Mapped[str | None] = mapped_column(String(64))
    actor_device: Mapped[str | None] = mapped_column(String(240))
    metadata_json: Mapped[dict[str, Any]] = mapped_column(
        "metadata",
        JSON_DOCUMENT,
        server_default=text("'{}'"),
        nullable=False,
    )


class ResolutionRevalidation(ResolutionRecordMixin, Base):
    """Comparación append-only de contexto autorizado y contexto actual."""

    __tablename__ = "resolution_revalidations"
    __table_args__ = (
        UniqueConstraint(
            "id",
            "resolution_id",
            name="uq_resolution_revalidations_id_resolution",
        ),
        UniqueConstraint(
            "id",
            "plan_id",
            "resolution_id",
            name="uq_resolution_revalidations_id_plan_resolution",
        ),
        ForeignKeyConstraint(
            ["plan_id", "resolution_id"],
            ["resolution_plans.id", "resolution_plans.resolution_id"],
            name="fk_resolution_revalidations_plan_same_resolution",
            ondelete="RESTRICT",
        ),
        ForeignKeyConstraint(
            ["previous_context_snapshot_id", "resolution_id"],
            [
                "resolution_context_snapshots.id",
                "resolution_context_snapshots.resolution_id",
            ],
            name="fk_resolution_revalidations_previous_context",
            ondelete="RESTRICT",
        ),
        ForeignKeyConstraint(
            ["current_context_snapshot_id", "resolution_id"],
            [
                "resolution_context_snapshots.id",
                "resolution_context_snapshots.resolution_id",
            ],
            name="fk_resolution_revalidations_current_context",
            ondelete="RESTRICT",
        ),
        CheckConstraint(
            "status IN ('valid','valid_with_warnings','requires_new_plan',"
            "'no_longer_resolvable','blocked')",
            name="ck_resolution_revalidations_status",
        ),
        CheckConstraint(
            "length(revalidation_hash) = 64",
            name="ck_resolution_revalidations_hash_length",
        ),
        Index(
            "ix_resolution_revalidations_plan_time",
            "plan_id",
            "revalidated_at",
        ),
    )

    resolution_id: Mapped[int] = mapped_column(
        BIGINT_ID,
        ForeignKey("resolutions.id", ondelete="RESTRICT"),
        nullable=False,
    )
    plan_id: Mapped[int] = mapped_column(BIGINT_ID, nullable=False)
    previous_context_snapshot_id: Mapped[int] = mapped_column(
        BIGINT_ID, nullable=False
    )
    current_context_snapshot_id: Mapped[int] = mapped_column(
        BIGINT_ID, nullable=False
    )
    status: Mapped[str] = mapped_column(String(32), nullable=False)
    changed_facts: Mapped[list[Any]] = mapped_column(
        JSON_DOCUMENT, server_default=text("'[]'"), nullable=False
    )
    ignored_changes: Mapped[list[Any]] = mapped_column(
        JSON_DOCUMENT, server_default=text("'[]'"), nullable=False
    )
    invalidating_changes: Mapped[list[Any]] = mapped_column(
        JSON_DOCUMENT, server_default=text("'[]'"), nullable=False
    )
    warnings: Mapped[list[Any]] = mapped_column(
        JSON_DOCUMENT, server_default=text("'[]'"), nullable=False
    )
    result: Mapped[dict[str, Any]] = mapped_column(JSON_DOCUMENT, nullable=False)
    revalidated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    revalidated_by: Mapped[str] = mapped_column(String(200), nullable=False)
    validator_version: Mapped[str] = mapped_column(String(32), nullable=False)
    revalidation_hash: Mapped[str] = mapped_column(String(64), nullable=False)
