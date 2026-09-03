"""add lab work order deliveries (exhibitions/items/final receipt)

Revision ID: c2d4e6f8a0b1
Revises: 9f3a2c7d1e84

Reemplaza in-place la primera versión WIP de este checkpoint (nunca se
aplicó fuera de esta rama) con el esquema final: la entrega física ahora
vive a nivel de grupo/cohorte (root_work_order_id) como una serie de
"exhibiciones" (LabWorkOrderDelivery), cada una con sus equipos entregados
(LabDeliveryItem) y, cuando el grupo queda completo, un resumen final
versionado (LabDeliveryGroupReceipt). También agrega el tipo de ticket
'partial_delivery' usado para autorizar entregas parciales excepcionales.
"""

from alembic import op
import sqlalchemy as sa


revision = "c2d4e6f8a0b1"
down_revision = "9f3a2c7d1e84"
branch_labels = None
depends_on = None


_PREVIOUS_TICKET_TYPES = (
    "reopen_work_order",
    "manual_myc_folio",
    "linked_folio",
    "partial_close",
    "certificate_folio_block",
    "field_sheet_template_request",
    "field_sheet_reopen",
    "reception_date_change",
)
_CURRENT_TICKET_TYPES = (*_PREVIOUS_TICKET_TYPES, "partial_delivery")


def _ticket_type_constraint(types: tuple[str, ...]) -> str:
    values = ", ".join(f"'{item}'" for item in types)
    return f"type IN ({values})"


