from pydantic import BaseModel


class ResultColumnRead(BaseModel):
    key: str
    label: str
    width: str | None = None


class ResultSectionRead(BaseModel):
    key: str
    title: str
    rows: int
    columns: list[ResultColumnRead]


class FieldDefinitionRead(BaseModel):
    key: str
    label: str
    field_type: str
    required: bool


class FieldSheetTemplateRead(BaseModel):
    key: str
    name: str
    code: str
    revision: str
    pages: int
    pdf_template: str

    common_fields: list[FieldDefinitionRead]

    extra_fields: list[FieldDefinitionRead]

    result_sections: list[ResultSectionRead]