"""2026 phase: new calibration-only ETS are executed in MYC Mobile.

They reserve no institutional OT folio and create no ServiceWorkOrder; the
ERP rejects productive technical reality for them with a structured 409.
Historical, mixed and non-calibration ETS keep the current productive flow.
"""

from datetime import date
from decimal import Decimal

import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

import app.models  # noqa: F401
from app.core.db import Base, get_db
from app.core.security import create_access_token
from app.main import app
from app.models.catalog_item import CatalogItem
from app.models.client import Client
from app.models.folio_sequence import InstitutionalFolioSequence
from app.models.lab_work_order import LabWorkOrder
from app.models.quotation import Quotation, QuotationItem
from app.models.service_order import ServiceOrder, ServiceOrderItem, ServiceWorkOrder
from app.models.service_order_lab_link import ServiceOrderLabLink
from app.models.user import Role, User
from app.schemas.certificate import CertificateCreate
from app.schemas.equipment import EquipmentCreate
from app.schemas.service_order import ServiceOrderCreate, ServiceOrderUpdate
from app.services import additional_equipment_resolution_operations as additional
from app.services.certificates import create_certificate
from app.services.equipment import create_equipment
from app.services.quotations import _build_operational_snapshot
from app.services.service_order_rebuilds import can_physically_rebuild_service_order
from app.services.service_order_technical_flow import (
    MOBILE_CALIBRATION_FLOW_CODE,
    is_calibration_only,
    is_mobile_calibration_service_order,
)
from app.services.service_orders import (
    confirm_signature_cycle,
    create_service_order,
    update_service_order,
)
from app.services.work_order_pdfs import (
    generate_service_order_work_orders_pdf,
    generate_work_order_pdf,
)


@pytest.fixture()
def ctx():
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine, expire_on_commit=False)
    db = factory()
    role = Role(name="Administrador", description="Admin")
    db.add(role)
    db.flush()
    user = User(
        username="ets-mobile",
        email="ets-mobile@example.test",
        full_name="Actor ETS Mobile",
        hashed_password="unused",
        role_id=role.id,
        roles=[role],
    )
    client = Client(legal_name="Cliente Calibración")
    db.add_all([user, client])
    db.commit()
    yield db, user, client, factory
    db.close()
    engine.dispose()


def _catalog(db, category: str, name: str | None = None) -> CatalogItem:
    item = CatalogItem(
        item_type="service",
        service_kind="simple",
        commodity=category,
        category=category,
        operational_category=category,
        name=name or f"Servicio {category}",
        origin_price=Decimal("100"),
        origin_currency="MXN",
        exchange_rate=Decimal("1"),
        margin_percent=Decimal("0"),
        final_price_mxn=Decimal("100"),
        tax_object="iva_16",
        tax_rate=Decimal("16"),
        calibration_scope="traceable" if category == "calibration" else None,
        service_type="traceable" if category == "calibration" else None,
    )
    db.add(item)
    db.flush()
    return item


def _quotation(db, client, user, catalogs, *, folio="COT-CAL-1", status="accepted", quantity=2):
    quote = Quotation(
        folio=folio,
        client_id=client.id,
        advisor_id=user.id,
        status=status,
        subtotal=Decimal("100"),
        tax_total=Decimal("16"),
        total=Decimal("116"),
    )
    quote.items = [
        QuotationItem(
            catalog_item_id=item.id,
            service_name=item.name,
            operational_category=item.operational_category,
            commodity=item.commodity,
            quantity=quantity,
            unit_price=Decimal("100"),
            discount_percent=Decimal("0"),
            tax_rate=Decimal("16"),
            tax_total=Decimal("16"),
            total=Decimal("100"),
            operational_snapshot=_build_operational_snapshot(db, item),
        )
        for item in catalogs
    ]
    db.add(quote)
    db.commit()
    return quote


def _order_from_quotation(db, client, user, quote) -> ServiceOrder:
    return create_service_order(
        db,
        ServiceOrderCreate(client_id=client.id, quotation_id=quote.id, advisor_id=user.id),
        user_id=user.id,
    )


def _mobile_order(db, client, user, *, folio="COT-CAL-1") -> ServiceOrder:
    quote = _quotation(db, client, user, [_catalog(db, "calibration", f"Cal {folio}")], folio=folio)
    return _order_from_quotation(db, client, user, quote)


def _work_order_sequence(db) -> int | None:
    return db.scalar(
        select(InstitutionalFolioSequence.next_value).where(
            InstitutionalFolioSequence.document_type == "work_order"
        )
    )


def _assert_mobile_conflict(exc: pytest.ExceptionInfo, action: str) -> None:
    assert exc.value.status_code == 409
    assert exc.value.detail["code"] == MOBILE_CALIBRATION_FLOW_CODE
    assert exc.value.detail["action"] == action


# ------------------------------------------------------------------
# 1–4. Calibration-only reserves no OT folio and creates no ServiceWorkOrder
# ------------------------------------------------------------------


