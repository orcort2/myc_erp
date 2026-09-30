import React, { useCallback, useEffect, useState } from 'react';

import { getServiceOrderMobileFieldSheet } from '../../services/api.js';
import { formatDateTime } from '../../utils/formatters.js';
import EtsMobileCorrectionDialog from './EtsMobileCorrectionDialog.jsx';
import EtsMobileModal from './EtsMobileModal.jsx';
import { fieldSheetPdfLoader, viewLabPdf } from './labDocumentActions.js';
import {
  LAB_FIELD_SHEET_STATUS_LABELS,
  correctionModeFor,
  describeCaptureValues,
  describeDocumentaryClient,
  describeEquipmentReadOnly,
  describeFieldSheetSections,
  describeResultSections,
  getMobileExecutionPermissions,
} from './mobileExecutionPresentation.js';

// Detalle técnico READ-ONLY de un equipo LAB (identidad, cliente documental,
// Hoja de Campo, resultados y revisiones con PDF final). Único para la vista
// "Ejecución técnica MYC Mobile" y para Captura. Sin inputs ni PATCH: la
// única acción es administrativa ("Enviar a corrección", según permiso).

// Patrón ERP read-only-grid (article/span/strong); sin inputs.
function ReadOnlyGrid({ rows }) {
  return (
    <div className="read-only-grid ets-lab-readonly-grid">
      {rows.map(([label, value]) => (
        <article key={label}><span>{label}</span><strong>{value}</strong></article>
      ))}
    </div>
  );
}

export default function EtsMobileEquipmentDetail({ serviceOrderId, equipmentId, user, onClose, onChanged }) {
  const permissions = getMobileExecutionPermissions(user);
  const [detail, setDetail] = useState(null);
  const [error, setError] = useState('');
  const [notice, setNotice] = useState('');
  const [correcting, setCorrecting] = useState(false);

  const load = useCallback(async () => {
    setError('');
    try {
      setDetail(await getServiceOrderMobileFieldSheet(serviceOrderId, equipmentId));
    } catch (requestError) {
      setError(requestError.message);
    }
  }, [equipmentId, serviceOrderId]);

  useEffect(() => { load(); }, [load]);

  async function viewPdf(fieldSheetId) {
    try {
      await viewLabPdf(fieldSheetPdfLoader(serviceOrderId, fieldSheetId), (problem) => setError(problem.message));
    } catch (requestError) {
      setError(requestError.message);
    }
  }

  const equipment = detail?.equipment;
  const sheet = detail?.field_sheet;
  const correctionMode = detail
    ? correctionModeFor({ status: detail.work_order_status }, { field_sheet: sheet })
    : null;
  const canCorrect = permissions.canRequestCorrection && Boolean(correctionMode);
  const currentRevision = detail?.revisions?.find((revision) => revision.is_current);

  return (
    <EtsMobileModal
      eyebrow="Detalle técnico MYC Mobile · sólo lectura"
      onClose={onClose}
      subtitle={equipment ? `OT ${detail.work_order_folio} · ${equipment.position}. ${equipment.instrument} · ${equipment.certificate_folio || 'Sin folio'}` : null}
      title="Equipo y Hoja de Campo"
    >
      {error ? <div className="form-error" role="alert">{error}</div> : null}
      {notice ? <div className="form-notice" role="status">{notice}</div> : null}
      {!detail && !error ? <p className="muted">Cargando…</p> : null}
      {detail ? (
        <div className="ets-lab-detail" data-readonly="true">
          <div className="ets-lab-detail__toolbar">
            <p className="muted">Vista administrativa. Los datos técnicos sólo se capturan y corrigen en MYC Mobile.</p>
            <div className="toolbar-actions">
              {currentRevision?.has_final_pdf ? (
                <button className="table-button" onClick={() => viewPdf(currentRevision.id)} type="button">Ver PDF final</button>
              ) : null}
              {canCorrect ? (
                <button className="table-button table-button--primary" onClick={() => setCorrecting(true)} type="button">
                  Enviar a corrección
                </button>
              ) : null}
            </div>
          </div>

          <section className="quotation-section ets-lab-detail__section">
            <div className="quotation-section__title"><div><p>Equipo</p><h3>Identidad y recepción</h3></div></div>
            <ReadOnlyGrid rows={describeEquipmentReadOnly(equipment)} />
          </section>
          <section className="quotation-section ets-lab-detail__section">
            <div className="quotation-section__title"><div><p>Cliente documental</p><h3>Destinatario del certificado</h3></div></div>
            <ReadOnlyGrid rows={describeDocumentaryClient(equipment)} />
          </section>

          <section className="quotation-section ets-lab-detail__section">
            <div className="quotation-section__title"><div><p>Hoja de Campo</p><h3>Datos técnicos capturados en MYC Mobile</h3></div></div>
            {!sheet ? <p className="muted">El equipo todavía no tiene Hoja de Campo vigente.</p> : null}
            {describeFieldSheetSections(sheet).map((section) => (
              <div className="ets-lab-detail__group" key={section.title}>
                <h4>{section.title}</h4>
                <ReadOnlyGrid rows={section.rows} />
              </div>
            ))}
            {describeCaptureValues(sheet).length ? (
              <div className="ets-lab-detail__group">
                <h4>Datos capturados</h4>
                <ReadOnlyGrid rows={describeCaptureValues(sheet)} />
              </div>
            ) : null}
            {describeResultSections(sheet).map((section) => (
              <div className="ets-lab-detail__group" key={section.key}>
                <h4>{section.title}</h4>
                <div className="ets-lab-table-wrap">
                  <table className="ets-lab-table">
                    <thead>
                      <tr><th>#</th>{section.columns.map((column) => <th key={column.key}>{column.label}</th>)}</tr>
                    </thead>
                    <tbody>
                      {section.rows.map((row) => (
                        <tr key={row.id}>
                          <td>{row.label}</td>
                          {row.cells.map((cell, index) => <td key={section.columns[index].key}>{cell || '-'}</td>)}
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>
            ))}
          </section>

          <section className="quotation-section ets-lab-detail__section">
            <div className="quotation-section__title"><div><p>Revisiones</p><h3>Historial y PDF final</h3></div></div>
            <ul className="ets-lab-revisions">
              {detail.revisions.map((revision) => (
                <li key={revision.id}>
                  <span>
                    Revisión {revision.revision_number} · {LAB_FIELD_SHEET_STATUS_LABELS[revision.status] || revision.status}
                    {revision.is_current ? ' · vigente' : ' · histórica'} · actualizada {formatDateTime(revision.updated_at)}
                    {revision.final_pdf_generated_at ? ` · PDF final ${formatDateTime(revision.final_pdf_generated_at)}` : ''}
                  </span>
                  {revision.has_final_pdf ? (
                    <button className="table-button" onClick={() => viewPdf(revision.id)} type="button">Ver PDF final</button>
                  ) : null}
                </li>
              ))}
            </ul>
          </section>
        </div>
      ) : null}
      {correcting && detail ? (
        <EtsMobileCorrectionDialog
          onCancel={() => setCorrecting(false)}
          onDone={async (projection) => {
            setCorrecting(false);
            setNotice('Hoja enviada a corrección: MYC Mobile ya tiene la nueva revisión editable.');
            await load();
            onChanged?.(projection);
          }}
          serviceOrderId={serviceOrderId}
          target={{ equipment, workOrderFolio: detail.work_order_folio, mode: correctionMode }}
        />
      ) : null}
    </EtsMobileModal>
  );
}
