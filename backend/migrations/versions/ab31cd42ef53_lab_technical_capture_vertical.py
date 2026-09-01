"""Evolve temporary LAB work orders with clients, field sheets and controlled folios.

Revision ID: ab31cd42ef53
Revises: e7a3c5d9f1b2
"""

from alembic import op
import sqlalchemy as sa


revision = "ab31cd42ef53"
down_revision = "e7a3c5d9f1b2"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "lab_clients",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("operator_client_id", sa.Integer(), nullable=True),
        sa.Column("company", sa.String(255), nullable=False),
        sa.Column("address", sa.Text(), nullable=False),
        sa.Column("attention", sa.String(180), nullable=False),
        sa.Column("normalized_company", sa.String(255), nullable=False),
        sa.Column("normalized_address", sa.Text(), nullable=False),
        sa.Column("normalized_attention", sa.String(180), nullable=False),
        sa.Column("created_by_user_id", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["operator_client_id"], ["clients.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["created_by_user_id"], ["users.id"], ondelete="RESTRICT"),
    )
    # Índice único funcional (no un UniqueConstraint plano): debe coincidir
    # exactamente con Index(...) en app/models/lab_client.py para que
    # `alembic check`/autogenerate no diverjan.
    op.create_index(
        "uq_lab_clients_tenant_normalized_identity",
        "lab_clients",
        [
            sa.text("COALESCE(operator_client_id, 0)"),
            "normalized_company",
            "normalized_address",
            "normalized_attention",
        ],
        unique=True,
    )
    op.create_index("ix_lab_clients_operator_client_id", "lab_clients", ["operator_client_id"])
    op.create_index("ix_lab_clients_company", "lab_clients", ["company"])
    op.create_index("ix_lab_clients_created_by_user_id", "lab_clients", ["created_by_user_id"])

    op.add_column("lab_work_order_group_requests", sa.Column("lab_client_id", sa.Integer()))
    op.create_foreign_key("fk_lab_group_requests_lab_client_id", "lab_work_order_group_requests", "lab_clients", ["lab_client_id"], ["id"], ondelete="RESTRICT")
    op.create_index("ix_lab_work_order_group_requests_lab_client_id", "lab_work_order_group_requests", ["lab_client_id"])

    op.add_column("lab_work_orders", sa.Column("lab_client_id", sa.Integer(), nullable=True))
    op.add_column("lab_work_orders", sa.Column("partially_closed_at", sa.DateTime(timezone=True)))
    op.add_column("lab_work_orders", sa.Column("partial_close_ticket_id", sa.Integer()))
    op.add_column("lab_work_orders", sa.Column("partial_close_pending_snapshot", sa.JSON()))
    op.add_column("lab_work_orders", sa.Column("cancelled_at", sa.DateTime(timezone=True)))
    op.add_column("lab_work_orders", sa.Column("cancelled_by_user_id", sa.Integer()))
    op.add_column("lab_work_orders", sa.Column("cancellation_reason", sa.Text()))
    op.create_foreign_key("fk_lab_work_orders_lab_client_id", "lab_work_orders", "lab_clients", ["lab_client_id"], ["id"], ondelete="RESTRICT")
    op.create_foreign_key("fk_lab_work_orders_cancelled_by_user_id", "lab_work_orders", "users", ["cancelled_by_user_id"], ["id"], ondelete="RESTRICT")
    op.create_index("ix_lab_work_orders_lab_client_id", "lab_work_orders", ["lab_client_id"])
    op.create_index("ix_lab_work_orders_cancelled_at", "lab_work_orders", ["cancelled_at"])
    op.drop_constraint("ck_lab_work_order_status", "lab_work_orders", type_="check")
    op.create_check_constraint(
        "ck_lab_work_order_status", "lab_work_orders",
        "status IN ('draft', 'ready_for_signatures', 'completed', 'partially_closed', 'cancelled')",
    )

    op.add_column("lab_work_order_equipment", sa.Column("service_type", sa.String(20)))
    op.add_column("lab_work_order_equipment", sa.Column("linked_company_id", sa.Integer()))
    op.add_column("lab_work_order_equipment", sa.Column("linked_company_name_snapshot", sa.String(255)))
    op.add_column("lab_work_order_equipment", sa.Column("linked_company_prefix_snapshot", sa.String(12)))
    op.add_column("lab_work_order_equipment", sa.Column("certificate_folio", sa.String(120)))
    op.add_column("lab_work_order_equipment", sa.Column("automatic_certificate_folio", sa.String(40)))
    op.add_column("lab_work_order_equipment", sa.Column("folio_status", sa.String(30), nullable=False, server_default="unassigned"))
    op.add_column("lab_work_order_equipment", sa.Column("folio_ticket_id", sa.Integer()))
    op.create_foreign_key("fk_lab_equipment_linked_company_id", "lab_work_order_equipment", "linked_companies", ["linked_company_id"], ["id"], ondelete="RESTRICT")
    op.create_index("ix_lab_work_order_equipment_service_type", "lab_work_order_equipment", ["service_type"])
    op.create_index("ix_lab_work_order_equipment_linked_company_id", "lab_work_order_equipment", ["linked_company_id"])
    op.create_index("ix_lab_work_order_equipment_certificate_folio", "lab_work_order_equipment", ["certificate_folio"], unique=True)
    op.create_index("ix_lab_work_order_equipment_automatic_certificate_folio", "lab_work_order_equipment", ["automatic_certificate_folio"])
    op.create_index("ix_lab_work_order_equipment_folio_status", "lab_work_order_equipment", ["folio_status"])

    op.drop_constraint("ck_operational_ticket_type", "operational_tickets", type_="check")
    op.drop_constraint("ck_operational_ticket_requested_signature_policy", "operational_tickets", type_="check")
    op.alter_column("operational_tickets", "work_order_id", nullable=True)
    op.alter_column("operational_tickets", "requested_signature_policy", nullable=True)
    op.add_column("operational_tickets", sa.Column("equipment_id", sa.Integer()))
    op.add_column("operational_tickets", sa.Column("operator_client_id", sa.Integer()))
    op.add_column("operational_tickets", sa.Column("linked_company_id", sa.Integer()))
    op.add_column("operational_tickets", sa.Column("conversation_id", sa.Integer()))
    op.add_column("operational_tickets", sa.Column("automatic_folio", sa.String(120)))
    op.add_column("operational_tickets", sa.Column("requested_folio", sa.String(120)))
    op.add_column("operational_tickets", sa.Column("authorized_folio", sa.String(120)))
    op.add_column("operational_tickets", sa.Column("accredited_quantity", sa.Integer()))
    op.add_column("operational_tickets", sa.Column("traceable_quantity", sa.Integer()))
    op.add_column("operational_tickets", sa.Column("resolution_snapshot", sa.JSON()))
    op.create_check_constraint(
        "ck_operational_ticket_type", "operational_tickets",
        "type IN ('reopen_work_order', 'manual_myc_folio', 'linked_folio', 'partial_close', 'certificate_folio_block')",
    )
    op.create_check_constraint(
        "ck_operational_ticket_requested_signature_policy", "operational_tickets",
        "requested_signature_policy IS NULL OR requested_signature_policy IN ('preserve', 'invalidate')",
    )
    op.create_check_constraint(
        "ck_operational_ticket_certificate_quantities", "operational_tickets",
        "(accredited_quantity IS NULL AND traceable_quantity IS NULL) OR "
        "(COALESCE(accredited_quantity, 0) >= 0 AND COALESCE(traceable_quantity, 0) >= 0 "
        "AND COALESCE(accredited_quantity, 0) + COALESCE(traceable_quantity, 0) BETWEEN 1 AND 100)",
    )
    op.create_foreign_key("fk_operational_tickets_equipment_id", "operational_tickets", "lab_work_order_equipment", ["equipment_id"], ["id"], ondelete="RESTRICT")
    op.create_foreign_key("fk_operational_tickets_operator_client_id", "operational_tickets", "clients", ["operator_client_id"], ["id"], ondelete="RESTRICT")
    op.create_foreign_key("fk_operational_tickets_linked_company_id", "operational_tickets", "linked_companies", ["linked_company_id"], ["id"], ondelete="RESTRICT")
    op.create_foreign_key("fk_operational_tickets_conversation_id", "operational_tickets", "communication_conversations", ["conversation_id"], ["id"], ondelete="SET NULL")
    op.create_index("ix_operational_tickets_equipment_id", "operational_tickets", ["equipment_id"])
    op.create_index("ix_operational_tickets_operator_client_id", "operational_tickets", ["operator_client_id"])

    op.create_foreign_key("fk_lab_work_orders_partial_close_ticket_id", "lab_work_orders", "operational_tickets", ["partial_close_ticket_id"], ["id"], ondelete="RESTRICT")
    op.create_index("ix_lab_work_orders_partial_close_ticket_id", "lab_work_orders", ["partial_close_ticket_id"])
    op.create_foreign_key("fk_lab_equipment_folio_ticket_id", "lab_work_order_equipment", "operational_tickets", ["folio_ticket_id"], ["id"], ondelete="RESTRICT")
    op.create_index("ix_lab_work_order_equipment_folio_ticket_id", "lab_work_order_equipment", ["folio_ticket_id"])

    op.alter_column("field_sheets", "equipment_id", nullable=True)
    op.add_column("field_sheets", sa.Column("lab_equipment_id", sa.Integer()))
    op.add_column("field_sheets", sa.Column("lab_signature_session_id", sa.Integer()))
    op.create_foreign_key("fk_field_sheets_lab_equipment_id", "field_sheets", "lab_work_order_equipment", ["lab_equipment_id"], ["id"], ondelete="CASCADE")
    op.create_foreign_key("fk_field_sheets_lab_signature_session_id", "field_sheets", "lab_work_order_signature_sessions", ["lab_signature_session_id"], ["id"], ondelete="RESTRICT")
    # El modelo declara lab_equipment_id con index=True (plain index, para
    # lookups) más un UniqueConstraint nombrado aparte en __table_args__: son
    # dos objetos de BD distintos y ambos deben existir para que
    # `alembic check`/autogenerate no diverjan.
    op.create_index("ix_field_sheets_lab_equipment_id", "field_sheets", ["lab_equipment_id"])
    op.create_unique_constraint("uq_field_sheets_lab_equipment_id", "field_sheets", ["lab_equipment_id"])
    op.create_index("ix_field_sheets_lab_signature_session_id", "field_sheets", ["lab_signature_session_id"])
    op.create_check_constraint(
        "ck_field_sheets_exactly_one_equipment_owner", "field_sheets",
        "(equipment_id IS NOT NULL AND lab_equipment_id IS NULL) OR "
        "(equipment_id IS NULL AND lab_equipment_id IS NOT NULL)",
    )


def downgrade() -> None:
    # Las hojas LAB no tienen propietario productivo válido al volver al
    # contrato anterior; se eliminan antes de restaurar equipment_id NOT NULL.
    op.execute("DELETE FROM field_sheets WHERE lab_equipment_id IS NOT NULL")
    op.drop_constraint("ck_field_sheets_exactly_one_equipment_owner", "field_sheets", type_="check")
    op.drop_index("ix_field_sheets_lab_signature_session_id", table_name="field_sheets")
    op.drop_constraint("uq_field_sheets_lab_equipment_id", "field_sheets", type_="unique")
    op.drop_index("ix_field_sheets_lab_equipment_id", table_name="field_sheets")
    op.drop_constraint("fk_field_sheets_lab_signature_session_id", "field_sheets", type_="foreignkey")
    op.drop_constraint("fk_field_sheets_lab_equipment_id", "field_sheets", type_="foreignkey")
    op.drop_column("field_sheets", "lab_signature_session_id")
    op.drop_column("field_sheets", "lab_equipment_id")
    op.alter_column("field_sheets", "equipment_id", nullable=False)

    op.drop_index("ix_lab_work_order_equipment_folio_ticket_id", table_name="lab_work_order_equipment")
    op.drop_constraint("fk_lab_equipment_folio_ticket_id", "lab_work_order_equipment", type_="foreignkey")
    op.drop_index("ix_lab_work_orders_partial_close_ticket_id", table_name="lab_work_orders")
    op.drop_constraint("fk_lab_work_orders_partial_close_ticket_id", "lab_work_orders", type_="foreignkey")

    op.drop_index("ix_operational_tickets_operator_client_id", table_name="operational_tickets")
    op.drop_index("ix_operational_tickets_equipment_id", table_name="operational_tickets")
    for name in (
        "fk_operational_tickets_conversation_id", "fk_operational_tickets_linked_company_id",
        "fk_operational_tickets_operator_client_id", "fk_operational_tickets_equipment_id",
    ):
        op.drop_constraint(name, "operational_tickets", type_="foreignkey")
    op.drop_constraint("ck_operational_ticket_certificate_quantities", "operational_tickets", type_="check")
    op.drop_constraint("ck_operational_ticket_requested_signature_policy", "operational_tickets", type_="check")
    op.drop_constraint("ck_operational_ticket_type", "operational_tickets", type_="check")
    for column in (
        "resolution_snapshot", "traceable_quantity", "accredited_quantity", "authorized_folio",
        "requested_folio", "automatic_folio", "conversation_id", "linked_company_id",
        "operator_client_id", "equipment_id",
    ):
        op.drop_column("operational_tickets", column)
    op.alter_column("operational_tickets", "requested_signature_policy", nullable=False)
    op.alter_column("operational_tickets", "work_order_id", nullable=False)
    op.create_check_constraint("ck_operational_ticket_requested_signature_policy", "operational_tickets", "requested_signature_policy IN ('preserve', 'invalidate')")
    op.create_check_constraint("ck_operational_ticket_type", "operational_tickets", "type IN ('reopen_work_order')")

    for index in (
        "ix_lab_work_order_equipment_folio_status", "ix_lab_work_order_equipment_automatic_certificate_folio",
        "ix_lab_work_order_equipment_certificate_folio", "ix_lab_work_order_equipment_linked_company_id",
        "ix_lab_work_order_equipment_service_type",
    ):
        op.drop_index(index, table_name="lab_work_order_equipment")
    op.drop_constraint("fk_lab_equipment_linked_company_id", "lab_work_order_equipment", type_="foreignkey")
    for column in (
        "folio_ticket_id", "folio_status", "automatic_certificate_folio", "certificate_folio",
        "linked_company_prefix_snapshot", "linked_company_name_snapshot", "linked_company_id", "service_type",
    ):
        op.drop_column("lab_work_order_equipment", column)

    # ADVERTENCIA: este downgrade es destructivo y puede fallar. Revierte el
    # check a solo 3 estados sin migrar filas 'partially_closed'/'cancelled'
    # existentes; si alguna lab_work_orders está en esos estados, este
    # create_check_constraint lanzará una violación de constraint. No se
    # limpia el dato de forma silenciosa: si necesitas bajar la revisión,
    # resuelve manualmente esas filas primero (o acepta que el downgrade
    # falle como señal explícita de que hay datos incompatibles).
    op.drop_constraint("ck_lab_work_order_status", "lab_work_orders", type_="check")
    op.create_check_constraint("ck_lab_work_order_status", "lab_work_orders", "status IN ('draft', 'ready_for_signatures', 'completed')")
    op.drop_index("ix_lab_work_orders_cancelled_at", table_name="lab_work_orders")
    op.drop_index("ix_lab_work_orders_lab_client_id", table_name="lab_work_orders")
    op.drop_constraint("fk_lab_work_orders_cancelled_by_user_id", "lab_work_orders", type_="foreignkey")
    op.drop_constraint("fk_lab_work_orders_lab_client_id", "lab_work_orders", type_="foreignkey")
    for column in (
        "cancellation_reason", "cancelled_by_user_id", "cancelled_at", "partial_close_pending_snapshot",
        "partial_close_ticket_id", "partially_closed_at", "lab_client_id",
    ):
        op.drop_column("lab_work_orders", column)

    op.drop_index("ix_lab_work_order_group_requests_lab_client_id", table_name="lab_work_order_group_requests")
    op.drop_constraint("fk_lab_group_requests_lab_client_id", "lab_work_order_group_requests", type_="foreignkey")
    op.drop_column("lab_work_order_group_requests", "lab_client_id")
    op.drop_table("lab_clients")
