"""Adaptadores SQLAlchemy del vertical administrativo de ETS."""

from __future__ import annotations

from collections.abc import Callable

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.models.quotation import Quotation
from app.models.service_order import ServiceOrder
from app.resolution_engine.domain.enums import EntityRelationshipType
from app.resolution_engine.domain.exceptions import ComponentBindingError
from app.resolution_engine.domain.execution import ActionCertainty, DomainActionResult, ExecutionEntityEffect
from app.resolution_engine.domain.value_objects import ComponentKey
from app.services.service_order_administration import (
    ServiceOrderAdministrationError,
    dependency_counts,
    execute_service_order_administration,
)

from .application import (
    COMPONENTS,
    OPERATION_KEY,
    REBUILD_RESOLUTION_TYPE,
    RESTORE_RESOLUTION_TYPE,
    VERSION,
    VOID_RESOLUTION_TYPE,
    AdministrationContextProvider,
    ServiceOrderAdministrationIntegration,
    build_definition,
)
from .domain import ServiceOrderAdministrationFacts, ServiceOrderAdministrationRequest

SessionFactory = Callable[[], Session]


class SqlAlchemyAdministrationFactsReader:
    def __init__(self, session_factory: SessionFactory) -> None:
        self._session_factory = session_factory

    def read(self, request: ServiceOrderAdministrationRequest, /):
        with self._session_factory() as session:
            if request.operation == "rebuild":
                return self._rebuild_facts(session, request)
            order = session.scalar(
                select(ServiceOrder)
                .where(ServiceOrder.id == request.subject_id)
                .options(selectinload(ServiceOrder.work_orders))
            )
            if order is None:
                return _missing(request, "service_order_not_found")
            active_sibling = _active_sibling(session, order.quotation_id, exclude=order.id)
            dependencies = dependency_counts(session, order.id)
            signature_data = any((
                order.technician_signature_data_url,
                order.client_received_signature_data_url,
                order.client_acceptance_signature_data_url,
                order.signatures_confirmed_at,
            ))
            blockers = [f"{key}:{value}" for key, value in dependencies.items() if value]
            if signature_data:
                blockers.append("signatures:1")
            if order.status != "scheduled":
                blockers.append(f"operational_status:{order.status}")
            if request.operation == "restore":
                if order.is_active:
                    blockers.append("service_order_already_active")
                if active_sibling is not None:
                    blockers.append(f"active_sibling:{active_sibling}")
                proposed = ("service_order.is_active:false→true", "work_orders.is_active:false→true")
            else:
                if not order.is_active:
                    blockers.append("service_order_already_inactive")
                proposed = ("service_order.is_active:true→false", "work_orders.is_active:true→false")
            quotation = session.get(Quotation, order.quotation_id) if order.quotation_id else None
            return ServiceOrderAdministrationFacts(
                operation=request.operation,
                subject_id=request.subject_id,
                service_order_id=order.id,
                service_order_folio=order.folio,
                quotation_id=order.quotation_id,
                quotation_status=quotation.status if quotation else None,
                service_order_active=order.is_active,
                active_sibling_id=active_sibling,
                inactive_order_ids=(),
                blockers=tuple(blockers),
                warnings=("La operación conserva snapshots, partidas y folios históricos.",),
                affected_entities=(f"service_order:{order.id}", *(f"work_order:{item.id}" for item in order.work_orders)),
                proposed_changes=proposed,
                updated_at=order.updated_at.isoformat() if order.updated_at else None,
            )

    def _rebuild_facts(self, session: Session, request):
        quotation = session.get(Quotation, request.subject_id)
        if quotation is None:
            return _missing(request, "quotation_not_found")
        orders = tuple(session.scalars(select(ServiceOrder).where(ServiceOrder.quotation_id == quotation.id).order_by(ServiceOrder.id)).all())
        active = next((item for item in orders if item.is_active), None)
        inactive = tuple(item.id for item in orders if not item.is_active)
        blockers = []
        if not quotation.is_active or quotation.status != "accepted":
            blockers.append("quotation_not_accepted")
        if active is not None:
            blockers.append(f"active_service_order:{active.id}")
        if inactive:
            blockers.append("inactive_service_order_requires_restore")
        return ServiceOrderAdministrationFacts(
            operation=request.operation,
            subject_id=request.subject_id,
            service_order_id=None,
            service_order_folio=None,
            quotation_id=quotation.id,
            quotation_status=quotation.status,
            service_order_active=None,
            active_sibling_id=active.id if active else None,
            inactive_order_ids=inactive,
            blockers=tuple(blockers),
            warnings=("El ETS se materializará sólo desde el snapshot congelado de la cotización.",),
            affected_entities=(f"quotation:{quotation.id}",),
            proposed_changes=("service_order:create", "service_order_items:create_from_frozen_snapshot", "work_orders:create"),
            updated_at=quotation.updated_at.isoformat() if quotation.updated_at else None,
        )


