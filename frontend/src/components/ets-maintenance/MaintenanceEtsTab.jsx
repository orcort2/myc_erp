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


const emptyCapture = {
  initial_condition: 'undetermined',
  initial_description: '',

  finding_component: '',
  finding_description: '',
  finding_severity: 'medium',
  finding_classification: 'maintenance',
  finding_resolution: 'corrected',

  action: 'cleaning',
  action_component: '',
  action_result: '',

  final_condition: 'operational',
  functional_result: '',
  technical_conclusion: '',

  recommendation: '',
  recommendation_decision: 'pending',

  before_photos: '',
  after_photos: '',
};


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


export default function MaintenanceEtsTab({
  order,
  user = null,
  users = [],
}) {
  const [board, setBoard] = useState(null);
  const [selectedId, setSelectedId] = useState(null);

  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState('');
  const [error, setError] = useState('');

  const [highlightedField, setHighlightedField] = useState('');

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
    address: '',
    scheduled_for: '',
  });

  const [capture, setCapture] = useState(emptyCapture);

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


  const technicians = useMemo(
    () => users.filter(
      (item) => item.is_active !== false,
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


  const activePauses = selected?.active_pauses || [];

  const hasActivePause =
    selected?.has_active_pause === true;

  const operationalBlockers =
    selected?.blockers || [];

  const closureBlockers =
    selected?.closure_blockers || [];

  const maintenanceTypeEvolved =
    selected?.maintenance_type_evolved === true;

  const originalMaintenanceType =
    selected?.original_maintenance_type
    || selected?.maintenance_type;

  const canSaveCapture =
    canExecute
    && selected?.status === 'in_maintenance';

  const canCompleteTechnical =
    canExecute
    && selected?.status === 'in_maintenance';

  const canAdministrativelyClose =
    canClose
    && selected?.status === 'pending_release'
    && closureBlockers.length === 0;


  async function load() {
    try {
      setError('');

      const value = await getMaintenanceBoard(
        order.id,
      );

      setBoard(value);

      setSelectedId((current) => {
        if (
          current
          && value.executions.some(
            (item) => item.id === current,
          )
        ) {
          return current;
        }

        return value.executions[0]?.id || null;
      });
    } catch (requestError) {
      setError(requestError.message);
    }
  }


  useEffect(() => {
    load();
  }, [order.id]);


  useEffect(() => {
    setHighlightedField('');
  }, [selectedId]);


  async function mutate(action, success) {
    setBusy(true);
    setError('');
    setMessage('');

    try {
      const value = await action();

      setBoard(value);
      setMessage(success);
    } catch (requestError) {
      setError(requestError.message);
    } finally {
      setBusy(false);
    }
  }


  function goToBlocker(blocker) {
    const target = sectionRefs.current[
      blocker.section
    ];

    setHighlightedField(blocker.field);

    target?.scrollIntoView({
      behavior: 'smooth',
      block: 'start',
    });

    window.setTimeout(() => {
      const field = target?.querySelector(
        `[name="${blocker.field}"]`,
      );

      field?.focus();
    }, 350);

    window.setTimeout(() => {
      setHighlightedField((current) => (
        current === blocker.field
          ? ''
          : current
      ));
    }, 4500);
  }


  function blockerClass(field) {
    return highlightedField === field
      ? 'maintenance-field-blocked'
      : '';
  }


  function capturePayload() {
    return {
      initial_condition:
        capture.initial_condition,

      initial_description:
        capture.initial_description,

      findings: capture.finding_description
        ? [
          {
            component:
              capture.finding_component
              || 'General',

            description:
              capture.finding_description,

            severity:
              capture.finding_severity,

            classification:
              capture.finding_classification,

            resolution:
              capture.finding_resolution,
          },
        ]
        : [],

      actions: capture.action_result
        ? [
          {
            action:
              capture.action,

            component:
              capture.action_component
              || 'General',

            result:
              capture.action_result,
          },
        ]
        : [],

      final_condition:
        capture.final_condition,

      functional_result:
        capture.functional_result,

      technical_conclusion:
        capture.technical_conclusion,

      recommendations:
        capture.recommendation
          ? [
            {
              description:
                capture.recommendation,

              decision:
                capture.recommendation_decision,
            },
          ]
          : [],

      before_photos:
        capture.before_photos
          .split('\n')
          .map((value) => value.trim())
          .filter(Boolean),

      after_photos:
        capture.after_photos
          .split('\n')
          .map((value) => value.trim())
          .filter(Boolean),
    };
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
      } = await downloadMaintenanceReport(
        order.id,
        selected.id,
      );

      const url = URL.createObjectURL(blob);

      const link = document.createElement('a');

      link.href = url;
      link.download =
        filename
        || `mantenimiento-${selected.id}.pdf`;

      document.body.appendChild(link);
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


  if (!board || !selected) {
    return (
      <section className="maintenance-shell">
        <p>
          {error || 'Cargando Mantenimiento…'}
        </p>
      </section>
    );
  }


  return (
    <section className="maintenance-shell">
      <header className="maintenance-heading">
        <div>
          <span>Vertical operativo</span>

          <h3>ETS Mantenimiento</h3>

          <p>
            Captura estructurada → reporte automático
            → firma → liberación.
          </p>
        </div>

        <select
          aria-label="Equipo de mantenimiento"
          onChange={(event) => {
            setSelectedId(
              Number(event.target.value),
            );
          }}
          value={selected.id}
        >
          {board.executions.map(
            (item, index) => (
              <option
                key={item.id}
                value={item.id}
              >
                Equipo {index + 1}
                {' · '}
                {
                  maintenanceTypeLabels[
                    item.maintenance_type
                  ]
                  || item.maintenance_type
                }
                {' · '}
                {
                  locationLabels[
                    item.location_mode
                  ]
                  || item.location_mode
                }
              </option>
            ),
          )}
        </select>
      </header>


      {error ? (
        <div className="maintenance-alert is-error">
          {error}
        </div>
      ) : null}


      {message ? (
        <div className="maintenance-alert is-success">
          {message}
        </div>
      ) : null}


      {operationalBlockers.length > 0 ? (
        <aside
          className="maintenance-blockers"
          aria-live="polite"
        >
          <strong>
            {operationalBlockers.length}
            {' '}
            bloqueante(s) requieren atención
          </strong>

          {operationalBlockers.map(
            (blocker, index) => (
              <button
                key={
                  `${blocker.section}`
                  + `-${blocker.field}`
                  + `-${index}`
                }
                onClick={() =>
                  goToBlocker(blocker)
                }
                type="button"
              >
                <span>Bloqueante</span>

                {blocker.message}

                <small>
                  Ir a {blocker.section}
                </small>
              </button>
            ),
          )}
        </aside>
      ) : (
        <div className="maintenance-alert is-success">
          No existen bloqueantes para la fase actual.
        </div>
      )}


      {hasActivePause ? (
        <aside className="maintenance-pause-banner">
          <strong>
            Servicio pausado operativamente
          </strong>

          <p>
            El mantenimiento conserva su estado principal:
            {' '}
            {
              statusLabels[selected.status]
              || selected.status
            }.
          </p>

          {activePauses.map((item) => (
            <button
              key={item.id}
              type="button"
              onClick={() =>
                goToBlocker({
                  section: 'pauses',
                  field: `pause-${item.id}`,
                })
              }
            >
              <span>
                {
                  pauseLabels[item.pause_type]
                  || item.pause_type
                }
              </span>

              <strong>{item.reason}</strong>

              <small>Ver pausa</small>
            </button>
          ))}
        </aside>
      ) : null}


      {(selected.notices || []).map(
        (notice, index) => (
          <button
            className={
              `maintenance-notice is-${notice.severity}`
            }
            key={
              `${notice.severity}`
              + `-${notice.section}`
              + `-${index}`
            }
            onClick={() =>
              goToBlocker(notice)
            }
            type="button"
          >
            <strong>
              {
                notice.severity === 'warning'
                  ? 'Advertencia'
                  : 'Recomendación'
              }
            </strong>

            <span>
              {notice.message}
            </span>

            <small>
              Ir a {notice.section}
            </small>
          </button>
        ),
      )}


      <div className="maintenance-status">
        <strong>
          {
            statusLabels[selected.status]
            || selected.status
          }
        </strong>

        <span>
          {
            maintenanceTypeLabels[
              selected.maintenance_type
            ]
            || selected.maintenance_type
          }
          {' · '}
          {
            selected.location_mode === 'field'
              ? 'Campo; equipo con cliente'
              : (
                'Laboratorio; custodia MYC '
                + 'al registrar arribo'
              )
          }
        </span>

        {maintenanceTypeEvolved ? (
          <small className="maintenance-evolution">
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
                selected.maintenance_type
              ]
              || selected.maintenance_type
            }
          </small>
        ) : null}
      </div>


      <section
        className="maintenance-panel"
        ref={(node) => {
          sectionRefs.current.equipment = node;
          sectionRefs.current.arrival = node;
        }}
      >
        <h4>
          {
            selected.location_mode === 'laboratory'
              ? 'Arribo, equipo y OT'
              : 'Equipo atendido en campo'
          }
        </h4>

        <div className="maintenance-grid">
          <label
            className={blockerClass('equipment')}
          >
            Equipo

            <input
              name="equipment"
              onChange={(event) =>
                setEquipment({
                  ...equipment,
                  name: event.target.value,
                })
              }
              value={equipment.name}
            />
          </label>

          <label>
            Marca

            <input
              onChange={(event) =>
                setEquipment({
                  ...equipment,
                  brand: event.target.value,
                })
              }
              value={equipment.brand}
            />
          </label>

          <label>
            Modelo

            <input
              onChange={(event) =>
                setEquipment({
                  ...equipment,
                  model: event.target.value,
                })
              }
              value={equipment.model}
            />
          </label>

          <label>
            Serie

            <input
              onChange={(event) =>
                setEquipment({
                  ...equipment,
                  serial_number:
                    event.target.value,
                })
              }
              value={equipment.serial_number}
            />
          </label>

          <label>
            Identificación interna

            <input
              onChange={(event) =>
                setEquipment({
                  ...equipment,
                  internal_id:
                    event.target.value,
                })
              }
              value={equipment.internal_id}
            />
          </label>

          <label>
            Rango / capacidad

            <input
              onChange={(event) =>
                setEquipment({
                  ...equipment,
                  range_or_capacity:
                    event.target.value,
                })
              }
              value={equipment.range_or_capacity}
            />
          </label>
        </div>


        {canManage && !selected.equipment_id ? (
          <button
            className="primary-button"
            disabled={
              busy
              || !equipment.name
            }
            onClick={() =>
              mutate(
                () => (
                  selected.location_mode
                  === 'laboratory'
                    ? registerMaintenanceArrival(
                      order.id,
                      selected.id,
                      equipment,
                    )
                    : registerMaintenanceFieldEquipment(
                      order.id,
                      selected.id,
                      equipment,
                    )
                ),
                (
                  'Equipo vinculado a la unidad '
                  + 'y OT institucional.'
                ),
              )
            }
            type="button"
          >
            {
              selected.location_mode
              === 'laboratory'
                ? 'Registrar arribo'
                : 'Vincular equipo en campo'
            }
          </button>
        ) : (
          <p>
            Equipo vinculado:
            {' '}
            {selected.equipment_name}
            {' · '}
            OT
            {' '}
            {selected.work_order_number}
          </p>
        )}
      </section>


      <section
        className="maintenance-panel"
        ref={(node) => {
          sectionRefs.current.assignment = node;
        }}
      >
        <h4>
          Asignación y programación
        </h4>

        <div className="maintenance-grid">
          <label
            className={blockerClass(
              'technician_id',
            )}
          >
            Técnico

            <select
              name="technician_id"
              onChange={(event) =>
                setAssignment({
                  ...assignment,
                  technician_id:
                    event.target.value,
                })
              }
              value={assignment.technician_id}
            >
              <option value="">
                Seleccionar
              </option>

              {technicians.map((item) => (
                <option
                  key={item.id}
                  value={item.id}
                >
                  {item.full_name || item.email}
                </option>
              ))}
            </select>
          </label>


          {selected.location_mode === 'field' ? (
            <label>
              Dirección

              <textarea
                onChange={(event) =>
                  setAssignment({
                    ...assignment,
                    address:
                      event.target.value,
                  })
                }
                value={assignment.address}
              />
            </label>
          ) : null}


          <label
            className={blockerClass(
              'field_request_status',
            )}
          >
            Programación

            <input
              name="field_request_status"
              onChange={(event) =>
                setAssignment({
                  ...assignment,
                  scheduled_for:
                    event.target.value,
                })
              }
              type="datetime-local"
              value={assignment.scheduled_for}
            />
          </label>
        </div>


        <div className="toolbar-actions">
          {
            canManage
            && selected.status === 'pending_assignment'
              ? (
                <button
                  className="primary-button"
                  disabled={
                    busy
                    || !assignment.technician_id
                    || (
                      selected.location_mode === 'field'
                      && !assignment.address.trim()
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
                                assignment.technician_id,
                              ),

                            field_address:
                              selected.location_mode
                              === 'field'
                                ? {
                                  formatted:
                                    assignment.address,
                                }
                                : null,

                            scheduled_for:
                              assignment.scheduled_for
                              || null,
                          },
                        ),
                      'Mantenimiento asignado.',
                    )
                  }
                  type="button"
                >
                  Asignar
                </button>
              )
              : null
          }


          {
            canExecute
            && selected.location_mode === 'field'
            && selected.field_request_status
            === 'requested'
              ? (
                <button
                  className="primary-button"
                  disabled={
                    busy
                    || !assignment.scheduled_for
                  }
                  onClick={() =>
                    mutate(
                      () =>
                        acceptMaintenanceFieldVisit(
                          order.id,
                          selected.id,
                          new Date(
                            assignment.scheduled_for,
                          ).toISOString(),
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
            && selected.status === 'assigned'
              ? (
                <button
                  className="primary-button"
                  disabled={
                    busy
                    || (
                      selected.location_mode
                      === 'field'
                      && selected.field_request_status
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
                      'Intervención iniciada.',
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


      <section
        className="maintenance-panel"
        ref={(node) => {
          sectionRefs.current.before = node;
        }}
      >
        <h4>
          ANTES — Qué tenía
        </h4>

        <div className="maintenance-grid">
          <label
            className={blockerClass(
              'initial_condition',
            )}
          >
            Condición inicial

            <select
              name="initial_condition"
              onChange={(event) =>
                setCapture({
                  ...capture,
                  initial_condition:
                    event.target.value,
                })
              }
              value={capture.initial_condition}
            >
              <option value="operational">
                Operativo
              </option>

              <option value="operational_with_anomalies">
                Operativo con anomalías
              </option>

              <option value="not_operational">
                No operativo
              </option>

              <option value="undetermined">
                No determinado
              </option>
            </select>
          </label>


          <label
            className={blockerClass(
              'initial_description',
            )}
          >
            Descripción

            <textarea
              name="initial_description"
              onChange={(event) =>
                setCapture({
                  ...capture,
                  initial_description:
                    event.target.value,
                })
              }
              value={capture.initial_description}
            />
          </label>


          <label>
            Componente con hallazgo

            <input
              onChange={(event) =>
                setCapture({
                  ...capture,
                  finding_component:
                    event.target.value,
                })
              }
              value={capture.finding_component}
            />
          </label>


          <label
            className={blockerClass(
              'findings',
            )}
          >
            Hallazgo

            <textarea
              name="findings"
              onChange={(event) =>
                setCapture({
                  ...capture,
                  finding_description:
                    event.target.value,
                })
              }
              value={capture.finding_description}
            />
          </label>


          <label>
            Severidad

            <select
              onChange={(event) =>
                setCapture({
                  ...capture,
                  finding_severity:
                    event.target.value,
                })
              }
              value={capture.finding_severity}
            >
              <option value="low">
                Baja
              </option>

              <option value="medium">
                Media
              </option>

              <option value="high">
                Alta
              </option>

              <option value="critical">
                Crítica
              </option>
            </select>
          </label>


          <label>
            Resolución

            <select
              onChange={(event) =>
                setCapture({
                  ...capture,
                  finding_resolution:
                    event.target.value,
                })
              }
              value={capture.finding_resolution}
            >
              <option value="corrected">
                Corregido
              </option>

              <option value="pending">
                Pendiente
              </option>

              <option value="not_authorized">
                No autorizado
              </option>

              <option value="recommended">
                Recomendado
              </option>
            </select>
          </label>


          <label
            className={blockerClass(
              'before_photos',
            )}
          >
            Fotografías antes
            {' '}
            (una referencia por línea)

            <textarea
              name="before_photos"
              onChange={(event) =>
                setCapture({
                  ...capture,
                  before_photos:
                    event.target.value,
                })
              }
              value={capture.before_photos}
            />
          </label>
        </div>
      </section>


      <section
        className="maintenance-panel"
        ref={(node) => {
          sectionRefs.current.intervention = node;
        }}
      >
        <h4>
          INTERVENCIÓN — Qué se hizo
        </h4>

        <div className="maintenance-grid">
          <label>
            Acción

            <select
              onChange={(event) =>
                setCapture({
                  ...capture,
                  action:
                    event.target.value,
                })
              }
              value={capture.action}
            >
              <option value="cleaning">
                Limpieza
              </option>

              <option value="adjustment">
                Ajuste
              </option>

              <option value="lubrication">
                Lubricación
              </option>

              <option value="replacement">
                Sustitución
              </option>

              <option value="correction">
                Corrección
              </option>

              <option value="repair_in_scope">
                Reparación dentro de alcance
              </option>

              <option value="test">
                Prueba
              </option>

              <option value="other">
                Otra
              </option>
            </select>
          </label>


          <label>
            Componente

            <input
              onChange={(event) =>
                setCapture({
                  ...capture,
                  action_component:
                    event.target.value,
                })
              }
              value={capture.action_component}
            />
          </label>


          <label>
            Resultado

            <textarea
              onChange={(event) =>
                setCapture({
                  ...capture,
                  action_result:
                    event.target.value,
                })
              }
              value={capture.action_result}
            />
          </label>
        </div>
      </section>


      <section
        className="maintenance-panel"
        ref={(node) => {
          sectionRefs.current.after = node;
        }}
      >
        <h4>
          DESPUÉS — Cómo quedó
        </h4>

        <div className="maintenance-grid">
          <label
            className={blockerClass(
              'final_condition',
            )}
          >
            Condición final

            <select
              name="final_condition"
              onChange={(event) =>
                setCapture({
                  ...capture,
                  final_condition:
                    event.target.value,
                })
              }
              value={capture.final_condition}
            >
              <option value="operational">
                Operativo
              </option>

              <option value="operational_with_observations">
                Operativo con observaciones
              </option>

              <option value="not_operational">
                No operativo
              </option>

              <option value="requires_additional_intervention">
                Requiere intervención adicional
              </option>
            </select>
          </label>


          <label
            className={blockerClass(
              'functional_result',
            )}
          >
            Resultado funcional

            <textarea
              name="functional_result"
              onChange={(event) =>
                setCapture({
                  ...capture,
                  functional_result:
                    event.target.value,
                })
              }
              value={capture.functional_result}
            />
          </label>


          <label
            className={blockerClass(
              'technical_conclusion',
            )}
          >
            Conclusión

            <textarea
              name="technical_conclusion"
              onChange={(event) =>
                setCapture({
                  ...capture,
                  technical_conclusion:
                    event.target.value,
                })
              }
              value={capture.technical_conclusion}
            />
          </label>


          <label
            className={blockerClass(
              'after_photos',
            )}
          >
            Fotografías finales
            {' '}
            (una referencia por línea)

            <textarea
              name="after_photos"
              onChange={(event) =>
                setCapture({
                  ...capture,
                  after_photos:
                    event.target.value,
                })
              }
              value={capture.after_photos}
            />
          </label>
        </div>
      </section>


      <section
        className="maintenance-panel"
        ref={(node) => {
          sectionRefs.current.future = node;
        }}
      >
        <h4>
          FUTURO — Qué necesita
        </h4>

        <div className="maintenance-grid">
          <label>
            Recomendación

            <textarea
              name="recommendations"
              onChange={(event) =>
                setCapture({
                  ...capture,
                  recommendation:
                    event.target.value,
                })
              }
              value={capture.recommendation}
            />
          </label>


          <label>
            Decisión

            <select
              onChange={(event) =>
                setCapture({
                  ...capture,
                  recommendation_decision:
                    event.target.value,
                })
              }
              value={
                capture.recommendation_decision
              }
            >
              <option value="pending">
                Pendiente
              </option>

              <option value="accepted">
                Aceptada
              </option>

              <option value="rejected">
                Rechazada
              </option>
            </select>
          </label>
        </div>


        {canSaveCapture ? (
          <button
            className="primary-button"
            disabled={busy}
            onClick={() =>
              mutate(
                () =>
                  saveMaintenanceCapture(
                    order.id,
                    selected.id,
                    capturePayload(),
                  ),
                'Captura técnica guardada.',
              )
            }
            type="button"
          >
            Guardar captura estructurada
          </button>
        ) : null}
      </section>


      <section
        className="maintenance-panel"
        ref={(node) => {
          sectionRefs.current.pauses = node;
        }}
      >
        <h4>
          Pausas y bloqueos
        </h4>


        {selected.pauses.length === 0 ? (
          <p>
            No existen pausas registradas.
          </p>
        ) : null}


        {selected.pauses.map((item) => (
          <div
            className="maintenance-row"
            id={`pause-${item.id}`}
            key={item.id}
          >
            <span>
              {
                pauseLabels[item.pause_type]
                || item.pause_type
              }
              {' · '}
              {
                pauseStatusLabels[item.status]
                || item.status
              }
            </span>

            <strong>
              {item.reason}
            </strong>

            {item.tentative_resume_at ? (
              <small>
                Reanudación tentativa:
                {' '}
                {
                  formatDateTime(
                    item.tentative_resume_at,
                  )
                }
              </small>
            ) : null}


            {
              item.status === 'resolved'
              && item.resolution
                ? (
                  <small>
                    Resolución:
                    {' '}
                    {item.resolution}
                  </small>
                )
                : null
            }


            {
              (
                canAuthorize
                || (
                  canExecute
                  && selected.technician_id
                  === user?.id
                )
              )
              && item.status === 'active'
                ? (
                  <button
                    onClick={() => {
                      const resolution =
                        window.prompt(
                          'Resolución documentada',
                        );

                      if (resolution) {
                        mutate(
                          () =>
                            resolveMaintenancePause(
                              order.id,
                              selected.id,
                              item.id,
                              resolution,
                            ),
                          'Pausa resuelta.',
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
        ))}


        {selected.status === 'in_maintenance' ? (
          <>
            <div className="maintenance-grid">
              <label>
                Tipo

                <select
                  name="pause_type"
                  onChange={(event) =>
                    setPause({
                      ...pause,
                      pause_type:
                        event.target.value,
                    })
                  }
                  value={pause.pause_type}
                >
                  <option value="spare_part">
                    Pendiente de refacción
                  </option>

                  <option value="authorization">
                    Autorización
                  </option>

                  <option value="second_intervention">
                    Segunda intervención
                  </option>

                  <option value="commercial_review">
                    Revisión comercial
                  </option>

                  {canAuthorize ? (
                    <option value="administrative_investigation">
                      Investigación administrativa
                    </option>
                  ) : null}
                </select>
              </label>


              <label>
                Motivo

                <textarea
                  onChange={(event) =>
                    setPause({
                      ...pause,
                      reason:
                        event.target.value,
                    })
                  }
                  value={pause.reason}
                />
              </label>


              <label>
                Reanudación tentativa

                <input
                  type="datetime-local"
                  onChange={(event) =>
                    setPause({
                      ...pause,
                      tentative_resume_at:
                        event.target.value,
                    })
                  }
                  value={pause.tentative_resume_at}
                />
              </label>
            </div>


            {(canExecute || canAuthorize) ? (
              <button
                className="table-button"
                disabled={
                  busy
                  || !pause.reason.trim()
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
                              pause.responsible_user_id
                              || user.id,
                            ),

                          tentative_resume_at:
                            pause.tentative_resume_at
                              ? new Date(
                                pause.tentative_resume_at,
                              ).toISOString()
                              : null,
                        },
                      ),
                    'Pausa registrada.',
                  )
                }
                type="button"
              >
                Registrar pausa
              </button>
            ) : null}
          </>
        ) : null}
      </section>


      <section
        className="maintenance-panel"
        ref={(node) => {
          sectionRefs.current.materials = node;
        }}
      >
        <h4>
          Material utilizado / requerido
        </h4>


        {selected.materials.map((item) => (
          <div
            className="maintenance-row"
            key={item.id}
          >
            <span>
              {
                item.material_type === 'used'
                  ? 'Utilizado'
                  : 'Requerido / recomendado'
              }
            </span>

            <strong>
              {item.name}
              {' · '}
              {item.quantity}
              {' '}
              {item.unit}
            </strong>

            <small>
              {
                item.decision
                || 'Sin decisión'
              }
            </small>
          </div>
        ))}


        {selected.status === 'in_maintenance' ? (
          <>
            <div className="maintenance-grid">
              <label>
                Clasificación

                <select
                  name="materials"
                  onChange={(event) =>
                    setMaterial({
                      ...material,
                      material_type:
                        event.target.value,
                    })
                  }
                  value={material.material_type}
                >
                  <option value="used">
                    Utilizado
                  </option>

                  <option value="required">
                    Requerido / recomendado
                  </option>
                </select>
              </label>


              <label>
                Material

                <input
                  onChange={(event) =>
                    setMaterial({
                      ...material,
                      name:
                        event.target.value,
                    })
                  }
                  value={material.name}
                />
              </label>


              <label>
                Cantidad

                <input
                  min="0.001"
                  onChange={(event) =>
                    setMaterial({
                      ...material,
                      quantity:
                        event.target.value,
                    })
                  }
                  step="0.001"
                  type="number"
                  value={material.quantity}
                />
              </label>


              <label>
                Unidad

                <input
                  onChange={(event) =>
                    setMaterial({
                      ...material,
                      unit:
                        event.target.value,
                    })
                  }
                  value={material.unit}
                />
              </label>


              <label>
                Componente

                <input
                  onChange={(event) =>
                    setMaterial({
                      ...material,
                      component:
                        event.target.value,
                    })
                  }
                  value={material.component}
                />
              </label>


              <label>
                Notas

                <textarea
                  onChange={(event) =>
                    setMaterial({
                      ...material,
                      notes:
                        event.target.value,
                    })
                  }
                  value={material.notes}
                />
              </label>


              {
                material.material_type
                === 'required'
                  ? (
                    <label>
                      Decisión

                      <select
                        onChange={(event) =>
                          setMaterial({
                            ...material,
                            decision:
                              event.target.value,
                          })
                        }
                        value={material.decision}
                      >
                        <option value="pending">
                          Pendiente
                        </option>

                        <option value="accepted">
                          Aceptado
                        </option>

                        <option value="rejected">
                          Rechazado
                        </option>
                      </select>
                    </label>
                  )
                  : null
              }
            </div>


            {canExecute ? (
              <button
                className="table-button"
                disabled={
                  busy
                  || !material.name.trim()
                  || Number(material.quantity) <= 0
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
                              material.quantity,
                            ),

                          internal_unit_cost:
                            null,

                          decision:
                            material.material_type
                            === 'required'
                              ? material.decision
                              : null,
                        },
                      ),
                    'Material documentado.',
                  )
                }
                type="button"
              >
                Agregar material
              </button>
            ) : null}
          </>
        ) : null}
      </section>


      <section
        className="maintenance-panel"
        ref={(node) => {
          sectionRefs.current.changes = node;
          sectionRefs.current.investigation = node;
        }}
      >
        <h4>
          Hallazgos fuera de alcance
          e investigación
        </h4>


        {selected.changes.map((item) => (
          <div
            className="maintenance-row"
            key={item.id}
          >
            <span>
              {item.change_type}
              {' · '}
              {item.status}
            </span>

            <strong>
              {item.summary}
            </strong>


            {
              canAuthorize
              && item.status === 'requested'
                ? (
                  <div className="toolbar-actions">
                    <button
                      onClick={() => {
                        const reason =
                          window.prompt(
                            'Motivo de rechazo',
                          );

                        if (reason) {
                          mutate(
                            () =>
                              resolveMaintenanceChange(
                                order.id,
                                selected.id,
                                item.id,
                                {
                                  decision: 'rejected',
                                  reason,
                                  quotation_item_id:
                                    null,
                                  linked_service_order_id:
                                    null,
                                },
                              ),
                            'Decisión registrada.',
                          );
                        }
                      }}
                      type="button"
                    >
                      Rechazar
                    </button>


                    {item.change_type === 'corrective' ? (
                      <>
                        <button
                          onClick={() => {
                            const quotationItemId =
                              Number(
                                window.prompt(
                                  (
                                    'ID de partida '
                                    + 'correctiva aprobada '
                                    + 'y vinculada'
                                  ),
                                ),
                              );

                            if (quotationItemId) {
                              mutate(
                                () =>
                                  resolveMaintenanceChange(
                                    order.id,
                                    selected.id,
                                    item.id,
                                    {
                                      decision:
                                        'approved',

                                      reason:
                                        (
                                          'Partida comercial '
                                          + 'aprobada y vinculada'
                                        ),

                                      quotation_item_id:
                                        quotationItemId,

                                      linked_service_order_id:
                                        null,
                                    },
                                  ),
                                (
                                  'Correctivo autorizado '
                                  + 'con trazabilidad.'
                                ),
                              );
                            }
                          }}
                          type="button"
                        >
                          Aplicar aprobación
                        </button>


                        <button
                          onClick={() => {
                            const reason =
                              window.prompt(
                                (
                                  'Justificación del '
                                  + 'override administrativo'
                                ),
                              );

                            if (reason) {
                              mutate(
                                () =>
                                  resolveMaintenanceChange(
                                    order.id,
                                    selected.id,
                                    item.id,
                                    {
                                      decision:
                                        'overridden',

                                      reason,

                                      quotation_item_id:
                                        null,

                                      linked_service_order_id:
                                        null,
                                    },
                                  ),
                                'Override auditado.',
                              );
                            }
                          }}
                          type="button"
                        >
                          Override
                        </button>
                      </>
                    ) : (
                      <button
                        onClick={() => {
                          const linkedServiceOrderId =
                            Number(
                              window.prompt(
                                (
                                  'ID del ETS '
                                  + 'independiente vinculado'
                                ),
                              ),
                            );

                          if (linkedServiceOrderId) {
                            mutate(
                              () =>
                                resolveMaintenanceChange(
                                  order.id,
                                  selected.id,
                                  item.id,
                                  {
                                    decision:
                                      'linked',

                                    reason:
                                      (
                                        'Expediente '
                                        + 'independiente '
                                        + 'vinculado'
                                      ),

                                    quotation_item_id:
                                      null,

                                    linked_service_order_id:
                                      linkedServiceOrderId,
                                  },
                                ),
                              (
                                'Expediente vinculado '
                                + 'sin ejecutar trabajo '
                                + 'fuera de alcance.'
                              ),
                            );
                          }
                        }}
                        type="button"
                      >
                        Vincular ETS
                      </button>
                    )}
                  </div>
                )
                : null
            }
          </div>
        ))}


        {selected.status === 'in_maintenance' ? (
          <>
            <div className="maintenance-grid">
              <label>
                Necesidad

                <select
                  name="changes"
                  onChange={(event) =>
                    setChange({
                      ...change,
                      change_type:
                        event.target.value,
                    })
                  }
                  value={change.change_type}
                >
                  <option value="corrective">
                    Correctivo adicional
                  </option>

                  <option value="repair">
                    Reparación separada
                  </option>

                  <option value="investigation">
                    Investigación / diagnóstico
                  </option>
                </select>
              </label>


              <label>
                Hallazgo

                <textarea
                  onChange={(event) =>
                    setChange({
                      ...change,
                      summary:
                        event.target.value,
                    })
                  }
                  value={change.summary}
                />
              </label>
            </div>


            {canExecute ? (
              <button
                className="table-button"
                disabled={
                  busy
                  || !change.summary.trim()
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
                      'Necesidad enviada al flujo '
                      + 'comercial/administrativo.'
                    ),
                  )
                }
                type="button"
              >
                Registrar necesidad
              </button>
            ) : null}
          </>
        ) : null}


        {
          canAuthorize
          && ['required', 'open'].includes(
            selected.investigation_status,
          )
            ? (
              <button
                className="table-button"
                onClick={() => {
                  const reason =
                    window.prompt(
                      (
                        'Resolución de la '
                        + 'investigación'
                      ),
                    );

                  if (reason) {
                    mutate(
                      () =>
                        resolveMaintenanceInvestigation(
                          order.id,
                          selected.id,
                          reason,
                        ),
                      'Investigación resuelta.',
                    );
                  }
                }}
                type="button"
              >
                Resolver investigación
              </button>
            )
            : null
        }
      </section>


      <section
        className="maintenance-panel"
        ref={(node) => {
          sectionRefs.current.completion = node;
          sectionRefs.current.report = node;
          sectionRefs.current.signature = node;
        }}
      >
        <h4>
          Terminación, reporte, firma y cierre
        </h4>


        {closureBlockers.length > 0 ? (
          <aside className="maintenance-closure-blockers">
            <strong>
              El mantenimiento todavía
              no puede cerrarse
            </strong>

            <p>
              Resuelve los siguientes requisitos
              antes de la liberación administrativa.
            </p>

            {closureBlockers.map(
              (blocker, index) => (
                <button
                  key={
                    `closure-${blocker.section}`
                    + `-${blocker.field}`
                    + `-${index}`
                  }
                  type="button"
                  onClick={() =>
                    goToBlocker(blocker)
                  }
                >
                  <span>
                    Requisito de cierre
                  </span>

                  <strong>
                    {blocker.message}
                  </strong>

                  <small>
                    Corregir en
                    {' '}
                    {blocker.section}
                  </small>
                </button>
              ),
            )}
          </aside>
        ) : selected.status !== 'closed' ? (
          <div className="maintenance-alert is-success">
            No existen bloqueantes administrativos
            de cierre.
          </div>
        ) : null}


        <div className="toolbar-actions">
          {canCompleteTechnical ? (
            <button
              className="primary-button"
              disabled={
                busy
                || operationalBlockers.length > 0
              }
              onClick={() =>
                mutate(
                  () =>
                    completeMaintenanceTechnical(
                      order.id,
                      selected.id,
                    ),
                  (
                    'Mantenimiento técnicamente '
                    + 'terminado; aún no está cerrado.'
                  ),
                )
              }
              type="button"
            >
              Terminar técnicamente
            </button>
          ) : null}


          {
            canManage
            && selected.status
            === 'technically_completed'
              ? (
                <button
                  className="table-button"
                  disabled={busy}
                  onClick={report}
                  type="button"
                >
                  Generar reporte PDF
                </button>
              )
              : null
          }


          {
            canManage
            && selected.status
            === 'pending_release'
              ? (
                <button
                  className="table-button"
                  disabled={busy}
                  onClick={report}
                  type="button"
                >
                  Regenerar reporte PDF
                </button>
              )
              : null
          }
        </div>


        {
          canSign
          && selected.status === 'pending_release'
          && selected.report_status === 'generated'
            ? (
              <form
                className="maintenance-grid"
                onSubmit={(event) => {
                  event.preventDefault();

                  mutate(
                    () =>
                      signMaintenanceReport(
                        order.id,
                        selected.id,
                        signature,
                      ),
                    'Reporte firmado.',
                  );
                }}
              >
                <label>
                  Firmante

                  <input
                    onChange={(event) =>
                      setSignature({
                        ...signature,
                        signer_name:
                          event.target.value,
                      })
                    }
                    required
                    value={signature.signer_name}
                  />
                </label>


                <label
                  className={blockerClass(
                    'signature_data_url',
                  )}
                >
                  Firma PNG/JPEG
                  {' '}
                  (data URL)

                  <textarea
                    name="signature_data_url"
                    onChange={(event) =>
                      setSignature({
                        ...signature,
                        signature_data_url:
                          event.target.value,
                      })
                    }
                    required
                    value={
                      signature.signature_data_url
                    }
                  />
                </label>


                <label>
                  Decisión

                  <select
                    onChange={(event) =>
                      setSignature({
                        ...signature,
                        client_decision:
                          event.target.value,
                      })
                    }
                    value={
                      signature.client_decision
                    }
                  >
                    <option value="acknowledged">
                      Enterado
                    </option>

                    <option value="accepted">
                      Aceptado
                    </option>

                    <option value="rejected_additional_work">
                      No procede con trabajo adicional
                    </option>
                  </select>
                </label>


                <button
                  className="primary-button"
                  disabled={busy}
                  type="submit"
                >
                  Firmar versión
                  {' '}
                  {selected.report_version}
                </button>
              </form>
            )
            : null
        }


        {canClose ? (
          <button
            className="primary-button"
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
                  'Mantenimiento cerrado '
                  + 'administrativamente.'
                ),
              )
            }
            type="button"
          >
            Cerrar Mantenimiento
          </button>
        ) : null}
      </section>
    </section>
  );
}