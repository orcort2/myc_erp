"""controlled unlock, service types, linked companies and folio sequences

Revision ID: ae1f2a3b4c5d
Revises: 9d0e1f2a3b4c
Create Date: 2026-07-29 23:30:00.000000
"""

from typing import Sequence, Union
from datetime import datetime, timezone

from alembic import op
import sqlalchemy as sa


revision: str = "ae1f2a3b4c5d"
down_revision: Union[str, None] = "9d0e1f2a3b4c"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    now = datetime.now(timezone.utc)
    op.create_table(
        "linked_companies",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=180), nullable=False),
        sa.Column("legal_name", sa.String(length=240), nullable=True),
        sa.Column("abbreviation", sa.String(length=40), nullable=False),
        sa.Column("default_certificate_prefix", sa.String(length=12), nullable=False),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("document_configuration", sa.JSON(), nullable=True),
        sa.Column("is_enabled", sa.Boolean(), server_default="true", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("deleted_by", sa.Integer(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("name", name="linked_companies_name_key"),
        sa.UniqueConstraint(
            "abbreviation", name="linked_companies_abbreviation_key"
        ),
    )
    for column in ("name", "abbreviation", "is_enabled"):
        op.create_index(f"ix_linked_companies_{column}", "linked_companies", [column])
    op.bulk_insert(
        sa.table(
            "linked_companies",
            sa.column("name", sa.String),
            sa.column("legal_name", sa.String),
            sa.column("abbreviation", sa.String),
            sa.column("default_certificate_prefix", sa.String),
            sa.column("notes", sa.Text),
            sa.column("document_configuration", sa.JSON),
            sa.column("is_enabled", sa.Boolean),
            sa.column("is_active", sa.Boolean),
            sa.column("created_at", sa.DateTime(timezone=True)),
            sa.column("updated_at", sa.DateTime(timezone=True)),
        ),
        [
            {
                "name": "CAPYMET",
                "legal_name": None,
                "abbreviation": "CAPYMET",
                "default_certificate_prefix": "CMVG",
                "notes": "Empresa vinculada institucional inicial.",
                "document_configuration": {},
                "is_enabled": True,
                "is_active": True,
                "created_at": now,
                "updated_at": now,
            },
            {
                "name": "BESS",
                "legal_name": None,
                "abbreviation": "BESS",
                "default_certificate_prefix": "BESS",
                "notes": "Empresa vinculada institucional inicial.",
                "document_configuration": {},
                "is_enabled": True,
                "is_active": True,
                "created_at": now,
                "updated_at": now,
            },
        ],
    )

    op.create_table(
        "institutional_folio_sequences",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("document_type", sa.String(length=40), nullable=False),
        sa.Column("prefix", sa.String(length=20), nullable=False),
        sa.Column("year", sa.Integer(), nullable=False),
        sa.Column("next_value", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "document_type",
            "prefix",
            "year",
            name="uq_institutional_folio_sequence_scope",
        ),
    )
    for column in ("document_type", "prefix", "year"):
        op.create_index(
            f"ix_institutional_folio_sequences_{column}",
            "institutional_folio_sequences",
            [column],
        )

    op.add_column("catalog_items", sa.Column("service_type", sa.String(length=20)))
    op.add_column("catalog_items", sa.Column("linked_company_id", sa.Integer()))
    op.add_column(
        "catalog_items", sa.Column("linked_certificate_prefix", sa.String(length=12))
    )
    op.create_foreign_key(
        "fk_catalog_items_linked_company_id",
        "catalog_items",
        "linked_companies",
        ["linked_company_id"],
        ["id"],
    )
    op.create_index("ix_catalog_items_service_type", "catalog_items", ["service_type"])
    op.create_index(
        "ix_catalog_items_linked_company_id", "catalog_items", ["linked_company_id"]
    )
    op.execute(
        """
        UPDATE catalog_items
        SET service_type = CASE calibration_scope
            WHEN 'accredited_iso_17025' THEN 'accredited'
            WHEN 'traceable' THEN 'traceable'
            WHEN 'accredited_linked_lab' THEN 'linked'
            ELSE NULL
        END
        WHERE item_type = 'service'
        """
    )

    op.add_column("service_order_items", sa.Column("service_snapshot", sa.JSON()))
    op.add_column("equipment", sa.Column("service_type_snapshot", sa.String(length=20)))
    op.add_column("equipment", sa.Column("linked_company_id", sa.Integer()))
    op.add_column(
        "equipment", sa.Column("linked_company_name_snapshot", sa.String(length=180))
    )
    op.add_column(
        "equipment", sa.Column("certificate_prefix_snapshot", sa.String(length=12))
    )
    op.create_foreign_key(
        "fk_equipment_linked_company_id",
        "equipment",
        "linked_companies",
        ["linked_company_id"],
        ["id"],
    )
    op.create_index(
        "ix_equipment_service_type_snapshot", "equipment", ["service_type_snapshot"]
    )
    op.create_index(
        "ix_equipment_linked_company_id", "equipment", ["linked_company_id"]
    )

    op.add_column(
        "quotation_service_change_requests",
        sa.Column("result_snapshot_id", sa.Integer()),
    )
    op.add_column(
        "quotation_service_change_requests",
        sa.Column("service_order_folio_snapshot", sa.String(length=40)),
    )
    op.add_column(
        "quotation_service_change_requests",
        sa.Column("base_quotation_snapshot", sa.JSON()),
    )
    op.add_column(
        "quotation_service_change_requests",
        sa.Column("delta_snapshot", sa.JSON()),
    )
    op.add_column(
        "quotation_service_change_requests",
        sa.Column("rebuild_audit_snapshot", sa.JSON()),
    )
    op.create_foreign_key(
        "fk_quotation_unlock_result_snapshot_id",
        "quotation_service_change_requests",
        "quotation_snapshots",
        ["result_snapshot_id"],
        ["id"],
        ondelete="RESTRICT",
    )
    op.create_index(
        "ix_quotation_service_change_requests_result_snapshot_id",
        "quotation_service_change_requests",
        ["result_snapshot_id"],
    )
    op.execute(
        """
        UPDATE quotation_service_change_requests AS request
        SET service_order_folio_snapshot = service_order.folio
        FROM service_orders AS service_order
        WHERE request.service_order_id = service_order.id
        """
    )
    for name in (
        "quotation_item_id",
        "current_catalog_item_id",
        "requested_catalog_item_id",
        "service_order_id",
    ):
        op.alter_column(
            "quotation_service_change_requests",
            name,
            existing_type=sa.Integer(),
            nullable=True,
        )
    op.drop_constraint(
        "quotation_service_change_requests_service_order_id_fkey",
        "quotation_service_change_requests",
        type_="foreignkey",
    )
    op.create_foreign_key(
        "fk_quotation_unlock_service_order_id",
        "quotation_service_change_requests",
        "service_orders",
        ["service_order_id"],
        ["id"],
        ondelete="SET NULL",
    )


def downgrade() -> None:
    op.drop_constraint(
        "fk_quotation_unlock_service_order_id",
        "quotation_service_change_requests",
        type_="foreignkey",
    )
    op.create_foreign_key(
        "quotation_service_change_requests_service_order_id_fkey",
        "quotation_service_change_requests",
        "service_orders",
        ["service_order_id"],
        ["id"],
        ondelete="RESTRICT",
    )
    for name in (
        "service_order_id",
        "requested_catalog_item_id",
        "current_catalog_item_id",
        "quotation_item_id",
    ):
        op.alter_column(
            "quotation_service_change_requests",
            name,
            existing_type=sa.Integer(),
            nullable=False,
        )
    op.drop_index(
        "ix_quotation_service_change_requests_result_snapshot_id",
        table_name="quotation_service_change_requests",
    )
    op.drop_constraint(
        "fk_quotation_unlock_result_snapshot_id",
        "quotation_service_change_requests",
        type_="foreignkey",
    )
    for column in (
        "rebuild_audit_snapshot",
        "delta_snapshot",
        "base_quotation_snapshot",
        "service_order_folio_snapshot",
        "result_snapshot_id",
    ):
        op.drop_column("quotation_service_change_requests", column)
    op.drop_index("ix_equipment_linked_company_id", table_name="equipment")
    op.drop_index("ix_equipment_service_type_snapshot", table_name="equipment")
    op.drop_constraint("fk_equipment_linked_company_id", "equipment", type_="foreignkey")
    for column in (
        "certificate_prefix_snapshot",
        "linked_company_name_snapshot",
        "linked_company_id",
        "service_type_snapshot",
    ):
        op.drop_column("equipment", column)
    op.drop_column("service_order_items", "service_snapshot")
    op.drop_index("ix_catalog_items_linked_company_id", table_name="catalog_items")
    op.drop_index("ix_catalog_items_service_type", table_name="catalog_items")
    op.drop_constraint(
        "fk_catalog_items_linked_company_id", "catalog_items", type_="foreignkey"
    )
    for column in (
        "linked_certificate_prefix",
        "linked_company_id",
        "service_type",
    ):
        op.drop_column("catalog_items", column)
    op.drop_table("institutional_folio_sequences")
    op.drop_table("linked_companies")
