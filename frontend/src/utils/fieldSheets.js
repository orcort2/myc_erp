import { emptyFieldSheetForm } from '../constants/forms.js';

export const fieldSheetTemplateRowConfig = {
  general: [{ key: 'main', label: 'Resultados', rows: 10 }],
  anemometro: [{ key: 'main', label: 'Resultados', rows: 10 }],
  temperatura: [{ key: 'main', label: 'Resultados', rows: 10 }],
  sonido: [{ key: 'main', label: 'Resultados', rows: 10 }],
  dimensional: [{ key: 'main', label: 'Resultados', rows: 10 }],
  electrica: [
    { key: 'main', label: 'Resultados', rows: 5 },
    { key: 'page2_a', label: 'Resultados complementarios A', rows: 5 },
    { key: 'page2_b', label: 'Resultados complementarios B', rows: 5 },
    { key: 'page2_c', label: 'Resultados complementarios C', rows: 5 },
    { key: 'page2_d', label: 'Resultados complementarios D', rows: 5 },
    { key: 'page2_e', label: 'Resultados complementarios E', rows: 5 }
  ]
};

function buildDefaultResultsRows(templateKey = 'general') {
  return (fieldSheetTemplateRowConfig[templateKey] ?? fieldSheetTemplateRowConfig.general).flatMap((section) =>
    Array.from({ length: section.rows }, (_, index) => ({
      id: null,
      sectionKey: section.key,
      rowNumber: index + 1,
      patternValue: '',
      ibcValue1: '',
      ibcValue2: '',
      ibcValue3: '',
      unit: '',
      notes: ''
    }))
  );
}

function normalizeResultsRows(rows = [], templateKey = 'general') {
  if (!rows.length) {
    return buildDefaultResultsRows(templateKey);
  }
  return rows.map((row) => ({
    id: row?.id ?? null,
    sectionKey: row?.section_key ?? row?.sectionKey ?? 'main',
    rowNumber: row?.row_number ?? row?.rowNumber ?? 1,
    patternValue: row?.pattern_value ?? row?.patternValue ?? '',
    ibcValue1: row?.ibc_value_1 ?? row?.ibcValue1 ?? '',
    ibcValue2: row?.ibc_value_2 ?? row?.ibcValue2 ?? '',
    ibcValue3: row?.ibc_value_3 ?? row?.ibcValue3 ?? '',
    unit: row?.unit ?? '',
    notes: row?.notes ?? ''
  }));
}

export function fieldSheetToForm(fieldSheet) {
  return {
    ...emptyFieldSheetForm,
    templateKey: fieldSheet?.template_key ?? 'general',
    calibrationProcedureId: fieldSheet?.calibration_procedure_id ? String(fieldSheet.calibration_procedure_id) : '',
    calibrationPlace: fieldSheet?.calibration_place ?? '',
    minimumDivision: fieldSheet?.minimum_division ?? '',
    location: fieldSheet?.location ?? '',
    attention: fieldSheet?.attention ?? '',
    company: fieldSheet?.company ?? '',
    address: fieldSheet?.address ?? '',
    receptionDate: fieldSheet?.reception_date ?? '',
    calibrationDate: fieldSheet?.calibration_date ?? '',
    nextCalibrationDate: fieldSheet?.next_calibration_date ?? '',
    environmentHumidityStart: fieldSheet?.environment_humidity_start ?? '',
    environmentHumidityEnd: fieldSheet?.environment_humidity_end ?? '',
    environmentTemperatureStart: fieldSheet?.environment_temperature_start ?? '',
    environmentTemperatureEnd: fieldSheet?.environment_temperature_end ?? '',
    equipmentGeneralCondition:
      fieldSheet?.equipment_general_condition === null || fieldSheet?.equipment_general_condition === undefined
        ? ''
        : fieldSheet.equipment_general_condition
          ? 'ok'
          : 'not_ok',
    considerEquipmentDeviations: Boolean(fieldSheet?.consider_equipment_deviations),
    units: fieldSheet?.units ?? '',
    calibratedBy: fieldSheet?.calibrated_by ?? '',
    reviewedBy: fieldSheet?.reviewed_by ?? '',
    reportMadeBy: fieldSheet?.report_made_by ?? '',
    purchaseOrderOrQuotation: fieldSheet?.purchase_order_or_quotation ?? '',
    initialCondition: fieldSheet?.initial_condition ?? '',
    finalCondition: fieldSheet?.final_condition ?? '',
    resultsSummary: fieldSheet?.results ?? '',
    patternUsed: fieldSheet?.pattern_used ?? '',
    observations: fieldSheet?.observations ?? '',
    evidenceNotes: fieldSheet?.evidence_notes ?? '',
    method: fieldSheet?.method ?? '',
    environmentalConditions: fieldSheet?.environmental_conditions ?? '',
    technicianNotes: fieldSheet?.technician_notes ?? '',
    reservedCertificateFolio: fieldSheet?.reserved_certificate_folio ?? '',
    certificateClientMode: fieldSheet?.certificate_client_mode ?? 'billing',
    certificateClientCompany: fieldSheet?.certificate_client_company ?? '',
    certificateClientAttention: fieldSheet?.certificate_client_attention ?? '',
    certificateClientAddress: fieldSheet?.certificate_client_address ?? '',
    applyCertificateClientToOrder: Boolean(fieldSheet?.apply_certificate_client_to_order),
    resultsRows: normalizeResultsRows(fieldSheet?.results_rows, fieldSheet?.template_key ?? 'general'),
    referenceStandards: Array.isArray(fieldSheet?.reference_standards)
      ? fieldSheet.reference_standards.map((item) => ({
          referenceStandardId: String(item.reference_standard_id),
          usageRole: item.usage_role ?? 'primary',
          measurementSection: item.measurement_section ?? '',
          notes: item.notes ?? '',
          referenceStandard: item.reference_standard ?? null
        }))
      : []
  };
}

