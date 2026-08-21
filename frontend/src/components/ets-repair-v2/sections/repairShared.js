/**
 * Utilidades compartidas entre las secciones del workflow de Reparación V2.
 * Ninguna regla de negocio vive aquí: solo formateo/lectura de datos que el
 * backend ya calculó (board/execution), y helpers de UI puramente locales.
 */

import { hasPermission } from '../../../utils/accessControl.js';

export const REPAIR_STATUS_LABELS = {
  pending_arrival: 'Pendiente de arribo',
  pending_assignment: 'Pendiente de asignación',
  assigned: 'Asignado',
  in_evaluation: 'En evaluación',
  in_repair: 'En reparación',
  testing: 'En pruebas',
  technically_completed: 'Cierre técnico',
  equipment_not_suitable: 'Equipo no apto',
  pending_release: 'Pendiente de liberación',
  closed: 'Cerrado',
  cancelled: 'Cancelado',
};

export const SEVERITY_LABELS = {
  minor: 'Menor',
  moderate: 'Moderada',
  major: 'Mayor',
  critical: 'Crítica',
};

export const REPAIRABILITY_LABELS = {
  repairable: 'Reparable',
  conditionally_repairable: 'Reparable con condiciones',
  not_repairable: 'No reparable',
  undetermined: 'Por determinar',
};

export const PAUSE_TYPE_LABELS = {
  spare_part: 'Refacción',
  authorization: 'Autorización',
  client_decision: 'Decisión del cliente',
  administrative_investigation: 'Investigación administrativa',
  warehouse: 'Almacén',
};

export const TEST_RESULT_LABELS = {
  pass: 'Aprobada',
  fail: 'Fallida',
  inconclusive: 'No concluyente',
};

export const INTERVENTION_OUTCOME_LABELS = {
  effective: 'Efectiva',
  partial: 'Parcial',
  ineffective: 'No efectiva',
};

export const CLIENT_DECISION_LABELS = {
  acknowledged: 'Enterado',
  accepted: 'Aceptado',
  rejected_additional_work: 'No procede con trabajo adicional',
};

export const REMOVED_COMPONENT_DISPOSITION_LABELS = {
  return_to_client: 'Se regresa al cliente',
  client_authorized_disposal: 'Disposición autorizada por el cliente',
};


export function safeArray(value) {
  return Array.isArray(value) ? value : [];
}


export function safeText(value, fallback = '-') {
  if (value === undefined || value === null || value === '') {
    return fallback;
  }

  return value;
}


export function formatDateTime(value) {
  if (!value) {
    return '-';
  }

  const parsed = new Date(value);

  if (Number.isNaN(parsed.getTime())) {
    return value;
  }

  return parsed.toLocaleString('es-MX', {
    dateStyle: 'medium',
    timeStyle: 'short',
  });
}


export function getUserDisplayName(users, userId) {
  if (!userId) {
    return 'Sin asignar';
  }

  const found = safeArray(users).find(
    (candidate) => Number(candidate?.id) === Number(userId),
  );

  return (
    found?.full_name ||
    found?.name ||
    found?.email ||
    `Usuario #${userId}`
  );
}


/**
 * El backend (_require_assigned_technician) exige coincidencia EXACTA entre
 * el técnico asignado a la ejecución y el actor autenticado para operar
 * diagnóstico/dictamen/intervenciones/pausas/pruebas. No basta el permiso de
 * rol: replicamos aquí la misma comparación solo para decidir qué controles
 * mostrar habilitados, nunca para autorizar nada por cuenta propia.
 */
export function isAssignedTechnician(execution, user) {
  return Boolean(
    execution?.technician_id &&
    user?.id &&
    Number(execution.technician_id) === Number(user.id),
  );
}


/**
 * El backend exige, en ese orden, permiso de rol
 * ('service_orders.repair.execute') Y coincidencia exacta de técnico
 * asignado para diagnóstico/dictamen/intervenciones/pausas/pruebas. Ambas
 * condiciones son necesarias; ninguna sustituye a la otra.
 */
export function canExecuteRepair(execution, user) {
  return (
    hasPermission(user, 'service_orders.repair.execute') &&
    isAssignedTechnician(execution, user)
  );
}


export function triggerBlobDownload(blob, filename) {
  const url = URL.createObjectURL(blob);

  const anchor = document.createElement('a');

  anchor.href = url;
  anchor.download = filename || 'reporte-reparacion.pdf';

  document.body.appendChild(anchor);
  anchor.click();
  document.body.removeChild(anchor);

  URL.revokeObjectURL(url);
}
