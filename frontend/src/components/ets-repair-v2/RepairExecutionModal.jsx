import React, {
  useEffect,
  useMemo,
} from 'react';

import RepairReceptionSection from './sections/RepairReceptionSection.jsx';
import RepairAssignmentSection from './sections/RepairAssignmentSection.jsx';
import RepairDiagnosisSection from './sections/RepairDiagnosisSection.jsx';
import RepairVerdictSection from './sections/RepairVerdictSection.jsx';
import RepairInterventionSection from './sections/RepairInterventionSection.jsx';
import RepairPauseSection from './sections/RepairPauseSection.jsx';
import RepairTestingSection from './sections/RepairTestingSection.jsx';
import RepairWarrantySection from './sections/RepairWarrantySection.jsx';
import RepairChangeSection from './sections/RepairChangeSection.jsx';
import RepairClosureSection from './sections/RepairClosureSection.jsx';

import {
  getFeaturedStageKeys,
  getStageTone,
  isClosed as isRepairClosed,
  isTerminalCancelled,
  getCancelledHistoryKeys,
  REPAIR_MAIN_STAGES,
} from './sections/repairStageModel.js';


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


function formatDateTime(value) {
  if (!value) {
    return '-';
  }

  const parsed =
    new Date(value);

  if (
    Number.isNaN(
      parsed.getTime(),
    )
  ) {
    return value;
  }

  return parsed.toLocaleString(
    'es-MX',
    {
      dateStyle: 'medium',
      timeStyle: 'short',
    },
  );
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


function getStatusTone(status) {
  if (
    [
      'closed',
      'technically_completed',
    ].includes(status)
  ) {
    return 'done';
  }

  if (
    [
      'assigned',
      'in_evaluation',
      'in_repair',
      'testing',
      'pending_release',
    ].includes(status)
  ) {
    return 'active';
  }

  if (
    [
      'cancelled',
      'equipment_not_suitable',
    ].includes(status)
  ) {
    return 'blocked';
  }

  return 'pending';
}


const STAGE_SECTION_COMPONENTS = {
  reception: RepairReceptionSection,
  assignment: RepairAssignmentSection,
  evaluation: RepairDiagnosisSection,
  verdict: RepairVerdictSection,
  intervention: RepairInterventionSection,
  testing: RepairTestingSection,
  closure: RepairClosureSection,
};


const PAUSE_UNAVAILABLE_STATUSES = new Set([
  'pending_arrival',
  'pending_assignment',
  'closed',
  'cancelled',
]);


function RepairExecutionModal({
  execution,
  order,
  board = null,
  users = [],
  user = null,

  isOpen = false,
  isBusy = false,

  error = '',
  notice = '',

  onClose,
  onBoardChange,
  onBusyChange,
  onError,
  onNotice,
}) {
  const statusLabel =
    REPAIR_STATUS_LABELS[
      execution?.status
    ] ||
    execution?.status ||
    'Sin estado';


  const tone =
    getStatusTone(
      execution?.status,
    );


  const blockerCount =
    useMemo(
      () =>
        safeArray(
          execution?.blockers,
        ).length,
      [execution],
    );


  const interventionCount =
    useMemo(
      () =>
        safeArray(
          execution?.interventions,
        ).length,
      [execution],
    );


  const testCount =
    useMemo(
      () =>
        safeArray(
          execution?.tests,
        ).length,
      [execution],
    );


  const pauseCount =
    useMemo(
      () =>
        safeArray(
          execution?.pauses,
        ).filter(
          (pause) =>
            pause?.status !==
            'resolved',
        ).length,
      [execution],
    );


  /* =======================================================
     RESOLUCIÓN DE ETAPA DE PRESENTACIÓN
     (derivada de execution.status/conclusion, no persistida)
     ======================================================= */

  const isCancelled = isTerminalCancelled(execution);
  const isClosedNow = isRepairClosed(execution);

  const featuredKeys = useMemo(
    () => (isCancelled ? [] : getFeaturedStageKeys(execution)),
    [execution, isCancelled],
  );

  const historyKeys = useMemo(() => {
    if (isCancelled) {
      return getCancelledHistoryKeys(execution);
    }

    return REPAIR_MAIN_STAGES
      .map((stage) => stage.key)
      .filter(
        (key) =>
          !featuredKeys.includes(key) &&
          getStageTone(key, execution) === 'done',
      );
  }, [execution, featuredKeys, isCancelled]);

  const hasTechnician = Boolean(execution?.technician_id);

  const showPausesPanel =
    !isCancelled &&
    (
      !PAUSE_UNAVAILABLE_STATUSES.has(execution?.status) ||
      safeArray(execution?.pauses).length > 0
    );

  const hasPendingChange = safeArray(execution?.changes).some(
    (change) => change?.status === 'requested',
  );

  const showChangesPanel =
    !isCancelled &&
    (
      (hasTechnician && !['closed', 'cancelled'].includes(execution?.status)) ||
      safeArray(execution?.changes).length > 0
    );

  const showWarrantyPanel =
    isClosedNow || Boolean(execution?.warranty_reopened_count);

  const activeWarrantyCycle = useMemo(
    () =>
      safeArray(execution?.warranty_cycles).find(
        (cycle) => cycle?.id === execution?.active_warranty_cycle_id,
      ),
    [execution],
  );

  const commonSectionProps = {
    order,
    execution,
    isBusy,
    onBoardChange,
    onBusyChange,
    onError,
    onNotice,
    user,
    users,
  };


  /* =======================================================
     ESCAPE
     ======================================================= */

  useEffect(() => {
    if (!isOpen) {
      return undefined;
    }

    function handleKeyDown(
      event,
    ) {
      if (
        event.key === 'Escape' &&
        !isBusy
      ) {
        onClose?.();
      }
    }

    document.addEventListener(
      'keydown',
      handleKeyDown,
    );

    return () => {
      document.removeEventListener(
        'keydown',
        handleKeyDown,
      );
    };
  }, [
    isOpen,
    isBusy,
    onClose,
  ]);


  /* =======================================================
     BLOQUEO DE SCROLL GLOBAL
     ======================================================= */

  useEffect(() => {
    if (!isOpen) {
      return undefined;
    }

    const previousOverflow =
      document.body.style.overflow;

    document.body.style.overflow =
      'hidden';

    return () => {
      document.body.style.overflow =
        previousOverflow;
    };
  }, [isOpen]);


  if (
    !isOpen ||
    !execution
  ) {
    return null;
  }


  /* =======================================================
     CIERRE POR BACKDROP
     ======================================================= */

  function handleBackdropMouseDown(
    event,
  ) {
    if (
      event.target !==
      event.currentTarget
    ) {
      return;
    }

    if (isBusy) {
      return;
    }

    onClose?.();
  }


  return (
    <div
      className="repair-v2-modal"
      onMouseDown={
        handleBackdropMouseDown
      }
      role="presentation"
    >
      <section
        aria-labelledby="repair-v2-modal-title"
        aria-modal="true"
        className="repair-v2-modal__dialog"
        role="dialog"
      >
        {/* =================================================
            HEADER FIJO
            ================================================= */}

        <header className="repair-v2-modal__header">
          <div className="repair-v2-modal__heading">
            <span>
              Reparación /
              Expediente técnico
            </span>

            <h3 id="repair-v2-modal-title">
              {safeText(
                execution.equipment_name,
                'Equipo sin identificar',
              )}
            </h3>

            <div className="repair-v2-modal__heading-meta">
              <small>
                {order?.folio
                  ? order.folio
                  : `ETS #${order?.id}`}
              </small>

              <span>
                ·
              </span>

              <small>
                {execution.work_order_number
                  ? `OT-${execution.work_order_number}`
                  : 'Sin OT'}
              </small>
            </div>
          </div>


          <div className="repair-v2-modal__header-actions">
            <span
              className={[
                'repair-v2-modal__status',
                `is-${tone}`,
              ].join(' ')}
            >
              {statusLabel}
            </span>

            <button
              aria-label="Cerrar expediente"
              className="repair-v2-modal__close"
              disabled={
                isBusy
              }
              onClick={() =>
                onClose?.()
              }
              type="button"
            >
              ×
            </button>
          </div>
        </header>


        {/* =================================================
            BODY
            ================================================= */}

        <div className="repair-v2-modal__body">
          {/* ===============================================
              ALERTAS DEL EXPEDIENTE
              =============================================== */}

          {error ? (
            <div className="repair-v2__alert is-error repair-v2-modal__alert">
              {error}
            </div>
          ) : null}


          {notice ? (
            <div className="repair-v2__alert is-success repair-v2-modal__alert">
              {notice}
            </div>
          ) : null}


          {/* ===============================================
              RESUMEN GENERAL
              =============================================== */}

          <section className="repair-v2-modal__summary">
            <div className="repair-v2-modal__summary-heading">
              <div>
                <span>
                  Resumen operativo
                </span>

                <h4>
                  Expediente de reparación
                </h4>
              </div>
            </div>


            <div className="repair-v2-modal__summary-grid">
              <article>
                <span>
                  Equipo
                </span>

                <strong>
                  {safeText(
                    execution.equipment_name,
                    'Sin identificar',
                  )}
                </strong>
              </article>


              <article>
                <span>
                  Orden de trabajo
                </span>

                <strong>
                  {execution.work_order_number
                    ? `OT-${execution.work_order_number}`
                    : 'Sin OT'}
                </strong>
              </article>


              <article>
                <span>
                  Técnico
                </span>

                <strong>
                  {getUserDisplayName(
                    users,
                    execution.technician_id,
                  )}
                </strong>
              </article>


              <article>
                <span>
                  Estado
                </span>

                <strong>
                  {statusLabel}
                </strong>
              </article>


              <article>
                <span>
                  Intervenciones
                </span>

                <strong>
                  {interventionCount}
                </strong>
              </article>


              <article>
                <span>
                  Pruebas
                </span>

                <strong>
                  {testCount}
                </strong>
              </article>


              <article>
                <span>
                  Pausas abiertas
                </span>

                <strong>
                  {pauseCount}
                </strong>
              </article>


              <article>
                <span>
                  Bloqueantes
                </span>

                <strong>
                  {blockerCount}
                </strong>
              </article>
            </div>
          </section>


          {/* ===============================================
              BLOQUEANTES
              =============================================== */}

          {blockerCount ? (
            <section className="repair-v2-modal__blockers">
              <header>
                <span>
                  Atención requerida
                </span>

                <h4>
                  Bloqueantes activos
                </h4>
              </header>

              <div className="repair-v2-modal__blocker-list">
                {safeArray(
                  execution.blockers,
                ).map(
                  (
                    blocker,
                    index,
                  ) => (
                    <article
                      key={
                        blocker?.id ||
                        `blocker-${index}`
                      }
                    >
                      <strong>
                        {safeText(
                          blocker?.message ||
                            blocker?.reason ||
                            blocker?.code,
                          'Bloqueante operativo',
                        )}
                      </strong>
                    </article>
                  ),
                )}
              </div>
            </section>
          ) : null}


          {/* ===============================================
              STEPPER DE ETAPAS PRINCIPALES
              =============================================== */}

          {isCancelled ? (
            <div className="repair-v2-context-banner">
              Esta reparación fue cancelada antes de su primera
              intervención técnica. El histórico disponible se
              conserva abajo.
            </div>
          ) : (
            <nav
              aria-label="Etapas de la reparación"
              className="repair-v2-stepper"
            >
              {REPAIR_MAIN_STAGES.map((stage, index) => {
                const stageTone = getStageTone(stage.key, execution);

                return (
                  <React.Fragment key={stage.key}>
                    {index > 0 ? (
                      <span
                        aria-hidden="true"
                        className="repair-v2-stepper__arrow"
                      >
                        →
                      </span>
                    ) : null}

                    <span
                      className={[
                        'repair-v2-stepper__node',
                        `is-${stageTone}`,
                      ].join(' ')}
                    >
                      <span className="repair-v2-stepper__node-index">
                        {index + 1}
                      </span>

                      {stage.label}
                    </span>
                  </React.Fragment>
                );
              })}
            </nav>
          )}

          {execution?.active_warranty_cycle_id ? (
            <div className="repair-v2-context-banner">
              Ciclo de garantía
              {activeWarrantyCycle?.sequence
                ? ` #${activeWarrantyCycle.sequence}`
                : ''}{' '}
              en curso: el trabajo técnico continúa a través de las
              mismas etapas de este expediente.
            </div>
          ) : null}


          {/* ===============================================
              ETAPA DESTACADA (la única con formulario abierto)
              =============================================== */}

          {featuredKeys.map((key) => {
            const StageComponent = STAGE_SECTION_COMPONENTS[key];

            return (
              <section className="repair-v2-modal__workspace" key={key}>
                <StageComponent
                  {...commonSectionProps}
                  board={board}
                />
              </section>
            );
          })}

          {isCancelled ? (
            <section className="repair-v2-modal__workspace">
              <RepairClosureSection {...commonSectionProps} />
            </section>
          ) : null}


          {/* ===============================================
              HISTORIAL DE ETAPAS COMPLETADAS (colapsado)
              =============================================== */}

          {historyKeys.length ? (
            <details className="repair-v2-history">
              <summary>
                Ver etapas anteriores ({historyKeys.length})
              </summary>

              <div className="repair-v2-history__body">
                {historyKeys.map((key) => {
                  const StageComponent = STAGE_SECTION_COMPONENTS[key];

                  return (
                    <div className="repair-v2-modal__workspace" key={key}>
                      <StageComponent
                        {...commonSectionProps}
                        board={board}
                      />
                    </div>
                  );
                })}
              </div>
            </details>
          ) : null}


          {/* ===============================================
              FLUJOS PARALELOS / CONTEXTUALES
              (no son pasos de la secuencia principal)
              =============================================== */}

          {showPausesPanel ? (
            <details
              className="repair-v2-context-panel"
              open={pauseCount > 0}
            >
              <summary>
                Pausas operativas
                {pauseCount
                  ? ` · ${pauseCount} activa${pauseCount === 1 ? '' : 's'}`
                  : ' · sin pausas activas'}
              </summary>

              <div className="repair-v2-context-panel__body">
                <RepairPauseSection {...commonSectionProps} />
              </div>
            </details>
          ) : null}

          {showChangesPanel ? (
            <details
              className="repair-v2-context-panel"
              open={hasPendingChange}
            >
              <summary>
                Solicitudes de cambio
                {hasPendingChange ? ' · pendiente de resolución' : ''}
              </summary>

              <div className="repair-v2-context-panel__body">
                <RepairChangeSection {...commonSectionProps} />
              </div>
            </details>
          ) : null}

          {showWarrantyPanel ? (
            <details
              className="repair-v2-context-panel"
              open={isClosedNow}
            >
              <summary>Garantía</summary>

              <div className="repair-v2-context-panel__body">
                <RepairWarrantySection {...commonSectionProps} />
              </div>
            </details>
          ) : null}


          {/* ===============================================
              TRAZABILIDAD
              =============================================== */}

          <section className="repair-v2-modal__traceability">
            <header>
              <span>
                Trazabilidad
              </span>

              <h4>
                Información del expediente
              </h4>
            </header>


            <div className="repair-v2-modal__traceability-grid">
              <article>
                <span>
                  Creación
                </span>

                <strong>
                  {formatDateTime(
                    execution.created_at,
                  )}
                </strong>
              </article>


              <article>
                <span>
                  Actualización
                </span>

                <strong>
                  {formatDateTime(
                    execution.updated_at,
                  )}
                </strong>
              </article>


              <article>
                <span>
                  Cierre técnico
                </span>

                <strong>
                  {formatDateTime(
                    execution.technically_completed_at,
                  )}
                </strong>
              </article>


              <article>
                <span>
                  Cierre final
                </span>

                <strong>
                  {formatDateTime(
                    execution.closed_at,
                  )}
                </strong>
              </article>
            </div>
          </section>
        </div>
      </section>
    </div>
  );
}


export default RepairExecutionModal;