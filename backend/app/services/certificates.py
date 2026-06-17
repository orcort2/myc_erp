from datetime import date, datetime, timezone

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.folios import FolioRequest, generate_folio
from app.models.certificate import Certificate
from app.models.equipment import Equipment
from app.models.field_sheet import FieldSheet
from app.models.service_order import ServiceOrder
from app.schemas.certificate import (
    CertificateCreate,
    CertificateStatusChange,
    CertificateUpdate,
)
from app.services.audit_logs import write_audit_log


TERMINAL_STATUSES = {"released", "cancelled"}
ALLOWED_TRANSITIONS = {
    "draft": {"generated", "cancelled", "suspended"},
    "generated": {"quality_review", "cancelled", "suspended"},
    "quality_review": {"approved", "cancelled", "suspended"},
    "approved": {"released", "suspended"},
    "released": set(),
    "cancelled": set(),
    "suspended": {"draft", "cancelled"},
}


def _next_certificate_folio(
    db: Session, *, certificate_type: str, issued_on: date
) -> str:
    service_type = "acreditado" if certificate_type == "acreditado" else "trazable"
    prefix = "MYCA" if service_type == "acreditado" else "MYCT"
    prefix = f"{prefix}-{issued_on:%m}-{issued_on:%Y}-"
    last_folio = db.scalar(
        select(Certificate.folio)
        .where(Certificate.folio.like(f"{prefix}%"))
        .order_by(Certificate.folio.desc())
        .limit(1)
    )
    sequence = 1 if not last_folio else int(last_folio.rsplit("-", 1)[-1]) + 1
    return generate_folio(
        FolioRequest(
            document_type="certificado",
            service_type=service_type,
            issued_on=issued_on,
            sequence=sequence,
        )
    )


def _validate_certificate_links(db: Session, payload: CertificateCreate) -> None:
    service_order = db.scalar(
        select(ServiceOrder).where(
            ServiceOrder.id == payload.service_order_id,
            ServiceOrder.is_active.is_(True),
        )
    )
    if service_order is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Orden de servicio no encontrada",
        )
    if service_order.status in {"closed", "cancelled"}:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="No se puede crear certificado para una orden cerrada o cancelada",
        )

    equipment = db.scalar(
        select(Equipment).where(
            Equipment.id == payload.equipment_id,
            Equipment.is_active.is_(True),
        )
    )
    if equipment is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Equipo no encontrado",
        )
    if equipment.service_order_id != payload.service_order_id:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="El equipo no pertenece a la orden de servicio indicada",
        )
    if equipment.status not in {"calibrated", "labeled"}:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="El equipo debe estar calibrado antes de generar certificado",
        )

    field_sheet = db.scalar(
        select(FieldSheet).where(
            FieldSheet.id == payload.field_sheet_id,
            FieldSheet.is_active.is_(True),
        )
    )
    if field_sheet is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Hoja de campo no encontrada",
        )
    if field_sheet.equipment_id != payload.equipment_id:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="La hoja de campo no pertenece al equipo indicado",
        )
    if field_sheet.status not in {"completed", "under_review", "approved"}:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="La hoja de campo debe estar completada para generar certificado",
        )


def _ensure_no_active_certificate(db: Session, field_sheet_id: int) -> None:
    exists = db.scalar(
        select(Certificate.id).where(
            Certificate.field_sheet_id == field_sheet_id,
            Certificate.is_active.is_(True),
        )
    )
    if exists is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="La hoja de campo ya tiene un certificado activo",
        )


def list_certificates(
    db: Session,
    *,
    service_order_id: int | None = None,
    equipment_id: int | None = None,
    include_inactive: bool = False,
) -> list[Certificate]:
    query = select(Certificate).order_by(Certificate.created_at.desc())
    if service_order_id is not None:
        query = query.where(Certificate.service_order_id == service_order_id)
    if equipment_id is not None:
        query = query.where(Certificate.equipment_id == equipment_id)
    if not include_inactive:
        query = query.where(Certificate.is_active.is_(True))
    return list(db.scalars(query).all())


