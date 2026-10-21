"""Proyección READ-ONLY de la ejecución técnica MYC Mobile de un ETS.

ServiceOrder → ServiceOrderLabLink (activo, única autoridad del vínculo) →
raíz LabWorkOrder → grupo LAB → equipo activo → FieldSheet vigente.

Nunca escribe: no crea ni copia Equipment, ServiceWorkOrder, FieldSheet ERP ni
snapshots; no regenera PDFs (sólo sirve el PDF final congelado tras validar
su SHA-256). MYC Mobile es la única interfaz de escritura técnica; el ERP
sólo consulta aquí y gobierna mediante acciones administrativas de dominio
(ver service_order_mobile_administration.py).
"""
from __future__ import annotations

from hashlib import sha256
import re

from fastapi import HTTPException
from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from app.models.field_sheet import FieldSheet
from app.models.lab_work_order import LabWorkOrder, LabWorkOrderEquipment
from app.models.service_order import ServiceOrder
from app.models.service_order_lab_link import ServiceOrderLabLink
from app.schemas.field_sheet import FieldSheetRead
from app.services.lab_delivery_correction_impacts import (
    is_authorized_correction_session,
    get_active_delivery_items_by_equipment,
    group_administrative_state,
    pending_impacts_for_items,
    pending_impacts_for_group,
    select_active_impact,
)
from app.schemas.service_order_mobile_execution import (
    MobileExecutionCorrectionImpact,
    MobileExecutionEquipmentDelivery,
    MobileExecutionEquipment,
    MobileExecutionFieldSheetDetail,
    MobileExecutionFieldSheetSummary,
    MobileExecutionProjection,
    MobileExecutionWorkOrder,
)
from app.services.storage_service import require_deliverable_file

LAB_LINK_REQUIRED = "LAB_LINK_REQUIRED"


def _service_order(db: Session, service_order_id: int) -> ServiceOrder:
    order = db.get(ServiceOrder, service_order_id)
    if order is None:
        raise HTTPException(status_code=404, detail="Orden de servicio no encontrada")
    return order


def active_lab_link(db: Session, service_order_id: int) -> ServiceOrderLabLink | None:
    return db.scalar(
        select(ServiceOrderLabLink).where(
            ServiceOrderLabLink.service_order_id == service_order_id,
            ServiceOrderLabLink.status == "active",
        )
    )


def cohort_revision(members: list[LabWorkOrder]) -> str:
    """Token optimista opaco de la cohorte: SHA-256 de todos los pares
    (work_order_id, edit_version) en orden estable por id. Cualquier cambio de
    cualquier miembro lo cambia (a diferencia de max/suma). Única autoridad:
    la proyección lo expone y request_mobile_correction lo compara; el
    frontend sólo lo conserva y lo devuelve."""
    canonical = "|".join(
        f"{item.id}:{item.edit_version}" for item in sorted(members, key=lambda member: member.id)
    )
    return sha256(canonical.encode()).hexdigest()


def linked_lab_group(db: Session, root_id: int) -> list[LabWorkOrder]:
    """Todas las OT del grupo (raíz legacy NULL o auto-referenciada)."""
    return list(db.scalars(
        select(LabWorkOrder)
        .where(func.coalesce(LabWorkOrder.root_work_order_id, LabWorkOrder.id) == root_id)
        .options(
            selectinload(LabWorkOrder.equipment).selectinload(LabWorkOrderEquipment.field_sheets),
            selectinload(LabWorkOrder.equipment).selectinload(LabWorkOrderEquipment.current_field_sheet),
        )
        .order_by(LabWorkOrder.sequence_number, LabWorkOrder.id)
    ).all())


def require_linked_lab_group(
    db: Session, service_order_id: int,
) -> tuple[ServiceOrderLabLink, list[LabWorkOrder]]:
    _service_order(db, service_order_id)
    link = active_lab_link(db, service_order_id)
    if link is None:
        raise HTTPException(
            status_code=409,
            detail={"code": LAB_LINK_REQUIRED, "message": "El ETS no tiene un servicio MYC Mobile vinculado"},
        )
    return link, linked_lab_group(db, link.lab_root_work_order_id)


