> Tipo: Cierre técnico de implementación acotada
>
> Fecha: 2026-09-21
>
> No declara SELLADO el módulo Mobile ni sustituye PROJECT_STATUS.

# BIOMETRIC-2 — Biometric login

## Estado inicial

Precondición ejecutada antes de modificar archivos: `git status`, rama, HEAD,
`origin/main`, diff, staged diff y archivos no versionados en el entorno de
este trabajo. La rama y el HEAD indicados originalmente
(`feat/mobile-session-authority-biometric-1` en
`d94e35ae5a0710c9f31adb0a0c8f3299a4b603c9`) no existían todavía en el clon
inicial de este entorno remoto; se detuvo el trabajo, se reportó la
incompatibilidad y, siguiendo instrucción explícita del usuario, se hizo
`git fetch origin` (la rama sí existía en `origin`, sólo faltaba en el clon
inicial) y `git switch` a ella. Confirmado entonces: rama
`feat/mobile-session-authority-biometric-1`, HEAD
`d94e35ae5a0710c9f31adb0a0c8f3299a4b603c9`, worktree limpio, y presentes
`mobile_trusted_device.py`, `mobile_auth_session.py`, `refresh_credentials.py`
y `sessionVersion`/single-flight en `AuthProvider.tsx`. Se creó
`feat/mobile-biometric-login-2` desde ese punto. Alembic inicial: current/head
únicos en `b10a1c202601`.

## Arquitectura implementada

- **Credencial biométrica opaca:** `MobileBiometricCredential`
  (`mobile_biometric_credentials`) es una autoridad server-side separada de
  `MobileAuthSession`: `secrets.token_urlsafe(48)` (espacio de credencial
  propio, nunca el mismo token que un refresh), SHA-256 UNIQUE, `user_id` +
  `device_id` (FK a `MobileTrustedDevice` existente; nunca crea dispositivo),
  `expires_at` (90 días vía `settings.mobile_biometric_credential_expire_days`,
  TTL independiente del refresh), `revoked_at` y `password_changed_at_snapshot`.
  No guarda rostro, huella, plantilla biométrica, clave pública/privada ni
  token nativo de Face ID/Touch ID.
- **Enroll:** requiere `MobileSecurityContext` con `mobile_session_id` (access
  Mobile vigente). Resuelve el dispositivo de la sesión actual, revoca (UPDATE
  dirigido) la credencial activa previa de ese mismo usuario+dispositivo,
  genera y persiste sólo el hash de una nueva, y devuelve el opaco en texto
  plano una única vez.
- **Exchange:** no requiere access previo (misma naturaleza pública que
  login). Hashea la credencial recibida, la localiza con
  `SELECT ... FOR UPDATE` (serializa contra un `DELETE` concurrente), valida
  no revocada/no expirada, dispositivo activo/no revocado, usuario
  activo/status/`mobile.access` vigente y `password_changed_at` no posterior
  al snapshot. Reconstruye el `MobileSecurityContext` reutilizando
  `_internal_context`/`_client_context`/`_ensure_mobile_access` de
  `core/mobile/security.py` (no reimplementa esa lógica) y crea una
  `MobileAuthSession` nueva con `_new_session` sobre el `MobileTrustedDevice`
  ya asociado a la credencial; nunca sobre uno nuevo. El payload no admite
  `device` (`extra="forbid"` en el schema): un intento de enviarlo devuelve
  422 antes de tocar ninguna autoridad.
- **Delete:** revoca sólo la credencial activa del usuario+dispositivo del
  contexto actual (otras instalaciones del mismo usuario no se ven afectadas).
  No revoca la `MobileAuthSession` actual.
- PushDevice nunca se consulta como autoridad en ninguno de los tres
  endpoints (probado explícitamente).

### Mobile

- **Servicio nativo** (`src/services/biometric-auth.ts`): `hasHardwareAsync`
  + `isEnrolledAsync` + `supportedAuthenticationTypesAsync` de
  `expo-local-authentication` determinan `available`/`enrolled`/`type`/`label`
  (`face_id`/`touch_id` en iOS según el tipo soportado, `fingerprint`/"Huella"
  para cualquier biometría fuerte en Android, `biometric`/`none` en el resto).
  `authenticateBiometric(reason)` llama `authenticateAsync` con
  `disableDeviceFallback: true` (ambas plataformas) y
  `biometricsSecurityLevel: 'strong'` (Android); nunca hay fallback silencioso
  a PIN/passcode del dispositivo.
