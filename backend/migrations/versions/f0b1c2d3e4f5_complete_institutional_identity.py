"""complete the central MYC institutional identity

Revision ID: f0b1c2d3e4f5
Revises: f0a1b2c3d4e5
Create Date: 2026-07-13 14:30:00.000000
"""

from collections.abc import Sequence
import json

import sqlalchemy as sa
from alembic import op


revision: str = "f0b1c2d3e4f5"
down_revision: str | None = "f0a1b2c3d4e5"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


REAL_ADDRESS = "Av. Cristóbal Colón 6086, Int. 57, San Pedro Tlaquepaque, Jalisco, C.P. 45601"
REAL_PHONE = "33 5009 2659 · Cel. 33 1398 8169"
REAL_EMAIL = "contacto@mycmetrology.com.mx"


def upgrade() -> None:
    connection = op.get_bind()
    connection.execute(
        sa.text(
            """
            UPDATE institutional_configurations
               SET legal_name = 'METROLOGÍA Y SERVICIOS MYC',
                   document_code = 'FCA-30',
                   initial_revision = 'R1',
                   address = CASE
                       WHEN address IS NULL OR trim(address) = '' OR lower(address) LIKE '%simulad%'
                       THEN :address ELSE address END,
                   phone = CASE
                       WHEN phone IS NULL OR trim(phone) = '' OR phone = '33 0000 0000'
                       THEN :phone ELSE phone END,
                   email = CASE
                       WHEN email IS NULL OR trim(email) = '' OR lower(email) LIKE '%myc.test%'
                       THEN :email ELSE email END
             WHERE configuration_key = 'default'
            """
        ),
        {"address": REAL_ADDRESS, "phone": REAL_PHONE, "email": REAL_EMAIL},
    )

    # Historical snapshots remain immutable. Only incomplete snapshots created by
    # the engine-foundation migration are completed with the same institutional data.
    rows = connection.execute(
        sa.text(
            "SELECT id, institutional_snapshot_json FROM field_sheets "
            "WHERE institutional_snapshot_json IS NOT NULL"
        )
    ).mappings()
    for row in rows:
        snapshot = dict(row["institutional_snapshot_json"] or {})
        if snapshot.get("address") or snapshot.get("phone") or snapshot.get("email"):
            continue
        snapshot.update({"address": REAL_ADDRESS, "phone": REAL_PHONE, "email": REAL_EMAIL})
        connection.execute(
            sa.text("UPDATE field_sheets SET institutional_snapshot_json = :snapshot WHERE id = :id"),
            {"id": row["id"], "snapshot": json.dumps(snapshot, ensure_ascii=False)},
        )


def downgrade() -> None:
    # Institutional identity is user-editable and must not be erased on downgrade.
    pass
