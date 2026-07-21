import React from 'react';

import { captureValidationLabels, getCaptureValidationIssues } from '../utils/captureMasters.js';

function count(value) {
  const parsed = Number(value);
  return Number.isFinite(parsed) ? parsed : 0;
}

export default function CaptureProcessingSummary({ result }) {
  if (!result) return null;
  const summary = result.summary || {};
  const issues = (result.processed || []).flatMap((file) => getCaptureValidationIssues(file.validation).map(([key, validation]) => ({
    file: file.filename,
    label: captureValidationLabels[key] || key,
    status: validation.status,
    expected: validation.expected,
  })));
  return (
    <section className="capture-processing-result" role="status">
      <div><p>Resultado de la carga</p><h4>Paquete procesado correctamente</h4></div>
      <div className="capture-processing-result__metrics">
        <span><strong>{count(summary.identified)}</strong> identificado(s)</span>
        <span><strong>{count(summary.unidentified)}</strong> no identificado(s)</span>
        <span><strong>{count(summary.ignored_auxiliary)}</strong> auxiliar(es) ignorado(s)</span>
        <span><strong>{count(summary.warnings)}</strong> advertencia(s)</span>
        <span><strong>{count(summary.mismatches)}</strong> diferencia(s) bloqueante(s)</span>
      </div>
      {issues.length ? (
        <div className="capture-processing-result__issues">
          <strong>Advertencias y diferencias detectadas</strong>
          <ul>{issues.map((issue, index) => <li key={`${issue.file}-${issue.label}-${index}`}><b>{issue.label}</b>: {issue.status === 'no_encontrado' ? 'no encontrado' : 'no coincide'}{issue.expected ? ` (esperado: ${issue.expected})` : ''}</li>)}</ul>
        </div>
      ) : <p className="capture-processing-result__clean">Sin advertencias ni diferencias.</p>}
    </section>
  );
}
