from datetime import datetime

from sqlalchemy import BigInteger, CheckConstraint, DateTime, ForeignKey, Index, Integer, String, text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base
from app.models.base import TimestampMixin


class AssistantAccountLink(TimestampMixin, Base):
    """MYC-ASSISTANT-1A: active/revoked binding between an internal MYC user and
    one private Telegram identity. Rows are never deleted; revocation keeps history."""

    __tablename__ = "assistant_account_links"
    __table_args__ = (
        CheckConstraint("status IN ('active', 'revoked')", name="ck_assistant_account_link_status"),
        CheckConstraint(
            "(status = 'active' AND revoked_at IS NULL AND revocation_reason IS NULL) OR "
            "(status = 'revoked' AND revoked_at IS NOT NULL AND revocation_reason IS NOT NULL)",
            name="ck_assistant_account_link_revocation",
        ),
        # At most one ACTIVE link per MYC user, per Telegram user and per chat.
        Index("uq_assistant_links_active_user", "user_id", unique=True,
              postgresql_where=text("status = 'active'"), sqlite_where=text("status = 'active'")),
        Index("uq_assistant_links_active_telegram_user", "telegram_user_id", unique=True,
              postgresql_where=text("status = 'active'"), sqlite_where=text("status = 'active'")),
        Index("uq_assistant_links_active_telegram_chat", "telegram_chat_id", unique=True,
              postgresql_where=text("status = 'active'"), sqlite_where=text("status = 'active'")),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"), index=True)
    telegram_user_id: Mapped[int] = mapped_column(BigInteger, index=True)
    telegram_chat_id: Mapped[int] = mapped_column(BigInteger)
    link_request_id: Mapped[int] = mapped_column(
        ForeignKey("assistant_link_requests.id", ondelete="RESTRICT"), unique=True
    )
    status: Mapped[str] = mapped_column(String(20), default="active", server_default="active")
    linked_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    revoked_by_user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"))
    # Canonical reason (see app.services.assistant_account_linking.REVOKE_*), never free text.
    revocation_reason: Mapped[str | None] = mapped_column(String(30))
