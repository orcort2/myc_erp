from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator


SIGNATURE_TRAILING_FIELD_KEYS = frozenset({"purchase_order_or_quotation"})


FieldSheetBlockType = Literal[
    "HeaderBlock",
    "ClientBlock",
    "ServiceOrderBlock",
    "EquipmentBlock",
    "CalibrationDataBlock",
    "EnvironmentalBlock",
    "StandardsBlock",
    "ResultsTableBlock",
    "ObservationsBlock",
    "SignaturesBlock",
    "FooterBlock",
    "CustomFieldsBlock",
    "SectionBlock",
    "AttachmentPlaceholderBlock",
    "GeneralDataBlock",
    "EquipmentDataBlock",
    "SimpleComparisonTableBlock",
    "MultiPointTableBlock",
    "SectionedTableBlock",
    "RepeatabilityTableBlock",
    "DimensionalTableBlock",
    "PressureTableBlock",
    "MassBalanceTableBlock",
    "ElectricalTableBlock",
]


class ResultColumnRead(BaseModel):
    key: str
    label: str
    source: str | None = None
    width: str | None = None
    unit: str | None = None
    editable: bool = True
    required: bool = False
    data_type: str = "text"
    suggested_unit: str | None = None
    alignment: Literal["left", "center", "right"] = "center"
    metadata: dict[str, Any] = Field(default_factory=dict)

    model_config = ConfigDict(extra="allow")


class ResultHeaderCellRead(BaseModel):
    label: str = Field(max_length=180)
    column_key: str | None = Field(default=None, max_length=120)
    colspan: int = Field(default=1, ge=1, le=64)
    rowspan: int = Field(default=1, ge=1, le=16)
    alignment: Literal["left", "center", "right"] = "center"
    width: str | None = Field(default=None, max_length=32)
    metadata: dict[str, Any] = Field(default_factory=dict)

    model_config = ConfigDict(extra="forbid")


class ResultHeaderRowRead(BaseModel):
    cells: list[ResultHeaderCellRead] = Field(min_length=1)
    metadata: dict[str, Any] = Field(default_factory=dict)

    model_config = ConfigDict(extra="forbid")


class ResultSectionLayoutRead(BaseModel):
    row_number_width: str | None = Field(default=None, max_length=32)
    metadata: dict[str, Any] = Field(default_factory=dict)

    model_config = ConfigDict(extra="forbid")


class ResultSectionRead(BaseModel):
    key: str
    title: str
    rows: int
    columns: list[ResultColumnRead]
    allow_add_rows: bool | None = None
    allow_remove_rows: bool | None = None
    min_rows: int | None = None
    max_rows: int | None = None
    header_rows: list[ResultHeaderRowRead] = Field(default_factory=list)
    row_labels: list[str] = Field(default_factory=list)
    layout: ResultSectionLayoutRead = Field(default_factory=ResultSectionLayoutRead)
    repeat_header: bool = True
    break_inside: Literal["auto", "avoid"] = "avoid"
    page_break_before: bool = False
    metadata: dict[str, Any] = Field(default_factory=dict)

    model_config = ConfigDict(extra="allow")


class FieldSheetFieldRead(BaseModel):
    key: str
    label: str
    field_type: str = "text"
    required: bool = False
    visible: bool = True
    order: int = 0
    placeholder: str | None = None
    help_text: str | None = None
    options: list[str] = Field(default_factory=list)
    column_span: int = Field(default=1, ge=1, le=12)
    label_position: Literal["top", "inline"] | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)

    model_config = ConfigDict(extra="allow")


class PrintBlockLayoutRead(BaseModel):
    grid_columns: int = Field(default=2, ge=1, le=12)
    column_span: int = Field(default=1, ge=1, le=12)
    order: int | None = Field(default=None, ge=0)
    title_visible: bool = True
    compact: bool = False
    border: bool = True
    spacing_before: float = Field(default=1.4, ge=0, le=100)
    spacing_after: float = Field(default=0, ge=0, le=100)
    break_inside: Literal["auto", "avoid"] = "avoid"
    page_break_before: bool = False
    label_position: Literal["top", "inline"] = "top"
    hide_empty_fields: bool = False
    metadata: dict[str, Any] = Field(default_factory=dict)

    model_config = ConfigDict(extra="forbid")


