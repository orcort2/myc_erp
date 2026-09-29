"""MYC Mobile ↔ ERP calibration ETS: read-only candidates and atomic create + link."""

import os
import uuid
from concurrent.futures import ThreadPoolExecutor
from decimal import Decimal
from threading import Barrier

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event, func, select, text
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

import app.models  # noqa: F401
from app.core.db import Base, get_db
from app.core.security import create_access_token
from app.main import app
from app.models.audit_log import AuditLog
from app.models.catalog_item import CatalogItem
from app.models.client import Client
from app.models.folio_sequence import InstitutionalFolioSequence
from app.models.lab_work_order import LabWorkOrder, LabWorkOrderGroupRequest
from app.models.quotation import Quotation, QuotationItem
from app.models.service_order import ServiceOrder, ServiceOrderItem
from app.models.service_order_lab_link import ServiceOrderLabLink
from app.models.user import Role, User
from app.schemas.service_order import ServiceOrderCreate
from app.services import lab_erp_calibration, service_order_lab_links
from app.services.quotations import _build_operational_snapshot
from app.services.service_orders import create_service_order

BASE = "/api/mobile/v1/technician/lab-work-orders"


def _catalog(db, category):
    item = CatalogItem(
        item_type="service", service_kind="simple", commodity=category, category=category,
        operational_category=category, name=f"Servicio {category}", origin_price=Decimal("100"),
        origin_currency="MXN", exchange_rate=Decimal("1"), margin_percent=Decimal("0"),
        final_price_mxn=Decimal("100"), tax_object="iva_16", tax_rate=Decimal("16"),
        calibration_scope="traceable" if category == "calibration" else None,
        service_type="traceable" if category == "calibration" else None,
    )
    db.add(item)
    db.flush()
    return item


def _ets(db, client, user, folio, categories=("calibration",), *, status="accepted", quantity=3):
    quote = Quotation(
        folio=folio, client_id=client.id, advisor_id=user.id, status=status,
        subtotal=Decimal("100"), tax_total=Decimal("16"), total=Decimal("116"),
    )
    quote.items = [
        QuotationItem(
            catalog_item_id=item.id, service_name=item.name,
            operational_category=item.operational_category, commodity=item.commodity,
            quantity=quantity, unit_price=Decimal("100"), discount_percent=Decimal("0"),
            tax_rate=Decimal("16"), tax_total=Decimal("16"), total=Decimal("100"),
            operational_snapshot=_build_operational_snapshot(db, item),
        )
        for item in (_catalog(db, category) for category in categories)
    ]
    db.add(quote)
    db.commit()
    return create_service_order(
        db, ServiceOrderCreate(client_id=client.id, quotation_id=quote.id, advisor_id=user.id),
        user_id=user.id,
    )


def _seed(factory):
    with factory() as db:
        roles = {name: Role(name=name, description=name) for name in ("Tecnico", "Comercial", "Cliente")}
        db.add_all(roles.values())
        db.flush()
        tech = User(
            username="mobile-tech", email="mobile-tech@example.test", full_name="Técnico Mobile",
            hashed_password="unused", account_type="internal", status="active", is_active=True,
            role_id=roles["Tecnico"].id, roles=[roles["Tecnico"]],
        )
        commercial = User(
            username="erp-commercial", email="erp-commercial@example.test", full_name="Comercial",
            hashed_password="unused", account_type="internal", status="active", is_active=True,
            role_id=roles["Comercial"].id, roles=[roles["Comercial"]],
        )
        client = Client(legal_name="Metrología Industrial SA", commercial_name="MetroInd")
        other = Client(legal_name="Otro Cliente SA")
        db.add_all([tech, commercial, client, other])
        db.commit()
        orders = {
            "mobile": _ets(db, client, commercial, "COT-26-0001"),
            "mobile_2": _ets(db, client, commercial, "COT-26-0002"),
            "mixed": _ets(db, client, commercial, "COT-26-0003", ("calibration", "maintenance")),
            "waiting": _ets(db, client, commercial, "COT-26-0004", status="waiting"),
            "other_client": _ets(db, other, commercial, "COT-26-0005"),
        }
        historical = ServiceOrder(
            folio="OSMYC-26-01-0077", work_order_number=7077, client_id=client.id,
            quotation_id=None, status="scheduled",
        )
        historical.items = [ServiceOrderItem(service_name="Cal", operational_category="calibration", quantity=1)]
        db.add(historical)
        db.commit()
        ids = {key: order.id for key, order in orders.items()} | {"historical": historical.id}
        return {"tech": tech.id, "commercial": commercial.id, "orders": ids}


