"""Composición explícita y única de integraciones instaladas."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, Mapping

from app.resolution_integrations.additional_equipment import (
    build_additional_equipment_resolution_integration,
)
from app.resolution_integrations.additional_equipment.domain import (
    AdditionalEquipmentFacts,
    AdditionalEquipmentResolutionContext,
    AdditionalEquipmentResolutionRequest,
)
from app.resolution_integrations.certificates import (
    build_certificate_resolution_integration,
)
from app.resolution_integrations.certificates.domain import (
    CertificateFacts,
    CertificateResolutionContext,
    CertificateResolutionRequest,
)
from app.resolution_integrations.service_order_administration import (
    build_service_order_administration_integrations,
)
from app.resolution_integrations.service_order_administration.domain import (
    ServiceOrderAdministrationFacts,
    ServiceOrderAdministrationContext,
    ServiceOrderAdministrationRequest,
)


@dataclass(frozen=True, slots=True)
class InstalledResolutionIntegration:
    integration: object
    presentation: Mapping[str, Any]
    request_factory: Callable[[str, Mapping[str, Any]], object]
    context_hydrator: Callable[[Mapping[str, Any]], object]
    request_snapshot: Callable[[object], Mapping[str, Any]]

    @property
    def definition(self):
        return self.integration.definition

    @property
    def component_resolver(self):
        return self.integration.component_resolver

    @property
    def action_handlers(self):
        return self.integration.action_handlers

    @property
    def compensation_handlers(self):
        return self.integration.compensation_handlers


def build_installed_resolution_integrations(
    session_factory,
    *,
    certificate_integration=None,
    additional_equipment_integration=None,
    service_order_administration_integrations=None,
) -> tuple[InstalledResolutionIntegration, ...]:
    """Fuente institucional de definiciones, componentes y handlers activos."""

    certificate = (
        certificate_integration
        or build_certificate_resolution_integration(session_factory)
    )
    additional = (
        additional_equipment_integration
        or build_additional_equipment_resolution_integration(session_factory)
    )
    administrative = (
        service_order_administration_integrations
        or build_service_order_administration_integrations(session_factory)
    )
    installed = [
        InstalledResolutionIntegration(
            integration=certificate,
            presentation={
                "family": "domain_resolution",
                "name": "Retiro de certificado liberado incorrectamente",
                "description": certificate.definition.description,
                "domain": "certificates",
                "object_type": "certificate",
                "object_route": "/dashboard#certificados",
                "risk_level": "high",
                "capabilities": (
                    "context",
                    "analysis",
                    "plan",
                    "simulation",
                    "authorization",
                    "distributed_execution",
                    "compensation",
                ),
                "required_permissions": (
                    "certificates.approve",
                    "certificates.release",
                ),
                "supports_simulation": True,
                "supports_compensation": True,
                "parameter_schema": {
                    "type": "object",
                    "additionalProperties": False,
                    "required": ["reason"],
                    "properties": {
                        "reason": {
                            "type": "string",
                            "title": "Motivo institucional",
                            "minLength": 1,
                            "maxLength": 2000,
                            "ui:widget": "textarea",
                            "ui:rows": 4,
                        }
                    },
                },
                "labels": {
                    "subject": "Certificado",
                    "subject_placeholder": "ID del certificado",
                    "create_title": "Retiro administrativo de acceso",
                    "analysis": "Validación de liberación y visibilidad",
                    "simulation": "Impacto previsto sobre acceso del cliente",
                    "result": "Resultado del retiro de acceso",
                },
                "warnings": (
                    "Retira visibilidad futura sin reescribir la liberación histórica.",
                ),
                "strategy_keys": ("withdraw_client_access",),
                "plan_summary": "Retirar acceso futuro al certificado",
                "expected_impacts": ("client_visible:true→false",),
                "preserved_entities": (
                    "certificate.status",
                    "certificate.release_history",
                ),
                "step_description": "Retirar visibilidad futura del certificado",
            },
            request_factory=lambda subject_id, parameters: (
                CertificateResolutionRequest(
                    certificate_id=int(subject_id),
                    reason=str(parameters["reason"]),
                )
            ),
            context_hydrator=lambda snapshot: CertificateResolutionContext(
                facts=CertificateFacts(**snapshot["facts"]),
                reason=str(snapshot["reason"]),
            ),
            request_snapshot=lambda request: {
                "certificate_id": request.certificate_id,
                "reason": request.reason,
            },
        ),
        InstalledResolutionIntegration(
            integration=additional,
            presentation={
                "family": "domain_resolution",
                "name": "Conciliación de equipo adicional",
                "description": additional.definition.description,
                "domain": "service_orders",
                "object_type": "service_order",
                "object_route": "/dashboard#ordenes-servicio",
                "risk_level": "high",
                "capabilities": (
                    "context",
                    "analysis",
                    "plan",
                    "simulation",
                    "authorization",
                    "distributed_execution",
                    "compensation",
                    "offline_reconciliation",
                ),
                "required_permissions": (
                    "service_orders.additional_equipment.propose",
                    "service_orders.additional_equipment.authorize",
                    "service_orders.additional_equipment.execute",
                ),
                "supports_simulation": True,
                "supports_compensation": True,
                "parameter_schema": _additional_equipment_schema(),
                "labels": {
                    "subject": "ETS",
                    "subject_placeholder": "ID del ETS",
                    "create_title": "Resolver equipo adicional",
                    "analysis": "Validación operativa, comercial y documental",
                    "simulation": "Impacto previsto sobre OT, firma y certificado",
                    "result": "Equipo adicional conciliado",
                },
                "warnings": (
                    "No se asignan OT ni folios antes de autorización y ejecución.",
                    "Un ETS avanzado puede requerir nueva firma y ajuste comercial.",
                ),
                "strategy_keys": (
                    "attach_existing_work_order",
                    "create_new_work_order",
                    "pending_signature",
                    "pending_commercial_adjustment",
                ),
                "plan_summary": "Conciliar y registrar equipo adicional en el ETS",
                "expected_impacts": (
                    "equipment:+1",
                    "work_order:reuse_or_create",
                    "certificate:expected_reservation",
                ),
                "preserved_entities": (
                    "service_order.signature_history",
                    "service_order.quotation_history",
                    "invoice.issued_documents",
                ),
                "step_description": "Registrar equipo adicional autorizado",
            },
            request_factory=_additional_request,
            context_hydrator=lambda snapshot: AdditionalEquipmentResolutionContext(
                facts=AdditionalEquipmentFacts(**{
                    **snapshot["facts"],
                    "active_work_orders": tuple(
                        snapshot["facts"]["active_work_orders"]
                    ),
                    "invoice_statuses": tuple(
                        snapshot["facts"]["invoice_statuses"]
                    ),
                }),
                request=AdditionalEquipmentResolutionRequest(
                    **snapshot["request"]
                ),
            ),
            request_snapshot=lambda request: request.snapshot(),
        ),
    ]
    operation_by_type = {
        "service_order.restore_soft_deleted": "restore",
        "service_order.rebuild_from_accepted_quotation": "rebuild",
        "service_order.void_preserving_history": "void",
    }
    metadata = {
        "restore": ("Restaurar ETS retirado", "service_order", "ETS", "ID del ETS", "high"),
        "rebuild": ("Reconstruir ETS faltante", "quotation", "Cotización", "ID de cotización aceptada", "critical"),
        "void": ("Dar de baja ETS", "service_order", "ETS", "ID del ETS", "critical"),
    }
    for integration in administrative:
        operation = operation_by_type[str(integration.definition.resolution_type)]
        name, object_type, subject, placeholder, risk = metadata[operation]
        installed.append(InstalledResolutionIntegration(
            integration=integration,
            presentation={
                "family": "administrative_tools",
                "name": name,
                "description": integration.definition.description,
                "domain": "service_orders",
                "object_type": object_type,
                "object_route": "/dashboard#ordenes-servicio",
                "risk_level": risk,
                "capabilities": ("context", "analysis", "plan", "simulation", "authorization", "distributed_execution"),
                "required_permissions": (
                    f"service_orders.administration.{operation}.propose",
                    f"service_orders.administration.{operation}.authorize",
                    f"service_orders.administration.{operation}.execute",
                ),
                "supports_simulation": True,
                "supports_compensation": False,
                "parameter_schema": {
                    "type": "object", "additionalProperties": False,
                    "required": ["reason"],
                    "properties": {"reason": {"type": "string", "title": "Motivo institucional", "minLength": 3, "maxLength": 2000, "ui:widget": "textarea", "ui:rows": 4}},
                },
                "labels": {"subject": subject, "subject_placeholder": placeholder, "create_title": name, "analysis": "Precheck administrativo", "simulation": "Impacto y evidencia preservada", "result": "Resultado administrativo"},
                "warnings": ("Requiere análisis, simulación y autorización separada antes de ejecutar.",),
                "strategy_keys": (operation, "no_action"),
                "plan_summary": name,
                "expected_impacts": (f"service_order:{operation}",),
                "preserved_entities": ("quotation.snapshot", "service_order.source_snapshot", "certificates", "invoices"),
                "step_description": name,
            },
            request_factory=lambda subject_id, parameters, operation=operation: ServiceOrderAdministrationRequest(
                operation=operation, subject_id=int(subject_id), reason=str(parameters["reason"])
            ),
            context_hydrator=_administration_context,
            request_snapshot=lambda request: request.snapshot(),
        ))
    return tuple(installed)


def _administration_context(snapshot: Mapping[str, Any]):
    facts = dict(snapshot["facts"])
    facts.pop("allowed", None)
    for key in (
        "inactive_order_ids", "blockers", "warnings",
        "affected_entities", "proposed_changes",
    ):
        facts[key] = tuple(facts[key])
    return ServiceOrderAdministrationContext(
        facts=ServiceOrderAdministrationFacts(**facts),
        request=ServiceOrderAdministrationRequest(**snapshot["request"]),
    )


def _additional_request(
    subject_id: str,
    parameters: Mapping[str, Any],
) -> AdditionalEquipmentResolutionRequest:
    return AdditionalEquipmentResolutionRequest(
        service_order_id=int(subject_id),
        reconciliation_id=str(parameters["reconciliation_id"]),
        name=str(parameters["name"]),
        calibration_scope=str(parameters["calibration_scope"]),
        catalog_item_id=int(parameters["catalog_item_id"]),
        quantity=int(parameters.get("quantity", 1)),
        brand=parameters.get("brand"),
        model=parameters.get("model"),
        serial_number=parameters.get("serial_number"),
        internal_id=parameters.get("internal_id"),
        range_or_capacity=parameters.get("range_or_capacity"),
        notes=parameters.get("notes"),
        source=str(parameters.get("source", "resolution_center")),
        requested_at=parameters.get("requested_at"),
        preferred_work_order_id=parameters.get("preferred_work_order_id"),
    )


def _additional_equipment_schema() -> dict[str, Any]:
    optional_text = {"type": ["string", "null"], "maxLength": 180}
    return {
        "type": "object",
        "additionalProperties": False,
        "required": [
            "reconciliation_id",
            "name",
            "calibration_scope",
            "catalog_item_id",
        ],
        "properties": {
            "reconciliation_id": {
                "type": "string",
                "title": "ID de conciliación",
                "minLength": 1,
                "maxLength": 160,
            },
            "name": {
                "type": "string",
                "title": "Equipo",
                "minLength": 1,
                "maxLength": 180,
            },
            "calibration_scope": {
                "type": "string",
                "title": "Clasificación",
                "enum": [
                    "accredited_iso_17025",
                    "traceable",
                    "accredited_linked_lab",
                ],
            },
            "catalog_item_id": {
                "type": "integer",
                "title": "Servicio de catálogo",
                "minimum": 1,
            },
            "quantity": {
                "type": "integer",
                "title": "Cantidad",
                "minimum": 1,
                "maximum": 10,
                "default": 1,
            },
            "brand": {**optional_text, "title": "Marca"},
            "model": {**optional_text, "title": "Modelo"},
            "serial_number": {**optional_text, "title": "Número de serie"},
            "internal_id": {**optional_text, "title": "Identificación interna"},
            "range_or_capacity": {**optional_text, "title": "Alcance/capacidad"},
            "notes": {
                "type": ["string", "null"],
                "title": "Notas",
                "maxLength": 2000,
                "ui:widget": "textarea",
            },
            "source": {
                "type": "string",
                "title": "Origen",
                "default": "resolution_center",
                "maxLength": 60,
            },
            "requested_at": {
                "type": ["string", "null"],
                "title": "Fecha de propuesta",
            },
            "preferred_work_order_id": {
                "type": ["integer", "null"],
                "title": "OT preferida",
                "minimum": 1,
            },
        },
    }


__all__ = [
    "InstalledResolutionIntegration",
    "build_installed_resolution_integrations",
]
