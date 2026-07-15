from datetime import date, datetime
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


InvoiceStatus = Literal[
    "draft",
    "pending",
    "issued",
    "paid",
    "partially_paid",
    "overdue",
    "cancelled",
    "credit_note",
]
PaymentStatus = Literal["pending", "partial", "settled", "refunded", "cancelled"]
CreditNoteStatus = Literal["draft", "applied", "cancelled"]


class InvoiceItemBase(BaseModel):
    quotation_item_id: int | None = None
    certificate_id: int | None = None
    equipment_id: int | None = None
    description: str = Field(min_length=1)
    quantity: Decimal = Field(default=Decimal("1.00"))
    unit: str | None = Field(default=None, max_length=80)
    sat_unit: str | None = Field(default=None, max_length=40)
    sat_key: str | None = Field(default=None, max_length=40)
    unit_price: Decimal = Field(default=Decimal("0.00"))
    discount_total: Decimal = Field(default=Decimal("0.00"))
    tax_rate: Decimal = Field(default=Decimal("16.00"))
    notes: str | None = None
    service_type: str | None = Field(default=None, max_length=80)
    source_type: str | None = Field(default=None, max_length=40)


class InvoiceItemCreate(InvoiceItemBase):
    pass


class InvoiceItemRead(InvoiceItemBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    tax_total: Decimal
    line_total: Decimal


class InvoicePaymentBase(BaseModel):
    paid_on: date
    amount: Decimal = Field(gt=Decimal("0.00"))
    bank_name: str | None = Field(default=None, max_length=120)
    bank_account: str | None = Field(default=None, max_length=120)
    reference: str | None = Field(default=None, max_length=120)
    payment_method: str | None = Field(default=None, max_length=80)
    payment_form: str | None = Field(default=None, max_length=80)
    status: PaymentStatus = "pending"
    notes: str | None = None


class InvoicePaymentCreate(InvoicePaymentBase):
    pass


class InvoicePaymentRead(InvoicePaymentBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    invoice_id: int
    registered_by_id: int | None = None
    created_at: datetime


class CreditNoteBase(BaseModel):
    issued_on: date
    reason: str = Field(min_length=1)
    subtotal: Decimal = Field(default=Decimal("0.00"))
    tax_total: Decimal = Field(default=Decimal("0.00"))
    total: Decimal = Field(default=Decimal("0.00"))
    status: CreditNoteStatus = "draft"
    observations: str | None = None


class CreditNoteCreate(CreditNoteBase):
    pass


class CreditNoteRead(CreditNoteBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    invoice_id: int
    folio: str


class InvoiceBase(BaseModel):
    client_id: int
    fiscal_client_id: int | None = None
    service_order_id: int | None = None
    quotation_id: int | None = None
    series: str | None = Field(default=None, max_length=20)
    folio: str | None = Field(default=None, max_length=40)
    issued_on: date | None = None
    due_on: date | None = None
    status: InvoiceStatus = "draft"
    payment_method: str | None = Field(default=None, max_length=80)
    payment_form: str | None = Field(default=None, max_length=80)
    usage_cfdi: str | None = Field(default=None, max_length=80)
    currency: str | None = Field(default=None, max_length=10)
    credit_days: int | None = Field(default=None, ge=0)
    observations: str | None = None
    internal_comments: str | None = None


class InvoiceCreate(InvoiceBase):
    items: list[InvoiceItemCreate] = Field(default_factory=list)


class InvoiceUpdate(BaseModel):
    fiscal_client_id: int | None = None
    service_order_id: int | None = None
    quotation_id: int | None = None
    issued_on: date | None = None
    due_on: date | None = None
    status: InvoiceStatus | None = None
    payment_method: str | None = Field(default=None, max_length=80)
    payment_form: str | None = Field(default=None, max_length=80)
    usage_cfdi: str | None = Field(default=None, max_length=80)
    currency: str | None = Field(default=None, max_length=10)
    credit_days: int | None = Field(default=None, ge=0)
    observations: str | None = None
    internal_comments: str | None = None
    cancellation_reason: str | None = None
    items: list[InvoiceItemCreate] | None = None


class InvoiceStatusChange(BaseModel):
    status: InvoiceStatus
    comment: str | None = None


class InvoiceRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    internal_uuid: str
    series: str
    folio: str
    client_id: int
    fiscal_client_id: int | None = None
    service_order_id: int | None = None
    quotation_id: int | None = None
    issued_on: date | None = None
    due_on: date | None = None
    subtotal: Decimal
    tax_total: Decimal
    withholding_total: Decimal
    discount_total: Decimal
    total: Decimal
    balance_due: Decimal
    amount_paid: Decimal
    status: str
    review_required: bool = False
    draft_reason: str | None = None
    source_snapshot: dict | None = None
    fiscal_snapshot: dict | None = None
    payment_method: str | None = None
    payment_form: str | None = None
    usage_cfdi: str | None = None
    currency: str
    credit_days: int
    observations: str | None = None
    internal_comments: str | None = None
    cancellation_reason: str | None = None
    created_by_id: int | None = None
    updated_by_id: int | None = None
    last_payment_on: date | None = None
    facturama_id: str | None = None
    cfdi_uuid: str | None = None
    facturama_environment: str | None = None
    stamped_at: datetime | None = None
    facturama_xml_path: str | None = None
    facturama_pdf_path: str | None = None
    created_at: datetime
    updated_at: datetime
    items: list[InvoiceItemRead] = Field(default_factory=list)
    payments: list[InvoicePaymentRead] = Field(default_factory=list)
    credit_notes: list[CreditNoteRead] = Field(default_factory=list)


class InvoiceSourceChange(BaseModel):
    reason: str = Field(default="service_exception", max_length=80)
    comment: str | None = None


class AccountsReceivableRow(BaseModel):
    invoice_id: int
    invoice_folio: str
    client_id: int
    client_name: str
    service_order_id: int | None = None
    status: str
    total: Decimal
    balance_due: Decimal
    due_on: date | None = None
    aging_bucket: str
    last_payment_on: date | None = None


class FinancialDashboardRead(BaseModel):
    total_facturado_mes: Decimal
    total_cobrado_mes: Decimal
    saldo_pendiente_total: Decimal
    saldo_vencido_total: Decimal
    facturas_pendientes: int
    facturas_vencidas: int
    facturas_pagadas: int
    pagos_hoy: Decimal
    pagos_mes: Decimal
    clientes_con_saldo: int
    top_clientes_deuda: list[dict] = Field(default_factory=list)


class ReleasedUninvoicedRow(BaseModel):
    service_order_id: int
    work_order_number: int | None = None
    client_id: int
    client_name: str
    released_certificates: int
    uninvoiced_certificates: int
    certificate_ids: list[int] = Field(default_factory=list)


class InvoiceSettingsUpdate(BaseModel):
    default_series: str | None = Field(default=None, max_length=20)
    next_sequence: int | None = Field(default=None, ge=1)
    reset_annually: bool | None = None
    default_tax_rate: Decimal | None = None
    default_currency: str | None = Field(default=None, max_length=10)
    default_credit_days: int | None = Field(default=None, ge=0)
    allow_manual_folio: bool | None = None
    forms_of_payment: dict | None = None
    methods_of_payment: dict | None = None
    usage_cfdi_catalog: dict | None = None
    tax_regime_catalog: dict | None = None
    currency_catalog: dict | None = None
    sat_product_keys: dict | None = None
    sat_units: dict | None = None
    banks: dict | None = None
    bank_accounts: dict | None = None
    legal_texts: dict | None = None
    billing_emails: dict | None = None
    emitter_data: dict | None = None
    pdf_template_name: str | None = Field(default=None, max_length=120)
    cfdi_future_parameters: dict | None = None


class InvoiceSettingsRead(InvoiceSettingsUpdate):
    model_config = ConfigDict(from_attributes=True)

    id: int
    key: str
    default_series: str
    next_sequence: int
    reset_annually: bool
    default_tax_rate: Decimal
    default_currency: str
    default_credit_days: int
    allow_manual_folio: bool
    forms_of_payment: dict | None = None
    methods_of_payment: dict | None = None
    usage_cfdi_catalog: dict | None = None
    tax_regime_catalog: dict | None = None
    currency_catalog: dict | None = None
    sat_product_keys: dict | None = None
    sat_units: dict | None = None
    banks: dict | None = None
    bank_accounts: dict | None = None
    legal_texts: dict | None = None
    billing_emails: dict | None = None
    emitter_data: dict | None = None
    pdf_template_name: str | None = None
    cfdi_future_parameters: dict | None = None


class FacturamaReconciliationConfirmation(BaseModel):
    """Facts independently confirmed in Facturama for a manual reconciliation."""

    facturama_id: str = Field(min_length=1, max_length=100)
    uuid: str = Field(min_length=1, max_length=64)
    cfdi_type: str = Field(default="I", min_length=1, max_length=4)
    series: str = Field(min_length=1, max_length=20)
    folio: str = Field(min_length=1, max_length=40)
    receiver_rfc: str = Field(min_length=12, max_length=13)
    subtotal: Decimal
    total: Decimal
    issued_at: datetime
    status: str = Field(default="active", max_length=40)
