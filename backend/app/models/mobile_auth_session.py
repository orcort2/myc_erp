from datetime import datetime

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base
from app.models.base import TimestampMixin


class MobileAuthSession(TimestampMixin, Base):
    """One refresh generation; consumed rows must survive for reuse detection."""

    __tablename__ = "mobile_auth_sessions"
    __table_args__ = (
        CheckConstraint(
            "(actor_type = 'internal' AND client_id IS NULL AND membership_id IS NULL) OR "
            "(actor_type = 'client' AND client_id IS NOT NULL AND membership_id IS NOT NULL)",
            name="ck_mobile_session_actor_scope",
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    device_id: Mapped[int] = mapped_column(ForeignKey("mobile_trusted_devices.id", ondelete="CASCADE"), index=True)
    family_id: Mapped[str] = mapped_column(String(36), index=True)
    refresh_token_hash: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    # A nullable, unique fingerprint makes the temporary JWT migration single-use.
    # It is retained on the first generation, never copied to successors.
    legacy_refresh_token_hash: Mapped[str | None] = mapped_column(String(64), unique=True, index=True)
    actor_type: Mapped[str] = mapped_column(String(20))
    client_id: Mapped[int | None] = mapped_column(ForeignKey("clients.id", ondelete="CASCADE"))
    membership_id: Mapped[int | None] = mapped_column(ForeignKey("client_portal_memberships.id", ondelete="CASCADE"))
    last_used_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), index=True)
    replaced_by_id: Mapped[int | None] = mapped_column(ForeignKey("mobile_auth_sessions.id", ondelete="SET NULL"), unique=True)
    reuse_detected_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
