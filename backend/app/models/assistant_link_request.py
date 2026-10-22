from datetime import datetime

from sqlalchemy import BigInteger, CheckConstraint, DateTime, ForeignKey, Index, Integer, String, text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base
from app.models.base import TimestampMixin


class AssistantLinkRequest(TimestampMixin, Base):
    """MYC-ASSISTANT-1A: short-lived (5 min) request to bind a private Telegram
    identity to an internal MYC user. It never authorizes by itself: only an
    approval re-proven with the existing biometric credential creates an
    ``AssistantAccountLink``. ``comparison_code`` is for visual comparison only."""

    __tablename__ = "assistant_link_requests"
    __table_args__ = (
        CheckConstraint(
            "status IN ('pending', 'approved', 'rejected', 'expired', 'superseded')",
            name="ck_assistant_link_request_status",
        ),
        # The code lives only while the request is pending; terminal states sanitize it.
        CheckConstraint(
            "(status = 'pending' AND comparison_code IS NOT NULL AND length(comparison_code) = 6) OR "
            "(status <> 'pending' AND comparison_code IS NULL)",
            name="ck_assistant_link_request_code",
        ),
        CheckConstraint(
            "(status = 'pending' AND decided_at IS NULL) OR "
            "(status <> 'pending' AND decided_at IS NOT NULL)",
            name="ck_assistant_link_request_decided",
        ),
        CheckConstraint(
            "status <> 'approved' OR approved_by_user_id IS NOT NULL",
            name="ck_assistant_link_request_approver",
        ),
        # Storage backstop: one open request per Telegram identity.
        Index(
            "uq_assistant_link_requests_pending_telegram",
            "telegram_user_id",
            unique=True,
            postgresql_where=text("status = 'pending'"),
            sqlite_where=text("status = 'pending'"),
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    public_id: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    telegram_user_id: Mapped[int] = mapped_column(BigInteger, index=True)
    telegram_chat_id: Mapped[int] = mapped_column(BigInteger)
    candidate_user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"), index=True)
    status: Mapped[str] = mapped_column(String(20), default="pending", server_default="pending")
    comparison_code: Mapped[str | None] = mapped_column(String(6))
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    decided_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    # Server-derived at approval time (Bearer context + stored biometric
    # credential), never accepted from the client.
    approved_by_user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"))
    approved_device_id: Mapped[int | None] = mapped_column(
        ForeignKey("mobile_trusted_devices.id", ondelete="SET NULL")
    )
