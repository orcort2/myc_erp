import React, { useState } from 'react';

import {
  Gavel,
  ShieldAlert,
} from 'lucide-react';

import {
  concludeRepairEvaluation,
} from '../../../services/api.js';

import {
  canExecuteRepair,
  getUserDisplayName,
} from './repairShared.js';


function RepairVerdictSection({
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
  const [conclusion, setConclusion] = useState('repaired');
  const [reason, setReason] = useState('');

  const isOwnTechnician = canExecuteRepair(execution, user);

  const isAvailable = execution?.status === 'in_evaluation';

  const isBeforeEvaluation = [
    'pending_arrival',
    'pending_assignment',
    'assigned',
  ].includes(execution?.status);

  const hasVerdict = Boolean(execution?.conclusion);

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

  async function handleSubmit(event) {
    event.preventDefault();

    if (!order?.id || !execution?.id || isBusy) {
      return;
    }

    if (
      conclusion === 'equipment_not_suitable' &&
      reason.trim().length < 10
    ) {
      reportError(
        'La conclusión "equipo no apto" requiere una justificación de al menos 10 caracteres.',
      );

      return;
    }

    setBusy(true);
    reportError('');
    reportNotice('');

    try {
      const result = await concludeRepairEvaluation(order.id, execution.id, {
        conclusion,
        conclusion_reason: reason.trim() || null,
      });

      updateBoard(result);
      setReason('');

      reportNotice('Dictamen técnico registrado.');
    } catch (requestError) {
      reportError(
        requestError?.message ||
          'No fue posible registrar el dictamen.',
      );
    } finally {
      setBusy(false);
    }
  }

  /* =======================================================
     BLOQUEADO: aún no en evaluación
     ======================================================= */

  if (isBeforeEvaluation) {
    return (
      <section className="repair-v2-stage">
        <header className="repair-v2-stage__heading">
          <div>
            <h4>Dictamen</h4>
          </div>

          <span className="repair-v2-stage__state is-pending">
            <Gavel size={15} />
            Aún no disponible
          </span>
        </header>

        <div className="repair-v2-stage__notice">
          El dictamen técnico solo puede registrarse durante
          la evaluación del equipo.
        </div>
      </section>
    );
  }

  /* =======================================================
     YA DICTAMINADO: solo lectura
     ======================================================= */

  if (!isAvailable) {
    if (!hasVerdict) {
      return null;
    }

    const isNotSuitable = execution.conclusion === 'equipment_not_suitable';

    return (
      <section className="repair-v2-stage">
        <header className="repair-v2-stage__heading">
          <div>
            <h4>Dictamen</h4>
          </div>

          <span
            className={[
              'repair-v2-stage__state',
              isNotSuitable ? 'is-blocked' : 'is-done',
            ].join(' ')}
          >
            {isNotSuitable ? <ShieldAlert size={15} /> : <Gavel size={15} />}
            {isNotSuitable ? 'Equipo no apto' : 'Reparable'}
          </span>
        </header>

        <div className="repair-v2-list__item">
          <p>
            <strong>Conclusión:</strong>{' '}
            {isNotSuitable ? 'Equipo no apto para reparación' : 'Equipo reparable'}
          </p>

          {execution.conclusion_reason ? (
            <p><strong>Justificación:</strong> {execution.conclusion_reason}</p>
          ) : null}
        </div>
      </section>
    );
  }

  /* =======================================================
     DISPONIBLE: formulario de dictamen
     ======================================================= */

  return (
    <section className="repair-v2-stage">
      <header className="repair-v2-stage__heading">
        <div>
          <h4>Dictamen</h4>
          <p>
            Conclusión técnica de la evaluación. Un dictamen de
            equipo no apto salta reparación y pruebas.
          </p>
        </div>

        <span className="repair-v2-stage__state is-waiting">
          <Gavel size={15} />
          Pendiente
        </span>
      </header>

      {!isOwnTechnician ? (
        <div className="repair-v2-stage__notice">
          Esta reparación está asignada a{' '}
          {getUserDisplayName(users, execution?.technician_id)}.
          Solo ese técnico puede registrar el dictamen.
        </div>
      ) : (
        <form className="repair-v2-form" onSubmit={handleSubmit}>
          <label className="repair-v2-form__field repair-v2-form__field--wide">
            Conclusión

            <select
              disabled={isBusy}
              onChange={(event) => setConclusion(event.target.value)}
              value={conclusion}
            >
              <option value="repaired">Equipo reparable</option>
              <option value="equipment_not_suitable">
                Equipo no apto para reparación
              </option>
            </select>
          </label>

          <label className="repair-v2-form__field repair-v2-form__field--wide">
            Justificación
            {conclusion === 'equipment_not_suitable' ? ' (obligatoria)' : ' (opcional)'}

            <textarea
              disabled={isBusy}
              onChange={(event) => setReason(event.target.value)}
              placeholder="Razón del dictamen"
              value={reason}
            />
          </label>

          <footer className="repair-v2-form__actions">
            <button className="primary-button" disabled={isBusy} type="submit">
              <Gavel size={16} />
              {isBusy ? 'Guardando...' : 'Registrar dictamen'}
            </button>
          </footer>
        </form>
      )}
    </section>
  );
}

export default RepairVerdictSection;
