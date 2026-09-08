import type { LabWorkOrder } from '@/src/types/lab-work-order';

/**
 * MOB-001: after a "preserve" reopening, the backend keeps
 * signature_session_id and sets signature_required = false so
 * complete_group() can run directly from `draft` without new signatures
 * (see backend/app/services/lab_work_orders.py::complete_group). The
 * technician only edits existing general/equipment data in that flow, so
 * the review step must skip straight to closing the group instead of
 * routing through the signature-capture step.
 *
 * All three fields are checked (not just signature_preserved) because a
 * structural change (added/removed equipment, extra OT) invalidates the
 * session server-side by clearing signature_session_id and flipping
 * signature_required back to true — at that point this must return false
 * and the normal "Continuar a firmas" flow takes over.
 *
 * Corrección 2026-09-08: antes también exigía `reopen_ticket_id != null`,
 * asumiendo que TODA reapertura pasa por un ticket. La reapertura directa
 * de Admin (`reopen_work_order_directly`, sin ticket artificial) preserva
 * la firma exactamente igual (signature_preserved/signature_required/
 * signature_session_id) pero deja `reopen_ticket_id` en null a propósito
 * -- con la condición vieja, esa reapertura nunca podía saltar la firma
 * aunque el backend sí la hubiera preservado. `signature_preserved` sólo
 * puede volverse true dentro de _reopen_closed_cohort (ver
 * operational_tickets.py), así que basta con los otros tres campos: ya
 * implican por sí solos que hubo una reapertura con firma preservada, sin
 * importar si fue mediada por ticket o directa.
 */
export function canSkipSignaturesAfterReopen(
  workOrder: Pick<
    LabWorkOrder,
    'signature_preserved' | 'signature_required' | 'signature_session_id'
  >,
): boolean {
  return (
    workOrder.signature_preserved === true
    && workOrder.signature_required === false
    && workOrder.signature_session_id != null
  );
}
