"""Declarative foundation for the official MYC field-sheet document engine.

This module intentionally contains no persistence or metrological calculations.  It
defines reusable document blocks, the eight approved table families and the four
first official templates as plain data so the API, capture UI, PDF renderer and the
future visual designer can share the same contract.
"""

from copy import deepcopy


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


def _template(key: str, name: str, family: str, table: dict, *, ambiguous: bool = False) -> dict:
    return {
        "template_key": key,
        "key": key,
        "name": name,
        "description": "Plantilla oficial MYC basada en FCA-30 R1.",
        "status": "active",
        "version": 1,
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
                        _column("position", "Posición", configurable=True),
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
    ),
}


def get_official_pilot_template(template_key: str) -> dict | None:
    template = OFFICIAL_PILOT_TEMPLATES.get(template_key)
    return deepcopy(template) if template else None

