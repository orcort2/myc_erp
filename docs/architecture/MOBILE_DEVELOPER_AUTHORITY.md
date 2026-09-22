> Estado: EN REVISIÓN — FASE DEV-0 (endurecimiento pre-cierre aplicado; pendiente de auditoría humana, NO cerrado)

> Tipo: Arquitectura vigente

> Corte: 2026-09-22 — DEV-0 (Developer Authority para MYC Mobile) + endurecimiento: política Developer explícita, una sola DeveloperSession activa, binding por MobileAuthSession y reconciliación Mobile por lifecycle

# Autoridad Developer de MYC Mobile

## Objetivo de esta fase

DEV-0 construye la autoridad de seguridad sobre la cual vivirán, en fases
posteriores (DEV-1+): Developer Center, Database Console, Shell Broker /
PowerShell, Logs, Services, Git y demás operaciones de infraestructura.

**Esta fase NO implementa PowerShell, subprocess, shell WebSocket, ejecución
SQL, explorador de base de datos, broker de Windows ni el puerto 8765.** Todo
eso es DEV-1+. DEV-0 sólo construye:

1. permisos Developer explícitos y una **política Developer canónica**
   (`app/core/developer_policy.py`) que no hereda del `"*"` de Administrador;
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
- **Administrador ERP ≠ Administrador de infraestructura.** El `"*"` de
  `Administrador` conserva su semántica global en el ERP, pero por sí solo
  **no** abre Developer (ver "Política Developer explícita").
- Un token Developer sólo es usable desde la **misma** `MobileAuthSession`
  (misma generación) que lo abrió: mismo usuario, mismo dispositivo y mismo
  `mobile_session_id`. Otra sesión Mobile del mismo usuario/dispositivo, otro
  dispositivo u otra identidad lo ven como inexistente.
- Nunca hay dos credenciales Developer vigentes para la misma autoridad
  Mobile: abrir una nueva revoca (`superseded`) la anterior.
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
El backend HTTP hablará con ese broker por un canal separado, nunca
abriendo un shell dentro de su propio proceso. **DEV-1A fijó el canal**:
IPC local por Windows Named Pipe + ACL del SO + mensajes autenticados con
HMAC; sin puerto (ni 8765 ni loopback TCP). El contrato, el cliente, el
anti-replay y el endpoint `GET /developer/broker/health` están en
[`MOBILE_DEVELOPER_BROKER.md`](MOBILE_DEVELOPER_BROKER.md); el adapter
Windows y el servicio con identidad dedicada siguen pendientes (DEV-1B).

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
(`backend/app/models/developer_session.py`; migraciones
`602a09af6218_dev_0_add_developer_sessions.py` (padre `9970e12e5f0d`) y
`c4d8e2f1a7b3_dev_0_single_active_developer_session.py` (padre
`602a09af6218`); `c4d8e2f1a7b3` es el head único):

```
id
user_id            -> users.id
device_id          -> mobile_trusted_devices.id
mobile_session_id  -> mobile_auth_sessions.id
token_hash         (SHA-256 del token opaco; índice único ix_developer_sessions_token_hash)
last_used_at
expires_at
revoked_at
revocation_reason  ("expired" | "user_lock" | "authority_revoked" | "superseded")
created_at / updated_at

uq_developer_sessions_active_device  UNIQUE (device_id) WHERE revoked_at IS NULL
```

FKs: `users`, `mobile_trusted_devices` y `mobile_auth_sessions`, todas
`ON DELETE CASCADE`. Índices simples en `user_id`, `device_id`,
`mobile_session_id`, `expires_at` y `revoked_at`.

`c4d8e2f1a7b3` es una revisión **nueva** encima de `602a09af6218` (no se
editó `602a09af6218`: ya estaba aplicada en la base local `erp_myc`, que de
otro modo nunca recibiría el índice). Hace tres cosas:

1. sanea datos previos: si un dispositivo tuviera más de una fila activa,
   conserva la más reciente y revoca las demás con `superseded` (sin esto el
   índice único no podría crearse);
