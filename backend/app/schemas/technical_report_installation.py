"""Contrato versionado de captura del reporte de Instalación (schema v1).

Autoridad única de los campos de `TechnicalReport.capture_values` para
`report_type='installation'`, `report_schema_version=1`. Mobile refleja esta
lista en `myc-mobile/src/services/technical-report-installation.ts`; ambas
listas se verifican contra el mismo conjunto en sus pruebas.

`capture_values` contiene SOLO la captura propia del trabajo. Cliente, OT,
equipo, marca, modelo, serie, identificación y folio pertenecen al
`document_snapshot`/modelo y nunca se duplican aquí.

Dos contratos distintos:
- `InstallationCapturePatch`: edición/autosave. Parcial, admite borradores
  incompletos y rechaza campos desconocidos.
- `installation_missing_fields`: validación COMPLETA para "confirmar captura"
  (SG-4E). Se define ahora para que el contrato quede en un solo lugar.
"""

from __future__ import annotations

from datetime import date
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

EffectivenessResult = Literal[
    "satisfactory",
    "satisfactory_with_observations",
    "unsatisfactory",
]

INSTALLATION_SCHEMA_VERSION = 1

LONG_TEXT_MAX = 4000
SHORT_TEXT_MAX = 255

# Orden de presentación; también es la lista cerrada de campos permitidos.
INSTALLATION_V1_FIELDS: tuple[str, ...] = (
    "installation_date",
    "installation_location",
    "initial_condition",
    "installation_description",
    "activities_performed",
    "has_incidents",
    "incident_description",
    "corrective_action",
    "functional_test_performed",
    "effectiveness_result",
    "effectiveness_description",
    "effectiveness_notes",
    "final_observations",
)


class InstallationCaptureValues(BaseModel):
    """Forma persistida/leída de `capture_values` (todo opcional: borrador)."""

    model_config = ConfigDict(extra="forbid")

    # Instalación
    installation_date: date | None = None
    installation_location: str | None = Field(default=None, max_length=SHORT_TEXT_MAX)
    initial_condition: str | None = Field(default=None, max_length=LONG_TEXT_MAX)
    installation_description: str | None = Field(default=None, max_length=LONG_TEXT_MAX)
    activities_performed: str | None = Field(default=None, max_length=LONG_TEXT_MAX)

    # Incidencias (una sola sección estructurada en v1)
    has_incidents: bool | None = None
    incident_description: str | None = Field(default=None, max_length=LONG_TEXT_MAX)
    corrective_action: str | None = Field(default=None, max_length=LONG_TEXT_MAX)

    # Verificación funcional / efectividad
    functional_test_performed: bool | None = None
    effectiveness_result: EffectivenessResult | None = None
    effectiveness_description: str | None = Field(default=None, max_length=LONG_TEXT_MAX)
    effectiveness_notes: str | None = Field(default=None, max_length=LONG_TEXT_MAX)

    # Observaciones
    final_observations: str | None = Field(default=None, max_length=LONG_TEXT_MAX)

    @field_validator(
        "installation_location",
        "initial_condition",
        "installation_description",
        "activities_performed",
        "incident_description",
        "corrective_action",
        "effectiveness_description",
        "effectiveness_notes",
        "final_observations",
        mode="before",
    )
    @classmethod
    def blank_text_is_none(cls, value):
        if isinstance(value, str):
            return value.strip() or None
        return value


class InstallationCapturePatch(InstallationCaptureValues):
    """Payload de autosave: sólo viaja lo que cambió (model_fields_set).

    Enviar `null` explícito limpia el campo; omitirlo lo conserva."""


# Etiquetas legibles (mensajes de validación al confirmar la captura).
INSTALLATION_FIELD_LABELS: dict[str, str] = {
    "installation_date": "Fecha de instalación",
    "installation_location": "Lugar de instalación",
    "initial_condition": "Condición inicial",
    "installation_description": "Descripción de la instalación",
    "activities_performed": "Actividades realizadas",
    "has_incidents": "Indicar si hubo incidencias",
    "incident_description": "Descripción de la incidencia",
    "corrective_action": "Acción correctiva",
    "functional_test_performed": "Indicar si se realizó prueba funcional",
    "effectiveness_result": "Resultado de efectividad",
    "effectiveness_description": "Descripción de la verificación",
    "effectiveness_notes": "Notas de efectividad",
    "final_observations": "Observaciones finales",
}


def check_installation_consistency(values: InstallationCaptureValues) -> None:
    """Invariantes que valen también para un borrador.

    Si no hubo prueba funcional no existe un resultado de efectividad: no se
    inventa uno."""
    if values.functional_test_performed is False and values.effectiveness_result is not None:
        raise ValueError(
            "effectiveness_result no aplica cuando no se realizó prueba funcional"
        )


def installation_missing_fields(values: InstallationCaptureValues) -> list[str]:
    """Campos que faltan para CONFIRMAR la captura (validación completa).

    - `has_incidents=false` no exige descripción ni acción correctiva.
    - `has_incidents=true` exige al menos `incident_description`.
    - `functional_test_performed=true` exige `effectiveness_result`.
    - `final_observations`, `effectiveness_description` y
      `effectiveness_notes` son opcionales."""
    missing: list[str] = []
    for field in (
        "installation_date",
        "installation_location",
        "initial_condition",
        "installation_description",
        "activities_performed",
        "has_incidents",
        "functional_test_performed",
    ):
        if getattr(values, field) is None:
            missing.append(field)
    if values.has_incidents is True and not values.incident_description:
        missing.append("incident_description")
    if values.functional_test_performed is True and values.effectiveness_result is None:
        missing.append("effectiveness_result")
    return missing
