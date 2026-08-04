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


router = APIRouter(prefix="/client-portal", tags=["client-portal"])


@router.get("/quotations", response_model=list[QuotationRead])
def get_client_portal_quotations(
    db: Session = Depends(get_db),
    context: PortalClientContext = Depends(get_portal_client_context),
) -> list[QuotationRead]:
    return [
        item
        for item in list_quotations(db, client_id=context.client.id)
        if item.status in {"sent", "waiting", "accepted"}
    ]


@router.get("/service-orders", response_model=list[ServiceOrderRead])
def get_client_portal_service_orders(
    db: Session = Depends(get_db),
    context: PortalClientContext = Depends(get_portal_client_context),
) -> list[ServiceOrderRead]:
    return [
        item
        for item in list_service_orders(db, client_id=context.client.id)
        if item.status not in {"cancelled"}
    ]


@router.get("/certificates", response_model=list[CertificateRead])
def get_client_portal_certificates(
    db: Session = Depends(get_db),
    context: PortalClientContext = Depends(get_portal_client_context),
) -> list[CertificateRead]:
    return list_certificates(
        db,
        client_id=context.client.id,
        client_visible=True,
    )


@router.get("/certificates/{certificate_id}/pdf")
def get_client_portal_certificate_pdf(
    certificate_id: int,
    db: Session = Depends(get_db),
    context: PortalClientContext = Depends(get_portal_client_context),
) -> FileResponse:
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
