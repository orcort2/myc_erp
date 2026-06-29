from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


UncertaintyModelStatus = Literal["draft", "active", "inactive", "obsolete", "archived"]
UncertaintyModelVersionStatus = Literal["draft", "in_review", "approved", "obsolete", "archived"]
UncertaintySourceType = Literal[
    "standard_uncertainty",
    "standard_resolution",
    "ibc_resolution",
    "repeatability",
    "fixed",
    "expression",
]


class UncertaintyComponentBase(BaseModel):
    key: str = Field(min_length=1, max_length=80)
    name: str = Field(min_length=1, max_length=180)
    description: str | None = None
    source_type: UncertaintySourceType
    distribution: str | None = Field(default=None, max_length=60)
    divisor: float | None = Field(default=None, gt=0)
    sensitivity_coefficient: float = 1.0
    value_expression: str | None = None
    required: bool = True
    sort_order: int = 0
    metadata_json: dict | None = None


class UncertaintyComponentCreate(UncertaintyComponentBase):
    pass


class UncertaintyComponentUpdate(BaseModel):
    key: str | None = Field(default=None, min_length=1, max_length=80)
    name: str | None = Field(default=None, min_length=1, max_length=180)
    description: str | None = None
    source_type: UncertaintySourceType | None = None
    distribution: str | None = Field(default=None, max_length=60)
    divisor: float | None = Field(default=None, gt=0)
    sensitivity_coefficient: float | None = None
    value_expression: str | None = None
    required: bool | None = None
    sort_order: int | None = None
    metadata_json: dict | None = None
    is_active: bool | None = None


class UncertaintyComponentRead(UncertaintyComponentBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    model_id: int
    model_version_id: int | None = None
    is_active: bool
    created_at: datetime
    updated_at: datetime


class UncertaintyFormulaBase(BaseModel):
    key: str = Field(min_length=1, max_length=80)
    name: str = Field(min_length=1, max_length=180)
    expression: str = Field(min_length=1)
    result_key: str = Field(min_length=1, max_length=80)
    description: str | None = None
    sort_order: int = 0
    is_active_formula: bool = True


class UncertaintyFormulaCreate(UncertaintyFormulaBase):
    pass


class UncertaintyFormulaUpdate(BaseModel):
    key: str | None = Field(default=None, min_length=1, max_length=80)
    name: str | None = Field(default=None, min_length=1, max_length=180)
    expression: str | None = Field(default=None, min_length=1)
    result_key: str | None = Field(default=None, min_length=1, max_length=80)
    description: str | None = None
    sort_order: int | None = None
    is_active_formula: bool | None = None


class UncertaintyFormulaRead(UncertaintyFormulaBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    model_id: int
    model_version_id: int | None = None
    created_at: datetime
    updated_at: datetime


class UncertaintyModelBase(BaseModel):
    code: str = Field(min_length=1, max_length=80)
    name: str = Field(min_length=1, max_length=180)
    description: str | None = None
    magnitude: str = Field(min_length=1, max_length=80)
    equipment_family: str | None = Field(default=None, max_length=120)
    version: str = Field(default="1.0", min_length=1, max_length=40)
    status: UncertaintyModelStatus = "draft"
    default_coverage_factor: float = Field(default=2.0, gt=0)
    notes: str | None = None


class UncertaintyModelCreate(UncertaintyModelBase):
    components: list[UncertaintyComponentCreate] = Field(default_factory=list)
    formulas: list[UncertaintyFormulaCreate] = Field(default_factory=list)


class UncertaintyModelUpdate(BaseModel):
    code: str | None = Field(default=None, min_length=1, max_length=80)
    name: str | None = Field(default=None, min_length=1, max_length=180)
    description: str | None = None
    magnitude: str | None = Field(default=None, min_length=1, max_length=80)
    equipment_family: str | None = Field(default=None, max_length=120)
    version: str | None = Field(default=None, min_length=1, max_length=40)
    status: UncertaintyModelStatus | None = None
    default_coverage_factor: float | None = Field(default=None, gt=0)
    notes: str | None = None


class UncertaintyModelRead(UncertaintyModelBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    is_active: bool
    created_at: datetime
    updated_at: datetime
    components: list[UncertaintyComponentRead] = Field(default_factory=list)
    formulas: list[UncertaintyFormulaRead] = Field(default_factory=list)
    versions: list["UncertaintyModelVersionRead"] = Field(default_factory=list)


class UncertaintyModelVersionBase(BaseModel):
    version_number: str = Field(default="1.0", min_length=1, max_length=40)
    change_summary: str | None = None
    default_coverage_factor: float = Field(default=2.0, gt=0)


class UncertaintyModelVersionCreate(UncertaintyModelVersionBase):
    components: list[UncertaintyComponentCreate] = Field(default_factory=list)
    formulas: list[UncertaintyFormulaCreate] = Field(default_factory=list)


class UncertaintyModelVersionUpdate(BaseModel):
    version_number: str | None = Field(default=None, min_length=1, max_length=40)
    change_summary: str | None = None
    default_coverage_factor: float | None = Field(default=None, gt=0)


class UncertaintyModelVersionRead(UncertaintyModelVersionBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    model_id: int
    status: UncertaintyModelVersionStatus
    submitted_at: datetime | None = None
    submitted_by_id: int | None = None
    approved_at: datetime | None = None
    approved_by_id: int | None = None
    obsolete_at: datetime | None = None
    archived_at: datetime | None = None
    is_active: bool
    created_at: datetime
    updated_at: datetime
    components: list[UncertaintyComponentRead] = Field(default_factory=list)
    formulas: list[UncertaintyFormulaRead] = Field(default_factory=list)


class UncertaintyModelExceptionBase(BaseModel):
    base_model_id: int | None = None
    alternate_model_id: int
    base_model_version_id: int | None = None
    alternate_model_version_id: int
    magnitude: str | None = Field(default=None, max_length=80)
    equipment_type: str | None = Field(default=None, max_length=180)
    equipment_model: str | None = Field(default=None, max_length=120)
    procedure_id: int | None = None
    profile_key: str | None = Field(default=None, max_length=80)
    reason: str = Field(min_length=1)
    status: str = Field(default="active", max_length=40)


class UncertaintyModelExceptionCreate(UncertaintyModelExceptionBase):
    pass


class UncertaintyModelExceptionRead(UncertaintyModelExceptionBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    authorized_by_id: int | None = None
    authorized_at: datetime | None = None
    is_active: bool
    created_at: datetime
    updated_at: datetime


class UncertaintyCalculationRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    field_sheet_id: int
    uncertainty_model_id: int
    uncertainty_model_version_id: int | None = None
    status: str
    calculated_at: datetime
    input_snapshot: dict
    component_results: list
    formula_results: dict
    calculation_snapshot: dict
    warnings: list
    errors: list
    created_at: datetime
    updated_at: datetime


class UncertaintyPreview(BaseModel):
    field_sheet_id: int
    uncertainty_model_id: int | None = None
    uncertainty_model_version_id: int | None = None
    status: str
    input_snapshot: dict
    component_results: list
    formula_results: dict
    calculation_snapshot: dict
    warnings: list[str] = Field(default_factory=list)
    errors: list[str] = Field(default_factory=list)
