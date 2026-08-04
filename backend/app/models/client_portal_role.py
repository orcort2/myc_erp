from sqlalchemy import Boolean, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.db import Base
from app.models.base import IntegerPkMixin, SoftDeleteMixin, TimestampMixin


class ClientPortalRole(
    IntegerPkMixin,
    TimestampMixin,
    SoftDeleteMixin,
    Base,
):
    """
    Rol asignable a las cuentas vinculadas al Portal del Cliente.

    Los roles del portal son independientes de los roles internos del ERP.

    Un rol puede ser:

    - Global:
      Definido por MYC y disponible para todos los clientes.
      En este caso, ``client_id`` es nulo.

    - Personalizado:
      Definido exclusivamente para un cliente.
      En este caso, ``client_id`` identifica al propietario del rol.

    El mismo rol puede asignarse a múltiples membresías. No existe una
    restricción que limite un rol a una sola cuenta dentro del cliente.
    """

    __tablename__ = "client_portal_roles"

    client_id: Mapped[int | None] = mapped_column(
        ForeignKey(
            "clients.id",
            ondelete="CASCADE",
        ),
        nullable=True,
        index=True,
    )

    code: Mapped[str] = mapped_column(
        String(160),
        unique=True,
        index=True,
        nullable=False,
    )

    name: Mapped[str] = mapped_column(
        String(120),
        nullable=False,
        index=True,
    )

    description: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    is_system: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
        index=True,
    )

    client: Mapped["Client | None"] = relationship(
        back_populates="portal_roles",
    )

    role_permissions: Mapped[list["ClientPortalRolePermission"]] = relationship(
        back_populates="role",
        cascade="all, delete-orphan",
    )

    membership_roles: Mapped[list["ClientPortalMembershipRole"]] = relationship(
        back_populates="role",
        cascade="all, delete-orphan",
    )

    invitation_roles: Mapped[list["PortalInvitationRole"]] = relationship(
        back_populates="role",
        cascade="all, delete-orphan",
    )