> Estado: VIGENTE — FASE DEV-0

> Tipo: Arquitectura vigente

> Corte: 2026-09-21 — DEV-0 (Developer Authority para MYC Mobile)

# Autoridad Developer de MYC Mobile

## Objetivo de esta fase

DEV-0 construye la autoridad de seguridad sobre la cual vivirán, en fases
posteriores (DEV-1+): Developer Center, Database Console, Shell Broker /
PowerShell, Logs, Services, Git y demás operaciones de infraestructura.

**Esta fase NO implementa PowerShell, subprocess, shell WebSocket, ejecución
SQL, explorador de base de datos, broker de Windows ni el puerto 8765.** Todo
eso es DEV-1+. DEV-0 sólo construye:

1. permisos Developer explícitos;
2. `DeveloperSession` server-side;
3. desbloqueo Developer mediante credencial biométrica real (reutilizando
   BIOMETRIC-2, nunca una segunda autoridad biométrica);
4. expiración/revocación;
5. `DeveloperProvider` en Mobile;
6. pantalla Developer placeholder;
7. el contrato de lifecycle que DEV-1 usará para `ShellSession`.

## Threat model

- Un actor externo (cliente, portal) nunca debe poder alcanzar Developer:
  gateado por `actor_type == "internal"` en el propio endpoint, no sólo por
  convención de UI.
- Un actor interno sin `developer.access` explícito nunca debe poder
  desbloquear Developer, aunque tenga `mobile.access`.
- Un dispositivo Mobile comprometido en el que el usuario NO tiene biometría
  configurada nunca debe poder desbloquear Developer con sólo el access
  token — se exige la credencial biométrica real (server-verificable),
  nunca un booleano "Face ID passed".
- Ningún dato de identidad (`device_id`, `device_uuid`, `user_id`,
  `mobile_session_id`) se acepta nunca del cliente como autoridad: todo se
  deriva server-side del token Mobile y de la fila de
  `MobileBiometricCredential` almacenada.
- El token Developer es opaco, aleatorio (`secrets.token_urlsafe(48)`), y
  server-side sólo se guarda su SHA-256 (`developer_sessions.token_hash`) —
  igual que `MobileAuthSession`/`MobileBiometricCredential`. El texto plano
  nunca se persiste, nunca se loguea, nunca viaja fuera de la respuesta HTTP
  inicial de `POST /developer/session`.
- El bloqueo de Developer (cierre voluntario, expiración o revocación de
  autoridad viva) **nunca** produce logout de MYC, nunca revoca la
  biometría, y nunca revoca `MobileAuthSession`. Son autoridades
  independientes con lifecycles independientes.

## Invariante de infraestructura — LocalSystem

En producción, `MYCBackend.exe` corre como servicio Windows bajo
`LocalSystem` (`C:\MYC\Services\backend\MYCBackend.exe`). **FastAPI nunca
debe lanzar `powershell.exe` (ni ningún subprocess) directamente**: heredaría
`NT AUTHORITY\SYSTEM`, el nivel de privilegio más alto posible en Windows.

El futuro Shell Broker (DEV-1+, `MYCDeveloperBroker`) será un **servicio
Windows separado, con identidad dedicada**, nunca el propio proceso backend.
El backend HTTP hablará con ese broker por un canal separado (WSS local o
named pipe autenticado), nunca abriendo un shell dentro de su propio
proceso. Ningún puerto de ese broker (p.ej. 8765) se implementa en esta fase.

No hay exposición directa de PostgreSQL ni se requiere SSH: toda futura
consola de base de datos y toda futura terminal viajarán por el mismo túnel
HTTPS/WSS que ya usa el resto de MYC Mobile.

## Tres autoridades, tres lifecycles

| | `MobileAuthSession` | `DeveloperSession` | `ShellSession` (futuro, DEV-1+) |
|---|---|---|---|
| Qué autoriza | Uso operativo de MYC Mobile | Control temporal de infraestructura | Un proceso PowerShell persistente en el broker |
| Emitida por | Login / refresh / biometric exchange | Biometría re-probada sobre una Mobile session vigente | Se adjunta a una DeveloperSession vigente |
| TTL | `refresh_token_expire_minutes` (30 días), con rotación | `developer_session_expire_minutes` = 10 min, **sin refresh** | Vive mientras el proceso siga vivo en el broker, sujeta a grace period |
| Renovación | Rotación silenciosa vía refresh token | Nunca silenciosa: exige nueva biometría | Se reengancha (reattach) a una DeveloperSession nueva, nunca se reinicia sola |
| Logout MYC | Se revoca | Se revoca (best-effort, ver abajo) | Se mata inmediatamente |
| Cierre Developer | No se toca | Se revoca | Sigue viva (grace period) |
| Expira por TTL | — | Se revoca de forma perezosa en el próximo uso | Terminal bloqueada, shell sigue viva (grace period) |

