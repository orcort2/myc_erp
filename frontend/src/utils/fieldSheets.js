export function fieldSheetToForm(fieldSheet) {
  return {
    initialCondition: fieldSheet?.initial_condition ?? '',
    finalCondition: fieldSheet?.final_condition ?? '',
    patternUsed: fieldSheet?.pattern_used ?? '',
    results: fieldSheet?.results ?? '',
    observations: fieldSheet?.observations ?? '',
    evidenceNotes: fieldSheet?.evidence_notes ?? '',
    method: fieldSheet?.method ?? '',
    environmentalConditions: fieldSheet?.environmental_conditions ?? '',
    technicianNotes: fieldSheet?.technician_notes ?? ''
  };
}

export function buildFieldSheetPayload(form) {
  return {
    initial_condition: form.initialCondition.trim() || null,
    final_condition: form.finalCondition.trim() || null,
    pattern_used: form.patternUsed.trim() || null,
    results: form.results.trim() || null,
    observations: form.observations.trim() || null,
    evidence_notes: form.evidenceNotes.trim() || null,
    method: form.method.trim() || null,
    environmental_conditions: form.environmentalConditions.trim() || null,
    technician_notes: form.technicianNotes.trim() || null
  };
}

export function getFieldSheetCompletionErrors(form) {
  const errors = [];
  if (!form.initialCondition.trim()) errors.push('Condicion inicial');
  if (!form.finalCondition.trim()) errors.push('Condicion final');
  if (!form.patternUsed.trim()) errors.push('Patron usado');
  if (!form.results.trim()) errors.push('Resultados');
  if (!form.observations.trim() && !form.evidenceNotes.trim()) {
    errors.push('Observaciones o evidencia');
  }
  return errors;
}