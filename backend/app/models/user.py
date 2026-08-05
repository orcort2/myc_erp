from datetime import datetime

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    ForeignKey,
    String,
    Table,
    event,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.db import Base
from app.models.base import IntegerPkMixin, SoftDeleteMixin, TimestampMixin


user_roles = Table(
    "user_roles",
    Base.metadata,
    Column(
        "user_id",
        ForeignKey(
            "users.id",
            ondelete="CASCADE",
        ),
        primary_key=True,
    ),
    Column(
        "role_id",
        ForeignKey(
            "roles.id",
            ondelete="CASCADE",
        ),
        primary_key=True,
    ),
)


class Role(
    IntegerPkMixin,
    TimestampMixin,
    SoftDeleteMixin,
    Base,
):
    """
    Rol interno del ERP.

    Estos roles pertenecen exclusivamente al personal de MYC y no deben
    utilizarse para administrar permisos del Portal del Cliente.
    """

    __tablename__ = "roles"

    name: Mapped[str] = mapped_column(
        String(80),
        unique=True,
        index=True,
        nullable=False,
    )

    description: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
    )

    users: Mapped[list["User"]] = relationship(
        secondary=user_roles,
        back_populates="roles",
    )


class User(
    IntegerPkMixin,
    TimestampMixin,
    SoftDeleteMixin,
    Base,
):
    """
    Cuenta autenticable del ERP y del Portal del Cliente.

    La identidad de acceso se mantiene en una única tabla, pero los permisos
    se separan por ámbito:

    - Los usuarios internos reciben roles mediante ``roles``.
    - Los usuarios externos reciben membresías y roles del portal mediante
      ``ClientPortalMembership``.

    ``account_type`` identifica el contexto principal de la cuenta, pero no
    debe utilizarse por sí solo como mecanismo de autorización.
    """

    __tablename__ = "users"

    username: Mapped[str] = mapped_column(
        String(80),
        unique=True,
        index=True,
        nullable=False,
    )

    email: Mapped[str] = mapped_column(
        String(255),
        unique=True,
        index=True,
        nullable=False,
    )

    full_name: Mapped[str] = mapped_column(
        String(180),
        nullable=False,
    )

    phone: Mapped[str | None] = mapped_column(String(40), nullable=True)
    job_title: Mapped[str | None] = mapped_column(String(120), nullable=True)
    area: Mapped[str | None] = mapped_column(String(120), nullable=True)
    language: Mapped[str] = mapped_column(String(10), default="es-MX", nullable=False)
    timezone: Mapped[str] = mapped_column(
        String(80), default="America/Mexico_City", nullable=False
    )

    hashed_password: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )

    account_type: Mapped[str] = mapped_column(
        String(30),
        default="internal",
        nullable=False,
        index=True,
    )

    status: Mapped[str] = mapped_column(
        String(30),
        default="active",
        nullable=False,
        index=True,
    )

    email_verified_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    last_login_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        index=True,
    )

    password_changed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    must_change_password: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
    )

    failed_login_attempts: Mapped[int] = mapped_column(
        default=0,
        nullable=False,
    )

    locked_until: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        index=True,
    )

    role_id: Mapped[int | None] = mapped_column(
        ForeignKey(
            "roles.id",
            ondelete="SET NULL",
        ),
        nullable=True,
        index=True,
    )

    role: Mapped[Role | None] = relationship(
        foreign_keys=[role_id],
    )

    roles: Mapped[list[Role]] = relationship(
        secondary=user_roles,
        back_populates="users",
    )

    portal_registration: Mapped["PortalRegistration | None"] = relationship(
        back_populates="user",
        cascade="all, delete-orphan",
        uselist=False,
    )

    portal_memberships: Mapped[list["ClientPortalMembership"]] = relationship(
        foreign_keys="ClientPortalMembership.user_id",
        back_populates="user",
        cascade="all, delete-orphan",
    )


@event.listens_for(User, "before_insert")
def _populate_legacy_internal_identity(_mapper, _connection, target: User) -> None:
    """Conserva creadores internos históricos que todavía sólo proporcionan correo."""
    if not target.username:
        target.username = target.email.strip().lower()
    if not target.account_type:
        target.account_type = "internal"
    if not target.status:
        # Compatibilidad con creadores históricos que sólo proporcionaban
        # `is_active=False`; desde aquí `status` queda como autoridad.
        target.status = "disabled" if target.is_active is False else "active"
    target.is_active = target.status == "active"


@event.listens_for(User, "before_update")
def _synchronize_account_enabled_state(_mapper, _connection, target: User) -> None:
    """`status` es la autoridad funcional; `is_active` refleja habilitación."""
    target.is_active = target.status == "active"