def require_group_equipment(
    members: list[LabWorkOrder], equipment_id: int,
) -> tuple[LabWorkOrder, LabWorkOrderEquipment]:
    """Equipo ACTIVO dentro del grupo vinculado; un tombstone no es operativo."""
    for work_order in members:
        for equipment in work_order.active_equipment:
            if equipment.id == equipment_id:
                return work_order, equipment
    raise HTTPException(status_code=404, detail="Equipo no encontrado en el servicio MYC Mobile vinculado")


def _sheet_summary(sheet: FieldSheet) -> MobileExecutionFieldSheetSummary:
    return MobileExecutionFieldSheetSummary(
        id=sheet.id,
        revision_number=sheet.revision_number,
        is_current=sheet.is_current,
        status=sheet.status,
        template_key=sheet.template_key,
        has_final_pdf=bool(sheet.final_pdf_path and sheet.final_pdf_sha256),
        final_pdf_generated_at=sheet.final_pdf_generated_at,
        created_at=sheet.created_at,
        updated_at=sheet.updated_at,
    )


def _equipment(equipment: LabWorkOrderEquipment) -> MobileExecutionEquipment:
    current = equipment.current_field_sheet
    return MobileExecutionEquipment(
        id=equipment.id,
        work_order_id=equipment.work_order_id,
        position=equipment.position,
        instrument=equipment.instrument,
        brand=equipment.brand,
        model=equipment.model,
        serial_number=equipment.serial_number,
        identification=equipment.identification,
        report_number=equipment.report_number,
        is_good_condition=equipment.is_good_condition,
        observations=equipment.observations,
        service_type=equipment.service_type,
        linked_company_name_snapshot=equipment.linked_company_name_snapshot,
        certificate_client_mode=equipment.certificate_client_mode,
        final_client_company_snapshot=equipment.final_client_company_snapshot,
        final_client_address_snapshot=equipment.final_client_address_snapshot,
        final_client_attention_snapshot=equipment.final_client_attention_snapshot,
        certificate_folio=equipment.certificate_folio,
        folio_status=equipment.folio_status,
        field_sheet=_sheet_summary(current) if current is not None and current.is_active else None,
        field_sheet_revision_count=len(equipment.field_sheets),
    )


def work_order_final_pdf_available(work_order: LabWorkOrder) -> bool:
    """Misma condición que lab_work_orders.get_pdf: OT cerrada con PDF final."""
    return work_order.status in {"completed", "partially_closed"} and bool(work_order.final_pdf)


def _work_order(db: Session, work_order: LabWorkOrder, root_id: int) -> MobileExecutionWorkOrder:
    return MobileExecutionWorkOrder(
        id=work_order.id,
        folio=work_order.folio,
        sequence_number=work_order.sequence_number,
        is_root=work_order.id == root_id,
        status=work_order.status,
        authorized_correction_session=is_authorized_correction_session(db, work_order),
        workflow_mode=work_order.workflow_mode,
        client_name=work_order.client_name,
        reception_date=work_order.reception_date,
        departure_date=work_order.departure_date,
        completed_at=work_order.completed_at,
        cancelled_at=work_order.cancelled_at,
        revision_number=work_order.revision_number,
        has_final_pdf=work_order_final_pdf_available(work_order),
        final_pdf_generated_at=work_order.final_pdf_generated_at,
        retired_equipment_count=sum(1 for item in work_order.equipment if not item.is_active),
        equipment=[_equipment(item) for item in work_order.active_equipment],
    )


def get_mobile_execution_projection(db: Session, service_order_id: int) -> MobileExecutionProjection:
    _service_order(db, service_order_id)
    link = active_lab_link(db, service_order_id)
    if link is None:
        return MobileExecutionProjection(service_order_id=service_order_id, linked=False)
    root_id = link.lab_root_work_order_id
    members = linked_lab_group(db, root_id)
    root = next((item for item in members if item.id == root_id), None)
    work_orders = [_work_order(db, item, root_id) for item in members]
    _attach_delivery_state(
        db, [equipment for work_order in work_orders for equipment in work_order.equipment]
    )
    state = group_administrative_state(impact.impact_type for impact in pending_impacts_for_group(db, root_id))
    return MobileExecutionProjection(
        service_order_id=service_order_id,
        linked=True,
        link_id=link.id,
        root_work_order_id=root_id,
        root_folio=root.folio if root is not None else None,
        work_orders=work_orders,
        cohort_revision=cohort_revision(members),
        has_pending_delivery_impacts=state.has_pending_delivery_impacts,
        pending_documentation_reissues=state.pending_documentation_reissues,
        pending_delivery_invalidations=state.pending_delivery_invalidations,
    )


