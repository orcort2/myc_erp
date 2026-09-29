"""Proyección READ-ONLY de la ejecución técnica MYC Mobile de un ETS.

La fuente actual es LAB (``source="lab"``): el ERP consulta el grupo LAB
vinculado por ``ServiceOrderLabLink`` sin copiarlo a Equipment,
ServiceWorkOrder ni a una tabla espejo. Los resúmenes nunca incluyen valores
técnicos de resultados; el detalle de una hoja vive en su propio contrato.
"""
from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, Field

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


class MobileExecutionWorkOrder(BaseModel):
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


class MobileExecutionFieldSheetDetail(BaseModel):
    """Lectura administrativa de UNA hoja LAB: sin inputs ni autoridad de
    escritura. ``field_sheet`` es la revisión vigente (o None)."""

    source: Literal["lab"] = "lab"
    service_order_id: int
    work_order_id: int
    work_order_folio: int
    work_order_status: str
    equipment: MobileExecutionEquipment
    field_sheet: FieldSheetRead | None
    revisions: list[MobileExecutionFieldSheetSummary] = Field(default_factory=list)


class MobileExecutionCorrectionRequest(BaseModel):
    reason: str = Field(min_length=1, max_length=2000)
    # Sólo aplica cuando la OT ya está cerrada (reapertura de la cohorte).
    signature_policy: Literal["preserve", "invalidate"] = "preserve"


class MobileExecutionCancellation(BaseModel):
    reason: str = Field(min_length=1, max_length=2000)
