from datetime import datetime

from sqlalchemy import (
    Boolean,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    JSON,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.db import Base
from app.models.base import TimestampMixin

JSON_DOCUMENT = JSON().with_variant(JSONB, "postgresql")


class Notification(TimestampMixin, Base):
    __tablename__ = "notifications"
    __table_args__ = (
        UniqueConstraint(
            "recipient_user_id",
            "notification_type",
            "activity_message_id",
            name="uq_notification_recipient_type_message",
        ),
        Index(
            "ix_notifications_recipient_read_created",
            "recipient_user_id",
            "read_at",
            "created_at",
        ),
        Index(
            "ix_notifications_entity",
            "entity_type",
            "entity_id",
        ),
    )

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        index=False,
    )

    recipient_user_id: Mapped[int] = mapped_column(
        ForeignKey(
            "users.id",
            ondelete="CASCADE",
        ),
        nullable=False,
        index=True,
    )

    actor_user_id: Mapped[int | None] = mapped_column(
        ForeignKey(
            "users.id",
            ondelete="SET NULL",
        ),
        nullable=True,
        index=True,
    )

    notification_type: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        index=True,
    )

    event_key: Mapped[str | None] = mapped_column(
        String(220), nullable=True, unique=True, index=True
    )

    title: Mapped[str] = mapped_column(
        String(180),
        nullable=False,
    )

    body: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    entity_type: Mapped[str | None] = mapped_column(
        String(40),
        nullable=True,
        index=True,
    )

    entity_id: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
        index=True,
    )

    activity_message_id: Mapped[int | None] = mapped_column(
        ForeignKey(
            "activity_messages.id",
            ondelete="CASCADE",
        ),
        nullable=True,
        index=True,
    )

    priority: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="normal",
        server_default="normal",
        index=True,
    )

    metadata_json: Mapped[dict] = mapped_column(
        JSON_DOCUMENT,
        nullable=False,
        default=dict,
        server_default="{}",
    )

    read_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        index=True,
    )

    delivery_status: Mapped[str] = mapped_column(
        String(30), nullable=False, default="pending", server_default="pending", index=True
    )
    push_attempted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    push_delivered_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    error_code: Mapped[str | None] = mapped_column(String(80))

    dismissed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        index=True,
    )

    revoked_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        index=True,
    )

    recipient_user: Mapped["User"] = relationship(
        foreign_keys=[recipient_user_id],
    )

    actor_user: Mapped["User | None"] = relationship(
        foreign_keys=[actor_user_id],
    )

    activity_message: Mapped["ActivityMessage | None"] = relationship(
        foreign_keys=[activity_message_id],
    )


class PushDevice(TimestampMixin, Base):
    __tablename__ = "push_devices"
    __table_args__ = (Index("ix_push_devices_user_active", "user_id", "is_active"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=False)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    expo_push_token: Mapped[str] = mapped_column(
        String(255), nullable=False, unique=True, index=True
    )
    platform: Mapped[str] = mapped_column(String(20), nullable=False)
    device_name: Mapped[str | None] = mapped_column(String(160))
    app_version: Mapped[str | None] = mapped_column(String(40))
    is_active: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True, server_default="true", index=True
    )
    last_seen_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    user: Mapped["User"] = relationship(foreign_keys=[user_id])
