from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timezone

from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.field_sheet import FieldSheetResult
from app.models.field_sheet_template_definition import FieldSheetTemplateDefinition
from app.schemas.field_sheet_template import (
    FieldSheetTemplateCreate,
    FieldSheetTemplateImport,
    FieldSheetTemplateUpdate,
)
from app.services.audit_logs import write_audit_log
from app.services.field_sheet_template_engine import (
    DEFAULT_SIGNATURE_LAYOUT,
    OFFICIAL_TABLE_FAMILIES,
    get_official_pilot_template,
    resolve_table_family,
)
from app.services.field_sheet_layouts import (
    normalize_block_print_layout,
    normalize_print_layout,
    normalize_result_section,
    normalize_signature_layout,
    resolve_organization_print_profile,
)


FIELD_SHEET_BLOCK_TYPES = {
    "HeaderBlock",
    "ClientBlock",
    "ServiceOrderBlock",
    "EquipmentBlock",
    "CalibrationDataBlock",
    "GeneralDataBlock",
    "EquipmentDataBlock",
    "EnvironmentalBlock",
    "StandardsBlock",
    "ResultsTableBlock",
    "SimpleComparisonTableBlock",
    "MultiPointTableBlock",
    "SectionedTableBlock",
    "RepeatabilityTableBlock",
    "DimensionalTableBlock",
    "PressureTableBlock",
    "MassBalanceTableBlock",
    "ElectricalTableBlock",
    "ObservationsBlock",
    "SignaturesBlock",
    "FooterBlock",
    "CustomFieldsBlock",
    "SectionBlock",
    "AttachmentPlaceholderBlock",
}
CANONICAL_PDF_RENDERER_KEY = "field_sheet_engine"
CANONICAL_PDF_RENDERER_VERSION = 1
CANONICAL_PDF_TEMPLATE = "field_sheet_engine_pdf.html"
TABLE_BLOCK_TYPES = {
    "ResultsTableBlock",
    "SimpleComparisonTableBlock",
    "MultiPointTableBlock",
    "SectionedTableBlock",
    "RepeatabilityTableBlock",
    "DimensionalTableBlock",
    "PressureTableBlock",
    "MassBalanceTableBlock",
    "ElectricalTableBlock",
}
BLOCK_TYPE_LABELS = {
    "HeaderBlock": "Encabezado",
    "ClientBlock": "Cliente",
    "ServiceOrderBlock": "Orden de servicio",
    "EquipmentBlock": "Equipo",
    "CalibrationDataBlock": "Datos de calibración",
    "EnvironmentalBlock": "Ambientales",
    "StandardsBlock": "Patrones",
    "ResultsTableBlock": "Tabla de resultados",
    "ObservationsBlock": "Observaciones",
    "SignaturesBlock": "Firmas",
    "FooterBlock": "Pie",
    "CustomFieldsBlock": "Campos libres",
    "SectionBlock": "Sección",
    "AttachmentPlaceholderBlock": "Adjuntos",
    "GeneralDataBlock": "Datos generales",
    "EquipmentDataBlock": "Datos del equipo",
    "SimpleComparisonTableBlock": "Comparación directa",
    "MultiPointTableBlock": "Tabla multipunto",
    "SectionedTableBlock": "Tabla seccionada",
    "RepeatabilityTableBlock": "Repetibilidad",
    "DimensionalTableBlock": "Dimensional",
    "PressureTableBlock": "Presión",
    "MassBalanceTableBlock": "Masa / balanza",
    "ElectricalTableBlock": "Eléctrica",
}
FIELD_SHEET_TEMPLATE_KEYS = (
    "calibradores",
    "presion",
    "general",
    "temperatura",
    "termometro",
    "termohigrometro",
    "cronometro",
    "tacometro",
    "anemometro",
    "manometro",
    "transductor_presion",
    "valvula",
    "dimensional",
    "regla",
    "vernier",
    "micrometro",
    "flexometro",
    "masa",
    "balanza",
    "bascula",
    "peso_patron",
    "electrica",
    "multimetro",
    "luxometro",
    "sonido",
    "sonometro",
    "torquimetro",
    "dinamometro",
    "durometro",
    "volumen",
)

BLOCK_FAMILY_DEFAULTS = {
    "HeaderBlock": {
        "title": "Encabezado",
        "visible_fields": [
            "document_code",
            "document_revision",
            "field_sheet_folio",
            "work_order_number",
            "reserved_certificate_folio",
        ],
        "fields": [],
        "required": True,
    },
    "ClientBlock": {
        "title": "Cliente",
        "visible_fields": ["attention", "company", "address"],
        "fields": [],
        "required": True,
    },
    "ServiceOrderBlock": {
        "title": "Orden de servicio",
        "visible_fields": ["work_order_number", "purchase_order_or_quotation"],
        "fields": [],
        "required": False,
    },
    "EquipmentBlock": {
        "title": "Equipo",
        "visible_fields": [
            "instrument",
            "brand",
            "model",
            "serial_number",
            "internal_id",
            "location",
            "minimum_division",
            "initial_condition",
            "final_condition",
        ],
        "fields": [],
        "required": True,
    },
    "CalibrationDataBlock": {
        "title": "Datos de calibración",
        "visible_fields": [
            "calibration_place",
            "reception_date",
            "calibration_date",
            "next_calibration_date",
            "units",
            "method",
        ],
        "fields": [],
        "required": False,
    },
    "GeneralDataBlock": {
        "title": "Datos generales",
        "visible_fields": [
            "work_order_number",
            "reserved_certificate_folio",
            "attention",
            "company",
            "address",
        ],
        "fields": [],
        "required": True,
    },
    "EquipmentDataBlock": {
        "title": "Datos del equipo",
        "visible_fields": [
            "instrument",
            "scope",
            "brand",
            "model",
            "serial_number",
            "internal_id",
            "location",
            "minimum_division",
        ],
        "fields": [],
        "required": True,
    },
    "EnvironmentalBlock": {
        "title": "Condiciones ambientales",
        "visible_fields": [
            "reception_date",
            "calibration_date",
            "next_calibration_date",
            "environment_humidity_start",
            "environment_humidity_end",
            "environment_temperature_start",
            "environment_temperature_end",
        ],
        "fields": [],
        "required": False,
    },
    "StandardsBlock": {
        "title": "Patrones",
        "visible_fields": ["pattern_used"],
        "fields": [],
        "required": False,
    },
    "ObservationsBlock": {
        "title": "Datos técnicos",
        "visible_fields": [
            "initial_condition",
            "final_condition",
            "method",
            "units",
            "observations",
            "evidence_notes",
        ],
        "fields": [],
        "required": True,
    },
    "SignaturesBlock": {
        "title": "Firmas",
        "visible_fields": [
            "calibrated_by",
            "reviewed_by",
            "report_made_by",
        ],
        "fields": [],
        "required": True,
    },
    "FooterBlock": {
        "title": "Pie",
        "visible_fields": ["observations"],
        "fields": [],
        "required": False,
    },
    "CustomFieldsBlock": {
        "title": "Campos libres",
        "visible_fields": [],
        "fields": [],
        "required": False,
    },
    "SectionBlock": {
        "title": "Sección",
        "visible_fields": [],
        "fields": [],
        "required": False,
    },
    "AttachmentPlaceholderBlock": {
        "title": "Adjuntos",
        "visible_fields": [],
        "fields": [],
        "required": False,
    },
}

