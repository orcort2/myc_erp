from datetime import datetime

from sqlalchemy import (
    Column,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Table,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.db import Base
from app.models.base import TimestampMixin

communication_participants = Table(
    "communication_participants",
    Base.metadata,
    Column("conversation_id", ForeignKey("communication_conversations.id", ondelete="CASCADE"), primary_key=True),
    Column("user_id", ForeignKey("users.id", ondelete="CASCADE"), primary_key=True),
    Column("joined_at", DateTime(timezone=True), nullable=False, server_default=func.now()),
    Column(
        "last_delivered_message_id",
        ForeignKey("communication_messages.id", ondelete="SET NULL"),
        nullable=True,
    ),
    Column(
        "last_read_message_id",
        ForeignKey("communication_messages.id", ondelete="SET NULL"),
        nullable=True,
    ),
    Column("last_read_at", DateTime(timezone=True), nullable=True),
    Index("ix_communication_participants_user_id", "user_id"),
)


class CommunicationConversation(TimestampMixin, Base):
    __tablename__ = "communication_conversations"
    __table_args__ = (
        Index("ix_communication_conversations_updated", "updated_at"),
        Index("ix_communication_conversations_client", "client_id"),
        Index("ix_communication_conversations_ticket", "ticket_id"),
        Index(
            "ix_communication_conversations_direct_key", "direct_key", unique=True
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    conversation_type: Mapped[str] = mapped_column(String(30), nullable=False, default="internal", server_default="internal", index=True)
    title: Mapped[str | None] = mapped_column(String(180), nullable=True)
    direct_key: Mapped[str | None] = mapped_column(String(80), nullable=True)
    client_id: Mapped[int | None] = mapped_column(ForeignKey("clients.id", ondelete="SET NULL"), nullable=True)
    ticket_id: Mapped[int | None] = mapped_column(
        ForeignKey("operational_tickets.id", ondelete="SET NULL"), nullable=True
    )
    created_by_user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"), nullable=False)
    next_message_sequence: Mapped[int] = mapped_column(
        Integer, nullable=False, default=1, server_default="1"
    )
    last_message_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True, index=True)
    archived_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    participants: Mapped[list["User"]] = relationship(secondary=communication_participants)
    client: Mapped["Client | None"] = relationship()
    ticket: Mapped["OperationalTicket | None"] = relationship()
    messages: Mapped[list["CommunicationMessage"]] = relationship(
        back_populates="conversation",
        cascade="all, delete-orphan",
        order_by="CommunicationMessage.created_at",
    )


class CommunicationMessage(TimestampMixin, Base):
    __tablename__ = "communication_messages"
    __table_args__ = (
        Index("ix_communication_messages_conversation_created", "conversation_id", "created_at"),
        UniqueConstraint(
            "conversation_id", "sequence", name="uq_communication_message_sequence"
        ),
        UniqueConstraint(
            "conversation_id",
            "sender_user_id",
            "client_message_id",
            name="uq_communication_message_client_id",
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    conversation_id: Mapped[int] = mapped_column(ForeignKey("communication_conversations.id", ondelete="CASCADE"), nullable=False, index=True)
    sender_user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"), nullable=False, index=True)
    client_message_id: Mapped[str | None] = mapped_column(String(80), nullable=True)
    sequence: Mapped[int] = mapped_column(Integer, nullable=False)
    body: Mapped[str] = mapped_column(Text, nullable=False)
    message_type: Mapped[str] = mapped_column(String(20), nullable=False, default="text", server_default="text")
    delivered_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    read_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    edited_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    conversation: Mapped[CommunicationConversation] = relationship(back_populates="messages")
    sender: Mapped["User"] = relationship()
    receipts: Mapped[list["CommunicationMessageReceipt"]] = relationship(
        back_populates="message", cascade="all, delete-orphan"
    )
    mentions: Mapped[list["CommunicationMessageMention"]] = relationship(
        back_populates="message", cascade="all, delete-orphan"
    )


class CommunicationMessageReceipt(Base):
    __tablename__ = "communication_message_receipts"
    __table_args__ = (
        Index("ix_communication_receipts_user_read", "user_id", "read_at"),
    )

    message_id: Mapped[int] = mapped_column(
        ForeignKey("communication_messages.id", ondelete="CASCADE"), primary_key=True
    )
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), primary_key=True
    )
    delivered_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    read_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    message: Mapped[CommunicationMessage] = relationship(back_populates="receipts")
    user: Mapped["User"] = relationship()


class CommunicationMessageMention(Base):
    __tablename__ = "communication_message_mentions"
    __table_args__ = (
        Index("ix_communication_mentions_user_read", "mentioned_user_id", "read_at"),
    )

    message_id: Mapped[int] = mapped_column(
        ForeignKey("communication_messages.id", ondelete="CASCADE"), primary_key=True
    )
    mentioned_user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), primary_key=True
    )
    mention_kind: Mapped[str] = mapped_column(String(20), nullable=False)
    mention_key: Mapped[str | None] = mapped_column(String(80))
    read_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    message: Mapped[CommunicationMessage] = relationship(back_populates="mentions")
    mentioned_user: Mapped["User"] = relationship()
