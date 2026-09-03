from __future__ import annotations

import hashlib
from datetime import datetime, timezone

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.lab_work_order_delivery import LabWorkOrderDelivery
from app.models.user import User
from app.schemas.lab_work_order import (
    LabWorkOrderDeliveryCreate,
    LabWorkOrderDeliveryRead,
)
from app.services.audit_logs import write_audit_log
from app.services.auth import user_has_permission
from app.services.lab_delivery_pdfs import generate_lab_delivery_receipt
from app.services.lab_work_orders import _decode_signature, _get


def _active_delivery(db: Session, work_order_id: int, *, lock: bool = False) -> LabWorkOrderDelivery | None:
    query = select(LabWorkOrderDelivery).where(
        LabWorkOrderDelivery.work_order_id == work_order_id,
        LabWorkOrderDelivery.status == "completed",
    )
    if lock:
        query = query.with_for_update()
    return db.scalar(query)


def _read_delivery(delivery: LabWorkOrderDelivery) -> LabWorkOrderDeliveryRead:
    return LabWorkOrderDeliveryRead(
        id=delivery.id,
        status=delivery.status,
        delivered_at=delivery.delivered_at,
        delivered_by_user_id=delivery.delivered_by_user_id,
        delivered_by_name=delivery.delivered_by.full_name,
        recipient_name=delivery.recipient_name,
        notes=delivery.notes,
        voucher_available=bool(delivery.voucher_pdf),
        voided_at=delivery.voided_at,
        void_reason=delivery.void_reason,
    )


def get_lab_work_order_delivery(db: Session, work_order_id: int) -> LabWorkOrderDeliveryRead | None:
    _get(db, work_order_id)
    delivery = _active_delivery(db, work_order_id)
    return _read_delivery(delivery) if delivery else None


def complete_lab_work_order_delivery(
    db: Session, work_order_id: int, payload: LabWorkOrderDeliveryCreate, user: User
) -> LabWorkOrderDeliveryRead:
    if not user_has_permission(user, "lab_work_orders.use"):
        raise HTTPException(status_code=403, detail="No tienes permiso para registrar la entrega")
    try:
        work_order = _get(db, work_order_id, lock=True)
        if work_order.status != "completed":
            raise HTTPException(status_code=409, detail="La entrega sólo puede registrarse cuando la OT está cerrada por completo")
        if _active_delivery(db, work_order_id, lock=True):
            raise HTTPException(status_code=409, detail="La OT ya tiene una entrega física vigente")
        _decode_signature(payload.recipient_signature_data_url)
        now = datetime.now(timezone.utc)
        if now.date() < work_order.reception_date:
            raise HTTPException(status_code=409, detail="La entrega no puede ser anterior a la recepción")
        delivery = LabWorkOrderDelivery(
            work_order_id=work_order.id,
            delivered_at=now,
            delivered_by_user_id=user.id,
            recipient_name=payload.recipient_name.strip(),
            recipient_signature_data_url=payload.recipient_signature_data_url,
            notes=(payload.notes or "").strip() or None,
            status="completed",
        )
        db.add(delivery)
        db.flush()
        pdf, _filename = generate_lab_delivery_receipt(work_order, delivery, user.full_name)
        delivery.voucher_pdf = pdf
        delivery.voucher_pdf_sha256 = hashlib.sha256(pdf).hexdigest()
        delivery.voucher_pdf_generated_at = now
        work_order.departure_date = now.date()
        write_audit_log(
            db,
            action="lab_work_order.delivery_completed",
            entity="lab_work_order_deliveries",
            entity_id=delivery.id,
            user_id=user.id,
            new_values={
                "work_order_id": work_order.id,
                "delivery_id": delivery.id,
                "delivered_at": now.isoformat(),
                "recipient_name": delivery.recipient_name,
                "equipment_ids": [item.id for item in work_order.equipment],
                "voucher_sha256": delivery.voucher_pdf_sha256,
            },
        )
        db.commit()
        db.refresh(delivery)
        return _read_delivery(delivery)
    except Exception:
        db.rollback()
        raise


def void_lab_work_order_delivery(
    db: Session, work_order_id: int, reason: str, user: User
) -> LabWorkOrderDeliveryRead:
    if not user_has_permission(user, "lab_work_orders.cancel"):
        raise HTTPException(status_code=403, detail="No tienes permiso para anular el acuse")
    try:
        work_order = _get(db, work_order_id, lock=True)
        delivery = _active_delivery(db, work_order_id, lock=True)
        if delivery is None:
            raise HTTPException(status_code=409, detail="La OT no tiene una entrega vigente")
        now = datetime.now(timezone.utc)
        delivery.status = "voided"
        delivery.voided_at = now
        delivery.voided_by_user_id = user.id
        delivery.void_reason = reason.strip()
        work_order.departure_date = None
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
        db.refresh(delivery)
        return _read_delivery(delivery)
    except Exception:
        db.rollback()
        raise


def get_lab_delivery_pdf(db: Session, work_order_id: int) -> tuple[bytes, str]:
    work_order = _get(db, work_order_id)
    delivery = _active_delivery(db, work_order_id)
    if delivery is None or not delivery.voucher_pdf:
        raise HTTPException(status_code=404, detail="La OT no tiene un acuse de entrega vigente")
    return delivery.voucher_pdf, f"Acuse-entrega-OT-{work_order.folio}.pdf"
