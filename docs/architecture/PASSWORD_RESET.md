# Recuperación de contraseña del ERP (EMAIL-2)

> Estado: EN REVISIÓN (sin commit). Alcance: cuentas **internas** (`account_type=internal`, `status=active`, `is_active`). Portal del Cliente queda fuera de esta fase.

## Endpoints públicos (`/api/auth`)

| Endpoint | Request | Respuesta |
|---|---|---|
| `POST /forgot-password` | `{ "email": EmailStr }` | `200 {"message": "Si existe una cuenta elegible, recibirás un correo con instrucciones."}` **siempre** (existente, inexistente, inactiva, no elegible, en cooldown). |
| `POST /reset-password` | `{ "token": str(1..512), "new_password": str(8..128) }` | `200 {"message": "Tu contraseña fue actualizada. Inicia sesión nuevamente."}` (sin tokens: no hay auto-login). Token inválido/usado/revocado/expirado o cuenta no elegible → `400` con un único mensaje. Política de contraseña = `UserRegister.password` (8–128). |

## Token

`password_reset_tokens(user_id, token_hash UNIQUE, expires_at, used_at, revoked_at)`. Token = `secrets.token_urlsafe(48)`; sólo se persiste SHA-256. TTL 30 min (`PASSWORD_RESET_EXPIRE_MINUTES`). One-shot: el consumo es un `UPDATE ... WHERE used_at IS NULL AND revoked_at IS NULL` verificado por `rowcount` (más `SELECT ... FOR UPDATE`), por lo que dos requests concurrentes no pueden consumirlo ambos. Una nueva solicitud revoca los tokens utilizables anteriores. Cooldown persistente de 60 s por cuenta (`PASSWORD_RESET_COOLDOWN_SECONDS`): en cooldown no se crea token ni correo y la respuesta pública no cambia.

## Flujo y transacciones

1. `forgot-password`: bloquea el usuario, revoca tokens previos, crea el nuevo, audita (`auth.password_reset.requested`, sólo para cuentas elegibles) y **hace COMMIT**.
2. Después de la respuesta, una tarea de fondo con su propia sesión envía el correo con `EmailService` (`password_reset`). Un fallo SMTP no revierte el token; `EmailDelivery` registra el resultado. El snapshot del correo redacta `reset_url`; los correos con enlace de un solo uso no se reintentan (EMAIL-1).
3. `reset-password`: valida, consume el token, cambia la contraseña, `password_changed_at=now`, `auth_version+=1`, limpia lockout, `must_change_password=false`, revoca los demás tokens, revoca `MobileAuthSession` y `MobileBiometricCredential` activas, audita (`auth.password_reset.completed`, `auth.sessions.revoked`) y hace COMMIT. **No** revoca `MobileTrustedDevice`.

## auth_version (sesiones web)

`users.auth_version INTEGER NOT NULL DEFAULT 1`. Los JWT web (access y refresh) llevan el claim `auth_version`. `services/auth.py::token_matches_auth_version` es la única regla: claim ausente (JWT legacy) = 1, válido sólo mientras `user.auth_version == 1`; tras un reset (≥2) todo JWT anterior responde 401. Se aplica en `resolve_access_token_user`, `refresh_tokens` y en el camino de compatibilidad Mobile de tokens ERP legacy (`auth_context=internal`). Los tokens `mobile_internal` quedan atados a su `MobileAuthSession`, que el reset revoca.

## URL pública

`PUBLIC_APP_BASE_URL` (nuevo) con fallback a `PORTAL_PUBLIC_BASE_URL` (legacy); `Settings.effective_public_base_url`. Sin default productivo; en desarrollo cae a `http://localhost:5173`. En producción con `EMAIL_ENABLED=true` la configuración exige una URL `https://`; si aun así falta, no se envía el correo (se registra un error sin token) y la respuesta pública no cambia. El enlace es `{base}/reset-password#token=...`: el token va en el **fragmento**, que el navegador nunca envía al servidor, por lo que no llega a access logs, proxy, Cloudflare ni observabilidad (un query string sí viajaría en el GET inicial). No usar `?token=`.

## Frontend

`/forgot-password` y `/reset-password` son rutas públicas (`pages/ForgotPasswordPage.jsx`, `pages/ResetPasswordPage.jsx`, helpers en `utils/passwordReset.js`). El token se lee una vez de `window.location.hash`, se retira de la barra de direcciones con `history.replaceState` y vive sólo en memoria (sin storage, sin logs, sin volver a query params); únicamente viaja en el cuerpo del `POST /api/auth/reset-password`. Un `?token=` en la URL se ignora. Tras el éxito se muestra "Iniciar sesión"; no hay auto-login.

## Limitaciones

Sin rate limiting anónimo/IP (gateway); el cooldown es por cuenta. El envío es por tarea de fondo del proceso (se pierde si el proceso muere entre el commit y el envío; el usuario puede volver a solicitar). Diferencias de latencia entre cuentas existentes e inexistentes son mínimas pero no nulas.
