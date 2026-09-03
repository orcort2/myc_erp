from __future__ import annotations

import hashlib
from datetime import datetime, timezone

from fastapi import HTTPException
from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from app.models.lab_delivery_group_receipt import LabDeliveryGroupReceipt
from app.models.lab_delivery_item import LabDeliveryItem
from app.models.lab_work_order import LabWorkOrder, LabWorkOrderEquipment
from app.models.lab_work_order_delivery import LabWorkOrderDelivery
from app.models.operational_ticket import OperationalTicket
from app.models.user import User
from app.schemas.lab_work_order import (
    LabDeliveryCreate,
    LabDeliveryGroupStatusRead,
    LabDeliveryItemRead,
    LabDeliveryPendingEquipmentItem,
    LabDeliveryRead,
    LabDeliveryVoid,
)
from app.services.audit_logs import write_audit_log
from app.services.auth import user_has_permission
from app.services.lab_delivery_pdfs import (
    generate_lab_delivery_final_receipt,
    generate_lab_delivery_receipt,
)
from app.services.lab_work_orders import _decode_signature, _get, _group, _lock_historical_group, _root_id


def _relevant_group_members(group: list[LabWorkOrder]) -> list[LabWorkOrder]:
    """OT vigentes del grupo para efectos de entrega: las canceladas nunca
    sucedieron operativamente y quedan fuera; partially_closed cuenta como
    cerrada igual que completed (la excepción de cierre parcial ya fue
    autorizada -- no vuelve a bloquear la entrega física)."""
    return [item for item in group if item.status != "cancelled"]


def _delivered_equipment_ids(db: Session, root_work_order_id: int) -> dict[int, datetime]:
    rows = db.execute(
        select(LabDeliveryItem.equipment_id, LabWorkOrderDelivery.delivered_at)
        .join(LabWorkOrderDelivery, LabDeliveryItem.delivery_id == LabWorkOrderDelivery.id)
        .where(
            LabWorkOrderDelivery.root_work_order_id == root_work_order_id,
            LabWorkOrderDelivery.status == "completed",
        )
    ).all()
    return {row[0]: row[1] for row in rows}


def _pending_equipment(
    members: list[LabWorkOrder], delivered_ids: dict[int, datetime]
) -> list[LabWorkOrderEquipment]:
    return [
        equipment
        for item in members
        for equipment in item.equipment
        if equipment.id not in delivered_ids
    ]


def _sync_departure_dates(members: list[LabWorkOrder], delivered_ids: dict[int, datetime]) -> None:
    for item in members:
        equipment_ids = [equipment.id for equipment in item.equipment]
        if not equipment_ids:
            continue
        dates = [delivered_ids[eid] for eid in equipment_ids if eid in delivered_ids]
        item.departure_date = max(dates).date() if len(dates) == len(equipment_ids) else None


def _reload_delivery(db: Session, delivery_id: int) -> LabWorkOrderDelivery:
    delivery = db.scalar(
        select(LabWorkOrderDelivery)
        .options(
            selectinload(LabWorkOrderDelivery.delivered_by),
            selectinload(LabWorkOrderDelivery.items).selectinload(LabDeliveryItem.work_order),
        )
        .where(LabWorkOrderDelivery.id == delivery_id)
    )
    if delivery is None:
        raise HTTPException(status_code=404, detail="Entrega no encontrada")
    return delivery


def _read_delivery(delivery: LabWorkOrderDelivery) -> LabDeliveryRead:
    return LabDeliveryRead(
        id=delivery.id,
        root_work_order_id=delivery.root_work_order_id,
        exhibition_number=delivery.exhibition_number,
        delivery_type=delivery.delivery_type,
        delivery_method=delivery.delivery_method,
        status=delivery.status,
        partial_delivery_ticket_id=delivery.partial_delivery_ticket_id,
        delivered_at=delivery.delivered_at,
        delivered_by_user_id=delivery.delivered_by_user_id,
        delivered_by_name=delivery.delivered_by.full_name,
        recipient_name=delivery.recipient_name,
        notes=delivery.notes,
        voucher_available=bool(delivery.voucher_pdf),
        voided_at=delivery.voided_at,
        void_reason=delivery.void_reason,
        items=[
            LabDeliveryItemRead(
                id=item.id,
                work_order_id=item.work_order_id,
                work_order_folio=item.work_order.folio,
                equipment_id=item.equipment_id,
                position_snapshot=item.position_snapshot,
                instrument_snapshot=item.instrument_snapshot,
                brand_snapshot=item.brand_snapshot,
                identification_snapshot=item.identification_snapshot,
                serial_number_snapshot=item.serial_number_snapshot,
                certificate_folio_snapshot=item.certificate_folio_snapshot,
            )
            for item in delivery.items
        ],
    )


