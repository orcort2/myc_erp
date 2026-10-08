"""SG-4J-A1 sobre PostgreSQL REAL (requiere LAB_POSTGRES_TEST_URL): upgrade,
downgrade y backfill con datos creados por el flujo real de Instalación, cadenas
históricas R1 -> R2, rechazo de cadenas corruptas, restricciones únicas y
concurrencia. Cada prueba usa un schema aislado; nunca toca otra base."""

from __future__ import annotations

import logging
import os
import uuid
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from threading import Barrier

import pytest
from alembic import command
from alembic.config import Config
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, inspect, select, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import sessionmaker

import app.models  # noqa: F401
from app.core.config import settings
from app.core.db import get_db
from app.core.security import create_access_token
from app.main import app
from app.models.user import Role, User
from test_general_service_delivery import deliver, finalize, order_with_reports, report_url  # noqa: F401
from test_technical_report_installation import isolated_storage  # noqa: F401

ROOT = Path(__file__).resolve().parents[2]
PREVIOUS_HEAD = "ef09a7ea9e97"
INTERVENTIONS_HEAD = "a4b7c1d9e3f2"
NEW_HEAD = "c6d9e2f5a8b1"

pytestmark = pytest.mark.skipif(
    not os.getenv("LAB_POSTGRES_TEST_URL"),
    reason="requiere LAB_POSTGRES_TEST_URL para migrar un esquema Postgres real",
)


class Db:
    def __init__(self, url: str, schema: str):
        self.url, self.schema = url, schema
        self.engine = create_engine(url, connect_args={"options": f"-csearch_path={schema}"})

    def alembic(self, action: str, revision: str) -> None:
        previous = settings.database_url
        settings.database_url = f"{self.url}?options=-csearch_path={self.schema}"
        # migrations/env.py llama a logging.fileConfig, que desactiva los loggers
        # ya creados y rompería pruebas posteriores basadas en caplog.
        root_state = (list(logging.root.handlers), logging.root.level)
        disabled = {name: logger.disabled for name, logger in logging.root.manager.loggerDict.items() if isinstance(logger, logging.Logger)}
        try:
            config = Config(str(ROOT / "backend" / "alembic.ini"))
            config.set_main_option("script_location", str(ROOT / "backend" / "migrations"))
            getattr(command, action)(config, revision)
        finally:
            settings.database_url = previous
            logging.root.handlers[:] = root_state[0]
            logging.root.setLevel(root_state[1])
            for name, was_disabled in disabled.items():
                logging.getLogger(name).disabled = was_disabled

    def tables(self) -> set[str]:
        return set(inspect(self.engine).get_table_names(schema=self.schema))

    def revision(self) -> str:
        with self.engine.connect() as connection:
            return connection.execute(text("SELECT version_num FROM alembic_version")).scalar()

    def rows(self, sql: str):
        with self.engine.connect() as connection:
            return [tuple(row) for row in connection.execute(text(sql)).all()]


@pytest.fixture()
def db():
    url = os.environ["LAB_POSTGRES_TEST_URL"]
    schema = f"sg4j_a1_{uuid.uuid4().hex}"
    with create_engine(url).begin() as connection:
        connection.execute(text(f'CREATE SCHEMA "{schema}"'))
    database = Db(url, schema)
    database.alembic("upgrade", "head")
    try:
        yield database
    finally:
        database.engine.dispose()
        app.dependency_overrides.clear()
        with create_engine(url).begin() as connection:
            connection.execute(text(f'DROP SCHEMA "{schema}" CASCADE'))


@pytest.fixture()
def api(db):
    factory = sessionmaker(bind=db.engine, expire_on_commit=False)
    with factory() as session:
        role = session.scalar(select(Role).where(Role.name == "Tecnico"))
        user = User(
            username=f"a1-{uuid.uuid4().hex[:8]}", email=f"a1-{uuid.uuid4().hex[:8]}@example.test", full_name="LAB tech",
            hashed_password="unused", account_type="internal", status="active", is_active=True, role_id=role.id, roles=[role],
        )
        session.add(user)
        session.commit()
        token = create_access_token(str(user.id), extra_claims={"roles": ["Tecnico"], "auth_context": "internal"})

    def override_db():
        with factory() as session:
            yield session

    app.dependency_overrides[get_db] = override_db
    yield TestClient(app), {"Authorization": f"Bearer {token}"}
    app.dependency_overrides.clear()


