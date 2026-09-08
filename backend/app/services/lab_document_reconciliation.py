"""Reconcile inherited LAB documents inside the work-order closing transaction."""
from copy import deepcopy
from datetime import date, datetime

from fastapi import HTTPException
from sqlalchemy import select

from app.models.field_sheet import FieldSheet
from app.models.lab_work_order_revision import LabWorkOrderRevision
from app.services.audit_logs import write_audit_log
from app.services.field_sheets import EDITABLE_STATUSES, _validate_ready_to_complete


def inherited_document_values(equipment, order) -> dict:
    from app.services.lab_work_orders import resolve_equipment_certificate_client

    client = resolve_equipment_certificate_client(equipment, order)
    return {
        "company": client["company"], "address": client["address"], "attention": client["attention"],
        "reception_date": order.reception_date.isoformat() if order.reception_date else None,
        "purchase_order_or_quotation": order.purchase_order,
        "equipment_general_condition": equipment.is_good_condition,
        "initial_condition": "BUENA" if equipment.is_good_condition else "REQUIERE REVISIÓN",
        "capture_values.instrument": equipment.instrument,
        "capture_values.brand": equipment.brand,
        "capture_values.model": equipment.model,
        "capture_values.internal_id": equipment.identification,
        "capture_values.serial_number": equipment.serial_number,
        "capture_values.reserved_certificate_folio": equipment.certificate_folio,
        "observations": (equipment.observations or "").strip() or None,
    }


def _sheet_value(sheet, key):
    value = (sheet.capture_values or {}).get(key.split(".", 1)[1]) if key.startswith("capture_values.") else getattr(sheet, key)
    return value.isoformat() if isinstance(value, (date, datetime)) else value


def _copy_columns(record, excluded):
    # Copy values, never ORM identity/relationships or mutable JSON references.
    return {column.key: deepcopy(getattr(record, column.key))
            for column in record.__table__.columns if column.key not in excluded}


def _next_document_revision(db, equipment, previous):
    from app.services.field_sheet_pdfs import freeze_final_field_sheet_pdf

    if not previous.final_pdf_path:
        raise HTTPException(status_code=409, detail="La revisión anterior carece de PDF final congelado")
    freeze_final_field_sheet_pdf(db, previous)  # Read/checksum only; never reinterpret history.
    values = _copy_columns(previous, {
        "id", "created_at", "updated_at", "status", "revision_number", "is_current",
        "supersedes_field_sheet_id", "final_pdf_path", "final_pdf_sha256",
        "final_pdf_generated_at", "final_pdf_template_definition_version",
    })
    next_number = max(sheet.revision_number for sheet in equipment.field_sheets) + 1
    previous.is_current = False
    db.flush()  # Release the partial unique index before inserting the successor.
    current = FieldSheet(**values, status="draft", revision_number=next_number,
                         is_current=True, supersedes_field_sheet_id=previous.id)
    current.lab_signature_session_id = equipment.work_order.signature_session_id
    for relationship in ("results_rows", "signatures", "reference_standard_links", "uncertainty_calculations"):
        setattr(current, relationship, [type(row)(**_copy_columns(row, {
            "id", "created_at", "updated_at", "field_sheet_id",
        })) for row in getattr(previous, relationship)])
    db.add(current)
    db.flush()
    db.expire(equipment, ["current_field_sheet", "field_sheets"])
    return current


