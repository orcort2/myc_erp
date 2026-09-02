/** Cierre UX 2026-09: "Guardar borrador" ya no se queda en modo edición --
 * pasa a modo consulta (sólo lectura) con una acción compacta "Editar" para
 * volver a habilitar los inputs. No es un estado backend nuevo: es UI local
 * sobre el mismo FieldSheet.status ya existente. Una hoja completed siempre
 * es de sólo lectura, independientemente de este modo (ver
 * captureIsAlwaysReadOnly). */
export type FieldSheetViewMode = 'edit' | 'view';

export function initialViewMode(): FieldSheetViewMode {
  return 'edit';
}

export function viewModeAfterDraftSaved(): FieldSheetViewMode {
  return 'view';
}

export function viewModeAfterEditRequested(): FieldSheetViewMode {
  return 'edit';
}

/** completed nunca vuelve a edición aunque el usuario haya tocado "Editar"
 * antes de completar -- backend sigue siendo la autoridad (EDITABLE_STATUSES). */
export function captureIsAlwaysReadOnly(status: string): boolean {
  return status === 'completed';
}

export function isFieldSheetEditable(status: string, viewMode: FieldSheetViewMode): boolean {
  return !captureIsAlwaysReadOnly(status) && viewMode === 'edit';
}
