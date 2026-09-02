from __future__ import annotations

from datetime import datetime, timezone

from fastapi import HTTPException
from sqlalchemy import and_, func, or_, select
from sqlalchemy.orm import Session, aliased, contains_eager, selectinload

from app.models.field_sheet import FieldSheet, FieldSheetResult
from app.models.lab_work_order import LabWorkOrder, LabWorkOrderEquipment
from app.models.user import User
from app.schemas.field_sheet import FieldSheetRead, FieldSheetUpdate
from app.schemas.lab_work_order import (
    LabFieldSheetCreate,
    LabFieldSheetTrayItem,
    LabFieldSheetTrayPage,
)
from app.services.audit_logs import write_audit_log
from app.services.field_sheet_templates import (
    CANONICAL_PDF_RENDERER_KEY,
    CANONICAL_PDF_RENDERER_VERSION,
    build_default_result_rows,
    canonicalize_new_field_sheet_snapshot,
    get_template_snapshot,
)
from app.services.field_sheets import (
    EDITABLE_STATUSES,
    _apply_results_updates,
    _default_signature_slots,
    _serialize_field_sheet,
    _validate_ready_to_complete,
)
from app.services.institutional_configurations import (
    get_or_create_institutional_configuration,
    institutional_snapshot,
)
from app.services.lab_work_orders import _missing_completed_sheets, resolve_equipment_certificate_client


def _has_capture_value(value: object) -> bool:
    return value is not None and str(value).strip() != ""


def _field_sheet_progress(sheet: FieldSheet | None) -> tuple[int, int]:
    """Calcula progreso sólo contra el snapshot congelado de la hoja."""
    if sheet is None or not sheet.template_definition_json:
        return 0, 0
    rows_by_section: dict[str, list[FieldSheetResult]] = {}
    for row in sheet.results_rows:
        rows_by_section.setdefault(row.section_key, []).append(row)
    completed_total = 0
    required_total = 0
    for section in sheet.template_definition_json.get("result_sections") or []:
        section_rows = rows_by_section.get(str(section.get("key") or ""), [])
        required = (
            max(int(section.get("min_rows") or 0), len(section_rows))
            if section.get("allow_add_rows")
            else int(section.get("rows") or len(section_rows))
        )
        required_total += required
        columns = list(section.get("columns") or [])
        required_columns = [column for column in columns if column.get("required")]
        columns_to_check = required_columns or [
            column for column in columns if column.get("editable") is not False
        ]
        for row in section_rows:
            data = row.row_data or {}
            values = [
                data.get(column.get("source") or column.get("key"))
                for column in columns_to_check
            ]
            captured = (
                bool(values) and all(_has_capture_value(value) for value in values)
                if required_columns
                else any(_has_capture_value(value) for value in values)
            )
            completed_total += int(captured)
    return min(completed_total, required_total), required_total


