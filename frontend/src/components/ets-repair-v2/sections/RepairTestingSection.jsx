import React, {
  useMemo,
  useState,
} from 'react';

import {
  CheckCircle2,
  FlaskConical,
} from 'lucide-react';

import {
  addRepairTest,
  completeRepairTechnical,
} from '../../../services/api.js';

import {
  canExecuteRepair,
  formatDateTime,
  getUserDisplayName,
  safeArray,
  TEST_RESULT_LABELS,
} from './repairShared.js';


function emptyForm() {
  return {
    testType: '',
    result: 'pass',
    notes: '',
    interventionId: '',
  };
}


function RepairTestingSection({
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
  const [form, setForm] = useState(emptyForm());

  const isOwnTechnician = canExecuteRepair(execution, user);

  const isEquipmentNotSuitable = execution?.conclusion === 'equipment_not_suitable';

  const isBeforeRepair = [
    'pending_arrival',
    'pending_assignment',
    'assigned',
    'in_evaluation',
  ].includes(execution?.status);

  const isAvailable = ['in_repair', 'testing'].includes(execution?.status);

  const openIntervention = useMemo(
    () => safeArray(execution?.interventions).find(
      (intervention) => !intervention?.completed_at,
    ),
    [execution],
  );

  const completedInterventions = useMemo(
    () => safeArray(execution?.interventions).filter(
      (intervention) => intervention?.completed_at,
    ),
    [execution],
  );

  const tests = useMemo(
    () => safeArray(execution?.tests).slice().reverse(),
    [execution],
  );

  const lastTest = execution?.tests?.[execution.tests.length - 1] || null;

  const canCompleteTechnically =
    execution?.status === 'testing' &&
    !openIntervention &&
    lastTest?.result === 'pass';

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

    if (!form.testType.trim()) {
      reportError('Especifica el tipo de prueba realizada.');
      return;
    }

    setBusy(true);
    reportError('');
    reportNotice('');

    try {
      const result = await addRepairTest(order.id, execution.id, {
        test_type: form.testType.trim(),
        result: form.result,
        notes: form.notes.trim() || null,
        intervention_id: form.interventionId ? Number(form.interventionId) : null,
      });

      updateBoard(result);
      setForm(emptyForm());

      reportNotice('Prueba registrada.');
    } catch (requestError) {
      reportError(
        requestError?.message || 'No fue posible registrar la prueba.',
      );
    } finally {
      setBusy(false);
    }
  }

  async function handleCompleteTechnically() {
    if (!order?.id || !execution?.id || isBusy) {
      return;
    }

    setBusy(true);
    reportError('');
    reportNotice('');

    try {
      const result = await completeRepairTechnical(order.id, execution.id);

      updateBoard(result);
      reportNotice('Cierre técnico registrado.');
    } catch (requestError) {
      reportError(
        requestError?.message ||
          'No fue posible completar técnicamente la reparación.',
      );
    } finally {
      setBusy(false);
    }
  }

  function renderHistory() {
    if (!tests.length) {
      return (
        <div className="repair-v2-list__empty">
          Aún no se registran pruebas.
        </div>
      );
    }

    return (
      <div className="repair-v2-list">
        {tests.map((test) => (
          <article className="repair-v2-list__item" key={test.id}>
            <div className="repair-v2-list__item-header">
              <strong>Prueba #{test.sequence} · {test.test_type}</strong>

              <span
                className={[
                  'repair-v2-list__badge',
                  test.result === 'pass'
                    ? 'is-done'
                    : test.result === 'fail'
                      ? 'is-blocked'
                      : 'is-waiting',
                ].join(' ')}
              >
                {TEST_RESULT_LABELS[test.result] || test.result}
              </span>
            </div>

            {test.notes ? <p>{test.notes}</p> : null}

            <div className="repair-v2-list__meta">
              <div>
                <span>Realizada por</span>
                <strong>{getUserDisplayName(users, test.performed_by_id)}</strong>
              </div>

              <div>
                <span>Fecha</span>
                <strong>{formatDateTime(test.performed_at)}</strong>
              </div>

              {test.intervention_id ? (
                <div>
                  <span>Intervención vinculada</span>
                  <strong>#{test.intervention_id}</strong>
                </div>
              ) : null}
            </div>
          </article>
        ))}
      </div>
    );
  }

  if (isBeforeRepair) {
    return (
      <section className="repair-v2-stage">
        <header className="repair-v2-stage__heading">
          <div>
            <span>Etapa 7</span>
            <h4>Pruebas</h4>
          </div>

          <span className="repair-v2-stage__state is-pending">
            <FlaskConical size={15} />
            Aún no disponible
          </span>
        </header>

        <div className="repair-v2-stage__notice">
          Requiere que el equipo esté dictaminado como reparable
          y en proceso de reparación.
        </div>
      </section>
    );
  }

  if (isEquipmentNotSuitable) {
    return (
      <section className="repair-v2-stage">
        <header className="repair-v2-stage__heading">
          <div>
            <span>Etapa 7</span>
            <h4>Pruebas</h4>
          </div>

          <span className="repair-v2-stage__state is-blocked">
            <FlaskConical size={15} />
            No aplica
          </span>
        </header>

        <div className="repair-v2-stage__notice">
          El equipo fue dictaminado como no apto para reparación.
          No se requieren pruebas técnicas.
        </div>
      </section>
    );
  }

  if (!isAvailable) {
    return (
      <section className="repair-v2-stage">
        <header className="repair-v2-stage__heading">
          <div>
            <span>Etapa 7</span>
            <h4>Pruebas</h4>
          </div>

          <span className="repair-v2-stage__state is-done">
            <FlaskConical size={15} />
            {tests.length} registrada{tests.length === 1 ? '' : 's'}
          </span>
        </header>

        {renderHistory()}
      </section>
    );
  }

  return (
    <section className="repair-v2-stage">
      <header className="repair-v2-stage__heading">
        <div>
          <span>Etapa 7</span>
          <h4>Pruebas</h4>
          <p>
            Ciclo intervención ↔ prueba. Una prueba fallida regresa
            la ejecución a reparación.
          </p>
        </div>

        <span
          className={[
            'repair-v2-stage__state',
            execution?.status === 'testing' ? 'is-active' : 'is-waiting',
          ].join(' ')}
        >
          <FlaskConical size={15} />
          {execution?.status === 'testing' ? 'En pruebas' : 'En reparación'}
        </span>
      </header>

      {!isOwnTechnician ? (
        <div className="repair-v2-stage__notice">
          Esta reparación está asignada a{' '}
          {getUserDisplayName(users, execution?.technician_id)}.
          Solo ese técnico puede registrar pruebas.
        </div>
      ) : openIntervention ? (
        <div className="repair-v2-stage__notice">
          Existe una intervención técnica en curso (#{openIntervention.sequence}).
          Debe finalizarse antes de registrar pruebas.
        </div>
      ) : (
        <form className="repair-v2-form" onSubmit={handleSubmit}>
          <label className="repair-v2-form__field">
            Tipo de prueba

            <input
              disabled={isBusy}
              onChange={(event) =>
                setForm((current) => ({ ...current, testType: event.target.value }))
              }
              placeholder="Ej. Prueba de fuga"
              type="text"
              value={form.testType}
            />
          </label>

          <label className="repair-v2-form__field">
            Resultado

            <select
              disabled={isBusy}
              onChange={(event) =>
                setForm((current) => ({ ...current, result: event.target.value }))
              }
              value={form.result}
            >
              {Object.entries(TEST_RESULT_LABELS).map(([value, label]) => (
                <option key={value} value={value}>{label}</option>
              ))}
            </select>
          </label>

          {completedInterventions.length ? (
            <label className="repair-v2-form__field repair-v2-form__field--wide">
              Intervención vinculada (opcional)

              <select
                disabled={isBusy}
                onChange={(event) =>
                  setForm((current) => ({
                    ...current,
                    interventionId: event.target.value,
                  }))
                }
                value={form.interventionId}
              >
                <option value="">Sin vincular</option>

                {completedInterventions.map((intervention) => (
                  <option key={intervention.id} value={intervention.id}>
                    #{intervention.sequence} · {intervention.description}
                  </option>
                ))}
              </select>
            </label>
          ) : null}

          <label className="repair-v2-form__field repair-v2-form__field--wide">
            Notas

            <textarea
              disabled={isBusy}
              onChange={(event) =>
                setForm((current) => ({ ...current, notes: event.target.value }))
              }
              placeholder="Detalles de la prueba"
              value={form.notes}
            />
          </label>

          <footer className="repair-v2-form__actions">
            <button className="primary-button" disabled={isBusy} type="submit">
              <FlaskConical size={16} />
              {isBusy ? 'Registrando...' : 'Registrar prueba'}
            </button>
          </footer>
        </form>
      )}

      {isOwnTechnician && execution?.status === 'testing' ? (
        <footer className="repair-v2-form__actions">
          <button
            className="primary-button"
            disabled={isBusy || !canCompleteTechnically}
            onClick={handleCompleteTechnically}
            type="button"
          >
            <CheckCircle2 size={16} />
            {isBusy ? 'Guardando...' : 'Completar técnicamente'}
          </button>
        </footer>
      ) : null}

      {execution?.status === 'testing' && !canCompleteTechnically && isOwnTechnician ? (
        <div className="repair-v2-stage__notice">
          La última prueba registrada debe tener resultado &quot;Aprobada&quot;
          para poder completar técnicamente la reparación.
        </div>
      ) : null}

      {renderHistory()}
    </section>
  );
}

export default RepairTestingSection;
