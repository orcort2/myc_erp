from __future__ import annotations

from datetime import date

from sqlalchemy import func, select, text
from sqlalchemy.orm import Session

from app.models.certificate import Certificate
from app.models.folio_sequence import InstitutionalFolioSequence
from app.models.service_order import ServiceOrder, ServiceWorkOrder
from app.schemas.service_type import ServiceType, normalize_certificate_prefix, normalize_service_type


def _initial_value(document_type: str, year: int) -> int:
    if year == 2026:
        return 7000 if document_type == "work_order" else 8000
    return 1000


def _existing_certificate_max(
    db: Session, *, prefix: str, issued_on: date
) -> int | None:
    values = db.scalars(
        select(Certificate.folio).where(Certificate.folio.like(f"{prefix}%"))
    ).all()
    compact_year_prefix = f"{prefix}{issued_on:%y}"
    verification_year_marker = f"-{issued_on:%y}-"
    sequences = []
    for value in values:
        if not value or len(value) < 4 or not value[-4:].isdigit():
            continue
        if value.startswith(compact_year_prefix) or (
            prefix == "MYCV" and verification_year_marker in value
        ):
            sequences.append(int(value[-4:]))
    return max(sequences) if sequences else None


def _existing_work_order_max(db: Session, *, year: int) -> int | None:
    if year != date.today().year:
        return None
    legacy = db.scalar(select(func.max(ServiceOrder.work_order_number)))
    normalized = db.scalar(select(func.max(ServiceWorkOrder.work_order_number)))
    values = [int(value) for value in (legacy, normalized) if value is not None]
    return max(values) if values else None


def allocate_sequence(
    db: Session,
    *,
    document_type: str,
    prefix: str,
    issued_on: date,
) -> int:
    normalized_prefix = normalize_certificate_prefix(prefix) or prefix.upper()
    key = f"{document_type}:{normalized_prefix}:{issued_on.year}"
    if db.bind is not None and db.bind.dialect.name == "postgresql":
        db.execute(text("SELECT pg_advisory_xact_lock(hashtext(:key))"), {"key": key})

    counter = db.scalar(
        select(InstitutionalFolioSequence)
        .where(
            InstitutionalFolioSequence.document_type == document_type,
            InstitutionalFolioSequence.prefix == normalized_prefix,
            InstitutionalFolioSequence.year == issued_on.year,
        )
        .with_for_update()
    )
    minimum = _initial_value(document_type, issued_on.year)
    existing_max = (
        _existing_work_order_max(db, year=issued_on.year)
        if document_type == "work_order"
        else _existing_certificate_max(db, prefix=normalized_prefix, issued_on=issued_on)
    )
    candidate = max(minimum, (existing_max + 1) if existing_max is not None else minimum)
    if counter is None:
        counter = InstitutionalFolioSequence(
            document_type=document_type,
            prefix=normalized_prefix,
            year=issued_on.year,
            next_value=candidate,
        )
        db.add(counter)
        db.flush()
    sequence = max(counter.next_value, candidate)
    counter.next_value = sequence + 1
    db.flush()
    return sequence


def build_certificate_folio(
    db: Session,
    *,
    service_type: str,
    issued_on: date,
    linked_prefix: str | None = None,
) -> str:
    normalized_type = normalize_service_type(service_type)
    if normalized_type is ServiceType.ACCREDITED:
        prefix = "MYCA"
    elif normalized_type is ServiceType.TRACEABLE:
        prefix = "MYCT"
    elif normalized_type is ServiceType.LINKED:
        prefix = normalize_certificate_prefix(linked_prefix)
        if prefix is None:
            raise ValueError("El servicio vinculado no tiene iniciales de certificado")
    elif service_type == "verification":
        prefix = "MYCV"
    else:
        raise ValueError("Tipo de servicio no reconocido")
    sequence = allocate_sequence(
        db,
        document_type="certificate",
        prefix=prefix,
        issued_on=issued_on,
    )
    if service_type == "verification":
        return f"{prefix}-{issued_on:%m}-{issued_on:%y}-{sequence:04d}"
    return f"{prefix}{issued_on:%y%m}{sequence:04d}"


def next_work_order_number(db: Session, *, issued_on: date | None = None) -> int:
    resolved_date = issued_on or date.today()
    return allocate_sequence(
        db,
        document_type="work_order",
        prefix="OT",
        issued_on=resolved_date,
    )
