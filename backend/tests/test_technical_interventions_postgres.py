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
NEW_HEAD = "a4b7c1d9e3f2"

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