DOCUMENT_SQL = (
    "SELECT id, folio, revision_number, status, is_current, final_pdf_path, final_pdf_sha256, pdf_renderer_version, "
    "completed_at, document_snapshot::text, capture_values::text FROM technical_reports ORDER BY id"
)


def build_delivered(client, headers, count=2):
    order, equipments, reports = order_with_reports(client, headers, count=count)
    for equipment in equipments:
        finalize(client, headers, order, equipment)
    assert deliver(client, headers, order).status_code == 201
    for equipment in equipments:
        assert client.post(report_url(order["id"], equipment["id"], "/finalize"), headers=headers).status_code == 200
    return order, equipments, reports


def test_downgrade_then_upgrade_preserves_every_document_and_rebuilds_interventions(db, api):
    client, headers = api
    build_delivered(client, headers)
    documents = db.rows(DOCUMENT_SQL)
    evidence = db.rows("SELECT id, sha256, storage_path FROM technical_report_evidence ORDER BY id")
    deliveries = db.rows("SELECT id, status, voucher_pdf_sha256 FROM lab_work_order_deliveries ORDER BY id")
    folios = [row[1] for row in documents]
    assert len(db.rows("SELECT id FROM technical_interventions")) == 2

    db.alembic("downgrade", PREVIOUS_HEAD)
    assert db.revision() == PREVIOUS_HEAD
    assert not {"technical_interventions", "technical_intervention_deliveries"} & db.tables()
    assert "intervention_id" not in {c["name"] for c in inspect(db.engine).get_columns("technical_reports", schema=db.schema)}
    assert db.rows(DOCUMENT_SQL) != [] and [row[:9] for row in db.rows(DOCUMENT_SQL)] == [row[:9] for row in documents], "el downgrade no toca documentos"

    db.alembic("upgrade", "head")
    assert db.revision() == NEW_HEAD
    assert db.rows(DOCUMENT_SQL) == documents, "folios, PDFs, SHA, snapshots y capturas idénticos tras el backfill"
    assert db.rows("SELECT id, sha256, storage_path FROM technical_report_evidence ORDER BY id") == evidence
    assert db.rows("SELECT id, status, voucher_pdf_sha256 FROM lab_work_order_deliveries ORDER BY id") == deliveries
    interventions = db.rows("SELECT id, folio, intervention_type, status, created_by_user_id FROM technical_interventions ORDER BY id")
    assert sorted(row[1] for row in interventions) == sorted(folios)
    assert {row[2:4] for row in interventions} == {("installation", "completed")}
    assert all(row[4] is not None for row in interventions), "actor recuperado de la auditoría"
    assert db.rows("SELECT count(*) FROM technical_reports WHERE intervention_id IS NULL") == [(0,)]
    links = db.rows("SELECT technical_report_id, delivery_id FROM technical_intervention_deliveries ORDER BY id")
    assert len(links) == 2 and all(link[0] is not None for link in links)
    # Integridad referencial real.
    assert db.rows(
        "SELECT count(*) FROM technical_reports r LEFT JOIN technical_interventions i ON i.id = r.intervention_id WHERE i.id IS NULL"
    ) == [(0,)]


