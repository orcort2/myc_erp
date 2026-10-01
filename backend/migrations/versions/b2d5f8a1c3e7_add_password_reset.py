"""add password reset tokens and users.auth_version (EMAIL-2)

users.auth_version is the web-session authority: JWTs carry it and a reset
increments it. Existing rows start at 1, so already-issued legacy JWTs (which
have no claim) stay valid until the first reset.
"""

from alembic import op
import sqlalchemy as sa

revision = "b2d5f8a1c3e7"
down_revision = "a1c4e7b9d2f6"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("users", sa.Column("auth_version", sa.Integer(), server_default="1", nullable=False))
    op.create_table(
        "password_reset_tokens",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("token_hash", sa.String(length=64), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("used_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(
            ["user_id"], ["users.id"], name="fk_password_reset_tokens_user_id_users", ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id", name="pk_password_reset_tokens"),
    )
    op.create_index("ix_password_reset_tokens_id", "password_reset_tokens", ["id"], unique=False)
    op.create_index("ix_password_reset_tokens_user_id", "password_reset_tokens", ["user_id"], unique=False)
    op.create_index("ix_password_reset_tokens_token_hash", "password_reset_tokens", ["token_hash"], unique=True)
    op.create_index("ix_password_reset_tokens_expires_at", "password_reset_tokens", ["expires_at"], unique=False)


def downgrade() -> None:
    op.drop_table("password_reset_tokens")
    op.drop_column("users", "auth_version")
