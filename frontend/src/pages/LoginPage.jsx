import React, { useEffect, useState } from 'react';

import BrandLockup from '../components/BrandLockup.jsx';
import { getRegistrationStatus, login, register } from '../services/api.js';
import { navigate } from '../utils/routing.js';
import { isClientPortalUser } from '../utils/accessControl.js';

function LoginPage({ onAuthenticated }) {
  const [mode, setMode] = useState('login');
  const [email, setEmail] = useState('');
  const [fullName, setFullName] = useState('');
  const [password, setPassword] = useState('');
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState('');
  const [hasRegisteredUsers, setHasRegisteredUsers] = useState(null);

  useEffect(() => {
    let isMounted = true;

    getRegistrationStatus()
      .then((status) => {
        if (isMounted) setHasRegisteredUsers(Boolean(status?.has_users));
      })
      .catch(() => {
        // Keep the registration link available if the status check is temporarily unavailable.
        if (isMounted) setHasRegisteredUsers(true);
      });

    return () => {
      isMounted = false;
    };
  }, []);

  async function handleSubmit(event) {
    event.preventDefault();
    setError('');
    setIsSubmitting(true);

    try {
      const user =
        mode === 'login'
          ? await login(email, password)
          : await register({ email, fullName, password });
      onAuthenticated(user);
      navigate(isClientPortalUser(user) ? '/portal' : '/dashboard');
    } catch (requestError) {
      setError(requestError.message);
    } finally {
      setIsSubmitting(false);
    }
  }

  return (
    <main className="auth-screen">
      <section className="auth-panel" aria-label="Acceso MYC SYSTEM">
        <BrandLockup subtitle="Acceso principal" />

        <div className="auth-heading">
          <p>{mode === 'login' ? 'Acceso seguro' : 'Primer acceso'}</p>
          <h1>{mode === 'login' ? 'Iniciar sesion' : 'Crear usuario'}</h1>
        </div>

        <form className="auth-form" onSubmit={handleSubmit}>
          {mode === 'register' ? (
            <label>
              Nombre
              <input
                autoComplete="name"
                onChange={(event) => setFullName(event.target.value)}
                required
                type="text"
                value={fullName}
              />
            </label>
          ) : null}

          <label>
            Correo
            <input
              autoComplete="email"
              onChange={(event) => setEmail(event.target.value)}
              required
              type="email"
              value={email}
            />
          </label>

          <label>
            Contrasena
            <input
              autoComplete={mode === 'login' ? 'current-password' : 'new-password'}
              minLength={8}
              onChange={(event) => setPassword(event.target.value)}
              required
              type="password"
              value={password}
            />
          </label>

          {error ? <div className="form-error">{error}</div> : null}

          <button className="primary-button" disabled={isSubmitting} type="submit">
            {isSubmitting ? 'Validando...' : mode === 'login' ? 'Entrar' : 'Crear usuario'}
          </button>
        </form>

        {hasRegisteredUsers === false || mode === 'register' ? <button
          className="text-button"
          onClick={() => {
            setError('');
            setMode(mode === 'login' ? 'register' : 'login');
          }}
          type="button"
        >
          {mode === 'login' ? 'Crear primer usuario' : 'Ya tengo usuario'}
        </button> : null}
        {mode === 'login' ? <button className="text-button" onClick={() => navigate('/portal/login')} type="button">Acceso al Portal del Cliente</button> : null}
      </section>
    </main>
  );
}



export default LoginPage;
