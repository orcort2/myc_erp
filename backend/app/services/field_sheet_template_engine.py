"""Declarative foundation for the official MYC field-sheet document engine.

This module intentionally contains no persistence or metrological calculations.  It
defines reusable document blocks, the eight approved table families and the four
first official templates as plain data so the API, capture UI, PDF renderer and the
future visual designer can share the same contract.

Fase 3 (2026-09, unificacion del registro de familias de resultados): este
modulo es la UNICA autoridad canonica de table families. OFFICIAL_TABLE_FAMILIES
son las 8 familias aprobadas; resolve_table_family() es el unico punto donde
una clave de family (canonica, legacy segura o legacy ambigua) se interpreta.
field_sheet_templates.py consume esta autoridad -- ya no mantiene su propio
catalogo paralelo de familias.
"""

from copy import deepcopy

from fastapi import HTTPException, status

from app.schemas.field_sheet_template import SignatureLayoutRead


OFFICIAL_TABLE_FAMILIES = {
    "replicated_comparison": {
        "family_key": "replicated_comparison",
        "name": "Comparación replicada",
        "description": "Una referencia y varias lecturas del instrumento.",
        "capture_behavior": {"manual_only": True},
        "pdf_behavior": {"repeat_header": True},
    },
    "direction_cycle": {
        "family_key": "direction_cycle",
        "name": "Ciclo o dirección",
        "description": "Lecturas organizadas por sentido, ascenso, descenso o ciclo.",
        "capture_behavior": {"manual_only": True},
        "pdf_behavior": {"repeat_header": True},
    },
    "before_after": {
        "family_key": "before_after",
        "name": "Antes y después",
        "description": "Estados o mediciones antes y después de una intervención.",
        "capture_behavior": {"manual_only": True},
        "pdf_behavior": {"repeat_header": True},
    },
    "mass_balance_composite": {
        "family_key": "mass_balance_composite",
        "name": "Masa y balanza compuesta",
        "description": "Excentricidad, ciclos y repetibilidad en secciones coordinadas.",
        "capture_behavior": {"manual_only": True},
        "pdf_behavior": {"repeat_header": True, "keep_sections_together": True},
    },
    "paired_multichannel": {
        "family_key": "paired_multichannel",
        "name": "Multicanal pareada",
        "description": "Pares de referencia e indicación repetidos por canal.",
        "capture_behavior": {"manual_only": True},
        "pdf_behavior": {"repeat_header": True},
    },
    "threshold_event": {
        "family_key": "threshold_event",
        "name": "Evento o umbral",
        "description": "Filas fijas para apertura, cierre u otros eventos.",
        "capture_behavior": {"manual_only": True},
        "pdf_behavior": {"repeat_header": True},
    },
    "verification_compliance": {
        "family_key": "verification_compliance",
        "name": "Verificación y cumplimiento",
        "description": "Resultados manuales con una declaración configurable.",
        "capture_behavior": {"manual_only": True},
        "pdf_behavior": {"repeat_header": True},
    },
    "cup_specialized": {
        "family_key": "cup_specialized",
        "name": "Copa especializada",
        "description": "Composición manual de tiempos, temperatura y geometría de copa.",
        "capture_behavior": {"manual_only": True},
        "pdf_behavior": {"repeat_header": True},
    },
}


# Fase 3 (2026-09): mapeos legacy CONCEPTUALMENTE seguros -- equivalencia
# semantica verificada contra el uso real de estas familias, no inventada
# solo para eliminar nombres. Se resuelven SIEMPRE al interpretar (aqui, en
# resolve_table_family), nunca reescribiendo un snapshot persistido.
LEGACY_FAMILY_ALIASES = {
    "direct_comparison": "replicated_comparison",
    "pressure": "direction_cycle",
    "mass": "mass_balance_composite",
}

# Claves legacy cuyo significado NO puede mapearse de forma inequivoca a una
# de las 8 familias oficiales sin cambiar semantica (multipoint podria ser
# replicated_comparison o direction_cycle segun el caso real; dimensional/
# electrical/repeatability agrupan geometrias distintas entre si; custom es
# deliberadamente libre). Se conservan LEGIBLES para reproducibilidad
# historica -- nunca se ofrecen como opcion para definiciones nuevas, nunca
# se reinterpretan silenciosamente hacia una familia canonica.
AMBIGUOUS_LEGACY_FAMILIES = {
    "multipoint",
    "dimensional",
    "electrical",
    "repeatability",
    "custom",
}


def resolve_table_family(value: str | None, *, mode: str = "lenient") -> str:
    """Autoridad UNICA de resolucion de una clave de table family.

    - Familia canonica (OFFICIAL_TABLE_FAMILIES): se conserva tal cual, en
      cualquier modo.
    - Alias legacy seguro (LEGACY_FAMILY_ALIASES): se resuelve SIEMPRE a su
      equivalente canonico, en cualquier modo -- la resolucion ocurre al
      interpretar el valor devuelto, nunca reescribiendo lo persistido.
    - Familia legacy ambigua (AMBIGUOUS_LEGACY_FAMILIES) o clave
      desconocida, segun `mode`:
        * "lenient" (default; lectura de fallback/historico YA persistido
          en BD -- _serialize_row, build_fallback_template_definition,
          duplicate_field_sheet_template): se conserva tal cual si `value`
          no es None -- legado legible, nunca "custom" silencioso. Si
          `value` es None, cae a "custom" como plantilla-sin-tabla
          defensivo (comportamiento previo).
        * "strict" (AUTORIA NUEVA -- create_field_sheet_template, o
          update_field_sheet_template cuando la propia edicion toca
          table_family): se rechaza con 422 explicito -- una definicion
          nueva nunca puede apoyarse en una familia ambigua ni quedar sin
          family_key.
        * "import" (REIMPORTACION de un artefacto exportado --
          import_field_sheet_template): admite una legacy ambigua sólo si
          es una de las CONOCIDAS en AMBIGUOUS_LEGACY_FAMILIES,
          preservandola tal cual (nunca la convierte en canonica ni en
          otra legacy) -- pero, a diferencia de "lenient", rechaza con 422
          cualquier clave totalmente desconocida que no sea canonica, alias
          seguro ni legacy ambigua conocida: un import no debe poder colar
          una family arbitraria saltandose la politica canonica.
    """
    if value in OFFICIAL_TABLE_FAMILIES:
        return value
    if value in LEGACY_FAMILY_ALIASES:
        return LEGACY_FAMILY_ALIASES[value]
    if mode == "import":
        if value in AMBIGUOUS_LEGACY_FAMILIES:
            return value
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=(
                f"Familia de tabla no reconocida al reimportar: {value!r}. "
                f"Debe ser una familia canonica, un alias legacy seguro o una "
                f"legacy ambigua conocida: {sorted(AMBIGUOUS_LEGACY_FAMILIES)}"
            ),
        )
    if mode == "strict":
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=(
                f"Familia de tabla no soportada para una definicion nueva: {value!r}. "
                f"Usa una de las familias canonicas: {sorted(OFFICIAL_TABLE_FAMILIES)}"
            ),
        )
    return value if value else "custom"