`DeveloperSession` **no es** `ShellSession`. `DeveloperSession` es la
autoridad temporal para *controlar* infraestructura; `ShellSession` (DEV-1+)
será el proceso PowerShell persistente en sí. Que expire una no implica que
la otra deba morir de inmediato — ver la sección de contrato futuro.

## `DeveloperSession` — modelo

Tabla `developer_sessions`
(`backend/app/models/developer_session.py`,
migración `602a09af6218_dev_0_add_developer_sessions.py`, depende de
`9970e12e5f0d`, head único tras aplicarla):

```
id
user_id            -> users.id
device_id          -> mobile_trusted_devices.id
mobile_session_id  -> mobile_auth_sessions.id
token_hash         (SHA-256 del token opaco, único, indexado)
last_used_at
expires_at
revoked_at
revocation_reason  ("expired" | "user_lock" | "authority_revoked")
created_at / updated_at
```

TTL configurable via `settings.developer_session_expire_minutes` (default
10). `DeveloperSession`:

- NO tiene refresh token.
- NO se renueva silenciosamente (cada extensión es una nueva biometría → una
  nueva fila).
- NO sobrevive logout.
- NO puede usarse como access token ERP normal (header propio, nunca
  `Authorization: Bearer`).

## Reutilización de la autoridad biométrica (BIOMETRIC-2)

`backend/app/core/mobile/biometric.py` se refactorizó para extraer
`resolve_biometric_credential(db, credential) -> ResolvedBiometricCredential`
(credencial → `MobileTrustedDevice` → `User`, validando hash, expiración,
revocación, dispositivo activo, cuenta activa y snapshot de contraseña),
**sin** crear una `MobileAuthSession` nueva. `exchange_biometric_credential`
(login biométrico) y `open_developer_session` (desbloqueo Developer) llaman
a la misma función; no existe una segunda autoridad biométrica.

`backend/app/core/mobile/developer.py` (`open_developer_session`) además
exige, sobre ese resultado:

- `context.actor_type == "internal"` (verificado antes incluso, por el
  dependency `require_internal_mobile_permission("developer.access")`);
- `developer.access` presente (o `"*"`, ver sección de riesgo aceptado);
- `resolved.user.id == context.user.id` (la credencial biométrica es de la
  MISMA identidad que el token Mobile presentado);
- `resolved.device.id == mobile_session.device_id` (la credencial biométrica
  está atada al MISMO dispositivo que la sesión Mobile activa).

Si cualquiera de estas comprobaciones falla, no se crea `DeveloperSession`
(401/403 según el caso).

## Permisos

Nuevos permisos explícitos (asignados sólo al rol `Desarrollador`, en
`backend/app/core/permissions.py`):

```
developer.access
developer.database.read
developer.database.write
developer.database.admin
developer.shell.access
developer.system.read
developer.logs.read
developer.services.execute
developer.git.read
```

Sólo `developer.access` se usa en esta fase (las demás quedan declaradas
para que DEV-1+ las consuma sin otra migración de permisos).

### Riesgo aceptado: `"*"` sigue abriendo Developer

El mecanismo central de permisos (`user_has_permission`/
`effective_user_permissions` en `app/services/auth.py`) trata `"*"` como "todo
permiso", y el rol `Administrador` tiene `"*"`. DEV-0 **no** rompe esa
semántica global (se nos pidió explícitamente no hacerlo), así que hoy un
`Administrador` puede desbloquear Developer igual que un `Desarrollador`
(`test_admin_wildcard_still_grants_developer_access`, documentado y
verificado por test). No se introdujo ningún atajo por email/user-id — la
autoridad sigue siendo enteramente el mecanismo de roles/permisos.

**Deuda técnica declarada para una fase futura:** antes de que DEV-1
implemente shell/DB real, definir una política canónica explícita que exija
"actor interno + capability Developer explícita" **sin** dejar que el
`"*"` genérico de "Administrador del ERP" baste por accidente para
infraestructura (motivo original de la tarea DEV-0). Esto requiere una
decisión de producto (¿se separa `Administrador` de `Desarrollador`
formalmente para infraestructura?), no una implementación técnica trivial, y
por eso queda fuera del alcance de DEV-0.

