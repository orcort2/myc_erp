import { resolveDocumentaryClientLabel } from '@/src/services/lab-documentary-client';
import type { LabFieldSheet, LabWorkOrder } from '@/src/types/lab-work-order';

/**
 * Fase 6: bandeja Mobile de Hojas de Campo -- reutiliza el detalle de OT LAB
 * ya existente (equipment[] con field_sheet_id/field_sheet_status), no un
 * endpoint ni un agregado productivo nuevo. "pending" sólo aplica a equipos
 * cuya OT ya admite captura técnica (received_signed/in_progress); un
 * equipo sin hoja en una OT todavía en draft no es "pendiente de hoja", es
 * "todavía en configuración de recepción" -- eso pertenece a Mesa Técnica /
 * la revisión de recepción, no a esta bandeja.
 */
export type FieldSheetTrayBucket = 'pending' | 'in_progress' | 'completed';

export type FieldSheetTrayEntry = {
  workOrderId: number;
  workOrderFolio: number;
  equipmentId: number;
  instrument: string;
  certificateFolio: string | null;
  documentaryClient: string;
  fieldSheetId: number | null;
  fieldSheetStatus: string | null;
  bucket: FieldSheetTrayBucket;
  // Enriquecidos aparte (ver enrichTrayEntryWithFieldSheet) una vez que se
  // conoce el detalle de la FieldSheet -- null hasta entonces, nunca
  // inventados.
  templateKey: string | null;
  templateName: string | null;
  progress: { completed: number; total: number } | null;
};

function classifyBucket(fieldSheetStatus: string | null, captureReady: boolean): FieldSheetTrayBucket | null {
  if (fieldSheetStatus === 'completed') return 'completed';
  if (fieldSheetStatus === 'draft' || fieldSheetStatus === 'in_progress') return 'in_progress';
  if (fieldSheetStatus == null && captureReady) return 'pending';
  return null;
}

export function buildFieldSheetTrayEntries(workOrders: LabWorkOrder[]): FieldSheetTrayEntry[] {
  const entries: FieldSheetTrayEntry[] = [];
  for (const order of workOrders) {
    const captureReady = order.status === 'received_signed' || order.status === 'in_progress';
    for (const equipment of order.equipment) {
      const bucket = classifyBucket(equipment.field_sheet_status, captureReady);
      if (bucket === null) continue;
      entries.push({
        workOrderId: order.id,
        workOrderFolio: order.folio,
        equipmentId: equipment.id,
        instrument: equipment.instrument,
        certificateFolio: equipment.certificate_folio,
        documentaryClient: resolveDocumentaryClientLabel(equipment, order),
        fieldSheetId: equipment.field_sheet_id,
        fieldSheetStatus: equipment.field_sheet_status,
        bucket,
        templateKey: null,
        templateName: null,
        progress: null,
      });
    }
  }
  return entries;
}

export type TrayBuckets = Record<FieldSheetTrayBucket, FieldSheetTrayEntry[]>;

export function groupTrayEntriesByBucket(entries: FieldSheetTrayEntry[]): TrayBuckets {
  return {
    pending: entries.filter((entry) => entry.bucket === 'pending'),
    in_progress: entries.filter((entry) => entry.bucket === 'in_progress'),
    completed: entries.filter((entry) => entry.bucket === 'completed'),
  };
}

/** Fusiona el detalle real de una FieldSheet (plantilla, progreso) en su
 * entrada de bandeja -- sólo se llama una vez que el detalle ya se pidió
 * (lazy, por entrada), nunca se calcula sin datos reales. */
export function enrichTrayEntryWithFieldSheet(
  entry: FieldSheetTrayEntry,
  sheet: Pick<LabFieldSheet, 'template_key' | 'results_rows'>,
  templateName: string | null,
  progress: { completed: number; total: number },
): FieldSheetTrayEntry {
  return {
    ...entry,
    templateKey: sheet.template_key,
    templateName,
    progress,
  };
}
