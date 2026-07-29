"""Adaptadores SQLAlchemy y gateways del vertical de equipo adicional."""

from __future__ import annotations

from collections.abc import Callable

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.models.catalog_item import CatalogItem
from app.models.equipment import Equipment
from app.models.invoice import Invoice
from app.models.service_order import ServiceOrder, ServiceOrderItem, ServiceWorkOrder
from app.resolution_engine.domain.compensation import CompensationActionRequest
from app.resolution_engine.domain.enums import EntityRelationshipType
from app.resolution_engine.domain.exceptions import ComponentBindingError
from app.resolution_engine.domain.execution import (
    ActionCertainty,
    DomainActionRequest,
    DomainActionResult,
    ExecutionEntityEffect,
)
from app.resolution_engine.domain.value_objects import ComponentKey
from app.resolution_integrations.additional_equipment.application import (
    ADDITIONAL_EQUIPMENT_RESOLUTION_VERSION,
    COMPENSATE_OPERATION,
    COMPONENT_IMPLEMENTATIONS,
    REGISTER_OPERATION,
    AdditionalEquipmentContextProvider,
    AdditionalEquipmentResolutionIntegration,
    build_additional_equipment_resolution_definition,
)
from app.resolution_integrations.additional_equipment.contracts import (
    AdditionalEquipmentCommandPort,
    AdditionalEquipmentFactsReader,
)
from app.resolution_integrations.additional_equipment.domain import (
    AdditionalEquipmentFacts,
    AdditionalEquipmentOperationOutcome,
    AdditionalEquipmentResolutionRequest,
)
from app.schemas.service_scope import ACCREDITATION_SCOPE_VALUES
from app.services.additional_equipment_resolution_operations import (
    AdditionalEquipmentOperationError,
    AdditionalEquipmentOperationResult,
    compensate_additional_equipment,
    register_additional_equipment,
)


SessionFactory = Callable[[], Session]


class SqlAlchemyAdditionalEquipmentFactsReader:
    def __init__(self, session_factory: SessionFactory) -> None:
        self._session_factory = session_factory

    def read(
        self,
        request: AdditionalEquipmentResolutionRequest,
        /,
    ) -> AdditionalEquipmentFacts:
        with self._session_factory() as session:
            service_order = session.get(ServiceOrder, request.service_order_id)
            if service_order is None:
                return _missing_service_order_facts(request)
            catalog = session.get(CatalogItem, request.catalog_item_id)
            work_orders = []
            for work_order in session.scalars(
                select(ServiceWorkOrder)
                .where(
                    ServiceWorkOrder.service_order_id == service_order.id,
                    ServiceWorkOrder.is_active.is_(True),
                    ServiceWorkOrder.status != "cancelled",
                )
                .order_by(ServiceWorkOrder.sequence, ServiceWorkOrder.id)
            ):
                count = int(
                    session.scalar(
                        select(func.count(Equipment.id)).where(
                            Equipment.work_order_id == work_order.id,
                            Equipment.is_active.is_(True),
                        )
                    )
                    or 0
                )
                work_orders.append(
                    {
                        "id": work_order.id,
                        "work_order_number": work_order.work_order_number,
                        "sequence": work_order.sequence,
                        "status": work_order.status,
                        "equipment_count": count,
                        "equipment_limit": min(work_order.equipment_limit or 10, 10),
                        "available_slots": max(
                            min(work_order.equipment_limit or 10, 10) - count,
                            0,
                        ),
                    }
                )
            service_order_item_id = session.scalar(
                select(ServiceOrderItem.id)
                .where(
                    ServiceOrderItem.service_order_id == service_order.id,
                    ServiceOrderItem.is_active.is_(True),
                    ServiceOrderItem.catalog_item_id == request.catalog_item_id,
                    ServiceOrderItem.calibration_scope
                    == request.calibration_scope,
                )
                .order_by(ServiceOrderItem.id)
            )
            duplicate = _duplicate_equipment(session, request)
            reconciliation_exists = session.scalar(
                select(Equipment.id).where(
                    or_(
                        Equipment.resolution_reconciliation_id
                        == request.reconciliation_id,
                        Equipment.resolution_reconciliation_id.startswith(
                            f"{request.reconciliation_id}:",
                            autoescape=True,
                        ),
                    )
                )
            )
            invoices = tuple(
                session.scalars(
                    select(Invoice.status).where(
                        Invoice.service_order_id == service_order.id,
                        Invoice.is_active.is_(True),
                        Invoice.status != "cancelled",
                    )
                ).all()
            )
            scope_allowed = bool(
                catalog is not None
                and catalog.is_active
                and request.calibration_scope in ACCREDITATION_SCOPE_VALUES
                and catalog.calibration_scope == request.calibration_scope
            )
            commercial_adjustment = service_order_item_id is None or bool(invoices)
            return AdditionalEquipmentFacts(
                service_order_id=service_order.id,
                service_order_folio=service_order.folio,
                service_order_status=service_order.status,
                service_order_active=service_order.is_active,
                technician_id=service_order.technician_id,
                client_id=service_order.client_id,
                quotation_id=service_order.quotation_id,
                signature_status=service_order.signature_status,
                signatures_confirmed=bool(
                    service_order.signatures_confirmed_at
                    or service_order.signature_status == "confirmed"
                ),
                active_work_orders=tuple(work_orders),
                catalog_exists=catalog is not None,
                catalog_active=bool(catalog and catalog.is_active),
                catalog_name=catalog.name if catalog else None,
                scope_allowed=scope_allowed,
                service_order_item_id=service_order_item_id,
                commercial_adjustment_required=commercial_adjustment,
                duplicate_equipment_id=duplicate,
                duplicate_reconciliation=reconciliation_exists is not None,
                invoice_statuses=invoices,
                late_stage=service_order.status not in {
                    "scheduled",
                    "in_progress",
                    "draft",
                },
                updated_at=(
                    service_order.updated_at.isoformat()
                    if service_order.updated_at
                    else None
                ),
            )