export function buildFieldSheetPayload(form) {
  return {
    template_key: form.templateKey || 'general',
    calibration_procedure_id: form.calibrationProcedureId ? Number(form.calibrationProcedureId) : null,
    calibration_place: form.calibrationPlace.trim() || null,
    minimum_division: form.minimumDivision.trim() || null,
    location: form.location.trim() || null,
    attention: form.attention.trim() || null,
    company: form.company.trim() || null,
    address: form.address.trim() || null,
    reception_date: form.receptionDate || null,
    calibration_date: form.calibrationDate || null,
    next_calibration_date: form.nextCalibrationDate || null,
    environment_humidity_start: form.environmentHumidityStart.trim() || null,
    environment_humidity_end: form.environmentHumidityEnd.trim() || null,
    environment_temperature_start: form.environmentTemperatureStart.trim() || null,
    environment_temperature_end: form.environmentTemperatureEnd.trim() || null,
    equipment_general_condition:
      form.equipmentGeneralCondition === '' ? null : form.equipmentGeneralCondition === 'ok',
    consider_equipment_deviations: Boolean(form.considerEquipmentDeviations),
    units: form.units.trim() || null,
    calibrated_by: form.calibratedBy.trim() || null,
    reviewed_by: form.reviewedBy.trim() || null,
    report_made_by: form.reportMadeBy.trim() || null,
    purchase_order_or_quotation: form.purchaseOrderOrQuotation.trim() || null,
    initial_condition: form.initialCondition.trim() || null,
    final_condition: form.finalCondition.trim() || null,
    pattern_used: form.patternUsed.trim() || null,
    results: form.resultsSummary.trim() || null,
    observations: form.observations.trim() || null,
    evidence_notes: form.evidenceNotes.trim() || null,
    method: form.method.trim() || null,
    environmental_conditions: form.environmentalConditions.trim() || null,
    technician_notes: form.technicianNotes.trim() || null,
    certificate_client_mode: form.certificateClientMode || 'billing',
    certificate_client_company: form.certificateClientCompany.trim() || null,
    certificate_client_attention: form.certificateClientAttention.trim() || null,
    certificate_client_address: form.certificateClientAddress.trim() || null,
    apply_certificate_client_to_order: Boolean(form.applyCertificateClientToOrder),
    reference_standards: [],
    results_rows: normalizeResultsRows(form.resultsRows, form.templateKey).map((row) => ({
      id: row.id ?? undefined,
      section_key: row.sectionKey,
      row_number: row.rowNumber,
      pattern_value: row.patternValue.trim() || null,
      ibc_value_1: row.ibcValue1.trim() || null,
      ibc_value_2: row.ibcValue2.trim() || null,
      ibc_value_3: row.ibcValue3.trim() || null,
      unit: row.unit.trim() || null,
      notes: row.notes.trim() || null
    }))
  };
}

export function updateFieldSheetResultsRowsForTemplate(form, templateKey) {
  return {
    ...form,
    templateKey,
    resultsRows: buildDefaultResultsRows(templateKey)
  };
}

export function updateFieldSheetResultCell(rows, rowIndex, field, value) {
  return rows.map((row, index) => (index === rowIndex ? { ...row, [field]: value } : row));
}

export function hasStructuredFieldSheetResults(form) {
  return normalizeResultsRows(form.resultsRows, form.templateKey).some((row) =>
    [row.patternValue, row.ibcValue1, row.ibcValue2, row.ibcValue3].some((value) => String(value ?? '').trim())
  );
}

export function getFieldSheetCompletionErrors(form) {
  const errors = [];
  if (!form.initialCondition.trim()) errors.push('Condicion inicial');
  if (!form.finalCondition.trim()) errors.push('Condicion final');
  if (!hasStructuredFieldSheetResults(form)) errors.push('Resultados estructurados');
  if (!form.observations.trim() && !form.evidenceNotes.trim()) {
    errors.push('Observaciones o evidencia');
  }
  return errors;
}
