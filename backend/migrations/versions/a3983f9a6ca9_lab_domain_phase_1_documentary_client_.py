"""lab domain phase 1 documentary client template ticket and client lifecycle

Revision ID: a3983f9a6ca9
Revises: ab31cd42ef53
Create Date: 2026-08-31 21:20:31.592576
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'a3983f9a6ca9'
down_revision: Union[str, None] = 'ab31cd42ef53'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # --- LabClient: Fase 1E, desactivación lógica (nunca DELETE físico) ---
    op.add_column(
        "lab_clients",
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
    )
    op.add_column(
        "lab_clients", sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True)
    )
    op.add_column("lab_clients", sa.Column("deleted_by", sa.Integer(), nullable=True))
    # Sin índice explícito: SoftDeleteMixin.is_active (app/models/base.py) no
    # declara index=True (es el mismo mixin usado por FieldSheet, sin índice
    # tampoco ahí); mantenemos el modelo como única fuente de verdad para que
    # `alembic check` no diverja.

    # --- LabWorkOrderEquipment: Fase 1A, cliente documental por equipo ---
    # "order" (default): el documento hereda cliente/dirección/atención de la
    # OT. "different": snapshot propio congelado, con la FK como mera
    # procedencia (nunca la autoridad); un cambio posterior en LabClient no
    # debe alterar lo que ya quedó documentado en un equipo/FieldSheet.
    op.add_column(
        "lab_work_order_equipment",
        sa.Column(
            "certificate_client_mode",
            sa.String(20),
            nullable=False,
            server_default="order",
        ),
    )
    op.add_column(
        "lab_work_order_equipment", sa.Column("final_lab_client_id", sa.Integer(), nullable=True)
    )
    op.add_column(
        "lab_work_order_equipment",
        sa.Column("final_client_company_snapshot", sa.String(255), nullable=True),
    )
    op.add_column(
        "lab_work_order_equipment",
        sa.Column("final_client_address_snapshot", sa.Text(), nullable=True),
    )
    op.add_column(
        "lab_work_order_equipment",
        sa.Column("final_client_attention_snapshot", sa.String(180), nullable=True),
    )
    op.create_foreign_key(
        "fk_lab_equipment_final_lab_client_id",
        "lab_work_order_equipment",
        "lab_clients",
        ["final_lab_client_id"],
        ["id"],
        ondelete="RESTRICT",
    )
    op.create_index(
        "ix_lab_work_order_equipment_final_lab_client_id",
        "lab_work_order_equipment",
        ["final_lab_client_id"],
    )
    op.create_check_constraint(
        "ck_lab_equipment_certificate_client_mode",
        "lab_work_order_equipment",
        "certificate_client_mode IN ('order', 'different')",
    )
    op.create_check_constraint(
        "ck_lab_equipment_certificate_client_snapshot",
        "lab_work_order_equipment",
        "(certificate_client_mode = 'order' AND final_client_company_snapshot IS NULL) "
        "OR (certificate_client_mode = 'different' AND final_client_company_snapshot IS NOT NULL "
        "AND final_client_company_snapshot <> '')",
    )
    op.create_check_constraint(
        "ck_lab_equipment_certificate_client_provenance",
        "lab_work_order_equipment",
        "certificate_client_mode = 'different' OR final_lab_client_id IS NULL",
    )

    # --- OperationalTicket: Fase 1F, nuevo tipo (misma tabla, sin tabla nueva) ---
    op.drop_constraint("ck_operational_ticket_type", "operational_tickets", type_="check")
    op.create_check_constraint(
        "ck_operational_ticket_type",
        "operational_tickets",
        "type IN ('reopen_work_order', 'manual_myc_folio', 'linked_folio', "
        "'partial_close', 'certificate_folio_block', 'field_sheet_template_request')",
    )

    # --- LabWorkOrder: Fase 1G, estados preparatorios (backward-compatible) ---
    # 'received_signed', 'in_progress' y 'ready_to_close' quedan reservados
    # para Fase 2/3 (mover la firma a la recepción). Ningún servicio de esta
    # fase asigna estos valores todavía; el flujo actual
    # draft -> ready_for_signatures -> completed/partially_closed/cancelled
    # sigue siendo el único que realmente ocurre.
    op.drop_constraint("ck_lab_work_order_status", "lab_work_orders", type_="check")
    op.create_check_constraint(
        "ck_lab_work_order_status",
        "lab_work_orders",
        "status IN ('draft', 'received_signed', 'in_progress', 'ready_for_signatures', "
        "'ready_to_close', 'completed', 'partially_closed', 'cancelled')",
    )


def downgrade() -> None:
    # ADVERTENCIA: estos create_check_constraint validan las filas existentes
    # por defecto (Postgres). Si Fase 2/3 ya llegó a producir alguna fila con
    # 'received_signed'/'in_progress'/'ready_to_close' o algún ticket
    # 'field_sheet_template_request', este downgrade FALLARÁ explícitamente en
    # vez de truncar/perder ese dato en silencio -- hay que resolver esas filas
    # manualmente (o aceptar que no se puede bajar la revisión) antes de continuar.
    op.drop_constraint("ck_lab_work_order_status", "lab_work_orders", type_="check")
    op.create_check_constraint(
        "ck_lab_work_order_status",
        "lab_work_orders",
        "status IN ('draft', 'ready_for_signatures', 'completed', 'partially_closed', 'cancelled')",
    )

    op.drop_constraint("ck_operational_ticket_type", "operational_tickets", type_="check")
    op.create_check_constraint(
        "ck_operational_ticket_type",
        "operational_tickets",
        "type IN ('reopen_work_order', 'manual_myc_folio', 'linked_folio', "
        "'partial_close', 'certificate_folio_block')",
    )

    op.drop_constraint(
        "ck_lab_equipment_certificate_client_provenance",
        "lab_work_order_equipment",
        type_="check",
    )
    op.drop_constraint(
        "ck_lab_equipment_certificate_client_snapshot", "lab_work_order_equipment", type_="check"
    )
    op.drop_constraint(
        "ck_lab_equipment_certificate_client_mode", "lab_work_order_equipment", type_="check"
    )
    op.drop_index(
        "ix_lab_work_order_equipment_final_lab_client_id",
        table_name="lab_work_order_equipment",
    )
    op.drop_constraint(
        "fk_lab_equipment_final_lab_client_id", "lab_work_order_equipment", type_="foreignkey"
    )
    op.drop_column("lab_work_order_equipment", "final_client_attention_snapshot")
    op.drop_column("lab_work_order_equipment", "final_client_address_snapshot")
    op.drop_column("lab_work_order_equipment", "final_client_company_snapshot")
    op.drop_column("lab_work_order_equipment", "final_lab_client_id")
    op.drop_column("lab_work_order_equipment", "certificate_client_mode")

    op.drop_column("lab_clients", "deleted_by")
    op.drop_column("lab_clients", "deleted_at")
    op.drop_column("lab_clients", "is_active")