def test_new_calibration_only_ets_has_null_work_order_number_and_no_work_orders(ctx):
    db, user, client, _ = ctx
    before = _work_order_sequence(db)
    order = _mobile_order(db, client, user)
    assert order.work_order_number is None
    assert order.work_orders == []
    assert db.scalar(select(func.count(ServiceWorkOrder.id))) == 0
    assert _work_order_sequence(db) == before  # institutional OT sequence untouched
    assert is_mobile_calibration_service_order(order)
    assert order.calibration_flow_managed_by_mobile is True
    assert [item.operational_category for item in order.items] == ["calibration"]


def test_retry_of_accepted_quotation_returns_same_ets_without_new_folios(ctx):
    db, user, client, _ = ctx
    quote = _quotation(db, client, user, [_catalog(db, "calibration")])
    first = _order_from_quotation(db, client, user, quote)
    sequence = _work_order_sequence(db)
    second = _order_from_quotation(db, client, user, quote)
    assert second.id == first.id
    assert db.scalar(select(func.count(ServiceOrder.id))) == 1
    assert db.scalar(select(func.count(ServiceWorkOrder.id))) == 0
    assert _work_order_sequence(db) == sequence


def test_direct_calibration_only_ets_without_quotation_follows_same_policy(ctx):
    db, user, client, _ = ctx
    order = create_service_order(
        db,
        ServiceOrderCreate(
            client_id=client.id,
            items=[{"service_name": "Calibración", "operational_category": "calibration", "quantity": 1}],
        ),
        user_id=user.id,
    )
    assert order.work_order_number is None and order.work_orders == []


def test_several_mobile_ets_coexist_with_null_unique_work_order_number(ctx):
    db, user, client, _ = ctx
    orders = [_mobile_order(db, client, user, folio=f"COT-CAL-{index}") for index in range(3)]
    assert all(order.work_order_number is None for order in orders)
    assert len({order.id for order in orders}) == 3


def test_empty_ets_is_not_calibration_only_and_keeps_productive_flow(ctx):
    db, user, client, _ = ctx
    order = create_service_order(db, ServiceOrderCreate(client_id=client.id), user_id=user.id)
    assert order.work_order_number is not None
    assert len(order.work_orders) == 1
    assert not is_calibration_only([])


# ------------------------------------------------------------------
# 5–10. Historical, other categories and mixed ETS keep the productive flow
# ------------------------------------------------------------------


def test_historical_calibration_ets_with_work_order_number_is_not_reinterpreted(ctx):
    db, user, client, _ = ctx
    order = ServiceOrder(
        folio="OSMYC-26-01-0001", work_order_number=7001, client_id=client.id, status="scheduled",
    )
    order.items = [ServiceOrderItem(service_name="Calibración", operational_category="calibration", quantity=1)]
    db.add(order)
    db.commit()
    db.refresh(order)
    assert is_calibration_only(order.items)
    assert not is_mobile_calibration_service_order(order)
    assert order.calibration_flow_managed_by_mobile is False
    # Productive signatures remain available for the historical ETS.
    updated = update_service_order(
        db, order.id, ServiceOrderUpdate(technician_signed_name="Técnico"), user_id=user.id,
    )
    assert updated.technician_signed_name == "Técnico"


@pytest.mark.parametrize("category", ["maintenance", "repair", "sale", "verification"])
def test_other_categories_keep_current_work_orders(ctx, category):
    db, user, client, _ = ctx
    before = _work_order_sequence(db)
    order = create_service_order(
        db,
        ServiceOrderCreate(
            client_id=client.id,
            items=[{"service_name": f"Servicio {category}", "operational_category": category, "quantity": 3}],
        ),
        user_id=user.id,
    )
    assert order.work_order_number is not None
    assert len(order.work_orders) == 1
    assert order.work_orders[0].work_order_number == order.work_order_number + 1
    assert _work_order_sequence(db) != before
    assert not is_mobile_calibration_service_order(order)


def test_mixed_calibration_quotation_keeps_current_flow_and_is_not_mobile(ctx):
    db, user, client, _ = ctx
    quote = _quotation(
        db, client, user, [_catalog(db, "calibration"), _catalog(db, "maintenance")], folio="COT-MIX-1",
    )
    order = _order_from_quotation(db, client, user, quote)
    assert {item.operational_category for item in order.items} == {"calibration", "maintenance"}
    assert order.work_order_number is not None
    assert len(order.work_orders) >= 1
    assert not is_mobile_calibration_service_order(order)
    assert order.calibration_flow_managed_by_mobile is False


def test_inactive_non_calibration_item_does_not_make_ets_mixed():
    class Item:
        def __init__(self, category, active=True):
            self.operational_category, self.is_active = category, active

    assert is_calibration_only([Item("calibration"), Item("maintenance", active=False)])
    assert not is_calibration_only([Item("calibration"), Item(None)])
    assert not is_calibration_only([Item("calibration", active=False)])


# ------------------------------------------------------------------
# 11–12 + guards. No productive technical reality for a Mobile ETS
# ------------------------------------------------------------------


