from sqlalchemy import Boolean, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.db import Base
from app.models.base import IntegerPkMixin, SoftDeleteMixin, TimestampMixin


class ClientPortal(
    IntegerPkMixin,
    TimestampMixin,
    SoftDeleteMixin,
    Base,
):
    """
    Espacio digital y configuración del Portal del Cliente.

    Cada cliente puede tener un único portal. Esta entidad mantiene la
    configuración propia de la experiencia del portal sin contaminar el
    expediente fiscal, comercial u operativo almacenado en ``Client``.

    La autorización efectiva continúa dependiendo de:

    - ClientPortalMembership
    - ClientPortalRole
    - ClientPortalPermission

    Esta entidad configura el portal, pero no concede acceso por sí misma.
    """

    __tablename__ = "client_portals"

    __table_args__ = (
        UniqueConstraint(
            "client_id",
            name="uq_client_portal_client",
        ),
    )

    client_id: Mapped[int] = mapped_column(
        ForeignKey(
            "clients.id",
            ondelete="CASCADE",
        ),
        nullable=False,
        unique=True,
        index=True,
    )

    display_name: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
    )

    logo_path: Mapped[str | None] = mapped_column(
        String(500),
        nullable=True,
    )

    primary_color: Mapped[str | None] = mapped_column(
        String(20),
        nullable=True,
    )

    language: Mapped[str] = mapped_column(
        String(10),
        default="es-MX",
        nullable=False,
    )

    timezone: Mapped[str] = mapped_column(
        String(80),
        default="America/Mexico_City",
        nullable=False,
    )

    default_home_page: Mapped[str] = mapped_column(
        String(80),
        default="dashboard",
        nullable=False,
    )

    welcome_message: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    allow_self_registration: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False,
    )

    allow_invitations: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False,
    )

    require_mfa: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
    )

    session_timeout_minutes: Mapped[int] = mapped_column(
        Integer,
        default=480,
        nullable=False,
    )

    password_expiration_days: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
    )

    email_notifications_enabled: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False,
    )

    is_enabled: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False,
        index=True,
    )

    created_by: Mapped[int | None] = mapped_column(
        ForeignKey(
            "users.id",
            ondelete="SET NULL",
        ),
        nullable=True,
        index=True,
    )

    updated_by: Mapped[int | None] = mapped_column(
        ForeignKey(
            "users.id",
            ondelete="SET NULL",
        ),
        nullable=True,
        index=True,
    )

    client: Mapped["Client"] = relationship(
        back_populates="portal",
    )

    created_by_user: Mapped["User | None"] = relationship(
        foreign_keys=[created_by],
    )

    updated_by_user: Mapped["User | None"] = relationship(
        foreign_keys=[updated_by],
    )