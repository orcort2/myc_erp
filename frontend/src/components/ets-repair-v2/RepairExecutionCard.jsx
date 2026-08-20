import React from 'react';


const REPAIR_STATUS_LABELS = {
  pending_arrival: 'Pendiente de arribo',
  pending_assignment: 'Pendiente de asignación',
  assigned: 'Asignado',
  in_evaluation: 'En evaluación',
  in_repair: 'En reparación',
  testing: 'En pruebas',
  technically_completed: 'Cierre técnico',
  equipment_not_suitable: 'Equipo no apto',
  pending_release: 'Pendiente de liberación',
  closed: 'Cerrado',
  cancelled: 'Cancelado',
};


function safeArray(value) {
  return Array.isArray(value)
    ? value
    : [];
}


function safeText(
  value,
  fallback = '-',
) {
  if (
    value === undefined ||
    value === null ||
    value === ''
  ) {
    return fallback;
  }

  return value;
}


function getUserDisplayName(
  users,
  userId,
) {
  if (!userId) {
    return 'Sin asignar';
  }

  const found =
    safeArray(users).find(
      (candidate) =>
        Number(candidate?.id) ===
        Number(userId),
    );

  return (
    found?.full_name ||
    found?.name ||
    found?.email ||
    `Usuario #${userId}`
  );
}


function RepairExecutionCard({
  execution,
  index = 0,
  tone = 'pending',
  users = [],
  onOpen,
}) {
  if (!execution) {
    return null;
  }


  const interventionCount =
    safeArray(
      execution.interventions,
    ).length;


  const testCount =
    safeArray(
      execution.tests,
    ).length;


  const blockerCount =
    safeArray(
      execution.blockers,
    ).length;


  const openPauseCount =
    safeArray(
      execution.pauses,
    ).filter(
      (pause) =>
        pause?.status !==
        'resolved',
    ).length;


  const statusLabel =
    REPAIR_STATUS_LABELS[
      execution.status
    ] ||
    execution.status ||
    'Sin estado';


  const equipmentName =
    safeText(
      execution.equipment_name,
      'Equipo sin identificar',
    );


  const workOrderNumber =
    safeText(
      execution.work_order_number,
      'Sin OT',
    );


  const technicianName =
    getUserDisplayName(
      users,
      execution.technician_id,
    );


  function handleClick() {
    if (
      typeof onOpen ===
      'function'
    ) {
      onOpen(execution);
    }
  }


  return (
    <button
      aria-label={`Abrir expediente de reparación de ${equipmentName}`}
      className="repair-v2-card"
      onClick={handleClick}
      type="button"
    >
      {/* ===================================================
          ENCABEZADO
          =================================================== */}

      <div className="repair-v2-card__header">
        <div className="repair-v2-card__title">
          <span>
            Equipo {index + 1}
          </span>

          <strong>
            {equipmentName}
          </strong>
        </div>


        <span
          className={[
            'repair-v2-card__status',
            `is-${tone}`,
          ].join(' ')}
        >
          {statusLabel}
        </span>
      </div>


      {/* ===================================================
          IDENTIDAD OPERATIVA
          =================================================== */}

      <div className="repair-v2-card__identity">
        <div>
          <span>
            Orden de trabajo
          </span>

          <strong>
            {workOrderNumber === 'Sin OT'
              ? workOrderNumber
              : `OT-${workOrderNumber}`}
          </strong>
        </div>


        <div>
          <span>
            Técnico
          </span>

          <strong>
            {technicianName}
          </strong>
        </div>
      </div>


      {/* ===================================================
          MÉTRICAS
          =================================================== */}

      <div className="repair-v2-card__metrics">
        <div>
          <span>
            Intervenciones
          </span>

          <strong>
            {interventionCount}
          </strong>
        </div>


        <div>
          <span>
            Pruebas
          </span>

          <strong>
            {testCount}
          </strong>
        </div>


        <div>
          <span>
            Pausas
          </span>

          <strong>
            {openPauseCount}
          </strong>
        </div>
      </div>


      {/* ===================================================
          PIE
          =================================================== */}

      <footer className="repair-v2-card__footer">
        <span
          className={
            blockerCount
              ? 'has-blockers'
              : 'is-clear'
          }
        >
          {blockerCount
            ? `${blockerCount} ${
                blockerCount === 1
                  ? 'bloqueante'
                  : 'bloqueantes'
              }`
            : 'Sin bloqueantes'}
        </span>


        <strong>
          Abrir expediente
          <span
            aria-hidden="true"
            className="repair-v2-card__arrow"
          >
            →
          </span>
        </strong>
      </footer>
    </button>
  );
}


export default RepairExecutionCard;