DEFAULT_SIGNATURE_LAYOUT = SignatureLayoutRead().model_dump()


def _column(key: str, label: str, width: str | None = None, *, configurable: bool = False) -> dict:
    return {
        "key": key,
        "source": key,
        "label": label,
        "width": width,
        "editable": True,
        "required": False,
        "data_type": "text",
        "metadata": {"label_configurable": configurable},
    }


def _section(
    key: str,
    title: str,
    rows: int,
    columns: list[dict],
    *,
    ambiguous: bool = False,
    header_rows: list[dict] | None = None,
    layout: dict | None = None,
    row_labels: list[str] | None = None,
    metadata: dict | None = None,
) -> dict:
    section = {
        "key": key,
        "title": title,
        "rows": rows,
        "min_rows": rows,
        "max_rows": rows,
        "allow_add_rows": False,
        "allow_remove_rows": False,
        "columns": deepcopy(columns),
        "metadata": {
            "fixed_geometry": True,
            "functional_validation_pending": ambiguous,
            "labels_configurable": ambiguous,
        },
    }
    if header_rows is not None:
        section["header_rows"] = header_rows
    if layout is not None:
        section["layout"] = layout
    if row_labels is not None:
        section["row_labels"] = row_labels
    if metadata:
        section["metadata"].update(metadata)
    return section


def _block(block_type: str, key: str, title: str, order: int, **extra) -> dict:
    return {
        "key": key,
        "block_key": key,
        "block_type": block_type,
        "title": title,
        "order": order,
        "capture_order": order,
        "print_order": order,
        "visible": True,
        "capture_visible": True,
        "print_visible": True,
        "pdf_visible": True,
        "visible_fields": [],
        "fields": [],
        "columns": [],
        "sections": [],
        "table_config": {},
        "metadata": {},
        **extra,
    }


def _base_blocks(table_block: dict) -> list[dict]:
    return [
        _block(
            "HeaderBlock",
            "institutional_header",
            "Encabezado institucional",
            1,
            visible_fields=["work_order_number", "reserved_certificate_folio"],
            required=True,
            metadata={"identity_source": "institutional_configuration"},
        ),
        _block(
            "ClientBlock",
            "client_data",
            "Datos del usuario",
            2,
            visible_fields=["attention", "company", "address"],
            required=True,
        ),
        _block(
            "EquipmentBlock",
            "equipment_data",
            "Datos del instrumento",
            3,
            visible_fields=["instrument", "brand", "model", "serial_number", "internal_id", "location", "minimum_division"],
            required=True,
        ),
        _block(
            "CalibrationDataBlock",
            "calibration_data",
            "Datos de calibración",
            4,
            visible_fields=["calibration_place", "reception_date", "calibration_date", "next_calibration_date", "units"],
        ),
        _block(
            "EnvironmentalBlock",
            "environmental_conditions",
            "Condiciones ambientales",
            5,
            visible_fields=["environment_humidity_start", "environment_humidity_end", "environment_temperature_start", "environment_temperature_end"],
        ),
        _block(
            "ObservationsBlock",
            "condition_observations",
            "Condición y observaciones",
            6,
            visible_fields=["initial_condition", "final_condition", "observations"],
        ),
        {**table_block, "order": 7, "capture_order": 7, "print_order": 7},
        _block(
            "SignaturesBlock",
            "signatures",
            "Firmas",
            8,
            required=True,
            metadata={"model": "common_signature"},
        ),
        _block("FooterBlock", "document_footer", "Pie documental", 9),
    ]


def _table_block(block_type: str, key: str, title: str, sections: list[dict], family: str, *, ambiguous: bool = False) -> dict:
    return _block(
        block_type,
        key,
        title,
        7,
        required=True,
        rows=None,
        min_rows=None,
        max_rows=None,
        allow_add_rows=False,
        allow_remove_rows=False,
        sections=sections,
        table_config={
            "family": family,
            "manual_only": True,
            "dynamic_pagination": True,
            "repeat_header": True,
        },
        metadata={
            "fixed_geometry": True,
            "functional_validation_pending": ambiguous,
            "labels_configurable": ambiguous,
        },
    )


def _template(
    key: str,
    name: str,
    family: str,
    table: dict,
    *,
    ambiguous: bool = False,
    version: int = 1,
    # Fase 2 del catalogo LAB (2026-09): metadata de organizacion/magnitud
    # -- puramente de presentacion/busqueda (nombre visible, selector Mobile).
    # No es autoridad de layout/PDF/tabla ni participa del contrato canonico
    # de captura (ver field-sheet-canonical-contract.ts); organization_key
    # es la autoridad, nunca se debe derivar por parseo de `name`.
    organization_key: str = "myc",
    organization_label: str = "MYC",
    magnitude_key: str | None = None,
    magnitude_label: str | None = None,
    # Micro-cierre Fases 1/2 (hallazgo 2): una magnitud puede tener varias
    # hojas oficiales con geometria/resultados distintos -- document_variant_*
    # identifica esa variante documental REAL dentro de la magnitud, sin
    # convertir cada equipo en su propia magnitud. None cuando la magnitud
    # sólo tiene una variante oficial implementada hoy (no es obligatorio
    # inventar un nombre).
    document_variant_key: str | None = None,
    document_variant_label: str | None = None,
    supported_equipment: list[str] | None = None,
    search_aliases: list[str] | None = None,
    source_document: str = "FCA-30 R1",
    document_revision: str = "R1",
    blocks: list[dict] | None = None,
    print_layout: dict | None = None,
    signature_layout: dict | None = None,
) -> dict:
    return {
        "template_key": key,
        "key": key,
        "name": name,
        "description": f"Plantilla oficial MYC basada en FCA-30 {document_revision}.",
        "status": "active",
        "version": version,
        "is_active": True,
        "code": "FCA-30",
        "revision": document_revision,
        "document_code": "FCA-30",
        "document_revision": document_revision,
        "pages": 1,
        "pdf_template": "field_sheet_engine_pdf.html",
        "pdf_renderer_key": "field_sheet_vector",
        "pdf_renderer_version": 2,
        "table_family": family,
        "blocks": deepcopy(blocks) if blocks is not None else _base_blocks(table),
        "print_layout": deepcopy(print_layout or {}),
        "signature_layout": deepcopy(signature_layout or DEFAULT_SIGNATURE_LAYOUT),
        "pagination": {"mode": "dynamic", "label": "Página X de Y"},
        "automation": {"mode": "manual_only", "calculations": []},
        "metadata": {
            "official_reference": f"FCA-30 {document_revision}",
            "functional_validation_pending": ambiguous,
            "visual_designer_compatible": True,
            "organization_key": organization_key,
            "organization_label": organization_label,
            "magnitude_key": magnitude_key,
            "magnitude_label": magnitude_label,
            "document_variant_key": document_variant_key,
            "document_variant_label": document_variant_label,
            "supported_equipment": list(supported_equipment or []),
            "search_aliases": list(search_aliases or []),
            "source_document": source_document,
        },
    }


