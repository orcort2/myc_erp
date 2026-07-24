"""freeze equipment certificate context

Revision ID: 8c2d4e6f7a9b
Revises: 7b1c213129ec
Create Date: 2026-07-23 16:00:00.000000
"""

from alembic import op
import sqlalchemy as sa


revision = "8c2d4e6f7a9b"
down_revision = "7b1c213129ec"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "service_order_items",
        sa.Column(
            "expected_certificate_master_id",
            sa.Integer(),
            nullable=True,
        ),
    )
    op.create_foreign_key(
        "fk_service_order_items_expected_certificate_master_id",
        "service_order_items",
        "controlled_documents",
        ["expected_certificate_master_id"],
        ["id"],
    )
    op.create_index(
        "ix_service_order_items_expected_certificate_master_id",
        "service_order_items",
        ["expected_certificate_master_id"],
        unique=False,
    )
    op.add_column(
        "equipment",
        sa.Column(
            "certificate_operational_context_snapshot",
            sa.JSON(),
            nullable=True,
        ),
    )

    # Historical rows are recovered only through stable foreign keys. A mutable
    # service name is deliberately never used as a migration or runtime key.
    op.execute(
        """
        UPDATE service_order_items AS soi
        SET expected_certificate_master_id =
            catalog_items.expected_certificate_master_id
        FROM catalog_items
        WHERE soi.catalog_item_id = catalog_items.id
          AND soi.expected_certificate_master_id IS NULL
        """
    )
    op.execute(
        """
        UPDATE service_order_items AS soi
        SET expected_certificate_master_id =
            catalog_items.expected_certificate_master_id
        FROM quotation_items
        JOIN catalog_items
          ON catalog_items.id = quotation_items.catalog_item_id
        WHERE soi.quotation_item_id = quotation_items.id
          AND soi.expected_certificate_master_id IS NULL
        """
    )
    op.execute(
        """
        UPDATE equipment
        SET certificate_operational_context_snapshot = json_build_object(
            'schema_version', 1,
            'calibration_scope', equipment.calibration_scope,
            'certificate_type',
                CASE equipment.calibration_scope
                    WHEN 'accredited_iso_17025' THEN 'acreditado'
                    WHEN 'accredited_linked_lab' THEN 'vinculado'
                    WHEN 'traceable' THEN 'trazable'
                    ELSE NULL
                END,
            'expected_certificate_master_id',
                COALESCE(
                    service_order_items.expected_certificate_master_id,
                    equipment.certificate_master_document_id
                ),
            'service_order_item_id', equipment.service_order_item_id,
            'source_catalog_item_id', service_order_items.catalog_item_id
        )
        FROM service_order_items
        WHERE equipment.service_order_item_id = service_order_items.id
          AND equipment.certificate_operational_context_snapshot IS NULL
        """
    )
    op.execute(
        """
        UPDATE equipment
        SET certificate_operational_context_snapshot = json_build_object(
            'schema_version', 1,
            'calibration_scope', equipment.calibration_scope,
            'certificate_type',
                CASE equipment.calibration_scope
                    WHEN 'accredited_iso_17025' THEN 'acreditado'
                    WHEN 'accredited_linked_lab' THEN 'vinculado'
                    WHEN 'traceable' THEN 'trazable'
                    ELSE NULL
                END,
            'expected_certificate_master_id',
                equipment.certificate_master_document_id,
            'service_order_item_id', equipment.service_order_item_id,
            'source_catalog_item_id', NULL
        )
        WHERE equipment.certificate_operational_context_snapshot IS NULL
        """
    )


def downgrade() -> None:
    op.drop_column(
        "equipment",
        "certificate_operational_context_snapshot",
    )
    op.drop_index(
        "ix_service_order_items_expected_certificate_master_id",
        table_name="service_order_items",
    )
    op.drop_constraint(
        "fk_service_order_items_expected_certificate_master_id",
        "service_order_items",
        type_="foreignkey",
    )
    op.drop_column(
        "service_order_items",
        "expected_certificate_master_id",
    )
