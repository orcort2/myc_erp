from sqlalchemy import ForeignKey, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.db import Base
from app.models.base import IntegerPkMixin, TimestampMixin


class ClientPortalMembershipRole(
    IntegerPkMixin,
    TimestampMixin,
    Base,
):
    """
    Asignación de un rol a una membresía del Portal del Cliente.

    Materializa la relación muchos-a-muchos entre las membresías y los roles:

    - una membresía puede recibir múltiples roles;
    - un rol puede asignarse a múltiples membresías;
    - el mismo rol puede utilizarse en varias cuentas del mismo cliente;
    - una misma combinación de membresía y rol no puede repetirse.
    """

    __tablename__ = "client_portal_membership_roles"

    __table_args__ = (
        UniqueConstraint(
            "membership_id",
            "role_id",
            name="uq_client_portal_membership_role",
        ),
    )

    membership_id: Mapped[int] = mapped_column(
        ForeignKey(
            "client_portal_memberships.id",
            ondelete="CASCADE",
        ),
        nullable=False,
        index=True,
    )

    role_id: Mapped[int] = mapped_column(
        ForeignKey(
            "client_portal_roles.id",
            ondelete="CASCADE",
        ),
        nullable=False,
        index=True,
    )

    membership: Mapped["ClientPortalMembership"] = relationship(
        back_populates="membership_roles",
    )

    role: Mapped["ClientPortalRole"] = relationship(
        back_populates="membership_roles",
    )