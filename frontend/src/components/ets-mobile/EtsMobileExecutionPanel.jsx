import React, { useCallback, useEffect, useState } from 'react';
import { createPortal } from 'react-dom';

import {
  downloadServiceOrderMobileFieldSheetPdf,
  getServiceOrderMobileExecution,
  getServiceOrderMobileFieldSheet,
  linkServiceOrderLab,
  replaceServiceOrderLab,
  searchServiceOrderLabCandidates,
  unlinkServiceOrderLab,
} from '../../services/api.js';
import { formatDateTime } from '../../utils/formatters.js';
import {
  LAB_FIELD_SHEET_STATUS_LABELS,
  LAB_FOLIO_STATUS_LABELS,
  LAB_SERVICE_TYPE_LABELS,
  LAB_WORK_ORDER_STATUS_LABELS,
  describeFieldSheetReadOnly,
  getMobileExecutionPermissions,
  summarizeMobileExecution,
} from './mobileExecutionPresentation.js';

// Vista administrativa READ-ONLY de la ejecución técnica MYC Mobile de un ETS.
// El staff ERP puede VER; no existe ningún input que edite datos técnicos LAB.
// Se monta en un portal para no quedar dentro del formulario del Resumen ETS.

function openBlob(blob) {
  const url = URL.createObjectURL(blob);
  window.open(url, '_blank', 'noopener');
  window.setTimeout(() => URL.revokeObjectURL(url), 60_000);
}

function Modal({ children, onClose, title, subtitle, eyebrow = 'MYC Mobile' }) {
  return createPortal(
    <div className="modal-backdrop" role="presentation">
      <section aria-modal="true" className="client-modal quotation-detail-modal ets-mobile-execution-modal" role="dialog">
        <div className="quotation-detail-header">
          <div>
            <p>{eyebrow}</p>
            <h2>{title}</h2>
            {subtitle ? <span>{subtitle}</span> : null}
          </div>
          <button className="icon-text-button" onClick={onClose} type="button">Cerrar</button>
        </div>
        {children}
      </section>
    </div>,
    document.body
  );
}

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
    <Modal
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
    </Modal>
  );
}

