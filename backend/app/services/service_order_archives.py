"""Archivo histórico recuperable de ETS eliminadas por un desbloqueo autorizado.

Única autoridad para construir, verificar y consultar ``ServiceOrderArchive``.
No restaura nada: la recuperación es administrativa y se limita a informar
conflictos (``restoration_conflicts``) para que una persona decida.
"""
from __future__ import annotations

import hashlib
import json
from datetime import date, datetime, timezone
from decimal import Decimal

from fastapi import HTTPException
from sqlalchemy import DateTime, Date, Numeric
from sqlalchemy import inspect as sa_inspect
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models.quotation import Quotation, QuotationSnapshot
from app.models.user import User
from app.models.quotation_acceptance import QuotationAcceptance
from app.models.quotation_service_change import QuotationServiceChangeRequest
from app.models.sale_execution import SaleOrderItem, SaleUnitState
from app.models.service_execution import ServiceStage, ServiceUnit
from app.models.service_order import ServiceOrder, ServiceOrderItem, ServiceWorkOrder
from app.models.service_order_archive import ARCHIVE_SCHEMA_VERSION, ServiceOrderArchive
from app.services.activity import publish_event
from app.services.audit_logs import write_audit_log
from app.services.auth import user_has_permission


def _json_value(value):
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    if isinstance(value, Decimal):
        return str(value)
    if isinstance(value, (bytes, bytearray)):
        # Los binarios nunca viajan en el archivo; sólo su huella.
        return {"sha256": hashlib.sha256(bytes(value)).hexdigest(), "bytes": len(value)}
    return value


def serialize_row(obj) -> dict:
    """Serializa las columnas de una fila ORM en un dict determinista y JSON-seguro."""
    mapper = sa_inspect(obj).mapper
    return {
        attr.key: _json_value(getattr(obj, attr.key))
        for attr in mapper.column_attrs
    }


