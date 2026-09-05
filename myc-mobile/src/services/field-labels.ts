// Mapa único de etiquetas humanas por clave de campo, compartido entre
// LabTechnicalCapture.tsx (bullets de missingFields) y error-detail.ts
// (mensajes de validación 422 humanizados). Vive aquí -- sin depender de
// react-native -- porque error-detail.ts debe seguir siendo importable bajo
// node:test sin arrastrar Expo/RN; LabTechnicalCapture.tsx sí puede importar
// este módulo sin problema. Una sola fuente evita que las dos listas
// diverjan (un campo nuevo con label en un lado y fallback genérico en el
// otro).
export const FIELD_LABELS: Record<string, string> = {
  work_order_number: 'No. de orden de trabajo',
  reserved_certificate_folio: 'Folio de certificado',
  attention: 'Atención a',
  company: 'Empresa',
  address: 'Dirección',
  instrument: 'Instrumento',
  scope: 'Alcance / capacidad',
  brand: 'Marca',
  model: 'Modelo',
  serial_number: 'No. de serie',
  identification: 'Identificación',
  internal_id: 'ID interno',
  report_number: 'Folio de informe',
  location: 'Ubicación',
  minimum_division: 'División mínima',
  reception_date: 'Fecha de recepción',
  calibration_date: 'Fecha de calibración',
  next_calibration_date: 'Próxima calibración',
  calibration_place: 'Lugar de calibración',
  environment_humidity_start: 'Humedad inicial',
  environment_humidity_end: 'Humedad final',
  environment_temperature_start: 'Temperatura inicial',
  environment_temperature_end: 'Temperatura final',
  initial_condition: 'Condición inicial',
  final_condition: 'Condición final',
  method: 'Método',
  units: 'Unidades',
  observations: 'Observaciones',
  evidence_notes: 'Notas de evidencia',
  calibrated_by: 'Calibrado por',
  reviewed_by: 'Revisado por',
  report_made_by: 'Reporte elaborado por',
  purchase_order_or_quotation: 'Orden de compra / cotización',
};
