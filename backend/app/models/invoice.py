from datetime import date
from decimal import Decimal

from sqlalchemy import JSON, Boolean, Date, ForeignKey, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.db import Base
from app.models.base import IntegerPkMixin, SoftDeleteMixin, TimestampMixin


class Invoice(IntegerPkMixin, TimestampMixin, SoftDeleteMixin, Base):
    __tablename__ = "invoices"

    internal_uuid: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    series: Mapped[str] = mapped_column(String(20), default="F", index=True)
    folio: Mapped[str] = mapped_column(String(40), unique=True, index=True)
    client_id: Mapped[int] = mapped_column(ForeignKey("clients.id"), index=True)
    fiscal_client_id: Mapped[int | None] = mapped_column(ForeignKey("clients.id"), index=True)
    service_order_id: Mapped[int | None] = mapped_column(ForeignKey("service_orders.id"), index=True)
    quotation_id: Mapped[int | None] = mapped_column(ForeignKey("quotations.id"), index=True)
    issued_on: Mapped[date | None] = mapped_column(Date, index=True)
    due_on: Mapped[date | None] = mapped_column(Date, index=True)
    subtotal: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=0)
    tax_total: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=0)
    withholding_total: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=0)
    discount_total: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=0)
    total: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=0)
    balance_due: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=0)
    amount_paid: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=0)
    status: Mapped[str] = mapped_column(String(40), default="draft", index=True)
    review_required: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False, index=True)
    draft_reason: Mapped[str | None] = mapped_column(String(80), index=True)
    source_snapshot: Mapped[dict | None] = mapped_column(JSON, default=dict)
    # Datos fiscales inmutables usados para este documento.
    fiscal_snapshot: Mapped[dict | None] = mapped_column(JSON, default=dict)
    payment_method: Mapped[str | None] = mapped_column(String(80))
    payment_form: Mapped[str | None] = mapped_column(String(80))
    usage_cfdi: Mapped[str | None] = mapped_column(String(80))
    currency: Mapped[str] = mapped_column(String(10), default="MXN")
    credit_days: Mapped[int] = mapped_column(default=0)
    observations: Mapped[str | None] = mapped_column(Text)
    internal_comments: Mapped[str | None] = mapped_column(Text)
    cancellation_reason: Mapped[str | None] = mapped_column(Text)
    created_by_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), index=True)
    updated_by_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), index=True)
    last_payment_on: Mapped[date | None] = mapped_column(Date)

    client: Mapped["Client"] = relationship(foreign_keys=[client_id])
    fiscal_client: Mapped["Client | None"] = relationship(foreign_keys=[fiscal_client_id])
    service_order: Mapped["ServiceOrder | None"] = relationship(back_populates="invoices")
    quotation: Mapped["Quotation | None"] = relationship()
    items: Mapped[list["InvoiceItem"]] = relationship(back_populates="invoice", cascade="all, delete-orphan")
    payments: Mapped[list["InvoicePayment"]] = relationship(back_populates="invoice", cascade="all, delete-orphan")
    credit_notes: Mapped[list["CreditNote"]] = relationship(back_populates="invoice", cascade="all, delete-orphan")


class InvoiceItem(IntegerPkMixin, TimestampMixin, SoftDeleteMixin, Base):
    __tablename__ = "invoice_items"

    invoice_id: Mapped[int] = mapped_column(ForeignKey("invoices.id"), index=True)
    quotation_item_id: Mapped[int | None] = mapped_column(ForeignKey("quotation_items.id"), index=True)
    certificate_id: Mapped[int | None] = mapped_column(ForeignKey("certificates.id"), index=True)
    equipment_id: Mapped[int | None] = mapped_column(ForeignKey("equipment.id"), index=True)
    description: Mapped[str] = mapped_column(Text)
    quantity: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=1)
    unit: Mapped[str | None] = mapped_column(String(80))
    sat_unit: Mapped[str | None] = mapped_column(String(40))
    sat_key: Mapped[str | None] = mapped_column(String(40))
    unit_price: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=0)
    discount_total: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=0)
    tax_rate: Mapped[Decimal] = mapped_column(Numeric(5, 2), default=16)
    tax_total: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=0)
    line_total: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=0)
    notes: Mapped[str | None] = mapped_column(Text)
    service_type: Mapped[str | None] = mapped_column(String(80))
    source_type: Mapped[str | None] = mapped_column(String(40), index=True)

    invoice: Mapped[Invoice] = relationship(back_populates="items")
    certificate: Mapped["Certificate | None"] = relationship()
    equipment: Mapped["Equipment | None"] = relationship()


