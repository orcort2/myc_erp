import React, { useEffect, useMemo, useState } from 'react';

import { createUser, listPortalInvitations, listPortalLinkRequests, listPortalMemberships, listPortalRegistrations, listRoles, listUserActivity, listUsers, updateUser } from '../../services/api.js';
import PortalAccessSettingsPanel from './PortalAccessSettingsPanel.jsx';
import UserModal from './UserModal.jsx';

const EMPTY_FORM = { username: '', full_name: '', email: '', password: '', role_names: [], is_active: true, phone: '', job_title: '', area: '', language: 'es-MX', timezone: 'America/Mexico_City', must_change_password: false };
const FILTERS = [
  ['all', 'Todos'], ['internal', 'Usuarios internos'], ['portal', 'Cuentas del portal'], ['verification', 'Pendientes de verificación'], ['review', 'Pendientes de revisión'], ['link', 'Pendientes de vinculación'], ['active', 'Activos'], ['suspended', 'Suspendidos'], ['blocked', 'Bloqueados'], ['unlinked', 'Sin cliente vinculado']
];
const PAGE_SIZE = 10;

function buildPortalRows(registrations, memberships) {
  const byUser = new Map();
  registrations.forEach((registration) => byUser.set(registration.user_id, { id: `portal-${registration.user_id}`, userId: registration.user_id, accountType: 'client_portal', ...registration.user, registration, membership: null, roles: [] }));
  memberships.forEach((membership) => {
    const row = byUser.get(membership.user_id) ?? { id: `portal-${membership.user_id}`, userId: membership.user_id, accountType: 'client_portal', username: membership.username, full_name: membership.full_name, email: membership.email, created_at: membership.created_at, registration: null };
    byUser.set(membership.user_id, { ...row, status: membership.account_status, is_active: membership.account_is_active, email_verified_at: membership.email_verified_at, last_login_at: membership.last_login_at, password_changed_at: membership.password_changed_at, must_change_password: membership.must_change_password, failed_login_attempts: membership.failed_login_attempts, locked_until: membership.locked_until, membership, roles: membership.role_codes ?? [] });
  });
  return [...byUser.values()];
}

