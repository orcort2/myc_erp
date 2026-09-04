import type { LabEquipment, LabWorkOrderWorkflowMode } from '@/src/types/lab-work-order';

// Copia de UX para el selector de modalidad al crear una OT LAB (nunca se
// muestran los nombres internos "group"/"equipment_by_equipment" al usuario).
export const WORKFLOW_MODE_OPTIONS: {
  value: LabWorkOrderWorkflowMode;
  title: string;
  description: string;
}[] = [
  {
    value: 'equipment_by_equipment',
    title: 'Equipo por equipo',
    description: 'Registra y captura la Hoja de Campo de cada equipo antes de continuar con el siguiente.',
  },
  {
    value: 'group',
    title: 'Grupo de equipos',
    description: 'Registra primero todos los equipos y continúa después con recepción y captura.',
  },
];

export type EquipmentByEquipmentAction = 'select_sheet' | 'continue_capture' | 'ready';

export type EquipmentByEquipmentActionDescriptor = {
  action: EquipmentByEquipmentAction;
  label: string;
};

/**
 * Reconstruye el estado de un equipo EXCLUSIVAMENTE desde lo que backend ya
 * proyecta en LabEquipment (field_sheet_id/field_sheet_status) -- nunca
 * desde un evento efímero de "acabo de guardar este equipo". Debe funcionar
 * igual inmediatamente después de crear el equipo, tras refresh, tras cerrar
 * y reabrir la app, y para equipos que ya existían antes de que la OT
 * cambiara a este workflow_mode.
 */
export function describeEquipmentByEquipmentAction(
  equipment: Pick<LabEquipment, 'field_sheet_id' | 'field_sheet_status'>,
): EquipmentByEquipmentActionDescriptor {
  if (!equipment.field_sheet_id) {
    return { action: 'select_sheet', label: 'Seleccionar Hoja de Campo' };
  }
  if (equipment.field_sheet_status === 'completed') {
    return { action: 'ready', label: 'Hoja lista' };
  }
  return { action: 'continue_capture', label: 'Continuar captura' };
}

export type EquipmentByEquipmentBlocker = {
  work_order_id: number;
  work_order_folio: number;
  equipment_id: number | null;
  equipment_position: number | null;
  equipment: string | null;
  reason: string;
  missing_fields?: string[] | null;
};

export type EquipmentByEquipmentPrevalidation = {
  ready: boolean;
  blockers: EquipmentByEquipmentBlocker[];
};

/** "Equipo 2 — falta resultado final." / "La OT no tiene equipos activos." */
export function formatEquipmentByEquipmentBlocker(blocker: EquipmentByEquipmentBlocker): string {
  const reason = blocker.reason.endsWith('.') ? blocker.reason : `${blocker.reason}.`;
  if (blocker.equipment_position == null) return reason;
  return `Equipo ${blocker.equipment_position} — ${reason}`;
}

export function canRegisterAnotherEquipmentByEquipmentUnit(equipmentCount: number): boolean {
  return equipmentCount < 10;
}