2. crea el índice único parcial `uq_developer_sessions_active_device`
   (PostgreSQL y SQLite, mismo patrón que `field_sheet`/`lab_work_order`);
3. elimina `uq_developer_session_token_hash`: `602a09af6218` había creado un
   UNIQUE constraint **y** un índice único sobre `token_hash`; el modelo sólo
   declara el índice, que ya garantiza la unicidad. Tras esto
   `alembic check` ya no reporta drift en `developer_sessions`.

`downgrade()` restaura el constraint y elimina el índice parcial (no
"des-revoca" filas saneadas). Verificado upgrade → downgrade → upgrade
contra PostgreSQL local desechable.

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

- la política Developer explícita: actor interno **y** `developer.access`
  exacto (verificado antes incluso, por el dependency
  `require_mobile_developer_capability(DEVELOPER_ACCESS)`, y de nuevo dentro
  del servicio);
- lock de la fila `MobileTrustedDevice` (mismo orden de locks que
  BIOMETRIC-1/2: dispositivo primero, luego credencial biométrica) y
  re-lectura de la `MobileAuthSession` bajo ese lock (serializa contra un
  logout concurrente);
- `resolved.user.id == context.user.id` (la credencial biométrica es de la
  MISMA identidad que el token Mobile presentado);
- `resolved.device.id == mobile_session.device_id` (la credencial biométrica
  está atada al MISMO dispositivo que la sesión Mobile activa);
- supersession de cualquier `DeveloperSession` aún abierta de ese
  dispositivo antes de insertar la nueva (ver sección siguiente).

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

Hoy `developer.access` gatea abrir/usar la `DeveloperSession`; las demás
quedan declaradas para que DEV-1+ las consuma como **capacidades
granulares** (p.ej. `developer.database.read`) sin otra migración de
permisos.

### Política Developer explícita (`"*"` ya NO concede Developer)

```
Developer permitido = actor interno AND capacidad Developer explícita
```

Autoridad canónica: `backend/app/core/developer_policy.py`.

- `grants_developer_capability(permissions, capability)`: **coincidencia
  exacta** del string (p.ej. `developer.access`); ni `"*"` ni el wildcard
  literal `"developer.*"` conceden una capacidad Developer. Rechaza
  (`ValueError`) cualquier string que no sea una de las capacidades Developer
  declaradas en `DEVELOPER_CAPABILITIES`.
- `user_has_developer_capability(user, capability)`: cuenta activa,
  `status == ACTIVE`, `account_type == internal` y la capacidad exacta en los
  permisos efectivos de sus roles **actuales**.
- `actor_has_developer_capability(actor_type, user, capability)`: además
  exige que el actor Mobile sea `internal` (un actor `client` nunca llega a
  Developer, aunque su contexto traiga capacidades Developer como
  `developer.access`).

Hoy sólo el rol `Desarrollador` recibe estas capacidades. Un
`Administrador` que además necesite infraestructura debe tener asignado
explícitamente el rol `Desarrollador` (o el rol que en el futuro porte
esas capacidades). No hay atajos por email/username/user_id.

La semántica global de `"*"` **no cambió**: `user_has_permission`,
`require_permission`, `require_mobile_permission` y
`require_internal_mobile_permission` siguen tratando `"*"` como "todo
permiso" para el ERP. Sólo los gates Developer usan la política explícita:

| Punto | Mecanismo |
|---|---|
| `POST /developer/session` (router) | `require_mobile_developer_capability(DEVELOPER_ACCESS)` |
| `open_developer_session` (servicio) | `actor_has_developer_capability` (defensa en profundidad) |
| Revalidación viva (`_live_authority`) | `user_has_developer_capability` sobre el usuario actual |
| Operaciones DEV-1+ | `authorize_developer_operation` / `require_developer_session(capability)` — primer uso real: `GET /developer/broker/health` con `developer.system.read` (DEV-1A) |
| Mobile: `canAccessDeveloper`, `DeveloperProvider.isDeveloperAvailable`, navegación | `hasDeveloperCapability` (`myc-mobile/src/permissions/developer-policy.ts`) |

