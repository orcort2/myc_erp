from __future__ import annotations

import base64
from dataclasses import dataclass, field
from math import ceil
from pathlib import Path
from typing import Any

from reportlab.lib.pagesizes import A4, letter, landscape

from app.models.field_sheet import FieldSheet
from app.services.field_sheet_layouts import (
    normalize_signature_layout,
    resolve_organization_print_profile,
)
from app.services.institutional_configurations import resolve_logo_path
from app.services.field_sheet_pdfs import (
    FIELD_LABELS,
    PrintBlock,
    ResultTableSection,
    _build_print_blocks,
    _field_value,
    _row_has_meaningful_capture,
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
    institution: dict[str, Any] | None = None
    signatures: tuple[Any, ...] = field(default_factory=tuple)
    """Firmas ya resueltas por la autoridad correspondiente (field_sheet_pdfs
    ._resolve_field_sheet_signatures): objetos con .role/.display_label/
    .name/.signature_data/.signed_at. El adapter nunca consulta DB -- sólo
    proyecta estos valores, ya resueltos, sobre los slots declarados por
    signature_layout."""


PROJECT_ROOT = Path(__file__).resolve().parents[3]

TITLE_BAR_HEIGHT = mm(5.2)
FIELD_ROW_HEIGHT_COMPACT = mm(6.2)
FIELD_ROW_HEIGHT_DEFAULT = mm(7.6)
TABLE_BODY_ROW_HEIGHT = mm(5.2)
SIGNATURE_SLOT_HEIGHT = mm(14)
SIGNATURE_SLOT_GAP = mm(2)
TRAILING_FIELD_HEIGHT = mm(9)
TRAILING_FIELD_GAP = mm(2)
ROW_GAP = mm(1.4)
GRID_GUTTER = mm(2)


# ---------------------------------------------------------------------------
# Primitivas de campo/columna (sin semántica de template_key).
# ---------------------------------------------------------------------------


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


def _resolve_result_column_widths(section: ResultTableSection) -> list[float]:
    """Anchos relativos incluyendo la columna física de número/etiqueta de fila."""

    columns = section.columns or []
    layout = section.layout or {}

    row_number_width = _parse_percent(layout.get("row_number_width"))
    if row_number_width is None:
        row_number_width = 0.08

    remaining = max(1.0 - row_number_width, 0.01)

    declared_widths: list[float | None] = []
    for column in columns:
        if isinstance(column, dict):
            width = _parse_percent(column.get("width"))
        else:
            width = _parse_percent(getattr(column, "width", None))
        declared_widths.append(width)

    valid_declared = [width for width in declared_widths if width is not None and width > 0]

    if len(valid_declared) == len(columns) and columns:
        total_declared = sum(valid_declared)
        if total_declared <= 0:
            normalized_data_widths = [remaining / max(len(columns), 1)] * len(columns)
        else:
            normalized_data_widths = [remaining * (width / total_declared) for width in valid_declared]
    else:
        normalized_data_widths = [remaining / max(len(columns), 1)] * len(columns) if columns else []

    return [row_number_width, *normalized_data_widths]


def _build_header_cells(*, section: ResultTableSection) -> tuple[list[VectorHeaderCell], list[float]]:
    """Convierte header_rows del DSL a la matriz física del renderer vectorial.

    __row_number__ ocupa la columna física 0; las columnas de resultado
    ocupan 1..N; celdas sin column_key se colocan en la primera posición
    libre; colspan/rowspan se preservan.
    """

    header_rows = section.header_rows or []
    physical_column_count = len(section.columns) + 1
    row_label_header = str((section.layout or {}).get("row_label_header") or "No.")

    if not header_rows:
        cells = [VectorHeaderCell(label=row_label_header, row=0, column=0)]
        for index, column in enumerate(section.columns):
            if isinstance(column, dict):
                label = column.get("label") or column.get("title") or column.get("key") or ""
            else:
                label = getattr(column, "label", None) or getattr(column, "title", None) or getattr(column, "key", "")
            cells.append(VectorHeaderCell(label=str(label), row=0, column=index + 1))
        return cells, [mm(5.4)]

    key_to_physical_column: dict[str, int] = {"__row_number__": 0}
    for index, column in enumerate(section.columns):
        key = column.get("key") if isinstance(column, dict) else getattr(column, "key", None)
        if key:
            key_to_physical_column[str(key)] = index + 1

    occupied: set[tuple[int, int]] = set()
    result: list[VectorHeaderCell] = []

    for row_index, row_definition in enumerate(header_rows):
        cells = row_definition.get("cells") or [] if isinstance(row_definition, dict) else []

        for cell_definition in cells:
            label = str(cell_definition.get("label") or "")
            if cell_definition.get("column_key") == "__row_number__" and label in {"No.", "#"}:
                label = row_label_header
            rowspan = int(cell_definition.get("rowspan") or 1)
            colspan = int(cell_definition.get("colspan") or 1)
            column_key = cell_definition.get("column_key")

            if column_key:
                if column_key not in key_to_physical_column:
                    raise ValueError(f"column_key desconocida en header_rows: {column_key}")
                physical_column = key_to_physical_column[column_key]
            else:
                physical_column = 0
                while physical_column < physical_column_count:
                    fits = True
                    for candidate_row in range(row_index, row_index + rowspan):
                        for candidate_column in range(physical_column, physical_column + colspan):
                            if candidate_column >= physical_column_count or (candidate_row, candidate_column) in occupied:
                                fits = False
                                break
                        if not fits:
                            break
                    if fits:
                        break
                    physical_column += 1
                if physical_column >= physical_column_count:
                    raise ValueError("No existe espacio físico para una celda de header")

            for occupied_row in range(row_index, row_index + rowspan):
                for occupied_column in range(physical_column, physical_column + colspan):
                    coordinate = (occupied_row, occupied_column)
                    if coordinate in occupied:
                        raise ValueError("header_rows contiene celdas superpuestas")
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

    header_heights = [mm(4.8) if index == 0 else mm(5.2) for index in range(len(header_rows))]
    return result, header_heights


def _row_display_label(section: ResultTableSection, row: Any) -> str:
    row_number = getattr(row, "row_number", None)
    if section.row_labels and row_number and 0 < row_number <= len(section.row_labels):
        return section.row_labels[row_number - 1]
    return str(row_number if row_number is not None else "")


def _filter_meaningful_rows(section: ResultTableSection) -> list[Any]:
    """Política de filas vacías del renderer vectorial (más estricta que el
    recorte de sólo-cola del HTML legacy).

    El documento sólo imprime filas que contienen información capturada.
    Esto aplica también a secciones con row_labels fijos (p.ej.
    "Disparo"/"Cierre", "H2S"/"CO"): la existencia de la etiqueta como
    concepto del formato NO es excepción -- una fila con row_label sin
    ningún valor capturado (_row_has_meaningful_capture) se omite igual que
    una fila numerada de captura libre vacía. 0/"0"/False cuentan como
    capturados (ver _has_capture_value); None/""/whitespace no. Las filas
    nunca se renumeran -- su etiqueta impresa sigue siendo su
    row_number/row_label original.
    """

    return [row for row in section.rows if _row_has_meaningful_capture(row, section.columns)]


def _build_result_rows(section: ResultTableSection, rows: list[Any]) -> list[list[str]]:
    output: list[list[str]] = []
    for row in rows:
        values = [_row_display_label(section, row)]
        for column in section.columns:
            source = (
                (column.get("source") or column.get("key"))
                if isinstance(column, dict)
                else (getattr(column, "source", None) or getattr(column, "key", None))
            )
            value = ""
            if source:
                if row.row_data and source in row.row_data:
                    raw = row.row_data.get(source)
                else:
                    raw = getattr(row, source, None)
                if raw is not None:
                    value = str(raw)
            values.append(value)
        output.append(values)
    return output


def _field(context: VectorRenderContext, key: str) -> str:
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
    document: FieldSheetVectorDocument, *, title: str, x: float, y: float, width: float, profile: dict[str, Any] | None = None
) -> float:
    box = VectorBox(x=x, y=y - TITLE_BAR_HEIGHT, width=width, height=TITLE_BAR_HEIGHT)
    primary_color = (profile or {}).get("primary_color")
    header_fill = (profile or {}).get("header_fill")
    document.draw_rounded_box(
        box,
        radius=mm(1.2),
        line_width=0.6,
        fill=header_fill is not None,
        fill_color=header_fill,
        stroke_color=primary_color,
    )
    document.draw_centered_text(title, box=box, style=VectorTextStyle(font_size=7.0, bold=True, color=primary_color))
    return y - TITLE_BAR_HEIGHT


