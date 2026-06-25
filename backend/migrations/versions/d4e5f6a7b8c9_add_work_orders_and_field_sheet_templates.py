"""add work order number and field sheet templates

Revision ID: d4e5f6a7b8c9
Revises: c3d4e5f6a7b8
Create Date: 2026-06-24 00:00:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op


revision: str = "d4e5f6a7b8c9"
down_revision: str | None = "c3d4e5f6a7b8"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "service_orders",
        sa.Column("work_order_number", sa.Integer(), nullable=True),
    )

    connection = op.get_bind()
    service_orders = sa.table(
        "service_orders",
        sa.column("id", sa.Integer()),
        sa.column("created_at", sa.DateTime(timezone=True)),
        sa.column("work_order_number", sa.Integer()),
    )
    rows = connection.execute(
        sa.select(service_orders.c.id)
        .order_by(service_orders.c.created_at.asc(), service_orders.c.id.asc())
    ).all()
    for offset, row in enumerate(rows, start=7001):
        connection.execute(
            service_orders.update()
            .where(service_orders.c.id == row.id)
            .values(work_order_number=offset)
        )

    op.alter_column("service_orders", "work_order_number", nullable=False)
    op.create_index(
        op.f("ix_service_orders_work_order_number"),
        "service_orders",
        ["work_order_number"],
        unique=True,
    )

    op.add_column(
        "field_sheets",
        sa.Column(
            "template_key",
            sa.String(length=40),
            nullable=False,
            server_default="general",
        ),
    )
    op.add_column("field_sheets", sa.Column("work_order_number", sa.Integer(), nullable=True))
    op.add_column("field_sheets", sa.Column("calibration_place", sa.String(length=180), nullable=True))
    op.add_column("field_sheets", sa.Column("reception_date", sa.Date(), nullable=True))
    op.add_column("field_sheets", sa.Column("calibration_date", sa.Date(), nullable=True))
    op.add_column("field_sheets", sa.Column("next_calibration_date", sa.Date(), nullable=True))
    op.add_column("field_sheets", sa.Column("environment_humidity_start", sa.String(length=40), nullable=True))
    op.add_column("field_sheets", sa.Column("environment_humidity_end", sa.String(length=40), nullable=True))
    op.add_column("field_sheets", sa.Column("environment_temperature_start", sa.String(length=40), nullable=True))
    op.add_column("field_sheets", sa.Column("environment_temperature_end", sa.String(length=40), nullable=True))
    op.add_column("field_sheets", sa.Column("equipment_general_condition", sa.Boolean(), nullable=True))
    op.add_column(
        "field_sheets",
        sa.Column(
            "consider_equipment_deviations",
            sa.Boolean(),
            nullable=False,
            server_default=sa.false(),
        ),
    )
    op.add_column("field_sheets", sa.Column("units", sa.String(length=80), nullable=True))
    op.add_column("field_sheets", sa.Column("calibrated_by", sa.String(length=180), nullable=True))
    op.add_column("field_sheets", sa.Column("reviewed_by", sa.String(length=180), nullable=True))
    op.add_column("field_sheets", sa.Column("report_made_by", sa.String(length=180), nullable=True))
    op.add_column("field_sheets", sa.Column("purchase_order_or_quotation", sa.String(length=180), nullable=True))

    op.create_index(op.f("ix_field_sheets_template_key"), "field_sheets", ["template_key"], unique=False)
    op.create_index(op.f("ix_field_sheets_work_order_number"), "field_sheets", ["work_order_number"], unique=False)

    field_sheets = sa.table(
        "field_sheets",
        sa.column("id", sa.Integer()),
        sa.column("equipment_id", sa.Integer()),
        sa.column("template_key", sa.String()),
        sa.column("work_order_number", sa.Integer()),
        sa.column("purchase_order_or_quotation", sa.String()),
    )
    equipment = sa.table(
        "equipment",
        sa.column("id", sa.Integer()),
        sa.column("service_order_id", sa.Integer()),
    )
    service_orders_ref = sa.table(
        "service_orders",
        sa.column("id", sa.Integer()),
        sa.column("work_order_number", sa.Integer()),
        sa.column("folio", sa.String()),
    )

    rows = connection.execute(
        sa.select(
            field_sheets.c.id,
            service_orders_ref.c.work_order_number,
            service_orders_ref.c.folio,
        )
        .select_from(
            field_sheets.join(equipment, equipment.c.id == field_sheets.c.equipment_id).join(
                service_orders_ref, service_orders_ref.c.id == equipment.c.service_order_id
            )
        )
    ).all()
    for row in rows:
        connection.execute(
            field_sheets.update()
            .where(field_sheets.c.id == row.id)
            .values(work_order_number=row.work_order_number, purchase_order_or_quotation=row.folio)
        )

    op.create_table(
        "field_sheet_results",
        sa.Column("field_sheet_id", sa.Integer(), nullable=False),
        sa.Column("section_key", sa.String(length=80), nullable=False),
        sa.Column("row_number", sa.Integer(), nullable=False),
        sa.Column("pattern_value", sa.String(length=180), nullable=True),
        sa.Column("ibc_value_1", sa.String(length=180), nullable=True),
        sa.Column("ibc_value_2", sa.String(length=180), nullable=True),
        sa.Column("ibc_value_3", sa.String(length=180), nullable=True),
        sa.Column("unit", sa.String(length=80), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["field_sheet_id"], ["field_sheets.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("field_sheet_id", "section_key", "row_number", name="uq_field_sheet_results_row"),
    )
    op.create_index(op.f("ix_field_sheet_results_id"), "field_sheet_results", ["id"], unique=False)
    op.create_index(op.f("ix_field_sheet_results_field_sheet_id"), "field_sheet_results", ["field_sheet_id"], unique=False)
    op.create_index(op.f("ix_field_sheet_results_section_key"), "field_sheet_results", ["section_key"], unique=False)

    field_sheet_results = sa.table(
        "field_sheet_results",
        sa.column("field_sheet_id", sa.Integer()),
        sa.column("section_key", sa.String()),
        sa.column("row_number", sa.Integer()),
    )
    field_sheet_rows = connection.execute(
        sa.select(field_sheets.c.id, field_sheets.c.template_key).order_by(field_sheets.c.id.asc())
    ).all()
    for field_sheet_row in field_sheet_rows:
        sections = [("main", 10)]
        if field_sheet_row.template_key == "electrica":
            sections = [
                ("main", 5),
                ("page2_a", 5),
                ("page2_b", 5),
                ("page2_c", 5),
                ("page2_d", 5),
                ("page2_e", 5),
            ]
        for section_key, total_rows in sections:
            for row_number in range(1, total_rows + 1):
                connection.execute(
                    field_sheet_results.insert().values(
                        field_sheet_id=field_sheet_row.id,
                        section_key=section_key,
                        row_number=row_number,
                    )
                )

    op.alter_column("field_sheets", "template_key", server_default=None)
    op.alter_column("field_sheets", "consider_equipment_deviations", server_default=None)


def downgrade() -> None:
    op.drop_index(op.f("ix_field_sheet_results_section_key"), table_name="field_sheet_results")
    op.drop_index(op.f("ix_field_sheet_results_field_sheet_id"), table_name="field_sheet_results")
    op.drop_index(op.f("ix_field_sheet_results_id"), table_name="field_sheet_results")
    op.drop_table("field_sheet_results")

    op.drop_index(op.f("ix_field_sheets_work_order_number"), table_name="field_sheets")
    op.drop_index(op.f("ix_field_sheets_template_key"), table_name="field_sheets")
    op.drop_column("field_sheets", "purchase_order_or_quotation")
    op.drop_column("field_sheets", "report_made_by")
    op.drop_column("field_sheets", "reviewed_by")
    op.drop_column("field_sheets", "calibrated_by")
    op.drop_column("field_sheets", "units")
    op.drop_column("field_sheets", "consider_equipment_deviations")
    op.drop_column("field_sheets", "equipment_general_condition")
    op.drop_column("field_sheets", "environment_temperature_end")
    op.drop_column("field_sheets", "environment_temperature_start")
    op.drop_column("field_sheets", "environment_humidity_end")
    op.drop_column("field_sheets", "environment_humidity_start")
    op.drop_column("field_sheets", "next_calibration_date")
    op.drop_column("field_sheets", "calibration_date")
    op.drop_column("field_sheets", "reception_date")
    op.drop_column("field_sheets", "calibration_place")
    op.drop_column("field_sheets", "work_order_number")
    op.drop_column("field_sheets", "template_key")

    op.drop_index(op.f("ix_service_orders_work_order_number"), table_name="service_orders")
    op.drop_column("service_orders", "work_order_number")
