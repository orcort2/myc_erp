from datetime import date, datetime, timezone
from unittest.mock import patch

import pytest
from fastapi import HTTPException
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker

import app.models  # noqa: F401
from app.core.db import Base
from app.models.certificate import Certificate, CertificateCaptureFile, CertificatePdfVersion
from app.models.client import Client
from app.models.equipment import Equipment
from app.models.field_sheet import FieldSheet
from app.models.service_order import ServiceOrderItem
from app.models.user import User
from app.schemas.certificate import CertificateCreate, CertificateUpdate
from app.schemas.equipment import EquipmentCreate
from app.schemas.service_order import ServiceOrderCreate, ServiceOrderItemCreate
from app.services.certificates import (
    ALLOWED_TRANSITIONS,
    create_certificate,
    quality_approve,
    release_to_client,
    send_to_quality,
    start_capture,
    update_certificate,
)
from app.services import certificate_authentication
from app.services.equipment import create_equipment
from app.services.institutional_folios import build_certificate_folio
from app.services.folio_engine import suggest_certificate_folio
from app.services.service_orders import create_service_order


@pytest.fixture()
def db():
    engine = create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine, expire_on_commit=False)
    with factory() as session:
        yield session
    engine.dispose()


@pytest.fixture()
def mixed_order(db):
    actor = User(
        username="verification-actor",
        email="verification@example.test",
        full_name="Verification Actor",
        hashed_password="unused",
    )
    client = Client(legal_name="Cliente metrológico")
    db.add_all([actor, client])
    db.commit()
    order = create_service_order(
        db,
        ServiceOrderCreate(
            client_id=client.id,
            requires_payment=False,
            items=[
                ServiceOrderItemCreate(
                    service_name="Calibración trazable",
                    operational_category="calibration",
                    calibration_scope="traceable",
                    quantity=1,
                ),
                ServiceOrderItemCreate(
                    service_name="Verificación dimensional",
                    operational_category="verification",
                    calibration_scope=None,
                    quantity=1,
                ),
            ],
        ),
        user_id=actor.id,
    )
    items = {item.operational_category: item for item in order.items}
    return actor, order, items


def test_verification_ets_has_work_order_equipment_and_distinct_certificate(db, mixed_order):
    actor, order, items = mixed_order
    assert len(order.work_orders) == 1
    assert order.work_orders[0].equipment_limit == 10

    verification = create_equipment(
        db,
        EquipmentCreate(
            service_order_id=order.id,
            service_order_item_id=items["verification"].id,
            calibration_scope=None,
            name="Micrómetro",
        ),
        user_id=actor.id,
    )
    calibration = create_equipment(
        db,
        EquipmentCreate(
            service_order_id=order.id,
            service_order_item_id=items["calibration"].id,
            calibration_scope="traceable",
            name="Termómetro",
        ),
        user_id=actor.id,
    )

    verification_certificate = db.scalar(
        select(Certificate).where(Certificate.equipment_id == verification.id)
    )
    calibration_certificate = db.scalar(
        select(Certificate).where(Certificate.equipment_id == calibration.id)
    )
    assert verification.calibration_scope is None
    assert verification.service_order_item_id == items["verification"].id
    assert verification_certificate.certificate_type == "verification"
    assert verification_certificate.title == "Certificado de Verificación"
    assert verification_certificate.folio.startswith("MYCV-")
    assert calibration_certificate.certificate_type == "trazable"
    assert calibration_certificate.folio.startswith("MYCT")
    with pytest.raises(HTTPException, match="no admite edición manual"):
        update_certificate(
            db,
            verification_certificate.id,
            CertificateUpdate(expected_folio="MANUAL-1"),
            user_id=actor.id,
        )


def test_mixed_ets_requires_exact_item_and_verification_rejects_calibration_scope(db, mixed_order):
    actor, order, items = mixed_order
    with pytest.raises(HTTPException, match="Selecciona la partida metrológica"):
        create_equipment(
            db,
            EquipmentCreate(service_order_id=order.id, name="Sin proceso"),
            user_id=actor.id,
        )
    with pytest.raises(HTTPException, match="Verificación no admite alcance"):
        create_equipment(
            db,
            EquipmentCreate(
                service_order_id=order.id,
                service_order_item_id=items["verification"].id,
                calibration_scope="traceable",
                name="Proceso falso",
            ),
            user_id=actor.id,
        )


