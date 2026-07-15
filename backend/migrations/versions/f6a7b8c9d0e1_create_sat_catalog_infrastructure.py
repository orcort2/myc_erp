"""create SAT catalog infrastructure

Revision ID: f6a7b8c9d0e1
Revises: f5d6e7f8a9b0
Create Date: 2026-07-14 12:00:00.000000
"""

from alembic import op
import sqlalchemy as sa


revision = "f6a7b8c9d0e1"
down_revision = "f5d6e7f8a9b0"
branch_labels = None
depends_on = None


CATALOGS = [
    ("products_services", "Productos y servicios", "c_ClaveProdServ"),
    ("units", "Unidades", "c_ClaveUnidad"),
    ("fiscal_regimes", "Régimen fiscal", "c_RegimenFiscal"),
    ("cfdi_uses", "Uso CFDI", "c_UsoCFDI"),
    ("payment_forms", "Formas de pago", "c_FormaPago"),
    ("payment_methods", "Métodos de pago", "c_MetodoPago"),
    ("currencies", "Monedas", "c_Moneda"),
    ("countries", "Países", "c_Pais"),
    ("postal_codes", "Códigos postales", "c_CodigoPostal"),
    ("tax_objects", "Objeto de impuesto", "c_ObjetoImp"),
    ("relation_types", "Tipos de relación", "c_TipoRelacion"),
    ("cancellation_reasons", "Motivos de cancelación", "c_MotivoCancelacion"),
    ("exports", "Exportación", "c_Exportacion"),
    ("taxes", "Impuestos", "c_Impuesto"),
    ("factor_types", "Tipos de factor", "c_TipoFactor"),
    ("tax_rates", "Tasas o cuotas", "c_TasaOCuota"),
    ("voucher_types", "Tipos de comprobante", "c_TipoDeComprobante"),
]


def upgrade() -> None:
    op.create_table(
        "sat_catalogs",
        sa.Column("code", sa.String(length=80), nullable=False),
        sa.Column("name", sa.String(length=180), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("code"),
    )
    op.create_index(op.f("ix_sat_catalogs_id"), "sat_catalogs", ["id"], unique=False)
    op.create_index(op.f("ix_sat_catalogs_code"), "sat_catalogs", ["code"], unique=True)
    op.create_table(
        "sat_catalog_versions",
        sa.Column("catalog_id", sa.Integer(), nullable=False),
        sa.Column("version", sa.String(length=120), nullable=False),
        sa.Column("publication_date", sa.Date(), nullable=True),
        sa.Column("imported_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("checksum", sa.String(length=128), nullable=False),
        sa.Column("source_filename", sa.String(length=255), nullable=False),
        sa.Column("imported_by_id", sa.Integer(), nullable=True),
        sa.Column("record_count", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(length=30), nullable=False),
        sa.Column("report", sa.JSON(), nullable=True),
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["catalog_id"], ["sat_catalogs.id"]),
        sa.ForeignKeyConstraint(["imported_by_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("catalog_id", "version", name="uq_sat_catalog_version"),
        sa.UniqueConstraint("catalog_id", "checksum", name="uq_sat_catalog_checksum"),
    )
    op.create_index(op.f("ix_sat_catalog_versions_id"), "sat_catalog_versions", ["id"], unique=False)
    op.create_index(op.f("ix_sat_catalog_versions_catalog_id"), "sat_catalog_versions", ["catalog_id"], unique=False)
    op.create_index(op.f("ix_sat_catalog_versions_imported_by_id"), "sat_catalog_versions", ["imported_by_id"], unique=False)
    op.create_index(op.f("ix_sat_catalog_versions_status"), "sat_catalog_versions", ["status"], unique=False)
    op.create_table(
        "sat_catalog_records",
        sa.Column("catalog_version_id", sa.Integer(), nullable=False),
        sa.Column("code", sa.String(length=120), nullable=False),
        sa.Column("name", sa.String(length=500), nullable=True),
        sa.Column("valid_from", sa.Date(), nullable=True),
        sa.Column("valid_until", sa.Date(), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("data", sa.JSON(), nullable=False),
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["catalog_version_id"], ["sat_catalog_versions.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("catalog_version_id", "code", name="uq_sat_catalog_record_version_code"),
    )
    op.create_index(op.f("ix_sat_catalog_records_id"), "sat_catalog_records", ["id"], unique=False)
    op.create_index(op.f("ix_sat_catalog_records_catalog_version_id"), "sat_catalog_records", ["catalog_version_id"], unique=False)
    op.create_index(op.f("ix_sat_catalog_records_code"), "sat_catalog_records", ["code"], unique=False)
    op.create_index(op.f("ix_sat_catalog_records_name"), "sat_catalog_records", ["name"], unique=False)
    op.create_index(op.f("ix_sat_catalog_records_is_active"), "sat_catalog_records", ["is_active"], unique=False)
    sat_catalogs = sa.table("sat_catalogs", sa.column("code", sa.String), sa.column("name", sa.String), sa.column("description", sa.Text))
    op.bulk_insert(sat_catalogs, [{"code": code, "name": name, "description": description} for code, name, description in CATALOGS])


def downgrade() -> None:
    op.drop_index(op.f("ix_sat_catalog_records_is_active"), table_name="sat_catalog_records")
    op.drop_index(op.f("ix_sat_catalog_records_name"), table_name="sat_catalog_records")
    op.drop_index(op.f("ix_sat_catalog_records_code"), table_name="sat_catalog_records")
    op.drop_index(op.f("ix_sat_catalog_records_catalog_version_id"), table_name="sat_catalog_records")
    op.drop_index(op.f("ix_sat_catalog_records_id"), table_name="sat_catalog_records")
    op.drop_table("sat_catalog_records")
    op.drop_index(op.f("ix_sat_catalog_versions_status"), table_name="sat_catalog_versions")
    op.drop_index(op.f("ix_sat_catalog_versions_imported_by_id"), table_name="sat_catalog_versions")
    op.drop_index(op.f("ix_sat_catalog_versions_catalog_id"), table_name="sat_catalog_versions")
    op.drop_index(op.f("ix_sat_catalog_versions_id"), table_name="sat_catalog_versions")
    op.drop_table("sat_catalog_versions")
    op.drop_index(op.f("ix_sat_catalogs_code"), table_name="sat_catalogs")
    op.drop_index(op.f("ix_sat_catalogs_id"), table_name="sat_catalogs")
    op.drop_table("sat_catalogs")
