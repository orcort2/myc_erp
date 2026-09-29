"""ETS de calibración MYC Mobile: proyección READ-ONLY, acciones administrativas
ERP sobre el dominio LAB, handoff PDF-only a Captura y convergencia del vínculo.

MYC Mobile es la única interfaz de escritura técnica. Estas pruebas verifican
que el ERP sólo consulta y gobierna mediante los servicios de dominio LAB.
"""
from __future__ import annotations

from datetime import date, datetime, timezone
from decimal import Decimal
from hashlib import sha256

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event, func, select
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

import app.models  # noqa: F401
from app.core.config import settings
from app.core.db import Base, get_db
from app.core.security import create_access_token
from app.main import app
from app.models.catalog_item import CatalogItem
from app.models.certificate import Certificate
from app.models.client import Client
from app.models.equipment import Equipment
from app.models.field_sheet import FieldSheet
from app.models.folio_sequence import InstitutionalFolioSequence
from app.models.lab_work_order import (
    LabWorkOrder,
    LabWorkOrderEquipment,
    LabWorkOrderSignatureSession,
)
from app.models.quotation import Quotation, QuotationItem
from app.models.service_order import ServiceWorkOrder
from app.models.service_order_lab_link import ServiceOrderLabLink
from app.models.user import Role, User
from app.schemas.service_order import ServiceOrderCreate
from app.services import service_order_lab_links
from app.services.quotations import _build_operational_snapshot
from app.services.service_orders import create_service_order

ROLES = ("Administrador", "Calidad", "Tecnico", "Captura", "Comercial", "Finanzas")


def _mobile_ets(db, client, user, folio):
    item = CatalogItem(
        item_type="service", service_kind="simple", commodity="calibration", category="Calibracion",
        operational_category="calibration", name="Calibración", origin_price=Decimal("100"),
        origin_currency="MXN", exchange_rate=Decimal("1"), margin_percent=Decimal("0"),
        final_price_mxn=Decimal("100"), tax_object="iva_16", tax_rate=Decimal("16"),
        calibration_scope="traceable", service_type="traceable",
    )
    db.add(item)
    db.flush()
    quote = Quotation(
        folio=folio, client_id=client.id, advisor_id=user.id, status="accepted",
        subtotal=Decimal("100"), tax_total=Decimal("16"), total=Decimal("116"),
    )
    quote.items = [QuotationItem(
        catalog_item_id=item.id, service_name=item.name, operational_category="calibration",
        commodity="calibration", quantity=2, unit_price=Decimal("100"), discount_percent=Decimal("0"),
        tax_rate=Decimal("16"), tax_total=Decimal("16"), total=Decimal("100"),
        operational_snapshot=_build_operational_snapshot(db, item),
    )]
    db.add(quote)
    db.commit()
    return create_service_order(
        db, ServiceOrderCreate(client_id=client.id, quotation_id=quote.id, advisor_id=user.id),
        user_id=user.id,
    )


class Lab:
    """Constructor mínimo de un grupo LAB real (filas de dominio, sin mocks)."""

    def __init__(self, db, user, storage):
        self.db, self.user, self.storage = db, user, storage

    def work_order(self, folio, *, root=None, status="completed", sequence=1):
        order = LabWorkOrder(
            folio=folio, sequence_number=sequence, created_by_user_id=self.user.id,
            reception_date=date(2026, 9, 1), client_name="Cliente Ejemplo SA", address="Calle 1",
            status=status, workflow_mode="group",
        )
        self.db.add(order)
        self.db.flush()
        order.root_work_order_id = root.id if root else order.id
        if root is not None:
            order.signature_session_id = root.signature_session_id
        elif status in {"completed", "partially_closed", "received_signed", "in_progress", "ready_to_close"}:
            session = LabWorkOrderSignatureSession(
                root_work_order_id=order.root_work_order_id, signed_by_user_id=self.user.id,
                signed_at=datetime.now(timezone.utc),
            )
            self.db.add(session)
            self.db.flush()
            order.signature_session_id = session.id
        self.db.flush()
        return order

    def equipment(self, order, position, *, folio="auto", folio_status="reserved",
                  sheet_status="completed", final_pdf=True, active=True):
        certificate_folio = f"MYCT-09-2026-{order.folio}{position}" if folio == "auto" else folio
        equipment = LabWorkOrderEquipment(
            work_order_id=order.id, position=position, instrument=f"Termómetro {position}",
            brand="Fluke", model="51-II", identification=f"TER-{order.folio}-{position}",
            serial_number=f"SN{order.folio}{position}", is_good_condition=True,
            service_type="traceable", certificate_folio=certificate_folio, folio_status=folio_status,
            is_active=active,
        )
        self.db.add(equipment)
        self.db.flush()
        if sheet_status is not None:
            sheet = FieldSheet(
                lab_equipment_id=equipment.id, status=sheet_status, template_key="general",
                revision_number=1, is_current=True, capture_values={"instrument": equipment.instrument},
                results="valor técnico secreto", lab_signature_session_id=order.signature_session_id,
            )
            self.db.add(sheet)
            self.db.flush()
            if final_pdf:
                content = f"%PDF-1.4 hoja {sheet.id}".encode()
                relative = f"field-sheets/{sheet.id}/final/renderer-1.pdf"
                path = self.storage / relative
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_bytes(content)
                sheet.final_pdf_path = relative
                sheet.final_pdf_sha256 = sha256(content).hexdigest()
                sheet.final_pdf_generated_at = datetime.now(timezone.utc)
        self.db.flush()
        return equipment


