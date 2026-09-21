> Tipo: Cierre técnico de implementación acotada
>
> Fecha: 2026-09-21
>
> No declara SELLADO el módulo Mobile ni sustituye PROJECT_STATUS.

# BIOMETRIC-1 / Fase 1 — Mobile Session Authority

## Estado inicial

Precondición ejecutada antes de modificar archivos: `git status`, rama, HEAD,
`origin/main`, diff, staged diff y archivos no versionados. Resultado: `main`,
`57756cdbbbe89d8f65eca56fda1dcb5014f07ab0`, idéntico a `origin/main`, worktree limpio.
Se creó y utilizó exclusivamente `feat/mobile-session-authority-biometric-1`.
Alembic inicial: current/head únicos en `6640c526c412`.

## Arquitectura implementada

- **Security device:** `MobileTrustedDevice` independiente de PushDevice,
  identificado por usuario + UUID generado en instalación, con metadata,
  estado y fechas UTC. Un dispositivo revocado/inactivo no se reactiva.
- **Auth session:** `MobileAuthSession` por generación de refresh, ligada a
  usuario, dispositivo, familia y scope original internal/client. No crea
  otra identidad de usuario ni otra autoridad de permisos.
- **Opaque refresh:** `secrets.token_urlsafe(48)`; PostgreSQL sólo almacena
  SHA-256. El campo HTTP continúa llamándose `refresh_token`.
- **Rotation:** dispositivo y sesión se bloquean en ese orden; se crea sucesor
  de la misma familia, se consume el anterior y se actualiza `replaced_by_id`.
  El vencimiento absoluto de familia se conserva.
- **Reuse:** una generación consumida revoca toda la familia y registra
  `reuse_detected_at`; la revocación se confirma antes del 401. Los locks
  coordinan también reuse contra descendientes y logout contra refresh.
- **Single-flight:** `AuthProvider.refreshPromise` comparte un único HTTP,
  resultado/error y liberación en finally. Los 401 tardíos reutilizan el access
  renovado; RealtimeProvider consume el mismo método. Versionado de sesión y
  serialización de SecureStore impiden resurrección local tras logout.

El lock de usuario para registro/migración es `FOR NO KEY UPDATE`: serializa
esos flujos y permite el KEY SHARE de FK al insertar un sucesor de otra
transacción. La regresión PostgreSQL coordina un login que posee el lock de
usuario con un refresh que posee el dispositivo y prueba ausencia de deadlock.

## Migración

Archivo: `backend/migrations/versions/b10a1c202601_mobile_session_authority.py`.
Revision `b10a1c202601`; down_revision `6640c526c412`.

Crea `mobile_trusted_devices` y `mobile_auth_sessions`; fechas timezone-aware,
defaults de timestamps, FKs y checks de plataforma/scope. Incluye índice de
usuario en dispositivo, UNIQUE usuario/UUID, índices de sesión por usuario,
dispositivo, familia, vencimiento y revocación; hashes refresh y legacy únicos;
sucesor self-FK único. Los campos de scope tienen referencias a Client y
ClientPortalMembership. Downgrade elimina ambas tablas en orden inverso.

Upgrade aplicado a la base local; current = heads = `b10a1c202601`.
Upgrade/downgrade/upgrade y concurrencia probados en esquema PostgreSQL aislado,
eliminado al terminar. No se modificaron migraciones anteriores.
`backup_erp_myc_antes_prueba.sql` regenerado con el script canónico y revisión
extraída/verificada contra head. El respaldo permanece local e ignorado por Git.

## Contratos API

Prefijo `/api/mobile/v1/auth`:

| Endpoint | Cambio exacto |
| --- | --- |
| POST login | Requiere email, password y device; responde TokenPair + user existentes, con refresh opaco y access ligado a sesión. |
| POST refresh, legacy JWT | Requiere refresh_token y device; un solo uso por JWT dentro del corte temporal. |
| POST refresh, opaco | Recibe únicamente refresh_token; device explícito, incluso null, devuelve 422. La asociación proviene de la sesión. |
| POST logout | Nuevo; access JWT Mobile con mobile_session_id. Revoca sólo la familia actual y devuelve 204. |
| GET me | Conserva proyección; valida también sesión y dispositivo para access nuevo. |

