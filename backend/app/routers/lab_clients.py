from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.core.mobile.security import MobileSecurityContext, require_mobile_permission
from app.schemas.lab_client import LabClientCreate, LabClientImportSummary, LabClientRead
from app.services.auth import user_has_permission
from app.services.lab_clients import create_lab_client, import_lab_clients_xlsx, list_lab_clients


router = APIRouter(prefix="/mobile/v1/technician/lab-clients", tags=["mobile-lab-clients"])


@router.get("", response_model=list[LabClientRead])
def get_clients(
    search: str | None = Query(default=None, max_length=255),
    db: Session = Depends(get_db),
    context: MobileSecurityContext = Depends(
        require_mobile_permission("lab_clients.read", "work_orders.read_organization")
    ),
) -> list[LabClientRead]:
    return list_lab_clients(db, operator_client_id=context.client_id, search=search)


@router.post("", response_model=LabClientRead, status_code=201)
def post_client(
    payload: LabClientCreate,
    db: Session = Depends(get_db),
    context: MobileSecurityContext = Depends(
        require_mobile_permission("lab_clients.create", "work_orders.group.request")
    ),
) -> LabClientRead:
    return create_lab_client(
        db, payload, context.user, operator_client_id=context.client_id
    )


@router.post("/import", response_model=LabClientImportSummary)
async def import_clients(
    upload: UploadFile = File(...),
    db: Session = Depends(get_db),
    context: MobileSecurityContext = Depends(require_mobile_permission("lab_clients.import")),
) -> LabClientImportSummary:
    if context.actor_type != "internal" or not user_has_permission(context.user, "lab_clients.import"):
        raise HTTPException(status_code=403, detail="Sólo Admin puede importar clientes LAB")
    return await import_lab_clients_xlsx(db, upload, context.user)