def canonical_hash(data: dict) -> str:
    payload = json.dumps(data, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def build_archive_data(db: Session, order: ServiceOrder) -> dict:
    """Partidas, OT derivadas y proyección de Venta de la ETS que se eliminará."""
    items = db.scalars(
        select(ServiceOrderItem)
        .where(ServiceOrderItem.service_order_id == order.id)
        .order_by(ServiceOrderItem.id)
    ).all()
    work_orders = db.scalars(
        select(ServiceWorkOrder)
        .where(ServiceWorkOrder.service_order_id == order.id)
        .order_by(ServiceWorkOrder.id)
    ).all()
    sale_items = db.scalars(
        select(SaleOrderItem)
        .where(SaleOrderItem.service_order_id == order.id)
        .order_by(SaleOrderItem.id)
    ).all()
    sale_item_ids = [item.id for item in sale_items]
    sale_states = (
        db.scalars(
            select(SaleUnitState)
            .where(SaleUnitState.sale_order_item_id.in_(sale_item_ids))
            .order_by(SaleUnitState.id)
        ).all()
        if sale_item_ids
        else []
    )
    units = db.scalars(
        select(ServiceUnit)
        .where(ServiceUnit.service_order_id == order.id)
        .order_by(ServiceUnit.id)
    ).all()
    unit_ids = [unit.id for unit in units]
    stages = (
        db.scalars(
            select(ServiceStage)
            .where(ServiceStage.service_unit_id.in_(unit_ids))
            .order_by(ServiceStage.id)
        ).all()
        if unit_ids
        else []
    )
    return {
        "service_order": serialize_row(order),
        "items": [serialize_row(row) for row in items],
        "work_orders": [serialize_row(row) for row in work_orders],
        "sale_order_items": [serialize_row(row) for row in sale_items],
        "sale_unit_states": [serialize_row(row) for row in sale_states],
        "service_units": [serialize_row(row) for row in units],
        "service_stages": [serialize_row(row) for row in stages],
    }


def verify_archive_integrity(archive: ServiceOrderArchive) -> bool:
    return canonical_hash(archive.archive_data) == archive.integrity_hash


def archive_service_order(
    db: Session,
    *,
    order: ServiceOrder,
    quotation: Quotation,
    snapshot: QuotationSnapshot,
    acceptance: QuotationAcceptance | None,
    request: QuotationServiceChangeRequest,
    user_id: int,
    reason: str,
    deleted_at: datetime,
) -> ServiceOrderArchive:
    """Persiste el snapshot y comprueba, releyéndolo, que quedó íntegro.

    No hace ``commit``: la eliminación de la ETS sólo debe ocurrir después de que
    esta función regrese sin excepción, dentro de la misma transacción.
    """
    data = build_archive_data(db, order)
    archive = ServiceOrderArchive(
        original_service_order_id=order.id,
        service_order_folio=order.folio,
        quotation_id=quotation.id,
        quotation_folio=quotation.folio,
        accepted_snapshot_id=snapshot.id,
        accepted_snapshot_number=snapshot.snapshot_number,
        acceptance_id=acceptance.id if acceptance else None,
        previous_status=order.status,
        source_snapshot=order.source_snapshot,
        archive_data=data,
        exception_request_id=request.id,
        exception_folio=request.folio,
        deleted_by_id=user_id,
        reason=reason,
        deleted_at=deleted_at,
        schema_version=ARCHIVE_SCHEMA_VERSION,
        integrity_hash=canonical_hash(data),
    )
    db.add(archive)
    db.flush()
    stored = db.execute(
        select(ServiceOrderArchive.archive_data, ServiceOrderArchive.integrity_hash).where(
            ServiceOrderArchive.id == archive.id
        )
    ).one_or_none()
    if stored is None or canonical_hash(stored.archive_data) != stored.integrity_hash:
        raise HTTPException(
            status_code=500,
            detail="No fue posible verificar el archivo histórico de la ETS; no se aplicó ningún cambio",
        )
    return archive


def latest_archived_folio(db: Session, quotation_id: int) -> str | None:
    """Folio de la última ETS archivada de la cotización (continuidad al reaceptar)."""
    return db.scalar(
        select(ServiceOrderArchive.service_order_folio)
        .where(ServiceOrderArchive.quotation_id == quotation_id)
        .order_by(ServiceOrderArchive.id.desc())
        .limit(1)
    )


def archive_summary(archive: ServiceOrderArchive) -> dict:
    return {
        "id": archive.id,
        "service_order_folio": archive.service_order_folio,
        "original_service_order_id": archive.original_service_order_id,
        "quotation_id": archive.quotation_id,
        "quotation_folio": archive.quotation_folio,
        "accepted_snapshot_number": archive.accepted_snapshot_number,
        "acceptance_id": archive.acceptance_id,
        "previous_status": archive.previous_status,
        "exception_folio": archive.exception_folio,
        "deleted_by_id": archive.deleted_by_id,
        "reason": archive.reason,
        "deleted_at": archive.deleted_at,
        "schema_version": archive.schema_version,
        "integrity_hash": archive.integrity_hash,
        "integrity_ok": verify_archive_integrity(archive),
        "restored_at": archive.restored_at,
        "restored_by_id": archive.restored_by_id,
        "restoration_reason": archive.restoration_reason,
    }


def list_archives(db: Session, quotation_id: int) -> list[dict]:
    rows = db.scalars(
        select(ServiceOrderArchive)
        .where(ServiceOrderArchive.quotation_id == quotation_id)
        .order_by(ServiceOrderArchive.id.desc())
    ).all()
    return [archive_summary(row) for row in rows]


def get_archive(db: Session, archive_id: int) -> ServiceOrderArchive:
    archive = db.get(ServiceOrderArchive, archive_id)
    if archive is None:
        raise HTTPException(status_code=404, detail="Archivo de ETS no encontrado")
    return archive


def restoration_conflicts(db: Session, archive: ServiceOrderArchive) -> list[str]:
    """Por qué NO es seguro restaurar. Lista vacía = restaurable."""
    conflicts: list[str] = []
    if not verify_archive_integrity(archive):
        conflicts.append("El hash de integridad del archivo no coincide.")
    if archive.schema_version != ARCHIVE_SCHEMA_VERSION:
        conflicts.append("La versión de esquema del archivo no es compatible.")
    if archive.restored_at is not None:
        conflicts.append("El archivo ya fue marcado como recuperado.")
    if db.scalar(
        select(ServiceOrder.id).where(ServiceOrder.folio == archive.service_order_folio)
    ):
        conflicts.append(f"Ya existe una ETS con el folio {archive.service_order_folio}.")
    if db.scalar(select(ServiceOrder.id).where(ServiceOrder.id == archive.original_service_order_id)):
        conflicts.append("El identificador original de la ETS ya está en uso.")
    if db.scalar(
        select(ServiceOrder.id).where(
            ServiceOrder.quotation_id == archive.quotation_id,
            ServiceOrder.is_active.is_(True),
        )
    ):
        conflicts.append("La cotización ya tiene una ETS activa.")
    quotation = db.get(Quotation, archive.quotation_id)
    if quotation is None or quotation.status != "in_revision":
        conflicts.append("La cotización ya no está en revisión; su versión comercial cambió.")
    else:
        latest_id = db.scalar(
            select(QuotationSnapshot.id)
            .where(QuotationSnapshot.quotation_id == quotation.id)
            .order_by(QuotationSnapshot.snapshot_number.desc())
            .limit(1)
        )
        if latest_id != archive.accepted_snapshot_id:
            conflicts.append(
                "La cotización tiene versiones comerciales posteriores a la aceptada; "
                "la ETS archivada ya no corresponde."
            )
    current = db.scalar(
        select(QuotationAcceptance.id).where(
            QuotationAcceptance.quotation_id == archive.quotation_id,
            QuotationAcceptance.invalidated_at.is_(None),
        )
    )
    if current is not None:
        conflicts.append("La cotización ya tiene una aceptación vigente.")
    return conflicts


# Inserción respetando dependencias entre tablas archivadas.
_RESTORE_ORDER = (
    ("service_order", ServiceOrder),
    ("items", ServiceOrderItem),
    ("work_orders", ServiceWorkOrder),
    ("service_units", ServiceUnit),
    ("service_stages", ServiceStage),
    ("sale_order_items", SaleOrderItem),
    ("sale_unit_states", SaleUnitState),
)


def _deserialize_row(model, data: dict):
    values = {}
    for column in sa_inspect(model).mapper.column_attrs:
        if column.key not in data:
            continue
        value = data[column.key]
        column_type = column.columns[0].type
        if isinstance(value, dict) and set(value) == {"sha256", "bytes"}:
            raise HTTPException(
                status_code=409,
                detail="El archivo contiene binarios que no se almacenan; no puede restaurarse.",
            )
        if isinstance(value, str):
            if isinstance(column_type, DateTime):
                value = datetime.fromisoformat(value)
            elif isinstance(column_type, Date):
                value = date.fromisoformat(value)
            elif isinstance(column_type, Numeric):
                value = Decimal(value)
        values[column.key] = value
    return model(**values)


def restore_service_order(
    db: Session, archive_id: int, user: User, reason: str
) -> dict:
    """Restauración administrativa explícita: deshace un desbloqueo sin cambios posteriores.

    Una sola transacción: bloquea archivo y cotización, exige cero conflictos,
    reinserta la ETS con su id y folio originales, reactiva la aceptación que el
    desbloqueo invalidó y devuelve la cotización a ``accepted``.
    """
    for permission in (
        "quotations.exceptions.inspect",
        "quotations.exceptions.apply_unlock",
        "quotations.exceptions.rebuild_empty_service_order",
    ):
        if not user_has_permission(user, permission):
            raise HTTPException(status_code=403, detail=f"Falta el permiso {permission}")
    reason = (reason or "").strip()
    if len(reason) < 3:
        raise HTTPException(status_code=422, detail="Indica el motivo de la restauración")
    archive = db.scalar(
        select(ServiceOrderArchive)
        .where(ServiceOrderArchive.id == archive_id)
        .with_for_update()
        .execution_options(populate_existing=True)
    )
    if archive is None:
        raise HTTPException(status_code=404, detail="Archivo de ETS no encontrado")
    quotation = db.scalar(
        select(Quotation)
        .where(Quotation.id == archive.quotation_id)
        .with_for_update()
        .execution_options(populate_existing=True)
    )
    conflicts = restoration_conflicts(db, archive)
    if conflicts:
        raise HTTPException(status_code=409, detail={"message": "No se puede restaurar", "conflicts": conflicts})

    moment = datetime.now(timezone.utc)
    data = archive.archive_data
    try:
        for key, model in _RESTORE_ORDER:
            payload = data[key] if key == "service_order" else data.get(key, [])
            for row in ([payload] if key == "service_order" else payload):
                db.add(_deserialize_row(model, row))
            db.flush()
        reinstated = []
        if archive.acceptance_id is not None:
            acceptance = db.scalar(
                select(QuotationAcceptance)
                .where(QuotationAcceptance.id == archive.acceptance_id)
                .with_for_update()
            )
            if acceptance is not None:
                acceptance.invalidated_at = None
                acceptance.invalidated_by_id = None
                acceptance.invalidation_reason = None
                reinstated.append(acceptance.id)
        quotation.status = "accepted"
        archive.restored_at = moment
        archive.restored_by_id = user.id
        archive.restoration_reason = reason
        db.flush()
        publish_event(
            db,
            entity_type="quotation",
            entity_id=quotation.id,
            event_code="quotation.service_order_restored",
            idempotency_key=f"archive:{archive.id}:restored",
            body=(
                f"La ETS {archive.service_order_folio} fue restaurada desde el archivo "
                f"#{archive.id}; la cotización {quotation.folio} volvió a Aceptada."
            ),
            actor_id=user.id,
            metadata={
                "archive_id": archive.id,
                "service_order_folio": archive.service_order_folio,
                "reinstated_acceptance_ids": reinstated,
                "reason": reason,
            },
        )
        write_audit_log(
            db,
            action="quotation.service_order_restored",
            entity="quotations",
            entity_id=quotation.id,
            user_id=user.id,
            previous_values={"status": "in_revision"},
            new_values={
                "status": "accepted",
                "archive_id": archive.id,
                "service_order_folio": archive.service_order_folio,
                "reinstated_acceptance_ids": reinstated,
                "reason": reason,
            },
        )
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=409,
            detail="No fue posible restaurar atómicamente la ETS; no se aplicó ningún cambio",
        )
    except Exception:
        db.rollback()
        raise
    return archive_summary(archive)