@pytest.fixture()
def ctx(tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "storage_root", str(tmp_path))
    engine = create_engine(
        "sqlite+pysqlite:///:memory:", connect_args={"check_same_thread": False}, poolclass=StaticPool,
    )

    @event.listens_for(engine, "connect")
    def foreign_keys(connection, _):
        connection.execute("PRAGMA foreign_keys=ON")

    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine, expire_on_commit=False)
    with factory() as db:
        roles = {name: Role(name=name, description=name) for name in ROLES}
        db.add_all(roles.values())
        db.flush()
        users = {}
        for name, role in roles.items():
            users[name] = User(
                username=f"u-{name}", email=f"{name}@example.test", full_name=name,
                hashed_password="unused", account_type="internal", status="active", is_active=True,
                role_id=role.id, roles=[role],
            )
        db.add_all(users.values())
        client = Client(legal_name="Cliente Ejemplo SA")
        db.add(client)
        db.commit()
        order = _mobile_ets(db, client, users["Comercial"], "COT-26-0100")
        other = _mobile_ets(db, client, users["Comercial"], "COT-26-0101")
        lab = Lab(db, users["Administrador"], tmp_path)
        root = lab.work_order(6438)
        child = lab.work_order(6439, root=root, sequence=2)
        e1 = lab.equipment(root, 1)
        e2 = lab.equipment(child, 1)
        retired = lab.equipment(child, 2, active=False)
        db.commit()
        ids = {
            "order": order.id, "other": other.id, "root": root.id, "child": child.id,
            "e1": e1.id, "e2": e2.id, "retired": retired.id,
            "users": {name: user.id for name, user in users.items()},
        }

    def override_db():
        with factory() as session:
            yield session

    previous = app.dependency_overrides.copy()
    app.dependency_overrides[get_db] = override_db
    http = TestClient(app)
    headers = {
        name: {"Authorization": f"Bearer {create_access_token(str(user_id))}"}
        for name, user_id in ids["users"].items()
    }
    try:
        yield {**ids, "http": http, "factory": factory, "headers": headers, "storage": tmp_path}
    finally:
        http.close()
        app.dependency_overrides.clear()
        app.dependency_overrides.update(previous)


def _link(ctx, work_order_id=None, order_key="order"):
    with ctx["factory"]() as db:
        return service_order_lab_links.link_lab_group(
            db, ctx[order_key], work_order_id or ctx["root"], user_id=ctx["users"]["Comercial"],
        ).id


def _counts(db):
    return {
        model.__name__: db.scalar(select(func.count(model.id)))
        for model in (Equipment, ServiceWorkOrder, Certificate, FieldSheet, InstitutionalFolioSequence)
    }


def _url(ctx, suffix="", order_key="order"):
    return f"/api/service-orders/{ctx[order_key]}{suffix}"


# --------------------------------------------------------------- PROJECTION


def test_projection_without_link_is_empty_and_readable(ctx):
    response = ctx["http"].get(_url(ctx, "/mobile-execution"), headers=ctx["headers"]["Captura"])
    assert response.status_code == 200
    assert response.json() == {
        "source": "lab", "service_order_id": ctx["order"], "linked": False, "link_id": None,
        "root_work_order_id": None, "root_folio": None, "work_orders": [],
    }


def test_projection_resolves_root_full_group_and_active_equipment_only(ctx):
    _link(ctx, ctx["child"])  # vincular por una hija resuelve la raíz
    body = ctx["http"].get(_url(ctx, "/mobile-execution"), headers=ctx["headers"]["Comercial"]).json()
    assert body["linked"] is True
    assert body["root_work_order_id"] == ctx["root"] and body["root_folio"] == 6438
    assert [(wo["folio"], wo["is_root"]) for wo in body["work_orders"]] == [(6438, True), (6439, False)]
    child = body["work_orders"][1]
    assert [item["id"] for item in child["equipment"]] == [ctx["e2"]]  # tombstone excluido
    assert child["retired_equipment_count"] == 1
    equipment = child["equipment"][0]
    assert equipment["certificate_folio"] == "MYCT-09-2026-64391"
    assert equipment["folio_status"] == "reserved"
    assert {"instrument", "brand", "model", "serial_number", "identification", "service_type"} <= set(equipment)
    sheet = equipment["field_sheet"]
    assert sheet["status"] == "completed" and sheet["revision_number"] == 1 and sheet["has_final_pdf"] is True
    # El resumen nunca incluye valores técnicos.
    assert "valor técnico secreto" not in str(body)
    assert "results" not in sheet and "capture_values" not in sheet


