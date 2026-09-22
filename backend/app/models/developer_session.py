from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base
from app.models.base import TimestampMixin


class DeveloperSession(TimestampMixin, Base):
    """DEV-0: short-lived (10 min, non-renewing) Developer infrastructure
    authority, unlocked by re-proving the same real biometric credential
    BIOMETRIC-2 already authors -- never a second biometric authority, never
    a substitute for MobileAuthSession, never survives logout and carries no
    refresh. See docs/architecture/MOBILE_DEVELOPER_AUTHORITY.md."""

    __tablename__ = "developer_sessions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    device_id: Mapped[int] = mapped_column(
        ForeignKey("mobile_trusted_devices.id", ondelete="CASCADE"), index=True
    )
    mobile_session_id: Mapped[int] = mapped_column(
        ForeignKey("mobile_auth_sessions.id", ondelete="CASCADE"), index=True
    )
    token_hash: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    last_used_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), index=True)
    # "expired" | "user_lock" | "authority_revoked" -- never free text from a caller.
    revocation_reason: Mapped[str | None] = mapped_column(String(30))
