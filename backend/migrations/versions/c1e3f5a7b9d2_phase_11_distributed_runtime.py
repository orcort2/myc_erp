"""Add the durable Resolution Engine distributed runtime.

Revision ID: c1e3f5a7b9d2
Revises: a0d2f4b6c8e1
Create Date: 2026-07-28
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "c1e3f5a7b9d2"
down_revision: str | None = "a0d2f4b6c8e1"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    json_document = sa.JSON().with_variant(
        postgresql.JSONB(astext_type=sa.Text()),
        "postgresql",
    )
    op.create_table(
        "resolution_worker_nodes",
        sa.Column("node_id", sa.String(length=160), nullable=False),
        sa.Column("instance_id", sa.String(length=160), nullable=False),
        sa.Column("status", sa.String(length=24), nullable=False),
        sa.Column("capacity", sa.Integer(), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column(
            "last_heartbeat_at", sa.DateTime(timezone=True), nullable=False
        ),
        sa.Column(
            "lease_expires_at", sa.DateTime(timezone=True), nullable=False
        ),
        sa.Column(
            "metadata",
            json_document,
            server_default=sa.text("'{}'"),
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.CheckConstraint(
            "status IN ('active','draining','offline')",
            name="ck_resolution_worker_nodes_status",
        ),
        sa.CheckConstraint(
            "capacity >= 1",
            name="ck_resolution_worker_nodes_capacity_positive",
        ),
        sa.PrimaryKeyConstraint("node_id"),
    )
    op.create_index(
        "ix_resolution_worker_nodes_status_lease",
        "resolution_worker_nodes",
        ["status", "lease_expires_at"],
    )

    op.create_table(
        "resolution_work_items",
        sa.Column("resolution_id", sa.BigInteger(), nullable=False),
        sa.Column("work_key", sa.String(length=240), nullable=False),
        sa.Column("organization_id", sa.String(length=160), nullable=False),
        sa.Column("kind", sa.String(length=32), nullable=False),
        sa.Column("status", sa.String(length=24), nullable=False),
        sa.Column(
            "payload",
            json_document,
            server_default=sa.text("'{}'"),
            nullable=False,
        ),
        sa.Column("request_hash", sa.String(length=64), nullable=False),
        sa.Column("correlation_id", sa.String(length=120), nullable=False),
        sa.Column("priority", sa.Integer(), nullable=False),
        sa.Column("available_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column(
            "attempt_count",
            sa.Integer(),
            server_default="0",
            nullable=False,
        ),
        sa.Column("max_attempts", sa.Integer(), nullable=False),
        sa.Column("retry_base_seconds", sa.Integer(), nullable=False),
        sa.Column("retry_maximum_seconds", sa.Integer(), nullable=False),
        sa.Column("claimed_by", sa.String(length=160)),
        sa.Column("lease_token", sa.String(length=160)),
        sa.Column(
            "lease_version",
            sa.Integer(),
            server_default="0",
            nullable=False,
        ),
        sa.Column("lease_expires_at", sa.DateTime(timezone=True)),
        sa.Column("effect_started_at", sa.DateTime(timezone=True)),
        sa.Column("completed_at", sa.DateTime(timezone=True)),
        sa.Column(
            "result_payload",
            json_document,
            server_default=sa.text("'{}'"),
            nullable=False,
        ),
        sa.Column("result_hash", sa.String(length=64)),
        sa.Column("last_error_code", sa.String(length=160)),
        sa.Column("last_error_message", sa.Text()),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "id", sa.BigInteger(), autoincrement=True, nullable=False
        ),
        sa.CheckConstraint(
            "kind IN ('execution','compensation','outbox_publication')",
            name="ck_resolution_work_items_kind",
        ),
        sa.CheckConstraint(
            "status IN ('queued','claimed','retry_wait','succeeded','failed',"
            "'blocked','cancelled')",
            name="ck_resolution_work_items_status",
        ),
        sa.CheckConstraint(
            "priority BETWEEN -1000 AND 1000",
            name="ck_resolution_work_items_priority",
        ),
        sa.CheckConstraint(
            "attempt_count >= 0 AND max_attempts >= 1 "
            "AND attempt_count <= max_attempts",
            name="ck_resolution_work_items_attempts",
        ),
        sa.CheckConstraint(
            "lease_version >= 0",
            name="ck_resolution_work_items_lease_version",
        ),
        sa.CheckConstraint(
            "length(request_hash) = 64",
            name="ck_resolution_work_items_request_hash",
        ),
        sa.CheckConstraint(
            "result_hash IS NULL OR length(result_hash) = 64",
            name="ck_resolution_work_items_result_hash",
        ),
        sa.CheckConstraint(
            "(status = 'claimed' AND claimed_by IS NOT NULL "
            "AND lease_token IS NOT NULL AND lease_expires_at IS NOT NULL) "
            "OR (status <> 'claimed' AND claimed_by IS NULL "
            "AND lease_token IS NULL AND lease_expires_at IS NULL)",
            name="ck_resolution_work_items_claim_complete",
        ),
        sa.ForeignKeyConstraint(
            ["claimed_by"],
            ["resolution_worker_nodes.node_id"],
            name="fk_resolution_work_items_claimed_node",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["resolution_id"],
            ["resolutions.id"],
            name="fk_resolution_work_items_resolution",
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "work_key", name="uq_resolution_work_items_key"
        ),
    )
    op.create_index(
        "ix_resolution_work_items_dispatch",
        "resolution_work_items",
        ["status", "available_at", "priority", "id"],
    )
    op.create_index(
        "ix_resolution_work_items_resolution_status",
        "resolution_work_items",
        ["resolution_id", "status"],
    )
    op.create_index(
        "uq_resolution_work_items_claimed_resolution",
        "resolution_work_items",
        ["resolution_id"],
        unique=True,
        postgresql_where=sa.text("status = 'claimed'"),
        sqlite_where=sa.text("status = 'claimed'"),
    )
    op.create_index(
        "ix_resolution_work_items_organization_status",
        "resolution_work_items",
        ["organization_id", "status"],
    )

    op.create_table(
        "resolution_work_events",
        sa.Column("work_item_id", sa.BigInteger(), nullable=False),
        sa.Column("resolution_id", sa.BigInteger(), nullable=False),
        sa.Column("sequence", sa.BigInteger(), nullable=False),
        sa.Column("event_type", sa.String(length=80), nullable=False),
        sa.Column("attempt_number", sa.Integer(), nullable=False),
        sa.Column("node_id", sa.String(length=160)),
        sa.Column("lease_version", sa.Integer()),
        sa.Column("occurred_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("correlation_id", sa.String(length=120), nullable=False),
        sa.Column(
            "payload",
            json_document,
            server_default=sa.text("'{}'"),
            nullable=False,
        ),
        sa.Column("payload_hash", sa.String(length=64), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "id", sa.BigInteger(), autoincrement=True, nullable=False
        ),
        sa.CheckConstraint(
            "sequence >= 1",
            name="ck_resolution_work_events_sequence_positive",
        ),
        sa.CheckConstraint(
            "attempt_number >= 0",
            name="ck_resolution_work_events_attempt_nonnegative",
        ),
        sa.CheckConstraint(
            "length(payload_hash) = 64",
            name="ck_resolution_work_events_payload_hash",
        ),
        sa.ForeignKeyConstraint(
            ["node_id"],
            ["resolution_worker_nodes.node_id"],
            name="fk_resolution_work_events_node",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["resolution_id"],
            ["resolutions.id"],
            name="fk_resolution_work_events_resolution",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["work_item_id"],
            ["resolution_work_items.id"],
            name="fk_resolution_work_events_item",
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "work_item_id",
            "sequence",
            name="uq_resolution_work_events_sequence",
        ),
    )
    op.create_index(
        "ix_resolution_work_events_item_time",
        "resolution_work_events",
        ["work_item_id", "occurred_at"],
    )
    op.create_index(
        "ix_resolution_work_events_node_time",
        "resolution_work_events",
        ["node_id", "occurred_at"],
    )
    if op.get_bind().dialect.name == "postgresql":
        op.execute(
            """
            CREATE TRIGGER trg_resolution_work_events_immutable
            BEFORE UPDATE OR DELETE ON resolution_work_events
            FOR EACH ROW
            EXECUTE FUNCTION resolution_engine_prevent_mutation()
            """
        )


def downgrade() -> None:
    if op.get_bind().dialect.name == "postgresql":
        op.execute(
            "DROP TRIGGER IF EXISTS trg_resolution_work_events_immutable "
            "ON resolution_work_events"
        )
    op.drop_index(
        "ix_resolution_work_events_node_time",
        table_name="resolution_work_events",
    )
    op.drop_index(
        "ix_resolution_work_events_item_time",
        table_name="resolution_work_events",
    )
    op.drop_table("resolution_work_events")
    op.drop_index(
        "ix_resolution_work_items_organization_status",
        table_name="resolution_work_items",
    )
    op.drop_index(
        "uq_resolution_work_items_claimed_resolution",
        table_name="resolution_work_items",
    )
    op.drop_index(
        "ix_resolution_work_items_resolution_status",
        table_name="resolution_work_items",
    )
    op.drop_index(
        "ix_resolution_work_items_dispatch",
        table_name="resolution_work_items",
    )
    op.drop_table("resolution_work_items")
    op.drop_index(
        "ix_resolution_worker_nodes_status_lease",
        table_name="resolution_worker_nodes",
    )
    op.drop_table("resolution_worker_nodes")
