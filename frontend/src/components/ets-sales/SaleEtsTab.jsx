import React, { useEffect, useMemo, useState } from 'react';

import {
  closeSaleOrder,
  confirmSaleDelivery,
  createSaleDelivery,
  dispatchSaleDelivery,
  downloadSaleDeliveryNote,
  getSaleBoard,
  initializeSaleOrder,
  registerSaleArrival,
  reportSaleCourierDelivery,
  requestSaleAuthorization,
  resolveSaleAuthorization,
  resolveSaleWarranty,
  returnSaleWarranty,
} from '../../services/api.js';

import './sale-ets.css';


const statusLabels = {
  pending_arrival: 'Pendiente de arribo',
  partially_arrived: 'Arribo parcial',
  commercial_review: 'Revisión comercial',
  arrived: 'Arribada',
  calibration_pending: 'Calibración pendiente',
  ready_for_delivery: 'Lista para entrega',
  delivery_prepared: 'Entrega preparada',
  partially_delivered: 'Entrega parcial',
  warranty_return: 'Retornado por garantía',
  replaced: 'Sustituida por garantía',
  delivered: 'Entregada',
  resolved: 'Resuelta comercialmente',

  prepared: 'Preparada',
  pickup_notified: 'Cliente notificado',
  technician_requested: 'Solicitada al técnico',
  technician_accepted: 'Aceptada por técnico',
  scheduled: 'Agendada',
  sent: 'Enviada',
  delivery_reported: 'Entrega reportada; firma pendiente',
  cancelled: 'Cancelada',

  requested: 'Solicitada',
  authorized: 'Autorizada',
  rejected: 'Rechazada',
  consumed: 'Consumida',
};

const authorizationTypeLabels = {
  substitution: 'Sustitución',
  individual_identification: 'Individualización excepcional',
  zero_cost_calibration: 'Calibración sin costo',
};

const deliveryModeLabels = {
  client_pickup: 'Recolección por cliente',
  courier: 'Paquetería',
  myc_technician: 'Técnico MYC',
};

const emptyArrival = {
  quantity: 1,
  serial_number: '',
  serial_unknown: false,
  brand: '',
  model: '',
  specification: '',
  substitution_authorization_id: '',
};

const emptyDelivery = {
  mode: 'client_pickup',
  courier_name: '',
  tracking_number: '',
  shipped_on: '',
  estimated_arrival_on: '',
  technician_id: '',
  address_source: 'client',
  custom_address: '',
};

const emptyReceipt = {
  receiver_name: '',
  signature_data_url: '',
  evidence: '',
};

const emptyAuthorization = {
  authorization_type: 'substitution',
  sale_order_item_id: '',
  sale_unit_state_id: '',
  reason: '',
};


function getStatusLabel(status) {
  return statusLabels[status] || status || 'Pendiente';
}

function getStatusTone(status) {
  if (
    [
      'delivered',
      'resolved',
      'authorized',
      'consumed',
      'ready_for_delivery',
    ].includes(status)
  ) {
    return 'done';
  }

  if (
    [
      'partially_arrived',
      'arrived',
      'calibration_pending',
      'delivery_prepared',
      'partially_delivered',
      'prepared',
      'pickup_notified',
      'technician_requested',
      'technician_accepted',
      'scheduled',
      'sent',
      'delivery_reported',
      'requested',
      'commercial_review',
    ].includes(status)
  ) {
    return 'active';
  }

  if (
    [
      'warranty_return',
      'rejected',
      'cancelled',
    ].includes(status)
  ) {
    return 'danger';
  }

  return 'pending';
}


