from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.db import Base
from app.models.base import IntegerPkMixin, SoftDeleteMixin, TimestampMixin


class ClientPortalPermission(
    IntegerPkMixin,
    TimestampMixin,
    SoftDeleteMixin,
    Base,
):
    """
    Permisos disponibles para el Portal del Cliente.

    Son independientes de los permisos internos del ERP.
    Los roles del portal consumirán estos permisos.
    """

    __tablename__ = "client_portal_permissions"

    code: Mapped[str] = mapped_column(
        String(120),
        unique=True,
        index=True,
    )

    name: Mapped[str] = mapped_column(
        String(120),
    )

    description: Mapped[str | None] = mapped_column(
        String(255),
    )

    module: Mapped[str] = mapped_column(
        String(80),
        index=True,
    )

    role_permissions: Mapped[list["ClientPortalRolePermission"]] = relationship(
        back_populates="permission",
        cascade="all, delete-orphan",
    )