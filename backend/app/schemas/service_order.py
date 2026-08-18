from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.operational_category import OperationalCategory
from app.schemas.service_scope import ServiceScope


ServiceOrderStatus = Literal[
    "scheduled",
    "confirmed",
    "called",
    "in_progress",
    "technical_review",
    "capture",
    "quality_review",
    "pending_payment",
    "released",
    "closed",
    "cancelled",
]


# ============================================================
# WORK ORDERS
# ============================================================


class ServiceWorkOrderBase(BaseModel):
    sequence: int = Field(
        default=1,
        ge=1,
    )

    work_order_number: int

    status: str = Field(
        default="pending",
        max_length=60,
    )

    equipment_limit: int = Field(
        default=10,
        ge=1,
    )

    notes: str | None = None


class ServiceWorkOrderRead(ServiceWorkOrderBase):
    model_config = ConfigDict(
        from_attributes=True,
    )

    id: int

    service_order_id: int

    created_at: datetime

    updated_at: datetime


# ============================================================
# SERVICE ORDER ITEMS
# ============================================================


class ServiceOrderItemBase(BaseModel):
    quotation_item_id: int | None = None

    catalog_item_id: int | None = None

    service_name: str = Field(
        min_length=1,
        max_length=180,
    )

    operational_category: OperationalCategory | None = None

    calibration_scope: ServiceScope | None = None

    quantity: int = Field(
        default=1,
        ge=1,
    )

    status: str = Field(
        default="pending",
        max_length=60,
    )


class ServiceOrderItemCreate(ServiceOrderItemBase):
    """
    Contrato temporal para alta directa de partidas ETS.

    Cuando existe quotation_id, la cotización y su snapshot son la
    autoridad y estos items no deben sustituir la identidad congelada.
    """

    pass


class ServiceOrderItemRead(ServiceOrderItemBase):
    model_config = ConfigDict(
        from_attributes=True,
    )

    id: int

    # Master esperado congelado para el servicio.
    expected_certificate_master_id: int | None = None

    # Snapshot operacional heredado de la cotización.
    #
    # Aquí viven, entre otros:
    # - operational_category;
    # - configuración de Venta;
    # - configuración de Mantenimiento;
    # - Master esperado;
    # - scope;
    # - identidad comercial/técnica congelada.
    service_snapshot: dict | None = None

    is_active: bool

    created_at: datetime

    updated_at: datetime


# ============================================================
# SERVICE ORDER
# ============================================================


class ServiceOrderBase(BaseModel):
    client_id: int

    quotation_id: int | None = None

    advisor_id: int | None = None

    technician_id: int | None = None

    agenda_date: date | None = None

    service_date: date | None = None

    total_equipment: int = Field(
        default=0,
        ge=0,
    )

    completed_equipment: int = Field(
        default=0,
        ge=0,
    )

    requires_payment: bool = True

    notes: str | None = None


class ServiceOrderCreate(ServiceOrderBase):
    items: list[ServiceOrderItemCreate] = Field(
        default_factory=list,
    )


class ServiceOrderUpdate(BaseModel):
    advisor_id: int | None = None

    technician_id: int | None = None

    agenda_date: date | None = None

    service_date: date | None = None

    total_equipment: int | None = Field(
        default=None,
        ge=0,
    )

    completed_equipment: int | None = Field(
        default=None,
        ge=0,
    )

    requires_payment: bool | None = None

    notes: str | None = None

    technician_signature_data_url: str | None = None

    client_received_signature_data_url: str | None = None

    client_acceptance_signature_data_url: str | None = None

    technician_signed_name: str | None = None

    client_received_signed_name: str | None = None

    client_acceptance_signed_name: str | None = None


class ServiceOrderStatusChange(BaseModel):
    comment: str | None = None


# ============================================================
# EXCEPTIONS
# ============================================================


class ServiceOrderExceptionCreate(BaseModel):
    source_stage: str = Field(
        min_length=1,
        max_length=80,
    )

    target_stage: str = Field(
        min_length=1,
        max_length=80,
    )

    reason: str = Field(
        min_length=3,
        max_length=1000,
    )


class ServiceOrderExceptionAuthorize(BaseModel):
    comment: str | None = Field(
        default=None,
        max_length=1000,
    )


class ServiceOrderExceptionRead(BaseModel):
    model_config = ConfigDict(
        from_attributes=True,
    )

    id: int

    service_order_id: int

    requested_by_id: int

    authorized_by_id: int | None = None

    executed_by_id: int | None = None

    status: str

    source_stage: str

    target_stage: str

    target_status: str | None = None

    service_order_status_at_request: str

    reason: str

    authorization_comment: str | None = None

    authorized_at: datetime | None = None

    executed_at: datetime | None = None

    created_at: datetime

    updated_at: datetime


# ============================================================
# SERVICE ORDER READ
# ============================================================


class ServiceOrderRead(ServiceOrderBase):
    model_config = ConfigDict(
        from_attributes=True,
    )

    id: int

    folio: str

    # Compatibilidad temporal con la OT principal histórica.
    #
    # La estructura nueva de órdenes físicas se encuentra en
    # work_orders.
    work_order_number: int

    advisor_name: str | None = None

    technician_name: str | None = None

    status: ServiceOrderStatus

    # Snapshot de origen de la cabecera ETS.
    source_snapshot: dict | None = None

    closed_at: date | None = None

    is_active: bool

    created_at: datetime

    updated_at: datetime

    technician_signature_data_url: str | None = None

    client_received_signature_data_url: str | None = None

    client_acceptance_signature_data_url: str | None = None

    technician_signed_name: str | None = None

    client_received_signed_name: str | None = None

    client_acceptance_signed_name: str | None = None

    technician_signed_at: datetime | None = None

    client_received_signed_at: datetime | None = None

    client_acceptance_signed_at: datetime | None = None

    has_pending_signature_work_orders: bool = False

    items: list[ServiceOrderItemRead] = Field(
        default_factory=list,
    )

    work_orders: list[ServiceWorkOrderRead] = Field(
        default_factory=list,
    )