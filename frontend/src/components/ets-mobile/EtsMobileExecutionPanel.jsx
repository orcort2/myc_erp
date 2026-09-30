import React, { useCallback, useEffect, useState } from 'react';

import {
  cancelServiceOrderMobileWorkOrder,
  getServiceOrderMobileExecution,
  linkServiceOrderLab,
  replaceServiceOrderLab,
  restoreServiceOrderMobileWorkOrder,
  searchServiceOrderLabCandidates,
  unlinkServiceOrderLab,
} from '../../services/api.js';
import { formatDate } from '../../utils/formatters.js';
import EtsMobileCorrectionDialog from './EtsMobileCorrectionDialog.jsx';
import EtsMobileEquipmentDetail from './EtsMobileEquipmentDetail.jsx';
import EtsMobileModal from './EtsMobileModal.jsx';
import {
  downloadLabPdf,
  fieldSheetPdfLoader,
  printLabPdf,
  viewLabPdf,
  workOrderPdfLoader,
} from './labDocumentActions.js';
import {
  LAB_FIELD_SHEET_STATUS_LABELS,
  LAB_FOLIO_STATUS_LABELS,
  LAB_SERVICE_TYPE_LABELS,
  LAB_WORK_ORDER_STATUS_LABELS,
  correctionModeFor,
  describeWorkOrderHeader,
  getMobileExecutionPermissions,
  summarizeMobileExecution,
} from './mobileExecutionPresentation.js';

// Vista administrativa READ-ONLY de la ejecución técnica LAB dentro del ERP.
// Usa el lenguaje visual del ERP (quotation-section, section-heading,
// read-only-grid, ets-metric-strip, quotation-status, table-button,
// toolbar-actions); las clases .ets-lab-* sólo resuelven layout. No existe
// ningún input que edite datos técnicos LAB. El detalle de equipo es el
// componente único EtsMobileEquipmentDetail.

function LinkPicker({ serviceOrderId, mode, onDone, onCancel }) {
  const [query, setQuery] = useState('');
  const [candidates, setCandidates] = useState([]);
  const [reason, setReason] = useState('');
  const [error, setError] = useState('');
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    let active = true;
    const timer = window.setTimeout(() => {
      searchServiceOrderLabCandidates(serviceOrderId, query.trim())
        .then((rows) => { if (active) setCandidates(Array.isArray(rows) ? rows : []); })
        .catch((requestError) => { if (active) setError(requestError.message); });
    }, 350);
    return () => { active = false; window.clearTimeout(timer); };
  }, [query, serviceOrderId]);

  async function choose(candidate) {
    if (mode === 'replace' && !reason.trim()) {
      setError('El motivo es obligatorio para cambiar el vínculo.');
      return;
    }
    setBusy(true);
    setError('');
    try {
      if (mode === 'replace') await replaceServiceOrderLab(serviceOrderId, candidate.root_id, reason.trim());
      else await linkServiceOrderLab(serviceOrderId, candidate.root_id);
      onDone();
    } catch (requestError) {
      setError(requestError.message);
    } finally {
      setBusy(false);
    }
  }

  return (
    <EtsMobileModal
      eyebrow="Vínculo ETS ↔ MYC Mobile"
      onClose={onCancel}
      subtitle="Busca la OT raíz o cualquier OT del grupo por folio"
      title={mode === 'replace' ? 'Cambiar servicio MYC Mobile' : 'Vincular servicio MYC Mobile'}
    >
      <label className="quotation-client-search">
        <span>Folio de OT MYC Mobile</span>
        <input autoFocus onChange={(event) => setQuery(event.target.value)} placeholder="6438" type="search" value={query} />
      </label>
      {mode === 'replace' ? (
        <label className="quotation-client-search">
          <span>Motivo del cambio</span>
          <input onChange={(event) => setReason(event.target.value)} type="text" value={reason} />
        </label>
      ) : null}
      {error ? <div className="form-error" role="alert">{error}</div> : null}
      <div className="quotation-client-results">
        {candidates.length ? candidates.map((candidate) => (
          <button
            className="quotation-client-result"
            disabled={busy || candidate.linked_to_other_service_order || candidate.status === 'cancelled'}
            key={candidate.root_id}
            onClick={() => choose(candidate)}
            type="button"
          >
            <strong>OT {candidate.root_folio} · {candidate.client_name}</strong>
            <span>
              {candidate.work_order_count} OT ({candidate.group_folios.join(', ')}) · {candidate.equipment_count} equipo(s) ·{' '}
              {LAB_WORK_ORDER_STATUS_LABELS[candidate.status] || candidate.status}
              {candidate.linked_to_other_service_order ? ' · Vinculado a otro ETS' : ''}
            </span>
          </button>
        )) : <div className="clients-empty">Sin grupos MYC Mobile que coincidan.</div>}
      </div>
    </EtsMobileModal>
  );
}

