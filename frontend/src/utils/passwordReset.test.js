import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import test from 'node:test';

import {
  FORGOT_PASSWORD_CONFIRMATION,
  RESET_PASSWORD_SUCCESS,
  isPasswordRecoveryPath,
  recoveryRoute,
  readResetToken,
  validateNewPassword
} from './passwordReset.js';

const source = (relative) => readFileSync(new URL(relative, import.meta.url), 'utf8');
const login = source('../pages/LoginPage.jsx');
const forgot = source('../pages/ForgotPasswordPage.jsx');
const reset = source('../pages/ResetPasswordPage.jsx');
const app = source('../pages/App.jsx');
const api = source('../services/api.js');

test('login offers the forgot-password link that navigates to /forgot-password', () => {
  assert.match(login, /¿Olvidaste tu contraseña\?/);
  assert.match(login, /navigate\('\/forgot-password'\)/);
});

test('recovery routes are public and routed before the session gate', () => {
  assert.equal(isPasswordRecoveryPath('/forgot-password'), true);
  assert.equal(isPasswordRecoveryPath('/reset-password'), true);
  assert.equal(isPasswordRecoveryPath('/dashboard'), false);
  assert.match(app, /isPasswordRecoveryPath\(path\)/);
  assert.match(app, /recoveryRoute\(path\) === '\/forgot-password'[\s\S]*<ForgotPasswordPage/);
  assert.match(app, /recoveryRoute\(path\) === '\/reset-password'[\s\S]*<ResetPasswordPage/);
});

test('forgot request posts only the email and shows the generic confirmation', () => {
  assert.match(api, /request\('\/auth\/forgot-password', \{ method: 'POST', body: JSON\.stringify\(\{ email \}\) \}\)/);
  assert.match(forgot, /requestPasswordReset\(email\.trim\(\)\)/);
  assert.match(forgot, /FORGOT_PASSWORD_CONFIRMATION/);
  assert.match(FORGOT_PASSWORD_CONFIRMATION, /^Si existe una cuenta asociada a ese correo/);
  // success and unknown-account paths must be identical: nothing inspects the response
  assert.doesNotMatch(forgot, /requestPasswordReset\([^)]*\)\s*\.then\(\s*\(?\s*\w+/);
});

test('reset reads the token from the URL fragment, never the query, and cleans the address bar', () => {
  assert.equal(readResetToken('#token=abc123'), 'abc123');
  assert.equal(readResetToken('token=abc123'), 'abc123');
  assert.equal(readResetToken('?token=abc123'), '');
  assert.equal(readResetToken('#other=1'), '');
  assert.equal(readResetToken(''), '');
  assert.match(reset, /readResetToken\(window\.location\.hash\)/);
  assert.doesNotMatch(reset, /readResetToken\(window\.location\.search\)/);
  assert.match(reset, /window\.history\.replaceState\(\{\}, '', RESET_PASSWORD_PATH\)/);
  // the cleaned URL carries neither fragment nor query
  assert.doesNotMatch(reset, /RESET_PASSWORD_PATH\s*\+|\?token|#token/);
});

test('fragment links still route to the reset page', () => {
  assert.equal(recoveryRoute('/reset-password#token=abc'), '/reset-password');
  assert.equal(isPasswordRecoveryPath('/reset-password#token=abc'), true);
  assert.equal(isPasswordRecoveryPath('/forgot-password'), true);
  assert.match(app, /recoveryRoute\(path\) === '\/reset-password'/);
});

test('the token only goes out in the POST body, never in a URL', () => {
  const resetCall = api.slice(api.indexOf('export function resetPassword'), api.indexOf('export async function getRegistrationStatus'));
  assert.match(resetCall, /request\('\/auth\/reset-password', \{/);
  assert.match(resetCall, /body: JSON\.stringify\(\{ token, new_password: newPassword \}\)/);
  assert.doesNotMatch(resetCall, /\?token|#token|\$\{token\}/);
  assert.doesNotMatch(reset, /location\.search|URLSearchParams|\?token/);
});

test('mismatched or short passwords block submit', () => {
  assert.match(validateNewPassword('abcdefgh', 'abcdefgX'), /no coinciden/);
  assert.match(validateNewPassword('short', 'short'), /al menos 8/);
  assert.match(validateNewPassword('x'.repeat(129), 'x'.repeat(129)), /128/);
  assert.equal(validateNewPassword('abcdefgh', 'abcdefgh'), '');
  assert.match(reset, /validateNewPassword\(password, confirmation\)[\s\S]*return;/);
});

test('reset success returns to login without auto-login', () => {
  assert.match(api, /new_password: newPassword/);
  assert.match(RESET_PASSWORD_SUCCESS, /Inicia sesión nuevamente/);
  assert.match(reset, /Iniciar sesión/);
  assert.match(reset, /navigate\('\/login'\)/);
  assert.doesNotMatch(reset, /saveTokens|onAuthenticated|getCurrentUser/);
  const resetCall = api.slice(api.indexOf('export function resetPassword'), api.indexOf('export async function getRegistrationStatus'));
  assert.doesNotMatch(resetCall, /saveTokens/);
});

test('invalid, expired or used links surface the backend message and offer a new request', () => {
  assert.match(reset, /setError\(requestError\.message\)/);
  assert.match(reset, /navigate\('\/forgot-password'\)/);
});

test('the token is never persisted or logged', () => {
  for (const page of [forgot, reset]) {
    assert.doesNotMatch(page, /localStorage|sessionStorage|console\./);
  }
  assert.doesNotMatch(source('./passwordReset.js'), /localStorage|sessionStorage|console\./);
});
