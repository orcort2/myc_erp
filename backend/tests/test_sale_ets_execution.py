from datetime import datetime, timezone
from decimal import Decimal

import pytest
from fastapi import HTTPException
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker

import app.models  # noqa: F401
from app.core.db import Base
from app.models.audit_log import AuditLog
from app.models.catalog_item import CatalogItem
from app.models.client import Client
from app.models.certificate import Certificate
from app.models.client_portal_membership import ClientPortalMembership
from app.models.notification import Notification
from app.models.quotation import Quotation, QuotationItem
from app.models.sale_execution import SaleAuthorization, SaleDelivery, SaleOrderItem
from app.models.service_execution import ServiceStage, ServiceUnit
from app.models.service_order import ServiceOrder, ServiceOrderItem
from app.models.user import Role, User
from app.schemas.quotation import QuotationStatusChange
from app.schemas.sale_execution import (
    SaleArrivalCreate,
    SaleAuthorizationCreate,
    SaleAuthorizationResolve,
    SaleDeliveryAccept,
    SaleDeliveryConfirm,
    SaleDeliveryCreate,
    SaleDeliveryLineCreate,
)
from app.schemas.service_order import ServiceOrderCreate
from app.services.quotations import _build_operational_snapshot, change_quotation_status
from app.services.sale_execution import (
    accept_technician_delivery,
    close_sale,
    confirm_delivery,
    create_delivery,
    dispatch_delivery,
    mark_warranty_return,
    initialize_existing_sale_execution,
    register_arrival,
    report_courier_delivery,
    request_authorization,
    resolve_authorization,
    sale_board,
)
from app.services.service_orders import create_service_order


@pytest.fixture()
def ctx():
    engine = create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(engine)
    db = sessionmaker(bind=engine, expire_on_commit=False)()
    admin_role = Role(name="Administrador", description="Admin")
    commercial_role = Role(name="Comercial", description="Comercial")
    technician_role = Role(name="Tecnico", description="Técnico")
    db.add_all([admin_role, commercial_role, technician_role]); db.flush()
    admin = User(username="sale-admin", email="sale-admin@example.test", full_name="Admin Venta", hashed_password="unused", role_id=admin_role.id, roles=[admin_role])
    advisor = User(username="sale-advisor", email="sale-advisor@example.test", full_name="Asesor Venta", hashed_password="unused", role_id=commercial_role.id, roles=[commercial_role])
    technician = User(username="sale-tech", email="sale-tech@example.test", full_name="Técnico Venta", hashed_password="unused", role_id=technician_role.id, roles=[technician_role])
    client = Client(legal_name="Cliente Venta")
    db.add_all([admin, advisor, technician, client]); db.commit()
    yield db, admin, advisor, technician, client
    db.close(); engine.dispose()


def _catalog(db, name, *, serial=False, calibration=None):
    item = CatalogItem(
        item_type="product", service_kind="simple", commodity="sale", category="Venta",
        operational_category="sale", name=name, origin_price=Decimal("100"),
        origin_currency="MXN", exchange_rate=Decimal("1"), margin_percent=Decimal("0"),
        final_price_mxn=Decimal("100"), tax_object="iva_16", tax_rate=Decimal("16"),
        requires_individual_identification=serial, sale_brand="MYC", sale_model="M-1",
        sale_specification="Exacta", included_calibration_catalog_item_id=calibration.id if calibration else None,
    )
    db.add(item); db.flush(); return item


def _calibration(db):
    item = CatalogItem(
        item_type="service", service_kind="simple", commodity="calibration", category="Calibracion",
        operational_category="calibration", name="Calibración trazable", origin_price=Decimal("50"),
        origin_currency="MXN", exchange_rate=Decimal("1"), margin_percent=Decimal("0"),
        final_price_mxn=Decimal("50"), tax_object="iva_16", tax_rate=Decimal("16"),
        calibration_scope="traceable", service_type="traceable",
    )
    db.add(item); db.flush(); return item


def _quotation(db, client, advisor, catalog, *, quantity=1, folio="COT-SALE-1"):
    quote = Quotation(folio=folio, client_id=client.id, advisor_id=advisor.id, status="waiting",
                      subtotal=Decimal("100"), tax_total=Decimal("16"), total=Decimal("116"))
    quote.items = [QuotationItem(
        catalog_item_id=catalog.id, service_name=catalog.name, operational_category="sale",
        commodity="sale", quantity=quantity, unit_price=Decimal("100"),
        discount_percent=Decimal("0"), tax_rate=Decimal("16"), tax_total=Decimal("16"),
        total=Decimal("100"), operational_snapshot=_build_operational_snapshot(db, catalog),
    )]
    db.add(quote); db.commit(); return quote


