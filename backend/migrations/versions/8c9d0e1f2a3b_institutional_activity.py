"""institutional activity across ERP entities

Revision ID: 8c9d0e1f2a3b
Revises: 7b8c9d0e1f2a
Create Date: 2026-07-29 18:30:00.000000
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "8c9d0e1f2a3b"
down_revision: Union[str, None] = "7b8c9d0e1f2a"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "activity_messages",
        sa.Column("event_code", sa.String(length=100), nullable=True),
    )
    op.add_column(
        "activity_messages",
        sa.Column("idempotency_key", sa.String(length=180), nullable=True),
    )
    op.add_column(
        "activity_messages",
        sa.Column("related_entity_type", sa.String(length=40), nullable=True),
    )
    op.add_column(
        "activity_messages",
        sa.Column("related_entity_id", sa.Integer(), nullable=True),
    )
    op.create_index(
        "ix_activity_messages_event_code",
        "activity_messages",
        ["event_code"],
        unique=False,
    )
    op.create_index(
        "ix_activity_messages_idempotency_key",
        "activity_messages",
        ["idempotency_key"],
        unique=True,
    )
    op.create_index(
        "ix_activity_messages_related_entity_type",
        "activity_messages",
        ["related_entity_type"],
        unique=False,
    )
    op.create_index(
        "ix_activity_messages_related_entity_id",
        "activity_messages",
        ["related_entity_id"],
        unique=False,
    )

    op.create_table(
        "activity_thread_reads",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("thread_id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("last_read_message_id", sa.Integer(), nullable=True),
        sa.Column("last_visited_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["last_read_message_id"],
            ["activity_messages.id"],
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["thread_id"],
            ["activity_threads.id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "thread_id",
            "user_id",
            name="uq_activity_thread_read_user",
        ),
    )
    op.create_index(
        "ix_activity_thread_reads_thread_id",
        "activity_thread_reads",
        ["thread_id"],
        unique=False,
    )
    op.create_index(
        "ix_activity_thread_reads_user_id",
        "activity_thread_reads",
        ["user_id"],
        unique=False,
    )
    op.create_index(
        "ix_activity_thread_reads_last_read_message_id",
        "activity_thread_reads",
        ["last_read_message_id"],
        unique=False,
    )

    op.create_table(
        "activity_attention_requests",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("thread_id", sa.Integer(), nullable=False),
        sa.Column("message_id", sa.Integer(), nullable=False),
        sa.Column("requested_by_id", sa.Integer(), nullable=False),
        sa.Column("assigned_user_id", sa.Integer(), nullable=True),
        sa.Column("assigned_area", sa.String(length=80), nullable=True),
        sa.Column("priority", sa.String(length=20), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("resolved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("resolved_by_id", sa.Integer(), nullable=True),
        sa.Column("resolution_note", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "priority IN ('low', 'normal', 'high', 'urgent')",
            name="ck_activity_attention_priority",
        ),
        sa.CheckConstraint(
            "status IN ('pending', 'resolved')",
            name="ck_activity_attention_status",
        ),
        sa.CheckConstraint(
            "assigned_user_id IS NOT NULL OR assigned_area IS NOT NULL",
            name="ck_activity_attention_target",
        ),
        sa.CheckConstraint(
            "(status = 'pending' AND resolved_at IS NULL AND "
            "resolved_by_id IS NULL) OR "
            "(status = 'resolved' AND resolved_at IS NOT NULL AND "
            "resolved_by_id IS NOT NULL)",
            name="ck_activity_attention_resolution",
        ),
        sa.ForeignKeyConstraint(
            ["assigned_user_id"],
            ["users.id"],
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["message_id"],
            ["activity_messages.id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["requested_by_id"],
            ["users.id"],
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["resolved_by_id"],
            ["users.id"],
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["thread_id"],
            ["activity_threads.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_activity_attention_requests_thread_id",
        "activity_attention_requests",
        ["thread_id"],
        unique=False,
    )
    op.create_index(
        "ix_activity_attention_requests_message_id",
        "activity_attention_requests",
        ["message_id"],
        unique=False,
    )
    op.create_index(
        "ix_activity_attention_requests_requested_by_id",
        "activity_attention_requests",
        ["requested_by_id"],
        unique=False,
    )
    op.create_index(
        "ix_activity_attention_requests_assigned_user_id",
        "activity_attention_requests",
        ["assigned_user_id"],
        unique=False,
    )
    op.create_index(
        "ix_activity_attention_requests_assigned_area",
        "activity_attention_requests",
        ["assigned_area"],
        unique=False,
    )
    op.create_index(
        "ix_activity_attention_requests_priority",
        "activity_attention_requests",
        ["priority"],
        unique=False,
    )
    op.create_index(
        "ix_activity_attention_requests_status",
        "activity_attention_requests",
        ["status"],
        unique=False,
    )
    op.create_index(
        "ix_activity_attention_requests_resolved_by_id",
        "activity_attention_requests",
        ["resolved_by_id"],
        unique=False,
    )
    op.create_index(
        "ix_activity_attention_assignee_status",
        "activity_attention_requests",
        ["assigned_user_id", "status"],
        unique=False,
    )
    op.create_index(
        "ix_activity_attention_thread_status",
        "activity_attention_requests",
        ["thread_id", "status"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        "ix_activity_attention_thread_status",
        table_name="activity_attention_requests",
    )
    op.drop_index(
        "ix_activity_attention_assignee_status",
        table_name="activity_attention_requests",
    )
    op.drop_index(
        "ix_activity_attention_requests_resolved_by_id",
        table_name="activity_attention_requests",
    )
    op.drop_index(
        "ix_activity_attention_requests_status",
        table_name="activity_attention_requests",
    )
    op.drop_index(
        "ix_activity_attention_requests_priority",
        table_name="activity_attention_requests",
    )
    op.drop_index(
        "ix_activity_attention_requests_assigned_area",
        table_name="activity_attention_requests",
    )
    op.drop_index(
        "ix_activity_attention_requests_assigned_user_id",
        table_name="activity_attention_requests",
    )
    op.drop_index(
        "ix_activity_attention_requests_requested_by_id",
        table_name="activity_attention_requests",
    )
    op.drop_index(
        "ix_activity_attention_requests_message_id",
        table_name="activity_attention_requests",
    )
    op.drop_index(
        "ix_activity_attention_requests_thread_id",
        table_name="activity_attention_requests",
    )
    op.drop_table("activity_attention_requests")

    op.drop_index(
        "ix_activity_thread_reads_last_read_message_id",
        table_name="activity_thread_reads",
    )
    op.drop_index(
        "ix_activity_thread_reads_user_id",
        table_name="activity_thread_reads",
    )
    op.drop_index(
        "ix_activity_thread_reads_thread_id",
        table_name="activity_thread_reads",
    )
    op.drop_table("activity_thread_reads")

    op.drop_index(
        "ix_activity_messages_related_entity_id",
        table_name="activity_messages",
    )
    op.drop_index(
        "ix_activity_messages_related_entity_type",
        table_name="activity_messages",
    )
    op.drop_index(
        "ix_activity_messages_idempotency_key",
        table_name="activity_messages",
    )
    op.drop_index(
        "ix_activity_messages_event_code",
        table_name="activity_messages",
    )
    op.drop_column("activity_messages", "related_entity_id")
    op.drop_column("activity_messages", "related_entity_type")
    op.drop_column("activity_messages", "idempotency_key")
    op.drop_column("activity_messages", "event_code")
