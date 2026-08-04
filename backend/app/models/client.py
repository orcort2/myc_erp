from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.db import Base
from app.models.base import IntegerPkMixin, SoftDeleteMixin, TimestampMixin


class Client(
    IntegerPkMixin,
    TimestampMixin,
    SoftDeleteMixin,
    Base,
):
    __tablename__ = "clients"

    client_type: Mapped[str] = mapped_column(
        String(30),
        default="persona_moral",
        nullable=False,
        index=True,
    )

    legal_name: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        index=True,
    )

    commercial_name: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
        index=True,
    )

    rfc: Mapped[str | None] = mapped_column(
        String(13),
        nullable=True,
        index=True,
    )

    curp: Mapped[str | None] = mapped_column(
        String(18),
        nullable=True,
        index=True,
    )

    first_name: Mapped[str | None] = mapped_column(
        String(120),
        nullable=True,
    )

    first_last_name: Mapped[str | None] = mapped_column(
        String(120),
        nullable=True,
    )

    second_last_name: Mapped[str | None] = mapped_column(
        String(120),
        nullable=True,
    )

    email: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
        index=True,
    )

    phone: Mapped[str | None] = mapped_column(
        String(40),
        nullable=True,
    )

    tax_regime: Mapped[str | None] = mapped_column(
        String(120),
        nullable=True,
    )

    cfdi_use: Mapped[str | None] = mapped_column(
        String(40),
        nullable=True,
    )

    street_type: Mapped[str | None] = mapped_column(
        String(80),
        nullable=True,
    )

    street: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
    )

    exterior_number: Mapped[str | None] = mapped_column(
        String(40),
        nullable=True,
    )

    interior_number: Mapped[str | None] = mapped_column(
        String(40),
        nullable=True,
    )

    neighborhood: Mapped[str | None] = mapped_column(
        String(180),
        nullable=True,
    )

    locality: Mapped[str | None] = mapped_column(
        String(180),
        nullable=True,
    )

    municipality: Mapped[str | None] = mapped_column(
        String(180),
        nullable=True,
    )

    city: Mapped[str | None] = mapped_column(
        String(180),
        nullable=True,
    )

    state: Mapped[str | None] = mapped_column(
        String(180),
        nullable=True,
    )

    postal_code: Mapped[str | None] = mapped_column(
        String(20),
        nullable=True,
    )

    country: Mapped[str | None] = mapped_column(
        String(120),
        nullable=True,
    )

    # Código SAT del país del domicilio fiscal.
    # `country` se conserva como descripción legible.
    fiscal_country_code: Mapped[str | None] = mapped_column(
        String(10),
        nullable=True,
    )

    fiscal_review_required: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False,
        index=True,
    )

    fiscal_postal_code: Mapped[str | None] = mapped_column(
        String(20),
        nullable=True,
    )

    tax_constancy_filename: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
    )

    tax_constancy_path: Mapped[str | None] = mapped_column(
        String(500),
        nullable=True,
    )

    tax_constancy_uploaded_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    payment_terms: Mapped[str | None] = mapped_column(
        String(120),
        nullable=True,
    )

    notes: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    contacts: Mapped[list["ClientContact"]] = relationship(
        back_populates="client",
        cascade="all, delete-orphan",
    )

    certificate_profiles: Mapped[list["ClientCertificateProfile"]] = relationship(
        back_populates="client",
        cascade="all, delete-orphan",
    )

    quotations: Mapped[list["Quotation"]] = relationship(
        back_populates="client",
    )

    service_orders: Mapped[list["ServiceOrder"]] = relationship(
        back_populates="client",
    )

    portal: Mapped["ClientPortal | None"] = relationship(
        back_populates="client",
        cascade="all, delete-orphan",
        uselist=False,
        single_parent=True,
    )

    # Cuentas de personas vinculadas al cliente.
    # Un cliente puede tener cualquier cantidad de membresías.
    portal_memberships: Mapped[list["ClientPortalMembership"]] = relationship(
        back_populates="client",
    )

    # Roles personalizados pertenecientes a este cliente.
    # Los roles globales del sistema mantienen client_id = None.
    portal_roles: Mapped[list["ClientPortalRole"]] = relationship(
        back_populates="client",
    )

    # Solicitudes que proponen vincular un registro del portal con este cliente.
    portal_link_requests: Mapped[list["ClientLinkRequest"]] = relationship(
        back_populates="proposed_client",
    )

    # Invitaciones preautorizadas emitidas para vincular nuevas cuentas
    # directamente con este cliente.
    portal_invitations: Mapped[list["PortalInvitation"]] = relationship(
        back_populates="client",
    )


class ClientContact(
    IntegerPkMixin,
    TimestampMixin,
    SoftDeleteMixin,
    Base,
):
    __tablename__ = "client_contacts"

    client_id: Mapped[int] = mapped_column(
        ForeignKey(
            "clients.id",
            ondelete="CASCADE",
        ),
        nullable=False,
        index=True,
    )

    name: Mapped[str] = mapped_column(
        String(180),
        nullable=False,
    )

    email: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
    )

    phone: Mapped[str | None] = mapped_column(
        String(40),
        nullable=True,
    )

    position: Mapped[str | None] = mapped_column(
        String(120),
        nullable=True,
    )

    client: Mapped["Client"] = relationship(
        back_populates="contacts",
    )


class ClientCertificateProfile(
    IntegerPkMixin,
    TimestampMixin,
    SoftDeleteMixin,
    Base,
):
    __tablename__ = "client_certificate_profiles"

    client_id: Mapped[int] = mapped_column(
        ForeignKey(
            "clients.id",
            ondelete="CASCADE",
        ),
        nullable=False,
        index=True,
    )

    label: Mapped[str] = mapped_column(
        String(120),
        nullable=False,
    )

    company: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )

    address: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )

    attention: Mapped[str | None] = mapped_column(
        String(180),
        nullable=True,
    )

    is_default: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
    )

    client: Mapped["Client"] = relationship(
        back_populates="certificate_profiles",
    )