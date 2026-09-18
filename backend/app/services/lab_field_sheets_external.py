"""PENDIENTE 7 (encargo de corrección LAB): servicio de "LAB EXTERNO".

Reutiliza exactamente el mismo ``FieldSheet``/``FieldSheetResult`` y el mismo
ciclo de vida (revisiones, ``is_current``, auditoría, congelado de PDF,
reapertura/corrección) que cualquier otra hoja de campo LAB -- ver
``lab_field_sheets.py: create_lab_field_sheet/discard_lab_field_sheet``, que
llaman a las funciones de este módulo en el punto donde normalmente
resolverían una plantilla institucional del catálogo (``get_template_snapshot``).

Diseño (estructura vs datos, sección "TABLAS DINÁMICAS" del encargo):

- ESTRUCTURA (grupos -> tablas -> columnas, orientación por grupo) vive en
  ``FieldSheet.template_definition_json["groups"]`` -- el mismo campo que ya
  usa cualquier plantilla para su definición, y que YA se clona
  automáticamente en cada revisión histórica sin cambios adicionales (ver
  ``_clone_field_sheet_for_correction``). Nunca se toca cuando la hoja deja
  de ser editable (draft/in_progress) -- ver ``apply_lab_external_structure``.
- DATOS (valores capturados) viven en ``FieldSheetResult`` -- una fila por
  ``(table.id como section_key, row_number)``, con las columnas dinámicas
  como ``row_data = {column_key: value}``. Se editan con el
  PATCH .../field-sheet YA EXISTENTE (``FieldSheetUpdate.results_rows``,
  ``FieldSheetResultUpdate.row_data``) -- ningún endpoint nuevo para esto.

No se creó una segunda tabla ni una migración: los tres campos JSON
involucrados (``template_definition_json``, ``capture_values``,
``FieldSheetResult.row_data``) ya existen, ya tienen integridad
referencial/cascada y ya participan del versionado por revisión.
"""

from __future__ import annotations

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models.field_sheet import FieldSheet, FieldSheetResult
from app.models.lab_work_order import LabWorkOrderEquipment
from app.models.user import User
from app.schemas.field_sheet import FieldSheetRead
from app.schemas.lab_field_sheet_external import LabExternalGroupWrite, LabExternalStructureWrite
from app.services.audit_logs import write_audit_log
from app.services.field_sheets import EDITABLE_STATUSES

LAB_EXTERNAL_TEMPLATE_KEY = "lab_externo"
LAB_EXTERNAL_PDF_RENDERER_KEY = f"legacy:field_sheet_{LAB_EXTERNAL_TEMPLATE_KEY}_pdf.html"
LAB_EXTERNAL_PDF_RENDERER_VERSION = 1
LAB_EXTERNAL_DEFINITION_VERSION = 1


def bootstrap_lab_external_definition() -> dict:
    """Definición inicial de una hoja LAB EXTERNO recién creada -- sin
    grupos todavía; el técnico los agrega con apply_lab_external_structure
    antes o mientras captura. Nunca proviene de get_template_snapshot: LAB
    EXTERNO no es una plantilla institucional del catálogo, es autorada por
    el técnico para ESTA hoja."""
    return {
        "kind": LAB_EXTERNAL_TEMPLATE_KEY,
        "pdf_renderer_key": LAB_EXTERNAL_PDF_RENDERER_KEY,
        "pdf_renderer_version": LAB_EXTERNAL_PDF_RENDERER_VERSION,
        "groups": [],
    }


def resolve_lab_external_definition(template_key: str) -> tuple[dict, int] | None:
    """None cuando template_key no es LAB EXTERNO -- el caller debe seguir
    con la resolución de catálogo normal (get_template_snapshot)."""
    if template_key != LAB_EXTERNAL_TEMPLATE_KEY:
        return None
    return bootstrap_lab_external_definition(), LAB_EXTERNAL_DEFINITION_VERSION