def list_lab_field_sheet_tray(
    db: Session,
    *,
    operator_client_id: int | None,
    offset: int,
    limit: int,
) -> LabFieldSheetTrayPage:
    """Bandeja LAB agregada sin fan-out ni revisiones históricas operativas.

    `operator_client_id=None` es scope interno global deliberado: no existe
    concepto de "hoja de campo asignada a un técnico" en el modelo LAB, así
    que cualquier caller interno autorizado (permiso `field_sheets.read`) ve
    toda la bandeja sin filtrar. Un `operator_client_id` no nulo sólo aplica
    a actores externos con organización cliente propia.
    """
    current_sheet = aliased(FieldSheet)
    statement = (
        select(LabWorkOrderEquipment, func.count().over().label("tray_total"))
        .join(LabWorkOrderEquipment.work_order)
        .outerjoin(
            current_sheet,
            and_(
                current_sheet.lab_equipment_id == LabWorkOrderEquipment.id,
                current_sheet.is_current.is_(True),
                current_sheet.is_active.is_(True),
            ),
        )
        .where(
            or_(
                LabWorkOrder.status.in_(("received_signed", "in_progress")),
                current_sheet.id.is_not(None),
            )
        )
        .options(
            contains_eager(
                LabWorkOrderEquipment.current_field_sheet,
                alias=current_sheet,
            ).joinedload(FieldSheet.results_rows),
            contains_eager(LabWorkOrderEquipment.work_order),
        )
        .order_by(LabWorkOrder.folio.desc(), LabWorkOrderEquipment.position.asc())
        .offset(offset)
        .limit(limit)
    )
    if operator_client_id is not None:
        statement = statement.where(LabWorkOrder.operator_client_id == operator_client_id)
    rows = db.execute(statement).unique().all()
    total = int(rows[0].tray_total) if rows else 0
    items: list[LabFieldSheetTrayItem] = []
    for equipment, _tray_total in rows:
        order = equipment.work_order
        sheet = equipment.current_field_sheet
        bucket = "pending" if sheet is None else (
            "completed" if sheet.status == "completed" else "in_progress"
        )
        progress_completed, progress_required = _field_sheet_progress(sheet)
        documentary_client = resolve_equipment_certificate_client(equipment, order)
        definition = sheet.template_definition_json if sheet is not None else None
        items.append(
            LabFieldSheetTrayItem(
                work_order_id=order.id,
                work_order_folio=order.folio,
                work_order_status=order.status,
                equipment_id=equipment.id,
                instrument=equipment.instrument,
                brand=equipment.brand,
                model=equipment.model,
                service_type=equipment.service_type,
                certificate_folio=equipment.certificate_folio,
                documentary_client_display=documentary_client["company"],
                field_sheet_id=sheet.id if sheet else None,
                field_sheet_status=sheet.status if sheet else None,
                template_key=sheet.template_key if sheet else None,
                template_name=(definition or {}).get("name"),
                revision_number=sheet.revision_number if sheet else None,
                is_current=sheet.is_current if sheet else None,
                progress_completed=progress_completed,
                progress_required=progress_required,
                bucket=bucket,
            )
        )
    return LabFieldSheetTrayPage(items=items, offset=offset, limit=limit, total=total)


def get_lab_equipment(
    db: Session, work_order_id: int, equipment_id: int, *, lock: bool = False
) -> LabWorkOrderEquipment:
    query = (
        select(LabWorkOrderEquipment)
        .where(
            LabWorkOrderEquipment.id == equipment_id,
            LabWorkOrderEquipment.work_order_id == work_order_id,
        )
        .options(
            selectinload(LabWorkOrderEquipment.work_order),
            selectinload(LabWorkOrderEquipment.current_field_sheet).selectinload(
                FieldSheet.results_rows
            ),
            selectinload(LabWorkOrderEquipment.current_field_sheet).selectinload(
                FieldSheet.signatures
            ),
            selectinload(LabWorkOrderEquipment.field_sheets).selectinload(FieldSheet.results_rows),
            selectinload(LabWorkOrderEquipment.field_sheets).selectinload(FieldSheet.signatures),
        )
        .execution_options(populate_existing=True)
    )
    if lock:
        query = query.with_for_update()
    equipment = db.scalar(query)
    if equipment is None:
        raise HTTPException(status_code=404, detail="Equipo LAB no encontrado")
    return equipment


def _ensure_capture_allowed(equipment: LabWorkOrderEquipment, *, external: bool) -> None:
    # Fase 3: la captura técnica (FieldSheets) sólo procede DESPUÉS de que la
    # recepción quedó firmada -- ya no en draft. received_signed cubre el
    # arranque; in_progress cubre la captura ya en marcha (ver
    # create_lab_field_sheet, que hace la transición received_signed ->
    # in_progress en la primera hoja creada).
    if equipment.work_order.status not in {"received_signed", "in_progress"}:
        raise HTTPException(status_code=409, detail="La OT no admite captura técnica")
    if equipment.service_type is None:
        raise HTTPException(status_code=409, detail="Selecciona el tipo de servicio")
    if equipment.service_type in {"accredited", "traceable"} and equipment.folio_status not in {
        "reserved", "authorized"
    }:
        raise HTTPException(status_code=409, detail="El equipo requiere folio MYCA/MYCT asignado")
    if equipment.service_type == "linked" and not external and equipment.folio_status != "authorized":
        raise HTTPException(status_code=409, detail="Vinculado requiere folio autorizado antes de capturar")


