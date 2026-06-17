from fastapi import APIRouter, Depends, Query, Response, status
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.schemas.equipment import (
    EquipmentCreate,
    EquipmentRead,
    EquipmentStatusChange,
    EquipmentUpdate,
)
from app.services.equipment import (
    change_status,
    create_equipment,
    deactivate_equipment,
    get_equipment,
    list_equipment,
    update_equipment,
)


router = APIRouter(prefix="/equipment", tags=["equipment"])


@router.get("", response_model=list[EquipmentRead])
def get_equipment_list(
    service_order_id: int | None = Query(default=None),
    include_inactive: bool = Query(default=False),
    db: Session = Depends(get_db),
) -> list[EquipmentRead]:
    return list_equipment(
        db,
        service_order_id=service_order_id,
        include_inactive=include_inactive,
    )


@router.post("", response_model=EquipmentRead, status_code=status.HTTP_201_CREATED)
def post_equipment(
    payload: EquipmentCreate,
    db: Session = Depends(get_db),
) -> EquipmentRead:
    return create_equipment(db, payload)


@router.get("/{equipment_id}", response_model=EquipmentRead)
def get_equipment_by_id(equipment_id: int, db: Session = Depends(get_db)) -> EquipmentRead:
    return get_equipment(db, equipment_id)


@router.patch("/{equipment_id}", response_model=EquipmentRead)
def patch_equipment(
    equipment_id: int,
    payload: EquipmentUpdate,
    db: Session = Depends(get_db),
) -> EquipmentRead:
    return update_equipment(db, equipment_id, payload)


@router.post("/{equipment_id}/realizing", response_model=EquipmentRead)
def mark_equipment_realizing(
    equipment_id: int,
    payload: EquipmentStatusChange | None = None,
    db: Session = Depends(get_db),
) -> EquipmentRead:
    return change_status(db, equipment_id, "realizing", payload)


@router.post("/{equipment_id}/calibrated", response_model=EquipmentRead)
def mark_equipment_calibrated(
    equipment_id: int,
    payload: EquipmentStatusChange | None = None,
    db: Session = Depends(get_db),
) -> EquipmentRead:
    return change_status(db, equipment_id, "calibrated", payload)


@router.post("/{equipment_id}/labeled", response_model=EquipmentRead)
def mark_equipment_labeled(
    equipment_id: int,
    payload: EquipmentStatusChange | None = None,
    db: Session = Depends(get_db),
) -> EquipmentRead:
    return change_status(db, equipment_id, "labeled", payload)


@router.post("/{equipment_id}/not-done", response_model=EquipmentRead)
def mark_equipment_not_done(
    equipment_id: int,
    payload: EquipmentStatusChange | None = None,
    db: Session = Depends(get_db),
) -> EquipmentRead:
    return change_status(db, equipment_id, "not_done", payload)


@router.delete("/{equipment_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_equipment(equipment_id: int, db: Session = Depends(get_db)) -> Response:
    deactivate_equipment(db, equipment_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