Retirar la capacidad explícita después de abrir la sesión la invalida en
el siguiente uso (`authority_revoked`), aunque el usuario conserve `"*"`.

## Una sola `DeveloperSession` activa por autoridad Mobile (supersession)

Invariante: **como máximo una `DeveloperSession` no revocada por
`MobileTrustedDevice`** (usuario + instalación). Como toda
`MobileAuthSession` pertenece a exactamente un dispositivo, esto implica
también "como máximo una por `mobile_session_id`", y es estrictamente más
fuerte.

Al abrir (`open_developer_session`), dentro de una sola transacción:

1. revalida autoridad (política explícita, sesión Mobile, dispositivo,
   credencial biométrica real);
2. toma `SELECT ... FOR UPDATE` sobre la fila del dispositivo
   (`_lock_device`, el mismo lock de BIOMETRIC-1/2), que serializa dos
   aperturas concurrentes del mismo dispositivo y también el logout;
3. bloquea y revoca (`UPDATE ... WHERE revoked_at IS NULL`) toda
   `DeveloperSession` aún abierta del dispositivo: `superseded` si seguía
   vigente, `expired` si ya había vencido sin que nadie la consultara;
4. inserta la nueva sesión;
5. audita: `developer_session.revoked` con `revocation_reason = superseded`
   y `superseded_by_session_id` por cada anterior, y
   `developer_session.opened` con `superseded_session_ids`;
6. commit.

Backstop de almacenamiento: el índice único parcial
`uq_developer_sessions_active_device`. Si alguna ruta futura escapara al
lock, el INSERT falla (`IntegrityError` → rollback → HTTP 409) en vez de dejar
dos sesiones vivas.

Por qué lock + índice y no sólo "buscar y revocar": bajo `READ COMMITTED`,
dos transacciones concurrentes sin lock no ven la fila de la otra y ambas
insertarían. El lock de dispositivo hace que la segunda espere, vea la
primera ya confirmada y la supersede; el índice garantiza el invariante aun
ante un error de programación. Verificado con PostgreSQL real
(`test_postgresql_concurrent_double_open_leaves_exactly_one_active_session`,
2 hilos con barrera × 3 rondas); contra el código anterior el mismo test deja
2 sesiones activas.

Todas las revocaciones (lock, expiración perezosa, pérdida de autoridad,
supersession) usan un `UPDATE` condicional (`WHERE revoked_at IS NULL`):
sólo la transacción que realmente revoca audita, así una carrera nunca
duplica auditoría ni sobrescribe la razón ganadora.

Política para otras `MobileAuthSession` legítimas:

| Caso | Resultado |
|---|---|
| "Extender con biometría" en la misma sesión Mobile | La anterior queda `superseded`; su token responde `active: false` |
| Otra `MobileAuthSession` del mismo usuario **en el mismo dispositivo** (p.ej. un segundo login sin logout) | Abrir Developer desde ella supersede la de la primera sesión |
| El mismo usuario en **otro dispositivo** | Independiente: cada dispositivo puede tener su propia `DeveloperSession` |
| Rotación de refresh de la sesión Mobile | La `DeveloperSession` muere (su `mobile_session_id` quedó revocado) |

La futura `ShellSession` **no** se reinicia al superseder una
`DeveloperSession`: se reengancha a la nueva (contrato DEV-1, abajo).

## Endpoints

Todos bajo `/api/mobile/v1/developer/session`, router
`backend/app/routers/mobile_developer.py`, incluidos vía
`include_api_router(..., prefix="/api")` — igual que el resto de Mobile,
por lo que el gate global `enforce_api_access` ya exige un Mobile Bearer
token válido (`mobile.access`) en las tres rutas antes de que el propio
handler se ejecute.

### `POST /session` — abrir Developer

- Auth: `Authorization: Bearer <mobile access token>` +
  `require_mobile_developer_capability(DEVELOPER_ACCESS)` (política
  explícita; `"*"` solo → 403).
