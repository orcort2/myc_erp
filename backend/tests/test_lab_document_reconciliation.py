"""Atomic selective documentary revision at the LAB close boundary."""
from copy import deepcopy

import pytest
from sqlalchemy import select

from app.core.config import settings
from app.models.audit_log import AuditLog
from app.models.field_sheet import FieldSheet
from app.models.lab_work_order import LabWorkOrder
from test_lab_phase5_operational_closure import (
    phase5_context, auth, create_order, add_equipment, set_service, sign,
    make_lab_client_id, complete_field_sheet_fully, close_individual,
)


@pytest.fixture
def reopened_documents(phase5_context, monkeypatch, tmp_path):
    monkeypatch.setattr(settings, "storage_root", str(tmp_path))
    client, factory, tokens, _ = phase5_context
    headers = auth(tokens["admin"])

    def create(count=3, policy="preserve", independent_last=False, serial=None, capture_overrides=None):
        order_id = create_order(client, headers, lab_client_id=make_lab_client_id(factory))
        ids = []
        for index in range(count):
            equipment_id = add_equipment(client, headers, order_id, index + 1)
            set_service(client, headers, order_id, equipment_id, "traceable")
            ids.append(equipment_id)
        if independent_last:
            with factory() as db:
                from app.models.lab_work_order import LabWorkOrderEquipment
                equipment = db.get(LabWorkOrderEquipment, ids[-1])
                equipment.certificate_client_mode = "different"
                equipment.final_client_company_snapshot = "Cliente independiente"
                equipment.final_client_address_snapshot = "Domicilio independiente"
                equipment.final_client_attention_snapshot = "Atención independiente"
                db.commit()
        if serial is not None:
            edit_equipment(client, headers, order_id, ids[0], serial_number=serial)
        assert sign(client, headers, order_id).status_code == 200
        sheets = [complete_field_sheet_fully(client, headers, order_id, equipment_id, capture_overrides=capture_overrides) for equipment_id in ids]
        assert close_individual(client, headers, order_id).status_code == 200
        with factory() as db:
            previous = {}
            for sheet_id in sheets:
                sheet = db.get(FieldSheet, sheet_id)
                previous[sheet.lab_equipment_id] = {
                    "id": sheet.id, "path": sheet.final_pdf_path,
                    "bytes": (tmp_path / sheet.final_pdf_path).read_bytes(),
                    "hash": sheet.final_pdf_sha256, "capture": deepcopy(sheet.capture_values),
                    "rows": [deepcopy(row.row_data) for row in sheet.results_rows],
                    "session": sheet.lab_signature_session_id,
                    "columns": {c.key: deepcopy(getattr(sheet, c.key)) for c in sheet.__table__.columns if c.key not in {"is_current", "updated_at"}},
                    "technical": {key: deepcopy(getattr(sheet, key)) for key in (capture_overrides or {})},
                    "template": deepcopy(sheet.template_definition_json),
                }
            order = db.get(LabWorkOrder, order_id)
            session_id = order.signature_session_id
            old_order_pdf = order.final_pdf
        reopened = client.post(f"/api/mobile/v1/technician/lab-work-orders/{order_id}/reopen",
                               json={"requested_signature_policy": policy, "reason": "Corrección documental"}, headers=headers)
        assert reopened.status_code == 200, reopened.text
        return order_id, ids, previous, session_id, old_order_pdf

    return client, factory, headers, tmp_path, create


def edit_equipment(client, headers, order_id, equipment_id, **changes):
    current = client.get(f"/api/mobile/v1/technician/lab-work-orders/{order_id}", headers=headers).json()
    equipment = next(item for item in current["equipment"] if item["id"] == equipment_id)
    payload = {key: equipment[key] for key in (
        "instrument", "brand", "model", "identification", "serial_number", "report_number", "observations", "is_good_condition",
    )}
    response = client.patch(f"/api/mobile/v1/technician/lab-work-orders/{order_id}/equipment/{equipment_id}",
                            json={**payload, **changes, "expected_edit_version": current["edit_version"]}, headers=headers)
    assert response.status_code == 200, response.text
    return response.json()


