import type {
  TechnicalReportCaptureUpdate,
  TechnicalReportEvidence,
  TechnicalReportEvidenceType,
  TechnicalReportRead,
} from '@/src/types/technical-report';
import { buildEvidenceFormData, type PreparedEvidenceImage } from '@/src/services/technical-report-media';
import { technicalReportPath } from '@/src/services/technical-report';

type Request = <T>(path: string, init?: RequestInit) => Promise<T>;

export type TechnicalReportApi = {
  load(): Promise<TechnicalReportRead>;
  saveCapture(update: TechnicalReportCaptureUpdate): Promise<TechnicalReportRead>;
  uploadEvidence(image: PreparedEvidenceImage, evidenceType: TechnicalReportEvidenceType): Promise<TechnicalReportEvidence>;
  deleteEvidence(evidenceId: number): Promise<TechnicalReportRead>;
  /** Transición explícita in_progress -> ready_for_signatures (el autosave nunca finaliza). */
  confirmCapture(): Promise<TechnicalReportRead>;
  /** Fuente autenticada para previsualizar una evidencia ya subida. */
  evidenceImageSource(evidenceId: number): { uri: string; headers: Record<string, string> };
};

/** Cliente del TechnicalReport vigente de un equipo. Reutiliza el `request`
 * autenticado de la pantalla (mismo refresh de sesión, mismos errores). */
export function createTechnicalReportApi(deps: {
  request: Request;
  workOrderId: number;
  equipmentId: number;
  apiUrl(path: string): string;
  accessToken: string;
}): TechnicalReportApi {
  const base = technicalReportPath(deps.workOrderId, deps.equipmentId);
  return {
    load: () => deps.request<TechnicalReportRead>(base),
    saveCapture: (update) => deps.request<TechnicalReportRead>(base, { method: 'PATCH', body: JSON.stringify(update) }),
    uploadEvidence: (image, evidenceType) => deps.request<TechnicalReportEvidence>(
      `${base}/evidence`,
      { method: 'POST', body: buildEvidenceFormData(image, evidenceType) },
    ),
    confirmCapture: () => deps.request<TechnicalReportRead>(`${base}/confirm-capture`, { method: 'POST' }),
    deleteEvidence: (evidenceId) => deps.request<TechnicalReportRead>(`${base}/evidence/${evidenceId}`, { method: 'DELETE' }),
    evidenceImageSource: (evidenceId) => ({
      uri: deps.apiUrl(`${base}/evidence/${evidenceId}/file`),
      headers: { Authorization: `Bearer ${deps.accessToken}` },
    }),
  };
}
