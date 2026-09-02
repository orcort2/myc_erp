"""lab client structured address, drop equipment intake scope, field sheet reopen ticket

Cierre de pendientes UX 2026-09: tres brechas de esquema separadas, todas
requeridas por el mismo pase.

1) LabClient gana postal_code/city/state estructurados. LabWorkOrder (el
   receptor de la OT) ya modela estos 3 campos por separado, pero LabClient
   sólo tenía `address` libre -- nunca se podían autorrellenar. No se agrega
   calle/número/colonia porque el dominio actual tampoco los modela así en
   LabWorkOrder; estos 3 son exactamente los que ya existen del lado OT.
   No participan del índice único normalizado (la identidad de dedup sigue
   siendo company+address+attention).

2) Se revierte `range_or_capacity` de LabWorkOrderEquipment (agregado en
   d7c297902425). No es un dato de control documental de alta de equipo --
   es dato operativo/metrológico que se captura en la FieldSheet cuando la
   plantilla lo requiere (ya existe ahí como campo "scope" de
   EquipmentDataBlock). `model` se conserva: es identidad legítima distinta.

3) Nuevo tipo de ticket `field_sheet_reopen` sobre la misma tabla
   operational_tickets (sin tabla nueva, reutiliza la columna equipment_id
   ya existente): solicitud auditable de desbloqueo/reapertura de UNA
   FieldSheet/equipo completed mientras la OT sigue abierta
   (in_progress/ready_to_close), sin tocar el estado global de la OT. Sigue
   siendo distinto del ticket reopen_work_order existente (que sí reabre la
   OT completa cuando ya está completed/partially_closed) -- ambos casos se
   resuelven con la infraestructura de OperationalTicket ya existente, sin
   una segunda política de seguridad.

Revision ID: 5e58473f1be6
Revises: d7c297902425
Create Date: 2026-09-01 00:00:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "5e58473f1be6"
down_revision: Union[str, None] = "d7c297902425"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("lab_clients", sa.Column("postal_code", sa.String(length=20), nullable=True))
    op.add_column("lab_clients", sa.Column("city", sa.String(length=120), nullable=True))
    op.add_column("lab_clients", sa.Column("state", sa.String(length=120), nullable=True))

    op.drop_column("lab_work_order_equipment", "range_or_capacity")

    op.drop_constraint("ck_operational_ticket_type", "operational_tickets", type_="check")
    op.create_check_constraint(
        "ck_operational_ticket_type",
        "operational_tickets",
        "type IN ('reopen_work_order', 'manual_myc_folio', 'linked_folio', "
        "'partial_close', 'certificate_folio_block', 'field_sheet_template_request', "
        "'field_sheet_reopen')",
    )


def downgrade() -> None:
    op.drop_constraint("ck_operational_ticket_type", "operational_tickets", type_="check")
    op.create_check_constraint(
        "ck_operational_ticket_type",
        "operational_tickets",
        "type IN ('reopen_work_order', 'manual_myc_folio', 'linked_folio', "
        "'partial_close', 'certificate_folio_block', 'field_sheet_template_request')",
    )

    op.add_column(
        "lab_work_order_equipment",
        sa.Column("range_or_capacity", sa.String(length=180), nullable=True),
    )

    op.drop_column("lab_clients", "state")
    op.drop_column("lab_clients", "city")
    op.drop_column("lab_clients", "postal_code")
