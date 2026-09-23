> Estado: DEV-1A MERGEADO en `main` (PR #8, `5bf2349`). DEV-1B EN REVISIÓN (rama `feat/mobile-developer-named-pipe-dev1b`; primera ejecución real en Windows FALLÓ por un defecto ya corregido en el worktree, sin commit; **pendiente re-ejecución de la suite Windows**, NO cerrado)

> Tipo: Arquitectura vigente

> Corte: 2026-09-22 — DEV-1A: frontera Broker + contrato versionado. DEV-1B: adapter Windows Named Pipe + host del Broker + frontera de identidad Windows

# Developer Broker de MYC (DEV-1)

Este documento es la autoridad del **Developer Control Plane ↔ Developer
Broker**. La autoridad de usuario (quién puede operar Developer) sigue
siendo exclusivamente DEV-0:
[`MOBILE_DEVELOPER_AUTHORITY.md`](MOBILE_DEVELOPER_AUTHORITY.md). Este
documento no la redefine.

Cada sección distingue **IMPLEMENTADO** (DEV-1A mergeado; DEV-1B en revisión)
de **DISEÑO FUTURO**. Nada marcado como futuro existe en código.
**Nada de DEV-1B se ha ejecutado todavía contra Named Pipes reales**: en
macOS se validó con un puerto Win32 falso (ver "Validación").

## Arquitectura objetivo

```
MYC Mobile
    │ HTTPS/WSS (mismo túnel que el resto de Mobile)
    ▼
FastAPI — Developer Control Plane
    │ DeveloperSession viva + capacidad Developer explícita (DEV-0)
    ▼
BrokerClient            (app/developer_broker/client.py)
    │ BrokerTransport   (puerto; app/developer_broker/transport.py)
    ▼
WindowsNamedPipeTransport (app/developer_broker/windows_pipe.py)
    │ \\.\pipe\<nombre lógico>, framing 4 bytes + DACL explícita + identidad del servidor verificada
    ▼
NamedPipeBrokerListener (host: python -m app.developer_broker.host)
    ▼
MYC Developer Broker    (BrokerServer, proceso/servicio separado)
    ▼
[futuro: ShellSession / operaciones estructuradas]
```

Separación obligatoria: **ERP ≠ Broker ≠ shell**. FastAPI no es, ni
contiene, un shell remoto.

## Trust boundary y responsabilidades

| | FastAPI (Developer Control Plane) | Developer Broker |
|---|---|---|
| Autentica | Al **usuario** (Mobile Bearer + `X-MYC-Developer-Token`) | Al **proceso llamante** (ACL del pipe + HMAC del mensaje) |
| Autoriza | `require_developer_session(capability)` / `authorize_developer_operation` (DEV-0, política exact-match) | Sólo su propio contrato: versión, operación registrada, payload |
| Conoce | JWT, roles, DeveloperSession, biometría, auditoría ERP | Nada de eso: ni JWT, ni roles, ni wildcard, ni biometría, ni SQLAlchemy |
| Anti-replay | — | Propietario del estado (nonce + request_id) |

El Broker **no** valida JWT, no consulta roles ERP, no implementa wildcard,
no valida biometría, no abre DeveloperSession y no decide si
`developer.shell.access` corresponde a un usuario. FastAPI autoriza al
usuario **antes** de tocar el `BrokerClient`.

Aislamiento verificado por test (`test_broker_package_is_decoupled_from_erp_frameworks_and_authorities`):
`app/developer_broker/` sólo importa stdlib y a sí mismo — nunca
`sqlalchemy`, `fastapi`, `pydantic`, `app.core`, `app.models`,
`app.services`, `app.routers`, `app.schemas` ni `app.realtime`.

## Protocolo (IMPLEMENTADO)

`app/developer_broker/protocol.py`. Protocolo `myc.developer-broker`,
versión `1` (`SUPPORTED_VERSIONS = {1}`). Cada frame es un objeto JSON
(máx. 64 KiB). DTOs explícitos (`BrokerRequest`, `BrokerResponse`,
`BrokerHealth`); nunca se envían objetos SQLAlchemy ni modelos FastAPI.

Request:

```
protocol    "myc.developer-broker"
version     1
kind        "request"
request_id  32 hex (uuid4)
timestamp   entero, ms epoch
nonce       32–64 hex (secrets.token_hex(16))
operation   nombre estructurado  ^[a-z][a-z0-9_]*(\.[a-z][a-z0-9_]*)+$  (≤64)
payload     objeto JSON (contrato propio de cada operación)
signature   64 hex — HMAC-SHA256
```

Response:

```
protocol, version, kind="response", request_id (o null si el request era ilegible),
timestamp, status ("ok" | "error"), result (objeto | null),
error ({"code", "message"} | null), signature
```

Validación estricta: conjunto de campos **exacto** (campos extra o faltantes
→ `malformed`), claves JSON duplicadas rechazadas, `NaN`/`Infinity`
rechazados, `version`/`timestamp` deben ser enteros (no `bool`, no
`float`). `operation` es un identificador estructurado, nunca texto libre:
no existe ningún campo que acepte un string de comando.

### Operaciones

| Operación | Estado | Payload | Resultado |
|---|---|---|---|
| `broker.health` | IMPLEMENTADO | `{}` exacto (cualquier otra cosa → `invalid_payload`) | `status`, `protocol`, `protocol_version`, `supported_versions`, `instance_id` (uuid aleatorio por proceso), `timestamp`, `operations`, `features` |
| `shell.*`, `database.*`, `git.*`, `alembic.*`, `services.*`, `logs.*` | RESERVADO (`RESERVED_NAMESPACES`), sin handler | — | `unknown_operation` |

`broker.health` no ejecuta nada y no revela hostname, rutas, entorno,
configuración ni credenciales.

### Códigos de error en el wire

`malformed`, `unsupported_version`, `unauthenticated`,
`unknown_operation`, `invalid_payload`, `unavailable`, `internal_error`.
Los mensajes son textos fijos por código, nunca el texto de una excepción.
Un fallo inesperado de un handler responde `internal_error` sin traceback.

## Autenticación FastAPI → Broker (IMPLEMENTADO en el contrato)

No se confía en `127.0.0.1`, `localhost` ni en "otro proceso de la misma
máquina". Defensa en dos capas:

1. **ACL del SO** sobre el Named Pipe (sólo la identidad del servicio ERP
   puede conectar) — DISEÑO FUTURO, parte del adapter Windows.
2. **HMAC de aplicación** — IMPLEMENTADO:
   - `HMAC-SHA256` (stdlib `hmac`/`hashlib`), sin criptografía propia.
   - Firma sobre la **representación canónica** de todos los campos salvo
     `signature`: `json.dumps(sort_keys=True, separators=(",", ":"),
     ensure_ascii=True, allow_nan=False)`. Nunca concatenaciones.
   - Comparación constant-time (`hmac.compare_digest`).
   - **Requests y responses firmados**: el cliente rechaza respuestas sin
     firma válida, ligadas a otro `request_id` o fuera de ventana (protege
     contra un proceso que suplante el pipe). El cliente **autentica antes
     de interpretar**: `decode_frame` → `verify_signature` →
     `parse_response`; un frame no autenticado nunca se interpreta como
     respuesta Broker. `kind` está firmado: una respuesta firmada no puede
     reinyectarse como request.
   - El resultado de `broker.health` se valida con **contrato exacto** en
     el cliente (`_health_from_result`): exactamente `status`, `protocol`,
     `protocol_version`, `supported_versions`, `instance_id`, `timestamp`,
     `operations`, `features`; `status == "ok"`, `protocol` propio,
     enteros reales (un `bool` nunca cuenta como entero), `timestamp > 0`,
     `supported_versions` lista no vacía, `instance_id` = 32 hex en
     minúsculas (`uuid4().hex`), `operations`/`features` = `list[str]`. Sin
     coerciones.
   - Secreto dedicado ERP↔Broker (`BrokerSecret`, mínimo 32 bytes): sólo
     de configuración externa (`DEVELOPER_BROKER_SECRET`), nunca en Git,
     nunca hardcodeado; `repr`/`str` → `BrokerSecret(<redacted>)`; nunca
     en logs, errores, auditoría ni respuestas (verificado por test).

Ventana temporal **half-open**: `timestamp ∈ (now − 30 s, now + 5 s]`
(ambos procesos comparten reloj de host; el cliente aplica la misma
ventana a las respuestas). El borde viejo es exclusivo a propósito: la
entrada anti-replay de un request aceptado expira en
`aceptación + 30 s + 5 s` y se purga cuando `expires <= now`; incluso un
frame aceptado con el skew futuro máximo (`timestamp = aceptación + 5 s`)
ya es viejo exactamente en ese instante (`timestamp == now − 30 s` →
rechazado), así que nunca queda válido tras desaparecer del store
(`test_frame_accepted_with_max_future_skew_cannot_be_replayed_after_its_replay_entry_expires`).

Orden del pipeline del Broker (`BrokerServer.process`):

1. decodificación estricta → `malformed`
2. protocolo / versión / campos / formatos → `malformed` | `unsupported_version`
3. firma HMAC → `unauthenticated`
4. ventana de timestamp → `unauthenticated`
5. nonce y request_id no vistos → `unauthenticated`
6. operación registrada → `unknown_operation`
7. contrato del payload → `invalid_payload`
8. handler

Todo fallo de autenticación (firma, timestamp viejo o futuro, replay) se
reporta en el wire como `unauthenticated`, sin indicar qué parte falló. La
razón precisa (`signature_mismatch`, `timestamp_expired`,
`timestamp_in_future`, `nonce_replay`, `request_id_replay`) sólo queda en
el log interno del Broker, que nunca registra el frame, la firma, el
payload ni el secreto.

Riesgo aceptado y documentado: el Broker firma también sus respuestas de
error a callers no autenticados (con `request_id` sólo si es un hex
válido). Esa respuesta no puede reutilizarse como request (`kind`) y sólo
contiene un código de error genérico.

## Anti-replay (IMPLEMENTADO)

`app/developer_broker/replay.py`. Puerto `ReplayGuard`; implementación
`InMemoryReplayGuard` para **una única instancia de Broker**:

- registra `nonce` y `request_id` de forma atómica (lock), con expiración
  `now + (30 s + 5 s)`; purga en cada uso;
- **acotado** (`max_entries`, 10 000 por defecto). Lleno → falla cerrado
  (`unavailable`); nunca desaloja entradas vigentes (eso reabriría replay);
- sólo se escribe **después** de validar firma y timestamp: un caller no
  autenticado no puede llenarlo.

El estado anti-replay pertenece al Broker. Un restart del Broker lo vacía;
el riesgo residual queda acotado por la ventana temporal (un frame
capturado de más de 30 s se rechaza igual; cubierto por test). Sin Redis ni
infraestructura externa.

## Transporte

| Adapter | Estado |
|---|---|
| `BrokerTransport` (puerto: `exchange(frame, timeout_seconds) -> frame`) | IMPLEMENTADO (DEV-1A) |
| `InMemoryBrokerTransport` | IMPLEMENTADO — **sólo tests/desarrollo del contrato**; la configuración de FastAPI no puede seleccionarlo |
| `WindowsNamedPipeTransport` + `NamedPipeBrokerListener` (`windows_pipe.py`) | IMPLEMENTADO en código (DEV-1B) — **sin validar aún en Windows real** |

El transporte sólo mueve bytes opacos; la autenticación de mensajes es
extremo a extremo entre `BrokerClient` y `BrokerServer` (HMAC, DEV-1A, sin
cambios). **No existe fallback TCP/loopback**: no se abre ningún puerto ni
socket; fuera de Windows el adapter falla cerrado (`platform_unsupported`).

### Dependencia: pywin32 (DEV-1B)

`pywin32==312; sys_platform == "win32"` en el `requirements.txt` canónico
de la raíz (`backend/requirements.txt` está vacío y no es canónico).
312 es la versión vigente en PyPI (publicada 2026-06-04) y publica wheels
`win_amd64` para CPython 3.12 (versión documentada del backend) y 3.14
(venv local). El marker hace que macOS/Linux la ignoren (`pip` reporta
"Ignoring pywin32"). Se eligió pywin32 frente a `ctypes`,
`multiprocessing.connection`, sockets o HTTP local porque expone
directamente `CreateNamedPipe`/`CreateFile`, DACL, `PIPE_REJECT_REMOTE_CLIENTS`,
`FILE_FLAG_FIRST_PIPE_INSTANCE`, `GetNamedPipeServerProcessId`,
tokens/SIDs y errores Win32. Se importa perezosamente sólo dentro del
puerto `_PyWin32Api` (`load_win32_api`), así que el backend importa en
cualquier plataforma sin mocks globales.

### Nombre del pipe

La configuración sólo aporta un **nombre lógico**
(`DEVELOPER_BROKER_PIPE_NAME`, p. ej. `MYCDeveloperBroker`); la ruta la
construye siempre el código: `\\.\pipe\<nombre>` (servidor local `.`,
namespace de pipes). Regla: `^[A-Za-z][A-Za-z0-9_-]{2,63}$` (3–64
caracteres). Se rechaza —no se "limpia"— cualquier `/`, `\`, `.`/`..`,
`:`, espacios, control, no-ASCII, rutas completas, UNC/host remoto,
namespaces alternativos (`Global\`, `Local\`) y nombres de dispositivo DOS
(`CON`, `PRN`, `AUX`, `NUL`, `COMn`, `LPTn`, …). El nombre no se registra
en logs.

### Framing

`framing.py` (propiedad del transporte, no del protocolo): cada frame viaja
como **longitud `uint32` big-endian + payload**. `0 < longitud <=
MAX_FRAME_BYTES` (64 KiB) se valida **antes** de pedir un solo byte del
payload (nunca se reserva memoria según una longitud no validada); lecturas
exactas en bucle, sin suponer que un `ReadFile` equivale a un frame; EOF o
pipe roto prematuro → `connection_closed`; longitud 0 → `frame_empty`;
excedida → `frame_too_large`. Exactamente un request y una response por
conexión. El JSON/HMAC de DEV-1A no cambia. El pipe usa modo byte
(`PIPE_TYPE_BYTE | PIPE_READMODE_BYTE`).

### Seguridad del pipe (servidor)

`CreateNamedPipe` con:

- `PIPE_ACCESS_DUPLEX | FILE_FLAG_OVERLAPPED`, y **`FILE_FLAG_FIRST_PIPE_INSTANCE`
  en la primera instancia**: si el nombre ya existe (otro proceso lo creó
  antes — pipe-squatting), el Broker **no arranca** (`pipe_name_in_use`,
  exit code 2); nunca se conecta a él, nunca lo reemplaza, nunca elige
  otro nombre.
- **`PIPE_REJECT_REMOTE_CLIENTS`** en todas las instancias.
- Tras aceptar una conexión, el listener crea la **siguiente instancia
  antes** de entregar la actual a un worker: el nombre nunca queda sin
  dueño mientras el Broker sirve.
- **DACL explícita** (nunca la DACL por defecto), owner = SID del servicio
  Broker, exactamente dos ACE *access-allowed*:

| SID | Máscara | Derechos |
|---|---|---|
| `DEVELOPER_BROKER_SERVICE_SID` | `0x0012019F` | `FILE_READ_DATA`, `FILE_WRITE_DATA`, `FILE_CREATE_PIPE_INSTANCE`, `FILE_READ_EA`, `FILE_WRITE_EA`, `FILE_READ_ATTRIBUTES`, `FILE_WRITE_ATTRIBUTES`, `READ_CONTROL`, `SYNCHRONIZE` (= `FILE_GENERIC_READ` ∪ `FILE_GENERIC_WRITE`, escrito como derechos específicos) |
| `DEVELOPER_BROKER_CLIENT_SID` | `0x00100083` | `FILE_READ_DATA`, `FILE_WRITE_DATA`, `FILE_READ_ATTRIBUTES`, `SYNCHRONIZE` |

  La máscara del Broker **no es privilegio extra por comodidad**: cada
  instancia adicional de `CreateNamedPipe` se evalúa contra esta DACL por
  los derechos implícitos del modo `PIPE_ACCESS_DUPLEX` (`FILE_GENERIC_READ`
  \| `FILE_GENERIC_WRITE` \| `SYNCHRONIZE`) más `FILE_CREATE_PIPE_INSTANCE`.
  La máscara previa a la auditoría (`0x00120087`) omitía `FILE_READ_EA`,
  `FILE_WRITE_EA` y `FILE_WRITE_ATTRIBUTES`, por lo que la segunda instancia
  habría fallado (corregido; pendiente de confirmar en Windows real con
  `test_subsequent_create_named_pipe_instances_succeed_under_the_explicit_dacl`).
  Sin `GENERIC_*`, `WRITE_DAC`, `WRITE_OWNER` ni `DELETE`. El cliente ERP
  **no** recibe `FILE_CREATE_PIPE_INSTANCE`: en un pipe ese bit es el mismo
  que `FILE_APPEND_DATA`, así que conceder `GENERIC_WRITE` le permitiría
  crear instancias servidor propias (squatting). Sin `Everyone`,
  `Authenticated Users`, `Users`, `Guests` ni `Administrators`.
- **SYSTEM**: no se añade implícitamente. Hoy `MYCBackend.exe` corre como
  `LocalSystem`, por lo que en el despliegue actual
  `DEVELOPER_BROKER_CLIENT_SID` sería `S-1-5-18` — es la única razón por la
  que SYSTEM puede aparecer, y sólo como identidad **cliente** configurada.
  Como identidad del Broker se rechazan `S-1-5-18` (LocalSystem),
  `S-1-5-19` (LocalService) y `S-1-5-20` (NetworkService): el Broker
  requiere una identidad dedicada.

Validación de SIDs: sólo SIDs literales `S-1-…` (no alias SDDL como `SY`
o `WD`), convertidos y canonizados con `ConvertStringSidToSid` /
`IsValid` / `ConvertSidToStringSid` (API Windows, no regex propio). Se
rechazan identidades amplias (Everyone, Authenticated Users, Users, Guests,
Administrators, Interactive, Network, Service, Anonymous, cuentas locales,
…). En el host y en FastAPI ERP y Broker deben ser **SIDs distintos**
(`sids_not_distinct`).

### Identidad del servidor (cliente → servidor)

HMAC autentica el protocolo, pero no impide que un proceso local cree antes
un pipe falso y **lea** requests. Por eso, tras abrir el handle y **antes de
escribir un solo byte**, `WindowsNamedPipeTransport`:

1. obtiene el PID del servidor con `GetNamedPipeServerProcessId`;
2. abre ese proceso con `PROCESS_QUERY_LIMITED_INFORMATION`;
3. abre su token con `TOKEN_QUERY` y lee `TokenUser`;
4. compara el SID canónico con `DEVELOPER_BROKER_SERVICE_SID`.

Si no coincide (`server_identity_mismatch`) o no puede verificarse
(`server_identity_unverifiable`, incluido el caso de que la función no
exista en la build de pywin32): cierra el handle y **no escribe nada**.
PID, usuario, SID real, rutas y handles nunca salen del adapter (ni HTTP,
ni AuditLog, ni logs: sólo códigos fijos).

El cliente abre el pipe con `SECURITY_SQOS_PRESENT | SECURITY_IDENTIFICATION`:
el Broker puede **identificar** al ERP (que corre como LocalSystem) pero
nunca **suplantarlo**.

### Identidad del cliente (servidor → cliente)

La DACL es la barrera obligatoria. Como defensa en profundidad —misma
identidad, no una segunda arquitectura— el listener, tras leer el frame
(Windows sólo permite `ImpersonateNamedPipeClient` después de leer datos;
el frame está acotado a 64 KiB y **no se procesa** hasta verificar),
suplanta al cliente a nivel *identification*, lee su `TokenUser`, hace
`RevertToSelf` y descarta la conexión sin procesar ni responder si no es
`DEVELOPER_BROKER_CLIENT_SID` (`client_identity_mismatch`).

| Capa | Garantía |
|---|---|
| DACL | Quién puede abrir el pipe (sólo ERP y Broker) |
| Verificación PID/token del servidor | Que FastAPI no entregue payload a un servidor impostor |
| Verificación del token del cliente | Defensa en profundidad de la misma identidad de la DACL |
| HMAC (DEV-1A) | Autenticidad e integridad de cada mensaje del protocolo |

### Timeouts y errores

Toda E/S es *overlapped* con un deadline real derivado de
`DEVELOPER_BROKER_TIMEOUT_SECONDS` (cliente, 5 s) o
`DEVELOPER_BROKER_IO_TIMEOUT_SECONDS` (por conexión en el host, 5 s):
`WaitNamedPipe` con el tiempo restante (nunca 0, que significaría "espera
por defecto"), `WaitForSingleObject` + `CancelIo` al vencer. Nunca hay
espera infinita. Razones internas estables: `pipe_not_found`, `timeout`,
`access_denied`, `pipe_open_failed`, `server_identity_mismatch`,
`server_identity_unverifiable`, `connection_closed`, `frame_too_large`,
`frame_empty`, `io_failed`, `transport_error`. El Control Plane sigue
devolviendo el mismo 503 opaco (`Developer Broker no disponible`) y sólo
registra/audita `exc.code` (`unavailable`); ningún WinError, ruta, PID ni
SID llega al cliente HTTP.

### Concurrencia

Una conexión por `exchange`: un request, una response, cierre. El listener
atiende conexiones con un pool acotado (`DEVELOPER_BROKER_MAX_CONNECTIONS`,
1–16, default 4) y un semáforo; cada worker está acotado por el timeout de
E/S, las excepciones se aíslan por conexión y el apagado es determinista
(cierra la instancia pendiente y espera a los workers). Sin multiplexing ni
streaming.

## Configuración (IMPLEMENTADO)

FastAPI (`app/core/config.py`, patrón `Settings`):

| Variable | Default | Nota |
|---|---|---|
| `DEVELOPER_BROKER_ENABLED` | `false` | El ERP arranca normal sin Broker |
| `DEVELOPER_BROKER_TRANSPORT` | `named_pipe` | Único valor aceptado |
| `DEVELOPER_BROKER_PIPE_NAME` | `""` | Nombre lógico, nunca ruta |
| `DEVELOPER_BROKER_SECRET` | `""` (`SecretStr`) | ≥ 32 bytes; sólo secreto externo |
| `DEVELOPER_BROKER_TIMEOUT_SECONDS` | `5` | Deadline real del adapter |
| `DEVELOPER_BROKER_SERVICE_SID` | `""` | SID esperado del servidor del pipe (obligatorio) |
| `DEVELOPER_BROKER_CLIENT_SID` | `""` | Opcional en FastAPI: si se define, el ERP exige correr realmente con ese SID (`client_identity_mismatch`) y que difiera del del Broker |

`build_developer_broker_client` falla cerrado, en este orden: `disabled`,
`secret_missing_or_too_short`, `unknown_transport`, `pipe_name_missing` /
`pipe_name_invalid`, `service_sid_missing`, `platform_unsupported` (fuera
de Windows, aun con `enabled=true`) / `win32_unavailable`, validación de
SIDs. Con todo válido en Windows crea `WindowsNamedPipeTransport` +
`BrokerClient`. Los códigos se registran sólo si pertenecen a la lista fija
`CONFIGURATION_CODES`; nunca el secreto.

Host del Broker: ver la sección siguiente; configuración propia y mínima.

## Host del Broker (IMPLEMENTADO en código, DEV-1B)

`python -m app.developer_broker.host` (`app/developer_broker/host.py`):
proceso independiente, sin FastAPI, SQLAlchemy, Mobile auth,
DeveloperSession, JWT, biometría, `app.realtime` ni `app.core.config`
(cierre de imports verificado por test). **Lee sólo su entorno de proceso,
nunca el `.env` del backend**, así que `DATABASE_URL`, `SECRET_KEY`,
Facturama, SMTP, etc. jamás se cargan en el Broker:

| Variable | Default | Nota |
|---|---|---|
| `DEVELOPER_BROKER_PIPE_NAME` | — | Obligatoria |
| `DEVELOPER_BROKER_SECRET` | — | Obligatoria; mismo secreto que el ERP |
| `DEVELOPER_BROKER_CLIENT_SID` | — | Obligatoria (identidad ERP) |
| `DEVELOPER_BROKER_SERVICE_SID` | — | Obligatoria (identidad propia) |
| `DEVELOPER_BROKER_IO_TIMEOUT_SECONDS` | `5` | 0 < t ≤ 60 |
| `DEVELOPER_BROKER_MAX_CONNECTIONS` | `4` | 1–16 |

Secuencia: valida configuración y SIDs (distintos) → **se niega a correr si
su propio token no es `DEVELOPER_BROKER_SERVICE_SID`**
(`service_identity_mismatch`) → crea la primera instancia (falla si el
nombre existe) → acepta conexiones → apagado limpio con Ctrl+C / Ctrl+Break
/ SIGTERM. Códigos de salida: 0 parada limpia, 2 configuración/identidad, 1
error de ejecución. Sólo registra códigos fijos. Sin daemonización propia,
sin WinSW, sin instalación de servicio, sin registro de Windows: una fase
posterior de despliegue lo envolverá como `MYCDeveloperBroker`.

## Endpoint de diagnóstico (IMPLEMENTADO)

`GET /api/mobile/v1/developer/broker/health`
(`app/routers/mobile_developer.py::read_developer_broker_health`).

- Guard: `require_developer_session("developer.system.read")` — el guard
  canónico DEV-0 (DeveloperSession viva ligada a la misma
  `MobileAuthSession` + capacidad exacta). **No** basta `developer.access`;
  no se usa el guard genérico de permisos ERP; `"*"` y `"developer.*"` no
  la conceden.
- Luego `developer_broker_health` (`app/services/developer_broker.py`)
  usa el `BrokerClient` inyectado por la dependencia
  `get_developer_broker_client` (que nunca lanza: devuelve `None` si el
  Broker no es usable). El router nunca toca el transporte.
- 200: DTO explícito `DeveloperBrokerHealth` (`status`, `protocol`,
  `protocol_version`, `supported_versions`, `broker_instance_id`,
  `broker_timestamp_ms`, `operations`, `features`).
- 401 sin Mobile Bearer / token Developer inválido o bloqueado; 422 sin
  header `X-MYC-Developer-Token`; 403 sin `developer.system.read`
  explícito. En todos esos casos el Broker **no** se contacta.
- 503 `{"detail": "Developer Broker no disponible"}` si no está
  configurado, no responde, el servidor del pipe no es la identidad
  esperada o su respuesta no es auténtica; sin traceback, WinError, PID,
  SID ni detalle de configuración.
- Logging del Control Plane: sólo el código estable (`exc.code`) de un
  `BrokerError`, nunca `exc.reason`. Para configuración sólo se registran
  los códigos de la lista fija `CONFIGURATION_CODES`
  (`app/services/developer_broker.py`); cualquier otro valor se registra
  como `not_configured`. El adapter Windows y el host registran sólo a
  través de `loggable_reason` (`windows_pipe.py`): emite el `reason` o el
  `code` únicamente si pertenecen a la lista fija `LOGGABLE_REASONS`; en
  otro caso registra `unrecognized`. Nunca texto de SO, WinError, ruta del
  pipe, PID, SID, handle ni excepción cruda. El log interno
  del `BrokerServer` conserva su `reason` sanitizado (identificadores fijos,
  nunca frame, firma, payload ni secreto).
- Auditoría (autoridad existente `write_audit_log`):
  `developer.broker.health`, `entity="developer_session"`, `new_values =
  {device_id, mobile_session_id, capability, outcome ("ok"|"unavailable"),
  broker_error}`. Nunca el token Developer, el secreto HMAC, firmas,
  payloads, credenciales biométricas ni contraseñas.
- Inventario HTTP: 537 operaciones (536 + esta), clasificada como el resto
  de `/api/mobile/v1/*` (`mobile_context`, base `mobile.access`); el gate
  fino vive en el endpoint.

## Identidad del servicio Windows

IMPLEMENTADO (DEV-1B, en código): el host exige una identidad dedicada
(rechaza LocalSystem/LocalService/NetworkService y SIDs amplios) y se niega
a correr bajo un token distinto de `DEVELOPER_BROKER_SERVICE_SID`; no
requiere privilegios administrativos.

DISEÑO FUTURO (despliegue): servicio `MYCDeveloperBroker` bajo una cuenta
virtual de servicio (`NT SERVICE\MYCDeveloperBroker`, SID `S-1-5-80-…`) o
cuenta local/gMSA dedicada con least privilege, nunca administrador "por
comodidad"; cualquier capacidad elevada futura se diseñará **por
operación**.

## Ausencias deliberadas (DEV-1A y DEV-1B)

- **Sin shell, sin PowerShell, sin ejecución de procesos**: ni
  `subprocess`, `os.system`, `os.popen`, `shell=True`, `pty`,
  `multiprocessing`, ni binarios de shell. Verificado por AST
  (`test_dev_1a_implementation_executes_no_processes`) y por búsqueda
  textual sobre los archivos tocados.
- Sin API de ejecución arbitraria: no existen `/execute`, `/command`,
  `/powershell`; ningún campo acepta un string de comando.
- Sin sockets, sin puertos (ni 8765, ni 5432, ni 22, ni 3389), sin
  listener TCP/HTTP, sin Cloudflare, sin firewall, sin despliegue, sin
  servicio Windows, sin migraciones. Única dependencia nueva (DEV-1B):
  `pywin32`, sólo Windows. Escaneado por test
  (`test_broker_package_opens_no_network_listener_or_tcp_fallback`).
- **Sin reutilizar el realtime del ERP**: `app/realtime/`
  (`RealtimeHub`, `InMemoryRealtimeHub`, envelope `myc.realtime.v1`) es
  comunicación del ERP; el Broker IPC tiene su propio protocolo,
  lifecycle y trust boundary. Ninguna `ShellSession` vivirá en rooms
  `user:*`/`conversation:*`.

## Compatibilidad con `ShellSession` (DISEÑO FUTURO, DEV-1C+)

DEV-1A/1B no implementan `ShellSession`, pero el contrato no la impide:

- `DeveloperSession` (autorización, ~10 min) ≠ `ShellSession` (proceso /
  contexto persistente en el Broker). El Broker no conoce
  `DeveloperSession`: FastAPI re-autoriza cada operación con DEV-0 y sólo
  entonces habla con el Broker, así que una `ShellSession` puede
  sobrevivir a la expiración/supersession de una `DeveloperSession` y
  reengancharse a la siguiente.
- Contrato ya decidido (ver `MOBILE_DEVELOPER_AUTHORITY.md`): warning ~60 s
  antes; reautenticación biométrica crea nueva autoridad y la misma
  `ShellSession` continúa; expiración normal bloquea control pero no mata
  el shell (grace period de 15 min); eventos de seguridad → kill
  inmediato.
- Operaciones reservadas `shell.*` (p. ej. `shell.create`,
  `shell.attach`, `shell.stdin`, `shell.kill`) se agregarán como handlers
  explícitos con payloads tipados; los eventos de salida continuos
  requerirán extender el puerto de transporte (canal dúplex/stream por
  sesión) o una versión 2 del protocolo — el versionado existe desde v1
  para eso.

## Pendiente

- **Validación de DEV-1B en Windows real** (ver "Validación"): nada del
  adapter se ha ejecutado aún contra Named Pipes, DACL o APIs de identidad
  reales.
- Instalación como servicio Windows (`MYCDeveloperBroker`), WinSW, cuenta
  de servicio dedicada y provisión del secreto/SIDs en el servidor.
- `ShellSession`, PowerShell, streaming (el puerto `exchange` es
  request/response; el streaming requerirá extenderlo o protocolo v2).
- Operaciones estructuradas (`database.*`, `logs.*`, `git.*`,
  `services.*`), cada una con su capacidad Developer granular.
- Rotación del secreto HMAC (`key_id` → nueva versión de protocolo).
- Anti-replay multi-instancia sólo si alguna vez hay más de un Broker.

## Pruebas

- `backend/tests/test_developer_broker_contract.py`: serialización
  canónica, request válida, firma incorrecta/alterada, timestamps viejo y
  futuro, replay de nonce y de request_id, estado anti-replay acotado y
  con expiración, restart, versión desconocida, operaciones desconocidas y
  reservadas, frames malformados, payload inválido, `broker.health`,
  Broker no disponible / no configurado / respuesta no auténtica, no fuga
  del secreto, aislamiento de imports y ausencia de ejecución de procesos.
- `backend/tests/test_mobile_developer_broker_health.py`: endpoint sin
  DeveloperSession, sesión bloqueada, sin `developer.system.read`,
  wildcard ERP (`"*"`, `"developer.*"`), actor cliente, permitido con
  capacidad explícita + auditoría, no configurado, no disponible y secreto
  desalineado (503 sin fugas).
- `backend/tests/test_developer_broker_named_pipe.py` (DEV-1B,
  cross-platform, **con puerto Win32 falso**): validación del nombre del
  pipe, framing (ida y vuelta con lecturas fragmentadas, prefijo excedido
  sin reservar memoria, truncados), flags y DACL como valores, política de
  SIDs, guardia de plataforma, builder FastAPI (sin fallback TCP), orden
  "identidad antes de escribir", cierre de handles, no fuga de errores de
  SO, listener (primera instancia, siguiente instancia antes de servir,
  cliente no autorizado, frames malos, fallos aislados, apagado
  determinista), host (configuración mínima, códigos de salida, cierre de
  imports) y escaneo de red/TCP. **No prueba Named Pipes reales.**
- `backend/tests/test_developer_broker_windows.py` (DEV-1B, **sólo
  Windows**, se omite en otras plataformas): health por pipe real, request
  y response atravesando el pipe, HMAC incorrecto, pipe inexistente,
  timeout real, frames excedidos/truncados, segunda primera-instancia,
  DACL real, SID del servidor esperado y SID incorrecto sin escritura. El
  caso "cliente remoto rechazado" queda omitido explícitamente (requiere
  otro host). Incluye la invariante "las instancias posteriores de
  `CreateNamedPipe` se crean bajo la DACL explícita" con varios
  `broker.health` consecutivos (debe fallar con la máscara `0x00120087`).

## Validación de DEV-1B

Ejecutado en macOS: suites anteriores + cross-platform con puerto Win32
falso (lógica del adapter, no Named Pipes reales).

Primera ejecución real en Windows: commit `0b9572d`, Python 3.14.7 +
pywin32, `test_developer_broker_windows.py` → 5 passed, 6 failed, 1
skipped.

### A. Validado por la primera ejecución real en Windows

- `pywin32` se instala e importa; `load_win32_api` funciona.
- Creación real de la primera instancia con `FILE_FLAG_FIRST_PIPE_INSTANCE`
  y DACL explícita; una segunda "primera instancia" con el mismo nombre se
  rechaza (`pipe_name_in_use`).
- La DACL real del pipe contiene exactamente las dos ACE configuradas
  (`0x0012019F` servicio, `0x00100083` cliente) y ningún SID amplio.
- Pipe inexistente → `pipe_not_found`, rápido y controlado.
- Timeout real del cliente con E/S overlapped (`timeout`).
- Verificación de identidad del servidor: `GetNamedPipeServerProcessId`
  existe en `win32pipe` y, con un SID esperado incorrecto, el cliente
  aborta con `server_identity_mismatch` **sin escribir ningún byte**.

### B. Falló por el defecto de pertenencia de módulo (causa raíz confirmada)

Fallaron las 6 pruebas que pasan por `NamedPipeBrokerListener._serve_connection`:
health por pipe real, instancias posteriores de `CreateNamedPipe`, builder
FastAPI, HMAC incorrecto (0 requests en el handler), y recuperación tras
frame excedido y truncado. El cliente veía `connection_closed` y el
servidor registraba `connection_failed`.

Causa raíz, confirmada con diagnóstico aislado en Windows:
`_PyWin32Api.client_user_sid` llamaba `ImpersonateNamedPipeClient` a través
de `win32pipe`, donde **no existe**; en pywin32 vive en `win32security`. El
`AttributeError` no era `pywintypes.error` ni `BrokerError` y caía en el
manejador genérico antes de invocar al handler. El mismo diagnóstico, usando
`win32security`, confirmó impersonación, token *identification* con
`OpenAsSelf=True`, `TokenUser` = `(PySID, int)`, SID correcto,
`RevertToSelf`, escritura del servidor y lectura del cliente.

Corrección (worktree, sin commit): llamada a través de `win32security`;
un fallo al suplantar → `client_identity_unverifiable` **sin**
`RevertToSelf`; tras suplantar con éxito, `RevertToSelf` exactamente una
vez aunque falle la lectura del token/SID; un fallo de `RevertToSelf` →
`revert_to_self_failed` y el listener deja de aceptar conexiones; prueba
estructural de pertenencia de cada nombre pywin32 a su módulo real.

### C. Pendiente hasta la re-ejecución en Windows tras la corrección

1. Re-ejecutar sin cambios
   `python -m pytest tests/test_developer_broker_windows.py -v -rs`
   (desde `backend\`, cuenta que no sea LocalSystem). Esperado: 11 passed,
   1 skipped. En particular deben pasar las 6 pruebas de B, incluida la
   creación real de instancias posteriores bajo la DACL explícita (la
   máscara `0x0012019F` para instancias adicionales aún no está probada).
2. Prueba manual de proceso separado: consola A con `DEVELOPER_BROKER_*` y
   `python -m app.developer_broker.host` bajo la cuenta del Broker;
   consola B (cuenta ERP) llamando `build_developer_broker_client(...).health()`.
3. Con dos cuentas reales: la cuenta ERP conecta; una tercera cuenta recibe
   `access_denied` (DACL); un servidor impostor bajo otra cuenta provoca
   `server_identity_mismatch` sin bytes escritos; el host se niega a correr
   bajo un SID distinto del configurado.

### D. Requiere un segundo host

- Rechazo de clientes remotos (`PIPE_REJECT_REMOTE_CLIENTS`): la prueba
  sigue omitida explícitamente; un fallo local al abrir
  `\\localhost\pipe\…` no distingue el flag de un servicio Server
  detenido.