def get_lab_delivery_group_status(db: Session, work_order_id: int) -> LabDeliveryGroupStatusRead:
    work_order = _get(db, work_order_id)
    root_id = _root_id(work_order)
    group = _group(db, work_order)
    members = _relevant_group_members(group)
    delivered_ids = _delivered_equipment_ids(db, root_id)
    pending = _pending_equipment(members, delivered_ids)
    total_equipment = sum(len(item.equipment) for item in members)
    deliveries = list(
        db.scalars(
            select(LabWorkOrderDelivery)
            .options(
                selectinload(LabWorkOrderDelivery.delivered_by),
                selectinload(LabWorkOrderDelivery.items).selectinload(LabDeliveryItem.work_order),
            )
            .where(LabWorkOrderDelivery.root_work_order_id == root_id)
            .order_by(LabWorkOrderDelivery.exhibition_number)
        )
    )
    receipt = db.scalar(
        select(LabDeliveryGroupReceipt)
        .where(
            LabDeliveryGroupReceipt.root_work_order_id == root_id,
            LabDeliveryGroupReceipt.superseded_at.is_(None),
        )
        .order_by(LabDeliveryGroupReceipt.version.desc())
        .limit(1)
    )
    pending_ticket_id = db.scalar(
        select(OperationalTicket.id)
        .where(
            OperationalTicket.work_order_id == root_id,
            OperationalTicket.type == "partial_delivery",
            OperationalTicket.status.in_(("pending", "approved")),
        )
        .order_by(OperationalTicket.id.desc())
        .limit(1)
    )
    return LabDeliveryGroupStatusRead(
        root_work_order_id=root_id,
        total_equipment=total_equipment,
        delivered_equipment=total_equipment - len(pending),
        pending_equipment=[
            LabDeliveryPendingEquipmentItem(
                work_order_id=equipment.work_order_id,
                work_order_folio=equipment.work_order.folio,
                equipment_id=equipment.id,
                position=equipment.position,
                instrument=equipment.instrument,
                brand=equipment.brand,
                identification=equipment.identification,
                serial_number=equipment.serial_number,
                certificate_folio=equipment.certificate_folio,
            )
            for equipment in pending
        ],
        exhibitions=[_read_delivery(item) for item in deliveries],
        group_complete=total_equipment > 0 and not pending,
        final_receipt_available=receipt is not None,
        final_receipt_version=receipt.version if receipt else None,
        pending_partial_delivery_ticket_id=pending_ticket_id,
    )


def _next_exhibition_number(db: Session, root_id: int) -> int:
    current_max = db.scalar(
        select(func.max(LabWorkOrderDelivery.exhibition_number)).where(
            LabWorkOrderDelivery.root_work_order_id == root_id
        )
    )
    return (current_max or 0) + 1


