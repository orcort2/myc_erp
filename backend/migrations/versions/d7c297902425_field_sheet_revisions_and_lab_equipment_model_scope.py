"""field sheet revisions and lab equipment model/scope

Fase 6: cierra dos brechas de esquema separadas pero ambas requeridas por
esta fase.

1) Modelo de revisión/versionado de FieldSheet LAB. La UniqueConstraint
   plana sobre lab_equipment_id impedía tener una segunda FieldSheet tras
   una reapertura que exige recaptura técnica -- la única forma de "liberar"
   el hueco era mutar la hoja completed de vuelta a draft, lo que habría
   sobrescrito el documento histórico. Se reemplaza por un índice único
   parcial (sólo una revisión is_current=True por equipo a la vez, mismo
   patrón que uq_field_sheets_active_equipment del lado productivo) más
   revision_number/is_current/supersedes_field_sheet_id para encadenar
   revisiones sin destruir ninguna. Todas las FieldSheets existentes
   (LAB y productivas) quedan como su propia revisión 1, vigente --
   server_default se encarga del backfill atómicamente, sin UPDATE aparte.

2) model y range_or_capacity ("scope" en capture_values/PDF) en
   LabWorkOrderEquipment: son identidad del equipo (mismo criterio que
   Equipment productivo, que ya los tiene como columnas propias), no datos
   de captura -- se agregan para que el prefill de FieldSheet no siga
   incompleto. location/minimum_division siguen sin tocarse: ya viven en
   FieldSheet porque son datos de la captura/servicio, no del equipo.

Revision ID: d7c297902425
Revises: b71d4a9f2c18
Create Date: 2026-09-01 00:00:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "d7c297902425"
down_revision: Union[str, None] = "b71d4a9f2c18"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "field_sheets",
        sa.Column("revision_number", sa.Integer(), nullable=False, server_default="1"),
    )
    op.add_column(
        "field_sheets",
        sa.Column("is_current", sa.Boolean(), nullable=False, server_default=sa.true()),
    )
    op.add_column(
        "field_sheets",
        sa.Column("supersedes_field_sheet_id", sa.Integer(), nullable=True),
    )
    op.create_foreign_key(
        "fk_field_sheets_supersedes_field_sheet_id",
        "field_sheets",
        "field_sheets",
        ["supersedes_field_sheet_id"],
        ["id"],
    )
    op.create_index(
        "ix_field_sheets_supersedes_field_sheet_id",
        "field_sheets",
        ["supersedes_field_sheet_id"],
    )

    op.drop_constraint("uq_field_sheets_lab_equipment_id", "field_sheets", type_="unique")
    op.create_index(
        "uq_field_sheets_current_lab_equipment",
        "field_sheets",
        ["lab_equipment_id"],
        unique=True,
        postgresql_where=sa.text("lab_equipment_id IS NOT NULL AND is_current IS TRUE"),
        sqlite_where=sa.text("lab_equipment_id IS NOT NULL AND is_current"),
    )

    op.add_column(
        "lab_work_order_equipment", sa.Column("model", sa.String(length=160), nullable=True)
    )
    op.add_column(
        "lab_work_order_equipment",
        sa.Column("range_or_capacity", sa.String(length=180), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("lab_work_order_equipment", "range_or_capacity")
    op.drop_column("lab_work_order_equipment", "model")

    op.drop_index("uq_field_sheets_current_lab_equipment", table_name="field_sheets")
    # Downgrade only round-trips cleanly while every lab_equipment_id still
    # has at most one FieldSheet (the common case right after upgrade, and
    # what CI/local validation exercises). If real revisions have since
    # accumulated in this environment, this unique constraint will reject
    # the downgrade -- that is a genuine data conflict, not a migration bug:
    # resolve which revisions to keep before downgrading past this point.
    op.create_unique_constraint(
        "uq_field_sheets_lab_equipment_id", "field_sheets", ["lab_equipment_id"]
    )

    op.drop_index("ix_field_sheets_supersedes_field_sheet_id", table_name="field_sheets")
    op.drop_constraint(
        "fk_field_sheets_supersedes_field_sheet_id", "field_sheets", type_="foreignkey"
    )
    op.drop_column("field_sheets", "supersedes_field_sheet_id")
    op.drop_column("field_sheets", "is_current")
    op.drop_column("field_sheets", "revision_number")
