// Presentación de la ejecución técnica MYC Mobile dentro del ETS (web).
//
// MYC Mobile es la ÚNICA interfaz de escritura técnica. El ERP sólo consulta
// la proyección READ-ONLY y ejecuta acciones administrativas explícitas del
// dominio LAB; nunca edita resultados, identidad técnica, firmas ni folios.
// La autoridad de permisos y estados es el backend: aquí sólo se decide qué
// mostrar; el servidor vuelve a validar cada acción.
import { hasPermission } from '../../utils/accessControl.js';

export const LAB_WORK_ORDER_STATUS_LABELS = {
  draft: 'Borrador',
  received_signed: 'Recepción firmada',
  in_progress: 'En proceso',
  ready_for_signatures: 'Lista para firmas',
  ready_to_close: 'Lista para cierre',
  completed: 'Cerrada',
  partially_closed: 'Cierre parcial',
  cancelled: 'Cancelada',
};

export const LAB_FOLIO_STATUS_LABELS = {
  unassigned: 'Sin folio',
  pending: 'Pendiente',
  reserved: 'Reservado',
  authorized: 'Autorizado',
};

export const LAB_FIELD_SHEET_STATUS_LABELS = {
  draft: 'Borrador',
  in_progress: 'En captura',
  completed: 'Completada',
  under_review: 'En revisión',
  approved: 'Aprobada',
  returned_to_technician: 'Devuelta',
  rejected: 'Rechazada',
};

export const LAB_SERVICE_TYPE_LABELS = {
  accredited: 'Acreditado',
  traceable: 'Trazable',
  linked: 'Vinculado',
};

// Estados LAB en los que el dominio permite enviar una hoja completada a
// corrección (reapertura directa de la hoja o reapertura de la OT cerrada).
const OPEN_CORRECTABLE_STATUSES = new Set(['received_signed', 'in_progress', 'ready_to_close']);
const CLOSED_CORRECTABLE_STATUSES = new Set(['completed', 'partially_closed']);

export const CAPTURE_BLOCKER_LABELS = {
  LAB_LINK_REQUIRED: 'Vincula el servicio MYC Mobile del ETS',
  LAB_NO_ACTIVE_EQUIPMENT: 'El servicio MYC Mobile no tiene equipos activos',
  LAB_WORK_ORDER_NOT_FINAL: 'OT sin cierre técnico en MYC Mobile',
  LAB_CERTIFICATE_FOLIO_MISSING: 'Sin folio de certificado',
  LAB_CERTIFICATE_FOLIO_NOT_READY: 'Folio no reservado/autorizado',
  LAB_FIELD_SHEET_MISSING: 'Sin Hoja de Campo',
  LAB_FIELD_SHEET_NOT_COMPLETED: 'Hoja de Campo no completada',
  LAB_FINAL_PDF_MISSING: 'Sin PDF final congelado',
  LAB_FINAL_PDF_HASH_MISMATCH: 'PDF final alterado (SHA-256)',
};

export function getMobileExecutionPermissions(user) {
  return {
    // Mismo contrato del bridge: create Y update; Técnico puro no administra.
    canManageLink: hasPermission(user, 'service_orders.create') && hasPermission(user, 'service_orders.update'),
    canReadFieldSheets: hasPermission(user, 'field_sheets.read'),
    canRequestCorrection: hasPermission(user, 'work_orders.reopen'),
    canCancelWorkOrders: hasPermission(user, 'lab_work_orders.cancel'),
  };
}

export function correctionModeFor(workOrder, equipment) {
  const sheet = equipment?.field_sheet;
  if (!sheet || sheet.status !== 'completed') return null;
  if (OPEN_CORRECTABLE_STATUSES.has(workOrder?.status)) return 'field_sheet_reopen';
  if (CLOSED_CORRECTABLE_STATUSES.has(workOrder?.status)) return 'work_order_reopen';
  return null;
}

export function summarizeMobileExecution(projection) {
  const workOrders = Array.isArray(projection?.work_orders) ? projection.work_orders : [];
  const equipment = workOrders.flatMap((workOrder) => workOrder.equipment || []);
  return {
    workOrders: workOrders.length,
    equipment: equipment.length,
    completedSheets: equipment.filter((item) => item.field_sheet?.status === 'completed').length,
    finalPdfs: equipment.filter((item) => item.field_sheet?.has_final_pdf).length,
  };
}

export function captureStateLabel(summary) {
  return summary?.ready ? 'LISTA' : 'BLOQUEADA';
}

export function describeCaptureBlocker(blocker) {
  const label = CAPTURE_BLOCKER_LABELS[blocker?.code] || blocker?.message || blocker?.code || 'Bloqueo';
  const where = [
    blocker?.work_order_folio ? `OT ${blocker.work_order_folio}` : null,
    blocker?.position ? `Equipo ${blocker.position}` : null,
    blocker?.instrument || null,
    blocker?.certificate_folio || null,
  ].filter(Boolean).join(' · ');
  return where ? `${where}: ${label}` : label;
}

// Lectura de una hoja LAB: sólo pares etiqueta/valor, nunca inputs.
export function describeFieldSheetReadOnly(sheet) {
  if (!sheet) return [];
  return [
    ['Estado', LAB_FIELD_SHEET_STATUS_LABELS[sheet.status] || sheet.status],
    ['Revisión', sheet.revision_number],
    ['Plantilla', sheet.template_key],
    ['Fecha de calibración', sheet.calibration_date],
    ['Próxima calibración', sheet.next_calibration_date],
    ['Lugar de calibración', sheet.calibration_place],
    ['Calibró', sheet.calibrated_by],
    ['Revisó', sheet.reviewed_by],
    ['Unidades', sheet.units],
    ['Método', sheet.method],
    ['Condición inicial', sheet.initial_condition],
    ['Condición final', sheet.final_condition],
    ['Observaciones', sheet.observations],
    ['Resultados', sheet.results],
  ].filter(([, value]) => value !== null && value !== undefined && value !== '');
}
