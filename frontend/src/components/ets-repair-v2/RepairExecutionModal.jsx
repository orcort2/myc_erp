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
import RepairClosureSection from './sections/RepairClosureSection.jsx';


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
              WORKFLOW OPERATIVO
              =============================================== */}

          <section className="repair-v2-modal__workspace">
            <RepairReceptionSection
              board={board}
              execution={execution}
              isBusy={isBusy}
              onBoardChange={onBoardChange}
              onBusyChange={onBusyChange}
              onError={onError}
              onNotice={onNotice}
              order={order}
            />
          </section>

          <section className="repair-v2-modal__workspace">
            <RepairAssignmentSection
              execution={execution}
              isBusy={isBusy}
              onBoardChange={onBoardChange}
              onBusyChange={onBusyChange}
              onError={onError}
              onNotice={onNotice}
              order={order}
              user={user}
              users={users}
            />
          </section>

          <section className="repair-v2-modal__workspace">
            <RepairDiagnosisSection
              execution={execution}
              isBusy={isBusy}
              onBoardChange={onBoardChange}
              onBusyChange={onBusyChange}
              onError={onError}
              onNotice={onNotice}
              order={order}
              user={user}
              users={users}
            />
          </section>

          <section className="repair-v2-modal__workspace">
            <RepairVerdictSection
              execution={execution}
              isBusy={isBusy}
              onBoardChange={onBoardChange}
              onBusyChange={onBusyChange}
              onError={onError}
              onNotice={onNotice}
              order={order}
              user={user}
              users={users}
            />
          </section>

          <section className="repair-v2-modal__workspace">
            <RepairInterventionSection
              execution={execution}
              isBusy={isBusy}
              onBoardChange={onBoardChange}
              onBusyChange={onBusyChange}
              onError={onError}
              onNotice={onNotice}
              order={order}
              user={user}
              users={users}
            />
          </section>

          <section className="repair-v2-modal__workspace">
            <RepairPauseSection
              execution={execution}
              isBusy={isBusy}
              onBoardChange={onBoardChange}
              onBusyChange={onBusyChange}
              onError={onError}
              onNotice={onNotice}
              order={order}
              user={user}
              users={users}
            />
          </section>

          <section className="repair-v2-modal__workspace">
            <RepairTestingSection
              execution={execution}
              isBusy={isBusy}
              onBoardChange={onBoardChange}
              onBusyChange={onBusyChange}
              onError={onError}
              onNotice={onNotice}
              order={order}
              user={user}
              users={users}
            />
          </section>

          <section className="repair-v2-modal__workspace">
            <RepairWarrantySection
              execution={execution}
              isBusy={isBusy}
              onBoardChange={onBoardChange}
              onBusyChange={onBusyChange}
              onError={onError}
              onNotice={onNotice}
              order={order}
              user={user}
              users={users}
            />
          </section>

          <section className="repair-v2-modal__workspace">
            <RepairClosureSection
              execution={execution}
              isBusy={isBusy}
              onBoardChange={onBoardChange}
              onBusyChange={onBusyChange}
              onError={onError}
              onNotice={onNotice}
              order={order}
              user={user}
            />
          </section>


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