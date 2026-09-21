"""BIOMETRIC-2: add opaque biometric login credentials bound to a trusted device."""

from alembic import op
import sqlalchemy as sa

revision = "9970e12e5f0d"
down_revision = "b10a1c202601"
branch_labels = None
depends_on = None


def _timestamps():
    return [sa.Column(name, sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now())
            for name in ("created_at", "updated_at")]


def upgrade() -> None:
    op.create_table(
        "mobile_biometric_credentials",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("device_id", sa.Integer(), sa.ForeignKey("mobile_trusted_devices.id", ondelete="CASCADE"), nullable=False),
        sa.Column("credential_hash", sa.String(64), nullable=False),
        sa.Column("last_used_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("revoked_at", sa.DateTime(timezone=True)),
        sa.Column("password_changed_at_snapshot", sa.DateTime(timezone=True)),
        *_timestamps(),
        sa.UniqueConstraint("credential_hash", name="uq_mobile_biometric_credential_hash"),
    )
    for name in ("user_id", "device_id", "expires_at", "revoked_at"):
        op.create_index(f"ix_mobile_biometric_credentials_{name}", "mobile_biometric_credentials", [name])
    op.create_index(
        "ix_mobile_biometric_credentials_credential_hash",
        "mobile_biometric_credentials",
        ["credential_hash"],
        unique=True,
    )


def downgrade() -> None:
    op.drop_table("mobile_biometric_credentials")
