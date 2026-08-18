"""complete communications foundation

Revision ID: f7c9d1e3a5b7
Revises: e6b8c0d2f4a6
Create Date: 2026-08-17
"""

from alembic import op
import sqlalchemy as sa


revision = "f7c9d1e3a5b7"
down_revision = "e6b8c0d2f4a6"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "communication_conversations", sa.Column("direct_key", sa.String(80))
    )
    op.add_column(
        "communication_conversations", sa.Column("ticket_id", sa.Integer())
    )
    op.add_column(
        "communication_conversations",
        sa.Column(
            "next_message_sequence",
            sa.Integer(),
            server_default="1",
            nullable=False,
        ),
    )
    op.create_foreign_key(
        "fk_communication_conversations_ticket",
        "communication_conversations",
        "operational_tickets",
        ["ticket_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_index(
        "ix_communication_conversations_direct_key",
        "communication_conversations",
        ["direct_key"],
        unique=True,
    )
    op.create_index(
        "ix_communication_conversations_ticket",
        "communication_conversations",
        ["ticket_id"],
    )

    op.add_column(
        "communication_messages", sa.Column("client_message_id", sa.String(80))
    )
    op.add_column(
        "communication_messages", sa.Column("sequence", sa.Integer())
    )
    op.add_column(
        "communication_messages",
        sa.Column("edited_at", sa.DateTime(timezone=True)),
    )
    op.execute(
        """
        WITH ranked AS (
            SELECT id,
                   row_number() OVER (
                       PARTITION BY conversation_id ORDER BY created_at, id
                   ) AS sequence
            FROM communication_messages
        )
        UPDATE communication_messages AS message
        SET sequence = ranked.sequence
        FROM ranked
        WHERE message.id = ranked.id
        """
    )
    op.alter_column("communication_messages", "sequence", nullable=False)
    op.create_unique_constraint(
        "uq_communication_message_sequence",
        "communication_messages",
        ["conversation_id", "sequence"],
    )
    op.create_unique_constraint(
        "uq_communication_message_client_id",
        "communication_messages",
        ["conversation_id", "sender_user_id", "client_message_id"],
    )
    op.execute(
        """
        UPDATE communication_conversations AS conversation
        SET next_message_sequence = COALESCE(messages.maximum, 0) + 1
        FROM (
            SELECT conversation_id, max(sequence) AS maximum
            FROM communication_messages
            GROUP BY conversation_id
        ) AS messages
        WHERE conversation.id = messages.conversation_id
        """
    )
    op.execute(
        """
        WITH direct_participants AS (
            SELECT conversation_id,
                   min(user_id) AS first_user_id,
                   max(user_id) AS second_user_id,
                   count(*) AS participant_count
            FROM communication_participants
            GROUP BY conversation_id
        )
        UPDATE communication_conversations AS conversation
        SET direct_key = direct_participants.first_user_id::text || ':' ||
                         direct_participants.second_user_id::text
        FROM direct_participants
        WHERE conversation.id = direct_participants.conversation_id
          AND conversation.conversation_type = 'internal'
          AND direct_participants.participant_count = 2
        """
    )

    op.add_column(
        "communication_participants",
        sa.Column("last_delivered_message_id", sa.Integer()),
    )
    op.add_column(
        "communication_participants",
        sa.Column("last_read_message_id", sa.Integer()),
    )
    op.add_column(
        "communication_participants",
        sa.Column("last_read_at", sa.DateTime(timezone=True)),
    )
    op.create_foreign_key(
        "fk_communication_participants_delivered_message",
        "communication_participants",
        "communication_messages",
        ["last_delivered_message_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_foreign_key(
        "fk_communication_participants_read_message",
        "communication_participants",
        "communication_messages",
        ["last_read_message_id"],
        ["id"],
        ondelete="SET NULL",
    )

    op.create_table(
        "communication_message_receipts",
        sa.Column("message_id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("delivered_at", sa.DateTime(timezone=True)),
        sa.Column("read_at", sa.DateTime(timezone=True)),
        sa.ForeignKeyConstraint(
            ["message_id"], ["communication_messages.id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("message_id", "user_id"),
    )
    op.create_index(
        "ix_communication_receipts_user_read",
        "communication_message_receipts",
        ["user_id", "read_at"],
    )
    op.create_table(
        "communication_message_mentions",
        sa.Column("message_id", sa.Integer(), nullable=False),
        sa.Column("mentioned_user_id", sa.Integer(), nullable=False),
        sa.Column("mention_kind", sa.String(20), nullable=False),
        sa.Column("mention_key", sa.String(80)),
        sa.Column("read_at", sa.DateTime(timezone=True)),
        sa.ForeignKeyConstraint(
            ["message_id"], ["communication_messages.id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(
            ["mentioned_user_id"], ["users.id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("message_id", "mentioned_user_id"),
    )
    op.create_index(
        "ix_communication_mentions_user_read",
        "communication_message_mentions",
        ["mentioned_user_id", "read_at"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_communication_mentions_user_read",
        table_name="communication_message_mentions",
    )
    op.drop_table("communication_message_mentions")
    op.drop_index(
        "ix_communication_receipts_user_read",
        table_name="communication_message_receipts",
    )
    op.drop_table("communication_message_receipts")
    op.drop_constraint(
        "fk_communication_participants_read_message",
        "communication_participants",
        type_="foreignkey",
    )
    op.drop_constraint(
        "fk_communication_participants_delivered_message",
        "communication_participants",
        type_="foreignkey",
    )
    op.drop_column("communication_participants", "last_read_at")
    op.drop_column("communication_participants", "last_read_message_id")
    op.drop_column("communication_participants", "last_delivered_message_id")
    op.drop_constraint(
        "uq_communication_message_client_id",
        "communication_messages",
        type_="unique",
    )
    op.drop_constraint(
        "uq_communication_message_sequence",
        "communication_messages",
        type_="unique",
    )
    op.drop_column("communication_messages", "edited_at")
    op.drop_column("communication_messages", "sequence")
    op.drop_column("communication_messages", "client_message_id")
    op.drop_index(
        "ix_communication_conversations_ticket",
        table_name="communication_conversations",
    )
    op.drop_index(
        "ix_communication_conversations_direct_key",
        table_name="communication_conversations",
    )
    op.drop_constraint(
        "fk_communication_conversations_ticket",
        "communication_conversations",
        type_="foreignkey",
    )
    op.drop_column("communication_conversations", "next_message_sequence")
    op.drop_column("communication_conversations", "ticket_id")
    op.drop_column("communication_conversations", "direct_key")