@pytest.mark.parametrize("case", ["global", "one", "two_of_ten", "unchanged", "reverted", "legacy"])
def test_selective_consolidation_preserves_capture_signatures_and_history(reopened_documents, case):
    client, factory, headers, root, create = reopened_documents
    order_id, equipment_ids, previous, session_id, old_order_pdf = create(10 if case == "two_of_ten" else 3, independent_last=case == "global")
    affected = set()
    if case == "global":
        current = client.get(f"/api/mobile/v1/technician/lab-work-orders/{order_id}", headers=headers).json()
        response = client.patch(f"/api/mobile/v1/technician/lab-work-orders/{order_id}", json={
            "client_name": "Empresa corregida", "address": "Domicilio corregido", "contact_name": "Atención corregida",
            "expected_edit_version": current["edit_version"],
        }, headers=headers)
        assert response.status_code == 200, response.text
        affected = set(equipment_ids[:-1])
    elif case != "unchanged":
        affected = {equipment_ids[1], equipment_ids[6]} if case == "two_of_ten" else {equipment_ids[1]}
        for equipment_id in affected:
            edit_equipment(client, headers, order_id, equipment_id, model="Modelo corregido", brand="Marca corregida")
        if case == "reverted":
            for equipment_id in affected:
                edit_equipment(client, headers, order_id, equipment_id, model=previous[equipment_id]["capture"]["model"], brand=previous[equipment_id]["capture"]["brand"])
            affected = set()
        if case == "legacy":
            with factory() as db:
                order = db.get(LabWorkOrder, order_id)
                snapshot = deepcopy(order.revisions[0].snapshot)
                for equipment in snapshot["equipment"]:
                    equipment.pop("id", None)
                    equipment.pop("inherited_document_values", None)
                order.revisions[0].snapshot = snapshot
                db.commit()
    result = close_individual(client, headers, order_id)
    assert result.status_code == 200, result.text
    with factory() as db:
        order = db.get(LabWorkOrder, order_id)
        assert order.status == "completed" and order.signature_session_id == session_id
        assert order.signature_preserved and not order.signature_required
        assert len(order.signature_session.signatures) == 2
        assert order.revisions[0].final_pdf == old_order_pdf
        for equipment in order.active_equipment:
            old = previous[equipment.id]
            current = equipment.field_sheet
            historical = db.get(FieldSheet, old["id"])
            assert historical.status == "completed"
            assert historical.final_pdf_path == old["path"] and historical.final_pdf_sha256 == old["hash"]
            assert (root / old["path"]).read_bytes() == old["bytes"]
            assert historical.capture_values == old["capture"]
            if equipment.id not in affected:
                assert current.id == old["id"] and len(equipment.field_sheets) == 1
                continue
            assert not historical.is_current
            assert current.id != old["id"] and current.supersedes_field_sheet_id == old["id"]
            assert current.revision_number == 2 and current.status == "completed" and current.is_current
            assert current.lab_signature_session_id == old["session"]
            assert current.template_definition_json == old["template"]
            assert [row.row_data for row in current.results_rows] == old["rows"]
            assert current.final_pdf_path != old["path"] and (root / current.final_pdf_path).is_file()
            if case == "global":
                assert (current.company, current.address, current.attention) == ("Empresa corregida", "Domicilio corregido", "Atención corregida")
            else:
                assert current.capture_values["model"] == "Modelo corregido"
                assert current.capture_values["brand"] == "Marca corregida"
        audit = db.scalar(select(AuditLog).where(AuditLog.action == "lab_work_order.changes_consolidated", AuditLog.entity_id == order_id))
        assert set(audit.new_values["affected_equipment_ids"]) == affected
        assert audit.new_values["signature_policy"] == "preserve" and audit.user_id
        if case == "global":
            assert set(audit.new_values["global_fields"]) == {"client_name", "address", "contact_name"}
        sheet_ids = {sheet.id for equipment in order.active_equipment for sheet in equipment.field_sheets}
    # Idempotent close must not create a third revision or another PDF.
    assert close_individual(client, headers, order_id).status_code == 200
    with factory() as db:
        assert {sheet.id for sheet in db.scalars(select(FieldSheet)).all()} == sheet_ids


@pytest.mark.parametrize("failure", ["first_pdf", "second_pdf", "flush", "commit", "order_pdf"])
def test_consolidation_rolls_back_every_revision_and_pdf(reopened_documents, monkeypatch, failure):
    from app.services import field_sheet_pdfs, lab_work_orders
    client, factory, headers, root, create = reopened_documents
    order_id, equipment_ids, previous, session_id, old_order_pdf = create()
    for equipment_id in equipment_ids[:2]:
        edit_equipment(client, headers, order_id, equipment_id, model="Corrección")
    before_files = {p.relative_to(root): p.read_bytes() for p in root.rglob("*.pdf")}
    with monkeypatch.context() as patch:
        original_render = field_sheet_pdfs._render_pdf
        count = 0
        def render(db, sheet):
            nonlocal count
            count += 1
            if failure == "first_pdf" and count == 1:
                raise RuntimeError("first PDF failed")
            if count == 2:
                if failure == "second_pdf":
                    raise RuntimeError("second PDF failed")
                if failure == "flush":
                    db.add(FieldSheet(equipment_id=None, lab_equipment_id=None))
            return original_render(db, sheet)
        patch.setattr(field_sheet_pdfs, "_render_pdf", render)
        def fail(*args, **kwargs):
            raise RuntimeError("injected failure")
        if failure == "commit":
            patch.setattr(factory.class_, "commit", fail)
        if failure == "order_pdf":
            patch.setattr(lab_work_orders, "generate_lab_work_order_pdf", fail)
        from sqlalchemy.exc import IntegrityError
        with pytest.raises((RuntimeError, IntegrityError)):
            close_individual(client, headers, order_id)
    with factory() as db:
        order = db.get(LabWorkOrder, order_id)
        assert order.status == "draft" and order.final_pdf is None and order.signature_session_id == session_id
        for equipment in order.active_equipment:
            assert equipment.field_sheet.id == previous[equipment.id]["id"]
            assert equipment.field_sheet.is_current and len(equipment.field_sheets) == 1
        assert not list(db.scalars(select(AuditLog).where(AuditLog.action == "lab_work_order.changes_consolidated")))
    assert {p.relative_to(root): p.read_bytes() for p in root.rglob("*.pdf")} == before_files
    assert close_individual(client, headers, order_id).status_code == 200


