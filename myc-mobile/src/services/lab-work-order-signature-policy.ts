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
 * All four fields are checked (not just signature_preserved) because a
 * structural change (added/removed equipment, extra OT) invalidates the
 * session server-side by clearing signature_session_id and flipping
 * signature_required back to true — at that point this must return false
 * and the normal "Continuar a firmas" flow takes over.
 */
export function canSkipSignaturesAfterReopen(
  workOrder: Pick<
    LabWorkOrder,
    'reopen_ticket_id' | 'signature_preserved' | 'signature_required' | 'signature_session_id'
  >,
): boolean {
  return (
    workOrder.reopen_ticket_id != null
    && workOrder.signature_preserved === true
    && workOrder.signature_required === false
    && workOrder.signature_session_id != null
  );
}
