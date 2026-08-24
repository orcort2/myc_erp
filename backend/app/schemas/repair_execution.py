import base64
import binascii
import re
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


RepairStatus = Literal[
    "pending_arrival",
    "pending_assignment",
    "assigned",
    "in_evaluation",
    "in_repair",
    "testing",
    "technically_completed",
    "equipment_not_suitable",
    "pending_release",
    "closed",
    "cancelled",
]


class RepairEquipmentCreate(BaseModel):
    """Confirmación de llegada / identificación del equipo (solo laboratorio)."""

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

    @model_validator(mode="after")
    def require_existing_or_name(self):
        if (
            self.equipment_id is None
            and not self.name
        ):
            raise ValueError(
                "Se requiere equipment_id o nombre "
                "para dar de alta el equipo"
            )

        return self


class RepairAssign(BaseModel):
    technician_id: int = Field(
        gt=0,
    )


class RepairDiagnosis(BaseModel):
    """Diagnóstico técnico opcional durante la evaluación."""

    reported_issue: str | None = Field(
        default=None,
        min_length=3,
        max_length=1000,
    )

    observed_condition: str | None = Field(
        default=None,
        min_length=3,
        max_length=2000,
    )

    findings: list[
        str
    ] = Field(
        default_factory=list,
        max_length=50,
    )

    probable_causes: list[
        str
    ] = Field(
        default_factory=list,
        max_length=50,
    )

    severity: Literal[
        "minor",
        "moderate",
        "major",
        "critical",
    ] | None = None

    repairability: Literal[
        "repairable",
        "conditionally_repairable",
        "not_repairable",
        "undetermined",
    ] | None = None

    diagnosis_notes: str | None = Field(
        default=None,
        min_length=3,
        max_length=3000,
    )

    @model_validator(mode="after")
    def validate_diagnosis(self):
        self.findings = [
            finding.strip()
            for finding in self.findings
        ]

        self.probable_causes = [
            cause.strip()
            for cause in self.probable_causes
        ]

        if any(
            len(finding) < 3
            or len(finding) > 500
            for finding in self.findings
        ):
            raise ValueError(
                "Cada hallazgo debe contener "
                "entre 3 y 500 caracteres"
            )

        if any(
            len(cause) < 3
            or len(cause) > 500
            for cause in self.probable_causes
        ):
            raise ValueError(
                "Cada causa probable debe contener "
                "entre 3 y 500 caracteres"
            )

        has_content = any(
            (
                self.reported_issue,
                self.observed_condition,
                self.findings,
                self.probable_causes,
                self.severity,
                self.repairability,
                self.diagnosis_notes,
            )
        )

        if not has_content:
            raise ValueError(
                "El diagnóstico debe contener "
                "al menos una evidencia técnica"
            )

        return self


class RepairConclude(BaseModel):
    """Conclusión técnica de la evaluación."""

    conclusion: Literal[
        "repaired",
        "equipment_not_suitable",
    ]

    conclusion_reason: str | None = Field(
        default=None,
        max_length=2000,
    )

    @model_validator(mode="after")
    def require_reason_when_not_suitable(self):
        if (
            self.conclusion
            == "equipment_not_suitable"
            and (
                not self.conclusion_reason
                or len(
                    self.conclusion_reason.strip()
                )
                < 10
            )
        ):
            raise ValueError(
                "La conclusión "
                "'equipment_not_suitable' "
                "requiere una justificación "
                "de al menos 10 caracteres"
            )

        return self


# ---------------------------------------------------------------------------
# INTERVENCIONES
# ---------------------------------------------------------------------------


class RepairInterventionStart(BaseModel):
    """Inicio de una sesión técnica de intervención."""

    description: str = Field(
        min_length=3,
        max_length=3000,
    )


class RepairInterventionComplete(BaseModel):
    """Finalización de una sesión técnica previamente iniciada."""

    actions: list[dict] = Field(
        default_factory=list,
        max_length=200,
    )

    removed_components: list[dict] = Field(
        default_factory=list,
        max_length=100,
    )

    outcome: Literal[
        "effective",
        "partial",
        "ineffective",
    ]

    @model_validator(mode="after")
    def validate_removed_components(self):
        for component in self.removed_components:
            disposition = component.get(
                "disposition",
                "return_to_client",
            )

            if disposition not in (
                "return_to_client",
                "client_authorized_disposal",
            ):
                raise ValueError(
                    "removed_components.disposition "
                    "debe ser 'return_to_client' o "
                    "'client_authorized_disposal'"
                )

            if not component.get("name"):
                raise ValueError(
                    "removed_components requiere 'name'"
                )

        return self


# ---------------------------------------------------------------------------
# PRUEBAS
# ---------------------------------------------------------------------------


class RepairTestCreate(BaseModel):
    test_type: str = Field(
        min_length=1,
        max_length=60,
    )

    result: Literal[
        "pass",
        "fail",
        "inconclusive",
    ]

    notes: str | None = Field(
        default=None,
        max_length=2000,
    )

    intervention_id: int | None = Field(
        default=None,
        gt=0,
    )


# ---------------------------------------------------------------------------
# PAUSAS
# ---------------------------------------------------------------------------


class RepairPauseCreate(BaseModel):
    pause_type: Literal[
        "spare_part",
        "authorization",
        "client_decision",
        "administrative_investigation",
        "warehouse",
    ]

    reason: str = Field(
        min_length=3,
        max_length=2000,
    )

    responsible_user_id: int = Field(
        gt=0,
    )

    tentative_resume_at: datetime | None = None


