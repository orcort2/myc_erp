from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from types import SimpleNamespace

import pytest
from fastapi import HTTPException
from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import Session, sessionmaker

import app.models  # noqa: F401
from app.core.db import Base
from app.models.activity import ActivityMessage
from app.models.catalog_item import CatalogItem
from app.models.client import Client
from app.models.equipment import Equipment
from app.models.notification import Notification
from app.models.quotation import Quotation, QuotationItem, QuotationSnapshot
from app.models.quotation_service_change import QuotationServiceChangeRequest
from app.models.service_order import ServiceOrder, ServiceOrderItem
from app.models.user import Role, User
from app.schemas.quotation_service_change import (
    QuotationServiceChangeCreate,
    QuotationServiceChangeRead,
    QuotationServiceChangeReview,
)
from app.services.quotation_service_changes import (
    apply_change,
    quotation_context,
    request_change,
    review_request,
)


@pytest.fixture()
def db():
    engine = create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine, expire_on_commit=False)
    with factory() as session:
        yield session
    engine.dispose()


def _user(db: Session, role_name: str, suffix: str) -> User:
    role = db.scalar(select(Role).where(Role.name == role_name))
    if role is None:
        role = Role(name=role_name, description=role_name)
        db.add(role)
        db.flush()
    user = User(
        email=f"{suffix}@example.test",
        full_name=f"Usuario {suffix}",
        hashed_password="unused",
        role_id=role.id,
        roles=[role],
    )
    db.add(user)
    db.flush()
    return user


def _service(db: Session, name: str, key: str) -> CatalogItem:
    item = CatalogItem(
        item_type="service",
        service_kind="simple",
        commodity="calibration",
        category="Calibracion",
        internal_key=key,
        name=name,
        origin_price=Decimal("1000.00"),
        origin_currency="MXN",
        exchange_rate=Decimal("1"),
        margin_percent=Decimal("0"),
        final_price_mxn=Decimal("1000.00"),
        calibration_scope="traceable",
        tax_object="iva_16",
        tax_rate=Decimal("16"),
    )
    db.add(item)
    db.flush()
    return item


@pytest.fixture()
def context(db: Session):
    requester = _user(db, "Comercial", "requester")
    administrator = _user(db, "Administrador", "administrator")
    developer = _user(db, "Desarrollador", "developer")
    auditor = _user(db, "Auditor", "auditor")
    client = Client(legal_name="Cliente visible")
    current = _service(db, "Calibración acreditada", "SRV-CAL-001")
    requested = _service(db, "Calibración trazable", "SRV-CAL-002")
    quotation = Quotation(
        folio="MYC-07-26-0125",
        client=client,
        advisor_id=requester.id,
        status="accepted",
        issued_on=date(2026, 7, 29),
        subtotal=Decimal("1000"),
        tax_total=Decimal("160"),
        total=Decimal("1160"),
    )
    quotation_item = QuotationItem(
        catalog_item_id=current.id,
        service_name=current.name,
        quantity=1,
        unit="service",
        unit_price=Decimal("1000"),
        discount_percent=Decimal("0"),
        currency="MXN",
        commodity=current.commodity,
        calibration_scope=current.calibration_scope,
        tax_object=current.tax_object,
        tax_rate=current.tax_rate,
        tax_total=Decimal("160"),
        total=Decimal("1000"),
        operational_snapshot={
            "schema_version": 1,
            "service_kind": "simple",
            "commercial_catalog_item_id": current.id,
            "commercial_service_name": current.name,
            "operational_items": [
                {
                    "catalog_item_id": current.id,
                    "service_name": current.name,
                    "calibration_scope": current.calibration_scope,
                    "quantity": 1,
                    "status": "pending",
                }
            ],
        },
    )
    quotation.items = [quotation_item]
    db.add(quotation)
    db.flush()
    order = ServiceOrder(
        folio="OSMYC-26-07-0001",
        work_order_number=7001,
        client_id=client.id,
        quotation_id=quotation.id,
        advisor_id=requester.id,
        status="scheduled",
        total_equipment=0,
        completed_equipment=0,
        requires_payment=True,
    )
    order.items = [
        ServiceOrderItem(
            quotation_item_id=quotation_item.id,
            catalog_item_id=current.id,
            service_name=current.name,
            calibration_scope=current.calibration_scope,
            quantity=1,
            status="pending",
        )
    ]
    db.add(order)
    db.commit()
    return SimpleNamespace(
        requester=requester,
        administrator=administrator,
        developer=developer,
        auditor=auditor,
        client=client,
        current=current,
        requested=requested,
        quotation=quotation,
        quotation_item=quotation_item,
        order=order,
    )


