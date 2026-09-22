"""DEV-0: add developer_sessions -- short-lived Developer infrastructure authority."""

from alembic import op
import sqlalchemy as sa

revision = "602a09af6218"
down_revision = "9970e12e5f0d"
branch_labels = None
depends_on = None


def _timestamps():
    return [sa.Column(name, sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now())
            for name in ("created_at", "updated_at")]


def upgrade() -> None:
    op.create_table(
        "developer_sessions",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("device_id", sa.Integer(), sa.ForeignKey("mobile_trusted_devices.id", ondelete="CASCADE"), nullable=False),
        sa.Column("mobile_session_id", sa.Integer(), sa.ForeignKey("mobile_auth_sessions.id", ondelete="CASCADE"), nullable=False),
        sa.Column("token_hash", sa.String(64), nullable=False),
        sa.Column("last_used_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("revoked_at", sa.DateTime(timezone=True)),
        sa.Column("revocation_reason", sa.String(30)),
        *_timestamps(),
        sa.UniqueConstraint("token_hash", name="uq_developer_session_token_hash"),
    )
    for name in ("user_id", "device_id", "mobile_session_id", "expires_at", "revoked_at"):
        op.create_index(f"ix_developer_sessions_{name}", "developer_sessions", [name])
    op.create_index(
        "ix_developer_sessions_token_hash",
        "developer_sessions",
        ["token_hash"],
        unique=True,
    )


def downgrade() -> None:
    op.drop_table("developer_sessions")
