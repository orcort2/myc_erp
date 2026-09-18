"""PENDIENTE 7 (encargo de corrección LAB): "LAB EXTERNO" -- la hoja de campo
de un equipo service_type=linked. Cubre FASE 1 (estructura reutiliza
FieldSheet/FieldSheetResult existentes, sin migración), FASE 2 (creación,
validación linked<->lab_externo, estructura dinámica, captura, completar,
prevalidación/cierre), y FASE 4 (PDF sin logos MYC, con la estructura y los
valores).
"""

from __future__ import annotations

import base64
from datetime import datetime, timezone

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event, select
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

import app.models  # noqa: F401
from app.core.db import Base, get_db
from app.core.security import create_access_token
from app.main import app
from app.models.field_sheet import FieldSheet, FieldSheetResult
from app.models.lab_work_order import LabWorkOrder
from app.models.user import Role, User
from app.schemas.lab_client import LabClientCreate
from app.services.lab_clients import create_lab_client
from app.services.lab_field_sheets_external import LAB_EXTERNAL_TEMPLATE_KEY

PNG_DATA_URL = "data:image/png;base64," + base64.b64encode(
    base64.b64decode(
        "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNk+A8AAQUBAScY42YAAAAASUVORK5CYII="
    )
).decode()


@pytest.fixture()
def lab_context():
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )

    @event.listens_for(engine, "connect")
    def enable_sqlite_foreign_keys(dbapi_connection, _connection_record):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine, expire_on_commit=False)
    with factory() as db:
        tech_role = Role(name="Tecnico", description="Técnico")
        admin_role = Role(name="Administrador", description="Administrador")
        db.add_all([tech_role, admin_role])
        db.flush()
        users = []
        for key, role in (("tech", tech_role), ("admin", admin_role)):
            user = User(
                username=f"lab-{key}",
                email=f"lab-{key}@example.test",
                full_name=f"LAB {key}",
                hashed_password="unused",
                account_type="internal",
                status="active",
                is_active=True,
                role_id=role.id,
                roles=[role],
            )
            users.append(user)
        db.add_all(users)
        db.commit()

    def override_db():
        with factory() as db:
            yield db

    app.dependency_overrides[get_db] = override_db
    client = TestClient(app)
    tokens = {
        key: create_access_token(
            str(user.id),
            extra_claims={"roles": [user.roles[0].name], "auth_context": "internal"},
        )
        for key, user in zip(("tech", "admin"), users, strict=True)
    }
    try:
        yield client, factory, tokens
    finally:
        app.dependency_overrides.clear()


