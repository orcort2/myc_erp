from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.models.equipment import Equipment
from app.models.field_sheet import FieldSheet
from app.models.service_order import ServiceOrder, ServiceWorkOrder
from app.models.user import User


def _not_found() -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail="Recurso no encontrado",
    )


def field_sheet_load_options():
    return (
        selectinload(FieldSheet.equipment),
        selectinload(FieldSheet.work_order),
        selectinload(FieldSheet.results_rows),
        selectinload(FieldSheet.signatures),
        selectinload(FieldSheet.reference_standard_links),
        selectinload(FieldSheet.certificates),
    )


def get_assigned_service_order(
    db: Session,
    *,
    service_order_id: int,
    technician: User,
) -> ServiceOrder:
    service_order = db.scalar(
        select(ServiceOrder)
        .where(
            ServiceOrder.id == service_order_id,
            ServiceOrder.is_active.is_(True),
            ServiceOrder.technician_id == technician.id,
        )
    )

    if service_order is None:
        raise _not_found()

    return service_order


def get_assigned_work_order(
    db: Session,
    *,
    work_order_id: int,
    technician: User,
) -> ServiceWorkOrder:
    work_order = db.scalar(
        select(ServiceWorkOrder)
        .join(
            ServiceOrder,
            ServiceOrder.id == ServiceWorkOrder.service_order_id,
        )
        .where(
            ServiceWorkOrder.id == work_order_id,
            ServiceWorkOrder.is_active.is_(True),
            ServiceOrder.is_active.is_(True),
            ServiceOrder.technician_id == technician.id,
        )
    )

    if work_order is None:
        raise _not_found()

    return work_order


def get_assigned_equipment(
    db: Session,
    *,
    equipment_id: int,
    technician: User,
) -> Equipment:
    equipment = db.scalar(
        select(Equipment)
        .join(
            ServiceOrder,
            ServiceOrder.id == Equipment.service_order_id,
        )
        .where(
            Equipment.id == equipment_id,
            Equipment.is_active.is_(True),
            ServiceOrder.is_active.is_(True),
            ServiceOrder.technician_id == technician.id,
        )
        .options(
            selectinload(Equipment.work_order),
            selectinload(Equipment.field_sheets),
        )
    )

    if equipment is None:
        raise _not_found()

    return equipment


def get_assigned_field_sheet(
    db: Session,
    *,
    field_sheet_id: int,
    technician: User,
) -> FieldSheet:
    field_sheet = db.scalar(
        select(FieldSheet)
        .join(
            Equipment,
            Equipment.id == FieldSheet.equipment_id,
        )
        .join(
            ServiceOrder,
            ServiceOrder.id == Equipment.service_order_id,
        )
        .where(
            FieldSheet.id == field_sheet_id,
            FieldSheet.is_active.is_(True),
            Equipment.is_active.is_(True),
            ServiceOrder.is_active.is_(True),
            ServiceOrder.technician_id == technician.id,
        )
        .options(*field_sheet_load_options())
    )

    if field_sheet is None:
        raise _not_found()

    return field_sheet
