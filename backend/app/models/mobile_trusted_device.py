from datetime import datetime

from sqlalchemy import Boolean, CheckConstraint, DateTime, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base
from app.models.base import TimestampMixin


class MobileTrustedDevice(TimestampMixin, Base):
    """Installation identity for Mobile authentication; independent of Expo Push."""

    __tablename__ = "mobile_trusted_devices"
    __table_args__ = (
        UniqueConstraint("user_id", "device_uuid", name="uq_mobile_device_user_uuid"),
        CheckConstraint("platform IN ('ios', 'android')", name="ck_mobile_device_platform"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    device_uuid: Mapped[str] = mapped_column(String(128))
    platform: Mapped[str] = mapped_column(String(20))
    device_name: Mapped[str | None] = mapped_column(String(160))
    app_version: Mapped[str | None] = mapped_column(String(40))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, server_default="true")
    trusted_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    last_seen_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
