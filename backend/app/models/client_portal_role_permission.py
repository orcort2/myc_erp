from sqlalchemy import ForeignKey, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.db import Base
from app.models.base import IntegerPkMixin, TimestampMixin


class ClientPortalRolePermission(
    IntegerPkMixin,
    TimestampMixin,
    Base,
):
    """
    Asignación de un permiso a un rol del Portal del Cliente.

    Esta entidad materializa la relación muchos-a-muchos entre:

    - client_portal_roles
    - client_portal_permissions

    Un mismo permiso puede pertenecer a múltiples roles.
    Un mismo rol puede contener múltiples permisos.
    """

    __tablename__ = "client_portal_role_permissions"

    __table_args__ = (
        UniqueConstraint(
            "role_id",
            "permission_id",
            name="uq_client_portal_role_permission",
        ),
    )

    role_id: Mapped[int] = mapped_column(
        ForeignKey(
            "client_portal_roles.id",
            ondelete="CASCADE",
        ),
        nullable=False,
        index=True,
    )

    permission_id: Mapped[int] = mapped_column(
        ForeignKey(
            "client_portal_permissions.id",
            ondelete="CASCADE",
        ),
        nullable=False,
        index=True,
    )

    role: Mapped["ClientPortalRole"] = relationship(
        back_populates="role_permissions",
    )

    permission: Mapped["ClientPortalPermission"] = relationship(
        back_populates="role_permissions",
    )