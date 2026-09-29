"""Acciones administrativas ERP sobre la ejecución técnica MYC Mobile (LAB).

El ERP GOBIERNA pero no edita: cada acción es un wrapper explícito que valida
que el objetivo pertenece al grupo LAB vinculado al ETS
(``ServiceOrderLabLink``), registra la trazabilidad en el ETS y delega en EL
MISMO servicio de dominio que ya usa MYC Mobile. Las reglas de estado,
permisos de dominio, preservación histórica y auditoría viven en esos
servicios; aquí no se duplican.

- Enviar a corrección → ``reopen_lab_field_sheet_directly`` (OT abierta) o
  ``reopen_work_order_directly(equipment_id=...)`` (OT cerrada). Ambos retiran
  la revisión N (intacta, con su PDF final) y abren N+1 editable en Mobile.
- Cancelar / restaurar OT → ``cancel_work_order`` / ``restore_work_order``.
"""
from __future__ import annotations

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.models.lab_work_order import LabWorkOrder
from app.models.service_order import ServiceOrder
from app.models.user import User
from app.schemas.service_order_mobile_execution import (
    MobileExecutionCorrectionRequest,
    MobileExecutionProjection,
)
from app.services.audit_logs import write_audit_log
from app.services.lab_field_sheets import (
    _FIELD_SHEET_REOPEN_ELIGIBLE_WORK_ORDER_STATUSES,
    reopen_lab_field_sheet_directly,
)
from app.services.lab_work_orders import cancel_work_order, restore_work_order
from app.services.operational_tickets import reopen_work_order_directly
from app.services.service_order_mobile_execution import (
    get_mobile_execution_projection,
    require_group_equipment,
    require_linked_lab_group,
)
from app.services.service_orders import TERMINAL_STATUSES

CLOSED_WORK_ORDER_STATUSES = {"completed", "partially_closed"}


def _ensure_governable(db: Session, service_order_id: int, user: User) -> None:
    if user.account_type != "internal":
        raise HTTPException(status_code=403, detail="Acción administrativa reservada a staff MYC")
    order = db.get(ServiceOrder, service_order_id)
    if order is None:
        raise HTTPException(status_code=404, detail="Orden de servicio no encontrada")
    if not order.is_active or order.status in TERMINAL_STATUSES:
        raise HTTPException(
            status_code=409,
            detail="No se puede administrar la ejecución técnica de un ETS inactivo, cerrado o cancelado",
        )


def _reason(value: str) -> str:
    reason = (value or "").strip()
    if not reason:
        raise HTTPException(status_code=422, detail="El motivo es obligatorio")
    return reason


def _group_work_order(members: list[LabWorkOrder], work_order_id: int) -> LabWorkOrder:
    work_order = next((item for item in members if item.id == work_order_id), None)
    if work_order is None:
        raise HTTPException(status_code=404, detail="OT no encontrada en el servicio MYC Mobile vinculado")
    return work_order


def _trace(db: Session, service_order_id: int, user: User, action: str, values: dict, reason: str | None) -> None:
    write_audit_log(
        db,
        action=action,
        entity="service_orders",
        entity_id=service_order_id,
        user_id=user.id,
        new_values={**values, "origin": "erp", **({"reason": reason} if reason else {})},
        comment=reason,
    )


def request_mobile_correction(
    db: Session,
    service_order_id: int,
    equipment_id: int,
    payload: MobileExecutionCorrectionRequest,
    user: User,
) -> MobileExecutionProjection:
    """"Enviar a corrección en MYC Mobile": nunca edita la hoja. Retira N
    (histórica, PDF final intacto) y abre N+1 editable mediante el dominio
    de reapertura existente; Mobile la ve como revisión vigente."""
    _ensure_governable(db, service_order_id, user)
    reason = _reason(payload.reason)
    _link, members = require_linked_lab_group(db, service_order_id)
    work_order, equipment = require_group_equipment(members, equipment_id)
    current = equipment.current_field_sheet
    if current is None or not current.is_active or current.status != "completed":
        raise HTTPException(
            status_code=409,
            detail={
                "code": "LAB_FIELD_SHEET_NOT_COMPLETED",
                "message": "Sólo una Hoja de Campo completada puede enviarse a corrección; una hoja editable ya está disponible en MYC Mobile",
            },
        )
    if work_order.status in _FIELD_SHEET_REOPEN_ELIGIBLE_WORK_ORDER_STATUSES:
        mode = "field_sheet_reopen"
    elif work_order.status in CLOSED_WORK_ORDER_STATUSES:
        mode = "work_order_reopen"
    else:
        raise HTTPException(
            status_code=409,
            detail={
                "code": "LAB_WORK_ORDER_NOT_CORRECTABLE",
                "message": "El estado actual de la OT no admite enviar la hoja a corrección",
            },
        )
    _trace(
        db, service_order_id, user, "service_order.mobile_correction_requested",
        {
            "mode": mode,
            "lab_work_order_id": work_order.id,
            "lab_work_order_folio": work_order.folio,
            "lab_equipment_id": equipment.id,
            "certificate_folio": equipment.certificate_folio,
            "field_sheet_id": current.id,
            "revision_number": current.revision_number,
            **({"signature_policy": payload.signature_policy} if mode == "work_order_reopen" else {}),
        },
        reason,
    )
    # El servicio de dominio verifica su propia autoridad (lab_folios.resolve
    # o work_orders.reopen + política) y hace commit de todo, incluida la
    # trazabilidad ETS; si rechaza, la sesión se descarta sin cambios.
    if mode == "field_sheet_reopen":
        reopen_lab_field_sheet_directly(db, work_order.id, equipment.id, user, reason=reason)
    else:
        reopen_work_order_directly(
            db, work_order.id, user,
            signature_policy=payload.signature_policy, reason=reason, equipment_id=equipment.id,
        )
    return get_mobile_execution_projection(db, service_order_id)


def cancel_mobile_work_order(
    db: Session, service_order_id: int, work_order_id: int, reason: str, user: User,
) -> MobileExecutionProjection:
    _ensure_governable(db, service_order_id, user)
    reason = _reason(reason)
    _link, members = require_linked_lab_group(db, service_order_id)
    work_order = _group_work_order(members, work_order_id)
    _trace(
        db, service_order_id, user, "service_order.mobile_work_order_cancelled",
        {"lab_work_order_id": work_order.id, "lab_work_order_folio": work_order.folio,
         "previous_status": work_order.status},
        reason,
    )
    cancel_work_order(db, work_order.id, user, reason)
    return get_mobile_execution_projection(db, service_order_id)


def restore_mobile_work_order(
    db: Session, service_order_id: int, work_order_id: int, user: User,
) -> MobileExecutionProjection:
    _ensure_governable(db, service_order_id, user)
    _link, members = require_linked_lab_group(db, service_order_id)
    work_order = _group_work_order(members, work_order_id)
    _trace(
        db, service_order_id, user, "service_order.mobile_work_order_restored",
        {"lab_work_order_id": work_order.id, "lab_work_order_folio": work_order.folio},
        None,
    )
    restore_work_order(db, work_order.id, user)
    return get_mobile_execution_projection(db, service_order_id)
