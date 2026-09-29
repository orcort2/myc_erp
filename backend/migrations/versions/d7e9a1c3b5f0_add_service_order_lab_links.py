"""Historical ETS to LAB group links, without technical LAB mutations."""

from alembic import op
import sqlalchemy as sa

revision = "d7e9a1c3b5f0"
down_revision = "c4d8e2f1a7b3"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "service_order_lab_links",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("service_order_id", sa.Integer(), sa.ForeignKey("service_orders.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("lab_root_work_order_id", sa.Integer(), sa.ForeignKey("lab_work_orders.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("status", sa.String(20), nullable=False),
        sa.Column("linked_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("linked_by_user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("unlinked_at", sa.DateTime(timezone=True)),
        sa.Column("unlinked_by_user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="RESTRICT")),
        sa.Column("unlink_reason", sa.Text()),
        sa.Column("replaced_by_link_id", sa.Integer(), sa.ForeignKey("service_order_lab_links.id", ondelete="RESTRICT")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.CheckConstraint("status IN ('active', 'unlinked', 'replaced')", name="ck_service_order_lab_link_status"),
        sa.CheckConstraint(
            "(status = 'active' AND unlinked_at IS NULL "
            "AND unlinked_by_user_id IS NULL AND unlink_reason IS NULL "
            "AND replaced_by_link_id IS NULL) OR "
            "(status IN ('unlinked', 'replaced') AND unlinked_at IS NOT NULL "
            "AND unlinked_by_user_id IS NOT NULL AND unlink_reason IS NOT NULL "
            "AND length(trim(unlink_reason)) > 0)",
            name="ck_service_order_lab_link_lifecycle",
        ),
        sa.CheckConstraint(
            "replaced_by_link_id IS NULL OR (status = 'replaced' AND replaced_by_link_id <> id)",
            name="ck_service_order_lab_link_replacement",
        ),
    )
    for column in ("id", "service_order_id", "lab_root_work_order_id"):
        op.create_index(f"ix_service_order_lab_links_{column}", "service_order_lab_links", [column])
    for suffix, column in (("ets", "service_order_id"), ("root", "lab_root_work_order_id")):
        op.create_index(
            f"uq_service_order_lab_link_active_{suffix}", "service_order_lab_links", [column],
            unique=True, postgresql_where=sa.text("status = 'active'"),
            sqlite_where=sa.text("status = 'active'"),
        )


def downgrade() -> None:
    op.drop_table("service_order_lab_links")
