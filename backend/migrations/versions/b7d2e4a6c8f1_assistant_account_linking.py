"""MYC-ASSISTANT-1A: assistant_link_requests and assistant_account_links.

Additive only: two new tables, no backfill, no change to existing tables.
Downgrade drops both (link table first: it references the request table).
"""

from alembic import op
import sqlalchemy as sa

revision = "b7d2e4a6c8f1"
down_revision = "a3c5e7f9b1d2"
branch_labels = None
depends_on = None


def _timestamps():
    return [sa.Column(name, sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now())
            for name in ("created_at", "updated_at")]


def upgrade() -> None:
    op.create_table(
        "assistant_link_requests",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("public_id", sa.String(64), nullable=False),
        sa.Column("telegram_user_id", sa.BigInteger(), nullable=False),
        sa.Column("telegram_chat_id", sa.BigInteger(), nullable=False),
        sa.Column("candidate_user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("status", sa.String(20), nullable=False, server_default="pending"),
        sa.Column("comparison_code", sa.String(6)),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("decided_at", sa.DateTime(timezone=True)),
        sa.Column("approved_by_user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="RESTRICT")),
        sa.Column("approved_device_id", sa.Integer(),
                  sa.ForeignKey("mobile_trusted_devices.id", ondelete="SET NULL")),
        *_timestamps(),
        sa.CheckConstraint(
            "status IN ('pending', 'approved', 'rejected', 'expired', 'superseded')",
            name="ck_assistant_link_request_status",
        ),
        sa.CheckConstraint(
            "(status = 'pending' AND comparison_code IS NOT NULL AND length(comparison_code) = 6) OR "
            "(status <> 'pending' AND comparison_code IS NULL)",
            name="ck_assistant_link_request_code",
        ),
        sa.CheckConstraint(
            "(status = 'pending' AND decided_at IS NULL) OR "
            "(status <> 'pending' AND decided_at IS NOT NULL)",
            name="ck_assistant_link_request_decided",
        ),
        sa.CheckConstraint(
            "status <> 'approved' OR approved_by_user_id IS NOT NULL",
            name="ck_assistant_link_request_approver",
        ),
    )
    op.create_index("ix_assistant_link_requests_public_id", "assistant_link_requests", ["public_id"], unique=True)
    op.create_index("ix_assistant_link_requests_telegram_user_id", "assistant_link_requests", ["telegram_user_id"])
    op.create_index("ix_assistant_link_requests_candidate_user_id", "assistant_link_requests", ["candidate_user_id"])
    op.create_index("ix_assistant_link_requests_expires_at", "assistant_link_requests", ["expires_at"])
    op.create_index(
        "uq_assistant_link_requests_pending_telegram", "assistant_link_requests", ["telegram_user_id"],
        unique=True, postgresql_where=sa.text("status = 'pending'"), sqlite_where=sa.text("status = 'pending'"),
    )

    op.create_table(
        "assistant_account_links",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("telegram_user_id", sa.BigInteger(), nullable=False),
        sa.Column("telegram_chat_id", sa.BigInteger(), nullable=False),
        sa.Column("link_request_id", sa.Integer(),
                  sa.ForeignKey("assistant_link_requests.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("status", sa.String(20), nullable=False, server_default="active"),
        sa.Column("linked_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("revoked_at", sa.DateTime(timezone=True)),
        sa.Column("revoked_by_user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="RESTRICT")),
        sa.Column("revocation_reason", sa.String(30)),
        *_timestamps(),
        sa.UniqueConstraint("link_request_id", name="uq_assistant_account_links_link_request_id"),
        sa.CheckConstraint("status IN ('active', 'revoked')", name="ck_assistant_account_link_status"),
        sa.CheckConstraint(
            "(status = 'active' AND revoked_at IS NULL AND revocation_reason IS NULL) OR "
            "(status = 'revoked' AND revoked_at IS NOT NULL AND revocation_reason IS NOT NULL)",
            name="ck_assistant_account_link_revocation",
        ),
    )
    op.create_index("ix_assistant_account_links_user_id", "assistant_account_links", ["user_id"])
    op.create_index("ix_assistant_account_links_telegram_user_id", "assistant_account_links", ["telegram_user_id"])
    for name, column in (
        ("uq_assistant_links_active_user", "user_id"),
        ("uq_assistant_links_active_telegram_user", "telegram_user_id"),
        ("uq_assistant_links_active_telegram_chat", "telegram_chat_id"),
    ):
        op.create_index(
            name, "assistant_account_links", [column], unique=True,
            postgresql_where=sa.text("status = 'active'"), sqlite_where=sa.text("status = 'active'"),
        )


def downgrade() -> None:
    op.drop_table("assistant_account_links")
    op.drop_table("assistant_link_requests")