Login y refresh legacy comparten `MobileSecurityDeviceInput`: device_uuid UUID,
platform ios/android, device_name nullable hasta 160, app_version nullable hasta
40. Los refresh desconocidos/inválidos, vencidos, revocados o sin autoridad
vigente devuelven 401 genérico. Device ausente en legacy es 422.

## Compatibilidad

La extensión de device en refresh legacy fue autorizada expresamente. Mobile
crea/persiste el UUID en `myc.security.device_uuid.v1` antes del login o de esa
migración; tras guardar el opaco, las renovaciones omiten metadata.

El fallback valida con la autoridad Mobile previa y conserva scope. Sólo
admite mobile_internal/mobile_client y la compatibilidad internal ya existente
para usuarios internos con mobile.access; no admite Portal ni cliente como
interno. No emite nuevos refresh JWT. El hash legacy único impide migraciones
repetidas, incluso con otro UUID o en paralelo; repetirlo revoca la familia.
Rechaza firmas JWT base64url no canónicas para evitar hashes alternativos de
una misma firma, comportamiento reproducido contra el decoder existente.

Fecha fija de cierre: **2026-10-22 00:00 UTC**; el exp legacy tampoco puede
superarla. Los access históricos sin sesión conservan validez hasta expirar.
La transición prueba posesión del JWT y UUID presentado ahora; no puede probar
qué dispositivo obtuvo originalmente ese JWT. No inventa esa relación.

## Seguridad y límites

- No se guardan contraseñas nuevas ni refresh plaintext en DB.
- PushDevice permanece separado y sin cambio de semántica.
- Logout server-side, session binding, scope client y permisos internal probados.
- Sin cambios a auth Web/Portal ni TTL global; sin biometría, passkeys, claves,
  SSH, consola SQL, lease, broker, logout-all o panel de dispositivos.
- Logout sigue auth → push best-effort → limpieza local. El DELETE push puede
  recibir 401 porque el access ya fue revocado; no garantiza baja remota push.
  Un fallo de red tampoco permite afirmar que la revocación remota ocurrió.
- SecureStore vacío genera UUID nuevo; iOS puede conservar Keychain al
  reinstalar. Se mantiene el UUID al cerrar sesión.
- Pendiente aceptación física iOS/Android con build que incluya expo-crypto y
  retiro del fallback al concluir la ventana. Son límites explícitos, sin
  declarar sellado global ni implementar BIOMETRIC-2.

## Tests y validación

Python canónico: `venv/bin/python`. Backend ejecutado desde `backend/`.
`MOBILE_AUTH_POSTGRES_TEST_URL` se configuró desde settings.database_url sin
imprimir credenciales; las pruebas crearon y eliminaron sus propios esquemas.

| Comando | Resultado |
| --- | --- |
| `../venv/bin/python -m alembic upgrade head` | OK, b10a1c202601 |
| `../venv/bin/python -m alembic current` y `heads` | Mismo head único |
| `../venv/bin/python -m pytest -q tests/test_mobile_session_authority.py tests/test_mobile_session_postgres.py tests/test_mobile_security_context.py tests/test_api_access_conformity.py` | 66 passed, 2 warnings |
| `../venv/bin/python -m pytest -q` | 1269 passed, 16 skipped, 34 warnings, 19 subtests passed |
| `npx tsx --test src/auth/AuthProvider.test.ts src/services/auth.service.test.ts` | 15 passed |
| `npm test` en myc-mobile | 680 passed |
| `npx tsc --noEmit` | Exit 0, sin errores |
| `npm run lint` | Exit 0, sin errores |
| `venv/bin/python scripts/generate_api_access_inventory.py` | 530 operaciones, incluye logout autenticado |
| `python3 scripts/generate_project_file_registry.py` y revisión de rutas | OK |
| `git diff --check` | OK |