# ---------------------------------------------------------------------------
# Preparación de contenido por tipo de item de grilla (fields / table /
# signatures). "Preparar" separa el cómputo (para poder medir su altura
# antes de decidir en qué página/fila cae) de su dibujo.
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class _PreparedFields:
    rows: list[list[tuple[str, str, float]]]
    row_height: float


def _pack_fields(block: PrintBlock) -> _PreparedFields:
    grid_columns = max(int(block.print_layout.get("grid_columns") or 2), 1)
    row_height = FIELD_ROW_HEIGHT_COMPACT if block.print_layout.get("compact") else FIELD_ROW_HEIGHT_DEFAULT

    rows: list[list[tuple[str, str, int]]] = []
    current: list[tuple[str, str, int]] = []
    current_span = 0

    for item in block.fields:
        span = max(1, min(item.column_span, grid_columns))
        if current and current_span + span > grid_columns:
            rows.append(current)
            current = []
            current_span = 0
        current.append((item.label, item.value, span))
        current_span += span
        if current_span >= grid_columns:
            rows.append(current)
            current = []
            current_span = 0
    if current:
        rows.append(current)

    normalized_rows = [
        [(label, value, span / (sum(s for _, _, s in row) or 1)) for label, value, span in row] for row in rows
    ]
    return _PreparedFields(rows=normalized_rows, row_height=row_height)


