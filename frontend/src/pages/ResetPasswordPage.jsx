import React, { useState } from 'react';

import BrandLockup from '../components/BrandLockup.jsx';
import { resetPassword } from '../services/api.js';
import { navigate } from '../utils/routing.js';
import {
  RESET_PASSWORD_PATH,
  RESET_PASSWORD_SUCCESS,
  readResetToken,
  validateNewPassword
} from '../utils/passwordReset.js';

function ResetPasswordPage() {
  // The token lives only in component state: it is read once from the URL
  // fragment, removed from the address bar and never written to any storage.
  const [token] = useState(() => {
    const value = readResetToken(window.location.hash);
    if (window.location.hash) {
      window.history.replaceState({}, '', RESET_PASSWORD_PATH);
    }
    return value;
  });
  const [password, setPassword] = useState('');
  const [confirmation, setConfirmation] = useState('');
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState('');
  const [done, setDone] = useState(false);

  async function handleSubmit(event) {
    event.preventDefault();
    const validationError = validateNewPassword(password, confirmation);
    if (validationError) {
      setError(validationError);
      return;
    }
    setError('');
    setIsSubmitting(true);

    try {
      await resetPassword(token, password);
      setPassword('');
      setConfirmation('');
      setDone(true);
    } catch (requestError) {
      setError(requestError.message);
    } finally {
      setIsSubmitting(false);
    }
  }

  return (
    <main className="auth-screen">
      <section className="auth-panel" aria-label="Restablecer contraseña">
        <BrandLockup subtitle="Acceso principal" />

        <div className="auth-heading">
          <p>Recuperación</p>
          <h1>Restablecer contraseña</h1>
        </div>

        {done ? (
          <>
            <div className="form-notice">{RESET_PASSWORD_SUCCESS}</div>
            <button className="primary-button" onClick={() => navigate('/login')} type="button">
              Iniciar sesión
            </button>
          </>
        ) : !token ? (
          <>
            <div className="form-error">El enlace no es válido o expiró. Solicita uno nuevo.</div>
            <button className="text-button" onClick={() => navigate('/forgot-password')} type="button">
              Solicitar un nuevo enlace
            </button>
          </>
        ) : (
          <form className="auth-form" onSubmit={handleSubmit}>
            <label>
              Nueva contraseña
              <input
                autoComplete="new-password"
                maxLength={128}
                minLength={8}
                onChange={(event) => setPassword(event.target.value)}
                required
                type="password"
                value={password}
              />
            </label>

            <label>
              Confirmar contraseña
              <input
                autoComplete="new-password"
                maxLength={128}
                minLength={8}
                onChange={(event) => setConfirmation(event.target.value)}
                required
                type="password"
                value={confirmation}
              />
            </label>

            {error ? <div className="form-error">{error}</div> : null}

            <button className="primary-button" disabled={isSubmitting} type="submit">
              {isSubmitting ? 'Guardando...' : 'Guardar contraseña'}
            </button>
          </form>
        )}

        {!done ? (
          <button className="text-button" onClick={() => navigate('/login')} type="button">
            Volver al acceso
          </button>
        ) : null}
      </section>
    </main>
  );
}

export default ResetPasswordPage;