- Body: `{"biometric_credential": "<opaco>"}`.
- 200: `{"developer_token": "...", "expires_at": "...", "session_id": N}`.
- 403 si el actor no es interno o no tiene `developer.access` explícito.
- 409 sólo si el backstop `uq_developer_sessions_active_device` rechaza una
  segunda sesión activa (no debería ocurrir con el lock de dispositivo).
- Supersede cualquier `DeveloperSession` abierta del mismo dispositivo.
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
- Binding estricto: el token sólo se reconoce si
  `record.user_id == context.user.id`,
  `record.mobile_session_id == context.mobile_session_id` **y**
  `record.device_id == mobile_session.device_id`. Antes del endurecimiento
  sólo se comparaban usuario y dispositivo, por lo que otra
  `MobileAuthSession` vigente del mismo usuario en el mismo dispositivo podía
  consultar (y bloquear) el token de la primera; ahora lo ve como inexistente.
- Re-valida autoridad viva en cada llamada (ver más abajo) — nunca confía
  sólo en `expires_at`/`revoked_at` capturados al emitir.

### `DELETE /session` — bloquear

- Misma auth que GET.
- Idempotente: token ausente/ajeno/ya revocado/no encontrado → 204 igual
  (no hay estado adicional que lograr). "Ajeno" usa el mismo binding estricto
  que GET: un DELETE desde otra sesión Mobile, otro dispositivo u otra
  identidad es un no-op y **no** revoca la sesión del dueño.
- Sólo revoca la `DeveloperSession` — nunca `MobileAuthSession` ni la
  biometría.

### Guard para operaciones Developer futuras (DEV-1+)

`authorize_developer_operation(db, context, developer_token, capability)` y
su forma dependency `require_developer_session(capability)` (en
`app/core/mobile/developer.py`; no montado en ninguna ruta en DEV-0; DEV-1A
lo monta en `GET /developer/broker/health` con `developer.system.read`, ver
[`MOBILE_DEVELOPER_BROKER.md`](MOBILE_DEVELOPER_BROKER.md)) son
la única puerta aceptable para cualquier operación privilegiada futura.
Exigen **ambas**:

1. una `DeveloperSession` viva y ligada a la misma autoridad Mobile (mismo
   binding que GET, más `_check_live`);
2. la capacidad granular específica (`developer.database.read`,
   `developer.shell.access`, …) según la política explícita —
   `developer.access` por sí solo no basta.

Invariante: **ninguna herramienta DEV-1 confía en el booleano
`isDeveloperUnlocked` del cliente.** Y a diferencia del sondeo de estado:

```
GET  /developer/session        token inválido → 200 {"active": false}
POST /developer/database/query token inválido → 401 (rechazo)
                               sin capacidad granular → 403
```

(`/database/query` no existe; el test lo monta en una app FastAPI de prueba
sólo para demostrar el contrato.)

## Revalidación en cada uso (no sólo al emitir)

`developer.py::_check_live` re-deriva, en cada `GET`, si la
`DeveloperSession` sigue siendo autoridad viva:

- `expires_at` no vencido;
- `MobileAuthSession` asociada sigue vigente (no revocada/expirada), es
  `internal` y sigue perteneciendo al mismo usuario/dispositivo;
- `MobileTrustedDevice` sigue activo y no revocado;
- `User` sigue activo/`ACTIVE` e `internal`;
- `developer.access` **explícito** sigue presente (`"*"` no cuenta).

Una expiración o pérdida de autoridad recién detectada se revoca de forma
perezosa (`revoked_at`/`revocation_reason` se escriben en ese momento) y se
audita — no se necesita un job de barrido aparte.

## Auditoría