def _fields_height(prepared: _PreparedFields) -> float:
    return len(prepared.rows) * prepared.row_height


def _draw_fields_item(document: FieldSheetVectorDocument, prepared: _PreparedFields, *, x: float, y_top: float, width: float) -> float:
    document.draw_field_grid(
        origin_x=x,
        origin_y=y_top,
        total_width=width,
        compact=True,
        vertical_gap=0,
        rows=prepared.rows,
        row_height=prepared.row_height,
    )
    return y_top - _fields_height(prepared)


@dataclass(frozen=True)
class _PreparedTable:
    section: ResultTableSection
    header_cells: list[VectorHeaderCell]
    header_heights: list[float]
    column_widths: list[float]
    rows: list[list[str]]


@dataclass(frozen=True)
class _PreparedTableGroup:
    tables: list[_PreparedTable]
    show_titles: bool


def _prepare_table(section: ResultTableSection, capture_values: dict[str, Any] | None = None) -> _PreparedTable:
    header_cells, header_heights = _build_header_cells(section=section)
    header_choices = (getattr(section, "metadata", None) or {}).get("header_choices") or {}
    if header_choices:
        values = capture_values or {}
        replaced: list[VectorHeaderCell] = []
        for cell in header_cells:
            label = cell.label
            for field_key, choice in header_choices.items():
                if label != choice.get("label"):
                    continue
                selected = values.get(field_key)
                options = choice.get("options") or []
                marks = " ".join(f"[{'X' if selected == option else ' '}] {option}" for option in options)
                label = f"{label}\n{marks}"
            replaced.append(VectorHeaderCell(label=label, row=cell.row, column=cell.column, rowspan=cell.rowspan, colspan=cell.colspan))
        header_cells = replaced
    column_widths = _resolve_result_column_widths(section)
    filtered_rows = _filter_meaningful_rows(section)
    rows = _build_result_rows(section, filtered_rows)
    return _PreparedTable(
        section=section,
        header_cells=header_cells,
        header_heights=header_heights,
        column_widths=column_widths,
        rows=rows,
    )


def _table_content_height(prepared: _PreparedTable) -> float:
    return sum(prepared.header_heights) + TABLE_BODY_ROW_HEIGHT * len(prepared.rows)


def _draw_table_content(
    document: FieldSheetVectorDocument, prepared: _PreparedTable, *, x: float, y_top: float, width: float, profile: dict[str, Any] | None = None
) -> float:
    height = _table_content_height(prepared)
    document.draw_structured_result_table(
        box=VectorBox(x=x, y=y_top - height, width=width, height=height),
        column_widths=prepared.column_widths,
        header_cells=prepared.header_cells,
        header_row_heights=prepared.header_heights,
        rows=prepared.rows,
        body_row_height=TABLE_BODY_ROW_HEIGHT,
        header_fill=(profile or {}).get("header_fill"),
        accent_color=(profile or {}).get("primary_color"),
    )
    return y_top - height


@dataclass(frozen=True)
class _PreparedSignatures:
    slots: list[dict]
    trailing_fields: list[str]
    columns: int
    groups: list[dict]


@dataclass(frozen=True)
class _PreparedStatic:
    text: str
    caption: str
    graphic: bool
    height: float
    asset_path: str | None = None


