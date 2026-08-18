from datetime import datetime
from decimal import Decimal, ROUND_HALF_UP
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.schemas.service_scope import (
    SERVICE_SCOPE_LEGENDS,
    SERVICE_SCOPE_VALUES_BY_CATEGORY,
    ServiceScope,
)
from app.schemas.service_type import (
    ServiceType,
    calibration_scope_for_service_type,
    normalize_certificate_prefix,
    normalize_service_type,
)
from app.schemas.operational_category import OperationalCategory


CatalogItemType = Literal["product", "service"]
CatalogServiceKind = Literal["simple", "composite"]
CatalogCommodity = Literal[
    "calibration", "maintenance", "repair", "verification", "qualification",
    "validation", "training", "consulting", "sale", "general_service",
]
InternalUnit = Literal[
    "service",
    "piece",
    "equipment",
    "hour",
    "day",
    "package",
    "lot",
    "meter",
    "kilogram",
    "liter",
    "other",
]
TaxObject = Literal["iva_16", "iva_0", "exempt", "not_subject"]

TAX_RATE_BY_OBJECT = {
    "iva_16": Decimal("16.00"),
    "iva_0": Decimal("0.00"),
    "exempt": Decimal("0.00"),
    "not_subject": Decimal("0.00"),
}


LEGENDS_BY_SCOPE = SERVICE_SCOPE_LEGENDS

CATEGORY_TO_COMMODITY = {
    "calibracion": "calibration",
    "mantenimiento": "maintenance",
    "reparacion": "repair",
    "venta": "sale",
    "servicio general": "general_service",
    "verificacion": "verification",
    "calificacion": "qualification",
    "validacion": "validation",
    "capacitacion": "training",
    "consultoria": "consulting",
}

CATEGORY_LEGENDS = {
    "Mantenimiento": "Mantenimiento",
    "Reparacion": "Reparacion",
    "Venta": "Venta",
    "Servicio general": "Servicio general",
}

CATEGORIES_REQUIRING_SCOPE = frozenset(SERVICE_SCOPE_VALUES_BY_CATEGORY)


class CatalogItemComponentCreate(BaseModel):
    component_catalog_item_id: int = Field(gt=0)
    quantity: int = Field(default=1, ge=1)


class CatalogItemComponentOut(CatalogItemComponentCreate):
    model_config = ConfigDict(from_attributes=True)

    id: int
    component_name: str
    component_internal_key: str | None = None
    component_service_kind: CatalogServiceKind


def calculate_final_price_mxn(
    origin_price: Decimal,
    exchange_rate: Decimal,
    margin_percent: Decimal,
) -> Decimal:
    value = origin_price * exchange_rate * (Decimal("1") + margin_percent / Decimal("100"))
    return value.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


class CatalogItemBase(BaseModel):
    item_type: CatalogItemType
    service_kind: CatalogServiceKind = "simple"
    commodity: CatalogCommodity
    category: str = Field(min_length=1, max_length=120)
    operational_category: OperationalCategory | None = None
    name: str = Field(min_length=1, max_length=180)
    description: str | None = None
    sat_key: str | None = Field(default=None, max_length=40)
    sat_unit: str | None = Field(default=None, max_length=40)
    internal_unit: InternalUnit = "service"
    custom_internal_unit: str | None = Field(default=None, max_length=80)
    origin_price: Decimal = Field(default=Decimal("0.00"), ge=0)
    origin_currency: str = Field(min_length=3, max_length=3)
    exchange_rate: Decimal = Field(default=Decimal("1.00"), gt=0)
    margin_percent: Decimal = Field(default=Decimal("0.00"), ge=0)
    final_price_mxn: Decimal | None = Field(default=None, ge=0)
    internal_cost: Decimal | None = Field(default=None, ge=0)
    cost_currency: str | None = Field(default=None, min_length=3, max_length=3)
    calibration_scope: ServiceScope | None = None
    service_type: ServiceType | None = None
    linked_company_id: int | None = Field(default=None, gt=0)
    linked_certificate_prefix: str | None = Field(default=None, max_length=12)
    expected_certificate_master_id: int | None = None
    quotation_legend: str | None = None
    tax_object: TaxObject = "iva_16"
    tax_rate: Decimal | None = Field(default=None, ge=0)

    @model_validator(mode="after")
    def validate_business_rules(self):
        if self.item_type == "service" and self.category == "Venta":
            raise ValueError("La categoria Venta debe capturarse como producto")
        if self.item_type == "product" and self.service_kind != "simple":
            raise ValueError("Los productos no pueden configurarse como servicios compuestos")
        allowed_scopes = SERVICE_SCOPE_VALUES_BY_CATEGORY.get(self.category)
        if allowed_scopes and self.calibration_scope is None:
            raise ValueError("calibration_scope es obligatorio para categorias con alcance")
        if allowed_scopes and self.calibration_scope not in allowed_scopes:
            raise ValueError(
                f"calibration_scope no corresponde a la categoria {self.category}"
            )
        if not allowed_scopes and self.calibration_scope is not None:
            raise ValueError("calibration_scope debe ser null para categorias sin alcance")
        if self.item_type == "product" and self.calibration_scope is not None:
            raise ValueError("calibration_scope debe ser null para productos")
        if self.item_type == "service" and self.category == "Calibracion":
            if self.service_type is None:
                self.service_type = normalize_service_type(
                    None, calibration_scope=self.calibration_scope
                )
            if self.service_type is None:
                raise ValueError("service_type es obligatorio para servicios de calibración")
            expected_scope = calibration_scope_for_service_type(self.service_type)
            if self.calibration_scope != expected_scope:
                raise ValueError("service_type y calibration_scope no corresponden")
            if self.service_type == ServiceType.LINKED:
                if self.linked_certificate_prefix:
                    self.linked_certificate_prefix = normalize_certificate_prefix(
                        self.linked_certificate_prefix
                    )
            elif self.linked_company_id is not None or self.linked_certificate_prefix:
                raise ValueError(
                    "La empresa y las iniciales vinculadas sólo aplican a servicios vinculados"
                )
        elif self.service_type is not None or self.linked_company_id is not None:
            raise ValueError("El tipo de servicio vinculado sólo aplica a calibración")
        if self.internal_unit == "other" and not self.custom_internal_unit:
            raise ValueError("custom_internal_unit es obligatorio si internal_unit es other")
        return self


