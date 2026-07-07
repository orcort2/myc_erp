from __future__ import annotations

from datetime import date
from decimal import Decimal, ROUND_HALF_UP
from uuid import uuid4

from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from app.models.certificate import Certificate
from app.models.client import Client
from app.models.invoice import CreditNote, Invoice, InvoiceItem, InvoicePayment, InvoiceSettings
from app.models.quotation import Quotation, QuotationItem
from app.models.service_order import ServiceOrder
from app.schemas.invoice import (
    CreditNoteCreate,
    FinancialDashboardRead,
    InvoiceCreate,
    InvoicePaymentCreate,
    InvoiceSettingsUpdate,
    InvoiceStatusChange,
    InvoiceUpdate,
    ReleasedUninvoicedRow,
)
from app.services.audit_logs import write_audit_log


INVOICE_TERMINAL_STATUSES = {"paid", "cancelled", "credit_note"}
INVOICE_ALLOWED_TRANSITIONS = {
    "draft": {"pending", "issued", "cancelled"},
    "pending": {"issued", "cancelled"},
    "issued": {"partially_paid", "paid", "cancelled"},
    "partially_paid": {"paid", "cancelled"},
    "paid": set(),
    "overdue": {"partially_paid", "paid", "cancelled"},
    "cancelled": set(),
    "credit_note": set(),
}


def _money(value: Decimal | int | float | None) -> Decimal:
    return Decimal(value or 0).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def get_invoice_settings(db: Session) -> InvoiceSettings:
    settings = db.scalar(select(InvoiceSettings).where(InvoiceSettings.key == "default"))
    if settings is None:
        settings = InvoiceSettings(
            key="default",
            forms_of_payment={"items": ["Transferencia", "Efectivo", "Tarjeta", "Cheque"]},
            methods_of_payment={"items": ["PUE", "PPD"]},
            usage_cfdi_catalog={"items": ["G03", "P01"]},
            tax_regime_catalog={"items": ["601", "603", "612"]},
            currency_catalog={"items": ["MXN", "USD"]},
            sat_product_keys={"items": ["81141504", "84111506"]},
            sat_units={"items": ["E48", "ACT"]},
            banks={"items": ["BBVA", "Banamex", "Santander"]},
            bank_accounts={"items": []},
            legal_texts={"invoice_legend": "Documento administrativo interno, no CFDI timbrado"},
            billing_emails={"items": ["cobranza@myc.com.mx"]},
            emitter_data={
                "commercial_name": "MYC SYSTEM",
                "legal_name": "METROLOGIA Y SERVICIOS MYC",
                "rfc": "",
                "tax_regime": "",
                "postal_code": "",
                "address": "",
                "email": "",
                "phone": "",
                "place_of_issue": "",
            },
            pdf_template_name="invoice_pdf.html",
            cfdi_future_parameters={},
        )
        db.add(settings)
        db.commit()
        db.refresh(settings)
    return settings


def update_invoice_settings(db: Session, payload: InvoiceSettingsUpdate) -> InvoiceSettings:
    settings = get_invoice_settings(db)
    for key, value in payload.model_dump(exclude_unset=True).items():
        setattr(settings, key, value)
    db.commit()
    db.refresh(settings)
    return settings


def _get_client(db: Session, client_id: int) -> Client:
    client = db.get(Client, client_id)
    if client is None or not client.is_active:
        raise HTTPException(status_code=404, detail="Cliente no encontrado")
    return client


def _get_service_order(db: Session, service_order_id: int | None) -> ServiceOrder | None:
    if service_order_id is None:
        return None
    order = db.get(ServiceOrder, service_order_id)
    if order is None or not order.is_active:
        raise HTTPException(status_code=404, detail="Orden de servicio no encontrada")
    return order


def _get_quotation(db: Session, quotation_id: int | None) -> Quotation | None:
    if quotation_id is None:
        return None
    quotation = db.get(Quotation, quotation_id)
    if quotation is None or not quotation.is_active:
        raise HTTPException(status_code=404, detail="Cotizacion no encontrada")
    return quotation


def _validate_fiscal_client(client: Client) -> list[str]:
    missing = []
    if not client.rfc:
        missing.append("RFC")
    if not client.legal_name:
        missing.append("Razon social")
    if not client.tax_regime:
        missing.append("Regimen fiscal")
    return missing


