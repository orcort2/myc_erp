"""Impacto administrativo de una corrección técnica sobre una entrega LAB (Fase 3B).

Una corrección sobre un equipo ya entregado NO invalida por sí sola la
entrega física. Este módulo es la autoridad única para:

- resolver el LabDeliveryItem vigente de un equipo;
- validar/crear el LabDeliveryItemCorrectionImpact (documentation_reissue |
  delivery_invalidated; ``none`` sólo se persiste en auditoría);
- derivar el estado administrativo vigente de un grupo (función pura).

No hace commit: el caller controla el boundary transaccional. Nunca toca la
Delivery, sus snapshots, el voucher ni su hash.
"""
from __future__ import annotations

from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from datetime import datetime, timezone

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.lab_delivery_item import LabDeliveryItem
from app.models.lab_delivery_item_correction_impact import LabDeliveryItemCorrectionImpact
from app.models.lab_work_order_delivery import LabWorkOrderDelivery
from app.models.lab_work_order_revision import LabWorkOrderRevision
from app.models.user import User
from app.services.audit_logs import write_audit_log

DELIVERY_IMPACT_CHOICES = ("none", "documentation_reissue", "delivery_invalidated")
_PERSISTED_IMPACTS = ("documentation_reissue", "delivery_invalidated")


def is_authorized_correction_session(db: Session, work_order) -> bool:
    """Persisted LAB reopening evidence; draft alone never grants authority."""
    if (work_order.status != "draft" or not work_order.reopened_at
            or not work_order.reopened_by_user_id or work_order.revision_number <= 1):
        return False
    return db.scalar(select(LabWorkOrderRevision.id).where(
        LabWorkOrderRevision.work_order_id == work_order.id,
        LabWorkOrderRevision.revision_number == work_order.revision_number - 1,
    )) is not None


def can_reopen_field_sheet(db: Session, work_order) -> bool:
    return work_order.status in {"received_signed", "in_progress", "ready_to_close"} or is_authorized_correction_session(db, work_order)


def get_active_delivery_item_for_equipment(db: Session, equipment_id: int) -> LabDeliveryItem | None:
    from app.services.technical_interventions import current_deliveries_for_equipment

    rows = current_deliveries_for_equipment(db, equipment_id)
    if len(rows) > 1:
        raise HTTPException(status_code=409, detail="El equipo tiene más de una entrega vigente; revisa las entregas")
    return rows[0][1] if rows else None


def get_active_delivery_items_by_equipment(
    db: Session, equipment_ids: Iterable[int]
) -> dict[int, LabDeliveryItem]:
    ids = list(equipment_ids)
    if not ids:
        return {}
    from app.models.lab_work_order import LabWorkOrderEquipment
    from app.services.technical_interventions import load_delivery_index

    equipments = list(db.scalars(select(LabWorkOrderEquipment).where(LabWorkOrderEquipment.id.in_(ids))))
    index = load_delivery_index(db, equipments)
    result = {}
    for equipment_id, rows in index.by_equipment.items():
        if len(rows) > 1:
            raise HTTPException(status_code=409, detail="El equipo tiene más de una entrega vigente; revisa las entregas")
        result[equipment_id] = rows[0][1]
    return result


def pending_impacts_for_group(db: Session, root_id: int) -> list[LabDeliveryItemCorrectionImpact]:
    """Include historical items even when their live equipment was retired."""
    return list(db.scalars(
        select(LabDeliveryItemCorrectionImpact)
        .join(LabDeliveryItem, LabDeliveryItemCorrectionImpact.delivery_item_id == LabDeliveryItem.id)
        .join(LabWorkOrderDelivery, LabDeliveryItem.delivery_id == LabWorkOrderDelivery.id)
        .where(LabWorkOrderDelivery.root_work_order_id_snapshot == root_id,
               LabWorkOrderDelivery.status == "completed",
               LabDeliveryItemCorrectionImpact.status == "pending")
    ))


def pending_impacts_for_items(
    db: Session, item_ids: Iterable[int]
) -> dict[int, list[LabDeliveryItemCorrectionImpact]]:
    ids = list(item_ids)
    grouped: dict[int, list[LabDeliveryItemCorrectionImpact]] = {}
    if not ids:
        return grouped
    rows = db.scalars(
        select(LabDeliveryItemCorrectionImpact)
        .where(
            LabDeliveryItemCorrectionImpact.delivery_item_id.in_(ids),
            LabDeliveryItemCorrectionImpact.status == "pending",
        )
        .order_by(LabDeliveryItemCorrectionImpact.id)
    )
    for row in rows:
        grouped.setdefault(row.delivery_item_id, []).append(row)
    return grouped


def select_active_impact(
    impacts: Sequence[LabDeliveryItemCorrectionImpact],
) -> LabDeliveryItemCorrectionImpact | None:
    """Impacto pending a mostrar: delivery_invalidated prevalece; luego el más reciente."""
    if not impacts:
        return None
    return max(impacts, key=lambda row: (row.impact_type == "delivery_invalidated", row.id))


