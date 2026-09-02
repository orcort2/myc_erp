import type { LabWorkOrder } from '@/src/types/lab-work-order';

/** Cierre UX 2026-09: "Calibró" nunca es un TextInput libre -- se deriva del
 * firmante técnico ya persistido en la sesión de firma de la OT (auditoría
 * real), o "Pendiente" si esa sesión todavía no existe. "Revisó" y "Elaboró
 * informe" permanecen "Pendiente": el vertical LAB temporal no produce hoy
 * ninguna etapa de revisión de calidad -- no se simula un flujo que no
 * existe (mismo criterio ya aplicado por el backend en
 * _resolve_field_sheet_signatures, ver field_sheet_pdfs.py). */
export const PENDING_SIGNATURE_LABEL = 'Pendiente';

export function resolveCalibradoPor(workOrder: Pick<LabWorkOrder, 'signature_session'>): string {
  const technician = workOrder.signature_session?.signatures.find(
    (item) => item.signature_type === 'technician',
  );
  return technician?.signer_name || PENDING_SIGNATURE_LABEL;
}