def upgrade() -> None:
    op.alter_column("lab_work_orders", "departure_date", existing_type=sa.Date(), nullable=True)
    op.alter_column("lab_work_order_group_requests", "departure_date", existing_type=sa.Date(), nullable=True)

    op.create_table(
        "lab_work_order_deliveries",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("root_work_order_id", sa.Integer(), nullable=False),
        sa.Column("exhibition_number", sa.Integer(), nullable=False),
        sa.Column("delivery_type", sa.String(length=20), nullable=False),
        sa.Column("delivery_method", sa.String(length=20), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("partial_delivery_ticket_id", sa.Integer(), nullable=True),
        sa.Column("delivered_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("delivered_by_user_id", sa.Integer(), nullable=False),
        sa.Column("delivered_by_signature_data_url", sa.Text(), nullable=False),
        sa.Column("recipient_name", sa.String(length=180), nullable=False),
        sa.Column("recipient_signature_data_url", sa.Text(), nullable=False),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("voided_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("voided_by_user_id", sa.Integer(), nullable=True),
        sa.Column("void_reason", sa.Text(), nullable=True),
        sa.Column("voucher_pdf", sa.LargeBinary(), nullable=True),
        sa.Column("voucher_pdf_sha256", sa.String(length=64), nullable=True),
        sa.Column("voucher_pdf_generated_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("status IN ('completed', 'voided')", name="ck_lab_work_order_delivery_status"),
        sa.CheckConstraint("delivery_type IN ('full', 'partial')", name="ck_lab_work_order_delivery_type"),
        sa.CheckConstraint(
            "delivery_method IN ('direct', 'client_pickup')", name="ck_lab_work_order_delivery_method"
        ),
        sa.CheckConstraint("exhibition_number >= 1", name="ck_lab_work_order_delivery_exhibition_number"),
        sa.ForeignKeyConstraint(["root_work_order_id"], ["lab_work_orders.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["delivered_by_user_id"], ["users.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["voided_by_user_id"], ["users.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(
            ["partial_delivery_ticket_id"], ["operational_tickets.id"], ondelete="RESTRICT"
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "root_work_order_id", "exhibition_number", name="uq_lab_work_order_delivery_exhibition"
        ),
    )
    op.create_index("ix_lab_work_order_deliveries_id", "lab_work_order_deliveries", ["id"])
    op.create_index(
        "ix_lab_work_order_deliveries_root_work_order_id",
        "lab_work_order_deliveries",
        ["root_work_order_id"],
    )
    op.create_index(
        "ix_lab_work_order_deliveries_delivered_by_user_id",
        "lab_work_order_deliveries",
        ["delivered_by_user_id"],
    )
    op.create_index(
        "ix_lab_work_order_deliveries_partial_delivery_ticket_id",
        "lab_work_order_deliveries",
        ["partial_delivery_ticket_id"],
    )
    op.create_index("ix_lab_work_order_deliveries_status", "lab_work_order_deliveries", ["status"])

    op.create_table(
        "lab_delivery_items",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("delivery_id", sa.Integer(), nullable=False),
        sa.Column("work_order_id", sa.Integer(), nullable=False),
        sa.Column("equipment_id", sa.Integer(), nullable=False),
        sa.Column("position_snapshot", sa.Integer(), nullable=True),
        sa.Column("instrument_snapshot", sa.String(length=255), nullable=False),
        sa.Column("brand_snapshot", sa.String(length=160), nullable=False),
        sa.Column("identification_snapshot", sa.String(length=160), nullable=False),
        sa.Column("serial_number_snapshot", sa.String(length=160), nullable=False),
        sa.Column("certificate_folio_snapshot", sa.String(length=160), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["delivery_id"], ["lab_work_order_deliveries.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["work_order_id"], ["lab_work_orders.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["equipment_id"], ["lab_work_order_equipment.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("delivery_id", "equipment_id", name="uq_lab_delivery_item_equipment"),
    )
    op.create_index("ix_lab_delivery_items_id", "lab_delivery_items", ["id"])
    op.create_index("ix_lab_delivery_items_delivery_id", "lab_delivery_items", ["delivery_id"])
    op.create_index("ix_lab_delivery_items_work_order_id", "lab_delivery_items", ["work_order_id"])
    op.create_index("ix_lab_delivery_items_equipment_id", "lab_delivery_items", ["equipment_id"])

    op.create_table(
        "lab_delivery_group_receipts",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("root_work_order_id", sa.Integer(), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("exhibitions_count", sa.Integer(), nullable=False),
        sa.Column("generated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("generated_by_user_id", sa.Integer(), nullable=False),
        sa.Column("superseded_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("pdf", sa.LargeBinary(), nullable=False),
        sa.Column("pdf_sha256", sa.String(length=64), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["root_work_order_id"], ["lab_work_orders.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["generated_by_user_id"], ["users.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("root_work_order_id", "version", name="uq_lab_delivery_group_receipt_version"),
    )
    op.create_index("ix_lab_delivery_group_receipts_id", "lab_delivery_group_receipts", ["id"])
    op.create_index(
        "ix_lab_delivery_group_receipts_root_work_order_id",
        "lab_delivery_group_receipts",
        ["root_work_order_id"],
    )

    op.drop_constraint("ck_operational_ticket_type", "operational_tickets", type_="check")
    op.create_check_constraint(
        "ck_operational_ticket_type",
        "operational_tickets",
        _ticket_type_constraint(_CURRENT_TICKET_TYPES),
    )


def downgrade() -> None:
    connection = op.get_bind()
    used = connection.scalar(
        sa.text("SELECT EXISTS (SELECT 1 FROM operational_tickets WHERE type = 'partial_delivery')")
    )
    if used:
        raise RuntimeError(
            "No se puede revertir c2d4e6f8a0b1: existen tickets partial_delivery; "
            "deben preservarse sin reinterpretar ni eliminar"
        )
    op.drop_constraint("ck_operational_ticket_type", "operational_tickets", type_="check")
    op.create_check_constraint(
        "ck_operational_ticket_type",
        "operational_tickets",
        _ticket_type_constraint(_PREVIOUS_TICKET_TYPES),
    )

    receipts = connection.scalar(sa.text("SELECT count(*) FROM lab_delivery_group_receipts"))
    if receipts:
        raise RuntimeError("No se puede revertir: existen resúmenes finales de entrega que deben conservarse")
    op.drop_table("lab_delivery_group_receipts")

    deliveries = connection.scalar(sa.text("SELECT count(*) FROM lab_work_order_deliveries"))
    if deliveries:
        raise RuntimeError("No se puede revertir: existen acuses de entrega LAB que deben conservarse")
    op.drop_table("lab_delivery_items")
    op.drop_table("lab_work_order_deliveries")

    legacy_nulls = connection.scalar(sa.text("SELECT count(*) FROM lab_work_orders WHERE departure_date IS NULL"))
    request_nulls = connection.scalar(sa.text("SELECT count(*) FROM lab_work_order_group_requests WHERE departure_date IS NULL"))
    if legacy_nulls or request_nulls:
        raise RuntimeError("No se puede revertir: existen OT o solicitudes sin fecha de salida")
    op.alter_column("lab_work_order_group_requests", "departure_date", existing_type=sa.Date(), nullable=False)
    op.alter_column("lab_work_orders", "departure_date", existing_type=sa.Date(), nullable=False)