class FieldSheetTemplateBlockRead(BaseModel):
    key: str
    block_key: str | None = None
    block_type: FieldSheetBlockType
    title: str
    order: int | None = None
    visible: bool = True
    visible_fields: list[str] = Field(default_factory=list)
    fields: list[FieldSheetFieldRead] = Field(default_factory=list)
    columns: list[ResultColumnRead] = Field(default_factory=list)
    sections: list[ResultSectionRead] = Field(default_factory=list)
    table_config: dict[str, Any] = Field(default_factory=dict)
    suggested_unit: str | None = None
    rows: int | None = None
    min_rows: int | None = None
    max_rows: int | None = None
    allow_add_rows: bool = False
    allow_remove_rows: bool = False
    required: bool = False
    print_order: int = 0
    capture_order: int = 0
    print_visible: bool = True
    capture_visible: bool = True
    pdf_visible: bool = True
    print_layout: PrintBlockLayoutRead = Field(default_factory=PrintBlockLayoutRead)
    metadata: dict[str, Any] = Field(default_factory=dict)

    model_config = ConfigDict(extra="allow")


class PrintMarginsRead(BaseModel):
    top: float = Field(default=12, ge=0, le=100)
    right: float = Field(default=10, ge=0, le=100)
    bottom: float = Field(default=14, ge=0, le=100)
    left: float = Field(default=10, ge=0, le=100)

    model_config = ConfigDict(extra="forbid")


class PrintPageLayoutRead(BaseModel):
    size: Literal["letter", "a4"] = "letter"
    orientation: Literal["portrait", "landscape"] = "portrait"
    margins: PrintMarginsRead = Field(default_factory=PrintMarginsRead)

    model_config = ConfigDict(extra="forbid")


class PrintDocumentLayoutRead(BaseModel):
    title_visible: bool = True
    header_visible: bool = True
    footer_visible: bool = True
    grid_columns: int = Field(default=1, ge=1, le=12)

    model_config = ConfigDict(extra="forbid")


class PrintLayoutRead(BaseModel):
    page: PrintPageLayoutRead = Field(default_factory=PrintPageLayoutRead)
    document: PrintDocumentLayoutRead = Field(default_factory=PrintDocumentLayoutRead)

    model_config = ConfigDict(extra="forbid")


class OrganizationPrintProfileRead(BaseModel):
    key: Literal["myc", "capymet"]
    display_name: str
    legal_name: str | None = None
    inherit_institutional_contact: bool = False
    address: str = ""
    phone: str = ""
    email: str = ""
    logo_key: Literal["institutional", "none"] = "institutional"
    header_variant: Literal["institutional", "text"] = "institutional"
    footer_variant: Literal["document_control", "minimal"] = "document_control"
    footer_show_document_control: bool = True
    typography: Literal["arial"] = "arial"
    base_font_size: float = Field(default=7.5, ge=6, le=14)
    primary_color: str
    header_fill: str

    model_config = ConfigDict(extra="forbid")


class SignatureSlotRead(BaseModel):
    role: str = Field(min_length=1, max_length=80)
    display_label: str = Field(min_length=1, max_length=180)

    model_config = ConfigDict(extra="forbid")


class SignatureLayoutRead(BaseModel):
    # ``layout`` y ``slots`` forman parte del contrato histórico. Las
    # propiedades nuevas tienen defaults que reproducen exactamente el grid
    # horizontal anterior cuando el snapshot no las declara.
    layout: str = Field(default="three_columns", min_length=1, max_length=80)
    slots: list[SignatureSlotRead] = Field(
        default_factory=lambda: [
            SignatureSlotRead(role="calibrated_by", display_label="Calibró"),
            SignatureSlotRead(role="reviewed_by", display_label="Revisó"),
            SignatureSlotRead(role="report_made_by", display_label="Elaboró informe"),
        ]
    )
    columns: int | None = Field(default=None, ge=1, le=4)
    direction: Literal["horizontal", "vertical"] = "horizontal"
    trailing_fields: list[str] = Field(default_factory=list)

    @field_validator("trailing_fields")
    @classmethod
    def validate_trailing_fields(cls, values: list[str]) -> list[str]:
        unknown = sorted(set(values) - SIGNATURE_TRAILING_FIELD_KEYS)
        if unknown:
            raise ValueError(f"Campos posteriores de firmas no permitidos: {unknown}")
        return values

    model_config = ConfigDict(extra="forbid")


