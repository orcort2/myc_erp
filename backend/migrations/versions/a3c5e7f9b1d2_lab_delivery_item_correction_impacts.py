"""LAB delivery item correction impacts (Fase 3B).

Creates lab_delivery_item_correction_impacts: administrative consequence of a
technical correction over an already delivered LabDeliveryItem. No backfill:
existing deliveries implicitly have no pending administrative impact. FKs are
non-destructive (RESTRICT / SET NULL); rows are never deleted.
"""

import sqlalchemy as sa
from alembic import context, op

revision = "a3c5e7f9b1d2"
down_revision = "ffcd7b40ac46"
branch_labels = None
depends_on = None

TABLE = "lab_delivery_item_correction_impacts"


def upgrade() -> None:
    op.create_table(
        TABLE,
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "delivery_item_id",
            sa.Integer(),
            sa.ForeignKey("lab_delivery_items.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("work_order_id_snapshot", sa.Integer(), nullable=False),
        sa.Column("equipment_id_snapshot", sa.Integer(), nullable=False),
        sa.Column("impact_type", sa.String(32), nullable=False),
        sa.Column("status", sa.String(16), nullable=False, server_default="pending"),
        sa.Column("reason", sa.Text(), nullable=False),
        sa.Column(
            "created_by_user_id",
            sa.Integer(),
            sa.ForeignKey("users.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("resolved_at", sa.DateTime(timezone=True)),
        sa.Column(
            "resolved_by_user_id",
            sa.Integer(),
            sa.ForeignKey("users.id", ondelete="RESTRICT"),
        ),
        sa.Column("resolution_note", sa.Text()),
        sa.Column(
            "source_work_order_revision_id",
            sa.Integer(),
            sa.ForeignKey("lab_work_order_revisions.id", ondelete="SET NULL"),
        ),
        sa.Column(
            "source_field_sheet_id",
            sa.Integer(),
            sa.ForeignKey("field_sheets.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("source_field_sheet_revision_number", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.CheckConstraint(
            "impact_type IN ('documentation_reissue', 'delivery_invalidated')",
            name="ck_lab_delivery_item_correction_impact_type",
        ),
        sa.CheckConstraint(
            "status IN ('pending', 'resolved', 'cancelled')",
            name="ck_lab_delivery_item_correction_impact_status",
        ),
    )
    op.create_index(f"ix_{TABLE}_id", TABLE, ["id"])
    op.create_index(f"ix_{TABLE}_delivery_item_id", TABLE, ["delivery_item_id"])
    op.create_index(f"ix_{TABLE}_status", TABLE, ["status"])
    op.create_index(
        "uq_lab_delivery_item_correction_impact_pending",
        TABLE,
        ["delivery_item_id", "source_field_sheet_id"],
        unique=True,
        postgresql_where=sa.text("status = 'pending'"),
        sqlite_where=sa.text("status = 'pending'"),
    )


def downgrade() -> None:
    # Do not allow offline SQL to bypass the historical-data guard.
    if context.is_offline_mode():
        raise RuntimeError("Downgrade requires an online emptiness check")
    connection = op.get_bind()
    if connection.dialect.name == "postgresql":
        connection.execute(sa.text(f"LOCK TABLE {TABLE} IN ACCESS EXCLUSIVE MODE"))
    if connection.execute(sa.text(f"SELECT 1 FROM {TABLE} LIMIT 1")).first() is not None:
        raise RuntimeError("Downgrade refused: historical correction impacts must be preserved")
    op.drop_index("uq_lab_delivery_item_correction_impact_pending", table_name=TABLE)
    op.drop_index(f"ix_{TABLE}_status", table_name=TABLE)
    op.drop_index(f"ix_{TABLE}_delivery_item_id", table_name=TABLE)
    op.drop_index(f"ix_{TABLE}_id", table_name=TABLE)
    op.drop_table(TABLE)