def auth(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def create_payload(client_name: str = "Cliente LAB", **extra) -> dict:
    return {
        "reception_date": "2026-08-13",
        "client_name": client_name,
        "address": "Av. Prueba 123",
        "contact_name": "Persona Cliente",
        "contact_phone": "3312345678",
        "contact_email": "cliente@example.com",
        "postal_code": "45601",
        "city": "Tlaquepaque",
        "state_name": "Jalisco",
        "purchase_order": "OC-123",
        "notes": "Recepción LAB",
        **extra,
    }


def make_lab_client_id(factory) -> int:
    """_requires_field_sheet_discipline (misma autoridad que exige
    FieldSheets completas para cerrar) sólo aplica a OT con lab_client_id --
    sin esto, el cierre "pasaría" sin importar si la hoja LAB EXTERNO está
    completed, dando un falso positivo a estos tests."""
    with factory() as db:
        admin = db.scalar(select(User).where(User.username == "lab-admin"))
        lab_client = create_lab_client(
            db, LabClientCreate(company="Cliente LAB Externo", address="Calle 1", attention="Ing. Prueba"),
            admin, operator_client_id=None,
        )
        return lab_client.id


def equipment_payload(index: int, **extra) -> dict:
    return {
        "instrument": f"Instrumento {index}",
        "brand": "MYC Test",
        "identification": f"ID-{index}",
        "serial_number": f"SER-{index}",
        "report_number": None,
        "is_good_condition": True,
        **extra,
    }


def signatures_payload() -> dict:
    signed_at = datetime.now(timezone.utc).isoformat()
    return {
        "technician": {
            "signer_name": "Técnico LAB", "signed_at": signed_at, "version": 1,
            "signature_data_url": PNG_DATA_URL,
        },
        "client": {
            "signer_name": "Cliente LAB", "signed_at": signed_at, "version": 1,
            "signature_data_url": PNG_DATA_URL,
        },
    }


def create_order_with_linked_equipment(client, headers, factory, *, client_name: str = "Cliente LAB") -> tuple[int, int]:
    lab_client_id = make_lab_client_id(factory)
    order = client.post(
        "/api/mobile/v1/technician/lab-work-orders",
        json=create_payload(client_name, lab_client_id=lab_client_id),
        headers=headers,
    )
    assert order.status_code == 201, order.text
    order_id = order.json()["id"]
    added = client.post(
        f"/api/mobile/v1/technician/lab-work-orders/{order_id}/equipment",
        json=equipment_payload(1),
        headers=headers,
    )
    assert added.status_code == 201, added.text
    equipment_id = added.json()["equipment"][-1]["id"]
    service = client.put(
        f"/api/mobile/v1/technician/lab-work-orders/{order_id}/equipment/{equipment_id}/service",
        json={"service_type": "linked", "linked_company_id": None},
        headers=headers,
    )
    assert service.status_code == 200, service.text
    signed = client.post(
        f"/api/mobile/v1/technician/lab-work-orders/{order_id}/signatures",
        json=signatures_payload(),
        headers=headers,
    )
    assert signed.status_code == 200, signed.text
    return order_id, equipment_id


def create_lab_external_sheet(client, headers, order_id: int, equipment_id: int) -> dict:
    created = client.post(
        f"/api/mobile/v1/technician/lab-work-orders/{order_id}/equipment/{equipment_id}/field-sheet",
        json={"template_key": LAB_EXTERNAL_TEMPLATE_KEY},
        headers=headers,
    )
    assert created.status_code == 201, created.text
    return created.json()


ONE_GROUP_TWO_TABLES_STRUCTURE = {
    "groups": [
        {
            "id": "g1",
            "title": "Grupo 1",
            "orientation": "pattern_to_ibc",
            "tables": [
                {
                    "id": "g1_t1", "title": "Tabla 1",
                    "columns": [{"key": "c1", "label": "Columna 1"}, {"key": "c2", "label": "Columna 2"}],
                    "row_count": 2,
                },
                {
                    "id": "g1_t2", "title": "Tabla 2",
                    "columns": [{"key": "c1", "label": "Columna A"}],
                    "row_count": 1,
                },
            ],
        },
    ],
}


def put_structure(client, headers, order_id: int, equipment_id: int, structure: dict):
    return client.put(
        f"/api/mobile/v1/technician/lab-work-orders/{order_id}/equipment/{equipment_id}/field-sheet/lab-externo/structure",
        json=structure,
        headers=headers,
    )


# ---------------------------------------------------------------------------
# FASE 2: creación e integración linked
# ---------------------------------------------------------------------------
def test_linked_equipment_creates_lab_externo_field_sheet(lab_context):
    client, factory, tokens = lab_context
    headers = auth(tokens["tech"])
    order_id, equipment_id = create_order_with_linked_equipment(client, headers, factory)
    sheet = create_lab_external_sheet(client, headers, order_id, equipment_id)
    assert sheet["template_key"] == LAB_EXTERNAL_TEMPLATE_KEY
    assert sheet["status"] == "draft"
    assert sheet["template_definition"]["groups"] == []


def test_linked_equipment_rejects_an_internal_template(lab_context):
    """Auditoría 2026-09-17 (corrige la versión anterior de este test, que
    afirmaba lo contrario): el contrato final es bidireccional --
    accredited/traceable -> plantilla interna, linked -> LAB EXTERNO, sin
    excepciones. Los suites que antes ejercían linked + "general"
    (test_lab_phase3_reception_signing.py, test_mobile_security_context.py,
    test_lab_equipment_by_equipment_workflow.py,
    test_lab_phase5_operational_closure.py) ya se migraron a LAB EXTERNO."""
    client, factory, tokens = lab_context
    headers = auth(tokens["tech"])
    order_id, equipment_id = create_order_with_linked_equipment(client, headers, factory)
    rejected = client.post(
        f"/api/mobile/v1/technician/lab-work-orders/{order_id}/equipment/{equipment_id}/field-sheet",
        json={"template_key": "general"},
        headers=headers,
    )
    assert rejected.status_code == 409, rejected.text


@pytest.mark.parametrize("service_type", ["traceable", "accredited"])
def test_non_linked_equipment_rejects_lab_externo(lab_context, service_type):
    """La regla también aplica en el sentido inverso: acreditado/trazable
    nunca usa LAB EXTERNO."""
    client, factory, tokens = lab_context
    headers = auth(tokens["tech"])
    order = client.post(
        "/api/mobile/v1/technician/lab-work-orders", json=create_payload(), headers=headers
    )
    order_id = order.json()["id"]
    added = client.post(
        f"/api/mobile/v1/technician/lab-work-orders/{order_id}/equipment",
        json=equipment_payload(1), headers=headers,
    )
    equipment_id = added.json()["equipment"][-1]["id"]
    client.put(
        f"/api/mobile/v1/technician/lab-work-orders/{order_id}/equipment/{equipment_id}/service",
        json={"service_type": service_type, "linked_company_id": None}, headers=headers,
    )
    client.post(
        f"/api/mobile/v1/technician/lab-work-orders/{order_id}/signatures",
        json=signatures_payload(), headers=headers,
    )
    rejected = client.post(
        f"/api/mobile/v1/technician/lab-work-orders/{order_id}/equipment/{equipment_id}/field-sheet",
        json={"template_key": LAB_EXTERNAL_TEMPLATE_KEY},
        headers=headers,
    )
    assert rejected.status_code == 409, rejected.text


# ---------------------------------------------------------------------------
# FASE 1/2: tablas dinámicas -- grupos, orientación, estructura vs datos
# ---------------------------------------------------------------------------
def test_defining_structure_creates_matching_result_rows(lab_context):
    client, factory, tokens = lab_context
    headers = auth(tokens["tech"])
    order_id, equipment_id = create_order_with_linked_equipment(client, headers, factory)
    create_lab_external_sheet(client, headers, order_id, equipment_id)

    updated = put_structure(client, headers, order_id, equipment_id, ONE_GROUP_TWO_TABLES_STRUCTURE)
    assert updated.status_code == 200, updated.text
    body = updated.json()
    assert len(body["template_definition"]["groups"]) == 1
    assert body["template_definition"]["groups"][0]["orientation"] == "pattern_to_ibc"

    rows_by_table: dict[str, list[dict]] = {}
    for row in body["results_rows"]:
        rows_by_table.setdefault(row["section_key"], []).append(row)
    assert sorted(row["row_number"] for row in rows_by_table["g1_t1"]) == [1, 2]
    assert sorted(row["row_number"] for row in rows_by_table["g1_t2"]) == [1]


def test_multiple_groups_each_with_their_own_orientation_and_multiple_tables(lab_context):
    client, factory, tokens = lab_context
    headers = auth(tokens["tech"])
    order_id, equipment_id = create_order_with_linked_equipment(client, headers, factory)
    create_lab_external_sheet(client, headers, order_id, equipment_id)

    structure = {
        "groups": [
            {
                "id": "g1", "title": "Grupo 1", "orientation": "pattern_to_ibc",
                "tables": [
                    {"id": "g1_t1", "title": "T1", "columns": [{"key": "c1", "label": "C1"}], "row_count": 1},
                ],
            },
            {
                "id": "g2", "title": "Grupo 2", "orientation": "ibc_to_pattern",
                "tables": [
                    {"id": "g2_t1", "title": "T1", "columns": [{"key": "c1", "label": "C1"}], "row_count": 3},
                    {"id": "g2_t2", "title": "T2", "columns": [{"key": "c1", "label": "C1"}, {"key": "c2", "label": "C2"}, {"key": "c3", "label": "C3"}], "row_count": 5},
                ],
            },
        ],
    }
    updated = put_structure(client, headers, order_id, equipment_id, structure)
    assert updated.status_code == 200, updated.text
    body = updated.json()
    groups_by_id = {group["id"]: group for group in body["template_definition"]["groups"]}
    assert groups_by_id["g1"]["orientation"] == "pattern_to_ibc"
    assert groups_by_id["g2"]["orientation"] == "ibc_to_pattern"
    assert len(groups_by_id["g2"]["tables"]) == 2

    row_counts = {}
    for row in body["results_rows"]:
        row_counts[row["section_key"]] = row_counts.get(row["section_key"], 0) + 1
    assert row_counts == {"g1_t1": 1, "g2_t1": 3, "g2_t2": 5}


def test_shrinking_a_table_row_count_drops_the_now_orphaned_rows(lab_context):
    client, factory, tokens = lab_context
    headers = auth(tokens["tech"])
    order_id, equipment_id = create_order_with_linked_equipment(client, headers, factory)
    create_lab_external_sheet(client, headers, order_id, equipment_id)
    put_structure(client, headers, order_id, equipment_id, ONE_GROUP_TWO_TABLES_STRUCTURE)

    shrunk = {
        "groups": [
            {
                "id": "g1", "title": "Grupo 1", "orientation": "pattern_to_ibc",
                "tables": [
                    {"id": "g1_t1", "title": "Tabla 1", "columns": [{"key": "c1", "label": "Columna 1"}], "row_count": 1},
                ],
            },
        ],
    }
    updated = put_structure(client, headers, order_id, equipment_id, shrunk)
    assert updated.status_code == 200, updated.text
    body = updated.json()
    remaining_keys = {(row["section_key"], row["row_number"]) for row in body["results_rows"]}
    assert remaining_keys == {("g1_t1", 1)}


def test_duplicate_table_ids_across_groups_are_rejected(lab_context):
    client, factory, tokens = lab_context
    headers = auth(tokens["tech"])
    order_id, equipment_id = create_order_with_linked_equipment(client, headers, factory)
    create_lab_external_sheet(client, headers, order_id, equipment_id)
    structure = {
        "groups": [
            {"id": "g1", "title": "G1", "orientation": "pattern_to_ibc", "tables": [
                {"id": "same", "title": "T", "columns": [{"key": "c1", "label": "C1"}], "row_count": 1},
            ]},
            {"id": "g2", "title": "G2", "orientation": "ibc_to_pattern", "tables": [
                {"id": "same", "title": "T", "columns": [{"key": "c1", "label": "C1"}], "row_count": 1},
            ]},
        ],
    }
    rejected = put_structure(client, headers, order_id, equipment_id, structure)
    assert rejected.status_code == 422, rejected.text


def test_structure_cannot_change_once_the_sheet_is_completed(lab_context):
    client, factory, tokens = lab_context
    headers = auth(tokens["tech"])
    order_id, equipment_id = create_order_with_linked_equipment(client, headers, factory)
    create_lab_external_sheet(client, headers, order_id, equipment_id)
    put_structure(client, headers, order_id, equipment_id, ONE_GROUP_TWO_TABLES_STRUCTURE)

    sheet = client.get(
        f"/api/mobile/v1/technician/lab-work-orders/{order_id}/equipment/{equipment_id}/field-sheet",
        headers=headers,
    ).json()
    rows = [
        {"id": row["id"], "section_key": row["section_key"], "row_number": row["row_number"], "row_data": {"c1": "1.00", "c2": "2.00"}}
        for row in sheet["results_rows"]
    ]
    patched = client.patch(
        f"/api/mobile/v1/technician/lab-work-orders/{order_id}/equipment/{equipment_id}/field-sheet",
        json={"results_rows": rows},
        headers=headers,
    )
    assert patched.status_code == 200, patched.text
    completed = client.post(
        f"/api/mobile/v1/technician/lab-work-orders/{order_id}/equipment/{equipment_id}/field-sheet/complete",
        headers=headers,
    )
    assert completed.status_code == 200, completed.text

    blocked = put_structure(client, headers, order_id, equipment_id, ONE_GROUP_TWO_TABLES_STRUCTURE)
    assert blocked.status_code == 409, blocked.text


# ---------------------------------------------------------------------------
# FASE 2: captura de valores (reutiliza el PATCH existente, sin endpoint nuevo)
# ---------------------------------------------------------------------------
def test_capturing_values_reuses_the_existing_patch_endpoint(lab_context):
    client, factory, tokens = lab_context
    headers = auth(tokens["tech"])
    order_id, equipment_id = create_order_with_linked_equipment(client, headers, factory)
    create_lab_external_sheet(client, headers, order_id, equipment_id)
    put_structure(client, headers, order_id, equipment_id, ONE_GROUP_TWO_TABLES_STRUCTURE)

    sheet = client.get(
        f"/api/mobile/v1/technician/lab-work-orders/{order_id}/equipment/{equipment_id}/field-sheet",
        headers=headers,
    ).json()
    row_g1_t1_1 = next(r for r in sheet["results_rows"] if r["section_key"] == "g1_t1" and r["row_number"] == 1)
    patched = client.patch(
        f"/api/mobile/v1/technician/lab-work-orders/{order_id}/equipment/{equipment_id}/field-sheet",
        json={"results_rows": [
            {"id": row_g1_t1_1["id"], "section_key": "g1_t1", "row_number": 1, "row_data": {"c1": "12.3", "c2": "45.6"}},
        ]},
        headers=headers,
    )
    assert patched.status_code == 200, patched.text
    saved = next(r for r in patched.json()["results_rows"] if r["id"] == row_g1_t1_1["id"])
    assert saved["row_data"]["c1"] == "12.3"
    assert saved["row_data"]["c2"] == "45.6"


def test_completing_requires_at_least_one_captured_value(lab_context):
    client, factory, tokens = lab_context
    headers = auth(tokens["tech"])
    order_id, equipment_id = create_order_with_linked_equipment(client, headers, factory)
    create_lab_external_sheet(client, headers, order_id, equipment_id)
    put_structure(client, headers, order_id, equipment_id, ONE_GROUP_TWO_TABLES_STRUCTURE)

    rejected = client.post(
        f"/api/mobile/v1/technician/lab-work-orders/{order_id}/equipment/{equipment_id}/field-sheet/complete",
        headers=headers,
    )
    assert rejected.status_code == 422, rejected.text


# ---------------------------------------------------------------------------
# PENDIENTE 7, auditoría 2026-09-17, sección 2: contrato explícito de
# completitud (validate_lab_external_ready_to_complete) -- antes dependía
# accidentalmente de que el motor genérico (piensa en "blocks"/
# "result_sections") no encontrara nada que exigir sobre
# template_definition_json["groups"].
# ---------------------------------------------------------------------------
def test_completing_with_zero_groups_is_rejected(lab_context):
    client, factory, tokens = lab_context
    headers = auth(tokens["tech"])
    order_id, equipment_id = create_order_with_linked_equipment(client, headers, factory)
    create_lab_external_sheet(client, headers, order_id, equipment_id)
    # Nunca se definió ningún grupo -- template_definition_json["groups"] == [].

    rejected = client.post(
        f"/api/mobile/v1/technician/lab-work-orders/{order_id}/equipment/{equipment_id}/field-sheet/complete",
        headers=headers,
    )
    assert rejected.status_code == 422, rejected.text
    assert rejected.json()["detail"]["missing_fields"] == ["groups"]


def test_completing_with_structure_and_real_capture_succeeds(lab_context):
    """Estructura válida + al menos un valor capturado -> completa. No
    exige llenar TODAS las celdas -- basta una captura real, mismo
    criterio ya vigente para cualquier otra plantilla LAB
    (_validate_results_rows, reutilizado tal cual)."""
    client, factory, tokens = lab_context
    headers = auth(tokens["tech"])
    order_id, equipment_id = create_order_with_linked_equipment(client, headers, factory)
    create_lab_external_sheet(client, headers, order_id, equipment_id)
    put_structure(client, headers, order_id, equipment_id, ONE_GROUP_TWO_TABLES_STRUCTURE)
    sheet = client.get(
        f"/api/mobile/v1/technician/lab-work-orders/{order_id}/equipment/{equipment_id}/field-sheet",
        headers=headers,
    ).json()
    only_first_row = sheet["results_rows"][0]
    patched = client.patch(
        f"/api/mobile/v1/technician/lab-work-orders/{order_id}/equipment/{equipment_id}/field-sheet",
        json={"results_rows": [
            {"id": only_first_row["id"], "section_key": only_first_row["section_key"], "row_number": only_first_row["row_number"], "row_data": {"c1": "1.00"}},
        ]},
        headers=headers,
    )
    assert patched.status_code == 200, patched.text

    completed = client.post(
        f"/api/mobile/v1/technician/lab-work-orders/{order_id}/equipment/{equipment_id}/field-sheet/complete",
        headers=headers,
    )
    assert completed.status_code == 200, completed.text
    assert completed.json()["status"] == "completed"


def test_completed_freezes_both_structure_and_captured_values(lab_context):
    client, factory, tokens = lab_context
    headers = auth(tokens["tech"])
    order_id, equipment_id = create_order_with_linked_equipment(client, headers, factory)
    create_lab_external_sheet(client, headers, order_id, equipment_id)
    put_structure(client, headers, order_id, equipment_id, ONE_GROUP_TWO_TABLES_STRUCTURE)
    sheet = client.get(
        f"/api/mobile/v1/technician/lab-work-orders/{order_id}/equipment/{equipment_id}/field-sheet",
        headers=headers,
    ).json()
    first_row = sheet["results_rows"][0]
    client.patch(
        f"/api/mobile/v1/technician/lab-work-orders/{order_id}/equipment/{equipment_id}/field-sheet",
        json={"results_rows": [
            {"id": first_row["id"], "section_key": first_row["section_key"], "row_number": first_row["row_number"], "row_data": {"c1": "1.00"}},
        ]},
        headers=headers,
    )
    completed = client.post(
        f"/api/mobile/v1/technician/lab-work-orders/{order_id}/equipment/{equipment_id}/field-sheet/complete",
        headers=headers,
    )
    assert completed.status_code == 200, completed.text

    structure_blocked = put_structure(client, headers, order_id, equipment_id, ONE_GROUP_TWO_TABLES_STRUCTURE)
    assert structure_blocked.status_code == 409, structure_blocked.text

    values_blocked = client.patch(
        f"/api/mobile/v1/technician/lab-work-orders/{order_id}/equipment/{equipment_id}/field-sheet",
        json={"results_rows": [
            {"id": first_row["id"], "section_key": first_row["section_key"], "row_number": first_row["row_number"], "row_data": {"c1": "OTRO VALOR"}},
        ]},
        headers=headers,
    )
    assert values_blocked.status_code == 409, values_blocked.text

    with factory() as db:
        frozen = db.get(FieldSheet, completed.json()["id"])
        assert frozen.template_definition_json["groups"][0]["tables"][0]["row_count"] == 2
        frozen_row = next(row for row in frozen.results_rows if row.id == first_row["id"])
        assert frozen_row.row_data["c1"] == "1.00"


# ---------------------------------------------------------------------------
# FASE 5: prevalidación/cierre -- linked exige LAB EXTERNO completed
# ---------------------------------------------------------------------------
def test_linked_without_a_completed_lab_externo_sheet_blocks_closure(lab_context):
    client, factory, tokens = lab_context
    headers = auth(tokens["tech"])
    order_id, equipment_id = create_order_with_linked_equipment(client, headers, factory)
    create_lab_external_sheet(client, headers, order_id, equipment_id)
    # Nunca se completa -- el cierre debe bloquear igual que cualquier otra
    # plantilla sin completar (_missing_completed_sheets es agnóstica de
    # template_key).
    rejected = client.post(
        f"/api/mobile/v1/technician/lab-work-orders/{order_id}/complete", headers=headers,
    )
    assert rejected.status_code == 409, rejected.text


def test_linked_with_a_completed_lab_externo_sheet_passes_prevalidation_and_closes(lab_context):
    client, factory, tokens = lab_context
    headers = auth(tokens["tech"])
    order_id, equipment_id = create_order_with_linked_equipment(client, headers, factory)
    create_lab_external_sheet(client, headers, order_id, equipment_id)
    put_structure(client, headers, order_id, equipment_id, ONE_GROUP_TWO_TABLES_STRUCTURE)
    sheet = client.get(
        f"/api/mobile/v1/technician/lab-work-orders/{order_id}/equipment/{equipment_id}/field-sheet",
        headers=headers,
    ).json()
    rows = [
        {"id": row["id"], "section_key": row["section_key"], "row_number": row["row_number"], "row_data": {"c1": "1.00"}}
        for row in sheet["results_rows"]
    ]
    client.patch(
        f"/api/mobile/v1/technician/lab-work-orders/{order_id}/equipment/{equipment_id}/field-sheet",
        json={"results_rows": rows}, headers=headers,
    )
    completed_sheet = client.post(
        f"/api/mobile/v1/technician/lab-work-orders/{order_id}/equipment/{equipment_id}/field-sheet/complete",
        headers=headers,
    )
    assert completed_sheet.status_code == 200, completed_sheet.text

    # Un equipo linked también exige su folio de certificado resuelto para
    # cerrar (_unresolved_folio_equipment) -- autoridad DISTINTA de
    # "FieldSheet completed" (_missing_completed_sheets); LAB EXTERNO no la
    # sustituye ni la evita.
    admin_headers = auth(tokens["admin"])
    order_detail = client.get(
        f"/api/mobile/v1/technician/lab-work-orders/{order_id}", headers=headers
    ).json()
    folio_ticket_id = order_detail["equipment"][0]["folio_ticket_id"]
    resolved = client.post(
        f"/api/mobile/v1/technician/tickets/{folio_ticket_id}/resolve",
        json={"authorized_folio": "LV-EXTERNO-1"},
        headers=admin_headers,
    )
    assert resolved.status_code == 200, resolved.text

    closed = client.post(
        f"/api/mobile/v1/technician/lab-work-orders/{order_id}/complete", headers=headers,
    )
    assert closed.status_code == 200, closed.text
    assert closed.json()["status"] == "completed"

    with factory() as db:
        sheet_row = db.query(FieldSheet).filter(FieldSheet.lab_equipment_id == equipment_id).one()
        assert sheet_row.template_key == LAB_EXTERNAL_TEMPLATE_KEY
        assert sheet_row.status == "completed"


# ---------------------------------------------------------------------------
# FASE 1/4: revisión histórica congela la estructura anterior; PDF sin logos
# ---------------------------------------------------------------------------
def test_pdf_renders_without_myc_logo_and_includes_structure_and_values(lab_context):
    client, factory, tokens = lab_context
    headers = auth(tokens["tech"])
    order_id, equipment_id = create_order_with_linked_equipment(client, headers, factory)
    create_lab_external_sheet(client, headers, order_id, equipment_id)
    put_structure(client, headers, order_id, equipment_id, ONE_GROUP_TWO_TABLES_STRUCTURE)
    sheet = client.get(
        f"/api/mobile/v1/technician/lab-work-orders/{order_id}/equipment/{equipment_id}/field-sheet",
        headers=headers,
    ).json()
    rows = [
        {"id": row["id"], "section_key": row["section_key"], "row_number": row["row_number"], "row_data": {"c1": "1.00", "c2": "2.00"}}
        for row in sheet["results_rows"]
    ]
    client.patch(
        f"/api/mobile/v1/technician/lab-work-orders/{order_id}/equipment/{equipment_id}/field-sheet",
        json={"results_rows": rows}, headers=headers,
    )
    client.post(
        f"/api/mobile/v1/technician/lab-work-orders/{order_id}/equipment/{equipment_id}/field-sheet/complete",
        headers=headers,
    )
    pdf = client.get(
        f"/api/mobile/v1/technician/lab-work-orders/{order_id}/equipment/{equipment_id}/field-sheet/pdf",
        headers=headers,
    )
    assert pdf.status_code == 200, pdf.text
    assert pdf.headers["content-type"] == "application/pdf"

    from pypdf import PdfReader
    import io

    text = "\n".join(page.extract_text() or "" for page in PdfReader(io.BytesIO(pdf.content)).pages)
    assert "LAB EXTERNO" in text
    assert "Tabla 1" in text
    assert "1.00" in text


def test_reopen_correction_freezes_the_previous_structure_and_new_revision_starts_from_it(lab_context):
    """La corrección clona la revisión (misma autoridad que cualquier otra
    plantilla, ver _clone_field_sheet_for_correction) -- la estructura
    anterior queda intacta como histórico, is_current=False."""
    client, factory, tokens = lab_context
    headers = auth(tokens["tech"])
    admin_headers = auth(tokens["admin"])
    order_id, equipment_id = create_order_with_linked_equipment(client, headers, factory)
    create_lab_external_sheet(client, headers, order_id, equipment_id)
    put_structure(client, headers, order_id, equipment_id, ONE_GROUP_TWO_TABLES_STRUCTURE)
    sheet = client.get(
        f"/api/mobile/v1/technician/lab-work-orders/{order_id}/equipment/{equipment_id}/field-sheet",
        headers=headers,
    ).json()
    original_sheet_id = sheet["id"]
    rows = [
        {"id": row["id"], "section_key": row["section_key"], "row_number": row["row_number"], "row_data": {"c1": "1.00"}}
        for row in sheet["results_rows"]
    ]
    client.patch(
        f"/api/mobile/v1/technician/lab-work-orders/{order_id}/equipment/{equipment_id}/field-sheet",
        json={"results_rows": rows}, headers=headers,
    )
    completed = client.post(
        f"/api/mobile/v1/technician/lab-work-orders/{order_id}/equipment/{equipment_id}/field-sheet/complete",
        headers=headers,
    )
    assert completed.status_code == 200, completed.text
    with factory() as db:
        # Único equipo activo, ya completed -> la OT sincroniza directo a
        # ready_to_close (_complete_lab_field_sheet_uncommitted); el reopen
        # directo de UNA hoja opera sobre received_signed/in_progress/
        # ready_to_close, nunca sobre una OT ya cerrada -- por eso este test
        # NO cierra la OT completa antes de reabrir la hoja.
        assert db.get(LabWorkOrder, order_id).status == "ready_to_close"

    reopened = client.post(
        f"/api/mobile/v1/technician/lab-work-orders/{order_id}/equipment/{equipment_id}/field-sheet/reopen",
        json={"reason": "Corrección de un valor capturado"},
        headers=admin_headers,
    )
    assert reopened.status_code == 200, reopened.text
    new_sheet = reopened.json()
    assert new_sheet["id"] != original_sheet_id
    assert new_sheet["status"] == "draft"
    assert new_sheet["template_definition"]["groups"][0]["id"] == "g1"

    with factory() as db:
        historical = db.get(FieldSheet, original_sheet_id)
        assert historical.is_current is False
        assert historical.status == "completed"
        assert historical.template_definition_json["groups"][0]["tables"][0]["row_count"] == 2


# ---------------------------------------------------------------------------
# PENDIENTE 7, auditoría 2026-09-17, sección 3: progreso de bandeja LAB
# EXTERNO. _field_sheet_progress (lab_field_sheets.py) recorría
# template_definition_json["result_sections"] -- LAB EXTERNO usa ["groups"],
# así que aparecía 0/0 sin importar cuánto se hubiera capturado.
# ---------------------------------------------------------------------------
def _tray_entry(client, headers, equipment_id: int) -> dict:
    tray = client.get(
        "/api/mobile/v1/technician/lab-field-sheets?offset=0&limit=50", headers=headers,
    )
    assert tray.status_code == 200, tray.text
    return next(item for item in tray.json()["items"] if item["equipment_id"] == equipment_id)


def test_lab_externo_freshly_structured_shows_zero_of_n_in_the_tray(lab_context):
    client, factory, tokens = lab_context
    headers = auth(tokens["tech"])
    order_id, equipment_id = create_order_with_linked_equipment(client, headers, factory)
    create_lab_external_sheet(client, headers, order_id, equipment_id)
    put_structure(client, headers, order_id, equipment_id, ONE_GROUP_TWO_TABLES_STRUCTURE)

    entry = _tray_entry(client, headers, equipment_id)
    assert entry["progress_completed"] == 0
    # ONE_GROUP_TWO_TABLES_STRUCTURE: g1_t1 (row_count=2) + g1_t2 (row_count=1) = 3.
    assert entry["progress_required"] == 3


def test_lab_externo_partial_capture_shows_x_of_n_in_the_tray(lab_context):
    client, factory, tokens = lab_context
    headers = auth(tokens["tech"])
    order_id, equipment_id = create_order_with_linked_equipment(client, headers, factory)
    create_lab_external_sheet(client, headers, order_id, equipment_id)
    put_structure(client, headers, order_id, equipment_id, ONE_GROUP_TWO_TABLES_STRUCTURE)
    sheet = client.get(
        f"/api/mobile/v1/technician/lab-work-orders/{order_id}/equipment/{equipment_id}/field-sheet",
        headers=headers,
    ).json()
    one_row = next(row for row in sheet["results_rows"] if row["section_key"] == "g1_t1" and row["row_number"] == 1)
    client.patch(
        f"/api/mobile/v1/technician/lab-work-orders/{order_id}/equipment/{equipment_id}/field-sheet",
        json={"results_rows": [
            {"id": one_row["id"], "section_key": "g1_t1", "row_number": 1, "row_data": {"c1": "1.00"}},
        ]},
        headers=headers,
    )

    entry = _tray_entry(client, headers, equipment_id)
    assert entry["progress_completed"] == 1
    assert entry["progress_required"] == 3


def test_lab_externo_full_capture_shows_n_of_n_in_the_tray(lab_context):
    client, factory, tokens = lab_context
    headers = auth(tokens["tech"])
    order_id, equipment_id = create_order_with_linked_equipment(client, headers, factory)
    create_lab_external_sheet(client, headers, order_id, equipment_id)
    put_structure(client, headers, order_id, equipment_id, ONE_GROUP_TWO_TABLES_STRUCTURE)
    sheet = client.get(
        f"/api/mobile/v1/technician/lab-work-orders/{order_id}/equipment/{equipment_id}/field-sheet",
        headers=headers,
    ).json()
    rows = [
        {"id": row["id"], "section_key": row["section_key"], "row_number": row["row_number"], "row_data": {"c1": "1.00"}}
        for row in sheet["results_rows"]
    ]
    client.patch(
        f"/api/mobile/v1/technician/lab-work-orders/{order_id}/equipment/{equipment_id}/field-sheet",
        json={"results_rows": rows}, headers=headers,
    )

    entry = _tray_entry(client, headers, equipment_id)
    assert entry["progress_completed"] == 3
    assert entry["progress_required"] == 3


def test_internal_template_progress_unaffected_by_lab_externo_change(lab_context):
    """Plantilla interna conserva su comportamiento existente
    (template_definition_json["result_sections"]) -- la rama nueva de LAB
    EXTERNO en _field_sheet_progress nunca se activa para ella."""
    client, factory, tokens = lab_context
    headers = auth(tokens["tech"])
    order = client.post(
        "/api/mobile/v1/technician/lab-work-orders", json=create_payload(), headers=headers
    )
    order_id = order.json()["id"]
    added = client.post(
        f"/api/mobile/v1/technician/lab-work-orders/{order_id}/equipment",
        json=equipment_payload(1), headers=headers,
    )
    equipment_id = added.json()["equipment"][-1]["id"]
    client.put(
        f"/api/mobile/v1/technician/lab-work-orders/{order_id}/equipment/{equipment_id}/service",
        json={"service_type": "traceable", "linked_company_id": None}, headers=headers,
    )
    client.post(
        f"/api/mobile/v1/technician/lab-work-orders/{order_id}/signatures",
        json=signatures_payload(), headers=headers,
    )
    created = client.post(
        f"/api/mobile/v1/technician/lab-work-orders/{order_id}/equipment/{equipment_id}/field-sheet",
        json={"template_key": "general"},
        headers=headers,
    )
    assert created.status_code == 201, created.text
    sheet = created.json()

    entry_before = _tray_entry(client, headers, equipment_id)
    required_before = entry_before["progress_required"]
    assert required_before > 0

    first_row = sheet["results_rows"][0]
    client.patch(
        f"/api/mobile/v1/technician/lab-work-orders/{order_id}/equipment/{equipment_id}/field-sheet",
        json={"results_rows": [
            {"id": first_row["id"], "section_key": first_row["section_key"], "row_number": first_row["row_number"], "row_data": {"simple_value": "1.00"}},
        ]},
        headers=headers,
    )
    entry_after = _tray_entry(client, headers, equipment_id)
    assert entry_after["progress_required"] == required_before
    assert entry_after["progress_completed"] >= 1
