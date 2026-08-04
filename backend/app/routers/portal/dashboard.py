from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.core.portal.security import PortalSecurityContext, require_portal_permission
from app.models.certificate import Certificate
from app.models.invoice import Invoice
from app.models.quotation import Quotation
from app.models.service_order import ServiceOrder
from app.schemas.portal.dashboard import PortalDashboardRead

router = APIRouter(prefix="/client-portal/dashboard", tags=["client-portal-dashboard"])


@router.get("", response_model=PortalDashboardRead)
def dashboard(context: PortalSecurityContext = Depends(require_portal_permission("portal.view")), db: Session = Depends(get_db)):
    client_id = context.client.id
    return PortalDashboardRead(
        client_id=client_id,
        client_name=context.client.commercial_name or context.client.legal_name,
        quotations=db.scalar(select(func.count(Quotation.id)).where(Quotation.client_id == client_id)) or 0,
        services=db.scalar(select(func.count(ServiceOrder.id)).where(ServiceOrder.client_id == client_id)) or 0,
        certificates=db.scalar(select(func.count(Certificate.id)).join(ServiceOrder).where(ServiceOrder.client_id == client_id, Certificate.client_visible.is_(True))) or 0,
        invoices=db.scalar(select(func.count(Invoice.id)).where(Invoice.client_id == client_id)) or 0,
    )