def _decode_signature_image(signature_data: str | None) -> bytes | None:
    """Decodifica un data URL de firma (p.ej. "data:image/png;base64,...")
    capturado por FieldSheetSignature/LabWorkOrderSignatureSession. Devuelve
    None si no hay payload utilizable -- nunca lanza sobre datos malformados,
    el slot simplemente cae de vuelta al nombre/label."""

    if not signature_data or "," not in signature_data:
        return None
    _, _, encoded = signature_data.partition(",")
    try:
        return base64.b64decode(encoded)
    except (ValueError, TypeError):
        return None


def _merge_resolved_signature(slot: dict[str, Any], resolved_by_role: dict[str, Any]) -> dict[str, Any]:
    resolved = resolved_by_role.get(slot.get("role"))
    if resolved is None:
        return slot
    merged = dict(slot)
    merged["name"] = getattr(resolved, "name", None)
    merged["signature_data"] = getattr(resolved, "signature_data", None)
    merged["signed_at"] = getattr(resolved, "signed_at", None)
    return merged


def _prepare_signatures(template_definition: dict[str, Any], resolved_signatures: tuple[Any, ...] = ()) -> _PreparedSignatures:
    layout = normalize_signature_layout(template_definition.get("signature_layout"))
    resolved_by_role = {getattr(item, "role", None): item for item in resolved_signatures}
    slots = [_merge_resolved_signature(slot, resolved_by_role) for slot in layout["slots"]]
    if layout["columns"]:
        columns = layout["columns"]
    elif layout["direction"] == "vertical":
        columns = 1
    else:
        columns = max(len(slots), 1)
    return _PreparedSignatures(slots=slots, trailing_fields=layout["trailing_fields"], columns=columns, groups=layout.get("groups") or [])


def _signatures_rows_count(prepared: _PreparedSignatures) -> int:
    if prepared.groups:
        return len(prepared.groups)
    if not prepared.slots:
        return 0
    return ceil(len(prepared.slots) / max(prepared.columns, 1))


def _signatures_height(prepared: _PreparedSignatures) -> float:
    rows = _signatures_rows_count(prepared)
    height = rows * SIGNATURE_SLOT_HEIGHT + max(rows - 1, 0) * SIGNATURE_SLOT_GAP if rows else 0.0
    if prepared.trailing_fields:
        height += len(prepared.trailing_fields) * (TRAILING_FIELD_HEIGHT + TRAILING_FIELD_GAP)
    return height


def _draw_signatures_item(
    document: FieldSheetVectorDocument,
    context: VectorRenderContext,
    prepared: _PreparedSignatures,
    *,
    x: float,
    y_top: float,
    width: float,
) -> float:
    cols = max(prepared.columns, 1)
    col_width = (width - GRID_GUTTER * (cols - 1)) / cols if cols > 1 else width

    grouped_rows: list[tuple[list[dict], int]]
    if prepared.groups:
        by_role = {slot.get("role"): slot for slot in prepared.slots}
        grouped_rows = [
            ([by_role[role] for role in group.get("slots", []) if role in by_role], max(int(group.get("columns") or 1), 1))
            for group in prepared.groups
        ]
    else:
        grouped_rows = [(prepared.slots[index:index + cols], cols) for index in range(0, len(prepared.slots), cols)]

    role_line_height = mm(4.2)
    name_line_height = mm(4.0)

    for row, (row_slots, row_columns) in enumerate(grouped_rows):
        row_col_width = (width - GRID_GUTTER * (row_columns - 1)) / row_columns
        for col, slot in enumerate(row_slots):
            slot_x = x + col * (row_col_width + GRID_GUTTER)
            slot_top = y_top - row * (SIGNATURE_SLOT_HEIGHT + SIGNATURE_SLOT_GAP)
            box = VectorBox(x=slot_x, y=slot_top - SIGNATURE_SLOT_HEIGHT, width=row_col_width, height=SIGNATURE_SLOT_HEIGHT)
            document.draw_rounded_box(box, radius=mm(1.2), line_width=0.6)

            label_text = str(slot.get("display_label") or slot.get("role") or "")
            name = slot.get("name")
            image_bytes = _decode_signature_image(slot.get("signature_data"))

            # Paridad documental con el renderer HTML legacy
            # (field_sheet_engine_pdf.html): siempre "{display_label}" seguido
            # de "{name}" o, si la sesión LAB/FieldSheetSignature aún no
            # resolvió firma para ese rol, "Pendiente" -- nunca un placeholder
            # visual distinto entre v1 y v2.
            reserved_text_height = role_line_height + name_line_height
            content_box = VectorBox(
                x=box.x, y=box.y + reserved_text_height, width=box.width, height=box.height - reserved_text_height
            )
            role_box = VectorBox(x=box.x, y=box.y + name_line_height, width=box.width, height=role_line_height)
            name_box = VectorBox(x=box.x, y=box.y, width=box.width, height=name_line_height)

            if image_bytes:
                document.draw_image_bytes(image_bytes, box=content_box, padding=mm(0.8))
            document.draw_centered_text(label_text, box=role_box, style=VectorTextStyle(font_size=6.0, bold=True))
            document.draw_centered_text(str(name) if name else "Pendiente", box=name_box, style=VectorTextStyle(font_size=6.0))

    rows_count = _signatures_rows_count(prepared)
    cursor_y = y_top - (rows_count * SIGNATURE_SLOT_HEIGHT + max(rows_count - 1, 0) * SIGNATURE_SLOT_GAP)

    for key in prepared.trailing_fields:
        cell_box = VectorBox(x=x, y=cursor_y - TRAILING_FIELD_HEIGHT, width=width, height=TRAILING_FIELD_HEIGHT)
        document.draw_field_cell(
            box=cell_box,
            label=FIELD_LABELS.get(key, key.replace("_", " ").title()),
            value=_field(context, key),
            compact=True,
        )
        cursor_y -= TRAILING_FIELD_HEIGHT + TRAILING_FIELD_GAP

    return cursor_y