def get_certificate(db: Session, certificate_id: int) -> Certificate:
    certificate = db.scalar(select(Certificate).where(Certificate.id == certificate_id))
    if certificate is None or not certificate.is_active:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Certificado no encontrado",
        )
    return certificate


def create_certificate(
    db: Session, payload: CertificateCreate, *, user_id: int | None = None
) -> Certificate:
    _validate_certificate_links(db, payload)
    _ensure_no_active_certificate(db, payload.field_sheet_id)
    issued_on = payload.issued_on or date.today()
    certificate = Certificate(
        **payload.model_dump(exclude={"issued_on"}),
        folio=_next_certificate_folio(
            db,
            certificate_type=payload.certificate_type,
            issued_on=issued_on,
        ),
        issued_on=issued_on,
        status="draft",
    )
    db.add(certificate)
    db.flush()
    write_audit_log(
        db,
        action="certificate.created",
        entity="certificates",
        entity_id=certificate.id,
        user_id=user_id,
        new_values={
            "folio": certificate.folio,
            "service_order_id": certificate.service_order_id,
            "equipment_id": certificate.equipment_id,
            "field_sheet_id": certificate.field_sheet_id,
            "status": certificate.status,
        },
    )
    db.commit()
    return get_certificate(db, certificate.id)


def update_certificate(
    db: Session,
    certificate_id: int,
    payload: CertificateUpdate,
    *,
    user_id: int | None = None,
) -> Certificate:
    certificate = get_certificate(db, certificate_id)
    if certificate.status in TERMINAL_STATUSES:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="No se puede editar un certificado liberado o cancelado",
        )
    updates = payload.model_dump(exclude_unset=True)
    previous_values = {key: getattr(certificate, key) for key in updates}
    for key, value in updates.items():
        setattr(certificate, key, value)
    write_audit_log(
        db,
        action="certificate.updated",
        entity="certificates",
        entity_id=certificate.id,
        user_id=user_id,
        previous_values={
            key: value.isoformat() if isinstance(value, date) else value
            for key, value in previous_values.items()
        },
        new_values={
            key: value.isoformat() if isinstance(value, date) else value
            for key, value in updates.items()
        },
    )
    db.commit()
    return get_certificate(db, certificate.id)


def change_status(
    db: Session,
    certificate_id: int,
    new_status: str,
    payload: CertificateStatusChange | None = None,
    *,
    user_id: int | None = None,
) -> Certificate:
    certificate = get_certificate(db, certificate_id)
    allowed = ALLOWED_TRANSITIONS.get(certificate.status, set())
    if new_status not in allowed:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Transicion no permitida: {certificate.status} -> {new_status}",
        )
    previous_status = certificate.status
    certificate.status = new_status
    if new_status == "released":
        certificate.released_on = date.today()
    write_audit_log(
        db,
        action=f"certificate.{new_status}",
        entity="certificates",
        entity_id=certificate.id,
        user_id=user_id,
        previous_values={"status": previous_status},
        new_values={"status": new_status},
        comment=payload.comment if payload else None,
    )
    db.commit()
    return get_certificate(db, certificate.id)


def deactivate_certificate(
    db: Session, certificate_id: int, *, user_id: int | None = None
) -> Certificate:
    certificate = get_certificate(db, certificate_id)
    if certificate.status == "released":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="No se puede cancelar por borrado logico un certificado liberado",
        )
    certificate.is_active = False
    certificate.status = "cancelled"
    certificate.deleted_at = datetime.now(timezone.utc)
    certificate.deleted_by = user_id
    write_audit_log(
        db,
        action="certificate.deactivated",
        entity="certificates",
        entity_id=certificate.id,
        user_id=user_id,
        previous_values={"is_active": True},
        new_values={"is_active": False, "status": "cancelled"},
    )
    db.commit()
    return certificate