def _create_delivery_event(
    db: Session,
    *,
    root_work_order: LabWorkOrder,
    equipment_items: list[LabWorkOrderEquipment],
    delivery_type: str,
    payload: LabDeliveryCreate,
    user: User,
    partial_delivery_ticket_id: int | None,
) -> LabWorkOrderDelivery:
    _decode_signature(payload.delivered_by_signature_data_url)
    _decode_signature(payload.recipient_signature_data_url)
    now = datetime.now(timezone.utc)
    if now.date() < root_work_order.reception_date:
        raise HTTPException(status_code=409, detail="La entrega no puede ser anterior a la recepción")
    delivery = LabWorkOrderDelivery(
        root_work_order_id=root_work_order.id,
        exhibition_number=_next_exhibition_number(db, root_work_order.id),
        delivery_type=delivery_type,
        delivery_method=payload.delivery_method,
        status="completed",
        partial_delivery_ticket_id=partial_delivery_ticket_id,
        delivered_at=now,
        delivered_by_user_id=user.id,
        delivered_by_signature_data_url=payload.delivered_by_signature_data_url,
        recipient_name=payload.recipient_name.strip(),
        recipient_signature_data_url=payload.recipient_signature_data_url,
        notes=(payload.notes or "").strip() or None,
    )
    db.add(delivery)
    db.flush()
    for equipment in equipment_items:
        db.add(
            LabDeliveryItem(
                delivery_id=delivery.id,
                work_order_id=equipment.work_order_id,
                equipment_id=equipment.id,
                position_snapshot=equipment.position,
                instrument_snapshot=equipment.instrument,
                brand_snapshot=equipment.brand,
                identification_snapshot=equipment.identification,
                serial_number_snapshot=equipment.serial_number,
                certificate_folio_snapshot=equipment.certificate_folio or equipment.report_number,
            )
        )
    db.flush()
    delivery = _reload_delivery(db, delivery.id)
    pdf, _filename = generate_lab_delivery_receipt(root_work_order, delivery, user.full_name)
    delivery.voucher_pdf = pdf
    delivery.voucher_pdf_sha256 = hashlib.sha256(pdf).hexdigest()
    delivery.voucher_pdf_generated_at = now
    return delivery


def _supersede_final_receipt_if_any(db: Session, root_id: int, when: datetime) -> None:
    current = db.scalar(
        select(LabDeliveryGroupReceipt)
        .where(
            LabDeliveryGroupReceipt.root_work_order_id == root_id,
            LabDeliveryGroupReceipt.superseded_at.is_(None),
        )
        .order_by(LabDeliveryGroupReceipt.version.desc())
        .limit(1)
        .with_for_update()
    )
    if current is not None:
        current.superseded_at = when


def _generate_final_receipt(
    db: Session, *, root_work_order: LabWorkOrder, user: User
) -> None:
    now = datetime.now(timezone.utc)
    deliveries = list(
        db.scalars(
            select(LabWorkOrderDelivery)
            .options(
                selectinload(LabWorkOrderDelivery.items).selectinload(LabDeliveryItem.work_order),
            )
            .where(
                LabWorkOrderDelivery.root_work_order_id == root_work_order.id,
                LabWorkOrderDelivery.status == "completed",
            )
            .order_by(LabWorkOrderDelivery.exhibition_number)
        )
    )
    next_version = (
        db.scalar(
            select(func.max(LabDeliveryGroupReceipt.version)).where(
                LabDeliveryGroupReceipt.root_work_order_id == root_work_order.id
            )
        )
        or 0
    ) + 1
    pdf, _filename = generate_lab_delivery_final_receipt(root_work_order, deliveries)
    receipt = LabDeliveryGroupReceipt(
        root_work_order_id=root_work_order.id,
        version=next_version,
        exhibitions_count=len(deliveries),
        generated_at=now,
        generated_by_user_id=user.id,
        pdf=pdf,
        pdf_sha256=hashlib.sha256(pdf).hexdigest(),
    )
    db.add(receipt)
    write_audit_log(
        db,
        action="lab_work_order.delivery_group_completed",
        entity="lab_delivery_group_receipts",
        entity_id=None,
        user_id=user.id,
        new_values={
            "root_work_order_id": root_work_order.id,
            "version": next_version,
            "exhibitions_count": len(deliveries),
        },
    )


