from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.schemas.certificate import CertificateRead
from app.schemas.quotation import QuotationRead
from app.schemas.service_order import ServiceOrderRead
from app.services.audit_logs import write_audit_log
from app.services.certificates import get_certificate, list_certificates
from app.services.quotations import list_quotations
from app.services.service_orders import list_service_orders


router = APIRouter(prefix="/client-portal", tags=["client-portal"])


@router.get("/quotations", response_model=list[QuotationRead])
def get_client_portal_quotations(db: Session = Depends(get_db)) -> list[QuotationRead]:
    return [item for item in list_quotations(db) if item.status in {"sent", "waiting", "accepted"}]


@router.get("/service-orders", response_model=list[ServiceOrderRead])
def get_client_portal_service_orders(db: Session = Depends(get_db)) -> list[ServiceOrderRead]:
    return [item for item in list_service_orders(db) if item.status not in {"cancelled"}]


@router.get("/certificates", response_model=list[CertificateRead])
def get_client_portal_certificates(db: Session = Depends(get_db)) -> list[CertificateRead]:
    return list_certificates(db, client_visible=True)


@router.get("/certificates/{certificate_id}/pdf")
def get_client_portal_certificate_pdf(
    certificate_id: int,
    db: Session = Depends(get_db),
) -> FileResponse:
    certificate = get_certificate(db, certificate_id)
    if not certificate.client_visible or not certificate.authenticated_pdf_path:
        raise HTTPException(status_code=404, detail="Certificado no disponible")
    path = Path(certificate.authenticated_pdf_path)
    if not path.exists():
        raise HTTPException(status_code=404, detail="PDF autenticado no encontrado")
    write_audit_log(
        db,
        action="client_portal.certificate_downloaded",
        entity="certificates",
        entity_id=certificate.id,
        new_values={"folio": certificate.folio},
    )
    db.commit()
    return FileResponse(
        path,
        media_type="application/pdf",
        filename=f"{certificate.authentication_code or certificate.folio}.pdf",
    )
