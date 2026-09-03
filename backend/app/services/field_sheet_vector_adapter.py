from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from app.models.field_sheet import FieldSheet
from app.services.field_sheet_pdfs import (
    FIELD_LABELS,
    _field_value,
    _group_sections,
)
from app.services.field_sheet_vector_renderer import (
    FieldSheetVectorDocument,
    VectorBox,
    VectorHeaderCell,
    VectorPageSpec,
    VectorTextStyle,
    mm,
)


@dataclass(frozen=True)
class VectorRenderContext:
    field_sheet: FieldSheet
    template_definition: dict[str, Any]
    equipment: dict[str, Any]
    client_name: str
    client_attention: str
    client_address: str | None
    certificate_folio: str | None


def _parse_percent(value: str | int | float | None) -> float | None:
    if value is None:
        return None

    if isinstance(value, (int, float)):
        return float(value)

    normalized = str(value).strip()

    if normalized.endswith("%"):
        try:
            return float(normalized[:-1]) / 100.0
        except ValueError:
            return None

    try:
        return float(normalized)
    except ValueError:
        return None


def _resolve_result_column_widths(section) -> list[float]:
    """
    Retorna anchos relativos incluyendo la columna física de número de fila.

    La definición actual de result_sections no declara __row_number__ como
    columna de datos; esa columna pertenece al layout documental.
    """

    columns = section.columns or []

    layout = section.layout or {}

    row_number_width = _parse_percent(
        layout.get("row_number_width")
    )

    if row_number_width is None:
        row_number_width = 0.08

    remaining = max(1.0 - row_number_width, 0.01)

    declared_widths: list[float | None] = []

    for column in columns:
        if isinstance(column, dict):
            width = _parse_percent(column.get("width"))
        else:
            width = _parse_percent(
                getattr(column, "width", None)
            )

        declared_widths.append(width)

    valid_declared = [
        width
        for width in declared_widths
        if width is not None and width > 0
    ]

    if len(valid_declared) == len(columns):
        total_declared = sum(valid_declared)

        if total_declared <= 0:
            normalized_data_widths = [
                remaining / max(len(columns), 1)
            ] * len(columns)
        else:
            normalized_data_widths = [
                remaining * (width / total_declared)
                for width in valid_declared
            ]
    else:
        normalized_data_widths = [
            remaining / max(len(columns), 1)
        ] * len(columns)

    return [
        row_number_width,
        *normalized_data_widths,
    ]


def _build_header_cells(
    *,
    section,
) -> tuple[list[VectorHeaderCell], list[float]]:
    """
    Convierte header_rows del DSL actual a la matriz física del renderer
    vectorial.

    Reglas:
    - __row_number__ ocupa la columna física 0.
    - las columnas de resultado ocupan 1..N;
    - celdas sin column_key se colocan en la primera posición libre;
    - colspan/rowspan se preservan.
    """

    header_rows = section.header_rows or []

    physical_column_count = len(section.columns) + 1

    if not header_rows:
        cells = [
            VectorHeaderCell(
                label="No.",
                row=0,
                column=0,
            )
        ]

        for index, column in enumerate(section.columns):
            if isinstance(column, dict):
                label = (
                    column.get("label")
                    or column.get("title")
                    or column.get("key")
                    or ""
                )
            else:
                label = (
                    getattr(column, "label", None)
                    or getattr(column, "title", None)
                    or getattr(column, "key", "")
                )

            cells.append(
                VectorHeaderCell(
                    label=str(label),
                    row=0,
                    column=index + 1,
                )
            )

        return cells, [mm(5.4)]

    key_to_physical_column: dict[str, int] = {
        "__row_number__": 0,
    }

    for index, column in enumerate(section.columns):
        if isinstance(column, dict):
            key = column.get("key")
        else:
            key = getattr(column, "key", None)

        if key:
            key_to_physical_column[str(key)] = index + 1

    occupied: set[tuple[int, int]] = set()

    result: list[VectorHeaderCell] = []

    for row_index, row_definition in enumerate(header_rows):
        cells = (
            row_definition.get("cells") or []
            if isinstance(row_definition, dict)
            else []
        )

        for cell_definition in cells:
            label = str(
                cell_definition.get("label")
                or ""
            )

            rowspan = int(
                cell_definition.get("rowspan")
                or 1
            )

            colspan = int(
                cell_definition.get("colspan")
                or 1
            )

            column_key = cell_definition.get(
                "column_key"
            )

            if column_key:
                if column_key not in key_to_physical_column:
                    raise ValueError(
                        f"column_key desconocida en header_rows: {column_key}"
                    )

                physical_column = (
                    key_to_physical_column[column_key]
                )
            else:
                physical_column = 0

                while physical_column < physical_column_count:
                    fits = True

                    for candidate_row in range(
                        row_index,
                        row_index + rowspan,
                    ):
                        for candidate_column in range(
                            physical_column,
                            physical_column + colspan,
                        ):
                            if candidate_column >= physical_column_count:
                                fits = False
                                break

                            if (
                                candidate_row,
                                candidate_column,
                            ) in occupied:
                                fits = False
                                break

                        if not fits:
                            break

                    if fits:
                        break

                    physical_column += 1

                if physical_column >= physical_column_count:
                    raise ValueError(
                        "No existe espacio físico para una celda de header"
                    )

            for occupied_row in range(
                row_index,
                row_index + rowspan,
            ):
                for occupied_column in range(
                    physical_column,
                    physical_column + colspan,
                ):
                    coordinate = (
                        occupied_row,
                        occupied_column,
                    )

                    if coordinate in occupied:
                        raise ValueError(
                            "header_rows contiene celdas superpuestas"
                        )

                    occupied.add(coordinate)

            result.append(
                VectorHeaderCell(
                    label=label,
                    row=row_index,
                    column=physical_column,
                    rowspan=rowspan,
                    colspan=colspan,
                )
            )

    header_heights = [
        mm(4.8)
        if index == 0
        else mm(5.2)
        for index in range(len(header_rows))
    ]

    return result, header_heights


