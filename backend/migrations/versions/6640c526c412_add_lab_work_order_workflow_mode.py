"""add LabWorkOrder.workflow_mode (group / equipment_by_equipment)

Revision ID: 6640c526c412
Revises: 7088fa142cc2

Backend authority for the LAB work order's capture workflow. The field
work happens two ways in practice: "group" (register every equipment, then
sign reception, then capture FieldSheets) -- the only workflow that has ever
existed -- and the new "equipment_by_equipment" (register one equipment,
capture its FieldSheet completely, repeat, then a single final Cliente +
Técnico signature formalizes reception + FieldSheets + delivery at once).

This is backend-authoritative persistent state, not a Mobile-only flag: it
must survive app kill/logout/refresh/device change and drive how a work
order's state is reconstructed from scratch. Every historical/new row
defaults to "group" -- this migration never reinterprets or converts any
existing OT. The one real production OT that needs to become
"equipment_by_equipment" will be switched manually in a separate, later,
reviewed operation (see docs/architecture/LAB_WORK_ORDERS.md); this
migration only makes that switch possible, it never performs it.

Hangs off 7088fa142cc2; does not touch it or any earlier migration.
"""

from alembic import op
import sqlalchemy as sa


revision = "6640c526c412"
down_revision = "7088fa142cc2"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "lab_work_orders",
        sa.Column(
            "workflow_mode",
            sa.String(length=30),
            nullable=False,
            server_default="group",
        ),
    )
    op.create_check_constraint(
        "ck_lab_work_order_workflow_mode",
        "lab_work_orders",
        "workflow_mode IN ('group', 'equipment_by_equipment')",
    )


def downgrade() -> None:
    op.drop_constraint("ck_lab_work_order_workflow_mode", "lab_work_orders", type_="check")
    op.drop_column("lab_work_orders", "workflow_mode")
