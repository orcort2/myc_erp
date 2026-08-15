"""add mobile push notification infrastructure

Revision ID: e6b8c0d2f4a6
Revises: d4e7a9c2b6f1
Create Date: 2026-08-14
"""

from alembic import op
import sqlalchemy as sa


revision = "e6b8c0d2f4a6"
down_revision = "d4e7a9c2b6f1"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("notifications", sa.Column("event_key", sa.String(220)))
    op.add_column(
        "notifications",
        sa.Column(
            "delivery_status",
            sa.String(30),
            server_default="pending",
            nullable=False,
        ),
    )
    op.add_column(
        "notifications", sa.Column("push_attempted_at", sa.DateTime(timezone=True))
    )
    op.add_column(
        "notifications", sa.Column("push_delivered_at", sa.DateTime(timezone=True))
    )
    op.add_column("notifications", sa.Column("error_code", sa.String(80)))
    op.create_index(
        "ix_notifications_event_key", "notifications", ["event_key"], unique=True
    )
    op.create_index(
        "ix_notifications_delivery_status",
        "notifications",
        ["delivery_status"],
    )

    op.create_table(
        "push_devices",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("expo_push_token", sa.String(255), nullable=False),
        sa.Column("platform", sa.String(20), nullable=False),
        sa.Column("device_name", sa.String(160)),
        sa.Column("app_version", sa.String(40)),
        sa.Column("is_active", sa.Boolean(), server_default=sa.true(), nullable=False),
        sa.Column("last_seen_at", sa.DateTime(timezone=True), nullable=False),
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
        sa.CheckConstraint("platform IN ('ios', 'android')", name="ck_push_device_platform"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_push_devices_user_id", "push_devices", ["user_id"])
    op.create_index(
        "ix_push_devices_expo_push_token",
        "push_devices",
        ["expo_push_token"],
        unique=True,
    )
    op.create_index("ix_push_devices_is_active", "push_devices", ["is_active"])
    op.create_index(
        "ix_push_devices_user_active", "push_devices", ["user_id", "is_active"]
    )


def downgrade() -> None:
    op.drop_index("ix_push_devices_user_active", table_name="push_devices")
    op.drop_index("ix_push_devices_is_active", table_name="push_devices")
    op.drop_index("ix_push_devices_expo_push_token", table_name="push_devices")
    op.drop_index("ix_push_devices_user_id", table_name="push_devices")
    op.drop_table("push_devices")
    op.drop_index("ix_notifications_delivery_status", table_name="notifications")
    op.drop_index("ix_notifications_event_key", table_name="notifications")
    for column in (
        "error_code",
        "push_delivered_at",
        "push_attempted_at",
        "delivery_status",
        "event_key",
    ):
        op.drop_column("notifications", column)