class CatalogItemCreate(CatalogItemBase):
    components: list[CatalogItemComponentCreate] = Field(default_factory=list)

    @model_validator(mode="after")
    def validate_components(self):
        if self.service_kind == "composite" and not self.components:
            raise ValueError("Un servicio compuesto debe tener al menos un componente")
        if self.service_kind == "simple" and self.components:
            raise ValueError("Un servicio simple no puede tener componentes")
        component_ids = [item.component_catalog_item_id for item in self.components]
        if len(component_ids) != len(set(component_ids)):
            raise ValueError("No se puede repetir un componente dentro del mismo servicio")
        return self


class CatalogItemUpdate(BaseModel):
    item_type: CatalogItemType | None = None
    service_kind: CatalogServiceKind | None = None
    components: list[CatalogItemComponentCreate] | None = None
    commodity: CatalogCommodity | None = None
    category: str | None = Field(default=None, min_length=1, max_length=120)
    operational_category: OperationalCategory | None = None
    name: str | None = Field(default=None, min_length=1, max_length=180)
    description: str | None = None
    sat_key: str | None = Field(default=None, max_length=40)
    sat_unit: str | None = Field(default=None, max_length=40)
    internal_unit: InternalUnit | None = None
    custom_internal_unit: str | None = Field(default=None, max_length=80)
    origin_price: Decimal | None = Field(default=None, ge=0)
    origin_currency: str | None = Field(default=None, min_length=3, max_length=3)
    exchange_rate: Decimal | None = Field(default=None, gt=0)
    margin_percent: Decimal | None = Field(default=None, ge=0)
    final_price_mxn: Decimal | None = Field(default=None, ge=0)
    internal_cost: Decimal | None = Field(default=None, ge=0)
    cost_currency: str | None = Field(default=None, min_length=3, max_length=3)
    calibration_scope: ServiceScope | None = None
    service_type: ServiceType | None = None
    linked_company_id: int | None = Field(default=None, gt=0)
    linked_certificate_prefix: str | None = Field(default=None, max_length=12)
    expected_certificate_master_id: int | None = None
    quotation_legend: str | None = None
    tax_object: TaxObject | None = None


class CatalogItemOut(CatalogItemBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    internal_key: str | None
    components: list[CatalogItemComponentOut] = Field(default_factory=list)
    is_active: bool
    created_at: datetime
    updated_at: datetime


class LinkedCompanyOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    legal_name: str | None = None
    abbreviation: str
    default_certificate_prefix: str
    notes: str | None = None
    document_configuration: dict | None = None
    is_enabled: bool
    is_active: bool


class LinkedCompanyCreate(BaseModel):
    name: str = Field(min_length=2, max_length=180)
    legal_name: str | None = Field(default=None, max_length=240)
    abbreviation: str = Field(min_length=2, max_length=40)
    default_certificate_prefix: str = Field(min_length=2, max_length=12)
    notes: str | None = None