COMPARISON_COLUMNS = [
    _column("pattern_value", "Patrón", "25%"),
    _column("ibc_value_1", "IBC 1", "25%"),
    _column("ibc_value_2", "IBC 2", "25%"),
    _column("ibc_value_3", "IBC 3", "25%"),
]


OFFICIAL_PILOT_TEMPLATES = {
    "anemometro": _template(
        "anemometro",
        "Hoja de Campo Anemómetro",
        "replicated_comparison",
        _table_block(
            "SimpleComparisonTableBlock",
            "measurements",
            "Resultados de la calibración",
            [_section("measurements", "Resultados de la calibración", 10, COMPARISON_COLUMNS)],
            "replicated_comparison",
        ),
        magnitude_key="air_velocity",
        magnitude_label="Velocidad de aire",
        supported_equipment=["anemómetro"],
        search_aliases=["anemometro", "velocidad de aire", "viento"],
    ),
    "calibradores": _template(
        "calibradores",
        "Hoja de Campo Calibradores",
        "replicated_comparison",
        _table_block(
            "SectionedTableBlock",
            "caliper_measurements",
            "Resultados de la calibración",
            [
                _section("exterior", "Medición de exteriores", 7, COMPARISON_COLUMNS),
                _section("interior", "Medición de interiores", 5, COMPARISON_COLUMNS),
                _section("depth", "Medición de profundidades", 3, COMPARISON_COLUMNS),
            ],
            "replicated_comparison",
        ),
        magnitude_key="dimensional",
        magnitude_label="Dimensional",
        document_variant_key="calibradores",
        document_variant_label="Calibradores",
        supported_equipment=["calibrador vernier", "calibrador de altura", "calibrador de profundidad"],
        search_aliases=["vernier", "calibrador", "dimensional"],
    ),
    "bascula": _template(
        "bascula",
        "Hoja de Campo Báscula y Balanza",
        "mass_balance_composite",
        _table_block(
            "MassBalanceTableBlock",
            "mass_balance_tests",
            "Resultados de la calibración",
            [
                _section(
                    "eccentricity_cycle",
                    "Excentricidad y ciclo",
                    6,
                    [
                        _column("pattern_value", "Patrón", configurable=True),
                        _column("ibc_value_1", "IBC 1", configurable=True),
                        _column("ibc_value_2", "IBC 2", configurable=True),
                        _column("ibc_value_3", "IBC 3", configurable=True),
                    ],
                    ambiguous=True,
                ),
                _section(
                    "repeatability_50",
                    "Repetibilidad al 50 %",
                    5,
                    [_column("pattern_value", "Patrón", configurable=True), _column("ibc_value_1", "Indicación", configurable=True)],
                    ambiguous=True,
                ),
                _section(
                    "repeatability_100",
                    "Repetibilidad al 100 %",
                    5,
                    [_column("pattern_value", "Patrón", configurable=True), _column("ibc_value_1", "Indicación", configurable=True)],
                    ambiguous=True,
                ),
            ],
            "mass_balance_composite",
            ambiguous=True,
        ),
        ambiguous=True,
        version=3,
        magnitude_key="mass",
        magnitude_label="Masa",
        supported_equipment=["báscula", "balanza"],
        search_aliases=["bascula", "balanza", "masa", "peso"],
    ),
}


OFFICIAL_FCA30_PRINT_LAYOUT = {
    "page": {
        "size": "letter",
        "orientation": "portrait",
        "margins": {"top": 12, "right": 10, "bottom": 14, "left": 10},
    },
    "document": {
        "title_visible": True,
        "header_visible": True,
        "footer_visible": True,
        "grid_columns": 3,
    },
}


OFFICIAL_FCA30_SIGNATURE_LAYOUT = {
    "layout": "three_columns",
    "slots": [
        {"role": "calibrated_by", "display_label": "CALIBRÓ"},
        {"role": "reviewed_by", "display_label": "REVISÓ"},
        {"role": "report_made_by", "display_label": "REALIZÓ INFORME (SMM)"},
    ],
    "columns": 1,
    "direction": "vertical",
    "trailing_fields": ["purchase_order_or_quotation"],
}


def _official_fca30_blocks(table_block: dict) -> list[dict]:
    """Composición declarativa común de los formatos FCA-30 inspeccionados."""
    full_width = {"column_span": 3}
    return [
        _block(
            "HeaderBlock",
            "institutional_header",
            "Encabezado institucional",
            1,
            visible_fields=["work_order_number", "reserved_certificate_folio"],
            required=True,
            print_layout={
                **full_width,
                "grid_columns": 2,
                "title_visible": False,
                "border": False,
                "compact": True,
                "label_position": "inline",
            },
            metadata={"identity_source": "institutional_configuration"},
        ),
        _block(
            "ClientBlock",
            "client_data",
            "Datos del Usuario",
            2,
            visible_fields=["attention", "company", "address"],
            required=True,
            print_layout={**full_width, "grid_columns": 1, "compact": True},
        ),
        _block(
            "EquipmentBlock",
            "equipment_data",
            "Datos del Instrumento a Calibrar",
            3,
            visible_fields=[
                "instrument",
                "scope",
                "minimum_division",
                "brand",
                "serial_number",
                "model",
                "internal_id",
                "location",
            ],
            required=True,
            print_layout={**full_width, "grid_columns": 2, "compact": True},
        ),
        _block(
            "CalibrationDataBlock",
            "calibration_data",
            "Datos de calibración",
            4,
            visible_fields=[
                "calibration_place",
                "reception_date",
                "calibration_date",
                "next_calibration_date",
            ],
            fields=[
                {
                    "key": "calibration_place",
                    "label": "Lugar de calibración",
                    "column_span": 3,
                }
            ],
            print_layout={
                **full_width,
                "grid_columns": 3,
                "title_visible": False,
                "compact": True,
            },
        ),
        _block(
            "EnvironmentalBlock",
            "environmental_conditions",
            "Condiciones ambientales",
            5,
            visible_fields=[
                "environment_humidity_start",
                "environment_temperature_start",
                "environment_humidity_end",
                "environment_temperature_end",
            ],
            print_layout={
                **full_width,
                "grid_columns": 2,
                "title_visible": False,
                "compact": True,
            },
        ),
        _block(
            "ObservationsBlock",
            "condition_observations",
            "OBSERVACIONES",
            6,
            visible_fields=[
                "equipment_general_condition",
                "observations",
                "consider_equipment_deviations",
                "units",
            ],
            print_layout={**full_width, "grid_columns": 2, "compact": True},
        ),
        {
            **deepcopy(table_block),
            "order": 7,
            "capture_order": 7,
            "print_order": 7,
            "print_layout": {
                "column_span": 2,
                "grid_columns": 2,
                "compact": True,
                "break_inside": "avoid",
            },
        },
        _block(
            "SignaturesBlock",
            "signatures",
            "Firmas",
            8,
            required=True,
            print_layout={
                "column_span": 1,
                "grid_columns": 1,
                "title_visible": False,
                "border": False,
                "break_inside": "avoid",
            },
            metadata={"model": "common_signature"},
        ),
        _block(
            "FooterBlock",
            "document_footer",
            "Pie documental",
            9,
            print_layout={**full_width, "title_visible": False, "border": False},
        ),
    ]


