"""add certificate authentication

Revision ID: f7a8b9c0d1e2
Revises: e6f7a8b9c0d1
Create Date: 2026-06-30 10:20:00.000000
"""
from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "f7a8b9c0d1e2"
down_revision: str | None = "e6f7a8b9c0d1"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("certificates", sa.Column("authentication_code", sa.String(length=40), nullable=True))
    op.add_column("certificates", sa.Column("authentication_hash", sa.String(length=64), nullable=True))
    op.add_column("certificates", sa.Column("authenticated_pdf_path", sa.String(length=255), nullable=True))
    op.add_column("certificates", sa.Column("authenticated_pdf_generated_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("certificates", sa.Column("authenticated_by_id", sa.Integer(), nullable=True))
    op.add_column("certificates", sa.Column("verification_url", sa.String(length=255), nullable=True))
    op.create_index(op.f("ix_certificates_authentication_code"), "certificates", ["authentication_code"], unique=True)
    op.create_index(op.f("ix_certificates_authentication_hash"), "certificates", ["authentication_hash"], unique=False)
    op.create_index(op.f("ix_certificates_authenticated_by_id"), "certificates", ["authenticated_by_id"], unique=False)
    op.create_foreign_key(
        "fk_certificates_authenticated_by_id_users",
        "certificates",
        "users",
        ["authenticated_by_id"],
        ["id"],
    )


def downgrade() -> None:
    op.drop_constraint("fk_certificates_authenticated_by_id_users", "certificates", type_="foreignkey")
    op.drop_index(op.f("ix_certificates_authenticated_by_id"), table_name="certificates")
    op.drop_index(op.f("ix_certificates_authentication_hash"), table_name="certificates")
    op.drop_index(op.f("ix_certificates_authentication_code"), table_name="certificates")
    op.drop_column("certificates", "verification_url")
    op.drop_column("certificates", "authenticated_by_id")
    op.drop_column("certificates", "authenticated_pdf_generated_at")
    op.drop_column("certificates", "authenticated_pdf_path")
    op.drop_column("certificates", "authentication_hash")
    op.drop_column("certificates", "authentication_code")