def test_structural_addition_blocks_close_until_new_signatures(reopened_documents):
    from test_lab_phase5_operational_closure import equipment_payload
    client, factory, headers, root, create = reopened_documents
    order_id, equipment_ids, previous, old_session, _ = create()
    current = edit_equipment(client, headers, order_id, equipment_ids[0], model="Corrección documental")
    added = client.post(f"/api/mobile/v1/technician/lab-work-orders/{order_id}/equipment",
                        json={**equipment_payload(4), "expected_edit_version": current["edit_version"]}, headers=headers)
    assert added.status_code == 201, added.text
    assert added.json()["signature_required"] and added.json()["signature_session_id"] is None
    blocked = close_individual(client, headers, order_id)
    assert blocked.status_code == 409
    with factory() as db:
        assert len(list(db.scalars(select(FieldSheet)))) == 3
    new_id = added.json()["equipment"][-1]["id"]
    set_service(client, headers, order_id, new_id, "traceable")
    signed = sign(client, headers, order_id)
    assert signed.status_code == 200 and signed.json()["signature_session_id"] != old_session
    complete_field_sheet_fully(client, headers, order_id, new_id)
    done = close_individual(client, headers, order_id)
    assert done.status_code == 200, done.text
    with factory() as db:
        order = db.get(LabWorkOrder, order_id)
        assert order.status == "completed" and order.signature_session_id != old_session
        assert order.active_equipment[0].field_sheet.revision_number == 2
        assert db.get(FieldSheet, previous[equipment_ids[0]]["id"]).lab_signature_session_id == old_session


@pytest.mark.parametrize("old_serial,new_serial,kind,preserved", [
    ("ABC-1234", "ABC1234", "correction", True),
    ("abc1234", "ABC1234", "correction", True),
    ("ABO123", "AB0123", "correction", True),
    ("I12345", "112345", "correction", True),
    ("ABC 123", "ABC-123", "correction", True),
    ("ABC12345", "XYZ98765", "correction", False),
    ("ABC12345", "ABC12346", "correction", False),
    ("ABC12345", "ABC12345X", "correction", True),
    ("ABC12345", "XYZ98765", "replacement", False),
    ("ABC-1234", "ABC1234", "replacement", False),
    ("O1", "01", "correction", False),
    ("ABOO1234", "AB001234", "correction", False),
    ("---", "ABC12345", "correction", False),
])
def test_serial_change_classification_is_backend_authority(reopened_documents, old_serial, new_serial, kind, preserved):
    client, factory, headers, root, create = reopened_documents
    order_id, equipment_ids, previous, session_id, _ = create(1, serial=old_serial or "")
    updated = edit_equipment(client, headers, order_id, equipment_ids[0],
                             serial_number=new_serial, identity_change_kind=kind)
    assert updated["signature_preserved"] is preserved
    assert updated["signature_required"] is not preserved
    assert updated["signature_session_id"] == (session_id if preserved else None)
    with factory() as db:
        audit = db.scalars(select(AuditLog).where(
            AuditLog.action == "lab_work_order.equipment_updated",
            AuditLog.entity_id == equipment_ids[0],
        ).order_by(AuditLog.id.desc())).first()
        assert audit.previous_values["serial_number"] == (old_serial or None)
        assert audit.new_values["identity_values"]["serial_number"] == new_serial
        assert audit.new_values["requested_identity_change_kind"] == kind
        assert audit.new_values["effective_identity_change_kind"] == ("correction" if preserved else "replacement")
        assert audit.new_values["signature_invalidated"] is not preserved
        assert audit.new_values["identity_change_reason"]
    closed = close_individual(client, headers, order_id)
    assert closed.status_code == (200 if preserved else 409), closed.text
    with factory() as db:
        order = db.get(LabWorkOrder, order_id)
        old = db.get(FieldSheet, previous[equipment_ids[0]]["id"])
        assert old.status == "completed" and not old.is_current
        assert old.lab_signature_session_id == session_id
        assert (root / old.final_pdf_path).read_bytes() == previous[equipment_ids[0]]["bytes"]
        if preserved:
            assert order.signature_session_id == session_id
            assert order.reopen_ticket_id is None
            assert order.active_equipment[0].field_sheet.revision_number == 2
            assert order.active_equipment[0].field_sheet.capture_values["serial_number"] == new_serial
        else:
            assert order.signature_session_id is None
            assert order.active_equipment[0].field_sheet is None


