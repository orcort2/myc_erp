"""add calibration capture package snapshots and upload traceability

Revision ID: fc4d5e6f7a8b
Revises: 670da69de732
Create Date: 2026-07-17 13:20:00.000000
"""
from alembic import op
import sqlalchemy as sa

revision = "fc4d5e6f7a8b"
down_revision = "670da69de732"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("catalog_items", sa.Column("expected_certificate_master_id", sa.Integer(), nullable=True))
    op.create_foreign_key("fk_catalog_items_expected_certificate_master", "catalog_items", "controlled_documents", ["expected_certificate_master_id"], ["id"])
    op.create_index("ix_catalog_items_expected_certificate_master_id", "catalog_items", ["expected_certificate_master_id"])
    for name, target in (("certificate_master_document_id", "controlled_documents"), ("certificate_master_version_id", "controlled_document_versions")):
        op.add_column("equipment", sa.Column(name, sa.Integer(), nullable=True))
        op.create_foreign_key(f"fk_equipment_{name}", "equipment", target, [name], ["id"])
        op.create_index(f"ix_equipment_{name}", "equipment", [name])
    op.add_column("equipment", sa.Column("certificate_template_path_snapshot", sa.String(length=255), nullable=True))
    op.add_column("equipment", sa.Column("certificate_template_filename_snapshot", sa.String(length=255), nullable=True))
    op.create_table("certificate_capture_files",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("certificate_id", sa.Integer(), sa.ForeignKey("certificates.id"), nullable=True, index=True),
        sa.Column("service_order_id", sa.Integer(), sa.ForeignKey("service_orders.id"), nullable=False, index=True),
        sa.Column("original_filename", sa.String(length=255), nullable=False),
        sa.Column("stored_path", sa.String(length=255), nullable=True),
        sa.Column("identification_status", sa.String(length=40), nullable=False, server_default="unidentified"),
        sa.Column("validation_results", sa.JSON(), nullable=True),
        sa.Column("uploaded_by_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=True, index=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
    )


def downgrade() -> None:
    op.drop_table("certificate_capture_files")
    op.drop_column("equipment", "certificate_template_filename_snapshot")
    op.drop_column("equipment", "certificate_template_path_snapshot")
    for name in ("certificate_master_version_id", "certificate_master_document_id"):
        op.drop_index(f"ix_equipment_{name}", table_name="equipment")
        op.drop_constraint(f"fk_equipment_{name}", "equipment", type_="foreignkey")
        op.drop_column("equipment", name)
    op.drop_index("ix_catalog_items_expected_certificate_master_id", table_name="catalog_items")
    op.drop_constraint("fk_catalog_items_expected_certificate_master", "catalog_items", type_="foreignkey")
    op.drop_column("catalog_items", "expected_certificate_master_id")
