"""add user permission overrides

Revision ID: fdc1c503a353
Revises: f4a1c9d2e710
Create Date: 2026-08-12 13:40:21.746653
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "fdc1c503a353"
down_revision: Union[str, None] = "f4a1c9d2e710"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "user_permission_overrides",
        sa.Column(
            "user_id",
            sa.Integer(),
            nullable=False,
        ),
        sa.Column(
            "permission",
            sa.String(length=160),
            nullable=False,
        ),
        sa.Column(
            "effect",
            sa.String(length=10),
            nullable=False,
        ),
        sa.Column(
            "id",
            sa.Integer(),
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "effect IN ('allow', 'deny')",
            name="ck_user_permission_override_effect",
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "user_id",
            "permission",
            name="uq_user_permission_override_user_permission",
        ),
    )

    op.create_index(
        op.f("ix_user_permission_overrides_permission"),
        "user_permission_overrides",
        ["permission"],
        unique=False,
    )

    op.create_index(
        op.f("ix_user_permission_overrides_user_id"),
        "user_permission_overrides",
        ["user_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        op.f("ix_user_permission_overrides_user_id"),
        table_name="user_permission_overrides",
    )

    op.drop_index(
        op.f("ix_user_permission_overrides_permission"),
        table_name="user_permission_overrides",
    )

    op.drop_table("user_permission_overrides")