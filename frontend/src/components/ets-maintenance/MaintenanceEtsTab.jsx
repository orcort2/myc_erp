import React, {
  useEffect,
  useMemo,
  useRef,
  useState,
} from 'react';

import {
  acceptMaintenanceFieldVisit,
  addMaintenanceMaterial,
  addMaintenancePause,
  closeMaintenance,
  completeMaintenanceTechnical,
  downloadMaintenanceReport,
  getMaintenanceBoard,
  prepareMaintenance,
  registerMaintenanceArrival,
  registerMaintenanceFieldEquipment,
  requestMaintenanceChange,
  resolveMaintenanceChange,
  resolveMaintenanceInvestigation,
  resolveMaintenancePause,
  saveMaintenanceCapture,
  signMaintenanceReport,
  startMaintenance,
} from '../../services/api.js';

import './maintenance-ets.css';


const statusLabels = {
  pending_arrival: 'Pendiente de arribo',
  pending_assignment: 'Pendiente de asignación',
  assigned: 'Asignado',
  in_maintenance: 'En mantenimiento',
  technically_completed: 'Técnicamente terminado',
  pending_release: 'Pendiente de liberación',
  closed: 'Cerrado',
};


const pauseLabels = {
  spare_part: 'Pendiente de refacción',
  authorization: 'Pendiente de autorización',
  second_intervention: 'Segunda intervención / visita',
  commercial_review: 'Revisión comercial',
  administrative_investigation: 'Investigación administrativa',
};


const pauseStatusLabels = {
  active: 'Activa',
  resolved: 'Resuelta',
};


const maintenanceTypeLabels = {
  preventive: 'Preventivo',
  corrective: 'Correctivo',
};


const locationLabels = {
  laboratory: 'Laboratorio',
  field: 'Campo',
};


const workflowSteps = [
  {
    id: 'before',
    label: 'Antes',
    title: '¿Cómo llegó?',
  },
  {
    id: 'intervention',
    label: 'Intervención',
    title: '¿Qué se hizo?',
  },
  {
    id: 'after',
    label: 'Después',
    title: '¿Cómo quedó?',
  },
  {
    id: 'future',
    label: 'Futuro',
    title: '¿Qué necesita?',
  },
  {
    id: 'materials',
    label: 'Materiales',
    title: 'Materiales e incidencias',
  },
  {
    id: 'review',
    label: 'Revisión',
    title: 'Revisión y cierre',
  },
];


const emptyCapture = {
  initial_condition: 'undetermined',
  initial_description: '',
  final_condition: 'operational',
  functional_result: '',
  technical_conclusion: '',
};


function createFinding(data = {}) {
  return {
    id:
      globalThis.crypto?.randomUUID?.()
      || `finding-${Date.now()}-${Math.random()}`,

    component:
      data.component || '',

    description:
      data.description || '',

    severity:
      data.severity || 'medium',

    classification:
      data.classification || 'maintenance',

    resolution:
      data.resolution || 'corrected',
  };
}


function createAction(data = {}) {
  return {
    id:
      globalThis.crypto?.randomUUID?.()
      || `action-${Date.now()}-${Math.random()}`,

    action:
      data.action || 'cleaning',

    component:
      data.component || '',

    result:
      data.result || '',
  };
}


function createRecommendation(data = {}) {
  return {
    id:
      globalThis.crypto?.randomUUID?.()
      || `recommendation-${Date.now()}-${Math.random()}`,

    description:
      data.description || '',

    decision:
      data.decision || 'pending',
  };
}


function hasPermission(user, permission) {
  return (user?.permissions || []).some(
    (value) => (
      value === '*'
      || value === permission
      || value === 'service_orders.*'
    ),
  );
}


function formatDateTime(value) {
  if (!value) {
    return 'Sin fecha';
  }

  try {
    return new Date(value).toLocaleString();
  } catch {
    return String(value);
  }
}


function maintenanceProgress(executions = []) {
  const total = executions.length;

  const closed = executions.filter(
    (item) => item.status === 'closed',
  ).length;

  const inProgress = executions.filter(
    (item) => [
      'assigned',
      'in_maintenance',
      'technically_completed',
      'pending_release',
    ].includes(item.status),
  ).length;

  const pending = total - closed - inProgress;

  return {
    total,
    closed,
    inProgress,
    pending,
  };
}


function maintenanceStatusTone(status) {
  if (status === 'closed') {
    return 'is-completed';
  }

  if (
    status === 'in_maintenance'
    || status === 'technically_completed'
    || status === 'pending_release'
  ) {
    return 'is-progress';
  }

  if (status === 'assigned') {
    return 'is-ready';
  }

  return 'is-pending';
}


function unitDisplayName(execution, index) {
  if (
    execution.equipment_id
    && execution.equipment_name
  ) {
    return execution.equipment_name;
  }

  return `Equipo ${index + 1}`;
}


function unitSecondaryLabel(execution) {
  const ot = execution.work_order_number
    ? `OT ${execution.work_order_number}`
    : 'OT pendiente';

  if (execution.equipment_id) {
    return `${ot} · Equipo vinculado`;
  }

  return `${ot} · Pendiente de identificación`;
}


