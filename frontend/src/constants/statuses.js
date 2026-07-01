export const serviceOrderStatusLabels = {
  scheduled: 'Agendada',
  confirmed: 'Confirmada',
  called: 'Llamado',
  in_progress: 'En proceso',
  technical_review: 'Revision tecnica',
  capture: 'Captura',
  quality_review: 'Revision calidad',
  pending_payment: 'Pendiente pago',
  released: 'Liberada',
  closed: 'Cerrada',
  cancelled: 'Cancelada'
};

export const equipmentStatusLabels = {
  registered: 'Registrado',
  realizing: 'Realizando',
  calibrated: 'Calibrado',
  labeled: 'Etiquetado',
  not_done: 'No realizado',
  cancelled: 'Cancelado'
};

export const fieldSheetStatusLabels = {
  draft: 'Borrador',
  in_progress: 'En proceso',
  completed: 'Completada',
  under_review: 'En revision',
  returned_to_technician: 'Devuelta a tecnico',
  approved: 'Aprobada',
  rejected: 'Rechazada',
  cancelled: 'Cancelada'
};

export const certificateStatusLabels = {
  draft: 'Borrador',
  expected: 'Esperado',
  field_sheet_ready: 'Hoja lista',
  capture_pending: 'Pendiente captura',
  capture_in_progress: 'En captura',
  ready_for_quality: 'Listo para calidad',
  generated: 'Generado',
  quality_review: 'En revision',
  quality_rejected: 'Rechazado calidad',
  correction_requested: 'Correccion solicitada',
  returned_to_technician: 'Devuelto a tecnico',
  quality_approved: 'Aprobado calidad',
  approved: 'Aprobado',
  pdf_pending: 'PDF pendiente',
  pdf_uploaded: 'PDF subido',
  released_to_client: 'Liberado al cliente',
  released: 'Liberado',
  cancelled: 'Cancelado',
  suspended: 'Suspendido'
};

export const quotationStatusLabels = {
  draft: 'Draft',
  sent: 'Sent',
  waiting: 'Waiting',
  accepted: 'Accepted',
  rejected: 'Rejected',
  expired: 'Expired',
  cancelled: 'Cancelled'
};

export const serviceOrderTransitions = {
  scheduled: new Set(['confirmed', 'cancelled']),
  confirmed: new Set(['called', 'in_progress', 'cancelled']),
  called: new Set(['in_progress', 'cancelled']),
  in_progress: new Set(['technical_review', 'capture', 'cancelled']),
  technical_review: new Set(['capture', 'cancelled']),
  capture: new Set(['quality_review', 'cancelled']),
  quality_review: new Set(['pending_payment', 'released', 'cancelled']),
  pending_payment: new Set(['released', 'cancelled']),
  released: new Set(['closed']),
  closed: new Set([]),
  cancelled: new Set([])
};

export const serviceOrderActions = [
  { key: 'confirm', nextStatus: 'confirmed', label: 'Confirmar' },
  { key: 'call', nextStatus: 'called', label: 'Llamar' },
  { key: 'start', nextStatus: 'in_progress', label: 'Iniciar' },
  { key: 'capture', nextStatus: 'capture', label: 'Captura' },
  { key: 'quality', nextStatus: 'quality_review', label: 'Calidad' },
  { key: 'pending-payment', nextStatus: 'pending_payment', label: 'Pendiente pago' },
  { key: 'release', nextStatus: 'released', label: 'Liberar' },
  { key: 'close', nextStatus: 'closed', label: 'Cerrar' }
];

export const equipmentTransitions = {
  registered: new Set(['realizing', 'not_done']),
  realizing: new Set(['calibrated', 'not_done']),
  calibrated: new Set(['labeled', 'not_done']),
  labeled: new Set([]),
  not_done: new Set([]),
  cancelled: new Set([])
};

export const equipmentActions = [
  { key: 'realizing', nextStatus: 'realizing', label: 'Realizando' },
  { key: 'calibrated', nextStatus: 'calibrated', label: 'Calibrado' },
  { key: 'labeled', nextStatus: 'labeled', label: 'Etiquetado' },
  { key: 'not-done', nextStatus: 'not_done', label: 'No realizado' }
];

export const certificateTypeLabels = {
  acreditado: 'Acreditado',
  trazable: 'Trazable'
};

