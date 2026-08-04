from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.db import Base
from app.models.base import IntegerPkMixin, SoftDeleteMixin, TimestampMixin


class PortalRegistration(
    IntegerPkMixin,
    TimestampMixin,
    SoftDeleteMixin,
    Base,
):
    """
    Registro inicial de una cuenta externa para acceder al Portal del Cliente.

    Esta entidad conserva la información declarada por la persona durante su
    registro y el estado general del proceso de incorporación.

    No representa una vinculación definitiva con un cliente del ERP. La
    vinculación se solicita mediante ``ClientLinkRequest`` y, cuando es
    aprobada, produce una ``ClientPortalMembership``.

    La información de autenticación permanece en ``User``:

    - correo electrónico;
    - nombre completo;
    - contraseña cifrada.

    Esta tabla almacena únicamente información adicional del registro y su
    trazabilidad operativa.
    """

    __tablename__ = "portal_registrations"

    __table_args__ = (
        UniqueConstraint(
            "user_id",
            name="uq_portal_registration_user",
        ),
    )

    user_id: Mapped[int] = mapped_column(
        ForeignKey(
            "users.id",
            ondelete="CASCADE",
        ),
        nullable=False,
        unique=True,
        index=True,
    )

    declared_company_name: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        index=True,
    )

    declared_company_rfc: Mapped[str | None] = mapped_column(
        String(13),
        nullable=True,
        index=True,
    )

    contact_phone: Mapped[str | None] = mapped_column(
        String(40),
        nullable=True,
    )

    job_title: Mapped[str | None] = mapped_column(
        String(120),
        nullable=True,
    )

    status: Mapped[str] = mapped_column(
        String(30),
        default="pending_email_verification",
        nullable=False,
        index=True,
    )

    email_verified_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    verification_token_hash: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
    )

    verification_token_expires_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        index=True,
    )

    last_internal_review_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    internal_notes: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    user: Mapped["User"] = relationship(
        back_populates="portal_registration",
    )

    link_requests: Mapped[list["ClientLinkRequest"]] = relationship(
        back_populates="portal_registration",
        cascade="all, delete-orphan",
    )