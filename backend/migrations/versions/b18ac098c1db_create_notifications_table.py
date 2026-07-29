"""create notifications table

Revision ID: b18ac098c1db
Revises: a0d2f4b6c8e1
Create Date: 2026-07-28 13:05:17.089241
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = 'b18ac098c1db'
down_revision: Union[str, None] = 'a0d2f4b6c8e1'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "notifications",
        sa.Column(
            "id",
            sa.Integer(),
            nullable=False,
        ),
        sa.Column(
            "recipient_user_id",
            sa.Integer(),
            nullable=False,
        ),
        sa.Column(
            "actor_user_id",
            sa.Integer(),
            nullable=True,
        ),
        sa.Column(
            "notification_type",
            sa.String(length=50),
            nullable=False,
        ),
        sa.Column(
            "title",
            sa.String(length=180),
            nullable=False,
        ),
        sa.Column(
            "body",
            sa.Text(),
            nullable=True,
        ),
        sa.Column(
            "entity_type",
            sa.String(length=40),
            nullable=True,
        ),
        sa.Column(
            "entity_id",
            sa.Integer(),
            nullable=True,
        ),
        sa.Column(
            "activity_message_id",
            sa.Integer(),
            nullable=True,
        ),
        sa.Column(
            "priority",
            sa.String(length=20),
            server_default="normal",
            nullable=False,
        ),
        sa.Column(
            "metadata_json",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'{}'::jsonb"),
            nullable=False,
        ),
        sa.Column(
            "read_at",
            sa.DateTime(timezone=True),
            nullable=True,
        ),
        sa.Column(
            "dismissed_at",
            sa.DateTime(timezone=True),
            nullable=True,
        ),
        sa.Column(
            "revoked_at",
            sa.DateTime(timezone=True),
            nullable=True,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["activity_message_id"],
            ["activity_messages.id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["actor_user_id"],
            ["users.id"],
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["recipient_user_id"],
            ["users.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "recipient_user_id",
            "notification_type",
            "activity_message_id",
            name="uq_notification_recipient_type_message",
        ),
    )

    op.create_index(
        "ix_notifications_activity_message_id",
        "notifications",
        ["activity_message_id"],
        unique=False,
    )

    op.create_index(
        "ix_notifications_actor_user_id",
        "notifications",
        ["actor_user_id"],
        unique=False,
    )

    op.create_index(
        "ix_notifications_dismissed_at",
        "notifications",
        ["dismissed_at"],
        unique=False,
    )

    op.create_index(
        "ix_notifications_entity",
        "notifications",
        ["entity_type", "entity_id"],
        unique=False,
    )

    op.create_index(
        "ix_notifications_entity_id",
        "notifications",
        ["entity_id"],
        unique=False,
    )

    op.create_index(
        "ix_notifications_entity_type",
        "notifications",
        ["entity_type"],
        unique=False,
    )

    op.create_index(
        "ix_notifications_notification_type",
        "notifications",
        ["notification_type"],
        unique=False,
    )

    op.create_index(
        "ix_notifications_priority",
        "notifications",
        ["priority"],
        unique=False,
    )

    op.create_index(
        "ix_notifications_read_at",
        "notifications",
        ["read_at"],
        unique=False,
    )

    op.create_index(
        "ix_notifications_recipient_read_created",
        "notifications",
        [
            "recipient_user_id",
            "read_at",
            "created_at",
        ],
        unique=False,
    )

    op.create_index(
        "ix_notifications_recipient_user_id",
        "notifications",
        ["recipient_user_id"],
        unique=False,
    )

    op.create_index(
        "ix_notifications_revoked_at",
        "notifications",
        ["revoked_at"],
        unique=False,
    )

def downgrade() -> None:
    op.drop_index(
        "ix_notifications_revoked_at",
        table_name="notifications",
    )

    op.drop_index(
        "ix_notifications_recipient_user_id",
        table_name="notifications",
    )

    op.drop_index(
        "ix_notifications_recipient_read_created",
        table_name="notifications",
    )

    op.drop_index(
        "ix_notifications_read_at",
        table_name="notifications",
    )

    op.drop_index(
        "ix_notifications_priority",
        table_name="notifications",
    )

    op.drop_index(
        "ix_notifications_notification_type",
        table_name="notifications",
    )

    op.drop_index(
        "ix_notifications_entity_type",
        table_name="notifications",
    )

    op.drop_index(
        "ix_notifications_entity_id",
        table_name="notifications",
    )

    op.drop_index(
        "ix_notifications_entity",
        table_name="notifications",
    )

    op.drop_index(
        "ix_notifications_dismissed_at",
        table_name="notifications",
    )

    op.drop_index(
        "ix_notifications_actor_user_id",
        table_name="notifications",
    )

    op.drop_index(
        "ix_notifications_activity_message_id",
        table_name="notifications",
    )

    op.drop_table("notifications")
