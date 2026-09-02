"""lab work order cancel/restore and direct reopen

Cierre UX 2026-09: dos brechas de esquema, ambas requeridas por el mismo
pase de correcciones QA.

1) LabWorkOrder.previous_status: cancel_work_order ya no bloquea
   completed/partially_closed (Admin puede cancelar una OT cerrada), pero
   cancelar nunca debe equivaler a reabrir. Sin un historial de estados
   genérico, este campo es el mecanismo mínimo para que restore_work_order
   devuelva la OT a su estado exacto anterior, no a draft/in_progress como
   si fuera una reapertura técnica.

2) LabWorkOrderRevision.reopen_ticket_id pasa a nullable: un Admin con
   work_orders.reopen + la política correspondiente puede reabrir una OT
   cerrada directamente (sin crear un ticket artificial sólo para poder
   aprobarlo él mismo). El snapshot histórico se sigue generando igual
   (LabWorkOrderRevision), sólo deja de exigir un ticket que en ese camino
   nunca existió.

Revision ID: b0b560e714db
Revises: 5e58473f1be6
Create Date: 2026-09-02 00:00:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "b0b560e714db"
down_revision: Union[str, None] = "5e58473f1be6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "lab_work_orders", sa.Column("previous_status", sa.String(length=30), nullable=True)
    )
    op.alter_column(
        "lab_work_order_revisions", "reopen_ticket_id", existing_type=sa.Integer(), nullable=True,
    )


def downgrade() -> None:
    # Una reapertura directa (sin ticket) habrá dejado reopen_ticket_id NULL
    # en algunas revisiones -- el downgrade sólo es seguro si ninguna existe
    # todavía en este entorno. Igual que el downgrade de d7c297902425, esto
    # es un genuino conflicto de datos si ya se usó la reapertura directa,
    # no un bug de la migración: resolver esas filas antes de bajar.
    op.alter_column(
        "lab_work_order_revisions", "reopen_ticket_id", existing_type=sa.Integer(), nullable=False,
    )
    op.drop_column("lab_work_orders", "previous_status")
