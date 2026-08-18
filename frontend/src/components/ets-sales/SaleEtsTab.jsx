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
  returnSaleWarranty,
} from '../../services/api.js';
import './sale-ets.css';

const statusLabels = {
  pending_arrival: 'Pendiente de arribo', partially_arrived: 'Arribo parcial',
  commercial_review: 'Revisión comercial', arrived: 'Arribada',
  calibration_pending: 'Calibración pendiente', ready_for_delivery: 'Lista para entrega',
  delivery_prepared: 'Entrega preparada', partially_delivered: 'Entrega parcial',
  warranty_return: 'Retornado por garantía', delivered: 'Entregada', resolved: 'Resuelta',
  prepared: 'Preparada', pickup_notified: 'Cliente notificado', technician_requested: 'Solicitada al técnico',
  scheduled: 'Agendada', sent: 'Enviada', delivery_reported: 'Entrega reportada; firma pendiente'
};

const emptyArrival = { quantity: 1, serial_number: '', serial_unknown: false, brand: '', model: '', specification: '', substitution_authorization_id: '' };
const emptyDelivery = { mode: 'client_pickup', courier_name: '', tracking_number: '', shipped_on: '', estimated_arrival_on: '', technician_id: '', address_source: 'client', custom_address: '' };

export default function SaleEtsTab({ order, user = null, users = [] }) {
  const [board, setBoard] = useState(null);
  const [arrival, setArrival] = useState(emptyArrival);
  const [arrivalTarget, setArrivalTarget] = useState(null);
  const [delivery, setDelivery] = useState(emptyDelivery);
  const [selectedLines, setSelectedLines] = useState({});
  const [receipt, setReceipt] = useState({ receiver_name: '', signature_data_url: '', evidence: '' });
  const [warranty, setWarranty] = useState({ unitId: null, reason: '' });
  const [authorization, setAuthorization] = useState({ authorization_type: 'substitution', sale_order_item_id: '', sale_unit_state_id: '', reason: '' });
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState('');
  const [error, setError] = useState('');

  async function refresh() {
    if (!order?.id) return;
    try { setBoard(await getSaleBoard(order.id)); } catch (requestError) { setError(requestError.message); }
  }

  useEffect(() => { refresh(); }, [order?.id]);

  const serviceItems = useMemo(() => new Map((order?.items || []).map((item) => [item.id, item])), [order]);
  const technicians = users.filter((user) => user.is_active !== false && (user.roles || []).some((role) => role.name === 'Tecnico'));
  const canAuthorize = (user?.permissions || []).some((permission) => permission === '*' || permission === 'service_orders.sales.authorize' || permission === 'service_orders.*');

  async function mutate(action, success) {
    setBusy(true); setError(''); setMessage('');
    try { const next = await action(); setBoard(next); setMessage(success); }
    catch (requestError) { setError(typeof requestError.message === 'string' ? requestError.message : 'No fue posible completar la acción.'); }
    finally { setBusy(false); }
  }

  async function mutateAndRefresh(action, success) {
    setBusy(true); setError(''); setMessage('');
    try { await action(); setBoard(await getSaleBoard(order.id)); setMessage(success); }
    catch (requestError) { setError(requestError.message || 'No fue posible completar la acción.'); }
    finally { setBusy(false); }
  }

  async function submitArrival(event) {
    event.preventDefault();
    if (!arrivalTarget) return;
    const item = board.items.find((candidate) => candidate.id === arrivalTarget.itemId);
    const source = serviceItems.get(item.service_order_item_id);
    await mutate(() => registerSaleArrival(order.id, item.id, {
      ...arrival,
      quantity: Number(arrival.quantity),
      catalog_item_id: source.catalog_item_id,
      serial_number: arrival.serial_number || null,
      brand: arrival.brand || null,
      model: arrival.model || null,
      specification: arrival.specification || null,
      substitution_authorization_id: arrival.substitution_authorization_id ? Number(arrival.substitution_authorization_id) : null
    }, arrivalTarget.unitId), 'Arribo registrado.');
    setArrivalTarget(null); setArrival(emptyArrival);
  }

  function toggleLine(key, value) {
    setSelectedLines((current) => ({ ...current, [key]: value }));
  }

  async function submitDelivery(event) {
    event.preventDefault();
    const lines = [];
    board.items.forEach((item) => {
      if (item.requires_individual_identification) {
        item.units.filter((unit) => selectedLines[`u-${unit.id}`]).forEach((unit) => lines.push({ sale_order_item_id: item.id, sale_unit_state_id: unit.id, quantity: 1 }));
      } else {
        const quantity = Number(selectedLines[`i-${item.id}`] || 0);
        if (quantity > 0) lines.push({ sale_order_item_id: item.id, quantity });
      }
    });
    await mutate(() => createSaleDelivery(order.id, {
      mode: delivery.mode, lines,
      courier_name: delivery.mode === 'courier' ? delivery.courier_name : null,
      tracking_number: delivery.mode === 'courier' ? delivery.tracking_number : null,
      shipped_on: delivery.shipped_on || null,
      estimated_arrival_on: delivery.estimated_arrival_on || null,
      technician_id: delivery.mode === 'myc_technician' ? Number(delivery.technician_id) : null,
      address_source: delivery.mode === 'myc_technician' ? delivery.address_source : null,
      delivery_address: delivery.address_source === 'custom' ? { formatted: delivery.custom_address } : null
    }), 'Entrega preparada.');
    setSelectedLines({});
  }

  async function openDeliveryNote(deliveryId) {
    setBusy(true); setError('');
    try {
      const result = await downloadSaleDeliveryNote(order.id, deliveryId);
      const url = URL.createObjectURL(result.blob);
      window.open(url, '_blank', 'noopener,noreferrer');
      window.setTimeout(() => URL.revokeObjectURL(url), 60000);
    } catch (requestError) { setError(requestError.message); }
    finally { setBusy(false); }
  }

  if (!board) return <div className="clients-empty">{error ? <><p>{error}</p><button className="primary-button" disabled={busy} onClick={() => mutate(() => initializeSaleOrder(order.id), 'Operación de Venta inicializada desde el snapshot histórico.')} type="button">Inicializar Venta histórica</button></> : 'Cargando operación de Venta…'}</div>;

  return (
    <section className="sale-ets">
      <header className="sale-ets__header">
        <div><p>ETS Venta</p><h3>Arribos, liberación y entrega</h3></div>
        <div className="sale-ets__progress"><strong>{board.items.reduce((sum, item) => sum + item.delivered_quantity + item.resolved_quantity, 0)}</strong><span>resueltas de {board.items.reduce((sum, item) => sum + item.ordered_quantity, 0)}</span></div>
      </header>
      {error ? <div className="form-error dashboard-error">{error}</div> : null}
      {message ? <div className="form-success">{message}</div> : null}

      <div className="sale-ets__grid">
        {board.items.map((item) => {
          const source = serviceItems.get(item.service_order_item_id);
          return (
            <article className="sale-item-card" key={item.id}>
              <div className="sale-item-card__heading"><div><span>Partida {source?.id}</span><strong>{source?.service_name || 'Venta'}</strong></div><em>{statusLabels[item.status] || item.status}</em></div>
              <div className="sale-item-card__metrics"><span>Vendidas <b>{item.ordered_quantity}</b></span><span>Arribadas <b>{item.arrived_quantity}</b></span><span>Entregadas <b>{item.delivered_quantity}</b></span></div>
              <small>{item.requires_individual_identification ? 'Control individual por unidad y serie' : 'Control por cantidad'}{item.included_calibration_catalog_item_id ? ' · Calibración incluida' : ''}</small>
              {item.requires_individual_identification ? (
                <div className="sale-units">
                  {item.units.map((unit, index) => (
                    <div className="sale-unit" key={unit.id}>
                      <div><strong>Unidad {index + 1}</strong><span>{unit.serial_number || 'Serie pendiente'} · {statusLabels[unit.status] || unit.status}</span></div>
                      <div className="toolbar-actions">
                        {unit.status === 'pending_arrival' || unit.status === 'commercial_review' ? <button className="table-button" onClick={() => setArrivalTarget({ itemId: item.id, unitId: unit.id })} type="button">Registrar arribo</button> : null}
                        {unit.arrived_at && !['delivered', 'resolved', 'warranty_return'].includes(unit.status) ? <button className="table-button table-button--danger" onClick={() => setWarranty({ unitId: unit.id, reason: '' })} type="button">Garantía</button> : null}
                        {unit.status === 'ready_for_delivery' ? <label className="sale-unit__select"><input checked={Boolean(selectedLines[`u-${unit.id}`])} onChange={(event) => toggleLine(`u-${unit.id}`, event.target.checked)} type="checkbox" /> Entregar</label> : null}
                      </div>
                    </div>
                  ))}
                </div>
              ) : (
                <div className="sale-quantity-actions">
                  {item.arrived_quantity < item.ordered_quantity ? <button className="table-button" onClick={() => setArrivalTarget({ itemId: item.id, unitId: null })} type="button">Registrar arribo parcial</button> : null}
                  <label>Cantidad a entregar<input min="0" onChange={(event) => toggleLine(`i-${item.id}`, event.target.value)} type="number" value={selectedLines[`i-${item.id}`] || ''} /></label>
                </div>
              )}
            </article>
          );
        })}
      </div>

      {arrivalTarget ? <form className="sale-panel" onSubmit={submitArrival}><h4>Alta física por asesor</h4><div className="sale-form-grid"><label>Cantidad<input disabled={Boolean(arrivalTarget.unitId)} min="1" onChange={(event) => setArrival({ ...arrival, quantity: event.target.value })} type="number" value={arrival.quantity} /></label><label>Serie<input disabled={arrival.serial_unknown} onChange={(event) => setArrival({ ...arrival, serial_number: event.target.value })} value={arrival.serial_number} /></label><label className="checkbox-field"><input checked={arrival.serial_unknown} onChange={(event) => setArrival({ ...arrival, serial_unknown: event.target.checked })} type="checkbox" />Serie desconocida</label><label>Marca<input onChange={(event) => setArrival({ ...arrival, brand: event.target.value })} value={arrival.brand} /></label><label>Modelo<input onChange={(event) => setArrival({ ...arrival, model: event.target.value })} value={arrival.model} /></label><label>Especificación<textarea onChange={(event) => setArrival({ ...arrival, specification: event.target.value })} value={arrival.specification} /></label><label>Autorización de sustitución (si aplica)<input min="1" onChange={(event) => setArrival({ ...arrival, substitution_authorization_id: event.target.value })} type="number" value={arrival.substitution_authorization_id} /></label></div><div className="toolbar-actions"><button className="primary-button" disabled={busy} type="submit">Registrar alta</button><button className="table-button" onClick={() => setArrivalTarget(null)} type="button">Cancelar</button></div></form> : null}

      {warranty.unitId ? <form className="sale-panel" onSubmit={(event) => { event.preventDefault(); mutate(() => returnSaleWarranty(order.id, warranty.unitId, warranty.reason), 'Retorno por garantía registrado.'); setWarranty({ unitId: null, reason: '' }); }}><h4>Retorno por garantía</h4><label>Motivo<textarea minLength="3" onChange={(event) => setWarranty({ ...warranty, reason: event.target.value })} required value={warranty.reason} /></label><div className="toolbar-actions"><button className="primary-button" disabled={busy} type="submit">Registrar retorno</button><button className="table-button" onClick={() => setWarranty({ unitId: null, reason: '' })} type="button">Cancelar</button></div></form> : null}

      <section className="sale-panel"><h4>Autorizaciones comerciales</h4><form className="sale-form-grid" onSubmit={(event) => { event.preventDefault(); mutateAndRefresh(() => requestSaleAuthorization(order.id, { authorization_type: authorization.authorization_type, sale_order_item_id: authorization.sale_order_item_id ? Number(authorization.sale_order_item_id) : null, sale_unit_state_id: authorization.sale_unit_state_id ? Number(authorization.sale_unit_state_id) : null, reason: authorization.reason }), 'Solicitud de autorización registrada.'); }}><label>Tipo<select onChange={(event) => setAuthorization({ ...authorization, authorization_type: event.target.value })} value={authorization.authorization_type}><option value="substitution">Sustitución</option><option value="individual_identification">Individualización excepcional</option><option value="zero_cost_calibration">Calibración sin costo</option></select></label><label>ID de partida Venta<input min="1" onChange={(event) => setAuthorization({ ...authorization, sale_order_item_id: event.target.value })} type="number" value={authorization.sale_order_item_id} /></label><label>ID de unidad<input min="1" onChange={(event) => setAuthorization({ ...authorization, sale_unit_state_id: event.target.value })} type="number" value={authorization.sale_unit_state_id} /></label><label>Justificación<textarea minLength="3" onChange={(event) => setAuthorization({ ...authorization, reason: event.target.value })} required value={authorization.reason} /></label><button className="primary-button" disabled={busy} type="submit">Solicitar autorización</button></form>{board.authorizations?.length ? board.authorizations.map((item) => <div className="sale-unit" key={item.id}><div><strong>Autorización #{item.id} · {item.authorization_type}</strong><span>{item.status} · {item.reason}</span></div>{canAuthorize && item.status === 'requested' ? <div className="toolbar-actions"><button className="table-button" onClick={() => mutateAndRefresh(() => resolveSaleAuthorization(order.id, item.id, { authorized: true, comment: 'Autorización aprobada desde ETS Venta' }), 'Autorización aprobada.')} type="button">Autorizar</button><button className="table-button table-button--danger" onClick={() => mutateAndRefresh(() => resolveSaleAuthorization(order.id, item.id, { authorized: false, comment: 'Autorización rechazada desde ETS Venta' }), 'Autorización rechazada.')} type="button">Rechazar</button></div> : null}</div>) : <p>Sin solicitudes registradas.</p>}</section>

      <form className="sale-panel" onSubmit={submitDelivery}><h4>Preparar entrega</h4><div className="sale-form-grid"><label>Modalidad<select onChange={(event) => setDelivery({ ...delivery, mode: event.target.value })} value={delivery.mode}><option value="client_pickup">Recolección por cliente</option><option value="courier">Paquetería</option><option value="myc_technician">Técnico MYC</option></select></label>{delivery.mode === 'courier' ? <><label>Paquetería<input required onChange={(event) => setDelivery({ ...delivery, courier_name: event.target.value })} value={delivery.courier_name} /></label><label>Rastreo<input required onChange={(event) => setDelivery({ ...delivery, tracking_number: event.target.value })} value={delivery.tracking_number} /></label><label>Fecha envío<input onChange={(event) => setDelivery({ ...delivery, shipped_on: event.target.value })} type="date" value={delivery.shipped_on} /></label><label>ETA<input onChange={(event) => setDelivery({ ...delivery, estimated_arrival_on: event.target.value })} type="date" value={delivery.estimated_arrival_on} /></label></> : null}{delivery.mode === 'myc_technician' ? <><label>Técnico<select required onChange={(event) => setDelivery({ ...delivery, technician_id: event.target.value })} value={delivery.technician_id}><option value="">Seleccionar</option>{technicians.map((user) => <option key={user.id} value={user.id}>{user.full_name}</option>)}</select></label><label>Dirección<select onChange={(event) => setDelivery({ ...delivery, address_source: event.target.value })} value={delivery.address_source}><option value="client">Registrada del cliente</option><option value="custom">Específica</option></select></label>{delivery.address_source === 'custom' ? <label>Dirección específica<textarea required onChange={(event) => setDelivery({ ...delivery, custom_address: event.target.value })} value={delivery.custom_address} /></label> : null}</> : null}</div><button className="primary-button" disabled={busy || !Object.values(selectedLines).some(Boolean)} type="submit">Generar entrega</button></form>

      <section className="sale-panel"><h4>Entregas y evidencia</h4>{board.deliveries.length ? board.deliveries.map((item) => <article className="sale-delivery" key={item.id}><div><strong>{item.mode === 'courier' ? item.courier_name : item.mode === 'client_pickup' ? 'Recolección' : 'Entrega MYC'}</strong><span>{statusLabels[item.status] || item.status}{item.tracking_number ? ` · ${item.tracking_number}` : ''}</span></div><div className="toolbar-actions"><button className="table-button" onClick={() => openDeliveryNote(item.id)} type="button">Nota</button>{item.status === 'prepared' ? <button className="table-button" onClick={() => mutate(() => dispatchSaleDelivery(order.id, item.id), 'Entrega despachada/notificada.')} type="button">{item.mode === 'client_pickup' ? 'Enviar al cliente' : 'Marcar enviada'}</button> : null}{item.status === 'sent' ? <button className="table-button" onClick={() => mutate(() => reportSaleCourierDelivery(order.id, item.id), 'Entrega reportada; falta firma.')} type="button">Confirmar paquetería</button> : null}</div>{['pickup_notified', 'scheduled', 'delivery_reported'].includes(item.status) ? <form className="sale-receipt" onSubmit={(event) => { event.preventDefault(); mutate(() => confirmSaleDelivery(order.id, item.id, { receiver_name: receipt.receiver_name, signature_data_url: receipt.signature_data_url || null, evidence: receipt.evidence ? { note: receipt.evidence } : null }), 'Recepción confirmada.'); }}><input onChange={(event) => setReceipt({ ...receipt, receiver_name: event.target.value })} placeholder="Nombre de quien recibe" required value={receipt.receiver_name} /><input onChange={(event) => setReceipt({ ...receipt, signature_data_url: event.target.value })} placeholder="Firma/evidencia (data URL)" value={receipt.signature_data_url} /><input onChange={(event) => setReceipt({ ...receipt, evidence: event.target.value })} placeholder="Evidencia o nota" value={receipt.evidence} /><button className="primary-button" type="submit">Confirmar recepción</button></form> : null}</article>) : <div className="clients-empty">Aún no hay entregas preparadas.</div>}</section>

      <section className="sale-panel sale-close"><div><h4>Bloqueantes de cierre</h4>{board.blockers.length ? <ul>{board.blockers.map((blocker) => <li key={blocker}>{blocker}</li>)}</ul> : <p>Venta completamente entregada y documentada.</p>}</div><button className="primary-button" disabled={!board.can_close || busy} onClick={() => mutate(() => closeSaleOrder(order.id), 'ETS Venta cerrado.')} type="button">Cerrar Venta</button></section>
    </section>
  );
}
