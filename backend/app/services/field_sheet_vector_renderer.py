from __future__ import annotations

from dataclasses import dataclass
from io import BytesIO
from typing import Iterable

from reportlab.lib.colors import HexColor
from reportlab.lib.pagesizes import letter
from reportlab.pdfbase.pdfmetrics import stringWidth
from reportlab.pdfgen.canvas import Canvas
from reportlab.lib.utils import ImageReader


POINTS_PER_INCH = 72.0
MM_PER_INCH = 25.4

LETTER_WIDTH_PT, LETTER_HEIGHT_PT = letter


def mm(value: float) -> float:
    """Convierte milímetros a puntos PDF."""
    return value * POINTS_PER_INCH / MM_PER_INCH


@dataclass(frozen=True)
class VectorPageSpec:
    width: float = LETTER_WIDTH_PT
    height: float = LETTER_HEIGHT_PT
    margin_left: float = mm(10)
    margin_right: float = mm(10)
    margin_top: float = mm(12)
    margin_bottom: float = mm(14)

    @property
    def content_width(self) -> float:
        return self.width - self.margin_left - self.margin_right

    @property
    def content_height(self) -> float:
        return self.height - self.margin_top - self.margin_bottom


@dataclass(frozen=True)
class VectorTextStyle:
    font_name: str = "Helvetica"
    font_size: float = 8.0
    line_height: float = 1.2
    bold: bool = False
    color: str | None = None

    @property
    def resolved_font_name(self) -> str:
        if self.bold and self.font_name == "Helvetica":
            return "Helvetica-Bold"
        return self.font_name


@dataclass(frozen=True)
class VectorBox:
    x: float
    y: float
    width: float
    height: float


@dataclass(frozen=True)
class VectorHeaderCell:
    """
    Celda declarativa de encabezado.

    row/column son índices físicos 0-based dentro de la matriz de encabezado.
    rowspan/colspan describen cuántas filas/columnas físicas ocupa.

    No conoce template_key ni semántica metrológica.
    """

    label: str
    row: int
    column: int
    rowspan: int = 1
    colspan: int = 1


