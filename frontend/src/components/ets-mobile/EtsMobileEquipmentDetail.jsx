import React, { useCallback, useEffect, useState } from 'react';

import {
  downloadServiceOrderMobileFieldSheetPdf,
  getServiceOrderMobileFieldSheet,
} from '../../services/api.js';
import { formatDateTime } from '../../utils/formatters.js';
import EtsMobileCorrectionDialog from './EtsMobileCorrectionDialog.jsx';
import EtsMobileModal, { openPdfBlob } from './EtsMobileModal.jsx';
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

function ReadOnlyGrid({ rows }) {
  return (
    <dl className="ets-mobile-readonly__grid">
      {rows.map(([label, value]) => (
        <div key={label}><dt>{label}</dt><dd>{value}</dd></div>
      ))}
    </dl>
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
      const { blob } = await downloadServiceOrderMobileFieldSheetPdf(serviceOrderId, fieldSheetId);
      openPdfBlob(blob);
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
        <div className="ets-mobile-readonly" data-readonly="true">
          <div className="ets-mobile-readonly__toolbar">
            <p className="muted">Vista administrativa. Los datos técnicos sólo se capturan y corrigen en MYC Mobile.</p>
            <div className="ets-mobile-equipment-card__actions">
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

          <section className="ets-mobile-readonly__section">
            <h3>Equipo</h3>
            <ReadOnlyGrid rows={describeEquipmentReadOnly(equipment)} />
          </section>
          <section className="ets-mobile-readonly__section">
            <h3>Cliente documental</h3>
            <ReadOnlyGrid rows={describeDocumentaryClient(equipment)} />
          </section>

          <section className="ets-mobile-readonly__section">
            <h3>Hoja de Campo</h3>
            {!sheet ? <p className="muted">El equipo todavía no tiene Hoja de Campo vigente.</p> : null}
            {describeFieldSheetSections(sheet).map((section) => (
              <div className="ets-mobile-readonly__group" key={section.title}>
                <h4>{section.title}</h4>
                <ReadOnlyGrid rows={section.rows} />
              </div>
            ))}
            {describeCaptureValues(sheet).length ? (
              <div className="ets-mobile-readonly__group">
                <h4>Datos capturados</h4>
                <ReadOnlyGrid rows={describeCaptureValues(sheet)} />
              </div>
            ) : null}
            {describeResultSections(sheet).map((section) => (
              <div className="ets-mobile-readonly__group" key={section.key}>
                <h4>{section.title}</h4>
                <div className="ets-mobile-readonly__table-wrap">
                  <table className="ets-mobile-readonly__table">
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

          <section className="ets-mobile-readonly__section">
            <h3>Revisiones</h3>
            <ul className="ets-mobile-readonly__revisions">
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