def _column(key: str, label: str, width: str | None = None, unit: str | None = None) -> dict:
    return {
        "key": key,
        "label": label,
        "source": key,
        "width": width,
        "unit": unit,
        "editable": True,
    }


COMPARISON_COLUMNS = [
    _column("pattern_value", "Patrón", "18%"),
    _column("instrument_reading", "Indicación instrumento"),
    _column("error_value", "Error"),
    _column("unit", "Unidad", "12%"),
    _column("notes", "Observaciones", "18%"),
]
MULTI_POINT_COLUMNS = [
    _column("nominal_point", "Punto nominal"),
    _column("pattern_value", "Patrón"),
    _column("instrument_reading", "Indicación instrumento"),
    _column("error_value", "Error"),
    _column("result_value", "Resultado"),
    _column("notes", "Observaciones", "18%"),
]
REPEATABILITY_COLUMNS = [
    _column("point_label", "Punto"),
    _column("reading_1", "Lectura 1"),
    _column("reading_2", "Lectura 2"),
    _column("reading_3", "Lectura 3"),
    _column("average_value", "Promedio"),
    _column("unit", "Unidad", "12%"),
    _column("notes", "Observaciones", "18%"),
]
DIMENSIONAL_COLUMNS = [
    _column("nominal_length", "Longitud nominal"),
    _column("pattern_reading", "Lectura patrón"),
    _column("instrument_reading", "Lectura instrumento"),
    _column("error_value", "Error"),
    _column("unit", "Unidad", "12%"),
    _column("notes", "Observaciones", "18%"),
]
PRESSURE_COLUMNS = [
    _column("nominal_point", "Punto nominal"),
    _column("ascending_pattern", "Ascendente patrón"),
    _column("ascending_instrument", "Ascendente instrumento"),
    _column("descending_pattern", "Descendente patrón"),
    _column("descending_instrument", "Descendente instrumento"),
    _column("error_value", "Error"),
    _column("unit", "Unidad", "12%"),
    _column("notes", "Observaciones", "18%"),
]
MASS_COLUMNS = [
    _column("applied_load", "Carga aplicada"),
    _column("instrument_reading", "Indicación"),
    _column("error_value", "Error"),
    _column("eccentricity_value", "Excentricidad"),
    _column("repeatability_value", "Repetibilidad"),
    _column("unit", "Unidad", "12%"),
    _column("notes", "Observaciones", "18%"),
]
ELECTRICAL_COLUMNS = [
    _column("nominal_point", "Punto nominal"),
    _column("pattern_value", "Patrón"),
    _column("instrument_reading", "Indicación instrumento"),
    _column("error_value", "Error"),
    _column("unit", "Unidad", "12%"),
    _column("notes", "Observaciones", "18%"),
]


def _table_block(
    block_type: str,
    key: str,
    title: str,
    columns: list[dict],
    *,
    rows: int = 10,
    min_rows: int = 3,
    max_rows: int = 20,
    allow_add_rows: bool = True,
    sections: list[dict] | None = None,
) -> dict:
    return {
        "key": key,
        "block_type": block_type,
        "title": title,
        "visible_fields": [],
        "columns": deepcopy(columns),
        "sections": deepcopy(sections or []),
        "suggested_unit": None,
        "rows": rows,
        "min_rows": min_rows,
        "max_rows": max_rows,
        "allow_add_rows": allow_add_rows,
        "required": True,
        "print_order": 0,
        "capture_order": 0,
    }


def _section(key: str, title: str, rows: int, columns: list[dict]) -> dict:
    return {
        "key": key,
        "title": title,
        "rows": rows,
        "columns": deepcopy(columns),
    }


