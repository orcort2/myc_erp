from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.models.client import Client
from app.models.equipment import Equipment
from app.models.field_sheet import FieldSheet
from app.models.service_order import ServiceOrder, ServiceWorkOrder
from app.models.user import User
from app.services.mobile_technician_scope import (
    field_sheet_load_options,
    get_assigned_equipment,
    get_assigned_field_sheet,
    get_assigned_service_order,
    get_assigned_work_order,
)


def list_assigned_service_orders(
    db: Session,
    *,
    technician: User,
) -> list[ServiceOrder]:
    """
    Devuelve exclusivamente las órdenes de servicio asignadas
    al técnico autenticado.
    """

    query = (
        select(ServiceOrder)
        .where(
            ServiceOrder.is_active.is_(True),
            ServiceOrder.technician_id == technician.id,
        )
        .options(
            selectinload(ServiceOrder.items),
            selectinload(ServiceOrder.work_orders).selectinload(
                ServiceWorkOrder.signature_cycle_links
            ),
            selectinload(ServiceOrder.equipment),
            selectinload(ServiceOrder.client).selectinload(Client.contacts),
            selectinload(ServiceOrder.quotation),
            selectinload(ServiceOrder.certificates),
            selectinload(ServiceOrder.advisor),
            selectinload(ServiceOrder.technician),
        )
        .order_by(ServiceOrder.created_at.desc())
    )

    return list(db.scalars(query).all())


def list_assigned_work_orders(
    db: Session,
    *,
    technician: User,
) -> list[ServiceWorkOrder]:
    query = (
        select(ServiceWorkOrder)
        .join(ServiceOrder, ServiceOrder.id == ServiceWorkOrder.service_order_id)
        .where(
            ServiceWorkOrder.is_active.is_(True),
            ServiceOrder.is_active.is_(True),
            ServiceOrder.technician_id == technician.id,
        )
        .order_by(ServiceWorkOrder.work_order_number.asc())
    )
    return list(db.scalars(query).all())


def list_assigned_equipment(
    db: Session,
    *,
    technician: User,
) -> list[Equipment]:
    query = (
        select(Equipment)
        .join(ServiceOrder, ServiceOrder.id == Equipment.service_order_id)
        .where(
            Equipment.is_active.is_(True),
            ServiceOrder.is_active.is_(True),
            ServiceOrder.technician_id == technician.id,
        )
        .options(selectinload(Equipment.work_order))
        .order_by(Equipment.id.asc())
    )
    return list(db.scalars(query).all())


def list_assigned_field_sheets(
    db: Session,
    *,
    technician: User,
) -> list[FieldSheet]:
    query = (
        select(FieldSheet)
        .join(Equipment, Equipment.id == FieldSheet.equipment_id)
        .join(ServiceOrder, ServiceOrder.id == Equipment.service_order_id)
        .where(
            FieldSheet.is_active.is_(True),
            Equipment.is_active.is_(True),
            ServiceOrder.is_active.is_(True),
            ServiceOrder.technician_id == technician.id,
        )
        .options(*field_sheet_load_options())
        .order_by(FieldSheet.updated_at.desc())
    )
    return list(db.scalars(query).all())


__all__ = [
    "get_assigned_service_order",
    "get_assigned_work_order",
    "get_assigned_equipment",
    "get_assigned_field_sheet",
    "list_assigned_service_orders",
    "list_assigned_work_orders",
    "list_assigned_equipment",
    "list_assigned_field_sheets",
]