## Endpoints

Todos bajo `/api/mobile/v1/developer/session`, router
`backend/app/routers/mobile_developer.py`, incluidos vía
`include_api_router(..., prefix="/api")` — igual que el resto de Mobile,
por lo que el gate global `enforce_api_access` ya exige un Mobile Bearer
token válido (`mobile.access`) en las tres rutas antes de que el propio
handler se ejecute.

### `POST /session` — abrir Developer

- Auth: `Authorization: Bearer <mobile access token>` +
  `require_internal_mobile_permission("developer.access")`.
- Body: `{"biometric_credential": "<opaco>"}`.
- 200: `{"developer_token": "...", "expires_at": "...", "session_id": N}`.
- 403 si el actor no es interno o no tiene `developer.access`.
- 401 si la credencial biométrica es inválida/ajena/de otro dispositivo/
  revocada/expirada, o si cambió la contraseña desde el enrolamiento.

### `GET /session` — estado

- Auth: `Authorization: Bearer <mobile access token>` **+** header dedicado
  `X-MYC-Developer-Token: <token opaco>` (obligatorio; se eligió un header
  propio, nunca mezclado con el JWT Mobile, para que Developer sea
  verificablemente su propia autoridad).
- 200 siempre que el header esté presente y el Mobile Bearer sea válido:
  `{"active": bool, "expires_at": ..., "remaining_seconds": ..., "user_id":
  ..., "device_id": ...}` (campos `null` cuando `active` es `false`).
- **Nunca** devuelve 401 por un token Developer inválido/expirado/ajeno —
  responde `active: false`. Esto es deliberado: un 401 aquí podría disparar
  el manejo genérico de sesión Mobile (refresh/logout) en el cliente, y
  cerrar Developer nunca debe tocar esa autoridad.
- Nunca devuelve `token_hash`.
- Re-valida autoridad viva en cada llamada (ver más abajo) — nunca confía
  sólo en `expires_at`/`revoked_at` capturados al emitir.

### `DELETE /session` — bloquear

- Misma auth que GET.
- Idempotente: token ausente/ajeno/ya revocado/no encontrado → 204 igual
  (no hay estado adicional que lograr).
- Sólo revoca la `DeveloperSession` — nunca `MobileAuthSession` ni la
  biometría.

## Revalidación en cada uso (no sólo al emitir)

`developer.py::_check_live` re-deriva, en cada `GET`, si la
`DeveloperSession` sigue siendo autoridad viva:

- `expires_at` no vencido;
- `MobileAuthSession` asociada sigue vigente (no revocada/expirada);
- `MobileTrustedDevice` sigue activo y no revocado;
- `User` sigue activo/`ACTIVE`;
- actor sigue siendo `internal`;
- `developer.access` (o `"*"`) sigue presente.

Una expiración o pérdida de autoridad recién detectada se revoca de forma
perezosa (`revoked_at`/`revocation_reason` se escriben en ese momento) y se
audita — no se necesita un job de barrido aparte.

## Auditoría

Vía la autoridad canónica existente (`app/services/audit_logs.py::write_audit_log`,
tabla `audit_logs`; no se inventó una segunda plataforma de auditoría).
Eventos: `developer_session.opened`, `developer_session.revoked`,
`developer_session.expired`. Datos: `user_id`, `entity="developer_session"`,
`entity_id` (id de la fila), `new_values={"device_id", "mobile_session_id"}`.
Nunca se registra el token en texto plano, la credencial biométrica, ni el
hash completo del token (el propio `token_hash` no se incluye en
`new_values`).

## Mobile — `DeveloperProvider`

`myc-mobile/src/auth/DeveloperProvider.tsx`, separado deliberadamente de
`AuthProvider` (lifecycles distintos), montado en `app/_layout.tsx` como
hijo de `AuthProvider` (necesita `useAuth()` para el access token y el
usuario actual).

API expuesta (`useDeveloper()`):

```
isDeveloperAvailable    // developer.access presente + actor interno
isDeveloperUnlocked
remainingSeconds
showExpirationWarning
unlockDeveloper()
lockDeveloper()
dismissExpirationWarning()
refreshDeveloperStatus()
```

`unlockDeveloper()`:

1. exige `isDeveloperAvailable`;
2. llama `readBiometricCredential()` (`expo-secure-store` con
   `requireAuthentication: true` — el SO exige Face ID/Touch ID/huella antes
   de liberar el valor; **nunca** `authenticateBiometric()` + un booleano);
