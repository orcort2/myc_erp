// Pure helpers for the ERP password recovery screens (EMAIL-2).
export const PASSWORD_MIN_LENGTH = 8; // same policy as the backend (8-128)
export const PASSWORD_MAX_LENGTH = 128;

export const FORGOT_PASSWORD_PATH = '/forgot-password';
export const RESET_PASSWORD_PATH = '/reset-password';

export const FORGOT_PASSWORD_CONFIRMATION =
  'Si existe una cuenta asociada a ese correo, te enviaremos instrucciones para restablecer tu contraseña.';
export const RESET_PASSWORD_SUCCESS = 'Tu contraseña fue actualizada. Inicia sesión nuevamente.';

// The app path may carry a fragment (e.g. "/reset-password#token=..."); route on the pathname only.
export function recoveryRoute(path) {
  return String(path ?? '').split('#')[0].split('?')[0];
}

export function isPasswordRecoveryPath(path) {
  const route = recoveryRoute(path);
  return route === FORGOT_PASSWORD_PATH || route === RESET_PASSWORD_PATH;
}

// The reset token travels in the URL fragment ("#token=..."), which browsers never
// send to the server, so it cannot land in access logs or proxies.
export function readResetToken(hash) {
  const raw = String(hash ?? '');
  if (raw.startsWith('?')) return ''; // query strings are never a valid carrier
  const token = new URLSearchParams(raw.replace(/^#/, '')).get('token');
  return token ? token.trim() : '';
}

export function validateNewPassword(password, confirmation) {
  if (password.length < PASSWORD_MIN_LENGTH) {
    return `La contraseña debe tener al menos ${PASSWORD_MIN_LENGTH} caracteres.`;
  }
  if (password.length > PASSWORD_MAX_LENGTH) {
    return `La contraseña no puede exceder ${PASSWORD_MAX_LENGTH} caracteres.`;
  }
  if (password !== confirmation) {
    return 'Las contraseñas no coinciden.';
  }
  return '';
}