export default function MaintenanceEtsTab({
  order,
  user = null,
  users = [],
}) {
  const [board, setBoard] = useState(null);
  const [selectedId, setSelectedId] = useState(null);

  const [
    maintenanceView,
    setMaintenanceView,
  ] = useState('items');

  const [
    selectedItemId,
    setSelectedItemId,
  ] = useState(null);

  const [
    workflowStep,
    setWorkflowStep,
  ] = useState('before');

  const [
    workflowDirection,
    setWorkflowDirection,
  ] = useState('forward');

  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState('');
  const [error, setError] = useState('');

  const [
    highlightedField,
    setHighlightedField,
  ] = useState('');

  const [equipment, setEquipment] = useState({
    name: '',
    brand: '',
    model: '',
    serial_number: '',
    internal_id: '',
    range_or_capacity: '',
  });

  const [assignment, setAssignment] = useState({
    technician_id: '',
    location_mode: '',
    address: '',
    scheduled_for: '',
  });

  const [
    capture,
    setCapture,
  ] = useState(emptyCapture);

  const [
    findings,
    setFindings,
  ] = useState([
    createFinding(),
  ]);

  const [
    actions,
    setActions,
  ] = useState([
    createAction(),
  ]);

  const [
    recommendations,
    setRecommendations,
  ] = useState([
    createRecommendation(),
  ]);

  /*
   * Evidencias existentes:
   * referencias institucionales ya persistidas.
   */
  const [
    persistedBeforeEvidence,
    setPersistedBeforeEvidence,
  ] = useState([]);

  const [
    persistedAfterEvidence,
    setPersistedAfterEvidence,
  ] = useState([]);

  /*
   * Evidencias nuevas:
   * archivos seleccionados localmente.
   *
   * TODAVÍA no son persistentes.
   * El siguiente paso será conectar el uploader
   * institucional de Mantenimiento.
   */
  const [
    beforeEvidence,
    setBeforeEvidence,
  ] = useState([]);

  const [
    afterEvidence,
    setAfterEvidence,
  ] = useState([]);

  const [pause, setPause] = useState({
    pause_type: 'spare_part',
    reason: '',
    responsible_user_id: '',
    tentative_resume_at: '',
  });

  const [material, setMaterial] = useState({
    material_type: 'used',
    name: '',
    quantity: '1',
    unit: 'pieza',
    component: '',
    notes: '',
    decision: 'pending',
  });

  const [change, setChange] = useState({
    change_type: 'corrective',
    summary: '',
  });

  const [signature, setSignature] = useState({
    signer_name: '',
    signature_data_url: '',
    client_decision: 'acknowledged',
  });

  const sectionRefs = useRef({});


  const selected = useMemo(
    () => (
      board?.executions.find(
        (item) => item.id === selectedId,
      )
      || board?.executions[0]
      || null
    ),
    [board, selectedId],
  );


  const maintenanceItems = useMemo(() => {
    if (!board?.executions?.length) {
      return [];
    }

    const grouped = new Map();

    board.executions.forEach((execution) => {
      const itemId =
        execution.service_order_item_id;

      if (!grouped.has(itemId)) {
        grouped.set(itemId, {
          id: itemId,
          executions: [],
        });
      }

      grouped
        .get(itemId)
        .executions
        .push(execution);
    });

    return Array
      .from(grouped.values())
      .map(
        (group, index) => {
          const orderItem =
            (order?.items || []).find(
              (item) => (
                Number(
                  item.id
                  ?? item.service_order_item_id,
                )
                === Number(group.id)
              ),
            );

          const firstExecution =
            group.executions[0];

          return {
            ...group,

            index,

            name:
              orderItem?.service_name
              || orderItem?.name
              || `Partida ${index + 1}`,

            maintenanceType:
              firstExecution?.maintenance_type
              || 'preventive',

            progress:
              maintenanceProgress(
                group.executions,
              ),
          };
        },
      );
  }, [board, order]);


  const selectedMaintenanceItem =
    useMemo(
      () => (
        maintenanceItems.find(
          (item) =>
            item.id === selectedItemId,
        )
        || null
      ),
      [
        maintenanceItems,
        selectedItemId,
      ],
    );


  const technicians = useMemo(
    () => users.filter(
      (item) =>
        item.is_active !== false,
    ),
    [users],
  );


  const canManage = hasPermission(
    user,
    'service_orders.maintenance.manage',
  );

  const canExecute = hasPermission(
    user,
    'service_orders.maintenance.execute',
  );

  const canAuthorize = hasPermission(
    user,
    'service_orders.maintenance.authorize',
  );

  const canSign = hasPermission(
    user,
    'service_orders.maintenance.sign',
  );

  const canClose = hasPermission(
    user,
    'service_orders.maintenance.close',
  );


  const activePauses =
    selected?.active_pauses || [];

  const hasActivePause =
    selected?.has_active_pause === true;

  const operationalBlockers =
    selected?.blockers || [];

  const closureBlockers =
    selected?.closure_blockers || [];

  const maintenanceTypeEvolved =
    selected?.maintenance_type_evolved
    === true;

  const originalMaintenanceType =
    selected?.original_maintenance_type
    || selected?.maintenance_type;

  const canSaveCapture =
    canExecute
    && selected?.status
    === 'in_maintenance';

  const canCompleteTechnical =
    canExecute
    && selected?.status
    === 'in_maintenance';

  const canAdministrativelyClose =
    canClose
    && selected?.status
    === 'pending_release'
    && closureBlockers.length === 0;


  async function load() {
    try {
      setError('');

      const value =
        await getMaintenanceBoard(
          order.id,
        );

      setBoard(value);

      setSelectedId((current) => {
        if (
          current
          && value.executions.some(
            (item) =>
              item.id === current,
          )
        ) {
          return current;
        }

        return (
          value.executions[0]?.id
          || null
        );
      });
    } catch (requestError) {
      setError(requestError.message);
    }
  }


  useEffect(() => {
    setBoard(null);
    setSelectedId(null);
    setSelectedItemId(null);
    setMaintenanceView('items');
    setWorkflowStep('before');

    load();
  }, [order.id]);


  useEffect(() => {
    setHighlightedField('');

    if (!selected) {
      return;
    }

    setAssignment({
      technician_id:
        selected.technician_id
          ? String(
            selected.technician_id,
          )
          : '',

      location_mode:
        selected.location_mode
        || '',

      address:
        selected.field_address
          ?.formatted
        || '',

      scheduled_for:
        selected.scheduled_for
          ? new Date(
            selected.scheduled_for,
          )
            .toISOString()
            .slice(0, 16)
          : '',
    });

    setCapture({
      initial_condition:
        selected.initial_condition
        || 'undetermined',

      initial_description:
        selected.initial_description
        || '',

      final_condition:
        selected.final_condition
        || 'operational',

      functional_result:
        selected.functional_result
        || '',

      technical_conclusion:
        selected.technical_conclusion
        || '',
    });

    setFindings(
      selected.findings?.length
        ? selected.findings.map(
          (item) =>
            createFinding(item),
        )
        : [createFinding()],
    );

    setActions(
      selected.actions?.length
        ? selected.actions.map(
          (item) =>
            createAction(item),
        )
        : [createAction()],
    );

    setRecommendations(
      selected.recommendations?.length
        ? selected.recommendations.map(
          (item) =>
            createRecommendation(item),
        )
        : [createRecommendation()],
    );

    setPersistedBeforeEvidence(
      selected.before_photos || [],
    );

    setPersistedAfterEvidence(
      selected.after_photos || [],
    );

    /*
     * Limpiamos File objects locales
     * cuando se cambia de ejecución.
     */
    setBeforeEvidence((current) => {
      current.forEach((item) => {
        if (item.preview) {
          URL.revokeObjectURL(
            item.preview,
          );
        }
      });

      return [];
    });

    setAfterEvidence((current) => {
      current.forEach((item) => {
        if (item.preview) {
          URL.revokeObjectURL(
            item.preview,
          );
        }
      });

      return [];
    });
  }, [selectedId, selected]);


  async function mutate(
    action,
    success,
  ) {
    setBusy(true);
    setError('');
    setMessage('');

    try {
      const value = await action();

      setBoard(value);
      setMessage(success);

      return true;
    } catch (requestError) {
      setError(requestError.message);

      return false;
    } finally {
      setBusy(false);
    }
  }


  function goToBlocker(blocker) {
    const target =
      sectionRefs.current[
        blocker.section
      ];

    setHighlightedField(
      blocker.field,
    );

    target?.scrollIntoView({
      behavior: 'smooth',
      block: 'start',
    });

    window.setTimeout(() => {
      const field =
        target?.querySelector(
          `[name="${blocker.field}"]`,
        );

      field?.focus();
    }, 350);

    window.setTimeout(() => {
      setHighlightedField(
        (current) => (
          current === blocker.field
            ? ''
            : current
        ),
      );
    }, 4500);
  }


  function blockerClass(field) {
    return (
      highlightedField === field
        ? 'maintenance-field-blocked'
        : ''
    );
  }


  function workflowStepIndex(step) {
    return workflowSteps.findIndex(
      (item) =>
        item.id === step,
    );
  }


  function goToWorkflowStep(
    nextStep,
  ) {
    const currentIndex =
      workflowStepIndex(
        workflowStep,
      );

    const nextIndex =
      workflowStepIndex(
        nextStep,
      );

    setWorkflowDirection(
      nextIndex >= currentIndex
        ? 'forward'
        : 'backward',
    );

    setWorkflowStep(nextStep);
  }


  function goNextStep() {
    const index =
      workflowStepIndex(
        workflowStep,
      );

    if (
      index < 0
      || index
      >= workflowSteps.length - 1
    ) {
      return;
    }

    goToWorkflowStep(
      workflowSteps[
        index + 1
      ].id,
    );
  }


  function goPreviousStep() {
    const index =
      workflowStepIndex(
        workflowStep,
      );

    if (index <= 0) {
      return;
    }

    goToWorkflowStep(
      workflowSteps[
        index - 1
      ].id,
    );
  }


  function updateFinding(
    id,
    field,
    value,
  ) {
    setFindings(
      (current) =>
        current.map(
          (item) => (
            item.id === id
              ? {
                ...item,
                [field]: value,
              }
              : item
          ),
        ),
    );
  }


  function addFinding() {
    setFindings(
      (current) => [
        ...current,
        createFinding(),
      ],
    );
  }


  function removeFinding(id) {
    setFindings(
      (current) =>
        current.filter(
          (item) =>
            item.id !== id,
        ),
    );
  }


  function updateAction(
    id,
    field,
    value,
  ) {
    setActions(
      (current) =>
        current.map(
          (item) => (
            item.id === id
              ? {
                ...item,
                [field]: value,
              }
              : item
          ),
        ),
    );
  }


  function addAction() {
    setActions(
      (current) => [
        ...current,
        createAction(),
      ],
    );
  }


  function removeAction(id) {
    setActions(
      (current) =>
        current.filter(
          (item) =>
            item.id !== id,
        ),
    );
  }


  function updateRecommendation(
    id,
    field,
    value,
  ) {
    setRecommendations(
      (current) =>
        current.map(
          (item) => (
            item.id === id
              ? {
                ...item,
                [field]: value,
              }
              : item
          ),
        ),
    );
  }


  function addRecommendation() {
    setRecommendations(
      (current) => [
        ...current,
        createRecommendation(),
      ],
    );
  }


  function removeRecommendation(id) {
    setRecommendations(
      (current) =>
        current.filter(
          (item) =>
            item.id !== id,
        ),
    );
  }


  function addLocalEvidence(
    event,
    setter,
  ) {
    const files =
      Array.from(
        event.target.files
        || [],
      );

    if (!files.length) {
      return;
    }

    const entries =
      files.map((file) => ({
        id:
          globalThis.crypto
            ?.randomUUID?.()
          || (
            `evidence-${Date.now()}`
            + `-${Math.random()}`
          ),

        file,
        name: file.name,
        type: file.type,

        preview:
          file.type
            .startsWith('image/')
            ? URL.createObjectURL(
              file,
            )
            : null,
      }));

    setter(
      (current) => [
        ...current,
        ...entries,
      ],
    );

    event.target.value = '';
  }


  function removeLocalEvidence(
    id,
    setter,
  ) {
    setter((current) => {
      const target =
        current.find(
          (item) =>
            item.id === id,
        );

      if (target?.preview) {
        URL.revokeObjectURL(
          target.preview,
        );
      }

      return current.filter(
        (item) =>
          item.id !== id,
      );
    });
  }


  function capturePayload() {
    return {
      initial_condition:
        capture.initial_condition,

      initial_description:
        capture.initial_description,

      findings:
        findings
          .filter(
            (item) =>
              item.description
                .trim(),
          )
          .map(
            (item) => ({
              component:
                item.component
                  .trim()
                || 'General',

              description:
                item.description
                  .trim(),

              severity:
                item.severity,

              classification:
                item.classification,

              resolution:
                item.resolution,
            }),
          ),

      actions:
        actions
          .filter(
            (item) =>
              item.result
                .trim(),
          )
          .map(
            (item) => ({
              action:
                item.action,

              component:
                item.component
                  .trim()
                || 'General',

              result:
                item.result
                  .trim(),
            }),
          ),

      final_condition:
        capture.final_condition,

      functional_result:
        capture.functional_result,

      technical_conclusion:
        capture.technical_conclusion,

      recommendations:
        recommendations
          .filter(
            (item) =>
              item.description
                .trim(),
          )
          .map(
            (item) => ({
              description:
                item.description
                  .trim(),

              decision:
                item.decision,
            }),
          ),

      /*
       * Sólo referencias ya almacenadas.
       * Los File objects nuevos NO deben
       * enviarse como blob/data URL.
       */
      before_photos:
        persistedBeforeEvidence,

      after_photos:
        persistedAfterEvidence,
    };
  }


  async function saveWorkflowProgress(
    continueAfter = false,
  ) {
    if (!selected) {
      return;
    }

    if (
      beforeEvidence.length
      || afterEvidence.length
    ) {
      setError(
        'Hay evidencia multimedia nueva pendiente de subir. '
        + 'Todavía falta conectar el almacenamiento institucional '
        + 'antes de poder persistir esos archivos.',
      );

      return;
    }

    const success =
      await mutate(
        () =>
          saveMaintenanceCapture(
            order.id,
            selected.id,
            capturePayload(),
          ),
        'Avance técnico guardado.',
      );

    if (
      success
      && continueAfter
    ) {
      goNextStep();
    }
  }


  async function report() {
    if (!selected) {
      return;
    }

    setBusy(true);
    setError('');
    setMessage('');

    try {
      const {
        blob,
        filename,
      } =
        await downloadMaintenanceReport(
          order.id,
          selected.id,
        );

      const url =
        URL.createObjectURL(blob);

      const link =
        document.createElement('a');

      link.href = url;

      link.download =
        filename
        || `mantenimiento-${selected.id}.pdf`;

      document.body
        .appendChild(link);

      link.click();
      link.remove();

      URL.revokeObjectURL(url);

      setMessage(
        'Reporte generado desde la captura estructurada.',
      );

      await load();
    } catch (requestError) {
      setError(requestError.message);
    } finally {
      setBusy(false);
    }
  }


  if (!board) {
    return (
      <section
        className="
          maintenance-shell
          maintenance-shell--loading
        "
      >
        <header
          className="
            maintenance-landing-heading
          "
        >
          <div>
            <span>
              Vertical operativo
            </span>

            <h3>
              Mantenimiento
            </h3>

            <p>
              Gestión individual de
              los equipos incluidos
              en el ETS.
            </p>
          </div>
        </header>

        <div
          className="
            maintenance-skeleton-grid
          "
        >
          {[1, 2, 3].map(
            (item) => (
              <article
                className="
                  maintenance-skeleton-card
                "
                key={item}
              >
                <span />
                <strong />
                <small />
                <div />
              </article>
            ),
          )}
        </div>

        {error ? (
          <div
            className="
              maintenance-alert
              is-error
            "
          >
            {error}
          </div>
        ) : null}
      </section>
    );
  }


  if (
    maintenanceView
    === 'items'
  ) {
    return (
      <section
        className="
          maintenance-shell
        "
      >
        <header
          className="
            maintenance-landing-heading
          "
        >
          <div>
            <span>
              Vertical operativo
            </span>

            <h3>
              Mantenimiento
            </h3>

            <p>
              Selecciona una partida
              para gestionar
              individualmente
              sus equipos.
            </p>
          </div>

          <div
            className="
              maintenance-landing-summary
            "
          >
            <strong>
              {
                board.executions
                  .length
              }
            </strong>

            <span>
              equipos en mantenimiento
            </span>
          </div>
        </header>

        {error ? (
          <div
            className="
              maintenance-alert
              is-error
            "
          >
            {error}
          </div>
        ) : null}

        {message ? (
          <div
            className="
              maintenance-alert
              is-success
            "
          >
            {message}
          </div>
        ) : null}

        <div
          className="
            maintenance-item-grid
          "
        >
          {maintenanceItems.map(
            (item) => {
              const {
                total,
                closed,
                inProgress,
                pending,
              } =
                item.progress;

              return (
                <button
                  className="
                    maintenance-item-card
                  "
                  key={item.id}
                  onClick={() => {
                    setSelectedItemId(
                      item.id,
                    );

                    setMaintenanceView(
                      'units',
                    );
                  }}
                  type="button"
                >
                  <div
                    className="
                      maintenance-item-card__top
                    "
                  >
                    <span>
                      Partida
                      {' '}
                      {
                        item.index
                        + 1
                      }
                    </span>

                    <span
                      className="
                        maintenance-item-card__type
                      "
                    >
                      {
                        maintenanceTypeLabels[
                          item.maintenanceType
                        ]
                        || item.maintenanceType
                      }
                    </span>
                  </div>

                  <div
                    className="
                      maintenance-item-card__body
                    "
                  >
                    <h4>
                      {item.name}
                    </h4>

                    <strong>
                      {total}
                      {' '}
                      {
                        total === 1
                          ? 'equipo'
                          : 'equipos'
                      }
                    </strong>
                  </div>

                  <div
                    className="
                      maintenance-item-card__progress
                    "
                  >
                    <div>
                      <span>
                        Terminados
                      </span>

                      <strong>
                        {closed}
                      </strong>
                    </div>

                    <div>
                      <span>
                        En proceso
                      </span>

                      <strong>
                        {inProgress}
                      </strong>
                    </div>

                    <div>
                      <span>
                        Pendientes
                      </span>

                      <strong>
                        {pending}
                      </strong>
                    </div>
                  </div>

                  <div
                    className="
                      maintenance-item-card__footer
                    "
                  >
                    <span>
                      Ver equipos
                    </span>

                    <strong>
                      →
                    </strong>
                  </div>
                </button>
              );
            },
          )}
        </div>
      </section>
    );
  }


  if (
    maintenanceView
      === 'units'
    && selectedMaintenanceItem
  ) {
    return (
      <section
        className="
          maintenance-shell
        "
      >
        <header
          className="
            maintenance-subview-heading
          "
        >
          <button
            className="
              maintenance-back-button
            "
            onClick={() => {
              setSelectedItemId(
                null,
              );

              setMaintenanceView(
                'items',
              );
            }}
            type="button"
          >
            ← Mantenimiento
          </button>

          <div>
            <span>
              Partida
              {' '}
              {
                selectedMaintenanceItem
                  .index
                + 1
              }
            </span>

            <h3>
              {
                selectedMaintenanceItem
                  .name
              }
            </h3>

            <p>
              {
                selectedMaintenanceItem
                  .executions
                  .length
              }
              {' '}
              {
                selectedMaintenanceItem
                  .executions
                  .length === 1
                  ? 'equipo'
                  : 'equipos'
              }
              {' · '}
              {
                maintenanceTypeLabels[
                  selectedMaintenanceItem
                    .maintenanceType
                ]
                || selectedMaintenanceItem
                  .maintenanceType
              }
            </p>
          </div>
        </header>

        <div
          className="
            maintenance-unit-grid
          "
        >
          {
            selectedMaintenanceItem
              .executions
              .map(
                (
                  execution,
                  index,
                ) => {
                  const blockerCount =
                    execution
                      .blockers
                      ?.length
                    || 0;

                  return (
                    <button
                      className={
                        `maintenance-unit-card ${
                          maintenanceStatusTone(
                            execution
                              .status,
                          )
                        }`
                      }
                      key={
                        execution.id
                      }
                      onClick={() => {
                        setSelectedId(
                          execution.id,
                        );

                        setWorkflowStep(
                          'before',
                        );

                        setMaintenanceView(
                          'execution',
                        );
                      }}
                      type="button"
                    >
                      <div
                        className="
                          maintenance-unit-card__header
                        "
                      >
                        <span>
                          Equipo
                          {' '}
                          {index + 1}
                        </span>

                        <span
                          className="
                            maintenance-unit-card__status
                          "
                        >
                          {
                            statusLabels[
                              execution
                                .status
                            ]
                            || execution
                              .status
                          }
                        </span>
                      </div>

                      <div
                        className="
                          maintenance-unit-card__identity
                        "
                      >
                        <strong>
                          {
                            unitDisplayName(
                              execution,
                              index,
                            )
                          }
                        </strong>

                        <span>
                          {
                            unitSecondaryLabel(
                              execution,
                            )
                          }
                        </span>
                      </div>

                      <div
                        className="
                          maintenance-unit-card__meta
                        "
                      >
                        <span>
                          {
                            execution
                              .location_mode
                              ? (
                                locationLabels[
                                  execution
                                    .location_mode
                                ]
                                || execution
                                  .location_mode
                              )
                              : (
                                'Modalidad pendiente'
                              )
                          }
                        </span>

                        <span>
                          {
                            execution
                              .technician_id
                              ? (
                                'Técnico asignado'
                              )
                              : (
                                'Sin técnico'
                              )
                          }
                        </span>
                      </div>

                      <div
                        className="
                          maintenance-unit-card__footer
                        "
                      >
                        <span
                          className={
                            blockerCount
                              ? 'has-blockers'
                              : 'is-clear'
                          }
                        >
                          {
                            blockerCount
                              ? (
                                `${blockerCount} pendiente(s)`
                              )
                              : (
                                'Sin bloqueantes'
                              )
                          }
                        </span>

                        <strong>
                          Abrir expediente →
                        </strong>
                      </div>
                    </button>
                  );
                },
              )
          }
        </div>
      </section>
    );
  }


  if (!selected) {
    return (
      <section
        className="
          maintenance-shell
        "
      >
        <div
          className="
            maintenance-alert
            is-error
          "
        >
          No fue posible seleccionar
          la ejecución de
          Mantenimiento.
        </div>

        <button
          className="
            maintenance-back-button
          "
          onClick={() => {
            setMaintenanceView(
              'items',
            );

            setSelectedItemId(
              null,
            );
          }}
          type="button"
        >
          ← Volver a Mantenimiento
        </button>
      </section>
    );
  }


  const executionCanStartWorkflow =
    [
      'in_maintenance',
      'technically_completed',
      'pending_release',
      'closed',
    ].includes(
      selected.status,
    );


  return (
    <section
      className="
        maintenance-shell
      "
    >
      <header
        className="
          maintenance-execution-heading
        "
      >
        <div
          className="
            maintenance-execution-heading__navigation
          "
        >
          <button
            className="
              maintenance-back-button
            "
            onClick={() => {
              setMaintenanceView(
                'units',
              );
            }}
            type="button"
          >
            ← Equipos
          </button>

          <span>
            {
              selectedMaintenanceItem
                ?.name
              || 'Mantenimiento'
            }
          </span>
        </div>

        <div
          className="
            maintenance-execution-heading__identity
          "
        >
          <div>
            <span>
              Expediente individual
            </span>

            <h3>
              {
                selected.equipment_id
                  ? (
                    selected
                      .equipment_name
                  )
                  : (
                    'Equipo pendiente de identificar'
                  )
              }
            </h3>

            <p>
              OT
              {' '}
              {
                selected
                  .work_order_number
              }
              {' · '}
              {
                maintenanceTypeLabels[
                  selected
                    .maintenance_type
                ]
                || selected
                  .maintenance_type
              }
            </p>
          </div>

          <div
            className="
              maintenance-execution-heading__state
            "
          >
            <strong>
              {
                statusLabels[
                  selected.status
                ]
                || selected.status
              }
            </strong>

            <span>
              {
                selected
                  .location_mode
                  ? (
                    locationLabels[
                      selected
                        .location_mode
                    ]
                    || selected
                      .location_mode
                  )
                  : (
                    'Modalidad pendiente'
                  )
              }
            </span>
          </div>
        </div>
      </header>


      {error ? (
        <div
          className="
            maintenance-alert
            is-error
          "
        >
          {error}
        </div>
      ) : null}


      {message ? (
        <div
          className="
            maintenance-alert
            is-success
          "
        >
          {message}
        </div>
      ) : null}


      {operationalBlockers.length > 0 ? (
        <aside
          className="
            maintenance-blockers
          "
          aria-live="polite"
        >
          <strong>
            {
              operationalBlockers
                .length
            }
            {' '}
            bloqueante(s)
            requieren atención
          </strong>

          {
            operationalBlockers
              .map(
                (
                  blocker,
                  index,
                ) => (
                  <button
                    key={
                      `${blocker.section}`
                      + `-${blocker.field}`
                      + `-${index}`
                    }
                    onClick={() => {
                      /*
                       * Para captura técnica,
                       * navegamos directamente
                       * al paso del workflow.
                       */
                      if (
                        blocker.section
                        === 'before'
                      ) {
                        goToWorkflowStep(
                          'before',
                        );

                        return;
                      }

                      if (
                        blocker.section
                        === 'intervention'
                      ) {
                        goToWorkflowStep(
                          'intervention',
                        );

                        return;
                      }

                      if (
                        blocker.section
                        === 'after'
                      ) {
                        goToWorkflowStep(
                          'after',
                        );

                        return;
                      }

                      if (
                        blocker.section
                        === 'future'
                      ) {
                        goToWorkflowStep(
                          'future',
                        );

                        return;
                      }

                      if (
                        blocker.section
                        === 'materials'
                      ) {
                        goToWorkflowStep(
                          'materials',
                        );

                        return;
                      }

                      goToBlocker(
                        blocker,
                      );
                    }}
                    type="button"
                  >
                    <span>
                      Bloqueante
                    </span>

                    {
                      blocker.message
                    }

                    <small>
                      Resolver
                    </small>
                  </button>
                ),
              )
          }
        </aside>
      ) : null}


      {hasActivePause ? (
        <aside
          className="
            maintenance-pause-banner
          "
        >
          <strong>
            Servicio pausado
            operativamente
          </strong>

          <p>
            El mantenimiento conserva
            su estado principal:
            {' '}
            {
              statusLabels[
                selected.status
              ]
              || selected.status
            }.
          </p>

          {activePauses.map(
            (item) => (
              <button
                key={item.id}
                type="button"
                onClick={() =>
                  goToWorkflowStep(
                    'materials',
                  )
                }
              >
                <span>
                  {
                    pauseLabels[
                      item.pause_type
                    ]
                    || item.pause_type
                  }
                </span>

                <strong>
                  {item.reason}
                </strong>

                <small>
                  Ver incidencia
                </small>
              </button>
            ),
          )}
        </aside>
      ) : null}


      <div
        className="
          maintenance-status
        "
      >
        <strong>
          {
            statusLabels[
              selected.status
            ]
            || selected.status
          }
        </strong>

        <span>
          {
            maintenanceTypeLabels[
              selected
                .maintenance_type
            ]
            || selected
              .maintenance_type
          }
          {' · '}
          {
            selected.location_mode
            === 'field'
              ? (
                'Campo; equipo con cliente'
              )
              : (
                selected.location_mode
                === 'laboratory'
                  ? (
                    'Laboratorio; custodia MYC'
                  )
                  : (
                    'Modalidad pendiente'
                  )
              )
          }
        </span>

        {maintenanceTypeEvolved ? (
          <small
            className="
              maintenance-evolution
            "
          >
            Alcance evolucionado:
            {' '}
            {
              maintenanceTypeLabels[
                originalMaintenanceType
              ]
              || originalMaintenanceType
            }
            {' → '}
            {
              maintenanceTypeLabels[
                selected
                  .maintenance_type
              ]
              || selected
                .maintenance_type
            }
          </small>
        ) : null}
      </div>


      {
        /*
         * PREPARACIÓN PREVIA AL WORKFLOW
         *
         * Sólo permanecen visibles mientras
         * todavía no empieza la intervención.
         */
      }

      {!executionCanStartWorkflow ? (
        <>
          <section
            className="
              maintenance-panel
            "
            ref={(node) => {
              sectionRefs.current
                .equipment = node;

              sectionRefs.current
                .arrival = node;
            }}
          >
            <h4>
              Equipo del servicio
            </h4>

            <div
              className="
                maintenance-grid
              "
            >
              <label
                className={
                  blockerClass(
                    'equipment',
                  )
                }
              >
                Equipo

                <input
                  name="equipment"
                  onChange={
                    (event) =>
                      setEquipment({
                        ...equipment,
                        name:
                          event
                            .target
                            .value,
                      })
                  }
                  value={
                    equipment.name
                  }
                />
              </label>

              <label>
                Marca

                <input
                  onChange={
                    (event) =>
                      setEquipment({
                        ...equipment,
                        brand:
                          event
                            .target
                            .value,
                      })
                  }
                  value={
                    equipment.brand
                  }
                />
              </label>

              <label>
                Modelo

                <input
                  onChange={
                    (event) =>
                      setEquipment({
                        ...equipment,
                        model:
                          event
                            .target
                            .value,
                      })
                  }
                  value={
                    equipment.model
                  }
                />
              </label>

              <label>
                Serie

                <input
                  onChange={
                    (event) =>
                      setEquipment({
                        ...equipment,

                        serial_number:
                          event
                            .target
                            .value,
                      })
                  }
                  value={
                    equipment
                      .serial_number
                  }
                />
              </label>

              <label>
                Identificación interna

                <input
                  onChange={
                    (event) =>
                      setEquipment({
                        ...equipment,

                        internal_id:
                          event
                            .target
                            .value,
                      })
                  }
                  value={
                    equipment
                      .internal_id
                  }
                />
              </label>

              <label>
                Rango / capacidad

                <input
                  onChange={
                    (event) =>
                      setEquipment({
                        ...equipment,

                        range_or_capacity:
                          event
                            .target
                            .value,
                      })
                  }
                  value={
                    equipment
                      .range_or_capacity
                  }
                />
              </label>
            </div>

            <div
              className="
                maintenance-panel-actions
              "
            >
              {
                canManage
                && !selected.equipment_id
                && selected.location_mode
                  ? (
                    <button
                      className="
                        primary-button
                      "
                      disabled={
                        busy
                        || !equipment
                          .name
                          .trim()
                      }
                      onClick={() =>
                        mutate(
                          () => (
                            selected
                              .location_mode
                            === 'laboratory'
                              ? (
                                registerMaintenanceArrival(
                                  order.id,
                                  selected.id,
                                  equipment,
                                )
                              )
                              : (
                                registerMaintenanceFieldEquipment(
                                  order.id,
                                  selected.id,
                                  equipment,
                                )
                              )
                          ),
                          (
                            'Equipo vinculado '
                            + 'correctamente.'
                          ),
                        )
                      }
                      type="button"
                    >
                      {
                        selected
                          .location_mode
                        === 'laboratory'
                          ? (
                            'Registrar arribo'
                          )
                          : (
                            'Vincular equipo'
                          )
                      }
                    </button>
                  )
                  : null
              }
            </div>
          </section>


          <section
            className="
              maintenance-panel
            "
            ref={(node) => {
              sectionRefs.current
                .assignment = node;
            }}
          >
            <h4>
              Asignación y programación
            </h4>

            <div
              className="
                maintenance-grid
              "
            >
              <label
                className={
                  blockerClass(
                    'location_mode',
                  )
                }
              >
                Modalidad operativa

                <select
                  name="location_mode"
                  disabled={
                    selected.status
                    !== 'pending_assignment'
                  }
                  onChange={
                    (event) =>
                      setAssignment({
                        ...assignment,

                        location_mode:
                          event
                            .target
                            .value,

                        address:
                          event
                            .target
                            .value
                          === 'field'
                            ? (
                              assignment
                                .address
                            )
                            : '',
                      })
                  }
                  value={
                    assignment
                      .location_mode
                  }
                >
                  <option value="">
                    Seleccionar modalidad
                  </option>

                  <option
                    value="laboratory"
                  >
                    Laboratorio
                  </option>

                  <option
                    value="field"
                  >
                    Campo
                  </option>
                </select>
              </label>

              <label
                className={
                  blockerClass(
                    'technician_id',
                  )
                }
              >
                Técnico

                <select
                  name="technician_id"
                  disabled={
                    selected.status
                    !== 'pending_assignment'
                  }
                  onChange={
                    (event) =>
                      setAssignment({
                        ...assignment,

                        technician_id:
                          event
                            .target
                            .value,
                      })
                  }
                  value={
                    assignment
                      .technician_id
                  }
                >
                  <option value="">
                    Seleccionar
                  </option>

                  {technicians.map(
                    (item) => (
                      <option
                        key={item.id}
                        value={item.id}
                      >
                        {
                          item.full_name
                          || item.email
                        }
                      </option>
                    ),
                  )}
                </select>
              </label>

              {
                assignment
                  .location_mode
                === 'field'
                  ? (
                    <label>
                      Dirección

                      <textarea
                        disabled={
                          selected.status
                          !== 'pending_assignment'
                        }
                        onChange={
                          (event) =>
                            setAssignment({
                              ...assignment,

                              address:
                                event
                                  .target
                                  .value,
                            })
                        }
                        value={
                          assignment
                            .address
                        }
                      />
                    </label>
                  )
                  : null
              }

              <label>
                Programación

                <input
                  onChange={
                    (event) =>
                      setAssignment({
                        ...assignment,

                        scheduled_for:
                          event
                            .target
                            .value,
                      })
                  }
                  type="datetime-local"
                  value={
                    assignment
                      .scheduled_for
                  }
                />
              </label>
            </div>

            <div
              className="
                maintenance-panel-actions
              "
            >
              {
                canManage
                && selected.status
                === 'pending_assignment'
                  ? (
                    <button
                      className="
                        primary-button
                      "
                      disabled={
                        busy
                        || !assignment
                          .technician_id
                        || !assignment
                          .location_mode
                        || (
                          assignment
                            .location_mode
                          === 'field'
                          && !assignment
                            .address
                            .trim()
                        )
                      }
                      onClick={() =>
                        mutate(
                          () =>
                            prepareMaintenance(
                              order.id,
                              selected.id,
                              {
                                technician_id:
                                  Number(
                                    assignment
                                      .technician_id,
                                  ),

                                location_mode:
                                  assignment
                                    .location_mode,

                                field_address:
                                  assignment
                                    .location_mode
                                  === 'field'
                                    ? {
                                      formatted:
                                        assignment
                                          .address,
                                    }
                                    : null,

                                scheduled_for:
                                  assignment
                                    .scheduled_for
                                  || null,
                              },
                            ),

                          (
                            'Mantenimiento '
                            + 'preparado.'
                          ),
                        )
                      }
                      type="button"
                    >
                      Preparar y asignar
                    </button>
                  )
                  : null
              }

              {
                canExecute
                && selected
                  .location_mode
                === 'field'
                && selected
                  .field_request_status
                === 'requested'
                  ? (
                    <button
                      className="
                        primary-button
                      "
                      disabled={
                        busy
                        || !assignment
                          .scheduled_for
                      }
                      onClick={() =>
                        mutate(
                          () =>
                            acceptMaintenanceFieldVisit(
                              order.id,
                              selected.id,

                              new Date(
                                assignment
                                  .scheduled_for,
                              )
                                .toISOString(),
                            ),

                          (
                            'Visita aceptada '
                            + 'y programada.'
                          ),
                        )
                      }
                      type="button"
                    >
                      Aceptar visita
                    </button>
                  )
                  : null
              }

              {
                canExecute
                && selected.status
                === 'assigned'
                  ? (
                    <button
                      className="
                        primary-button
                      "
                      disabled={
                        busy
                        || (
                          selected
                            .location_mode
                          === 'field'
                          && selected
                            .field_request_status
                          !== 'accepted'
                        )
                      }
                      onClick={() =>
                        mutate(
                          () =>
                            startMaintenance(
                              order.id,
                              selected.id,
                            ),

                          (
                            'Intervención '
                            + 'iniciada.'
                          ),
                        )
                      }
                      type="button"
                    >
                      Iniciar mantenimiento
                    </button>
                  )
                  : null
              }
            </div>
          </section>
        </>
      ) : null}


      {
        /*
         * WORKFLOW OPERATIVO
         */
      }

      {executionCanStartWorkflow ? (
        <section
          className="
            maintenance-workflow
          "
        >
          <header
            className="
              maintenance-workflow__header
            "
          >
            <div>
              <span>
                Flujo técnico
              </span>

              <h4>
                {
                  selected
                    .equipment_name
                  || (
                    'Equipo '
                    + 'sin identificar'
                  )
                }
              </h4>

              <p>
                OT
                {' '}
                {
                  selected
                    .work_order_number
                }
                {' · '}
                {
                  maintenanceTypeLabels[
                    selected
                      .maintenance_type
                  ]
                  || selected
                    .maintenance_type
                }
              </p>
            </div>

            <div
              className="
                maintenance-workflow__progress
              "
            >
              {workflowSteps.map(
                (step, index) => {
                  const currentIndex =
                    workflowStepIndex(
                      workflowStep,
                    );

                  const completed =
                    currentIndex
                    > index;

                  const active =
                    workflowStep
                    === step.id;

                  return (
                    <button
                      className={
                        active
                          ? 'is-active'
                          : (
                            completed
                              ? (
                                'is-completed'
                              )
                              : ''
                          )
                      }
                      key={step.id}
                      onClick={() =>
                        goToWorkflowStep(
                          step.id,
                        )
                      }
                      type="button"
                    >
                      <span>
                        {index + 1}
                      </span>

                      <small>
                        {step.label}
                      </small>
                    </button>
                  );
                },
              )}
            </div>
          </header>


          <div
            className={
              `maintenance-workflow__viewport `
              + `is-${workflowDirection}`
            }
          >
            {
              /*
               * PASO 1 — ANTES
               */
            }

            {workflowStep === 'before' ? (
              <section
                className="
                  maintenance-workflow-step
                "
              >
                <div
                  className="
                    maintenance-workflow-step__heading
                  "
                >
                  <span>
                    Paso 1
                  </span>

                  <h3>
                    ¿Cómo llegó
                    el equipo?
                  </h3>

                  <p>
                    Documenta su condición
                    antes de intervenirlo.
                  </p>
                </div>


                <div
                  className="
                    maintenance-workflow-form
                  "
                >
                  <label>
                    Condición inicial

                    <select
                      value={
                        capture
                          .initial_condition
                      }
                      onChange={
                        (event) =>
                          setCapture({
                            ...capture,

                            initial_condition:
                              event
                                .target
                                .value,
                          })
                      }
                    >
                      <option
                        value="operational"
                      >
                        Operativo
                      </option>

                      <option
                        value="
                          operational_with_anomalies
                        "
                      >
                        Operativo
                        con anomalías
                      </option>

                      <option
                        value="not_operational"
                      >
                        No operativo
                      </option>

                      <option
                        value="undetermined"
                      >
                        No determinado
                      </option>
                    </select>
                  </label>

                  <label
                    className="
                      maintenance-field-wide
                    "
                  >
                    Descripción inicial

                    <textarea
                      value={
                        capture
                          .initial_description
                      }
                      onChange={
                        (event) =>
                          setCapture({
                            ...capture,

                            initial_description:
                              event
                                .target
                                .value,
                          })
                      }
                    />
                  </label>
                </div>


                <div
                  className="
                    maintenance-collection
                  "
                >
                  <div
                    className="
                      maintenance-collection__heading
                    "
                  >
                    <div>
                      <span>
                        Hallazgos
                      </span>

                      <strong>
                        Condición inicial
                        observada
                      </strong>
                    </div>

                    <button
                      className="
                        table-button
                      "
                      onClick={
                        addFinding
                      }
                      type="button"
                    >
                      + Agregar hallazgo
                    </button>
                  </div>

                  {findings.map(
                    (
                      finding,
                      index,
                    ) => (
                      <article
                        className="
                          maintenance-collection-card
                        "
                        key={
                          finding.id
                        }
                      >
                        <header>
                          <strong>
                            Hallazgo
                            {' '}
                            {index + 1}
                          </strong>

                          {
                            findings
                              .length
                            > 1
                              ? (
                                <button
                                  onClick={() =>
                                    removeFinding(
                                      finding.id,
                                    )
                                  }
                                  type="button"
                                >
                                  Eliminar
                                </button>
                              )
                              : null
                          }
                        </header>

                        <div
                          className="
                            maintenance-workflow-form
                          "
                        >
                          <label>
                            Componente

                            <input
                              value={
                                finding
                                  .component
                              }
                              onChange={
                                (event) =>
                                  updateFinding(
                                    finding.id,
                                    'component',

                                    event
                                      .target
                                      .value,
                                  )
                              }
                            />
                          </label>

                          <label
                            className="
                              maintenance-field-wide
                            "
                          >
                            Hallazgo

                            <textarea
                              value={
                                finding
                                  .description
                              }
                              onChange={
                                (event) =>
                                  updateFinding(
                                    finding.id,
                                    'description',

                                    event
                                      .target
                                      .value,
                                  )
                              }
                            />
                          </label>

                          <label>
                            Severidad

                            <select
                              value={
                                finding
                                  .severity
                              }
                              onChange={
                                (event) =>
                                  updateFinding(
                                    finding.id,
                                    'severity',

                                    event
                                      .target
                                      .value,
                                  )
                              }
                            >
                              <option
                                value="low"
                              >
                                Baja
                              </option>

                              <option
                                value="medium"
                              >
                                Media
                              </option>

                              <option
                                value="high"
                              >
                                Alta
                              </option>

                              <option
                                value="critical"
                              >
                                Crítica
                              </option>
                            </select>
                          </label>

                          <label>
                            Resolución

                            <select
                              value={
                                finding
                                  .resolution
                              }
                              onChange={
                                (event) =>
                                  updateFinding(
                                    finding.id,
                                    'resolution',

                                    event
                                      .target
                                      .value,
                                  )
                              }
                            >
                              <option
                                value="corrected"
                              >
                                Corregido
                              </option>

                              <option
                                value="pending"
                              >
                                Pendiente
                              </option>

                              <option
                                value="recommended"
                              >
                                Recomendado
                              </option>

                              <option
                                value="not_authorized"
                              >
                                No autorizado
                              </option>
                            </select>
                          </label>
                        </div>
                      </article>
                    ),
                  )}
                </div>


                <div
                  className="
                    maintenance-evidence
                  "
                >
                  <div
                    className="
                      maintenance-evidence__heading
                    "
                  >
                    <div>
                      <span>
                        Evidencia inicial
                      </span>

                      <strong>
                        Fotografías
                        y multimedia
                      </strong>
                    </div>

                    <label
                      className="
                        maintenance-evidence__add
                      "
                    >
                      + Agregar archivo

                      <input
                        accept="
                          image/*,
                          video/*
                        "
                        multiple
                        onChange={
                          (event) =>
                            addLocalEvidence(
                              event,

                              setBeforeEvidence,
                            )
                        }
                        type="file"
                      />
                    </label>
                  </div>


                  <div
                    className="
                      maintenance-evidence__grid
                    "
                  >
                    {
                      persistedBeforeEvidence
                        .map(
                          (
                            reference,
                            index,
                          ) => (
                            <article
                              className="
                                maintenance-evidence-card
                                is-persisted
                              "
                              key={
                                `persisted-before-${index}`
                              }
                            >
                              <div
                                className="
                                  maintenance-evidence-card__file
                                "
                              >
                                Evidencia
                                almacenada
                              </div>

                              <footer>
                                <span>
                                  {reference}
                                </span>

                                <small>
                                  Guardada
                                </small>
                              </footer>
                            </article>
                          ),
                        )
                    }

                    {beforeEvidence.map(
                      (item) => (
                        <article
                          className="
                            maintenance-evidence-card
                            is-local
                          "
                          key={item.id}
                        >
                          {
                            item.preview
                              ? (
                                <img
                                  alt={
                                    item.name
                                  }
                                  src={
                                    item.preview
                                  }
                                />
                              )
                              : (
                                <div
                                  className="
                                    maintenance-evidence-card__file
                                  "
                                >
                                  Archivo
                                  multimedia
                                </div>
                              )
                          }

                          <footer>
                            <span>
                              {item.name}
                            </span>

                            <button
                              onClick={() =>
                                removeLocalEvidence(
                                  item.id,

                                  setBeforeEvidence,
                                )
                              }
                              type="button"
                            >
                              Eliminar
                            </button>
                          </footer>
                        </article>
                      ),
                    )}

                    {
                      !persistedBeforeEvidence
                        .length
                      && !beforeEvidence
                        .length
                        ? (
                          <div
                            className="
                              maintenance-evidence-empty
                            "
                          >
                            Aún no hay
                            evidencia inicial.
                          </div>
                        )
                        : null
                    }
                  </div>

                  {
                    beforeEvidence.length
                    > 0
                      ? (
                        <div
                          className="
                            maintenance-evidence-pending
                          "
                        >
                          {
                            beforeEvidence
                              .length
                          }
                          {' '}
                          archivo(s)
                          pendientes de
                          subir al
                          almacenamiento
                          institucional.
                        </div>
                      )
                      : null
                  }
                </div>
              </section>
            ) : null}


            {
              /*
               * PASO 2 — INTERVENCIÓN
               */
            }

            {
              workflowStep
              === 'intervention'
                ? (
                  <section
                    className="
                      maintenance-workflow-step
                    "
                  >
                    <div
                      className="
                        maintenance-workflow-step__heading
                      "
                    >
                      <span>
                        Paso 2
                      </span>

                      <h3>
                        ¿Qué se hizo?
                      </h3>

                      <p>
                        Registra todas
                        las intervenciones
                        realizadas.
                      </p>
                    </div>

                    <div
                      className="
                        maintenance-collection
                      "
                    >
                      <div
                        className="
                          maintenance-collection__heading
                        "
                      >
                        <div>
                          <span>
                            Intervenciones
                          </span>

                          <strong>
                            Acciones realizadas
                          </strong>
                        </div>

                        <button
                          className="
                            table-button
                          "
                          onClick={
                            addAction
                          }
                          type="button"
                        >
                          + Agregar intervención
                        </button>
                      </div>

                      {actions.map(
                        (
                          action,
                          index,
                        ) => (
                          <article
                            className="
                              maintenance-collection-card
                            "
                            key={
                              action.id
                            }
                          >
                            <header>
                              <strong>
                                Intervención
                                {' '}
                                {
                                  index
                                  + 1
                                }
                              </strong>

                              {
                                actions
                                  .length
                                > 1
                                  ? (
                                    <button
                                      onClick={() =>
                                        removeAction(
                                          action.id,
                                        )
                                      }
                                      type="button"
                                    >
                                      Eliminar
                                    </button>
                                  )
                                  : null
                              }
                            </header>

                            <div
                              className="
                                maintenance-workflow-form
                              "
                            >
                              <label>
                                Acción

                                <select
                                  value={
                                    action
                                      .action
                                  }
                                  onChange={
                                    (event) =>
                                      updateAction(
                                        action.id,
                                        'action',

                                        event
                                          .target
                                          .value,
                                      )
                                  }
                                >
                                  <option
                                    value="cleaning"
                                  >
                                    Limpieza
                                  </option>

                                  <option
                                    value="adjustment"
                                  >
                                    Ajuste
                                  </option>

                                  <option
                                    value="lubrication"
                                  >
                                    Lubricación
                                  </option>

                                  <option
                                    value="replacement"
                                  >
                                    Sustitución
                                  </option>

                                  <option
                                    value="correction"
                                  >
                                    Corrección
                                  </option>

                                  <option
                                    value="repair_in_scope"
                                  >
                                    Reparación
                                    dentro
                                    de alcance
                                  </option>

                                  <option
                                    value="test"
                                  >
                                    Prueba
                                  </option>

                                  <option
                                    value="other"
                                  >
                                    Otra
                                  </option>
                                </select>
                              </label>

                              <label>
                                Componente

                                <input
                                  value={
                                    action
                                      .component
                                  }
                                  onChange={
                                    (event) =>
                                      updateAction(
                                        action.id,
                                        'component',

                                        event
                                          .target
                                          .value,
                                      )
                                  }
                                />
                              </label>

                              <label
                                className="
                                  maintenance-field-wide
                                "
                              >
                                Resultado

                                <textarea
                                  value={
                                    action
                                      .result
                                  }
                                  onChange={
                                    (event) =>
                                      updateAction(
                                        action.id,
                                        'result',

                                        event
                                          .target
                                          .value,
                                      )
                                  }
                                />
                              </label>
                            </div>
                          </article>
                        ),
                      )}
                    </div>
                  </section>
                )
                : null
            }


            {
              /*
               * PASO 3 — DESPUÉS
               */
            }

            {workflowStep === 'after' ? (
              <section
                className="
                  maintenance-workflow-step
                "
              >
                <div
                  className="
                    maintenance-workflow-step__heading
                  "
                >
                  <span>
                    Paso 3
                  </span>

                  <h3>
                    ¿Cómo quedó?
                  </h3>

                  <p>
                    Documenta la condición
                    final después de
                    la intervención.
                  </p>
                </div>

                <div
                  className="
                    maintenance-workflow-form
                  "
                >
                  <label>
                    Condición final

                    <select
                      value={
                        capture
                          .final_condition
                      }
                      onChange={
                        (event) =>
                          setCapture({
                            ...capture,

                            final_condition:
                              event
                                .target
                                .value,
                          })
                      }
                    >
                      <option
                        value="operational"
                      >
                        Operativo
                      </option>

                      <option
                        value="
                          operational_with_observations
                        "
                      >
                        Operativo con
                        observaciones
                      </option>

                      <option
                        value="not_operational"
                      >
                        No operativo
                      </option>

                      <option
                        value="
                          requires_additional_intervention
                        "
                      >
                        Requiere
                        intervención
                        adicional
                      </option>
                    </select>
                  </label>

                  <label
                    className="
                      maintenance-field-wide
                    "
                  >
                    Resultado funcional

                    <textarea
                      value={
                        capture
                          .functional_result
                      }
                      onChange={
                        (event) =>
                          setCapture({
                            ...capture,

                            functional_result:
                              event
                                .target
                                .value,
                          })
                      }
                    />
                  </label>

                  <label
                    className="
                      maintenance-field-wide
                    "
                  >
                    Conclusión técnica

                    <textarea
                      value={
                        capture
                          .technical_conclusion
                      }
                      onChange={
                        (event) =>
                          setCapture({
                            ...capture,

                            technical_conclusion:
                              event
                                .target
                                .value,
                          })
                      }
                    />
                  </label>
                </div>


                <div
                  className="
                    maintenance-evidence
                  "
                >
                  <div
                    className="
                      maintenance-evidence__heading
                    "
                  >
                    <div>
                      <span>
                        Evidencia final
                      </span>

                      <strong>
                        Fotografías
                        y multimedia
                      </strong>
                    </div>

                    <label
                      className="
                        maintenance-evidence__add
                      "
                    >
                      + Agregar archivo

                      <input
                        accept="
                          image/*,
                          video/*
                        "
                        multiple
                        onChange={
                          (event) =>
                            addLocalEvidence(
                              event,

                              setAfterEvidence,
                            )
                        }
                        type="file"
                      />
                    </label>
                  </div>

                  <div
                    className="
                      maintenance-evidence__grid
                    "
                  >
                    {
                      persistedAfterEvidence
                        .map(
                          (
                            reference,
                            index,
                          ) => (
                            <article
                              className="
                                maintenance-evidence-card
                                is-persisted
                              "
                              key={
                                `persisted-after-${index}`
                              }
                            >
                              <div
                                className="
                                  maintenance-evidence-card__file
                                "
                              >
                                Evidencia
                                almacenada
                              </div>

                              <footer>
                                <span>
                                  {reference}
                                </span>

                                <small>
                                  Guardada
                                </small>
                              </footer>
                            </article>
                          ),
                        )
                    }

                    {afterEvidence.map(
                      (item) => (
                        <article
                          className="
                            maintenance-evidence-card
                            is-local
                          "
                          key={item.id}
                        >
                          {
                            item.preview
                              ? (
                                <img
                                  alt={
                                    item.name
                                  }
                                  src={
                                    item.preview
                                  }
                                />
                              )
                              : (
                                <div
                                  className="
                                    maintenance-evidence-card__file
                                  "
                                >
                                  Archivo
                                  multimedia
                                </div>
                              )
                          }

                          <footer>
                            <span>
                              {item.name}
                            </span>

                            <button
                              onClick={() =>
                                removeLocalEvidence(
                                  item.id,

                                  setAfterEvidence,
                                )
                              }
                              type="button"
                            >
                              Eliminar
                            </button>
                          </footer>
                        </article>
                      ),
                    )}

                    {
                      !persistedAfterEvidence
                        .length
                      && !afterEvidence
                        .length
                        ? (
                          <div
                            className="
                              maintenance-evidence-empty
                            "
                          >
                            Aún no hay
                            evidencia final.
                          </div>
                        )
                        : null
                    }
                  </div>

                  {
                    afterEvidence.length
                    > 0
                      ? (
                        <div
                          className="
                            maintenance-evidence-pending
                          "
                        >
                          {
                            afterEvidence
                              .length
                          }
                          {' '}
                          archivo(s)
                          pendientes de
                          subir al
                          almacenamiento
                          institucional.
                        </div>
                      )
                      : null
                  }
                </div>
              </section>
            ) : null}


            {
              /*
               * PASO 4 — FUTURO
               */
            }

            {workflowStep === 'future' ? (
              <section
                className="
                  maintenance-workflow-step
                "
              >
                <div
                  className="
                    maintenance-workflow-step__heading
                  "
                >
                  <span>
                    Paso 4
                  </span>

                  <h3>
                    ¿Qué necesita
                    después?
                  </h3>

                  <p>
                    Documenta recomendaciones
                    posteriores al servicio.
                  </p>
                </div>

                <div
                  className="
                    maintenance-collection
                  "
                >
                  <div
                    className="
                      maintenance-collection__heading
                    "
                  >
                    <strong>
                      Recomendaciones
                    </strong>

                    <button
                      className="
                        table-button
                      "
                      onClick={
                        addRecommendation
                      }
                      type="button"
                    >
                      + Agregar recomendación
                    </button>
                  </div>

                  {recommendations.map(
                    (
                      item,
                      index,
                    ) => (
                      <article
                        className="
                          maintenance-collection-card
                        "
                        key={
                          item.id
                        }
                      >
                        <header>
                          <strong>
                            Recomendación
                            {' '}
                            {
                              index
                              + 1
                            }
                          </strong>

                          {
                            recommendations
                              .length
                            > 1
                              ? (
                                <button
                                  onClick={() =>
                                    removeRecommendation(
                                      item.id,
                                    )
                                  }
                                  type="button"
                                >
                                  Eliminar
                                </button>
                              )
                              : null
                          }
                        </header>

                        <div
                          className="
                            maintenance-workflow-form
                          "
                        >
                          <label
                            className="
                              maintenance-field-wide
                            "
                          >
                            Recomendación

                            <textarea
                              value={
                                item
                                  .description
                              }
                              onChange={
                                (event) =>
                                  updateRecommendation(
                                    item.id,
                                    'description',

                                    event
                                      .target
                                      .value,
                                  )
                              }
                            />
                          </label>

                          <label>
                            Decisión

                            <select
                              value={
                                item
                                  .decision
                              }
                              onChange={
                                (event) =>
                                  updateRecommendation(
                                    item.id,
                                    'decision',

                                    event
                                      .target
                                      .value,
                                  )
                              }
                            >
                              <option
                                value="pending"
                              >
                                Pendiente
                              </option>

                              <option
                                value="accepted"
                              >
                                Aceptada
                              </option>

                              <option
                                value="rejected"
                              >
                                Rechazada
                              </option>
                            </select>
                          </label>
                        </div>
                      </article>
                    ),
                  )}
                </div>
              </section>
            ) : null}


            {
              /*
               * PASO 5 — MATERIALES / PAUSAS /
               * HALLAZGOS FUERA DE ALCANCE
               */
            }

            {
              workflowStep
              === 'materials'
                ? (
                  <section
                    className="
                      maintenance-workflow-step
                    "
                  >
                    <div
                      className="
                        maintenance-workflow-step__heading
                      "
                    >
                      <span>
                        Paso 5
                      </span>

                      <h3>
                        Materiales
                        e incidencias
                      </h3>

                      <p>
                        Documenta materiales,
                        pausas y necesidades
                        fuera del alcance.
                      </p>
                    </div>


                    <div
                      className="
                        maintenance-workflow-section
                      "
                    >
                      <h4>
                        Material utilizado
                        / requerido
                      </h4>

                      {
                        selected.materials
                          .map(
                            (item) => (
                              <div
                                className="
                                  maintenance-row
                                "
                                key={
                                  item.id
                                }
                              >
                                <span>
                                  {
                                    item
                                      .material_type
                                    === 'used'
                                      ? 'Utilizado'
                                      : (
                                        'Requerido '
                                        + '/ recomendado'
                                      )
                                  }
                                </span>

                                <strong>
                                  {item.name}
                                  {' · '}
                                  {
                                    item
                                      .quantity
                                  }
                                  {' '}
                                  {
                                    item
                                      .unit
                                  }
                                </strong>

                                <small>
                                  {
                                    item
                                      .decision
                                    || (
                                      'Sin decisión'
                                    )
                                  }
                                </small>
                              </div>
                            ),
                          )
                      }

                      {
                        selected.status
                        === 'in_maintenance'
                          ? (
                            <>
                              <div
                                className="
                                  maintenance-workflow-form
                                "
                              >
                                <label>
                                  Clasificación

                                  <select
                                    onChange={
                                      (event) =>
                                        setMaterial({
                                          ...material,

                                          material_type:
                                            event
                                              .target
                                              .value,
                                        })
                                    }
                                    value={
                                      material
                                        .material_type
                                    }
                                  >
                                    <option
                                      value="used"
                                    >
                                      Utilizado
                                    </option>

                                    <option
                                      value="required"
                                    >
                                      Requerido /
                                      recomendado
                                    </option>
                                  </select>
                                </label>

                                <label>
                                  Material

                                  <input
                                    onChange={
                                      (event) =>
                                        setMaterial({
                                          ...material,

                                          name:
                                            event
                                              .target
                                              .value,
                                        })
                                    }
                                    value={
                                      material.name
                                    }
                                  />
                                </label>

                                <label>
                                  Cantidad

                                  <input
                                    min="0.001"
                                    step="0.001"
                                    type="number"
                                    onChange={
                                      (event) =>
                                        setMaterial({
                                          ...material,

                                          quantity:
                                            event
                                              .target
                                              .value,
                                        })
                                    }
                                    value={
                                      material
                                        .quantity
                                    }
                                  />
                                </label>

                                <label>
                                  Unidad

                                  <input
                                    onChange={
                                      (event) =>
                                        setMaterial({
                                          ...material,

                                          unit:
                                            event
                                              .target
                                              .value,
                                        })
                                    }
                                    value={
                                      material.unit
                                    }
                                  />
                                </label>

                                <label>
                                  Componente

                                  <input
                                    onChange={
                                      (event) =>
                                        setMaterial({
                                          ...material,

                                          component:
                                            event
                                              .target
                                              .value,
                                        })
                                    }
                                    value={
                                      material
                                        .component
                                    }
                                  />
                                </label>

                                <label
                                  className="
                                    maintenance-field-wide
                                  "
                                >
                                  Notas

                                  <textarea
                                    onChange={
                                      (event) =>
                                        setMaterial({
                                          ...material,

                                          notes:
                                            event
                                              .target
                                              .value,
                                        })
                                    }
                                    value={
                                      material
                                        .notes
                                    }
                                  />
                                </label>
                              </div>

                              <div
                                className="
                                  maintenance-panel-actions
                                "
                              >
                                <button
                                  className="
                                    table-button
                                  "
                                  disabled={
                                    busy
                                    || !material
                                      .name
                                      .trim()
                                    || Number(
                                      material
                                        .quantity,
                                    ) <= 0
                                  }
                                  onClick={() =>
                                    mutate(
                                      () =>
                                        addMaintenanceMaterial(
                                          order.id,
                                          selected.id,
                                          {
                                            ...material,

                                            quantity:
                                              Number(
                                                material
                                                  .quantity,
                                              ),

                                            internal_unit_cost:
                                              null,

                                            decision:
                                              material
                                                .material_type
                                              === 'required'
                                                ? (
                                                  material
                                                    .decision
                                                )
                                                : null,
                                          },
                                        ),

                                      (
                                        'Material '
                                        + 'documentado.'
                                      ),
                                    )
                                  }
                                  type="button"
                                >
                                  Agregar material
                                </button>
                              </div>
                            </>
                          )
                          : null
                      }
                    </div>


                    <div
                      className="
                        maintenance-workflow-section
                      "
                    >
                      <h4>
                        Pausas y bloqueos
                      </h4>

                      {
                        selected.pauses
                          .length
                        === 0
                          ? (
                            <p>
                              No existen pausas
                              registradas.
                            </p>
                          )
                          : null
                      }

                      {selected.pauses.map(
                        (item) => (
                          <div
                            className="
                              maintenance-row
                            "
                            key={item.id}
                          >
                            <span>
                              {
                                pauseLabels[
                                  item
                                    .pause_type
                                ]
                                || item
                                  .pause_type
                              }
                            </span>

                            <strong>
                              {item.reason}
                            </strong>

                            <small>
                              {
                                pauseStatusLabels[
                                  item.status
                                ]
                                || item.status
                              }
                            </small>

                            {
                              item.status
                              === 'active'
                              && (
                                canAuthorize
                                || canExecute
                              )
                                ? (
                                  <button
                                    onClick={() => {
                                      const resolution =
                                        window.prompt(
                                          (
                                            'Resolución '
                                            + 'documentada'
                                          ),
                                        );

                                      if (
                                        resolution
                                      ) {
                                        mutate(
                                          () =>
                                            resolveMaintenancePause(
                                              order.id,
                                              selected.id,
                                              item.id,
                                              resolution,
                                            ),

                                          (
                                            'Pausa '
                                            + 'resuelta.'
                                          ),
                                        );
                                      }
                                    }}
                                    type="button"
                                  >
                                    Resolver
                                  </button>
                                )
                                : null
                            }
                          </div>
                        ),
                      )}

                      {
                        selected.status
                        === 'in_maintenance'
                          ? (
                            <>
                              <div
                                className="
                                  maintenance-workflow-form
                                "
                              >
                                <label>
                                  Tipo de pausa

                                  <select
                                    onChange={
                                      (event) =>
                                        setPause({
                                          ...pause,

                                          pause_type:
                                            event
                                              .target
                                              .value,
                                        })
                                    }
                                    value={
                                      pause
                                        .pause_type
                                    }
                                  >
                                    <option
                                      value="spare_part"
                                    >
                                      Pendiente
                                      de refacción
                                    </option>

                                    <option
                                      value="authorization"
                                    >
                                      Autorización
                                    </option>

                                    <option
                                      value="second_intervention"
                                    >
                                      Segunda
                                      intervención
                                    </option>

                                    <option
                                      value="commercial_review"
                                    >
                                      Revisión comercial
                                    </option>
                                  </select>
                                </label>

                                <label
                                  className="
                                    maintenance-field-wide
                                  "
                                >
                                  Motivo

                                  <textarea
                                    onChange={
                                      (event) =>
                                        setPause({
                                          ...pause,

                                          reason:
                                            event
                                              .target
                                              .value,
                                        })
                                    }
                                    value={
                                      pause.reason
                                    }
                                  />
                                </label>
                              </div>

                              <div
                                className="
                                  maintenance-panel-actions
                                "
                              >
                                <button
                                  className="
                                    table-button
                                  "
                                  disabled={
                                    busy
                                    || !pause
                                      .reason
                                      .trim()
                                    || !user?.id
                                  }
                                  onClick={() =>
                                    mutate(
                                      () =>
                                        addMaintenancePause(
                                          order.id,
                                          selected.id,
                                          {
                                            ...pause,

                                            responsible_user_id:
                                              Number(
                                                pause
                                                  .responsible_user_id
                                                || user.id,
                                              ),

                                            tentative_resume_at:
                                              pause
                                                .tentative_resume_at
                                                ? (
                                                  new Date(
                                                    pause
                                                      .tentative_resume_at,
                                                  )
                                                    .toISOString()
                                                )
                                                : null,
                                          },
                                        ),

                                      (
                                        'Pausa '
                                        + 'registrada.'
                                      ),
                                    )
                                  }
                                  type="button"
                                >
                                  Registrar pausa
                                </button>
                              </div>
                            </>
                          )
                          : null
                      }
                    </div>


                    <div
                      className="
                        maintenance-workflow-section
                      "
                    >
                      <h4>
                        Fuera de alcance
                      </h4>

                      {selected.changes.map(
                        (item) => (
                          <div
                            className="
                              maintenance-row
                            "
                            key={item.id}
                          >
                            <span>
                              {
                                item
                                  .change_type
                              }
                            </span>

                            <strong>
                              {
                                item
                                  .summary
                              }
                            </strong>

                            <small>
                              {
                                item
                                  .status
                              }
                            </small>
                          </div>
                        ),
                      )}

                      {
                        selected.status
                        === 'in_maintenance'
                          ? (
                            <>
                              <div
                                className="
                                  maintenance-workflow-form
                                "
                              >
                                <label>
                                  Necesidad

                                  <select
                                    onChange={
                                      (event) =>
                                        setChange({
                                          ...change,

                                          change_type:
                                            event
                                              .target
                                              .value,
                                        })
                                    }
                                    value={
                                      change
                                        .change_type
                                    }
                                  >
                                    <option
                                      value="corrective"
                                    >
                                      Correctivo
                                      adicional
                                    </option>

                                    <option
                                      value="repair"
                                    >
                                      Reparación
                                      separada
                                    </option>

                                    <option
                                      value="investigation"
                                    >
                                      Investigación
                                      / diagnóstico
                                    </option>
                                  </select>
                                </label>

                                <label
                                  className="
                                    maintenance-field-wide
                                  "
                                >
                                  Hallazgo

                                  <textarea
                                    onChange={
                                      (event) =>
                                        setChange({
                                          ...change,

                                          summary:
                                            event
                                              .target
                                              .value,
                                        })
                                    }
                                    value={
                                      change
                                        .summary
                                    }
                                  />
                                </label>
                              </div>

                              <div
                                className="
                                  maintenance-panel-actions
                                "
                              >
                                <button
                                  className="
                                    table-button
                                  "
                                  disabled={
                                    busy
                                    || !change
                                      .summary
                                      .trim()
                                  }
                                  onClick={() =>
                                    mutate(
                                      () =>
                                        requestMaintenanceChange(
                                          order.id,
                                          selected.id,
                                          change,
                                        ),

                                      (
                                        'Necesidad '
                                        + 'registrada.'
                                      ),
                                    )
                                  }
                                  type="button"
                                >
                                  Registrar necesidad
                                </button>
                              </div>
                            </>
                          )
                          : null
                      }
                    </div>
                  </section>
                )
                : null
            }


            {
              /*
               * PASO 6 — REVISIÓN Y CIERRE
               */
            }

            {workflowStep === 'review' ? (
              <section
                className="
                  maintenance-workflow-step
                "
              >
                <div
                  className="
                    maintenance-workflow-step__heading
                  "
                >
                  <span>
                    Paso 6
                  </span>

                  <h3>
                    Revisión y cierre
                  </h3>

                  <p>
                    Revisa el expediente antes
                    de terminar técnicamente
                    el mantenimiento.
                  </p>
                </div>


                <div
                  className="
                    maintenance-review-grid
                  "
                >
                  <article>
                    <span>
                      Antes
                    </span>

                    <strong>
                      {
                        capture
                          .initial_description
                          ? 'Documentado'
                          : 'Pendiente'
                      }
                    </strong>
                  </article>

                  <article>
                    <span>
                      Hallazgos
                    </span>

                    <strong>
                      {
                        findings
                          .filter(
                            (item) =>
                              item
                                .description
                                .trim(),
                          )
                          .length
                      }
                    </strong>
                  </article>

                  <article>
                    <span>
                      Intervenciones
                    </span>

                    <strong>
                      {
                        actions
                          .filter(
                            (item) =>
                              item
                                .result
                                .trim(),
                          )
                          .length
                      }
                    </strong>
                  </article>

                  <article>
                    <span>
                      Evidencia inicial
                    </span>

                    <strong>
                      {
                        persistedBeforeEvidence
                          .length
                        + beforeEvidence
                          .length
                      }
                    </strong>
                  </article>

                  <article>
                    <span>
                      Evidencia final
                    </span>

                    <strong>
                      {
                        persistedAfterEvidence
                          .length
                        + afterEvidence
                          .length
                      }
                    </strong>
                  </article>

                  <article>
                    <span>
                      Recomendaciones
                    </span>

                    <strong>
                      {
                        recommendations
                          .filter(
                            (item) =>
                              item
                                .description
                                .trim(),
                          )
                          .length
                      }
                    </strong>
                  </article>
                </div>


                {
                  closureBlockers
                    .length > 0
                    ? (
                      <aside
                        className="
                          maintenance-closure-blockers
                        "
                      >
                        <strong>
                          El mantenimiento
                          todavía no
                          puede cerrarse
                        </strong>

                        {
                          closureBlockers.map(
                            (
                              blocker,
                              index,
                            ) => (
                              <div
                                key={
                                  `closure-${index}`
                                }
                              >
                                {
                                  blocker.message
                                }
                              </div>
                            ),
                          )
                        }
                      </aside>
                    )
                    : (
                      <div
                        className="
                          maintenance-alert
                          is-success
                        "
                      >
                        No existen
                        bloqueantes
                        administrativos
                        de cierre.
                      </div>
                    )
                }


                <div
                  className="
                    maintenance-review-actions
                  "
                >
                  {
                    canCompleteTechnical
                      ? (
                        <button
                          className="
                            primary-button
                          "
                          disabled={
                            busy
                            || operationalBlockers
                              .length > 0
                            || beforeEvidence
                              .length > 0
                            || afterEvidence
                              .length > 0
                          }
                          onClick={() =>
                            mutate(
                              () =>
                                completeMaintenanceTechnical(
                                  order.id,
                                  selected.id,
                                ),

                              (
                                'Mantenimiento '
                                + 'técnicamente '
                                + 'terminado.'
                              ),
                            )
                          }
                          type="button"
                        >
                          Terminar técnicamente
                        </button>
                      )
                      : null
                  }

                  {
                    canManage
                    && [
                      'technically_completed',
                      'pending_release',
                    ].includes(
                      selected.status,
                    )
                      ? (
                        <button
                          className="
                            table-button
                          "
                          disabled={busy}
                          onClick={
                            report
                          }
                          type="button"
                        >
                          {
                            selected.status
                            === 'pending_release'
                              ? (
                                'Regenerar reporte'
                              )
                              : (
                                'Generar reporte'
                              )
                          }
                        </button>
                      )
                      : null
                  }

                  {
                    canClose
                      ? (
                        <button
                          className="
                            primary-button
                          "
                          disabled={
                            busy
                            || !canAdministrativelyClose
                          }
                          onClick={() =>
                            mutate(
                              () =>
                                closeMaintenance(
                                  order.id,
                                  selected.id,
                                ),

                              (
                                'Mantenimiento '
                                + 'cerrado '
                                + 'administrativamente.'
                              ),
                            )
                          }
                          type="button"
                        >
                          Cerrar Mantenimiento
                        </button>
                      )
                      : null
                  }
                </div>


                {
                  canSign
                  && selected.status
                  === 'pending_release'
                  && selected.report_status
                  === 'generated'
                    ? (
                      <form
                        className="
                          maintenance-workflow-form
                        "
                        onSubmit={
                          (event) => {
                            event
                              .preventDefault();

                            mutate(
                              () =>
                                signMaintenanceReport(
                                  order.id,
                                  selected.id,
                                  signature,
                                ),

                              (
                                'Reporte '
                                + 'firmado.'
                              ),
                            );
                          }
                        }
                      >
                        <label>
                          Firmante

                          <input
                            required
                            onChange={
                              (event) =>
                                setSignature({
                                  ...signature,

                                  signer_name:
                                    event
                                      .target
                                      .value,
                                })
                            }
                            value={
                              signature
                                .signer_name
                            }
                          />
                        </label>

                        <label
                          className="
                            maintenance-field-wide
                          "
                        >
                          Firma PNG/JPEG

                          <textarea
                            required
                            onChange={
                              (event) =>
                                setSignature({
                                  ...signature,

                                  signature_data_url:
                                    event
                                      .target
                                      .value,
                                })
                            }
                            value={
                              signature
                                .signature_data_url
                            }
                          />
                        </label>

                        <label>
                          Decisión

                          <select
                            onChange={
                              (event) =>
                                setSignature({
                                  ...signature,

                                  client_decision:
                                    event
                                      .target
                                      .value,
                                })
                            }
                            value={
                              signature
                                .client_decision
                            }
                          >
                            <option
                              value="acknowledged"
                            >
                              Enterado
                            </option>

                            <option
                              value="accepted"
                            >
                              Aceptado
                            </option>

                            <option
                              value="
                                rejected_additional_work
                              "
                            >
                              No procede
                              con trabajo
                              adicional
                            </option>
                          </select>
                        </label>

                        <div
                          className="
                            maintenance-field-wide
                            maintenance-panel-actions
                          "
                        >
                          <button
                            className="
                              primary-button
                            "
                            disabled={
                              busy
                            }
                            type="submit"
                          >
                            Firmar reporte
                          </button>
                        </div>
                      </form>
                    )
                    : null
                }
              </section>
            ) : null}
          </div>


          <footer
            className="
              maintenance-workflow__actions
            "
          >
            <button
              className="
                table-button
              "
              disabled={
                workflowStep
                === workflowSteps[0].id
              }
              onClick={
                goPreviousStep
              }
              type="button"
            >
              ← Anterior
            </button>

            <div>
              <span>
                Paso
                {' '}
                {
                  workflowStepIndex(
                    workflowStep,
                  )
                  + 1
                }
                {' '}
                de
                {' '}
                {
                  workflowSteps.length
                }
              </span>

              {
                workflowStep
                !== 'review'
                  ? (
                    <>
                      <button
                        className="
                          table-button
                        "
                        disabled={
                          busy
                          || !canSaveCapture
                        }
                        onClick={() =>
                          saveWorkflowProgress(
                            false,
                          )
                        }
                        type="button"
                      >
                        Guardar
                      </button>

                      <button
                        className="
                          primary-button
                        "
                        disabled={
                          busy
                          || !canSaveCapture
                        }
                        onClick={() =>
                          saveWorkflowProgress(
                            true,
                          )
                        }
                        type="button"
                      >
                        Guardar y continuar →
                      </button>
                    </>
                  )
                  : null
              }
            </div>
          </footer>
        </section>
      ) : null}
    </section>
  );
}