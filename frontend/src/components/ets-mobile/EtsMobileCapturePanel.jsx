import React, { useState } from 'react';

import { downloadCapturePackage } from '../../services/api.js';
import EtsMobileEquipmentDetail from './EtsMobileEquipmentDetail.jsx';
import {
  LAB_FIELD_SHEET_STATUS_LABELS,
  LAB_WORK_ORDER_STATUS_LABELS,
  captureStateLabel,
  describeCaptureBlocker,
  getMobileExecutionPermissions,
} from './mobileExecutionPresentation.js';

// Captura para un ETS ejecutado en MYC Mobile: handoff DOCUMENTAL PDF-only.
// Recibe las Hojas de Campo finales congeladas por LAB; no hay XLSX/Master,
// no se genera certificado ni folio y no se capturan valores técnicos.
//
// El resumen LAB NO se consulta aquí: lo carga una sola vez la página
// (useMobileCaptureSummary) y lo comparten esta pestaña, su badge y la franja
// de etapas del Resumen. "Actualizar" usa ese mismo loader.

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

export default function EtsMobileCapturePanel({
  serviceOrderId,
  serviceOrderFolio,
  user,
  summary,
  summaryError = '',
  onRefresh,
}) {
  const permissions = getMobileExecutionPermissions(user);
  const [error, setError] = useState('');
  const [notice, setNotice] = useState('');
  const [busy, setBusy] = useState(false);
  const [detailEquipmentId, setDetailEquipmentId] = useState(null);

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
      await onRefresh?.();
    } finally {
      setBusy(false);
    }
  }

  const ready = Boolean(summary?.ready);
  const canOpenDetail = permissions.canReadFieldSheets;
  return (
    <section className="quotation-section ets-mobile-capture">
      <div className="quotation-section__title">
        <div>
          <p>Captura · handoff documental MYC Mobile</p>
          <h3>Hojas de Campo finales (PDF)</h3>
        </div>
        <span className={`ets-mobile-capture__state ${summary ? (ready ? 'is-ready' : 'is-blocked') : ''}`}>
          {summary ? captureStateLabel(summary) : 'VALIDANDO'}
        </span>
        <button className="table-button table-button--primary" disabled={!ready || busy} onClick={download} type="button">
          Descargar paquete PDF
        </button>
        <button className="table-button" onClick={() => onRefresh?.()} type="button">Actualizar</button>
      </div>
      <p className="muted">
        El paquete contiene sólo los PDF finales congelados en MYC Mobile: una carpeta por OT y cada archivo nombrado con
        el folio de certificado LAB. La carga de XLSX documental y la generación de certificados corresponden a una fase posterior.
      </p>
      {error || summaryError ? <div className="form-error" role="alert">{error || summaryError}</div> : null}
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
            <article className="ets-mobile-work-order" key={group.work_order_id}>
              <header className="ets-mobile-work-order__header">
                <div className="ets-mobile-work-order__title">
                  <small>Orden de Trabajo MYC Mobile</small>
                  <strong>OT {group.work_order_folio}</strong>
                  <span>{group.ready} listo(s) · {group.pending} pendiente(s)</span>
                </div>
                <mark className={`quotation-status status-${group.status} ets-mobile-work-order__status`}>
                  {LAB_WORK_ORDER_STATUS_LABELS[group.status] || group.status}
                </mark>
              </header>
              <div className="ets-mobile-work-order__equipment">
                {group.equipment.map((item) => {
                  const sheetLabel = LAB_FIELD_SHEET_STATUS_LABELS[item.field_sheet_status] || item.field_sheet_status || 'Sin hoja';
                  return (
                    <article className="ets-mobile-equipment-card" key={item.equipment_id}>
                      <div className="ets-mobile-equipment-card__identity">
                        {canOpenDetail ? (
                          <button
                            className="ets-mobile-equipment-card__link"
                            onClick={() => setDetailEquipmentId(item.equipment_id)}
                            type="button"
                          >
                            <strong>{item.position}. {item.instrument}</strong>
                            <small>Ver detalle</small>
                          </button>
                        ) : (
                          <strong>{item.position}. {item.instrument}</strong>
                        )}
                        <span>{item.identification}</span>
                      </div>
                      <dl className="ets-mobile-equipment-card__meta">
                        <div><dt>Folio</dt><dd>{item.certificate_folio || '-'}</dd></div>
                        <div>
                          <dt>Hoja</dt>
                          <dd>
                            {canOpenDetail && item.field_sheet_status ? (
                              <button
                                className="ets-mobile-equipment-card__inline-link"
                                onClick={() => setDetailEquipmentId(item.equipment_id)}
                                type="button"
                              >
                                {sheetLabel}
                              </button>
                            ) : sheetLabel}
                          </dd>
                        </div>
                      </dl>
                      <div className="ets-mobile-equipment-card__actions">
                        <mark className={`quotation-status status-${item.ready ? 'completed' : 'pending'}`}>
                          {item.ready ? 'Lista' : 'Bloqueada'}
                        </mark>
                      </div>
                    </article>
                  );
                })}
              </div>
            </article>
          ))}
        </>
      ) : null}
      {detailEquipmentId ? (
        <EtsMobileEquipmentDetail
          equipmentId={detailEquipmentId}
          onChanged={() => onRefresh?.()}
          onClose={() => setDetailEquipmentId(null)}
          serviceOrderId={serviceOrderId}
          user={user}
        />
      ) : null}
    </section>
  );
}
