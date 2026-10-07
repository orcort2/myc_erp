import type { TechnicalReportStatus, TechnicalReportType } from '@/src/types/lab-work-order';

/**
 * Contrato Mobile del TechnicalReport (espejo de backend/app/schemas/
 * technical_report*.py). `capture_values` contiene SOLO la captura propia del
 * trabajo; cliente, OT, equipo y folio viven en el snapshot/proyección.
 */

export type EffectivenessResult = 'satisfactory' | 'satisfactory_with_observations' | 'unsatisfactory';

/** Installation v1 -- lista cerrada de campos. */
export type InstallationCaptureValues = {
  installation_date: string | null;
  installation_location: string | null;
  initial_condition: string | null;
  installation_description: string | null;
  activities_performed: string | null;
  has_incidents: boolean | null;
  incident_description: string | null;
  corrective_action: string | null;
  functional_test_performed: boolean | null;
  effectiveness_result: EffectivenessResult | null;
  effectiveness_description: string | null;
  effectiveness_notes: string | null;
  final_observations: string | null;
};

export type InstallationCaptureField = keyof InstallationCaptureValues;

/** Campos de texto libre (sin booleanos, fecha ni enumerados). */
export type InstallationTextField =
  | 'installation_location'
  | 'initial_condition'
  | 'installation_description'
  | 'activities_performed'
  | 'incident_description'
  | 'corrective_action'
  | 'effectiveness_description'
  | 'effectiveness_notes'
  | 'final_observations';

/** Cuerpo del PATCH de autosave: sólo capture_values. */
export type TechnicalReportCaptureUpdate = {
  capture_values: InstallationCaptureValues;
};

export type TechnicalReportEvidenceType = 'before' | 'during' | 'incident' | 'after';

export type TechnicalReportEvidence = {
  id: number;
  technical_report_id: number;
  evidence_type: TechnicalReportEvidenceType;
  mime_type: 'image/jpeg' | 'image/png';
  sha256: string;
  size_bytes: number;
  position: number;
  caption: string | null;
  created_at: string;
};

/** Respuesta de POST .../technical-report/evidence. */
export type TechnicalReportEvidenceUploadResponse = TechnicalReportEvidence;

/** Lectura del TechnicalReport vigente. `capture_values` llega parcial (sólo
 * lo capturado); el formulario lo completa con nulls. */
export type TechnicalReportRead = {
  id: number;
  lab_equipment_id: number;
  report_type: TechnicalReportType;
  folio: string;
  status: TechnicalReportStatus;
  capture_values: Partial<InstallationCaptureValues>;
  document_snapshot: Record<string, unknown> | null;
  report_schema_version: number;
  revision_number: number;
  is_current: boolean;
  /** Se fijan al confirmar la captura: el usuario autenticado que confirma. */
  performed_by_name_snapshot: string | null;
  performed_at: string | null;
  evidence: TechnicalReportEvidence[];
};