function FieldSheetDetail({ serviceOrderId, equipmentId, onClose }) {
  const [detail, setDetail] = useState(null);
  const [error, setError] = useState('');

  useEffect(() => {
    let active = true;
    getServiceOrderMobileFieldSheet(serviceOrderId, equipmentId)
      .then((payload) => { if (active) setDetail(payload); })
      .catch((requestError) => { if (active) setError(requestError.message); });
    return () => { active = false; };
  }, [equipmentId, serviceOrderId]);

  async function viewPdf(fieldSheetId) {
    try {
      const { blob } = await downloadServiceOrderMobileFieldSheetPdf(serviceOrderId, fieldSheetId);
      openBlob(blob);
    } catch (requestError) {
      setError(requestError.message);
    }
  }

  const equipment = detail?.equipment;
  const sheet = detail?.field_sheet;
  return (
    <Modal
      eyebrow="Hoja de Campo MYC Mobile · sólo lectura"
      onClose={onClose}
      subtitle={equipment ? `OT ${detail.work_order_folio} · ${equipment.instrument} · ${equipment.certificate_folio || 'Sin folio'}` : null}
      title="Detalle técnico"
    >
      {error ? <div className="form-error" role="alert">{error}</div> : null}
      {!detail && !error ? <p className="muted">Cargando…</p> : null}
      {detail ? (
        <div className="ets-mobile-readonly" data-readonly="true">
          <p className="muted">
            Vista administrativa. Los datos técnicos sólo se capturan y corrigen en MYC Mobile.
          </p>
          <dl className="ets-mobile-readonly__grid">
            <div><dt>Instrumento</dt><dd>{equipment.instrument}</dd></div>
            <div><dt>Marca / modelo</dt><dd>{[equipment.brand, equipment.model].filter(Boolean).join(' · ')}</dd></div>
            <div><dt>Serie</dt><dd>{equipment.serial_number}</dd></div>
            <div><dt>Identificación</dt><dd>{equipment.identification}</dd></div>
            <div><dt>Servicio</dt><dd>{LAB_SERVICE_TYPE_LABELS[equipment.service_type] || equipment.service_type || '-'}</dd></div>
            <div><dt>Folio</dt><dd>{equipment.certificate_folio || '-'} ({LAB_FOLIO_STATUS_LABELS[equipment.folio_status] || equipment.folio_status})</dd></div>
            {describeFieldSheetReadOnly(sheet).map(([label, value]) => (
              <div key={label}><dt>{label}</dt><dd>{String(value)}</dd></div>
            ))}
          </dl>
          {sheet?.results_rows?.length ? (
            <table className="ets-mobile-readonly__table">
              <thead><tr><th>Sección</th><th>#</th><th>Patrón</th><th>Lecturas</th><th>Unidad</th></tr></thead>
              <tbody>
                {sheet.results_rows.map((row) => (
                  <tr key={row.id ?? `${row.section_key}-${row.row_number}`}>
                    <td>{row.section_key}</td>
                    <td>{row.row_number}</td>
                    <td>{row.pattern_value || '-'}</td>
                    <td>{[row.ibc_value_1, row.ibc_value_2, row.ibc_value_3].filter(Boolean).join(' / ') || '-'}</td>
                    <td>{row.unit || '-'}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          ) : null}
          <h3>Revisiones</h3>
          <ul className="ets-mobile-readonly__revisions">
            {detail.revisions.map((revision) => (
              <li key={revision.id}>
                <span>
                  Revisión {revision.revision_number} · {LAB_FIELD_SHEET_STATUS_LABELS[revision.status] || revision.status}
                  {revision.is_current ? ' · vigente' : ' · histórica'} · {formatDateTime(revision.updated_at)}
                </span>
                {revision.has_final_pdf ? (
                  <button className="table-button" onClick={() => viewPdf(revision.id)} type="button">Ver PDF final</button>
                ) : null}
              </li>
            ))}
          </ul>
        </div>
      ) : null}
    </Modal>
  );
}

export default function EtsMobileExecutionPanel({ serviceOrderId, user, onLinkChanged }) {
  const permissions = getMobileExecutionPermissions(user);
  const [projection, setProjection] = useState(null);
  const [error, setError] = useState('');
  const [notice, setNotice] = useState('');
  const [picker, setPicker] = useState(null);
  const [detailEquipmentId, setDetailEquipmentId] = useState(null);

  const load = useCallback(async () => {
    setError('');
    try {
      setProjection(await getServiceOrderMobileExecution(serviceOrderId));
    } catch (requestError) {
      setError(requestError.message);
    }
  }, [serviceOrderId]);

  useEffect(() => { load(); }, [load]);

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
      openBlob(blob);
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
              <div className="toolbar-actions">
                <button className="table-button" onClick={() => setPicker('replace')} type="button">Cambiar vínculo</button>
                <button className="table-button" onClick={unlink} type="button">Desvincular</button>
              </div>
            ) : null}
          </div>
          {projection.work_orders.map((workOrder) => (
            <article className="ets-field-sheet-work-order is-expanded" key={workOrder.id}>
              <div className="ets-field-sheet-work-order__summary">
                <div>
                  <small>{workOrder.is_root ? 'OT raíz' : 'OT del grupo'}</small>
                  <strong>OT {workOrder.folio}</strong>
                  <span>{workOrder.client_name}</span>
                </div>
                <mark className={`quotation-status status-${workOrder.status}`}>
                  {LAB_WORK_ORDER_STATUS_LABELS[workOrder.status] || workOrder.status}
                </mark>
              </div>
              <div className="ets-field-sheet-work-order__equipment">
                {workOrder.equipment.length ? workOrder.equipment.map((equipment) => {
                  const sheet = equipment.field_sheet;
                  return (
                    <article className="ets-field-sheet-equipment-row" key={equipment.id}>
                      <div>
                        <strong>{equipment.position}. {equipment.instrument}</strong>
                        <span>{[equipment.brand, equipment.model].filter(Boolean).join(' · ')}</span>
                      </div>
                      <dl>
                        <div><dt>Serie</dt><dd>{equipment.serial_number}</dd></div>
                        <div><dt>Identificación</dt><dd>{equipment.identification}</dd></div>
                        <div><dt>Servicio</dt><dd>{LAB_SERVICE_TYPE_LABELS[equipment.service_type] || '-'}</dd></div>
                        <div><dt>Folio</dt><dd>{equipment.certificate_folio || '-'}</dd></div>
                        <div><dt>Estado folio</dt><dd>{LAB_FOLIO_STATUS_LABELS[equipment.folio_status] || equipment.folio_status}</dd></div>
                        <div><dt>Hoja</dt><dd>{sheet ? `R${sheet.revision_number} · ${LAB_FIELD_SHEET_STATUS_LABELS[sheet.status] || sheet.status}` : 'Sin hoja'}</dd></div>
                      </dl>
                      <div className="toolbar-actions">
                        {permissions.canReadFieldSheets ? (
                          <button className="table-button" onClick={() => setDetailEquipmentId(equipment.id)} type="button">Ver hoja</button>
                        ) : null}
                        {permissions.canReadFieldSheets && sheet?.has_final_pdf ? (
                          <button className="table-button" onClick={() => viewPdf(sheet.id)} type="button">Ver PDF final</button>
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
      {detailEquipmentId ? (
        <FieldSheetDetail
          equipmentId={detailEquipmentId}
          onClose={() => setDetailEquipmentId(null)}
          serviceOrderId={serviceOrderId}
        />
      ) : null}
    </section>
  );
}

export function EtsMobileExecutionDialog({ serviceOrderId, serviceOrderFolio, user, onClose, onLinkChanged }) {
  return (
    <Modal
      eyebrow="Ejecución técnica MYC Mobile"
      onClose={onClose}
      subtitle={`${serviceOrderFolio || `ETS ${serviceOrderId}`} · vista administrativa de sólo lectura`}
      title="Servicio / grupo LAB"
    >
      <EtsMobileExecutionPanel onLinkChanged={onLinkChanged} serviceOrderId={serviceOrderId} user={user} />
    </Modal>
  );
}