def _next_invoice_folio(db: Session, settings: InvoiceSettings, *, issued_on: date, series: str | None = None) -> tuple[str, str]:
    series_value = (series or settings.default_series or "F").strip().upper()
    if settings.reset_annually:
        year_prefix = f"{series_value}-{issued_on:%Y}-"
        last = db.scalar(
            select(Invoice.folio).where(Invoice.folio.like(f"{year_prefix}%")).order_by(Invoice.folio.desc()).limit(1)
        )
        sequence = settings.next_sequence if not last else int(last.rsplit("-", 1)[-1]) + 1
        folio = f"{year_prefix}{sequence:04d}"
    else:
        sequence = int(settings.next_sequence or 1)
        folio = f"{series_value}-{issued_on:%Y}-{sequence:04d}"
    settings.next_sequence = sequence + 1
    return series_value, folio


def _build_invoice_item(db: Session, payload, *, invoice_id: int | None = None) -> InvoiceItem:
    certificate = None
    equipment_id = payload.equipment_id
    if payload.certificate_id is not None:
        certificate = db.get(Certificate, payload.certificate_id)
        if certificate is None or not certificate.is_active:
            raise HTTPException(status_code=404, detail="Certificado no encontrado")
        existing = db.scalar(
            select(InvoiceItem.id)
            .join(Invoice)
            .where(
                InvoiceItem.certificate_id == payload.certificate_id,
                Invoice.is_active.is_(True),
                Invoice.status != "cancelled",
                Invoice.id != (invoice_id or 0),
            )
        )
        if existing is not None:
            raise HTTPException(status_code=409, detail="El certificado ya esta facturado")
        equipment_id = equipment_id or certificate.equipment_id
    item = InvoiceItem(
        quotation_item_id=payload.quotation_item_id,
        certificate_id=payload.certificate_id,
        equipment_id=equipment_id,
        description=payload.description,
        quantity=payload.quantity,
        unit=payload.unit,
        sat_unit=payload.sat_unit,
        sat_key=payload.sat_key,
        unit_price=payload.unit_price,
        discount_total=payload.discount_total,
        tax_rate=payload.tax_rate,
        notes=payload.notes,
        service_type=payload.service_type,
        source_type=payload.source_type,
    )
    return item


def _recalculate_invoice(invoice: Invoice) -> None:
    subtotal = Decimal("0.00")
    discount = Decimal("0.00")
    taxes = Decimal("0.00")
    for item in invoice.items:
        gross = _money(Decimal(item.quantity or 0) * Decimal(item.unit_price or 0))
        item.discount_total = _money(item.discount_total)
        taxable = gross - item.discount_total
        item.tax_total = _money(taxable * (Decimal(item.tax_rate or 0) / Decimal("100")))
        item.line_total = _money(taxable + item.tax_total)
        subtotal += taxable
        discount += item.discount_total
        taxes += item.tax_total
    paid = sum((_money(payment.amount) for payment in invoice.payments if payment.status != "cancelled"), Decimal("0.00"))
    credits = sum((_money(note.total) for note in invoice.credit_notes if note.status == "applied"), Decimal("0.00"))
    invoice.subtotal = _money(subtotal)
    invoice.discount_total = _money(discount)
    invoice.tax_total = _money(taxes)
    invoice.total = _money(invoice.subtotal + invoice.tax_total - _money(invoice.withholding_total))
    invoice.amount_paid = _money(paid + credits)
    invoice.balance_due = _money(max(invoice.total - invoice.amount_paid, Decimal("0.00")))
    if invoice.balance_due == Decimal("0.00") and invoice.total > Decimal("0.00"):
        invoice.status = "paid"
    elif invoice.amount_paid > Decimal("0.00"):
        invoice.status = "partially_paid"
    elif invoice.due_on and invoice.due_on < date.today() and invoice.status not in {"draft", "cancelled"}:
        invoice.status = "overdue"


def list_invoices(db: Session) -> list[Invoice]:
    query = (
        select(Invoice)
        .where(Invoice.is_active.is_(True))
        .options(
            selectinload(Invoice.client),
            selectinload(Invoice.fiscal_client),
            selectinload(Invoice.service_order),
            selectinload(Invoice.items).selectinload(InvoiceItem.certificate),
            selectinload(Invoice.payments),
            selectinload(Invoice.credit_notes),
        )
        .order_by(Invoice.created_at.desc())
    )
    return list(db.scalars(query).all())


