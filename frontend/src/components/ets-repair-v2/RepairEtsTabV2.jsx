import React, {
  useCallback,
  useEffect,
  useMemo,
  useState,
} from 'react';

import { RefreshCw } from 'lucide-react';

import {
  getRepairBoard,
  initializeRepairExecution,
} from '../../services/api.js';

import { hasPermission } from '../../utils/accessControl.js';

import RepairExecutionCard from './RepairExecutionCard.jsx';
import RepairExecutionModal from './RepairExecutionModal.jsx';

import './repair-ets-v2.css';


/* =========================================================
   CONSTANTES
   ========================================================= */

const CLOSED_STATUSES = new Set([
  'closed',
  'cancelled',
]);

const SUCCESS_STATUSES = new Set([
  'closed',
  'technically_completed',
]);

const BLOCKED_STATUSES = new Set([
  'cancelled',
  'equipment_not_suitable',
]);


/* =========================================================
   HELPERS
   ========================================================= */

function safeArray(value) {
  return Array.isArray(value)
    ? value
    : [];
}


function getRepairItems(order) {
  return safeArray(order?.items).filter(
    (item) =>
      item?.operational_category ===
      'repair',
  );
}


function getExecutionTone(status) {
  if (SUCCESS_STATUSES.has(status)) {
    return 'done';
  }

  if (BLOCKED_STATUSES.has(status)) {
    return 'blocked';
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

  return 'pending';
}


function getActiveBlockerCount(
  executions,
  board,
) {
  const executionBlockers =
    executions.reduce(
      (total, execution) =>
        total +
        safeArray(
          execution?.blockers,
        ).length,
      0,
    );

  const boardBlockers =
    safeArray(board?.blockers).length;

  return Math.max(
    executionBlockers,
    boardBlockers,
  );
}


/* =========================================================
   COMPONENTE
   ========================================================= */

function RepairEtsTabV2({
  order,
  user,
  users = [],
}) {
  /* =======================================================
     ESTADO
     ======================================================= */

  const [board, setBoard] =
    useState(null);

  const [isLoading, setIsLoading] =
    useState(true);

  const [
    isInitializing,
    setIsInitializing,
  ] = useState(false);

  const [
    selectedExecutionId,
    setSelectedExecutionId,
  ] = useState(null);

  const [
    isExecutionModalOpen,
    setIsExecutionModalOpen,
  ] = useState(false);

  const [
    isExecutionBusy,
    setIsExecutionBusy,
  ] = useState(false);

  const [error, setError] =
    useState('');

  const [notice, setNotice] =
    useState('');


  /* =======================================================
     DATOS DERIVADOS
     ======================================================= */

  const repairItems =
    useMemo(
      () => getRepairItems(order),
      [order],
    );


  const hasRepairItems =
    repairItems.length > 0;


  const executions =
    useMemo(
      () =>
        safeArray(
          board?.executions,
        ),
      [board],
    );


  const selectedExecution =
    useMemo(
      () =>
        executions.find(
          (execution) =>
            Number(execution?.id) ===
            Number(selectedExecutionId),
        ) || null,
      [
        executions,
        selectedExecutionId,
      ],
    );


  const canManageRepair =
    useMemo(
      () =>
        hasPermission(
          user,
          'service_orders.repair.manage',
        ),
      [user],
    );


  const metrics =
    useMemo(() => {
      const total =
        executions.length;

      const closed =
        executions.filter(
          (execution) =>
            execution?.status ===
            'closed',
        ).length;

      const active =
        executions.filter(
          (execution) =>
            !CLOSED_STATUSES.has(
              execution?.status,
            ),
        ).length;

      const blockers =
        getActiveBlockerCount(
          executions,
          board,
        );

      return {
        total,
        active,
        closed,
        blockers,
      };
    }, [
      executions,
      board,
    ]);


  /* =======================================================
     CARGA DEL BOARD
     ======================================================= */

  const loadBoard =
    useCallback(
      async ({
        silent = false,
      } = {}) => {
        if (!order?.id) {
          setBoard(null);
          setIsLoading(false);

          return null;
        }

        if (!silent) {
          setIsLoading(true);
        }

        setError('');

        try {
          const result =
            await getRepairBoard(
              order.id,
            );

          setBoard(result);

          return result;
        } catch (requestError) {
          setBoard(null);

          setError(
            requestError?.message ||
              'No fue posible cargar Reparación.',
          );

          return null;
        } finally {
          if (!silent) {
            setIsLoading(false);
          }
        }
      },
      [order?.id],
    );


  /* =======================================================
     CAMBIO DE ETS
     ======================================================= */

  useEffect(() => {
    setBoard(null);

    setSelectedExecutionId(null);
    setIsExecutionModalOpen(false);
    setIsExecutionBusy(false);

    setNotice('');
    setError('');

    loadBoard();
  }, [
    order?.id,
    loadBoard,
  ]);


  /* =======================================================
     CONSISTENCIA DEL EXPEDIENTE SELECCIONADO
     ======================================================= */

  useEffect(() => {
    if (
      !isExecutionModalOpen ||
      selectedExecutionId === null
    ) {
      return;
    }

    const stillExists =
      executions.some(
        (execution) =>
          Number(execution?.id) ===
          Number(selectedExecutionId),
      );

    if (!stillExists) {
      setSelectedExecutionId(null);
      setIsExecutionModalOpen(false);
      setIsExecutionBusy(false);
    }
  }, [
    executions,
    isExecutionModalOpen,
    selectedExecutionId,
  ]);


  /* =======================================================
     INICIALIZACIÓN
     ======================================================= */

  async function initializeRepair() {
    if (
      !order?.id ||
      isInitializing
    ) {
      return;
    }

    setIsInitializing(true);

    setError('');
    setNotice('');

    try {
      const result =
        await initializeRepairExecution(
          order.id,
        );

      setBoard(result);

      setNotice(
        'Reparación inicializada a partir de las partidas del ETS.',
      );
    } catch (requestError) {
      setError(
        requestError?.message ||
          'No fue posible inicializar Reparación.',
      );
    } finally {
      setIsInitializing(false);
    }
  }


  /* =======================================================
     APERTURA DEL EXPEDIENTE
     ======================================================= */

  function handleOpenExecution(
    execution,
  ) {
    if (!execution?.id) {
      return;
    }

    setError('');
    setNotice('');

    setSelectedExecutionId(
      execution.id,
    );

    setIsExecutionModalOpen(true);
  }


  /* =======================================================
     CIERRE DEL EXPEDIENTE
     ======================================================= */

  function handleCloseExecution() {
    if (isExecutionBusy) {
      return;
    }

    setIsExecutionModalOpen(false);
    setSelectedExecutionId(null);

    setError('');
    setNotice('');
  }


  /* =======================================================
     ACTUALIZACIÓN DESDE EL EXPEDIENTE
     ======================================================= */

  function handleExecutionBoardChange(
    nextBoard,
  ) {
    if (!nextBoard) {
      return;
    }

    setBoard(nextBoard);
  }


  function handleExecutionBusyChange(
    value,
  ) {
    setIsExecutionBusy(
      Boolean(value),
    );
  }


  function handleExecutionError(
    message,
  ) {
    setError(
      message || '',
    );

    if (message) {
      setNotice('');
    }
  }


  function handleExecutionNotice(
    message,
  ) {
    setNotice(
      message || '',
    );

    if (message) {
      setError('');
    }
  }


  /* =======================================================
     LOADING
     ======================================================= */

  if (isLoading) {
    return (
      <section className="repair-v2">
        <header className="repair-v2__heading">
          <div>
            <span>
              Vertical operativo
            </span>

            <h3>
              Reparación
            </h3>

            <p>
              Cargando partidas y
              ejecuciones de reparación.
            </p>
          </div>
        </header>

        <div className="repair-v2__skeleton-grid">
          {[1, 2, 3].map(
            (item) => (
              <article
                className="repair-v2__skeleton-card"
                key={item}
              >
                <span />
                <strong />
                <div />
                <div />
              </article>
            ),
          )}
        </div>
      </section>
    );
  }


  /* =======================================================
     ETS SIN REPARACIÓN
     ======================================================= */

  if (!hasRepairItems) {
    return (
      <section className="repair-v2">
        <header className="repair-v2__heading">
          <div>
            <span>
              Vertical operativo
            </span>

            <h3>
              Reparación
            </h3>

            <p>
              Gestión individual de los
              equipos incluidos en servicios
              de reparación.
            </p>
          </div>
        </header>

        <section className="repair-v2__empty">
          <strong>
            Este ETS no contiene
            Reparación
          </strong>

          <span>
            No existen partidas con
            categoría operativa
            &quot;repair&quot; asociadas a
            esta orden.
          </span>
        </section>
      </section>
    );
  }


  /* =======================================================
     SIN EJECUCIÓN
     ======================================================= */

  if (!executions.length) {
    return (
      <section className="repair-v2">
        <header className="repair-v2__heading">
          <div>
            <span>
              Vertical operativo
            </span>

            <h3>
              Reparación
            </h3>

            <p>
              El ETS contiene Reparación,
              pero todavía no existe una
              ejecución operativa disponible.
            </p>
          </div>

          <button
            className="repair-v2__refresh-button"
            disabled={
              isInitializing
            }
            onClick={() =>
              loadBoard()
            }
            type="button"
          >
            <RefreshCw size={16} />

            Actualizar
          </button>
        </header>


        {error ? (
          <div className="repair-v2__alert is-error">
            {error}
          </div>
        ) : null}


        {notice ? (
          <div className="repair-v2__alert is-success">
            {notice}
          </div>
        ) : null}


        <section className="repair-v2__empty">
          <strong>
            Ejecución no materializada
          </strong>

          <span>
            Existe al menos una partida de
            Reparación en el ETS, pero el
            expediente operativo todavía no
            ha sido creado.
          </span>

          {canManageRepair ? (
            <button
              className="primary-button"
              disabled={
                isInitializing
              }
              onClick={
                initializeRepair
              }
              type="button"
            >
              {isInitializing
                ? 'Inicializando...'
                : 'Inicializar Reparación'}
            </button>
          ) : null}
        </section>
      </section>
    );
  }


  /* =======================================================
     VISTA PRINCIPAL
     ======================================================= */

  return (
    <>
      <section className="repair-v2">
        <header className="repair-v2__heading">
          <div>
            <span>
              Vertical operativo
            </span>

            <h3>
              Reparación
            </h3>

            <p>
              Selecciona un equipo para abrir
              su expediente técnico de
              reparación.
            </p>
          </div>


          <div className="repair-v2__heading-actions">
            <small>
              {order?.folio
                ? order.folio
                : `ETS #${order?.id}`}
            </small>

            <button
              className="repair-v2__refresh-button"
              disabled={
                isExecutionBusy
              }
              onClick={() =>
                loadBoard()
              }
              type="button"
            >
              <RefreshCw size={16} />

              Actualizar
            </button>
          </div>
        </header>


        {error ? (
          <div className="repair-v2__alert is-error">
            {error}
          </div>
        ) : null}


        {notice ? (
          <div className="repair-v2__alert is-success">
            {notice}
          </div>
        ) : null}


        <section
          aria-label="Resumen de reparación"
          className="repair-v2__metrics"
        >
          <article>
            <span>
              Reparaciones
            </span>

            <strong>
              {metrics.total}
            </strong>
          </article>


          <article>
            <span>
              Activas
            </span>

            <strong>
              {metrics.active}
            </strong>
          </article>


          <article>
            <span>
              Cerradas
            </span>

            <strong>
              {metrics.closed}
            </strong>
          </article>


          <article>
            <span>
              Bloqueantes
            </span>

            <strong>
              {metrics.blockers}
            </strong>
          </article>
        </section>


        <section className="repair-v2__catalog">
          <header className="repair-v2__section-heading">
            <div>
              <span>
                Operación técnica
              </span>

              <h4>
                Equipos en reparación
              </h4>
            </div>

            <small>
              {executions.length}{' '}
              {executions.length === 1
                ? 'expediente'
                : 'expedientes'}
            </small>
          </header>


          <div className="repair-v2__grid">
            {executions.map(
              (
                execution,
                index,
              ) => (
                <RepairExecutionCard
                  execution={
                    execution
                  }
                  index={index}
                  key={
                    execution.id
                  }
                  onOpen={() =>
                    handleOpenExecution(
                      execution,
                    )
                  }
                  tone={
                    getExecutionTone(
                      execution.status,
                    )
                  }
                  users={users}
                />
              ),
            )}
          </div>
        </section>
      </section>


      <RepairExecutionModal
        board={board}
        error={error}
        execution={
          selectedExecution
        }
        isBusy={
          isExecutionBusy
        }
        isOpen={
          isExecutionModalOpen &&
          Boolean(
            selectedExecution,
          )
        }
        notice={notice}
        onBoardChange={
          handleExecutionBoardChange
        }
        onBusyChange={
          handleExecutionBusyChange
        }
        onClose={
          handleCloseExecution
        }
        onError={
          handleExecutionError
        }
        onNotice={
          handleExecutionNotice
        }
        order={order}
        user={user}
        users={users}
      />
    </>
  );
}


export default RepairEtsTabV2;