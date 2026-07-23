"""normalize operational calibration scope keys

Revision ID: fe6f7a8b9c0d
Revises: fd5e6f7a8b9c
Create Date: 2026-07-22 12:00:00.000000
"""

from alembic import op
from sqlalchemy import text


revision = "fe6f7a8b9c0d"
down_revision = "fd5e6f7a8b9c"
branch_labels = None
depends_on = None


OPERATIONAL_TABLES = (
    "catalog_items",
    "quotation_items",
    "service_order_items",
    "equipment",
)

TECHNICAL_SCOPE_TABLES = (
    "document_interpretations",
    "technical_profiles",
)


def upgrade() -> None:
    connection = op.get_bind()
    special_sources = []
    for table_name in TECHNICAL_SCOPE_TABLES:
        count = connection.execute(
            text(
                f"SELECT count(*) FROM {table_name} "
                "WHERE calibration_scope = 'special'"
            )
        ).scalar_one()
        if count:
            special_sources.append(f"{table_name}={count}")
    if special_sources:
        raise RuntimeError(
            "No se puede normalizar calibration_scope='special' automáticamente; "
            "clasifique esos registros como accredited_iso_17025, traceable o "
            f"accredited_linked_lab antes de migrar ({', '.join(special_sources)})."
        )

    for table_name in OPERATIONAL_TABLES:
        op.execute(
            f"""
            UPDATE {table_name}
            SET calibration_scope = CASE calibration_scope
                WHEN 'Certificado / Certificate: L25-313' THEN 'accredited_iso_17025'
                WHEN 'accredited' THEN 'accredited_iso_17025'
                WHEN 'linked_lab' THEN 'accredited_linked_lab'
                ELSE calibration_scope
            END
            WHERE calibration_scope IN (
                'Certificado / Certificate: L25-313',
                'accredited',
                'linked_lab'
            )
            """
        )

    for table_name in TECHNICAL_SCOPE_TABLES:
        op.execute(
            f"""
            UPDATE {table_name}
            SET calibration_scope = CASE calibration_scope
                WHEN 'accredited' THEN 'accredited_iso_17025'
                WHEN 'linked_lab' THEN 'accredited_linked_lab'
                ELSE calibration_scope
            END
            WHERE calibration_scope IN ('accredited', 'linked_lab')
            """
        )


def downgrade() -> None:
    # La normalización consolida alias ambiguos y no puede revertirse sin
    # reintroducir valores que incumplen el contrato operacional vigente.
    pass