def get_invoice(db: Session, invoice_id: int) -> Invoice:
    invoice = db.scalar(
        select(Invoice)
        .where(Invoice.id == invoice_id, Invoice.is_active.is_(True))
        .options(
            selectinload(Invoice.client),
            selectinload(Invoice.fiscal_client),
            selectinload(Invoice.service_order),
            selectinload(Invoice.quotation),
            selectinload(Invoice.items).selectinload(InvoiceItem.certificate).selectinload(Certificate.equipment),
            selectinload(Invoice.payments),
            selectinload(Invoice.credit_notes),
        )
    )
    if invoice is None:
        raise HTTPException(status_code=404, detail="Factura no encontrada")
    _recalculate_invoice(invoice)
    return invoice


def create_invoice(db: Session, payload: InvoiceCreate, *, user_id: int | None = None) -> Invoice:
    settings = get_invoice_settings(db)
    client = _get_client(db, payload.client_id)
    fiscal_client = _get_client(db, payload.fiscal_client_id or payload.client_id)
    service_order = _get_service_order(db, payload.service_order_id)
    _get_quotation(db, payload.quotation_id)
    issued_on = payload.issued_on or date.today()
    if payload.status in {"pending", "issued"}:
        missing = _validate_fiscal_client(fiscal_client)
        if missing:
            raise HTTPException(status_code=409, detail=f"Datos fiscales incompletos: {', '.join(missing)}")
    if payload.folio and settings.allow_manual_folio:
        series_value = payload.series or settings.default_series
        folio = payload.folio
    else:
        series_value, folio = _next_invoice_folio(db, settings, issued_on=issued_on, series=payload.series)
    credit_days = payload.credit_days if payload.credit_days is not None else settings.default_credit_days
    invoice = Invoice(
        internal_uuid=uuid4().hex,
        series=series_value,
        folio=folio,
        client_id=client.id,
        fiscal_client_id=fiscal_client.id,
        service_order_id=service_order.id if service_order else None,
        quotation_id=payload.quotation_id,
        issued_on=issued_on,
        due_on=payload.due_on or (issued_on.fromordinal(issued_on.toordinal() + credit_days) if credit_days else issued_on),
        status=payload.status,
        payment_method=payload.payment_method,
        payment_form=payload.payment_form,
        usage_cfdi=payload.usage_cfdi,
        currency=(payload.currency or settings.default_currency or "MXN").upper(),
        credit_days=credit_days,
        observations=payload.observations,
        internal_comments=payload.internal_comments,
        created_by_id=user_id,
        updated_by_id=user_id,
    )
    invoice.items = [_build_invoice_item(db, item) for item in payload.items]
    _recalculate_invoice(invoice)
    db.add(invoice)
    db.flush()
    write_audit_log(db, action="invoice.created", entity="invoices", entity_id=invoice.id, user_id=user_id, new_values={"folio": invoice.folio, "status": invoice.status})
    db.commit()
    return get_invoice(db, invoice.id)


def update_invoice(db: Session, invoice_id: int, payload: InvoiceUpdate, *, user_id: int | None = None) -> Invoice:
    invoice = get_invoice(db, invoice_id)
    if invoice.status in {"paid", "cancelled"} and payload.items is not None:
        raise HTTPException(status_code=409, detail="La factura no permite modificar conceptos en este estado")
    updates = payload.model_dump(exclude_unset=True)
    if "fiscal_client_id" in updates and updates["fiscal_client_id"]:
        _get_client(db, updates["fiscal_client_id"])
    if "service_order_id" in updates and updates["service_order_id"]:
        _get_service_order(db, updates["service_order_id"])
    if "quotation_id" in updates and updates["quotation_id"]:
        _get_quotation(db, updates["quotation_id"])
    if payload.items is not None:
        invoice.items = [_build_invoice_item(db, item, invoice_id=invoice.id) for item in payload.items]
    for key, value in updates.items():
        if key == "items":
            continue
        setattr(invoice, key, value)
    invoice.updated_by_id = user_id
    _recalculate_invoice(invoice)
    write_audit_log(db, action="invoice.updated", entity="invoices", entity_id=invoice.id, user_id=user_id, new_values={"status": invoice.status})
    db.commit()
    return get_invoice(db, invoice.id)