class FieldSheetTemplateCreate(BaseModel):
    template_key: str = Field(min_length=1, max_length=60)
    name: str = Field(min_length=1, max_length=180)
    description: str | None = None
    status: str = Field(default="draft", max_length=40)
    code: str = Field(default="FCA-30", max_length=40)
    revision: str = Field(default="R1", max_length=40)
    pages: int = Field(default=1, ge=1)
    pdf_template: str = Field(default="field_sheet_general_pdf.html", max_length=120)
    document_code: str | None = Field(default=None, max_length=80)
    document_revision: str | None = Field(default=None, max_length=80)
    table_family: str | None = Field(default=None, max_length=80)
    blocks: list[FieldSheetTemplateBlockRead] = Field(default_factory=list)
    result_sections: list[ResultSectionRead] = Field(default_factory=list)
    visible_fields: list[str] = Field(default_factory=list)
    validations: dict[str, Any] = Field(default_factory=dict)
    print_config: dict[str, Any] = Field(default_factory=dict)
    print_layout: PrintLayoutRead = Field(default_factory=PrintLayoutRead)
    pdf_config: dict[str, Any] = Field(default_factory=dict)
    permissions_config: dict[str, Any] = Field(default_factory=dict)
    metadata: dict[str, Any] = Field(default_factory=dict)
    signature_layout: SignatureLayoutRead = Field(default_factory=SignatureLayoutRead)
    pagination: dict[str, Any] = Field(default_factory=dict)
    automation: dict[str, Any] = Field(default_factory=dict)

    model_config = ConfigDict(extra="allow")


class FieldSheetTemplateUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=180)
    description: str | None = None
    status: str | None = Field(default=None, max_length=40)
    code: str | None = Field(default=None, max_length=40)
    revision: str | None = Field(default=None, max_length=40)
    pages: int | None = Field(default=None, ge=1)
    pdf_template: str | None = Field(default=None, max_length=120)
    document_code: str | None = Field(default=None, max_length=80)
    document_revision: str | None = Field(default=None, max_length=80)
    table_family: str | None = Field(default=None, max_length=80)
    blocks: list[FieldSheetTemplateBlockRead] | None = None
    result_sections: list[ResultSectionRead] | None = None
    visible_fields: list[str] | None = None
    validations: dict[str, Any] | None = None
    print_config: dict[str, Any] | None = None
    print_layout: PrintLayoutRead | None = None
    pdf_config: dict[str, Any] | None = None
    permissions_config: dict[str, Any] | None = None
    metadata: dict[str, Any] | None = None
    signature_layout: SignatureLayoutRead | None = None
    pagination: dict[str, Any] | None = None
    automation: dict[str, Any] | None = None

    model_config = ConfigDict(extra="allow")


class FieldSheetTemplateImport(BaseModel):
    template: FieldSheetTemplateCreate
    activate: bool = False
    mode: Literal["new_version", "new_key"] = "new_version"
    new_template_key: str | None = Field(default=None, max_length=60)


class FieldSheetTemplateCatalogRead(BaseModel):
    block_types: list[dict[str, Any]]
    table_families: list[dict[str, Any]]
    supported_template_keys: list[str]


class FieldSheetTemplateRead(BaseModel):
    id: int | None = None
    source: Literal["database", "fallback"] = "fallback"
    template_key: str
    key: str
    name: str
    description: str | None = None
    type: str
    status: str
    version: int
    is_active: bool = True
    code: str
    revision: str
    pages: int
    pdf_template: str
    document_code: str | None = None
    document_revision: str | None = None
    table_family: str | None = None
    visible_fields: list[str]
    result_sections: list[ResultSectionRead]
    blocks: list[FieldSheetTemplateBlockRead]
    validations: dict[str, Any] = Field(default_factory=dict)
    print_config: dict[str, Any] = Field(default_factory=dict)
    print_layout: PrintLayoutRead = Field(default_factory=PrintLayoutRead)
    pdf_config: dict[str, Any] = Field(default_factory=dict)
    permissions_config: dict[str, Any] = Field(default_factory=dict)
    metadata: dict[str, Any] = Field(default_factory=dict)
    signature_layout: SignatureLayoutRead = Field(default_factory=SignatureLayoutRead)
    pagination: dict[str, Any] = Field(default_factory=dict)
    automation: dict[str, Any] = Field(default_factory=dict)
    organization_profile: OrganizationPrintProfileRead | None = None

    model_config = ConfigDict(extra="allow")
