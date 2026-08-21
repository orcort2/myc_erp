import React, { useState } from 'react';

import {
  AlertTriangle,
  CircleX,
  FileCheck2,
  FileDown,
  Lock,
} from 'lucide-react';

import {
  cancelRepairExecution,
  closeRepair,
  downloadRepairReport,
  getRepairBoard,
  signRepairReport,
} from '../../../services/api.js';

import SignaturePad from '../../signatures/SignaturePad.jsx';
import '../../signatures/signature.css';

import {
  hasPermission,
} from '../../../utils/accessControl.js';

import {
  CLIENT_DECISION_LABELS,
  formatDateTime,
  safeArray,
  safeText,
  triggerBlobDownload,
} from './repairShared.js';


const REPORTABLE_STATUSES = new Set([
  'technically_completed',
  'equipment_not_suitable',
  'pending_release',
  'closed',
]);

const SIGNABLE_STATUSES = new Set([
  'technically_completed',
  'equipment_not_suitable',
]);


function RepairClosureSection({
  order,
  execution,
  user,
  isBusy = false,
  onBusyChange,
  onBoardChange,
  onError,
  onNotice,
}) {
  const [signerName, setSignerName] = useState('');
  const [signatureDataUrl, setSignatureDataUrl] = useState('');
  const [clientDecision, setClientDecision] = useState('acknowledged');
  const [cancelReason, setCancelReason] = useState('');
  const [showCancelForm, setShowCancelForm] = useState(false);

  const canManage = hasPermission(user, 'service_orders.repair.manage');
  const canSign = hasPermission(user, 'service_orders.repair.sign');
  const canClose = hasPermission(user, 'service_orders.repair.close');

  const canGenerateReport = REPORTABLE_STATUSES.has(execution?.status);

  const canSignReport =
    SIGNABLE_STATUSES.has(execution?.status) &&
    execution?.report_status === 'generated';

  const isSigned = execution?.report_status === 'signed';

  const canCloseNow =
    execution?.status === 'pending_release' &&
    !safeArray(execution?.closure_blockers).length;

  const canCancel =
    !['closed', 'cancelled'].includes(execution?.status) &&
    !safeArray(execution?.interventions).length;

  const isClosed = execution?.status === 'closed';
  const isCancelled = execution?.status === 'cancelled';

  function setBusy(value) {
    if (typeof onBusyChange === 'function') {
      onBusyChange(value);
    }
  }

  function reportError(message) {
    if (typeof onError === 'function') {
      onError(message);
    }
  }

  function reportNotice(message) {
    if (typeof onNotice === 'function') {
      onNotice(message);
    }
  }

  function updateBoard(result) {
    if (result && typeof onBoardChange === 'function') {
      onBoardChange(result);
    }
  }

  async function handleGenerateReport() {
    if (!order?.id || !execution?.id || isBusy) {
      return;
    }

    setBusy(true);
    reportError('');
    reportNotice('');

    try {
      const result = await downloadRepairReport(order.id, execution.id);

      if (result?.blob) {
        triggerBlobDownload(
          result.blob,
          result.filename || `reparacion-${execution.id}.pdf`,
        );
      }

      // El endpoint de reporte devuelve el PDF, no el board actualizado.
      // El backend versiona el reporte e invalida cualquier firma previa,
      // así que refrescamos el board para reflejar ese nuevo estado.
      const refreshedBoard = await getRepairBoard(order.id);
      updateBoard(refreshedBoard);

      reportNotice('Reporte técnico generado y descargado.');
    } catch (requestError) {
      reportError(
        requestError?.message || 'No fue posible generar el reporte.',
      );
    } finally {
      setBusy(false);
    }
  }

  async function handleSign(event) {
    event.preventDefault();

    if (!order?.id || !execution?.id || isBusy) {
      return;
    }

    if (!signerName.trim() || signerName.trim().length < 2) {
      reportError('Captura el nombre de quien firma.');
      return;
    }

    if (!signatureDataUrl) {
      reportError('Captura la firma antes de continuar.');
      return;
    }

    setBusy(true);
    reportError('');
    reportNotice('');

    try {
      const result = await signRepairReport(order.id, execution.id, {
        signer_name: signerName.trim(),
        signature_data_url: signatureDataUrl,
        client_decision: clientDecision,
      });

      updateBoard(result);
      setSignerName('');
      setSignatureDataUrl('');

      reportNotice('Reporte firmado. La ejecución queda pendiente de liberación.');
    } catch (requestError) {
      reportError(
        requestError?.message || 'No fue posible firmar el reporte.',
      );
    } finally {
      setBusy(false);
    }
  }

  async function handleClose() {
    if (!order?.id || !execution?.id || isBusy) {
      return;
    }

    setBusy(true);
    reportError('');
    reportNotice('');

    try {
      const result = await closeRepair(order.id, execution.id);

      updateBoard(result);

      reportNotice('Expediente de reparación cerrado.');
    } catch (requestError) {
      reportError(
        requestError?.message || 'No fue posible cerrar la ejecución.',
      );
    } finally {
      setBusy(false);
    }
  }

  async function handleCancel(event) {
    event.preventDefault();

    if (!order?.id || !execution?.id || isBusy) {
      return;
    }

    if (cancelReason.trim().length < 10) {
      reportError('Describe el motivo de cancelación con al menos 10 caracteres.');
      return;
    }

    setBusy(true);
    reportError('');
    reportNotice('');

    try {
      const result = await cancelRepairExecution(order.id, execution.id, {
        reason: cancelReason.trim(),
      });

      updateBoard(result);
      setCancelReason('');
      setShowCancelForm(false);

      reportNotice('Ejecución cancelada.');
    } catch (requestError) {
      reportError(
        requestError?.message || 'No fue posible cancelar la ejecución.',
      );
    } finally {
      setBusy(false);
    }
  }

  if (isCancelled) {
    return (
      <section className="repair-v2-stage">
        <header className="repair-v2-stage__heading">
          <div>
            <span>Etapa 9</span>
            <h4>Cierre</h4>
          </div>

          <span className="repair-v2-stage__state is-blocked">
            <CircleX size={15} />
            Cancelada
          </span>
        </header>

        <div className="repair-v2-list__item">
          <p><strong>Motivo:</strong> {safeText(execution?.cancellation_reason)}</p>
          <p><strong>Fecha:</strong> {formatDateTime(execution?.cancelled_at)}</p>
        </div>
      </section>
    );
  }

  return (
    <section className="repair-v2-stage">
      <header className="repair-v2-stage__heading">
        <div>
          <span>Etapa 9</span>
          <h4>Cierre</h4>
          <p>
            Reporte técnico, firma del cliente y liberación final
            del expediente.
          </p>
        </div>

        <span
          className={[
            'repair-v2-stage__state',
            isClosed ? 'is-done' : 'is-waiting',
          ].join(' ')}
        >
          <Lock size={15} />
          {isClosed ? 'Cerrado' : 'En proceso'}
        </span>
      </header>

      {/* ================= REPORTE ================= */}

      <div className="repair-v2-form__group repair-v2-form__group--full">
        <header>
          <span>Reporte técnico</span>
          <p>
            Versión vigente: {execution?.report_version || 0} ·{' '}
            Estado: {execution?.report_status || 'pending'}
            {execution?.report_generated_at
              ? ` · Generado ${formatDateTime(execution.report_generated_at)}`
              : ''}
          </p>
        </header>

        {isSigned ? (
          <div className="repair-v2-stage__notice">
            Regenerar el reporte invalidará la firma actual y requerirá
            firmar nuevamente.
          </div>
        ) : null}

        {canGenerateReport ? (
          canManage ? (
            <footer className="repair-v2-form__actions">
              <button
                className="primary-button"
                disabled={isBusy}
                onClick={handleGenerateReport}
                type="button"
              >
                <FileDown size={16} />
                {isBusy ? 'Generando...' : 'Generar / descargar reporte PDF'}
              </button>
            </footer>
          ) : (
            <div className="repair-v2-stage__notice">
              No tienes permiso para generar el reporte técnico.
            </div>
          )
        ) : (
          <div className="repair-v2-stage__notice">
            El reporte solo puede generarse tras el dictamen técnico.
          </div>
        )}
      </div>

      {/* ================= FIRMA ================= */}

      <div className="repair-v2-form__group repair-v2-form__group--full">
        <header>
          <span>Firma del cliente</span>
          <p>Requiere el reporte técnico vigente ya generado.</p>
        </header>

        {isSigned ? (
          <div className="repair-v2-reception-summary">
            <article>
              <span>Firmado por</span>
              <strong>{safeText(execution?.signer_name)}</strong>
            </article>

            <article>
              <span>Fecha</span>
              <strong>{formatDateTime(execution?.signed_at)}</strong>
            </article>

            <article>
              <span>Decisión del cliente</span>
              <strong>
                {CLIENT_DECISION_LABELS[execution?.client_decision] ||
                  safeText(execution?.client_decision)}
              </strong>
            </article>
          </div>
        ) : canSignReport ? (
          canSign ? (
            <form className="repair-v2-form" onSubmit={handleSign}>
              <div className="repair-v2-form__group--full">
                <SignaturePad
                  label="Firma del cliente"
                  name={signerName}
                  onNameChange={setSignerName}
                  onSignatureChange={setSignatureDataUrl}
                  signedAt={null}
                />
              </div>

              <label className="repair-v2-form__field repair-v2-form__field--wide">
                Decisión del cliente

                <select
                  disabled={isBusy}
                  onChange={(event) => setClientDecision(event.target.value)}
                  value={clientDecision}
                >
                  {Object.entries(CLIENT_DECISION_LABELS).map(
                    ([value, label]) => (
                      <option key={value} value={value}>{label}</option>
                    ),
                  )}
                </select>
              </label>

              <footer className="repair-v2-form__actions">
                <button className="primary-button" disabled={isBusy} type="submit">
                  <FileCheck2 size={16} />
                  {isBusy ? 'Firmando...' : 'Registrar firma'}
                </button>
              </footer>
            </form>
          ) : (
            <div className="repair-v2-stage__notice">
              No tienes permiso para firmar el reporte técnico.
            </div>
          )
        ) : (
          <div className="repair-v2-stage__notice">
            Primero debe generarse el reporte técnico vigente.
          </div>
        )}
      </div>

      {/* ================= CIERRE ================= */}

      <div className="repair-v2-form__group repair-v2-form__group--full">
        <header>
          <span>Liberación final</span>
          <p>Cierra definitivamente el expediente de reparación.</p>
        </header>

        {isClosed ? (
          <div className="repair-v2-reception-summary">
            <article>
              <span>Cerrado</span>
              <strong>{formatDateTime(execution?.closed_at)}</strong>
            </article>

            <article>
              <span>Conclusión</span>
              <strong>
                {execution?.conclusion === 'equipment_not_suitable'
                  ? 'Equipo no apto'
                  : 'Reparado'}
              </strong>
            </article>
          </div>
        ) : (
          <>
            {safeArray(execution?.closure_blockers).length ? (
              <div className="repair-v2-modal__blocker-list">
                {execution.closure_blockers.map((blocker, index) => (
                  <article key={blocker?.field || index}>
                    <AlertTriangle size={14} />
                    <strong>
                      {safeText(blocker?.message, 'Pendiente de cierre')}
                    </strong>
                  </article>
                ))}
              </div>
            ) : null}

            {canClose ? (
              <footer className="repair-v2-form__actions">
                <button
                  className="primary-button"
                  disabled={isBusy || !canCloseNow}
                  onClick={handleClose}
                  type="button"
                >
                  <Lock size={16} />
                  {isBusy ? 'Cerrando...' : 'Cerrar reparación'}
                </button>
              </footer>
            ) : (
              <div className="repair-v2-stage__notice">
                No tienes permiso para cerrar esta ejecución.
              </div>
            )}
          </>
        )}
      </div>

      {/* ================= CANCELACIÓN ================= */}

      {canCancel && canManage ? (
        <div className="repair-v2-danger-zone">
          <header>
            <span>Zona de riesgo</span>
            <p>
              Solo puede cancelarse una reparación que aún no ha sido
              intervenida técnicamente. Una vez iniciada la primera
              intervención, debe finalizarse mediante el flujo técnico.
            </p>
          </header>

          {showCancelForm ? (
            <form className="repair-v2-form" onSubmit={handleCancel}>
              <label className="repair-v2-form__field repair-v2-form__field--wide">
                Motivo de cancelación

                <textarea
                  disabled={isBusy}
                  onChange={(event) => setCancelReason(event.target.value)}
                  placeholder="Motivo de la cancelación administrativa"
                  value={cancelReason}
                />
              </label>

              <footer className="repair-v2-form__actions">
                <button
                  className="table-button"
                  disabled={isBusy}
                  onClick={() => setShowCancelForm(false)}
                  type="button"
                >
                  Volver
                </button>

                <button className="danger-button" disabled={isBusy} type="submit">
                  <CircleX size={16} />
                  {isBusy ? 'Cancelando...' : 'Confirmar cancelación'}
                </button>
              </footer>
            </form>
          ) : (
            <button
              className="danger-button"
              disabled={isBusy}
              onClick={() => setShowCancelForm(true)}
              type="button"
            >
              <CircleX size={16} />
              Cancelar reparación
            </button>
          )}
        </div>
      ) : null}
    </section>
  );
}

export default RepairClosureSection;
