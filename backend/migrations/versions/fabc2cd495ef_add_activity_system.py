"""add activity system

Revision ID: fabc2cd495ef
Revises: e7f9a1b3c5d7
Create Date: 2026-07-27 16:31:57.488676
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "fabc2cd495ef"
down_revision: Union[str, None] = "e7f9a1b3c5d7"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "activity_threads",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("entity_type", sa.String(length=40), nullable=False),
        sa.Column("entity_id", sa.Integer(), nullable=False),
        sa.Column("created_by_id", sa.Integer(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["created_by_id"],
            ["users.id"],
            name="fk_activity_threads_created_by_id_users",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_activity_threads"),
        sa.UniqueConstraint(
            "entity_type",
            "entity_id",
            name="uq_activity_thread_entity",
        ),
    )

    op.create_index(
        "ix_activity_threads_entity_type",
        "activity_threads",
        ["entity_type"],
        unique=False,
    )
    op.create_index(
        "ix_activity_threads_entity_id",
        "activity_threads",
        ["entity_id"],
        unique=False,
    )
    op.create_index(
        "ix_activity_threads_created_by_id",
        "activity_threads",
        ["created_by_id"],
        unique=False,
    )

    op.create_table(
        "activity_messages",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("thread_id", sa.Integer(), nullable=False),
        sa.Column("author_id", sa.Integer(), nullable=True),
        sa.Column(
            "message_type",
            sa.String(length=30),
            server_default=sa.text("'comment'"),
            nullable=False,
        ),
        sa.Column(
            "body",
            sa.Text(),
            server_default=sa.text("''"),
            nullable=False,
        ),
        sa.Column(
            "is_system",
            sa.Boolean(),
            server_default=sa.text("false"),
            nullable=False,
        ),
        sa.Column(
            "is_formal",
            sa.Boolean(),
            server_default=sa.text("false"),
            nullable=False,
        ),
        sa.Column("edited_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("withdrawn_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("withdrawn_by_id", sa.Integer(), nullable=True),
        sa.Column("withdrawal_reason", sa.String(length=80), nullable=True),
        sa.Column("withdrawal_note", sa.Text(), nullable=True),
        sa.Column(
            "metadata_json",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'{}'::jsonb"),
            nullable=True,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["thread_id"],
            ["activity_threads.id"],
            name="fk_activity_messages_thread_id_activity_threads",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["author_id"],
            ["users.id"],
            name="fk_activity_messages_author_id_users",
        ),
        sa.ForeignKeyConstraint(
            ["withdrawn_by_id"],
            ["users.id"],
            name="fk_activity_messages_withdrawn_by_id_users",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_activity_messages"),
    )

    op.create_index(
        "ix_activity_messages_thread_id",
        "activity_messages",
        ["thread_id"],
        unique=False,
    )
    op.create_index(
        "ix_activity_messages_author_id",
        "activity_messages",
        ["author_id"],
        unique=False,
    )
    op.create_index(
        "ix_activity_messages_message_type",
        "activity_messages",
        ["message_type"],
        unique=False,
    )
    op.create_index(
        "ix_activity_messages_withdrawn_by_id",
        "activity_messages",
        ["withdrawn_by_id"],
        unique=False,
    )

    op.create_table(
        "activity_message_revisions",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("message_id", sa.Integer(), nullable=False),
        sa.Column("previous_body", sa.Text(), nullable=False),
        sa.Column("new_body", sa.Text(), nullable=False),
        sa.Column("edited_by_id", sa.Integer(), nullable=False),
        sa.Column("reason", sa.String(length=255), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["message_id"],
            ["activity_messages.id"],
            name=(
                "fk_activity_message_revisions_message_id_"
                "activity_messages"
            ),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["edited_by_id"],
            ["users.id"],
            name="fk_activity_message_revisions_edited_by_id_users",
        ),
        sa.PrimaryKeyConstraint(
            "id",
            name="pk_activity_message_revisions",
        ),
    )

    op.create_index(
        "ix_activity_message_revisions_message_id",
        "activity_message_revisions",
        ["message_id"],
        unique=False,
    )
    op.create_index(
        "ix_activity_message_revisions_edited_by_id",
        "activity_message_revisions",
        ["edited_by_id"],
        unique=False,
    )

    op.create_table(
        "activity_mentions",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("message_id", sa.Integer(), nullable=False),
        sa.Column("mentioned_user_id", sa.Integer(), nullable=False),
        sa.Column("read_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["message_id"],
            ["activity_messages.id"],
            name="fk_activity_mentions_message_id_activity_messages",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["mentioned_user_id"],
            ["users.id"],
            name="fk_activity_mentions_mentioned_user_id_users",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_activity_mentions"),
        sa.UniqueConstraint(
            "message_id",
            "mentioned_user_id",
            name="uq_activity_message_mention",
        ),
    )

    op.create_index(
        "ix_activity_mentions_message_id",
        "activity_mentions",
        ["message_id"],
        unique=False,
    )
    op.create_index(
        "ix_activity_mentions_mentioned_user_id",
        "activity_mentions",
        ["mentioned_user_id"],
        unique=False,
    )

    op.create_table(
        "activity_attachments",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("message_id", sa.Integer(), nullable=False),
        sa.Column("original_name", sa.String(length=255), nullable=False),
        sa.Column("stored_path", sa.String(length=500), nullable=False),
        sa.Column("content_type", sa.String(length=120), nullable=True),
        sa.Column("size_bytes", sa.Integer(), nullable=False),
        sa.Column("uploaded_by_id", sa.Integer(), nullable=True),
        sa.Column(
            "is_official_evidence",
            sa.Boolean(),
            server_default=sa.text("false"),
            nullable=False,
        ),
        sa.Column(
            "hidden_with_message",
            sa.Boolean(),
            server_default=sa.text("false"),
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["message_id"],
            ["activity_messages.id"],
            name="fk_activity_attachments_message_id_activity_messages",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["uploaded_by_id"],
            ["users.id"],
            name="fk_activity_attachments_uploaded_by_id_users",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_activity_attachments"),
    )

    op.create_index(
        "ix_activity_attachments_message_id",
        "activity_attachments",
        ["message_id"],
        unique=False,
    )
    op.create_index(
        "ix_activity_attachments_uploaded_by_id",
        "activity_attachments",
        ["uploaded_by_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        "ix_activity_attachments_uploaded_by_id",
        table_name="activity_attachments",
    )
    op.drop_index(
        "ix_activity_attachments_message_id",
        table_name="activity_attachments",
    )
    op.drop_table("activity_attachments")

    op.drop_index(
        "ix_activity_mentions_mentioned_user_id",
        table_name="activity_mentions",
    )
    op.drop_index(
        "ix_activity_mentions_message_id",
        table_name="activity_mentions",
    )
    op.drop_table("activity_mentions")

    op.drop_index(
        "ix_activity_message_revisions_edited_by_id",
        table_name="activity_message_revisions",
    )
    op.drop_index(
        "ix_activity_message_revisions_message_id",
        table_name="activity_message_revisions",
    )
    op.drop_table("activity_message_revisions")

    op.drop_index(
        "ix_activity_messages_withdrawn_by_id",
        table_name="activity_messages",
    )
    op.drop_index(
        "ix_activity_messages_message_type",
        table_name="activity_messages",
    )
    op.drop_index(
        "ix_activity_messages_author_id",
        table_name="activity_messages",
    )
    op.drop_index(
        "ix_activity_messages_thread_id",
        table_name="activity_messages",
    )
    op.drop_table("activity_messages")

    op.drop_index(
        "ix_activity_threads_created_by_id",
        table_name="activity_threads",
    )
    op.drop_index(
        "ix_activity_threads_entity_id",
        table_name="activity_threads",
    )
    op.drop_index(
        "ix_activity_threads_entity_type",
        table_name="activity_threads",
    )
    op.drop_table("activity_threads")