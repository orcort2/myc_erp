import type {
  EffectivenessResult,
  InstallationCaptureField,
  InstallationCaptureValues,
  TechnicalReportEvidenceType,
} from '@/src/types/technical-report';

/**
 * Contrato de captura del reporte de Instalación (schema v1) en Mobile.
 * Espejo de backend/app/schemas/technical_report_installation.py: la lista de
 * campos es cerrada y ambas se verifican contra el mismo conjunto en pruebas.
 */

export const INSTALLATION_SCHEMA_VERSION = 1;

export const INSTALLATION_V1_FIELDS = [
  'installation_date',
  'installation_location',
  'initial_condition',
  'installation_description',
  'activities_performed',
  'has_incidents',
  'incident_description',
  'corrective_action',
  'functional_test_performed',
  'effectiveness_result',
  'effectiveness_description',
  'effectiveness_notes',
  'final_observations',
] as const satisfies readonly InstallationCaptureField[];

export const LONG_TEXT_MAX = 4000;
export const SHORT_TEXT_MAX = 255;

export const EFFECTIVENESS_OPTIONS: { value: EffectivenessResult; label: string }[] = [
  { value: 'satisfactory', label: 'Satisfactorio' },
  { value: 'satisfactory_with_observations', label: 'Satisfactorio con observaciones' },
  { value: 'unsatisfactory', label: 'No satisfactorio' },
];

/** Secciones del formulario y la evidencia que cada una puede recibir: el
 * contexto de la sección determina `evidence_type` (nunca se pregunta). */
export type InstallationSectionKey =
  | 'installation'
  | 'initial_condition'
  | 'work_performed'
  | 'incidents'
  | 'functional_verification'
  | 'final_observations'
  | 'evidence';

export const SECTION_EVIDENCE_TYPE: Partial<Record<InstallationSectionKey, TechnicalReportEvidenceType>> = {
  initial_condition: 'before',
  work_performed: 'during',
  incidents: 'incident',
  functional_verification: 'after',
};

export const EVIDENCE_TYPE_LABELS: Record<TechnicalReportEvidenceType, string> = {
  before: 'Antes',
  during: 'Durante',
  incident: 'Incidencia',
  after: 'Resultado final',
};

export function emptyInstallationCapture(): InstallationCaptureValues {
  return Object.fromEntries(INSTALLATION_V1_FIELDS.map((field) => [field, null])) as InstallationCaptureValues;
}

/** Hidrata el formulario con lo capturado en el servidor (parcial). */
export function installationCaptureFromServer(stored: Partial<InstallationCaptureValues>): InstallationCaptureValues {
  return { ...emptyInstallationCapture(), ...stored };
}

/** Aplica un cambio local respetando las reglas del contrato: si no hubo
 * prueba funcional no existe un resultado (no se inventa uno). */
export function applyInstallationChange<K extends InstallationCaptureField>(
  values: InstallationCaptureValues,
  field: K,
  value: InstallationCaptureValues[K],
): InstallationCaptureValues {
  const next = { ...values, [field]: value };
  if (field === 'functional_test_performed' && value === false) next.effectiveness_result = null;
  return next;
}

export function showsIncidentFields(values: InstallationCaptureValues): boolean {
  return values.has_incidents === true;
}

export function showsEffectivenessFields(values: InstallationCaptureValues): boolean {
  return values.functional_test_performed === true;
}

/** Texto vacío = null: el backend interpreta null como "limpiar el campo". */
export function textOrNull(value: string): string | null {
  return value.trim() ? value : null;
}
