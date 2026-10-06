/**
 * Contexto activo de captura técnica dentro de una OT: qué equipo y qué
 * FieldSheet tiene abiertos el técnico. Los IDs son la identidad estable; el
 * draft (`values`) NO forma parte de este contexto -- el autosave sigue siendo
 * su única autoridad mientras el componente permanezca montado.
 */
export type ActiveFieldSheetContext = {
  equipmentId: number;
  /** null mientras el equipo aún no tiene hoja (selector de plantilla). */
  sheetId: number | null;
  /**
   * Hoja que ESTE componente acaba de crear/reemplazar (crear, LAB EXTERNO,
   * desbloquear, cambiar plantilla) y que ningún detalle de la OT ha
   * confirmado todavía. Mientras siga pendiente, un detalle que no la
   * menciona puede ser anterior a la operación local y no prueba nada.
   */
  pendingLocalSheetId?: number | null;
};

export type FieldSheetContextValidity =
  | 'valid'
  | 'confirmed'
  | 'equipment_removed'
  | 'sheet_replaced'
  | 'sheet_removed';

/**
 * Reconcilia el contexto activo contra el detalle vigente de la OT que envía
 * backend.
 *
 * - El equipo ya no pertenece a la OT -> 'equipment_removed'.
 * - El detalle apunta a la misma hoja -> 'confirmed' (cierra cualquier
 *   operación local pendiente).
 * - La hoja es la creada localmente y aún sin confirmar -> 'valid': el detalle
 *   puede ser anterior a esa operación (null o la hoja previa).
 * - En cualquier otro caso el detalle es autoritativo: otra hoja vigente ->
 *   'sheet_replaced'; ninguna (field_sheet_id null) -> 'sheet_removed'.
 */
export function validateFieldSheetContext(
  equipment: readonly { id: number; field_sheet_id: number | null }[],
  context: ActiveFieldSheetContext,
): FieldSheetContextValidity {
  const current = equipment.find((item) => item.id === context.equipmentId);
  if (!current) return 'equipment_removed';
  if (context.sheetId == null) return 'valid';
  if (current.field_sheet_id === context.sheetId) return 'confirmed';
  if (context.pendingLocalSheetId === context.sheetId) return 'valid';
  return current.field_sheet_id == null ? 'sheet_removed' : 'sheet_replaced';
}