# ---------------------------------------------------------------------------
# Motor de grilla genérico (equivalente vectorial del CSS grid que usa
# field_sheet_engine_pdf.html: document.grid_columns + block.print_layout.
# column_span). No conoce template_key; sólo lee números de la definición.
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class _GridItem:
    kind: str  # "fields" | "table" | "signatures"
    column_span: int
    title: str
    title_visible: bool
    payload: Any
    unit_value: str | None = None
    width_fraction: float | None = None
    page_break_before: bool = False


def _collect_grid_items(print_blocks: list[PrintBlock], context: VectorRenderContext) -> list[_GridItem]:
    items: list[_GridItem] = []

    for block in print_blocks:
        layout = block.print_layout
        span = max(1, int(layout.get("column_span") or 1))
        title_visible = bool(layout.get("title_visible", True))

        if block.block_type in {"StaticTextBlock", "ReferenceGraphicBlock"}:
            graphic = block.block_type == "ReferenceGraphicBlock"
            items.append(_GridItem(
                kind="static",
                column_span=span,
                title=block.title,
                title_visible=title_visible,
                payload=_PreparedStatic(
                    text=str(block.metadata.get("text") or ""),
                    caption=str(block.metadata.get("caption") or ""),
                    graphic=graphic,
                    height=mm(28 if graphic else 12),
                    asset_path=str(block.metadata.get("asset_path") or "") or None,
                ),
            ))
            continue

        if block.block_type == "SignaturesBlock":
            prepared = _prepare_signatures(context.template_definition, context.signatures)
            items.append(
                _GridItem(kind="signatures", column_span=span, title=block.title, title_visible=title_visible, payload=prepared)
            )
            continue

        if block.fields:
            items.append(
                _GridItem(kind="fields", column_span=span, title=block.title, title_visible=title_visible, payload=_pack_fields(block))
            )

        if len(block.sections) > 1 and span < 4:
            items.append(_GridItem(
                kind="table_group",
                column_span=span,
                title=block.title,
                title_visible=False,
                payload=_PreparedTableGroup(
                    tables=[_prepare_table(section, context.field_sheet.capture_values or {}) for section in block.sections],
                    show_titles=title_visible,
                ),
            ))
            continue

        for section in block.sections:
            section_layout = section.layout or {}
            items.append(
                _GridItem(
                    kind="table",
                    column_span=span,
                    title=section.title,
                    title_visible=title_visible and bool(section_layout.get("print_title_visible", True)),
                    payload=_prepare_table(section, context.field_sheet.capture_values or {}),
                    unit_value=section.unit_value,
                    width_fraction=float(section_layout.get("width_fraction") or 1.0),
                    page_break_before=bool(section.page_break_before),
                )
            )

    return items


