"""add Facturama sandbox issuance traceability

Revision ID: 670da69de732
Revises: 660da69de732
"""
from alembic import op
import sqlalchemy as sa

revision = "670da69de732"
down_revision = "660da69de732"
branch_labels = None
depends_on = None

def upgrade() -> None:
    for name, column in (
        ("facturama_id", sa.Column("facturama_id", sa.String(100))),
        ("cfdi_uuid", sa.Column("cfdi_uuid", sa.String(64))),
        ("facturama_environment", sa.Column("facturama_environment", sa.String(20))),
        ("stamped_at", sa.Column("stamped_at", sa.DateTime(timezone=True))),
        ("facturama_request_json", sa.Column("facturama_request_json", sa.JSON())),
        ("facturama_response_json", sa.Column("facturama_response_json", sa.JSON())),
        ("facturama_http_status", sa.Column("facturama_http_status", sa.Integer())),
        ("facturama_error_message", sa.Column("facturama_error_message", sa.Text())),
        ("facturama_attempted_at", sa.Column("facturama_attempted_at", sa.DateTime(timezone=True))),
        ("facturama_xml_path", sa.Column("facturama_xml_path", sa.String(500))),
        ("facturama_pdf_path", sa.Column("facturama_pdf_path", sa.String(500))),
    ): op.add_column("invoices", column)
    op.create_index("ix_invoices_facturama_id", "invoices", ["facturama_id"], unique=True)
    op.create_index("ix_invoices_cfdi_uuid", "invoices", ["cfdi_uuid"], unique=True)
    op.create_index("ix_invoices_facturama_environment", "invoices", ["facturama_environment"])
    op.create_table("facturama_invoice_attempts", sa.Column("invoice_id", sa.Integer(), sa.ForeignKey("invoices.id"), nullable=False), sa.Column("attempt_number", sa.Integer(), nullable=False), sa.Column("status", sa.String(40), nullable=False), sa.Column("request_json", sa.JSON()), sa.Column("response_json", sa.JSON()), sa.Column("http_status", sa.Integer()), sa.Column("error_message", sa.Text()), sa.Column("issued_by_id", sa.Integer(), sa.ForeignKey("users.id")), sa.Column("completed_at", sa.DateTime(timezone=True), server_default=sa.func.now()), sa.Column("id", sa.Integer(), primary_key=True), sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False), sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False))
    op.create_index("ix_facturama_invoice_attempts_invoice_id", "facturama_invoice_attempts", ["invoice_id"])
    op.create_index("ix_facturama_invoice_attempts_status", "facturama_invoice_attempts", ["status"])

def downgrade() -> None:
    op.drop_table("facturama_invoice_attempts")
    for index in ("ix_invoices_facturama_environment", "ix_invoices_cfdi_uuid", "ix_invoices_facturama_id"): op.drop_index(index, table_name="invoices")
    for name in ("facturama_pdf_path", "facturama_xml_path", "facturama_attempted_at", "facturama_error_message", "facturama_http_status", "facturama_response_json", "facturama_request_json", "stamped_at", "facturama_environment", "cfdi_uuid", "facturama_id"): op.drop_column("invoices", name)
