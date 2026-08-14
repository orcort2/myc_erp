from typing import Literal

from fastapi import APIRouter, Depends, Query, Response
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.models.user import User
from app.schemas.lab_work_order import (
    LabEquipmentWrite,
    LabSignatureGroupWrite,
    LabWorkOrderCreate,
    LabWorkOrderListItem,
    LabWorkOrderRead,
    LabWorkOrderUpdate,
)
from app.schemas.operational_ticket import LabRevisionRead
from app.services.auth import require_permission
from app.services.lab_work_orders import (
    add_equipment,
    complete_group,
    create_additional_work_order,
    create_work_order,
    delete_equipment,
    export_all,
    get_pdf,
    get_work_order,
    list_work_orders,
    sign_group,
    update_equipment,
    update_work_order,
)
from app.services.operational_tickets import get_revision_pdf, list_revisions


router = APIRouter(
    prefix="/mobile/v1/technician/lab-work-orders",
    tags=["mobile-lab-work-orders"],
)


@router.post("", response_model=LabWorkOrderRead, status_code=201)
def create_lab_work_order(
    payload: LabWorkOrderCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("lab_work_orders.use")),
) -> LabWorkOrderRead:
    return create_work_order(db, payload, current_user)


@router.get("", response_model=list[LabWorkOrderListItem])
def list_lab_work_orders(
    folio: str | None = Query(default=None, max_length=20),
    client: str | None = Query(default=None, max_length=255),
    status: Literal["all", "open", "completed"] = "all",
    offset: int = Query(default=0, ge=0),
    limit: int = Query(default=25, ge=1, le=100),
    db: Session = Depends(get_db),
    _current_user: User = Depends(require_permission("lab_work_orders.use")),
) -> list[LabWorkOrderListItem]:
    return list_work_orders(
        db,
        folio=folio,
        client=client,
        work_order_status=status,
        offset=offset,
        limit=limit,
    )


@router.get("/export")
def export_lab_work_orders(
    db: Session = Depends(get_db),
    _current_user: User = Depends(require_permission("lab_work_orders.export")),
) -> Response:
    content, filename = export_all(db)
    return Response(
        content=content,
        media_type="application/zip",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.get("/{work_order_id}", response_model=LabWorkOrderRead)
def get_lab_work_order(
    work_order_id: int,
    db: Session = Depends(get_db),
    _current_user: User = Depends(require_permission("lab_work_orders.use")),
) -> LabWorkOrderRead:
    return get_work_order(db, work_order_id)


@router.patch("/{work_order_id}", response_model=LabWorkOrderRead)
def patch_lab_work_order(
    work_order_id: int,
    payload: LabWorkOrderUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("lab_work_orders.use")),
) -> LabWorkOrderRead:
    return update_work_order(db, work_order_id, payload, current_user)


@router.post("/{work_order_id}/equipment", response_model=LabWorkOrderRead, status_code=201)
def create_lab_equipment(
    work_order_id: int,
    payload: LabEquipmentWrite,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("lab_work_orders.use")),
) -> LabWorkOrderRead:
    return add_equipment(db, work_order_id, payload, current_user)


@router.patch("/{work_order_id}/equipment/{equipment_id}", response_model=LabWorkOrderRead)
def patch_lab_equipment(
    work_order_id: int,
    equipment_id: int,
    payload: LabEquipmentWrite,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("lab_work_orders.use")),
) -> LabWorkOrderRead:
    return update_equipment(db, work_order_id, equipment_id, payload, current_user)


@router.delete("/{work_order_id}/equipment/{equipment_id}", response_model=LabWorkOrderRead)
def remove_lab_equipment(
    work_order_id: int,
    equipment_id: int,
    expected_edit_version: int | None = Query(default=None, ge=1),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("lab_work_orders.use")),
) -> LabWorkOrderRead:
    return delete_equipment(
        db,
        work_order_id,
        equipment_id,
        current_user,
        expected_edit_version=expected_edit_version,
    )


@router.post("/{work_order_id}/additional", response_model=LabWorkOrderRead, status_code=201)
def create_lab_additional_work_order(
    work_order_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("lab_work_orders.use")),
) -> LabWorkOrderRead:
    return create_additional_work_order(db, work_order_id, current_user)


@router.post("/{work_order_id}/signatures", response_model=LabWorkOrderRead)
def create_lab_group_signatures(
    work_order_id: int,
    payload: LabSignatureGroupWrite,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("lab_work_orders.use")),
) -> LabWorkOrderRead:
    return sign_group(db, work_order_id, payload, current_user)


@router.post("/{work_order_id}/complete", response_model=LabWorkOrderRead)
def complete_lab_group(
    work_order_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("lab_work_orders.use")),
) -> LabWorkOrderRead:
    return complete_group(db, work_order_id, current_user)


@router.get("/{work_order_id}/pdf")
def get_lab_pdf(
    work_order_id: int,
    db: Session = Depends(get_db),
    _current_user: User = Depends(require_permission("lab_work_orders.use")),
) -> Response:
    content, filename = get_pdf(db, work_order_id)
    return Response(
        content=content,
        media_type="application/pdf",
        headers={"Content-Disposition": f'inline; filename="{filename}"'},
    )


@router.get("/{work_order_id}/revisions", response_model=list[LabRevisionRead])
def get_lab_revisions(
    work_order_id: int,
    db: Session = Depends(get_db),
    _current_user: User = Depends(require_permission("lab_work_orders.use")),
) -> list[LabRevisionRead]:
    return list_revisions(db, work_order_id)


@router.get("/{work_order_id}/revisions/{revision_number}/pdf")
def get_lab_revision_pdf(
    work_order_id: int,
    revision_number: int,
    db: Session = Depends(get_db),
    _current_user: User = Depends(require_permission("lab_work_orders.use")),
) -> Response:
    content, filename = get_revision_pdf(db, work_order_id, revision_number)
    return Response(
        content=content,
        media_type="application/pdf",
        headers={"Content-Disposition": f'inline; filename="{filename}"'},
    )
