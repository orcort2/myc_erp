"""soft-delete LabWorkOrderEquipment (tombstone), partial unique position

Revision ID: 7088fa142cc2
Revises: c91f47a8b2d0

Retirar un equipo de una OT LAB reabierta usaba DELETE físico
(LabWorkOrder.equipment con cascade="all, delete-orphan"). Eso hacía que
SQLAlchemy, al no declarar passive_deletes en LabWorkOrderEquipment.
field_sheets, emitiera un UPDATE field_sheets SET lab_equipment_id = NULL
antes de borrar la fila padre -- lo que revienta contra
ck_field_sheets_exactly_one_equipment_owner en cuanto el equipo tiene
cualquier FieldSheet histórica (completed o de una revisión anterior), con
un 500 crudo en PostgreSQL. Además, aunque no reventara, borrar la fila
destruiría el propietario de esa FieldSheet histórica -- exactamente lo que
la preservación documental del sistema prohíbe.

Esta migración adopta el patrón SoftDeleteMixin ya existente en el
repositorio (is_active/deleted_at/deleted_by) para lab_work_order_equipment:
retirar un equipo pasa a ser un tombstone -- la fila permanece, sus
FieldSheets siguen resolviendo lab_equipment_id sin tocarlas, y deja de
contar como parte de la composición operativa vigente (Mobile, firma,
cierre, PDF, máximo 10).

uq_lab_equipment_position (UniqueConstraint plana) se reemplaza por un
índice único parcial sobre equipo activo: un tombstone conserva su position
histórica sin bloquear que un equipo nuevo reutilice esa misma posición.

No toca ninguna otra tabla ni migración existente.
"""

from alembic import op
import sqlalchemy as sa


revision = "7088fa142cc2"
down_revision = "c91f47a8b2d0"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "lab_work_order_equipment",
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
    )
    op.add_column(
        "lab_work_order_equipment",
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "lab_work_order_equipment",
        sa.Column("deleted_by", sa.Integer(), nullable=True),
    )

    op.drop_constraint("uq_lab_equipment_position", "lab_work_order_equipment", type_="unique")
    op.create_index(
        "uq_lab_equipment_position_active",
        "lab_work_order_equipment",
        ["work_order_id", "position"],
        unique=True,
        postgresql_where=sa.text("is_active IS TRUE"),
    )


def downgrade() -> None:
    connection = op.get_bind()

    tombstones = connection.scalar(
        sa.text("SELECT count(*) FROM lab_work_order_equipment WHERE is_active IS FALSE")
    )
    if tombstones:
        duplicates = connection.scalar(
            sa.text(
                """
                SELECT count(*) FROM (
                    SELECT work_order_id, position
                    FROM lab_work_order_equipment
                    GROUP BY work_order_id, position
                    HAVING count(*) > 1
                ) AS dup
                """
            )
        )
        if duplicates:
            raise RuntimeError(
                "No se puede revertir 7088fa142cc2: existen equipos retirados (tombstone) que "
                "comparten (work_order_id, position) con otro equipo -- eso es válido bajo el "
                "índice único parcial actual, pero violaría la UniqueConstraint plana original. "
                "No hay una forma segura de revertir sin perder la distinción activo/retirado."
            )

    op.drop_index("uq_lab_equipment_position_active", table_name="lab_work_order_equipment")
    op.create_unique_constraint(
        "uq_lab_equipment_position", "lab_work_order_equipment", ["work_order_id", "position"]
    )

    op.drop_column("lab_work_order_equipment", "deleted_by")
    op.drop_column("lab_work_order_equipment", "deleted_at")
    op.drop_column("lab_work_order_equipment", "is_active")
