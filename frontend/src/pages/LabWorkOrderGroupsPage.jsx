import React, { useCallback, useEffect, useState } from 'react';

import { approveLabGroupRequest, claimLabGroupRequest, createLabWorkOrderGroup, listLabGroupRequests, listOperationalRequests, rejectLabGroupRequest } from '../services/api.js';
import { hasAnyPermission } from '../utils/accessControl.js';
import { navigate } from '../utils/routing.js';

const STATUS = { pending: 'Pendiente', in_review: 'En revisión', approved: 'Aprobada', rejected: 'Rechazada' };

export default function LabWorkOrderGroupsPage({ user }) {
  const [items, setItems] = useState([]);
  const [tickets, setTickets] = useState([]);
  const [section, setSection] = useState('groups');
  const [error, setError] = useState('');
  const [busy, setBusy] = useState(null);
  const today = new Date().toISOString().slice(0, 10);
  const [form, setForm] = useState({ quantity: 2, reception_date: today, departure_date: today, client_name: '', address: '' });
  const canClaim = hasAnyPermission(user, ['lab_work_order_groups.requests.claim']);
  const canDecide = hasAnyPermission(user, ['lab_work_order_groups.requests.decide']);
  const load = useCallback(async () => {
    try { const [requests, operationalTickets] = await Promise.all([listLabGroupRequests(), listOperationalRequests()]); setItems(requests); setTickets(operationalTickets); setError(''); }
    catch (requestError) { setError(requestError.message || 'No fue posible cargar las solicitudes.'); }
  }, []);
  useEffect(() => { load(); }, [load]);
  const selectedRequestId = Number(new URLSearchParams(window.location.search).get('request_id') || 0);
  const selectedTicketId = Number(new URLSearchParams(window.location.search).get('ticket_id') || 0);
  useEffect(() => { if (selectedTicketId) setSection('tickets'); }, [selectedTicketId]);

  async function act(item, action) {
    setBusy(item.id);
    try {
      if (action === 'claim') await claimLabGroupRequest(item.id);
      if (action === 'approve') await approveLabGroupRequest(item.id);
      if (action === 'reject') {
        const reason = window.prompt('Motivo obligatorio del rechazo');
        if (!reason?.trim()) return;
        await rejectLabGroupRequest(item.id, reason.trim());
      }
      await load();
    } catch (requestError) { setError(requestError.message || 'No fue posible completar la acción.'); }
    finally { setBusy(null); }
  }

  async function createDirect(event) {
    event.preventDefault(); setBusy('create');
    try { const group = await createLabWorkOrderGroup({ ...form, quantity: Number(form.quantity) }); window.alert(`Grupo creado: folios ${group.related_work_orders.map((item) => item.folio).join(', ')}`); setForm({ ...form, client_name: '', address: '' }); }
    catch (requestError) { setError(requestError.message || 'No fue posible crear el grupo.'); }
    finally { setBusy(null); }
  }

  return <section className="module-page">
    <header className="module-page__header"><div><p className="eyebrow">LAB · CONTROL DE FOLIOS</p><h1>Grupos anticipados de OT</h1><p>Las solicitudes pendientes no reservan folios. La aprobación materializa el grupo completo en una sola transacción.</p></div></header>
    {error && <div className="alert alert--error">{error}</div>}
    <div className="tabs"><button className={section === 'groups' ? 'is-active' : ''} onClick={() => setSection('groups')} type="button">Solicitudes de grupos ({items.length})</button><button className={section === 'tickets' ? 'is-active' : ''} onClick={() => setSection('tickets')} type="button">Reaperturas OT ({tickets.length})</button></div>
    {hasAnyPermission(user, ['lab_work_order_groups.create']) && <form className="card" onSubmit={createDirect}><h2>Crear grupo directo</h2><p>La operación reservará y materializará todas las OT al confirmar.</p><div className="form-grid"><label>Cantidad<input min="1" max="50" type="number" value={form.quantity} onChange={(e) => setForm({ ...form, quantity: e.target.value })} required /></label><label>Recepción<input type="date" value={form.reception_date} onChange={(e) => setForm({ ...form, reception_date: e.target.value })} required /></label><label>Salida<input type="date" value={form.departure_date} onChange={(e) => setForm({ ...form, departure_date: e.target.value })} required /></label><label>Cliente final<input value={form.client_name} onChange={(e) => setForm({ ...form, client_name: e.target.value })} required /></label><label>Domicilio<input value={form.address} onChange={(e) => setForm({ ...form, address: e.target.value })} /></label></div><button disabled={busy === 'create'} type="submit">Crear grupo y asignar folios</button></form>}
    {section === 'groups' && <div className="table-shell"><table><thead><tr><th>Solicitud</th><th>Organización / solicitante</th><th>Cliente final</th><th>Cantidad / fecha</th><th>Estado / handler</th><th>Grupo</th><th>Acciones</th></tr></thead><tbody>
      {items.map((item) => <tr className={selectedRequestId === item.id ? 'is-selected' : ''} key={item.id}><td>#{item.id}</td><td>{item.operator_client_name}<br/><small>{item.requested_by_name}</small></td><td>{item.client_name}</td><td>{item.quantity} OT<br/><small>{new Date(item.created_at).toLocaleString('es-MX')}</small></td><td>{STATUS[item.status] || item.status}<br/><small>{item.handled_by_name || 'Sin handler'}</small></td><td>{item.root_work_order_id ? `Folios ${item.folios.join(', ')}` : 'Sin folios'}</td><td>
        {canClaim && item.status === 'pending' && <button disabled={busy === item.id} onClick={() => act(item, 'claim')}>Tomar</button>}
        {canDecide && item.status === 'in_review' && <><button disabled={busy === item.id} onClick={() => act(item, 'approve')}>Aprobar</button> <button disabled={busy === item.id} onClick={() => act(item, 'reject')}>Rechazar</button></>}
        {item.conversation_id && <button onClick={() => navigate(`/communications?conversation_id=${item.conversation_id}`)} type="button">Abrir conversación</button>}
        {item.root_work_order_id && <button onClick={() => window.alert(`Folios del grupo: ${item.folios.join(', ')}`)} type="button">Ver grupo</button>}
      </td></tr>)}
      {!items.length && <tr><td colSpan="7">No hay solicitudes registradas.</td></tr>}
    </tbody></table></div>}
    {section === 'tickets' && <div className="table-shell"><table><thead><tr><th>Ticket</th><th>OT</th><th>Cliente</th><th>Solicitante</th><th>Motivo</th><th>Estado</th></tr></thead><tbody>{tickets.map((ticket) => <tr className={selectedTicketId === ticket.id ? 'is-selected' : ''} key={ticket.id}><td>#{ticket.id}</td><td>{ticket.work_order_folio}</td><td>{ticket.client_name}</td><td>{ticket.requested_by_name}</td><td>{ticket.reason}</td><td>{ticket.status}</td></tr>)}{!tickets.length && <tr><td colSpan="6">No hay reaperturas registradas.</td></tr>}</tbody></table></div>}
  </section>;
}
