from datetime import date, datetime, timezone
from hashlib import sha256
from decimal import Decimal
from types import SimpleNamespace

import pytest
from fastapi import HTTPException
from sqlalchemy import create_engine, func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, sessionmaker

import app.models  # noqa: F401
from app.core.db import Base
from app.models.activity import ActivityMessage
from app.models.audit_log import AuditLog
from app.models.catalog_item import CatalogItem
from app.models.client import Client
from app.models.equipment import Equipment
from app.models.linked_company import LinkedCompany
from app.models.notification import Notification
from app.models.quotation import Quotation, QuotationItem, QuotationSnapshot
from app.models.quotation_acceptance import QuotationAcceptance
from app.models.service_order_archive import ServiceOrderArchive
from app.models.quotation_service_change import QuotationServiceChangeRequest
from app.models.service_order import ServiceOrder, ServiceOrderItem, ServiceWorkOrder
from app.models.user import Role, User
from app.schemas.quotation_service_change import (
    QuotationServiceChangeCreate,
    QuotationServiceChangeReview,
    QuotationUnlockApply,
)
from app.schemas.service_type import (
    ServiceType,
    normalize_certificate_prefix,
    normalize_service_type,
)
from app.services.institutional_folios import build_certificate_folio, next_work_order_number
from app.services.auth import user_has_permission
from app.services.quotation_service_changes import (
    apply_change,
    preview_change,
    quotation_context,
    request_change,
    review_request,
)
from app.schemas.quotation import QuotationUpdate
from app.services.quotations import (
    _build_operational_snapshot,
    _write_snapshot,
    change_quotation_status,
    update_quotation,
)
from app.services.service_order_archives import restoration_conflicts, verify_archive_integrity
from app.services.service_order_rebuilds import can_physically_rebuild_service_order


@pytest.fixture()
def db():
    engine = create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine, expire_on_commit=False)
    with factory() as session:
        yield session
    engine.dispose()


def _user(db: Session, role_name: str, suffix: str) -> User:
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


def _service(
    db: Session,
    *,
    name: str,
    key: str,
    service_type: str,
    price: str,
    linked_company: LinkedCompany | None = None,
    prefix: str | None = None,
) -> CatalogItem:
    scopes = {
        "accredited": "accredited_iso_17025",
        "traceable": "traceable",
        "linked": "accredited_linked_lab",
    }
    item = CatalogItem(
        item_type="service",
        service_kind="simple",
        commodity="calibration",
        category="Calibracion",
        internal_key=key,
        name=name,
        origin_price=Decimal(price),
        origin_currency="MXN",
        exchange_rate=Decimal("1"),
        margin_percent=Decimal("0"),
        final_price_mxn=Decimal(price),
        calibration_scope=scopes[service_type],
        service_type=service_type,
        linked_company_id=linked_company.id if linked_company else None,
        linked_certificate_prefix=prefix,
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
    client = Client(legal_name="Cliente visible")
    db.add(client)
    db.flush()
    company = LinkedCompany(
        name="CAPYMET",
        abbreviation="CAPYMET",
        default_certificate_prefix="CMVG",
        is_enabled=True,
    )
    db.add(company)
    db.flush()
    traceable = _service(
        db,
        name="Calibración de pirómetro",
        key="SER-CAL-0001",
        service_type="traceable",
        price="2",
    )
    accredited = _service(
        db,
        name="Calibración de pirómetro",
        key="SER-CAL-0002",
        service_type="accredited",
        price="3",
    )
    linked = _service(
        db,
        name="Calibración vinculada",
        key="SER-CAL-0003",
        service_type="linked",
        price="4",
        linked_company=company,
        prefix="CMVG",
    )
    quotation = Quotation(
        folio="MYC-07-26-0125",
        client=client,
        advisor_id=requester.id,
        status="accepted",
        issued_on=date(2026, 7, 29),
        subtotal=Decimal("2"),
        tax_total=Decimal("0.32"),
        total=Decimal("2.32"),
    )
    quotation_item = QuotationItem(
        catalog_item_id=traceable.id,
        service_name=traceable.name,
        quantity=1,
        unit="service",
        unit_price=Decimal("2"),
        discount_percent=Decimal("0"),
        currency="MXN",
        commodity=traceable.commodity,
        calibration_scope=traceable.calibration_scope,
        tax_object=traceable.tax_object,
        tax_rate=traceable.tax_rate,
        tax_total=Decimal("0.32"),
        total=Decimal("2"),
        operational_snapshot=_build_operational_snapshot(db, traceable),
    )
    quotation.items = [quotation_item]
    db.add(quotation)
    db.flush()
    base_snapshot = _write_snapshot(db, quotation, reason="accepted", user_id=requester.id)
    order = ServiceOrder(
        folio="OSMYC-26-07-0005",
        work_order_number=7000,
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
            catalog_item_id=traceable.id,
            service_name=traceable.name,
            calibration_scope=traceable.calibration_scope,
            quantity=1,
            status="pending",
            service_snapshot=quotation_item.operational_snapshot["commercial_service_snapshot"],
        )
    ]
    order.work_orders = [
        ServiceWorkOrder(
            work_order_number=7001,
            sequence=1,
            status="pending",
            equipment_limit=10,
        )
    ]
    db.add(order)
    db.commit()
    return SimpleNamespace(
        requester=requester,
        administrator=administrator,
        client=client,
        company=company,
        traceable=traceable,
        accredited=accredited,
        linked=linked,
        quotation=quotation,
        quotation_item=quotation_item,
        base_snapshot=base_snapshot,
        order=order,
    )


