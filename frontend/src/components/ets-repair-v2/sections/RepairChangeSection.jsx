import React, {
  useMemo,
  useState,
} from 'react';

import {
  GitPullRequestArrow,
  Scale,
} from 'lucide-react';

import {
  requestRepairChange,
  resolveRepairChange,
} from '../../../services/api.js';

import {
  canExecuteRepair,
  formatDateTime,
  safeArray,
  safeText,
} from './repairShared.js';

import {
  hasPermission,
} from '../../../utils/accessControl.js';


const CHANGE_TYPE_LABELS = {
  additional_scope: 'Alcance adicional',
  investigation: 'Investigación administrativa',
};

const CHANGE_STATUS_LABELS = {
  requested: 'Pendiente',
  approved: 'Aprobada',
  rejected: 'Rechazada',
  linked: 'Vinculada a otro ETS',
};

const UNAVAILABLE_STATUSES = new Set(['closed', 'cancelled']);


function RepairChangeSection({
  order,
  execution,
  user,
  isBusy = false,
  onBusyChange,
  onBoardChange,
  onError,
  onNotice,
}) {
  const [changeType, setChangeType] = useState('additional_scope');
  const [summary, setSummary] = useState('');

  const [resolutionDrafts, setResolutionDrafts] = useState({});

  const canRequest =
    Boolean(execution?.technician_id) &&
    !UNAVAILABLE_STATUSES.has(execution?.status) &&
    canExecuteRepair(execution, user);

  const canAuthorize = hasPermission(user, 'service_orders.repair.authorize');

  const changes = useMemo(
    () => safeArray(execution?.changes).slice().reverse(),
    [execution],
  );

  const pendingChanges = changes.filter((change) => change.status === 'requested');

  const isBlockingClosure = safeArray(execution?.closure_blockers).some(
    (blocker) => blocker?.section === 'changes',
  );

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

  async function handleRequest(event) {
    event.preventDefault();

    if (!order?.id || !execution?.id || isBusy) {
      return;
    }

    if (summary.trim().length < 3) {
      reportError('Describe la solicitud de cambio con al menos 3 caracteres.');
      return;
    }

    setBusy(true);
    reportError('');
    reportNotice('');

    try {
      const result = await requestRepairChange(order.id, execution.id, {
        change_type: changeType,
        summary: summary.trim(),
      });

      updateBoard(result);
      setSummary('');

      reportNotice('Solicitud de cambio registrada.');
    } catch (requestError) {
      reportError(
        requestError?.message ||
          'No fue posible registrar la solicitud de cambio.',
      );
    } finally {
      setBusy(false);
    }
  }

  function updateDraft(changeId, field, value) {
    setResolutionDrafts((current) => ({
      ...current,
      [changeId]: {
        ...(current[changeId] || { decision: 'approved', reason: '', linkedServiceOrderId: '' }),
        [field]: value,
      },
    }));
  }

  async function handleResolve(changeId) {
    if (!order?.id || !execution?.id || isBusy) {
      return;
    }

    const draft = resolutionDrafts[changeId] || { decision: 'approved', reason: '' };

    if ((draft.reason || '').trim().length < 3) {
      reportError('Describe la razón de la decisión con al menos 3 caracteres.');
      return;
    }

    const change = changes.find((item) => item.id === changeId);

    if (
      change?.change_type === 'investigation' &&
      draft.decision === 'linked' &&
      !draft.linkedServiceOrderId
    ) {
      reportError('La vinculación de una investigación requiere el ETS destino.');
      return;
    }

    setBusy(true);
    reportError('');
    reportNotice('');

    try {
      const result = await resolveRepairChange(order.id, execution.id, changeId, {
        decision: draft.decision,
        reason: draft.reason.trim(),
        linked_service_order_id: draft.linkedServiceOrderId
          ? Number(draft.linkedServiceOrderId)
          : null,
      });

      updateBoard(result);

      setResolutionDrafts((current) => {
        const next = { ...current };
        delete next[changeId];
        return next;
      });

      reportNotice('Solicitud de cambio resuelta.');
    } catch (requestError) {
      reportError(
        requestError?.message ||
          'No fue posible resolver la solicitud de cambio.',
      );
    } finally {
      setBusy(false);
    }
  }

  if (!canRequest && !changes.length) {
    return null;
  }

  return (
    <section className="repair-v2-stage">
      <header className="repair-v2-stage__heading">
        <div>
          <span>Flujo paralelo</span>
          <h4>Solicitudes de cambio</h4>
          <p>
            Alcance adicional o investigación administrativa. Una solicitud
            pendiente bloquea el cierre del expediente.
          </p>
        </div>

        <span
          className={[
            'repair-v2-stage__state',
            pendingChanges.length ? 'is-waiting' : 'is-done',
          ].join(' ')}
        >
          <GitPullRequestArrow size={15} />
          {pendingChanges.length
            ? `${pendingChanges.length} pendiente${pendingChanges.length === 1 ? '' : 's'}`
            : 'Sin pendientes'}
        </span>
      </header>

      {isBlockingClosure ? (
        <div className="repair-v2-stage__notice">
          Existen solicitudes de cambio pendientes que están bloqueando
          el cierre de este expediente.
        </div>
      ) : null}

      {canRequest ? (
        <form className="repair-v2-form" onSubmit={handleRequest}>
          <label className="repair-v2-form__field">
            Tipo de solicitud

            <select
              disabled={isBusy}
              onChange={(event) => setChangeType(event.target.value)}
              value={changeType}
            >
              {Object.entries(CHANGE_TYPE_LABELS).map(([value, label]) => (
                <option key={value} value={value}>{label}</option>
              ))}
            </select>
          </label>

          <label className="repair-v2-form__field repair-v2-form__field--wide">
            Descripción

            <textarea
              disabled={isBusy}
              onChange={(event) => setSummary(event.target.value)}
              placeholder="Detalle de la solicitud"
              value={summary}
            />
          </label>

          <footer className="repair-v2-form__actions">
            <button className="primary-button" disabled={isBusy} type="submit">
              <GitPullRequestArrow size={16} />
              {isBusy ? 'Registrando...' : 'Solicitar cambio'}
            </button>
          </footer>
        </form>
      ) : null}

      {changes.length ? (
        <div className="repair-v2-list">
          {changes.map((change) => {
            const draft = resolutionDrafts[change.id] || {
              decision: 'approved',
              reason: '',
              linkedServiceOrderId: '',
            };

            return (
              <article
                className={[
                  'repair-v2-list__item',
                  change.status === 'requested' ? 'is-waiting' : '',
                ].join(' ').trim()}
                key={change.id}
              >
                <div className="repair-v2-list__item-header">
                  <strong>
                    {CHANGE_TYPE_LABELS[change.change_type] || change.change_type}
                  </strong>

                  <span
                    className={[
                      'repair-v2-list__badge',
                      change.status === 'requested'
                        ? 'is-waiting'
                        : change.status === 'rejected'
                          ? 'is-blocked'
                          : 'is-done',
                    ].join(' ')}
                  >
                    {CHANGE_STATUS_LABELS[change.status] || change.status}
                  </span>
                </div>

                <p>{change.summary}</p>

                <div className="repair-v2-list__meta">
                  <div>
                    <span>Registrada</span>
                    <strong>{formatDateTime(change.created_at)}</strong>
                  </div>

                  {change.status !== 'requested' ? (
                    <div>
                      <span>Decisión</span>
                      <strong>{safeText(change.decision_reason)}</strong>
                    </div>
                  ) : null}

                  {change.linked_service_order_id ? (
                    <div>
                      <span>ETS vinculado</span>
                      <strong>#{change.linked_service_order_id}</strong>
                    </div>
                  ) : null}
                </div>

                {change.status === 'requested' && canAuthorize ? (
                  <div className="repair-v2-form__group repair-v2-form__group--full">
                    <header>
                      <span>Resolver solicitud</span>
                    </header>

                    <label className="repair-v2-form__field">
                      Decisión

                      <select
                        disabled={isBusy}
                        onChange={(event) =>
                          updateDraft(change.id, 'decision', event.target.value)
                        }
                        value={draft.decision}
                      >
                        <option value="approved">Aprobar</option>
                        <option value="rejected">Rechazar</option>
                        <option value="linked">Vincular a otro ETS</option>
                      </select>
                    </label>

                    {draft.decision === 'linked' ? (
                      <label className="repair-v2-form__field">
                        ETS destino (ID)

                        <input
                          disabled={isBusy}
                          onChange={(event) =>
                            updateDraft(
                              change.id,
                              'linkedServiceOrderId',
                              event.target.value,
                            )
                          }
                          placeholder="ID del ETS de servicio general"
                          type="number"
                          value={draft.linkedServiceOrderId}
                        />
                      </label>
                    ) : null}

                    <label className="repair-v2-form__field repair-v2-form__field--wide">
                      Razón

                      <textarea
                        disabled={isBusy}
                        onChange={(event) =>
                          updateDraft(change.id, 'reason', event.target.value)
                        }
                        placeholder="Justificación de la decisión"
                        value={draft.reason}
                      />
                    </label>

                    <footer className="repair-v2-form__actions">
                      <button
                        className="primary-button"
                        disabled={isBusy}
                        onClick={() => handleResolve(change.id)}
                        type="button"
                      >
                        <Scale size={16} />
                        {isBusy ? 'Guardando...' : 'Registrar decisión'}
                      </button>
                    </footer>
                  </div>
                ) : null}
              </article>
            );
          })}
        </div>
      ) : (
        <div className="repair-v2-list__empty">
          No se han registrado solicitudes de cambio.
        </div>
      )}
    </section>
  );
}

export default RepairChangeSection;
