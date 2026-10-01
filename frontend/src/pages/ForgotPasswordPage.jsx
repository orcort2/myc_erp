import React, { useState } from 'react';

import BrandLockup from '../components/BrandLockup.jsx';
import { requestPasswordReset } from '../services/api.js';
import { navigate } from '../utils/routing.js';
import { FORGOT_PASSWORD_CONFIRMATION } from '../utils/passwordReset.js';

function ForgotPasswordPage() {
  const [email, setEmail] = useState('');
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState('');
  const [sent, setSent] = useState(false);

  async function handleSubmit(event) {
    event.preventDefault();
    setError('');
    setIsSubmitting(true);

    try {
      await requestPasswordReset(email.trim());
      // Same confirmation whether or not the account exists (anti-enumeration).
      setSent(true);
    } catch (requestError) {
      setError(requestError.message);
    } finally {
      setIsSubmitting(false);
    }
  }

  return (
    <main className="auth-screen">
      <section className="auth-panel" aria-label="Recuperar contraseña">
        <BrandLockup subtitle="Acceso principal" />

        <div className="auth-heading">
          <p>Recuperación</p>
          <h1>¿Olvidaste tu contraseña?</h1>
        </div>

        {sent ? (
          <div className="form-notice">{FORGOT_PASSWORD_CONFIRMATION}</div>
        ) : (
          <form className="auth-form" onSubmit={handleSubmit}>
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

            {error ? <div className="form-error">{error}</div> : null}

            <button className="primary-button" disabled={isSubmitting} type="submit">
              {isSubmitting ? 'Enviando...' : 'Enviar instrucciones'}
            </button>
          </form>
        )}

        <button className="text-button" onClick={() => navigate('/login')} type="button">
          Volver al acceso
        </button>
      </section>
    </main>
  );
}

export default ForgotPasswordPage;
