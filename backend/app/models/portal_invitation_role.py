from sqlalchemy import ForeignKey, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.db import Base
from app.models.base import IntegerPkMixin, TimestampMixin


class PortalInvitationRole(
    IntegerPkMixin,
    TimestampMixin,
    Base,
):
    """
    Asignación de un rol del Portal del Cliente a una invitación.

    Esta entidad permite que:

    - una invitación incluya uno o varios roles;
    - el mismo rol se utilice en múltiples invitaciones;
    - una misma combinación de invitación y rol no se repita.

    Los roles aquí almacenados son una preasignación. Cuando la invitación es
    aceptada, el servicio de negocio debe crear las correspondientes
    ``ClientPortalMembershipRole`` para la membresía resultante.
    """

    __tablename__ = "portal_invitation_roles"

    __table_args__ = (
        UniqueConstraint(
            "invitation_id",
            "role_id",
            name="uq_portal_invitation_role",
        ),
    )

    invitation_id: Mapped[int] = mapped_column(
        ForeignKey(
            "portal_invitations.id",
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

    invitation: Mapped["PortalInvitation"] = relationship(
        back_populates="invitation_roles",
    )

    role: Mapped["ClientPortalRole"] = relationship(
        back_populates="invitation_roles",
    )