def _finalize_delivery(
    db: Session, *, root_work_order: LabWorkOrder, members: list[LabWorkOrder], delivery: LabWorkOrderDelivery, user: User
) -> None:
    delivered_ids = _delivered_equipment_ids(db, root_work_order.id)
    _sync_departure_dates(members, delivered_ids)
    pending = _pending_equipment(members, delivered_ids)
    if not pending:
        _generate_final_receipt(db, root_work_order=root_work_order, user=user)
    write_audit_log(
        db,
        action="lab_work_order.delivery_completed",
        entity="lab_work_order_deliveries",
        entity_id=delivery.id,
        user_id=user.id,
        new_values={
            "root_work_order_id": root_work_order.id,
            "delivery_id": delivery.id,
            "exhibition_number": delivery.exhibition_number,
            "delivery_type": delivery.delivery_type,
            "delivered_at": delivery.delivered_at.isoformat(),
            "recipient_name": delivery.recipient_name,
            "equipment_ids": [item.equipment_id for item in delivery.items],
            "voucher_sha256": delivery.voucher_pdf_sha256,
        },
    )


def _resolve_root_work_order(work_order: LabWorkOrder, group: list[LabWorkOrder]) -> LabWorkOrder:
    root_id = _root_id(work_order)
    root = next((item for item in group if item.id == root_id), None)
    if root is None:
        raise HTTPException(status_code=404, detail="Orden de trabajo LAB no encontrada")
    return root


def complete_lab_delivery(
    db: Session, work_order_id: int, payload: LabDeliveryCreate, user: User
) -> LabDeliveryRead:
    if not user_has_permission(user, "lab_work_orders.use"):
        raise HTTPException(status_code=403, detail="No tienes permiso para registrar la entrega")
    try:
        work_order, group = _lock_historical_group(db, work_order_id)
        root_work_order = _resolve_root_work_order(work_order, group)
        members = _relevant_group_members(group)
        if not members or any(item.status not in {"completed", "partially_closed"} for item in members):
            raise HTTPException(
                status_code=409,
                detail="La entrega sólo puede registrarse cuando todas las OT relevantes del grupo están cerradas",
            )
        delivered_ids = _delivered_equipment_ids(db, root_work_order.id)
        pending = _pending_equipment(members, delivered_ids)
        if not pending:
            raise HTTPException(status_code=409, detail="El grupo no tiene equipos pendientes de entrega")
        delivery = _create_delivery_event(
            db,
            root_work_order=root_work_order,
            equipment_items=pending,
            delivery_type="full",
            payload=payload,
            user=user,
            partial_delivery_ticket_id=None,
        )
        _finalize_delivery(db, root_work_order=root_work_order, members=members, delivery=delivery, user=user)
        db.commit()
        return _read_delivery(_reload_delivery(db, delivery.id))
    except Exception:
        db.rollback()
        raise


def execute_partial_delivery(
    db: Session, work_order_id: int, ticket_id: int, payload: LabDeliveryCreate, user: User
) -> LabDeliveryRead:
    if not user_has_permission(user, "lab_work_orders.use"):
        raise HTTPException(status_code=403, detail="No tienes permiso para registrar la entrega")
    try:
        work_order, group = _lock_historical_group(db, work_order_id)
        root_work_order = _resolve_root_work_order(work_order, group)
        ticket = db.scalar(
            select(OperationalTicket).where(OperationalTicket.id == ticket_id).with_for_update()
        )
        if ticket is None or ticket.type != "partial_delivery" or ticket.work_order_id != root_work_order.id:
            raise HTTPException(status_code=404, detail="Ticket de entrega parcial no encontrado")
        if ticket.status != "approved":
            raise HTTPException(status_code=409, detail="El ticket de entrega parcial no está aprobado")
        requested_ids = set((ticket.resolution_snapshot or {}).get("requested_equipment_ids") or [])
        members = _relevant_group_members(group)
        delivered_ids = _delivered_equipment_ids(db, root_work_order.id)
        pending_by_id = {equipment.id: equipment for equipment in _pending_equipment(members, delivered_ids)}
        if not requested_ids or any(eid not in pending_by_id for eid in requested_ids):
            raise HTTPException(
                status_code=409,
                detail="El set autorizado ya no coincide con los equipos pendientes del grupo",
            )
        equipment_items = [pending_by_id[eid] for eid in requested_ids]
        delivery = _create_delivery_event(
            db,
            root_work_order=root_work_order,
            equipment_items=equipment_items,
            delivery_type="partial",
            payload=payload,
            user=user,
            partial_delivery_ticket_id=ticket.id,
        )
        _finalize_delivery(db, root_work_order=root_work_order, members=members, delivery=delivery, user=user)
        now = datetime.now(timezone.utc)
        ticket.status = "resolved"
        ticket.resolved_at = now
        write_audit_log(
            db,
            action="ticket.partial_delivery_executed",
            entity="operational_tickets",
            entity_id=ticket.id,
            user_id=user.id,
            previous_values={"status": "approved"},
            new_values={"status": "resolved", "delivery_id": delivery.id},
        )
        db.commit()
        return _read_delivery(_reload_delivery(db, delivery.id))
    except Exception:
        db.rollback()
        raise