class FieldSheetVectorDocument:
    """
    Primitive vectorial genérico para PDFs controlados de hojas de campo.

    No conoce template_key, magnitud, equipo ni organización.
    Su responsabilidad es exclusivamente geometría/dibujo PDF.
    """

    def __init__(
        self,
        *,
        page_spec: VectorPageSpec | None = None,
    ) -> None:
        self.page_spec = page_spec or VectorPageSpec()
        self._buffer = BytesIO()

        self.canvas = Canvas(
            self._buffer,
            pagesize=(
                self.page_spec.width,
                self.page_spec.height,
            ),
        )

    def finish(self) -> bytes:
        self.canvas.save()
        return self._buffer.getvalue()

    def new_page(self) -> None:
        self.canvas.showPage()

    def draw_image(self, path: str, *, box: VectorBox, padding: float = mm(1)) -> None:
        """Draw a trusted local reference asset, centered and aspect-safe."""
        self._draw_image_reader(ImageReader(path), box=box, padding=padding)

    def draw_image_bytes(self, data: bytes, *, box: VectorBox, padding: float = mm(1)) -> None:
        """Draw an in-memory raster image (e.g. a decoded signature capture),
        centered and aspect-safe, same placement rules as draw_image."""
        self._draw_image_reader(ImageReader(BytesIO(data)), box=box, padding=padding)

    def _draw_image_reader(self, image: ImageReader, *, box: VectorBox, padding: float) -> None:
        source_width, source_height = image.getSize()
        available_width = max(box.width - padding * 2, 1)
        available_height = max(box.height - padding * 2, 1)
        scale = min(available_width / source_width, available_height / source_height)
        width = source_width * scale
        height = source_height * scale
        self.canvas.drawImage(
            image,
            box.x + (box.width - width) / 2,
            box.y + (box.height - height) / 2,
            width=width,
            height=height,
            preserveAspectRatio=True,
            mask="auto",
        )

    def draw_rounded_box(
        self,
        box: VectorBox,
        *,
        radius: float = mm(1.2),
        line_width: float = 0.6,
        stroke: bool = True,
        fill: bool = False,
        stroke_color: str | None = None,
        fill_color: str | None = None,
    ) -> None:
        self.canvas.saveState()
        self.canvas.setLineWidth(line_width)
        if stroke_color is not None:
            self.canvas.setStrokeColor(HexColor(stroke_color))
        if fill_color is not None:
            self.canvas.setFillColor(HexColor(fill_color))

        self.canvas.roundRect(
            box.x,
            box.y,
            box.width,
            box.height,
            radius,
            stroke=1 if stroke else 0,
            fill=1 if fill else 0,
        )
        self.canvas.restoreState()

    def draw_line(
        self,
        *,
        x1: float,
        y1: float,
        x2: float,
        y2: float,
        line_width: float = 0.6,
        color: str | None = None,
    ) -> None:
        self.canvas.saveState()
        self.canvas.setLineWidth(line_width)
        if color is not None:
            self.canvas.setStrokeColor(HexColor(color))
        self.canvas.line(x1, y1, x2, y2)
        self.canvas.restoreState()

    def draw_text(
        self,
        text: str,
        *,
        x: float,
        y: float,
        style: VectorTextStyle | None = None,
    ) -> None:
        resolved = style or VectorTextStyle()

        self.canvas.saveState()
        self.canvas.setFont(
            resolved.resolved_font_name,
            resolved.font_size,
        )
        if resolved.color is not None:
            self.canvas.setFillColor(HexColor(resolved.color))

        self.canvas.drawString(
            x,
            y,
            text,
        )
        self.canvas.restoreState()

    def draw_centered_text(
        self,
        text: str,
        *,
        box: VectorBox,
        style: VectorTextStyle | None = None,
    ) -> None:
        resolved = style or VectorTextStyle()

        font_name = resolved.resolved_font_name
        font_size = resolved.font_size

        self.canvas.saveState()
        self.canvas.setFont(
            font_name,
            font_size,
        )
        if resolved.color is not None:
            self.canvas.setFillColor(HexColor(resolved.color))

        lines = wrap_text(
            text,
            usable_width=max(box.width - mm(1.2), 1),
            font_name=font_name,
            font_size=font_size,
        )

        line_step = font_size * resolved.line_height

        total_text_height = line_step * max(len(lines), 1)

        cursor_y = (
            box.y
            + (box.height + total_text_height) / 2
            - line_step
            + 1
        )

        for line in lines:
            text_width = stringWidth(
                line,
                font_name,
                font_size,
            )

            x = (
                box.x
                + max(
                    (box.width - text_width) / 2,
                    0,
                )
            )

            self.canvas.drawString(
                x,
                cursor_y,
                line,
            )

            cursor_y -= line_step

        self.canvas.restoreState()

    def draw_wrapped_text(
        self,
        text: str,
        *,
        box: VectorBox,
        style: VectorTextStyle | None = None,
        padding_x: float = mm(1.4),
        padding_y: float = mm(1.1),
        max_lines: int | None = None,
    ) -> list[str]:
        resolved = style or VectorTextStyle()

        usable_width = max(
            box.width - (padding_x * 2),
            1,
        )

        lines = wrap_text(
            text,
            usable_width=usable_width,
            font_name=resolved.resolved_font_name,
            font_size=resolved.font_size,
        )

        if max_lines is not None:
            lines = lines[:max_lines]

        self.canvas.saveState()
        self.canvas.setFont(
            resolved.resolved_font_name,
            resolved.font_size,
        )
        if resolved.color is not None:
            self.canvas.setFillColor(HexColor(resolved.color))

        line_step = (
            resolved.font_size
            * resolved.line_height
        )

        cursor_y = (
            box.y
            + box.height
            - padding_y
            - resolved.font_size
        )

        for line in lines:
            if cursor_y < box.y + padding_y:
                break

            self.canvas.drawString(
                box.x + padding_x,
                cursor_y,
                line,
            )

            cursor_y -= line_step

        self.canvas.restoreState()

        return lines

    def draw_field_cell(
        self,
        *,
        box: VectorBox,
        label: str,
        value: str,
        compact: bool = False,
        radius: float = mm(1.2),
    ) -> None:
        self.draw_rounded_box(
            box,
            radius=radius,
            line_width=0.6,
        )

        label_style = VectorTextStyle(
            font_size=6.8 if compact else 7.2,
            line_height=1.15,
            bold=True,
        )

        value_style = VectorTextStyle(
            font_size=7.4 if compact else 8.0,
            line_height=1.2,
        )

        top_inset = mm(0.3)
        label_height = mm(2.6 if compact else 3.0)
        gap = mm(0.3)
        bottom_inset = mm(0.3)

        label_box = VectorBox(
            x=box.x,
            y=box.y + box.height - top_inset - label_height,
            width=box.width,
            height=label_height,
        )

        value_box_height = max(
            box.height - top_inset - label_height - gap - bottom_inset,
            value_style.font_size,
        )
        value_box = VectorBox(
            x=box.x,
            y=box.y + bottom_inset,
            width=box.width,
            height=value_box_height,
        )
        # padding_y se reduce en cajas estrechas para garantizar que el valor
        # siempre tenga espacio para al menos una línea -- un padding fijo
        # dejaba value_box más bajo que font_size + 2*padding en filas
        # compactas, y draw_wrapped_text descartaba la línea entera antes de
        # dibujar nada (el valor capturado nunca llegaba a imprimirse).
        value_padding_y = min(mm(0.3), max((value_box_height - value_style.font_size) / 2, 0))

        self.draw_wrapped_text(
            label,
            box=label_box,
            style=label_style,
            padding_x=mm(1.2),
            padding_y=0,
            max_lines=1,
        )

        self.draw_wrapped_text(
            value or "-",
            box=value_box,
            style=value_style,
            padding_x=mm(1.2),
            padding_y=value_padding_y,
        )

    def draw_field_grid(
        self,
        *,
        origin_x: float,
        origin_y: float,
        total_width: float,
        rows: Iterable[
            list[
                tuple[
                    str,
                    str,
                    float,
                ]
            ]
        ],
        row_height: float = mm(7.6),
        vertical_gap: float = mm(1.2),
        horizontal_gap: float = mm(1.2),
        compact: bool = False,
    ) -> float:
        cursor_y = origin_y

        for row in rows:
            available_width = (
                total_width
                - horizontal_gap
                * max(
                    len(row) - 1,
                    0,
                )
            )

            cursor_x = origin_x

            for label, value, fraction in row:
                cell_width = (
                    available_width
                    * fraction
                )

                box = VectorBox(
                    x=cursor_x,
                    y=cursor_y - row_height,
                    width=cell_width,
                    height=row_height,
                )

                self.draw_field_cell(
                    box=box,
                    label=label,
                    value=value,
                    compact=compact,
                )

                cursor_x += (
                    cell_width
                    + horizontal_gap
                )

            cursor_y -= (
                row_height
                + vertical_gap
            )

        return cursor_y

    def draw_structured_result_table(
        self,
        *,
        box: VectorBox,
        column_widths: list[float],
        header_cells: list[VectorHeaderCell],
        header_row_heights: list[float],
        rows: list[list[str]],
        body_row_height: float = mm(5.2),
        outer_radius: float = mm(1.2),
        line_width: float = 0.6,
        header_fill: str | None = None,
        accent_color: str | None = None,
    ) -> None:
        """
        Tabla vectorial estructurada con soporte real para:

        - múltiples filas físicas de header;
        - rowspan;
        - colspan;
        - anchos relativos;
        - perímetro exterior redondeado;
        - cuerpo tabular.

        El renderer no conoce etiquetas ni significado de columnas.

        header_fill/accent_color son puramente cosméticos (branding
        institucional por organización, resuelto por el caller): con ambos
        en None el resultado es idéntico al de antes de que existieran --
        ninguna geometría (colspan/rowspan/anchos/alturas) depende de ellos.
        accent_color tiñe únicamente el marco exterior y los separadores del
        header; las líneas internas del cuerpo permanecen neutras.
        """

        if not column_widths:
            raise ValueError(
                "column_widths no puede estar vacío"
            )

        if not header_row_heights:
            raise ValueError(
                "header_row_heights no puede estar vacío"
            )

        column_count = len(column_widths)
        header_row_count = len(header_row_heights)

        total_fraction = sum(column_widths)

        if total_fraction <= 0:
            raise ValueError(
                "column_widths debe sumar un valor mayor que cero"
            )

        normalized_widths = [
            width / total_fraction
            for width in column_widths
        ]

        for cell in header_cells:
            if cell.row < 0 or cell.column < 0:
                raise ValueError(
                    "row y column deben ser >= 0"
                )

            if cell.rowspan < 1 or cell.colspan < 1:
                raise ValueError(
                    "rowspan y colspan deben ser >= 1"
                )

            if (
                cell.row
                + cell.rowspan
                > header_row_count
            ):
                raise ValueError(
                    "Header cell excede las filas disponibles"
                )

            if (
                cell.column
                + cell.colspan
                > column_count
            ):
                raise ValueError(
                    "Header cell excede las columnas disponibles"
                )

        occupied: set[tuple[int, int]] = set()

        for cell in header_cells:
            for row_index in range(
                cell.row,
                cell.row + cell.rowspan,
            ):
                for column_index in range(
                    cell.column,
                    cell.column + cell.colspan,
                ):
                    coordinate = (
                        row_index,
                        column_index,
                    )

                    if coordinate in occupied:
                        raise ValueError(
                            "Dos header cells se superponen"
                        )

                    occupied.add(coordinate)

        expected_coordinates = {
            (
                row_index,
                column_index,
            )
            for row_index in range(
                header_row_count
            )
            for column_index in range(
                column_count
            )
        }

        if occupied != expected_coordinates:
            missing = sorted(
                expected_coordinates
                - occupied
            )

            raise ValueError(
                "La matriz de headers no cubre "
                f"todas las posiciones: {missing}"
            )

        header_total_height = sum(
            header_row_heights
        )

        body_total_height = (
            body_row_height
            * len(rows)
        )

        table_height = (
            header_total_height
            + body_total_height
        )

        if table_height > box.height:
            raise ValueError(
                "La tabla no cabe dentro del VectorBox proporcionado"
            )

        table_top = (
            box.y
            + box.height
        )

        table_bottom = (
            table_top
            - table_height
        )

        x_positions = [box.x]

        cursor_x = box.x

        for fraction in normalized_widths:
            cursor_x += (
                box.width
                * fraction
            )

            x_positions.append(
                cursor_x
            )

        header_row_tops = [table_top]

        cursor_y = table_top

        for height in header_row_heights:
            cursor_y -= height

            header_row_tops.append(
                cursor_y
            )

        header_bottom = (
            table_top
            - header_total_height
        )

        if header_fill is not None:
            # Banda de fondo del header: rectángulo recto (radius=0), dibujado
            # antes que el marco exterior redondeado para que sus esquinas
            # superiores queden bajo el trazo del marco. Puramente cosmético
            # -- no ocupa geometría propia, no desplaza columnas ni filas.
            self.draw_rounded_box(
                VectorBox(
                    x=box.x,
                    y=header_bottom,
                    width=box.width,
                    height=header_total_height,
                ),
                radius=0,
                line_width=line_width,
                stroke=False,
                fill=True,
                fill_color=header_fill,
            )

        self.draw_rounded_box(
            VectorBox(
                x=box.x,
                y=table_bottom,
                width=box.width,
                height=table_height,
            ),
            radius=outer_radius,
            line_width=line_width,
            stroke_color=accent_color,
        )

        header_style = VectorTextStyle(
            font_size=6.8,
            bold=True,
            line_height=1.12,
            color=accent_color,
        )

        body_style = VectorTextStyle(
            font_size=7.2,
            line_height=1.15,
        )

        # Headers:
        # Cada celda dibuja únicamente sus fronteras internas
        # derecha/inferior.
        # El perímetro exterior pertenece al contenedor.
        for cell in header_cells:
            x1 = x_positions[
                cell.column
            ]

            x2 = x_positions[
                cell.column
                + cell.colspan
            ]

            y_top = header_row_tops[
                cell.row
            ]

            y_bottom = header_row_tops[
                cell.row
                + cell.rowspan
            ]

            cell_box = VectorBox(
                x=x1,
                y=y_bottom,
                width=x2 - x1,
                height=y_top - y_bottom,
            )

            self.draw_centered_text(
                cell.label,
                box=cell_box,
                style=header_style,
            )

            if (
                cell.column
                + cell.colspan
                < column_count
            ):
                self.draw_line(
                    x1=x2,
                    y1=y_bottom,
                    x2=x2,
                    y2=y_top,
                    line_width=line_width,
                    color=accent_color,
                )

            if (
                cell.row
                + cell.rowspan
                < header_row_count
            ):
                self.draw_line(
                    x1=x1,
                    y1=y_bottom,
                    x2=x2,
                    y2=y_bottom,
                    line_width=line_width,
                    color=accent_color,
                )

        # Frontera entre header y cuerpo.
        self.draw_line(
            x1=box.x,
            y1=header_bottom,
            x2=box.x + box.width,
            y2=header_bottom,
            line_width=line_width,
            color=accent_color,
        )

        # Verticales del cuerpo.
        for x in x_positions[1:-1]:
            self.draw_line(
                x1=x,
                y1=table_bottom,
                x2=x,
                y2=header_bottom,
                line_width=line_width,
            )

        # Horizontales del cuerpo.
        current_y = header_bottom

        for row_index in range(
            len(rows)
        ):
            current_y -= body_row_height

            if row_index < len(rows) - 1:
                self.draw_line(
                    x1=box.x,
                    y1=current_y,
                    x2=box.x + box.width,
                    y2=current_y,
                    line_width=line_width,
                )

        # Valores.
        for row_index, row in enumerate(
            rows
        ):
            row_top = (
                header_bottom
                - body_row_height
                * row_index
            )

            row_bottom = (
                row_top
                - body_row_height
            )

            for column_index in range(
                column_count
            ):
                value = (
                    str(
                        row[column_index]
                    )
                    if column_index
                    < len(row)
                    else ""
                )

                cell_box = VectorBox(
                    x=x_positions[
                        column_index
                    ],
                    y=row_bottom,
                    width=(
                        x_positions[
                            column_index + 1
                        ]
                        - x_positions[
                            column_index
                        ]
                    ),
                    height=body_row_height,
                )

                self.draw_centered_text(
                    value,
                    box=cell_box,
                    style=body_style,
                )


