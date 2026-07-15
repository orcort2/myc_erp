from fastapi import APIRouter, Depends
from fastapi.responses import Response
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.models.user import User
from app.schemas.invoice import (
    AccountsReceivableRow,
    CreditNoteCreate,
    FinancialDashboardRead,
    InvoiceCreate,
    InvoicePaymentCreate,
    InvoicePaymentRead,
    InvoiceRead,
    InvoiceSettingsRead,
    InvoiceSettingsUpdate,
    InvoiceSourceChange,
    InvoiceStatusChange,
    InvoiceUpdate,
    ReleasedUninvoicedRow,
)
from app.services.auth import require_permission
from app.services.invoice_pdfs import generate_invoice_payment_receipt_pdf, generate_invoice_pdf
from app.services.invoices import (
    change_invoice_status,
    confirm_invoice_review,
    create_credit_note,
    create_invoice,
    get_financial_dashboard,
    get_invoice,
    get_invoice_payment,
    get_invoice_settings,
    list_accounts_receivable,
    list_invoice_payments,
    list_invoices,
    list_released_uninvoiced,
    mark_invoice_source_changed,
    register_invoice_payment,
    update_invoice,
    update_invoice_settings,
)


router = APIRouter(tags=["invoices"])


@router.get("/invoices/dashboard", response_model=FinancialDashboardRead)
def invoice_dashboard(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("invoices.read")),
):
    return get_financial_dashboard(db)


@router.get("/invoices/accounts-receivable", response_model=list[AccountsReceivableRow])
def accounts_receivable(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("invoices.read")),
):
    return list_accounts_receivable(db)


@router.get("/invoices/released-uninvoiced", response_model=list[ReleasedUninvoicedRow])
def released_uninvoiced(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("invoices.read")),
):
    return list_released_uninvoiced(db)


@router.get("/invoices", response_model=list[InvoiceRead])
def read_invoices(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("invoices.read")),
):
    return list_invoices(db)


@router.get("/invoices/{invoice_id}", response_model=InvoiceRead)
def read_invoice(
    invoice_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("invoices.read")),
):
    return get_invoice(db, invoice_id)


@router.post("/invoices", response_model=InvoiceRead)
def create_invoice_route(
    payload: InvoiceCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("invoices.manage")),
):
    return create_invoice(db, payload, user_id=current_user.id)


@router.put("/invoices/{invoice_id}", response_model=InvoiceRead)
@router.patch("/invoices/{invoice_id}", response_model=InvoiceRead, include_in_schema=False)
def update_invoice_route(
    invoice_id: int,
    payload: InvoiceUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("invoices.manage")),
):
    return update_invoice(db, invoice_id, payload, user_id=current_user.id)


@router.post("/invoices/{invoice_id}/status", response_model=InvoiceRead)
def change_status_route(
    invoice_id: int,
    payload: InvoiceStatusChange,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("invoices.manage")),
):
    return change_invoice_status(db, invoice_id, payload, user_id=current_user.id)


@router.post("/invoices/{invoice_id}/source-change", response_model=InvoiceRead)
def invoice_source_change_route(
    invoice_id: int,
    payload: InvoiceSourceChange,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("invoices.manage")),
):
    return mark_invoice_source_changed(db, invoice_id, payload, user_id=current_user.id)


@router.post("/invoices/{invoice_id}/confirm-review", response_model=InvoiceRead)
def confirm_invoice_review_route(
    invoice_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("invoices.manage")),
):
    return confirm_invoice_review(db, invoice_id, user_id=current_user.id)


@router.post("/invoices/{invoice_id}/payments", response_model=InvoiceRead)
def register_payment_route(
    invoice_id: int,
    payload: InvoicePaymentCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("payments.manage")),
):
    return register_invoice_payment(db, invoice_id, payload, user_id=current_user.id)


@router.post("/invoices/{invoice_id}/credit-notes", response_model=InvoiceRead)
def create_credit_note_route(
    invoice_id: int,
    payload: CreditNoteCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("invoices.manage")),
):
    return create_credit_note(db, invoice_id, payload, user_id=current_user.id)


@router.get("/invoices/{invoice_id}/pdf")
def invoice_pdf(
    invoice_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("invoices.read")),
):
    pdf, filename = generate_invoice_pdf(db, invoice_id)
    return Response(content=pdf, media_type="application/pdf", headers={"Content-Disposition": f'inline; filename="{filename}"'})


@router.get("/invoice-payments", response_model=list[InvoicePaymentRead])
def read_invoice_payments(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("payments.read")),
):
    return list_invoice_payments(db)


@router.get("/invoice-payments/{payment_id}", response_model=InvoicePaymentRead)
def read_invoice_payment(
    payment_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("payments.read")),
):
    return get_invoice_payment(db, payment_id)


@router.get("/invoice-payments/{payment_id}/receipt-pdf")
def payment_receipt_pdf(
    payment_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("payments.read")),
):
    pdf, filename = generate_invoice_payment_receipt_pdf(db, payment_id)
    return Response(content=pdf, media_type="application/pdf", headers={"Content-Disposition": f'inline; filename="{filename}"'})


@router.get("/invoice-settings", response_model=InvoiceSettingsRead)
def read_invoice_settings(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("invoices.read")),
):
    return get_invoice_settings(db)


@router.patch("/invoice-settings", response_model=InvoiceSettingsRead)
def patch_invoice_settings(
    payload: InvoiceSettingsUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("invoices.manage")),
):
    return update_invoice_settings(db, payload)