export default function EtsMobileExecutionPanel({ serviceOrderId, user, onLinkChanged, onExecutionChanged }) {
  const permissions = getMobileExecutionPermissions(user);
  const [projection, setProjection] = useState(null);
  const [error, setError] = useState('');
  const [notice, setNotice] = useState('');
  const [picker, setPicker] = useState(null);
  const [detailEquipmentId, setDetailEquipmentId] = useState(null);
  const [correctionTarget, setCorrectionTarget] = useState(null);

  const load = useCallback(async () => {
    setError('');
    try {
      setProjection(await getServiceOrderMobileExecution(serviceOrderId));
    } catch (requestError) {
      setError(requestError.message);
    }
  }, [serviceOrderId]);

  useEffect(() => { load(); }, [load]);

  function applyProjection(next, message) {
    if (next) setProjection(next);
    if (message) setNotice(message);
    onExecutionChanged?.();
  }

  async function afterLinkChange(message) {
    setPicker(null);
    setNotice(message);
    await load();
    onLinkChanged?.();
  }

  async function run(action) {
    setError('');
    try {
      await action();
    } catch (requestError) {
      setError(requestError.message);
    }
  }

  async function unlink() {
    const reason = window.prompt('Motivo para desvincular el servicio MYC Mobile');
    if (!reason?.trim()) return;
    await run(async () => {
      await unlinkServiceOrderLab(serviceOrderId, reason.trim());
      await afterLinkChange('Servicio MYC Mobile desvinculado; el historial se conserva.');
    });
  }

  async function cancelWorkOrder(workOrder) {
    const reason = window.prompt(`Motivo para cancelar la OT ${workOrder.folio} en MYC Mobile`);
    if (!reason?.trim()) return;
    await run(async () => applyProjection(
      await cancelServiceOrderMobileWorkOrder(serviceOrderId, workOrder.id, reason.trim()),
      `OT ${workOrder.folio} cancelada; su historial técnico se conserva.`,
    ));
  }

  async function restoreWorkOrder(workOrder) {
    await run(async () => applyProjection(
      await restoreServiceOrderMobileWorkOrder(serviceOrderId, workOrder.id),
      `OT ${workOrder.folio} restaurada a su estado anterior.`,
    ));
  }

  const totals = summarizeMobileExecution(projection);
  return (
    <section className="ets-lab-execution" aria-label="Ejecución técnica MYC Mobile">
      {error ? <div className="form-error" role="alert">{error}</div> : null}
      {notice ? <div className="form-notice" role="status">{notice}</div> : null}
      {!projection && !error ? <p className="muted">Consultando MYC Mobile…</p> : null}

      {projection && !projection.linked ? (
        <div className="glass-card-mini">
          <strong>Sin servicio MYC Mobile vinculado</strong>
          <span>El vínculo puede crearse al generar la OT en MYC Mobile o desde aquí.</span>
          {permissions.canManageLink ? (
            <button className="table-button table-button--primary" onClick={() => setPicker('link')} type="button">
              Vincular servicio MYC Mobile
            </button>
          ) : null}
        </div>
      ) : null}

      {projection?.linked ? (
        <>
          <div className="section-heading ets-lab-execution__heading">
            <div>
              <p>Servicio MYC Mobile</p>
              <h2>OT raíz {projection.root_folio}</h2>
            </div>
            {permissions.canManageLink ? (
              <div className="toolbar-actions">
                <button className="table-button" onClick={() => setPicker('replace')} type="button">Cambiar vínculo</button>
                <button className="table-button" onClick={unlink} type="button">Desvincular</button>
              </div>
            ) : null}
          </div>
          <div className="ets-metric-strip">
            <span className="ets-metric-badge"><strong>{totals.workOrders}</strong>OT</span>
            <span className="ets-metric-badge"><strong>{totals.equipment}</strong>Equipos</span>
            <span className="ets-metric-badge"><strong>{totals.completedSheets}</strong>Hojas completadas</span>
            <span className="ets-metric-badge"><strong>{totals.finalPdfs}</strong>Hojas con PDF final</span>
          </div>
          {projection.work_orders.map((workOrder) => {
            const header = describeWorkOrderHeader(workOrder);
            const otLoader = workOrderPdfLoader(serviceOrderId, workOrder.id);
            return (
              <article className="quotation-section ets-lab-work-order" key={workOrder.id}>
                <div className="quotation-section__title ets-lab-work-order__title">
                  <div>
                    <p>{header.role}</p>
                    <h3>OT {workOrder.folio}</h3>
                    <span>{workOrder.client_name}</span>
                  </div>
                  <mark className={`quotation-status status-${workOrder.status}`}>{header.statusLabel}</mark>
                </div>
                <div className="ets-metric-strip">
                  <span className="ets-metric-badge"><strong>{header.receptionDate ? formatDate(header.receptionDate) : '-'}</strong>Recepción</span>
                  <span className="ets-metric-badge"><strong>{header.departureDate ? formatDate(header.departureDate) : '-'}</strong>Salida</span>
                  <span className="ets-metric-badge"><strong>{header.equipmentCount}</strong>Equipos</span>
                  <span className="ets-metric-badge"><strong>{header.completedSheets}</strong>Hojas completadas</span>
                  <span className="ets-metric-badge"><strong>{header.finalSheetPdfs}</strong>PDF finales</span>
                </div>
                <div className="ets-lab-work-order__actions">
                  <div className="ets-lab-action-group" role="group" aria-label="Documentos">
                    <span className="ets-lab-action-group__label">Documentos</span>
                    {header.hasFinalPdf ? (
                      <div className="toolbar-actions">
                        <button className="table-button" onClick={() => run(() => viewLabPdf(otLoader, (e) => setError(e.message)))} type="button">Ver OT</button>
                        <button className="table-button" onClick={() => run(() => printLabPdf(otLoader, (e) => setError(e.message)))} type="button">Imprimir OT</button>
                        <button className="table-button" onClick={() => run(() => downloadLabPdf(otLoader, `OT-${workOrder.folio}.pdf`))} type="button">Descargar OT</button>
                      </div>
                    ) : (
                      <span className="ets-metric-badge ets-lab-unavailable">OT final no disponible</span>
                    )}
                  </div>
                  {permissions.canCancelWorkOrders ? (
                    <div className="ets-lab-action-group ets-lab-action-group--admin" role="group" aria-label="Administración">
                      <span className="ets-lab-action-group__label">Administración</span>
                      <div className="toolbar-actions">
                        {workOrder.status === 'cancelled' ? (
                          <button className="table-button" onClick={() => restoreWorkOrder(workOrder)} type="button">Restaurar OT</button>
                        ) : (
                          <button className="table-button" onClick={() => cancelWorkOrder(workOrder)} type="button">Cancelar OT</button>
                        )}
                      </div>
                    </div>
                  ) : null}
                </div>
                <h4 className="ets-lab-work-order__subtitle">Equipos</h4>
                <div className="ets-lab-equipment-list">
                  {workOrder.equipment.length ? workOrder.equipment.map((equipment) => {
                    const sheet = equipment.field_sheet;
                    const correctionMode = correctionModeFor(workOrder, equipment);
                    return (
                      <article className="glass-card-mini ets-lab-equipment-card" key={equipment.id}>
                        <div className="ets-lab-equipment-card__identity">
                          {permissions.canReadFieldSheets ? (
                            <button className="ets-lab-link" onClick={() => setDetailEquipmentId(equipment.id)} type="button">
                              <strong>{equipment.position}. {equipment.instrument}</strong>
                              <small>Ver detalle</small>
                            </button>
                          ) : (
                            <strong>{equipment.position}. {equipment.instrument}</strong>
                          )}
                          <span>{[equipment.brand, equipment.model].filter(Boolean).join(' · ')}</span>
                        </div>
                        <div className="read-only-grid ets-lab-readonly-grid ets-lab-readonly-grid--compact">
                          <article><span>Serie</span><strong>{equipment.serial_number}</strong></article>
                          <article><span>Identificación</span><strong>{equipment.identification}</strong></article>
                          <article><span>Servicio</span><strong>{LAB_SERVICE_TYPE_LABELS[equipment.service_type] || '-'}</strong></article>
                          <article><span>Folio</span><strong>{equipment.certificate_folio || '-'}</strong></article>
                          <article><span>Estado folio</span><strong>{LAB_FOLIO_STATUS_LABELS[equipment.folio_status] || equipment.folio_status}</strong></article>
                          <article><span>Hoja</span><strong>{sheet ? `R${sheet.revision_number} · ${LAB_FIELD_SHEET_STATUS_LABELS[sheet.status] || sheet.status}` : 'Sin hoja'}</strong></article>
                        </div>
                        <div className="toolbar-actions ets-lab-equipment-card__actions">
                          {permissions.canReadFieldSheets && sheet?.has_final_pdf ? (
                            <button
                              className="table-button"
                              onClick={() => run(() => viewLabPdf(fieldSheetPdfLoader(serviceOrderId, sheet.id), (e) => setError(e.message)))}
                              type="button"
                            >
                              Ver hoja
                            </button>
                          ) : null}
                          {permissions.canRequestCorrection && correctionMode ? (
                            <button
                              className="table-button"
                              onClick={() => setCorrectionTarget({ equipment, workOrderFolio: workOrder.folio, mode: correctionMode })}
                              type="button"
                            >
                              Enviar a corrección
                            </button>
                          ) : null}
                        </div>
                      </article>
                    );
                  }) : <div className="clients-empty">Esta OT no tiene equipos activos.</div>}
                </div>
              </article>
            );
          })}
        </>
      ) : null}

      {picker ? (
        <LinkPicker
          mode={picker}
          onCancel={() => setPicker(null)}
          onDone={() => afterLinkChange(picker === 'replace' ? 'Vínculo MYC Mobile actualizado.' : 'Servicio MYC Mobile vinculado.')}
          serviceOrderId={serviceOrderId}
        />
      ) : null}
      {correctionTarget ? (
        <EtsMobileCorrectionDialog
          onCancel={() => setCorrectionTarget(null)}
          onDone={(next) => {
            setCorrectionTarget(null);
            applyProjection(next, 'Hoja enviada a corrección: MYC Mobile ya tiene la nueva revisión editable.');
          }}
          serviceOrderId={serviceOrderId}
          target={correctionTarget}
        />
      ) : null}
      {detailEquipmentId ? (
        <EtsMobileEquipmentDetail
          equipmentId={detailEquipmentId}
          onChanged={(next) => applyProjection(next)}
          onClose={() => setDetailEquipmentId(null)}
          serviceOrderId={serviceOrderId}
          user={user}
        />
      ) : null}
    </section>
  );
}

export function EtsMobileExecutionDialog({ serviceOrderId, serviceOrderFolio, user, onClose, onLinkChanged, onExecutionChanged }) {
  return (
    <EtsMobileModal
      eyebrow="Ejecución técnica MYC Mobile"
      onClose={onClose}
      subtitle={`${serviceOrderFolio || `ETS ${serviceOrderId}`} · vista administrativa de sólo lectura`}
      title="Servicio / grupo LAB"
    >
      <EtsMobileExecutionPanel
        onExecutionChanged={onExecutionChanged}
        onLinkChanged={onLinkChanged}
        serviceOrderId={serviceOrderId}
        user={user}
      />
    </EtsMobileModal>
  );
}