def _order(db, client, advisor, catalog, *, quantity=1, folio="COT-SALE-1"):
    quote = _quotation(db, client, advisor, catalog, quantity=quantity, folio=folio)
    return create_service_order(db, ServiceOrderCreate(client_id=client.id, quotation_id=quote.id,
                                                        advisor_id=advisor.id), user_id=advisor.id)


def test_serialized_sale_freezes_configuration_and_materializes_independent_units(ctx):
    db, _, advisor, _, client = ctx
    catalog = _catalog(db, "Equipo serial", serial=True)
    order = _order(db, client, advisor, catalog, quantity=3)
    projection = db.scalar(select(SaleOrderItem).where(SaleOrderItem.service_order_id == order.id))
    assert projection.requires_individual_identification is True
    assert projection.frozen_configuration["model"] == "M-1"
    assert len(projection.units) == 3
    assert {unit.status for unit in projection.units} == {"pending_arrival"}
    assert db.query(ServiceUnit).filter(ServiceUnit.service_order_id == order.id).count() == 3

    catalog.requires_individual_identification = False
    catalog.sale_model = "CATALOGO-NUEVO"
    db.commit()
    board = sale_board(db, order.id)
    assert board["items"][0].requires_individual_identification is True
    assert board["items"][0].frozen_configuration["model"] == "M-1"


def test_nonserialized_partial_arrival_delivery_and_close(ctx):
    db, _, advisor, _, client = ctx
    portal_user = User(username="sale-portal", email="sale-portal@example.test", full_name="Compras Portal",
                       hashed_password="unused", account_type="client_portal")
    db.add(portal_user); db.flush()
    db.add(ClientPortalMembership(client_id=client.id, user_id=portal_user.id, status="active")); db.commit()
    catalog = _catalog(db, "Consumible por cantidad")
    order = _order(db, client, advisor, catalog, quantity=100)
    item = db.scalar(select(SaleOrderItem).where(SaleOrderItem.service_order_id == order.id))
    register_arrival(db, order.id, item.id, SaleArrivalCreate(quantity=60, catalog_item_id=catalog.id,
                                                              brand="MYC", model="M-1", specification="Exacta"), actor=advisor)
    delivery = create_delivery(db, order.id, SaleDeliveryCreate(
        mode="client_pickup", lines=[SaleDeliveryLineCreate(sale_order_item_id=item.id, quantity=60)]
    ), actor=advisor)
    delivery_id = delivery["deliveries"][0].id
    dispatch_delivery(db, order.id, delivery_id, actor=advisor)
    assert db.scalar(select(Notification).where(
        Notification.recipient_user_id == portal_user.id,
        Notification.notification_type == "sale_ready_for_pickup",
    )) is not None
    confirmed = confirm_delivery(db, order.id, delivery_id, SaleDeliveryConfirm(
        receiver_name="Compras Cliente", evidence={"folio": "REC-1"}
    ), actor=advisor)
    assert confirmed["items"][0].delivered_quantity == 60
    assert any("40 unidad" in blocker for blocker in confirmed["blockers"])
    with pytest.raises(HTTPException):
        close_sale(db, order.id, actor=advisor)

    register_arrival(db, order.id, item.id, SaleArrivalCreate(quantity=40, catalog_item_id=catalog.id,
                                                              brand="MYC", model="M-1", specification="Exacta"), actor=advisor)
    second = create_delivery(db, order.id, SaleDeliveryCreate(
        mode="client_pickup", lines=[SaleDeliveryLineCreate(sale_order_item_id=item.id, quantity=40)]
    ), actor=advisor)
    second_id = second["deliveries"][0].id
    dispatch_delivery(db, order.id, second_id, actor=advisor)
    confirm_delivery(db, order.id, second_id, SaleDeliveryConfirm(receiver_name="Almacén", signature_data_url="data:image/png;base64,AA=="), actor=advisor)
    assert close_sale(db, order.id, actor=advisor)["status"] == "closed"