def create_lab_field_sheet(
    db: Session,
    work_order_id: int,
    equipment_id: int,
    payload: LabFieldSheetCreate,
    user: User,
    *,
    external: bool,
) -> FieldSheetRead:
    equipment = get_lab_equipment(db, work_order_id, equipment_id, lock=True)
    _ensure_capture_allowed(equipment, external=external)
    if equipment.field_sheet is not None:
        raise HTTPException(status_code=409, detail="El equipo ya tiene una hoja de campo")
    # Fase 6: modelo de revisión. equipment.field_sheets ya trae todas las
    # revisiones (incluida cualquiera retirada por
    # _retire_current_field_sheet_revision), ordenadas revision_number desc
    # -- la [0] es siempre la última conocida, sin importar si es la primera
    # vez o una reapertura con recaptura.
    previous_revision = equipment.field_sheets[0] if equipment.field_sheets else None
    revision_number = (previous_revision.revision_number + 1) if previous_revision else 1
    definition, version = get_template_snapshot(db, payload.template_key)
    definition = canonicalize_new_field_sheet_snapshot(definition)
    order = equipment.work_order
    institution = get_or_create_institutional_configuration(db)
    # Fase 4: el cliente documental es una autoridad por-equipo, distinta del
    # cliente receptor de la OT (resolve_equipment_certificate_client es el
    # único punto de lectura, ver lab_work_orders.py) -- nunca se asume
    # order.client_name/address/contact_name directamente aquí.
    documentary_client = resolve_equipment_certificate_client(equipment, order)
    # Fase 6: prefill de captura con TODOS los datos disponibles hoy en
    # LabWorkOrderEquipment -- model y scope (range_or_capacity) ya son
    # columnas propias del equipo (mismo criterio que Equipment productivo),
    # se agregan aquí. location/minimum_division siguen siendo datos de la
    # captura/servicio (ya viven en FieldSheet, no en el equipo) -- el
    # técnico los llena en la hoja, no se prellenan desde el equipo.
    capture_values = {
        "instrument": equipment.instrument,
        "brand": equipment.brand,
        "serial_number": equipment.serial_number,
        "internal_id": equipment.identification,
        "model": equipment.model,
        "scope": equipment.range_or_capacity,
    }
    sheet = FieldSheet(
        equipment_id=None,
        lab_equipment_id=equipment.id,
        work_order_id=None,
        work_order_number=order.folio,
        revision_number=revision_number,
        is_current=True,
        supersedes_field_sheet_id=previous_revision.id if previous_revision else None,
        template_key=payload.template_key,
        template_definition_json=definition,
        template_definition_version=version,
        pdf_renderer_key=CANONICAL_PDF_RENDERER_KEY,
        pdf_renderer_version=CANONICAL_PDF_RENDERER_VERSION,
        institutional_snapshot_json=institutional_snapshot(institution),
        status="draft",
        company=documentary_client["company"],
        address=documentary_client["address"],
        attention=documentary_client["attention"],
        reception_date=order.reception_date,
        equipment_general_condition=equipment.is_good_condition,
        purchase_order_or_quotation=order.purchase_order,
        initial_condition="BUENA" if equipment.is_good_condition else "REQUIERE REVISIÓN",
        capture_values=capture_values,
        # Fase 3: la sesión de firma HISTÓRICA aplicable ya es conocida y
        # estable en este momento -- la OT sólo admite crear hojas cuando ya
        # está received_signed/in_progress, es decir, ya firmó recepción. No
        # se usa "la última sesión" como autoridad; se lee directamente la
        # sesión vigente de ESTA OT (nunca se reescribe después).
        lab_signature_session_id=order.signature_session_id,
    )
    sheet.results_rows = build_default_result_rows(definition)
    sheet.signatures = _default_signature_slots(definition, sheet)
    db.add(sheet)
    db.flush()
    # Fase 3: la primera mutación técnica real (la primera FieldSheet que se
    # crea para la OT) es el punto canónico received_signed -> in_progress --
    # backend-authoritative, no depende de que Mobile navegue a ninguna
    # pantalla.
    if order.status == "received_signed":
        order.status = "in_progress"
        write_audit_log(
            db,
            action="lab_work_order.capture_started",
            entity="lab_work_orders",
            entity_id=order.id,
            user_id=user.id,
            previous_values={"status": "received_signed"},
            new_values={"status": "in_progress", "field_sheet_id": sheet.id},
        )
    write_audit_log(
        db,
        action="lab_field_sheet.created",
        entity="field_sheets",
        entity_id=sheet.id,
        user_id=user.id,
        new_values={
            "work_order_id": order.id,
            "lab_equipment_id": equipment.id,
            "template_key": payload.template_key,
            "template_version": version,
        },
    )
    db.commit()
    return read_lab_field_sheet(db, work_order_id, equipment_id)