def _acceptance(db: Session, context) -> QuotationAcceptance:
    pdf = b"%PDF-1.4 frozen"
    now = datetime(2026, 7, 29, 12, 0, tzinfo=timezone.utc)
    acceptance = QuotationAcceptance(
        confirmation_folio="MYC-AC-2026-000001",
        quotation_id=context.quotation.id,
        snapshot_id=context.base_snapshot.id,
        pdf_sha256=sha256(pdf).hexdigest(),
        pdf_bytes=pdf,
        signer_name="Cliente Autorizado",
        signer_email="firmante@example.test",
        consent_text="Acepto",
        evidence={"method": "email_otp"},
        verified_at=now,
        accepted_at=now,
    )
    db.add(acceptance)
    db.commit()
    return acceptance


def _request_and_authorize(db: Session, context) -> dict:
    requested = request_change(
        db,
        context.quotation.folio,
        QuotationServiceChangeCreate(
            reason="Corregir el tipo de servicio antes de iniciar la operación."
        ),
        context.requester,
    )
    return review_request(
        db,
        requested["folio"],
        QuotationServiceChangeReview(decision="authorize", validity_hours=24),
        context.administrator,
    )


def test_controlled_unlock_archives_ets_and_enters_revision(db, context):
    eligibility = quotation_context(db, context.quotation.folio, context.requester)
    assert eligibility["eligible"] is True
    assert eligibility["service_order_folio"] == "OSMYC-26-07-0005"

    authorized = _request_and_authorize(db, context)
    assert authorized["capability"] == "quotation.controlled_unlock"
    assert authorized["base_snapshot_number"] == 1
    request_record = db.scalar(select(QuotationServiceChangeRequest))
    assert request_record.authorized_apply_user_id == context.requester.id
    assert user_has_permission(context.requester, "quotations.exceptions.apply_unlock")
    active_for_requester = quotation_context(
        db, context.quotation.folio, context.requester
    )["active_request"]
    assert active_for_requester["can_apply"] is True

    preview = preview_change(db, authorized["folio"], context.requester)
    assert preview["outcome"]["creates_service_order"] is False
    assert preview["rebuild"]["allowed"] is True

    previous_order_id = context.order.id
    acceptance = _acceptance(db, context)
    completed = apply_change(
        db,
        authorized["folio"],
        QuotationUnlockApply(expected_snapshot_number=authorized["base_snapshot_number"]),
        context.requester,
    )
    assert completed["status"] == "completed"
    # La ETS operativa desaparece y no se crea una de reemplazo.
    assert db.get(ServiceOrder, previous_order_id) is None
    assert db.scalar(select(func.count(ServiceOrder.id))) == 0
    assert db.get(Quotation, context.quotation.id).status == "in_revision"
    # El snapshot histórico queda íntegro y no es una ETS activa.
    archive = db.scalar(select(ServiceOrderArchive))
    assert archive.service_order_folio == "OSMYC-26-07-0005"
    assert archive.original_service_order_id == previous_order_id
    assert archive.exception_folio == authorized["folio"]
    assert archive.acceptance_id == acceptance.id
    assert archive.accepted_snapshot_number == 1
    assert archive.archive_data["items"][0]["service_name"] == context.traceable.name
    assert len(archive.archive_data["work_orders"]) == 1
    assert verify_archive_integrity(archive)
    assert restoration_conflicts(db, archive) == []
    # La evidencia de la aceptación se conserva; sólo se invalida su vigencia.
    db.refresh(acceptance)
    assert acceptance.invalidated_at is not None
    assert acceptance.invalidation_reason == f"controlled_unlock:{authorized['folio']}"
    assert acceptance.pdf_bytes == b"%PDF-1.4 frozen"
    assert acceptance.confirmation_folio == "MYC-AC-2026-000001"
    codes = set(db.scalars(select(ActivityMessage.event_code)).all())
    assert {
        "quotation.unlock.completed",
        "quotation.service_order_archived",
        "quotation.in_revision",
    } <= codes
    assert db.scalar(select(func.count(Notification.id))) >= 2
    # Una aplicación repetida no puede duplicar archivo ni eliminar nada más.
    with pytest.raises(HTTPException) as repeated:
        apply_change(
            db,
            authorized["folio"],
            QuotationUnlockApply(expected_snapshot_number=1),
            context.requester,
        )
    assert repeated.value.status_code == 409
    assert db.scalar(select(func.count(ServiceOrderArchive.id))) == 1