def test_sale_with_calibration_blocks_delivery_until_same_unit_stage_closes(ctx):
    db, _, advisor, _, client = ctx
    calibration = _calibration(db)
    catalog = _catalog(db, "Equipo con calibración", serial=True, calibration=calibration)
    order = _order(db, client, advisor, catalog, folio="COT-SALE-CAL")
    item = db.scalar(select(SaleOrderItem).where(SaleOrderItem.service_order_id == order.id))
    unit = item.units[0]
    board = register_arrival(db, order.id, item.id, SaleArrivalCreate(
        catalog_item_id=catalog.id, serial_number="SER-1", brand="MYC", model="M-1", specification="Exacta"
    ), actor=advisor, sale_unit_state_id=unit.id)
    state = board["items"][0].units[0]
    assert state.equipment_id is not None and state.calibration_stage_id is not None
    assert db.query(Certificate).filter(Certificate.equipment_id == state.equipment_id).count() == 1
    assert db.query(ServiceUnit).filter(ServiceUnit.id == state.service_unit_id).one().equipment_id == state.equipment_id
    with pytest.raises(HTTPException, match="liberada"):
        create_delivery(db, order.id, SaleDeliveryCreate(
            mode="client_pickup", lines=[SaleDeliveryLineCreate(sale_order_item_id=item.id,
                                                                 sale_unit_state_id=state.id)]
        ), actor=advisor)
    db.get(ServiceStage, state.calibration_stage_id).status = "completed"; db.commit()
    ready = sale_board(db, order.id)
    assert ready["items"][0].units[0].status == "ready_for_delivery"


def test_discrepancy_requires_authorized_substitution_and_warranty_isolated(ctx):
    db, admin, advisor, _, client = ctx
    catalog = _catalog(db, "Equipo controlado", serial=True)
    order = _order(db, client, advisor, catalog, folio="COT-SALE-DIFF")
    item = db.scalar(select(SaleOrderItem).where(SaleOrderItem.service_order_id == order.id)); unit = item.units[0]
    mismatch = SaleArrivalCreate(catalog_item_id=catalog.id, serial_number="SER-X", brand="MYC",
                                 model="OTRO", specification="Exacta")
    with pytest.raises(HTTPException, match="bloqueada"):
        register_arrival(db, order.id, item.id, mismatch, actor=advisor, sale_unit_state_id=unit.id)
    assert db.get(type(unit), unit.id).status == "commercial_review"
    authorization = request_authorization(db, order.id, SaleAuthorizationCreate(
        authorization_type="substitution", sale_order_item_id=item.id,
        sale_unit_state_id=unit.id, reason="Proveedor sustituyó modelo equivalente"
    ), actor=advisor)
    resolve_authorization(db, order.id, authorization.id, SaleAuthorizationResolve(
        authorized=True, comment="Equivalencia comercial verificada"
    ), actor=admin)
    mismatch.substitution_authorization_id = authorization.id
    register_arrival(db, order.id, item.id, mismatch, actor=advisor, sale_unit_state_id=unit.id)
    returned = mark_warranty_return(db, order.id, unit.id, "Defecto de fábrica", actor=advisor)
    assert returned["items"][0].units[0].status == "warranty_return"
    assert any("garantía" in blocker for blocker in returned["blockers"])
    assert db.get(SaleAuthorization, authorization.id).status == "consumed"


def test_courier_and_technician_delivery_contracts_and_notifications(ctx):
    db, _, advisor, technician, client = ctx
    catalog = _catalog(db, "Dos equipos", serial=True)
    order = _order(db, client, advisor, catalog, quantity=2, folio="COT-SALE-DEL")
    item = db.scalar(select(SaleOrderItem).where(SaleOrderItem.service_order_id == order.id))
    with pytest.raises(HTTPException, match="asesor"):
        register_arrival(db, order.id, item.id, SaleArrivalCreate(
            catalog_item_id=catalog.id, serial_number="NO", brand="MYC", model="M-1", specification="Exacta"
        ), actor=technician, sale_unit_state_id=item.units[0].id)
    for index, unit in enumerate(item.units, start=1):
        register_arrival(db, order.id, item.id, SaleArrivalCreate(
            catalog_item_id=catalog.id, serial_number=f"S-{index}", brand="MYC", model="M-1", specification="Exacta"
        ), actor=advisor, sale_unit_state_id=unit.id)
    courier = create_delivery(db, order.id, SaleDeliveryCreate(
        mode="courier", courier_name="DHL", tracking_number="TRACK-1",
        lines=[SaleDeliveryLineCreate(sale_order_item_id=item.id, sale_unit_state_id=item.units[0].id)]
    ), actor=advisor)
    courier_id = courier["deliveries"][0].id
    dispatch_delivery(db, order.id, courier_id, actor=advisor)
    reported = report_courier_delivery(db, order.id, courier_id, actor=advisor)
    assert reported["deliveries"][0].status == "delivery_reported"
    assert reported["blockers"]

    technician_board = create_delivery(db, order.id, SaleDeliveryCreate(
        mode="myc_technician", technician_id=technician.id, address_source="custom",
        delivery_address={"street": "Av. Uno"},
        lines=[SaleDeliveryLineCreate(sale_order_item_id=item.id, sale_unit_state_id=item.units[1].id)]
    ), actor=advisor)
    technician_delivery = next(delivery for delivery in technician_board["deliveries"] if delivery.mode == "myc_technician")
    assert db.scalar(select(Notification).where(Notification.recipient_user_id == technician.id)) is not None
    accepted = accept_technician_delivery(db, order.id, technician_delivery.id,
                                          SaleDeliveryAccept(scheduled_for=datetime.now(timezone.utc)), actor=technician)
    assert next(delivery for delivery in accepted["deliveries"] if delivery.id == technician_delivery.id).status == "scheduled"


