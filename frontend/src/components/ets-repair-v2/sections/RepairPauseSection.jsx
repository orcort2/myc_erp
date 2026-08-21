import React, {
  useMemo,
  useState,
} from 'react';

import {
  Pause,
  PlayCircle,
} from 'lucide-react';

import {
  addRepairPause,
  resolveRepairPause,
} from '../../../services/api.js';

import {
  canExecuteRepair,
  formatDateTime,
  getUserDisplayName,
  PAUSE_TYPE_LABELS,
  safeArray,
} from './repairShared.js';


const UNAVAILABLE_STATUSES = new Set([
  'pending_arrival',
  'pending_assignment',
  'closed',
  'cancelled',
]);


function RepairPauseSection({
  order,
  execution,
  user,
  users = [],
  isBusy = false,
  onBusyChange,
  onBoardChange,
  onError,
  onNotice,
}) {
  const [form, setForm] = useState({
    pauseType: 'spare_part',
    reason: '',
    responsibleUserId: '',
    tentativeResumeAt: '',
  });

  const [resolutionDrafts, setResolutionDrafts] = useState({});

  const isOwnTechnician = canExecuteRepair(execution, user);

  const isAvailable =
    Boolean(execution?.technician_id) &&
    !UNAVAILABLE_STATUSES.has(execution?.status);

  const pauses = useMemo(
    () => safeArray(execution?.pauses).slice().reverse(),
    [execution],
  );

  const activePauses = pauses.filter((pause) => pause.status === 'active');

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

  async function handleAddPause(event) {
    event.preventDefault();

    if (!order?.id || !execution?.id || isBusy) {
      return;
    }

    if (form.reason.trim().length < 3) {
      reportError('Describe el motivo de la pausa con al menos 3 caracteres.');
      return;
    }

    if (!form.responsibleUserId) {
      reportError('Selecciona el usuario responsable de esta pausa.');
      return;
    }

    setBusy(true);
    reportError('');
    reportNotice('');

    try {
      const result = await addRepairPause(order.id, execution.id, {
        pause_type: form.pauseType,
        reason: form.reason.trim(),
        responsible_user_id: Number(form.responsibleUserId),
        tentative_resume_at: form.tentativeResumeAt
          ? new Date(form.tentativeResumeAt).toISOString()
          : null,
      });

      updateBoard(result);

      setForm({
        pauseType: 'spare_part',
        reason: '',
        responsibleUserId: '',
        tentativeResumeAt: '',
      });

      reportNotice('Pausa registrada.');
    } catch (requestError) {
      reportError(
        requestError?.message || 'No fue posible registrar la pausa.',
      );
    } finally {
      setBusy(false);
    }
  }

  async function handleResolvePause(pauseId) {
    if (!order?.id || !execution?.id || isBusy) {
      return;
    }

    const resolution = (resolutionDrafts[pauseId] || '').trim();

    if (resolution.length < 3) {
      reportError('Describe la resolución con al menos 3 caracteres.');
      return;
    }

    setBusy(true);
    reportError('');
    reportNotice('');

    try {
      const result = await resolveRepairPause(order.id, execution.id, pauseId, {
        resolution,
      });

      updateBoard(result);

      setResolutionDrafts((current) => {
        const next = { ...current };
        delete next[pauseId];
        return next;
      });

      reportNotice('Pausa resuelta.');
    } catch (requestError) {
      reportError(
        requestError?.message || 'No fue posible resolver la pausa.',
      );
    } finally {
      setBusy(false);
    }
  }

  if (!isAvailable) {
    return (
      <section className="repair-v2-stage">
        <header className="repair-v2-stage__heading">
          <div>
            <span>Etapa 6</span>
            <h4>Pausas</h4>
          </div>

          <span className="repair-v2-stage__state is-pending">
            <Pause size={15} />
            Aún no disponible
          </span>
        </header>

        <div className="repair-v2-stage__notice">
          Las pausas operativas requieren un técnico asignado y una
          ejecución en curso.
        </div>
      </section>
    );
  }

  return (
    <section className="repair-v2-stage">
      <header className="repair-v2-stage__heading">
        <div>
          <span>Etapa 6</span>
          <h4>Pausas</h4>
          <p>
            Bloqueantes paralelos (refacción, autorización, decisión
            del cliente, investigación administrativa o almacén). No
            modifican el estado principal de la reparación.
          </p>
        </div>

        <span
          className={[
            'repair-v2-stage__state',
            activePauses.length ? 'is-waiting' : 'is-done',
          ].join(' ')}
        >
          <Pause size={15} />
          {activePauses.length
            ? `${activePauses.length} activa${activePauses.length === 1 ? '' : 's'}`
            : 'Sin pausas activas'}
        </span>
      </header>

      {isOwnTechnician ? (
        <form className="repair-v2-form" onSubmit={handleAddPause}>
          <label className="repair-v2-form__field">
            Tipo de pausa

            <select
              disabled={isBusy}
              onChange={(event) =>
                setForm((current) => ({ ...current, pauseType: event.target.value }))
              }
              value={form.pauseType}
            >
              {Object.entries(PAUSE_TYPE_LABELS).map(([value, label]) => (
                <option key={value} value={value}>{label}</option>
              ))}
            </select>
          </label>

          <label className="repair-v2-form__field">
            Responsable

            <select
              disabled={isBusy}
              onChange={(event) =>
                setForm((current) => ({
                  ...current,
                  responsibleUserId: event.target.value,
                }))
              }
              value={form.responsibleUserId}
            >
              <option value="">Selecciona un usuario</option>

              {safeArray(users)
                .filter((candidate) => candidate?.is_active !== false)
                .map((candidate) => (
                  <option key={candidate.id} value={candidate.id}>
                    {candidate.full_name || candidate.name || candidate.email}
                  </option>
                ))}
            </select>
          </label>

          <label className="repair-v2-form__field repair-v2-form__field--wide">
            Motivo

            <textarea
              disabled={isBusy}
              onChange={(event) =>
                setForm((current) => ({ ...current, reason: event.target.value }))
              }
              placeholder="Detalle del bloqueante"
              value={form.reason}
            />
          </label>

          <label className="repair-v2-form__field">
            Reanudación tentativa (opcional)

            <input
              disabled={isBusy}
              onChange={(event) =>
                setForm((current) => ({
                  ...current,
                  tentativeResumeAt: event.target.value,
                }))
              }
              type="datetime-local"
              value={form.tentativeResumeAt}
            />
          </label>

          <footer className="repair-v2-form__actions">
            <button className="primary-button" disabled={isBusy} type="submit">
              <Pause size={16} />
              {isBusy ? 'Registrando...' : 'Registrar pausa'}
            </button>
          </footer>
        </form>
      ) : (
        <div className="repair-v2-stage__notice">
          Solo el técnico asignado ({getUserDisplayName(users, execution?.technician_id)})
          puede registrar o resolver pausas.
        </div>
      )}

      {pauses.length ? (
        <div className="repair-v2-list">
          {pauses.map((pause) => (
            <article
              className={[
                'repair-v2-list__item',
                pause.status === 'active' ? 'is-waiting' : '',
              ].join(' ').trim()}
              key={pause.id}
            >
              <div className="repair-v2-list__item-header">
                <strong>{PAUSE_TYPE_LABELS[pause.pause_type] || pause.pause_type}</strong>

                <span
                  className={[
                    'repair-v2-list__badge',
                    pause.status === 'active' ? 'is-waiting' : 'is-done',
                  ].join(' ')}
                >
                  {pause.status === 'active' ? 'Activa' : 'Resuelta'}
                </span>
              </div>

              <p>{pause.reason}</p>

              <div className="repair-v2-list__meta">
                <div>
                  <span>Responsable</span>
                  <strong>{getUserDisplayName(users, pause.responsible_user_id)}</strong>
                </div>

                <div>
                  <span>Reanudación tentativa</span>
                  <strong>{formatDateTime(pause.tentative_resume_at)}</strong>
                </div>

                {pause.status !== 'active' ? (
                  <div>
                    <span>Resuelta</span>
                    <strong>{formatDateTime(pause.resolved_at)}</strong>
                  </div>
                ) : null}
              </div>

              {pause.resolution ? (
                <p><strong>Resolución:</strong> {pause.resolution}</p>
              ) : null}

              {pause.status === 'active' && isOwnTechnician ? (
                <div style={{ display: 'flex', gap: '6px' }}>
                  <input
                    disabled={isBusy}
                    onChange={(event) =>
                      setResolutionDrafts((current) => ({
                        ...current,
                        [pause.id]: event.target.value,
                      }))
                    }
                    placeholder="Describe cómo se resolvió"
                    type="text"
                    value={resolutionDrafts[pause.id] || ''}
                  />

                  <button
                    className="table-button"
                    disabled={isBusy}
                    onClick={() => handleResolvePause(pause.id)}
                    type="button"
                  >
                    <PlayCircle size={14} />
                    Resolver
                  </button>
                </div>
              ) : null}
            </article>
          ))}
        </div>
      ) : (
        <div className="repair-v2-list__empty">
          No se han registrado pausas para este expediente.
        </div>
      )}
    </section>
  );
}

export default RepairPauseSection;