def _default_block(block_type: str, order: int) -> dict:
    if block_type in BLOCK_FAMILY_DEFAULTS:
        block = deepcopy(BLOCK_FAMILY_DEFAULTS[block_type])
        block.update(
            {
                "key": f"{block_type}_{order}",
                "block_key": f"{block_type}_{order}",
                "block_type": block_type,
                "columns": [],
                "sections": [],
                "table_config": {},
                "suggested_unit": None,
                "rows": None,
                "min_rows": None,
                "max_rows": None,
                "allow_add_rows": False,
                "allow_remove_rows": False,
                "print_order": order,
                "capture_order": order,
                "order": order,
                "visible": True,
                "print_visible": True,
                "capture_visible": True,
                "pdf_visible": True,
                "metadata": {},
            }
        )
        return block
    if block_type == "ResultsTableBlock":
        block = _table_block(block_type, f"results_table_{order}", "Tabla de resultados", COMPARISON_COLUMNS, rows=10)
    if block_type == "SimpleComparisonTableBlock":
        block = _table_block(block_type, f"simple_comparison_{order}", "Tabla comparativa", COMPARISON_COLUMNS, rows=10)
    elif block_type == "MultiPointTableBlock":
        block = _table_block(block_type, f"multi_point_{order}", "Tabla multipunto", MULTI_POINT_COLUMNS, rows=10)
    elif block_type == "RepeatabilityTableBlock":
        block = _table_block(block_type, f"repeatability_{order}", "Tabla de repetibilidad", REPEATABILITY_COLUMNS, rows=5, min_rows=3, max_rows=10)
    elif block_type == "DimensionalTableBlock":
        block = _table_block(block_type, f"dimensional_{order}", "Tabla dimensional", DIMENSIONAL_COLUMNS, rows=10)
    elif block_type == "PressureTableBlock":
        block = _table_block(block_type, f"pressure_{order}", "Tabla de presión", PRESSURE_COLUMNS, rows=8)
    elif block_type == "MassBalanceTableBlock":
        block = _table_block(block_type, f"mass_balance_{order}", "Tabla masa / balanza", MASS_COLUMNS, rows=8)
    elif block_type == "ElectricalTableBlock":
        block = _table_block(
            block_type,
            f"electrical_{order}",
            "Tabla eléctrica",
            ELECTRICAL_COLUMNS,
            rows=5,
            min_rows=3,
            max_rows=10,
            sections=[
                _section("voltage_ac", "Voltaje AC", 5, ELECTRICAL_COLUMNS),
                _section("voltage_dc", "Voltaje DC", 5, ELECTRICAL_COLUMNS),
                _section("current_ac", "Corriente AC", 5, ELECTRICAL_COLUMNS),
                _section("current_dc", "Corriente DC", 5, ELECTRICAL_COLUMNS),
                _section("resistance", "Resistencia", 5, ELECTRICAL_COLUMNS),
                _section("frequency", "Frecuencia", 5, ELECTRICAL_COLUMNS),
                _section("continuity", "Continuidad", 5, ELECTRICAL_COLUMNS),
            ],
        )
    elif block_type == "SectionedTableBlock":
        block = _table_block(
            block_type,
            f"sectioned_{order}",
            "Secciones personalizadas",
            ELECTRICAL_COLUMNS,
            rows=5,
            sections=[_section("custom_section", "Sección personalizada", 5, ELECTRICAL_COLUMNS)],
        )
    else:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Bloque no soportado: {block_type}",
        )
    block["print_order"] = order
    block["capture_order"] = order
    block["order"] = order
    block["block_key"] = block["key"]
    block["visible"] = True
    block["table_config"] = {}
    block["allow_remove_rows"] = True
    block["print_visible"] = True
    block["capture_visible"] = True
    block["pdf_visible"] = True
    block["metadata"] = {}
    return block


TEMPLATE_BLOCK_ASSIGNMENTS = {
    "calibradores": ["GeneralDataBlock", "EquipmentDataBlock", "EnvironmentalBlock", "SectionedTableBlock", "ObservationsBlock", "SignaturesBlock"],
    "presion": ["GeneralDataBlock", "EquipmentDataBlock", "EnvironmentalBlock", "PressureTableBlock", "ObservationsBlock", "SignaturesBlock"],
    "general": ["GeneralDataBlock", "EquipmentDataBlock", "EnvironmentalBlock", "SimpleComparisonTableBlock", "ObservationsBlock", "SignaturesBlock"],
    "temperatura": ["GeneralDataBlock", "EquipmentDataBlock", "EnvironmentalBlock", "SimpleComparisonTableBlock", "ObservationsBlock", "SignaturesBlock"],
    "termometro": ["GeneralDataBlock", "EquipmentDataBlock", "EnvironmentalBlock", "SimpleComparisonTableBlock", "ObservationsBlock", "SignaturesBlock"],
    "termohigrometro": ["GeneralDataBlock", "EquipmentDataBlock", "EnvironmentalBlock", "SimpleComparisonTableBlock", "ObservationsBlock", "SignaturesBlock"],
    "cronometro": ["GeneralDataBlock", "EquipmentDataBlock", "EnvironmentalBlock", "SimpleComparisonTableBlock", "RepeatabilityTableBlock", "ObservationsBlock", "SignaturesBlock"],
    "tacometro": ["GeneralDataBlock", "EquipmentDataBlock", "EnvironmentalBlock", "SimpleComparisonTableBlock", "RepeatabilityTableBlock", "ObservationsBlock", "SignaturesBlock"],
    "anemometro": ["GeneralDataBlock", "EquipmentDataBlock", "EnvironmentalBlock", "MultiPointTableBlock", "ObservationsBlock", "SignaturesBlock"],
    "manometro": ["GeneralDataBlock", "EquipmentDataBlock", "EnvironmentalBlock", "PressureTableBlock", "ObservationsBlock", "SignaturesBlock"],
    "transductor_presion": ["GeneralDataBlock", "EquipmentDataBlock", "EnvironmentalBlock", "PressureTableBlock", "ObservationsBlock", "SignaturesBlock"],
    "valvula": ["GeneralDataBlock", "EquipmentDataBlock", "EnvironmentalBlock", "PressureTableBlock", "ObservationsBlock", "SignaturesBlock"],
    "dimensional": ["GeneralDataBlock", "EquipmentDataBlock", "EnvironmentalBlock", "DimensionalTableBlock", "ObservationsBlock", "SignaturesBlock"],
    "regla": ["GeneralDataBlock", "EquipmentDataBlock", "EnvironmentalBlock", "DimensionalTableBlock", "ObservationsBlock", "SignaturesBlock"],
    "vernier": ["GeneralDataBlock", "EquipmentDataBlock", "EnvironmentalBlock", "DimensionalTableBlock", "ObservationsBlock", "SignaturesBlock"],
    "micrometro": ["GeneralDataBlock", "EquipmentDataBlock", "EnvironmentalBlock", "DimensionalTableBlock", "RepeatabilityTableBlock", "ObservationsBlock", "SignaturesBlock"],
    "flexometro": ["GeneralDataBlock", "EquipmentDataBlock", "EnvironmentalBlock", "DimensionalTableBlock", "ObservationsBlock", "SignaturesBlock"],
    "masa": ["GeneralDataBlock", "EquipmentDataBlock", "EnvironmentalBlock", "MassBalanceTableBlock", "ObservationsBlock", "SignaturesBlock"],
    "balanza": ["GeneralDataBlock", "EquipmentDataBlock", "EnvironmentalBlock", "MassBalanceTableBlock", "RepeatabilityTableBlock", "ObservationsBlock", "SignaturesBlock"],
    "bascula": ["GeneralDataBlock", "EquipmentDataBlock", "EnvironmentalBlock", "MassBalanceTableBlock", "RepeatabilityTableBlock", "ObservationsBlock", "SignaturesBlock"],
    "peso_patron": ["GeneralDataBlock", "EquipmentDataBlock", "EnvironmentalBlock", "MassBalanceTableBlock", "ObservationsBlock", "SignaturesBlock"],
    "electrica": ["GeneralDataBlock", "EquipmentDataBlock", "EnvironmentalBlock", "ElectricalTableBlock", "SectionedTableBlock", "ObservationsBlock", "SignaturesBlock"],
    "multimetro": ["GeneralDataBlock", "EquipmentDataBlock", "EnvironmentalBlock", "ElectricalTableBlock", "SectionedTableBlock", "ObservationsBlock", "SignaturesBlock"],
    "luxometro": ["GeneralDataBlock", "EquipmentDataBlock", "EnvironmentalBlock", "MultiPointTableBlock", "ObservationsBlock", "SignaturesBlock"],
    "sonido": ["GeneralDataBlock", "EquipmentDataBlock", "EnvironmentalBlock", "MultiPointTableBlock", "ObservationsBlock", "SignaturesBlock"],
    "sonometro": ["GeneralDataBlock", "EquipmentDataBlock", "EnvironmentalBlock", "MultiPointTableBlock", "ObservationsBlock", "SignaturesBlock"],
    "torquimetro": ["GeneralDataBlock", "EquipmentDataBlock", "EnvironmentalBlock", "MultiPointTableBlock", "RepeatabilityTableBlock", "ObservationsBlock", "SignaturesBlock"],
    "dinamometro": ["GeneralDataBlock", "EquipmentDataBlock", "EnvironmentalBlock", "MultiPointTableBlock", "RepeatabilityTableBlock", "ObservationsBlock", "SignaturesBlock"],
    "durometro": ["GeneralDataBlock", "EquipmentDataBlock", "EnvironmentalBlock", "MultiPointTableBlock", "ObservationsBlock", "SignaturesBlock"],
    "volumen": ["GeneralDataBlock", "EquipmentDataBlock", "EnvironmentalBlock", "MultiPointTableBlock", "RepeatabilityTableBlock", "ObservationsBlock", "SignaturesBlock"],
}

