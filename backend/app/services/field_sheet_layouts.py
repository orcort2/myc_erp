from __future__ import annotations

from copy import deepcopy
from re import fullmatch
from typing import Any

from fastapi import HTTPException, status
from pydantic import ValidationError

from app.schemas.field_sheet_template import PrintBlockLayoutRead, PrintLayoutRead, ResultSectionRead


ROW_NUMBER_COLUMN_KEY = "__row_number__"
_SAFE_LENGTH = r"(?:auto|0|(?:\d+(?:\.\d+)?)(?:mm|cm|in|pt|px|%))"

DEFAULT_PRINT_LAYOUT = PrintLayoutRead().model_dump()

ORGANIZATION_PRINT_PROFILES: dict[str, dict[str, Any]] = {
    "myc": {
        "key": "myc",
        "display_name": "MYC",
        "legal_name": None,
        "inherit_institutional_contact": True,
        "address": "",
        "phone": "",
        "email": "",
        "logo_key": "institutional",
        "header_variant": "institutional",
        "footer_variant": "document_control",
        "footer_show_document_control": True,
        "typography": "arial",
        "base_font_size": 7.5,
        "primary_color": "#175cd3",
        "header_fill": "#dbeafe",
    },
    "capymet": {
        "key": "capymet",
        "display_name": "CAPYMET",
        "legal_name": "CAPYMET",
        "inherit_institutional_contact": False,
        "address": "",
        "phone": "",
        "email": "",
        "logo_key": "none",
        "header_variant": "text",
        "footer_variant": "minimal",
        "footer_show_document_control": False,
        "typography": "arial",
        "base_font_size": 7.5,
        "primary_color": "#344054",
        "header_fill": "#eaecf0",
    },
}


def _unprocessable(detail: str) -> HTTPException:
    return HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=detail)


def _validate_safe_length(value: str | None, *, field_name: str) -> None:
    if value is not None and fullmatch(_SAFE_LENGTH, value.strip().lower()) is None:
        raise _unprocessable(f"{field_name} debe usar una longitud segura (mm, cm, in, pt, px, % o auto)")


def _validate_header_geometry(section: dict) -> None:
    header_rows = section.get("header_rows") or []
    if not header_rows:
        return
    total_columns = len(section.get("columns") or []) + 1
    row_count = len(header_rows)
    occupied = [[False] * total_columns for _ in range(row_count)]
    valid_keys = {ROW_NUMBER_COLUMN_KEY, *(column["key"] for column in section.get("columns") or [])}
    column_positions = {
        ROW_NUMBER_COLUMN_KEY: 0,
        **{column["key"]: index for index, column in enumerate(section.get("columns") or [], start=1)},
    }

    for row_index, header_row in enumerate(header_rows):
        cursor = 0
        for cell in header_row["cells"]:
            while cursor < total_columns and occupied[row_index][cursor]:
                cursor += 1
            colspan = int(cell.get("colspan", 1))
            rowspan = int(cell.get("rowspan", 1))
            column_key = cell.get("column_key")
            if column_key is not None and column_key not in valid_keys:
                raise _unprocessable(
                    f"header_rows de {section['key']} referencia column_key inválida: {column_key}"
                )
            if column_key is not None and colspan != 1:
                raise _unprocessable("Una celda enlazada a column_key no puede abarcar varias columnas")
            if column_key is not None and column_positions[column_key] != cursor:
                raise _unprocessable(
                    f"header_rows de {section['key']} ubica {column_key} sobre una columna distinta"
                )
            if cursor + colspan > total_columns or row_index + rowspan > row_count:
                raise _unprocessable(f"header_rows de {section['key']} excede la geometría de la tabla")
            for target_row in range(row_index, row_index + rowspan):
                for target_column in range(cursor, cursor + colspan):
                    if occupied[target_row][target_column]:
                        raise _unprocessable(f"header_rows de {section['key']} contiene celdas superpuestas")
                    occupied[target_row][target_column] = True
            cursor += colspan

    if any(not slot for row in occupied for slot in row):
        raise _unprocessable(
            f"header_rows de {section['key']} no cubre las {total_columns} columnas efectivas"
        )


def normalize_result_section(section: dict) -> dict:
    try:
        normalized = ResultSectionRead.model_validate(section).model_dump()
    except ValidationError as exc:
        raise _unprocessable(f"Definición inválida de sección de resultados: {exc.errors()}") from exc

    for column in normalized["columns"]:
        _validate_safe_length(column.get("width"), field_name=f"columns.{column['key']}.width")
    _validate_safe_length(
        normalized["layout"].get("row_number_width"),
        field_name=f"result_sections.{normalized['key']}.layout.row_number_width",
    )
    for header_row in normalized["header_rows"]:
        for cell in header_row["cells"]:
            _validate_safe_length(cell.get("width"), field_name="header_rows.cells.width")
    if normalized["row_labels"] and len(normalized["row_labels"]) != normalized["rows"]:
        raise _unprocessable(f"row_labels de {normalized['key']} debe contener exactamente {normalized['rows']} labels")
    _validate_header_geometry(normalized)
    return normalized


def normalize_print_layout(value: dict | None) -> dict:
    try:
        return PrintLayoutRead.model_validate(value or {}).model_dump()
    except ValidationError as exc:
        raise _unprocessable(f"print_layout inválido: {exc.errors()}") from exc


def normalize_block_print_layout(value: dict | None) -> dict:
    try:
        return PrintBlockLayoutRead.model_validate(value or {}).model_dump()
    except ValidationError as exc:
        raise _unprocessable(f"print_layout de bloque inválido: {exc.errors()}") from exc


def resolve_organization_print_profile(template_definition: dict) -> dict:
    metadata = template_definition.get("metadata") or {}
    snapshot_profile = template_definition.get("organization_profile") or {}
    key = str(snapshot_profile.get("key") or metadata.get("organization_key") or "myc").strip().lower()
    profile = ORGANIZATION_PRINT_PROFILES.get(key)
    if profile is None:
        raise _unprocessable(f"Perfil de organización no soportado: {key}")
    return deepcopy(profile)
