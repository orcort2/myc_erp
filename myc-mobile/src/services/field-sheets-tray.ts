/**
 * Fase 6: Mobile presenta la proyección ya clasificada por backend. No
 * reconstruye ownership, revisión vigente, cliente documental ni progreso.
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

export type LabFieldSheetTrayApiItem = {
  work_order_id: number;
  work_order_folio: number;
  work_order_status: string;
  equipment_id: number;
  instrument: string;
  brand: string;
  model: string | null;
  service_type: string | null;
  certificate_folio: string | null;
  documentary_client_display: string;
  field_sheet_id: number | null;
  field_sheet_status: string | null;
  template_key: string | null;
  template_name: string | null;
  revision_number: number | null;
  is_current: boolean | null;
  progress_completed: number;
  progress_required: number;
  bucket: FieldSheetTrayBucket;
};

export type LabFieldSheetTrayApiPage = {
  items: LabFieldSheetTrayApiItem[];
  offset: number;
  limit: number;
  total: number;
};

export function trayEntryFromApi(item: LabFieldSheetTrayApiItem): FieldSheetTrayEntry {
  return {
    workOrderId: item.work_order_id,
    workOrderFolio: item.work_order_folio,
    equipmentId: item.equipment_id,
    instrument: item.instrument,
    certificateFolio: item.certificate_folio,
    documentaryClient: item.documentary_client_display,
    fieldSheetId: item.field_sheet_id,
    fieldSheetStatus: item.field_sheet_status,
    bucket: item.bucket,
    templateKey: item.template_key,
    templateName: item.template_name,
    progress: { completed: item.progress_completed, total: item.progress_required },
  };
}

export type TrayBuckets = Record<FieldSheetTrayBucket, FieldSheetTrayEntry[]>;

export function groupTrayEntriesByBucket(entries: FieldSheetTrayEntry[]): TrayBuckets {
  return {
    pending: entries.filter((entry) => entry.bucket === 'pending'),
    in_progress: entries.filter((entry) => entry.bucket === 'in_progress'),
    completed: entries.filter((entry) => entry.bucket === 'completed'),
  };
}