def wrap_text(
    text: str,
    *,
    usable_width: float,
    font_name: str,
    font_size: float,
) -> list[str]:
    """
    Wrapping determinista basado en métricas reales de ReportLab.
    """

    normalized = " ".join(
        str(
            text or ""
        ).split()
    )

    if not normalized:
        return [""]

    words = normalized.split(" ")

    lines: list[str] = []
    current = ""

    for word in words:
        candidate = (
            word
            if not current
            else f"{current} {word}"
        )

        candidate_width = stringWidth(
            candidate,
            font_name,
            font_size,
        )

        if (
            candidate_width
            <= usable_width
        ):
            current = candidate
            continue

        if current:
            lines.append(
                current
            )

        if (
            stringWidth(
                word,
                font_name,
                font_size,
            )
            <= usable_width
        ):
            current = word
            continue

        fragment = ""

        for character in word:
            next_fragment = (
                f"{fragment}{character}"
            )

            if (
                stringWidth(
                    next_fragment,
                    font_name,
                    font_size,
                )
                <= usable_width
            ):
                fragment = (
                    next_fragment
                )
            else:
                if fragment:
                    lines.append(
                        fragment
                    )

                fragment = character

        current = fragment

    if current:
        lines.append(
            current
        )

    return lines


def render_vector_smoke_test_pdf() -> bytes:
    """
    Smoke renderer sin semántica FieldSheet.

    Valida:
    - Letter;
    - mm -> pt;
    - roundRect;
    - grids;
    - structured table;
    - rowspan/colspan.
    """

    document = (
        FieldSheetVectorDocument()
    )

    page = document.page_spec

    top_y = (
        page.height
        - page.margin_top
    )

    document.draw_rounded_box(
        VectorBox(
            x=page.margin_left,
            y=top_y - mm(14),
            width=page.content_width,
            height=mm(14),
        ),
        radius=mm(2),
        line_width=0.8,
    )

    document.draw_centered_text(
        "MYC · FIELD SHEET VECTOR RENDERER V2",
        box=VectorBox(
            x=page.margin_left,
            y=top_y - mm(14),
            width=page.content_width,
            height=mm(14),
        ),
        style=VectorTextStyle(
            font_size=10,
            bold=True,
        ),
    )

    cursor_y = (
        top_y
        - mm(18)
    )

    cursor_y = document.draw_field_grid(
        origin_x=page.margin_left,
        origin_y=cursor_y,
        total_width=page.content_width,
        rows=[
            [
                (
                    "Orden de trabajo",
                    "OT-6401",
                    0.5,
                ),
                (
                    "Certificado",
                    "MYC-0001",
                    0.5,
                ),
            ],
            [
                (
                    "Empresa",
                    "Cliente de prueba para renderer vectorial",
                    0.67,
                ),
                (
                    "Atención",
                    "Paulina Cueto",
                    0.33,
                ),
            ],
            [
                (
                    "Dirección",
                    (
                        "Texto suficientemente largo "
                        "para validar wrapping sin "
                        "invadir líneas del documento."
                    ),
                    1.0,
                ),
            ],
        ],
    )

    table_top = (
        cursor_y
        - mm(4)
    )

    document.draw_structured_result_table(
        box=VectorBox(
            x=page.margin_left,
            y=table_top - mm(72),
            width=page.content_width,
            height=mm(72),
        ),
        column_widths=[
            0.10,
            0.225,
            0.225,
            0.225,
            0.225,
        ],
        header_row_heights=[
            mm(4.8),
            mm(5.4),
            mm(5.0),
        ],
        header_cells=[
            VectorHeaderCell(
                label="DATOS DE MEDICIÓN",
                row=0,
                column=0,
                colspan=5,
            ),
            VectorHeaderCell(
                label="No.",
                row=1,
                column=0,
                rowspan=2,
            ),
            VectorHeaderCell(
                label="Valores medidos (IBC)",
                row=1,
                column=1,
                rowspan=2,
            ),
            VectorHeaderCell(
                label="Patrón",
                row=1,
                column=2,
                colspan=3,
            ),
            VectorHeaderCell(
                label="1",
                row=2,
                column=2,
            ),
            VectorHeaderCell(
                label="2",
                row=2,
                column=3,
            ),
            VectorHeaderCell(
                label="3",
                row=2,
                column=4,
            ),
        ],
        rows=[
            [
                str(index),
                "",
                "",
                "",
                "",
            ]
            for index in range(
                1,
                11,
            )
        ],
    )

    return document.finish()
