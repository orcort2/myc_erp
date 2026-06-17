"""create certificates

Revision ID: 8b9c0d1e2f13
Revises: 7a8b9c0d1e12
Create Date: 2026-06-17 14:20:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "8b9c0d1e2f13"
down_revision: Union[str, None] = "7a8b9c0d1e12"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "certificates",
        sa.Column("folio", sa.String(length=40), nullable=False),
        sa.Column("service_order_id", sa.Integer(), nullable=False),
        sa.Column("equipment_id", sa.Integer(), nullable=False),
        sa.Column("field_sheet_id", sa.Integer(), nullable=False),
        sa.Column("certificate_type", sa.String(length=40), nullable=False),
        sa.Column("status", sa.String(length=60), nullable=False),
        sa.Column("issued_on", sa.Date(), nullable=True),
        sa.Column("released_on", sa.Date(), nullable=True),
        sa.Column("title", sa.String(length=180), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("id", sa.Integer(), nullable=False),
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
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("deleted_by", sa.Integer(), nullable=True),
        sa.ForeignKeyConstraint(["equipment_id"], ["equipment.id"]),
        sa.ForeignKeyConstraint(["field_sheet_id"], ["field_sheets.id"]),
        sa.ForeignKeyConstraint(["service_order_id"], ["service_orders.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_certificates_certificate_type"), "certificates", ["certificate_type"], unique=False)
    op.create_index(op.f("ix_certificates_equipment_id"), "certificates", ["equipment_id"], unique=False)
    op.create_index(op.f("ix_certificates_field_sheet_id"), "certificates", ["field_sheet_id"], unique=False)
    op.create_index(op.f("ix_certificates_folio"), "certificates", ["folio"], unique=True)
    op.create_index(op.f("ix_certificates_id"), "certificates", ["id"], unique=False)
    op.create_index(op.f("ix_certificates_service_order_id"), "certificates", ["service_order_id"], unique=False)
    op.create_index(op.f("ix_certificates_status"), "certificates", ["status"], unique=False)
    op.create_index(
        "uq_certificates_active_field_sheet",
        "certificates",
        ["field_sheet_id"],
        unique=True,
        postgresql_where=sa.text("is_active IS true"),
    )


def downgrade() -> None:
    op.drop_index("uq_certificates_active_field_sheet", table_name="certificates")
    op.drop_index(op.f("ix_certificates_status"), table_name="certificates")
    op.drop_index(op.f("ix_certificates_service_order_id"), table_name="certificates")
    op.drop_index(op.f("ix_certificates_id"), table_name="certificates")
    op.drop_index(op.f("ix_certificates_folio"), table_name="certificates")
    op.drop_index(op.f("ix_certificates_field_sheet_id"), table_name="certificates")
    op.drop_index(op.f("ix_certificates_equipment_id"), table_name="certificates")
    op.drop_index(op.f("ix_certificates_certificate_type"), table_name="certificates")
    op.drop_table("certificates")
