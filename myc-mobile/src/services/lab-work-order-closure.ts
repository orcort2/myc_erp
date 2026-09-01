import type { LabWorkOrder } from '@/src/types/lab-work-order';

export type LabClosureScope = 'group' | 'individual';

export type LabClosureOptions = {
  activeCohortSize: number;
  canFinalizeGroup: boolean;
  canFinalizeIndividual: boolean;
  groupMissingEquipmentCount: number;
  groupParticipantCount: number;
  hasHistoricalSiblings: boolean;
  /**
   * True only when there is currently more than one open, unsigned OT sharing
   * this root group (groupParticipantCount already counts the OT itself, so
   * a lone OT with no live siblings evaluates to 1, not 0). "Solicitar
   * excepción de cierre parcial" only makes sense when part of a real
   * multi-OT cohort is being left open — never for a single OT closing alone,
   * even if it has fully-historical (already completed/cancelled) siblings.
   */
  hasEligiblePartialCloseCohort: boolean;
  /**
   * True once a signature session exists for this OT and it covers no other
   * OT (or the session id isn't set yet). Drives whether the post-signature
   * screen should show the short single-OT copy ("Firma completada") instead
   * of the group-cohort copy ("OT individual firmada" / "grupo histórico...").
   */
  isSingleOtSignatureSession: boolean;
};

export function labClosureContextId(
  workOrder: Pick<LabWorkOrder, 'id' | 'root_work_order_id'>,
  scope: LabClosureScope,
): number {
  return scope === 'individual' ? workOrder.id : workOrder.root_work_order_id;
}

const TERMINAL_CLOSURE_STATUSES = new Set(['completed', 'partially_closed', 'cancelled']);

export function deriveLabClosureOptions(
  workOrder: LabWorkOrder,
): LabClosureOptions {
  // Candidatas a FIRMAR recepción: siguen en draft (Fase 3 firma la
  // recepción, no el cierre técnico) y sin sesión de firma todavía.
  const groupCandidates = workOrder.related_work_orders.filter(
    (item) => item.status === 'draft' && item.signature_session_id == null,
  );
  const groupMissingEquipmentCount = groupCandidates.filter(
    (item) => item.equipment_count === 0,
  ).length;
  // Candidatas a la EXCEPCIÓN DE CIERRE PARCIAL: cualquier OT del grupo que
  // todavía no llegó a un estado terminal -- ya no sólo "draft", porque tras
  // Fase 3 la recepción se firma antes de capturar, así que una OT abierta
  // en el momento del cierre normalmente está received_signed/in_progress/
  // ready_to_close, no draft.
  const openCandidates = workOrder.related_work_orders.filter(
    (item) => !TERMINAL_CLOSURE_STATUSES.has(item.status),
  );
  const activeCohortSize = workOrder.signature_session_id == null
    ? 0
    : workOrder.related_work_orders.filter(
      (item) => item.status !== 'completed'
        && item.signature_session_id === workOrder.signature_session_id,
    ).length;

  return {
    activeCohortSize,
    canFinalizeGroup: workOrder.status === 'draft'
      && groupCandidates.length > 0
      && groupMissingEquipmentCount === 0,
    canFinalizeIndividual: workOrder.status === 'draft'
      && workOrder.equipment.length > 0,
    groupMissingEquipmentCount,
    groupParticipantCount: groupCandidates.length,
    hasHistoricalSiblings: workOrder.related_work_orders.length > 1,
    hasEligiblePartialCloseCohort: openCandidates.length > 1,
    isSingleOtSignatureSession: activeCohortSize <= 1,
  };
}