def void_lab_delivery(
    db: Session, work_order_id: int, delivery_id: int, payload: LabDeliveryVoid, user: User
) -> LabDeliveryRead:
    if not user_has_permission(user, "lab_work_orders.cancel"):
        raise HTTPException(status_code=403, detail="No tienes permiso para anular el acuse")
    try:
        work_order, group = _lock_historical_group(db, work_order_id)
        root_work_order = _resolve_root_work_order(work_order, group)
        delivery = db.scalar(
            select(LabWorkOrderDelivery)
            .where(
                LabWorkOrderDelivery.id == delivery_id,
                LabWorkOrderDelivery.root_work_order_id == root_work_order.id,
            )
            .with_for_update()
        )
        if delivery is None:
            raise HTTPException(status_code=404, detail="Entrega no encontrada")
        if delivery.status != "completed":
            raise HTTPException(status_code=409, detail="La entrega ya no está vigente")
        now = datetime.now(timezone.utc)
        delivery.status = "voided"
        delivery.voided_at = now
        delivery.voided_by_user_id = user.id
        delivery.void_reason = payload.reason.strip()
        members = _relevant_group_members(group)
        delivered_ids = _delivered_equipment_ids(db, root_work_order.id)
        _sync_departure_dates(members, delivered_ids)
        pending = _pending_equipment(members, delivered_ids)
        if pending:
            _supersede_final_receipt_if_any(db, root_work_order.id, now)
        write_audit_log(
            db,
            action="lab_work_order.delivery_voided",
            entity="lab_work_order_deliveries",
            entity_id=delivery.id,
            user_id=user.id,
            previous_values={"status": "completed"},
            new_values={"status": "voided", "delivery_id": delivery.id, "void_reason": delivery.void_reason},
        )
        db.commit()
        return _read_delivery(_reload_delivery(db, delivery.id))
    except Exception:
        db.rollback()
        raise


def get_lab_delivery_pdf(db: Session, work_order_id: int, delivery_id: int) -> tuple[bytes, str]:
    work_order = _get(db, work_order_id)
    root_id = _root_id(work_order)
    delivery = db.scalar(
        select(LabWorkOrderDelivery).where(
            LabWorkOrderDelivery.id == delivery_id,
            LabWorkOrderDelivery.root_work_order_id == root_id,
        )
    )
    if delivery is None or not delivery.voucher_pdf:
        raise HTTPException(status_code=404, detail="Acuse de entrega no encontrado")
    return delivery.voucher_pdf, f"Acuse-entrega-OT-{work_order.folio}-exhibicion-{delivery.exhibition_number}.pdf"


def get_lab_delivery_final_receipt_pdf(db: Session, work_order_id: int) -> tuple[bytes, str]:
    work_order = _get(db, work_order_id)
    root_id = _root_id(work_order)
    receipt = db.scalar(
        select(LabDeliveryGroupReceipt)
        .where(
            LabDeliveryGroupReceipt.root_work_order_id == root_id,
            LabDeliveryGroupReceipt.superseded_at.is_(None),
        )
        .order_by(LabDeliveryGroupReceipt.version.desc())
        .limit(1)
    )
    if receipt is None:
        raise HTTPException(status_code=404, detail="El grupo aún no tiene un resumen final de entrega")
    return receipt.pdf, f"Acuse-final-entrega-OT-{work_order.folio}.pdf"