def test_reopen_endpoint_cannot_bypass_the_unlock_flow(db, context):
    from app.services.quotations import reopen_accepted_quotation

    with pytest.raises(HTTPException) as error:
        reopen_accepted_quotation(db, context.quotation.id)
    assert error.value.status_code == 409
    assert db.get(Quotation, context.quotation.id).status == "accepted"
    assert db.get(ServiceOrder, context.order.id) is not None


def test_intervened_ets_blocks_unlock_and_keeps_everything(db, context):
    authorized = _request_and_authorize(db, context)
    db.add(
        Equipment(
            service_order_id=context.order.id,
            work_order_id=context.order.work_orders[0].id,
            status="registered",
            name="Pirómetro",
        )
    )
    db.commit()
    with pytest.raises(HTTPException) as error:
        apply_change(
            db,
            authorized["folio"],
            QuotationUnlockApply(expected_snapshot_number=1),
            context.requester,
        )
    assert error.value.status_code == 409
    assert db.get(ServiceOrder, context.order.id) is not None
    assert db.get(Quotation, context.quotation.id).status == "accepted"
    assert db.scalar(select(func.count(ServiceOrderArchive.id))) == 0
    assert db.scalar(
        select(func.count(ActivityMessage.id)).where(
            ActivityMessage.event_code == "quotation.unlock.blocked"
        )
    ) == 1


def test_revision_cycle_new_version_resend_and_reacceptance_creates_one_ets(db, context):
    authorized = _request_and_authorize(db, context)
    first = _acceptance(db, context)
    apply_change(
        db,
        authorized["folio"],
        QuotationUnlockApply(expected_snapshot_number=1),
        context.requester,
    )
    quotation = db.get(Quotation, context.quotation.id)
    assert quotation.status == "in_revision"

    # in_revision permite edición y genera una nueva versión comercial.
    update_quotation(
        db,
        quotation.id,
        QuotationUpdate(notes="Alcance corregido"),
        user_id=context.requester.id,
    )
    assert db.scalar(
        select(func.count(QuotationSnapshot.id)).where(
            QuotationSnapshot.quotation_id == quotation.id
        )
    ) == 2
    assert db.scalar(
        select(func.count(ActivityMessage.id)).where(
            ActivityMessage.event_code == "quotation.new_version"
        )
    ) == 1

    # No se puede aceptar sin reenviar, ni reutilizar la aceptación anterior.
    with pytest.raises(HTTPException) as skipped:
        change_quotation_status(db, quotation.id, "accepted", user_id=context.requester.id)
    assert skipped.value.status_code == 409
    sent = change_quotation_status(db, quotation.id, "sent", user_id=context.requester.id)
    assert sent.status == "sent"
    change_quotation_status(db, quotation.id, "accepted", user_id=context.requester.id)

    orders = db.scalars(select(ServiceOrder)).all()
    assert len(orders) == 1
    assert orders[0].folio == "OSMYC-26-07-0005"
    assert orders[0].id != context.order.id
    # Cada ciclo conserva su propio evento de estado (claves por ciclo).
    sent_events = db.scalars(
        select(ActivityMessage.idempotency_key).where(
            ActivityMessage.idempotency_key.like(f"quotation:{quotation.id}:status:%")
        )
    ).all()
    assert any(key.endswith(":r1") for key in sent_events)
    db.refresh(first)
    assert first.invalidated_at is not None
    assert first.confirmation_folio == "MYC-AC-2026-000001"


def test_administrator_registers_reason_and_unlocks_directly(db, context):
    result = request_change(
        db,
        context.quotation.folio,
        QuotationServiceChangeCreate(
            reason="Corrección administrativa antes de iniciar la operación."
        ),
        context.administrator,
    )
    request = db.scalar(select(QuotationServiceChangeRequest))

    assert result["status"] == "authorized"
    assert result["can_apply"] is True
    assert result["requester_name"] == context.administrator.full_name
    assert result["reviewer_name"] == context.administrator.full_name
    assert request.requester_id == context.administrator.id
    assert request.reviewer_id == context.administrator.id
    assert request.authorized_apply_user_id == context.administrator.id
    assert request.expires_at is not None
    assert db.scalar(
        select(func.count(AuditLog.id)).where(
            AuditLog.action == "quotation.unlock_self_authorized"
        )
    ) == 1
    assert db.scalar(
        select(func.count(ActivityMessage.id)).where(
            ActivityMessage.event_code == "quotation.unlock.authorized"
        )
    ) == 1


