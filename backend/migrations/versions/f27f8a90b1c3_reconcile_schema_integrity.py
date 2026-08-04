"""reconcile schema integrity

Revision ID: f27f8a90b1c3
Revises: e16e7f8091a2
Create Date: 2026-08-04 12:00:00.000000
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "f27f8a90b1c3"
down_revision: Union[str, None] = "e16e7f8091a2"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


TIMESTAMP_TABLES = (
    "activity_attention_requests",
    "activity_thread_reads",
    "linked_companies",
    "uncertainty_calculations",
    "uncertainty_components",
    "uncertainty_formulas",
    "uncertainty_model_exceptions",
    "uncertainty_models",
)

MISSING_INDEXES = (
    ("ix_certificate_capture_files_identification_status", "certificate_capture_files", ("identification_status",)),
    ("ix_credit_notes_created_by_id", "credit_notes", ("created_by_id",)),
    ("ix_credit_notes_invoice_id", "credit_notes", ("invoice_id",)),
    ("ix_facturama_invoice_attempts_issued_by_id", "facturama_invoice_attempts", ("issued_by_id",)),
    ("ix_invoice_items_equipment_id", "invoice_items", ("equipment_id",)),
    ("ix_invoice_items_quotation_item_id", "invoice_items", ("quotation_item_id",)),
    ("ix_invoice_payments_paid_on", "invoice_payments", ("paid_on",)),
    ("ix_invoice_payments_registered_by_id", "invoice_payments", ("registered_by_id",)),
    ("ix_invoices_client_id", "invoices", ("client_id",)),
    ("ix_invoices_created_by_id", "invoices", ("created_by_id",)),
    ("ix_invoices_due_on", "invoices", ("due_on",)),
    ("ix_invoices_fiscal_client_id", "invoices", ("fiscal_client_id",)),
    ("ix_invoices_issued_on", "invoices", ("issued_on",)),
    ("ix_invoices_quotation_id", "invoices", ("quotation_id",)),
    ("ix_invoices_service_order_id", "invoices", ("service_order_id",)),
    ("ix_invoices_updated_by_id", "invoices", ("updated_by_id",)),
    ("ix_uncertainty_model_exceptions_authorized_by_id", "uncertainty_model_exceptions", ("authorized_by_id",)),
)


def upgrade() -> None:
    for table_name in TIMESTAMP_TABLES:
        for column_name in ("created_at", "updated_at"):
            op.alter_column(
                table_name,
                column_name,
                existing_type=sa.DateTime(timezone=True),
                existing_nullable=False,
                server_default=sa.text("now()"),
            )

    op.add_column(
        "uncertainty_formulas",
        sa.Column("is_active", sa.Boolean(), server_default=sa.true(), nullable=False),
    )
    op.add_column(
        "uncertainty_formulas",
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "uncertainty_formulas",
        sa.Column("deleted_by", sa.Integer(), nullable=True),
    )
    op.alter_column("uncertainty_formulas", "is_active", server_default=None)

    for index_name, table_name, columns in MISSING_INDEXES:
        op.create_index(index_name, table_name, list(columns), unique=False)


def downgrade() -> None:
    for index_name, table_name, _columns in reversed(MISSING_INDEXES):
        op.drop_index(index_name, table_name=table_name)

    op.drop_column("uncertainty_formulas", "deleted_by")
    op.drop_column("uncertainty_formulas", "deleted_at")
    op.drop_column("uncertainty_formulas", "is_active")

    for table_name in reversed(TIMESTAMP_TABLES):
        for column_name in ("updated_at", "created_at"):
            op.alter_column(
                table_name,
                column_name,
                existing_type=sa.DateTime(timezone=True),
                existing_nullable=False,
                server_default=None,
            )
