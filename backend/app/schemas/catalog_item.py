from datetime import datetime
from decimal import Decimal, ROUND_HALF_UP
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


CatalogItemType = Literal["product", "service"]
CatalogCommodity = Literal["calibration", "maintenance", "repair", "sale", "general_service"]
CalibrationScope = Literal["accredited_iso_17025", "traceable", "accredited_linked_lab"]
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


LEGENDS_BY_COMMODITY = {
    "maintenance": "Mantenimiento",
    "repair": "Reparacion",
    "sale": "Venta",
}

LEGENDS_BY_SCOPE = {
    "accredited_iso_17025": "Servicio acreditado ISO/IEC 17025:2017",
    "traceable": "Servicio trazable",
    "accredited_linked_lab": "Servicio acreditado ISO/IEC 17025:2017, laboratorio vinculado",
}


def calculate_final_price_mxn(
    origin_price: Decimal,
    exchange_rate: Decimal,
    margin_percent: Decimal,
) -> Decimal:
    value = origin_price * exchange_rate * (Decimal("1") + margin_percent / Decimal("100"))
    return value.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


class CatalogItemBase(BaseModel):
    item_type: CatalogItemType
    commodity: CatalogCommodity
    category: str = Field(min_length=1, max_length=120)
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
    calibration_scope: CalibrationScope | None = None
    quotation_legend: str | None = None
    tax_object: TaxObject = "iva_16"
    tax_rate: Decimal | None = Field(default=None, ge=0)

    @model_validator(mode="after")
    def validate_business_rules(self):
        if self.item_type == "product" and self.commodity != "sale":
            raise ValueError("Los productos deben usar commodity sale")
        if self.item_type == "service" and self.commodity == "sale":
            raise ValueError("Los servicios no deben usar commodity sale")
        if self.commodity == "calibration" and self.calibration_scope is None:
            raise ValueError("calibration_scope es obligatorio para commodity calibration")
        if self.commodity != "calibration" and self.calibration_scope is not None:
            raise ValueError("calibration_scope debe ser null si commodity no es calibration")
        if self.internal_unit == "other" and not self.custom_internal_unit:
            raise ValueError("custom_internal_unit es obligatorio si internal_unit es other")
        if self.commodity == "general_service" and not self.quotation_legend:
            raise ValueError("quotation_legend es obligatorio para commodity general_service")
        return self


class CatalogItemCreate(CatalogItemBase):
    pass


class CatalogItemUpdate(BaseModel):
    item_type: CatalogItemType | None = None
    commodity: CatalogCommodity | None = None
    category: str | None = Field(default=None, min_length=1, max_length=120)
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
    calibration_scope: CalibrationScope | None = None
    quotation_legend: str | None = None
    tax_object: TaxObject | None = None


class CatalogItemOut(CatalogItemBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    internal_key: str | None
    is_active: bool
    created_at: datetime
    updated_at: datetime