- **Storage separado** (`src/storage/biometric-storage.ts`):
  `myc.biometric.profile.v1` (no protegido — sólo `user_id`/`email`/
  `full_name`/`biometric_label`, nunca password, para que el login muestre
  "Bienvenido, `<nombre>`" sin tocar el secreto) y
  `myc.biometric.credential.v1` (protegido con `requireAuthentication: true`
  + `keychainAccessible: WHEN_UNLOCKED_THIS_DEVICE_ONLY` de
  `expo-secure-store`: el sistema operativo exige biometría para leerlo).
  Por contrato propio de SecureStore, una lectura protegida resuelve `null`
  exactamente cuando no hay entrada o cuando el conjunto biométrico del
  dispositivo invalidó la entrada; una cancelación o fallo del prompt en
  cambio RECHAZA la promesa. `AuthProvider.biometricLogin()` distingue ambos
  casos: sólo el `null` limpia el enrolamiento.
- **AuthProvider:** agrega `biometricProfile`, `biometricAvailable`,
  `biometricLogin()`, `enableBiometric()`, `disableBiometric()` sin
  reescribir BIOMETRIC-1. `applySession(next, version)` es el único punto de
  autoridad de sesión: login por contraseña y login biométrico lo comparten,
  ambos con el mismo versionado/serialización de persistencia que ya existía.
  Mientras hay perfil biométrico local, `persistOperationalSession` deja de
  escribir el `TokenPair` en `myc.internal.session.v1`; el mount effect
  detecta el perfil primero y, si existe, nunca restaura sesión desde disco
  (cold start exige biometría). Sin perfil biométrico, el comportamiento
  BIOMETRIC-1 es exactamente el mismo (probado, ver Tests).
- **Login screen:** si hay perfil biométrico local muestra primero
  "Bienvenido, `<nombre>`" + botón "Ingresar con `<label>`" + "Usar otra
  cuenta" (nunca borra el enrolamiento, sólo cambia de vista). Tras un login
  por contraseña exitoso sin enrolamiento previo, si el dispositivo tiene
  hardware disponible y enrolado, ofrece el modal "Protege tu acceso a MYC"
  (Activar/Ahora no); nunca se activa automáticamente.
- **Home técnica:** agrega "Desactivar acceso biométrico en este dispositivo"
  junto a "Cerrar sesión" (visible sólo con perfil biométrico local); logout
  normal nunca la ejecuta.

## Migración

Archivo:
`backend/migrations/versions/9970e12e5f0d_biometric_2_add_mobile_biometric_.py`.
Revision `9970e12e5f0d`; down_revision `b10a1c202601`.

Crea `mobile_biometric_credentials`: FKs a `users`/`mobile_trusted_devices`
con `ondelete="CASCADE"`, `credential_hash` UNIQUE + índice, índices de
`user_id`/`device_id`/`expires_at`/`revoked_at`, timestamps con default.
Downgrade elimina la tabla. No se modificó ninguna migración histórica.

Upgrade/downgrade/upgrade probados contra PostgreSQL local (mismo motor que
`DATABASE_URL`, servido en este entorno); `alembic current` = `alembic heads`
= `9970e12e5f0d` tras el ciclo final.

## Contratos API

Prefijo `/api/mobile/v1/auth/biometric`:

| Endpoint | Auth | Cambio exacto |
| --- | --- | --- |
| POST `/enroll` | Access Mobile ligado a sesión | Revoca la credencial activa previa del mismo usuario+dispositivo; devuelve `{biometric_credential, expires_at}` una sola vez. |
| POST `/exchange` | Ninguna (pública, como login) | `{biometric_credential}` únicamente; `device` en el payload es 422. Devuelve `MobileTokenPair` nuevo sobre el mismo `MobileTrustedDevice`. |
| DELETE `/biometric` | Access Mobile ligado a sesión | Revoca sólo la credencial activa de usuario+dispositivo actuales; 204. No toca otras instalaciones ni la sesión actual. |

`exchange` devuelve 401 genérico para credencial inexistente/revocada/
expirada, dispositivo inactivo/revocado, usuario inactivo/status≠active o
password cambiado tras el snapshot; devuelve 403 si el usuario perdió
`mobile.access` (mismo contrato que el resto de la autoridad Mobile vía
`_ensure_mobile_access`, sin caso especial).

## Storage local (Mobile)

| Clave | Protegida | Contenido |
| --- | --- | --- |
| `myc.biometric.profile.v1` | No | `user_id`, `email`, `full_name`, `biometric_label` |
| `myc.biometric.credential.v1` | Sí (`requireAuthentication`) | Credencial opaca en texto plano local únicamente |

Nunca se guarda contraseña en ninguna de las dos. Sólo una cuenta biométrica
recordada por instalación (una clave de cada tipo); no hay selector
multi-cuenta en esta fase.

## Revocación

