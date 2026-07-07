"""create invoicing module

Revision ID: 0f1e2d3c4b5a
Revises: 9a8b7c6d5e4f
Create Date: 2026-07-06 10:30:00.000000
"""

from alembic import op
import sqlalchemy as sa


revision = "0f1e2d3c4b5a"
down_revision = "9a8b7c6d5e4f"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "invoice_settings",
        sa.Column("key", sa.String(length=60), nullable=False),
        sa.Column("default_series", sa.String(length=20), nullable=False),
        sa.Column("next_sequence", sa.Integer(), nullable=False),
        sa.Column("reset_annually", sa.Boolean(), nullable=False),
        sa.Column("default_tax_rate", sa.Numeric(5, 2), nullable=False),
        sa.Column("default_currency", sa.String(length=10), nullable=False),
        sa.Column("default_credit_days", sa.Integer(), nullable=False),
        sa.Column("allow_manual_folio", sa.Boolean(), nullable=False),
        sa.Column("forms_of_payment", sa.JSON(), nullable=True),
        sa.Column("methods_of_payment", sa.JSON(), nullable=True),
        sa.Column("usage_cfdi_catalog", sa.JSON(), nullable=True),
        sa.Column("tax_regime_catalog", sa.JSON(), nullable=True),
        sa.Column("currency_catalog", sa.JSON(), nullable=True),
        sa.Column("sat_product_keys", sa.JSON(), nullable=True),
        sa.Column("sat_units", sa.JSON(), nullable=True),
        sa.Column("banks", sa.JSON(), nullable=True),
        sa.Column("bank_accounts", sa.JSON(), nullable=True),
        sa.Column("legal_texts", sa.JSON(), nullable=True),
        sa.Column("billing_emails", sa.JSON(), nullable=True),
        sa.Column("emitter_data", sa.JSON(), nullable=True),
        sa.Column("pdf_template_name", sa.String(length=120), nullable=True),
        sa.Column("cfdi_future_parameters", sa.JSON(), nullable=True),
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_invoice_settings_id"), "invoice_settings", ["id"], unique=False)
    op.create_index(op.f("ix_invoice_settings_key"), "invoice_settings", ["key"], unique=True)

    op.create_table(
        "invoices",
        sa.Column("internal_uuid", sa.String(length=64), nullable=False),
        sa.Column("series", sa.String(length=20), nullable=False),
        sa.Column("folio", sa.String(length=40), nullable=False),
        sa.Column("client_id", sa.Integer(), nullable=False),
        sa.Column("fiscal_client_id", sa.Integer(), nullable=True),
        sa.Column("service_order_id", sa.Integer(), nullable=True),
        sa.Column("quotation_id", sa.Integer(), nullable=True),
        sa.Column("issued_on", sa.Date(), nullable=True),
        sa.Column("due_on", sa.Date(), nullable=True),
        sa.Column("subtotal", sa.Numeric(12, 2), nullable=False),
        sa.Column("tax_total", sa.Numeric(12, 2), nullable=False),
        sa.Column("withholding_total", sa.Numeric(12, 2), nullable=False),
        sa.Column("discount_total", sa.Numeric(12, 2), nullable=False),
        sa.Column("total", sa.Numeric(12, 2), nullable=False),
        sa.Column("balance_due", sa.Numeric(12, 2), nullable=False),
        sa.Column("amount_paid", sa.Numeric(12, 2), nullable=False),
        sa.Column("status", sa.String(length=40), nullable=False),
        sa.Column("payment_method", sa.String(length=80), nullable=True),
        sa.Column("payment_form", sa.String(length=80), nullable=True),
        sa.Column("usage_cfdi", sa.String(length=80), nullable=True),
        sa.Column("currency", sa.String(length=10), nullable=False),
        sa.Column("credit_days", sa.Integer(), nullable=False),
        sa.Column("observations", sa.Text(), nullable=True),
        sa.Column("internal_comments", sa.Text(), nullable=True),
        sa.Column("cancellation_reason", sa.Text(), nullable=True),
        sa.Column("created_by_id", sa.Integer(), nullable=True),
        sa.Column("updated_by_id", sa.Integer(), nullable=True),
        sa.Column("last_payment_on", sa.Date(), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("deleted_by", sa.Integer(), nullable=True),
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["client_id"], ["clients.id"]),
        sa.ForeignKeyConstraint(["created_by_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["fiscal_client_id"], ["clients.id"]),
        sa.ForeignKeyConstraint(["quotation_id"], ["quotations.id"]),
        sa.ForeignKeyConstraint(["service_order_id"], ["service_orders.id"]),
        sa.ForeignKeyConstraint(["updated_by_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_invoices_id"), "invoices", ["id"], unique=False)
    op.create_index(op.f("ix_invoices_internal_uuid"), "invoices", ["internal_uuid"], unique=True)
    op.create_index(op.f("ix_invoices_folio"), "invoices", ["folio"], unique=True)
    op.create_index(op.f("ix_invoices_series"), "invoices", ["series"], unique=False)
    op.create_index(op.f("ix_invoices_status"), "invoices", ["status"], unique=False)

    op.create_table(
        "invoice_items",
        sa.Column("invoice_id", sa.Integer(), nullable=False),
        sa.Column("quotation_item_id", sa.Integer(), nullable=True),
        sa.Column("certificate_id", sa.Integer(), nullable=True),
        sa.Column("equipment_id", sa.Integer(), nullable=True),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("quantity", sa.Numeric(12, 2), nullable=False),
        sa.Column("unit", sa.String(length=80), nullable=True),
        sa.Column("sat_unit", sa.String(length=40), nullable=True),
        sa.Column("sat_key", sa.String(length=40), nullable=True),
        sa.Column("unit_price", sa.Numeric(12, 2), nullable=False),
        sa.Column("discount_total", sa.Numeric(12, 2), nullable=False),
        sa.Column("tax_rate", sa.Numeric(5, 2), nullable=False),
        sa.Column("tax_total", sa.Numeric(12, 2), nullable=False),
        sa.Column("line_total", sa.Numeric(12, 2), nullable=False),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("service_type", sa.String(length=80), nullable=True),
        sa.Column("source_type", sa.String(length=40), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("deleted_by", sa.Integer(), nullable=True),
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["certificate_id"], ["certificates.id"]),
        sa.ForeignKeyConstraint(["equipment_id"], ["equipment.id"]),
        sa.ForeignKeyConstraint(["invoice_id"], ["invoices.id"]),
        sa.ForeignKeyConstraint(["quotation_item_id"], ["quotation_items.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_invoice_items_id"), "invoice_items", ["id"], unique=False)
    op.create_index(op.f("ix_invoice_items_invoice_id"), "invoice_items", ["invoice_id"], unique=False)
    op.create_index(op.f("ix_invoice_items_certificate_id"), "invoice_items", ["certificate_id"], unique=False)
    op.create_index(op.f("ix_invoice_items_source_type"), "invoice_items", ["source_type"], unique=False)

    op.create_table(
        "invoice_payments",
        sa.Column("invoice_id", sa.Integer(), nullable=False),
        sa.Column("paid_on", sa.Date(), nullable=True),
        sa.Column("amount", sa.Numeric(12, 2), nullable=False),
        sa.Column("bank_name", sa.String(length=120), nullable=True),
        sa.Column("bank_account", sa.String(length=120), nullable=True),
        sa.Column("reference", sa.String(length=120), nullable=True),
        sa.Column("payment_method", sa.String(length=80), nullable=True),
        sa.Column("payment_form", sa.String(length=80), nullable=True),
        sa.Column("status", sa.String(length=40), nullable=False),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("registered_by_id", sa.Integer(), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("deleted_by", sa.Integer(), nullable=True),
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["invoice_id"], ["invoices.id"]),
        sa.ForeignKeyConstraint(["registered_by_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_invoice_payments_id"), "invoice_payments", ["id"], unique=False)
    op.create_index(op.f("ix_invoice_payments_invoice_id"), "invoice_payments", ["invoice_id"], unique=False)
    op.create_index(op.f("ix_invoice_payments_reference"), "invoice_payments", ["reference"], unique=False)
    op.create_index(op.f("ix_invoice_payments_status"), "invoice_payments", ["status"], unique=False)

    op.create_table(
        "credit_notes",
        sa.Column("invoice_id", sa.Integer(), nullable=False),
        sa.Column("folio", sa.String(length=40), nullable=False),
        sa.Column("issued_on", sa.Date(), nullable=True),
        sa.Column("reason", sa.Text(), nullable=False),
        sa.Column("subtotal", sa.Numeric(12, 2), nullable=False),
        sa.Column("tax_total", sa.Numeric(12, 2), nullable=False),
        sa.Column("total", sa.Numeric(12, 2), nullable=False),
        sa.Column("status", sa.String(length=40), nullable=False),
        sa.Column("observations", sa.Text(), nullable=True),
        sa.Column("created_by_id", sa.Integer(), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("deleted_by", sa.Integer(), nullable=True),
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["created_by_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["invoice_id"], ["invoices.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_credit_notes_id"), "credit_notes", ["id"], unique=False)
    op.create_index(op.f("ix_credit_notes_folio"), "credit_notes", ["folio"], unique=True)
    op.create_index(op.f("ix_credit_notes_status"), "credit_notes", ["status"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_credit_notes_status"), table_name="credit_notes")
    op.drop_index(op.f("ix_credit_notes_folio"), table_name="credit_notes")
    op.drop_index(op.f("ix_credit_notes_id"), table_name="credit_notes")
    op.drop_table("credit_notes")
    op.drop_index(op.f("ix_invoice_payments_status"), table_name="invoice_payments")
    op.drop_index(op.f("ix_invoice_payments_reference"), table_name="invoice_payments")
    op.drop_index(op.f("ix_invoice_payments_invoice_id"), table_name="invoice_payments")
    op.drop_index(op.f("ix_invoice_payments_id"), table_name="invoice_payments")
    op.drop_table("invoice_payments")
    op.drop_index(op.f("ix_invoice_items_source_type"), table_name="invoice_items")
    op.drop_index(op.f("ix_invoice_items_certificate_id"), table_name="invoice_items")
    op.drop_index(op.f("ix_invoice_items_invoice_id"), table_name="invoice_items")
    op.drop_index(op.f("ix_invoice_items_id"), table_name="invoice_items")
    op.drop_table("invoice_items")
    op.drop_index(op.f("ix_invoices_status"), table_name="invoices")
    op.drop_index(op.f("ix_invoices_series"), table_name="invoices")
    op.drop_index(op.f("ix_invoices_folio"), table_name="invoices")
    op.drop_index(op.f("ix_invoices_internal_uuid"), table_name="invoices")
    op.drop_index(op.f("ix_invoices_id"), table_name="invoices")
    op.drop_table("invoices")
    op.drop_index(op.f("ix_invoice_settings_key"), table_name="invoice_settings")
    op.drop_index(op.f("ix_invoice_settings_id"), table_name="invoice_settings")
    op.drop_table("invoice_settings")