def _official_fca30_template(
    key: str,
    name: str,
    family: str,
    table: dict,
    *,
    version: int,
    magnitude_key: str,
    magnitude_label: str,
    supported_equipment: list[str],
    search_aliases: list[str],
    source_document: str,
    document_revision: str,
) -> dict:
    return _template(
        key,
        name,
        family,
        table,
        version=version,
        magnitude_key=magnitude_key,
        magnitude_label=magnitude_label,
        supported_equipment=supported_equipment,
        search_aliases=search_aliases,
        source_document=source_document,
        document_revision=document_revision,
        blocks=_official_fca30_blocks(table),
        print_layout=OFFICIAL_FCA30_PRINT_LAYOUT,
        signature_layout=OFFICIAL_FCA30_SIGNATURE_LAYOUT,
    )


OFFICIAL_PILOT_TEMPLATES.update(
    {
        "temperatura": _official_fca30_template(
            "temperatura",
            "Hoja de Campo Temperatura",
            "replicated_comparison",
            _table_block(
                "SimpleComparisonTableBlock",
                "temperature_measurements",
                "Resultados de la Calibración",
                [
                    _section(
                        "temperature_measurements",
                        "Resultados de la Calibración",
                        10,
                        [
                            _column("ibc", "Valores medidos (IBC)", "23%"),
                            _column("pattern_1", "1", "23%"),
                            _column("pattern_2", "2", "23%"),
                            _column("pattern_3", "3", "24%"),
                        ],
                        header_rows=[
                            {"cells": [{"label": "DATOS DE MEDICION", "colspan": 5}]},
                            {
                                "cells": [
                                    {
                                        "label": "No.",
                                        "column_key": "__row_number__",
                                        "rowspan": 2,
                                    },
                                    {
                                        "label": "Valores medidos (IBC)",
                                        "column_key": "ibc",
                                        "rowspan": 2,
                                    },
                                    {"label": "Patrón", "colspan": 3},
                                ]
                            },
                            {
                                "cells": [
                                    {"label": "1", "column_key": "pattern_1"},
                                    {"label": "2", "column_key": "pattern_2"},
                                    {"label": "3", "column_key": "pattern_3"},
                                ]
                            },
                        ],
                        layout={"row_number_width": "7%"},
                    )
                ],
                "replicated_comparison",
            ),
            version=2,
            magnitude_key="temperature",
            magnitude_label="Temperatura",
            supported_equipment=[],
            search_aliases=["temperatura"],
            source_document="FCA-30 R1 HOJA DE CAMPO TEMPERATURA.pdf",
            document_revision="R-1",
        ),
        "presion": _official_fca30_template(
            "presion",
            "Hoja de Campo Presión",
            "direction_cycle",
            _table_block(
                "PressureTableBlock",
                "pressure_cycle",
                "Resultados de la Calibración",
                [
                    _section(
                        "pressure_cycle",
                        "Resultados de la Calibración",
                        11,
                        [
                            _column("ibc_value_1", "Valores Medidos IBC", "22%"),
                            _column("pattern_value", "Acendente", "24%"),
                            _column("ibc_value_2", "Descendente", "24%"),
                            _column("ibc_value_3", "Ascendente", "24%"),
                        ],
                        header_rows=[
                            {"cells": [{"label": "DATOS DE MEDICION", "colspan": 5}]},
                            {
                                "cells": [
                                    {
                                        "label": "No.",
                                        "column_key": "__row_number__",
                                        "rowspan": 2,
                                    },
                                    {
                                        "label": "Valores Medidos IBC",
                                        "column_key": "ibc_value_1",
                                        "rowspan": 2,
                                    },
                                    {"label": "Valores Medidos Patrón", "colspan": 3},
                                ]
                            },
                            {
                                "cells": [
                                    {"label": "Acendente", "column_key": "pattern_value"},
                                    {"label": "Descendente", "column_key": "ibc_value_2"},
                                    {"label": "Ascendente", "column_key": "ibc_value_3"},
                                ]
                            },
                        ],
                        layout={"row_number_width": "6%"},
                    )
                ],
                "direction_cycle",
            ),
            version=3,
            magnitude_key="pressure",
            magnitude_label="Presión",
            supported_equipment=["manómetro", "vacuómetro", "diferencial de presión"],
            search_aliases=[
                "manometro",
                "vacuometro",
                "diferencial de presion",
                "presion",
            ],
            source_document="FCA-30_R1_PRESION.pdf",
            document_revision="R1",
        ),
    }
)


# Catálogo documental MYC 2026-09. Las diferencias entre formatos viven
# exclusivamente en estas definiciones; Mobile y el renderer consumen el
# mismo snapshot y no contienen ramas por template_key.
OFFICIAL_MYC_TEMPLATE_KEYS = (
    "calibradores", "electrica", "detector_gases", "tld", "general",
    "angulimetro", "sonido", "pesas", "tacometro", "maestro_altura",
    "valvula", "flujo", "dimensional", "regla", "anemometro",
    "cronometro", "copa", "tld_6_canales", "temperatura",
    "par_torsional", "presion", "verificacion_equipos", "bascula",
)