Se corrigieron los fallos de implementación encontrados durante el trabajo;
no se ocultaron fallos ajenos para obtener verde. Los warnings de deprecación y
SQLAlchemy se conservan en la salida. Las seis pruebas nuevas PostgreSQL sí se
ejecutaron; las omisiones corresponden a otras suites.

## Git

Commit único de entrega: `feat(mobile-auth): add rotatable device-bound sessions`.
El SHA final se reporta en la entrega; el documento pertenece a ese mismo commit.
**NO PUSH, NO MERGE, NO DESPLIEGUE.**

## Documentación actualizada

Contrato Mobile, referencia de acceso técnico y precisión del logout push,
estado, alcance, flujo, reglas,
decisiones, deuda TD-035, índice, inventarios y snapshot operativo sincronizados.
OBSERVATIONS_REGISTER, COMMUNICATIONS_REALTIME y la
custodia SecureStore existente revisados sin cambios: no se añaden observaciones
funcionales/UX ni cambia el contrato propio de esos subsistemas. Las limitaciones
de autenticación quedan en su autoridad y TD-035.

Se crea únicamente este cierre documental; no hay movimientos, fusiones ni
archivado documental. Los nuevos archivos funcionales se enumeran abajo y están
registrados con responsabilidad, dependencias, consumidores, criticidad y estado.

## Diff

### Archivos creados

- `backend/app/core/mobile/refresh_credentials.py`
- `backend/app/models/mobile_auth_session.py`
- `backend/app/models/mobile_trusted_device.py`
- `backend/migrations/versions/b10a1c202601_mobile_session_authority.py`
- `backend/tests/test_mobile_session_authority.py`
- `backend/tests/test_mobile_session_postgres.py`
- `docs/closures/BIOMETRIC_1_MOBILE_SESSION_AUTHORITY.md`
- `myc-mobile/src/auth/AuthProvider.test.ts`
- `myc-mobile/src/services/security-device.ts`

### Archivos modificados

- `backend/app/core/mobile/security.py`
- `backend/app/models/__init__.py`
- `backend/app/routers/mobile_auth.py`
- `backend/app/schemas/mobile_auth.py`
- `backend/tests/test_api_access_conformity.py`
- `backend/tests/test_lab_phase2_integrated_alta.py`
- `backend/tests/test_lab_phase3_reception_signing.py`
- `backend/tests/test_lab_phase5_operational_closure.py`
- `backend/tests/test_mobile_security_context.py`
- `docs/BACKUP_ESTADO_ACTUAL.md`
- `docs/PROJECT_FILE_REGISTRY.md`
- `docs/architecture/MOBILE_NOTIFICATIONS_V1.md`
- `docs/architecture/MOBILE_SECURITY_CONTEXT.md`
- `docs/architecture/MOBILE_TECHNICIAN_ACCESS.md`
- `docs/architecture/security/API_ENDPOINT_INVENTORY_2026-08-03.csv`
- `docs/project/BUSINESS_RULES.md`
- `docs/project/CURRENT_PROCESS_FLOW.md`
- `docs/project/CURRENT_SCOPE.md`
- `docs/project/DECISIONS.md`
- `docs/project/DOCUMENTATION_INDEX.md`
- `docs/project/PROJECT_STATUS.md`
- `docs/project/TECHNICAL_DEBT.md`
- `myc-mobile/package-lock.json`
- `myc-mobile/package.json`
- `myc-mobile/src/auth/AuthProvider.tsx`
- `myc-mobile/src/services/auth.service.test.ts`
- `myc-mobile/src/services/auth.service.ts`
- `myc-mobile/src/services/mobile-auth-client.ts`
- `myc-mobile/src/types/auth.ts`
- `scripts/generate_project_file_registry.py`

Respaldo SQL regenerado fuera de Git; no se versionaron logs ni artefactos de prueba.