def change_invoice_status(db: Session, invoice_id: int, payload: InvoiceStatusChange, *, user_id: int | None = None) -> Invoice:
    invoice = get_invoice(db, invoice_id)
    current_status = invoice.status
    if payload.status not in INVOICE_ALLOWED_TRANSITIONS.get(current_status, set()):
        raise HTTPException(status_code=409, detail=f"Transicion no permitida: {current_status} -> {payload.status}")
    if payload.status in {"pending", "issued"}:
        fiscal_client = invoice.fiscal_client or invoice.client
        missing = _validate_fiscal_client(fiscal_client)
        if missing:
            raise HTTPException(status_code=409, detail=f"Datos fiscales incompletos: {', '.join(missing)}")
    if payload.status == "cancelled" and invoice.amount_paid > Decimal("0.00") and not payload.comment:
        raise HTTPException(status_code=409, detail="Indica motivo para cancelar una factura con pagos")
    invoice.status = payload.status
    if payload.status == "cancelled":
        invoice.cancellation_reason = payload.comment
    _recalculate_invoice(invoice)
    write_audit_log(db, action=f"invoice.{payload.status}", entity="invoices", entity_id=invoice.id, user_id=user_id, previous_values={"status": current_status}, new_values={"status": invoice.status}, comment=payload.comment)
    db.commit()
    return get_invoice(db, invoice.id)


def list_invoice_payments(db: Session) -> list[InvoicePayment]:
    return list(db.scalars(select(InvoicePayment).where(InvoicePayment.is_active.is_(True)).options(selectinload(InvoicePayment.invoice)).order_by(InvoicePayment.created_at.desc())).all())


def get_invoice_payment(db: Session, payment_id: int) -> InvoicePayment:
    payment = db.scalar(select(InvoicePayment).where(InvoicePayment.id == payment_id, InvoicePayment.is_active.is_(True)).options(selectinload(InvoicePayment.invoice).selectinload(Invoice.client), selectinload(InvoicePayment.invoice).selectinload(Invoice.fiscal_client)))
    if payment is None:
        raise HTTPException(status_code=404, detail="Pago no encontrado")
    return payment


def register_invoice_payment(db: Session, invoice_id: int, payload: InvoicePaymentCreate, *, user_id: int | None = None) -> Invoice:
    invoice = get_invoice(db, invoice_id)
    if invoice.status == "cancelled":
        raise HTTPException(status_code=409, detail="No se puede registrar pago en factura cancelada")
    if _money(payload.amount) > invoice.balance_due and invoice.balance_due > Decimal("0.00"):
        raise HTTPException(status_code=409, detail="El pago excede el saldo pendiente")
    payment = InvoicePayment(
        invoice_id=invoice.id,
        paid_on=payload.paid_on,
        amount=payload.amount,
        bank_name=payload.bank_name,
        bank_account=payload.bank_account,
        reference=payload.reference,
        payment_method=payload.payment_method,
        payment_form=payload.payment_form,
        status=payload.status,
        notes=payload.notes,
        registered_by_id=user_id,
    )
    invoice.payments.append(payment)
    invoice.last_payment_on = payload.paid_on
    _recalculate_invoice(invoice)
    write_audit_log(db, action="invoice.payment_registered", entity="invoice_payments", entity_id=invoice.id, user_id=user_id, new_values={"amount": str(payload.amount), "invoice_id": invoice.id})
    db.commit()
    return get_invoice(db, invoice.id)


def create_credit_note(db: Session, invoice_id: int, payload: CreditNoteCreate, *, user_id: int | None = None) -> Invoice:
    invoice = get_invoice(db, invoice_id)
    folio = f"NC-{date.today():%Y}-{invoice_id:04d}-{len(invoice.credit_notes) + 1:02d}"
    note = CreditNote(
        invoice_id=invoice.id,
        folio=folio,
        issued_on=payload.issued_on,
        reason=payload.reason,
        subtotal=payload.subtotal,
        tax_total=payload.tax_total,
        total=payload.total,
        status=payload.status,
        observations=payload.observations,
        created_by_id=user_id,
    )
    invoice.credit_notes.append(note)
    _recalculate_invoice(invoice)
    if payload.status == "applied":
        invoice.status = "credit_note" if invoice.balance_due == Decimal("0.00") else invoice.status
    write_audit_log(db, action="invoice.credit_note_created", entity="credit_notes", entity_id=invoice.id, user_id=user_id, new_values={"folio": folio, "status": payload.status})
    db.commit()
    return get_invoice(db, invoice.id)