def _active_sibling(session, quotation_id, *, exclude=None):
    if quotation_id is None:
        return None
    statement = select(ServiceOrder.id).where(ServiceOrder.quotation_id == quotation_id, ServiceOrder.is_active.is_(True))
    if exclude is not None:
        statement = statement.where(ServiceOrder.id != exclude)
    return session.scalar(statement.order_by(ServiceOrder.id))


def _missing(request, blocker):
    return ServiceOrderAdministrationFacts(
        operation=request.operation, subject_id=request.subject_id,
        service_order_id=None, service_order_folio=None, quotation_id=None,
        quotation_status=None, service_order_active=None, active_sibling_id=None,
        inactive_order_ids=(), blockers=(blocker,), warnings=(),
        affected_entities=(), proposed_changes=(), updated_at=None,
    )


class AdministrationComponentResolver:
    def __init__(self, reader) -> None:
        self._instances = {
            implementation.component_key: (
                AdministrationContextProvider(reader)
                if implementation is AdministrationContextProvider else implementation()
            ) for implementation in COMPONENTS.values()
        }

    def resolve(self, reference, /):
        component = self._instances.get(reference.key)
        if component is None or reference.version != VERSION or not isinstance(component, reference.implementation):
            raise ComponentBindingError(f"Service-order administration binding mismatch: {reference.key}")
        return component


class AdministrationGateway:
    operation_key = ComponentKey(OPERATION_KEY)

    def __init__(self, session_factory: SessionFactory) -> None:
        self._session_factory = session_factory

    def execute(self, request, /):
        try:
            with self._session_factory() as session, session.begin():
                outcome = execute_service_order_administration(
                    session,
                    **dict(request.step.input_payload),
                    resolution_id=request.resolution_id,
                    request_hash=request.request_hash,
                    actor_id=_erp_user_id(request.actor_id),
                )
        except ServiceOrderAdministrationError as exc:
            return DomainActionResult(success=False, certainty=ActionCertainty.CONFIRMED, error_code=exc.code, error_message=str(exc))
        relationship = EntityRelationshipType.CREATED if outcome.created else EntityRelationshipType.MODIFIED
        return DomainActionResult(
            success=True,
            certainty=ActionCertainty.CONFIRMED,
            response_payload={
                "operation": outcome.operation,
                "service_order_id": outcome.service_order_id,
                "service_order_folio": outcome.service_order_folio,
                "quotation_id": outcome.quotation_id,
                "created": outcome.created,
            },
            entity_effects=(ExecutionEntityEffect(
                relationship=relationship,
                entity_type="service_order",
                entity_id=str(outcome.service_order_id),
                module="service_orders",
                public_identifier=outcome.service_order_folio,
                before_snapshot=outcome.before_snapshot,
                after_snapshot=outcome.after_snapshot,
                metadata={"operation": outcome.operation, "quotation_id": outcome.quotation_id},
            ),),
            domain_transaction_reference=outcome.domain_transaction_reference,
        )


def build_service_order_administration_integrations(session_factory: SessionFactory):
    resolver = AdministrationComponentResolver(SqlAlchemyAdministrationFactsReader(session_factory))
    handler = AdministrationGateway(session_factory)
    specs = (
        (RESTORE_RESOLUTION_TYPE, "Restaura el mismo ETS retirado, sólo cuando no existe actividad operativa ni otro ETS activo."),
        (REBUILD_RESOLUTION_TYPE, "Materializa un ETS faltante desde una cotización aceptada y su snapshot congelado."),
        (VOID_RESOLUTION_TYPE, "Retira un ETS prístino de la operación visible sin eliminar su historia."),
    )
    return tuple(
        ServiceOrderAdministrationIntegration(
            build_definition(kind, description),
            resolver,
            (handler,) if index == 0 else (),
        )
        for index, (kind, description) in enumerate(specs)
    )


def _erp_user_id(actor_id: str) -> int:
    prefix, separator, value = str(actor_id).partition(":")
    if separator != ":" or prefix != "user" or not value.isdigit():
        raise ServiceOrderAdministrationError(
            "invalid_erp_actor",
            "La operación administrativa exige un actor humano ERP.",
        )
    return int(value)
