"""quotation service change exception

Revision ID: 9d0e1f2a3b4c
Revises: 8c9d0e1f2a3b
Create Date: 2026-07-29 21:00:00.000000
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "9d0e1f2a3b4c"
down_revision: Union[str, None] = "8c9d0e1f2a3b"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "quotation_service_change_requests",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("folio", sa.String(length=40), nullable=False),
        sa.Column("quotation_id", sa.Integer(), nullable=False),
        sa.Column("service_order_id", sa.Integer(), nullable=False),
        sa.Column("quotation_item_id", sa.Integer(), nullable=False),
        sa.Column("current_catalog_item_id", sa.Integer(), nullable=False),
        sa.Column("requested_catalog_item_id", sa.Integer(), nullable=False),
        sa.Column("requester_id", sa.Integer(), nullable=False),
        sa.Column("reviewer_id", sa.Integer(), nullable=True),
        sa.Column("authorized_apply_user_id", sa.Integer(), nullable=True),
        sa.Column("applied_by_id", sa.Integer(), nullable=True),
        sa.Column("snapshot_id", sa.Integer(), nullable=True),
        sa.Column("status", sa.String(length=40), nullable=False),
        sa.Column("capability", sa.String(length=80), nullable=False),
        sa.Column("active_scope_key", sa.String(length=240), nullable=True),
        sa.Column("reason", sa.Text(), nullable=False),
        sa.Column("observation", sa.Text(), nullable=True),
        sa.Column("review_comment", sa.Text(), nullable=True),
        sa.Column("block_reason", sa.Text(), nullable=True),
        sa.Column("current_service_snapshot", sa.JSON(), nullable=False),
        sa.Column("requested_service_snapshot", sa.JSON(), nullable=False),
        sa.Column("impact_snapshot", sa.JSON(), nullable=False),
        sa.Column("quotation_version_at_request", sa.DateTime(timezone=True), nullable=False),
        sa.Column("requested_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("reviewed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("applied_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("consumed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["quotation_id"], ["quotations.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["service_order_id"], ["service_orders.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["quotation_item_id"], ["quotation_items.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["current_catalog_item_id"], ["catalog_items.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["requested_catalog_item_id"], ["catalog_items.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["requester_id"], ["users.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["reviewer_id"], ["users.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["authorized_apply_user_id"], ["users.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["applied_by_id"], ["users.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["snapshot_id"], ["quotation_snapshots.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("folio", name="uq_quotation_service_change_folio"),
        sa.UniqueConstraint("active_scope_key", name="uq_quotation_service_change_active_scope"),
    )
    for column in (
        "folio", "quotation_id", "service_order_id", "quotation_item_id",
        "current_catalog_item_id", "requested_catalog_item_id", "requester_id",
        "reviewer_id", "authorized_apply_user_id", "applied_by_id", "snapshot_id",
        "status", "expires_at",
    ):
        op.create_index(
            f"ix_quotation_service_change_requests_{column}",
            "quotation_service_change_requests",
            [column],
            unique=False,
        )


def downgrade() -> None:
    op.drop_table("quotation_service_change_requests")