class InvoicePayment(IntegerPkMixin, TimestampMixin, SoftDeleteMixin, Base):
    __tablename__ = "invoice_payments"

    invoice_id: Mapped[int] = mapped_column(ForeignKey("invoices.id"), index=True)
    paid_on: Mapped[date | None] = mapped_column(Date, index=True)
    amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=0)
    bank_name: Mapped[str | None] = mapped_column(String(120))
    bank_account: Mapped[str | None] = mapped_column(String(120))
    reference: Mapped[str | None] = mapped_column(String(120), index=True)
    payment_method: Mapped[str | None] = mapped_column(String(80))
    payment_form: Mapped[str | None] = mapped_column(String(80))
    status: Mapped[str] = mapped_column(String(40), default="pending", index=True)
    notes: Mapped[str | None] = mapped_column(Text)
    registered_by_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), index=True)

    invoice: Mapped[Invoice] = relationship(back_populates="payments")


class CreditNote(IntegerPkMixin, TimestampMixin, SoftDeleteMixin, Base):
    __tablename__ = "credit_notes"

    invoice_id: Mapped[int] = mapped_column(ForeignKey("invoices.id"), index=True)
    folio: Mapped[str] = mapped_column(String(40), unique=True, index=True)
    issued_on: Mapped[date | None] = mapped_column(Date)
    reason: Mapped[str] = mapped_column(Text)
    subtotal: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=0)
    tax_total: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=0)
    total: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=0)
    status: Mapped[str] = mapped_column(String(40), default="draft", index=True)
    observations: Mapped[str | None] = mapped_column(Text)
    created_by_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), index=True)

    invoice: Mapped[Invoice] = relationship(back_populates="credit_notes")


class InvoiceSettings(IntegerPkMixin, TimestampMixin, Base):
    __tablename__ = "invoice_settings"

    key: Mapped[str] = mapped_column(String(60), unique=True, index=True)
    default_series: Mapped[str] = mapped_column(String(20), default="F")
    next_sequence: Mapped[int] = mapped_column(default=1)
    reset_annually: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    default_tax_rate: Mapped[Decimal] = mapped_column(Numeric(5, 2), default=16)
    default_currency: Mapped[str] = mapped_column(String(10), default="MXN")
    default_credit_days: Mapped[int] = mapped_column(default=0)
    allow_manual_folio: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    forms_of_payment: Mapped[dict | None] = mapped_column(JSON, default=dict)
    methods_of_payment: Mapped[dict | None] = mapped_column(JSON, default=dict)
    usage_cfdi_catalog: Mapped[dict | None] = mapped_column(JSON, default=dict)
    tax_regime_catalog: Mapped[dict | None] = mapped_column(JSON, default=dict)
    currency_catalog: Mapped[dict | None] = mapped_column(JSON, default=dict)
    sat_product_keys: Mapped[dict | None] = mapped_column(JSON, default=dict)
    sat_units: Mapped[dict | None] = mapped_column(JSON, default=dict)
    banks: Mapped[dict | None] = mapped_column(JSON, default=dict)
    bank_accounts: Mapped[dict | None] = mapped_column(JSON, default=dict)
    legal_texts: Mapped[dict | None] = mapped_column(JSON, default=dict)
    billing_emails: Mapped[dict | None] = mapped_column(JSON, default=dict)
    emitter_data: Mapped[dict | None] = mapped_column(JSON, default=dict)
    pdf_template_name: Mapped[str | None] = mapped_column(String(120))
    cfdi_future_parameters: Mapped[dict | None] = mapped_column(JSON, default=dict)