Vía la autoridad canónica existente (`app/services/audit_logs.py::write_audit_log`,
tabla `audit_logs`; no se inventó una segunda plataforma de auditoría).
Eventos: `developer_session.opened`, `developer_session.revoked`,
`developer_session.expired`. Datos: `user_id`, `entity="developer_session"`,
`entity_id` (id de la fila), `new_values={"device_id", "mobile_session_id", ...}`
más, según el evento: `revocation_reason` (`expired`, `user_lock`,
`authority_revoked`, `superseded`) en revoked/expired,
`superseded_by_session_id` en la revocación por supersession y
`superseded_session_ids` en `opened`.
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
isDeveloperAvailable    // hasDeveloperCapability(user): actor interno + developer.access exacto ("*" no basta)
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

Una segunda llamada (p.ej. "Extender con biometría") abre una sesión nueva
que supersede la anterior server-side; el provider reemplaza el token local.

Cold start (proceso matado) siempre vuelve bloqueado: no hay nada que leer,
el token nunca se persistió.

### Expiración y warning

El countdown es local (deriva de `expires_at`, no hace polling continuo al
backend). A ≤60s y >0s se muestra exactamente un warning por ciclo
(`showExpirationWarning`), con dos acciones: "Extender con biometría"
(vuelve a llamar `unlockDeveloper()`, produce una `DeveloperSession` nueva)
o "Bloquear ahora" (`lockDeveloper()`). Al llegar a 0, el token se olvida
localmente sin llamar al backend (el backend expira la misma fila de forma
independiente si se la vuelve a consultar).

### Logout y pérdida de capacidad

`DeveloperProvider` deriva `canHoldDeveloper = sesión Mobile presente AND
isDeveloperAvailable`. En cuanto pasa a `false` —logout, **o** pérdida de la
capacidad explícita tras refrescar el usuario (p.ej. quedar sólo con `"*"`,
cambio de rol)— bloquea localmente de inmediato, sin esperar el countdown
ni ninguna respuesta, e intenta un DELETE best-effort con la credencial Mobile
que quede (la actual o, tras logout, la que abrió la sesión Developer).
Una carrera "logout/pérdida de capacidad mientras `unlockDeveloper()` sigue
esperando biometría/red" se resuelve con un contador de versión: si la
versión cambió cuando la promesa resuelve, la `DeveloperSession` recién
abierta se revoca (best-effort) y el estado local nunca se resucita
unlocked.

El efecto depende de `[canHoldDeveloper, discardDeveloper]` (callback
estable basado en refs): ya no existe el `eslint-disable` que ocultaba el
warning `missing dependency: clearLocal`.

### Reconciliación por lifecycle (sin polling)

El countdown local es sólo UX; el backend es la autoridad. Con un token
Developer en memoria, el provider consulta `GET /developer/session`
**únicamente** en estos eventos discretos:

| Evento | Qué pasa |
|---|---|
| `AppState` → `active` (vuelta a foreground) | GET; `active: false` → limpia Developer |
| Entrada/reentrada al Developer Center | La pantalla llama `refreshDeveloperStatus()` una vez por montaje (nunca por render) |
| Cambio del access token Mobile (rotación de refresh) | GET con el token nuevo; el backend responde `active: false` porque el token Developer quedó ligado a la generación anterior |

Reglas:

- sin token Developer en memoria no se envía nada; `background`/`inactive`
  no consultan;
- un solo listener `AppState` por vida del provider, removido al desmontar;
  el callback es estable y lee refs (sin closures obsoletos);
- reconciliaciones simultáneas del mismo token se deduplican;
- una respuesta tardía se descarta si entretanto hubo lock, logout,
  pérdida de capacidad o un token nuevo ("Extender");
- `active: true` re-sincroniza el reloj con `expires_at` del servidor sin
  re-armar un warning ya mostrado en ese ciclo;
- **fail-closed**: un error de red al reconciliar bloquea localmente
  (siempre se puede volver a desbloquear con biometría).

Casos cubiertos: revocación de `developer.access`, usuario deshabilitado,
dispositivo revocado, sesión invalidada/superseded en backend y vuelta de
background — todos se reflejan como `active: false` en la siguiente
reconciliación.

## UI — pantalla Developer (placeholder)

