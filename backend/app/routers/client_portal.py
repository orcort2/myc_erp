from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.schemas.certificate import CertificateRead
from app.schemas.quotation import QuotationRead
from app.schemas.service_order import ServiceOrderRead
from app.services.audit_logs import write_audit_log
from app.services.certificates import get_certificate, list_certificates
from app.services.client_portal import PortalClientContext, get_portal_client_context
from app.services.quotations import list_quotations
from app.services.service_orders import list_service_orders
from app.services.storage_service import require_deliverable_file
from app.core.portal.security import PortalSecurityContext, require_portal_permission
from app.models.invoice import Invoice, InvoicePayment
from app.models.equipment import Equipment
from app.models.service_order import ServiceOrder
from sqlalchemy import select


router = APIRouter(prefix="/client-portal", tags=["client-portal"])


@router.get("/quotations", response_model=list[QuotationRead])
def get_client_portal_quotations(
    db: Session = Depends(get_db),
    security: PortalSecurityContext = Depends(require_portal_permission("quotations.view")),
) -> list[QuotationRead]:
    context = PortalClientContext(security.user, security.client)
    return [
        item
        for item in list_quotations(db, client_id=context.client.id)
        if item.status in {"sent", "waiting", "accepted"}
    ]


@router.get("/service-orders", response_model=list[ServiceOrderRead])
def get_client_portal_service_orders(
    db: Session = Depends(get_db),
    security: PortalSecurityContext = Depends(require_portal_permission("services.view")),
) -> list[ServiceOrderRead]:
    context = PortalClientContext(security.user, security.client)
    return [
        item
        for item in list_service_orders(db, client_id=context.client.id)
        if item.status not in {"cancelled"}
    ]


@router.get("/certificates", response_model=list[CertificateRead])
def get_client_portal_certificates(
    db: Session = Depends(get_db),
    security: PortalSecurityContext = Depends(require_portal_permission("certificates.view")),
) -> list[CertificateRead]:
    context = PortalClientContext(security.user, security.client)
    return list_certificates(
        db,
        client_id=context.client.id,
        client_visible=True,
    )


@router.get("/certificates/{certificate_id}/pdf")
def get_client_portal_certificate_pdf(
    certificate_id: int,
    db: Session = Depends(get_db),
    security: PortalSecurityContext = Depends(require_portal_permission("certificates.download")),
) -> FileResponse:
    context = PortalClientContext(security.user, security.client)
    certificate = get_certificate(db, certificate_id)
    if (
        certificate.service_order.client_id != context.client.id
        or not certificate.client_visible
        or not certificate.authenticated_pdf_path
    ):
        raise HTTPException(status_code=404, detail="Certificado no disponible")
    path = require_deliverable_file(certificate.authenticated_pdf_path, not_found_detail="PDF autenticado no encontrado")
    write_audit_log(
        db,
        action="client_portal.certificate_downloaded",
        entity="certificates",
        entity_id=certificate.id,
        user_id=context.user.id,
        new_values={"folio": certificate.folio},
    )
    db.commit()
    return FileResponse(
        path,
        media_type="application/pdf",
        filename=f"{certificate.authentication_code or certificate.folio}.pdf",
    )


@router.get("/company")
def get_company(context: PortalSecurityContext = Depends(require_portal_permission("client.view"))) -> dict:
    client = context.client
    return {"id": client.id, "legal_name": client.legal_name, "commercial_name": client.commercial_name, "rfc": client.rfc, "email": client.email, "phone": client.phone}


@router.get("/equipment")
def get_equipment(db: Session = Depends(get_db), context: PortalSecurityContext = Depends(require_portal_permission("equipment.view"))) -> list[dict]:
    items = db.scalars(select(Equipment).join(ServiceOrder).where(ServiceOrder.client_id == context.client.id, Equipment.is_active.is_(True)).order_by(Equipment.created_at.desc())).all()
    return [{"id": item.id, "service_order_id": item.service_order_id, "name": item.name, "brand": item.brand, "model": item.model, "serial_number": item.serial_number, "status": item.status} for item in items]


@router.get("/invoices")
def get_invoices(db: Session = Depends(get_db), context: PortalSecurityContext = Depends(require_portal_permission("invoices.view"))) -> list[dict]:
    items = db.scalars(select(Invoice).where(Invoice.client_id == context.client.id, Invoice.status != "draft", Invoice.is_active.is_(True)).order_by(Invoice.created_at.desc())).all()
    return [{"id": item.id, "folio": item.folio, "issued_on": item.issued_on, "due_on": item.due_on, "total": item.total, "amount_paid": item.amount_paid, "balance_due": item.balance_due, "currency": item.currency, "status": item.status} for item in items]


@router.get("/payments")
def get_payments(db: Session = Depends(get_db), context: PortalSecurityContext = Depends(require_portal_permission("payments.view"))) -> list[dict]:
    items = db.execute(select(InvoicePayment, Invoice.folio).join(Invoice, Invoice.id == InvoicePayment.invoice_id).where(Invoice.client_id == context.client.id).order_by(InvoicePayment.created_at.desc())).all()
    return [{"id": payment.id, "invoice_id": payment.invoice_id, "invoice_folio": folio, "paid_on": payment.paid_on, "amount": payment.amount, "status": payment.status, "reference": payment.reference} for payment, folio in items]