def list_accounts_receivable(db: Session) -> list[dict]:
    rows = []
    for invoice in list_invoices(db):
        if invoice.balance_due <= Decimal("0.00"):
            continue
        today = date.today()
        if not invoice.due_on or invoice.due_on >= today:
            bucket = "Por vencer"
        else:
            delta = (today - invoice.due_on).days
            if delta <= 7:
                bucket = "0-7 dias"
            elif delta <= 15:
                bucket = "8-15 dias"
            elif delta <= 30:
                bucket = "16-30 dias"
            else:
                bucket = "Mas de 30 dias"
        rows.append(
            {
                "invoice_id": invoice.id,
                "invoice_folio": invoice.folio,
                "client_id": invoice.client_id,
                "client_name": invoice.client.commercial_name or invoice.client.legal_name,
                "service_order_id": invoice.service_order_id,
                "status": invoice.status,
                "total": invoice.total,
                "balance_due": invoice.balance_due,
                "due_on": invoice.due_on,
                "aging_bucket": bucket,
                "last_payment_on": invoice.last_payment_on,
            }
        )
    return rows


def get_financial_dashboard(db: Session) -> FinancialDashboardRead:
    today = date.today()
    invoices = list_invoices(db)
    payments = list_invoice_payments(db)
    month_invoices = [item for item in invoices if item.issued_on and item.issued_on.year == today.year and item.issued_on.month == today.month]
    month_payments = [item for item in payments if item.paid_on and item.paid_on.year == today.year and item.paid_on.month == today.month and item.status != "cancelled"]
    overdue = [item for item in invoices if item.balance_due > Decimal("0.00") and item.due_on and item.due_on < today]
    debt_by_client: dict[int, Decimal] = {}
    for invoice in invoices:
        if invoice.balance_due > Decimal("0.00"):
            debt_by_client[invoice.client_id] = debt_by_client.get(invoice.client_id, Decimal("0.00")) + invoice.balance_due
    top_clientes = sorted(
        [
            {"client_id": client_id, "saldo": _money(amount), "client_name": _get_client(db, client_id).commercial_name or _get_client(db, client_id).legal_name}
            for client_id, amount in debt_by_client.items()
        ],
        key=lambda item: item["saldo"],
        reverse=True,
    )[:5]
    return FinancialDashboardRead(
        total_facturado_mes=_money(sum((item.total for item in month_invoices), Decimal("0.00"))),
        total_cobrado_mes=_money(sum((item.amount for item in month_payments), Decimal("0.00"))),
        saldo_pendiente_total=_money(sum((item.balance_due for item in invoices), Decimal("0.00"))),
        saldo_vencido_total=_money(sum((item.balance_due for item in overdue), Decimal("0.00"))),
        facturas_pendientes=len([item for item in invoices if item.status in {"pending", "issued", "partially_paid", "overdue"}]),
        facturas_vencidas=len(overdue),
        facturas_pagadas=len([item for item in invoices if item.status == "paid"]),
        pagos_hoy=_money(sum((item.amount for item in payments if item.paid_on == today and item.status != "cancelled"), Decimal("0.00"))),
        pagos_mes=_money(sum((item.amount for item in month_payments), Decimal("0.00"))),
        clientes_con_saldo=len(debt_by_client),
        top_clientes_deuda=top_clientes,
    )


def list_released_uninvoiced(db: Session) -> list[ReleasedUninvoicedRow]:
    released_certs = list(
        db.scalars(
            select(Certificate)
            .where(
                Certificate.is_active.is_(True),
                Certificate.status == "released_to_client",
                Certificate.client_visible.is_(True),
            )
            .options(selectinload(Certificate.service_order).selectinload(ServiceOrder.client))
        ).all()
    )
    invoiced_cert_ids = set(
        db.scalars(
            select(InvoiceItem.certificate_id)
            .join(Invoice)
            .where(
                InvoiceItem.certificate_id.is_not(None),
                Invoice.is_active.is_(True),
                Invoice.status != "cancelled",
            )
        ).all()
    )
    grouped: dict[int, dict] = {}
    for cert in released_certs:
        row = grouped.setdefault(
            cert.service_order_id,
            {
                "service_order_id": cert.service_order_id,
                "work_order_number": cert.service_order.work_order_number if cert.service_order else None,
                "client_id": cert.service_order.client_id if cert.service_order else 0,
                "client_name": cert.service_order.client.commercial_name or cert.service_order.client.legal_name if cert.service_order and cert.service_order.client else "-",
                "released_certificates": 0,
                "uninvoiced_certificates": 0,
                "certificate_ids": [],
            },
        )
        row["released_certificates"] += 1
        if cert.id not in invoiced_cert_ids:
            row["uninvoiced_certificates"] += 1
            row["certificate_ids"].append(cert.id)
    return [ReleasedUninvoicedRow(**row) for row in grouped.values() if row["uninvoiced_certificates"] > 0]