def reconcile_reopened_field_sheets(db, members, user) -> list[dict]:
    """No commit: the caller owns all document writes and the OT finalization.

    New snapshots record inherited values by equipment ID. Legacy revisions
    fall back to their frozen FieldSheet values, never to a mutable position.
    Retired sheets requiring technical recapture are never resurrected.
    """
    from app.services.lab_field_sheets import _complete_lab_field_sheet_uncommitted
    from app.services.field_sheet_pdfs import FINAL_DOCUMENT_STATUSES

    reports = []
    for order in members:
        if not order.reopened_at:
            continue
        closed = db.scalar(select(LabWorkOrderRevision).where(
            LabWorkOrderRevision.work_order_id == order.id,
            LabWorkOrderRevision.revision_number == order.revision_number - 1,
        ))
        if closed is None:
            raise HTTPException(status_code=409, detail="Falta la revisión cerrada anterior para consolidar cambios")
        snapshot = closed.snapshot
        global_fields = [key for key in (
            "client_name", "address", "contact_name", "contact_phone", "contact_email",
            "reception_date", "purchase_order", "postal_code", "city", "state_name", "notes",
        ) if key in snapshot and snapshot[key] != (
            getattr(order, key).isoformat() if isinstance(getattr(order, key), date) else getattr(order, key)
        )]
        previous_equipment = {item["id"]: item for item in snapshot.get("equipment", []) if "id" in item}
        prior_active_ids = {item["id"] for item in snapshot.get("equipment", [])
                            if "id" in item and item.get("is_active", True)}
        active_ids = {item.id for item in order.active_equipment}
        added_ids = sorted(active_ids - prior_active_ids) if previous_equipment else []
        removed_ids = sorted(prior_active_ids - active_ids) if previous_equipment else []
        revised = []
        affected = []
        for equipment in order.active_equipment:
            sheet = equipment.field_sheet
            if sheet is None or not sheet.is_active:
                continue
            target = inherited_document_values(equipment, order)
            before = previous_equipment.get(equipment.id, {}).get("inherited_document_values")
            # If an editable sheet was already synchronized, it needs no duplicate
            # work. A change reverted to the closed value is also a no-op.
            changed = {key: value for key, value in target.items()
                       if (before is None or before.get(key) != value)
                       and _sheet_value(sheet, key) != value
                       # Observation capture is editable: only propagate when it
                       # still inherited the equipment value at the last close.
                       and (key != "observations" or (before is not None and _sheet_value(sheet, key) == before.get(key)))
                       and (before is not None or key != "capture_values.reserved_certificate_folio")}
            if not changed:
                continue
            previous = sheet
            if sheet.status in FINAL_DOCUMENT_STATUSES:
                sheet = _next_document_revision(db, equipment, previous)
            elif sheet.status not in EDITABLE_STATUSES:
                raise HTTPException(status_code=409, detail="La hoja afectada no admite consolidación documental")
            capture_values = deepcopy(sheet.capture_values or {})
            for key, value in changed.items():
                if key.startswith("capture_values."):
                    capture_values[key.split(".", 1)[1]] = value
                else:
                    setattr(sheet, key, date.fromisoformat(value) if key == "reception_date" and value else value)
                    # Do not let a stale declarative duplicate override the new
                    # canonical documentary value when rendering the successor.
                    if key in capture_values:
                        capture_values[key] = value
            sheet.capture_values = capture_values
            affected.append(equipment.id)
            if sheet is not previous:
                try:
                    _validate_ready_to_complete(sheet)
                except HTTPException as exc:
                    raise HTTPException(status_code=422, detail={
                        "code": "LAB_DRAFT_SHEETS_INVALID", "items": [{
                            "equipment_id": equipment.id, "equipment": equipment.instrument,
                            "work_order_id": order.id, "validation": exc.detail,
                        }],
                    }) from exc
                _complete_lab_field_sheet_uncommitted(db, equipment, sheet, user)
            revised.append({
                "equipment_id": equipment.id, "fields": sorted(changed),
                "previous_field_sheet_id": previous.id, "field_sheet_id": sheet.id,
                "previous_revision": previous.revision_number, "revision": sheet.revision_number,
                "previous_pdf_path": previous.final_pdf_path, "previous_pdf_sha256": previous.final_pdf_sha256,
                "pdf_path": sheet.final_pdf_path, "pdf_sha256": sheet.final_pdf_sha256,
            })
        from app.services.lab_work_orders import _missing_completed_sheets
        if order.status in {"received_signed", "in_progress"} and not _missing_completed_sheets([order]):
            order.status = "ready_to_close"
        reports.append({
                            "work_order_id": order.id, "global_fields": global_fields,
                            "affected_equipment_ids": sorted(set(affected + added_ids + removed_ids)), "field_sheets": revised,
                            "added_equipment_ids": added_ids, "removed_equipment_ids": removed_ids,
                            "signature_policy": "preserve" if order.signature_preserved else "new_signature",
                            "signature_session_id": order.signature_session_id,
                            "signature_required": order.signature_required,
                        })
    return reports


def audit_consolidated_documents(db, reports, user):
    # Existing editable sheets may have been completed by the normal closing
    # flow after reconciliation. Audit their final paths, not an earlier draft.
    for report in reports:
        for item in report["field_sheets"]:
            sheet = db.get(FieldSheet, item["field_sheet_id"])
            item["pdf_path"] = sheet.final_pdf_path
            item["pdf_sha256"] = sheet.final_pdf_sha256
        write_audit_log(db, action="lab_work_order.changes_consolidated", entity="lab_work_orders",
                        entity_id=report["work_order_id"], user_id=user.id, new_values=report)
