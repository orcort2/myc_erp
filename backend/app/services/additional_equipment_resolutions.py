"""Productor canónico de propuestas de equipo adicional desde el ERP."""

from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy.orm import Session

from app.models.user import User
from app.resolution_center.schemas import (
    CreateAdministrativeResolutionRequest,
    OperationAccepted,
)
from app.resolution_center.workflow import (
    ResolutionCenterWorkflowError,
    ResolutionCenterWorkflowService,
)
from app.services.auth import user_has_permission


@dataclass(frozen=True, slots=True)
class AdditionalEquipmentProposal:
    service_order_id: int
    reconciliation_id: str
    catalog_item_id: int
    name: str
    calibration_scope: str
    quantity: int = 1
    brand: str | None = None
    model: str | None = None
    serial_number: str | None = None
    internal_id: str | None = None
    range_or_capacity: str | None = None
    notes: str | None = None
    source: str = "erp"
    requested_at: str | None = None
    preferred_work_order_id: int | None = None

    def parameters(self) -> dict:
        return {
            key: value
            for key, value in {
                "reconciliation_id": self.reconciliation_id,
                "catalog_item_id": self.catalog_item_id,
                "name": self.name,
                "calibration_scope": self.calibration_scope,
                "quantity": self.quantity,
                "brand": self.brand,
                "model": self.model,
                "serial_number": self.serial_number,
                "internal_id": self.internal_id,
                "range_or_capacity": self.range_or_capacity,
                "notes": self.notes,
                "source": self.source,
                "requested_at": self.requested_at,
                "preferred_work_order_id": self.preferred_work_order_id,
            }.items()
            if value is not None
        }


def request_additional_equipment_resolution(
    db: Session,
    proposal: AdditionalEquipmentProposal,
    *,
    user: User,
    idempotency_key: str,
    correlation_id: str | None = None,
    session_factory=None,
) -> OperationAccepted:
    """Crea o recupera la propuesta; nunca analiza, autoriza ni ejecuta."""

    if not user_has_permission(
        user,
        "service_orders.additional_equipment.propose",
    ):
        raise ResolutionCenterWorkflowError(
            "proposal_permission_missing",
            "No cuenta con permiso para proponer equipo adicional.",
            status_code=403,
        )
    kwargs = {}
    if session_factory is not None:
        kwargs["session_factory"] = session_factory
    workflow = ResolutionCenterWorkflowService(db, **kwargs)
    return workflow.create(
        CreateAdministrativeResolutionRequest(
            resolution_type="service_order.resolve_additional_equipment",
            definition_version="1.0",
            subject_type="service_order",
            subject_id=str(proposal.service_order_id),
            title=f"Equipo adicional para ETS {proposal.service_order_id}",
            description=(
                "Propuesta pendiente de análisis, autorización y ejecución."
            ),
            reason=proposal.notes or "Equipo adicional detectado",
            parameters=proposal.parameters(),
        ),
        user=user,
        idempotency_key=idempotency_key,
        correlation_id=correlation_id,
    )