def ensure_lab_field_sheet_template_matches_service(
    equipment: LabWorkOrderEquipment, template_key: str
) -> None:
    """Sección "INTEGRACIÓN LINKED" del encargo -- contrato final,
    bidireccional (auditoría 2026-09-17, corrige la versión anterior de esta
    función que sólo exigía un sentido):

        accredited / traceable -> plantilla LAB interna (nunca LAB EXTERNO)
        linked                 -> LAB EXTERNO (nunca una plantilla interna)

    La versión previa permitía linked + plantilla interna alegando que era
    "un flujo preexistente y probado" -- eso describía el estado de los
    tests, no el contrato acordado. Los tests que de verdad estudiaban
    linked (test_signing_and_field_sheet_allow_linked_without_company,
    test_external_linked_sheet_can_start_pending_but_close_stays_internal,
    test_prevalidation_blocks_missing_sheet_incomplete_sheet_and_
    unresolved_folio, test_close_rejected_with_unresolved_linked_folio,
    test_linked_pending_capture_completes_then_blocks_close_until_
    authorized) ya se migraron a LAB EXTERNO -- ver esos archivos. Mobile ya
    exige esta misma regla (isLabExternalEquipment/LabTechnicalCapture);
    esta función sólo hace a backend consistente con lo que Mobile ya
    hacía."""
    is_linked = equipment.service_type == "linked"
    is_lab_external = template_key == LAB_EXTERNAL_TEMPLATE_KEY
    if is_lab_external and not is_linked:
        raise HTTPException(
            status_code=409,
            detail="LAB EXTERNO sólo aplica a equipo con servicio Vinculado",
        )
    if is_linked and not is_lab_external:
        raise HTTPException(
            status_code=409,
            detail="Este equipo es de servicio Vinculado: su hoja de campo debe ser LAB EXTERNO",
        )


def validate_lab_external_ready_to_complete(field_sheet: FieldSheet) -> None:
    """Sección 2 de la auditoría 2026-09-17: contrato EXPLÍCITO de
    completitud para LAB EXTERNO -- antes dependía por accidente de que
    _validate_ready_to_complete (motor genérico, piensa en "blocks"/
    "result_sections") simplemente no encontrara nada que exigir sobre
    template_definition_json["groups"], una forma que ese motor no conoce.

    Exige estructura mínima (al menos 1 grupo, cada grupo con al menos 1
    tabla, cada tabla con al menos 1 columna y row_count >= 1) y reutiliza
    _validate_results_rows (misma autoridad y mismo criterio ya vigente
    para cualquier otra plantilla LAB: basta con que ALGUNA celda tenga un
    valor no vacío en algún lado -- nunca exige llenar todas las celdas,
    eso no es la regla de negocio acordada)."""
    definition = field_sheet.template_definition_json or {}
    groups = definition.get("groups") or []
    if not groups:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail={
                "message": "LAB EXTERNO necesita al menos un grupo de tablas antes de completarse",
                "missing_fields": ["groups"],
            },
        )
    for group in groups:
        group_label = group.get("title") or group.get("id") or "?"
        tables = group.get("tables") or []
        if not tables:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail={
                    "message": f'El grupo "{group_label}" necesita al menos una tabla',
                    "missing_fields": ["tables"],
                },
            )
        for table in tables:
            table_label = table.get("title") or table.get("id") or "?"
            if not (table.get("columns") or []):
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                    detail={
                        "message": f'La tabla "{table_label}" necesita al menos una columna',
                        "missing_fields": ["columns"],
                    },
                )
            if int(table.get("row_count") or 0) < 1:
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                    detail={
                        "message": f'La tabla "{table_label}" necesita al menos una fila',
                        "missing_fields": ["row_count"],
                    },
                )

    from app.services.field_sheets import _validate_results_rows

    _validate_results_rows(field_sheet)