TEMPLATE_ALIASES = {
    "indicador": "general",
    "vacuometro": "manometro",
    "indicador_presion": "manometro",
    "presostato": "transductor_presion",
    "calibrador": "dimensional",
    "pinza_amperimetrica": "multimetro",
    "fuente": "electrica",
    "flujo": "volumen",
}

# Fase 3 (2026-09): esto NO es autoridad de familias para definiciones
# nuevas -- es compatibilidad exclusiva para las plantillas fallback
# legacy que todavia no tienen una FieldSheetTemplateDefinition propia en
# BD (ver build_fallback_template_definition). Los valores aqui son claves
# legacy (algunas ambiguas, ver AMBIGUOUS_LEGACY_FAMILIES en el motor) que
# resolve_table_family() interpreta en modo "lenient" -- nunca se ofrecen
# como opcion para una definicion nueva.
#
# Las 5 plantillas oficiales
# (calibradores/presion/anemometro/bascula/temperatura) NO
# tienen entrada aqui a propósito: su family_key vive en su propia
# definicion oficial (field_sheet_template_engine.OFFICIAL_PILOT_TEMPLATES)
# y build_fallback_template_definition la usa directamente sin consultar
# este diccionario -- una entrada aqui nunca podria sobrescribirla, pero
# mantenerla igual invitaria a leerla como si fuera autoridad.
LEGACY_TEMPLATE_FAMILY = {
    "general": "direct_comparison",
    "termometro": "direct_comparison",
    "termohigrometro": "direct_comparison",
    "cronometro": "direct_comparison",
    "tacometro": "direct_comparison",
    "luxometro": "multipoint",
    "sonido": "multipoint",
    "sonometro": "multipoint",
    "torquimetro": "multipoint",
    "dinamometro": "multipoint",
    "durometro": "multipoint",
    "volumen": "multipoint",
    "manometro": "pressure",
    "transductor_presion": "pressure",
    "valvula": "pressure",
    "dimensional": "dimensional",
    "regla": "dimensional",
    "vernier": "dimensional",
    "micrometro": "dimensional",
    "flexometro": "dimensional",
    "masa": "mass",
    "balanza": "mass",
    "peso_patron": "mass",
    "electrica": "electrical",
    "multimetro": "electrical",
}

TEMPLATE_NAMES = {
    "calibradores": "Hoja de Campo Calibradores",
    "presion": "Hoja de Campo Presión",
    "general": "Hoja de Campo General",
    "temperatura": "Hoja de Campo Temperatura",
    "termometro": "Hoja de Campo Termómetro",
    "termohigrometro": "Hoja de Campo Termohigrómetro",
    "cronometro": "Hoja de Campo Cronómetro",
    "tacometro": "Hoja de Campo Tacómetro",
    "anemometro": "Hoja de Campo Anemómetro",
    "manometro": "Hoja de Campo Manómetro",
    "transductor_presion": "Hoja de Campo Transductor de Presión",
    "valvula": "Hoja de Campo Válvula",
    "dimensional": "Hoja de Campo Dimensional",
    "regla": "Hoja de Campo Regla",
    "vernier": "Hoja de Campo Vernier",
    "micrometro": "Hoja de Campo Micrómetro",
    "flexometro": "Hoja de Campo Flexómetro",
    "masa": "Hoja de Campo Masa",
    "balanza": "Hoja de Campo Balanza",
    "bascula": "Hoja de Campo Báscula",
    "peso_patron": "Hoja de Campo Peso Patrón",
    "electrica": "Hoja de Campo Eléctrica",
    "multimetro": "Hoja de Campo Multímetro",
    "luxometro": "Hoja de Campo Luxómetro",
    "sonido": "Hoja de Campo Sonido",
    "sonometro": "Hoja de Campo Sonómetro",
    "torquimetro": "Hoja de Campo Torquímetro",
    "dinamometro": "Hoja de Campo Dinamómetro",
    "durometro": "Hoja de Campo Durómetro",
    "volumen": "Hoja de Campo Volumen",
}