def _header_rows(title: str, groups: list[tuple[str, list[tuple[str, str]]]]) -> list[dict]:
    """Build a fully-covered multi-row header for No. plus declared columns."""
    has_grouped_children = any(len(columns) > 1 for _, columns in groups)
    second = [{"label": "No.", "column_key": "__row_number__", "rowspan": 2 if has_grouped_children else 1}]
    third: list[dict] = []
    for label, columns in groups:
        if len(columns) == 1:
            second.append({"label": label, "column_key": columns[0][0], "rowspan": 2 if has_grouped_children else 1})
        else:
            second.append({"label": label, "colspan": len(columns)})
            third.extend({"label": child_label, "column_key": key} for key, child_label in columns)
    rows = [
        {"cells": [{"label": title, "colspan": 1 + sum(len(cols) for _, cols in groups)}]},
        {"cells": second},
    ]
    if has_grouped_children:
        rows.append({"cells": third})
    return rows


def _result_section(
    key: str,
    title: str,
    rows: int,
    groups: list[tuple[str, list[tuple[str, str]]]],
    *,
    row_labels: list[str] | None = None,
    layout: dict | None = None,
    metadata: dict | None = None,
    data_types: dict[str, str] | None = None,
) -> dict:
    flattened = [item for _, children in groups for item in children]
    columns = []
    for key_name, label in flattened:
        column = _column(key_name, label)
        if data_types and key_name in data_types:
            column["data_type"] = data_types[key_name]
        columns.append(column)
    return _section(
        key, title, rows, columns,
        header_rows=_header_rows(title, groups),
        row_labels=row_labels,
        layout={"row_number_width": "7%", **(layout or {})},
        metadata=metadata,
    )


def _signature_layout(labels: list[str], *, columns: int, direction: str = "horizontal", groups: list[dict] | None = None) -> dict:
    roles = ["calibrated_by", "reviewed_by", "report_made_by", "purchase_order_or_quotation"]
    return {
        "layout": "declarative_grid",
        "slots": [{"role": roles[index] if index < len(roles) else f"signature_{index + 1}", "display_label": label} for index, label in enumerate(labels)],
        "columns": columns,
        "direction": direction,
        "trailing_fields": [],
        "groups": groups or [],
    }


COMMON_VISIBLE_FIELDS = {
    "header": ["work_order_number", "reserved_certificate_folio"],
    "client": ["attention", "company", "address"],
    "equipment": ["instrument", "scope", "minimum_division", "brand", "model", "serial_number", "internal_id", "location"],
    "calibration": ["reception_date", "calibration_date", "next_calibration_date", "calibration_place"],
    "environment": ["environment_humidity_start", "environment_humidity_end", "environment_temperature_start", "environment_temperature_end"],
    "condition": ["equipment_general_condition", "consider_equipment_deviations", "observations", "units"],
}


def _document_blocks(
    table: dict,
    *,
    common_overrides: dict[str, list[str]] | None = None,
    field_specs: dict[str, list[dict]] | None = None,
    table_span: int = 4,
    signature_span: int = 4,
    extra_blocks: list[dict] | None = None,
) -> list[dict]:
    visible = {key: list(value) for key, value in COMMON_VISIBLE_FIELDS.items()}
    visible.update(common_overrides or {})
    specs = field_specs or {}
    for group_key, group_specs in specs.items():
        visible.setdefault(group_key, [])
        for spec in group_specs:
            if spec["key"] not in visible[group_key]:
                visible[group_key].append(spec["key"])
    block_definitions = [
        ("HeaderBlock", "header", "Encabezado", "header"),
        ("ClientBlock", "client", "Datos del Usuario", "client"),
        ("EquipmentBlock", "equipment", "Datos del Instrumento", "equipment"),
        ("CalibrationDataBlock", "calibration", "Datos de calibración", "calibration"),
        ("EnvironmentalBlock", "environment", "Condiciones ambientales", "environment"),
        ("ObservationsBlock", "condition", "Observaciones", "condition"),
    ]
    blocks: list[dict] = []
    for order, (block_type, key, title, visible_key) in enumerate(block_definitions, start=1):
        blocks.append(_block(
            block_type, key, title, order,
            visible_fields=visible[visible_key],
            fields=specs.get(visible_key, []),
            print_layout={"column_span": 4, "grid_columns": 4, "compact": True, "title_visible": order != 1, "border": order != 1},
        ))
    blocks.extend(extra_blocks or [])
    table = deepcopy(table)
    table["order"] = table["capture_order"] = table["print_order"] = 20
    table["print_layout"] = {"column_span": table_span, "grid_columns": 4, "compact": True, "break_inside": "avoid", "title_visible": False}
    blocks.append(table)
    blocks.append(_block(
        "SignaturesBlock", "signatures", "Firmas", 30,
        print_layout={"column_span": signature_span, "grid_columns": 4, "title_visible": False, "border": False, "break_inside": "avoid"},
    ))
    blocks.append(_block("FooterBlock", "footer", "Pie documental", 40, capture_visible=False, print_layout={"column_span": 4, "title_visible": False, "border": False}))
    return blocks


def _official_template(
    key: str,
    name: str,
    family: str,
    sections: list[dict],
    *,
    magnitude: str,
    source: str,
    variant: str | None = None,
    supported: list[str] | None = None,
    pages: int = 1,
    signature: dict | None = None,
    common_overrides: dict[str, list[str]] | None = None,
    field_specs: dict[str, list[dict]] | None = None,
    table_span: int = 4,
    signature_span: int = 4,
    extra_blocks: list[dict] | None = None,
) -> dict:
    table = _table_block("SectionedTableBlock", "results", "Resultados", sections, family)
    definition = _template(
        key, name, family, table,
        magnitude_key=key, magnitude_label=magnitude,
        document_variant_key=key if variant else None,
        document_variant_label=variant,
        supported_equipment=supported or [], search_aliases=[key.replace("_", " "), magnitude, *(supported or [])],
        source_document=source, document_revision="R1",
        blocks=_document_blocks(table, common_overrides=common_overrides, field_specs=field_specs, table_span=table_span, signature_span=signature_span, extra_blocks=extra_blocks),
        print_layout={"page": {"size": "letter", "orientation": "portrait", "margins": {"top": 9, "right": 8, "bottom": 10, "left": 8}}, "document": {"title_visible": True, "header_visible": True, "footer_visible": True, "grid_columns": 4}},
        signature_layout=signature or _signature_layout(["CALIBRÓ", "REVISÓ", "REALIZÓ INFORME", "OC/COTIZACIÓN"], columns=4),
    )
    definition["pages"] = pages
    return definition