export default function UsersSettingsPanel() {
  const [view, setView] = useState('accounts');
  const [data, setData] = useState({ users: [], roles: [], registrations: [], memberships: [], invitations: [], requests: [] });
  const [query, setQuery] = useState(''); const [filter, setFilter] = useState('all'); const [page, setPage] = useState(1);
  const [modal, setModal] = useState(null); const [form, setForm] = useState(EMPTY_FORM); const [activity, setActivity] = useState([]);
  const [loading, setLoading] = useState(true); const [submitting, setSubmitting] = useState(false); const [error, setError] = useState(''); const [notice, setNotice] = useState('');

  async function load() {
    setLoading(true); setError('');
    try {
      const [users, roles, registrations, memberships, invitations, requests] = await Promise.all([listUsers(), listRoles(), listPortalRegistrations(), listPortalMemberships(), listPortalInvitations(), listPortalLinkRequests()]);
      setData({ users, roles, registrations, memberships, invitations, requests });
    } catch (requestError) { setError(requestError.message); } finally { setLoading(false); }
  }
  useEffect(() => { load(); }, []);

  const rows = useMemo(() => [
    ...data.users.map((user) => ({ ...user, userId: user.id, accountType: 'internal', roles: user.roles?.map((role) => role.name) ?? [] })),
    ...buildPortalRows(data.registrations, data.memberships)
  ], [data]);
  const filtered = useMemo(() => rows.filter((row) => {
    const needle = query.trim().toLowerCase();
    if (needle && ![row.full_name, row.username, row.email, row.registration?.declared_company_name, row.registration?.declared_company_rfc].some((value) => String(value ?? '').toLowerCase().includes(needle))) return false;
    const registrationStatus = row.registration?.status;
    if (filter === 'internal') return row.accountType === 'internal'; if (filter === 'portal') return row.accountType === 'client_portal';
    if (filter === 'verification') return registrationStatus === 'pending_email_verification'; if (filter === 'review') return registrationStatus === 'pending_review';
    if (filter === 'link') return registrationStatus === 'link_requested'; if (filter === 'active') return row.status === 'active' && (!row.membership || row.membership.status === 'active');
    if (filter === 'suspended') return row.status === 'suspended' || row.membership?.status === 'suspended'; if (filter === 'blocked') return Boolean(row.locked_until);
    if (filter === 'unlinked') return row.accountType === 'client_portal' && !row.membership; return true;
  }), [filter, query, rows]);
  const pages = Math.max(1, Math.ceil(filtered.length / PAGE_SIZE));
  const visible = filtered.slice((Math.min(page, pages) - 1) * PAGE_SIZE, Math.min(page, pages) * PAGE_SIZE);

  async function openRow(row) {
    setActivity([]);
    try { setActivity(await listUserActivity(row.userId)); } catch { setActivity([]); }
    setForm(row.accountType === 'internal' ? { ...EMPTY_FORM, ...row, role_names: row.roles } : { ...EMPTY_FORM, ...row, role_names: row.roles, is_active: row.status === 'active', failed_login_attempts: row.failed_login_attempts ?? 0 });
    setModal({ mode: 'edit', row });
  }
  function openCreate() { setForm({ ...EMPTY_FORM, role_names: data.roles[0] ? [data.roles[0].name] : [] }); setModal({ mode: 'create', row: { accountType: 'internal' } }); setActivity([]); }
  function change(event) { const { name, value, type, checked } = event.target; setForm((current) => ({ ...current, [name]: type === 'checkbox' ? checked : value })); }
  async function submit(event) {
    event.preventDefault(); setSubmitting(true); setError('');
    try {
      const payload = { username: form.username, email: form.email.trim().toLowerCase(), full_name: form.full_name.trim(), role_names: form.role_names, phone: form.phone || null, job_title: form.job_title || null, area: form.area || null, language: form.language, timezone: form.timezone, is_active: form.is_active, must_change_password: form.must_change_password };
      if (modal.mode === 'create') await createUser({ ...payload, password: form.password }); else await updateUser(modal.row.userId, payload);
      setNotice(modal.mode === 'create' ? 'Usuario creado.' : 'Usuario actualizado.'); setModal(null); await load();
    } catch (requestError) { setError(requestError.message); } finally { setSubmitting(false); }
  }

  return <section className="settings-panel portal-user-administration">
    <div className="client-modal-tabs" role="tablist"><button className={view === 'accounts' ? 'client-modal-tab is-active' : 'client-modal-tab'} onClick={() => setView('accounts')} type="button">Usuarios y cuentas</button><button className={view === 'operations' ? 'client-modal-tab is-active' : 'client-modal-tab'} onClick={() => setView('operations')} type="button">Registros, solicitudes e invitaciones</button></div>
    {view === 'operations' ? <PortalAccessSettingsPanel globalMode onChanged={load} /> : <>
      <div className="section-heading"><div><p>Ajustes · Usuarios</p><h2>{loading ? 'Cargando…' : `${filtered.length} cuentas`}</h2></div><button className="primary-button" onClick={openCreate} type="button">Nuevo usuario interno</button></div>
      {error ? <div className="form-error">{error}</div> : null}{notice ? <div className="form-notice">{notice}</div> : null}
      <div className="settings-account-toolbar"><input aria-label="Buscar cuentas" className="text-input" onChange={(event) => { setQuery(event.target.value); setPage(1); }} placeholder="Buscar nombre, usuario, correo, empresa o RFC" value={query} /><select aria-label="Filtrar cuentas" className="settings-role-select" onChange={(event) => { setFilter(event.target.value); setPage(1); }} value={filter}>{FILTERS.map(([value, label]) => <option key={value} value={value}>{label}</option>)}</select></div>
      <div className="clients-table settings-account-table"><div className="clients-table__head"><span>Cuenta</span><span>Tipo</span><span>Estado</span><span>Empresa / cliente</span><span>Roles</span></div>{visible.map((row) => <div className="clients-table__row settings-users-table__row" key={row.id} onClick={() => openRow(row)} onKeyDown={(event) => { if (event.key === 'Enter') openRow(row); }} role="button" tabIndex={0}><span><strong>{row.full_name}</strong><small>@{row.username} · {row.email}</small><small>Registro: {row.created_at ? new Date(row.created_at).toLocaleDateString() : 'sin fecha'}</small></span><span>{row.accountType === 'internal' ? 'Staff MYC' : 'Usuario externo'}</span><span><span className={`settings-status ${row.status === 'active' ? 'active' : 'inactive'}`}>{row.membership?.status ?? row.registration?.status ?? row.status}</span><small>{row.email_verified_at ? 'Correo verificado' : 'Correo no verificado'}</small><small>Último acceso: {row.last_login_at ? new Date(row.last_login_at).toLocaleDateString() : 'nunca'}</small></span><span>{row.registration?.declared_company_name ?? (row.membership ? `Cliente #${row.membership.client_id}` : 'MYC')}</span><span className="settings-chip-list">{row.roles.length ? row.roles.slice(0, 2).map((role) => <span key={role}>{role}</span>) : <small>Sin roles</small>}{row.roles.length > 2 ? <span>+{row.roles.length - 2}</span> : null}</span></div>)}{!visible.length && !loading ? <div className="clients-empty">No hay cuentas que coincidan con los filtros.</div> : null}</div>
      <div className="settings-pagination"><button className="secondary-button" disabled={page <= 1} onClick={() => setPage((value) => value - 1)} type="button">Anterior</button><span>Página {Math.min(page, pages)} de {pages}</span><button className="secondary-button" disabled={page >= pages} onClick={() => setPage((value) => value + 1)} type="button">Siguiente</button></div>
      {modal ? <UserModal accountType={modal.row.accountType} activity={activity} availableRoles={modal.row.accountType === 'internal' ? data.roles.filter((role) => role.is_active !== false) : []} form={form} isSubmitting={submitting} membership={modal.row.membership} mode={modal.mode} onChange={change} onClose={() => setModal(null)} onSubmit={submit} registration={modal.row.registration} /> : null}
    </>}
  </section>;
}