def test_historical_r1_to_r2_chain_becomes_one_intervention_with_two_revisions(db, api):
    client, headers = api
    order, [equipment], [report] = build_delivered(client, headers, count=1)
    db.alembic("downgrade", PREVIOUS_HEAD)
    with db.engine.begin() as connection:
        connection.execute(text("UPDATE technical_reports SET is_current = false WHERE id = :id"), {"id": report["id"]})
        connection.execute(text(
            "INSERT INTO technical_reports (lab_equipment_id, report_type, folio, status, capture_values, report_schema_version, "
            "revision_number, is_current, supersedes_report_id) "
            "SELECT lab_equipment_id, report_type, 'MYC-IN10-26-9002', 'draft', capture_values, report_schema_version, 2, true, id "
            "FROM technical_reports WHERE id = :id"
        ), {"id": report["id"]})
    before = db.rows("SELECT id, folio, revision_number, final_pdf_sha256 FROM technical_reports ORDER BY id")
    db.alembic("upgrade", "head")
    assert db.rows("SELECT id, folio, revision_number, final_pdf_sha256 FROM technical_reports ORDER BY id") == before
    interventions = db.rows("SELECT id, folio, status FROM technical_interventions")
    assert len(interventions) == 1 and interventions[0][1] == report["folio"] and interventions[0][2] == "open", "estado = el de la última revisión"
    assert db.rows("SELECT count(DISTINCT intervention_id), count(*) FROM technical_reports") == [(1, 2)]
    # El vínculo con la entrega apunta a la revisión que la usó (R1).
    assert db.rows("SELECT technical_report_id FROM technical_intervention_deliveries") == [(report["id"],)]


# Un fork (dos sucesores) ya es imposible en el esquema heredado: uq_technical_reports_supersedes_report_id.
@pytest.mark.parametrize("corruption, message", [("cycle", "a sí mismo"), ("mixed_equipment", "mezcla equipos")])
def test_corrupt_historical_chains_abort_the_migration_without_partial_state(db, api, corruption, message):
    client, headers = api
    order, equipments, [first, *_] = build_delivered(client, headers, count=2 if corruption == "mixed_equipment" else 1)
    db.alembic("downgrade", PREVIOUS_HEAD)
    copy = (
        "INSERT INTO technical_reports (lab_equipment_id, report_type, folio, status, capture_values, report_schema_version, "
        "revision_number, is_current, supersedes_report_id) SELECT {equipment}, report_type, '{folio}', 'draft', capture_values, "
        "report_schema_version, {revision}, false, {supersedes} FROM technical_reports WHERE id = {source}"
    )
    with db.engine.begin() as connection:
        connection.execute(text("UPDATE technical_reports SET is_current = false WHERE id = :id"), {"id": first["id"]})
        if corruption == "cycle":
            connection.execute(text(f"UPDATE technical_reports SET supersedes_report_id = {first['id']} WHERE id = {first['id']}"))
        else:
            other = db.rows("SELECT id FROM lab_work_order_equipment ORDER BY id")[-1][0]
            connection.execute(text(copy.format(equipment=other, folio="MYC-IN10-26-9103", revision=2, supersedes=first["id"], source=first["id"])))
    with pytest.raises(Exception, match=message):
        db.alembic("upgrade", "head")
    assert db.revision() == PREVIOUS_HEAD, "la migración transaccional no avanzó"
    assert not {"technical_interventions", "technical_intervention_deliveries"} & db.tables(), "sin estructuras a medias"


def test_database_constraints_enforce_unique_revisions_and_a_single_current_report_per_intervention(db, api):
    client, headers = api
    order, [equipment], [report] = order_with_reports(client, headers)
    base = (
        "INSERT INTO technical_reports (lab_equipment_id, intervention_id, report_type, folio, status, capture_values, "
        "report_schema_version, revision_number, is_current) SELECT lab_equipment_id, intervention_id, report_type, :folio, 'draft', "
        "capture_values, report_schema_version, :revision, :current FROM technical_reports WHERE id = :id"
    )
    with pytest.raises(IntegrityError):  # misma (intervención, revisión)
        with db.engine.begin() as connection:
            connection.execute(text(base), {"folio": "MYC-IN10-26-9201", "revision": 1, "current": False, "id": report["id"]})
    with pytest.raises(IntegrityError):  # dos vigentes para la misma intervención (aun con otra revisión)
        with db.engine.begin() as connection:
            connection.execute(text(base), {"folio": "MYC-IN10-26-9202", "revision": 2, "current": True, "id": report["id"]})
    with db.engine.begin() as connection:  # una revisión no vigente adicional sí es válida a nivel de intervención
        connection.execute(text(base), {"folio": "MYC-IN10-26-9203", "revision": 2, "current": False, "id": report["id"]})
    assert db.rows("SELECT count(*) FROM technical_reports") == [(2,)]