def test_verification_rejects_calibration_certificate_types(db, mixed_order):
    actor, order, items = mixed_order
    equipment = create_equipment(
        db,
        EquipmentCreate(
            service_order_id=order.id,
            service_order_item_id=items["verification"].id,
            name="Balanza",
        ),
        user_id=actor.id,
    )
    for certificate_type in ("acreditado", "trazable", "vinculado"):
        with pytest.raises(HTTPException, match="no corresponde al proceso"):
            create_certificate(
                db,
                CertificateCreate(
                    service_order_id=order.id,
                    equipment_id=equipment.id,
                    certificate_type=certificate_type,
                ),
                user_id=actor.id,
            )


def test_verification_folio_format_and_institutional_sequence(db):
    first = build_certificate_folio(
        db, service_type="verification", issued_on=date(2026, 8, 24)
    )
    second = build_certificate_folio(
        db, service_type="verification", issued_on=date(2026, 8, 24)
    )
    assert first == "MYCV-08-26-8000"
    assert second == "MYCV-08-26-8001"
    suggested = suggest_certificate_folio(
        db,
        certificate_type="verification",
        issued_on=date(2026, 8, 24),
        sequence=9123,
    )
    assert suggested.suggested_folio == "MYCV-08-26-9123"
    with pytest.raises(HTTPException, match="secuencia institucional"):
        suggest_certificate_folio(
            db,
            certificate_type="verification",
            issued_on=date(2026, 8, 24),
            manual_folio="MYCV-MANUAL",
        )


def test_verification_uses_shared_capture_quality_authentication_release_and_versions(db, mixed_order):
    actor, order, items = mixed_order
    equipment = create_equipment(
        db,
        EquipmentCreate(
            service_order_id=order.id,
            service_order_item_id=items["verification"].id,
            name="Vernier",
        ),
        user_id=actor.id,
    )
    certificate = db.scalar(select(Certificate).where(Certificate.equipment_id == equipment.id))
    sheet = FieldSheet(
        equipment_id=equipment.id,
        work_order_id=equipment.work_order_id,
        work_order_number=equipment.work_order_number,
        status="completed",
        calibration_date=date(2026, 8, 24),
    )
    db.add(sheet)
    db.flush()
    certificate.field_sheet_id = sheet.id
    equipment.certificate_master_document_id = 1
    equipment.certificate_master_version_id = 1
    equipment.certificate_template_path_snapshot = "masters/verification.xlsx"
    db.add(
        CertificateCaptureFile(
            certificate_id=certificate.id,
            service_order_id=order.id,
            original_filename="Master_MYCV-08-26-8000.xlsx",
            stored_path="capture/Master_MYCV-08-26-8000.xlsx",
            identification_status="identified",
            validation_results={},
            uploaded_by_id=actor.id,
        )
    )
    db.commit()

    assert start_capture(db, certificate.id, user_id=actor.id).status == "capture_in_progress"
    assert send_to_quality(db, certificate.id, user_id=actor.id).status == "quality_review"
    assert quality_approve(db, certificate.id, user_id=actor.id).status == "quality_approved"
    assert "authenticated" in ALLOWED_TRANSITIONS["quality_approved"]
    assert "released_to_client" in ALLOWED_TRANSITIONS["authenticated"]

    def authenticate(_db, item, *, user_id, origin):
        item.status = "authenticated"
        item.authentication_code = "MYC-AUTH-VERIFICATION-1"
        item.authenticated_pdf_path = "certificates/verification-authenticated.pdf"
        item.authenticated_by_id = user_id
        return item

    with patch.object(
        certificate_authentication,
        "_authenticate_certificate_pdf",
        side_effect=authenticate,
    ):
        authenticated = certificate_authentication.authenticate_certificate(
            db,
            certificate.id,
            user_id=actor.id,
            origin="quality",
        )
    assert authenticated.status == "authenticated"
    assert authenticated.certificate_type == "verification"
    with patch("app.services.certificates._authenticated_document_exists", return_value=True):
        released = release_to_client(db, certificate.id, user_id=actor.id)
    assert released.status == "released_to_client"

    now = datetime.now(timezone.utc)
    db.add_all(
        [
            CertificatePdfVersion(
                certificate_id=certificate.id,
                version_number=1,
                file_path="certificates/verification-v1.pdf",
                uploaded_at=now,
                is_current=False,
            ),
            CertificatePdfVersion(
                certificate_id=certificate.id,
                version_number=2,
                file_path="certificates/verification-v2.pdf",
                uploaded_at=now,
                is_current=True,
            ),
        ]
    )
    db.commit()
    versions = db.scalars(
        select(CertificatePdfVersion)
        .where(CertificatePdfVersion.certificate_id == certificate.id)
        .order_by(CertificatePdfVersion.version_number)
    ).all()
    assert [version.version_number for version in versions] == [1, 2]
    assert [version.is_current for version in versions] == [False, True]