def test_rebuild_validator_blocks_equipment_and_executed_work_order(db, context):
    context.order.work_orders[0].status = "in_progress"
    db.commit()
    validation = can_physically_rebuild_service_order(db, context.order)
    assert validation.allowed is False
    assert {item.code for item in validation.dependencies} == {"executed_work_orders"}

    context.order.work_orders[0].status = "pending"
    db.add(
        Equipment(
            service_order_id=context.order.id,
            work_order_id=context.order.work_orders[0].id,
            status="registered",
            name="Pirómetro",
        )
    )
    db.commit()
    validation = can_physically_rebuild_service_order(db, context.order)
    assert validation.allowed is False
    assert "equipment" in {item.code for item in validation.dependencies}
    with pytest.raises(HTTPException, match="información operativa"):
        request_change(
            db,
            context.quotation.folio,
            QuotationServiceChangeCreate(reason="No debe autorizarse."),
            context.requester,
        )


def test_unlock_requires_explicit_permission(db, context):
    technician = _user(db, "Tecnico", "technician")
    db.commit()
    with pytest.raises(HTTPException) as error:
        request_change(
            db,
            context.quotation.folio,
            QuotationServiceChangeCreate(reason="Intento sin permiso explícito."),
            technician,
        )
    assert error.value.status_code == 403


def test_rebuild_validator_blocks_existing_signature(db, context):
    context.order.technician_signature_data_url = "data:image/png;base64,signature"
    db.commit()
    validation = can_physically_rebuild_service_order(db, context.order)
    assert validation.allowed is False
    assert "signatures" in {item.code for item in validation.dependencies}


def test_apply_rolls_back_if_atomic_commit_fails(db, context, monkeypatch):
    authorized = _request_and_authorize(db, context)
    previous_order_id = context.order.id
    real_commit = db.commit

    def fail_commit():
        raise IntegrityError("forced", {}, RuntimeError("forced"))

    monkeypatch.setattr(db, "commit", fail_commit)
    with pytest.raises(HTTPException, match="atómicamente"):
        apply_change(
            db,
            authorized["folio"],
            QuotationUnlockApply(expected_snapshot_number=authorized["base_snapshot_number"]),
            context.requester,
        )
    monkeypatch.setattr(db, "commit", real_commit)

    original_order = db.get(ServiceOrder, previous_order_id)
    request = db.scalar(select(QuotationServiceChangeRequest))
    assert original_order is not None
    assert original_order.folio == "OSMYC-26-07-0005"
    assert request.status == "authorized"
    assert request.consumed_at is None
    assert db.scalar(
        select(func.count(QuotationSnapshot.id)).where(
            QuotationSnapshot.quotation_id == context.quotation.id
        )
    ) == 1
    assert db.scalar(select(func.count(ServiceOrderArchive.id))) == 0
    assert db.get(Quotation, context.quotation.id).status == "accepted"


def test_service_type_aliases_and_linked_prefix_are_canonical():
    assert normalize_service_type("acreditado") is ServiceType.ACCREDITED
    assert normalize_service_type("trazable") is ServiceType.TRACEABLE
    assert normalize_service_type("linked_lab") is ServiceType.LINKED
    assert normalize_certificate_prefix(" cmvg ") == "CMVG"
    with pytest.raises(ValueError):
        normalize_certificate_prefix("CM VG")
    with pytest.raises(ValueError):
        normalize_certificate_prefix("CM-VG")


def test_certificate_and_work_order_sequences_follow_2026_and_annual_rules(db):
    assert build_certificate_folio(
        db, service_type="accredited", issued_on=date(2026, 7, 1)
    ) == "MYCA-07-26-8000"
    assert build_certificate_folio(
        db, service_type="traceable", issued_on=date(2026, 7, 1)
    ) == "MYCT-07-26-8000"
    assert build_certificate_folio(
        db,
        service_type="linked",
        linked_prefix="CMVG",
        issued_on=date(2026, 7, 1),
    ) == "CMVG26078000"
    assert build_certificate_folio(
        db,
        service_type="linked",
        linked_prefix="BESS",
        issued_on=date(2026, 7, 1),
    ) == "BESS26078000"
    assert build_certificate_folio(
        db, service_type="accredited", issued_on=date(2027, 1, 1)
    ) == "MYCA-01-27-1000"
    assert next_work_order_number(db, issued_on=date(2026, 7, 1)) == 7000
    assert next_work_order_number(db, issued_on=date(2027, 1, 1)) == 1000