def _pdf_template_for_key(template_key: str) -> str:
    if get_official_pilot_template(template_key) is not None:
        return "field_sheet_engine_pdf.html"
    if template_key == "electrica":
        return "field_sheet_electrical_pdf.html"
    if template_key == "anemometro":
        return "field_sheet_anemometer_pdf.html"
    return "field_sheet_general_pdf.html"


def _build_result_sections(blocks: list[dict]) -> list[dict]:
    def result_section(block: dict, section: dict, *, key: str, title: str, rows: int) -> dict:
        source = {
            "key": key,
            "title": title,
            "rows": rows,
            "columns": deepcopy(section.get("columns") or block.get("columns") or []),
        }
        for field_name in (
            "allow_add_rows",
            "allow_remove_rows",
            "min_rows",
            "max_rows",
            "header_rows",
            "row_labels",
            "layout",
            "repeat_header",
            "break_inside",
            "page_break_before",
            "metadata",
        ):
            if field_name in section:
                source[field_name] = deepcopy(section[field_name])
            elif field_name in block:
                source[field_name] = deepcopy(block[field_name])
        return normalize_result_section(source)

    sections: list[dict] = []
    for block in sorted(blocks, key=lambda item: (item.get("print_order", 0), item.get("capture_order", 0))):
        if block["block_type"] not in TABLE_BLOCK_TYPES:
            continue
        if block.get("sections"):
            for index, section in enumerate(block["sections"], start=1):
                sections.append(
                    result_section(
                        block,
                        section,
                        key=section.get("key") or f"{block['key']}_{index}",
                        title=section.get("title") or block["title"],
                        rows=int(section.get("rows") or block.get("rows") or 1),
                    )
                )
        else:
            sections.append(
                result_section(
                    block,
                    block,
                    key=block["key"],
                    title=block["title"],
                    rows=int(block.get("rows") or 1),
                )
            )
    return sections


def _collect_visible_fields(blocks: list[dict]) -> list[str]:
    ordered = sorted(blocks, key=lambda item: (item.get("capture_order", 0), item.get("print_order", 0)))
    fields: list[str] = []
    for block in ordered:
        for field_name in block.get("visible_fields") or []:
            if field_name not in fields:
                fields.append(field_name)
    return fields


def _resolve_template_key(template_key: str, *, allow_custom: bool = False) -> str:
    canonical = TEMPLATE_ALIASES.get(template_key, template_key)
    if canonical not in TEMPLATE_BLOCK_ASSIGNMENTS and not allow_custom:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Plantilla de hoja de campo no soportada: {template_key}",
        )
    return canonical


def _catalog_block_types() -> list[dict]:
    return [
        {
            "key": block_type,
            "label": BLOCK_TYPE_LABELS.get(block_type, block_type),
            "is_table": block_type in TABLE_BLOCK_TYPES,
        }
        for block_type in sorted(FIELD_SHEET_BLOCK_TYPES)
    ]


