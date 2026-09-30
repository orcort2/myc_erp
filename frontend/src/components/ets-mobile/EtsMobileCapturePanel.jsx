import React, { useState } from 'react';

import { downloadCapturePackage } from '../../services/api.js';
import EtsMobileEquipmentDetail from './EtsMobileEquipmentDetail.jsx';
import { fieldSheetPdfLoader, viewLabPdf, workOrderPdfLoader } from './labDocumentActions.js';
import {
  LAB_FIELD_SHEET_STATUS_LABELS,
  LAB_WORK_ORDER_STATUS_LABELS,
  captureGroupDocuments,
  captureStateLabel,
  countCaptureDocuments,
  describeCaptureBlocker,
  getMobileExecutionPermissions,
} from './mobileExecutionPresentation.js';

// Captura para un ETS ejecutado en MYC Mobile: handoff DOCUMENTAL PDF-only.
// Por OT recibe el PDF final oficial de la OT y las Hojas de Campo finales
// congeladas por LAB; no hay XLSX/Master, no se genera certificado ni folio y
// no se capturan valores técnicos (sin inputs).
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

  async function run(action) {
    setError('');
    try {
      await action();
    } catch (requestError) {
      setError(requestError.message);
    }
  }

  async function download() {
    setBusy(true);
    setError('');
    try {
      const { blob, filename } = await downloadCapturePackage(
        serviceOrderId, null, `${serviceOrderFolio || `ETS-${serviceOrderId}`}.zip`
      );
      triggerBlobDownload(blob, filename);
      setNotice('Paquete documental de Captura descargado.');
    } catch (requestError) {
      setError(requestError.message);
      await onRefresh?.();
    } finally {
      setBusy(false);
    }
  }

  const ready = Boolean(summary?.ready);
  const canReadTechnical = permissions.canReadFieldSheets;
  const groups = summary?.groups || [];
  return (
    <section className="quotation-section ets-lab-capture">
      <div className="quotation-section__title">
        <div>
          <p>Captura · handoff documental</p>
          <h3>Paquete documental MYC Mobile</h3>
        </div>
        <mark className={`quotation-status ${summary ? (ready ? 'status-completed' : 'status-pending') : 'status-draft'}`}>
          {summary ? captureStateLabel(summary) : 'VALIDANDO'}
        </mark>
        <div className="toolbar-actions">
          <button className="table-button table-button--primary" disabled={!ready || busy} onClick={download} type="button">
            Descargar paquete PDF
          </button>
          <button className="table-button" onClick={() => onRefresh?.()} type="button">Actualizar</button>
        </div>
      </div>
      <p className="muted">
        El paquete contiene, por OT, el PDF final oficial de la OT y las Hojas de Campo finales congeladas en MYC Mobile,
        cada una nombrada con el folio de certificado LAB. La carga de XLSX documental y la generación de certificados
        corresponden a una fase posterior.
      </p>
      {error || summaryError ? <div className="form-error" role="alert">{error || summaryError}</div> : null}
      {notice ? <div className="form-notice" role="status">{notice}</div> : null}
      {summary ? (
        <>
          <div className="ets-metric-strip">
            <span className="ets-metric-badge"><strong>{captureStateLabel(summary)}</strong>Estado</span>
            <span className="ets-metric-badge"><strong>{summary.root_folio ?? '-'}</strong>OT raíz</span>
            <span className="ets-metric-badge"><strong>{groups.length}</strong>OT</span>
            <span className="ets-metric-badge"><strong>{countCaptureDocuments(summary)}</strong>Documentos</span>
            <span className="ets-metric-badge"><strong>{summary.ready_total}</strong>Equipos listos</span>
            <span className="ets-metric-badge"><strong>{summary.pending_total}</strong>Pendientes</span>
          </div>
          {summary.blockers?.length ? (
            <div className="form-error" role="alert">
              <strong>Bloqueos</strong>
              <ul className="ets-lab-capture__blockers">
                {summary.blockers.map((blocker, index) => (
                  <li data-code={blocker.code} key={`${blocker.code}-${blocker.equipment_id ?? blocker.work_order_id ?? index}`}>
                    {describeCaptureBlocker(blocker)}
                  </li>
                ))}
              </ul>
            </div>
          ) : null}
          {groups.map((group) => (
            <article className="quotation-section ets-lab-work-order" key={group.work_order_id}>
              <div className="quotation-section__title ets-lab-work-order__title">
                <div>
                  <p>Orden de Trabajo MYC Mobile</p>
                  <h3>OT {group.work_order_folio} · {LAB_WORK_ORDER_STATUS_LABELS[group.status] || group.status}</h3>
                  <span>{group.ready} listo(s) · {group.pending} pendiente(s)</span>
                </div>
                <mark className={`quotation-status status-${group.status}`}>
                  {LAB_WORK_ORDER_STATUS_LABELS[group.status] || group.status}
                </mark>
              </div>

              <h4 className="ets-lab-work-order__subtitle">Documentos</h4>
              <ul className="ets-lab-document-list">
                {captureGroupDocuments(group).map((document) => (
                  <li className="glass-card-mini ets-lab-document" data-kind={document.kind} key={document.key}>
                    <strong>{document.label}</strong>
                    <span>{document.available ? 'PDF final congelado' : 'No disponible'}</span>
                    {document.available && document.kind === 'work_order' ? (
                      <button
                        className="table-button"
                        onClick={() => run(() => viewLabPdf(workOrderPdfLoader(serviceOrderId, group.work_order_id), (e) => setError(e.message)))}
                        type="button"
                      >
                        Ver OT
                      </button>
                    ) : null}
                    {document.available && document.kind === 'field_sheet' && canReadTechnical ? (
                      <button
                        className="table-button"
                        onClick={() => run(() => viewLabPdf(fieldSheetPdfLoader(serviceOrderId, document.fieldSheetId), (e) => setError(e.message)))}
                        type="button"
                      >
                        Ver hoja
                      </button>
                    ) : null}
                  </li>
                ))}
              </ul>

              <h4 className="ets-lab-work-order__subtitle">Equipos</h4>
              <div className="ets-lab-equipment-list">
                {group.equipment.map((item) => {
                  const sheetLabel = LAB_FIELD_SHEET_STATUS_LABELS[item.field_sheet_status] || item.field_sheet_status || 'Sin hoja';
                  return (
                    <article className="glass-card-mini ets-lab-equipment-card" key={item.equipment_id}>
                      <div className="ets-lab-equipment-card__identity">
                        {canReadTechnical ? (
                          <button className="ets-lab-link" onClick={() => setDetailEquipmentId(item.equipment_id)} type="button">
                            <strong>{item.position}. {item.instrument}</strong>
                            <small>Ver detalle</small>
                          </button>
                        ) : (
                          <strong>{item.position}. {item.instrument}</strong>
                        )}
                        <span>{item.identification}</span>
                      </div>
                      <div className="read-only-grid ets-lab-readonly-grid ets-lab-readonly-grid--compact">
                        <article><span>Folio</span><strong>{item.certificate_folio || '-'}</strong></article>
                        <article>
                          <span>Hoja</span>
                          <strong>
                            {canReadTechnical && item.field_sheet_status ? (
                              <button className="ets-lab-inline-link" onClick={() => setDetailEquipmentId(item.equipment_id)} type="button">
                                {sheetLabel}
                              </button>
                            ) : sheetLabel}
                          </strong>
                        </article>
                      </div>
                      <div className="toolbar-actions ets-lab-equipment-card__actions">
                        <mark className={`quotation-status status-${item.ready ? 'completed' : 'pending'}`}>
                          {item.ready ? 'Lista' : 'Bloqueada'}
                        </mark>
                        {canReadTechnical ? (
                          <button className="table-button" onClick={() => setDetailEquipmentId(item.equipment_id)} type="button">
                            Ver detalle equipo
                          </button>
                        ) : null}
                        {canReadTechnical && item.field_sheet_has_final_pdf && item.field_sheet_id ? (
                          <button
                            className="table-button"
                            onClick={() => run(() => viewLabPdf(fieldSheetPdfLoader(serviceOrderId, item.field_sheet_id), (e) => setError(e.message)))}
                            type="button"
                          >
                            Ver hoja
                          </button>
                        ) : null}
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
