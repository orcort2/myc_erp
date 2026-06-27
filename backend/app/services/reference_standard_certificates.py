from __future__ import annotations

from datetime import date, datetime, timezone

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.models.controlled_document import ControlledDocument, ControlledDocumentVersion
from app.models.reference_standard import ReferenceStandard
from app.models.reference_standard_certificate import (
    ReferenceStandardCertificate,
    ReferenceStandardCertificateUncertainty,
)
from app.schemas.reference_standard_certificate import (
    ReferenceStandardCertificateCreate,
    ReferenceStandardCertificateUncertaintyCreate,
    ReferenceStandardCertificateUncertaintyUpdate,
    ReferenceStandardCertificateUpdate,
)
from app.services.audit_logs import write_audit_log


def _with_relations():
    return (
        selectinload(ReferenceStandardCertificate.reference_standard),
        selectinload(ReferenceStandardCertificate.uncertainties),
    )


def _json_safe(value):
    if hasattr(value, "isoformat"):
        return value.isoformat()
    if isinstance(value, dict):
        return {key: _json_safe(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_json_safe(item) for item in value]
    return value


def _serialize_uncertainty(item: ReferenceStandardCertificateUncertainty | None) -> dict | None:
    if item is None:
        return None
    return {
        "id": item.id,
        "range_min": float(item.range_min) if item.range_min is not None else None,
        "range_max": float(item.range_max) if item.range_max is not None else None,
        "unit": item.unit,
        "uncertainty_value": float(item.uncertainty_value),
        "uncertainty_unit": item.uncertainty_unit,
        "k_factor": float(item.k_factor) if item.k_factor is not None else None,
        "is_active": item.is_active,
    }


def _serialize_certificate(item: ReferenceStandardCertificate) -> dict:
    return {
        "id": item.id,
        "reference_standard_id": item.reference_standard_id,
        "certificate_number": item.certificate_number,
        "status": item.status,
        "effective_status": item.effective_status,
        "is_current": item.is_current,
        "expiration_date": item.expiration_date.isoformat() if item.expiration_date else None,
        "uncertainties_count": len([row for row in item.uncertainties if row.is_active]),
    }


def _ensure_document_links(
    db: Session,
    *,
    controlled_document_id: int | None,
    controlled_document_version_id: int | None,
) -> None:
    if controlled_document_id is not None and db.get(ControlledDocument, controlled_document_id) is None:
        raise HTTPException(status_code=422, detail="Documento controlado no encontrado")
    if controlled_document_version_id is not None:
        version = db.get(ControlledDocumentVersion, controlled_document_version_id)
        if version is None:
            raise HTTPException(status_code=422, detail="Version documental no encontrada")
        if controlled_document_id is not None and version.document_id != controlled_document_id:
            raise HTTPException(status_code=422, detail="La version no pertenece al documento")


def _ensure_standard(db: Session, standard_id: int) -> ReferenceStandard:
    standard = db.get(ReferenceStandard, standard_id)
    if standard is None or not standard.is_active:
        raise HTTPException(status_code=404, detail="Patron no encontrado")
    return standard


def list_certificates(
    db: Session,
    *,
    reference_standard_id: int | None = None,
    status: str | None = None,
    is_current: bool | None = None,
) -> list[ReferenceStandardCertificate]:
    query = select(ReferenceStandardCertificate).options(*_with_relations()).order_by(
        ReferenceStandardCertificate.created_at.desc(),
        ReferenceStandardCertificate.id.desc(),
    )
    if reference_standard_id is not None:
        query = query.where(ReferenceStandardCertificate.reference_standard_id == reference_standard_id)
    if status:
        query = query.where(ReferenceStandardCertificate.status == status)
    if is_current is not None:
        query = query.where(ReferenceStandardCertificate.is_current.is_(is_current))
    return list(db.scalars(query).all())


def get_certificate(db: Session, certificate_id: int) -> ReferenceStandardCertificate:
    certificate = db.scalar(
        select(ReferenceStandardCertificate)
        .where(ReferenceStandardCertificate.id == certificate_id)
        .options(*_with_relations())
    )
    if certificate is None:
        raise HTTPException(status_code=404, detail="Certificado de patron no encontrado")
    return certificate


def create_certificate(
    db: Session,
    reference_standard_id: int,
    payload: ReferenceStandardCertificateCreate,
    *,
    user_id: int | None = None,
) -> ReferenceStandardCertificate:
    _ensure_standard(db, reference_standard_id)
    _ensure_document_links(
        db,
        controlled_document_id=payload.controlled_document_id,
        controlled_document_version_id=payload.controlled_document_version_id,
    )
    certificate = ReferenceStandardCertificate(
        **payload.model_dump(exclude={"uncertainties", "status"}),
        reference_standard_id=reference_standard_id,
        status="draft",
        created_by_id=user_id,
    )
    certificate.uncertainties = [
        ReferenceStandardCertificateUncertainty(**item.model_dump())
        for item in payload.uncertainties
    ]
    db.add(certificate)
    db.flush()
    write_audit_log(
        db,
        action="reference_standard_certificate.created",
        entity="reference_standard_certificates",
        entity_id=certificate.id,
        user_id=user_id,
        new_values=_serialize_certificate(certificate),
    )
    if payload.status == "active":
        _activate_certificate(db, certificate, user_id=user_id)
    db.commit()
    return get_certificate(db, certificate.id)


def update_certificate(
    db: Session,
    certificate_id: int,
    payload: ReferenceStandardCertificateUpdate,
    *,
    user_id: int | None = None,
) -> ReferenceStandardCertificate:
    certificate = get_certificate(db, certificate_id)
    updates = payload.model_dump(exclude_unset=True)
    _ensure_document_links(
        db,
        controlled_document_id=updates.get("controlled_document_id", certificate.controlled_document_id),
        controlled_document_version_id=updates.get(
            "controlled_document_version_id", certificate.controlled_document_version_id
        ),
    )
    previous = _serialize_certificate(certificate)
    requested_active = updates.pop("status", None) == "active"
    for key, value in updates.items():
        setattr(certificate, key, value)
    if requested_active:
        _activate_certificate(db, certificate, user_id=user_id)
    write_audit_log(
        db,
        action="reference_standard_certificate.updated",
        entity="reference_standard_certificates",
        entity_id=certificate.id,
        user_id=user_id,
        previous_values=previous,
        new_values=_serialize_certificate(certificate),
    )
    db.commit()
    return get_certificate(db, certificate.id)


def _activate_certificate(
    db: Session,
    certificate: ReferenceStandardCertificate,
    *,
    user_id: int | None = None,
) -> None:
    if certificate.expiration_date and certificate.expiration_date < date.today():
        raise HTTPException(status_code=409, detail="No se puede activar un certificado vencido")
    siblings = list(
        db.scalars(
            select(ReferenceStandardCertificate).where(
                ReferenceStandardCertificate.reference_standard_id == certificate.reference_standard_id,
                ReferenceStandardCertificate.id != certificate.id,
            )
        ).all()
    )
    for sibling in siblings:
        if sibling.is_current:
            sibling.is_current = False
        if sibling.status == "active":
            sibling.status = "obsolete"
    certificate.status = "active"
    certificate.is_current = True
    certificate.approved_by_id = user_id
    certificate.approved_at = datetime.now(timezone.utc)
    write_audit_log(
        db,
        action="reference_standard_certificate.activated",
        entity="reference_standard_certificates",
        entity_id=certificate.id,
        user_id=user_id,
        new_values=_serialize_certificate(certificate),
    )


def activate_certificate(
    db: Session,
    certificate_id: int,
    *,
    user_id: int | None = None,
) -> ReferenceStandardCertificate:
    certificate = get_certificate(db, certificate_id)
    _activate_certificate(db, certificate, user_id=user_id)
    db.commit()
    return get_certificate(db, certificate.id)


def suspend_certificate(
    db: Session,
    certificate_id: int,
    *,
    user_id: int | None = None,
) -> ReferenceStandardCertificate:
    certificate = get_certificate(db, certificate_id)
    previous = _serialize_certificate(certificate)
    certificate.status = "suspended"
    certificate.is_current = False
    write_audit_log(
        db,
        action="reference_standard_certificate.suspended",
        entity="reference_standard_certificates",
        entity_id=certificate.id,
        user_id=user_id,
        previous_values=previous,
        new_values=_serialize_certificate(certificate),
    )
    db.commit()
    return get_certificate(db, certificate.id)


def add_certificate_uncertainty(
    db: Session,
    certificate_id: int,
    payload: ReferenceStandardCertificateUncertaintyCreate,
    *,
    user_id: int | None = None,
) -> ReferenceStandardCertificate:
    certificate = get_certificate(db, certificate_id)
    row = ReferenceStandardCertificateUncertainty(certificate_id=certificate.id, **payload.model_dump())
    db.add(row)
    db.flush()
    write_audit_log(
        db,
        action="reference_standard_certificate.uncertainty.created",
        entity="reference_standard_certificate_uncertainties",
        entity_id=row.id,
        user_id=user_id,
        new_values=_serialize_uncertainty(row),
    )
    db.commit()
    return get_certificate(db, certificate.id)


def update_certificate_uncertainty(
    db: Session,
    uncertainty_id: int,
    payload: ReferenceStandardCertificateUncertaintyUpdate,
    *,
    user_id: int | None = None,
) -> ReferenceStandardCertificate:
    row = db.get(ReferenceStandardCertificateUncertainty, uncertainty_id)
    if row is None or not row.is_active:
        raise HTTPException(status_code=404, detail="Incertidumbre de certificado no encontrada")
    previous = _serialize_uncertainty(row)
    for key, value in payload.model_dump(exclude_unset=True).items():
        setattr(row, key, value)
    write_audit_log(
        db,
        action="reference_standard_certificate.uncertainty.updated",
        entity="reference_standard_certificate_uncertainties",
        entity_id=row.id,
        user_id=user_id,
        previous_values=previous,
        new_values=_serialize_uncertainty(row),
    )
    db.commit()
    return get_certificate(db, row.certificate_id)


def deactivate_certificate_uncertainty(
    db: Session,
    uncertainty_id: int,
    *,
    user_id: int | None = None,
) -> ReferenceStandardCertificate:
    row = db.get(ReferenceStandardCertificateUncertainty, uncertainty_id)
    if row is None or not row.is_active:
        raise HTTPException(status_code=404, detail="Incertidumbre de certificado no encontrada")
    previous = _serialize_uncertainty(row)
    row.is_active = False
    write_audit_log(
        db,
        action="reference_standard_certificate.uncertainty.deactivated",
        entity="reference_standard_certificate_uncertainties",
        entity_id=row.id,
        user_id=user_id,
        previous_values=previous,
        new_values=_serialize_uncertainty(row),
    )
    db.commit()
    return get_certificate(db, row.certificate_id)


def get_current_certificate_for_standard(
    db: Session,
    reference_standard_id: int,
) -> ReferenceStandardCertificate | None:
    return db.scalar(
        select(ReferenceStandardCertificate)
        .where(
            ReferenceStandardCertificate.reference_standard_id == reference_standard_id,
            ReferenceStandardCertificate.is_current.is_(True),
            ReferenceStandardCertificate.status == "active",
        )
        .options(*_with_relations())
    )


def get_applicable_uncertainty(
    certificate: ReferenceStandardCertificate,
    *,
    value: float | None = None,
    range_min: float | None = None,
    range_max: float | None = None,
    unit: str | None = None,
) -> ReferenceStandardCertificateUncertainty | None:
    target_min = value if value is not None else range_min
    target_max = value if value is not None else range_max
    candidates = [item for item in certificate.uncertainties if item.is_active]
    if unit:
        unit_candidates = [item for item in candidates if not item.unit or item.unit == unit]
        candidates = unit_candidates or candidates
    matched = []
    for item in candidates:
        item_min = float(item.range_min) if item.range_min is not None else None
        item_max = float(item.range_max) if item.range_max is not None else None
        if target_min is not None and item_min is not None and target_min < item_min:
            continue
        if target_max is not None and item_max is not None and target_max > item_max:
            continue
        matched.append(item)
    if not matched:
        return None
    return sorted(
        matched,
        key=lambda item: (
            float(item.uncertainty_value),
            (
                (float(item.range_max) if item.range_max is not None else float("inf"))
                - (float(item.range_min) if item.range_min is not None else 0)
            ),
        ),
    )[0]