def test_concurrent_creation_yields_a_single_intervention_and_a_clean_conflict(db, api):
    client, headers = api
    from test_general_service_delivery import create_order, general_equipment, sign_reception

    order = create_order(client, headers, operational_category="general_service")
    equipment = general_equipment(client, headers, order["id"])
    assert sign_reception(client, headers, order["id"]).status_code == 200
    barrier = Barrier(2)

    def create():
        barrier.wait()
        return client.post(report_url(order["id"], equipment["id"]), json={"report_type": "installation"}, headers=headers).status_code

    with ThreadPoolExecutor(max_workers=2) as pool:
        codes = sorted(future.result() for future in [pool.submit(create), pool.submit(create)])
    assert codes == [201, 409], codes
    assert db.rows("SELECT count(*) FROM technical_reports") == [(1,)]
    assert db.rows("SELECT count(*) FROM technical_interventions") == [(1,)], "ninguna intervención huérfana"
    assert db.rows("SELECT count(*) FROM technical_reports r JOIN technical_interventions i ON i.id = r.intervention_id AND i.folio = r.folio") == [(1,)]


# --------------------------------------------------------------- SG-4J-A2 sobre PostgreSQL real

def _close(client, headers, order):
    return client.post(f"/api/mobile/v1/technician/lab-work-orders/{order['id']}/complete", headers=headers)


def test_cancelled_historical_intervention_with_its_own_report_never_blocks_close_or_package(db, api):
    client, headers = api
    order, [equipment], [report] = build_delivered(client, headers, count=1)
    with db.engine.begin() as connection:
        # Segunda intervención cancelada del mismo equipo con una revisión histórica no vigente
        # (el índice parcial heredado sólo permite una revisión VIGENTE por equipo).
        connection.execute(text(
            "INSERT INTO technical_interventions (lab_equipment_id, intervention_type, folio, status) "
            "SELECT lab_equipment_id, intervention_type, 'MYC-IN10-26-9301', 'cancelled' FROM technical_interventions"
        ))
        connection.execute(text(
            "INSERT INTO technical_reports (lab_equipment_id, intervention_id, report_type, folio, status, capture_values, "
            "report_schema_version, revision_number, is_current) "
            "SELECT lab_equipment_id, (SELECT id FROM technical_interventions WHERE folio = 'MYC-IN10-26-9301'), report_type, "
            "'MYC-IN10-26-9302', 'cancelled', capture_values, report_schema_version, 1, false FROM technical_reports WHERE id = :id"
        ), {"id": report["id"]})
    assert _close(client, headers, order).status_code == 200
    package = client.get(f"/api/mobile/v1/technician/lab-work-orders/{order['id']}/package", headers=headers)
    assert package.status_code == 200
    import io

    from pypdf import PdfReader

    text_pages = "\n".join(page.extract_text() for page in PdfReader(io.BytesIO(package.content)).pages)
    assert "MYC-IN10-26-9302" not in text_pages and report["folio"] in text_pages


def test_voided_delivery_keeps_its_links_and_blocks_close_in_postgres(db, api):
    client, headers = api
    order, equipments, reports = build_delivered(client, headers, count=2)
    with db.engine.begin() as connection:  # anulación oficial requiere permiso administrativo; se aplica el estado persistido
        connection.execute(text("UPDATE lab_work_order_deliveries SET status = 'voided'"))
    assert db.rows("SELECT count(*) FROM technical_intervention_deliveries") == [(2,)], "los vínculos se conservan"
    response = _close(client, headers, order)
    assert response.status_code == 409 and response.json()["detail"]["code"] == "TECHNICAL_REPORT_REVISION_REQUIRED"


def test_documentary_consistency_after_the_full_flow(db, api):
    client, headers = api
    build_delivered(client, headers, count=3)
    assert db.rows(
        "SELECT count(*) FROM technical_intervention_deliveries l JOIN technical_reports r ON r.id = l.technical_report_id "
        "WHERE r.intervention_id <> l.intervention_id OR (r.document_snapshot::json->'delivery'->>'delivery_id')::int <> l.delivery_id"
    ) == [(0,)]
    assert db.rows("SELECT count(*) FROM technical_interventions i WHERE NOT EXISTS (SELECT 1 FROM technical_reports r WHERE r.intervention_id = i.id)") == [(0,)]
    assert db.rows("SELECT count(*) FROM technical_interventions WHERE status <> 'completed'") == [(0,)]