@pytest.fixture()
def ctx():
    engine = create_engine(
        "sqlite+pysqlite:///:memory:", connect_args={"check_same_thread": False}, poolclass=StaticPool,
    )

    @event.listens_for(engine, "connect")
    def foreign_keys(connection, _):
        connection.execute("PRAGMA foreign_keys=ON")

    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine, expire_on_commit=False)
    seeded = _seed(factory)

    def override_db():
        with factory() as db:
            yield db

    previous = app.dependency_overrides.copy()
    app.dependency_overrides[get_db] = override_db
    client = TestClient(app)
    token = create_access_token(str(seeded["tech"]), extra_claims={"auth_context": "mobile_internal"})
    try:
        yield {
            **seeded, "http": client, "factory": factory,
            "headers": {"Authorization": f"Bearer {token}"},
        }
    finally:
        client.close()
        app.dependency_overrides.clear()
        app.dependency_overrides.update(previous)
        engine.dispose()


def payload(**extra):
    return {
        "reception_date": "2026-09-29", "client_name": "MetroInd", "address": "Av. 1",
        "purchase_order": "OC-DOCUMENTAL-7", **extra,
    }


def counts(ctx):
    with ctx["factory"]() as db:
        return {
            "lab": db.scalar(select(func.count(LabWorkOrder.id))),
            "links": db.scalar(select(func.count(ServiceOrderLabLink.id))),
            "sequence": db.scalar(select(InstitutionalFolioSequence.next_value).where(
                InstitutionalFolioSequence.document_type == "lab_work_order")),
        }


# 13–15. Candidates: read-only Mobile endpoint, ERP admin endpoint stays closed


def test_candidates_are_only_accepted_active_calibration_only_mobile_ets(ctx):
    response = ctx["http"].get(f"{BASE}/erp-calibration-candidates", params={"q": "cot-26"}, headers=ctx["headers"])
    assert response.status_code == 200, response.text
    by_id = {row["service_order_id"]: row for row in response.json()}
    assert set(by_id) == {ctx["orders"][key] for key in ("mobile", "mobile_2", "other_client")}
    row = by_id[ctx["orders"]["mobile"]]
    assert row["quotation_folio"] == "COT-26-0001"
    assert row["client_name"] == "MetroInd"
    assert row["calibration_item_count"] == 1 and row["calibration_quantity"] == 3
    assert row["available"] is True and row["active_lab_root_id"] is None
    assert not {"total", "subtotal", "unit_price"} & set(row)


@pytest.mark.parametrize("term, expected", [("0001", "mobile"), ("metroind", "mobile"), ("otro cliente", "other_client")])
def test_candidates_search_by_quotation_ets_folio_and_client(ctx, term, expected):
    rows = ctx["http"].get(f"{BASE}/erp-calibration-candidates", params={"q": term}, headers=ctx["headers"]).json()
    assert ctx["orders"][expected] in {row["service_order_id"] for row in rows}
    with ctx["factory"]() as db:
        ets_folio = db.get(ServiceOrder, ctx["orders"]["mobile_2"]).folio
    rows = ctx["http"].get(f"{BASE}/erp-calibration-candidates", params={"q": ets_folio}, headers=ctx["headers"]).json()
    assert [row["service_order_id"] for row in rows] == [ctx["orders"]["mobile_2"]]


