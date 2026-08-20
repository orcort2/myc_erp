import {
  AlertTriangle,
  CheckCircle2,
  ChevronDown,
  ChevronRight,
  ClipboardCheck,
  RefreshCw,
  UserRound,
  Wrench,
} from 'lucide-react';
import React, {
  useEffect,
  useMemo,
  useRef,
  useState,
} from 'react';

import {
  addRepairPause,
  addRepairTest,
  assignRepairTechnician,
  completeRepairIntervention,
  completeRepairTechnical,
  concludeRepairEvaluation,
  downloadRepairReport,
  getRepairBoard,
  initializeRepairExecution,
  registerRepairArrival,
  resolveRepairPause,
  saveRepairDiagnosis,
  startRepairEvaluation,
  startRepairIntervention,
} from '../../services/api.js';
import { hasPermission } from '../../utils/accessControl.js';

import './repair-ets.css';


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


const SEVERITY_LABELS = {
  minor: 'Menor',
  moderate: 'Moderada',
  major: 'Mayor',
  critical: 'Crítica',
};


const REPAIRABILITY_LABELS = {
  repairable: 'Reparable',
  conditionally_repairable: 'Reparable con condiciones',
  not_repairable: 'No reparable',
  undetermined: 'Por determinar',
};


const PAUSE_TYPE_LABELS = {
  spare_part: 'Refacción',
  authorization: 'Autorización',
  client_decision: 'Decisión del cliente',
  administrative_investigation: 'Investigación administrativa',
  warehouse: 'Almacén',
};


const TEST_RESULT_LABELS = {
  pass: 'Aprobada',
  fail: 'Fallida',
  inconclusive: 'No concluyente',
};


function safeArray(value) {
  return Array.isArray(value) ? value : [];
}


