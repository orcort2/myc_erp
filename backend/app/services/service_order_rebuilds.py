from __future__ import annotations

from dataclasses import asdict, dataclass

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.service_order_lab_link import ServiceOrderLabLink
from app.models.certificate import Certificate, CertificateCaptureFile
from app.models.equipment import Equipment
from app.models.invoice import Invoice
from app.models.service_order import (
    ServiceOrder,
    ServiceOrderSignatureCycle,
    ServiceWorkOrder,
)
from app.models.maintenance_execution import MaintenanceExecution
from app.models.quotation import QuotationItem
from app.models.repair_execution import RepairExecution
from app.models.sale_execution import SaleOrderItem, SaleUnitState
from app.models.service_execution import ServiceTask, ServiceUnit, TechnicalServiceRequest
from app.models.service_order_exception import ServiceOrderExceptionRequest
from app.resolution_engine.infrastructure.persistence import ResolutionEntityReference
from app.services.sale_execution import count_non_pristine_sale_dependencies


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
    # Un vínculo LAB (activo o histórico) significa ejecución técnica en MYC
    # Mobile y además impide borrar físicamente el ETS (FK RESTRICT).
    add(
        "lab_links",
        "vínculos con OT MYC Mobile",
        _count(
            db,
            ServiceOrderLabLink,
            ServiceOrderLabLink.service_order_id == service_order.id,
        ),
    )
    add(
        "sale_execution",
        "movimientos operativos de Venta",
        count_non_pristine_sale_dependencies(db, service_order.id),
    )
    # Dependencias reales que el validador no cubría y que impiden borrar la ETS
    # (FK RESTRICT o evidencia operativa propia).
    add(
        "exception_requests",
        "excepciones operativas de la ETS",
        _count(
            db,
            ServiceOrderExceptionRequest,
            ServiceOrderExceptionRequest.service_order_id == service_order.id,
        ),
    )
    add(
        "dependent_quotation_items",
        "partidas de cotización originadas en la ETS",
        _count(
            db,
            QuotationItem,
            QuotationItem.source_service_order_id == service_order.id,
        ),
    )
    add(
        "technical_requests",
        "solicitudes técnicas",
        _count(
            db,
            TechnicalServiceRequest,
            TechnicalServiceRequest.service_order_id == service_order.id,
        ),
    )
    add(
        "service_tasks",
        "tareas de servicio",
        _count(db, ServiceTask, ServiceTask.service_order_id == service_order.id),
    )
    add(
        "repair_executions",
        "ejecuciones de reparación",
        _count(
            db,
            RepairExecution,
            RepairExecution.service_order_id == service_order.id,
        ),
    )
    add(
        "maintenance_executions",
        "ejecuciones de mantenimiento",
        _count(
            db,
            MaintenanceExecution,
            MaintenanceExecution.service_order_id == service_order.id,
        ),
    )
    sale_unit_ids = select(SaleUnitState.service_unit_id).join(SaleOrderItem).where(
        SaleOrderItem.service_order_id == service_order.id
    )
    add(
        "service_units",
        "unidades de servicio no derivadas de Venta",
        _count(
            db,
            ServiceUnit,
            (ServiceUnit.service_order_id == service_order.id)
            & ServiceUnit.id.not_in(sale_unit_ids),
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