class SqlAlchemyAdditionalEquipmentCommandService:
    def __init__(self, session_factory: SessionFactory) -> None:
        self._session_factory = session_factory

    def register(self, **values) -> AdditionalEquipmentOperationOutcome:
        with self._session_factory() as session, session.begin():
            result = register_additional_equipment(session, **values)
        return _outcome(result)

    def compensate(self, **values) -> AdditionalEquipmentOperationOutcome:
        with self._session_factory() as session, session.begin():
            result = compensate_additional_equipment(session, **values)
        return _outcome(result)


class AdditionalEquipmentGateway:
    operation_key = ComponentKey(REGISTER_OPERATION)

    def __init__(self, commands: AdditionalEquipmentCommandPort) -> None:
        self._commands = commands

    def execute(self, request: DomainActionRequest, /) -> DomainActionResult:
        payload = dict(request.step.input_payload)
        for key in (
            "quantity",
            "source",
            "requested_at",
        ):
            payload.pop(key, None)
        try:
            outcome = self._commands.register(
                **payload,
                resolution_id=request.resolution_id,
                request_hash=request.request_hash,
                actor_id=request.actor_id,
            )
        except AdditionalEquipmentOperationError as exc:
            return _failure(exc)
        return _success(outcome)


class AdditionalEquipmentCompensationGateway:
    operation_key = ComponentKey(COMPENSATE_OPERATION)

    def __init__(self, commands: AdditionalEquipmentCommandPort) -> None:
        self._commands = commands

    def execute(
        self,
        request: CompensationActionRequest,
        /,
    ) -> DomainActionResult:
        try:
            outcome = self._commands.compensate(
                service_order_id=int(
                    request.step.input_payload["service_order_id"]
                ),
                reconciliation_id=str(
                    request.step.input_payload["reconciliation_id"]
                ),
                actor_id=request.actor_id,
            )
        except AdditionalEquipmentOperationError as exc:
            return _failure(exc)
        return _success(outcome, compensated=True)


class AdditionalEquipmentComponentResolver:
    def __init__(self, *, facts: AdditionalEquipmentFactsReader) -> None:
        self._instances = {
            implementation.component_key: (
                AdditionalEquipmentContextProvider(facts)
                if implementation is AdditionalEquipmentContextProvider
                else implementation()
            )
            for implementation in COMPONENT_IMPLEMENTATIONS.values()
        }

    def resolve(self, reference, /):
        component = self._instances.get(reference.key)
        if component is None:
            raise ComponentBindingError(
                f"Additional-equipment component not found: {reference.key}"
            )
        if (
            reference.version != ADDITIONAL_EQUIPMENT_RESOLUTION_VERSION
            or not isinstance(component, reference.implementation)
        ):
            raise ComponentBindingError(
                f"Additional-equipment binding mismatch: {reference.key}"
            )
        return component


