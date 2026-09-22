"""DEV-0 hardening: at most one active DeveloperSession per trusted device.

A new revision on top of 602a09af6218 instead of editing it: that revision
may already be applied on local/dev databases, which would otherwise never
receive this index.

Also drops ``uq_developer_session_token_hash``: 602a09af6218 created BOTH that
unique constraint AND the unique index ``ix_developer_sessions_token_hash``
over the same column. The model declares only the unique index, which alone
already guarantees token_hash uniqueness.
"""

from alembic import op
import sqlalchemy as sa

revision = "c4d8e2f1a7b3"
down_revision = "602a09af6218"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Pre-existing duplicates (only possible before this hardening) would make
    # the unique index fail: keep the newest active row per device and revoke
    # the rest with the same canonical reason the application now uses.
    op.execute(sa.text(
        "UPDATE developer_sessions "
        "SET revoked_at = CURRENT_TIMESTAMP, revocation_reason = 'superseded' "
        "WHERE revoked_at IS NULL AND id NOT IN ("
        "  SELECT max(id) FROM developer_sessions WHERE revoked_at IS NULL GROUP BY device_id"
        ")"
    ))
    op.create_index(
        "uq_developer_sessions_active_device",
        "developer_sessions",
        ["device_id"],
        unique=True,
        postgresql_where=sa.text("revoked_at IS NULL"),
        sqlite_where=sa.text("revoked_at IS NULL"),
    )
    with op.batch_alter_table("developer_sessions") as batch:
        batch.drop_constraint("uq_developer_session_token_hash", type_="unique")


def downgrade() -> None:
    with op.batch_alter_table("developer_sessions") as batch:
        batch.create_unique_constraint("uq_developer_session_token_hash", ["token_hash"])
    op.drop_index("uq_developer_sessions_active_device", table_name="developer_sessions")
