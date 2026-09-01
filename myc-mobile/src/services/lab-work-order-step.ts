import type { LabWorkOrderStatus } from '@/src/types/lab-work-order';

export type Step = 'general' | 'capture' | 'technical' | 'review' | 'signatures' | 'completed';

export const TERMINAL_STATUSES = new Set<LabWorkOrderStatus>(['completed', 'partially_closed', 'cancelled']);

export type StatusPresentation = { label: string; color: string };

const STATUS_PRESENTATION: Partial<Record<LabWorkOrderStatus, StatusPresentation>> = {
  completed: { label: 'CERRADA', color: '#16834b' },
  partially_closed: { label: 'CERRADA PARCIALMENTE', color: '#d87913' },
  cancelled: { label: 'CANCELADA', color: '#c73636' },
  // Legacy: OT firmada bajo el flujo anterior a Fase 3 (recepción y cierre
  // técnico en un solo paso). Se conserva para no falsear historicidad.
  ready_for_signatures: { label: 'EN PROCESO', color: '#d7a51b' },
  draft: { label: 'EN PROCESO', color: '#d7a51b' },
  received_signed: { label: 'RECEPCIÓN FIRMADA', color: '#2f7fd1' },
  in_progress: { label: 'EN CAPTURA', color: '#2f7fd1' },
  ready_to_close: { label: 'LISTA PARA CIERRE', color: '#7a52c9' },
};

export function statusPresentation(status: string): StatusPresentation {
  return STATUS_PRESENTATION[status as LabWorkOrderStatus] ?? { label: status.toUpperCase(), color: '#d7a51b' };
}

/**
 * Fase 3: dado el status vigente de la OT, a qué paso de la pantalla debe
 * llevar (al abrir un deep-link, al reconciliar un evento realtime, o al
 * cambiar de OT relacionada). Único punto de esta lógica -- antes estaba
 * triplicada e inconsistente entre sí en work-orders.tsx.
 *
 * La firma de recepción ahora ocurre ANTES de la captura técnica: draft
 * lleva a configurar equipos ('capture'); una vez firmada la recepción
 * (received_signed/in_progress), la captura técnica es el destino natural
 * ('technical'); ready_to_close lleva directo a confirmar cierre ('review'),
 * sin volver a pedir firma. 'ready_for_signatures' es legacy (flujo anterior
 * a esta fase, recepción y cierre firmados juntos) y sigue aterrizando en
 * 'signatures', que sabe presentar esa pantalla histórica.
 */
export function inferStepForStatus(status: LabWorkOrderStatus | string): Step {
  if (TERMINAL_STATUSES.has(status as LabWorkOrderStatus)) return 'completed';
  if (status === 'ready_for_signatures') return 'signatures';
  if (status === 'ready_to_close') return 'review';
  if (status === 'received_signed' || status === 'in_progress') return 'technical';
  return 'capture';
}

/**
 * Fase 5: al reconciliar un evento realtime o reabrir una OT (deep link),
 * work-orders.tsx evita interrumpir una firma en curso del mismo cohorte
 * conservando el paso 'signatures' aunque llegue una actualización de
 * status. Pero eso nunca puede sustituir un status terminal ya confirmado
 * por backend (completed/partially_closed/cancelled) -- si el cohorte ya
 * cerró (p.ej. otro dispositivo/sesión lo cerró), el paso debe reflejar
 * 'completed' de inmediato, no quedarse mostrando una pantalla de firma
 * para una OT que el backend ya considera cerrada.
 */
export function resolveStepAfterStatusUpdate(
  currentStep: Step,
  sameSignatureCohort: boolean,
  nextStatus: LabWorkOrderStatus | string,
): Step {
  const preserveSignatures = sameSignatureCohort
    && currentStep === 'signatures'
    && !TERMINAL_STATUSES.has(nextStatus as LabWorkOrderStatus);
  return preserveSignatures ? currentStep : inferStepForStatus(nextStatus);
}

/**
 * Fase 3: la recepción (equipo, cliente documental, servicio, cliente
 * receptor) sólo es editable mientras la OT sigue en 'draft' -- una vez
 * firmada (received_signed en adelante) queda de sólo lectura en Mobile,
 * reflejando exactamente el mismo corte que ya exige el backend
 * (_ensure_members_editable en lab_work_orders.py). No es una gate extra:
 * es la MISMA condición que ya gobernaba `editable` antes de esta fase --
 * se nombra explícitamente aquí para que sea reusable y comprobable.
 */
export function isReceptionEditable(status: LabWorkOrderStatus | string): boolean {
  return status === 'draft';
}

/**
 * Contexto breve del modal. Durante la firma inicial el lenguaje debe ser de
 * recepción: en Fase 3 todavía no existe un cierre técnico que confirmar.
 */
export function flowContextLabel(
  step: Step,
  status: LabWorkOrderStatus | string | undefined,
): string {
  if (step === 'signatures' && status === 'draft') return 'Revisión y firma de recepción';
  if (step === 'technical' && (status === 'received_signed' || status === 'in_progress')) {
    return 'Captura técnica';
  }
  if (step === 'review' || status === 'ready_to_close') return 'Cierre técnico';
  return 'Grupo histórico';
}