def _attach_delivery_state(db: Session, equipment_models: list[MobileExecutionEquipment]):
    """Completa ``delivery`` de cada equipo (sólo lectura) con el
    LabDeliveryItem vigente y su impacto pending prevaleciente. Devuelve todos
    los impactos pending del grupo para los contadores."""
    items = get_active_delivery_items_by_equipment(db, [item.id for item in equipment_models])
    pending = pending_impacts_for_items(db, [item.id for item in items.values()])
    all_pending = []
    for equipment in equipment_models:
        item = items.get(equipment.id)
        if item is None:
            continue
        rows = pending.get(item.id, [])
        all_pending.extend(rows)
        active = select_active_impact(rows)
        delivery = item.delivery
        equipment.delivery = MobileExecutionEquipmentDelivery(
            delivered=True,
            delivery_id=delivery.id,
            delivery_item_id=item.id,
            exhibition_number=delivery.exhibition_number,
            delivered_at=delivery.delivered_at,
            active_correction_impact=(
                MobileExecutionCorrectionImpact(
                    id=active.id, impact_type=active.impact_type, status=active.status
                )
                if active is not None
                else None
            ),
        )
    return all_pending


def get_mobile_execution_field_sheet(
    db: Session, service_order_id: int, equipment_id: int,
) -> MobileExecutionFieldSheetDetail:
    _link, members = require_linked_lab_group(db, service_order_id)
    work_order, equipment = require_group_equipment(members, equipment_id)
    current = equipment.current_field_sheet
    equipment_read = _equipment(equipment)
    _attach_delivery_state(db, [equipment_read])
    return MobileExecutionFieldSheetDetail(
        service_order_id=service_order_id,
        work_order_id=work_order.id,
        work_order_folio=work_order.folio,
        work_order_status=work_order.status,
        authorized_correction_session=is_authorized_correction_session(db, work_order),
        cohort_revision=cohort_revision(members),
        equipment=equipment_read,
        field_sheet=(
            FieldSheetRead.model_validate(current)
            if current is not None and current.is_active
            else None
        ),
        revisions=[_sheet_summary(sheet) for sheet in equipment.field_sheets],
    )


def read_frozen_final_pdf(sheet: FieldSheet) -> bytes:
    """Lee el PDF final congelado SIN regenerarlo y valida su SHA-256."""
    if not sheet.final_pdf_path or not sheet.final_pdf_sha256:
        raise HTTPException(status_code=409, detail="La Hoja de Campo no tiene PDF final congelado")
    content = require_deliverable_file(
        sheet.final_pdf_path, not_found_detail="El PDF final congelado no está disponible",
    ).read_bytes()
    if sha256(content).hexdigest() != sheet.final_pdf_sha256:
        raise HTTPException(status_code=409, detail="El PDF final congelado no coincide con su SHA-256")
    return content


def get_mobile_execution_field_sheet_pdf(
    db: Session, service_order_id: int, field_sheet_id: int,
) -> tuple[bytes, str]:
    """PDF final (vigente o histórico) de una hoja del grupo vinculado."""
    _link, members = require_linked_lab_group(db, service_order_id)
    for work_order in members:
        for equipment in work_order.active_equipment:
            for sheet in equipment.field_sheets:
                if sheet.id == field_sheet_id:
                    folio = re.sub(
                        r"[^A-Za-z0-9._-]", "-",
                        equipment.certificate_folio or f"OT-{work_order.folio}-{equipment.position}",
                    )
                    return (
                        read_frozen_final_pdf(sheet),
                        f"Hoja_Campo_{folio}_R{sheet.revision_number}.pdf",
                    )
    raise HTTPException(status_code=404, detail="Hoja de Campo no encontrada en el servicio MYC Mobile vinculado")


def get_mobile_execution_work_order_pdf(
    db: Session, service_order_id: int, work_order_id: int,
) -> tuple[bytes, str]:
    """PDF oficial de una OT del grupo vinculado: reutiliza get_pdf (el
    final_pdf congelado de LAB); nunca regenera ni muta."""
    from app.services.lab_work_orders import get_pdf

    _link, members = require_linked_lab_group(db, service_order_id)
    if not any(item.id == work_order_id for item in members):
        raise HTTPException(status_code=404, detail="OT no encontrada en el servicio MYC Mobile vinculado")
    return get_pdf(db, work_order_id)
