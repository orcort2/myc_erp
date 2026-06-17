from datetime import datetime, timezone

from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.equipment import Equipment
from app.models.service_order import ServiceOrder, ServiceOrderItem
from app.schemas.equipment import (
    EquipmentCreate,
    EquipmentStatusChange,
    EquipmentUpdate,
)
from app.services.audit_logs import write_audit_log


COMPLETED_STATUSES = {"calibrated", "labeled", "not_done"}
TERMINAL_STATUSES = {"labeled", "not_done", "cancelled"}
ALLOWED_TRANSITIONS = {
    "registered": {"realizing", "not_done", "cancelled"},
    "realizing": {"calibrated", "not_done", "cancelled"},
    "calibrated": {"labeled", "not_done", "cancelled"},
    "labeled": set(),
    "not_done": set(),
    "cancelled": set(),
}


def _ensure_active_service_order(db: Session, service_order_id: int) -> ServiceOrder:
    service_order = db.scalar(
        select(ServiceOrder).where(
            ServiceOrder.id == service_order_id,
            ServiceOrder.is_active.is_(True),
        )
    )
    if service_order is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Orden de servicio no encontrada",
        )
    if service_order.status in {"closed", "cancelled"}:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="No se puede modificar equipo de una orden cerrada o cancelada",
        )
    return service_order


def _ensure_service_order_item(
    db: Session, service_order_id: int, service_order_item_id: int | None
) -> None:
    if service_order_item_id is None:
        return
    exists = db.scalar(
        select(ServiceOrderItem.id).where(
            ServiceOrderItem.id == service_order_item_id,
            ServiceOrderItem.service_order_id == service_order_id,
            ServiceOrderItem.is_active.is_(True),
        )
    )
    if exists is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Partida de orden de servicio no encontrada",
        )


def _sync_service_order_equipment_counts(db: Session, service_order_id: int) -> None:
    total_equipment = db.scalar(
        select(func.count(Equipment.id)).where(
            Equipment.service_order_id == service_order_id,
            Equipment.is_active.is_(True),
        )
    )
    completed_equipment = db.scalar(
        select(func.count(Equipment.id)).where(
            Equipment.service_order_id == service_order_id,
            Equipment.is_active.is_(True),
            Equipment.status.in_(COMPLETED_STATUSES),
        )
    )
    service_order = db.get(ServiceOrder, service_order_id)
    if service_order is not None:
        service_order.total_equipment = int(total_equipment or 0)
        service_order.completed_equipment = int(completed_equipment or 0)


def list_equipment(
    db: Session,
    *,
    service_order_id: int | None = None,
    include_inactive: bool = False,
) -> list[Equipment]:
    query = select(Equipment).order_by(Equipment.created_at.desc())
    if service_order_id is not None:
        query = query.where(Equipment.service_order_id == service_order_id)
    if not include_inactive:
        query = query.where(Equipment.is_active.is_(True))
    return list(db.scalars(query).all())


def get_equipment(db: Session, equipment_id: int) -> Equipment:
    equipment = db.scalar(select(Equipment).where(Equipment.id == equipment_id))
    if equipment is None or not equipment.is_active:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Equipo no encontrado",
        )
    return equipment


def create_equipment(
    db: Session, payload: EquipmentCreate, *, user_id: int | None = None
) -> Equipment:
    _ensure_active_service_order(db, payload.service_order_id)
    _ensure_service_order_item(
        db, payload.service_order_id, payload.service_order_item_id
    )
    equipment = Equipment(**payload.model_dump(), status="registered")
    db.add(equipment)
    db.flush()
    _sync_service_order_equipment_counts(db, equipment.service_order_id)
    write_audit_log(
        db,
        action="equipment.created",
        entity="equipment",
        entity_id=equipment.id,
        user_id=user_id,
        new_values={
            "service_order_id": equipment.service_order_id,
            "name": equipment.name,
            "status": equipment.status,
        },
    )
    db.commit()
    db.refresh(equipment)
    return get_equipment(db, equipment.id)


def update_equipment(
    db: Session,
    equipment_id: int,
    payload: EquipmentUpdate,
    *,
    user_id: int | None = None,
) -> Equipment:
    equipment = get_equipment(db, equipment_id)
    _ensure_active_service_order(db, equipment.service_order_id)
    if equipment.status in TERMINAL_STATUSES:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="No se puede editar equipo en estado terminal",
        )
    updates = payload.model_dump(exclude_unset=True)
    _ensure_service_order_item(
        db, equipment.service_order_id, updates.get("service_order_item_id")
    )
    previous_values = {key: getattr(equipment, key) for key in updates}
    for key, value in updates.items():
        setattr(equipment, key, value)
    write_audit_log(
        db,
        action="equipment.updated",
        entity="equipment",
        entity_id=equipment.id,
        user_id=user_id,
        previous_values=previous_values,
        new_values=updates,
    )
    db.commit()
    return get_equipment(db, equipment.id)


def change_status(
    db: Session,
    equipment_id: int,
    new_status: str,
    payload: EquipmentStatusChange | None = None,
    *,
    user_id: int | None = None,
) -> Equipment:
    equipment = get_equipment(db, equipment_id)
    _ensure_active_service_order(db, equipment.service_order_id)
    allowed = ALLOWED_TRANSITIONS.get(equipment.status, set())
    if new_status not in allowed:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Transicion no permitida: {equipment.status} -> {new_status}",
        )
    previous_status = equipment.status
    equipment.status = new_status
    _sync_service_order_equipment_counts(db, equipment.service_order_id)
    write_audit_log(
        db,
        action=f"equipment.{new_status}",
        entity="equipment",
        entity_id=equipment.id,
        user_id=user_id,
        previous_values={"status": previous_status},
        new_values={"status": new_status},
        comment=payload.comment if payload else None,
    )
    db.commit()
    return get_equipment(db, equipment.id)


def deactivate_equipment(
    db: Session, equipment_id: int, *, user_id: int | None = None
) -> Equipment:
    equipment = get_equipment(db, equipment_id)
    _ensure_active_service_order(db, equipment.service_order_id)
    equipment.is_active = False
    equipment.status = "cancelled"
    equipment.deleted_at = datetime.now(timezone.utc)
    equipment.deleted_by = user_id
    _sync_service_order_equipment_counts(db, equipment.service_order_id)
    write_audit_log(
        db,
        action="equipment.deactivated",
        entity="equipment",
        entity_id=equipment.id,
        user_id=user_id,
        previous_values={"is_active": True},
        new_values={"is_active": False, "status": "cancelled"},
    )
    db.commit()
    return equipment