def validate_delivery_impact(delivery_item: LabDeliveryItem | None, delivery_impact: str | None) -> str:
    """Decisión explícita obligatoria sólo si el equipo está entregado.
    Devuelve el impacto efectivo ('none' si no aplica)."""
    if delivery_item is None:
        if delivery_impact in (None, "none"):
            return "none"
        raise HTTPException(
            status_code=422,
            detail={
                "code": "DELIVERY_IMPACT_NOT_APPLICABLE",
                "message": "El equipo no está entregado: delivery_impact debe omitirse o ser none",
            },
        )
    if delivery_impact is None:
        raise HTTPException(
            status_code=422,
            detail={
                "code": "DELIVERY_IMPACT_REQUIRED",
                "message": "El equipo ya fue entregado: indica el impacto de la corrección sobre la entrega",
            },
        )
    if delivery_impact not in DELIVERY_IMPACT_CHOICES:
        raise HTTPException(status_code=422, detail="delivery_impact inválido")
    return delivery_impact


def establish_reopening_decisions(
    db: Session, *, members, equipment_id: int | None, user: User, reason: str,
    delivery_impact: str | None = None, delivery_impacts: dict[int, str] | None = None,
) -> list[LabDeliveryItemCorrectionImpact]:
    """Validate current LAB scope under the caller's cohort lock, then persist.

    Values supplied by clients are decisions, never authorization. Callers must
    enforce their existing LAB permission before invoking this primitive. No
    pending historical impact can authorize a new reopening. No commit here.
    """
    from app.models.lab_work_order import LabWorkOrderEquipment

    equipments = list(db.scalars(select(LabWorkOrderEquipment).where(
        LabWorkOrderEquipment.work_order_id.in_([member.id for member in members]),
        LabWorkOrderEquipment.is_active.is_(True),
    ).execution_options(populate_existing=True).with_for_update()))
    by_id = {equipment.id: equipment for equipment in equipments}
    if equipment_id is not None:
        if equipment_id not in by_id:
            raise HTTPException(status_code=422, detail="CORRECTION_EQUIPMENT_OUTSIDE_COHORT")
        equipments = [by_id[equipment_id]]
    if not reason.strip():
        raise HTTPException(status_code=422, detail="CORRECTION_REASON_REQUIRED")
    decisions = dict(delivery_impacts or {})
    if delivery_impact is not None:
        if equipment_id is None or decisions:
            raise HTTPException(status_code=422, detail="DELIVERY_IMPACT_SCOPE_REQUIRED")
        decisions[equipment_id] = delivery_impact
    scope = {equipment.id for equipment in equipments}
    if decisions.keys() - scope:
        raise HTTPException(status_code=422, detail="DELIVERY_IMPACT_OUTSIDE_SCOPE")
    # Validate every decision before creating any row or changing a receipt.
    validated = []
    for equipment in equipments:
        item = get_active_delivery_item_for_equipment(db, equipment.id)
        if item is not None and equipment.id not in decisions:
            raise HTTPException(status_code=409, detail="DELIVERY_IMPACT_REQUIRED")
        kind = validate_delivery_impact(item, decisions.get(equipment.id))
        if item is None:
            continue
        sheet = equipment.current_field_sheet
        if sheet is None or not sheet.is_active or sheet.status != "completed":
            raise HTTPException(status_code=409, detail="LAB_FIELD_SHEET_NOT_COMPLETED")
        validated.append((equipment, item, sheet, kind))
    impacts = []
    for equipment, item, sheet, kind in validated:
        write_audit_log(
            db, action="lab_delivery_item.correction_decided", entity="lab_delivery_items",
            entity_id=item.id, user_id=user.id, comment=reason,
            new_values={"delivery_impact": kind, "equipment_id": equipment.id,
                        "source_field_sheet_id": sheet.id,
                        "source_field_sheet_revision_number": sheet.revision_number},
        )
        if kind != "none":
            impacts.append(create_correction_impact(
                db, delivery_item=item, impact_type=kind, reason=reason, user=user,
                source_field_sheet_id=sheet.id,
                source_field_sheet_revision_number=sheet.revision_number,
            ))
    return impacts


def lock_correction_group(db: Session, work_order_id: int, expected_cohort_revision: str | None = None):
    from app.services.lab_work_orders import _lock_historical_group
    from app.services.service_order_mobile_execution import cohort_revision

    _lock_historical_group(db, work_order_id)
    # Expire only before mutation, so all entry points see the committed state
    # after waiting for the root lock (including sessions loaded before it).
    db.expire_all()
    work_order, members = _lock_historical_group(db, work_order_id)
    if expected_cohort_revision is not None and expected_cohort_revision != cohort_revision(members):
        raise HTTPException(status_code=409, detail={
            "code": "COHORT_REVISION_CONFLICT",
            "message": "La OT cambió desde que abriste la solicitud; recarga e inténtalo de nuevo",
        })
    return work_order, members