def normalize_template_definition(payload: dict, *, table_family_mode: str = "lenient") -> dict:
    """`table_family_mode` se pasa tal cual a resolve_table_family():

    - "strict" (autoria NUEVA/editada de verdad via CRUD de plantillas): la
      family_key debe resolver a una de las 8 canonicas (o a un alias
      legacy seguro equivalente) -- una clave ambigua o desconocida se
      rechaza con 422.
    - "import" (reimportacion de un artefacto exportado): admite ademas las
      legacy ambiguas CONOCIDAS (AMBIGUOUS_LEGACY_FAMILIES), preservandolas
      tal cual -- pero una clave totalmente desconocida sigue rechazandose
      con 422.
    - "lenient" (default; releer definiciones YA persistidas en BD o
      fallback legacy): una family legacy ambigua o desconocida se
      conserva legible tal cual, nunca se rechaza ni se reescribe."""
    template_key = _resolve_template_key(payload["template_key"], allow_custom=True)
    blocks = [deepcopy(item) for item in payload.get("blocks") or []]
    if not blocks:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="La plantilla debe contener al menos un bloque",
        )
    normalized_blocks: list[dict] = []
    for index, block in enumerate(blocks, start=1):
        block_type = block["block_type"]
        if block_type not in FIELD_SHEET_BLOCK_TYPES:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"Bloque no soportado: {block_type}",
            )
        merged = _default_block(block_type, index)
        merged.update(block)
        merged["block_key"] = merged.get("block_key") or merged.get("key") or f"{block_type}_{index}"
        merged["key"] = merged["block_key"]
        merged["order"] = int(merged.get("order") or index)
        merged["visible"] = bool(merged.get("visible", True))
        merged["print_order"] = int(merged.get("print_order") or index)
        merged["capture_order"] = int(merged.get("capture_order") or index)
        merged["columns"] = [dict(column) for column in (merged.get("columns") or [])]
        merged["sections"] = [dict(section) for section in (merged.get("sections") or [])]
        merged["fields"] = [dict(field) for field in (merged.get("fields") or [])]
        merged["table_config"] = dict(merged.get("table_config") or {})
        merged["metadata"] = dict(merged.get("metadata") or {})
        merged["print_layout"] = normalize_block_print_layout(merged.get("print_layout"))
        merged["print_visible"] = bool(merged.get("print_visible", True))
        merged["capture_visible"] = bool(merged.get("capture_visible", True))
        merged["pdf_visible"] = bool(merged.get("pdf_visible", True))
        normalized_blocks.append(merged)

    definition = {
        "id": payload.get("id"),
        "source": payload.get("source", "fallback"),
        "template_key": template_key,
        "key": template_key,
        "name": payload.get("name") or TEMPLATE_NAMES.get(template_key, template_key),
        "description": payload.get("description"),
        "type": template_key,
        "status": payload.get("status") or "draft",
        "version": int(payload.get("version") or 1),
        "is_active": bool(payload.get("is_active", True)),
        "code": payload.get("code") or "FCA-30",
        "revision": payload.get("revision") or "R1",
        "pages": int(payload.get("pages") or 1),
        "pdf_template": payload.get("pdf_template") or _pdf_template_for_key(template_key),
        "document_code": payload.get("document_code") or payload.get("code") or "FCA-30",
        "document_revision": payload.get("document_revision") or payload.get("revision") or "R1",
        "table_family": resolve_table_family(
            payload.get("table_family") or LEGACY_TEMPLATE_FAMILY.get(template_key),
            mode=table_family_mode,
        ),
        "blocks": sorted(normalized_blocks, key=lambda item: (item["capture_order"], item["print_order"])),
        "validations": dict(payload.get("validations") or {}),
        "print_config": dict(payload.get("print_config") or {}),
        "print_layout": normalize_print_layout(payload.get("print_layout")),
        "pdf_config": dict(payload.get("pdf_config") or {}),
        "permissions_config": dict(payload.get("permissions_config") or {}),
        "metadata": dict(payload.get("metadata") or {}),
        "signature_layout": normalize_signature_layout(
            payload.get("signature_layout") or DEFAULT_SIGNATURE_LAYOUT
        ),
        "pagination": dict(payload.get("pagination") or {"mode": "dynamic", "label": "Página X de Y"}),
        "automation": dict(payload.get("automation") or {"mode": "manual_only", "calculations": []}),
    }
    document_grid_columns = definition["print_layout"]["document"]["grid_columns"]
    for block in definition["blocks"]:
        block_layout = block["print_layout"]
        if block_layout["column_span"] > document_grid_columns:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"El column_span de {block['key']} excede el grid documental",
            )
        for field in block.get("fields") or []:
            if int(field.get("column_span") or 1) > block_layout["grid_columns"]:
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    detail=f"El column_span del campo {field.get('key')} excede el grid del bloque",
                )
    definition["visible_fields"] = _collect_visible_fields(definition["blocks"])
    definition["result_sections"] = _build_result_sections(definition["blocks"])
    definition["organization_profile"] = resolve_organization_print_profile(definition)
    return definition


def canonicalize_new_field_sheet_snapshot(definition: dict) -> dict:
    """Orient only a newly created FieldSheet snapshot to the canonical engine.

    Historical snapshots remain byte-for-byte untouched and continue resolving
    their legacy ``pdf_template`` through the versioned renderer resolver.
    """
    snapshot = deepcopy(definition)
    snapshot["pdf_template"] = CANONICAL_PDF_TEMPLATE
    snapshot["pdf_renderer_key"] = CANONICAL_PDF_RENDERER_KEY
    snapshot["pdf_renderer_version"] = CANONICAL_PDF_RENDERER_VERSION
    return snapshot


def build_fallback_template_definition(template_key: str) -> dict:
    template_key = _resolve_template_key(template_key)
    official_template = get_official_pilot_template(template_key)
    if official_template is not None:
        return normalize_template_definition(official_template)
    blocks = [_default_block(block_type, index) for index, block_type in enumerate(TEMPLATE_BLOCK_ASSIGNMENTS[template_key], start=1)]
    return normalize_template_definition(
        {
            "template_key": template_key,
            "name": TEMPLATE_NAMES[template_key],
            "status": "active",
            "version": 1,
            "is_active": True,
            "source": "fallback",
            "pages": 2 if template_key == "electrica" else 1,
            "pdf_template": _pdf_template_for_key(template_key),
            "blocks": blocks,
        }
    )


def _latest_version(db: Session, template_key: str) -> int:
    current = db.scalar(
        select(func.max(FieldSheetTemplateDefinition.version)).where(
            FieldSheetTemplateDefinition.template_key == template_key,
        )
    )
    return int(current or 0)


def _query_active_templates(db: Session) -> list[FieldSheetTemplateDefinition]:
    return list(
        db.scalars(
            select(FieldSheetTemplateDefinition)
            .where(
                FieldSheetTemplateDefinition.is_active.is_(True),
                FieldSheetTemplateDefinition.status == "active",
            )
            .order_by(FieldSheetTemplateDefinition.template_key.asc(), FieldSheetTemplateDefinition.version.desc())
        ).all()
    )


def _serialize_row(row: FieldSheetTemplateDefinition) -> dict:
    return normalize_template_definition(
        {
            **row.definition_json,
            "id": row.id,
            "source": "database",
            "template_key": row.template_key,
            "name": row.name,
            "description": row.description,
            "status": row.status,
            "version": row.version,
            "is_active": row.is_active,
        }
    )


def list_field_sheet_templates(db: Session, *, include_all: bool = False) -> list[dict]:
    if include_all:
        rows = list(
            db.scalars(
                select(FieldSheetTemplateDefinition)
                .where(FieldSheetTemplateDefinition.is_active.is_(True))
                .order_by(
                    FieldSheetTemplateDefinition.template_key.asc(),
                    FieldSheetTemplateDefinition.version.desc(),
                )
            ).all()
        )
        return [_serialize_row(row) for row in rows]

    active_rows = _query_active_templates(db)
    rows_by_key = {row.template_key: row for row in active_rows}

    templates: list[dict] = []

    for template_key in TEMPLATE_BLOCK_ASSIGNMENTS:
        official_template = get_official_pilot_template(template_key)

        if official_template is not None:
            # Las plantillas oficiales controladas por código son la autoridad
            # para nuevas capturas. Una definición histórica/administrativa en
            # BD con la misma key no puede eclipsarlas.
            definition = normalize_template_definition(
                official_template
            )
        else:
            row = rows_by_key.get(template_key)

            if row is not None:
                definition = _serialize_row(row)
            else:
                definition = build_fallback_template_definition(
                    template_key
                )

        templates.append(definition)

    return templates