def _item_content_height(item: _GridItem) -> float:
    if item.kind == "fields":
        return _fields_height(item.payload)
    if item.kind == "table":
        return _table_content_height(item.payload)
    if item.kind == "table_group":
        return sum(
            _table_content_height(table) + (TITLE_BAR_HEIGHT if item.payload.show_titles and (table.section.layout or {}).get("print_title_visible", True) else 0) + ROW_GAP
            for table in item.payload.tables
        )
    if item.kind == "signatures":
        return _signatures_height(item.payload)
    if item.kind == "static":
        return item.payload.height
    return 0.0


def _item_total_height(item: _GridItem) -> float:
    return _item_content_height(item) + (TITLE_BAR_HEIGHT if item.title_visible else 0.0)


def _draw_item(
    document: FieldSheetVectorDocument,
    context: VectorRenderContext,
    item: _GridItem,
    *,
    x: float,
    y_top: float,
    width: float,
    profile: dict[str, Any] | None = None,
) -> float:
    cursor_y = y_top
    if item.title_visible:
        title_text = item.title
        if item.kind == "table" and item.unit_value:
            title_text = f"{title_text} · Unidades: {item.unit_value}"
        cursor_y = _draw_section_title(document, title=title_text, x=x, y=cursor_y, width=width, profile=profile)

    if item.kind == "fields":
        return _draw_fields_item(document, item.payload, x=x, y_top=cursor_y, width=width)
    if item.kind == "table":
        return _draw_table_content(document, item.payload, x=x, y_top=cursor_y, width=width, profile=profile)
    if item.kind == "table_group":
        for table in item.payload.tables:
            if item.payload.show_titles and (table.section.layout or {}).get("print_title_visible", True):
                cursor_y = _draw_section_title(document, title=table.section.title, x=x, y=cursor_y, width=width, profile=profile)
            cursor_y = _draw_table_content(document, table, x=x, y_top=cursor_y, width=width, profile=profile) - ROW_GAP
        return cursor_y
    if item.kind == "signatures":
        return _draw_signatures_item(document, context, item.payload, x=x, y_top=cursor_y, width=width)
    if item.kind == "static":
        box = VectorBox(x=x, y=cursor_y - item.payload.height, width=width, height=item.payload.height)
        document.draw_rounded_box(box, radius=mm(1.2), line_width=0.6)
        if item.payload.graphic and item.payload.asset_path:
            asset = (PROJECT_ROOT / item.payload.asset_path).resolve()
            allowed_root = (PROJECT_ROOT / "backend" / "app" / "assets").resolve()
            if asset.is_relative_to(allowed_root) and asset.is_file():
                document.draw_image(str(asset), box=box, padding=mm(1.2))
            else:
                document.draw_centered_text(item.payload.caption, box=box, style=VectorTextStyle(font_size=6.5, bold=True))
        else:
            text = item.payload.caption if item.payload.graphic else item.payload.text
            document.draw_centered_text(text, box=box, style=VectorTextStyle(font_size=6.5, bold=item.payload.graphic))
        return cursor_y - item.payload.height
    return cursor_y


_GridRow = list[tuple[_GridItem, int, int]]


def _pack_grid_rows(items: list[_GridItem], grid_columns: int) -> list[_GridRow]:
    """Empaqueta items en filas siguiendo el mismo algoritmo de auto-flow no
    denso que usa CSS grid en field_sheet_engine_pdf.html: cuando un item no
    cabe en el espacio restante de la fila actual, se abre una fila nueva
    (nunca se rellenan huecos de filas ya cerradas)."""

    grid_columns = max(grid_columns, 1)
    rows: list[_GridRow] = []
    current: _GridRow = []
    cursor_col = 0

    for item in items:
        span = (
            min(max(round(item.width_fraction * grid_columns), 1), grid_columns)
            if item.width_fraction is not None
            else min(max(item.column_span, 1), grid_columns)
        )
        if current and cursor_col + span > grid_columns:
            rows.append(current)
            current = []
            cursor_col = 0
        current.append((item, cursor_col, span))
        cursor_col += span
        if cursor_col >= grid_columns:
            rows.append(current)
            current = []
            cursor_col = 0

    if current:
        rows.append(current)

    return rows


def _paginate(rows: list[_GridRow], *, available_height: float, row_gap: float) -> list[list[_GridRow]]:
    pages: list[list[_GridRow]] = []
    current: list[_GridRow] = []
    remaining = available_height

    for row in rows:
        if any(item.page_break_before for item, _, _ in row) and current:
            pages.append(current)
            current = []
            remaining = available_height
        row_height = max((_item_total_height(item) for item, _, _ in row), default=0.0)
        needed = row_height + (row_gap if current else 0.0)
        if needed > remaining and current:
            pages.append(current)
            current = []
            remaining = available_height
            needed = row_height
        current.append(row)
        remaining -= needed

    if current:
        pages.append(current)

    return pages or [[]]


