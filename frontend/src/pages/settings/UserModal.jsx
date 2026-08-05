import React, { useEffect, useMemo, useState } from 'react';

const TABS = ['Perfil', 'Acceso', 'Roles y permisos', 'Organización', 'Comunicaciones', 'Actividad', 'Seguridad'];

function Field({ label, children }) {
  return <label className="field-label">{label}{children}</label>;
}

export default function UserModal({ accountType = 'internal', activity = [], availableRoles = [], form, isSubmitting, membership = null, mode, onChange, onClose, onSubmit, registration = null }) {
  const [tab, setTab] = useState('Perfil');
  const [dirty, setDirty] = useState(false);
  const portal = accountType === 'client_portal';
  const selectedRoles = form.role_names ?? [];
  const effectivePermissions = useMemo(() => {
    if (!portal) return [];
    return membership?.effective_permissions ?? [];
  }, [membership, portal]);

  useEffect(() => {
    function escape(event) {
      if (event.key === 'Escape' && (!dirty || window.confirm('Hay cambios sin guardar. ¿Cerrar de todos modos?'))) onClose();
    }
    window.addEventListener('keydown', escape);
    return () => window.removeEventListener('keydown', escape);
  }, [dirty, onClose]);

  function change(event) { setDirty(true); onChange(event); }
  function close() { if (!dirty || window.confirm('Hay cambios sin guardar. ¿Cerrar de todos modos?')) onClose(); }
  function backdrop(event) { if (event.target === event.currentTarget && !dirty && !isSubmitting) onClose(); }
  function toggleRole(roleName) {
    setDirty(true);
    onChange({ target: { name: 'role_names', type: 'role-list', value: selectedRoles.includes(roleName) ? selectedRoles.filter((item) => item !== roleName) : [...selectedRoles, roleName] } });
  }

  return <div className="modal-backdrop" onMouseDown={backdrop}>
    <div aria-modal="true" className="client-modal settings-user-modal settings-user-modal--complete" onMouseDown={(event) => event.stopPropagation()} role="dialog">
      <header className="section-heading settings-user-modal__header"><div><p>{portal ? 'Portal del Cliente' : 'Usuarios internos'}</p><h2>{mode === 'create' ? 'Nuevo usuario' : form.full_name || 'Detalle de usuario'}</h2><small>{portal ? 'Cuenta externa y organización vinculada' : `@${form.username || 'nuevo'}`}</small></div><button aria-label="Cerrar" className="modal-close-button" onClick={close} type="button">×</button></header>
      <div className="client-modal-tabs settings-user-tabs" role="tablist">{TABS.map((item) => <button className={tab === item ? 'client-modal-tab is-active' : 'client-modal-tab'} key={item} onClick={() => setTab(item)} role="tab" type="button">{item}</button>)}</div>
      <form className="settings-user-form settings-user-modal__body" onSubmit={onSubmit}>
        {tab === 'Perfil' ? <div className="settings-user-grid">
          <Field label="Nombre completo"><input className="text-input" disabled={portal} name="full_name" onChange={change} value={form.full_name ?? ''} /></Field>
          <Field label="Nombre de usuario"><input className="text-input" disabled={portal} name="username" onChange={change} required value={form.username ?? ''} /></Field>
          <Field label="Correo"><input className="text-input" disabled={portal} name="email" onChange={change} type="email" value={form.email ?? ''} /></Field>
          <Field label="Teléfono"><input className="text-input" disabled={portal} name="phone" onChange={change} value={form.phone ?? registration?.contact_phone ?? ''} /></Field>
          <Field label="Puesto"><input className="text-input" disabled={portal} name="job_title" onChange={change} value={form.job_title ?? registration?.job_title ?? ''} /></Field>
          <Field label="Área"><input className="text-input" disabled={portal} name="area" onChange={change} value={form.area ?? ''} /></Field>
          <Field label="Idioma"><select className="settings-role-select" disabled={portal} name="language" onChange={change} value={form.language ?? 'es-MX'}><option value="es-MX">Español (México)</option><option value="en-US">English (US)</option></select></Field>
          <Field label="Zona horaria"><input className="text-input" disabled={portal} name="timezone" onChange={change} value={form.timezone ?? 'America/Mexico_City'} /></Field>
          {mode === 'create' ? <Field label="Contraseña inicial"><input className="text-input" minLength="8" name="password" onChange={change} required type="password" value={form.password ?? ''} /></Field> : null}
        </div> : null}

        {tab === 'Acceso' ? <div className="settings-detail-grid">
          <span><small>Tipo de cuenta</small><strong>{portal ? 'Portal del Cliente' : 'Interna'}</strong></span><span><small>Estado de cuenta</small><strong>{form.status ?? (form.is_active ? 'active' : 'disabled')}</strong></span><span><small>Activo</small><strong>{form.is_active ? 'Sí' : 'No'}</strong></span><span><small>Correo verificado</small><strong>{form.email_verified_at ? 'Sí' : 'No'}</strong></span><span><small>Último acceso</small><strong>{form.last_login_at ? new Date(form.last_login_at).toLocaleString() : 'Sin acceso'}</strong></span><span><small>Intentos fallidos</small><strong>{form.failed_login_attempts ?? 0}</strong></span><span><small>Bloqueado hasta</small><strong>{form.locked_until ? new Date(form.locked_until).toLocaleString() : 'No'}</strong></span><span><small>Último cambio de contraseña</small><strong>{form.password_changed_at ? new Date(form.password_changed_at).toLocaleString() : 'Sin registro'}</strong></span>
          {!portal && mode === 'edit' ? <><label className="settings-checkbox"><input checked={Boolean(form.is_active)} name="is_active" onChange={change} type="checkbox" />Cuenta habilitada</label><label className="settings-checkbox"><input checked={Boolean(form.must_change_password)} name="must_change_password" onChange={change} type="checkbox" />Forzar cambio de contraseña</label></> : null}
        </div> : null}

        {tab === 'Roles y permisos' ? <div><p className="settings-tab-help">{portal ? 'Los permisos efectivos son la unión de los roles de esta membresía.' : 'Selecciona uno o varios roles internos. Los roles del portal se administran por membresía.'}</p><div className="settings-role-checklist">{availableRoles.map((role) => { const code = portal ? role.code : role.name; return <label className="settings-checkbox" key={role.id}><input checked={selectedRoles.includes(code)} disabled={portal} onChange={() => toggleRole(code)} type="checkbox" /><span><strong>{role.name}</strong><small>{role.description}</small></span></label>; })}</div>{portal ? <div className="settings-chip-list">{effectivePermissions.map((permission) => <span key={permission}>{permission}</span>)}</div> : null}</div> : null}

        {tab === 'Organización' ? portal ? <div className="settings-detail-grid"><span><small>Empresa declarada</small><strong>{registration?.declared_company_name || 'No disponible'}</strong></span><span><small>RFC declarado</small><strong>{registration?.declared_company_rfc || 'No disponible'}</strong></span><span><small>Cliente vinculado</small><strong>{membership?.client_name || membership?.client_id || 'Sin vínculo'}</strong></span><span><small>Razón social</small><strong>{membership?.client_legal_name || 'No disponible'}</strong></span><span><small>Nombre comercial</small><strong>{membership?.client_commercial_name || 'No disponible'}</strong></span><span><small>Estado de membresía</small><strong>{membership?.status || 'Sin membresía'}</strong></span><span><small>Contacto principal</small><strong>{membership?.is_primary_contact ? 'Sí' : 'No'}</strong></span><span><small>Fecha de vinculación</small><strong>{membership?.approved_at ? new Date(membership.approved_at).toLocaleString() : 'Sin vínculo'}</strong></span><span><small>Aprobado por</small><strong>{membership?.approved_by_name || membership?.approved_by || 'No disponible'}</strong></span><span><small>Origen</small><strong>{membership?.source || 'Registro público pendiente'}</strong></span></div> : <div className="clients-empty">La organización sólo aplica a cuentas del Portal del Cliente.</div> : null}
        {tab === 'Comunicaciones' ? <div className="clients-empty"><strong>Comunicaciones bidireccionales no disponibles</strong><p>Esta pestaña no simula conversaciones. La capacidad permanece fuera del alcance actual.</p></div> : null}
        {tab === 'Actividad' ? <div className="settings-activity-list">{activity.length ? activity.map((item) => <article key={item.id}><strong>{item.action}</strong><span>{item.comment || item.entity}</span><small>{new Date(item.created_at).toLocaleString()}</small></article>) : <div className="clients-empty">No hay actividad disponible para esta cuenta.</div>}</div> : null}
        {tab === 'Seguridad' ? <div className="settings-detail-grid"><span><small>Estado</small><strong>{form.status ?? 'pending'}</strong></span><span><small>Correo verificado</small><strong>{form.email_verified_at ? 'Sí' : 'No'}</strong></span><span><small>Intentos fallidos</small><strong>{form.failed_login_attempts ?? 0}</strong></span><span><small>Bloqueado hasta</small><strong>{form.locked_until ? new Date(form.locked_until).toLocaleString() : 'No'}</strong></span><span><small>Sesiones y dispositivos</small><strong>No se almacenan</strong></span><span><small>MFA</small><strong>No disponible</strong></span></div> : null}
        <footer className="client-form__actions--modal"><button className="secondary-button" onClick={close} type="button">Cerrar</button>{!portal ? <button className="primary-button" disabled={isSubmitting || !selectedRoles.length} type="submit">{isSubmitting ? 'Guardando…' : mode === 'create' ? 'Crear usuario' : 'Guardar cambios'}</button> : null}</footer>
      </form>
    </div>
  </div>;
}
