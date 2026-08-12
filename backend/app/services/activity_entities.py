"""Catálogo canónico de entidades que pueden exponer Actividad."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.calibration_procedure import CalibrationProcedure
from app.models.certificate import Certificate
from app.models.client import Client, ClientContact
from app.models.controlled_document import (
    ControlledDocument,
    DocumentInterpretation,
    TechnicalProfile,
)
from app.models.equipment import Equipment
from app.models.field_sheet import FieldSheet
from app.models.invoice import CreditNote, Invoice, InvoicePayment
from app.models.quotation import Quotation
from app.models.reference_standard import ReferenceStandard
from app.models.reference_standard_certificate import (
    ReferenceStandardCertificate,
)
from app.models.service_order import ServiceOrder, ServiceWorkOrder
from app.models.service_execution import ServiceStage, ServiceUnit
from app.models.uncertainty import UncertaintyModel
from app.resolution_engine.infrastructure.persistence import Resolution
from app.services.auth import user_has_permission


@dataclass(frozen=True, slots=True)
class ActivityEntityDefinition:
    code: str
    label: str
    model: type
    read_permission: str
    frontend_path: str
    reference_fields: tuple[str, ...]

    def reference(self, entity: Any) -> str:
        value = next(
            (
                getattr(entity, field)
                for field in self.reference_fields
                if getattr(entity, field, None) not in (None, "")
            ),
            entity.id,
        )
        return f"{self.label} {value}"

    def snapshot(self) -> dict[str, Any]:
        return {
            "code": self.code,
            "label": self.label,
            "read_permission": self.read_permission,
            "frontend_path": self.frontend_path,
        }


_DEFINITIONS = (
    ActivityEntityDefinition(
        "client", "Cliente", Client, "clients.read",
        "/dashboard#clientes", ("legal_name", "commercial_name"),
    ),
    ActivityEntityDefinition(
        "contact", "Contacto", ClientContact, "clients.read",
        "/dashboard#clientes", ("name", "email"),
    ),
    ActivityEntityDefinition(
        "quotation", "Cotización", Quotation, "quotations.read",
        "/dashboard#cotizaciones", ("folio",),
    ),
    ActivityEntityDefinition(
        "service_order", "ETS", ServiceOrder, "service_orders.read",
        "/dashboard#servicios", ("folio", "work_order_number"),
    ),
    ActivityEntityDefinition(
        "equipment", "Equipo", Equipment, "equipment.read",
        "/dashboard#servicios", ("internal_id", "serial_number", "name"),
    ),
    ActivityEntityDefinition(
        "work_order", "Orden de trabajo", ServiceWorkOrder,
        "service_orders.read", "/dashboard#servicios", ("work_order_number",),
    ),
    ActivityEntityDefinition(
        "service_unit", "Unidad ETS", ServiceUnit,
        "service_orders.read", "/dashboard#servicios", ("serial_number", "name"),
    ),
    ActivityEntityDefinition(
        "service_stage", "Etapa ETS", ServiceStage,
        "service_orders.read", "/dashboard#servicios", ("category", "id"),
    ),
    ActivityEntityDefinition(
        "field_sheet", "Hoja de Campo", FieldSheet, "field_sheets.read",
        "/dashboard#servicios", ("id",),
    ),
    ActivityEntityDefinition(
        "certificate", "Certificado", Certificate, "certificates.read",
        "/dashboard#certificados", ("folio", "expected_folio"),
    ),
    ActivityEntityDefinition(
        "invoice", "Factura", Invoice, "invoices.read",
        "/dashboard#facturacion", ("folio",),
    ),
    ActivityEntityDefinition(
        "payment", "Pago", InvoicePayment, "payments.read",
        "/dashboard#facturacion", ("reference", "id"),
    ),
    ActivityEntityDefinition(
        "credit_note", "Nota de crédito", CreditNote, "invoices.read",
        "/dashboard#facturacion", ("folio",),
    ),
    ActivityEntityDefinition(
        "document", "Documento", ControlledDocument, "documents.read",
        "/dashboard#documentos", ("code", "name"),
    ),
    ActivityEntityDefinition(
        "document_interpretation", "Interpretación documental",
        DocumentInterpretation, "document_interpretations.read",
        "/dashboard#documentos", ("name",),
    ),
    ActivityEntityDefinition(
        "technical_profile", "Perfil técnico", TechnicalProfile,
        "technical_profiles.read", "/dashboard#documentos", ("code", "name"),
    ),
    ActivityEntityDefinition(
        "reference_standard", "Patrón", ReferenceStandard, "standards.read",
        "/dashboard#patrones", ("internal_code", "name"),
    ),
    ActivityEntityDefinition(
        "reference_standard_certificate", "Certificado de patrón",
        ReferenceStandardCertificate, "reference_standard_certificates.read",
        "/dashboard#patrones", ("certificate_number", "id"),
    ),
    ActivityEntityDefinition(
        "calibration_procedure", "Procedimiento", CalibrationProcedure,
        "procedures.read", "/dashboard#procedimientos", ("code", "name"),
    ),
    ActivityEntityDefinition(
        "uncertainty_model", "Modelo de incertidumbre", UncertaintyModel,
        "uncertainty_models.read", "/dashboard#incertidumbre", ("code", "name"),
    ),
    ActivityEntityDefinition(
        "resolution", "Resolución", Resolution, "resolution_center.read",
        "/dashboard#resoluciones", ("public_id", "title"),
    ),
)

ACTIVITY_ENTITY_DEFINITIONS = {
    definition.code: definition for definition in _DEFINITIONS
}


def get_activity_entity_definition(
    entity_type: str,
) -> ActivityEntityDefinition:
    definition = ACTIVITY_ENTITY_DEFINITIONS.get(entity_type)
    if definition is None:
        raise HTTPException(
            status_code=422,
            detail="Tipo de entidad no compatible con Actividad",
        )
    return definition


def resolve_activity_entity(
    db: Session,
    *,
    entity_type: str,
    entity_id: int,
    user,
):
    definition = get_activity_entity_definition(entity_type)
    if not user_has_permission(user, "activity.read"):
        raise HTTPException(
            status_code=403,
            detail="No tienes permiso para consultar Actividad",
        )
    if not user_has_permission(user, definition.read_permission):
        raise HTTPException(
            status_code=403,
            detail="No tienes permiso para acceder a esta entidad",
        )
    entity = db.get(definition.model, entity_id)
    if entity is None:
        raise HTTPException(status_code=404, detail="Entidad no encontrada")
    return definition, entity


def entity_resource(
    definition: ActivityEntityDefinition,
    entity: Any,
) -> dict[str, Any]:
    return {
        "entity_type": definition.code,
        "entity_id": entity.id,
        "label": definition.label,
        "reference": definition.reference(entity),
        "frontend_path": definition.frontend_path,
    }


def resolve_resolution_activity_target(
    db: Session,
    *,
    public_id: str,
    user,
) -> dict[str, Any]:
    definition = get_activity_entity_definition("resolution")
    if not user_has_permission(user, "activity.read"):
        raise HTTPException(
            status_code=403,
            detail="No tienes permiso para consultar Actividad",
        )
    if not user_has_permission(user, definition.read_permission):
        raise HTTPException(
            status_code=403,
            detail="No tienes permiso para acceder a esta resolución",
        )
    resolution = db.scalar(
        select(Resolution).where(Resolution.public_id == public_id)
    )
    if resolution is None:
        raise HTTPException(status_code=404, detail="Resolución no encontrada")
    return entity_resource(definition, resolution)