def _build_result_rows(section) -> list[list[str]]:
    rows: list[list[str]] = []

    for row_index, row in enumerate(section.rows, start=1):
        values = [str(row_index)]

        for column in section.columns:
            if isinstance(column, dict):
                source = (
                    column.get("source")
                    or column.get("key")
                )
            else:
                source = (
                    getattr(column, "source", None)
                    or getattr(column, "key", None)
                )

            value = ""

            if source:
                if (
                    row.row_data
                    and source in row.row_data
                ):
                    raw = row.row_data.get(source)
                else:
                    raw = getattr(
                        row,
                        source,
                        None,
                    )

                if raw is not None:
                    value = str(raw)

            values.append(value)

        rows.append(values)

    return rows


def _field(
    context: VectorRenderContext,
    key: str,
) -> str:
    return _field_value(
        key,
        field_sheet=context.field_sheet,
        template_definition=context.template_definition,
        equipment=context.equipment,
        client_name=context.client_name,
        client_attention=context.client_attention,
        client_address=context.client_address,
        certificate_folio=context.certificate_folio,
    )


def _draw_section_title(
    document: FieldSheetVectorDocument,
    *,
    title: str,
    x: float,
    y: float,
    width: float,
) -> float:
    height = mm(5.2)

    document.draw_rounded_box(
        VectorBox(
            x=x,
            y=y - height,
            width=width,
            height=height,
        ),
        radius=mm(1.2),
        line_width=0.6,
    )

    document.draw_centered_text(
        title,
        box=VectorBox(
            x=x,
            y=y - height,
            width=width,
            height=height,
        ),
        style=VectorTextStyle(
            font_size=7.0,
            bold=True,
        ),
    )

    return y - height