def test_productive_equipment_creation_is_structured_409(ctx):
    db, user, client, _ = ctx
    order = _mobile_order(db, client, user)
    with pytest.raises(HTTPException) as exc:
        create_equipment(
            db,
            EquipmentCreate(service_order_id=order.id, name="Manómetro", serial_number="S-1"),
            user_id=user.id,
        )
    _assert_mobile_conflict(exc, "equipment.create")


def test_erp_work_order_pdfs_are_structured_409(ctx):
    db, user, client, _ = ctx
    order = _mobile_order(db, client, user)
    for generator in (generate_work_order_pdf, generate_service_order_work_orders_pdf):
        with pytest.raises(HTTPException) as exc:
            generator(db, order.id)
        _assert_mobile_conflict(exc, "work_order_pdf")


def test_erp_technical_signatures_are_structured_409(ctx):
    db, user, client, _ = ctx
    order = _mobile_order(db, client, user)
    with pytest.raises(HTTPException) as exc:
        update_service_order(
            db, order.id, ServiceOrderUpdate(technician_signed_name="Técnico"), user_id=user.id,
        )
    _assert_mobile_conflict(exc, "service_order.technical_signature")
    with pytest.raises(HTTPException) as exc:
        confirm_signature_cycle(db, order.id, user_id=user.id)
    _assert_mobile_conflict(exc, "service_order.signature_cycle")
    # Non-technical administrative edits remain available.
    edited = update_service_order(db, order.id, ServiceOrderUpdate(notes="Seguimiento"), user_id=user.id)
    assert edited.notes == "Seguimiento"


def test_productive_certificate_creation_is_structured_409(ctx):
    db, user, client, _ = ctx
    order = _mobile_order(db, client, user)
    with pytest.raises(HTTPException) as exc:
        create_certificate(
            db,
            CertificateCreate(service_order_id=order.id, equipment_id=1, certificate_type="trazable"),
            user_id=user.id,
        )
    _assert_mobile_conflict(exc, "certificate.create")


def test_additional_equipment_resolution_cannot_create_productive_ot(ctx):
    db, user, client, _ = ctx
    order = _mobile_order(db, client, user)
    with pytest.raises(additional.AdditionalEquipmentOperationError) as exc:
        additional.register_additional_equipment(
            db, resolution_id=1, service_order_id=order.id, reconciliation_id="rec-1",
            request_hash="hash", expected_service_order_status=order.status, catalog_item_id=1,
            service_order_item_id=None, calibration_scope="traceable", name="Equipo", brand=None,
            model=None, serial_number="S-9", internal_id=None, range_or_capacity=None, notes=None,
            preferred_work_order_id=None, allow_new_work_order=True, requires_signature=False,
            requires_commercial_adjustment=False, actor_id=str(user.id),
        )
    assert exc.value.code == MOBILE_CALIBRATION_FLOW_CODE
    assert db.scalar(select(func.count(ServiceWorkOrder.id))) == 0


def test_productive_equipment_and_pdf_http_contracts(ctx):
    db, user, client, factory = ctx
    order = _mobile_order(db, client, user)

    def override_db():
        with factory() as session:
            yield session

    previous = app.dependency_overrides.copy()
    app.dependency_overrides[get_db] = override_db
    headers = {"Authorization": f"Bearer {create_access_token(str(user.id))}"}
    http = TestClient(app)
    try:
        if True:
            read = http.get(f"/api/service-orders/{order.id}", headers=headers)
            assert read.status_code == 200, read.text
            body = read.json()
            assert body["work_order_number"] is None
            assert body["work_orders"] == []
            assert body["calibration_flow_managed_by_mobile"] is True
            pdf = http.get(f"/api/service-orders/{order.id}/work-order-pdf", headers=headers)
            assert pdf.status_code == 409
            assert pdf.json()["detail"]["code"] == MOBILE_CALIBRATION_FLOW_CODE
            equipment = http.post(
                "/api/equipment",
                json={"service_order_id": order.id, "name": "Balanza", "serial_number": "B-1"},
                headers=headers,
            )
            assert equipment.status_code == 409, equipment.text
            assert equipment.json()["detail"]["code"] == MOBILE_CALIBRATION_FLOW_CODE
    finally:
        http.close()
        app.dependency_overrides.clear()
        app.dependency_overrides.update(previous)


def test_rebuild_is_blocked_while_a_lab_link_exists(ctx):
    db, user, client, _ = ctx
    order = _mobile_order(db, client, user)
    assert can_physically_rebuild_service_order(db, order).allowed
    root = LabWorkOrder(
        folio=6400, sequence_number=1, created_by_user_id=user.id,
        reception_date=date.today(), client_name="Cliente", status="draft",
    )
    db.add(root)
    db.flush()
    root.root_work_order_id = root.id
    from datetime import datetime, timezone

    db.add(ServiceOrderLabLink(
        service_order_id=order.id, lab_root_work_order_id=root.id, status="active",
        linked_at=datetime.now(timezone.utc), linked_by_user_id=user.id,
    ))
    db.commit()
    validation = can_physically_rebuild_service_order(db, order)
    assert not validation.allowed
    assert any(item.code == "lab_links" for item in validation.dependencies)
