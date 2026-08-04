import React, { useEffect, useState } from 'react';

import BrandLockup from '../components/BrandLockup.jsx';
import { acceptPortalInvitation, createPortalRegistration, portalLogin, validatePortalInvitation, verifyPortalEmail } from '../services/api.js';
import { navigate } from '../utils/routing.js';

export default function PortalAccessPage({ path, onAuthenticated }) {
  const invitationToken = path.startsWith('/portal/invitacion/') ? decodeURIComponent(path.split('/').pop()) : '';
  const verificationToken = new URLSearchParams(window.location.search).get('token');
  const mode = invitationToken ? 'invitation' : path === '/portal/registro' ? 'register' : path === '/portal/verificar-correo' ? 'verify' : 'login';
  const [form, setForm] = useState({ username: '', email: '', full_name: '', password: '', password_confirmation: '', declared_company_name: '', declared_company_rfc: '' });
  const [invitation, setInvitation] = useState(null);
  const [error, setError] = useState('');
  const [notice, setNotice] = useState('');
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    if (invitationToken) validatePortalInvitation(invitationToken).then(setInvitation).catch((e) => setError(e.message));
    if (mode === 'verify' && verificationToken) verifyPortalEmail(verificationToken).then((r) => setNotice(r.message)).catch((e) => setError(e.message));
  }, [invitationToken, mode, verificationToken]);

  function change(event) { setForm((current) => ({ ...current, [event.target.name]: event.target.value })); }
  async function submit(event) {
    event.preventDefault(); setBusy(true); setError(''); setNotice('');
    try {
      if (mode === 'login') {
        const user = await portalLogin(form.email, form.password); onAuthenticated(user); navigate('/portal');
      } else if (mode === 'register') {
        const result = await createPortalRegistration({ ...form, declared_company_rfc: form.declared_company_rfc || null }); setNotice(result.message);
      } else if (mode === 'invitation') {
        const result = await acceptPortalInvitation(invitationToken, { username: form.username, full_name: form.full_name, password: form.password }); setNotice(result.message); setTimeout(() => navigate('/portal/login'), 800);
      }
    } catch (e) { setError(e.message); } finally { setBusy(false); }
  }

  return <main className="auth-screen"><section className="auth-panel" aria-label="Acceso al Portal del Cliente"><BrandLockup subtitle="Portal de clientes" /><div className="auth-heading"><p>Acceso independiente</p><h1>{mode === 'register' ? 'Crear cuenta del portal' : mode === 'invitation' ? 'Aceptar invitación' : mode === 'verify' ? 'Verificar correo' : 'Ingresar al portal'}</h1></div>{invitation ? <p>Invitación para {invitation.email} · {invitation.client_name}</p> : null}{mode !== 'verify' ? <form className="auth-form" onSubmit={submit}>{mode !== 'login' ? <><label>Usuario<input name="username" required onChange={change} value={form.username} /></label><label>Nombre completo<input name="full_name" required onChange={change} value={form.full_name} /></label></> : null}{mode === 'register' ? <><label>Correo<input name="email" type="email" required onChange={change} value={form.email} /></label><label>Empresa<input name="declared_company_name" required onChange={change} value={form.declared_company_name} /></label><label>RFC (opcional)<input name="declared_company_rfc" onChange={change} value={form.declared_company_rfc} /></label></> : null}{mode === 'login' ? <label>Usuario o correo<input name="email" required onChange={change} value={form.email} /></label> : null}<label>Contraseña<input name="password" type="password" minLength="8" required onChange={change} value={form.password} /></label>{mode === 'register' ? <label>Confirmar contraseña<input name="password_confirmation" type="password" minLength="8" required onChange={change} value={form.password_confirmation} /></label> : null}<button className="primary-button" disabled={busy} type="submit">{busy ? 'Procesando…' : 'Continuar'}</button></form> : null}{error ? <div className="form-error">{error}</div> : null}{notice ? <div className="form-notice">{notice}</div> : null}<button className="text-button" onClick={() => navigate(mode === 'login' ? '/portal/registro' : '/portal/login')} type="button">{mode === 'login' ? 'Crear cuenta del portal' : 'Volver al acceso'}</button></section></main>;
}
