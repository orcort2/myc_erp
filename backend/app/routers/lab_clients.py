from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.core.mobile.security import MobileSecurityContext, require_mobile_permission
from app.schemas.lab_client import (
    LabClientCreate,
    LabClientImportSummary,
    LabClientRead,
    LabClientUpdate,
)
from app.services.auth import user_has_permission
from app.services.lab_clients import (
    activate_lab_client,
    count_inactive_lab_clients,
    create_lab_client,
    deactivate_lab_client,
    import_lab_clients_xlsx,
    list_lab_clients,
    update_lab_client,
)


router = APIRouter(prefix="/mobile/v1/technician/lab-clients", tags=["mobile-lab-clients"])


@router.get("/inactive-count", response_model=dict[str, int])
def get_inactive_client_count(
    db: Session = Depends(get_db),
    context: MobileSecurityContext = Depends(require_mobile_permission("lab_clients.deactivate")),
) -> dict[str, int]:
    if context.actor_type != "internal" or not user_has_permission(
        context.user, "lab_clients.deactivate"
    ):
        raise HTTPException(status_code=403, detail="Sólo Admin puede consultar clientes LAB inactivos")
    return {
        "count": count_inactive_lab_clients(
            db, operator_client_id=context.client_id
        )
    }


@router.get("", response_model=list[LabClientRead])
def get_clients(
    search: str | None = Query(default=None, max_length=255),
    include_inactive: bool = Query(default=False),
    offset: int = Query(default=0, ge=0),
    limit: int = Query(default=25, ge=1, le=100),
    db: Session = Depends(get_db),
    context: MobileSecurityContext = Depends(
        require_mobile_permission("lab_clients.read", "work_orders.read_organization")
    ),
) -> list[LabClientRead]:
    return list_lab_clients(
        db,
        operator_client_id=context.client_id,
        search=search,
        include_inactive=include_inactive,
        offset=offset,
        limit=limit,
    )


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


@router.patch("/{client_id}", response_model=LabClientRead)
def patch_client(
    client_id: int,
    payload: LabClientUpdate,
    db: Session = Depends(get_db),
    context: MobileSecurityContext = Depends(require_mobile_permission("lab_clients.update")),
) -> LabClientRead:
    return update_lab_client(
        db, client_id, payload, context.user, operator_client_id=context.client_id
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


@router.post("/{client_id}/deactivate", response_model=LabClientRead)
def post_deactivate_client(
    client_id: int,
    db: Session = Depends(get_db),
    context: MobileSecurityContext = Depends(require_mobile_permission("lab_clients.deactivate")),
) -> LabClientRead:
    if context.actor_type != "internal" or not user_has_permission(context.user, "lab_clients.deactivate"):
        raise HTTPException(status_code=403, detail="Sólo Admin puede desactivar clientes LAB")
    return deactivate_lab_client(
        db, client_id, operator_client_id=context.client_id, user=context.user
    )


@router.post("/{client_id}/activate", response_model=LabClientRead)
def post_activate_client(
    client_id: int,
    db: Session = Depends(get_db),
    context: MobileSecurityContext = Depends(require_mobile_permission("lab_clients.deactivate")),
) -> LabClientRead:
    if context.actor_type != "internal" or not user_has_permission(context.user, "lab_clients.deactivate"):
        raise HTTPException(status_code=403, detail="Sólo Admin puede reactivar clientes LAB")
    return activate_lab_client(
        db, client_id, operator_client_id=context.client_id, user=context.user
    )