def render_field_sheet_vector_preview(
    context: VectorRenderContext,
) -> bytes:
    """
    Preview vectorial genérico del snapshot actual.

    Todavía NO es autoridad documental ni cambia pdf_renderer_key/version.
    Sirve para montar una FieldSheet real sobre v2 y comparar contra el FCA-30.
    """

    page_layout = (
        context.template_definition.get("print_layout")
        or {}
    ).get("page") or {}

    margins = page_layout.get("margins") or {}

    page_spec = VectorPageSpec(
        margin_top=mm(float(margins.get("top", 12))),
        margin_right=mm(float(margins.get("right", 10))),
        margin_bottom=mm(float(margins.get("bottom", 14))),
        margin_left=mm(float(margins.get("left", 10))),
    )

    document = FieldSheetVectorDocument(
        page_spec=page_spec,
    )

    page = document.page_spec

    x = page.margin_left
    width = page.content_width
    cursor_y = page.height - page.margin_top

    document.draw_centered_text(
        "METROLOGÍA Y CALIBRACIÓN",
        box=VectorBox(
            x=x,
            y=cursor_y - mm(5),
            width=width,
            height=mm(5),
        ),
        style=VectorTextStyle(
            font_size=8.5,
            bold=True,
        ),
    )

    cursor_y -= mm(5.5)

    document.draw_centered_text(
        context.template_definition.get("name")
        or "HOJA DE CAMPO",
        box=VectorBox(
            x=x,
            y=cursor_y - mm(5),
            width=width,
            height=mm(5),
        ),
        style=VectorTextStyle(
            font_size=9.0,
            bold=True,
        ),
    )

    cursor_y -= mm(7)

    cursor_y = document.draw_field_grid(
        origin_x=x,
        origin_y=cursor_y,
        total_width=width,
        compact=True,
        rows=[
            [
                (
                    "Orden de trabajo",
                    _field(
                        context,
                        "work_order_number",
                    ),
                    0.5,
                ),
                (
                    "Certificado",
                    _field(
                        context,
                        "reserved_certificate_folio",
                    ),
                    0.5,
                ),
            ],
        ],
        row_height=mm(7),
    )

    cursor_y -= mm(2)

    cursor_y = _draw_section_title(
        document,
        title="Datos del Usuario",
        x=x,
        y=cursor_y,
        width=width,
    )

    cursor_y = document.draw_field_grid(
        origin_x=x,
        origin_y=cursor_y,
        total_width=width,
        compact=True,
        vertical_gap=0,
        rows=[
            [
                (
                    "Atención",
                    _field(context, "attention"),
                    1.0,
                )
            ],
            [
                (
                    "Empresa",
                    _field(context, "company"),
                    1.0,
                )
            ],
            [
                (
                    "Domicilio",
                    _field(context, "address"),
                    1.0,
                )
            ],
        ],
        row_height=mm(6.2),
    )

    cursor_y -= mm(2.5)

    cursor_y = _draw_section_title(
        document,
        title="Datos del Instrumento a Calibrar",
        x=x,
        y=cursor_y,
        width=width,
    )

    cursor_y = document.draw_field_grid(
        origin_x=x,
        origin_y=cursor_y,
        total_width=width,
        compact=True,
        vertical_gap=0,
        rows=[
            [
                (
                    "Instrumento",
                    _field(context, "instrument"),
                    0.5,
                ),
                (
                    "Alcance",
                    _field(context, "scope"),
                    0.5,
                ),
            ],
            [
                (
                    "División mínima",
                    _field(
                        context,
                        "minimum_division",
                    ),
                    0.5,
                ),
                (
                    "Marca",
                    _field(context, "brand"),
                    0.5,
                ),
            ],
            [
                (
                    "Serie",
                    _field(
                        context,
                        "serial_number",
                    ),
                    0.5,
                ),
                (
                    "Modelo",
                    _field(context, "model"),
                    0.5,
                ),
            ],
            [
                (
                    "Identificación",
                    _field(
                        context,
                        "internal_id",
                    ),
                    0.5,
                ),
                (
                    "Ubicación",
                    _field(context, "location"),
                    0.5,
                ),
            ],
        ],
        row_height=mm(6.2),
    )

    cursor_y -= mm(2.5)

    cursor_y = document.draw_field_grid(
        origin_x=x,
        origin_y=cursor_y,
        total_width=width,
        compact=True,
        vertical_gap=0,
        rows=[
            [
                (
                    "Lugar de calibración",
                    _field(
                        context,
                        "calibration_place",
                    ),
                    1.0,
                )
            ],
            [
                (
                    "Fecha de recepción",
                    _field(
                        context,
                        "reception_date",
                    ),
                    1 / 3,
                ),
                (
                    "Fecha de calibración",
                    _field(
                        context,
                        "calibration_date",
                    ),
                    1 / 3,
                ),
                (
                    "Próxima calibración",
                    _field(
                        context,
                        "next_calibration_date",
                    ),
                    1 / 3,
                ),
            ],
        ],
        row_height=mm(6.2),
    )

    cursor_y -= mm(2.5)

    cursor_y = document.draw_field_grid(
        origin_x=x,
        origin_y=cursor_y,
        total_width=width,
        compact=True,
        vertical_gap=0,
        rows=[
            [
                (
                    "Humedad inicial",
                    _field(
                        context,
                        "environment_humidity_start",
                    ),
                    0.5,
                ),
                (
                    "Temperatura inicial",
                    _field(
                        context,
                        "environment_temperature_start",
                    ),
                    0.5,
                ),
            ],
            [
                (
                    "Humedad final",
                    _field(
                        context,
                        "environment_humidity_end",
                    ),
                    0.5,
                ),
                (
                    "Temperatura final",
                    _field(
                        context,
                        "environment_temperature_end",
                    ),
                    0.5,
                ),
            ],
        ],
        row_height=mm(6.2),
    )

    cursor_y -= mm(2.5)

    cursor_y = _draw_section_title(
        document,
        title="OBSERVACIONES",
        x=x,
        y=cursor_y,
        width=width,
    )

    cursor_y = document.draw_field_grid(
        origin_x=x,
        origin_y=cursor_y,
        total_width=width,
        compact=True,
        vertical_gap=0,
        rows=[
            [
                (
                    "Equipo en buen estado general",
                    _field(
                        context,
                        "equipment_general_condition",
                    ),
                    0.5,
                ),
                (
                    "Observaciones",
                    _field(
                        context,
                        "observations",
                    ),
                    0.5,
                ),
            ],
            [
                (
                    "Considerar desviaciones del equipo",
                    _field(
                        context,
                        "consider_equipment_deviations",
                    ),
                    0.5,
                ),
                (
                    "Unidades",
                    _field(
                        context,
                        "units",
                    ),
                    0.5,
                ),
            ],
        ],
        row_height=mm(6.2),
    )

    cursor_y -= mm(3)

    grouped_sections = _group_sections(
        context.field_sheet,
        context.template_definition,
    )

    if grouped_sections:
        section = grouped_sections[0]

        header_cells, header_heights = (
            _build_header_cells(
                section=section,
            )
        )

        column_widths = (
            _resolve_result_column_widths(
                section
            )
        )

        rows = _build_result_rows(
            section
        )

        result_height = (
            sum(header_heights)
            + mm(5.2) * len(rows)
        )

        result_width = width * (2 / 3)

        document.draw_structured_result_table(
            box=VectorBox(
                x=x,
                y=cursor_y - result_height,
                width=result_width,
                height=result_height,
            ),
            column_widths=column_widths,
            header_cells=header_cells,
            header_row_heights=header_heights,
            rows=rows,
            body_row_height=mm(5.2),
        )

        signature_x = (
            x
            + result_width
            + mm(3)
        )

        signature_width = (
            width
            - result_width
            - mm(3)
        )

        signature_cursor = cursor_y

        signature_slots = (
            context.template_definition.get(
                "signature_layout"
            )
            or {}
        ).get("slots") or []

        for slot in signature_slots:
            slot_height = mm(14)

            document.draw_rounded_box(
                VectorBox(
                    x=signature_x,
                    y=signature_cursor - slot_height,
                    width=signature_width,
                    height=slot_height,
                ),
                radius=mm(1.2),
                line_width=0.6,
            )

            document.draw_centered_text(
                str(
                    slot.get("display_label")
                    or slot.get("role")
                    or ""
                ),
                box=VectorBox(
                    x=signature_x,
                    y=signature_cursor - mm(5),
                    width=signature_width,
                    height=mm(4),
                ),
                style=VectorTextStyle(
                    font_size=6.5,
                    bold=True,
                ),
            )

            signature_cursor -= (
                slot_height
                + mm(2)
            )

        trailing_fields = (
            context.template_definition.get(
                "signature_layout"
            )
            or {}
        ).get("trailing_fields") or []

        for key in trailing_fields:
            document.draw_field_cell(
                box=VectorBox(
                    x=signature_x,
                    y=signature_cursor - mm(9),
                    width=signature_width,
                    height=mm(9),
                ),
                label=FIELD_LABELS.get(
                    key,
                    key.replace(
                        "_",
                        " ",
                    ).title(),
                ),
                value=_field(
                    context,
                    key,
                ),
                compact=True,
            )

            signature_cursor -= mm(11)

    footer_y = page.margin_bottom - mm(1)

    document.draw_text(
        (
            f"{context.template_definition.get('document_code') or 'FCA-30'}"
            f" | "
            f"{context.template_definition.get('document_revision') or '-'}"
        ),
        x=page.margin_left,
        y=footer_y,
        style=VectorTextStyle(
            font_size=5.8,
        ),
    )

    document.draw_text(
        "Página 1 de 1",
        x=(
            page.width
            - page.margin_right
            - mm(20)
        ),
        y=footer_y,
        style=VectorTextStyle(
            font_size=5.8,
        ),
    )

    return document.finish()