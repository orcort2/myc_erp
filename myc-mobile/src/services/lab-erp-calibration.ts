/**
 * Vínculo OPCIONAL de una OT LAB nueva con un ETS de calibración del ERP.
 *
 * Es distinto de `purchase_order` ("Orden de compra / cotización"), que sigue
 * siendo texto documental libre. El vínculo sólo se establece al crear una OT
 * individual o un grupo directo de staff MYC; nunca en la solicitud externa
 * de grupo ni al editar una OT existente (reemplazar/desvincular es
 * administrativo en el ERP).
 */

export type ErpCalibrationCandidate = {
  service_order_id: number;
  service_order_folio: string;
  quotation_id: number;
  quotation_folio: string;
  client_id: number;
  client_name: string;
  calibration_item_count: number;
  calibration_quantity: number;
  calibration_items: { service_name: string; quantity: number }[];
  active_lab_root_id: number | null;
  active_lab_root_folio: number | null;
  available: boolean;
};

export const ERP_CANDIDATE_MIN_CHARS = 2;
export const ERP_CANDIDATE_DEBOUNCE_MS = 300;
export const ERP_CANDIDATE_LIMIT = 20;
export const ERP_CANDIDATES_PATH = '/mobile/v1/technician/lab-work-orders/erp-calibration-candidates';

export function shouldSearchErpCandidates(term: string): boolean {
  return term.trim().length >= ERP_CANDIDATE_MIN_CHARS;
}

export function buildErpCandidateQuery(term: string): string {
  const params = new URLSearchParams();
  params.set('q', term.trim());
  params.set('limit', String(ERP_CANDIDATE_LIMIT));
  return params.toString();
}

export type CreationGroupMode = 'none' | 'request' | 'direct';

/** true sólo cuando el envío crea una OT individual o un grupo directo nuevo. */
export function canAttachErpLink(groupMode: CreationGroupMode, isEditingExisting: boolean): boolean {
  return !isEditingExisting && groupMode !== 'request';
}

/** Agrega `service_order_id` únicamente si hay selección y el envío lo admite. */
export function withErpLink<T extends Record<string, unknown>>(
  body: T,
  selection: ErpCalibrationCandidate | null,
  groupMode: CreationGroupMode,
  isEditingExisting: boolean,
): T & { service_order_id?: number } {
  if (!selection || !canAttachErpLink(groupMode, isEditingExisting)) return body;
  return { ...body, service_order_id: selection.service_order_id };
}

export function describeErpCandidate(candidate: ErpCalibrationCandidate): {
  quotation: string;
  serviceOrder: string;
  client: string;
  detail: string;
} {
  const items = candidate.calibration_quantity === 1 ? '1 equipo' : `${candidate.calibration_quantity} equipos`;
  return {
    quotation: `Cotización ${candidate.quotation_folio}`,
    serviceOrder: `ETS ${candidate.service_order_folio}`,
    client: candidate.client_name,
    detail: candidate.available
      ? `Calibración · ${items}`
      : `Ya vinculada a OT ${candidate.active_lab_root_folio ?? candidate.active_lab_root_id ?? ''}`.trim(),
  };
}

function normalizeClientName(value: string): string {
  return value
    .normalize('NFD')
    .replace(/[\u0300-\u036f]/g, '')
    .replace(/\s+/g, ' ')
    .trim()
    .toLowerCase();
}

/**
 * Advertencia NO bloqueante: el cliente capturado en la OT LAB difiere del
 * cliente del ETS elegido. No hay FK ni sobrescritura de client_name; la
 * validación fuerte cliente/equipo/documento corresponde a la fase de
 * ingestión documental.
 */
export function erpClientMismatchWarning(
  labClientName: string,
  selection: ErpCalibrationCandidate | null,
): string | null {
  if (!selection || !labClientName.trim()) return null;
  if (normalizeClientName(labClientName) === normalizeClientName(selection.client_name)) return null;
  return `El cliente de esta OT (“${labClientName.trim()}”) es distinto al del ETS seleccionado (“${selection.client_name}”). Revísalo antes de crear; no se cambiará automáticamente.`;
}
