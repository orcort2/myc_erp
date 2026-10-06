import type { LabWorkOrderWorkflowMode } from '../types/lab-work-order';
import type { CreationGroupMode } from './lab-erp-calibration';

export function validGroupQuantity(value: string): number | null {
  const quantity = Number(value);
  return Number.isInteger(quantity) && quantity >= 1 && quantity <= 50 ? quantity : null;
}

/** Preserve surviving positions; new positions receive the current base mode. */
export function reconcileMemberWorkflowModes(
  current: readonly LabWorkOrderWorkflowMode[],
  quantity: number,
  baseMode: LabWorkOrderWorkflowMode,
): LabWorkOrderWorkflowMode[] {
  if (!Number.isInteger(quantity) || quantity < 1 || quantity > 50) return [];
  return Array.from({ length: quantity }, (_, index) => current[index] ?? baseMode);
}

/** Creation-only fields; external requests retain their historical payload. */
export function buildLabWorkflowCreationPayload(
  groupMode: CreationGroupMode,
  baseMode: LabWorkOrderWorkflowMode,
  quantityText: string,
  manual: boolean,
  memberModes: readonly LabWorkOrderWorkflowMode[],
): {
  workflow_mode: LabWorkOrderWorkflowMode;
  quantity?: number;
  member_workflow_modes?: LabWorkOrderWorkflowMode[];
} {
  if (groupMode === 'none') return { workflow_mode: baseMode };
  const quantity = validGroupQuantity(quantityText);
  if (quantity === null) throw new Error('La cantidad de OT debe ser un entero entre 1 y 50.');
  if (groupMode === 'direct' && manual) {
    if (memberModes.length !== quantity) throw new Error('Revisa la modalidad de cada OT.');
    return { workflow_mode: baseMode, quantity, member_workflow_modes: [...memberModes] };
  }
  return { workflow_mode: baseMode, quantity };
}
