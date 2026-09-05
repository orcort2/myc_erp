import type { LabWorkOrder } from '@/src/types/lab-work-order';

type FolioDistributionRequest = <T>(path: string, init?: RequestInit) => Promise<T>;

export type LabCertificateFolioDistributionItem = {
  equipment_id: number;
  position: number;
  instrument: string;
  prefix: 'MYCA' | 'MYCT';
  folio: string | null;
};

/** GET .../certificate-folios/preview -- sólo lectura, nunca muta nada. Se
 * llama ANTES de ofrecer confirmar "Distribuir folios disponibles". */
export type LabCertificateFolioDistributionPreview = {
  work_order_id: number;
  work_order_folio: number;
  pending_accredited_count: number;
  pending_traceable_count: number;
  available_myca_count: number;
  available_myct_count: number;
  items: LabCertificateFolioDistributionItem[];
};

export type LabCertificateFolioDistributionResult = {
  work_order_id: number;
  assigned: LabCertificateFolioDistributionItem[];
};

export function getLabCertificateFolioDistributionPreview({
  request,
  workOrder,
}: {
  request: FolioDistributionRequest;
  workOrder: LabWorkOrder;
}): Promise<LabCertificateFolioDistributionPreview> {
  return request<LabCertificateFolioDistributionPreview>(
    `/mobile/v1/technician/lab-work-orders/${workOrder.id}/certificate-folios/preview`,
  );
}

/** Todo-o-nada por prefijo en el propio backend -- ver
 * isFolioDistributionSufficient: el caller nunca debe llamar esto si algún
 * prefijo pending excede lo disponible; el backend lo re-valida de todas
 * formas y responde 409 LAB_CERTIFICATE_FOLIOS_INSUFFICIENT si algo cambió
 * entre el preview y esta llamada. */
export function postLabCertificateFolioDistribution({
  request,
  workOrder,
}: {
  request: FolioDistributionRequest;
  workOrder: LabWorkOrder;
}): Promise<LabCertificateFolioDistributionResult> {
  return request<LabCertificateFolioDistributionResult>(
    `/mobile/v1/technician/lab-work-orders/${workOrder.id}/certificate-folios/distribute`,
    { method: 'POST' },
  );
}

/** Un solo lugar para decidir si el pool alcanza -- la UI nunca ofrece
 * confirmar si algún prefijo pending excede lo disponible. */
export function isFolioDistributionSufficient(preview: LabCertificateFolioDistributionPreview): boolean {
  return (
    preview.pending_accredited_count <= preview.available_myca_count
    && preview.pending_traceable_count <= preview.available_myct_count
  );
}

/** true cuando no hay nada que distribuir -- la UI oculta el botón de
 * confirmar y muestra un mensaje distinto al de "insuficiente". */
export function hasNoPendingCertificateFolios(preview: LabCertificateFolioDistributionPreview): boolean {
  return preview.pending_accredited_count === 0 && preview.pending_traceable_count === 0;
}
