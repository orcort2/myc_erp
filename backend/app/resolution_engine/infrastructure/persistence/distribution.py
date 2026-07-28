"""Cola durable, nodos y eventos operativos del Motor distribuido."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import (
    CheckConstraint,
    DateTime,
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


class ResolutionWorkerNode(MutableTimestampMixin, Base):
    __tablename__ = "resolution_worker_nodes"
    __table_args__ = (
        CheckConstraint(
            "status IN ('active','draining','offline')",
            name="ck_resolution_worker_nodes_status",
        ),
        CheckConstraint(
            "capacity >= 1",
            name="ck_resolution_worker_nodes_capacity_positive",
        ),
        Index(
            "ix_resolution_worker_nodes_status_lease",
            "status",
            "lease_expires_at",
        ),
    )

    node_id: Mapped[str] = mapped_column(String(160), primary_key=True)
    instance_id: Mapped[str] = mapped_column(String(160), nullable=False)
    status: Mapped[str] = mapped_column(String(24), nullable=False)
    capacity: Mapped[int] = mapped_column(Integer, nullable=False)
    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    last_heartbeat_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    lease_expires_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    metadata_json: Mapped[dict[str, Any]] = mapped_column(
        "metadata",
        JSON_DOCUMENT,
        server_default=text("'{}'"),
        nullable=False,
    )


class ResolutionWorkItem(
    ResolutionRecordMixin,
    MutableTimestampMixin,
    Base,
):
    __tablename__ = "resolution_work_items"
    __table_args__ = (
        UniqueConstraint("work_key", name="uq_resolution_work_items_key"),
        CheckConstraint(
            "kind IN ('execution','compensation','outbox_publication')",
            name="ck_resolution_work_items_kind",
        ),
        CheckConstraint(
            "status IN ('queued','claimed','retry_wait','succeeded','failed',"
            "'blocked','cancelled')",
            name="ck_resolution_work_items_status",
        ),
        CheckConstraint(
            "priority BETWEEN -1000 AND 1000",
            name="ck_resolution_work_items_priority",
        ),
        CheckConstraint(
            "attempt_count >= 0 AND max_attempts >= 1 "
            "AND attempt_count <= max_attempts",
            name="ck_resolution_work_items_attempts",
        ),
        CheckConstraint(
            "lease_version >= 0",
            name="ck_resolution_work_items_lease_version",
        ),
        CheckConstraint(
            "length(request_hash) = 64",
            name="ck_resolution_work_items_request_hash",
        ),
        CheckConstraint(
            "result_hash IS NULL OR length(result_hash) = 64",
            name="ck_resolution_work_items_result_hash",
        ),
        CheckConstraint(
            "(status = 'claimed' AND claimed_by IS NOT NULL "
            "AND lease_token IS NOT NULL AND lease_expires_at IS NOT NULL) "
            "OR (status <> 'claimed' AND claimed_by IS NULL "
            "AND lease_token IS NULL AND lease_expires_at IS NULL)",
            name="ck_resolution_work_items_claim_complete",
        ),
        ForeignKeyConstraint(
            ["resolution_id"],
            ["resolutions.id"],
            name="fk_resolution_work_items_resolution",
            ondelete="RESTRICT",
        ),
        ForeignKeyConstraint(
            ["claimed_by"],
            ["resolution_worker_nodes.node_id"],
            name="fk_resolution_work_items_claimed_node",
            ondelete="RESTRICT",
        ),
        Index(
            "ix_resolution_work_items_dispatch",
            "status",
            "available_at",
            "priority",
            "id",
        ),
        Index(
            "ix_resolution_work_items_resolution_status",
            "resolution_id",
            "status",
        ),
        Index(
            "uq_resolution_work_items_claimed_resolution",
            "resolution_id",
            unique=True,
            postgresql_where=text("status = 'claimed'"),
            sqlite_where=text("status = 'claimed'"),
        ),
        Index(
            "ix_resolution_work_items_organization_status",
            "organization_id",
            "status",
        ),
    )

    resolution_id: Mapped[int] = mapped_column(
        BIGINT_ID,
        nullable=False,
    )
    work_key: Mapped[str] = mapped_column(String(240), nullable=False)
    organization_id: Mapped[str] = mapped_column(String(160), nullable=False)
    kind: Mapped[str] = mapped_column(String(32), nullable=False)
    status: Mapped[str] = mapped_column(String(24), nullable=False)
    payload: Mapped[dict[str, Any]] = mapped_column(
        JSON_DOCUMENT, server_default=text("'{}'"), nullable=False
    )
    request_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    correlation_id: Mapped[str] = mapped_column(String(120), nullable=False)
    priority: Mapped[int] = mapped_column(Integer, nullable=False)
    available_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    attempt_count: Mapped[int] = mapped_column(
        Integer, server_default="0", nullable=False
    )
    max_attempts: Mapped[int] = mapped_column(Integer, nullable=False)
    retry_base_seconds: Mapped[int] = mapped_column(Integer, nullable=False)
    retry_maximum_seconds: Mapped[int] = mapped_column(Integer, nullable=False)
    claimed_by: Mapped[str | None] = mapped_column(
        String(160),
    )
    lease_token: Mapped[str | None] = mapped_column(String(160))
    lease_version: Mapped[int] = mapped_column(
        Integer, server_default="0", nullable=False
    )
    lease_expires_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True)
    )
    effect_started_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True)
    )
    completed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True)
    )
    result_payload: Mapped[dict[str, Any]] = mapped_column(
        JSON_DOCUMENT, server_default=text("'{}'"), nullable=False
    )
    result_hash: Mapped[str | None] = mapped_column(String(64))
    last_error_code: Mapped[str | None] = mapped_column(String(160))
    last_error_message: Mapped[str | None] = mapped_column(Text)


class ResolutionWorkEvent(
    ResolutionRecordMixin,
    CreatedAtMixin,
    Base,
):
    """Evento append-only de despacho, lease, recuperación o terminación."""

    __tablename__ = "resolution_work_events"
    __table_args__ = (
        UniqueConstraint(
            "work_item_id",
            "sequence",
            name="uq_resolution_work_events_sequence",
        ),
        CheckConstraint(
            "sequence >= 1",
            name="ck_resolution_work_events_sequence_positive",
        ),
        ForeignKeyConstraint(
            ["work_item_id"],
            ["resolution_work_items.id"],
            name="fk_resolution_work_events_item",
            ondelete="RESTRICT",
        ),
        ForeignKeyConstraint(
            ["resolution_id"],
            ["resolutions.id"],
            name="fk_resolution_work_events_resolution",
            ondelete="RESTRICT",
        ),
        ForeignKeyConstraint(
            ["node_id"],
            ["resolution_worker_nodes.node_id"],
            name="fk_resolution_work_events_node",
            ondelete="RESTRICT",
        ),
        CheckConstraint(
            "attempt_number >= 0",
            name="ck_resolution_work_events_attempt_nonnegative",
        ),
        CheckConstraint(
            "length(payload_hash) = 64",
            name="ck_resolution_work_events_payload_hash",
        ),
        Index(
            "ix_resolution_work_events_item_time",
            "work_item_id",
            "occurred_at",
        ),
        Index(
            "ix_resolution_work_events_node_time",
            "node_id",
            "occurred_at",
        ),
    )

    work_item_id: Mapped[int] = mapped_column(
        BIGINT_ID,
        nullable=False,
    )
    resolution_id: Mapped[int] = mapped_column(
        BIGINT_ID,
        nullable=False,
    )
    sequence: Mapped[int] = mapped_column(BIGINT_ID, nullable=False)
    event_type: Mapped[str] = mapped_column(String(80), nullable=False)
    attempt_number: Mapped[int] = mapped_column(Integer, nullable=False)
    node_id: Mapped[str | None] = mapped_column(
        String(160),
    )
    lease_version: Mapped[int | None] = mapped_column(Integer)
    occurred_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    correlation_id: Mapped[str] = mapped_column(String(120), nullable=False)
    payload: Mapped[dict[str, Any]] = mapped_column(
        JSON_DOCUMENT, server_default=text("'{}'"), nullable=False
    )
    payload_hash: Mapped[str] = mapped_column(String(64), nullable=False)