export const certificateTabs = [
  { key: 'pending', label: 'Pendientes' },
  { key: 'capture', label: 'Captura' },
  { key: 'review', label: 'En revision' },
  { key: 'approved', label: 'Aprobados' },
  { key: 'pdf', label: 'PDF' },
  { key: 'released', label: 'Liberados' },
  { key: 'all', label: 'Todos' }
];

export const certificateActions = [
  { key: 'start-capture', nextStatus: 'capture_in_progress', label: 'Iniciar captura' },
  { key: 'send-to-quality', nextStatus: 'ready_for_quality', label: 'Enviar a calidad' },
  { key: 'quality-reject', nextStatus: 'quality_rejected', label: 'Rechazar calidad' },
  { key: 'return-to-technician', nextStatus: 'returned_to_technician', label: 'Regresar a tecnico' },
  { key: 'quality-approve', nextStatus: 'quality_approved', label: 'Aprobar calidad' },
  { key: 'release-to-client', nextStatus: 'released_to_client', label: 'Liberar cliente' },
  { key: 'suspend', nextStatus: 'suspended', label: 'Suspender' }
];

export const certificateTransitions = {
  draft: new Set(['expected', 'capture_pending', 'suspended']),
  expected: new Set(['field_sheet_ready', 'capture_pending', 'capture_in_progress', 'suspended']),
  field_sheet_ready: new Set(['capture_pending', 'capture_in_progress', 'suspended']),
  capture_pending: new Set(['capture_in_progress', 'ready_for_quality', 'suspended']),
  capture_in_progress: new Set(['ready_for_quality', 'quality_rejected', 'suspended']),
  ready_for_quality: new Set(['quality_review', 'quality_approved', 'quality_rejected', 'suspended']),
  generated: new Set(['quality_review', 'quality_rejected', 'suspended']),
  quality_review: new Set(['quality_approved', 'quality_rejected', 'suspended']),
  quality_rejected: new Set(['capture_in_progress', 'ready_for_quality', 'suspended']),
  returned_to_technician: new Set(['capture_in_progress', 'ready_for_quality', 'suspended']),
  correction_requested: new Set(['capture_in_progress', 'ready_for_quality', 'suspended']),
  quality_approved: new Set(['pdf_pending', 'pdf_uploaded', 'released_to_client', 'suspended']),
  approved: new Set(['pdf_pending', 'pdf_uploaded', 'released_to_client', 'suspended']),
  pdf_pending: new Set(['pdf_uploaded', 'released_to_client', 'suspended']),
  pdf_uploaded: new Set(['released_to_client', 'suspended']),
  released_to_client: new Set([]),
  released: new Set([]),
  cancelled: new Set([]),
  suspended: new Set(['capture_pending'])
};

export const certificateReadyFieldSheetStatuses = new Set(['completed', 'under_review', 'approved']);
export const certificateReadyEquipmentStatuses = new Set(['calibrated', 'labeled']);

export const qualityTabs = [
  { key: 'pending', label: 'Pendientes' },
  { key: 'review', label: 'En revision' },
  { key: 'approved', label: 'Aprobados' },
  { key: 'pdf', label: 'PDF' },
  { key: 'released', label: 'Liberados' },
  { key: 'suspended', label: 'Suspendidos' }
];

export const referenceStandardStatusLabels = {
  active: 'Activo',
  expired: 'Vencido',
  out_of_service: 'Fuera de servicio',
  inactive: 'Inactivo'
};

export const calibrationProcedureStatusLabels = {
  active: 'Activo',
  inactive: 'Inactivo',
  draft: 'Borrador',
  obsolete: 'Obsoleto'
};

export const quotationActions = [
  { key: 'send', label: 'Enviar', nextStatus: 'sent' },
  { key: 'waiting', label: 'Esperando respuesta', nextStatus: 'waiting' },
  { key: 'accept', label: 'Aceptar', nextStatus: 'accepted' },
  { key: 'reject', label: 'Rechazar', nextStatus: 'rejected' },
  { key: 'expire', label: 'Expirar', nextStatus: 'expired' },
  { key: 'cancel', label: 'Cancelar', nextStatus: 'cancelled' }
];

export const quotationTransitions = {
  draft: new Set(['sent', 'cancelled']),
  sent: new Set(['waiting', 'accepted', 'rejected', 'expired', 'cancelled']),
  waiting: new Set(['accepted', 'rejected', 'expired', 'cancelled']),
  accepted: new Set(),
  rejected: new Set(),
  expired: new Set(),
  cancelled: new Set()
};