def rollback_failed_reopening(operation):
    """Rollback the whole LAB reopening, including the caller's ETS audit.

    Public coordinators retain the existing single commit/notification boundary.
    This guard also covers flush failures before entering the reopen primitive.
    """
    from functools import wraps

    @wraps(operation)
    def guarded(db: Session, *args, **kwargs):
        try:
            return operation(db, *args, **kwargs)
        except Exception:
            db.rollback()
            db.info.pop("push_notification_ids", None)
            raise
    return guarded


def create_correction_impact(
    db: Session,
    *,
    delivery_item: LabDeliveryItem,
    impact_type: str,
    reason: str,
    user: User,
    source_field_sheet_id: int,
    source_field_sheet_revision_number: int,
) -> LabDeliveryItemCorrectionImpact:
    """Crea (flush, sin commit) un impacto pending y aplica su efecto sobre el
    acuse final. Rechaza duplicar un pending para el mismo (item, hoja origen);
    el índice único parcial lo garantiza también a nivel de BD."""
    if impact_type not in _PERSISTED_IMPACTS:
        raise ValueError("Sólo documentation_reissue/delivery_invalidated se persisten")
    if db.scalar(
        select(LabDeliveryItemCorrectionImpact.id).where(
            LabDeliveryItemCorrectionImpact.delivery_item_id == delivery_item.id,
            LabDeliveryItemCorrectionImpact.source_field_sheet_id == source_field_sheet_id,
            LabDeliveryItemCorrectionImpact.status == "pending",
        )
    ) is not None:
        raise HTTPException(
            status_code=409,
            detail="Ya existe un impacto pendiente para esta corrección del equipo entregado [DELIVERY_IMPACT_ALREADY_PENDING]",
        )
    impact = LabDeliveryItemCorrectionImpact(
        delivery_item_id=delivery_item.id,
        work_order_id_snapshot=delivery_item.work_order_id_snapshot,
        equipment_id_snapshot=delivery_item.equipment_id_snapshot,
        impact_type=impact_type,
        status="pending",
        reason=reason,
        created_by_user_id=user.id,
        source_field_sheet_id=source_field_sheet_id,
        source_field_sheet_revision_number=source_field_sheet_revision_number,
    )
    db.add(impact)
    db.flush()
    delivery = delivery_item.delivery
    if final_receipt_effect(impact_type) == "supersede" and delivery.root_work_order_id is not None:
        from app.services.lab_work_order_deliveries import _supersede_final_receipt_if_any
        _supersede_final_receipt_if_any(db, delivery.root_work_order_id, datetime.now(timezone.utc))
    write_audit_log(
        db,
        action="lab_delivery_item.correction_impact_created",
        entity="lab_delivery_item_correction_impacts",
        entity_id=impact.id,
        user_id=user.id,
        new_values={
            "delivery_id": delivery_item.delivery_id,
            "delivery_item_id": delivery_item.id,
            "work_order_id": delivery_item.work_order_id_snapshot,
            "equipment_id": delivery_item.equipment_id_snapshot,
            "impact_type": impact_type,
            "reason": reason,
            "actor": user.id,
        },
        comment=reason,
    )
    return impact


def attach_source_revision(
    db: Session, impact: LabDeliveryItemCorrectionImpact, work_order_id: int
) -> None:
    """Vincula la LabWorkOrderRevision congelada por la reapertura (si existe)."""
    impact.source_work_order_revision_id = db.scalar(
        select(LabWorkOrderRevision.id)
        .where(LabWorkOrderRevision.work_order_id == work_order_id)
        .order_by(LabWorkOrderRevision.revision_number.desc())
        .limit(1)
    )


# ----------------------------------------------------------------- PURE STATE


def final_receipt_effect(impact_type: str) -> str:
    """Efecto de un impacto pending sobre el acuse final vigente:
    'keep' (queda disponible, reemisión pendiente) o 'supersede'."""
    return "supersede" if impact_type == "delivery_invalidated" else "keep"


@dataclass(frozen=True)
class GroupAdministrativeState:
    has_pending_delivery_impacts: bool
    pending_documentation_reissues: int
    pending_delivery_invalidations: int


def group_administrative_state(impact_types: Iterable[str]) -> GroupAdministrativeState:
    """Estado administrativo vigente del grupo a partir de los impactos
    pending (función pura; ``none`` no existe como fila)."""
    types = list(impact_types)
    reissues = sum(1 for kind in types if kind == "documentation_reissue")
    invalidations = sum(1 for kind in types if kind == "delivery_invalidated")
    return GroupAdministrativeState(
        has_pending_delivery_impacts=bool(reissues or invalidations),
        pending_documentation_reissues=reissues,
        pending_delivery_invalidations=invalidations,
    )
