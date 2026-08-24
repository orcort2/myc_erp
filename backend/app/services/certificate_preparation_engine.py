from __future__ import annotations

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.certificate import Certificate
from app.models.equipment import Equipment
from app.models.field_sheet import FieldSheet
from app.schemas.certificate import CertificateCreate
from app.schemas.operational_engine import CertificatePreparationResult, EngineMessage
from app.services.audit_logs import write_audit_log
from app.services.certificates import create_certificate, get_certificate
from app.services.service_order_certificate_capacity import certificate_type_for_equipment


def _message(severity: str, code: str, message: str) -> EngineMessage:
    return EngineMessage(severity=severity, code=code, message=message)


def prepare_certificate_from_field_sheet(
    db: Session,
    field_sheet_id: int,
    *,
    user_id: int | None = None,
) -> CertificatePreparationResult:
    field_sheet = db.get(FieldSheet, field_sheet_id)
    if field_sheet is None or not field_sheet.is_active:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Hoja de campo no encontrada",
        )
    if field_sheet.status not in {"completed", "under_review", "approved"}:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="La hoja debe estar completada o en revision para preparar certificado",
        )

    existing_id = db.scalar(
        select(Certificate.id).where(
            Certificate.field_sheet_id == field_sheet.id,
            Certificate.is_active.is_(True),
        )
    )
    if existing_id is not None:
        certificate = get_certificate(db, existing_id)
        return CertificatePreparationResult(
            certificate_id=certificate.id,
            folio=certificate.folio,
            status=certificate.status,
            created=False,
            messages=[
                _message(
                    "ADVERTENCIA",
                    "certificate_already_exists",
                    "La hoja ya tenia un certificado activo; se devolvio el existente.",
                )
            ],
        )

    equipment = db.get(Equipment, field_sheet.equipment_id)
    if equipment is None or not equipment.is_active:
        raise HTTPException(status_code=404, detail="Equipo no encontrado")
    procedure = field_sheet.calibration_procedure
    certificate_type = certificate_type_for_equipment(db, equipment)
    if certificate_type is None:
        raise HTTPException(status_code=422, detail="El equipo no pertenece a un proceso metrológico")
    payload = CertificateCreate(
        service_order_id=equipment.service_order_id,
        equipment_id=equipment.id,
        field_sheet_id=field_sheet.id,
        certificate_type=(
            certificate_type
            if certificate_type == "verification"
            else procedure.certificate_type if procedure else certificate_type
        ),
        issued_on=field_sheet.calibration_date,
        title=(
            f"Certificado de Verificación - {equipment.name}"
            if certificate_type == "verification"
            else f"Certificado de calibración - {equipment.name}"
        ),
        notes="Preparado automaticamente por motor documental.",
    )
    certificate = create_certificate(db, payload, user_id=user_id)
    write_audit_log(
        db,
        action="engine.certificate_prepared",
        entity="certificates",
        entity_id=certificate.id,
        user_id=user_id,
        new_values={
            "field_sheet_id": field_sheet.id,
            "equipment_id": equipment.id,
            "service_order_id": equipment.service_order_id,
            "folio": certificate.folio,
        },
    )
    db.commit()
    return CertificatePreparationResult(
        certificate_id=certificate.id,
        folio=certificate.folio,
        status=certificate.status,
        created=True,
        messages=[
            _message("VALIDO", "certificate_prepared", "Certificado draft preparado correctamente.")
        ],
    )
