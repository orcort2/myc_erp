from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Index, Integer, String, Table, Column, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.db import Base
from app.models.base import TimestampMixin

communication_participants = Table(
    "communication_participants",
    Base.metadata,
    Column("conversation_id", ForeignKey("communication_conversations.id", ondelete="CASCADE"), primary_key=True),
    Column("user_id", ForeignKey("users.id", ondelete="CASCADE"), primary_key=True),
    Column("joined_at", DateTime(timezone=True), nullable=False, server_default=func.now()),
    Index("ix_communication_participants_user_id", "user_id"),
)


class CommunicationConversation(TimestampMixin, Base):
    __tablename__ = "communication_conversations"
    __table_args__ = (
        Index("ix_communication_conversations_updated", "updated_at"),
        Index("ix_communication_conversations_client", "client_id"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    conversation_type: Mapped[str] = mapped_column(String(30), nullable=False, default="internal", server_default="internal", index=True)
    title: Mapped[str | None] = mapped_column(String(180), nullable=True)
    client_id: Mapped[int | None] = mapped_column(ForeignKey("clients.id", ondelete="SET NULL"), nullable=True)
    created_by_user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"), nullable=False)
    last_message_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True, index=True)
    archived_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    participants: Mapped[list["User"]] = relationship(secondary=communication_participants)
    client: Mapped["Client | None"] = relationship()
    messages: Mapped[list["CommunicationMessage"]] = relationship(
        back_populates="conversation",
        cascade="all, delete-orphan",
        order_by="CommunicationMessage.created_at",
    )


class CommunicationMessage(TimestampMixin, Base):
    __tablename__ = "communication_messages"
    __table_args__ = (
        Index("ix_communication_messages_conversation_created", "conversation_id", "created_at"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    conversation_id: Mapped[int] = mapped_column(ForeignKey("communication_conversations.id", ondelete="CASCADE"), nullable=False, index=True)
    sender_user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"), nullable=False, index=True)
    body: Mapped[str] = mapped_column(Text, nullable=False)
    message_type: Mapped[str] = mapped_column(String(20), nullable=False, default="text", server_default="text")
    delivered_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    read_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    conversation: Mapped[CommunicationConversation] = relationship(back_populates="messages")
    sender: Mapped["User"] = relationship()
