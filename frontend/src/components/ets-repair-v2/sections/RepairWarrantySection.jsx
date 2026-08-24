import React, { useState } from 'react';

import {
  RefreshCcw,
  ShieldCheck,
} from 'lucide-react';

import {
  reopenRepairWarranty,
} from '../../../services/api.js';

import {
  formatDateTime,
  getUserDisplayName,
  safeArray,
} from './repairShared.js';

import {
  hasPermission,
} from '../../../utils/accessControl.js';


function RepairWarrantySection({
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
  const [reason, setReason] = useState('');

  const canAuthorize = hasPermission(
    user,
    'service_orders.repair.authorize',
  );

  const cycles = safeArray(execution?.warranty_cycles).slice().reverse();

  const hasActiveCycle = Boolean(execution?.active_warranty_cycle_id);

  const canReopen = execution?.status === 'closed' && !hasActiveCycle;

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

    if (reason.trim().length < 10) {
      reportError('Describe el motivo de la garantía con al menos 10 caracteres.');
      return;
    }

    setBusy(true);
    reportError('');
    reportNotice('');

    try {
      const result = await reopenRepairWarranty(order.id, execution.id, {
        reason: reason.trim(),
      });

      updateBoard(result);
      setReason('');

      reportNotice('Ciclo de garantía abierto. La ejecución vuelve a asignación técnica.');
    } catch (requestError) {
      reportError(
        requestError?.message ||
          'No fue posible abrir el ciclo de garantía.',
      );
    } finally {
      setBusy(false);
    }
  }

  return (
    <section className="repair-v2-stage">
      <header className="repair-v2-stage__heading">
        <div>
          <span>Flujo paralelo · posterior al cierre</span>
          <h4>Garantía</h4>
          <p>
            Un ciclo de garantía no deshace el cierre anterior: crea un
            nuevo ciclo versionado que retoma la reparación desde la
            asignación técnica.
          </p>
        </div>

        <span
          className={[
            'repair-v2-stage__state',
            hasActiveCycle ? 'is-active' : execution?.warranty_reopened_count
              ? 'is-done'
              : 'is-pending',
          ].join(' ')}
        >
          <ShieldCheck size={15} />
          {hasActiveCycle
            ? 'Ciclo en curso'
            : execution?.warranty_reopened_count
              ? `${execution.warranty_reopened_count} ciclo(s) previos`
              : 'Sin garantías'}
        </span>
      </header>

      {hasActiveCycle ? (
        <div className="repair-v2-stage__notice">
          Existe un ciclo de garantía activo. El trabajo técnico
          se realiza a través de las etapas de asignación, diagnóstico,
          intervención y pruebas de este mismo expediente.
        </div>
      ) : null}

      {canReopen ? (
        canAuthorize ? (
          <form className="repair-v2-form" onSubmit={handleSubmit}>
            <label className="repair-v2-form__field repair-v2-form__field--wide">
              Motivo de la garantía

              <textarea
                disabled={isBusy}
                onChange={(event) => setReason(event.target.value)}
                placeholder="Motivo del retorno del equipo por garantía"
                value={reason}
              />
            </label>

            <footer className="repair-v2-form__actions">
              <button className="primary-button" disabled={isBusy} type="submit">
                <RefreshCcw size={16} />
                {isBusy ? 'Abriendo...' : 'Abrir ciclo de garantía'}
              </button>
            </footer>
          </form>
        ) : (
          <div className="repair-v2-stage__notice">
            No tienes permiso para autorizar ciclos de garantía.
          </div>
        )
      ) : !hasActiveCycle ? (
        <div className="repair-v2-stage__notice">
          La garantía solo puede abrirse sobre una ejecución cerrada.
        </div>
      ) : null}

      {cycles.length ? (
        <div className="repair-v2-list">
          {cycles.map((cycle) => (
            <article
              className={[
                'repair-v2-list__item',
                cycle.status === 'open' ? 'is-active' : '',
              ].join(' ').trim()}
              key={cycle.id}
            >
              <div className="repair-v2-list__item-header">
                <strong>Ciclo de garantía #{cycle.sequence}</strong>

                <span
                  className={[
                    'repair-v2-list__badge',
                    cycle.status === 'open' ? 'is-active' : 'is-done',
                  ].join(' ')}
                >
                  {cycle.status === 'open' ? 'Abierto' : 'Cerrado'}
                </span>
              </div>

              <p>{cycle.reason}</p>

              <div className="repair-v2-list__meta">
                <div>
                  <span>Abierto por</span>
                  <strong>{getUserDisplayName(users, cycle.opened_by_id)}</strong>
                </div>

                <div>
                  <span>Fecha de apertura</span>
                  <strong>{formatDateTime(cycle.opened_at)}</strong>
                </div>

                {cycle.status === 'closed' ? (
                  <>
                    <div>
                      <span>Resolución</span>
                      <strong>
                        {cycle.resolution === 'equipment_not_suitable'
                          ? 'Equipo no apto'
                          : 'Reparado'}
                      </strong>
                    </div>

                    <div>
                      <span>Cerrado</span>
                      <strong>{formatDateTime(cycle.closed_at)}</strong>
                    </div>
                  </>
                ) : null}
              </div>
            </article>
          ))}
        </div>
      ) : (
        <div className="repair-v2-list__empty">
          Esta ejecución no ha tenido ciclos de garantía.
        </div>
      )}
    </section>
  );
}

export default RepairWarrantySection;
