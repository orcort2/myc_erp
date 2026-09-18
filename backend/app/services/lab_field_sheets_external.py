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

from fastapi import HTTPException
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
    """Sección "INTEGRACIÓN LINKED" del encargo: LAB EXTERNO sólo aplica a
    equipo con servicio Vinculado -- nunca a acreditado/trazable.

    Corrección 2026-09-17: la regla NO aplica en el sentido inverso.
    Vinculado usando una plantilla LAB interna (p.ej. "general") es un
    flujo preexistente y probado (ver test_signing_and_field_sheet_allow_
    linked_without_company, test_external_linked_sheet_can_start_pending_
    but_close_stays_internal, entre otros) -- forzarlo aquí habría sido
    redefinir ese contrato sin que el encargo lo pidiera. Lo que el
    encargo sí pide ("no pedir plantilla de laboratorio interno") es una
    decisión de UX en Mobile (ofrecer/crear LAB EXTERNO de forma natural
    para un equipo linked), no una prohibición backend de la combinación
    contraria."""
    is_linked = equipment.service_type == "linked"
    is_lab_external = template_key == LAB_EXTERNAL_TEMPLATE_KEY
    if is_lab_external and not is_linked:
        raise HTTPException(
            status_code=409,
            detail="LAB EXTERNO sólo aplica a equipo con servicio Vinculado",
        )


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
