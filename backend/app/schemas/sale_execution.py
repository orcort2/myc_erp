from datetime import date, datetime
import base64
import binascii
import re
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


SaleAuthorizationType = Literal[
    "individual_identification", "zero_cost_calibration", "substitution"
]
SaleDeliveryMode = Literal["courier", "client_pickup", "myc_technician"]


class SaleUnitRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    sale_order_item_id: int
    service_unit_id: int
    equipment_id: int | None = None
    calibration_stage_id: int | None = None
    status: str
    serial_number: str | None = None
    brand: str | None = None
    model: str | None = None
    specification: str | None = None
    discrepancy_reason: str | None = None
    arrived_at: datetime | None = None
    warranty_returned_at: datetime | None = None


class SaleOrderItemRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    service_order_id: int
    service_order_item_id: int
    requires_individual_identification: bool
    included_calibration_catalog_item_id: int | None = None
    frozen_configuration: dict
    ordered_quantity: int
    arrived_quantity: int
    delivered_quantity: int
    resolved_quantity: int
    status: str
    units: list[SaleUnitRead] = Field(default_factory=list)


class SaleDeliveryLineCreate(BaseModel):
    sale_order_item_id: int
    sale_unit_state_id: int | None = None
    quantity: int = Field(default=1, gt=0)


class SaleDeliveryLineRead(SaleDeliveryLineCreate):
    model_config = ConfigDict(from_attributes=True)
    id: int


class SaleDeliveryCreate(BaseModel):
    mode: SaleDeliveryMode
    lines: list[SaleDeliveryLineCreate] = Field(min_length=1)
    courier_name: str | None = Field(default=None, max_length=120)
    tracking_number: str | None = Field(default=None, max_length=160)
    shipped_on: date | None = None
    estimated_arrival_on: date | None = None
    technician_id: int | None = None
    address_source: Literal["client", "custom"] | None = None
    delivery_address: dict | None = None

    @model_validator(mode="after")
    def validate_mode_fields(self):
        if self.mode == "courier" and not (self.courier_name and self.tracking_number):
            raise ValueError("Paquetería y número de rastreo son obligatorios")
        if self.mode == "myc_technician" and (
            self.technician_id is None or self.address_source is None
        ):
            raise ValueError("La entrega MYC requiere técnico y origen de dirección")
        if self.address_source == "custom" and not self.delivery_address:
            raise ValueError("La dirección específica es obligatoria")
        return self


class SaleDeliveryRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    service_order_id: int
    mode: SaleDeliveryMode
    status: str
    courier_name: str | None = None
    tracking_number: str | None = None
    shipped_on: date | None = None
    estimated_arrival_on: date | None = None
    technician_id: int | None = None
    address_source: str | None = None
    delivery_address: dict | None = None
    accepted_at: datetime | None = None
    scheduled_for: datetime | None = None
    receiver_name: str | None = None
    received_at: datetime | None = None
    received_by_user_id: int | None = None
    signature_data_url: str | None = None
    evidence: dict | None = None
    lines: list[SaleDeliveryLineRead] = Field(default_factory=list)
    created_at: datetime
    updated_at: datetime


class SaleArrivalCreate(BaseModel):
    quantity: int = Field(default=1, gt=0)
    catalog_item_id: int
    serial_number: str | None = Field(default=None, max_length=120)
    serial_unknown: bool = False
    brand: str | None = Field(default=None, max_length=120)
    model: str | None = Field(default=None, max_length=120)
    specification: str | None = None
    substitution_authorization_id: int | None = None


class SaleWarrantyReturnCreate(BaseModel):
    reason: str = Field(min_length=3, max_length=2000)


class SaleUnitResolution(BaseModel):
    resolution: Literal["return_to_flow", "replacement", "commercial_cancellation"] = "return_to_flow"
    reason: str = Field(min_length=3, max_length=2000)


class SaleAuthorizationCreate(BaseModel):
    authorization_type: SaleAuthorizationType
    sale_order_item_id: int | None = None
    sale_unit_state_id: int | None = None
    reason: str = Field(min_length=3, max_length=2000)


class SaleAuthorizationResolve(BaseModel):
    authorized: bool
    comment: str = Field(min_length=3, max_length=2000)


class SaleAuthorizationRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    service_order_id: int
    sale_order_item_id: int | None = None
    sale_unit_state_id: int | None = None
    authorization_type: SaleAuthorizationType
    status: str
    reason: str
    requested_by_id: int
    authorized_by_id: int | None = None
    consumed_by_id: int | None = None
    resolution_comment: str | None = None
    authorized_at: datetime | None = None
    consumed_at: datetime | None = None
    created_at: datetime
    updated_at: datetime


class SaleBoardRead(BaseModel):
    service_order_id: int
    status: str
    items: list[SaleOrderItemRead]
    deliveries: list[SaleDeliveryRead]
    authorizations: list[SaleAuthorizationRead]
    blockers: list[str]
    can_close: bool


class SaleDeliveryAccept(BaseModel):
    scheduled_for: datetime


class SaleTechnicianEvidence(BaseModel):
    type: Literal["technician_attestation"]
    note: str = Field(min_length=3, max_length=1000)
    reference: str | None = Field(default=None, max_length=160)


class SaleDeliveryConfirm(BaseModel):
    receiver_name: str = Field(min_length=2, max_length=180)
    signature_data_url: str | None = Field(default=None, max_length=350_000)
    evidence: SaleTechnicianEvidence | None = None

    @model_validator(mode="after")
    def validate_confirmation(self):
        if not self.signature_data_url and not self.evidence:
            raise ValueError("Se requiere firma o evidencia técnica de recepción")
        if self.signature_data_url:
            match = re.fullmatch(
                r"data:image/(png|jpeg);base64,([A-Za-z0-9+/]+={0,2})",
                self.signature_data_url,
            )
            if match is None:
                raise ValueError("La firma debe ser una imagen PNG/JPEG en data URL base64")
            try:
                binary = base64.b64decode(match.group(2), validate=True)
            except (binascii.Error, ValueError) as exc:
                raise ValueError("La firma contiene base64 inválido") from exc
            if not binary or len(binary) > 256_000:
                raise ValueError("La firma debe contener entre 1 byte y 250 KiB")
            image_type = match.group(1)
            if image_type == "png" and not binary.startswith(b"\x89PNG\r\n\x1a\n"):
                raise ValueError("La firma declarada como PNG no contiene un PNG válido")
            if image_type == "jpeg" and not binary.startswith(b"\xff\xd8\xff"):
                raise ValueError("La firma declarada como JPEG no contiene un JPEG válido")
        return self
