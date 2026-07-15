"""add invoice SAT catalog definitions

Revision ID: fb2c3d4e5f6
Revises: fa1b2c3d4e5
Create Date: 2026-07-14 13:00:00.000000
"""

from alembic import op
import sqlalchemy as sa


revision = "fb2c3d4e5f6"
down_revision = "fa1b2c3d4e5"
branch_labels = None
depends_on = None


CATALOGS = [
    ("tax_rates", "Tasas o cuotas", "c_TasaOCuota"),
    ("voucher_types", "Tipos de comprobante", "c_TipoDeComprobante"),
]


def upgrade() -> None:
    sat_catalogs = sa.table(
        "sat_catalogs",
        sa.column("code", sa.String),
        sa.column("name", sa.String),
        sa.column("description", sa.Text),
    )
    bind = op.get_bind()
    for code, name, description in CATALOGS:
        exists = bind.execute(sa.select(sat_catalogs.c.code).where(sat_catalogs.c.code == code)).scalar()
        if not exists:
            op.bulk_insert(sat_catalogs, [{"code": code, "name": name, "description": description}])


def downgrade() -> None:
    op.execute(sa.text("DELETE FROM sat_catalogs WHERE code IN ('tax_rates', 'voucher_types')"))