def lab_external_field_sheet_progress(sheet: FieldSheet) -> tuple[int, int]:
    """Sección 3 de la auditoría 2026-09-17: _field_sheet_progress (bandeja
    LAB, lab_field_sheets.py) recorre template_definition_json
    ["result_sections"] -- LAB EXTERNO usa ["groups"], una forma distinta,
    así que sin este cálculo dedicado toda hoja LAB EXTERNO aparecía 0/0 en
    la bandeja sin importar cuánto tuviera capturado.

    required_total = filas declaradas en todas las tablas de todos los
    grupos (suma de table.row_count). completed_total = filas con captura
    significativa: al menos una de las columnas declaradas de ESA tabla
    con un valor no vacío -- mismo criterio de "algo capturado" que ya usa
    _has_capture_value/_validate_results_rows, no exige llenar todas las
    columnas de la fila."""
    from app.services.lab_field_sheets import _has_capture_value

    rows_by_key = {(row.section_key, row.row_number): row for row in sheet.results_rows}
    completed_total = 0
    required_total = 0
    for group in (sheet.template_definition_json or {}).get("groups") or []:
        for table in group.get("tables") or []:
            column_keys = [column.get("key") for column in (table.get("columns") or [])]
            row_count = int(table.get("row_count") or 0)
            required_total += row_count
            for row_number in range(1, row_count + 1):
                row = rows_by_key.get((table.get("id"), row_number))
                row_data = row.row_data if row is not None else None
                if row_data and any(_has_capture_value(row_data.get(key)) for key in column_keys):
                    completed_total += 1
    return min(completed_total, required_total), required_total


def _reconcile_lab_external_rows(sheet: FieldSheet, groups: list[LabExternalGroupWrite]) -> None:
    """Sincroniza FieldSheetResult con la estructura recién guardada: crea
    filas nuevas (row_data={}) para tablas/filas que no existían, y suelta
    (cascade delete-orphan, mismo patrón que _apply_results_updates) las que
    ya no corresponden a ninguna tabla/fila declarada -- nunca conserva una
    fila huérfana de una tabla eliminada."""
    wanted_keys = {
        (table.id, row_number)
        for group in groups
        for table in group.tables
        for row_number in range(1, table.row_count + 1)
    }
    existing_by_key = {(row.section_key, row.row_number): row for row in sheet.results_rows}
    kept = [row for key, row in existing_by_key.items() if key in wanted_keys]
    kept_keys = set(existing_by_key.keys()) & wanted_keys
    for key in wanted_keys - kept_keys:
        kept.append(FieldSheetResult(section_key=key[0], row_number=key[1], row_data={}))
    sheet.results_rows = kept


def apply_lab_external_structure(
    db: Session,
    work_order_id: int,
    equipment_id: int,
    payload: LabExternalStructureWrite,
    user: User,
    *,
    external: bool,
) -> FieldSheetRead:
    # Import perezoso: evita un ciclo de import entre este módulo y
    # lab_field_sheets.py (que a su vez importa de aquí), mismo patrón ya
    # usado en el resto del servicio LAB (ver freeze_final_field_sheet_pdf/
    # _complete_lab_field_sheet_uncommitted).
    from app.services.lab_field_sheets import _ensure_capture_allowed, get_lab_equipment, read_lab_field_sheet

    equipment = get_lab_equipment(db, work_order_id, equipment_id, lock=True)
    _ensure_capture_allowed(equipment, external=external)
    sheet = equipment.field_sheet
    if sheet is None or not sheet.is_active:
        raise HTTPException(status_code=404, detail="Equipo sin hoja de campo LAB EXTERNO")
    if sheet.template_key != LAB_EXTERNAL_TEMPLATE_KEY:
        raise HTTPException(
            status_code=409, detail="La hoja de campo de este equipo no es LAB EXTERNO"
        )
    if sheet.status not in EDITABLE_STATUSES:
        raise HTTPException(
            status_code=409,
            detail="La estructura sólo puede editarse mientras la revisión esté en borrador/captura",
        )

    previous_group_ids = [item.get("id") for item in (sheet.template_definition_json or {}).get("groups", [])]
    definition = dict(sheet.template_definition_json or bootstrap_lab_external_definition())
    definition["groups"] = [group.model_dump() for group in payload.groups]
    sheet.template_definition_json = definition

    _reconcile_lab_external_rows(sheet, payload.groups)

    write_audit_log(
        db,
        action="lab_field_sheet.lab_externo_structure_updated",
        entity="field_sheets",
        entity_id=sheet.id,
        user_id=user.id,
        previous_values={"group_ids": previous_group_ids},
        new_values={
            "group_ids": [group.id for group in payload.groups],
            "table_count": sum(len(group.tables) for group in payload.groups),
        },
    )
    db.commit()
    return read_lab_field_sheet(db, work_order_id, equipment_id)
