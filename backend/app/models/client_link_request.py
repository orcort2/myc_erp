from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.db import Base
from app.models.base import IntegerPkMixin, TimestampMixin


class ClientLinkRequest(
    IntegerPkMixin,
    TimestampMixin,
    Base,
):
    """
    Solicitud administrativa para vincular una cuenta del portal con un
    cliente existente del ERP.

    La solicitud conserva el proceso de revisión separado de:

    - PortalRegistration: registra el alta inicial de la cuenta.
    - ClientPortalMembership: representa la vinculación finalmente aprobada.

    Flujo esperado:

        pending
            -> under_review
            -> approved

        pending / under_review
            -> rejected
            -> cancelled
            -> expired

    Una solicitud aprobada debe producir una membresía activa mediante el
    servicio de negocio correspondiente. El modelo no ejecuta esa operación
    automáticamente.
    """

    __tablename__ = "client_link_requests"

    __table_args__ = (
        UniqueConstraint(
            "portal_registration_id",
            "proposed_client_id",
            name="uq_client_link_request_registration_client",
        ),
    )

    portal_registration_id: Mapped[int] = mapped_column(
        ForeignKey(
            "portal_registrations.id",
            ondelete="CASCADE",
        ),
        nullable=False,
        index=True,
    )

    proposed_client_id: Mapped[int] = mapped_column(
        ForeignKey(
            "clients.id",
            ondelete="CASCADE",
        ),
        nullable=False,
        index=True,
    )

    requested_by: Mapped[int] = mapped_column(
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

    request_reason: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    reviewed_by: Mapped[int | None] = mapped_column(
        ForeignKey(
            "users.id",
            ondelete="SET NULL",
        ),
        nullable=True,
        index=True,
    )

    reviewed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    resolution_reason: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    resolved_by: Mapped[int | None] = mapped_column(
        ForeignKey(
            "users.id",
            ondelete="SET NULL",
        ),
        nullable=True,
        index=True,
    )

    resolved_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    expires_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
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

    portal_registration: Mapped["PortalRegistration"] = relationship(
        back_populates="link_requests",
    )

    proposed_client: Mapped["Client"] = relationship(
        back_populates="portal_link_requests",
    )

    requested_by_user: Mapped["User"] = relationship(
        foreign_keys=[requested_by],
    )

    reviewed_by_user: Mapped["User | None"] = relationship(
        foreign_keys=[reviewed_by],
    )

    resolved_by_user: Mapped["User | None"] = relationship(
        foreign_keys=[resolved_by],
    )

    resulting_membership: Mapped["ClientPortalMembership | None"] = relationship(
        foreign_keys=[resulting_membership_id],
        back_populates="source_link_request",
    )