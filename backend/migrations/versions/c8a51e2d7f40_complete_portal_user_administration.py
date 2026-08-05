"""complete portal user administration

Revision ID: c8a51e2d7f40
Revises: bd2270bc5282
"""

from alembic import op
import sqlalchemy as sa


revision = "c8a51e2d7f40"
down_revision = "bd2270bc5282"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("users", sa.Column("phone", sa.String(length=40), nullable=True))
    op.add_column("users", sa.Column("job_title", sa.String(length=120), nullable=True))
    op.add_column("users", sa.Column("area", sa.String(length=120), nullable=True))
    op.add_column(
        "users",
        sa.Column("language", sa.String(length=10), server_default="es-MX", nullable=False),
    )
    op.add_column(
        "users",
        sa.Column(
            "timezone",
            sa.String(length=80),
            server_default="America/Mexico_City",
            nullable=False,
        ),
    )
    op.execute("UPDATE users SET is_active = CASE WHEN status = 'active' THEN true ELSE false END")


def downgrade() -> None:
    op.drop_column("users", "timezone")
    op.drop_column("users", "language")
    op.drop_column("users", "area")
    op.drop_column("users", "job_title")
    op.drop_column("users", "phone")