def test_candidates_require_two_characters_bounded_limit_and_literal_wildcards(ctx):
    short = ctx["http"].get(f"{BASE}/erp-calibration-candidates", params={"q": "c"}, headers=ctx["headers"])
    assert short.status_code == 422
    too_many = ctx["http"].get(f"{BASE}/erp-calibration-candidates", params={"q": "cot", "limit": 26}, headers=ctx["headers"])
    assert too_many.status_code == 422
    wildcard = ctx["http"].get(f"{BASE}/erp-calibration-candidates", params={"q": "%%"}, headers=ctx["headers"])
    assert wildcard.status_code == 200 and wildcard.json() == []


def test_erp_token_and_client_actor_boundaries(ctx):
    no_token = ctx["http"].get(f"{BASE}/erp-calibration-candidates", params={"q": "cot"})
    assert no_token.status_code == 401
    # The Mobile token cannot use the administrative ERP bridge (401, Phase 1 boundary).
    admin_link = ctx["http"].post(
        f"/api/service-orders/{ctx['orders']['mobile']}/lab-link", json={"work_order_id": 1},
        headers=ctx["headers"],
    )
    assert admin_link.status_code == 401


# 16–19. Legacy creation unchanged; linked creation is one transaction


def test_single_without_service_order_is_legacy(ctx):
    response = ctx["http"].post(BASE, json=payload(), headers=ctx["headers"])
    assert response.status_code == 201, response.text
    assert response.json()["purchase_order"] == "OC-DOCUMENTAL-7"
    assert counts(ctx)["links"] == 0


def test_group_without_service_order_is_legacy(ctx):
    response = ctx["http"].post(f"{BASE}/groups", json=payload(quantity=2), headers=ctx["headers"])
    assert response.status_code == 201, response.text
    assert len(response.json()["related_work_orders"]) == 2
    assert counts(ctx)["links"] == 0


def test_single_with_service_order_creates_order_and_link_atomically(ctx):
    so_id = ctx["orders"]["mobile"]
    response = ctx["http"].post(BASE, json=payload(service_order_id=so_id), headers=ctx["headers"])
    assert response.status_code == 201, response.text
    order_id = response.json()["id"]
    with ctx["factory"]() as db:
        link = db.scalar(select(ServiceOrderLabLink))
        assert (link.service_order_id, link.lab_root_work_order_id, link.status) == (so_id, order_id, "active")
        assert link.linked_by_user_id == ctx["tech"]
        order = db.get(LabWorkOrder, order_id)
        assert order.root_work_order_id == order.id and order.purchase_order == "OC-DOCUMENTAL-7"
        audit = db.scalar(select(AuditLog).where(AuditLog.action == "service_order.lab_group_linked"))
        assert audit.new_values["origin"] == "mobile_lab_creation" and audit.user_id == ctx["tech"]
        assert db.scalar(select(AuditLog).where(AuditLog.action == "lab_work_order.created")) is not None
        assert db.get(ServiceOrder, so_id).work_order_number is None  # still no ERP OT
    rows = ctx["http"].get(f"{BASE}/erp-calibration-candidates", params={"q": "0001"}, headers=ctx["headers"]).json()
    assert rows[0]["available"] is False and rows[0]["active_lab_root_id"] == order_id


def test_group_with_service_order_links_only_the_root(ctx):
    so_id = ctx["orders"]["mobile"]
    response = ctx["http"].post(f"{BASE}/groups", json=payload(quantity=3, service_order_id=so_id), headers=ctx["headers"])
    assert response.status_code == 201, response.text
    with ctx["factory"]() as db:
        members = list(db.scalars(select(LabWorkOrder).order_by(LabWorkOrder.sequence_number)))
        assert len(members) == 3 and {item.root_work_order_id for item in members} == {members[0].id}
        links = list(db.scalars(select(ServiceOrderLabLink)))
        assert len(links) == 1 and links[0].lab_root_work_order_id == members[0].id
        for member in members:  # every sibling resolves to the single link through its root
            assert service_order_lab_links.resolve_lab_root_work_order(db, member.id).id == members[0].id


# 20–23. Conflicts and failures roll back everything, including LAB folios


