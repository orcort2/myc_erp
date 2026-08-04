from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.db import Base
from app.models.base import IntegerPkMixin, TimestampMixin


class ClientPortalMembership(
    IntegerPkMixin,
    TimestampMixin,
    Base,
):
    """
    Vinculación entre una cuenta de usuario y un cliente del ERP.

    Un cliente puede tener múltiples cuentas vinculadas.

    Cada membresía representa el acceso de una persona concreta a la
    organización y mantiene su propio estado, roles y trazabilidad.

    Los roles no se almacenan directamente en esta tabla. Se asignan mediante
    ``ClientPortalMembershipRole``, lo que permite:

    - asignar varios roles a una cuenta;
    - utilizar el mismo rol en varias cuentas;
    - modificar roles sin alterar la vinculación con el cliente.
    """

    __tablename__ = "client_portal_memberships"

    __table_args__ = (
        UniqueConstraint(
            "client_id",
            "user_id",
            name="uq_client_portal_membership_client_user",
        ),
    )

    client_id: Mapped[int] = mapped_column(
        ForeignKey(
            "clients.id",
            ondelete="CASCADE",
        ),
        nullable=False,
        index=True,
    )

    user_id: Mapped[int] = mapped_column(
        ForeignKey(
            "users.id",
            ondelete="CASCADE",
        ),
        nullable=False,
        index=True,
    )

    status: Mapped[str] = mapped_column(
        String(30),
        default="pending",
        nullable=False,
        index=True,
    )

    is_primary_contact: Mapped[bool] = mapped_column(
        default=False,
        nullable=False,
        index=True,
    )

    approved_by: Mapped[int | None] = mapped_column(
        ForeignKey(
            "users.id",
            ondelete="SET NULL",
        ),
        nullable=True,
        index=True,
    )

    approved_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    suspended_by: Mapped[int | None] = mapped_column(
        ForeignKey(
            "users.id",
            ondelete="SET NULL",
        ),
        nullable=True,
        index=True,
    )

    suspended_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    suspension_reason: Mapped[str | None] = mapped_column(
        String(500),
        nullable=True,
    )

    revoked_by: Mapped[int | None] = mapped_column(
        ForeignKey(
            "users.id",
            ondelete="SET NULL",
        ),
        nullable=True,
        index=True,
    )

    revoked_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    revocation_reason: Mapped[str | None] = mapped_column(
        String(500),
        nullable=True,
    )

    client: Mapped["Client"] = relationship(
        back_populates="portal_memberships",
    )

    user: Mapped["User"] = relationship(
        foreign_keys=[user_id],
        back_populates="portal_memberships",
    )

    approved_by_user: Mapped["User | None"] = relationship(
        foreign_keys=[approved_by],
    )

    suspended_by_user: Mapped["User | None"] = relationship(
        foreign_keys=[suspended_by],
    )

    revoked_by_user: Mapped["User | None"] = relationship(
        foreign_keys=[revoked_by],
    )

    membership_roles: Mapped[list["ClientPortalMembershipRole"]] = relationship(
        back_populates="membership",
        cascade="all, delete-orphan",
    )

    source_link_request: Mapped["ClientLinkRequest | None"] = relationship(
        foreign_keys="ClientLinkRequest.resulting_membership_id",
        back_populates="resulting_membership",
        uselist=False,
    )

    source_invitation: Mapped["PortalInvitation | None"] = relationship(
        foreign_keys="PortalInvitation.resulting_membership_id",
        back_populates="resulting_membership",
        uselist=False,
    )