def build_additional_equipment_resolution_integration(
    session_factory: SessionFactory,
) -> AdditionalEquipmentResolutionIntegration:
    commands = SqlAlchemyAdditionalEquipmentCommandService(session_factory)
    return AdditionalEquipmentResolutionIntegration(
        definition=build_additional_equipment_resolution_definition(),
        component_resolver=AdditionalEquipmentComponentResolver(
            facts=SqlAlchemyAdditionalEquipmentFactsReader(session_factory)
        ),
        action_handlers=(AdditionalEquipmentGateway(commands),),
        compensation_handlers=(
            AdditionalEquipmentCompensationGateway(commands),
        ),
    )


def _duplicate_equipment(
    session: Session,
    request: AdditionalEquipmentResolutionRequest,
) -> int | None:
    predicates = []
    if request.serial_number and request.serial_number.strip():
        predicates.append(
            func.lower(Equipment.serial_number)
            == request.serial_number.strip().lower()
        )
    if request.internal_id and request.internal_id.strip():
        predicates.append(
            func.lower(Equipment.internal_id)
            == request.internal_id.strip().lower()
        )
    if not predicates:
        return None
    return session.scalar(
        select(Equipment.id).where(
            Equipment.service_order_id == request.service_order_id,
            Equipment.is_active.is_(True),
            or_(*predicates),
        )
    )


def _missing_service_order_facts(
    request: AdditionalEquipmentResolutionRequest,
) -> AdditionalEquipmentFacts:
    return AdditionalEquipmentFacts(
        service_order_id=request.service_order_id,
        service_order_folio="",
        service_order_status="missing",
        service_order_active=False,
        technician_id=None,
        client_id=0,
        quotation_id=None,
        signature_status="missing",
        signatures_confirmed=False,
        active_work_orders=(),
        catalog_exists=False,
        catalog_active=False,
        catalog_name=None,
        scope_allowed=False,
        service_order_item_id=None,
        commercial_adjustment_required=False,
        duplicate_equipment_id=None,
        duplicate_reconciliation=False,
        invoice_statuses=(),
        late_stage=False,
        updated_at=None,
    )


def _outcome(
    result: AdditionalEquipmentOperationResult,
) -> AdditionalEquipmentOperationOutcome:
    return AdditionalEquipmentOperationOutcome(
        equipment_id=result.equipment_id,
        service_order_id=result.service_order_id,
        work_order_id=result.work_order_id,
        work_order_number=result.work_order_number,
        reconciliation_id=result.reconciliation_id,
        created_work_order=result.created_work_order,
        certificate_id=result.certificate_id,
        before_snapshot=result.before_snapshot,
        after_snapshot=result.after_snapshot,
        domain_transaction_reference=result.domain_transaction_reference,
    )


def _success(
    result: AdditionalEquipmentOperationOutcome,
    *,
    compensated: bool = False,
) -> DomainActionResult:
    relationship = (
        EntityRelationshipType.CANCELLED
        if compensated
        else EntityRelationshipType.CREATED
    )
    return DomainActionResult(
        success=True,
        certainty=ActionCertainty.CONFIRMED,
        response_payload={
            "equipment_id": result.equipment_id,
            "service_order_id": result.service_order_id,
            "work_order_id": result.work_order_id,
            "work_order_number": result.work_order_number,
            "certificate_id": result.certificate_id,
            "reconciliation_id": result.reconciliation_id,
            "created_work_order": result.created_work_order,
            "compensated": compensated,
        },
        entity_effects=(
            ExecutionEntityEffect(
                relationship=relationship,
                entity_type="equipment",
                entity_id=str(result.equipment_id),
                module="service_orders",
                public_identifier=result.reconciliation_id,
                before_snapshot=result.before_snapshot,
                after_snapshot=result.after_snapshot,
                metadata={
                    "work_order_id": result.work_order_id,
                    "certificate_id": result.certificate_id,
                },
            ),
        ),
        domain_transaction_reference=result.domain_transaction_reference,
    )


def _failure(exc: AdditionalEquipmentOperationError) -> DomainActionResult:
    return DomainActionResult(
        success=False,
        certainty=ActionCertainty.CONFIRMED,
        error_code=exc.code,
        error_message=str(exc),
    )