P_I3 = [("Patrón", [("pattern_value", "Patrón")]), ("Valores medidos (IBC)", [("ibc_value_1", "1"), ("ibc_value_2", "2"), ("ibc_value_3", "3")])]
P_I5 = [("Patrón", [("pattern_value", "Patrón")]), ("Valores medidos IBC", [(f"ibc_{i}", str(i)) for i in range(1, 6)])]
PAIR3 = [
    ("Valores medidos", [("measured", "Valor")]),
    ("Patrón / IBC", [item for i in range(1, 4) for item in ((f"pattern_{i}", "Patrón"), (f"ibc_{i}", "IBC"))]),
]


def _materialize_official_templates() -> dict[str, dict]:
    vertical = _signature_layout(["CALIBRÓ", "REVISÓ", "REALIZÓ INFORME (SMM)"], columns=1, direction="vertical")
    vertical["trailing_fields"] = ["purchase_order_or_quotation"]
    two_by_two = _signature_layout(["CALIBRÓ", "REVISÓ", "REALIZÓ INFORME", "OC/COTIZACIÓN"], columns=2)
    four = _signature_layout(["CALIBRÓ", "REVISÓ", "REALIZÓ INFORME", "OC/COTIZACIÓN"], columns=4)
    docs: dict[str, dict] = {}

    docs["calibradores"] = _official_template(
        "calibradores", "Hoja de Campo Calibradores", "replicated_comparison",
        [_result_section("exterior", "DATOS DE MEDICION DE EXTERIORES", 7, [("Patrón", [("pattern_value", "Patrón")]), ("IBC", [("ibc_value_1", "IBC 1"), ("ibc_value_2", "IBC 2"), ("ibc_value_3", "IBC 3")])]),
         _result_section("interior", "DATOS DE MEDICION DE INTERIORES", 5, [("Patrón", [("pattern_value", "Patrón")]), ("IBC", [("ibc_value_1", "IBC 1"), ("ibc_value_2", "IBC 2"), ("ibc_value_3", "IBC 3")])]),
         _result_section("depth", "DATOS DE MEDICION DE PROFUNDIDADES", 3, [("Patrón", [("pattern_value", "Patrón")]), ("IBC", [("ibc_value_1", "IBC 1"), ("ibc_value_2", "IBC 2"), ("ibc_value_3", "IBC 3")])])],
        magnitude="Dimensional", variant="Calibradores", source="FCA-30 R1 HOJA DE CAMPO CALIBRADORES.pdf", supported=["calibrador vernier", "calibrador de altura", "calibrador de profundidad"], signature=vertical, table_span=3, signature_span=1,
    )

    electrical_sections = []
    for index in range(1, 7):
        electrical_section = _result_section(
            f"block_{index}", f"Bloque {index}", 5,
            [("Patrón", [("pattern_value", "Patrón")]), ("IBC", [("ibc_value_1", "IBC 1"), ("ibc_value_2", "IBC 2"), ("ibc_value_3", "IBC 3")])],
            layout={"capture_title": f"Bloque {index}", "print_title_visible": False},
            metadata={"unit_field": f"electrical_unit_{index}"},
        )
        electrical_section["header_rows"] = electrical_section["header_rows"][1:]
        electrical_sections.append(electrical_section)
    docs["electrica"] = _official_template(
        "electrica", "Hoja de Campo Eléctrica", "replicated_comparison", electrical_sections,
        magnitude="Eléctrica", source="FCA-30 R1 HOJA DE CAMPO ELECTRICA (amperimetro, multimetro, megaohmetro).pdf",
        supported=["amperímetro", "multímetro", "megaóhmetro"], pages=2, signature=four,
        field_specs={"condition": [{"key": f"electrical_unit_{i}", "label": f"Unidades tabla {i}", "order": i, "field_type": "text"} for i in range(1, 7)]},
    )

    gas_groups = [("Patrón", [("pattern_value", "Patrón")]), ("Valores Medidos", [(f"reading_{i}", label) for i, label in enumerate(["Primera", "Segunda", "Tercera", "Cuarta", "Quinta"], 1)])]
    gas_labels = ["H₂S", "CO", "O₂", "% LEL"]
    docs["detector_gases"] = _official_template(
        "detector_gases", "Hoja de Campo Detector de Gases", "before_after",
        [_result_section("before", "Antes del ajuste", 4, gas_groups, row_labels=gas_labels, layout={"row_label_header": "GAS"}), _result_section("after", "Despues del ajuste", 4, gas_groups, row_labels=gas_labels, layout={"row_label_header": "GAS"})],
        magnitude="Concentración de gases", source="FCA-30 R1 HOJA DE CAMPO DETECTOR DE GASES.pdf", signature=four,
    )

    tld_fields = {"equipment": [{"key": "type", "label": "Tipo", "field_type": "text", "order": 99}]}
    docs["tld"] = _official_template(
        "tld", "Hoja de Campo TLD", "paired_multichannel", [_result_section("channel_1", "DATOS DE MEDICIÓN", 5, PAIR3)],
        magnitude="Temperatura", variant="TLD", source="FCA-30 R1 HOJA DE CAMPO TLD (temperatura de lectura directa).pdf", signature=two_by_two, field_specs=tld_fields,
    )

    general_groups = [("Serie simple", [("simple_value", "Patrón / IBC")]), ("Serie triple", [(f"triple_{i}", str(i)) for i in range(1, 4)])]
    docs["general"] = _official_template(
        "general", "Hoja de Campo General", "replicated_comparison", [_result_section("measurements", "DATOS DE MEDICIÓN", 10, general_groups, metadata={"header_choices": {"simple_role": {"label": "Serie simple", "options": ["Patrón", "IBC"]}, "triple_role": {"label": "Serie triple", "options": ["Patrón", "IBC"]}}})],
        magnitude="General", source="FCA-30 R1 HOJA DE CAMPO GENERAL.pdf", signature=vertical, table_span=3, signature_span=1,
        field_specs={"condition": [{"key": "simple_role", "label": "Rol de serie simple", "field_type": "enum", "options": ["Patrón", "IBC"]}, {"key": "triple_role", "label": "Rol de serie triple", "field_type": "enum", "options": ["Patrón", "IBC"]}]},
    )

    docs["angulimetro"] = _official_template("angulimetro", "Hoja de Campo Angulímetro", "replicated_comparison", [_result_section("measurements", "DATOS DE MEDICION", 5, P_I3)], magnitude="Ángulo", source="FCA-30 R1 HOJA DE CAMPO ANGULIMETRO.pdf", signature=two_by_two)
    docs["sonido"] = _official_template("sonido", "Hoja de Campo Sonido", "replicated_comparison", [_result_section("measurements", "DATOS DE MEDICIÓN", 10, P_I3)], magnitude="Sonido / Acústica", source="FCA-30 R1 HOJA DE CAMPO SONIDO.pdf", signature=vertical, table_span=3, signature_span=1)

    pesas_groups = [("Patrón", [("pattern_value", "Patrón")]), ("Valores Medidos IBC", [(f"ibc_{i}", str(i)) for i in range(1, 5)]), ("ID", [("weight_id", "ID")])]
    docs["pesas"] = _official_template("pesas", "Hoja de Campo Pesas", "replicated_comparison", [_result_section("measurements", "DATOS DE MEDICIÓN", 10, pesas_groups)], magnitude="Masa", variant="Pesas", source="FCA-30 R1 HOJA DE CAMPO PESAS.pdf", signature=vertical, table_span=3, signature_span=1, field_specs={"equipment": [{"key": "class", "label": "Clase", "field_type": "text"}]})
    docs["tacometro"] = _official_template("tacometro", "Hoja de Campo Tacómetro", "replicated_comparison", [_result_section("measurements", "DATOS DE MEDICIÓN", 5, P_I3)], magnitude="Velocidad de rotación", source="FCA-30 R1 HOJA DE CAMPO TACOMETRO.pdf", signature=two_by_two)

    directional = [("Equipo Patrón", [("pattern_value", "Equipo Patrón")]), ("Valores medidos", [(f"ibc_{i}", str(i)) for i in range(1, 4)])]
    docs["maestro_altura"] = _official_template("maestro_altura", "Hoja de Campo Maestro de Altura", "direction_cycle", [_result_section("ascending", "DATOS DE MEDICION ASCENDENTE", 10, directional), _result_section("descending", "DATOS DE MEDICION DESCENDENTE", 10, directional)], magnitude="Dimensional", variant="Maestro de altura", source="FCA-30 R1 HOJA DE CAMPO MAESTRO DE ALTURA.pdf", signature=vertical, table_span=3, signature_span=1)

    valve_groups = [("Referencia", [("reference", "Referencia")]), ("Valores Medidos Patrón", [(f"measured_{i}", label) for i, label in enumerate(["Primera", "Segunda", "Tercera"], 1)])]
    docs["valvula"] = _official_template("valvula", "Hoja de Campo Válvula de Seguridad", "threshold_event", [_result_section("events", "DATOS DE MEDICIÓN", 2, valve_groups, row_labels=["Disparo", "Cierre"], layout={"row_label_header": "Presión"})], magnitude="Presión", variant="Válvula de seguridad", source="FCA-30 R1 HOJA DE CAMPO VALVULA DE SEGURIDAD.pdf", signature=two_by_two, field_specs={"equipment": [{"key": "measure", "label": "Medida", "field_type": "text"}]})

    flow_groups = [("Valores Medidos IBC", [("ibc_value", "Valores Medidos IBC")]), ("Valores Medidos Patrón", [(f"pattern_{i}", str(i)) for i in range(1, 4)])]
    docs["flujo"] = _official_template("flujo", "Hoja de Campo Flujo", "replicated_comparison", [_result_section("measurements", "DATOS DE MEDICIÓN", 10, flow_groups)], magnitude="Flujo", source="FCA-30 R1 HOJA DE CAMPO FLUJO.pdf", signature=vertical, table_span=3, signature_span=1)
    docs["dimensional"] = _official_template("dimensional", "Hoja de Campo Dimensional", "replicated_comparison", [_result_section("measurements", "DATOS DE MEDICIÓN", 10, P_I3)], magnitude="Dimensional", variant="Indicador / micrómetro / medidor de espesores", source="FCA-30 R1 HOJA DE CAMPO DIMENSIONAL (indicador de caratula, micrometro, medidor de espesores).pdf", signature=vertical, table_span=3, signature_span=1)

    rule_groups = [("Equipo", [("equipment_value", "Equipo")]), ("Valores Medidos Patrón", [(f"pattern_{i}", str(i)) for i in range(1, 6)])]
    docs["regla"] = _official_template("regla", "Hoja de Campo Reglas", "replicated_comparison", [_result_section("measurements", "REGLA", 15, rule_groups)], magnitude="Dimensional", variant="Regla", source="FCA-30 R1 HOJA DE CAMPO REGLAS.pdf", signature=vertical, table_span=3, signature_span=1, field_specs={"header": [{"key": "purchase_order_or_quotation", "label": "ORDEN DE TRABAJO/COTIZACIÓN", "field_type": "text"}]})
    docs["anemometro"] = _official_template("anemometro", "Hoja de Campo Anemómetro", "replicated_comparison", [_result_section("measurements", "DATOS DE MEDICIÓN", 10, P_I3)], magnitude="Velocidad de aire", source="FCA-30 R1 HOJA DE CAMPO ANEMOMETRO.pdf", supported=["anemómetro"], signature=vertical, table_span=3, signature_span=1)

    static_note = _block("StaticTextBlock", "formula_note", "Nota técnica", 19, capture_visible=False, visible_fields=[], print_layout={"column_span": 3, "grid_columns": 1, "compact": True}, metadata={"text": "= 2.16 s\nDRAFT SOP 24-NIST"})
    docs["cronometro"] = _official_template("cronometro", "Hoja de Campo Cronómetro", "replicated_comparison", [_result_section("measurements", "DATOS DE MEDICIÓN", 5, P_I5)], magnitude="Tiempo", source="FCA-30 R1 HOJA DE CAMPO CRONOMETRO.pdf", signature=vertical, table_span=3, signature_span=1, extra_blocks=[static_note])

    graphic = _block("ReferenceGraphicBlock", "cup_figure", "FORD VISCOSITY CUP", 18, capture_visible=False, visible_fields=[], print_layout={"column_span": 2, "grid_columns": 1, "compact": True}, metadata={"caption": "FIG. 1 Ford Viscosity Cup and Orifices", "asset_key": "ford_viscosity_cup", "asset_path": "backend/app/assets/field-sheets/ford_viscosity_cup.png"})
    cup_sections = [
        _result_section("diameter", "Unidades milímetros", 1, [("Característica", [("feature", "Diámetro de salida (mm) No.4")]), ("Mediciones", [(f"measurement_{i}", f"Medición {i}") for i in range(1, 4)])]),
        _result_section("flow_time", "Unidades segundos", 5, [("Tiempo en derramarse el líquido", [("seconds", "Tiempo")])]),
        _result_section("standard", "Datos tecnicos del standard de referencia", 1, [("Patron", [("standard", "Patron")]), ("Referencia", [("kinematic_viscosity", "Kinematic Viscosity @ 25 °C"), ("flow_cup_designation", "Flow Cup Designation"), ("flow_cup_size", "Flow Cup Size"), ("time_seconds", "Time (s)")])]),
        _result_section("temperature", "Temperatura", 1, [("Temperatura de calibracion promedio", [("average_temperature", "Valor")])]),
    ]
    cup_common = {"equipment": ["instrument", "brand", "model", "internal_id", "serial_number", "location", "scope", "minimum_division"], "condition": ["observations"], "calibration": ["calibration_date", "calibration_place"], "environment": ["environment_humidity_start", "environment_humidity_end", "environment_temperature_start", "environment_temperature_end"]}
    cup_signature = {
        "layout": "grouped",
        "slots": [
            {"role": "client", "display_label": "CLIENTE"},
            {"role": "calibrated_by", "display_label": "CALIBRÓ TÉCNICO"},
            {"role": "authorized_by", "display_label": "AUTORIZÓ"},
            {"role": "report_made_by", "display_label": "REALIZÓ INFORME"},
        ],
        "columns": 3,
        "direction": "horizontal",
        "trailing_fields": [],
        "groups": [{"slots": ["client"], "columns": 1}, {"slots": ["calibrated_by", "authorized_by", "report_made_by"], "columns": 3}],
    }
    docs["copa"] = _official_template("copa", "Hoja de Campo Copa", "cup_specialized", cup_sections, magnitude="Viscosidad", source="HOJA DE CAMPO COPA.pdf", signature=cup_signature, common_overrides=cup_common, extra_blocks=[graphic])

    tld_sections = [_result_section(f"channel_{i}", f"Canal {i}", 5, PAIR3, layout={"row_group": "channels", "group_order": i, "width_fraction": 1.0}) for i in range(1, 7)]
    docs["tld_6_canales"] = _official_template("tld_6_canales", "Hoja de Campo TLD 6 Canales", "paired_multichannel", tld_sections, magnitude="Temperatura", variant="TLD 6 canales", source="FCA-30 R1 HOJA DE CAMPO TLD (temperatura de lectura directa) 6 CANALES.pdf", pages=2, signature=two_by_two, field_specs=tld_fields)

    docs["temperatura"] = _official_template("temperatura", "Hoja de Campo Temperatura", "replicated_comparison", [_result_section("temperature_measurements", "DATOS DE MEDICION", 10, flow_groups)], magnitude="Temperatura", source="FCA-30 R1 HOJA DE CAMPO TEMPERATURA.pdf", signature=vertical, table_span=3, signature_span=1)
    docs["temperatura"]["version"] = 2
    docs["temperatura"]["revision"] = docs["temperatura"]["document_revision"] = "R-1"

    torque_groups = [("Equipo", [("equipment_value", "Equipo")]), ("Valores Medidos Patrón", [(f"pattern_{i}", str(i)) for i in range(1, 6)])]
    docs["par_torsional"] = _official_template("par_torsional", "Hoja de Campo Par Torsional", "direction_cycle", [_result_section("cw", "Par torsional CW", 5, torque_groups), _result_section("ccw", "Par torsional CCW", 5, torque_groups)], magnitude="Par torsional", source="FCA-30 R1 HOJA DE CAMPO PAR TORSIONAL.pdf", signature=vertical, table_span=3, signature_span=1)

    pressure_groups = [("Valores Medidos IBC", [("ibc_value_1", "Valores Medidos IBC")]), ("Valores Medidos Patrón", [("pattern_value", "Acendente"), ("ibc_value_2", "Descendente"), ("ibc_value_3", "Ascendente")])]
    docs["presion"] = _official_template("presion", "Hoja de Campo Presión", "direction_cycle", [_result_section("pressure_cycle", "DATOS DE MEDICION", 11, pressure_groups)], magnitude="Presión", source="FCA-30 R1 HOJA DE CAMPO PRESIÓN (manometro, vacuometro, diferencial de presion).pdf", supported=["manómetro", "vacuómetro", "diferencial de presión"], signature=vertical, table_span=3, signature_span=1)
    docs["presion"]["version"] = 3

    verification_groups = [("Unidades medidas", [("measured_units", "Unidades medidas")]), ("Valores medidos (IBC)", [(f"ibc_{i}", label) for i, label in enumerate(["Primera", "Segunda", "Tercera"], 1)]), ("Cumple", [("complies", "Cumple con funcionamiento")])]
    verification_common = {"header": [], "client": ["attention", "company", "address"], "equipment": ["instrument", "brand", "serial_number", "model", "internal_id", "location"], "calibration": ["calibration_date", "next_calibration_date", "calibration_place"]}
    verification_specs = {"calibration": [{"key": "calibration_date", "label": "Fecha de verificación", "field_type": "date"}, {"key": "next_calibration_date", "label": "Próxima verificación", "field_type": "date"}]}
    docs["verificacion_equipos"] = _official_template("verificacion_equipos", "Hoja de Campo Verificación de Equipos", "verification_compliance", [_result_section("verification", "DATOS DE VERIFICACIÓN", 6, verification_groups, data_types={"complies": "boolean"})], magnitude="Verificación", source="FCA-30 R1 HOJA DE CAMPO VERIFICACION DE EQUIPOS.pdf", signature=four, common_overrides=verification_common, field_specs=verification_specs)

    main_mass = _result_section("eccentricity", "Prueba de Excentrica", 6, [("Prueba de Excentrica", [("eccentricity", "Prueba de Excentrica")]), ("Valores Medidos Patrón", [("pattern_value", "Patrón")]), ("Valores Medidos IBC", [("ascending", "Ascendente"), ("descending", "Descendente"), ("ascending_2", "Asdcendente")])], layout={"width_fraction": 0.62, "row_group": "mass", "group_order": 1})
    rep50 = _result_section("repeatability_50", "Prueba de Repetibilidad al 50%", 5, [("Valor", [("value", "Valor")])], layout={"width_fraction": 0.19, "row_group": "mass", "group_order": 2})
    rep100 = _result_section("repeatability_100", "Prueba de Repetibilidad al 100%", 5, [("Valor", [("value", "Valor")])], layout={"width_fraction": 0.19, "row_group": "mass", "group_order": 3})
    docs["bascula"] = _official_template("bascula", "Hoja de Campo Báscula y Balanza", "mass_balance_composite", [main_mass, rep50, rep100], magnitude="Masa", variant="Báscula y Balanza", source="FCA-30 R1 HOJA DE CAMPO BASCULA Y BALANZA.pdf", supported=["báscula", "balanza"], signature=four)
    docs["bascula"]["version"] = 4
    return docs


OFFICIAL_PILOT_TEMPLATES.update(_materialize_official_templates())


def get_official_pilot_template(template_key: str) -> dict | None:
    template = OFFICIAL_PILOT_TEMPLATES.get(template_key)
    return deepcopy(template) if template else None