@pytest.mark.parametrize("override", [False, True])
def test_revision_preserves_editable_prefill_overrides(reopened_documents, monkeypatch, override):
    client, factory, headers, root, create = reopened_documents
    from app.models.field_sheet import FieldSheetSignature
    from app.models.reference_standard import FieldSheetReferenceStandard, ReferenceStandard
    from app.services import lab_field_sheets
    original_complete = lab_field_sheets._complete_lab_field_sheet_uncommitted

    def complete_with_technical_relations(db, equipment, sheet, user):
        if sheet.revision_number == 1:
            standard = ReferenceStandard(internal_code="REF-TEST", name="Patrón de prueba", magnitude="pressure")
            db.add(standard)
            db.flush()
            sheet.reference_standard_links.append(FieldSheetReferenceStandard(
                reference_standard_id=standard.id, usage_role="auxiliary", notes="Referencia técnica",
                validation_snapshot={"verified": True},
            ))
            sheet.signatures.append(FieldSheetSignature(
                role="technical_review", display_label="Revisión técnica", name="Revisor",
                user_id=user.id, signature_data=None,
            ))
            sheet.capture_values = {**sheet.capture_values, "technical_custom": {"measurement": [1, 2, 3]}}
        original_complete(db, equipment, sheet, user)

    monkeypatch.setattr(lab_field_sheets, "_complete_lab_field_sheet_uncommitted", complete_with_technical_relations)
    capture = {"initial_condition": "Equipo presenta desgaste superficial en carcasa",
               "equipment_general_condition": None, "observations": "Nota técnica manual",
               "environment_temperature_start": "23", "environment_humidity_start": "45",
               "technician_notes": "Captura técnica", "results": "Resultados válidos"} if override else {}
    order_id, ids, previous, session, _ = create(1, capture_overrides=capture)
    edit_equipment(client, headers, order_id, ids[0], model="Metadata corregida",
                   is_good_condition=False, observations="Nueva observación heredada")
    response = close_individual(client, headers, order_id)
    assert response.status_code == 200, response.text
    with factory() as db:
        current = db.get(LabWorkOrder, order_id).active_equipment[0].field_sheet
        historical = db.get(FieldSheet, previous[ids[0]]["id"])
        assert {key: getattr(historical, key) for key in previous[ids[0]]["columns"]} == previous[ids[0]]["columns"]
        assert (root / historical.final_pdf_path).read_bytes() == previous[ids[0]]["bytes"]
        assert current.is_current and current.revision_number == 2
        assert current.supersedes_field_sheet_id == historical.id
        assert current.capture_values["model"] == "Metadata corregida"
        assert [row.row_data for row in current.results_rows] == previous[ids[0]]["rows"]
        assert current.capture_values["technical_custom"] == {"measurement": [1, 2, 3]}
        for relationship in ("results_rows", "signatures", "reference_standard_links", "uncertainty_calculations"):
            def data(row):
                return {c.key: getattr(row, c.key) for c in row.__table__.columns
                        if c.key not in {"id", "created_at", "updated_at", "field_sheet_id"}}
            assert [data(row) for row in getattr(current, relationship)] == [data(row) for row in getattr(historical, relationship)]
        assert current.signatures and current.reference_standard_links
        if override:
            assert {key: getattr(current, key) for key in capture} == capture
        else:
            assert current.initial_condition == "REQUIERE REVISIÓN"
            assert current.equipment_general_condition is False
        assert current.observations == (capture.get("observations") or "Sin observaciones")


def test_affected_sheet_with_missing_original_pdf_blocks_without_reinterpreting_history(reopened_documents):
    client, factory, headers, root, create = reopened_documents
    order_id, ids, previous, session_id, _ = create()
    edit_equipment(client, headers, order_id, ids[0], model="Corrección")
    (root / previous[ids[0]]["path"]).unlink()
    response = close_individual(client, headers, order_id)
    assert response.status_code == 404
    with factory() as db:
        order = db.get(LabWorkOrder, order_id)
        assert order.status == "draft"
        assert order.active_equipment[0].field_sheet.id == previous[ids[0]]["id"]
        assert len(order.active_equipment[0].field_sheets) == 1
