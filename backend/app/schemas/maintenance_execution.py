import base64
import binascii
import re
from datetime import datetime
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


MaintenanceStatus = Literal[
    "pending_arrival",
    "received",
    "pending_assignment",
    "assigned",
    "in_maintenance",
    "technically_completed",
    "pending_release",
    "closed",
]


MaintenanceLocationMode = Literal[
    "laboratory",
    "field",
]


class MaintenanceEquipmentCreate(BaseModel):
    equipment_id: int | None = Field(
        default=None,
        gt=0,
    )

    name: str | None = Field(
        default=None,
        min_length=1,
        max_length=180,
    )

    brand: str | None = Field(
        default=None,
        max_length=120,
    )

    model: str | None = Field(
        default=None,
        max_length=120,
    )

    serial_number: str | None = Field(
        default=None,
        max_length=120,
    )

    internal_id: str | None = Field(
        default=None,
        max_length=120,
    )

    range_or_capacity: str | None = Field(
        default=None,
        max_length=180,
    )

    @model_validator(mode="after")
    def require_existing_or_name(self):
        if self.equipment_id is None and not self.name:
            raise ValueError(
                "Se requiere equipment_id o nombre "
                "para dar de alta el equipo"
            )

        return self


class MaintenancePrepare(BaseModel):
    technician_id: int = Field(
        gt=0,
    )

    location_mode: MaintenanceLocationMode

    field_address: dict | None = None

    scheduled_for: datetime | None = None

    @model_validator(mode="after")
    def validate_location_requirements(self):
        if (
            self.location_mode == "field"
            and not self.field_address
        ):
            raise ValueError(
                "La modalidad de campo requiere dirección"
            )

        if (
            self.location_mode == "laboratory"
            and self.field_address is not None
        ):
            self.field_address = None

        return self


class MaintenanceCapture(BaseModel):
    initial_condition: Literal[
        "operational",
        "operational_with_anomalies",
        "not_operational",
        "undetermined",
    ]

    initial_description: str = Field(
        min_length=3,
        max_length=2000,
    )

    findings: list[dict] = Field(
        default_factory=list,
        max_length=100,
    )

    actions: list[dict] = Field(
        default_factory=list,
        max_length=200,
    )

    final_condition: Literal[
        "operational",
        "operational_with_observations",
        "not_operational",
        "requires_additional_intervention",
    ]

    functional_result: str = Field(
        min_length=3,
        max_length=3000,
    )

    technical_conclusion: str = Field(
        min_length=3,
        max_length=2000,
    )

    recommendations: list[dict] = Field(
        default_factory=list,
        max_length=100,
    )

    before_photos: list[str] = Field(
        default_factory=list,
        max_length=20,
    )

    after_photos: list[str] = Field(
        default_factory=list,
        max_length=20,
    )

    @model_validator(mode="after")
    def validate_photo_references(self):
        references = [
            *self.before_photos,
            *self.after_photos,
        ]

        for reference in references:
            if (
                len(reference) > 500
                or reference.startswith(
                    (
                        "/",
                        "data:",
                        "http://",
                        "https://",
                        "file:",
                    )
                )
                or ".." in reference.split("/")
            ):
                raise ValueError(
                    "Las fotografías deben usar "
                    "referencias relativas seguras "
                    "del almacenamiento institucional"
                )

        return self


class MaintenancePauseCreate(BaseModel):
    pause_type: Literal[
        "spare_part",
        "authorization",
        "second_intervention",
        "commercial_review",
        "administrative_investigation",
    ]

    reason: str = Field(
        min_length=3,
        max_length=2000,
    )

    responsible_user_id: int = Field(
        gt=0,
    )

    tentative_resume_at: datetime | None = None


class MaintenancePauseResolve(BaseModel):
    resolution: str = Field(
        min_length=3,
        max_length=2000,
    )


class MaintenanceMaterialCreate(BaseModel):
    material_type: Literal[
        "used",
        "required",
    ]

    name: str = Field(
        min_length=1,
        max_length=180,
    )

    quantity: Decimal = Field(
        gt=0,
    )

    unit: str = Field(
        min_length=1,
        max_length=40,
    )

    component: str | None = Field(
        default=None,
        max_length=180,
    )

    notes: str | None = Field(
        default=None,
        max_length=2000,
    )

    internal_unit_cost: Decimal | None = Field(
        default=None,
        ge=0,
    )

    decision: Literal[
        "accepted",
        "rejected",
        "pending",
    ] | None = None