def test_already_linked_ets_is_409_without_orphan_order_or_consumed_folio(ctx):
    so_id = ctx["orders"]["mobile"]
    assert ctx["http"].post(BASE, json=payload(service_order_id=so_id), headers=ctx["headers"]).status_code == 201
    before = counts(ctx)
    response = ctx["http"].post(f"{BASE}/groups", json=payload(quantity=2, service_order_id=so_id), headers=ctx["headers"])
    assert response.status_code == 409
    assert response.json()["detail"]["code"] == "SERVICE_ORDER_ALREADY_LINKED_TO_LAB"
    assert counts(ctx) == before


@pytest.mark.parametrize("key", ["mixed", "waiting", "historical"])
def test_non_candidate_ets_is_409_and_nothing_is_created(ctx, key):
    before = counts(ctx)
    response = ctx["http"].post(BASE, json=payload(service_order_id=ctx["orders"][key]), headers=ctx["headers"])
    assert response.status_code == 409
    assert response.json()["detail"]["code"] == "SERVICE_ORDER_NOT_MOBILE_CALIBRATION_CANDIDATE"
    assert counts(ctx) == before


def test_missing_ets_is_404(ctx):
    response = ctx["http"].post(BASE, json=payload(service_order_id=999999), headers=ctx["headers"])
    assert response.status_code == 404


def test_unique_index_race_rolls_back_order_and_folio(ctx, monkeypatch):
    """SQLite has no row locks: the partial unique index is the final guard."""
    so_id = ctx["orders"]["mobile"]
    before = counts(ctx)
    real_lock = lab_erp_calibration._lock_candidate

    def lock_then_competitor_links(db, service_order_id):
        order = real_lock(db, service_order_id)
        competitor = LabWorkOrder(
            folio=6999, sequence_number=1, created_by_user_id=ctx["tech"],
            reception_date=order.created_at.date(), client_name="Competidor", status="draft",
        )
        db.add(competitor)
        db.flush()
        competitor.root_work_order_id = competitor.id
        db.execute(ServiceOrderLabLink.__table__.insert().values(
            service_order_id=service_order_id, lab_root_work_order_id=competitor.id, status="active",
            linked_at=order.created_at, linked_by_user_id=ctx["tech"],
        ))
        return order

    monkeypatch.setattr(lab_erp_calibration, "_lock_candidate", lock_then_competitor_links)
    response = ctx["http"].post(BASE, json=payload(service_order_id=so_id), headers=ctx["headers"])
    assert response.status_code == 409
    assert counts(ctx) == before


@pytest.mark.parametrize("failure", ["audit", "commit"])
def test_audit_or_commit_failure_rolls_back_everything(ctx, monkeypatch, failure):
    before = counts(ctx)

    def boom(*_args, **_kwargs):
        raise RuntimeError(f"{failure} failed")

    if failure == "audit":
        monkeypatch.setattr(service_order_lab_links, "write_audit_log", boom)
    else:
        monkeypatch.setattr(lab_erp_calibration, "commit_and_dispatch_notifications", boom)
    client = TestClient(app, raise_server_exceptions=False)
    try:
        response = client.post(
            f"{BASE}/groups", json=payload(quantity=2, service_order_id=ctx["orders"]["mobile"]),
            headers=ctx["headers"],
        )
    finally:
        client.close()
    assert response.status_code == 500
    assert counts(ctx) == before  # no orphan OT, no link, LAB sequence not consumed
    with ctx["factory"]() as db:
        assert db.scalar(select(func.count(AuditLog.id)).where(
            AuditLog.action.in_(("lab_work_order.group_materialized", "service_order.lab_group_linked"))
        )) == 0


# 24–25. Additional OT inherit through the root; external requests unchanged