def test_concurrent_finalize_is_serialized_and_links_the_report_once(db, api):
    client, headers = api
    order, [equipment], [report] = order_with_reports(client, headers, count=1)
    finalize(client, headers, order, equipment)
    assert deliver(client, headers, order).status_code == 201
    barrier = Barrier(2)

    def run():
        barrier.wait()
        return client.post(report_url(order["id"], equipment["id"], "/finalize"), headers=headers).status_code

    with ThreadPoolExecutor(max_workers=2) as pool:
        codes = [future.result() for future in [pool.submit(run), pool.submit(run)]]
    assert codes == [200, 200], codes  # el segundo devuelve el documento ya generado
    assert db.rows("SELECT count(*) FROM technical_intervention_deliveries WHERE technical_report_id IS NOT NULL") == [(1,)]
    assert len(db.rows("SELECT DISTINCT final_pdf_sha256 FROM technical_reports")) == 1


def test_concurrent_deliveries_of_the_same_equipment_yield_one_delivery_and_one_link(db, api):
    client, headers = api
    order, [equipment], _ = order_with_reports(client, headers, count=1)
    finalize(client, headers, order, equipment)
    barrier = Barrier(2)

    def run():
        barrier.wait()
        return deliver(client, headers, order).status_code

    with ThreadPoolExecutor(max_workers=2) as pool:
        codes = sorted(future.result() for future in [pool.submit(run), pool.submit(run)])
    assert codes == [201, 409], codes
    assert db.rows("SELECT count(*) FROM lab_work_order_deliveries") == [(1,)]
    assert db.rows("SELECT count(*) FROM technical_intervention_deliveries") == [(1,)]


# --------------------------------------------------------------- SG-4J-A3: varias intervenciones por equipo

CLONE_INTERVENTION = (
    "INSERT INTO technical_interventions (lab_equipment_id, intervention_type, folio, status) "
    "SELECT lab_equipment_id, intervention_type, :folio, 'open' FROM technical_interventions WHERE id = :source"
)
CLONE_REPORT = (
    "INSERT INTO technical_reports (lab_equipment_id, intervention_id, report_type, folio, status, capture_values, document_snapshot, "
    "report_schema_version, performed_by_user_id, performed_by_name_snapshot, performed_at, client_conformity_text_snapshot, "
    "revision_number, is_current, supersedes_report_id, pdf_renderer_version, final_pdf_path, final_pdf_sha256, final_pdf_generated_at, completed_at) "
    "SELECT lab_equipment_id, :intervention, report_type, :folio, status, capture_values, document_snapshot, report_schema_version, "
    "performed_by_user_id, performed_by_name_snapshot, performed_at, client_conformity_text_snapshot, :revision, :current, :supersedes, "
    "pdf_renderer_version, final_pdf_path, final_pdf_sha256, final_pdf_generated_at, completed_at FROM technical_reports WHERE id = :source "
    "RETURNING id"
)


def second_intervention(db, source_report_id: int, folio: str, *, link_delivery: bool = True) -> tuple[int, int]:
    """Segunda intervención del MISMO equipo y tipo con su propio reporte vigente
    (idéntico en PDF/snapshot al original) y el mismo vínculo de entrega."""
    with db.engine.begin() as connection:
        source_intervention = connection.execute(
            text("SELECT intervention_id FROM technical_reports WHERE id = :id"), {"id": source_report_id}
        ).scalar()
        new_intervention = connection.execute(
            text(CLONE_INTERVENTION + " RETURNING id"), {"folio": folio, "source": source_intervention}
        ).scalar()
        new_report = connection.execute(text(CLONE_REPORT), {
            "intervention": new_intervention, "folio": folio, "revision": 1, "current": True, "supersedes": None, "source": source_report_id,
        }).scalar()
        connection.execute(text("UPDATE technical_interventions SET status = 'completed' WHERE id = :id"), {"id": new_intervention})
        if link_delivery:
            connection.execute(text(
                "INSERT INTO technical_intervention_deliveries (intervention_id, delivery_id, delivery_item_id, technical_report_id) "
                "SELECT :intervention, delivery_id, delivery_item_id, :report FROM technical_intervention_deliveries "
                "WHERE intervention_id = :source"
            ), {"intervention": new_intervention, "report": new_report, "source": source_intervention})
    return new_intervention, new_report


