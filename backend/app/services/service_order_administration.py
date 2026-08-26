"""Operaciones propietarias y transaccionales para resoluciones administrativas de ETS."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.certificate import Certificate, CertificateCaptureFile
from app.models.equipment import Equipment
from app.models.invoice import Invoice
from app.models.quotation import Quotation
from app.models.service_order import ServiceOrder, ServiceWorkOrder
from app.schemas.service_order import ServiceOrderCreate
from app.services.activity import publish_event
from app.services.audit_logs import write_audit_log
from app.services.service_orders import create_service_order


class ServiceOrderAdministrationError(RuntimeError):
    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code


@dataclass(frozen=True, slots=True)
class ServiceOrderAdministrationResult:
    operation: str
    service_order_id: int
    service_order_folio: str
    quotation_id: int | None
    before_snapshot: dict
    after_snapshot: dict
    domain_transaction_reference: str
    created: bool = False


def _count(session: Session, model, criterion) -> int:
    return int(session.scalar(select(func.count()).select_from(model).where(criterion)) or 0)


def dependency_counts(session: Session, service_order_id: int) -> dict[str, int]:
    """Dependencias que vuelven insegura una baja/restauración automática."""
    from app.models.service_order import ServiceOrderSignatureCycle
    from app.services.sale_execution import count_non_pristine_sale_dependencies

    return {
        "equipment": _count(session, Equipment, Equipment.service_order_id == service_order_id),
        "certificates": _count(session, Certificate, Certificate.service_order_id == service_order_id),
        "capture_files": _count(session, CertificateCaptureFile, CertificateCaptureFile.service_order_id == service_order_id),
        "invoices": _count(session, Invoice, Invoice.service_order_id == service_order_id),
        "signature_cycles": _count(session, ServiceOrderSignatureCycle, ServiceOrderSignatureCycle.service_order_id == service_order_id),
        "sale_execution": count_non_pristine_sale_dependencies(session, service_order_id),
    }


def execute_service_order_administration(
    session: Session,
    *,
    operation: str,
    subject_id: int,
    reason: str,
    expected_service_order_id: int | None,
    expected_active_sibling_id: int | None,
    expected_updated_at: str | None,
    resolution_id: int,
    request_hash: str,
    actor_id: int,
) -> ServiceOrderAdministrationResult:
    if operation == "rebuild":
        return _rebuild(
            session,
            quotation_id=subject_id,
            reason=reason,
            expected_active_sibling_id=expected_active_sibling_id,
            expected_updated_at=expected_updated_at,
            resolution_id=resolution_id,
            request_hash=request_hash,
            actor_id=actor_id,
        )
    order = session.scalar(
        select(ServiceOrder).where(ServiceOrder.id == subject_id).with_for_update()
    )
    if order is None or order.id != expected_service_order_id:
        raise ServiceOrderAdministrationError("service_order_changed", "El ETS ya no coincide con el expediente autorizado")
    current_updated_at = order.updated_at.isoformat() if order.updated_at else None
    if expected_updated_at and current_updated_at != expected_updated_at:
        raise ServiceOrderAdministrationError("service_order_changed", "El ETS cambió después de la autorización")
    if operation == "restore":
        return _restore(session, order, reason, resolution_id, request_hash, actor_id)
    if operation == "void":
        return _void(session, order, reason, resolution_id, request_hash, actor_id)
    raise ServiceOrderAdministrationError("invalid_operation", "Operación administrativa desconocida")


def _snapshot(order: ServiceOrder) -> dict:
    return {
        "id": order.id,
        "folio": order.folio,
        "quotation_id": order.quotation_id,
        "status": order.status,
        "is_active": order.is_active,
        "deleted_at": order.deleted_at.isoformat() if order.deleted_at else None,
        "work_orders": [
            {"id": item.id, "status": item.status, "is_active": item.is_active}
            for item in order.work_orders
        ],
    }


def _active_sibling(session: Session, order: ServiceOrder) -> int | None:
    if order.quotation_id is None:
        return None
    return session.scalar(
        select(ServiceOrder.id).where(
            ServiceOrder.quotation_id == order.quotation_id,
            ServiceOrder.is_active.is_(True),
            ServiceOrder.id != order.id,
        ).order_by(ServiceOrder.id)
    )


def _assert_pristine(session: Session, order: ServiceOrder) -> None:
    blockers = {key: value for key, value in dependency_counts(session, order.id).items() if value}
    if blockers or order.status != "scheduled":
        detail = ", ".join(f"{key}:{value}" for key, value in blockers.items())
        if order.status != "scheduled":
            detail = f"{detail}, status:{order.status}".strip(", ")
        raise ServiceOrderAdministrationError("operational_dependencies", f"El ETS conserva dependencias operativas: {detail}")


def _restore(session, order, reason, resolution_id, request_hash, actor_id):
    if order.is_active:
        return ServiceOrderAdministrationResult("restore", order.id, order.folio, order.quotation_id, _snapshot(order), _snapshot(order), f"service-order:{order.id}:already-active")
    if _active_sibling(session, order) is not None:
        raise ServiceOrderAdministrationError("active_sibling_exists", "La cotización ya tiene otro ETS activo")
    _assert_pristine(session, order)
    before = _snapshot(order)
    order.is_active = True
    order.deleted_at = None
    order.deleted_by = None
    for work_order in order.work_orders:
        work_order.is_active = True
        work_order.deleted_at = None
        work_order.deleted_by = None
        if work_order.status == "cancelled":
            work_order.status = "pending"
    session.flush()
    after = _snapshot(order)
    _record(session, order, "restored", reason, before, after, resolution_id, request_hash, actor_id)
    return ServiceOrderAdministrationResult("restore", order.id, order.folio, order.quotation_id, before, after, f"service-order:{order.id}:resolution:{resolution_id}")


def _void(session, order, reason, resolution_id, request_hash, actor_id):
    if not order.is_active:
        return ServiceOrderAdministrationResult("void", order.id, order.folio, order.quotation_id, _snapshot(order), _snapshot(order), f"service-order:{order.id}:already-inactive")
    _assert_pristine(session, order)
    before = _snapshot(order)
    now = datetime.now(timezone.utc)
    order.is_active = False
    order.deleted_at = now
    order.deleted_by = actor_id
    # No se destruye el estado de las OT: sólo se retiran de la operación visible.
    for work_order in order.work_orders:
        work_order.is_active = False
        work_order.deleted_at = now
        work_order.deleted_by = actor_id
    session.flush()
    after = _snapshot(order)
    _record(session, order, "voided", reason, before, after, resolution_id, request_hash, actor_id)
    return ServiceOrderAdministrationResult("void", order.id, order.folio, order.quotation_id, before, after, f"service-order:{order.id}:resolution:{resolution_id}")


def _rebuild(session, *, quotation_id, reason, expected_active_sibling_id, expected_updated_at, resolution_id, request_hash, actor_id):
    quotation = session.scalar(select(Quotation).where(Quotation.id == quotation_id).with_for_update())
    if quotation is None or not quotation.is_active or quotation.status != "accepted":
        raise ServiceOrderAdministrationError("quotation_not_accepted", "La cotización no existe, está inactiva o no está aceptada")
    current_updated_at = quotation.updated_at.isoformat() if quotation.updated_at else None
    if expected_updated_at and current_updated_at != expected_updated_at:
        raise ServiceOrderAdministrationError("quotation_changed", "La cotización cambió después de la autorización")
    orders = tuple(session.scalars(select(ServiceOrder).where(ServiceOrder.quotation_id == quotation.id).order_by(ServiceOrder.id)).all())
    active = next((item for item in orders if item.is_active), None)
    if active is not None:
        if expected_active_sibling_id not in {None, active.id}:
            raise ServiceOrderAdministrationError("active_sibling_changed", "El ETS activo cambió")
        return ServiceOrderAdministrationResult("rebuild", active.id, active.folio, quotation.id, _snapshot(active), _snapshot(active), f"service-order:{active.id}:already-materialized", created=False)
    if orders:
        raise ServiceOrderAdministrationError("restorable_service_order_exists", "Existe un ETS inactivo; debe evaluarse Restaurar ETS, no reconstruirlo")
    order = create_service_order(
        session,
        ServiceOrderCreate(
            client_id=quotation.client_id,
            quotation_id=quotation.id,
            advisor_id=quotation.advisor_id,
            notes=f"ETS reconstruido administrativamente desde {quotation.folio}: {reason}",
        ),
        user_id=actor_id,
        commit=False,
    )
    session.flush()
    after = _snapshot(order)
    _record(session, order, "rebuilt", reason, {}, after, resolution_id, request_hash, actor_id)
    return ServiceOrderAdministrationResult("rebuild", order.id, order.folio, quotation.id, {}, after, f"service-order:{order.id}:resolution:{resolution_id}", created=True)


def _record(session, order, action, reason, before, after, resolution_id, request_hash, actor_id):
    write_audit_log(
        session,
        action=f"service_order.administration.{action}",
        entity="service_orders",
        entity_id=order.id,
        user_id=actor_id,
        previous_values=before,
        new_values={**after, "resolution_id": resolution_id, "request_hash": request_hash},
        comment=reason,
    )
    publish_event(
        session,
        entity_type="service_order",
        entity_id=order.id,
        event_code=f"service_order.administration.{action}",
        idempotency_key=f"resolution:{resolution_id}:service_order:{order.id}:{action}",
        body=f"ETS {order.folio}: operación administrativa {action}.",
        actor_id=actor_id,
        metadata={"resolution_id": resolution_id, "reason": reason},
        related_entity_type="quotation" if order.quotation_id else None,
        related_entity_id=order.quotation_id,
    )