function safeText(value, fallback = '-') {
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

  const parsed = new Date(value);

  if (Number.isNaN(parsed.getTime())) {
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


function getUserDisplayName(users, userId) {
  if (!userId) {
    return 'Sin asignar';
  }

  const found = users.find(
    (candidate) =>
      Number(candidate.id) === Number(userId),
  );

  return (
    found?.full_name ||
    found?.name ||
    found?.email ||
    `Usuario #${userId}`
  );
}


function isTechnicianCandidate(user) {
  if (user?.is_active === false) {
    return false;
  }

  const roles = safeArray(user?.roles)
    .map((role) =>
      String(role?.name || '')
        .trim()
        .toLowerCase(),
    );

  if (!roles.length) {
    return true;
  }

  return roles.some((role) =>
    [
      'tecnico',
      'técnico',
      'technical',
      'admin',
      'administrador',
      'administrator',
      'desarrollador',
      'developer',
    ].includes(role),
  );
}


function getExecutionTone(status) {
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
      'in_evaluation',
      'in_repair',
      'testing',
      'assigned',
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


function triggerBlobDownload(blob, filename) {
  const url = URL.createObjectURL(blob);

  const anchor = document.createElement('a');

  anchor.href = url;
  anchor.download = filename || 'reporte-reparacion.pdf';

  document.body.appendChild(anchor);

  anchor.click();

  document.body.removeChild(anchor);

  URL.revokeObjectURL(url);
}


function emptyDiagnosis() {
  return {
    reportedIssue: '',
    observedCondition: '',
    findings: '',
    probableCauses: '',
    severity: '',
    repairability: '',
    diagnosisNotes: '',
  };
}


function diagnosisFormFromExecution(execution) {
  const data =
    execution?.diagnosis_data &&
    typeof execution.diagnosis_data === 'object'
      ? execution.diagnosis_data
      : {};

  return {
    reportedIssue:
      data.reported_issue || '',
    observedCondition:
      data.observed_condition || '',
    findings: safeArray(data.findings)
      .join('\n'),
    probableCauses:
      safeArray(data.probable_causes)
        .join('\n'),
    severity:
      data.severity || '',
    repairability:
      data.repairability || '',
    diagnosisNotes:
      data.diagnosis_notes ||
      execution?.diagnosis_notes ||
      '',
  };
}


function linesToArray(value) {
  return String(value || '')
    .split('\n')
    .map((line) => line.trim())
    .filter(Boolean);
}


function RepairEtsTab({
  order,
  user,
  users = [],
}) {
  const [board, setBoard] =
    useState(null);

  const [
    selectedExecutionId,
    setSelectedExecutionId,
  ] = useState(null);

  const [expandedExecutionIds, setExpandedExecutionIds] =
    useState(() => new Set());

  const [isLoading, setIsLoading] =
    useState(true);

  const [isSaving, setIsSaving] =
    useState(false);

  const [isInitializing, setIsInitializing] =
    useState(false);

  const [error, setError] =
    useState('');

  const [notice, setNotice] =
    useState('');

  const [arrivalForm, setArrivalForm] =
    useState({
      equipmentId: '',
      name: '',
      brand: '',
      model: '',
      serialNumber: '',
    });

  const [
    selectedTechnicianId,
    setSelectedTechnicianId,
  ] = useState('');

  const [diagnosisForm, setDiagnosisForm] =
    useState(emptyDiagnosis);

  const [conclusionForm, setConclusionForm] =
    useState({
      conclusion: 'repaired',
      reason: '',
    });

  const [
    interventionDescription,
    setInterventionDescription,
  ] = useState('');

  const [
    interventionCompletion,
    setInterventionCompletion,
  ] = useState({
    outcome: 'effective',
    actions: '',
    removedComponents: '',
  });

  const [testForm, setTestForm] =
    useState({
      testType: '',
      result: 'pass',
      notes: '',
      interventionId: '',
    });

  const [pauseForm, setPauseForm] =
    useState({
      pauseType: 'spare_part',
      reason: '',
      responsibleUserId: '',
      tentativeResumeAt: '',
    });

  const [
    pauseResolutionById,
    setPauseResolutionById,
  ] = useState({});


  const technicianOptions =
    useMemo(
      () =>
        users.filter(
          isTechnicianCandidate,
        ),
      [users],
    );


  const executions =
    useMemo(
      () => safeArray(board?.executions),
      [board],
    );


  const hasRepairItem =
    useMemo(
      () =>
        safeArray(order?.items).some(
          (item) =>
            item.operational_category ===
            'repair',
        ),
      [order],
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


  const selectedExecution =
    useMemo(() => {
      if (!executions.length) {
        return null;
      }

      const selected =
        executions.find(
          (execution) =>
            Number(execution.id) ===
            Number(selectedExecutionId),
        );

      return selected || executions[0];
    }, [
      executions,
      selectedExecutionId,
    ]);


  const activeIntervention =
    useMemo(() => {
      if (!selectedExecution) {
        return null;
      }

      return (
        safeArray(
          selectedExecution.interventions,
        )
          .filter(
            (intervention) =>
              !intervention.completed_at,
          )
          .sort(
            (left, right) =>
              Number(right.sequence || 0) -
              Number(left.sequence || 0),
          )[0] || null
      );
    }, [selectedExecution]);


  const openPauses =
    useMemo(
      () =>
        safeArray(
          selectedExecution?.pauses,
        ).filter(
          (pause) =>
            pause.status !== 'resolved',
        ),
      [selectedExecution],
    );


  async function loadBoard({
    preserveSelection = true,
  } = {}) {
    if (!order?.id) {
      setBoard(null);
      setIsLoading(false);
      return;
    }

    setIsLoading(true);
    setError('');

    try {
      const result =
        await getRepairBoard(order.id);

      const nextExecutions =
        safeArray(result?.executions);

      setBoard(result);

      setSelectedExecutionId(
        (current) => {
          if (
            preserveSelection &&
            current &&
            nextExecutions.some(
              (execution) =>
                Number(execution.id) ===
                Number(current),
            )
          ) {
            return current;
          }

          return (
            nextExecutions[0]?.id ??
            null
          );
        },
      );
    } catch (requestError) {
      setError(
        requestError?.message ||
          'No fue posible cargar Reparación.',
      );
    } finally {
      setIsLoading(false);
    }
  }


  useEffect(() => {
    loadBoard({
      preserveSelection: false,
    });
  }, [order?.id]);


  useEffect(() => {
    if (!selectedExecution) {
      setDiagnosisForm(
        emptyDiagnosis(),
      );

      setSelectedTechnicianId('');
      return;
    }

    setDiagnosisForm(
      diagnosisFormFromExecution(
        selectedExecution,
      ),
    );

    setSelectedTechnicianId(
      selectedExecution.technician_id
        ? String(
            selectedExecution.technician_id,
          )
        : '',
    );
  }, [selectedExecution?.id]);


  function updateBoard(nextBoard) {
    setBoard(nextBoard);

    const stillExists =
      safeArray(nextBoard?.executions)
        .some(
          (execution) =>
            Number(execution.id) ===
            Number(selectedExecutionId),
        );

    if (!stillExists) {
      setSelectedExecutionId(
        nextBoard?.executions?.[0]?.id ??
          null,
      );
    }
  }


  const initAttemptedForOrderRef =
    useRef(null);


  async function attemptInitialize() {
    if (
      !order?.id ||
      isInitializing
    ) {
      return;
    }

    setIsInitializing(true);
    setError('');

    try {
      const result =
        await initializeRepairExecution(
          order.id,
        );

      updateBoard(result);

      setNotice(
        'Reparación inicializada a partir de las partidas existentes.',
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


  useEffect(() => {
    // Auto-reconciliación: una ETS con partida repair puede existir sin
    // RepairExecution materializada (creada antes de que la inicialización
    // automática de create_service_order() existiera). GET /repair devuelve
    // 404 ("El ETS no contiene Reparación") en ese caso -- no un board con
    // executions: [] -- así que board se queda en null y el efecto se
    // apoya en executions.length (siempre 0 mientras board es null) en vez
    // de exigir un board no-nulo. Se intenta UNA sola vez por
    // service_order_id mientras el componente está montado; el ref (no el
    // estado) es lo que impide reintentos automáticos, incluso si el
    // intento falla o si el GET falló por otra razón.
    if (
      isLoading ||
      !order?.id ||
      executions.length > 0 ||
      !hasRepairItem ||
      !canManageRepair
    ) {
      return;
    }

    if (
      initAttemptedForOrderRef.current ===
      order.id
    ) {
      return;
    }

    initAttemptedForOrderRef.current =
      order.id;

    attemptInitialize();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [
    isLoading,
    order?.id,
    executions.length,
    hasRepairItem,
    canManageRepair,
  ]);


  async function runAction(
    action,
    {
      successMessage = '',
    } = {},
  ) {
    setIsSaving(true);
    setError('');
    setNotice('');

    try {
      const result =
        await action();

      if (result) {
        updateBoard(result);
      }

      if (successMessage) {
        setNotice(successMessage);
      }

      return result;
    } catch (requestError) {
      setError(
        requestError?.message ||
          'La operación no pudo completarse.',
      );

      return null;
    } finally {
      setIsSaving(false);
    }
  }


  function toggleExecution(
    executionId,
  ) {
    setExpandedExecutionIds(
      (current) => {
        const next =
          new Set(current);

        if (
          next.has(executionId)
        ) {
          next.delete(executionId);
        } else {
          next.add(executionId);
        }

        return next;
      },
    );
  }


  async function submitArrival(
    event,
  ) {
    event.preventDefault();

    if (!selectedExecution) {
      return;
    }

    const equipmentId =
      arrivalForm.equipmentId
        ? Number(
            arrivalForm.equipmentId,
          )
        : null;

    const name =
      arrivalForm.name.trim();

    if (!equipmentId && !name) {
      setError(
        'Captura el equipo existente o el nombre del equipo recibido.',
      );
      return;
    }

    const result =
      await runAction(
        () =>
          registerRepairArrival(
            order.id,
            selectedExecution.id,
            {
              equipment_id:
                equipmentId,
              name:
                equipmentId
                  ? null
                  : name,
              brand:
                arrivalForm.brand.trim() ||
                null,
              model:
                arrivalForm.model.trim() ||
                null,
              serial_number:
                arrivalForm.serialNumber.trim() ||
                null,
            },
          ),
        {
          successMessage:
            'Equipo recibido y vinculado a Reparación.',
        },
      );

    if (result) {
      setArrivalForm({
        equipmentId: '',
        name: '',
        brand: '',
        model: '',
        serialNumber: '',
      });
    }
  }


  async function submitAssignment(
    event,
  ) {
    event.preventDefault();

    if (
      !selectedExecution ||
      !selectedTechnicianId
    ) {
      setError(
        'Selecciona un técnico.',
      );
      return;
    }

    await runAction(
      () =>
        assignRepairTechnician(
          order.id,
          selectedExecution.id,
          {
            technician_id:
              Number(
                selectedTechnicianId,
              ),
          },
        ),
      {
        successMessage:
          'Técnico asignado.',
      },
    );
  }


  async function handleStartEvaluation() {
    if (!selectedExecution) {
      return;
    }

    await runAction(
      () =>
        startRepairEvaluation(
          order.id,
          selectedExecution.id,
        ),
      {
        successMessage:
          'Evaluación técnica iniciada.',
      },
    );
  }


  async function submitDiagnosis(
    event,
  ) {
    event.preventDefault();

    if (!selectedExecution) {
      return;
    }

    const payload = {
      reported_issue:
        diagnosisForm.reportedIssue.trim() ||
        null,

      observed_condition:
        diagnosisForm.observedCondition.trim() ||
        null,

      findings:
        linesToArray(
          diagnosisForm.findings,
        ),

      probable_causes:
        linesToArray(
          diagnosisForm.probableCauses,
        ),

      severity:
        diagnosisForm.severity ||
        null,

      repairability:
        diagnosisForm.repairability ||
        null,

      diagnosis_notes:
        diagnosisForm.diagnosisNotes.trim() ||
        null,
    };

    const hasContent =
      Boolean(
        payload.reported_issue ||
        payload.observed_condition ||
        payload.findings.length ||
        payload.probable_causes.length ||
        payload.severity ||
        payload.repairability ||
        payload.diagnosis_notes,
      );

    if (!hasContent) {
      setError(
        'El diagnóstico requiere al menos una evidencia técnica.',
      );
      return;
    }

    await runAction(
      () =>
        saveRepairDiagnosis(
          order.id,
          selectedExecution.id,
          payload,
        ),
      {
        successMessage:
          'Diagnóstico guardado.',
      },
    );
  }


  async function submitConclusion(
    event,
  ) {
    event.preventDefault();

    if (!selectedExecution) {
      return;
    }

    const reason =
      conclusionForm.reason.trim();

    if (
      conclusionForm.conclusion ===
        'equipment_not_suitable' &&
      reason.length < 10
    ) {
      setError(
        'Cuando el equipo no es apto se requiere una justificación de al menos 10 caracteres.',
      );
      return;
    }

    await runAction(
      () =>
        concludeRepairEvaluation(
          order.id,
          selectedExecution.id,
          {
            conclusion:
              conclusionForm.conclusion,
            conclusion_reason:
              reason || null,
          },
        ),
      {
        successMessage:
          'Evaluación concluida.',
      },
    );
  }


  async function submitIntervention(
    event,
  ) {
    event.preventDefault();

    if (!selectedExecution) {
      return;
    }

    const description =
      interventionDescription.trim();

    if (description.length < 3) {
      setError(
        'Describe la intervención a realizar.',
      );
      return;
    }

    const result =
      await runAction(
        () =>
          startRepairIntervention(
            order.id,
            selectedExecution.id,
            {
              description,
            },
          ),
        {
          successMessage:
            'Intervención iniciada.',
        },
      );

    if (result) {
      setInterventionDescription('');
    }
  }


  function parseActionLines(value) {
    return linesToArray(value)
      .map((description) => ({
        description,
      }));
  }


  function parseRemovedComponents(
    value,
  ) {
    return linesToArray(value)
      .map((line) => ({
        name: line,
        disposition:
          'return_to_client',
      }));
  }


  async function submitInterventionCompletion(
    event,
  ) {
    event.preventDefault();

    if (
      !selectedExecution ||
      !activeIntervention
    ) {
      return;
    }

    await runAction(
      () =>
        completeRepairIntervention(
          order.id,
          selectedExecution.id,
          activeIntervention.id,
          {
            outcome:
              interventionCompletion.outcome,

            actions:
              parseActionLines(
                interventionCompletion.actions,
              ),

            removed_components:
              parseRemovedComponents(
                interventionCompletion.removedComponents,
              ),
          },
        ),
      {
        successMessage:
          'Intervención completada. Continúa con las pruebas.',
      },
    );

    setInterventionCompletion({
      outcome: 'effective',
      actions: '',
      removedComponents: '',
    });
  }


  async function submitTest(
    event,
  ) {
    event.preventDefault();

    if (!selectedExecution) {
      return;
    }

    const type =
      testForm.testType.trim();

    if (!type) {
      setError(
        'Captura el tipo de prueba.',
      );
      return;
    }

    const result =
      await runAction(
        () =>
          addRepairTest(
            order.id,
            selectedExecution.id,
            {
              test_type: type,
              result:
                testForm.result,
              notes:
                testForm.notes.trim() ||
                null,
              intervention_id:
                testForm.interventionId
                  ? Number(
                      testForm.interventionId,
                    )
                  : null,
            },
          ),
        {
          successMessage:
            testForm.result === 'pass'
              ? 'Prueba aprobada.'
              : testForm.result === 'fail'
                ? 'Prueba fallida. La reparación vuelve a intervención.'
                : 'Prueba registrada como no concluyente.',
        },
      );

    if (result) {
      setTestForm({
        testType: '',
        result: 'pass',
        notes: '',
        interventionId: '',
      });
    }
  }


  async function submitPause(
    event,
  ) {
    event.preventDefault();

    if (!selectedExecution) {
      return;
    }

    const reason =
      pauseForm.reason.trim();

    if (
      !reason ||
      !pauseForm.responsibleUserId
    ) {
      setError(
        'Captura motivo y responsable de la pausa.',
      );
      return;
    }

    const result =
      await runAction(
        () =>
          addRepairPause(
            order.id,
            selectedExecution.id,
            {
              pause_type:
                pauseForm.pauseType,

              reason,

              responsible_user_id:
                Number(
                  pauseForm.responsibleUserId,
                ),

              tentative_resume_at:
                pauseForm.tentativeResumeAt
                  ? new Date(
                      pauseForm.tentativeResumeAt,
                    ).toISOString()
                  : null,
            },
          ),
        {
          successMessage:
            'Pausa operativa registrada.',
        },
      );

    if (result) {
      setPauseForm({
        pauseType: 'spare_part',
        reason: '',
        responsibleUserId: '',
        tentativeResumeAt: '',
      });
    }
  }


  async function submitPauseResolution(
    pause,
  ) {
    if (!selectedExecution) {
      return;
    }

    const resolution =
      String(
        pauseResolutionById[
          pause.id
        ] || '',
      ).trim();

    if (resolution.length < 3) {
      setError(
        'Captura la resolución de la pausa.',
      );
      return;
    }

    const result =
      await runAction(
        () =>
          resolveRepairPause(
            order.id,
            selectedExecution.id,
            pause.id,
            {
              resolution,
            },
          ),
        {
          successMessage:
            'Pausa resuelta.',
        },
      );

    if (result) {
      setPauseResolutionById(
        (current) => {
          const next = {
            ...current,
          };

          delete next[pause.id];

          return next;
        },
      );
    }
  }


  async function handleTechnicalComplete() {
    if (!selectedExecution) {
      return;
    }

    await runAction(
      () =>
        completeRepairTechnical(
          order.id,
          selectedExecution.id,
        ),
      {
        successMessage:
          'Cierre técnico registrado.',
      },
    );
  }


  async function handleDownloadReport() {
    if (!selectedExecution) {
      return;
    }

    setIsSaving(true);
    setError('');
    setNotice('');

    try {
      const result =
        await downloadRepairReport(
          order.id,
          selectedExecution.id,
        );

      if (result?.blob) {
        triggerBlobDownload(
          result.blob,
          result.filename ||
            `reparacion-${order.folio || order.id}.pdf`,
        );
      } else if (
        result instanceof Blob
      ) {
        triggerBlobDownload(
          result,
          `reparacion-${order.folio || order.id}.pdf`,
        );
      }

      setNotice(
        'Reporte de reparación generado.',
      );
    } catch (requestError) {
      setError(
        requestError?.message ||
          'No fue posible generar el reporte.',
      );
    } finally {
      setIsSaving(false);
    }
  }


  if (isLoading) {
    return (
      <section className="repair-ets">
        <div className="clients-empty">
          Cargando Reparación...
        </div>
      </section>
    );
  }


  if (!executions.length) {
    let emptyStateMessage =
      'Esta orden no contiene partidas de Reparación.';

    if (hasRepairItem) {
      emptyStateMessage =
        'Esta orden contiene una partida de ' +
        'Reparación, pero todavía no tiene una ' +
        'ejecución operativa materializada.';
    }

    if (isInitializing) {
      emptyStateMessage =
        'Inicializando Reparación a partir ' +
        'de las partidas existentes...';
    }

    return (
      <section className="repair-ets">
        <div className="quotation-section">
          <div className="quotation-section__title">
            <div>
              <p>ETS / Reparación</p>
              <h3>
                Sin ejecuciones de reparación
              </h3>
            </div>

            <button
              className="table-button"
              disabled={
                isLoading ||
                isInitializing
              }
              onClick={() =>
                loadBoard({
                  preserveSelection: false,
                })
              }
              type="button"
            >
              <RefreshCw size={16} />
              Actualizar
            </button>
          </div>

          {error ? (
            <div className="form-error dashboard-error">
              {error}
            </div>
          ) : null}

          <div className="clients-empty">
            {emptyStateMessage}
          </div>

          {hasRepairItem ? (
            <button
              className="primary-button"
              disabled={isInitializing}
              onClick={attemptInitialize}
              type="button"
            >
              {isInitializing
                ? 'Inicializando...'
                : 'Inicializar Reparación'}
            </button>
          ) : null}
        </div>
      </section>
    );
  }


  return (
    <section className="repair-ets">
      {error ? (
        <div className="form-error dashboard-error">
          {error}
        </div>
      ) : null}

      {notice ? (
        <div className="form-notice dashboard-error">
          {notice}
        </div>
      ) : null}


      <section className="quotation-section repair-ets__header">
        <div className="quotation-section__title">
          <div>
            <p>ETS / Reparación</p>

            <h3>
              Gestión técnica de reparación
            </h3>

            <span>
              {order?.folio || `ETS #${order?.id}`}
            </span>
          </div>

          <button
            className="table-button"
            disabled={
              isLoading ||
              isSaving
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


        <div className="ets-metric-strip">
          <span className="ets-metric-badge">
            <strong>
              {executions.length}
            </strong>
            Reparaciones
          </span>

          <span className="ets-metric-badge">
            <strong>
              {
                executions.filter(
                  (execution) =>
                    execution.status ===
                    'closed',
                ).length
              }
            </strong>
            Cerradas
          </span>

          <span className="ets-metric-badge">
            <strong>
              {
                executions.filter(
                  (execution) =>
                    ![
                      'closed',
                      'cancelled',
                    ].includes(
                      execution.status,
                    ),
                ).length
              }
            </strong>
            Activas
          </span>

          <span className="ets-metric-badge">
            <strong>
              {safeArray(
                board?.blockers,
              ).length}
            </strong>
            Bloqueantes
          </span>
        </div>
      </section>


      <div className="repair-ets__layout">
        <aside className="repair-ets__executions">
          <div className="repair-ets__panel-heading">
            <div>
              <span>
                Equipos / partidas
              </span>

              <strong>
                Reparaciones
              </strong>
            </div>
          </div>

          {executions.map(
            (execution) => {
              const active =
                Number(
                  selectedExecution?.id,
                ) ===
                Number(execution.id);

              const expanded =
                expandedExecutionIds.has(
                  execution.id,
                );

              return (
                <article
                  className={[
                    'repair-execution-card',
                    active
                      ? 'is-selected'
                      : '',
                  ]
                    .filter(Boolean)
                    .join(' ')}
                  key={execution.id}
                >
                  <button
                    className="repair-execution-card__main"
                    onClick={() =>
                      setSelectedExecutionId(
                        execution.id,
                      )
                    }
                    type="button"
                  >
                    <div>
                      <small>
                        OT-
                        {safeText(
                          execution.work_order_number,
                        )}
                      </small>

                      <strong>
                        {safeText(
                          execution.equipment_name,
                          'Equipo sin identificar',
                        )}
                      </strong>
                    </div>

                    <span
                      className={`ets-stage-badge is-${getExecutionTone(
                        execution.status,
                      )}`}
                    >
                      {REPAIR_STATUS_LABELS[
                        execution.status
                      ] ||
                        execution.status}
                    </span>
                  </button>

                  <button
                    aria-expanded={
                      expanded
                    }
                    className="repair-execution-card__expand"
                    onClick={() =>
                      toggleExecution(
                        execution.id,
                      )
                    }
                    type="button"
                  >
                    {expanded ? (
                      <ChevronDown
                        size={15}
                      />
                    ) : (
                      <ChevronRight
                        size={15}
                      />
                    )}

                    Detalles
                  </button>

                  {expanded ? (
                    <dl className="repair-execution-card__details">
                      <div>
                        <dt>
                          Técnico
                        </dt>
                        <dd>
                          {getUserDisplayName(
                            users,
                            execution.technician_id,
                          )}
                        </dd>
                      </div>

                      <div>
                        <dt>
                          Intervenciones
                        </dt>
                        <dd>
                          {
                            safeArray(
                              execution.interventions,
                            ).length
                          }
                        </dd>
                      </div>

                      <div>
                        <dt>
                          Pruebas
                        </dt>
                        <dd>
                          {
                            safeArray(
                              execution.tests,
                            ).length
                          }
                        </dd>
                      </div>

                      <div>
                        <dt>
                          Pausas abiertas
                        </dt>
                        <dd>
                          {
                            safeArray(
                              execution.pauses,
                            ).filter(
                              (pause) =>
                                pause.status !==
                                'resolved',
                            ).length
                          }
                        </dd>
                      </div>
                    </dl>
                  ) : null}
                </article>
              );
            },
          )}
        </aside>


        {selectedExecution ? (
          <main className="repair-ets__workspace">
            <section className="quotation-section repair-execution-summary">
              <div className="quotation-section__title">
                <div>
                  <p>
                    Ejecución #
                    {selectedExecution.id}
                  </p>

                  <h3>
                    {selectedExecution.equipment_name}
                  </h3>
                </div>

                <span
                  className={`ets-inline-stage is-${getExecutionTone(
                    selectedExecution.status,
                  )}`}
                >
                  {REPAIR_STATUS_LABELS[
                    selectedExecution.status
                  ] ||
                    selectedExecution.status}
                </span>
              </div>

              <div className="quotation-commercial-grid service-order-info-grid">
                <article>
                  <span>
                    Orden de trabajo
                  </span>

                  <strong>
                    OT-
                    {selectedExecution.work_order_number}
                  </strong>
                </article>

                <article>
                  <span>
                    Equipo
                  </span>

                  <strong>
                    {selectedExecution.equipment_name}
                  </strong>
                </article>

                <article>
                  <span>
                    Técnico
                  </span>

                  <strong>
                    {getUserDisplayName(
                      users,
                      selectedExecution.technician_id,
                    )}
                  </strong>
                </article>

                <article>
                  <span>
                    Estado
                  </span>

                  <strong>
                    {REPAIR_STATUS_LABELS[
                      selectedExecution.status
                    ] ||
                      selectedExecution.status}
                  </strong>
                </article>

                <article>
                  <span>
                    Intervenciones
                  </span>

                  <strong>
                    {
                      safeArray(
                        selectedExecution.interventions,
                      ).length
                    }
                  </strong>
                </article>

                <article>
                  <span>
                    Pruebas
                  </span>

                  <strong>
                    {
                      safeArray(
                        selectedExecution.tests,
                      ).length
                    }
                  </strong>
                </article>
              </div>


              {safeArray(
                selectedExecution.blockers,
              ).length ? (
                <div className="repair-blockers">
                  <div className="repair-blockers__heading">
                    <AlertTriangle
                      size={18}
                    />

                    <strong>
                      Bloqueantes activos
                    </strong>
                  </div>

                  {safeArray(
                    selectedExecution.blockers,
                  ).map(
                    (blocker, index) => (
                      <article
                        key={`blocker-${index}`}
                      >
                        {safeText(
                          blocker.message ||
                            blocker.reason ||
                            blocker.code,
                          'Bloqueante operativo',
                        )}
                      </article>
                    ),
                  )}
                </div>
              ) : null}
            </section>


            {selectedExecution.status ===
            'pending_arrival' ? (
              <section className="quotation-section">
                <div className="quotation-section__title">
                  <div>
                    <p>
                      Recepción
                    </p>

                    <h3>
                      Confirmar arribo del equipo
                    </h3>
                  </div>
                </div>

                <form
                  className="repair-form"
                  onSubmit={
                    submitArrival
                  }
                >
                  <label>
                    ID de equipo existente
                    <input
                      min="1"
                      onChange={(
                        event,
                      ) =>
                        setArrivalForm(
                          (current) => ({
                            ...current,
                            equipmentId:
                              event
                                .target
                                .value,
                          }),
                        )
                      }
                      placeholder="Opcional"
                      type="number"
                      value={
                        arrivalForm.equipmentId
                      }
                    />
                  </label>

                  <label>
                    Nombre del equipo
                    <input
                      onChange={(
                        event,
                      ) =>
                        setArrivalForm(
                          (current) => ({
                            ...current,
                            name:
                              event
                                .target
                                .value,
                          }),
                        )
                      }
                      type="text"
                      value={
                        arrivalForm.name
                      }
                    />
                  </label>

                  <label>
                    Marca
                    <input
                      onChange={(
                        event,
                      ) =>
                        setArrivalForm(
                          (current) => ({
                            ...current,
                            brand:
                              event
                                .target
                                .value,
                          }),
                        )
                      }
                      type="text"
                      value={
                        arrivalForm.brand
                      }
                    />
                  </label>

                  <label>
                    Modelo
                    <input
                      onChange={(
                        event,
                      ) =>
                        setArrivalForm(
                          (current) => ({
                            ...current,
                            model:
                              event
                                .target
                                .value,
                          }),
                        )
                      }
                      type="text"
                      value={
                        arrivalForm.model
                      }
                    />
                  </label>

                  <label>
                    Serie
                    <input
                      onChange={(
                        event,
                      ) =>
                        setArrivalForm(
                          (current) => ({
                            ...current,
                            serialNumber:
                              event
                                .target
                                .value,
                          }),
                        )
                      }
                      type="text"
                      value={
                        arrivalForm.serialNumber
                      }
                    />
                  </label>

                  <div className="repair-form__actions">
                    <button
                      className="primary-button"
                      disabled={
                        isSaving
                      }
                      type="submit"
                    >
                      Confirmar recepción
                    </button>
                  </div>
                </form>
              </section>
            ) : null}


            {[
              'pending_assignment',
              'assigned',
            ].includes(
              selectedExecution.status,
            ) ? (
              <section className="quotation-section">
                <div className="quotation-section__title">
                  <div>
                    <p>
                      Responsable
                    </p>

                    <h3>
                      Asignación técnica
                    </h3>
                  </div>
                </div>

                <form
                  className="repair-form"
                  onSubmit={
                    submitAssignment
                  }
                >
                  <label className="repair-form__wide">
                    Técnico
                    <select
                      onChange={(
                        event,
                      ) =>
                        setSelectedTechnicianId(
                          event.target
                            .value,
                        )
                      }
                      value={
                        selectedTechnicianId
                      }
                    >
                      <option value="">
                        Selecciona técnico
                      </option>

                      {technicianOptions.map(
                        (
                          technician,
                        ) => (
                          <option
                            key={
                              technician.id
                            }
                            value={
                              technician.id
                            }
                          >
                            {technician.full_name ||
                              technician.email}
                          </option>
                        ),
                      )}
                    </select>
                  </label>

                  <div className="repair-form__actions">
                    <button
                      className="table-button"
                      disabled={
                        isSaving
                      }
                      type="submit"
                    >
                      <UserRound
                        size={16}
                      />
                      Guardar asignación
                    </button>

                    {selectedExecution.status ===
                    'assigned' ? (
                      <button
                        className="primary-button"
                        disabled={
                          isSaving
                        }
                        onClick={
                          handleStartEvaluation
                        }
                        type="button"
                      >
                        Iniciar evaluación
                      </button>
                    ) : null}
                  </div>
                </form>
              </section>
            ) : null}


            {selectedExecution.status ===
            'in_evaluation' ? (
              <>
                <section className="quotation-section">
                  <div className="quotation-section__title">
                    <div>
                      <p>
                        Evaluación
                      </p>

                      <h3>
                        Diagnóstico estructurado
                      </h3>
                    </div>
                  </div>

                  <form
                    className="repair-form"
                    onSubmit={
                      submitDiagnosis
                    }
                  >
                    <label className="repair-form__wide">
                      Falla reportada
                      <textarea
                        onChange={(
                          event,
                        ) =>
                          setDiagnosisForm(
                            (
                              current,
                            ) => ({
                              ...current,
                              reportedIssue:
                                event
                                  .target
                                  .value,
                            }),
                          )
                        }
                        rows={3}
                        value={
                          diagnosisForm.reportedIssue
                        }
                      />
                    </label>

                    <label className="repair-form__wide">
                      Condición observada
                      <textarea
                        onChange={(
                          event,
                        ) =>
                          setDiagnosisForm(
                            (
                              current,
                            ) => ({
                              ...current,
                              observedCondition:
                                event
                                  .target
                                  .value,
                            }),
                          )
                        }
                        rows={3}
                        value={
                          diagnosisForm.observedCondition
                        }
                      />
                    </label>

                    <label>
                      Severidad
                      <select
                        onChange={(
                          event,
                        ) =>
                          setDiagnosisForm(
                            (
                              current,
                            ) => ({
                              ...current,
                              severity:
                                event
                                  .target
                                  .value,
                            }),
                          )
                        }
                        value={
                          diagnosisForm.severity
                        }
                      >
                        <option value="">
                          Sin definir
                        </option>

                        {Object.entries(
                          SEVERITY_LABELS,
                        ).map(
                          ([
                            value,
                            label,
                          ]) => (
                            <option
                              key={
                                value
                              }
                              value={
                                value
                              }
                            >
                              {label}
                            </option>
                          ),
                        )}
                      </select>
                    </label>

                    <label>
                      Reparabilidad
                      <select
                        onChange={(
                          event,
                        ) =>
                          setDiagnosisForm(
                            (
                              current,
                            ) => ({
                              ...current,
                              repairability:
                                event
                                  .target
                                  .value,
                            }),
                          )
                        }
                        value={
                          diagnosisForm.repairability
                        }
                      >
                        <option value="">
                          Sin definir
                        </option>

                        {Object.entries(
                          REPAIRABILITY_LABELS,
                        ).map(
                          ([
                            value,
                            label,
                          ]) => (
                            <option
                              key={
                                value
                              }
                              value={
                                value
                              }
                            >
                              {label}
                            </option>
                          ),
                        )}
                      </select>
                    </label>

                    <label className="repair-form__wide">
                      Hallazgos
                      <textarea
                        onChange={(
                          event,
                        ) =>
                          setDiagnosisForm(
                            (
                              current,
                            ) => ({
                              ...current,
                              findings:
                                event
                                  .target
                                  .value,
                            }),
                          )
                        }
                        placeholder="Un hallazgo por línea"
                        rows={5}
                        value={
                          diagnosisForm.findings
                        }
                      />
                    </label>

                    <label className="repair-form__wide">
                      Causas probables
                      <textarea
                        onChange={(
                          event,
                        ) =>
                          setDiagnosisForm(
                            (
                              current,
                            ) => ({
                              ...current,
                              probableCauses:
                                event
                                  .target
                                  .value,
                            }),
                          )
                        }
                        placeholder="Una causa por línea"
                        rows={5}
                        value={
                          diagnosisForm.probableCauses
                        }
                      />
                    </label>

                    <label className="repair-form__wide">
                      Notas del diagnóstico
                      <textarea
                        onChange={(
                          event,
                        ) =>
                          setDiagnosisForm(
                            (
                              current,
                            ) => ({
                              ...current,
                              diagnosisNotes:
                                event
                                  .target
                                  .value,
                            }),
                          )
                        }
                        rows={4}
                        value={
                          diagnosisForm.diagnosisNotes
                        }
                      />
                    </label>

                    <div className="repair-form__actions">
                      <button
                        className="table-button"
                        disabled={
                          isSaving
                        }
                        type="submit"
                      >
                        <ClipboardCheck
                          size={16}
                        />
                        Guardar diagnóstico
                      </button>
                    </div>
                  </form>
                </section>


                <section className="quotation-section">
                  <div className="quotation-section__title">
                    <div>
                      <p>
                        Dictamen
                      </p>

                      <h3>
                        Concluir evaluación
                      </h3>
                    </div>
                  </div>

                  <form
                    className="repair-form"
                    onSubmit={
                      submitConclusion
                    }
                  >
                    <label>
                      Resultado
                      <select
                        onChange={(
                          event,
                        ) =>
                          setConclusionForm(
                            (
                              current,
                            ) => ({
                              ...current,
                              conclusion:
                                event
                                  .target
                                  .value,
                            }),
                          )
                        }
                        value={
                          conclusionForm.conclusion
                        }
                      >
                        <option value="repaired">
                          Proceder a reparación
                        </option>

                        <option value="equipment_not_suitable">
                          Equipo no apto
                        </option>
                      </select>
                    </label>

                    <label className="repair-form__wide">
                      Justificación
                      <textarea
                        onChange={(
                          event,
                        ) =>
                          setConclusionForm(
                            (
                              current,
                            ) => ({
                              ...current,
                              reason:
                                event
                                  .target
                                  .value,
                            }),
                          )
                        }
                        rows={3}
                        value={
                          conclusionForm.reason
                        }
                      />
                    </label>

                    <div className="repair-form__actions">
                      <button
                        className="primary-button"
                        disabled={
                          isSaving
                        }
                        type="submit"
                      >
                        Concluir evaluación
                      </button>
                    </div>
                  </form>
                </section>
              </>
            ) : null}


            {selectedExecution.status ===
            'in_repair' ? (
              <section className="quotation-section">
                <div className="quotation-section__title">
                  <div>
                    <p>
                      Intervención
                    </p>

                    <h3>
                      Trabajo técnico
                    </h3>
                  </div>
                </div>

                {activeIntervention ? (
                  <form
                    className="repair-form"
                    onSubmit={
                      submitInterventionCompletion
                    }
                  >
                    <div className="repair-active-intervention repair-form__wide">
                      <Wrench
                        size={19}
                      />

                      <div>
                        <span>
                          Intervención #
                          {activeIntervention.sequence}
                        </span>

                        <strong>
                          {activeIntervention.description}
                        </strong>

                        <small>
                          Iniciada{' '}
                          {formatDateTime(
                            activeIntervention.started_at,
                          )}
                        </small>
                      </div>
                    </div>

                    <label>
                      Resultado
                      <select
                        onChange={(
                          event,
                        ) =>
                          setInterventionCompletion(
                            (
                              current,
                            ) => ({
                              ...current,
                              outcome:
                                event
                                  .target
                                  .value,
                            }),
                          )
                        }
                        value={
                          interventionCompletion.outcome
                        }
                      >
                        <option value="effective">
                          Efectiva
                        </option>

                        <option value="partial">
                          Parcial
                        </option>

                        <option value="ineffective">
                          No efectiva
                        </option>
                      </select>
                    </label>

                    <label className="repair-form__wide">
                      Acciones realizadas
                      <textarea
                        onChange={(
                          event,
                        ) =>
                          setInterventionCompletion(
                            (
                              current,
                            ) => ({
                              ...current,
                              actions:
                                event
                                  .target
                                  .value,
                            }),
                          )
                        }
                        placeholder="Una acción por línea"
                        rows={5}
                        value={
                          interventionCompletion.actions
                        }
                      />
                    </label>

                    <label className="repair-form__wide">
                      Componentes retirados
                      <textarea
                        onChange={(
                          event,
                        ) =>
                          setInterventionCompletion(
                            (
                              current,
                            ) => ({
                              ...current,
                              removedComponents:
                                event
                                  .target
                                  .value,
                            }),
                          )
                        }
                        placeholder="Un componente por línea. Por ahora se registra con devolución al cliente."
                        rows={4}
                        value={
                          interventionCompletion.removedComponents
                        }
                      />
                    </label>

                    <div className="repair-form__actions">
                      <button
                        className="primary-button"
                        disabled={
                          isSaving
                        }
                        type="submit"
                      >
                        Completar intervención
                      </button>
                    </div>
                  </form>
                ) : (
                  <form
                    className="repair-form"
                    onSubmit={
                      submitIntervention
                    }
                  >
                    <label className="repair-form__wide">
                      Trabajo a realizar
                      <textarea
                        onChange={(
                          event,
                        ) =>
                          setInterventionDescription(
                            event.target
                              .value,
                          )
                        }
                        rows={4}
                        value={
                          interventionDescription
                        }
                      />
                    </label>

                    <div className="repair-form__actions">
                      <button
                        className="primary-button"
                        disabled={
                          isSaving
                        }
                        type="submit"
                      >
                        <Wrench
                          size={16}
                        />
                        Iniciar intervención
                      </button>
                    </div>
                  </form>
                )}
              </section>
            ) : null}


            {[
              'in_repair',
              'testing',
            ].includes(
              selectedExecution.status,
            ) &&
            !activeIntervention ? (
              <section className="quotation-section">
                <div className="quotation-section__title">
                  <div>
                    <p>
                      Pruebas
                    </p>

                    <h3>
                      Validación posterior a intervención
                    </h3>
                  </div>
                </div>

                <form
                  className="repair-form"
                  onSubmit={
                    submitTest
                  }
                >
                  <label>
                    Tipo de prueba
                    <input
                      onChange={(
                        event,
                      ) =>
                        setTestForm(
                          (current) => ({
                            ...current,
                            testType:
                              event
                                .target
                                .value,
                          }),
                        )
                      }
                      placeholder="Ej. Prueba funcional"
                      type="text"
                      value={
                        testForm.testType
                      }
                    />
                  </label>

                  <label>
                    Resultado
                    <select
                      onChange={(
                        event,
                      ) =>
                        setTestForm(
                          (current) => ({
                            ...current,
                            result:
                              event
                                .target
                                .value,
                          }),
                        )
                      }
                      value={
                        testForm.result
                      }
                    >
                      <option value="pass">
                        Aprobada
                      </option>

                      <option value="fail">
                        Fallida
                      </option>

                      <option value="inconclusive">
                        No concluyente
                      </option>
                    </select>
                  </label>

                  <label>
                    Intervención asociada
                    <select
                      onChange={(
                        event,
                      ) =>
                        setTestForm(
                          (current) => ({
                            ...current,
                            interventionId:
                              event
                                .target
                                .value,
                          }),
                        )
                      }
                      value={
                        testForm.interventionId
                      }
                    >
                      <option value="">
                        Sin asociación explícita
                      </option>

                      {safeArray(
                        selectedExecution.interventions,
                      )
                        .filter(
                          (
                            intervention,
                          ) =>
                            intervention.completed_at,
                        )
                        .map(
                          (
                            intervention,
                          ) => (
                            <option
                              key={
                                intervention.id
                              }
                              value={
                                intervention.id
                              }
                            >
                              Intervención #
                              {intervention.sequence}
                            </option>
                          ),
                        )}
                    </select>
                  </label>

                  <label className="repair-form__wide">
                    Notas
                    <textarea
                      onChange={(
                        event,
                      ) =>
                        setTestForm(
                          (current) => ({
                            ...current,
                            notes:
                              event
                                .target
                                .value,
                          }),
                        )
                      }
                      rows={3}
                      value={
                        testForm.notes
                      }
                    />
                  </label>

                  <div className="repair-form__actions">
                    <button
                      className="primary-button"
                      disabled={
                        isSaving
                      }
                      type="submit"
                    >
                      Registrar prueba
                    </button>

                    {selectedExecution.status ===
                    'testing' ? (
                      <button
                        className="table-button"
                        disabled={
                          isSaving
                        }
                        onClick={
                          handleTechnicalComplete
                        }
                        type="button"
                      >
                        <CheckCircle2
                          size={16}
                        />
                        Cierre técnico
                      </button>
                    ) : null}
                  </div>
                </form>
              </section>
            ) : null}


            {![
              'pending_arrival',
              'closed',
              'cancelled',
            ].includes(
              selectedExecution.status,
            ) ? (
              <section className="quotation-section">
                <div className="quotation-section__title">
                  <div>
                    <p>
                      Bloqueantes
                    </p>

                    <h3>
                      Pausas operativas
                    </h3>
                  </div>
                </div>

                {openPauses.length ? (
                  <div className="repair-pause-list">
                    {openPauses.map(
                      (pause) => (
                        <article
                          className="repair-pause-card"
                          key={
                            pause.id
                          }
                        >
                          <div>
                            <span>
                              {
                                PAUSE_TYPE_LABELS[
                                  pause.pause_type
                                ] ||
                                pause.pause_type
                              }
                            </span>

                            <strong>
                              {pause.reason}
                            </strong>

                            <small>
                              Responsable:{' '}
                              {getUserDisplayName(
                                users,
                                pause.responsible_user_id,
                              )}
                            </small>
                          </div>

                          <label>
                            Resolución
                            <textarea
                              onChange={(
                                event,
                              ) =>
                                setPauseResolutionById(
                                  (
                                    current,
                                  ) => ({
                                    ...current,
                                    [pause.id]:
                                      event
                                        .target
                                        .value,
                                  }),
                                )
                              }
                              rows={2}
                              value={
                                pauseResolutionById[
                                  pause.id
                                ] || ''
                              }
                            />
                          </label>

                          <button
                            className="table-button"
                            disabled={
                              isSaving
                            }
                            onClick={() =>
                              submitPauseResolution(
                                pause,
                              )
                            }
                            type="button"
                          >
                            Resolver pausa
                          </button>
                        </article>
                      ),
                    )}
                  </div>
                ) : null}

                <form
                  className="repair-form"
                  onSubmit={
                    submitPause
                  }
                >
                  <label>
                    Tipo
                    <select
                      onChange={(
                        event,
                      ) =>
                        setPauseForm(
                          (current) => ({
                            ...current,
                            pauseType:
                              event
                                .target
                                .value,
                          }),
                        )
                      }
                      value={
                        pauseForm.pauseType
                      }
                    >
                      {Object.entries(
                        PAUSE_TYPE_LABELS,
                      ).map(
                        ([
                          value,
                          label,
                        ]) => (
                          <option
                            key={
                              value
                            }
                            value={
                              value
                            }
                          >
                            {label}
                          </option>
                        ),
                      )}
                    </select>
                  </label>

                  <label>
                    Responsable
                    <select
                      onChange={(
                        event,
                      ) =>
                        setPauseForm(
                          (current) => ({
                            ...current,
                            responsibleUserId:
                              event
                                .target
                                .value,
                          }),
                        )
                      }
                      value={
                        pauseForm.responsibleUserId
                      }
                    >
                      <option value="">
                        Selecciona
                      </option>

                      {users
                        .filter(
                          (candidate) =>
                            candidate.is_active !==
                            false,
                        )
                        .map(
                          (
                            candidate,
                          ) => (
                            <option
                              key={
                                candidate.id
                              }
                              value={
                                candidate.id
                              }
                            >
                              {candidate.full_name ||
                                candidate.email}
                            </option>
                          ),
                        )}
                    </select>
                  </label>

                  <label>
                    Reanudación tentativa
                    <input
                      onChange={(
                        event,
                      ) =>
                        setPauseForm(
                          (current) => ({
                            ...current,
                            tentativeResumeAt:
                              event
                                .target
                                .value,
                          }),
                        )
                      }
                      type="datetime-local"
                      value={
                        pauseForm.tentativeResumeAt
                      }
                    />
                  </label>

                  <label className="repair-form__wide">
                    Motivo
                    <textarea
                      onChange={(
                        event,
                      ) =>
                        setPauseForm(
                          (current) => ({
                            ...current,
                            reason:
                              event
                                .target
                                .value,
                          }),
                        )
                      }
                      rows={3}
                      value={
                        pauseForm.reason
                      }
                    />
                  </label>

                  <div className="repair-form__actions">
                    <button
                      className="table-button"
                      disabled={
                        isSaving
                      }
                      type="submit"
                    >
                      Registrar pausa
                    </button>
                  </div>
                </form>
              </section>
            ) : null}


            {safeArray(
              selectedExecution.interventions,
            ).length ? (
              <section className="quotation-section">
                <div className="quotation-section__title">
                  <div>
                    <p>
                      Historial técnico
                    </p>

                    <h3>
                      Intervenciones
                    </h3>
                  </div>
                </div>

                <div className="repair-history-list">
                  {safeArray(
                    selectedExecution.interventions,
                  )
                    .slice()
                    .sort(
                      (
                        left,
                        right,
                      ) =>
                        Number(
                          right.sequence ||
                            0,
                        ) -
                        Number(
                          left.sequence ||
                            0,
                        ),
                    )
                    .map(
                      (
                        intervention,
                      ) => (
                        <article
                          key={
                            intervention.id
                          }
                        >
                          <div>
                            <span>
                              Intervención #
                              {intervention.sequence}
                            </span>

                            <strong>
                              {intervention.description}
                            </strong>
                          </div>

                          <small>
                            Inicio:{' '}
                            {formatDateTime(
                              intervention.started_at,
                            )}
                          </small>

                          <small>
                            Fin:{' '}
                            {formatDateTime(
                              intervention.completed_at,
                            )}
                          </small>

                          <mark>
                            {intervention.outcome ||
                              (intervention.completed_at
                                ? 'Completada'
                                : 'Abierta')}
                          </mark>
                        </article>
                      ),
                    )}
                </div>
              </section>
            ) : null}


            {safeArray(
              selectedExecution.tests,
            ).length ? (
              <section className="quotation-section">
                <div className="quotation-section__title">
                  <div>
                    <p>
                      Historial técnico
                    </p>

                    <h3>
                      Pruebas
                    </h3>
                  </div>
                </div>

                <div className="repair-history-list">
                  {safeArray(
                    selectedExecution.tests,
                  )
                    .slice()
                    .sort(
                      (
                        left,
                        right,
                      ) =>
                        Number(
                          right.sequence ||
                            0,
                        ) -
                        Number(
                          left.sequence ||
                            0,
                        ),
                    )
                    .map(
                      (test) => (
                        <article
                          key={
                            test.id
                          }
                        >
                          <div>
                            <span>
                              Prueba #
                              {test.sequence}
                            </span>

                            <strong>
                              {test.test_type}
                            </strong>
                          </div>

                          <small>
                            {formatDateTime(
                              test.performed_at,
                            )}
                          </small>

                          <mark
                            className={`is-${test.result}`}
                          >
                            {TEST_RESULT_LABELS[
                              test.result
                            ] ||
                              test.result}
                          </mark>

                          {test.notes ? (
                            <p>
                              {test.notes}
                            </p>
                          ) : null}
                        </article>
                      ),
                    )}
                </div>
              </section>
            ) : null}


            {[
              'technically_completed',
              'pending_release',
              'closed',
              'equipment_not_suitable',
            ].includes(
              selectedExecution.status,
            ) ? (
              <section className="quotation-section">
                <div className="quotation-section__title">
                  <div>
                    <p>
                      Documento técnico
                    </p>

                    <h3>
                      Reporte de reparación
                    </h3>
                  </div>
                </div>

                <div className="repair-report-summary">
                  <article>
                    <span>
                      Estado de reporte
                    </span>

                    <strong>
                      {safeText(
                        selectedExecution.report_status,
                      )}
                    </strong>
                  </article>

                  <article>
                    <span>
                      Versión
                    </span>

                    <strong>
                      {safeText(
                        selectedExecution.report_version,
                      )}
                    </strong>
                  </article>

                  <article>
                    <span>
                      Firma
                    </span>

                    <strong>
                      {selectedExecution.signed_at
                        ? `Firmado por ${safeText(
                            selectedExecution.signer_name,
                          )}`
                        : 'Pendiente'}
                    </strong>
                  </article>

                  <article>
                    <span>
                      Cierre
                    </span>

                    <strong>
                      {formatDateTime(
                        selectedExecution.closed_at,
                      )}
                    </strong>
                  </article>
                </div>

                <div className="repair-form__actions">
                  <button
                    className="table-button"
                    disabled={
                      isSaving
                    }
                    onClick={
                      handleDownloadReport
                    }
                    type="button"
                  >
                    Descargar reporte PDF
                  </button>
                </div>

                {safeArray(
                  selectedExecution.closure_blockers,
                ).length ? (
                  <div className="repair-blockers">
                    <div className="repair-blockers__heading">
                      <AlertTriangle
                        size={18}
                      />

                      <strong>
                        Pendientes para cierre
                      </strong>
                    </div>

                    {safeArray(
                      selectedExecution.closure_blockers,
                    ).map(
                      (
                        blocker,
                        index,
                      ) => (
                        <article
                          key={`closure-${index}`}
                        >
                          {safeText(
                            blocker.message ||
                              blocker.reason ||
                              blocker.code,
                            'Pendiente de cierre',
                          )}
                        </article>
                      ),
                    )}
                  </div>
                ) : null}
              </section>
            ) : null}
          </main>
        ) : null}
      </div>
    </section>
  );
}


export default RepairEtsTab;