`myc-mobile/app/(technician)/developer.tsx`. Tarjeta "Desarrollador" en
Home visible sólo con la capacidad Developer explícita (`canAccessDeveloper`
en `mobile-capabilities.ts`, vía `hasDeveloperCapability`; `"*"` solo no la
muestra). Locked: "Developer / Acceso protegido" + "Desbloquear con
biometría" (etiqueta genérica: el SO decide Face ID/Touch ID/huella).
Al montarse reconcilia una vez el estado con el backend. Unlocked:
"Developer Center", countdown "Sesión activa · MM:SS restantes", cinco tarjetas "Próximamente" (Base de
datos, Terminal, Logs, Servicios, Git) y "Bloquear Developer". Ninguna
herramienta real se implementó.

## Contrato futuro — `ShellSession` (DEV-1+, NO implementado aquí)

Documentado para que DEV-1 no tenga que re-derivar estas decisiones:

- `DeveloperSession` TTL: 10 min. Warning Mobile a 60s.
- Extender (biometría) → nueva `DeveloperSession` que **supersede** la
  anterior → la `ShellSession` futura **no se reinicia**, se reengancha a la
  nueva `DeveloperSession` y sigue siendo el mismo proceso PowerShell. La
  expiración/supersession de `DeveloperSession` y el lifecycle de
  `ShellSession` son deliberadamente independientes.
- Cada operación del broker/consola se autoriza server-side con
  `authorize_developer_operation` (DeveloperSession viva + capacidad
  granular), nunca con el estado del cliente.
- Si `DeveloperSession` expira: **no** se mata la `ShellSession` de
  inmediato. Comportamiento DEV-1: la terminal UI queda bloqueada, ningún
  stdin/comando nuevo se acepta, pero el shell sigue vivo server-side en
  estado detached/locked durante un **grace period de 15 minutos**. Dentro
  de ese periodo, una nueva biometría → nueva `DeveloperSession` → reattach a
  el mismo `shell_session_id` (mismo cwd/proceso/psql si sigue vivo). Pasado
  el grace period, el broker termina el proceso PowerShell.
- Un comando/proceso ya en ejecución cuando `DeveloperSession` expira
  **no** se mata sólo por eso — se perdería control/input sobre un trabajo
  legítimo en curso; puede seguir corriendo mientras la `ShellSession` siga
  dentro del grace period.
- KILL inmediato de la futura `ShellSession` (nunca grace period) si:
  logout MYC, usuario deshabilitado, `MobileTrustedDevice` revocado,
  capacidad Developer explícita revocada, "Cerrar terminal" explícito, apagado/reinicio
  del broker, o cualquier revocación de seguridad equivalente.

## Qué NO se tocó

BIOMETRIC-1 (arquitectura de sesión Mobile), rotación de refresh,
`PushDevice`, comunicaciones en tiempo real, LAB, tickets, certificados,
facturas, field sheets, EAS, proyecto iOS nativo, firma de builds, Pods,
servicios Windows existentes, configuración de Cloudflare.

## Validación de esta fase

Ver `docs/BACKUP_ESTADO_ACTUAL.md` (corte 2026-09-22) para resultados
exactos. Resumen del endurecimiento:

- Backend: `tests/test_mobile_developer_session.py` pasa de 24 a 44 casos
  (política explícita, supersession, auditoría sin secretos, binding por
  sesión/dispositivo/identidad, rotación, logout, guard DEV-1+, backstop del
  índice y concurrencia PostgreSQL real). 10 de los nuevos fallan contra el
  código previo al endurecimiento, además del test PostgreSQL de concurrencia.
- Mobile: `DeveloperProvider.test.ts` ejecuta la política real y cubre
  pérdida de capacidad, foreground, rotación, dedupe, respuestas tardías,
  fail-closed, listener único y ausencia de polling; pantalla y
  capabilities actualizadas.
- `alembic heads` = `c4d8e2f1a7b3` (único).
- Mobile: dos errores TypeScript preexistentes y ajenos en
  `src/realtime/realtime-client.ts`, no tocados.
