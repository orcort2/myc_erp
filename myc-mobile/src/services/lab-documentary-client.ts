import type { LabEquipment, LabWorkOrder } from '@/src/types/lab-work-order';

/**
 * Fase 4: espejo de sólo lectura de resolve_equipment_certificate_client
 * (backend/app/services/lab_work_orders.py). El cliente documental de un
 * equipo se decide UNA vez, en recepción (draft), vía
 * PATCH .../equipment/{id}/certificate-client -- Mesa Técnica nunca vuelve a
 * pedirlo ni a recalcularlo, sólo lo muestra tal cual quedó congelado. En
 * modo 'order' (default) es el cliente receptor de la OT; en modo
 * 'different' es el snapshot propio del equipo, que nunca se resincroniza
 * desde el catálogo LabClient.
 */
export function resolveDocumentaryClientLabel(
  equipment: Pick<LabEquipment, 'certificate_client_mode' | 'final_client_company_snapshot'>,
  workOrder: Pick<LabWorkOrder, 'client_name'>,
): string {
  if (equipment.certificate_client_mode === 'different') {
    return equipment.final_client_company_snapshot ?? '';
  }
  return workOrder.client_name;
}