def test_two_interventions_of_the_same_equipment_and_type_hold_distinct_current_reports(db, api):
    client, headers = api
    order, [equipment], [report] = build_delivered(client, headers, count=1)
    new_intervention, new_report = second_intervention(db, report["id"], "MYC-IN10-26-9401")
    assert db.rows(
        "SELECT i.intervention_type, count(*), count(DISTINCT i.folio), sum(CASE WHEN r.is_current THEN 1 ELSE 0 END) "
        "FROM technical_interventions i JOIN technical_reports r ON r.intervention_id = i.id GROUP BY i.intervention_type"
    ) == [("installation", 2, 2, 2)], "mismo tipo, folios distintos, dos vigentes en el mismo equipo"
    with pytest.raises(IntegrityError):  # el folio institucional sigue siendo único por intervención
        with db.engine.begin() as connection:
            connection.execute(text(CLONE_INTERVENTION), {"folio": "MYC-IN10-26-9401", "source": new_intervention})


def test_r1_and_r2_of_one_intervention_share_the_institutional_folio_but_not_current_state_or_revision(db, api):
    client, headers = api
    order, [equipment], [report] = build_delivered(client, headers, count=1)
    intervention = db.rows("SELECT intervention_id FROM technical_reports")[0][0]
    with db.engine.begin() as connection:
        connection.execute(text("UPDATE technical_reports SET is_current = false WHERE id = :id"), {"id": report["id"]})
        connection.execute(text(CLONE_REPORT), {
            "intervention": intervention, "folio": report["folio"], "revision": 2, "current": True, "supersedes": report["id"], "source": report["id"],
        })
    assert db.rows("SELECT count(*), count(DISTINCT folio) FROM technical_reports") == [(2, 1)], "R1 y R2 comparten folio"
    with pytest.raises(IntegrityError):  # una sola vigente por intervención
        with db.engine.begin() as connection:
            connection.execute(text(CLONE_REPORT), {
                "intervention": intervention, "folio": report["folio"], "revision": 3, "current": True, "supersedes": None, "source": report["id"],
            })
    with pytest.raises(IntegrityError):  # revisión duplicada
        with db.engine.begin() as connection:
            connection.execute(text(CLONE_REPORT), {
                "intervention": intervention, "folio": report["folio"], "revision": 2, "current": False, "supersedes": None, "source": report["id"],
            })
    with pytest.raises(IntegrityError):  # sin bifurcaciones: R1 ya tiene sucesora
        with db.engine.begin() as connection:
            connection.execute(text(CLONE_REPORT), {
                "intervention": intervention, "folio": report["folio"], "revision": 3, "current": False, "supersedes": report["id"], "source": report["id"],
            })


def test_structural_integrity_rejects_orphans_cross_equipment_and_cross_intervention_links(db, api):
    client, headers = api
    order, [first, second], [r1, r2] = build_delivered(client, headers, count=2)
    i1, i2 = [row[0] for row in db.rows("SELECT id FROM technical_interventions ORDER BY id")]
    with pytest.raises(IntegrityError):  # intervention_id NOT NULL
        with db.engine.begin() as connection:
            connection.execute(text("UPDATE technical_reports SET intervention_id = NULL WHERE id = :id"), {"id": r1["id"]})
    with pytest.raises(IntegrityError):  # el reporte debe tener el mismo equipo que su intervención
        with db.engine.begin() as connection:
            connection.execute(text("UPDATE technical_reports SET intervention_id = :other WHERE id = :id"), {"other": i2, "id": r1["id"]})
    with pytest.raises(IntegrityError):  # una revisión no puede superseder a un reporte de otra intervención
        with db.engine.begin() as connection:
            connection.execute(text("UPDATE technical_reports SET supersedes_report_id = :other WHERE id = :id"), {"other": r1["id"], "id": r2["id"]})


