from datetime import datetime

from sqlalchemy import (
    Boolean,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.db import Base
from app.models.base import TimestampMixin


class ActivityThread(TimestampMixin, Base):
    __tablename__ = "activity_threads"
    __table_args__ = (
        UniqueConstraint(
            "entity_type",
            "entity_id",
            name="uq_activity_thread_entity",
        ),
    )

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        index=False,
    )
    entity_type: Mapped[str] = mapped_column(
        String(40),
        index=True,
    )
    entity_id: Mapped[int] = mapped_column(
        Integer,
        index=True,
    )
    created_by_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id"),
        index=True,
    )

    messages: Mapped[list["ActivityMessage"]] = relationship(
        back_populates="thread",
        cascade="all, delete-orphan",
        order_by="ActivityMessage.created_at",
    )


class ActivityMessage(TimestampMixin, Base):
    __tablename__ = "activity_messages"

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        index=False,
    )
    thread_id: Mapped[int] = mapped_column(
        ForeignKey(
            "activity_threads.id",
            ondelete="CASCADE",
        ),
        index=True,
    )
    author_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id"),
        index=True,
    )
    message_type: Mapped[str] = mapped_column(
        String(30),
        default="comment",
        index=True,
    )
    body: Mapped[str] = mapped_column(
        Text,
        default="",
    )
    is_system: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
    )
    is_formal: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
    )
    edited_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
    )
    withdrawn_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
    )
    withdrawn_by_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id"),
        index=True,
    )
    withdrawal_reason: Mapped[str | None] = mapped_column(
        String(80),
    )
    withdrawal_note: Mapped[str | None] = mapped_column(
        Text,
    )
    metadata_json: Mapped[dict | None] = mapped_column(
        JSONB,
        default=dict,
    )

    thread: Mapped["ActivityThread"] = relationship(
        back_populates="messages",
    )
    author: Mapped["User | None"] = relationship(
        foreign_keys=[author_id],
    )
    revisions: Mapped[list["ActivityMessageRevision"]] = relationship(
        back_populates="message",
        cascade="all, delete-orphan",
        order_by="ActivityMessageRevision.created_at",
    )
    attachments: Mapped[list["ActivityAttachment"]] = relationship(
        back_populates="message",
        cascade="all, delete-orphan",
    )
    mentions: Mapped[list["ActivityMention"]] = relationship(
        back_populates="message",
        cascade="all, delete-orphan",
    )


class ActivityMessageRevision(Base):
    __tablename__ = "activity_message_revisions"

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        index=False,
    )
    message_id: Mapped[int] = mapped_column(
        ForeignKey(
            "activity_messages.id",
            ondelete="CASCADE",
        ),
        index=True,
    )
    previous_body: Mapped[str] = mapped_column(
        Text,
    )
    new_body: Mapped[str] = mapped_column(
        Text,
    )
    edited_by_id: Mapped[int] = mapped_column(
        ForeignKey("users.id"),
        index=True,
    )
    reason: Mapped[str | None] = mapped_column(
        String(255),
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )

    message: Mapped["ActivityMessage"] = relationship(
        back_populates="revisions",
    )


class ActivityMention(TimestampMixin, Base):
    __tablename__ = "activity_mentions"
    __table_args__ = (
        UniqueConstraint(
            "message_id",
            "mentioned_user_id",
            name="uq_activity_message_mention",
        ),
    )

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        index=False,
    )
    message_id: Mapped[int] = mapped_column(
        ForeignKey(
            "activity_messages.id",
            ondelete="CASCADE",
        ),
        index=True,
    )
    mentioned_user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id"),
        index=True,
    )
    read_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
    )
    revoked_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
    )

    message: Mapped["ActivityMessage"] = relationship(
        back_populates="mentions",
    )
    mentioned_user: Mapped["User"] = relationship(
        foreign_keys=[mentioned_user_id],
    )


class ActivityAttachment(TimestampMixin, Base):
    __tablename__ = "activity_attachments"

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        index=False,
    )
    message_id: Mapped[int] = mapped_column(
        ForeignKey(
            "activity_messages.id",
            ondelete="CASCADE",
        ),
        index=True,
    )
    original_name: Mapped[str] = mapped_column(
        String(255),
    )
    stored_path: Mapped[str] = mapped_column(
        String(500),
    )
    content_type: Mapped[str | None] = mapped_column(
        String(120),
    )
    size_bytes: Mapped[int] = mapped_column(
        Integer,
    )
    uploaded_by_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id"),
        index=True,
    )
    is_official_evidence: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
    )
    hidden_with_message: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
    )

    message: Mapped["ActivityMessage"] = relationship(
        back_populates="attachments",
    )