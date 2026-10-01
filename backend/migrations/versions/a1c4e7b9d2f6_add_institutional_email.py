"""add institutional email infrastructure (EMAIL-1)

Creates email_templates and email_deliveries. Default templates are created
idempotently by application code (get-or-create), not by this migration.
"""

from alembic import op
import sqlalchemy as sa

revision = "a1c4e7b9d2f6"
down_revision = "e8f1a3c5d7b9"
branch_labels = None
depends_on = None


def _timestamps() -> list[sa.Column]:
    return [
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    ]


def upgrade() -> None:
    op.create_table(
        "email_templates",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("template_key", sa.String(length=80), nullable=False),
        sa.Column("name", sa.String(length=180), nullable=False),
        sa.Column("subject_template", sa.String(length=300), nullable=False),
        sa.Column("body_template", sa.Text(), nullable=False),
        sa.Column("is_active", sa.Boolean(), server_default=sa.true(), nullable=False),
        *_timestamps(),
        sa.PrimaryKeyConstraint("id", name="pk_email_templates"),
    )
    op.create_index("ix_email_templates_id", "email_templates", ["id"], unique=False)
    op.create_index("ix_email_templates_template_key", "email_templates", ["template_key"], unique=True)

    op.create_table(
        "email_deliveries",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("template_key", sa.String(length=80), nullable=False),
        sa.Column("related_entity_type", sa.String(length=60), nullable=True),
        sa.Column("related_entity_id", sa.Integer(), nullable=True),
        sa.Column("to_json", sa.JSON(), nullable=False),
        sa.Column("cc_json", sa.JSON(), nullable=False),
        sa.Column("bcc_json", sa.JSON(), nullable=False),
        sa.Column("subject", sa.String(length=300), nullable=False),
        sa.Column("body_text_snapshot", sa.Text(), nullable=False),
        sa.Column("body_html_snapshot", sa.Text(), nullable=False),
        sa.Column("attachments_json", sa.JSON(), nullable=False),
        sa.Column("status", sa.String(length=20), server_default="pending", nullable=False),
        sa.Column("attempt_count", sa.Integer(), server_default="0", nullable=False),
        sa.Column("provider_message_id", sa.String(length=255), nullable=True),
        sa.Column("provider_response", sa.Text(), nullable=True),
        sa.Column("last_error", sa.Text(), nullable=True),
        sa.Column("failure_code", sa.String(length=40), nullable=True),
        sa.Column("requested_by_id", sa.Integer(), nullable=True),
        sa.Column("sent_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("failed_at", sa.DateTime(timezone=True), nullable=True),
        *_timestamps(),
        sa.CheckConstraint(
            "status IN ('pending', 'sending', 'sent', 'failed')",
            name="ck_email_deliveries_status",
        ),
        sa.ForeignKeyConstraint(
            ["requested_by_id"], ["users.id"], name="fk_email_deliveries_requested_by_id_users", ondelete="SET NULL"
        ),
        sa.PrimaryKeyConstraint("id", name="pk_email_deliveries"),
    )
    op.create_index("ix_email_deliveries_id", "email_deliveries", ["id"], unique=False)
    op.create_index("ix_email_deliveries_template_key", "email_deliveries", ["template_key"], unique=False)
    op.create_index("ix_email_deliveries_status", "email_deliveries", ["status"], unique=False)
    op.create_index("ix_email_deliveries_requested_by_id", "email_deliveries", ["requested_by_id"], unique=False)
    op.create_index(
        "ix_email_deliveries_related_entity",
        "email_deliveries",
        ["related_entity_type", "related_entity_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_table("email_deliveries")
    op.drop_table("email_templates")