def test_projection_reads_never_create_or_copy_erp_technical_rows(ctx):
    _link(ctx)
    with ctx["factory"]() as db:
        before = _counts(db)
    http, headers = ctx["http"], ctx["headers"]["Administrador"]
    assert http.get(_url(ctx, "/mobile-execution"), headers=headers).status_code == 200
    assert http.get(_url(ctx, f"/mobile-execution/equipment/{ctx['e1']}/field-sheet"), headers=headers).status_code == 200
    assert http.get(_url(ctx, "/capture-package-summary"), headers=headers).status_code == 200
    with ctx["factory"]() as db:
        assert _counts(db) == before


def test_field_sheet_detail_is_read_only_and_scoped_to_linked_group(ctx):
    _link(ctx)
    http = ctx["http"]
    detail = http.get(
        _url(ctx, f"/mobile-execution/equipment/{ctx['e2']}/field-sheet"), headers=ctx["headers"]["Calidad"],
    )
    assert detail.status_code == 200
    body = detail.json()
    assert body["work_order_folio"] == 6439
    assert body["field_sheet"]["results"] == "valor técnico secreto"
    assert [item["revision_number"] for item in body["revisions"]] == [1]
    # Tombstone y equipo ajeno al grupo vinculado no son accesibles.
    assert http.get(_url(ctx, f"/mobile-execution/equipment/{ctx['retired']}/field-sheet"),
                    headers=ctx["headers"]["Calidad"]).status_code == 404
    other = http.get(_url(ctx, f"/mobile-execution/equipment/{ctx['e1']}/field-sheet", "other"),
                     headers=ctx["headers"]["Calidad"])
    assert other.status_code == 409 and other.json()["detail"]["code"] == "LAB_LINK_REQUIRED"
    # Comercial/Finanzas no leen valores técnicos (field_sheets.read).
    assert http.get(_url(ctx, f"/mobile-execution/equipment/{ctx['e2']}/field-sheet"),
                    headers=ctx["headers"]["Finanzas"]).status_code == 403


def test_final_pdf_is_served_frozen_and_hash_validated(ctx):
    _link(ctx)
    with ctx["factory"]() as db:
        sheet = db.scalar(select(FieldSheet).where(FieldSheet.lab_equipment_id == ctx["e1"]))
        sheet_id, path = sheet.id, ctx["storage"] / sheet.final_pdf_path
    url = _url(ctx, f"/mobile-execution/field-sheets/{sheet_id}/pdf")
    response = ctx["http"].get(url, headers=ctx["headers"]["Captura"])
    assert response.status_code == 200
    assert response.headers["content-type"] == "application/pdf"
    assert response.content == path.read_bytes()
    path.write_bytes(b"alterado")
    assert ctx["http"].get(url, headers=ctx["headers"]["Captura"]).status_code == 409


# ------------------------------------------------------------------- BRIDGE


def test_link_from_erp_and_from_mobile_converge_on_service_order_lab_link(ctx):
    # A. desde ERP
    erp_link = ctx["http"].post(
        _url(ctx, "/lab-link"), json={"work_order_id": ctx["root"]}, headers=ctx["headers"]["Comercial"],
    )
    assert erp_link.status_code == 200
    # B. desde Mobile: el núcleo compartido usado por la creación atómica.
    with ctx["factory"]() as db:
        other_root = Lab(db, db.get(User, ctx["users"]["Administrador"]), ctx["storage"]).work_order(6500)
        db.commit()
        service_order_lab_links.link_lab_root_in_transaction(
            db, ctx["other"], other_root, user_id=ctx["users"]["Tecnico"], origin="mobile_lab_creation",
        )
        db.commit()
        links = db.scalars(select(ServiceOrderLabLink).order_by(ServiceOrderLabLink.id)).all()
        assert [(link.service_order_id, link.status) for link in links] == [
            (ctx["order"], "active"), (ctx["other"], "active"),
        ]
    projection = ctx["http"].get(_url(ctx, "/mobile-execution", "other"), headers=ctx["headers"]["Comercial"]).json()
    assert projection["linked"] is True and projection["root_folio"] == 6500


def test_replace_and_unlink_preserve_history_and_projection_follows_active_link(ctx):
    http, headers = ctx["http"], ctx["headers"]["Comercial"]
    assert http.post(_url(ctx, "/lab-link"), json={"work_order_id": ctx["root"]}, headers=headers).status_code == 200
    with ctx["factory"]() as db:
        new_root = Lab(db, db.get(User, ctx["users"]["Administrador"]), ctx["storage"]).work_order(6600)
        db.commit()
        new_root_id = new_root.id
    replaced = http.post(_url(ctx, "/lab-link/replace"), json={"work_order_id": new_root_id, "reason": "Corrección"}, headers=headers)
    assert replaced.status_code == 200
    assert http.get(_url(ctx, "/mobile-execution"), headers=headers).json()["root_folio"] == 6600
    assert http.post(_url(ctx, "/lab-link/unlink"), json={"reason": "Baja"}, headers=headers).status_code == 200
    assert http.get(_url(ctx, "/mobile-execution"), headers=headers).json()["linked"] is False
    history = http.get(_url(ctx, "/lab-link/history"), headers=headers).json()
    assert [item["status"] for item in history] == ["unlinked", "replaced"]
