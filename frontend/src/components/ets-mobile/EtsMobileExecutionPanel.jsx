import React, { useCallback, useEffect, useState } from 'react';

import {
  cancelServiceOrderMobileWorkOrder,
  downloadServiceOrderMobileFieldSheetPdf,
  getServiceOrderMobileExecution,
  linkServiceOrderLab,
  replaceServiceOrderLab,
  restoreServiceOrderMobileWorkOrder,
  searchServiceOrderLabCandidates,
  unlinkServiceOrderLab,
} from '../../services/api.js';
import EtsMobileCorrectionDialog from './EtsMobileCorrectionDialog.jsx';
import EtsMobileEquipmentDetail from './EtsMobileEquipmentDetail.jsx';
import EtsMobileModal, { openPdfBlob } from './EtsMobileModal.jsx';
import {
  LAB_FIELD_SHEET_STATUS_LABELS,
  LAB_FOLIO_STATUS_LABELS,
  LAB_SERVICE_TYPE_LABELS,
  LAB_WORK_ORDER_STATUS_LABELS,
  correctionModeFor,
  getMobileExecutionPermissions,
  summarizeMobileExecution,
} from './mobileExecutionPresentation.js';

// Vista administrativa READ-ONLY de la ejecución técnica MYC Mobile de un ETS.
// El staff ERP puede VER; no existe ningún input que edite datos técnicos LAB.
// El detalle de equipo es el componente único EtsMobileEquipmentDetail.
// Clases propias (.ets-mobile-work-order / .ets-mobile-equipment-card): no
// reutiliza los grids rígidos del flujo legacy de Hojas de Campo.

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

  async function unlink() {
    const reason = window.prompt('Motivo para desvincular el servicio MYC Mobile');
    if (!reason?.trim()) return;
    try {
      await unlinkServiceOrderLab(serviceOrderId, reason.trim());
      await afterLinkChange('Servicio MYC Mobile desvinculado; el historial se conserva.');
    } catch (requestError) {
      setError(requestError.message);
    }
  }

  async function viewPdf(fieldSheetId) {
    try {
      const { blob } = await downloadServiceOrderMobileFieldSheetPdf(serviceOrderId, fieldSheetId);
      openPdfBlob(blob);
    } catch (requestError) {
      setError(requestError.message);
    }
  }

  async function cancelWorkOrder(workOrder) {
    const reason = window.prompt(`Motivo para cancelar la OT ${workOrder.folio} en MYC Mobile`);
    if (!reason?.trim()) return;
    try {
      applyProjection(
        await cancelServiceOrderMobileWorkOrder(serviceOrderId, workOrder.id, reason.trim()),
        `OT ${workOrder.folio} cancelada; su historial técnico se conserva.`,
      );
    } catch (requestError) {
      setError(requestError.message);
    }
  }

  async function restoreWorkOrder(workOrder) {
    try {
      applyProjection(
        await restoreServiceOrderMobileWorkOrder(serviceOrderId, workOrder.id),
        `OT ${workOrder.folio} restaurada a su estado anterior.`,
      );
    } catch (requestError) {
      setError(requestError.message);
    }
  }

  const totals = summarizeMobileExecution(projection);
  return (
    <section className="ets-mobile-execution" aria-label="Ejecución técnica MYC Mobile">
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
          <div className="ets-mobile-execution__header">
            <div>
              <strong>Servicio MYC Mobile · OT raíz {projection.root_folio}</strong>
              <span>
                {totals.workOrders} OT · {totals.equipment} equipo(s) · {totals.completedSheets} hoja(s) completada(s) ·{' '}
                {totals.finalPdfs} PDF final(es)
              </span>
            </div>
            {permissions.canManageLink ? (
              <div className="ets-mobile-equipment-card__actions">
                <button className="table-button" onClick={() => setPicker('replace')} type="button">Cambiar vínculo</button>
                <button className="table-button" onClick={unlink} type="button">Desvincular</button>
              </div>
            ) : null}
          </div>
          {projection.work_orders.map((workOrder) => (
            <article className="ets-mobile-work-order" key={workOrder.id}>
              <header className="ets-mobile-work-order__header">
                <div className="ets-mobile-work-order__title">
                  <small>{workOrder.is_root ? 'OT raíz' : 'OT del grupo'}</small>
                  <strong>OT {workOrder.folio}</strong>
                  <span>{workOrder.client_name}</span>
                </div>
                <mark className={`quotation-status status-${workOrder.status} ets-mobile-work-order__status`}>
                  {LAB_WORK_ORDER_STATUS_LABELS[workOrder.status] || workOrder.status}
                </mark>
                {permissions.canCancelWorkOrders ? (
                  <div className="ets-mobile-work-order__actions">
                    {workOrder.status === 'cancelled' ? (
                      <button className="table-button" onClick={() => restoreWorkOrder(workOrder)} type="button">Restaurar OT</button>
                    ) : (
                      <button className="table-button" onClick={() => cancelWorkOrder(workOrder)} type="button">Cancelar OT</button>
                    )}
                  </div>
                ) : null}
              </header>
              <div className="ets-mobile-work-order__equipment">
                {workOrder.equipment.length ? workOrder.equipment.map((equipment) => {
                  const sheet = equipment.field_sheet;
                  const correctionMode = correctionModeFor(workOrder, equipment);
                  return (
                    <article className="ets-mobile-equipment-card" key={equipment.id}>
                      <div className="ets-mobile-equipment-card__identity">
                        {permissions.canReadFieldSheets ? (
                          <button
                            className="ets-mobile-equipment-card__link"
                            onClick={() => setDetailEquipmentId(equipment.id)}
                            type="button"
                          >
                            <strong>{equipment.position}. {equipment.instrument}</strong>
                            <small>Ver detalle</small>
                          </button>
                        ) : (
                          <strong>{equipment.position}. {equipment.instrument}</strong>
                        )}
                        <span>{[equipment.brand, equipment.model].filter(Boolean).join(' · ')}</span>
                      </div>
                      <dl className="ets-mobile-equipment-card__meta">
                        <div><dt>Serie</dt><dd>{equipment.serial_number}</dd></div>
                        <div><dt>Identificación</dt><dd>{equipment.identification}</dd></div>
                        <div><dt>Servicio</dt><dd>{LAB_SERVICE_TYPE_LABELS[equipment.service_type] || '-'}</dd></div>
                        <div><dt>Folio</dt><dd>{equipment.certificate_folio || '-'}</dd></div>
                        <div><dt>Estado folio</dt><dd>{LAB_FOLIO_STATUS_LABELS[equipment.folio_status] || equipment.folio_status}</dd></div>
                        <div><dt>Hoja</dt><dd>{sheet ? `R${sheet.revision_number} · ${LAB_FIELD_SHEET_STATUS_LABELS[sheet.status] || sheet.status}` : 'Sin hoja'}</dd></div>
                      </dl>
                      <div className="ets-mobile-equipment-card__actions">
                        {permissions.canReadFieldSheets && sheet?.has_final_pdf ? (
                          <button className="table-button" onClick={() => viewPdf(sheet.id)} type="button">Ver PDF final</button>
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
          ))}
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