def _payload(context) -> QuotationServiceChangeCreate:
    return QuotationServiceChangeCreate(
        quotation_line_number=1,
        requested_service_key=context.requested.internal_key,
        reason="El servicio se dio de alta equivocadamente.",
        observation="Corregir antes de registrar equipos.",
    )


def _create(db: Session, context) -> dict:
    return request_change(
        db,
        context.quotation.folio,
        _payload(context),
        context.requester,
    )


def _authorize(db: Session, context, folio: str) -> dict:
    return review_request(
        db,
        folio,
        QuotationServiceChangeReview(decision="authorize", validity_hours=24),
        context.administrator,
    )


def test_context_and_request_use_visible_folios_and_are_idempotent(db, context):
    eligibility = quotation_context(
        db, context.quotation.folio, context.requester
    )
    assert eligibility["eligible"] is True
    assert eligibility["quotation_folio"] == "MYC-07-26-0125"
    assert eligibility["service_order_folio"] == "OSMYC-26-07-0001"

    first = _create(db, context)
    second = _create(db, context)

    assert first["folio"].startswith("EXV-2026-")
    assert first["folio"] == second["folio"]
    assert first["quotation_folio"] == context.quotation.folio
    assert first["service_order_folio"] == context.order.folio
    public_resource = QuotationServiceChangeRead.model_validate(first)
    assert public_resource.quotation_line_number == 1
    assert public_resource.requested_service_key == "SRV-CAL-002"
    assert "quotation_item_id" not in public_resource.model_dump()
    assert db.scalar(select(func.count(QuotationServiceChangeRequest.id))) == 1
    assert db.scalar(select(func.count(ActivityMessage.id))) == 2
    assert db.scalar(select(func.count(Notification.id))) >= 1


@pytest.mark.parametrize("status", ["draft", "sent", "rejected"])
def test_non_approved_quotation_cannot_request(db, context, status):
    context.quotation.status = status
    db.commit()
    with pytest.raises(HTTPException) as error:
        _create(db, context)
    assert error.value.status_code == 409


def test_missing_ets_equipment_permission_and_same_service_are_rejected(db, context):
    context.order.is_active = False
    db.commit()
    with pytest.raises(HTTPException, match="ETS relacionado"):
        _create(db, context)

    context.order.is_active = True
    equipment = Equipment(
        service_order_id=context.order.id,
        status="cancelled",
        name="Equipo cancelado que conserva participación",
    )
    db.add(equipment)
    db.commit()
    with pytest.raises(HTTPException, match="equipos registrados"):
        _create(db, context)

    db.delete(equipment)
    db.commit()
    with pytest.raises(HTTPException) as forbidden:
        request_change(
            db,
            context.quotation.folio,
            _payload(context),
            context.auditor,
        )
    assert forbidden.value.status_code == 403

    same = _payload(context)
    same.requested_service_key = context.current.internal_key
    with pytest.raises(HTTPException, match="distinto"):
        request_change(
            db, context.quotation.folio, same, context.requester
        )


def test_review_segregation_rejection_and_information_do_not_change_entities(db, context):
    created = _create(db, context)
    self_requested = request_change(
        db,
        context.quotation.folio,
        _payload(context),
        context.developer,
    )
    with pytest.raises(HTTPException) as forbidden:
        review_request(
            db,
            self_requested["folio"],
            QuotationServiceChangeReview(decision="authorize"),
            context.developer,
        )
    assert forbidden.value.status_code == 403

    info = review_request(
        db,
        created["folio"],
        QuotationServiceChangeReview(
            decision="request_information",
            comment="Confirma la regla de acreditación.",
        ),
        context.administrator,
    )
    assert info["status"] == "information_required"
    rejected = review_request(
        db,
        created["folio"],
        QuotationServiceChangeReview(
            decision="reject",
            comment="No procede.",
        ),
        context.administrator,
    )
    assert rejected["status"] == "rejected"
    assert context.quotation_item.catalog_item_id == context.current.id
    assert context.order.items[0].catalog_item_id == context.current.id