class MaintenanceChangeCreate(BaseModel):
    change_type: Literal[
        "corrective",
        "repair",
        "investigation",
    ]

    summary: str = Field(
        min_length=3,
        max_length=3000,
    )


class MaintenanceChangeResolve(BaseModel):
    decision: Literal[
        "approved",
        "rejected",
        "overridden",
        "linked",
    ]

    reason: str = Field(
        min_length=3,
        max_length=2000,
    )

    quotation_item_id: int | None = Field(
        default=None,
        gt=0,
    )

    linked_service_order_id: int | None = Field(
        default=None,
        gt=0,
    )


class MaintenanceSignature(BaseModel):
    signer_name: str = Field(
        min_length=2,
        max_length=180,
    )

    signature_data_url: str = Field(
        max_length=350_000,
    )

    client_decision: Literal[
        "accepted",
        "rejected_additional_work",
        "acknowledged",
    ]

    @model_validator(mode="after")
    def validate_signature(self):
        match = re.fullmatch(
            (
                r"data:image/(png|jpeg);base64,"
                r"([A-Za-z0-9+/]+={0,2})"
            ),
            self.signature_data_url,
        )

        if match is None:
            raise ValueError(
                "La firma debe ser una imagen PNG/JPEG "
                "en data URL base64"
            )

        try:
            binary = base64.b64decode(
                match.group(2),
                validate=True,
            )
        except (binascii.Error, ValueError) as exc:
            raise ValueError(
                "La firma contiene base64 inválido"
            ) from exc

        if not binary or len(binary) > 256_000:
            raise ValueError(
                "La firma debe contener entre "
                "1 byte y 250 KiB"
            )

        if (
            match.group(1) == "png"
            and not binary.startswith(
                b"\x89PNG\r\n\x1a\n"
            )
        ):
            raise ValueError(
                "La firma PNG no es válida"
            )

        if (
            match.group(1) == "jpeg"
            and not binary.startswith(
                b"\xff\xd8\xff"
            )
        ):
            raise ValueError(
                "La firma JPEG no es válida"
            )

        return self


class MaintenanceOverride(BaseModel):
    reason: str = Field(
        min_length=10,
        max_length=2000,
    )


class MaintenanceEntityRead(BaseModel):
    model_config = ConfigDict(
        from_attributes=True,
    )

    id: int
    created_at: datetime
    updated_at: datetime


class MaintenancePauseRead(
    MaintenanceEntityRead
):
    pause_type: str
    reason: str
    responsible_user_id: int
    tentative_resume_at: datetime | None
    status: str
    resolution: str | None
    resolved_by_id: int | None
    resolved_at: datetime | None


class MaintenanceMaterialRead(
    MaintenanceEntityRead
):
    material_type: str
    name: str
    quantity: Decimal
    unit: str
    component: str | None
    notes: str | None
    decision: str | None
    source: str


class MaintenanceChangeRead(
    MaintenanceEntityRead
):
    change_type: str
    summary: str
    status: str
    quotation_item_id: int | None
    linked_service_order_id: int | None
    decision_reason: str | None


class MaintenanceExecutionRead(
    MaintenanceEntityRead
):
    service_order_id: int
    service_order_item_id: int
    service_unit_id: int
    service_stage_id: int

    equipment_id: int | None
    equipment_name: str
    work_order_number: int

    maintenance_type: str

    location_mode: MaintenanceLocationMode | None

    configuration_snapshot: dict

    status: MaintenanceStatus

    technician_id: int | None

    field_request_status: str | None
    field_address: dict | None

    scheduled_for: datetime | None

    initial_condition: str | None
    initial_description: str | None

    findings: list
    actions: list

    final_condition: str | None

    functional_result: str | None
    technical_conclusion: str | None

    recommendations: list

    before_photos: list
    after_photos: list

    technical_completed_at: datetime | None

    report_status: str
    report_version: int
    report_generated_at: datetime | None

    signed_report_version: int | None
    signer_name: str | None
    signed_at: datetime | None

    client_decision: str | None

    investigation_status: str | None

    closed_at: datetime | None

    pauses: list[MaintenancePauseRead]
    materials: list[MaintenanceMaterialRead]
    changes: list[MaintenanceChangeRead]

    blockers: list[dict] = Field(
        default_factory=list,
    )

    notices: list[dict] = Field(
        default_factory=list,
    )


class MaintenanceBoardRead(BaseModel):
    service_order_id: int

    executions: list[
        MaintenanceExecutionRead
    ]

    blockers: list[dict]

    can_close: bool