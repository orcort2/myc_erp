import React, {
  useEffect,
  useMemo,
  useState,
} from 'react';

import {
  Plus,
  Trash2,
  Wrench,
} from 'lucide-react';

import {
  completeRepairIntervention,
  startRepairIntervention,
} from '../../../services/api.js';

import {
  canExecuteRepair,
  formatDateTime,
  getUserDisplayName,
  INTERVENTION_OUTCOME_LABELS,
  REMOVED_COMPONENT_DISPOSITION_LABELS,
  safeArray,
} from './repairShared.js';


function emptyCompletionForm() {
  return {
    actions: [''],
    removedComponents: [],
    outcome: 'effective',
  };
}


function RepairInterventionSection({
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
  const [description, setDescription] = useState('');
  const [completion, setCompletion] = useState(emptyCompletionForm());

  const isOwnTechnician = canExecuteRepair(execution, user);

  const interventions = useMemo(
    () => safeArray(execution?.interventions).slice().reverse(),
    [execution],
  );

  const openIntervention = useMemo(
    () => safeArray(execution?.interventions).find(
      (intervention) => !intervention?.completed_at,
    ),
    [execution],
  );

  const isActive = execution?.status === 'in_repair';

  const isEquipmentNotSuitable = execution?.conclusion === 'equipment_not_suitable';

  const isBeforeRepair = [
    'pending_arrival',
    'pending_assignment',
    'assigned',
    'in_evaluation',
  ].includes(execution?.status);

  useEffect(() => {
    setCompletion(emptyCompletionForm());
  }, [openIntervention?.id]);

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

  async function handleStart(event) {
    event.preventDefault();

    if (!order?.id || !execution?.id || isBusy) {
      return;
    }

    if (description.trim().length < 3) {
      reportError('Describe la intervención con al menos 3 caracteres.');
      return;
    }

    setBusy(true);
    reportError('');
    reportNotice('');

    try {
      const result = await startRepairIntervention(order.id, execution.id, {
        description: description.trim(),
      });

      updateBoard(result);
      setDescription('');

      reportNotice('Intervención técnica iniciada.');
    } catch (requestError) {
      reportError(
        requestError?.message ||
          'No fue posible iniciar la intervención.',
      );
    } finally {
      setBusy(false);
    }
  }

  function updateActionLine(index, value) {
    setCompletion((current) => ({
      ...current,
      actions: current.actions.map((line, lineIndex) =>
        lineIndex === index ? value : line,
      ),
    }));
  }

  function addActionLine() {
    setCompletion((current) => ({
      ...current,
      actions: [...current.actions, ''],
    }));
  }

  function removeActionLine(index) {
    setCompletion((current) => ({
      ...current,
      actions: current.actions.filter((_, lineIndex) => lineIndex !== index),
    }));
  }

  function addRemovedComponent() {
    setCompletion((current) => ({
      ...current,
      removedComponents: [
        ...current.removedComponents,
        { name: '', disposition: 'return_to_client' },
      ],
    }));
  }

  function updateRemovedComponent(index, field, value) {
    setCompletion((current) => ({
      ...current,
      removedComponents: current.removedComponents.map((component, componentIndex) =>
        componentIndex === index ? { ...component, [field]: value } : component,
      ),
    }));
  }

  function removeRemovedComponent(index) {
    setCompletion((current) => ({
      ...current,
      removedComponents: current.removedComponents.filter(
        (_, componentIndex) => componentIndex !== index,
      ),
    }));
  }

  async function handleComplete(event) {
    event.preventDefault();

    if (!order?.id || !execution?.id || !openIntervention?.id || isBusy) {
      return;
    }

    const invalidComponent = completion.removedComponents.find(
      (component) => !component.name.trim(),
    );

    if (invalidComponent) {
      reportError('Cada componente removido requiere un nombre.');
      return;
    }

    setBusy(true);
    reportError('');
    reportNotice('');

    try {
      const result = await completeRepairIntervention(
        order.id,
        execution.id,
        openIntervention.id,
        {
          actions: completion.actions
            .map((line) => line.trim())
            .filter(Boolean)
            .map((description) => ({ description })),
          removed_components: completion.removedComponents.map((component) => ({
            name: component.name.trim(),
            disposition: component.disposition,
          })),
          outcome: completion.outcome,
        },
      );

      updateBoard(result);
      setCompletion(emptyCompletionForm());

      reportNotice('Intervención técnica finalizada.');
    } catch (requestError) {
      reportError(
        requestError?.message ||
          'No fue posible finalizar la intervención.',
      );
    } finally {
      setBusy(false);
    }
  }

  function renderHistory() {
    if (!interventions.length) {
      return (
        <div className="repair-v2-list__empty">
          Aún no se registran intervenciones.
        </div>
      );
    }

    return (
      <div className="repair-v2-list">
        {interventions.map((intervention) => (
          <article
            className={[
              'repair-v2-list__item',
              !intervention.completed_at ? 'is-active' : '',
            ].join(' ').trim()}
            key={intervention.id}
          >
            <div className="repair-v2-list__item-header">
              <strong>Intervención #{intervention.sequence}</strong>

              <span
                className={[
                  'repair-v2-list__badge',
                  intervention.completed_at
                    ? intervention.outcome === 'effective'
                      ? 'is-done'
                      : intervention.outcome === 'ineffective'
                        ? 'is-blocked'
                        : 'is-waiting'
                    : 'is-active',
                ].join(' ')}
              >
                {intervention.completed_at
                  ? INTERVENTION_OUTCOME_LABELS[intervention.outcome] || 'Finalizada'
                  : 'En curso'}
              </span>
            </div>

            <p>{intervention.description}</p>

            <div className="repair-v2-list__meta">
              <div>
                <span>Técnico</span>
                <strong>{getUserDisplayName(users, intervention.technician_id)}</strong>
              </div>

              <div>
                <span>Inicio</span>
                <strong>{formatDateTime(intervention.started_at)}</strong>
              </div>

              <div>
                <span>Fin</span>
                <strong>{formatDateTime(intervention.completed_at)}</strong>
              </div>
            </div>

            {safeArray(intervention.removed_components).length ? (
              <p>
                <strong>Componentes removidos:</strong>{' '}
                {intervention.removed_components
                  .map((component) =>
                    `${component.name} (${
                      REMOVED_COMPONENT_DISPOSITION_LABELS[component.disposition] ||
                      component.disposition
                    })`,
                  )
                  .join(' · ')}
              </p>
            ) : null}
          </article>
        ))}
      </div>
    );
  }

  /* =======================================================
     BLOQUEADO: aún no hay dictamen "reparable"
     ======================================================= */

  if (isBeforeRepair) {
    return (
      <section className="repair-v2-stage">
        <header className="repair-v2-stage__heading">
          <div>
            <h4>Intervención</h4>
          </div>

          <span className="repair-v2-stage__state is-pending">
            <Wrench size={15} />
            Aún no disponible
          </span>
        </header>

        <div className="repair-v2-stage__notice">
          Requiere que el equipo esté dictaminado como reparable.
        </div>
      </section>
    );
  }

  if (isEquipmentNotSuitable) {
    return (
      <section className="repair-v2-stage">
        <header className="repair-v2-stage__heading">
          <div>
            <h4>Intervención</h4>
          </div>

          <span className="repair-v2-stage__state is-blocked">
            <Wrench size={15} />
            No aplica
          </span>
        </header>

        <div className="repair-v2-stage__notice">
          El equipo fue dictaminado como no apto para reparación.
          No se requieren intervenciones técnicas.
        </div>
      </section>
    );
  }

  /* =======================================================
     ACTIVO: in_repair
     ======================================================= */

  if (isActive) {
    return (
      <section className="repair-v2-stage">
        <header className="repair-v2-stage__heading">
          <div>
            <h4>Intervención</h4>
            <p>
              Registra cada sesión técnica de intervención sobre
              el equipo. Solo puede haber una sesión abierta a la vez.
            </p>
          </div>

          <span className="repair-v2-stage__state is-active">
            <Wrench size={15} />
            En reparación
          </span>
        </header>

        {!isOwnTechnician ? (
          <div className="repair-v2-stage__notice">
            Esta reparación está asignada a{' '}
            {getUserDisplayName(users, execution?.technician_id)}.
            Solo ese técnico puede registrar intervenciones.
          </div>
        ) : openIntervention ? (
          <form className="repair-v2-form" onSubmit={handleComplete}>
            <div className="repair-v2-form__group repair-v2-form__group--full">
              <header>
                <span>Finalizar intervención #{openIntervention.sequence}</span>
                <p>{openIntervention.description}</p>
              </header>

              <label className="repair-v2-form__field repair-v2-form__field--wide">
                Acciones realizadas

                {completion.actions.map((line, index) => (
                  <div
                    key={index}
                    style={{ display: 'flex', gap: '6px', marginBottom: '6px' }}
                  >
                    <input
                      disabled={isBusy}
                      onChange={(event) =>
                        updateActionLine(index, event.target.value)
                      }
                      placeholder="Ej. Se reemplazó capacitor dañado"
                      type="text"
                      value={line}
                    />

                    <button
                      className="table-button"
                      disabled={isBusy || completion.actions.length <= 1}
                      onClick={() => removeActionLine(index)}
                      type="button"
                    >
                      <Trash2 size={14} />
                    </button>
                  </div>
                ))}

                <button
                  className="table-button"
                  disabled={isBusy}
                  onClick={addActionLine}
                  type="button"
                >
                  <Plus size={14} />
                  Agregar acción
                </button>
              </label>
            </div>

            <div className="repair-v2-form__group repair-v2-form__group--full">
              <header>
                <span>Componentes removidos</span>
                <p>Opcional. Por defecto se regresan al cliente.</p>
              </header>

              {completion.removedComponents.map((component, index) => (
                <div
                  key={index}
                  style={{ display: 'flex', gap: '6px', marginBottom: '6px' }}
                >
                  <input
                    disabled={isBusy}
                    onChange={(event) =>
                      updateRemovedComponent(index, 'name', event.target.value)
                    }
                    placeholder="Nombre del componente"
                    type="text"
                    value={component.name}
                  />

                  <select
                    disabled={isBusy}
                    onChange={(event) =>
                      updateRemovedComponent(index, 'disposition', event.target.value)
                    }
                    value={component.disposition}
                  >
                    {Object.entries(REMOVED_COMPONENT_DISPOSITION_LABELS).map(
                      ([value, label]) => (
                        <option key={value} value={value}>{label}</option>
                      ),
                    )}
                  </select>

                  <button
                    className="table-button"
                    disabled={isBusy}
                    onClick={() => removeRemovedComponent(index)}
                    type="button"
                  >
                    <Trash2 size={14} />
                  </button>
                </div>
              ))}

              <button
                className="table-button"
                disabled={isBusy}
                onClick={addRemovedComponent}
                type="button"
              >
                <Plus size={14} />
                Agregar componente removido
              </button>
            </div>

            <label className="repair-v2-form__field repair-v2-form__field--wide">
              Resultado

              <select
                disabled={isBusy}
                onChange={(event) =>
                  setCompletion((current) => ({
                    ...current,
                    outcome: event.target.value,
                  }))
                }
                value={completion.outcome}
              >
                {Object.entries(INTERVENTION_OUTCOME_LABELS).map(
                  ([value, label]) => (
                    <option key={value} value={value}>{label}</option>
                  ),
                )}
              </select>
            </label>

            <footer className="repair-v2-form__actions">
              <button className="primary-button" disabled={isBusy} type="submit">
                <Wrench size={16} />
                {isBusy ? 'Guardando...' : 'Finalizar intervención'}
              </button>
            </footer>
          </form>
        ) : (
          <form className="repair-v2-form" onSubmit={handleStart}>
            <label className="repair-v2-form__field repair-v2-form__field--wide">
              Descripción de la intervención

              <textarea
                disabled={isBusy}
                onChange={(event) => setDescription(event.target.value)}
                placeholder="Qué se va a realizar en esta sesión técnica"
                value={description}
              />
            </label>

            <footer className="repair-v2-form__actions">
              <button className="primary-button" disabled={isBusy} type="submit">
                <Wrench size={16} />
                {isBusy ? 'Iniciando...' : 'Iniciar intervención'}
              </button>
            </footer>
          </form>
        )}

        {renderHistory()}
      </section>
    );
  }

  /* =======================================================
     POSTERIOR: solo lectura
     ======================================================= */

  return (
    <section className="repair-v2-stage">
      <header className="repair-v2-stage__heading">
        <div>
          <h4>Intervención</h4>
        </div>

        <span className="repair-v2-stage__state is-done">
          <Wrench size={15} />
          {interventions.length} registrada
          {interventions.length === 1 ? '' : 's'}
        </span>
      </header>

      {renderHistory()}
    </section>
  );
}

export default RepairInterventionSection;
