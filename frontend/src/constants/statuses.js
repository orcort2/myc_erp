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
  approved: 'Aprobada',
  rejected: 'Rechazada',
  cancelled: 'Cancelada'
};

export const certificateStatusLabels = {
  draft: 'Borrador',
  generated: 'Generado',
  quality_review: 'En revision',
  approved: 'Aprobado',
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
  { key: 'review', label: 'En revision' },
  { key: 'approved', label: 'Aprobados' },
  { key: 'released', label: 'Liberados' },
  { key: 'all', label: 'Todos' }
];

export const certificateActions = [
  { key: 'generate', nextStatus: 'generated', label: 'Generar' },
  { key: 'quality', nextStatus: 'quality_review', label: 'Enviar a calidad' },
  { key: 'approve', nextStatus: 'approved', label: 'Aprobar' },
  { key: 'release', nextStatus: 'released', label: 'Liberar' },
  { key: 'suspend', nextStatus: 'suspended', label: 'Suspender' }
];

export const certificateTransitions = {
  draft: new Set(['generated', 'suspended']),
  generated: new Set(['quality_review', 'suspended']),
  quality_review: new Set(['approved', 'suspended']),
  approved: new Set(['released', 'suspended']),
  released: new Set([]),
  cancelled: new Set([]),
  suspended: new Set([])
};

export const certificateReadyFieldSheetStatuses = new Set(['completed', 'under_review', 'approved']);
export const certificateReadyEquipmentStatuses = new Set(['calibrated', 'labeled']);

export const qualityTabs = [
  { key: 'pending', label: 'Pendientes' },
  { key: 'review', label: 'En revision' },
  { key: 'approved', label: 'Aprobados' },
  { key: 'released', label: 'Liberados' },
  { key: 'suspended', label: 'Suspendidos' }
];

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

