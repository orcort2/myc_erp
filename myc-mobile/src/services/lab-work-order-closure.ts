import type { LabWorkOrder } from '@/src/types/lab-work-order';

export type LabClosureScope = 'group' | 'individual';

export type LabClosureOptions = {
  activeCohortSize: number;
  canFinalizeGroup: boolean;
  canFinalizeIndividual: boolean;
  groupMissingEquipmentCount: number;
  groupParticipantCount: number;
  hasHistoricalSiblings: boolean;
};

export function labClosureContextId(
  workOrder: Pick<LabWorkOrder, 'id' | 'root_work_order_id'>,
  scope: LabClosureScope,
): number {
  return scope === 'individual' ? workOrder.id : workOrder.root_work_order_id;
}

export function deriveLabClosureOptions(
  workOrder: LabWorkOrder,
): LabClosureOptions {
  const groupCandidates = workOrder.related_work_orders.filter(
    (item) => item.status === 'draft' && item.signature_session_id == null,
  );
  const groupMissingEquipmentCount = groupCandidates.filter(
    (item) => item.equipment_count === 0,
  ).length;
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
  };
}