def get_field_sheet_template(
    db: Session,
    template_key: str,
) -> dict:
    template_key = _resolve_template_key(
        template_key
    )

    official_template = get_official_pilot_template(
        template_key
    )

    if official_template is not None:
        # Autoridad documental para nuevas FieldSheets.
        # Los snapshots históricos persistidos no pasan por aquí:
        # continúan utilizando su template_definition_json congelado.
        return normalize_template_definition(
            official_template
        )

    row = db.scalar(
        select(FieldSheetTemplateDefinition).where(
            FieldSheetTemplateDefinition.template_key
            == template_key,
            FieldSheetTemplateDefinition.is_active.is_(True),
            FieldSheetTemplateDefinition.status
            == "active",
        )
    )

    if row is not None:
        return _serialize_row(row)

    return build_fallback_template_definition(
        template_key
    )


def create_field_sheet_template(
    db: Session,
    payload: FieldSheetTemplateCreate,
    *,
    user_id: int | None = None,
    table_family_mode: str = "strict",
) -> dict:
    """`table_family_mode="strict"` (default) es AUTORIA NUEVA real -- exige
    family canonica o alias legacy seguro, rechaza cualquier ambigua/
    desconocida con 422. `import_field_sheet_template` pasa "import" para
    reimportar un artefacto exportado (micro-cierre Fase 3, hallazgo unico):
    ese artefacto puede traer una legacy ambigua CONOCIDA ya persistida
    legitimamente en su momento -- import debe conservarla tal cual, no
    inventarla ni convertirla, pero sigue rechazando cualquier clave
    totalmente desconocida (ver resolve_table_family)."""
    template_key = _resolve_template_key(payload.template_key)
    definition = normalize_template_definition(
        {**payload.model_dump(), "template_key": template_key}, table_family_mode=table_family_mode
    )
    version = _latest_version(db, template_key) + 1 or 1
    desired_status = payload.status if payload.status in {"draft", "active", "inactive"} else "draft"
    row = FieldSheetTemplateDefinition(
        template_key=template_key,
        name=payload.name,
        description=payload.description,
        status=desired_status,
        version=version,
        definition_json={**definition, "version": version, "status": desired_status},
    )
    db.add(row)
    db.flush()
    if desired_status == "active":
        db.execute(
            FieldSheetTemplateDefinition.__table__.update()
            .where(
                FieldSheetTemplateDefinition.template_key == template_key,
                FieldSheetTemplateDefinition.id != row.id,
            )
            .values(status="inactive")
        )
    write_audit_log(
        db,
        action="field_sheet_template.created",
        entity="field_sheet_template_definitions",
        entity_id=row.id,
        user_id=user_id,
        new_values={"template_key": row.template_key, "version": row.version, "status": row.status},
    )
    db.commit()
    return get_field_sheet_template(db, template_key) if row.status == "active" else _serialize_row(row)


def update_field_sheet_template(db: Session, template_id: int, payload: FieldSheetTemplateUpdate, *, user_id: int | None = None) -> dict:
    row = db.get(FieldSheetTemplateDefinition, template_id)
    if row is None or not row.is_active:
        raise HTTPException(status_code=404, detail="Plantilla no encontrada")
    previous = {"name": row.name, "status": row.status, "version": row.version}
    data = payload.model_dump(exclude_unset=True)
    merged = {**row.definition_json, **data, "template_key": row.template_key, "name": data.get("name", row.name)}
    # Fase 3: sólo exigir resolucion estricta de family cuando ESTA edicion
    # de verdad la toca -- editar cualquier otro campo de una plantilla
    # antigua no debe romperse por una family legacy que nadie está
    # tocando en esta llamada.
    definition = normalize_template_definition(
        merged, table_family_mode="strict" if "table_family" in data else "lenient"
    )
    if row.status == "active":
        version = _latest_version(db, row.template_key) + 1
        desired_status = data.get("status") if data.get("status") in {"draft", "active", "inactive"} else "draft"
        new_row = FieldSheetTemplateDefinition(
            template_key=row.template_key,
            name=data.get("name", row.name),
            description=data.get("description", row.description),
            status=desired_status,
            version=version,
            definition_json={**definition, "version": version, "status": desired_status},
        )
        db.add(new_row)
        db.flush()
        if desired_status == "active":
            db.execute(
                FieldSheetTemplateDefinition.__table__.update()
                .where(
                    FieldSheetTemplateDefinition.template_key == row.template_key,
                    FieldSheetTemplateDefinition.id != new_row.id,
                    FieldSheetTemplateDefinition.is_active.is_(True),
                )
                .values(status="inactive")
            )
        write_audit_log(
            db,
            action="field_sheet_template.versioned",
            entity="field_sheet_template_definitions",
            entity_id=new_row.id,
            user_id=user_id,
            previous_values=previous,
            new_values={"template_key": new_row.template_key, "version": new_row.version, "status": new_row.status},
        )
        db.commit()
        return _serialize_row(new_row)
    if "name" in data:
        row.name = data["name"]
    if "description" in data:
        row.description = data["description"]
    if "status" in data:
        row.status = data["status"]
        if row.status == "active":
            db.execute(
                FieldSheetTemplateDefinition.__table__.update()
                .where(
                    FieldSheetTemplateDefinition.template_key == row.template_key,
                    FieldSheetTemplateDefinition.id != row.id,
                    FieldSheetTemplateDefinition.is_active.is_(True),
                )
                .values(status="inactive")
            )
    row.definition_json = {**definition, "version": row.version, "status": row.status}
    write_audit_log(
        db,
        action="field_sheet_template.updated",
        entity="field_sheet_template_definitions",
        entity_id=row.id,
        user_id=user_id,
        previous_values=previous,
        new_values={"name": row.name, "status": row.status, "version": row.version},
    )
    db.commit()
    return _serialize_row(row)