def test_additional_work_order_inherits_link_without_new_row(ctx):
    so_id = ctx["orders"]["mobile"]
    root_id = ctx["http"].post(BASE, json=payload(service_order_id=so_id), headers=ctx["headers"]).json()["id"]
    for index in range(1, 11):  # LAB only materializes an additional OT for a full OT
        added = ctx["http"].post(f"{BASE}/{root_id}/equipment", headers=ctx["headers"], json={
            "instrument": f"Instrumento {index}", "brand": "MYC", "identification": f"ID-{index}",
            "serial_number": f"SER-{index}", "is_good_condition": True,
        })
        assert added.status_code == 201, added.text
    additional = ctx["http"].post(f"{BASE}/{root_id}/additional", headers=ctx["headers"])
    assert additional.status_code == 201, additional.text
    with ctx["factory"]() as db:
        assert db.scalar(select(func.count(ServiceOrderLabLink.id))) == 1
        added = db.get(LabWorkOrder, additional.json()["id"])
        assert added.root_work_order_id == root_id
        root = service_order_lab_links.resolve_lab_root_work_order(db, added.id)
        assert service_order_lab_links.get_active_lab_link(db, so_id).lab_root_work_order_id == root.id


def test_external_group_request_contract_does_not_accept_service_order(ctx):
    from app.schemas.lab_work_order import LabWorkOrderGroupCreate

    assert "service_order_id" not in LabWorkOrderGroupCreate.model_fields
    with ctx["factory"]() as db:
        assert db.scalar(select(func.count(LabWorkOrderGroupRequest.id))) == 0


def test_existing_order_patch_cannot_change_the_bridge(ctx):
    order_id = ctx["http"].post(BASE, json=payload(), headers=ctx["headers"]).json()["id"]
    response = ctx["http"].patch(
        f"{BASE}/{order_id}", json={"service_order_id": ctx["orders"]["mobile"]}, headers=ctx["headers"],
    )
    assert response.status_code == 422
    assert counts(ctx)["links"] == 0


# 22. Real PostgreSQL race: two creations for the same ETS


@pytest.fixture()
def pg_factory():
    url = os.getenv("ETS_LAB_POSTGRES_TEST_URL")
    if not url:
        pytest.skip("requiere ETS_LAB_POSTGRES_TEST_URL para probar locks PostgreSQL reales")
    schema = f"mobile_cal_{uuid.uuid4().hex}"
    admin = create_engine(url)
    with admin.begin() as connection:
        connection.execute(text(f'CREATE SCHEMA "{schema}"'))
    engine = create_engine(url, connect_args={"options": f"-csearch_path={schema}"})
    Base.metadata.create_all(engine)
    try:
        yield sessionmaker(bind=engine, expire_on_commit=False)
    finally:
        engine.dispose()
        with admin.begin() as connection:
            connection.execute(text(f'DROP SCHEMA "{schema}" CASCADE'))
        admin.dispose()


def test_postgresql_concurrent_creations_leave_one_linked_group(pg_factory):
    seeded = _seed(pg_factory)
    so_id = seeded["orders"]["mobile"]
    barrier = Barrier(2)

    def create(index):
        from app.schemas.lab_work_order import LabWorkOrderGroupCreate

        with pg_factory() as db:
            user = db.get(User, seeded["tech"])
            barrier.wait()
            try:
                result = lab_erp_calibration.create_linked_work_order_group(
                    db, LabWorkOrderGroupCreate(**payload(quantity=2)), so_id, user,
                )
                return 201, result.id
            except Exception as exc:  # noqa: BLE001 - collected for assertions
                return getattr(exc, "status_code", 500), None

    with ThreadPoolExecutor(max_workers=2) as pool:
        results = sorted(pool.map(create, range(2)))
    assert [status for status, _ in results] == [201, 409]
    with pg_factory() as db:
        links = list(db.scalars(select(ServiceOrderLabLink).where(ServiceOrderLabLink.status == "active")))
        assert len(links) == 1
        assert db.scalar(select(func.count(LabWorkOrder.id))) == 2  # only the winner's group
        assert sorted(db.scalars(select(LabWorkOrder.folio))) == [6400, 6401]
        assert db.scalar(select(InstitutionalFolioSequence.next_value).where(
            InstitutionalFolioSequence.document_type == "lab_work_order")) == 6402