class RepairPauseResolve(BaseModel):
    resolution: str = Field(
        min_length=3,
        max_length=2000,
    )


# ---------------------------------------------------------------------------
# CAMBIOS / SOLICITUDES
# ---------------------------------------------------------------------------


class RepairChangeCreate(BaseModel):
    change_type: Literal[
        "additional_scope",
        "investigation",
    ]

    summary: str = Field(
        min_length=3,
        max_length=3000,
    )


class RepairChangeResolve(BaseModel):
    decision: Literal[
        "approved",
        "rejected",
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


# ---------------------------------------------------------------------------
# FIRMA
# ---------------------------------------------------------------------------


class RepairSignature(BaseModel):
    """Firma del reporte técnico de Reparación."""

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
                "La firma debe ser una imagen "
                "PNG/JPEG en data URL base64"
            )

        try:
            binary = base64.b64decode(
                match.group(2),
                validate=True,
            )
        except (
            binascii.Error,
            ValueError,
        ) as exc:
            raise ValueError(
                "La firma contiene base64 inválido"
            ) from exc

        if (
            not binary
            or len(binary) > 256_000
        ):
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


# ---------------------------------------------------------------------------
# CANCELACIÓN / GARANTÍA
# ---------------------------------------------------------------------------


class RepairCancel(BaseModel):
    reason: str = Field(
        min_length=10,
        max_length=2000,
    )


class RepairWarrantyReopen(BaseModel):
    """Apertura de un nuevo ciclo de garantía (RepairWarrantyCycle).

    No deshace el cierre anterior: crea un nuevo ciclo versionado sobre la
    misma RepairExecution.
    """

    reason: str = Field(
        min_length=10,
        max_length=2000,
    )


# ---------------------------------------------------------------------------
# READ MODELS
# ---------------------------------------------------------------------------


class RepairEntityRead(BaseModel):
    model_config = ConfigDict(
        from_attributes=True,
    )

    id: int
    created_at: datetime
    updated_at: datetime


class RepairInterventionRead(
    RepairEntityRead,
):
    sequence: int
    technician_id: int

    warranty_cycle_id: int | None

    description: str

    actions: list
    removed_components: list

    outcome: str | None

    started_at: datetime | None
    completed_at: datetime | None


class RepairTestRead(
    RepairEntityRead,
):
    sequence: int

    intervention_id: int | None
    warranty_cycle_id: int | None

    test_type: str
    result: str

    notes: str | None

    performed_by_id: int
    performed_at: datetime


class RepairPauseRead(
    RepairEntityRead,
):
    pause_type: str
    reason: str

    warranty_cycle_id: int | None

    responsible_user_id: int

    tentative_resume_at: datetime | None

    status: str

    resolution: str | None

    resolved_by_id: int | None
    resolved_at: datetime | None


class RepairChangeRead(
    RepairEntityRead,
):
    change_type: str
    summary: str

    warranty_cycle_id: int | None

    status: str

    quotation_item_id: int | None
    linked_service_order_id: int | None

    decision_reason: str | None


class RepairWarrantyCycleRead(
    RepairEntityRead,
):
    sequence: int
    reason: str
    status: str

    opened_by_id: int
    opened_at: datetime

    resolution: str | None
    resolution_notes: str | None

    closed_by_id: int | None
    closed_at: datetime | None


class RepairExecutionRead(
    RepairEntityRead,
):
    service_order_id: int
    service_order_item_id: int

    service_unit_id: int
    service_stage_id: int

    equipment_id: int | None
    equipment_name: str

    work_order_number: int

    origin: str

    source_maintenance_change_request_id: (
        int | None
    )

    configuration_snapshot: dict

    status: RepairStatus

    technician_id: int | None

    diagnosis_data: dict

    diagnosis_notes: str | None
    diagnosis_completed_at: datetime | None

    conclusion: str | None
    conclusion_reason: str | None

    technical_completed_at: datetime | None

    report_status: str
    report_version: int
    report_generated_at: datetime | None

    signed_report_version: int | None

    signer_name: str | None
    signed_at: datetime | None

    client_decision: str | None

    sla_due_at: datetime | None

    warranty_reopened_count: int
    original_closed_at: datetime | None
    original_conclusion: str | None
    original_conclusion_reason: str | None
    original_technical_completed_at: datetime | None

    cancelled_at: datetime | None
    cancelled_after_intervention: bool
    cancellation_reason: str | None

    linked_calibration_stage_id: int | None

    closed_at: datetime | None

    pauses: list[
        RepairPauseRead
    ]

    interventions: list[
        RepairInterventionRead
    ]

    tests: list[
        RepairTestRead
    ]

    changes: list[
        RepairChangeRead
    ]

    warranty_cycles: list[
        RepairWarrantyCycleRead
    ] = Field(
        default_factory=list,
    )

    active_warranty_cycle_id: int | None = None

    blockers: list[dict] = Field(
        default_factory=list,
    )

    closure_blockers: list[dict] = Field(
        default_factory=list,
    )

    notices: list[dict] = Field(
        default_factory=list,
    )


class RepairBoardRead(BaseModel):
    service_order_id: int

    executions: list[
        RepairExecutionRead
    ]

    blockers: list[dict]

    closure_blockers: list[dict]

    can_close: bool