from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.schemas.calibration_procedure import CalibrationProcedureRead
from app.schemas.reference_standard import (
    FieldSheetReferenceStandardCreate,
    FieldSheetReferenceStandardRead,
)
from app.schemas.field_sheet_template import FieldSheetTemplateRead


FieldSheetStatus = Literal[
    "draft",
    "in_progress",
    "completed",
    "under_review",
    "returned_to_technician",
    "approved",
    "rejected",
    "cancelled",
]

FieldSheetTemplateKey = Literal[
    "anemometro", "angulimetro", "bascula", "calibradores", "cronometro",
    "detector_gases", "dimensional", "electrica", "flujo", "general",
    "maestro_altura", "par_torsional", "pesas", "presion", "reglas",
    "sonido", "tacometro", "temperatura", "tld_6_canales", "tld",
    "valvula_seguridad", "verificacion_equipos", "copa",
    # Claves históricas conservadas para lectura y compatibilidad.
    "dinamometro", "durometro", "luxometro", "manometro", "multimetro",
    "peso_patron", "sonometro", "termometro", "termohigrometro",
    "transductor_presion", "torquimetro", "volumen", "masa", "balanza",
    "regla", "flexometro", "vernier", "micrometro", "valvula",
]


class FieldSheetSignatureBase(BaseModel):
    role: str = Field(min_length=1, max_length=80)
    display_label: str = Field(min_length=1, max_length=180)
    name: str | None = Field(default=None, max_length=180)
    signature_data: str | None = None
    signed_at: datetime | None = None
    user_id: int | None = None
    position: int = Field(default=0, ge=0)


class FieldSheetSignatureCreate(FieldSheetSignatureBase):
    pass


class FieldSheetSignatureUpdate(FieldSheetSignatureBase):
    id: int | None = None


class FieldSheetSignatureRead(FieldSheetSignatureBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    created_at: datetime
    updated_at: datetime


class FieldSheetResultBase(BaseModel):
    section_key: str = Field(min_length=1, max_length=80)
    row_number: int = Field(ge=1)
    pattern_value: str | None = Field(default=None, max_length=180)
    ibc_value_1: str | None = Field(default=None, max_length=180)
    ibc_value_2: str | None = Field(default=None, max_length=180)
    ibc_value_3: str | None = Field(default=None, max_length=180)
    unit: str | None = Field(default=None, max_length=80)
    notes: str | None = None
    row_data: dict | None = None


class FieldSheetResultCreate(FieldSheetResultBase):
    pass


class FieldSheetResultUpdate(FieldSheetResultBase):
    id: int | None = None


class FieldSheetResultRead(FieldSheetResultBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    created_at: datetime
    updated_at: datetime


class FieldSheetBase(BaseModel):
    equipment_id: int
    work_order_id: int | None = None
    template_key: FieldSheetTemplateKey = "general"
    calibration_procedure_id: int | None = None
    calibration_place: str | None = None
    minimum_division: str | None = None
    location: str | None = None
    attention: str | None = None
    company: str | None = None
    address: str | None = None
    reception_date: date | None = None
    calibration_date: date | None = None
    next_calibration_date: date | None = None
    environment_humidity_start: str | None = None
    environment_humidity_end: str | None = None
    environment_temperature_start: str | None = None
    environment_temperature_end: str | None = None
    equipment_general_condition: bool | None = None
    consider_equipment_deviations: bool = False
    units: str | None = None
    calibrated_by: str | None = None
    reviewed_by: str | None = None
    report_made_by: str | None = None
    purchase_order_or_quotation: str | None = None
    initial_condition: str | None = None
    final_condition: str | None = None
    pattern_used: str | None = None
    results: str | None = None
    observations: str | None = None
    evidence_notes: str | None = None
    method: str | None = None
    environmental_conditions: str | None = None
    technician_notes: str | None = None
    certificate_client_mode: Literal["billing", "different"] = "billing"
    certificate_client_company: str | None = None
    certificate_client_attention: str | None = None
    certificate_client_address: str | None = None
    apply_certificate_client_to_order: bool = False
    capture_values: dict = Field(default_factory=dict)
    results_rows: list[FieldSheetResultCreate] = Field(default_factory=list)
    reference_standards: list[FieldSheetReferenceStandardCreate] = Field(default_factory=list)
    signatures: list[FieldSheetSignatureCreate] = Field(default_factory=list)

    @field_validator("capture_values", mode="before")
    @classmethod
    def normalize_legacy_capture_values(cls, value):
        """Expose an empty object for sheets created before this column existed."""
        return {} if value is None else value


class FieldSheetCreate(FieldSheetBase):
    template_version: int | None = Field(default=None, ge=1)
    template_snapshot: dict | None = None


class FieldSheetUpdate(BaseModel):
    work_order_id: int | None = None
    template_key: FieldSheetTemplateKey | None = None
    calibration_procedure_id: int | None = None
    calibration_place: str | None = None
    minimum_division: str | None = None
    location: str | None = None
    attention: str | None = None
    company: str | None = None
    address: str | None = None
    reception_date: date | None = None
    calibration_date: date | None = None
    next_calibration_date: date | None = None
    environment_humidity_start: str | None = None
    environment_humidity_end: str | None = None
    environment_temperature_start: str | None = None
    environment_temperature_end: str | None = None
    equipment_general_condition: bool | None = None
    consider_equipment_deviations: bool | None = None
    units: str | None = None
    calibrated_by: str | None = None
    reviewed_by: str | None = None
    report_made_by: str | None = None
    purchase_order_or_quotation: str | None = None
    initial_condition: str | None = None
    final_condition: str | None = None
    pattern_used: str | None = None
    results: str | None = None
    observations: str | None = None
    evidence_notes: str | None = None
    method: str | None = None
    environmental_conditions: str | None = None
    technician_notes: str | None = None
    certificate_client_mode: Literal["billing", "different"] | None = None
    certificate_client_company: str | None = None
    certificate_client_attention: str | None = None
    certificate_client_address: str | None = None
    apply_certificate_client_to_order: bool | None = None
    capture_values: dict | None = None
    results_rows: list[FieldSheetResultUpdate] | None = None
    reference_standards: list[FieldSheetReferenceStandardCreate] | None = None
    signatures: list[FieldSheetSignatureUpdate] | None = None


class FieldSheetStatusChange(BaseModel):
    comment: str | None = None


class FieldSheetRead(FieldSheetBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    work_order_id: int | None = None
    work_order_number: int | None = None
    calibration_procedure_id: int | None = None
    status: FieldSheetStatus
    is_active: bool
    created_at: datetime
    updated_at: datetime
    returned_to_technician_at: datetime | None = None
    returned_to_technician_by_id: int | None = None
    returned_to_technician_reason: str | None = None
    reserved_certificate_folio: str | None = None
    template_definition: FieldSheetTemplateRead | dict | None = None
    template_definition_version: int | None = None
    institutional_snapshot: dict | None = None
    results_rows: list[FieldSheetResultRead] = Field(default_factory=list)
    calibration_procedure: CalibrationProcedureRead | None = None
    reference_standards: list[FieldSheetReferenceStandardRead] = Field(default_factory=list)
    signatures: list[FieldSheetSignatureRead] = Field(default_factory=list)
