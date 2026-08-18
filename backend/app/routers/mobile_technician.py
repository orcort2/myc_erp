from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.models.user import User
from app.schemas.equipment import EquipmentRead
from app.schemas.field_sheet import FieldSheetRead
from app.schemas.service_order import ServiceOrderRead, ServiceWorkOrderRead
from app.schemas.sale_execution import SaleBoardRead, SaleDeliveryAccept, SaleDeliveryConfirm, SaleDeliveryRead
from app.services.auth import require_permission
from app.services.mobile_technician import (
    list_assigned_equipment,
    list_assigned_field_sheets,
    list_assigned_service_orders,
    list_assigned_work_orders,
)
from app.services.mobile_technician_scope import (
    get_assigned_equipment,
    get_assigned_field_sheet,
    get_assigned_service_order,
    get_assigned_work_order,
)
from app.services.sale_execution import (
    accept_technician_delivery,
    confirm_delivery,
    list_technician_deliveries,
)


router = APIRouter(
    prefix="/mobile/v1/technician",
    tags=["mobile-technician"],
)


@router.get("/sale-deliveries", response_model=list[SaleDeliveryRead])
def get_my_sale_deliveries(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("service_orders.sales.deliver")),
):
    return list_technician_deliveries(db, current_user.id)


@router.post("/sale-deliveries/{delivery_id}/accept", response_model=SaleBoardRead)
def accept_my_sale_delivery(
    delivery_id: int, payload: SaleDeliveryAccept, db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("service_orders.sales.deliver")),
):
    delivery = next((item for item in list_technician_deliveries(db, current_user.id) if item.id == delivery_id), None)
    if delivery is None:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Entrega no asignada")
    return accept_technician_delivery(db, delivery.service_order_id, delivery.id, payload, actor=current_user)


@router.post("/sale-deliveries/{delivery_id}/receive", response_model=SaleBoardRead)
def receive_my_sale_delivery(
    delivery_id: int, payload: SaleDeliveryConfirm, db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("service_orders.sales.deliver")),
):
    delivery = next((item for item in list_technician_deliveries(db, current_user.id) if item.id == delivery_id), None)
    if delivery is None:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Entrega no asignada")
    return confirm_delivery(db, delivery.service_order_id, delivery.id, payload, actor=current_user)


# ============================================================
# SERVICE ORDERS
# ============================================================


@router.get(
    "/service-orders",
    response_model=list[ServiceOrderRead],
)
def get_my_service_orders(
    db: Session = Depends(get_db),
    current_user: User = Depends(
        require_permission("service_orders.read_assigned")
    ),
) -> list[ServiceOrderRead]:
    """
    Devuelve exclusivamente los servicios asignados
    al técnico autenticado.
    """

    return list_assigned_service_orders(
        db,
        technician=current_user,
    )


@router.get(
    "/service-orders/{service_order_id}",
    response_model=ServiceOrderRead,
)
def get_my_service_order(
    service_order_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(
        require_permission("service_orders.read_assigned")
    ),
) -> ServiceOrderRead:
    """
    Devuelve un servicio únicamente cuando está asignado
    al técnico autenticado.
    """

    return get_assigned_service_order(
        db,
        service_order_id=service_order_id,
        technician=current_user,
    )


# ============================================================
# WORK ORDERS
# ============================================================


@router.get(
    "/work-orders",
    response_model=list[ServiceWorkOrderRead],
)
def get_my_work_orders(
    db: Session = Depends(get_db),
    current_user: User = Depends(
        require_permission("service_orders.read_assigned")
    ),
) -> list[ServiceWorkOrderRead]:
    """
    Devuelve exclusivamente las órdenes de trabajo
    pertenecientes a servicios asignados al técnico.
    """

    return list_assigned_work_orders(db, technician=current_user)


@router.get(
    "/work-orders/{work_order_id}",
    response_model=ServiceWorkOrderRead,
)
def get_my_work_order(
    work_order_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(
        require_permission("service_orders.read_assigned")
    ),
) -> ServiceWorkOrderRead:
    """
    Devuelve una orden de trabajo únicamente cuando
    pertenece a un servicio asignado al técnico.
    """

    return get_assigned_work_order(
        db,
        work_order_id=work_order_id,
        technician=current_user,
    )


# ============================================================
# EQUIPMENT
# ============================================================


@router.get(
    "/equipment",
    response_model=list[EquipmentRead],
)
def get_my_equipment(
    db: Session = Depends(get_db),
    current_user: User = Depends(
        require_permission("service_orders.read_assigned")
    ),
) -> list[EquipmentRead]:
    """
    Devuelve exclusivamente los equipos pertenecientes
    a servicios asignados al técnico autenticado.
    """

    return list_assigned_equipment(db, technician=current_user)


@router.get(
    "/equipment/{equipment_id}",
    response_model=EquipmentRead,
)
def get_my_equipment_item(
    equipment_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(
        require_permission("service_orders.read_assigned")
    ),
) -> EquipmentRead:
    """
    Devuelve un equipo únicamente cuando pertenece
    a un servicio asignado al técnico autenticado.
    """

    return get_assigned_equipment(
        db,
        equipment_id=equipment_id,
        technician=current_user,
    )


# ============================================================
# FIELD SHEETS
# ============================================================


@router.get(
    "/field-sheets",
    response_model=list[FieldSheetRead],
)
def get_my_field_sheets(
    db: Session = Depends(get_db),
    current_user: User = Depends(
        require_permission("service_orders.read_assigned")
    ),
    _field_sheet_reader: User = Depends(require_permission("field_sheets.read")),
) -> list[FieldSheetRead]:
    """
    Devuelve exclusivamente las hojas de campo asociadas
    a equipos de servicios asignados al técnico.
    """

    return list_assigned_field_sheets(db, technician=current_user)


@router.get(
    "/field-sheets/{field_sheet_id}",
    response_model=FieldSheetRead,
)
def get_my_field_sheet(
    field_sheet_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(
        require_permission("service_orders.read_assigned")
    ),
    _field_sheet_reader: User = Depends(require_permission("field_sheets.read")),
) -> FieldSheetRead:
    """
    Devuelve una hoja de campo únicamente cuando pertenece
    a un equipo de un servicio asignado al técnico.
    """

    return get_assigned_field_sheet(
        db,
        field_sheet_id=field_sheet_id,
        technician=current_user,
    )