def test_authorization_grants_limited_single_use_and_apply_syncs_same_records(db, context):
    created = _create(db, context)
    authorized = _authorize(db, context, created["folio"])
    assert authorized["capability"] == "quotation.change_service_type"
    assert authorized["status"] == "authorized"
    notification_types = set(db.scalars(select(Notification.notification_type)).all())
    assert "quotation_service_change_capability_available" in notification_types
    assert "quotation_service_change_expiring" in notification_types
    assert quotation_context(
        db, context.quotation.folio, context.requester
    )["active_request"]["can_apply"] is True

    quotation_id = context.quotation.id
    order_id = context.order.id
    applied = apply_change(db, created["folio"], context.requester)

    assert applied["status"] == "completed"
    assert applied["quotation_folio"] == "MYC-07-26-0125"
    assert applied["service_order_folio"] == "OSMYC-26-07-0001"
    assert db.get(Quotation, quotation_id).items[0].catalog_item_id == context.requested.id
    order_item = db.scalar(
        select(ServiceOrderItem).where(ServiceOrderItem.service_order_id == order_id)
    )
    assert order_item.catalog_item_id == context.requested.id
    assert order_item.calibration_scope == context.requested.calibration_scope
    assert db.scalar(
        select(func.count(QuotationSnapshot.id)).where(
            QuotationSnapshot.quotation_id == quotation_id
        )
    ) == 2

    repeated = apply_change(db, created["folio"], context.requester)
    assert repeated["status"] == "completed"
    assert db.scalar(
        select(func.count(QuotationSnapshot.id)).where(
            QuotationSnapshot.quotation_id == quotation_id
        )
    ) == 2


def test_equipment_after_authorization_blocks_without_partial_update(db, context):
    created = _create(db, context)
    _authorize(db, context, created["folio"])
    db.add(
        Equipment(
            service_order_id=context.order.id,
            status="registered",
            name="Equipo registrado después de autorizar",
        )
    )
    db.commit()

    with pytest.raises(HTTPException, match="equipos registrados"):
        apply_change(db, created["folio"], context.requester)

    request = db.scalar(
        select(QuotationServiceChangeRequest).where(
            QuotationServiceChangeRequest.folio == created["folio"]
        )
    )
    assert request.status == "blocked"
    assert db.get(QuotationItem, context.quotation_item.id).catalog_item_id == context.current.id
    assert db.scalar(
        select(ServiceOrderItem.catalog_item_id).where(
            ServiceOrderItem.service_order_id == context.order.id
        )
    ) == context.current.id
    assert db.scalar(select(func.count(QuotationSnapshot.id))) == 0


def test_commercial_impact_cannot_be_authorized(db, context):
    context.requested.final_price_mxn = Decimal("1500")
    db.commit()
    created = _create(db, context)
    assert created["impact"]["commercial_changes_required"] is True
    with pytest.raises(HTTPException, match="excepción comercial"):
        _authorize(db, context, created["folio"])


def test_expired_or_revoked_capability_cannot_be_used(db, context):
    created = _create(db, context)
    _authorize(db, context, created["folio"])
    request = db.scalar(
        select(QuotationServiceChangeRequest).where(
            QuotationServiceChangeRequest.folio == created["folio"]
        )
    )
    request.expires_at = datetime.now(timezone.utc) - timedelta(minutes=1)
    db.commit()
    with pytest.raises(HTTPException, match="venció"):
        apply_change(db, created["folio"], context.requester)
    assert request.status == "expired"
    assert context.quotation_item.catalog_item_id == context.current.id

    second = request_change(
        db, context.quotation.folio, _payload(context), context.requester
    )
    second_request = db.scalar(
        select(QuotationServiceChangeRequest).where(
            QuotationServiceChangeRequest.folio == second["folio"]
        )
    )
    second_request.status = "revoked"
    second_request.active_scope_key = None
    db.commit()
    with pytest.raises(HTTPException, match="no está disponible"):
        apply_change(db, second["folio"], context.requester)


def test_relation_version_and_inactive_target_are_revalidated(db, context):
    created = _create(db, context)
    _authorize(db, context, created["folio"])
    context.order.quotation_id = None
    db.commit()
    with pytest.raises(HTTPException, match="ya no pertenece"):
        apply_change(db, created["folio"], context.requester)
    assert context.quotation_item.catalog_item_id == context.current.id

    context.order.quotation_id = context.quotation.id
    db.commit()
    next_request = _create(db, context)
    _authorize(db, context, next_request["folio"])
    context.requested.is_active = False
    db.commit()
    with pytest.raises(HTTPException, match="no está activo"):
        apply_change(db, next_request["folio"], context.requester)
    blocked = db.scalar(
        select(QuotationServiceChangeRequest).where(
            QuotationServiceChangeRequest.folio == next_request["folio"]
        )
    )
    assert blocked.status == "blocked"
    assert context.quotation_item.catalog_item_id == context.current.id

    context.requested.is_active = True
    db.commit()
    versioned = _create(db, context)
    _authorize(db, context, versioned["folio"])
    context.quotation.updated_at = context.quotation.updated_at + timedelta(seconds=1)
    db.commit()
    with pytest.raises(HTTPException, match="versión"):
        apply_change(db, versioned["folio"], context.requester)
    assert context.quotation_item.catalog_item_id == context.current.id
