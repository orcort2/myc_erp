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


DEFAULT_SIGNATURE_LAYOUT = {
    "layout": "three_columns",
    "slots": [
        {"role": "calibrated_by", "display_label": "Calibró"},
        {"role": "reviewed_by", "display_label": "Revisó"},
        {"role": "report_made_by", "display_label": "Elaboró informe"},
    ],
}


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
) -> dict:
    return {
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
) -> dict:
    return {
        "template_key": key,
        "key": key,
        "name": name,
        "description": "Plantilla oficial MYC basada en FCA-30 R1.",
        "status": "active",
        "version": version,
        "is_active": True,
        "code": "FCA-30",
        "revision": "R1",
        "document_code": "FCA-30",
        "document_revision": "R1",
        "pages": 1,
        "pdf_template": "field_sheet_engine_pdf.html",
        "table_family": family,
        "blocks": _base_blocks(table),
        "signature_layout": deepcopy(DEFAULT_SIGNATURE_LAYOUT),
        "pagination": {"mode": "dynamic", "label": "Página X de Y"},
        "automation": {"mode": "manual_only", "calculations": []},
        "metadata": {
            "official_reference": "FCA-30 R1",
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
    "presion": _template(
        "presion",
        "Hoja de Campo Presión",
        "direction_cycle",
        _table_block(
            "PressureTableBlock",
            "pressure_cycle",
            "Resultados de la calibración",
            [
                _section(
                    "pressure_cycle",
                    "Ciclo de presión",
                    11,
                    [
                        _column("ibc_value_1", "IBC", "25%", configurable=True),
                        _column("pattern_value", "Patrón ascendente", "25%", configurable=True),
                        _column("ibc_value_2", "Patrón descendente", "25%", configurable=True),
                        _column("ibc_value_3", "Patrón ascendente", "25%", configurable=True),
                    ],
                    ambiguous=True,
                )
            ],
            "direction_cycle",
            ambiguous=True,
        ),
        ambiguous=True,
        magnitude_key="pressure",
        magnitude_label="Presión",
        supported_equipment=["manómetro", "vacuómetro", "manovacuómetro"],
        search_aliases=["manometro", "vacuometro", "manovacuometro", "presion", "presion diferencial"],
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


def get_official_pilot_template(template_key: str) -> dict | None:
    template = OFFICIAL_PILOT_TEMPLATES.get(template_key)
    return deepcopy(template) if template else None
