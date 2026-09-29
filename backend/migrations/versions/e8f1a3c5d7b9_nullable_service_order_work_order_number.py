"""Allow ETS without productive OT folio (calibration executed in MYC Mobile).

service_orders.work_order_number becomes INT UNIQUE NULLABLE. Existing rows
are not modified, backfilled or renumbered. PostgreSQL allows several NULL
values under the existing unique index ix_service_orders_work_order_number.
"""

from alembic import op
import sqlalchemy as sa

revision = "e8f1a3c5d7b9"
down_revision = "d7e9a1c3b5f0"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("service_orders") as batch:
        batch.alter_column(
            "work_order_number",
            existing_type=sa.Integer(),
            nullable=True,
        )


def downgrade() -> None:
    # Never invent OT folios to restore NOT NULL: Mobile calibration ETS must be
    # resolved explicitly before downgrading.
    pending = op.get_bind().execute(
        sa.text("SELECT COUNT(*) FROM service_orders WHERE work_order_number IS NULL")
    ).scalar()
    if pending:
        raise RuntimeError(
            f"No se puede revertir: {pending} ETS sin folio OT ERP (calibración MYC Mobile). "
            "Resuélvalos explícitamente; esta migración no asigna folios ficticios."
        )
    with op.batch_alter_table("service_orders") as batch:
        batch.alter_column(
            "work_order_number",
            existing_type=sa.Integer(),
            nullable=False,
        )