def test_legacy_endpoints_resolve_the_principal_intervention_deterministically(db, api):
    client, headers = api
    order, [equipment], [report] = build_delivered(client, headers, count=1)
    second_intervention(db, report["id"], "MYC-IN10-26-9402")
    for _ in range(3):  # siempre la de menor id, nunca al azar
        body = client.get(report_url(order["id"], equipment["id"]), headers=headers).json()
        assert body["id"] == report["id"] and body["folio"] == report["folio"]


def test_close_and_package_cover_every_mandatory_intervention_with_one_voucher(db, api):
    client, headers = api
    order, [equipment], [report] = build_delivered(client, headers, count=1)
    second_intervention(db, report["id"], "MYC-IN10-26-9403")
    close = _close(client, headers, order)
    assert close.status_code == 200, close.text
    package = client.get(f"/api/mobile/v1/technician/lab-work-orders/{order['id']}/package", headers=headers)
    assert package.status_code == 200, package.text
    import io

    from pypdf import PdfReader

    texts = [page.extract_text() for page in PdfReader(io.BytesIO(package.content)).pages]
    assert sum("REPORTE DE INSTALACIÓN" in text for text in texts) == 2, "un reporte por intervención obligatoria"
    assert sum("ACUSE DE ENTREGA DE EQUIPOS" in text for text in texts) == 1, "un solo acuse"
    # La entrega anulada bloquea el cierre de TODAS las intervenciones que respaldaba.
    with db.engine.begin() as connection:
        connection.execute(text("UPDATE lab_work_order_deliveries SET status = 'voided'"))
    blocked = client.get(f"/api/mobile/v1/technician/lab-work-orders/{order['id']}/package", headers=headers)
    assert blocked.status_code == 409 and blocked.json()["detail"]["code"] == "TECHNICAL_REPORT_REVISION_REQUIRED"
    assert len(blocked.json()["detail"]["items"]) == 2


def test_downgrade_is_refused_while_data_depends_on_the_new_structure_and_then_succeeds_without_losing_documents(db, api):
    client, headers = api
    order, [equipment], [report] = build_delivered(client, headers, count=1)
    documents = db.rows(DOCUMENT_SQL)
    second_intervention(db, report["id"], "MYC-IN10-26-9404")  # dos vigentes en el equipo
    with pytest.raises(Exception, match="varias intervenciones vigentes"):
        db.alembic("downgrade", INTERVENTIONS_HEAD)
    assert db.revision() == NEW_HEAD, "el downgrade abortado no cambió nada"
    with db.engine.begin() as connection:  # R1/R2 con folio compartido también lo impide
        connection.execute(text("DELETE FROM technical_intervention_deliveries WHERE intervention_id <> (SELECT intervention_id FROM technical_reports WHERE id = :id)"), {"id": report["id"]})
        connection.execute(text("DELETE FROM technical_reports WHERE id <> :id"), {"id": report["id"]})
        connection.execute(text("DELETE FROM technical_interventions WHERE id <> (SELECT intervention_id FROM technical_reports WHERE id = :id)"), {"id": report["id"]})
        connection.execute(text("UPDATE technical_reports SET is_current = false WHERE id = :id"), {"id": report["id"]})
        connection.execute(text(CLONE_REPORT), {
            "intervention": db.rows("SELECT intervention_id FROM technical_reports")[0][0], "folio": report["folio"], "revision": 2,
            "current": True, "supersedes": report["id"], "source": report["id"],
        })
    with pytest.raises(Exception, match="comparten folio"):
        db.alembic("downgrade", INTERVENTIONS_HEAD)
    with db.engine.begin() as connection:
        connection.execute(text("UPDATE technical_reports SET supersedes_report_id = NULL WHERE revision_number = 2"))
        connection.execute(text("DELETE FROM technical_reports WHERE revision_number = 2"))
        connection.execute(text("UPDATE technical_reports SET is_current = true"))
    db.alembic("downgrade", INTERVENTIONS_HEAD)
    assert db.revision() == INTERVENTIONS_HEAD
    assert db.rows(DOCUMENT_SQL) == documents, "PDFs, hashes, folios y snapshots intactos tras revertir"
    db.alembic("upgrade", "head")
    assert db.rows(DOCUMENT_SQL) == documents