export default function SaleEtsTab({
  order,
  user = null,
  users = [],
}) {
  const [board, setBoard] = useState(null);

  const [arrival, setArrival] = useState(emptyArrival);
  const [arrivalTarget, setArrivalTarget] = useState(null);

  const [delivery, setDelivery] = useState(emptyDelivery);
  const [selectedLines, setSelectedLines] = useState({});

  const [receipt, setReceipt] = useState(emptyReceipt);

  const [warranty, setWarranty] = useState({
    unitId: null,
    reason: '',
  });

  const [warrantyResolution, setWarrantyResolution] = useState({
    unitId: null,
    resolution: 'return_to_flow',
    reason: '',
  });

  const [authorization, setAuthorization] = useState(
    emptyAuthorization
  );

  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState('');
  const [error, setError] = useState('');

  const [expandedItemId, setExpandedItemId] = useState(null);
  const [itemSearch, setItemSearch] = useState('');


  async function refresh() {
    if (!order?.id) {
      return;
    }

    try {
      setBoard(await getSaleBoard(order.id));
    } catch (requestError) {
      setError(
        requestError.message ||
          'No fue posible cargar la operación de Venta.'
      );
    }
  }


  useEffect(() => {
    refresh();
  }, [order?.id]);


  const serviceItems = useMemo(
    () =>
      new Map(
        (order?.items || []).map((item) => [
          Number(item.id),
          item,
        ])
      ),
    [order]
  );


  const technicians = useMemo(
    () =>
      users.filter(
        (candidate) =>
          candidate.is_active !== false &&
          (candidate.roles || []).some(
            (role) => role.name === 'Tecnico'
          )
      ),
    [users]
  );


  const canAuthorize = useMemo(
    () =>
      (user?.permissions || []).some(
        (permission) =>
          permission === '*' ||
          permission === 'service_orders.sales.authorize' ||
          permission === 'service_orders.*'
      ),
    [user]
  );


  const saleSummary = useMemo(() => {
    const items = board?.items || [];

    const totals = items.reduce(
      (summary, item) => {
        summary.items += 1;
        summary.ordered += Number(item.ordered_quantity || 0);
        summary.arrived += Number(item.arrived_quantity || 0);
        summary.delivered += Number(item.delivered_quantity || 0);
        summary.resolved += Number(item.resolved_quantity || 0);

        if (item.included_calibration_catalog_item_id) {
          summary.withCalibration += 1;
        }

        if (item.requires_individual_identification) {
          summary.ready += (item.units || []).filter(
            (unit) => unit.status === 'ready_for_delivery'
          ).length;
        } else {
          summary.ready += Math.max(
            Number(item.arrived_quantity || 0) -
              Number(item.delivered_quantity || 0) -
              Number(item.resolved_quantity || 0),
            0
          );
        }

        return summary;
      },
      {
        items: 0,
        ordered: 0,
        arrived: 0,
        delivered: 0,
        resolved: 0,
        ready: 0,
        withCalibration: 0,
      }
    );

    const completed = totals.delivered + totals.resolved;

    return {
      ...totals,
      completed,
      progress:
        totals.ordered > 0
          ? Math.min(
              100,
              Math.round((completed / totals.ordered) * 100)
            )
          : 0,
    };
  }, [board]);

  const filteredSaleItems = useMemo(() => {
    const query = itemSearch.trim().toLowerCase();

    if (!query) {
      return board?.items || [];
    }

    return (board?.items || []).filter((item) => {
      const source = serviceItems.get(
        Number(item.service_order_item_id)
      );

      const name =
        source?.service_name ||
        source?.description ||
        '';

      const unitText = (item.units || [])
        .map((unit) =>
          [
            unit.serial_number,
            unit.brand,
            unit.model,
          ]
            .filter(Boolean)
            .join(' ')
        )
        .join(' ');

      return [
        source?.id,
        item.id,
        name,
        item.status,
        unitText,
      ]
        .filter(Boolean)
        .join(' ')
        .toLowerCase()
        .includes(query);
    });
  }, [board, serviceItems, itemSearch]);


  const selectedAuthorizationItem = useMemo(
    () =>
      (board?.items || []).find(
        (item) =>
          Number(item.id) ===
          Number(authorization.sale_order_item_id)
      ) || null,
    [board, authorization.sale_order_item_id]
  );


  const selectedAuthorizationUnits =
    selectedAuthorizationItem?.units || [];


  const hasSelectedDeliveryLines = useMemo(
    () =>
      Object.values(selectedLines).some((value) => {
        if (typeof value === 'boolean') {
          return value;
        }

        return Number(value || 0) > 0;
      }),
    [selectedLines]
  );


  async function mutate(action, success) {
    setBusy(true);
    setError('');
    setMessage('');

    try {
      const next = await action();
      setBoard(next);
      setMessage(success);
    } catch (requestError) {
      setError(
        typeof requestError.message === 'string'
          ? requestError.message
          : 'No fue posible completar la acción.'
      );
    } finally {
      setBusy(false);
    }
  }


  async function mutateAndRefresh(action, success) {
    setBusy(true);
    setError('');
    setMessage('');

    try {
      await action();
      setBoard(await getSaleBoard(order.id));
      setMessage(success);
    } catch (requestError) {
      setError(
        requestError.message ||
          'No fue posible completar la acción.'
      );
    } finally {
      setBusy(false);
    }
  }


  async function submitArrival(event) {
    event.preventDefault();

    if (!arrivalTarget) {
      return;
    }

    const item = board.items.find(
      (candidate) => candidate.id === arrivalTarget.itemId
    );

    const source = serviceItems.get(
      Number(item?.service_order_item_id)
    );

    if (!item) {
      setError('No se encontró la partida de Venta.');
      return;
    }

    if (!source?.catalog_item_id) {
      setError(
        'La partida no conserva el concepto de catálogo necesario para registrar el arribo.'
      );
      return;
    }

    await mutate(
      () =>
        registerSaleArrival(
          order.id,
          item.id,
          {
            ...arrival,
            quantity: Number(arrival.quantity),
            catalog_item_id: source.catalog_item_id,
            serial_number:
              arrival.serial_unknown || !arrival.serial_number
                ? null
                : arrival.serial_number,
            brand: arrival.brand || null,
            model: arrival.model || null,
            specification: arrival.specification || null,
            substitution_authorization_id:
              arrival.substitution_authorization_id
                ? Number(
                    arrival.substitution_authorization_id
                  )
                : null,
          },
          arrivalTarget.unitId
        ),
      'Arribo registrado.'
    );

    setArrivalTarget(null);
    setArrival(emptyArrival);
  }


  function toggleLine(key, value) {
    setSelectedLines((current) => ({
      ...current,
      [key]: value,
    }));
  }


  async function submitDelivery(event) {
    event.preventDefault();

    const lines = [];

    board.items.forEach((item) => {
      if (item.requires_individual_identification) {
        item.units
          .filter(
            (unit) =>
              selectedLines[`u-${unit.id}`] &&
              unit.status === 'ready_for_delivery'
          )
          .forEach((unit) =>
            lines.push({
              sale_order_item_id: item.id,
              sale_unit_state_id: unit.id,
              quantity: 1,
            })
          );

        return;
      }

      const quantity = Number(
        selectedLines[`i-${item.id}`] || 0
      );

      if (quantity > 0) {
        lines.push({
          sale_order_item_id: item.id,
          quantity,
        });
      }
    });

    if (!lines.length) {
      setError(
        'Selecciona al menos una unidad o cantidad lista para entrega.'
      );
      return;
    }

    await mutate(
      () =>
        createSaleDelivery(order.id, {
          mode: delivery.mode,
          lines,
          courier_name:
            delivery.mode === 'courier'
              ? delivery.courier_name
              : null,
          tracking_number:
            delivery.mode === 'courier'
              ? delivery.tracking_number
              : null,
          shipped_on: delivery.shipped_on || null,
          estimated_arrival_on:
            delivery.estimated_arrival_on || null,
          technician_id:
            delivery.mode === 'myc_technician'
              ? Number(delivery.technician_id)
              : null,
          address_source:
            delivery.mode === 'myc_technician'
              ? delivery.address_source
              : null,
          delivery_address:
            delivery.mode === 'myc_technician' &&
            delivery.address_source === 'custom'
              ? {
                  formatted: delivery.custom_address,
                }
              : null,
        }),
      'Entrega preparada.'
    );

    setSelectedLines({});
  }


  async function openDeliveryNote(deliveryId) {
    setBusy(true);
    setError('');

    try {
      const result = await downloadSaleDeliveryNote(
        order.id,
        deliveryId
      );

      const url = URL.createObjectURL(result.blob);

      window.open(
        url,
        '_blank',
        'noopener,noreferrer'
      );

      window.setTimeout(
        () => URL.revokeObjectURL(url),
        60000
      );
    } catch (requestError) {
      setError(
        requestError.message ||
          'No fue posible abrir la nota de entrega.'
      );
    } finally {
      setBusy(false);
    }
  }


  function selectAuthorizationItem(value) {
    setAuthorization((current) => ({
      ...current,
      sale_order_item_id: value,
      sale_unit_state_id: '',
    }));
  }


  function getSaleItemName(item) {
    const source = serviceItems.get(
      Number(item.service_order_item_id)
    );

    return (
      source?.service_name ||
      source?.description ||
      `Partida ${source?.id || item.id}`
    );
  }


  if (!board) {
    return (
      <div className="clients-empty">
        {error ? (
          <>
            <p>{error}</p>

            <button
              className="primary-button"
              disabled={busy}
              onClick={() =>
                mutate(
                  () => initializeSaleOrder(order.id),
                  'Operación de Venta inicializada desde el snapshot histórico.'
                )
              }
              type="button"
            >
              Inicializar Venta histórica
            </button>
          </>
        ) : (
          'Cargando operación de Venta…'
        )}
      </div>
    );
  }


  return (
    <section className="sale-ets">
      <header className="sale-ets__hero">
        <div className="sale-ets__hero-copy">
          <span className="sale-ets__eyebrow">
            ETS · Venta
          </span>

          <h3>
            Arribos, liberación y entrega
          </h3>

          <p>
            Control comercial de las partidas de Venta vinculadas
            al expediente. Las calibraciones incluidas continúan
            su proceso técnico en las etapas metrológicas del ETS.
          </p>
        </div>

        <div className="sale-ets__progress-card">
          <div className="sale-ets__progress-heading">
            <strong>{saleSummary.progress}%</strong>
            <span>Resolución comercial</span>
          </div>

          <div
            aria-label={`Progreso ${saleSummary.progress}%`}
            className="sale-ets__progress-bar"
          >
            <span
              style={{
                width: `${saleSummary.progress}%`,
              }}
            />
          </div>

          <small>
            {saleSummary.completed} de {saleSummary.ordered}{' '}
            unidades resueltas
          </small>
        </div>
      </header>


      {error ? (
        <div className="form-error dashboard-error">
          {error}
        </div>
      ) : null}

      {message ? (
        <div className="form-success dashboard-error">
          {message}
        </div>
      ) : null}


      <section className="sale-ets__summary">
        <article>
          <span>Partidas</span>
          <strong>{saleSummary.items}</strong>
        </article>

        <article>
          <span>Vendidas</span>
          <strong>{saleSummary.ordered}</strong>
        </article>

        <article>
          <span>Arribadas</span>
          <strong>{saleSummary.arrived}</strong>
        </article>

        <article>
          <span>Listas para entrega</span>
          <strong>{saleSummary.ready}</strong>
        </article>

        <article>
          <span>Entregadas</span>
          <strong>{saleSummary.delivered}</strong>
        </article>

        <article>
          <span>Con calibración</span>
          <strong>{saleSummary.withCalibration}</strong>
        </article>
      </section>


      <section className="sale-section">
        <header className="sale-section__heading">
          <div>
            <span>Operación comercial</span>
            <h4>Partidas de Venta</h4>
          </div>

          <small>
            {filteredSaleItems.length} de {saleSummary.items}{' '}
            {saleSummary.items === 1 ? 'partida' : 'partidas'}
          </small>
        </header>

        <div className="sale-items-toolbar">
          <label className="sale-items-search">
            <span>Buscar partida</span>

            <input
              onChange={(event) =>
                setItemSearch(event.target.value)
              }
              placeholder="Equipo, partida, serie, marca o modelo"
              type="search"
              value={itemSearch}
            />
          </label>

          {expandedItemId ? (
            <button
              className="table-button"
              onClick={() => setExpandedItemId(null)}
              type="button"
            >
              Contraer partida
            </button>
          ) : null}
        </div>

        {filteredSaleItems.length ? (
          <div className="sale-ets__grid">
            {filteredSaleItems.map((item) => {
              const source = serviceItems.get(
                Number(item.service_order_item_id)
              );

              const hasCalibration = Boolean(
                item.included_calibration_catalog_item_id
              );

              const remaining =
                Number(item.ordered_quantity || 0) -
                Number(item.delivered_quantity || 0) -
                Number(item.resolved_quantity || 0);

              const isExpanded =
                Number(expandedItemId) === Number(item.id);

              const availableForDelivery = Math.max(
                Number(item.arrived_quantity || 0) -
                  Number(item.delivered_quantity || 0) -
                  Number(item.resolved_quantity || 0),
                0
              );

              const toggleItem = () => {
                setExpandedItemId((current) =>
                  Number(current) === Number(item.id)
                    ? null
                    : item.id
                );
              };

              return (
                <article
                  aria-expanded={isExpanded}
                  className={[
                    'sale-item-card',
                    hasCalibration
                      ? 'sale-item-card--calibration'
                      : 'sale-item-card--pure',
                    isExpanded
                      ? 'sale-item-card--expanded'
                      : '',
                  ]
                    .filter(Boolean)
                    .join(' ')}
                  key={item.id}
                >
                  <button
                    className="sale-item-card__trigger"
                    onClick={toggleItem}
                    type="button"
                  >
                    <div className="sale-item-card__trigger-main">
                      <div className="sale-item-card__title">
                        <span>
                          Partida {source?.id || item.id}
                        </span>

                        <strong>
                          {source?.service_name ||
                            source?.description ||
                            'Venta'}
                        </strong>

                        <div className="sale-item-card__badges">
                          <small className="sale-capability-badge">
                            Venta
                          </small>

                          {hasCalibration ? (
                            <small className="sale-capability-badge is-calibration">
                              + Calibración
                            </small>
                          ) : null}
                        </div>
                      </div>

                      <em
                        className={`sale-status-badge is-${getStatusTone(
                          item.status
                        )}`}
                      >
                        {getStatusLabel(item.status)}
                      </em>
                    </div>

                    <div className="sale-item-card__compact-metrics">
                      <div>
                        <span>Vendidas</span>
                        <strong>{item.ordered_quantity}</strong>
                      </div>

                      <div>
                        <span>Arribadas</span>
                        <strong>{item.arrived_quantity}</strong>
                      </div>

                      <div>
                        <span>Entregadas</span>
                        <strong>{item.delivered_quantity}</strong>
                      </div>

                      <div>
                        <span>Pendientes</span>
                        <strong>{Math.max(remaining, 0)}</strong>
                      </div>

                      <div className="sale-item-card__next">
                        <span>Siguiente</span>
                        <strong>
                          {item.status === 'calibration_pending'
                            ? 'Proceso técnico'
                            : item.status === 'ready_for_delivery'
                              ? 'Preparar entrega'
                              : item.status === 'delivered'
                                ? 'Completada'
                                : getStatusLabel(item.status)}
                        </strong>
                      </div>

                      <span
                        aria-hidden="true"
                        className="sale-item-card__chevron"
                      >
                        {isExpanded ? '−' : '+'}
                      </span>
                    </div>
                  </button>

                  {isExpanded ? (
                    <div className="sale-item-card__detail">
                      <div className="sale-item-card__configuration">
                        <div>
                          <span>Control</span>
                          <strong>
                            {item.requires_individual_identification
                              ? 'Individual por unidad y serie'
                              : 'Por cantidad'}
                          </strong>
                        </div>

                        <div>
                          <span>Calibración</span>
                          <strong>
                            {hasCalibration
                              ? 'Incluida'
                              : 'No incluida'}
                          </strong>
                        </div>

                        <div>
                          <span>Estado comercial</span>
                          <strong>
                            {getStatusLabel(item.status)}
                          </strong>
                        </div>

                        <div>
                          <span>Disponibles para entrega</span>
                          <strong>{availableForDelivery}</strong>
                        </div>
                      </div>

                      {item.requires_individual_identification ? (
                        <div className="sale-units">
                          {(item.units || []).map(
                            (unit, index) => (
                              <article
                                className="sale-unit"
                                key={unit.id}
                              >
                                <div className="sale-unit__identity">
                                  <span>
                                    Unidad {index + 1}
                                  </span>

                                  <strong>
                                    {unit.serial_number ||
                                      'Serie pendiente'}
                                  </strong>

                                  <small>
                                    {getStatusLabel(unit.status)}
                                  </small>
                                </div>

                                <div className="sale-unit__actions">
                                  {[
                                    'pending_arrival',
                                    'commercial_review',
                                  ].includes(unit.status) ? (
                                    <button
                                      className="table-button table-button--primary"
                                      disabled={busy}
                                      onClick={() =>
                                        setArrivalTarget({
                                          itemId: item.id,
                                          unitId: unit.id,
                                        })
                                      }
                                      type="button"
                                    >
                                      Registrar arribo
                                    </button>
                                  ) : null}

                                  {unit.status ===
                                  'calibration_pending' ? (
                                    <span className="sale-unit__technical-status">
                                      Continúa en flujo técnico
                                    </span>
                                  ) : null}

                                  {unit.arrived_at &&
                                  ![
                                    'delivered',
                                    'resolved',
                                    'replaced',
                                    'warranty_return',
                                  ].includes(unit.status) ? (
                                    <button
                                      className="table-button table-button--danger"
                                      disabled={busy}
                                      onClick={() =>
                                        setWarranty({
                                          unitId: unit.id,
                                          reason: '',
                                        })
                                      }
                                      type="button"
                                    >
                                      Garantía
                                    </button>
                                  ) : null}

                                  {canAuthorize &&
                                  unit.status ===
                                    'warranty_return' ? (
                                    <button
                                      className="table-button"
                                      disabled={busy}
                                      onClick={() =>
                                        setWarrantyResolution({
                                          unitId: unit.id,
                                          resolution:
                                            'return_to_flow',
                                          reason: '',
                                        })
                                      }
                                      type="button"
                                    >
                                      Resolver garantía
                                    </button>
                                  ) : null}

                                  {unit.status ===
                                  'ready_for_delivery' ? (
                                    <label className="sale-unit__select">
                                      <input
                                        checked={Boolean(
                                          selectedLines[
                                            `u-${unit.id}`
                                          ]
                                        )}
                                        onChange={(event) =>
                                          toggleLine(
                                            `u-${unit.id}`,
                                            event.target.checked
                                          )
                                        }
                                        type="checkbox"
                                      />

                                      <span>
                                        Incluir en entrega
                                      </span>
                                    </label>
                                  ) : null}
                                </div>
                              </article>
                            )
                          )}
                        </div>
                      ) : (
                        <div className="sale-quantity-actions">
                          <div>
                            <span>Control por cantidad</span>

                            <small>
                              {availableForDelivery}{' '}
                              disponibles para entrega
                            </small>
                          </div>

                          <div className="sale-quantity-actions__controls">
                            {item.arrived_quantity <
                            item.ordered_quantity ? (
                              <button
                                className="table-button"
                                disabled={busy}
                                onClick={() =>
                                  setArrivalTarget({
                                    itemId: item.id,
                                    unitId: null,
                                  })
                                }
                                type="button"
                              >
                                Registrar arribo
                              </button>
                            ) : null}

                            <label>
                              Cantidad a entregar

                              <input
                                min="0"
                                onChange={(event) =>
                                  toggleLine(
                                    `i-${item.id}`,
                                    event.target.value
                                  )
                                }
                                type="number"
                                value={
                                  selectedLines[
                                    `i-${item.id}`
                                  ] || ''
                                }
                              />
                            </label>
                          </div>
                        </div>
                      )}

                      <footer className="sale-item-card__footer">
                        <span>Siguiente etapa</span>

                        <strong>
                          {item.status === 'calibration_pending'
                            ? 'Proceso técnico de calibración'
                            : item.status ===
                                'ready_for_delivery'
                              ? 'Preparar entrega'
                              : item.status === 'delivered'
                                ? 'Entrega completada'
                                : getStatusLabel(item.status)}
                        </strong>
                      </footer>
                    </div>
                  ) : null}
                </article>
              );
            })}
          </div>
        ) : (
          <div className="sale-empty">
            <strong>No encontramos partidas</strong>
            <span>
              Cambia el término de búsqueda para volver a
              mostrar resultados.
            </span>
          </div>
        )}
      </section>


      {arrivalTarget ? (
        <form
          className="sale-panel sale-panel--active"
          onSubmit={submitArrival}
        >
          <header className="sale-panel__heading">
            <div>
              <span>Recepción física</span>
              <h4>Registrar arribo</h4>
            </div>

            <button
              className="table-button"
              disabled={busy}
              onClick={() => {
                setArrivalTarget(null);
                setArrival(emptyArrival);
              }}
              type="button"
            >
              Cancelar
            </button>
          </header>

          <div className="sale-form-grid">
            <label>
              Cantidad

              <input
                disabled={Boolean(
                  arrivalTarget.unitId
                )}
                min="1"
                onChange={(event) =>
                  setArrival({
                    ...arrival,
                    quantity: event.target.value,
                  })
                }
                type="number"
                value={arrival.quantity}
              />
            </label>

            <label>
              Serie

              <input
                disabled={arrival.serial_unknown}
                onChange={(event) =>
                  setArrival({
                    ...arrival,
                    serial_number:
                      event.target.value,
                  })
                }
                value={arrival.serial_number}
              />
            </label>

            <label className="checkbox-field sale-checkbox-field">
              <input
                checked={arrival.serial_unknown}
                onChange={(event) =>
                  setArrival({
                    ...arrival,
                    serial_unknown:
                      event.target.checked,
                    serial_number:
                      event.target.checked
                        ? ''
                        : arrival.serial_number,
                  })
                }
                type="checkbox"
              />

              <span>Serie desconocida</span>
            </label>

            <label>
              Marca

              <input
                onChange={(event) =>
                  setArrival({
                    ...arrival,
                    brand: event.target.value,
                  })
                }
                value={arrival.brand}
              />
            </label>

            <label>
              Modelo

              <input
                onChange={(event) =>
                  setArrival({
                    ...arrival,
                    model: event.target.value,
                  })
                }
                value={arrival.model}
              />
            </label>

            <label className="sale-field--wide">
              Especificación

              <textarea
                onChange={(event) =>
                  setArrival({
                    ...arrival,
                    specification:
                      event.target.value,
                  })
                }
                value={arrival.specification}
              />
            </label>

            <label>
              Autorización de sustitución

              <input
                min="1"
                onChange={(event) =>
                  setArrival({
                    ...arrival,
                    substitution_authorization_id:
                      event.target.value,
                  })
                }
                placeholder="Sólo si aplica"
                type="number"
                value={
                  arrival.substitution_authorization_id
                }
              />
            </label>
          </div>

          <div className="sale-panel__actions">
            <button
              className="primary-button"
              disabled={busy}
              type="submit"
            >
              Registrar arribo
            </button>
          </div>
        </form>
      ) : null}


      {warranty.unitId ? (
        <form
          className="sale-panel sale-panel--warning"
          onSubmit={(event) => {
            event.preventDefault();

            mutate(
              () =>
                returnSaleWarranty(
                  order.id,
                  warranty.unitId,
                  warranty.reason
                ),
              'Retorno por garantía registrado.'
            );

            setWarranty({
              unitId: null,
              reason: '',
            });
          }}
        >
          <header className="sale-panel__heading">
            <div>
              <span>Excepción comercial</span>
              <h4>Retorno por garantía</h4>
            </div>
          </header>

          <label>
            Motivo

            <textarea
              minLength="3"
              onChange={(event) =>
                setWarranty({
                  ...warranty,
                  reason: event.target.value,
                })
              }
              required
              value={warranty.reason}
            />
          </label>

          <div className="sale-panel__actions">
            <button
              className="primary-button"
              disabled={busy}
              type="submit"
            >
              Registrar retorno
            </button>

            <button
              className="table-button"
              disabled={busy}
              onClick={() =>
                setWarranty({
                  unitId: null,
                  reason: '',
                })
              }
              type="button"
            >
              Cancelar
            </button>
          </div>
        </form>
      ) : null}


      {warrantyResolution.unitId ? (
        <form
          className="sale-panel sale-panel--warning"
          onSubmit={(event) => {
            event.preventDefault();

            mutate(
              () =>
                resolveSaleWarranty(
                  order.id,
                  warrantyResolution.unitId,
                  {
                    resolution:
                      warrantyResolution.resolution,
                    reason:
                      warrantyResolution.reason,
                  }
                ),
              'Garantía resuelta con trazabilidad comercial.'
            );

            setWarrantyResolution({
              unitId: null,
              resolution: 'return_to_flow',
              reason: '',
            });
          }}
        >
          <header className="sale-panel__heading">
            <div>
              <span>Resolución administrativa</span>
              <h4>Resolver garantía</h4>
            </div>
          </header>

          <div className="sale-form-grid">
            <label>
              Resultado

              <select
                onChange={(event) =>
                  setWarrantyResolution({
                    ...warrantyResolution,
                    resolution:
                      event.target.value,
                  })
                }
                value={
                  warrantyResolution.resolution
                }
              >
                <option value="return_to_flow">
                  Unidad vuelve al flujo
                </option>

                <option value="replacement">
                  Reemplazo pendiente de arribo
                </option>

                <option value="commercial_cancellation">
                  Cancelación comercial definitiva
                </option>
              </select>
            </label>

            <label className="sale-field--wide">
              Justificación

              <textarea
                minLength="3"
                onChange={(event) =>
                  setWarrantyResolution({
                    ...warrantyResolution,
                    reason: event.target.value,
                  })
                }
                required
                value={warrantyResolution.reason}
              />
            </label>
          </div>

          <div className="sale-panel__actions">
            <button
              className="primary-button"
              disabled={busy}
              type="submit"
            >
              Aplicar resolución
            </button>

            <button
              className="table-button"
              disabled={busy}
              onClick={() =>
                setWarrantyResolution({
                  unitId: null,
                  resolution:
                    'return_to_flow',
                  reason: '',
                })
              }
              type="button"
            >
              Cancelar
            </button>
          </div>
        </form>
      ) : null}


      <section className="sale-panel">
        <header className="sale-panel__heading">
          <div>
            <span>Excepciones</span>
            <h4>Autorizaciones comerciales</h4>
          </div>

          <small>
            Las autorizaciones excepcionales conservan
            trazabilidad dentro del ETS.
          </small>
        </header>

        <form
          className="sale-authorization-form"
          onSubmit={(event) => {
            event.preventDefault();

            mutateAndRefresh(
              () =>
                requestSaleAuthorization(order.id, {
                  authorization_type:
                    authorization.authorization_type,
                  sale_order_item_id:
                    authorization.sale_order_item_id
                      ? Number(
                          authorization.sale_order_item_id
                        )
                      : null,
                  sale_unit_state_id:
                    authorization.sale_unit_state_id
                      ? Number(
                          authorization.sale_unit_state_id
                        )
                      : null,
                  reason: authorization.reason,
                }),
              'Solicitud de autorización registrada.'
            );
          }}
        >
          <label>
            Tipo

            <select
              onChange={(event) =>
                setAuthorization({
                  ...authorization,
                  authorization_type:
                    event.target.value,
                })
              }
              value={
                authorization.authorization_type
              }
            >
              <option value="substitution">
                Sustitución
              </option>

              <option value="individual_identification">
                Individualización excepcional
              </option>

              <option value="zero_cost_calibration">
                Calibración sin costo
              </option>
            </select>
          </label>

          <label>
            Partida de Venta

            <select
              onChange={(event) =>
                selectAuthorizationItem(
                  event.target.value
                )
              }
              value={
                authorization.sale_order_item_id
              }
            >
              <option value="">
                Seleccionar partida
              </option>

              {board.items.map((item) => (
                <option
                  key={item.id}
                  value={item.id}
                >
                  {getSaleItemName(item)}
                </option>
              ))}
            </select>
          </label>

          <label>
            Unidad

            <select
              disabled={
                !selectedAuthorizationItem ||
                !selectedAuthorizationItem
                  .requires_individual_identification
              }
              onChange={(event) =>
                setAuthorization({
                  ...authorization,
                  sale_unit_state_id:
                    event.target.value,
                })
              }
              value={
                authorization.sale_unit_state_id
              }
            >
              <option value="">
                {selectedAuthorizationItem?.requires_individual_identification
                  ? 'Seleccionar unidad'
                  : 'No aplica'}
              </option>

              {selectedAuthorizationUnits.map(
                (unit, index) => (
                  <option
                    key={unit.id}
                    value={unit.id}
                  >
                    Unidad {index + 1}
                    {unit.serial_number
                      ? ` · ${unit.serial_number}`
                      : ''}
                  </option>
                )
              )}
            </select>
          </label>

          <label className="sale-authorization-form__reason">
            Justificación

            <textarea
              minLength="3"
              onChange={(event) =>
                setAuthorization({
                  ...authorization,
                  reason: event.target.value,
                })
              }
              required
              value={authorization.reason}
            />
          </label>

          <button
            className="primary-button"
            disabled={busy}
            type="submit"
          >
            Solicitar autorización
          </button>
        </form>


        <div className="sale-authorization-list">
          {board.authorizations?.length ? (
            board.authorizations.map((item) => (
              <article
                className="sale-authorization"
                key={item.id}
              >
                <div>
                  <span>
                    Autorización #{item.id}
                  </span>

                  <strong>
                    {authorizationTypeLabels[
                      item.authorization_type
                    ] ||
                      item.authorization_type}
                  </strong>

                  <p>{item.reason}</p>
                </div>

                <div className="sale-authorization__status">
                  <em
                    className={`sale-status-badge is-${getStatusTone(
                      item.status
                    )}`}
                  >
                    {getStatusLabel(item.status)}
                  </em>

                  {canAuthorize &&
                  item.status === 'requested' ? (
                    <div className="toolbar-actions">
                      <button
                        className="table-button"
                        disabled={busy}
                        onClick={() =>
                          mutateAndRefresh(
                            () =>
                              resolveSaleAuthorization(
                                order.id,
                                item.id,
                                {
                                  authorized: true,
                                  comment:
                                    'Autorización aprobada desde ETS Venta',
                                }
                              ),
                            'Autorización aprobada.'
                          )
                        }
                        type="button"
                      >
                        Autorizar
                      </button>

                      <button
                        className="table-button table-button--danger"
                        disabled={busy}
                        onClick={() =>
                          mutateAndRefresh(
                            () =>
                              resolveSaleAuthorization(
                                order.id,
                                item.id,
                                {
                                  authorized: false,
                                  comment:
                                    'Autorización rechazada desde ETS Venta',
                                }
                              ),
                            'Autorización rechazada.'
                          )
                        }
                        type="button"
                      >
                        Rechazar
                      </button>
                    </div>
                  ) : null}
                </div>
              </article>
            ))
          ) : (
            <div className="sale-empty">
              Sin solicitudes registradas.
            </div>
          )}
        </div>
      </section>


      <section className="sale-panel">
        <header className="sale-panel__heading">
          <div>
            <span>Logística</span>
            <h4>Preparar entrega</h4>
          </div>

          <div className="sale-panel__counter">
            <strong>{saleSummary.ready}</strong>
            <span>listas</span>
          </div>
        </header>

        {saleSummary.ready <= 0 ? (
          <div className="sale-empty sale-empty--delivery">
            <strong>
              No hay unidades listas para entrega
            </strong>

            <span>
              Cuando una partida quede liberada,
              aparecerá aquí para seleccionar su
              modalidad de entrega.
            </span>
          </div>
        ) : (
          <form onSubmit={submitDelivery}>
            <div className="sale-form-grid">
              <label>
                Modalidad

                <select
                  onChange={(event) =>
                    setDelivery({
                      ...delivery,
                      mode: event.target.value,
                    })
                  }
                  value={delivery.mode}
                >
                  <option value="client_pickup">
                    Recolección por cliente
                  </option>

                  <option value="courier">
                    Paquetería
                  </option>

                  <option value="myc_technician">
                    Técnico MYC
                  </option>
                </select>
              </label>


              {delivery.mode === 'courier' ? (
                <>
                  <label>
                    Paquetería

                    <input
                      required
                      onChange={(event) =>
                        setDelivery({
                          ...delivery,
                          courier_name:
                            event.target.value,
                        })
                      }
                      value={
                        delivery.courier_name
                      }
                    />
                  </label>

                  <label>
                    Rastreo

                    <input
                      required
                      onChange={(event) =>
                        setDelivery({
                          ...delivery,
                          tracking_number:
                            event.target.value,
                        })
                      }
                      value={
                        delivery.tracking_number
                      }
                    />
                  </label>

                  <label>
                    Fecha de envío

                    <input
                      onChange={(event) =>
                        setDelivery({
                          ...delivery,
                          shipped_on:
                            event.target.value,
                        })
                      }
                      type="date"
                      value={delivery.shipped_on}
                    />
                  </label>

                  <label>
                    ETA

                    <input
                      onChange={(event) =>
                        setDelivery({
                          ...delivery,
                          estimated_arrival_on:
                            event.target.value,
                        })
                      }
                      type="date"
                      value={
                        delivery.estimated_arrival_on
                      }
                    />
                  </label>
                </>
              ) : null}


              {delivery.mode ===
              'myc_technician' ? (
                <>
                  <label>
                    Técnico

                    <select
                      required
                      onChange={(event) =>
                        setDelivery({
                          ...delivery,
                          technician_id:
                            event.target.value,
                        })
                      }
                      value={
                        delivery.technician_id
                      }
                    >
                      <option value="">
                        Seleccionar
                      </option>

                      {technicians.map(
                        (technician) => (
                          <option
                            key={technician.id}
                            value={technician.id}
                          >
                            {technician.full_name}
                          </option>
                        )
                      )}
                    </select>
                  </label>

                  <label>
                    Dirección

                    <select
                      onChange={(event) =>
                        setDelivery({
                          ...delivery,
                          address_source:
                            event.target.value,
                        })
                      }
                      value={
                        delivery.address_source
                      }
                    >
                      <option value="client">
                        Registrada del cliente
                      </option>

                      <option value="custom">
                        Específica
                      </option>
                    </select>
                  </label>

                  {delivery.address_source ===
                  'custom' ? (
                    <label className="sale-field--wide">
                      Dirección específica

                      <textarea
                        required
                        onChange={(event) =>
                          setDelivery({
                            ...delivery,
                            custom_address:
                              event.target.value,
                          })
                        }
                        value={
                          delivery.custom_address
                        }
                      />
                    </label>
                  ) : null}
                </>
              ) : null}
            </div>

            <div className="sale-panel__actions">
              <button
                className="primary-button"
                disabled={
                  busy ||
                  !hasSelectedDeliveryLines
                }
                type="submit"
              >
                Generar entrega
              </button>
            </div>
          </form>
        )}
      </section>


      <section className="sale-panel">
        <header className="sale-panel__heading">
          <div>
            <span>Trazabilidad logística</span>
            <h4>Entregas y evidencia</h4>
          </div>

          <small>
            {board.deliveries?.length || 0}{' '}
            {(board.deliveries?.length || 0) === 1
              ? 'entrega'
              : 'entregas'}
          </small>
        </header>

        <div className="sale-delivery-list">
          {board.deliveries?.length ? (
            board.deliveries.map((item) => (
              <article
                className="sale-delivery"
                key={item.id}
              >
                <header className="sale-delivery__heading">
                  <div>
                    <span>
                      {deliveryModeLabels[
                        item.mode
                      ] || item.mode}
                    </span>

                    <strong>
                      {item.mode === 'courier'
                        ? item.courier_name ||
                          'Paquetería'
                        : item.mode ===
                            'client_pickup'
                          ? 'Recolección'
                          : 'Entrega MYC'}
                    </strong>

                    {item.tracking_number ? (
                      <small>
                        Rastreo:{' '}
                        {item.tracking_number}
                      </small>
                    ) : null}
                  </div>

                  <em
                    className={`sale-status-badge is-${getStatusTone(
                      item.status
                    )}`}
                  >
                    {getStatusLabel(item.status)}
                  </em>
                </header>

                <div className="sale-delivery__actions">
                  <button
                    className="table-button"
                    disabled={busy}
                    onClick={() =>
                      openDeliveryNote(item.id)
                    }
                    type="button"
                  >
                    Nota de entrega
                  </button>

                  {item.status === 'prepared' ? (
                    <button
                      className="table-button table-button--primary"
                      disabled={busy}
                      onClick={() =>
                        mutate(
                          () =>
                            dispatchSaleDelivery(
                              order.id,
                              item.id
                            ),
                          'Entrega despachada/notificada.'
                        )
                      }
                      type="button"
                    >
                      {item.mode ===
                      'client_pickup'
                        ? 'Notificar al cliente'
                        : 'Marcar enviada'}
                    </button>
                  ) : null}

                  {item.status === 'sent' ? (
                    <button
                      className="table-button"
                      disabled={busy}
                      onClick={() =>
                        mutate(
                          () =>
                            reportSaleCourierDelivery(
                              order.id,
                              item.id
                            ),
                          'Entrega reportada; falta firma.'
                        )
                      }
                      type="button"
                    >
                      Confirmar paquetería
                    </button>
                  ) : null}
                </div>


                {[
                  'pickup_notified',
                  'scheduled',
                  'delivery_reported',
                ].includes(item.status) ? (
                  <form
                    className="sale-receipt"
                    onSubmit={(event) => {
                      event.preventDefault();

                      mutate(
                        () =>
                          confirmSaleDelivery(
                            order.id,
                            item.id,
                            {
                              receiver_name:
                                receipt.receiver_name,
                              signature_data_url:
                                receipt.signature_data_url ||
                                null,
                              evidence:
                                item.mode ===
                                  'myc_technician' &&
                                receipt.evidence
                                  ? {
                                      type: 'technician_attestation',
                                      note: receipt.evidence,
                                    }
                                  : null,
                            }
                          ),
                        'Recepción confirmada.'
                      );

                      setReceipt(emptyReceipt);
                    }}
                  >
                    <input
                      onChange={(event) =>
                        setReceipt({
                          ...receipt,
                          receiver_name:
                            event.target.value,
                        })
                      }
                      placeholder="Nombre de quien recibe"
                      required
                      value={
                        receipt.receiver_name
                      }
                    />

                    <input
                      onChange={(event) =>
                        setReceipt({
                          ...receipt,
                          signature_data_url:
                            event.target.value,
                        })
                      }
                      placeholder="Firma PNG/JPEG (data URL)"
                      required={
                        item.mode !==
                        'myc_technician'
                      }
                      value={
                        receipt.signature_data_url
                      }
                    />

                    {item.mode ===
                    'myc_technician' ? (
                      <input
                        onChange={(event) =>
                          setReceipt({
                            ...receipt,
                            evidence:
                              event.target.value,
                          })
                        }
                        placeholder="Atestación del técnico si no hay firma"
                        value={receipt.evidence}
                      />
                    ) : null}

                    <button
                      className="primary-button"
                      disabled={busy}
                      type="submit"
                    >
                      Confirmar recepción
                    </button>
                  </form>
                ) : null}
              </article>
            ))
          ) : (
            <div className="sale-empty">
              Aún no hay entregas preparadas.
            </div>
          )}
        </div>
      </section>


      <section className="sale-panel sale-close">
        <div>
          <span className="sale-panel__eyebrow">
            Cierre
          </span>

          <h4>Bloqueantes de cierre</h4>

          {board.blockers.length ? (
            <ul>
              {board.blockers.map((blocker) => (
                <li key={blocker}>
                  {blocker}
                </li>
              ))}
            </ul>
          ) : (
            <p>
              Venta completamente entregada y
              documentada.
            </p>
          )}
        </div>

        <button
          className="primary-button"
          disabled={
            !board.can_close || busy
          }
          onClick={() =>
            mutate(
              () => closeSaleOrder(order.id),
              'ETS Venta cerrado.'
            )
          }
          type="button"
        >
          Cerrar Venta
        </button>
      </section>
    </section>
  );
}