LETTERHEAD_LOGO_WIDTH = mm(16)
LETTERHEAD_LOGO_GUTTER = mm(2)


def _draw_letterhead_and_title(
    document: FieldSheetVectorDocument,
    *,
    page: VectorPageSpec,
    template_definition: dict[str, Any],
    x: float,
    width: float,
    header_visible: bool,
    title_visible: bool,
    institution: dict[str, Any] | None = None,
    profile: dict[str, Any] | None = None,
) -> float:
    cursor_y = page.height - page.margin_top
    organization_profile = profile or {}
    primary_color = organization_profile.get("primary_color")
    header_fill = organization_profile.get("header_fill")

    if header_visible:
        institution_values = institution or {}
        institution_name = institution_values.get("legal_name") or organization_profile.get("legal_name") or organization_profile.get("display_name") or "MYC"

        logo_path = (
            resolve_logo_path(institution_values, PROJECT_ROOT)
            if organization_profile.get("logo_key") != "none"
            else None
        )
        show_logo = logo_path is not None
        text_x = x + (LETTERHEAD_LOGO_WIDTH + LETTERHEAD_LOGO_GUTTER if show_logo else 0)
        text_width = width - (LETTERHEAD_LOGO_WIDTH + LETTERHEAD_LOGO_GUTTER if show_logo else 0)
        letterhead_top = cursor_y

        document.draw_centered_text(
            str(institution_name).upper(),
            box=VectorBox(x=text_x, y=cursor_y - mm(5), width=text_width, height=mm(5)),
            style=VectorTextStyle(font_size=8.5, bold=True, color=primary_color),
        )
        cursor_y -= mm(5.5)
        contact = " · ".join(str(institution_values.get(key) or "") for key in ("address", "phone", "email") if institution_values.get(key))
        if contact:
            document.draw_centered_text(contact, box=VectorBox(x=text_x, y=cursor_y - mm(4), width=text_width - mm(24), height=mm(4)), style=VectorTextStyle(font_size=5.5))
            cursor_y -= mm(4)

        if show_logo:
            # El logo ocupa exactamente la misma franja vertical que el
            # nombre institucional (+ contacto si lo hay), a la izquierda --
            # nunca invade el título ni el bloque de código documental.
            document.draw_image(
                str(logo_path),
                box=VectorBox(x=x, y=cursor_y, width=LETTERHEAD_LOGO_WIDTH, height=letterhead_top - cursor_y),
                padding=mm(0.5),
            )

        code = template_definition.get("document_code") or template_definition.get("code") or "FCA-30"
        revision = template_definition.get("document_revision") or template_definition.get("revision") or "-"
        control_width = mm(22)
        control_box = VectorBox(x=x + width - control_width, y=cursor_y - mm(0.5), width=control_width, height=mm(8))
        document.draw_rounded_box(
            control_box,
            radius=mm(1),
            line_width=0.5,
            fill=header_fill is not None,
            fill_color=header_fill,
            stroke_color=primary_color,
        )
        document.draw_centered_text(
            str(code),
            box=VectorBox(x=control_box.x, y=control_box.y + control_box.height / 2, width=control_width, height=control_box.height / 2),
            style=VectorTextStyle(font_size=6, bold=True, color=primary_color),
        )
        document.draw_centered_text(
            str(revision),
            box=VectorBox(x=control_box.x, y=control_box.y, width=control_width, height=control_box.height / 2),
            style=VectorTextStyle(font_size=6, bold=True, color=primary_color),
        )

    if title_visible:
        document.draw_centered_text(
            template_definition.get("name") or "HOJA DE CAMPO",
            box=VectorBox(x=x, y=cursor_y - mm(5), width=width, height=mm(5)),
            style=VectorTextStyle(font_size=9.0, bold=True, color=primary_color),
        )
        cursor_y -= mm(7)
    else:
        cursor_y -= mm(1.5)

    return cursor_y


