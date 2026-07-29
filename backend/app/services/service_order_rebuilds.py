from __future__ import annotations

from dataclasses import asdict, dataclass

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.certificate import Certificate, CertificateCaptureFile
from app.models.equipment import Equipment
from app.models.invoice import Invoice
from app.models.service_order import (
    ServiceOrder,
    ServiceOrderSignatureCycle,
    ServiceWorkOrder,
)
from app.resolution_engine.infrastructure.persistence import ResolutionEntityReference


@dataclass(frozen=True)
class RebuildDependency:
    code: str
    label: str
    count: int


@dataclass(frozen=True)
class ServiceOrderRebuildValidation:
    allowed: bool
    blockers: tuple[str, ...]
    dependencies: tuple[RebuildDependency, ...]

    def to_dict(self) -> dict:
        return {
            "allowed": self.allowed,
            "blockers": list(self.blockers),
            "dependencies": [asdict(item) for item in self.dependencies],
        }


def _count(db: Session, model, criterion) -> int:
    return int(db.scalar(select(func.count()).select_from(model).where(criterion)) or 0)


def can_physically_rebuild_service_order(
    db: Session, service_order: ServiceOrder
) -> ServiceOrderRebuildValidation:
    dependencies: list[RebuildDependency] = []

    def add(code: str, label: str, count: int) -> None:
        if count:
            dependencies.append(RebuildDependency(code, label, count))

    add(
        "equipment",
        "equipos",
        _count(db, Equipment, Equipment.service_order_id == service_order.id),
    )
    add(
        "certificates",
        "certificados o reservas",
        _count(db, Certificate, Certificate.service_order_id == service_order.id),
    )
    add(
        "capture_files",
        "archivos de captura",
        _count(
            db,
            CertificateCaptureFile,
            CertificateCaptureFile.service_order_id == service_order.id,
        ),
    )
    add(
        "invoices",
        "facturas vinculadas",
        _count(db, Invoice, Invoice.service_order_id == service_order.id),
    )
    add(
        "signature_cycles",
        "ciclos de firma",
        _count(
            db,
            ServiceOrderSignatureCycle,
            ServiceOrderSignatureCycle.service_order_id == service_order.id,
        ),
    )
    add(
        "resolution_references",
        "resoluciones vinculadas",
        _count(
            db,
            ResolutionEntityReference,
            ResolutionEntityReference.entity_type.in_(
                ("service_order", "service_orders", "ets")
            )
            & (ResolutionEntityReference.entity_id == str(service_order.id)),
        ),
    )
    # Las OT pendientes creadas automáticamente son datos derivados reconstruibles.
    # Cualquier OT que ya cambió de estado representa actividad operativa.
    add(
        "executed_work_orders",
        "órdenes de trabajo con ejecución",
        _count(
            db,
            ServiceWorkOrder,
            ServiceWorkOrder.service_order_id == service_order.id,
        )
        - _count(
            db,
            ServiceWorkOrder,
            (ServiceWorkOrder.service_order_id == service_order.id)
            & (ServiceWorkOrder.status == "pending"),
        ),
    )
    signature_fields = (
        service_order.technician_signature_data_url,
        service_order.client_received_signature_data_url,
        service_order.client_acceptance_signature_data_url,
        service_order.signatures_confirmed_at,
    )
    if any(signature_fields):
        add("signatures", "firmas del ETS", 1)
    if service_order.status not in {"scheduled"}:
        add("operational_status", f"estado operativo {service_order.status}", 1)
    blockers = tuple(
        f"{dependency.label}: {dependency.count}" for dependency in dependencies
    )
    return ServiceOrderRebuildValidation(
        allowed=not dependencies,
        blockers=blockers,
        dependencies=tuple(dependencies),
    )
