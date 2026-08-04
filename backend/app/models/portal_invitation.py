from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.db import Base
from app.models.base import IntegerPkMixin, SoftDeleteMixin, TimestampMixin


class PortalInvitation(
    IntegerPkMixin,
    TimestampMixin,
    SoftDeleteMixin,
    Base,
):
    """
    Invitación preautorizada para registrar una cuenta del Portal del Cliente.

    A diferencia de ``PortalRegistration``, esta entidad ya contiene un cliente
    definido por MYC. Cuando la persona acepta la invitación:

    - se crea o valida su cuenta de usuario;
    - se crea una membresía activa con el cliente;
    - se asignan los roles incluidos en la invitación;
    - la invitación queda consumida.

    El cliente, los roles y el correo invitado se obtienen exclusivamente desde
    esta entidad. El frontend no puede reemplazarlos durante la aceptación.
    """

    __tablename__ = "portal_invitations"

    client_id: Mapped[int] = mapped_column(
        ForeignKey(
            "clients.id",
            ondelete="CASCADE",
        ),
        nullable=False,
        index=True,
    )

    email: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        index=True,
    )

    full_name: Mapped[str | None] = mapped_column(
        String(180),
        nullable=True,
    )

    invited_by: Mapped[int] = mapped_column(
        ForeignKey(
            "users.id",
            ondelete="RESTRICT",
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

    token_hash: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        unique=True,
        index=True,
    )

    expires_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        index=True,
    )

    accepted_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    cancelled_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    cancelled_by: Mapped[int | None] = mapped_column(
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

    revoked_by: Mapped[int | None] = mapped_column(
        ForeignKey(
            "users.id",
            ondelete="SET NULL",
        ),
        nullable=True,
        index=True,
    )

    accepted_user_id: Mapped[int | None] = mapped_column(
        ForeignKey(
            "users.id",
            ondelete="SET NULL",
        ),
        nullable=True,
        index=True,
    )

    resulting_membership_id: Mapped[int | None] = mapped_column(
        ForeignKey(
            "client_portal_memberships.id",
            ondelete="SET NULL",
        ),
        nullable=True,
        unique=True,
        index=True,
    )

    notes: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    client: Mapped["Client"] = relationship(
        back_populates="portal_invitations",
    )

    invited_by_user: Mapped["User"] = relationship(
        foreign_keys=[invited_by],
    )

    cancelled_by_user: Mapped["User | None"] = relationship(
        foreign_keys=[cancelled_by],
    )

    revoked_by_user: Mapped["User | None"] = relationship(
        foreign_keys=[revoked_by],
    )

    accepted_user: Mapped["User | None"] = relationship(
        foreign_keys=[accepted_user_id],
    )

    resulting_membership: Mapped["ClientPortalMembership | None"] = relationship(
        foreign_keys=[resulting_membership_id],
        back_populates="source_invitation",
    )

    invitation_roles: Mapped[list["PortalInvitationRole"]] = relationship(
        back_populates="invitation",
        cascade="all, delete-orphan",
    )