def _draw_footer(
    document: FieldSheetVectorDocument,
    *,
    page: VectorPageSpec,
    template_definition: dict[str, Any],
    page_index: int,
    total_pages: int,
) -> None:
    footer_y = page.margin_bottom - mm(1)
    code = template_definition.get("document_code") or template_definition.get("code") or "FCA-30"
    revision = template_definition.get("document_revision") or template_definition.get("revision") or "-"
    document.draw_text(f"{code} | {revision}", x=page.margin_left, y=footer_y, style=VectorTextStyle(font_size=5.8))
    document.draw_text(
        f"Página {page_index} de {total_pages}",
        x=page.width - page.margin_right - mm(24),
        y=footer_y,
        style=VectorTextStyle(font_size=5.8),
    )


def render_field_sheet_vector_preview(context: VectorRenderContext) -> bytes:
    """Renderer vectorial genérico, guiado por completo por
    template_definition["blocks"]/["result_sections"]/["signature_layout"]/
    ["print_layout"].

    No contiene ninguna rama por template_key: el layout de grilla
    (document.grid_columns + block.print_layout.column_span), el layout de
    firmas (signature_layout.direction/columns) y el filtrado de filas
    vacías (_filter_meaningful_rows) son policies puramente declarativas
    aplicadas igual a los 23 documentos oficiales y a cualquier definición
    futura.

    Todavía no es autoridad documental ni cambia pdf_renderer_key/version.
    """

    template_definition = context.template_definition
    # Resuelto una sola vez por documento: la organización (MYC/CAPYMET/...)
    # gobierna logo/colores institucionales de forma transversal -- nunca por
    # template_key. Ver resolve_organization_print_profile.
    profile = resolve_organization_print_profile(template_definition)

    page_layout = (template_definition.get("print_layout") or {}).get("page") or {}
    margins = page_layout.get("margins") or {}
    page_size = A4 if page_layout.get("size") == "a4" else letter
    if page_layout.get("orientation") == "landscape":
        page_size = landscape(page_size)
    page_spec = VectorPageSpec(
        width=page_size[0],
        height=page_size[1],
        margin_top=mm(float(margins.get("top", 12))),
        margin_right=mm(float(margins.get("right", 10))),
        margin_bottom=mm(float(margins.get("bottom", 14))),
        margin_left=mm(float(margins.get("left", 10))),
    )

    document = FieldSheetVectorDocument(page_spec=page_spec)
    page = document.page_spec

    document_layout = (template_definition.get("print_layout") or {}).get("document") or {}
    grid_columns = max(int(document_layout.get("grid_columns") or 1), 1)
    header_visible = document_layout.get("header_visible", True)
    title_visible = document_layout.get("title_visible", True)
    footer_visible = document_layout.get("footer_visible", True)

    x = page.margin_left
    width = page.content_width
    usable_col_width = (width - GRID_GUTTER * (grid_columns - 1)) / grid_columns if grid_columns > 1 else width

    print_blocks = _build_print_blocks(
        context.field_sheet,
        template_definition,
        equipment=context.equipment,
        client_name=context.client_name,
        client_attention=context.client_attention,
        client_address=context.client_address,
        certificate_folio=context.certificate_folio,
    )

    items = _collect_grid_items(print_blocks, context)
    rows = _pack_grid_rows(items, grid_columns)

    institutional_contact_height = mm(4) if header_visible and context.institution and any(context.institution.get(key) for key in ("address", "phone", "email")) else 0
    header_and_title_height = (mm(5.5) if header_visible else 0.0) + institutional_contact_height + (mm(7) if title_visible else mm(1.5))
    available_height = max(page.content_height - header_and_title_height, mm(20))

    pages = _paginate(rows, available_height=available_height, row_gap=ROW_GAP)
    total_pages = len(pages)

    for page_index, page_rows in enumerate(pages, start=1):
        if page_index > 1:
            document.new_page()

        cursor_y = _draw_letterhead_and_title(
            document,
            page=page,
            template_definition=template_definition,
            x=x,
            width=width,
            header_visible=header_visible,
            title_visible=title_visible,
            institution=context.institution,
            profile=profile,
        )

        for row in page_rows:
            row_height = max((_item_total_height(item) for item, _, _ in row), default=0.0)
            for item, col_start, span in row:
                item_x = x + col_start * (usable_col_width + GRID_GUTTER)
                item_width = span * usable_col_width + GRID_GUTTER * (span - 1)
                _draw_item(document, context, item, x=item_x, y_top=cursor_y, width=item_width, profile=profile)
            cursor_y -= row_height + ROW_GAP

        if footer_visible:
            _draw_footer(
                document,
                page=page,
                template_definition=template_definition,
                page_index=page_index,
                total_pages=total_pages,
            )

    return document.finish()
