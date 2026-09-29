import React, { useCallback, useEffect, useState } from 'react';

import { downloadCapturePackage, getCapturePackageSummary } from '../../services/api.js';
import {
  LAB_FIELD_SHEET_STATUS_LABELS,
  LAB_WORK_ORDER_STATUS_LABELS,
  captureStateLabel,
  describeCaptureBlocker,
} from './mobileExecutionPresentation.js';

// Captura para un ETS ejecutado en MYC Mobile: handoff DOCUMENTAL PDF-only.
// Recibe las Hojas de Campo finales congeladas por LAB; no hay XLSX/Master,
// no se genera certificado ni folio y no se capturan valores técnicos.
// Consultar el resumen nunca muta el lifecycle del ETS.

function triggerBlobDownload(blob, filename) {
  const url = URL.createObjectURL(blob);
  const link = document.createElement('a');
  link.href = url;
  link.download = filename;
  document.body.appendChild(link);
  link.click();
  link.remove();
  window.setTimeout(() => URL.revokeObjectURL(url), 1000);
}

export default function EtsMobileCapturePanel({ serviceOrderId, serviceOrderFolio }) {
  const [summary, setSummary] = useState(null);
  const [error, setError] = useState('');
  const [notice, setNotice] = useState('');
  const [busy, setBusy] = useState(false);

  const load = useCallback(async () => {
    setError('');
    try {
      setSummary(await getCapturePackageSummary(serviceOrderId));
    } catch (requestError) {
      setError(requestError.message);
    }
  }, [serviceOrderId]);

  useEffect(() => { load(); }, [load]);

  async function download() {
    setBusy(true);
    setError('');
    try {
      const { blob, filename } = await downloadCapturePackage(
        serviceOrderId, null, `${serviceOrderFolio || `ETS-${serviceOrderId}`}.zip`
      );
      triggerBlobDownload(blob, filename);
      setNotice('Paquete PDF de Captura descargado.');
    } catch (requestError) {
      setError(requestError.message);
      await load();
    } finally {
      setBusy(false);
    }
  }

  const ready = Boolean(summary?.ready);
  return (
    <section className="quotation-section ets-mobile-capture">
      <div className="quotation-section__title">
        <div>
          <p>Captura · handoff documental MYC Mobile</p>
          <h3>Hojas de Campo finales (PDF)</h3>
        </div>
        <span className={`ets-mobile-capture__state ${ready ? 'is-ready' : 'is-blocked'}`}>
          {summary ? captureStateLabel(summary) : '…'}
        </span>
        <button className="table-button table-button--primary" disabled={!ready || busy} onClick={download} type="button">
          Descargar paquete PDF
        </button>
        <button className="table-button" onClick={load} type="button">Actualizar</button>
      </div>
      <p className="muted">
        El paquete contiene sólo los PDF finales congelados en MYC Mobile, organizados por OT y folio de certificado LAB.
        La carga de XLSX documental y la generación de certificados corresponden a una fase posterior.
      </p>
      {error ? <div className="form-error" role="alert">{error}</div> : null}
      {notice ? <div className="form-notice" role="status">{notice}</div> : null}
      {summary ? (
        <>
          <div className="ets-metric-strip">
            <article><span>Listos</span><strong>{summary.ready_total}</strong></article>
            <article><span>Pendientes</span><strong>{summary.pending_total}</strong></article>
            <article><span>OT raíz</span><strong>{summary.root_folio ?? '-'}</strong></article>
          </div>
          {summary.blockers?.length ? (
            <div className="form-error" role="alert">
              <strong>Bloqueos</strong>
              <ul className="ets-mobile-capture__blockers">
                {summary.blockers.map((blocker, index) => (
                  <li data-code={blocker.code} key={`${blocker.code}-${blocker.equipment_id ?? blocker.work_order_id ?? index}`}>
                    {describeCaptureBlocker(blocker)}
                  </li>
                ))}
              </ul>
            </div>
          ) : null}
          {(summary.groups || []).map((group) => (
            <article className="ets-field-sheet-work-order is-expanded" key={group.work_order_id}>
              <div className="ets-field-sheet-work-order__summary">
                <div><small>Orden de Trabajo MYC Mobile</small><strong>OT {group.work_order_folio}</strong></div>
                <mark className={`quotation-status status-${group.status}`}>
                  {LAB_WORK_ORDER_STATUS_LABELS[group.status] || group.status}
                </mark>
                <span>{group.ready} listo(s) · {group.pending} pendiente(s)</span>
              </div>
              <div className="ets-field-sheet-work-order__equipment">
                {group.equipment.map((item) => (
                  <article className="ets-field-sheet-equipment-row" key={item.equipment_id}>
                    <div><strong>{item.position}. {item.instrument}</strong><span>{item.identification}</span></div>
                    <dl>
                      <div><dt>Folio</dt><dd>{item.certificate_folio || '-'}</dd></div>
                      <div><dt>Hoja</dt><dd>{LAB_FIELD_SHEET_STATUS_LABELS[item.field_sheet_status] || item.field_sheet_status || 'Sin hoja'}</dd></div>
                    </dl>
                    <mark className={`quotation-status status-${item.ready ? 'completed' : 'pending'}`}>
                      {item.ready ? 'Lista' : 'Bloqueada'}
                    </mark>
                  </article>
                ))}
              </div>
            </article>
          ))}
        </>
      ) : null}
    </section>
  );
}
