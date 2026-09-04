"""snapshot lab delivery history ids/folios, live FKs become SET NULL

Revision ID: da6ad5a90e57
Revises: d3e4f5a6b7c8

El flujo aprobado es: entrega completed -> Anular entrega -> queda voided e
histórica -> después se puede cancelar/eliminar la OT (y sus equipos), sujeto
sólo a bloqueos independientes (p.ej. FieldSheets históricas). Hoy eso es
imposible: lab_delivery_items.work_order_id/equipment_id y
lab_work_order_deliveries.root_work_order_id/lab_delivery_group_receipts.
root_work_order_id son RESTRICT hacia lab_work_orders/lab_work_order_equipment
-- cualquier DELETE de una OT con historial de entrega (aun voided) revienta
por integridad referencial, sin importar el guard de aplicación.

Esta migración independiza el histórico de Delivery de las entidades vivas:

- agrega columnas *_snapshot (NOT NULL, congeladas al crear el registro,
  nunca se vuelven a escribir) que preservan permanentemente qué OT/folio/
  equipo participó, incluso después de que la fila viva se borre;
- vuelve nullable los FKs operativos existentes (work_order_id, equipment_id,
  root_work_order_id) y les cambia ondelete a SET NULL -- dejan de ser la
  autoridad histórica, son sólo una referencia operativa de conveniencia
  mientras la fila viva exista.

No borra, no reescribe, no reinterpreta ningún dato existente: sólo congela
(vía backfill desde las filas vivas de hoy) lo que ya es cierto.
"""

from alembic import op
import sqlalchemy as sa