def read_lab_field_sheet(db: Session, work_order_id: int, equipment_id: int) -> FieldSheetRead:
    equipment = get_lab_equipment(db, work_order_id, equipment_id)
    if equipment.field_sheet is None or not equipment.field_sheet.is_active:
        raise HTTPException(status_code=404, detail="Hoja de campo LAB no encontrada")
    return FieldSheetRead.model_validate(equipment.field_sheet)


def update_lab_field_sheet(
    db: Session,
    work_order_id: int,
    equipment_id: int,
    payload: FieldSheetUpdate,
    user: User,
) -> FieldSheetRead:
    equipment = get_lab_equipment(db, work_order_id, equipment_id, lock=True)
    sheet = equipment.field_sheet
    if sheet is None or not sheet.is_active:
        raise HTTPException(status_code=404, detail="Hoja de campo LAB no encontrada")
    if sheet.status not in EDITABLE_STATUSES:
        raise HTTPException(status_code=409, detail="La hoja no admite edición")
    previous = _serialize_field_sheet(sheet)
    updates = payload.model_dump(
        exclude_unset=True,
        exclude={"results_rows", "reference_standards", "signatures", "work_order_id", "template_key"},
    )
    for key, value in updates.items():
        setattr(sheet, key, value)
    if payload.results_rows is not None:
        before_count = len(sheet.results_rows)
        _apply_results_updates(sheet, payload.results_rows)
        if len(sheet.results_rows) > before_count:
            write_audit_log(
                db,
                action="lab_field_sheet.instance_row_added",
                entity="field_sheets",
                entity_id=sheet.id,
                user_id=user.id,
                new_values={"previous_rows": before_count, "rows": len(sheet.results_rows)},
            )
    if sheet.status == "draft":
        sheet.status = "in_progress"
    write_audit_log(
        db,
        action="lab_field_sheet.updated",
        entity="field_sheets",
        entity_id=sheet.id,
        user_id=user.id,
        previous_values=previous,
        new_values=_serialize_field_sheet(sheet),
    )
    db.commit()
    return read_lab_field_sheet(db, work_order_id, equipment_id)


def complete_lab_field_sheet(
    db: Session, work_order_id: int, equipment_id: int, user: User
) -> FieldSheetRead:
    equipment = get_lab_equipment(db, work_order_id, equipment_id, lock=True)
    sheet = equipment.field_sheet
    if sheet is None or not sheet.is_active:
        raise HTTPException(status_code=404, detail="Hoja de campo LAB no encontrada")
    if sheet.status not in EDITABLE_STATUSES:
        raise HTTPException(status_code=409, detail="La hoja no puede completarse desde este estado")
    _validate_ready_to_complete(sheet)
    previous = sheet.status
    sheet.status = "completed"
    from app.services.field_sheet_pdfs import freeze_final_field_sheet_pdf, guard_final_pdf_write

    # guard_final_pdf_write spans the write through this function's own
    # commit so a failure anywhere in that span (audit log, OT status sync,
    # commit itself) deletes the orphaned artifact and rolls back instead of
    # leaving a frozen PDF that no committed row points to.
    with guard_final_pdf_write(db, sheet):
        freeze_final_field_sheet_pdf(db, sheet)
        write_audit_log(
            db,
            action="lab_field_sheet.completed",
            entity="field_sheets",
            entity_id=sheet.id,
            user_id=user.id,
            previous_values={"status": previous},
            new_values={"status": "completed", "completed_at": datetime.now(timezone.utc).isoformat()},
        )
        # Fase 3: cuando esta era la última hoja pendiente de la OT, el trabajo
        # técnico normal queda completo -- in_progress -> ready_to_close,
        # backend-authoritative (reutiliza _missing_completed_sheets, la misma
        # autoridad que ya exigía hojas completas para cerrar; sólo cambia el
        # momento en que se evalúa).
        order = equipment.work_order
        if order.status == "in_progress" and not _missing_completed_sheets([order]):
            order.status = "ready_to_close"
            write_audit_log(
                db,
                action="lab_work_order.ready_to_close",
                entity="lab_work_orders",
                entity_id=order.id,
                user_id=user.id,
                previous_values={"status": "in_progress"},
                new_values={"status": "ready_to_close"},
            )
        db.commit()
    return read_lab_field_sheet(db, work_order_id, equipment_id)
