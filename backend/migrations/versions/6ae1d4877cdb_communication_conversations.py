"""communication_conversations

Revision ID: 6ae1d4877cdb
Revises: 4c7ef14e1391
Create Date: 2026-07-29 12:36:45.626365
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "6ae1d4877cdb"
down_revision: Union[str, None] = "4c7ef14e1391"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "communication_conversations",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column(
            "conversation_type",
            sa.String(length=30),
            nullable=False,
            server_default=sa.text("'internal'"),
        ),
        sa.Column(
            "title",
            sa.String(length=180),
            nullable=True,
        ),
        sa.Column(
            "client_id",
            sa.Integer(),
            nullable=True,
        ),
        sa.Column(
            "created_by_user_id",
            sa.Integer(),
            nullable=False,
        ),
        sa.Column(
            "last_message_at",
            sa.DateTime(timezone=True),
            nullable=True,
        ),
        sa.Column(
            "archived_at",
            sa.DateTime(timezone=True),
            nullable=True,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.ForeignKeyConstraint(
            ["client_id"],
            ["clients.id"],
            name="fk_communication_conversations_client_id_clients",
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["created_by_user_id"],
            ["users.id"],
            name="fk_communication_conversations_created_by_user_id_users",
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint(
            "id",
            name="pk_communication_conversations",
        ),
    )

    op.create_index(
        "ix_communication_conversations_conversation_type",
        "communication_conversations",
        ["conversation_type"],
        unique=False,
    )

    op.create_index(
        "ix_communication_conversations_updated",
        "communication_conversations",
        ["updated_at"],
        unique=False,
    )

    op.create_index(
        "ix_communication_conversations_client",
        "communication_conversations",
        ["client_id"],
        unique=False,
    )

    op.create_index(
        "ix_communication_conversations_last_message_at",
        "communication_conversations",
        ["last_message_at"],
        unique=False,
    )

    op.create_table(
        "communication_participants",
        sa.Column(
            "conversation_id",
            sa.Integer(),
            nullable=False,
        ),
        sa.Column(
            "user_id",
            sa.Integer(),
            nullable=False,
        ),
        sa.Column(
            "joined_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.ForeignKeyConstraint(
            ["conversation_id"],
            ["communication_conversations.id"],
            name="fk_communication_participants_conversation_id",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            name="fk_communication_participants_user_id",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint(
            "conversation_id",
            "user_id",
            name="pk_communication_participants",
        ),
        sa.UniqueConstraint(
            "conversation_id",
            "user_id",
            name="uq_communication_participant",
        ),
    )

    op.create_index(
        "ix_communication_participants_user_id",
        "communication_participants",
        ["user_id"],
        unique=False,
    )

    op.create_table(
        "communication_messages",
        sa.Column(
            "id",
            sa.Integer(),
            nullable=False,
        ),
        sa.Column(
            "conversation_id",
            sa.Integer(),
            nullable=False,
        ),
        sa.Column(
            "sender_user_id",
            sa.Integer(),
            nullable=False,
        ),
        sa.Column(
            "body",
            sa.Text(),
            nullable=False,
        ),
        sa.Column(
            "message_type",
            sa.String(length=20),
            nullable=False,
            server_default=sa.text("'text'"),
        ),
        sa.Column(
            "delivered_at",
            sa.DateTime(timezone=True),
            nullable=True,
        ),
        sa.Column(
            "read_at",
            sa.DateTime(timezone=True),
            nullable=True,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.ForeignKeyConstraint(
            ["conversation_id"],
            ["communication_conversations.id"],
            name="fk_communication_messages_conversation_id",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["sender_user_id"],
            ["users.id"],
            name="fk_communication_messages_sender_user_id",
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint(
            "id",
            name="pk_communication_messages",
        ),
    )

    op.create_index(
        "ix_communication_messages_conversation_id",
        "communication_messages",
        ["conversation_id"],
        unique=False,
    )

    op.create_index(
        "ix_communication_messages_sender_user_id",
        "communication_messages",
        ["sender_user_id"],
        unique=False,
    )

    op.create_index(
        "ix_communication_messages_conversation_created",
        "communication_messages",
        ["conversation_id", "created_at"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        "ix_communication_messages_conversation_created",
        table_name="communication_messages",
    )

    op.drop_index(
        "ix_communication_messages_sender_user_id",
        table_name="communication_messages",
    )

    op.drop_index(
        "ix_communication_messages_conversation_id",
        table_name="communication_messages",
    )

    op.drop_table("communication_messages")

    op.drop_index(
        "ix_communication_participants_user_id",
        table_name="communication_participants",
    )

    op.drop_table("communication_participants")

    op.drop_index(
        "ix_communication_conversations_last_message_at",
        table_name="communication_conversations",
    )

    op.drop_index(
        "ix_communication_conversations_client",
        table_name="communication_conversations",
    )

    op.drop_index(
        "ix_communication_conversations_updated",
        table_name="communication_conversations",
    )

    op.drop_index(
        "ix_communication_conversations_conversation_type",
        table_name="communication_conversations",
    )

    op.drop_table("communication_conversations")