3. envía esa credencial real a `POST /developer/session`;
4. guarda el `developer_token` devuelto **sólo en memoria** (`useRef`,
   nunca `SecureStore`/`AsyncStorage`/filesystem — verificado por test: el
   archivo no importa ningún módulo de storage-write);
5. arranca un countdown local (1s) derivado de `expires_at`.

Cold start (proceso matado) siempre vuelve bloqueado: no hay nada que leer,
el token nunca se persistió.

### Expiración y warning

El countdown es local (deriva de `expires_at`, no hace polling continuo al
backend). A ≤60s y >0s se muestra exactamente un warning por ciclo
(`showExpirationWarning`), con dos acciones: "Extender con Face ID"
(vuelve a llamar `unlockDeveloper()`, produce una `DeveloperSession` nueva)
o "Bloquear ahora" (`lockDeveloper()`). Al llegar a 0, el token se olvida
localmente sin llamar al backend (el backend expira la misma fila de forma
independiente si se la vuelve a consultar).

### Logout

`DeveloperProvider` observa `session` de `AuthProvider`: en cuanto pasa a
`null`, revoca el token Developer local de inmediato y hace un DELETE
best-effort al backend. Una carrera "logout mientras `unlockDeveloper()`
sigue esperando Face ID/red" se resuelve con un contador de versión: si la
versión cambió cuando la promesa resuelve, el `DeveloperSession` recién
abierto se revoca (best-effort) y el estado local nunca se resucita
unlocked.

## UI — pantalla Developer (placeholder)

`myc-mobile/app/(technician)/developer.tsx`. Tarjeta "Desarrollador" en
Home visible sólo con `developer.access` (`canAccessDeveloper` en
`mobile-capabilities.ts`). Locked: "Developer / Acceso protegido" +
"Desbloquear con Face ID". Unlocked: "Developer Center", countdown
"Sesión activa · MM:SS restantes", cinco tarjetas "Próximamente" (Base de
datos, Terminal, Logs, Servicios, Git) y "Bloquear Developer". Ninguna
herramienta real se implementó.

## Contrato futuro — `ShellSession` (DEV-1+, NO implementado aquí)

Documentado para que DEV-1 no tenga que re-derivar estas decisiones:

- `DeveloperSession` TTL: 10 min. Warning Mobile a 60s.
- Extender (Face ID) → nueva `DeveloperSession` → la `ShellSession` futura
  **no se reinicia**, sigue siendo el mismo proceso PowerShell.
- Si `DeveloperSession` expira: **no** se mata la `ShellSession` de
  inmediato. Comportamiento DEV-1: la terminal UI queda bloqueada, ningún
  stdin/comando nuevo se acepta, pero el shell sigue vivo server-side en
  estado detached/locked durante un **grace period de 15 minutos**. Dentro
  de ese periodo, un nuevo Face ID → nueva `DeveloperSession` → reattach a
  el mismo `shell_session_id` (mismo cwd/proceso/psql si sigue vivo). Pasado
  el grace period, el broker termina el proceso PowerShell.
- Un comando/proceso ya en ejecución cuando `DeveloperSession` expira
  **no** se mata sólo por eso — se perdería control/input sobre un trabajo
  legítimo en curso; puede seguir corriendo mientras la `ShellSession` siga
  dentro del grace period.
- KILL inmediato de la futura `ShellSession` (nunca grace period) si:
  logout MYC, usuario deshabilitado, `MobileTrustedDevice` revocado,
  `developer.access` revocado, "Cerrar terminal" explícito, apagado/reinicio
  del broker, o cualquier revocación de seguridad equivalente.

## Qué NO se tocó

BIOMETRIC-1 (arquitectura de sesión Mobile), rotación de refresh,
`PushDevice`, comunicaciones en tiempo real, LAB, tickets, certificados,
facturas, field sheets, EAS, proyecto iOS nativo, firma de builds, Pods,
servicios Windows existentes, configuración de Cloudflare.

## Validación de esta fase

- Backend: `tests/test_mobile_developer_session.py` (24 casos) +
  `tests/test_mobile_biometric.py` + `tests/test_mobile_security_context.py`
  + `tests/test_api_access_conformity.py` + `tests/test_capability_gate_reconciliation.py`
  en verde; suite completa del backend en verde
  (`test_schema_integrity_stage_2a.py::test_current_revision_is_the_single_head`
  confirma un único head de Alembic tras la migración).
- Mobile: `npm test`, `npx tsc --noEmit`, `npm run lint` en verde (dos
  errores preexistentes y ajenos en `src/realtime/realtime-client.ts`, no
  tocado por esta fase).
