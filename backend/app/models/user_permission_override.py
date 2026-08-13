from sqlalchemy import (
    CheckConstraint,
    ForeignKey,
    String,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.db import Base
from app.models.base import IntegerPkMixin, TimestampMixin


class UserPermissionOverride(
    IntegerPkMixin,
    TimestampMixin,
    Base,
):
    """
    Excepción individual de autorización para un usuario interno.

    No modifica los roles ni ROLE_PERMISSIONS. Permite conceder o denegar
    explícitamente un permiso a un usuario concreto.

    La resolución efectiva de estos overrides se implementa en la capa
    de autorización y no forma parte del modelo.
    """

    __tablename__ = "user_permission_overrides"

    user_id: Mapped[int] = mapped_column(
        ForeignKey(
            "users.id",
            ondelete="CASCADE",
        ),
        nullable=False,
        index=True,
    )

    permission: Mapped[str] = mapped_column(
        String(160),
        nullable=False,
        index=True,
    )

    effect: Mapped[str] = mapped_column(
        String(10),
        nullable=False,
    )

    user: Mapped["User"] = relationship(
        back_populates="permission_overrides",
    )

    __table_args__ = (
        UniqueConstraint(
            "user_id",
            "permission",
            name="uq_user_permission_override_user_permission",
        ),
        CheckConstraint(
            "effect IN ('allow', 'deny')",
            name="ck_user_permission_override_effect",
        ),
    )


from app.models.user import User  # noqa: E402