revision = "da6ad5a90e57"
down_revision = "d3e4f5a6b7c8"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ---------------------------------------------------------------------
    # lab_delivery_items
    # ---------------------------------------------------------------------
    op.add_column("lab_delivery_items", sa.Column("work_order_id_snapshot", sa.Integer(), nullable=True))
    op.add_column("lab_delivery_items", sa.Column("work_order_folio_snapshot", sa.Integer(), nullable=True))
    op.add_column("lab_delivery_items", sa.Column("equipment_id_snapshot", sa.Integer(), nullable=True))

    op.execute(
        """
        UPDATE lab_delivery_items AS li
        SET work_order_id_snapshot = li.work_order_id,
            equipment_id_snapshot = li.equipment_id,
            work_order_folio_snapshot = lwo.folio
        FROM lab_work_orders AS lwo
        WHERE lwo.id = li.work_order_id
        """
    )

    op.alter_column("lab_delivery_items", "work_order_id_snapshot", existing_type=sa.Integer(), nullable=False)
    op.alter_column("lab_delivery_items", "work_order_folio_snapshot", existing_type=sa.Integer(), nullable=False)
    op.alter_column("lab_delivery_items", "equipment_id_snapshot", existing_type=sa.Integer(), nullable=False)

    op.drop_constraint("lab_delivery_items_work_order_id_fkey", "lab_delivery_items", type_="foreignkey")
    op.drop_constraint("lab_delivery_items_equipment_id_fkey", "lab_delivery_items", type_="foreignkey")
    op.alter_column("lab_delivery_items", "work_order_id", existing_type=sa.Integer(), nullable=True)
    op.alter_column("lab_delivery_items", "equipment_id", existing_type=sa.Integer(), nullable=True)
    op.create_foreign_key(
        "lab_delivery_items_work_order_id_fkey",
        "lab_delivery_items",
        "lab_work_orders",
        ["work_order_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_foreign_key(
        "lab_delivery_items_equipment_id_fkey",
        "lab_delivery_items",
        "lab_work_order_equipment",
        ["equipment_id"],
        ["id"],
        ondelete="SET NULL",
    )

    # ---------------------------------------------------------------------
    # lab_work_order_deliveries
    # ---------------------------------------------------------------------
    op.add_column("lab_work_order_deliveries", sa.Column("root_work_order_id_snapshot", sa.Integer(), nullable=True))
    op.add_column("lab_work_order_deliveries", sa.Column("root_work_order_folio_snapshot", sa.Integer(), nullable=True))

    op.execute(
        """
        UPDATE lab_work_order_deliveries AS d
        SET root_work_order_id_snapshot = d.root_work_order_id,
            root_work_order_folio_snapshot = lwo.folio
        FROM lab_work_orders AS lwo
        WHERE lwo.id = d.root_work_order_id
        """
    )

    op.alter_column(
        "lab_work_order_deliveries", "root_work_order_id_snapshot", existing_type=sa.Integer(), nullable=False
    )
    op.alter_column(
        "lab_work_order_deliveries", "root_work_order_folio_snapshot", existing_type=sa.Integer(), nullable=False
    )

    op.drop_constraint(
        "lab_work_order_deliveries_root_work_order_id_fkey", "lab_work_order_deliveries", type_="foreignkey"
    )
    op.alter_column("lab_work_order_deliveries", "root_work_order_id", existing_type=sa.Integer(), nullable=True)
    op.create_foreign_key(
        "lab_work_order_deliveries_root_work_order_id_fkey",
        "lab_work_order_deliveries",
        "lab_work_orders",
        ["root_work_order_id"],
        ["id"],
        ondelete="SET NULL",
    )

    # ---------------------------------------------------------------------
    # lab_delivery_group_receipts
    # ---------------------------------------------------------------------
    op.add_column(
        "lab_delivery_group_receipts", sa.Column("root_work_order_id_snapshot", sa.Integer(), nullable=True)
    )
    op.add_column(
        "lab_delivery_group_receipts", sa.Column("root_work_order_folio_snapshot", sa.Integer(), nullable=True)
    )

    op.execute(
        """
        UPDATE lab_delivery_group_receipts AS r
        SET root_work_order_id_snapshot = r.root_work_order_id,
            root_work_order_folio_snapshot = lwo.folio
        FROM lab_work_orders AS lwo
        WHERE lwo.id = r.root_work_order_id
        """
    )

    op.alter_column(
        "lab_delivery_group_receipts", "root_work_order_id_snapshot", existing_type=sa.Integer(), nullable=False
    )
    op.alter_column(
        "lab_delivery_group_receipts", "root_work_order_folio_snapshot", existing_type=sa.Integer(), nullable=False
    )

    op.drop_constraint(
        "lab_delivery_group_receipts_root_work_order_id_fkey", "lab_delivery_group_receipts", type_="foreignkey"
    )
    op.alter_column("lab_delivery_group_receipts", "root_work_order_id", existing_type=sa.Integer(), nullable=True)
    op.create_foreign_key(
        "lab_delivery_group_receipts_root_work_order_id_fkey",
        "lab_delivery_group_receipts",
        "lab_work_orders",
        ["root_work_order_id"],
        ["id"],
        ondelete="SET NULL",
    )


def downgrade() -> None:
    connection = op.get_bind()

    orphan_items = connection.scalar(
        sa.text("SELECT count(*) FROM lab_delivery_items WHERE work_order_id IS NULL OR equipment_id IS NULL")
    )
    if orphan_items:
        raise RuntimeError(
            "No se puede revertir da6ad5a90e57: existen lab_delivery_items cuyo work_order_id/"
            "equipment_id vivo ya es NULL (la OT o el equipo original fue eliminado). Revertir "
            "exigiría volver a RESTRICT/NOT NULL sobre una referencia que ya no existe -- no hay "
            "un valor seguro equivalente al que reasignar."
        )
    orphan_deliveries = connection.scalar(
        sa.text("SELECT count(*) FROM lab_work_order_deliveries WHERE root_work_order_id IS NULL")
    )
    if orphan_deliveries:
        raise RuntimeError(
            "No se puede revertir da6ad5a90e57: existen lab_work_order_deliveries cuyo "
            "root_work_order_id vivo ya es NULL (la OT raíz fue eliminada)."
        )
    orphan_receipts = connection.scalar(
        sa.text("SELECT count(*) FROM lab_delivery_group_receipts WHERE root_work_order_id IS NULL")
    )
    if orphan_receipts:
        raise RuntimeError(
            "No se puede revertir da6ad5a90e57: existen lab_delivery_group_receipts cuyo "
            "root_work_order_id vivo ya es NULL (la OT raíz fue eliminada)."
        )

    op.drop_constraint(
        "lab_delivery_group_receipts_root_work_order_id_fkey", "lab_delivery_group_receipts", type_="foreignkey"
    )
    op.alter_column("lab_delivery_group_receipts", "root_work_order_id", existing_type=sa.Integer(), nullable=False)
    op.create_foreign_key(
        "lab_delivery_group_receipts_root_work_order_id_fkey",
        "lab_delivery_group_receipts",
        "lab_work_orders",
        ["root_work_order_id"],
        ["id"],
        ondelete="RESTRICT",
    )
    op.drop_column("lab_delivery_group_receipts", "root_work_order_folio_snapshot")
    op.drop_column("lab_delivery_group_receipts", "root_work_order_id_snapshot")

    op.drop_constraint(
        "lab_work_order_deliveries_root_work_order_id_fkey", "lab_work_order_deliveries", type_="foreignkey"
    )
    op.alter_column("lab_work_order_deliveries", "root_work_order_id", existing_type=sa.Integer(), nullable=False)
    op.create_foreign_key(
        "lab_work_order_deliveries_root_work_order_id_fkey",
        "lab_work_order_deliveries",
        "lab_work_orders",
        ["root_work_order_id"],
        ["id"],
        ondelete="RESTRICT",
    )
    op.drop_column("lab_work_order_deliveries", "root_work_order_folio_snapshot")
    op.drop_column("lab_work_order_deliveries", "root_work_order_id_snapshot")

    op.drop_constraint("lab_delivery_items_work_order_id_fkey", "lab_delivery_items", type_="foreignkey")
    op.drop_constraint("lab_delivery_items_equipment_id_fkey", "lab_delivery_items", type_="foreignkey")
    op.alter_column("lab_delivery_items", "work_order_id", existing_type=sa.Integer(), nullable=False)
    op.alter_column("lab_delivery_items", "equipment_id", existing_type=sa.Integer(), nullable=False)
    op.create_foreign_key(
        "lab_delivery_items_work_order_id_fkey",
        "lab_delivery_items",
        "lab_work_orders",
        ["work_order_id"],
        ["id"],
        ondelete="RESTRICT",
    )
    op.create_foreign_key(
        "lab_delivery_items_equipment_id_fkey",
        "lab_delivery_items",
        "lab_work_order_equipment",
        ["equipment_id"],
        ["id"],
        ondelete="RESTRICT",
    )
    op.drop_column("lab_delivery_items", "equipment_id_snapshot")
    op.drop_column("lab_delivery_items", "work_order_folio_snapshot")
    op.drop_column("lab_delivery_items", "work_order_id_snapshot")