- **Backend:** `enroll` revoca automáticamente la credencial anterior del
  mismo usuario+dispositivo (reemplazo, no acumulación). `DELETE /biometric`
  revoca la activa del usuario+dispositivo del contexto actual solamente.
  `exchange` nunca revoca nada por sí mismo (sólo lee/valida).
- **Mobile:** `disableBiometric()` llama `DELETE /biometric` best-effort
  (captura el error de red) y SIEMPRE limpia ambas claves locales después,
  incluso si la llamada de red falla — ver TD-059 para el riesgo aceptado
  documentado. Un `401`/`403` de `exchange` (credencial inválida real) o una
  lectura de SecureStore que resuelve `null` (invalidación real del sistema
  operativo) limpian el enrolamiento local automáticamente.

## Comportamiento ante cambio de contraseña

`password_changed_at_snapshot` se congela en el momento del `enroll`. Si
`user.password_changed_at` es posterior (o existe mientras el snapshot es
`None`, es decir la contraseña cambió después de enrolar sin haber cambiado
antes), `exchange` rechaza con 401. El backend nunca actualiza el snapshot
automáticamente: el usuario debe iniciar sesión con contraseña y volver a
activar biometría, lo que genera un nuevo enroll con snapshot fresco.

## Política de logout

Cerrar sesión (`logout()`) nunca desactiva biometría: conserva perfil y
credencial locales (push deactivate → auth logout → limpieza local, mismo
orden que BIOMETRIC-1). Sólo la acción explícita "Desactivar acceso
biométrico en este dispositivo" limpia el enrolamiento, ver Revocación.

## Overscroll (Home técnica)

`myc-mobile/app/(technician)/index.tsx`: el `ScrollView` principal agrega
`bounces={false}`, `alwaysBounceVertical={false}` y `overScrollMode="never"`.
Sin cambios a módulos, permisos, navegación ni contenido de la Home.

## Límites y alcance NO implementado

Sin cambios a: admin lease de 15 minutos, step-up de infraestructura, SSH,
SQL Console, Infrastructure Broker, passkeys/WebAuthn, claves
públicas/privadas device-bound, terminal embebida, panel de dispositivos ni
selector multi-account biométrico. `PushDevice` no se usó como autoridad de
seguridad en ningún punto. No se tocó auth Web/Portal (sólo se registró un
nuevo endpoint público en el allowlist deny-by-default de
`api_access.py`, requerido por el propio guard transversal existente para
que `exchange` sea alcanzable sin token, igual que login/refresh). No se
guardó contraseña ni dato biométrico nuevo; no se envía biometría al backend
en ningún momento (sólo el resultado local de `authenticateAsync` decide si
se procede a `enroll`/lectura de SecureStore).

## Tests y validación

Entorno: venv dedicado (`/home/user/.venvs/myc_backend`, requirements del
repo) con PostgreSQL local levantado en este entorno remoto (no existía
`erp_myc` ni rol autenticable; se creó un rol/BD locales sólo para esta
sesión, credenciales en `backend/.env`, ignorado por Git). Backend ejecutado
desde `backend/`.

| Comando | Resultado |
| --- | --- |
| `python -m alembic upgrade head` | OK, head `9970e12e5f0d` |
| `python -m alembic current` y `heads` | Único head, coinciden |
| `python -m alembic downgrade -1` seguido de `upgrade head` | OK, ciclo completo probado |
| `pytest -q tests/test_mobile_biometric.py tests/test_mobile_session_authority.py tests/test_mobile_security_context.py tests/test_api_access_conformity.py` | 78 passed |
| `pytest -q` (suite completa) | 1277 passed, 4 failed, 22 skipped, 34 warnings, 19 subtests passed |
| `npx tsx --test` (AuthProvider + AuthProvider.biometric + biometric-auth + biometric-storage + overscroll wiring) | 38 passed |
| `npm test` en myc-mobile (suite completa) | 709 passed |
| `npx tsc --noEmit` | 2 errores preexistentes en `realtime-client.ts`, ajenos a este trabajo (no tocado) |
| `npm run lint` | Exit 0, sin errores |
| `python scripts/generate_project_file_registry.py` | OK, archivos nuevos registrados |
| `git diff --check` | Sin errores |

De los 4 fallos de la suite backend completa, 3 son fallos preexistentes de
entorno ajenos a este trabajo (`test_certificate_authentication_from_master.py`
×2 y `test_sat_xls_source.py`: dependen de un LibreOffice funcional no
disponible/roto en este sandbox) y 1 es intermitente
(`test_maintenance_ets_execution.py::test_material_used_and_required_are_separate_and_report_has_no_internal_cost`,
verificado pasando en ejecución aislada; no relacionado con Mobile/biometría).
Ninguno de los 4 toca código modificado en esta entrega. No se ocultaron
fallos propios para forzar verde.

