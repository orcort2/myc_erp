"""BIOMETRIC-1: separate security devices and rotating Mobile sessions."""

from alembic import op
import sqlalchemy as sa

revision = "b10a1c202601"
down_revision = "6640c526c412"
branch_labels = None
depends_on = None


def _timestamps():
    return [sa.Column(name, sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now())
            for name in ("created_at", "updated_at")]


def upgrade() -> None:
    op.create_table(
        "mobile_trusted_devices",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("device_uuid", sa.String(128), nullable=False),
        sa.Column("platform", sa.String(20), nullable=False),
        sa.Column("device_name", sa.String(160)),
        sa.Column("app_version", sa.String(40)),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("trusted_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("last_seen_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("revoked_at", sa.DateTime(timezone=True)),
        *_timestamps(),
        sa.UniqueConstraint("user_id", "device_uuid", name="uq_mobile_device_user_uuid"),
        sa.CheckConstraint("platform IN ('ios', 'android')", name="ck_mobile_device_platform"),
    )
    op.create_index("ix_mobile_trusted_devices_user_id", "mobile_trusted_devices", ["user_id"])
    op.create_table(
        "mobile_auth_sessions",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("device_id", sa.Integer(), sa.ForeignKey("mobile_trusted_devices.id", ondelete="CASCADE"), nullable=False),
        sa.Column("family_id", sa.String(36), nullable=False),
        sa.Column("refresh_token_hash", sa.String(64), nullable=False),
        sa.Column("legacy_refresh_token_hash", sa.String(64)),
        sa.Column("actor_type", sa.String(20), nullable=False),
        sa.Column("client_id", sa.Integer(), sa.ForeignKey("clients.id", ondelete="CASCADE")),
        sa.Column("membership_id", sa.Integer(), sa.ForeignKey("client_portal_memberships.id", ondelete="CASCADE")),
        sa.Column("last_used_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("revoked_at", sa.DateTime(timezone=True)),
        sa.Column("replaced_by_id", sa.Integer(), sa.ForeignKey("mobile_auth_sessions.id", ondelete="SET NULL"), unique=True),
        sa.Column("reuse_detected_at", sa.DateTime(timezone=True)),
        *_timestamps(),
        sa.CheckConstraint(
            "(actor_type = 'internal' AND client_id IS NULL AND membership_id IS NULL) OR "
            "(actor_type = 'client' AND client_id IS NOT NULL AND membership_id IS NOT NULL)",
            name="ck_mobile_session_actor_scope",
        ),
    )
    for name in ("user_id", "device_id", "family_id", "expires_at", "revoked_at", "refresh_token_hash", "legacy_refresh_token_hash"):
        op.create_index(f"ix_mobile_auth_sessions_{name}", "mobile_auth_sessions", [name], unique=name.endswith("token_hash"))


def downgrade() -> None:
    op.drop_table("mobile_auth_sessions")
    op.drop_table("mobile_trusted_devices")