def duplicate_field_sheet_template(db: Session, template_id: int, *, user_id: int | None = None) -> dict:
    row = db.get(FieldSheetTemplateDefinition, template_id)
    if row is None or not row.is_active:
        raise HTTPException(status_code=404, detail="Plantilla no encontrada")
    version = _latest_version(db, row.template_key) + 1
    duplicate = FieldSheetTemplateDefinition(
        template_key=row.template_key,
        name=f"{row.name} v{version}",
        description=row.description,
        status="draft",
        version=version,
        definition_json=normalize_template_definition(
            {
                **row.definition_json,
                "template_key": row.template_key,
                "name": f"{row.name} v{version}",
                "version": version,
                "status": "draft",
            }
        ),
    )
    db.add(duplicate)
    db.flush()
    write_audit_log(
        db,
        action="field_sheet_template.duplicated",
        entity="field_sheet_template_definitions",
        entity_id=duplicate.id,
        user_id=user_id,
        new_values={"template_key": duplicate.template_key, "version": duplicate.version},
    )
    db.commit()
    return _serialize_row(duplicate)


def activate_field_sheet_template(db: Session, template_id: int, *, user_id: int | None = None) -> dict:
    row = db.get(FieldSheetTemplateDefinition, template_id)
    if row is None or not row.is_active:
        raise HTTPException(status_code=404, detail="Plantilla no encontrada")
    db.execute(
        FieldSheetTemplateDefinition.__table__.update()
        .where(
            FieldSheetTemplateDefinition.template_key == row.template_key,
            FieldSheetTemplateDefinition.is_active.is_(True),
        )
        .values(status="inactive")
    )
    row.status = "active"
    write_audit_log(
        db,
        action="field_sheet_template.activated",
        entity="field_sheet_template_definitions",
        entity_id=row.id,
        user_id=user_id,
        new_values={"template_key": row.template_key, "version": row.version, "status": row.status},
    )
    db.commit()
    return get_field_sheet_template(db, row.template_key)


def delete_field_sheet_template(db: Session, template_id: int, *, user_id: int | None = None) -> None:
    row = db.get(FieldSheetTemplateDefinition, template_id)
    if row is None or not row.is_active:
        raise HTTPException(status_code=404, detail="Plantilla no encontrada")
    previous_status = row.status
    row.is_active = False
    row.status = "archived"
    write_audit_log(
        db,
        action="field_sheet_template.deleted",
        entity="field_sheet_template_definitions",
        entity_id=row.id,
        user_id=user_id,
        previous_values={"status": previous_status},
        new_values={"is_active": False, "status": row.status},
    )
    db.commit()


def export_field_sheet_template(db: Session, template_id: int, *, user_id: int | None = None) -> dict:
    row = db.get(FieldSheetTemplateDefinition, template_id)
    if row is None or not row.is_active:
        raise HTTPException(status_code=404, detail="Plantilla no encontrada")
    write_audit_log(
        db,
        action="field_sheet_template.exported",
        entity="field_sheet_template_definitions",
        entity_id=row.id,
        user_id=user_id,
        new_values={"template_key": row.template_key, "version": row.version},
    )
    db.commit()
    return {
        "exported_at": datetime.now(timezone.utc).isoformat(),
        "template": _serialize_row(row),
    }


def import_field_sheet_template(db: Session, payload: FieldSheetTemplateImport, *, user_id: int | None = None) -> dict:
    """Micro-cierre Fase 3 (hallazgo unico): reimportar un artefacto
    exportado NO es autoria nueva -- su table_family puede ser una legacy
    ambigua CONOCIDA que ya era legitima cuando se exporto (p.ej.
    'electrical'). create_field_sheet_template() recibe
    table_family_mode="import" en vez del "strict" por defecto: preserva esa
    legacy ambigua tal cual (nunca la inventa, nunca la convierte a otra),
    sigue resolviendo alias legacy seguros a su canonico, y sigue
    rechazando con 422 cualquier clave totalmente desconocida."""
    template_payload = payload.template.model_dump()
    template_key = _resolve_template_key(payload.new_template_key or template_payload["template_key"], allow_custom=True)
    template_payload["template_key"] = template_key
    if payload.mode == "new_key":
        template_payload["status"] = "active" if payload.activate else template_payload.get("status", "draft")
        created = create_field_sheet_template(
            db,
            FieldSheetTemplateCreate.model_validate(template_payload),
            user_id=user_id,
            table_family_mode="import",
        )
        write_audit_log(
            db,
            action="field_sheet_template.imported",
            entity="field_sheet_template_definitions",
            entity_id=created.get("id"),
            user_id=user_id,
            new_values={"template_key": template_key, "mode": payload.mode},
        )
        db.commit()
        return created
    imported = create_field_sheet_template(
        db,
        FieldSheetTemplateCreate.model_validate(
            {
                **template_payload,
                "status": "active" if payload.activate else template_payload.get("status", "draft"),
            }
        ),
        user_id=user_id,
        table_family_mode="import",
    )
    write_audit_log(
        db,
        action="field_sheet_template.imported",
        entity="field_sheet_template_definitions",
        entity_id=imported.get("id"),
        user_id=user_id,
        new_values={"template_key": template_key, "mode": payload.mode},
    )
    db.commit()
    return imported


def get_field_sheet_template_catalog() -> dict:
    return {
        "block_types": _catalog_block_types(),
        "table_families": [deepcopy(item) for item in OFFICIAL_TABLE_FAMILIES.values()],
        "supported_template_keys": sorted(TEMPLATE_BLOCK_ASSIGNMENTS.keys()),
    }


def get_template_snapshot(db: Session, template_key: str) -> tuple[dict, int]:
    template = get_field_sheet_template(db, template_key)
    return template, int(template.get("version") or 1)


def build_default_result_rows(template_definition: dict) -> list[FieldSheetResult]:
    rows: list[FieldSheetResult] = []
    for section in template_definition.get("result_sections") or []:
        for row_number in range(1, int(section.get("rows") or 0) + 1):
            rows.append(
                FieldSheetResult(
                    section_key=section["key"],
                    row_number=row_number,
                    row_data={},
                )
            )
    return rows
