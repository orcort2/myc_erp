export const captureValidationLabels = {
  cliente: 'Cliente',
  proxima_calibracion: 'Próxima calibración',
  servicio: 'Servicio',
  folio: 'Folio',
  equipo: 'Equipo',
  identificacion: 'Identificación',
  marca: 'Marca',
  modelo: 'Modelo',
  serie: 'Serie',
  fecha_calibracion: 'Fecha de calibración',
};

export function getCaptureValidationIssues(validation = {}) {
  return Object.entries(validation || {}).filter(([, result]) => ['no_encontrado', 'mismatch', 'no_coincide'].includes(result?.status));
}

export function getCaptureMasterReadiness({ certificate, equipment, captureFile }) {
  const masterExpected = Boolean(
    equipment?.certificate_master_document_id
      && equipment?.certificate_master_version_id
      && equipment?.certificate_template_path_snapshot
  );
  const issues = getCaptureValidationIssues(captureFile?.validation);
  const warnings = issues.filter(([, result]) => result?.status === 'no_encontrado');
  const mismatches = issues.filter(([, result]) => ['mismatch', 'no_coincide'].includes(result?.status));
  const identified = captureFile?.status === 'identified';
  const ready = masterExpected && identified && mismatches.length === 0;
  let reason = '';
  if (!masterExpected) reason = 'No existe un Master esperado.';
  else if (!identified) reason = 'El Master esperado no está identificado.';
  else if (mismatches.length) reason = 'El Master contiene diferencias bloqueantes.';
  return { masterExpected, identified, ready, reason, warnings, mismatches };
}

export function latestCaptureFileMap(files = []) {
  const latest = new Map();
  files.forEach((file) => {
    if (file.certificate_id && !latest.has(file.certificate_id)) latest.set(file.certificate_id, file);
  });
  return latest;
}