## Git

Commit único de entrega: `feat(mobile-auth): add biometric login flow`.
El SHA final se reporta en la entrega; el documento pertenece a ese mismo
commit. **NO PUSH, NO MERGE, NO DESPLIEGUE.**

## Documentación actualizada

Contrato Mobile (`architecture/MOBILE_SECURITY_CONTEXT.md`), alcance, flujo,
estado, decisiones, deuda técnica (TD-059, TD-060), índice de documentación,
inventario de acceso API (CSV + tests de conformidad) e inventario de
archivos funcionales sincronizados. `BACKUP_ESTADO_ACTUAL.md` actualizado
como snapshot operativo vigente (reemplaza el corte BIOMETRIC-1 anterior,
trazable en Git).

## Validación física pendiente (checklist)

No puede automatizarse completamente; queda pendiente para dispositivo real.

**iPhone:**
- [ ] Face ID aparece en el botón biométrico del login.
- [ ] Face ID correcto entra a Home.
- [ ] Cancelar Face ID mantiene el login disponible (no borra el enrolamiento).
- [ ] Cerrar sesión conserva el acceso Face ID (reabrir muestra "Continuar con Face ID").
- [ ] Cold start (app recién abierta tras matar el proceso) pide Face ID, no entra directo.
- [ ] "Usar otra cuenta" funciona y no borra el enrolamiento existente.
- [ ] La Home ya no se desplaza fuera del viewport (overscroll).
- [ ] El scroll normal de la Home sigue funcionando.
- [ ] La rotación de pantalla no rompe la Home.

**Android:**
- [ ] Huella/biometría fuerte aparece y funciona.
- [ ] Cancelación mantiene el login disponible.
- [ ] No hay fallback silencioso a PIN/patrón del dispositivo.
- [ ] Cold start pide biometría.

## Diff

### Archivos creados

- `backend/app/core/mobile/biometric.py`
- `backend/app/core/mobile/biometric_credentials.py`
- `backend/app/models/mobile_biometric_credential.py`
- `backend/migrations/versions/9970e12e5f0d_biometric_2_add_mobile_biometric_.py`
- `backend/tests/test_mobile_biometric.py`
- `docs/closures/BIOMETRIC_2_BIOMETRIC_LOGIN.md`
- `myc-mobile/src/auth/AuthProvider.biometric.test.ts`
- `myc-mobile/src/services/biometric-auth.test.ts`
- `myc-mobile/src/services/biometric-auth.ts`
- `myc-mobile/src/storage/biometric-storage.test.ts`
- `myc-mobile/src/storage/biometric-storage.ts`
- `myc-mobile/src/wiring-tests/technician-home.overscroll.wiring.test.ts`

### Archivos modificados

- `backend/app/core/config.py`
- `backend/app/models/__init__.py`
- `backend/app/routers/mobile_auth.py`
- `backend/app/schemas/mobile_auth.py`
- `backend/app/security/api_access.py`
- `backend/tests/test_api_access_conformity.py`
- `docs/PROJECT_FILE_REGISTRY.md`
- `docs/architecture/MOBILE_SECURITY_CONTEXT.md`
- `docs/architecture/security/API_ENDPOINT_INVENTORY_2026-08-03.csv`
- `docs/project/CURRENT_PROCESS_FLOW.md`
- `docs/project/CURRENT_SCOPE.md`
- `docs/project/DECISIONS.md`
- `docs/project/DOCUMENTATION_INDEX.md`
- `docs/project/PROJECT_STATUS.md`
- `docs/project/TECHNICAL_DEBT.md`
- `docs/BACKUP_ESTADO_ACTUAL.md`
- `myc-mobile/app.json`
- `myc-mobile/app/(auth)/login.tsx`
- `myc-mobile/app/(technician)/index.tsx`
- `myc-mobile/package-lock.json`
- `myc-mobile/package.json`
- `myc-mobile/src/auth/AuthProvider.test.ts` (fix de infraestructura de pruebas: el `require` shim de la harness sólo resolvía especificadores `@/src/...`; un módulo cargado por ese alias que a su vez importa un hermano con ruta relativa —como `api/error-detail.ts` importando `../services/field-labels`— fallaba con ENOENT. Se corrigió para resolver rutas relativas contra el directorio del módulo que las emite, sin tocar ningún test BIOMETRIC-1 existente; los 11 tests originales pasan igual que antes)
- `myc-mobile/src/auth/AuthProvider.tsx`
- `myc-mobile/src/services/auth.service.ts`
- `myc-mobile/src/services/mobile-auth-client.ts`

No se versionó el respaldo de base de datos ni artefactos de prueba; el
`.env` local con credenciales del PostgreSQL de este entorno permanece
ignorado por Git.
