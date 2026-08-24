import React, {
  useMemo,
  useState,
} from 'react';

import {
  UserRoundCheck,
  UserRoundCog,
} from 'lucide-react';

import {
  assignRepairTechnician,
} from '../../../services/api.js';

import {
  getUserDisplayName,
  REPAIR_STATUS_LABELS,
  safeArray,
} from './repairShared.js';

import {
  hasPermission,
} from '../../../utils/accessControl.js';


function RepairAssignmentSection({
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
  const [technicianId, setTechnicianId] = useState('');

  const canManage = hasPermission(
    user,
    'service_orders.repair.manage',
  );

  const technicianOptions = useMemo(
    () => safeArray(users).filter(
      (candidate) =>
        candidate?.is_active !== false &&
        hasPermission(candidate, 'service_orders.repair.execute'),
    ),
    [users],
  );

  const canAssign = execution?.status === 'pending_assignment';
  const isLocked = execution?.status === 'pending_arrival';
  const isAssigned = Boolean(execution?.technician_id);

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

    if (!order?.id || !execution?.id || isBusy || !technicianId) {
      return;
    }

    setBusy(true);
    reportError('');
    reportNotice('');

    try {
      const result = await assignRepairTechnician(
        order.id,
        execution.id,
        { technician_id: Number(technicianId) },
      );

      updateBoard(result);
      setTechnicianId('');

      reportNotice('Técnico asignado correctamente a la reparación.');
    } catch (requestError) {
      reportError(
        requestError?.message ||
          'No fue posible asignar el técnico.',
      );
    } finally {
      setBusy(false);
    }
  }

  /* =======================================================
     BLOQUEADO: recepción pendiente
     ======================================================= */

  if (isLocked) {
    return (
      <section className="repair-v2-stage">
        <header className="repair-v2-stage__heading">
          <div>
            <h4>Asignación técnica</h4>
          </div>

          <span className="repair-v2-stage__state is-pending">
            <UserRoundCog size={15} />
            Aún no disponible
          </span>
        </header>

        <div className="repair-v2-stage__notice">
          Primero debe completarse la recepción del equipo
          para poder asignar un técnico responsable.
        </div>
      </section>
    );
  }

  /* =======================================================
     YA ASIGNADO
     ======================================================= */

  if (!canAssign) {
    return (
      <section className="repair-v2-stage">
        <header className="repair-v2-stage__heading">
          <div>
            <h4>Asignación técnica</h4>
          </div>

          <span className="repair-v2-stage__state is-done">
            <UserRoundCheck size={15} />
            Asignado
          </span>
        </header>

        <div className="repair-v2-reception-summary">
          <article>
            <span>Técnico responsable</span>
            <strong>
              {getUserDisplayName(users, execution?.technician_id)}
            </strong>
          </article>

          <article>
            <span>Estado actual</span>
            <strong>
              {REPAIR_STATUS_LABELS[execution?.status] || execution?.status}
            </strong>
          </article>
        </div>
      </section>
    );
  }

  /* =======================================================
     PENDIENTE DE ASIGNAR
     ======================================================= */

  return (
    <section className="repair-v2-stage">
      <header className="repair-v2-stage__heading">
        <div>
          <h4>Asignación técnica</h4>
          <p>
            Selecciona al técnico responsable de ejecutar
            esta reparación.
          </p>
        </div>

        <span className="repair-v2-stage__state is-waiting">
          <UserRoundCog size={15} />
          Pendiente
        </span>
      </header>

      {isAssigned ? (
        <div className="repair-v2-stage__notice">
          Este expediente ya tiene un técnico registrado,
          pero permanece pendiente de asignación formal.
          Revisa la consistencia del flujo.
        </div>
      ) : null}

      {!canManage ? (
        <div className="repair-v2-stage__notice">
          No tienes permiso para asignar técnicos en Reparación.
        </div>
      ) : !technicianOptions.length ? (
        <div className="repair-v2-stage__notice">
          No hay usuarios activos con facultades para ejecutar Reparación
          (service_orders.repair.execute). Solicita que se asigne ese
          permiso a un técnico antes de continuar.
        </div>
      ) : (
        <form className="repair-v2-form" onSubmit={handleSubmit}>
          <label className="repair-v2-form__field repair-v2-form__field--wide">
            Técnico responsable

            <select
              disabled={isBusy}
              onChange={(event) => setTechnicianId(event.target.value)}
              value={technicianId}
            >
              <option value="">Selecciona un técnico</option>

              {technicianOptions.map((candidate) => (
                <option key={candidate.id} value={candidate.id}>
                  {candidate.full_name || candidate.name || candidate.email}
                </option>
              ))}
            </select>
          </label>

          <footer className="repair-v2-form__actions">
            <button
              className="primary-button"
              disabled={isBusy || !technicianId}
              type="submit"
            >
              <UserRoundCheck size={16} />
              {isBusy ? 'Asignando...' : 'Asignar técnico'}
            </button>
          </footer>
        </form>
      )}
    </section>
  );
}

export default RepairAssignmentSection;