def test_accepting_sale_quote_creates_single_sale_ets_and_audits(ctx):
    db, _, advisor, _, client = ctx
    catalog = _catalog(db, "Venta automática")
    quote = _quotation(db, client, advisor, catalog, folio="COT-SALE-AUTO")
    change_quotation_status(db, quote.id, "accepted", QuotationStatusChange(comment="Aprobada"), user_id=advisor.id)
    orders = list(db.scalars(select(ServiceOrder).where(ServiceOrder.quotation_id == quote.id)).all())
    assert len(orders) == 1
    assert db.scalar(select(SaleOrderItem.id).where(SaleOrderItem.service_order_id == orders[0].id)) is not None
    create_service_order(db, ServiceOrderCreate(client_id=client.id, quotation_id=quote.id,
                                                 advisor_id=advisor.id), user_id=advisor.id)
    assert db.query(ServiceOrder).filter(ServiceOrder.quotation_id == quote.id).count() == 1
    assert db.scalar(select(AuditLog.id).where(AuditLog.action == "sale.execution_initialized")) is not None


def test_historical_sale_requires_explicit_snapshot_initialization(ctx):
    db, _, advisor, _, client = ctx
    catalog = _catalog(db, "Venta histórica", serial=True)
    order = _order(db, client, advisor, catalog, folio="COT-SALE-HIST")
    projection = db.scalar(select(SaleOrderItem).where(SaleOrderItem.service_order_id == order.id))
    frozen_model = projection.frozen_configuration["model"]
    from app.services.sale_execution import delete_pristine_sale_execution
    delete_pristine_sale_execution(db, order.id)
    catalog.sale_model = "CATALOGO-VIGENTE"
    db.commit()

    assert sale_board(db, order.id)["items"] == []
    initialized = initialize_existing_sale_execution(db, order.id, actor=advisor)
    assert initialized["items"][0].frozen_configuration["model"] == frozen_model


def test_closing_sale_does_not_close_mixed_ets_with_open_non_sale_item(ctx):
    db, _, advisor, _, client = ctx
    catalog = _catalog(db, "Venta mixta")
    order = _order(db, client, advisor, catalog, folio="COT-SALE-MIX")
    item = db.scalar(select(SaleOrderItem).where(SaleOrderItem.service_order_id == order.id))
    db.add(ServiceOrderItem(
        service_order_id=order.id, service_name="Servicio pendiente",
        operational_category="maintenance", quantity=1, status="pending",
    ))
    db.commit()
    register_arrival(db, order.id, item.id, SaleArrivalCreate(
        quantity=1, catalog_item_id=catalog.id, brand="MYC", model="M-1", specification="Exacta",
    ), actor=advisor)
    delivery = create_delivery(db, order.id, SaleDeliveryCreate(
        mode="client_pickup", lines=[SaleDeliveryLineCreate(sale_order_item_id=item.id, quantity=1)],
    ), actor=advisor)
    delivery_id = delivery["deliveries"][0].id
    dispatch_delivery(db, order.id, delivery_id, actor=advisor)
    confirm_delivery(db, order.id, delivery_id, SaleDeliveryConfirm(
        receiver_name="Almacén", evidence={"folio": "MIX-1"},
    ), actor=advisor)

    result = close_sale(db, order.id, actor=advisor)
    assert result["status"] != "closed"
    assert order.items[0].status == "completed"
