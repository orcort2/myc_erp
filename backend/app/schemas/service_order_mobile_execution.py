"""Proyección READ-ONLY de la ejecución técnica MYC Mobile de un ETS.

La fuente actual es LAB (``source="lab"``): el ERP consulta el grupo LAB
vinculado por ``ServiceOrderLabLink`` sin copiarlo a Equipment,
ServiceWorkOrder ni a una tabla espejo. Los resúmenes nunca incluyen valores
técnicos de resultados; el detalle de una hoja vive en su propio contrato.
"""
from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.field_sheet import FieldSheetRead


class MobileExecutionFieldSheetSummary(BaseModel):
    id: int
    revision_number: int
    is_current: bool
    status: str
    template_key: str
    has_final_pdf: bool
    final_pdf_generated_at: datetime | None
    created_at: datetime
    updated_at: datetime


class MobileExecutionCorrectionImpact(BaseModel):
    id: int
    impact_type: Literal["documentation_reissue", "delivery_invalidated"]
    status: Literal["pending", "resolved", "cancelled"]


class MobileExecutionEquipmentDelivery(BaseModel):
    delivered: bool = False
    delivery_id: int | None = None
    delivery_item_id: int | None = None
    exhibition_number: int | None = None
    delivered_at: datetime | None = None
    active_correction_impact: MobileExecutionCorrectionImpact | None = None


class MobileExecutionEquipment(BaseModel):
    id: int
    work_order_id: int
    position: int
    instrument: str
    brand: str
    model: str | None
    serial_number: str
    identification: str
    report_number: str | None = None
    is_good_condition: bool
    # Observaciones de recepción capturadas por el técnico en MYC Mobile.
    observations: str | None = None
    service_type: str | None
    linked_company_name_snapshot: str | None = None
    # Cliente documental del equipo: "order" hereda la OT; "different" congela snapshot.
    certificate_client_mode: str = "order"
    final_client_company_snapshot: str | None = None
    final_client_address_snapshot: str | None = None
    final_client_attention_snapshot: str | None = None
    certificate_folio: str | None
    folio_status: str
    field_sheet: MobileExecutionFieldSheetSummary | None
    field_sheet_revision_count: int
    delivery: MobileExecutionEquipmentDelivery = Field(default_factory=MobileExecutionEquipmentDelivery)


class MobileExecutionWorkOrder(BaseModel):
    authorized_correction_session: bool = False
    id: int
    folio: int
    sequence_number: int
    is_root: bool
    status: str
    workflow_mode: str
    client_name: str
    reception_date: date
    departure_date: date | None
    completed_at: datetime | None
    cancelled_at: datetime | None
    revision_number: int
    # Documento oficial LAB: LabWorkOrder.final_pdf congelado al cierre.
    has_final_pdf: bool = False
    final_pdf_generated_at: datetime | None = None
    retired_equipment_count: int
    equipment: list[MobileExecutionEquipment] = Field(default_factory=list)


class MobileExecutionProjection(BaseModel):
    source: Literal["lab"] = "lab"
    service_order_id: int
    linked: bool
    link_id: int | None = None
    root_work_order_id: int | None = None
    root_folio: int | None = None
    work_orders: list[MobileExecutionWorkOrder] = Field(default_factory=list)
    # Token opaco de cohorte: EXACTAMENTE el valor que request_mobile_correction
    # compara contra expected_cohort_revision (cohort_revision).
    cohort_revision: str | None = None
    has_pending_delivery_impacts: bool = False
    pending_documentation_reissues: int = 0
    pending_delivery_invalidations: int = 0


class MobileExecutionFieldSheetDetail(BaseModel):
    authorized_correction_session: bool = False
    """Lectura administrativa de UNA hoja LAB: sin inputs ni autoridad de
    escritura. ``field_sheet`` es la revisión vigente (o None)."""

    source: Literal["lab"] = "lab"
    service_order_id: int
    work_order_id: int
    work_order_folio: int
    work_order_status: str
    cohort_revision: str | None = None
    equipment: MobileExecutionEquipment
    field_sheet: FieldSheetRead | None
    revisions: list[MobileExecutionFieldSheetSummary] = Field(default_factory=list)


class MobileExecutionCorrectionRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    reason: str = Field(min_length=1, max_length=2000)
    # Sólo aplica cuando la OT ya está cerrada (reapertura de la cohorte).
    signature_policy: Literal["preserve", "invalidate"] = "preserve"
    # Consecuencia administrativa sobre la entrega ya realizada. Obligatorio
    # sólo si el equipo tiene una Delivery vigente; si no, omitirlo o "none".
    delivery_impact: Literal["none", "documentation_reissue", "delivery_invalidated"] | None = None
    # Opcional: si se envía, debe coincidir con `cohort_revision` de la proyección.
    expected_cohort_revision: str | None = Field(default=None, max_length=64)


class MobileExecutionCancellation(BaseModel):
    reason: str = Field(min_length=1, max_length=2000)
