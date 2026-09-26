> Estado: DEV-1A MERGEADO (PR #8, `5bf2349`). DEV-1B MERGEADO (PR #9, `05f4c62`; validado en Windows real: 11 passed, 1 skipped, 0 failed). DEV-1C EN REVISIÓN (rama `feat/mobile-developer-broker-service-dev1c`, sin commit): activos de despliegue del servicio `MYCDeveloperBroker`; **instalación en el servidor Windows pendiente**

> Tipo: Arquitectura vigente

> Corte: 2026-09-25 — DEV-1A: frontera Broker + contrato versionado. DEV-1B: adapter Windows Named Pipe + host del Broker + frontera de identidad Windows. DEV-1C: despliegue como servicio Windows con identidad dedicada (activos + pruebas; sin ejecutar en Windows)

# Developer Broker de MYC (DEV-1)

Este documento es la autoridad del **Developer Control Plane ↔ Developer
Broker**. La autoridad de usuario (quién puede operar Developer) sigue
siendo exclusivamente DEV-0:
[`MOBILE_DEVELOPER_AUTHORITY.md`](MOBILE_DEVELOPER_AUTHORITY.md). Este
documento no la redefine.

Cada sección distingue **IMPLEMENTADO** (DEV-1A y DEV-1B mergeados; DEV-1C
en revisión) de **DISEÑO FUTURO**. Nada marcado como futuro existe en código.
DEV-1B está validado contra Named Pipes reales en Windows (ver "Validación
de DEV-1B"). DEV-1C (despliegue como servicio) sólo se validó fuera de
Windows: sus scripts **no se han ejecutado todavía en el servidor** (ver
"Despliegue como servicio Windows (DEV-1C)").

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
| `WindowsNamedPipeTransport` + `NamedPipeBrokerListener` (`windows_pipe.py`) | IMPLEMENTADO (DEV-1B, PR #9) — validado en Windows real (11 passed, 1 skipped) |

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
  habría fallado (corregido y confirmado en Windows real por
  `test_subsequent_create_named_pipe_instances_succeed_under_the_explicit_dacl`
  en la re-ejecución de `6a9374c`).
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

## Host del Broker (IMPLEMENTADO, DEV-1B)

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
error de ejecución. Sólo registra códigos fijos. Sin daemonización propia.
El host no instala nada: DEV-1C lo envuelve como servicio `MYCDeveloperBroker`
con activos de despliegue externos al paquete (sección siguiente al
endpoint); `host.py` no cambió.

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

IMPLEMENTADO (DEV-1B): el host exige una identidad dedicada (rechaza
LocalSystem/LocalService/NetworkService y SIDs amplios), se niega a correr
bajo un token distinto de `DEVELOPER_BROKER_SERVICE_SID` y no requiere
privilegios administrativos.

DEV-1C (EN REVISIÓN): cuenta virtual de servicio
`NT SERVICE\MYCDeveloperBroker` (SID `S-1-5-80-…` resuelto en el host).
Detalle en la sección siguiente. Cualquier capacidad elevada futura se
diseñará **por operación**, nunca como membresía de Administrators.

## Despliegue como servicio Windows (DEV-1C, EN REVISIÓN)

Activos en `deploy/windows/developer-broker/` (ubicación nueva: el
repositorio no tenía un área de despliegue Windows; `scripts/` es el
toolkit bash de desarrollo). **Validado sólo fuera de Windows**
(`backend/tests/test_developer_broker_deployment.py`); la instalación real
en `ADMIN` sigue pendiente.

```
MYCBackend            LocalSystem, S-1-5-18 (sin cambios)
    │ Named Pipe \\.\pipe\MYCDeveloperBroker + HMAC (DEV-1A/1B, sin cambios)
    ▼
MYCDeveloperBroker    NT SERVICE\MYCDeveloperBroker (cuenta virtual)
    └── broker.health (única operación)
```

| Archivo | Rol |
|---|---|
| `MYCDeveloperBroker.xml.template` | Plantilla WinSW (sólo placeholders; sin `serviceaccount`) |
| `broker_deploy.py` | Decisiones testeables fuera de Windows: plan y política ACL, veredicto de compatibilidad del servicio, INF de `SeServiceLogonRight`, render del XML, bloque gestionado de `backend\.env`, secreto. Sólo stdlib + validadores del propio Broker; no ejecuta procesos |
| `MYCDeveloperBroker.psm1` | Parte Windows: SCM, SIDs, `icacls`, `secedit`, verificaciones de runtime |
| `Install-MYCDeveloperBroker.ps1` | Preflight + instalación/re-aplicación idempotente |
| `Uninstall-MYCDeveloperBroker.ps1` | Rollback acotado y explícito (`ShouldProcess`, `ConfirmImpact=High`) |
| `Test-MYCDeveloperBroker.ps1` | Validación post-instalación de sólo lectura |
| `Set-MYCServicesAcl.ps1` | Endurecimiento de `C:\MYC\Services` (sólo lectura sin `-Apply`) |

### Modelo de identidad

- Cuenta virtual `NT SERVICE\MYCDeveloperBroker`: SID estable, sin
  contraseña, no es LocalSystem/LocalService/NetworkService/`SMM ADMIN`, no
  es miembro de Administrators, ACLable.
- **Registro SCM directo bajo la cuenta virtual**:
  `sc.exe create MYCDeveloperBroker binPath= C:\MYC\Services\developer-broker\MYCDeveloperBroker.exe start= demand obj= "NT SERVICE\MYCDeveloperBroker"`.
  No se usa `MYCDeveloperBroker.exe install` ni `<serviceaccount>`: el
  esquema de `serviceaccount` difiere entre WinSW v2 y v3 y la versión
  instalada en `ADMIN` no se ha verificado; con `sc.exe` la identidad queda
  fijada de forma atómica al crear el servicio y **nunca existe, ni
  transitoriamente, como LocalSystem**. WinSW sigue siendo el binario host
  del servicio (misma convención que `MYCBackend`). No se ejecuta
  `MYCDeveloperBroker.exe refresh` (podría reescribir la configuración del
  SCM); la validación detecta cualquier deriva de `StartName`.
- `sc.exe sidtype MYCDeveloperBroker unrestricted`; acciones de fallo SCM
  `restart/10000/restart/30000/restart/60000`, `reset= 3600`,
  `failureflag 1` (reflejan los `<onfailure>` del XML).
- **SID nunca inventado**: tras crear el servicio se resuelve por dos
  fuentes independientes —`NTAccount.Translate` (LSA) y `sc.exe showsid`
  (SCM)— que deben coincidir y cumplir `S-1-5-80-x-x-x-x-x`; si no, se
  aborta. No hay SIDs de servicio en archivos versionados.
- Cliente ERP: el preflight exige `MYCBackend` con `StartName = LocalSystem`
  y su árbol de procesos con dueño `S-1-5-18`;
  `DEVELOPER_BROKER_CLIENT_SID=S-1-5-18` (el Broker identifica, nunca
  suplanta).
- `SeServiceLogonRight`: se exporta la política efectiva (`secedit /export
  /mergedpolicy /areas USER_RIGHTS`); si ya cubre al Broker (directamente o
  vía `NT SERVICE\ALL SERVICES`, `S-1-5-80-0`, presente por defecto) **no se
  toca nada**. Si no, se aplica con `secedit /configure /areas USER_RIGHTS`
  un INF de **una sola línea** (`SeServiceLogonRight`) que conserva todos los
  miembros existentes y agrega `*<SID>`; se re-exporta para verificar. Si
  `SeDenyServiceLogonRight` cubre al Broker, se falla cerrado. Nunca
  `ntrights.exe`, nunca una plantilla de política completa. La propiedad
  se persiste alrededor del cambio en `install-state.json`: `pending` justo
  antes de `secedit` (el export acaba de probar que el SID no estaba) y
  `added` tras la re-exportación verificada. Un derecho ya efectivo
  (directo o vía `ALL SERVICES`) nunca se registra como propio, y una
  propiedad registrada por una ejecución anterior se conserva al
  reinstalar. El rollback revoca sólo `pending`/`added` (revocar un SID
  ausente no cambia nada). Si el Broker es el **único** miembro (estado
  original: derecho sin asignar), un INF de una línea no expresa de forma
  fiable la lista vacía: se elimina exactamente ese derecho de ese SID con
  `LsaRemoveAccountRights` (sin tocar ninguna otra cuenta ni derecho) y se
  verifica con una re-exportación; nunca se conserva el privilegio por
  comodidad. Este caso **requiere validación específica en Windows**. En un equipo con GPO de dominio que defina ese derecho, el
  cambio local sería sobrescrito: el preflight/validación lo detectaría.

### Layout del servicio

```
C:\MYC\Services\developer-broker\       ACL protegida: SYSTEM F, Administrators F, Broker RX
    MYCDeveloperBroker.exe              copia de WinSW cuyo SHA-256 coincide con -WinSWExpectedSha256 (sin descarga; hash en el ledger)
    MYCDeveloperBroker.exe.config       sólo si existe junto al origen Y coincide con -WinSWConfigExpectedSha256
    MYCDeveloperBroker.xml              renderizado en el host; contiene el secreto; nunca versionado
C:\MYC\Logs\developer-broker\           ACL protegida: SYSTEM F, Administrators F, Broker Modify
C:\MYC\Deployment\                    SÓLO inspección (se crea sin tocar su ACL si falta); nunca se re-protege
C:\MYC\Deployment\developer-broker\     ACL protegida: SYSTEM F, Administrators F (ledger, journal transitorio, respaldos ACL, exports secedit)
```

**Integridad de WinSW (P0 operativo, pendiente antes de Windows)**: el
origen por defecto es `C:\MYC\Services\backend\MYCBackend.exe`, que estuvo
en un directorio con `Authenticated Users: Modify`; su metadata
(`ProductName`, `FileDescription`) no prueba nada. El preflight y el
instalador exigen `-WinSWExpectedSha256` (hash obtenido de una procedencia
confiable: la versión oficial de WinSW) y verifican el origen antes de
copiar y la copia después; un `.exe.config` acompañante requiere
`-WinSWConfigExpectedSha256` o el preflight falla. Authenticode se reporta
(PASS si es válido; WARN si la distribución no está firmada). Si el binario
actual no coincide con ningún release oficial, debe sustituirse por una
copia verificada (`-WinSWSource`) **antes** de instalar, y el propio
`MYCBackend.exe`/`MYCFrontend.exe` debe tratarse como sospechoso (TD-061).

**Directorios propios y lápida** (ledger esquema 6): `service_dir` y
`log_dir` siguen el mismo modelo que el servicio, `none → pending → owned`.
`pending` se registra antes de crear (intención, **nunca** autoridad para
borrar); `New-Item` falla si el directorio apareció entretanto; tras
crearlo y protegerlo se relee y se demuestra (ruta canónica, no reparse
point, owner Administrators, ACL base exacta sin Deny y **vacío**) y sólo
entonces pasa a `owned`. Si la prueba falla queda `pending`: el uninstall
lo registra `none` si ya no existe y, si existe, lo conserva para
reconciliación manual. Un `owned` sólo se elimina a petición y tras una
nueva prueba de propiedad. En una reinstalación, un directorio `owned` que
supera la prueba **no se re-protege** (no se retira temporalmente la ACE
operativa del Broker); la ACE exacta se normaliza después, en el paso de
ACL con el plan y el SID. Un directorio preexistente sólo se acepta si el
ledger lo registra `owned` y supera la prueba. Si el uninstall los
conserva (sin `-RemoveServiceFiles`/`-RemoveLogs`), el ledger permanece en
fase `uninstalled` como lápida; sólo se elimina cuando no queda ningún
recurso ni artefacto propio. Así una reinstalación reconoce esos
directorios en lugar de rechazarlos como desconocidos, sin adoptar nada
que DEV-1C no haya registrado.

**Alcance de propiedad ACL** (`broker_deploy.py directory-plan`): DEV-1C
sólo cambia owner/herencia/ACE/descendientes de sus cuatro directorios
`developer-broker` (estado, `acl-backups`, servicio, logs);
`New-MYCProtectedDirectory` rechaza cualquier otra ruta. `C:\MYC\Deployment`
y `C:\MYC\Logs` son padres **sólo inspeccionados** (política
`owned_parent`: dueño confiable y ningún principal no administrativo con
`DELETE_CHILD`, `WRITE_DAC` o `WRITE_OWNER`, que permitirían sustituir el
hijo protegido; un `Modify` ordinario se tolera). Ningún hermano (p. ej.
`C:\MYC\Deployment\another-component`) entra en el plan de mutación.
`C:\MYC\Services` sigue siendo el único endurecimiento global, deliberado y
con respaldo.

XML: `<executable>` = `…\venv\Scripts\python.exe`, `<arguments>-B -s -m
app.developer_broker.host</arguments>`, `<workingdirectory>` = `…\backend`,
`<startmode>Automatic</startmode>`, `<stoptimeout>15 sec</stoptimeout>`,
tres `<onfailure action="restart">` (10/30/60 s), `<resetfailure>1
hour</resetfailure>`, `<logpath>` + `<log mode="roll-by-size">`, y
exactamente las seis `<env>` que lee el host (`ENVIRONMENT_KEYS`). El
proceso no se daemoniza: WinSW lo supervisa y registra stdout/stderr. La
ruta del wrapper no admite espacios (se evita el riesgo de *unquoted
service path*); las rutas del repo con espacios (`C:\Users\SMM ADMIN\…`)
viajan escapadas dentro del XML y como argumentos separados a `icacls`.

### Modelo ACL

Concesiones explícitas del Broker (plan `acl-plan`, aplicadas con
`icacls /grant:r` —reemplaza la ACE del SID, nunca suma— y re-verificadas):

| Ruta | Derecho | Alcance |
|---|---|---|
| `C:\MYC\Services\developer-broker` | RX | árbol |
| `C:\MYC\Logs\developer-broker` | **Modify** (único Modify) | árbol |
| `<repo>\backend` | RX | **sólo la carpeta** (listar/cwd; sus archivos —`.env`— no) |
| `<repo>\backend\app` | RX | carpeta + archivos directos (`__init__.py`) |
| `<repo>\backend\app\developer_broker` | RX | árbol |
| `<repo>\venv` | RX | árbol (intérprete, pywin32) |
| `home` de `pyvenv.cfg` (runtime base de Python) | RX | árbol, sólo si está fuera del venv |

**Rutas no propias (repo, venv, Python home)**: antes de registrar o
aplicar cualquier concesión se inspecciona la ACL; si ya existe una ACE
**explícita** (allow o deny) del SID del Broker y el ledger no la registra
como de DEV-1C, la instalación falla cerrada (`preexisting_broker_ace`),
porque el rollback revoca por SID y borraría una ACE ajena. En una
reinstalación se aceptan sólo si el ledger demuestra la propiedad **y** la
ACE sigue siendo exactamente la aplicada (una sola ACE Allow, mismos
derechos, mismos `InheritanceFlags`/`PropagationFlags`; cualquier ampliación,
Deny o cambio de alcance → `broker_ace_drifted`).

**Propiedad por concesión, nunca por intención** (ledger esquema 6: cada
entrada de `acl_grants` es `{path, grant, status: pending|owned}`): por cada
concesión, en ese momento, verificación fresca → `pending` → `icacls
/grant:r` (o, en `ServiceDir`/`LogDir`, su ACL protegida) → relectura y
verificación **exacta** (SID, Allow, derechos, herencia, propagación) →
`owned`. `pending` + ACE exacta = resultado del propio `/grant:r` antes de un
corte (se reconcilia); `pending` + ACE distinta = ambigua → falla cerrada.
En el uninstall, cada concesión se decide con una lectura fresca
(`acl-grant-uninstall-action`): sin ACE explícita → sólo se limpia el
ledger; ACE exactamente la registrada → se retira y se verifica que no
queda ninguna; cualquier otra → no se toca (reconciliación manual). Nunca
una revocación por SID sólo porque la ruta aparece en el ledger. Los Deny explícitos
en directorios protegidos por DEV-1C son violación de política
(`unexpected_deny`).
Además la ruta debe ser canónica y ningún componente, desde la raíz de la
unidad hasta la ruta, puede ser un reparse point (junction/symlink).

**Reparse points y carreras**: una verificación previa seguida de una
operación recursiva (`icacls /T`, `Remove-Item -Recurse`) deja una ventana
TOCTOU, así que ya no se usa ninguna:
- `Set-MYCProtectedAcl` cierra **primero la raíz** sin `/T` (owner, herencia
  deshabilitada, ACE esperadas) y después recorre el árbol de arriba abajo
  "bloquear y luego enumerar": cada entrada se re-verifica como no reparse,
  recibe owner y `/reset` individual, se vuelve a verificar, y un
  directorio sólo se enumera **después** de quedar bloqueado (ya hereda la
  ACL cerrada). Un reparse point aborta.
- **Backup: JSON per-entry SDDL** — el SDDL de la raíz y de cada entrada
  del recorrido sin seguir enlaces (excluido `developer-broker`), en
  `acl-backups\<etiqueta>-<UTC>.acl.json`.
  **Restore: `Restore-MYCServicesAcl.ps1 -BackupFile <archivo>`** —
  herramienta explícita de recuperación (nunca automática, tampoco en el
  uninstall): PowerShell elevado; validación estricta del JSON
  (`restore-plan`: estructura, rutas canónicas dentro de `C:\MYC\Services`
  y fuera de `developer-broker`, sin `..`, sin duplicados, SDDL válido,
  entrada raíz presente); antes del primer cambio, cada entrada debe
  existir y no ser (ni estar bajo) un reparse point; restauración con
  `Set-Acl` (`SetSecurityDescriptorSddlForm`) de lo más profundo a la raíz
  (la raíz al final), relectura y comparación exacta del SDDL tras cada
  entrada y pasada final completa; `-WhatIf` muestra el plan. No es un
  archivo `icacls /save` y no se restaura con icacls.
- La eliminación de directorios propios (`remove-owned-tree`, Python) se
  hace tras demostrar la propiedad (ACL protegida: sólo SYSTEM/
  Administrators escriben): de abajo arriba, `lstat` de cada entrada
  inmediatamente antes de `unlink`/`rmdir`, sin seguir symlinks/junctions,
  con `rmdir` no recursivo que falla si algo apareció.
- Límite honesto: cuando cambia la DACL heredable de un directorio, Windows
  propaga la herencia por su cuenta; esa propagación es del sistema
  operativo, no un recorrido `/T` de DEV-1C, y su comportamiento ante
  reparse points debe validarse en Windows (TD-062).

Más estrecho que "RX sobre todo el repo" a propósito: el repo contiene
`backend\.env` (base de datos, JWT, Facturama, SMTP) y el Broker no debe
poder leerlo. Como el token de una cuenta virtual incluye `BUILTIN\Users` y
`Authenticated Users`, el preflight además exige que `backend\.env` no sea
legible por identidades amplias ni por SIDs de servicio (política
`secret_file`). Sin Modify al repo, sin acceso PostgreSQL, sin control de
servicios, sin firewall, sin derechos de política (fases Shell).

**Hallazgo de seguridad de producción** — `C:\MYC\Services` tenía
`Authenticated Users: Modify` mientras aloja wrappers/XML de servicios
LocalSystem (`MYCBackend`, `MYCFrontend`): cualquier usuario local podía
reemplazar un binario o configuración que corre como SYSTEM. No se
normaliza como aceptable. Endurecimiento reproducible
(`Set-MYCServicesAclHardening`, vía `-HardenServicesAcl` del instalador o
`Set-MYCServicesAcl.ps1 -Apply`): respaldo previo por entrada (SDDL, JSON)
en `C:\MYC\Deployment\developer-broker\acl-backups`; raíz cerrada primero y
luego owner Administrators entrada por entrada; herencia deshabilitada; SYSTEM y Administrators Full Control;
`BUILTIN\Users` RX **sólo** con `-AllowUsersReadOnServices` (los servicios
LocalSystem no lo necesitan); Authenticated Users y cualquier otro
principal explícito eliminados; descendientes reseteados a heredar
(excepto `developer-broker`, con ACL propia). El instalador **falla** si
`C:\MYC\Services` no es conforme y no se pasó `-HardenServicesAcl`. El
rollback del Broker no revierte este endurecimiento (restauración explícita
y deliberada con `Restore-MYCServicesAcl.ps1` a partir del respaldo JSON
por entrada). `C:\MYC` y `C:\MYC\Logs`
no se inspeccionaron para DEV-1C; el preflight reporta como WARN cualquier
principal amplio con escritura en ellos (TD-061).

### Modelo de secreto

- `DEVELOPER_BROKER_SECRET` nunca en Git, nunca en argumentos de línea de
  comandos, nunca en consola/log/excepción. Origen explícito
  (`-SecretSource`, obligatorio para instalar): `Generate` (48 bytes
  aleatorios base64url, generados dentro de `broker_deploy.py`), `Prompt`
  (`Read-Host -AsSecureString` dos veces; pasa a la herramienta **por
  stdin**; para comparar ambas entradas y escribirlo en stdin, PowerShell lo
  materializa como texto plano transitorio en memoria del proceso: nunca
  se imprime, registra ni pasa por argumentos, pero no es cierto que sólo
  exista como `SecureString`; con `Generate`/`Reuse` nunca entra en
  PowerShell) o `Reuse` (el existente, que debe estar en ambos lados y ser
  idéntico; comparación `hmac.compare_digest`). Alfabeto obligatorio
  `[A-Za-z0-9_-]{43,512}`: nada que XML, la expansión `%VAR%` de WinSW o el
  parser `.env` reinterpreten.
- Broker: `<env name="DEVELOPER_BROKER_SECRET">` en el XML renderizado
  (escritura atómica dentro del directorio protegido). El Broker sigue
  leyendo **sólo `DEVELOPER_BROKER_*` de su entorno de proceso**; nunca
  carga `backend\.env` (y no puede leerlo). No se usa la clave
  `Environment` del registro del servicio (legible por usuarios); el
  preflight falla si existe.
- ERP: bloque gestionado en `backend\.env` delimitado por
  `# >>> MYC Developer Broker … >>>` / `# <<< MYC Developer Broker <<<` con
  `DEVELOPER_BROKER_ENABLED`, `_TRANSPORT=named_pipe`, `_PIPE_NAME`,
  `_SECRET`, `_SERVICE_SID`, `_CLIENT_SID=S-1-5-18`, `_TIMEOUT_SECONDS=5`.
  Reescritura **en el mismo archivo** (conserva su ACL). Cualquier
  `DEVELOPER_BROKER_*` fuera del bloque, bloques duplicados o sin cerrar →
  rechazo antes de escribir nada.
- **Aprovisionamiento transaccional XML + `.env`**: plantilla, `.env`,
  secreto, XML y nuevo `.env` se validan y renderizan antes de escribir.
  Luego se guarda el contenido previo de ambos en un journal privado dentro
  de `C:\MYC\Deployment\developer-broker` (ACL protegida), commit 1 =
  `os.replace` atómico del XML, commit 2 = reescritura in-place del `.env`.
  Cualquier fallo restaura ambos (`provision_commit_failed`); si la
  restauración falla, `provision_rollback_failed` y el journal se conserva;
  la siguiente provisión o el desinstalador (`provision-recover`) restauran
  el par antes de hacer nada. Tras ambos commits se marca `committed`
  antes de borrar el journal (un corte durante la limpieza nunca revierte
  un commit terminado). El journal sólo existe durante la transacción:
  no queda como copia permanente del secreto. Errores sólo como códigos
  fijos, sin contenido. `Reuse` rechaza copias divergentes.
- **Propiedad del bloque de `backend\.env`** (ledger `backend_config` +
  `backend_config_evidence`): el bloque lleva un **marcador no secreto**
  (comentario `# dev1c-ownership-marker: <32 hex>`, ignorado por el parser
  del backend) y el ledger guarda marcador + **huella** PBKDF2-HMAC-SHA256
  (sal = marcador, 200 000 iteraciones) de una representación canónica del
  bloque (marcador, transporte, pipe, secreto, SIDs, timeout;
  `DEVELOPER_BROKER_ENABLED` excluido por ser el interruptor que DEV-1C
  mismo cambia). La huella no permite recuperar el secreto y nunca se
  imprime. `provision` (la herramienta, no PowerShell): un bloque presente
  debe demostrarse de DEV-1C (marcador + huella) o no se escribe nada; la
  evidencia del bloque nuevo se persiste **antes** del commit (`pending`, o
  `owned` + `fingerprint_next` en reinstalación); tras el commit se relee y
  sólo entonces `owned`. Uninstall: `none` → no se toca; `pending|owned` +
  bloque ausente → `none`; bloque presente **con** prueba → deshabilitar o
  eliminar; **sin** prueba (bloque ajeno aparecido durante `pending`, o
  bloque `owned` alterado) → no se modifica (reconciliación manual).
- Rotación: re-ejecutar con `-SecretSource Generate` (actualiza ambos
  lados) y reiniciar ambos servicios.
- La validación busca el secreto (UTF-8 y UTF-16) en todos los logs del
  Broker sin imprimirlo.

### Preflight del instalador (sólo lectura; cualquier FAIL aborta sin cambios)

Elevación (`#Requires -RunAsAdministrator` + `WindowsPrincipal`), Windows,
repo y `.git`, archivos requeridos del Broker y del despliegue, scripts
ejecutados desde el propio checkout, venv y `home` de Python, imports de
pywin32, import del host + nombre de pipe válido (validador del Broker),
WinSW de origen presente y verificado (sin descargas), `MYCBackend` existe,
corre como LocalSystem y su árbol de procesos es `S-1-5-18`, SID de
LocalSystem, estado del servicio Broker (ausente/compatible; **incompatible
→ rechazo**: nunca adopta ni sobrescribe un servicio ajeno), ruta del
wrapper sin espacios, raíces de servicios/logs, contenido del directorio
del servicio y logs preexistentes sin instalación registrada (rechazo),
ausencia de `Environment` en el registro del servicio, `backend\.env` sin
`DEVELOPER_BROKER_*` no gestionado y con ACL no amplia, origen del secreto,
pipe no ocupado por otro proceso (anti-squatting), ACL de
`C:\MYC\Services` (o `-HardenServicesAcl`), herramientas `sc.exe`,
`icacls.exe`, `secedit.exe`; `install-state.json` válido (corrupto o
de otra instalación → FAIL), servicio compatible sólo si el ledger lo
registra (nunca se adopta uno sin estado), y `C:\MYC\Deployment` /
`C:\MYC\Logs` seguros como padres (`owned_parent`).

### Secuencia de instalación

Preflight → **ledger `install-state.json` (antes de cualquier mutación
con rollback)** → endurecimiento de `C:\MYC\Services` (si hace falta y se
pidió) → directorios propios → detener un Broker compatible existente →
copiar WinSW (hash de confianza verificado antes y después) → decisión SCM
contra el ledger (`create` sólo si el servicio no existe y el ledger dice
`none`; `reconfigure` sólo si es compatible y el ledger dice `owned`;
`pending` = instalación parcial a reconciliar con Uninstall; `none` con un
servicio existente = no demostrado propio → falla) → propiedad del servicio `pending` → `sc.exe create` (demand)
bajo la cuenta virtual → **re-consulta del SCM** (cuenta, binario y tipo
exactos → `owned`; create fallido y servicio ausente → `none`; cualquier
otra combinación queda `pending` y falla cerrada para inspección manual) → sidtype, descripción, acciones de fallo →
re-verificación → SID (LSA+SCM, registrado) → `SeServiceLogonRight` si hace
falta (propiedad `pending`→`added`) → registrar concesiones ACL → ACLs →
provisión transaccional del secreto y configuración (**bloque ERP con
`DEVELOPER_BROKER_ENABLED=false`**) →
`start= auto` + arranque → validación de runtime (servicio Running,
`StartName`, todo el árbol de procesos con dueño = SID del Broker y ninguno
LocalSystem, pipe presente, **un administrador elevado recibe acceso
denegado al abrir el pipe**, log "Developer Broker escuchando", secreto
ausente de los logs, configuración ERP/Broker consistente, ACLs) → **sólo
entonces** `DEVELOPER_BROKER_ENABLED=true` → ledger en fase `installed`
(sin secreto; escrito siempre de forma atómica y validado por esquema e
identidad antes de confiar en él). `MYCBackend` sólo se reinicia con
`-RestartBackend`; ese reinicio es un paso de **activación** separado del
despliegue: si falla, el Broker queda instalado y validado, el ledger
registra `backend_activation = restart_failed`, se informa el estado de
`MYCBackend` con pasos de recuperación y el script sale con código 3 (nunca
una excepción sin controlar). Si algo falla antes: si **este** intento ya había puesto
`DEVELOPER_BROKER_ENABLED=true`, primero se revierte a `false` y se
verifica; si esa reversión falla, el mensaje lo dice explícitamente (el
`.env` puede seguir habilitado) en lugar de afirmar lo contrario. Después
el Broker se detiene y queda en inicio manual, y se indica el rollback.
Los temporales de `secedit` (exports, INF, `.sdb`, log) se eliminan en
`finally`, con éxito o fallo.

### Rollback (`Uninstall-MYCDeveloperBroker.ps1`)

0. Valida el ledger (corrupto/ajeno → no hace nada).
1. ERP primero, **sólo si el ledger posee el bloque** (`backend_config`
   `pending|owned`): restaura un aprovisionamiento interrumpido desde el
   journal, y según lo que realmente haya (`backend-config-action`):
   bloque ausente → `none`; presente **con prueba** →
   `DEVELOPER_BROKER_ENABLED=false` (o bloque eliminado con
   `-RemoveBackendConfig`); presente sin prueba → no se modifica. Con
   `backend_config = none` no se toca `backend\.env`. En la instalación,
   `provision` valida el ownership del managed block mediante marker +
   fingerprint persistidos en el ledger; un bloque presente sin prueba se
   rechaza sin modificarlo (`none → pending → owned`, `owned` tras
   releerlo); `MYCBackend` sólo se reinicia con
   `-RestartBackend`, nunca se detiene ni reconfigura.
2. Parada acotada: SCM stop ≤ 45 s; después sólo procesos del árbol del
   servicio cuyo dueño es el SID del Broker, ≤ 10 s más; si no, falla.
3. `sc.exe delete` y espera ≤ 30 s, sólo si el ledger registra el servicio
   como `owned` o `pending` **y** el SCM, re-consultado en ese momento,
   muestra exactamente la cuenta, el binario y el tipo esperados.
4. Por cada concesión registrada, relee la ACL: ACE exacta → se retira y se
   verifica; sin ACE → sólo ledger; cualquier otra → no se toca.
5. Revoca `SeServiceLogonRight` sólo si el ledger lo registra como
   `pending`/`added`.
   Cada paso limpia su propia entrada del ledger; el ledger se elimina sólo
   cuando ya no posee nada. Funciona igual tras una instalación parcial.
6. `-RemoveServiceFiles` (incluye el XML con el secreto) y `-RemoveLogs`
   explícitos, sólo sobre directorios `owned` que superen una prueba
   fresca (`directory-uninstall-action`); un `pending` nunca se borra. Lo
   retenido (directorios, bloque deshabilitado) deja el ledger como lápida
   (`uninstalled`).
   El reinicio opcional de `MYCBackend` se maneja igual que en la
   instalación (fallo de activación → código 3, sin excepción cruda).

Un servicio `MYCDeveloperBroker` incompatible (otra identidad o binario),
o compatible pero sin ledger, no se toca. **Sin ledger, el uninstall no
modifica nada**, tampoco el bloque `DEVELOPER_BROKER_*` de `backend\.env`:
DEV-1C no puede demostrar que lo creó (una instalación normal siempre crea
el ledger antes de provisionar); limpiar un bloque huérfano es una acción
manual explícita, no un efecto implícito de Uninstall.

**Una sola puerta SCM para toda mutación del servicio existente**:
`stop`, `config demand`, `sidtype`, `description`, `failure`,
`failureflag`, `config auto`, `start` y `delete` pasan todas por
`Invoke-MYCGuardedScm` (o `Stop-MYCBrokerService`, que la usa): consulta
fresca del SCM + SID de LSA y del SCM, evaluadas por `scm-guard`
(compatible, LSA == SCM, ledger `service` `pending|owned`, mismo SID que el
ledger) **inmediatamente** seguida de la única llamada `sc.exe`, sin
trabajo intermedio. Las únicas llamadas directas a `sc.exe` son lecturas
(`showsid`) y `create` (servicio que aún no existe; se re-consulta
después). El `catch` del instalador usa la misma puerta aunque el SID no
se haya resuelto en esa ejecución; si no puede demostrar la propiedad, no
toca el SCM y pide reconciliación manual. Un script
no puede cerrar del todo la ventana entre esa verificación y `sc.exe`; sólo
la reduce al mínimo y mantiene el fallo cerrado ante cambios concurrentes.

**Normalización completa de ACL propias**: `Set-MYCProtectedAcl` elimina
todo Deny explícito (`icacls /remove:d`) y toda ACE Allow explícita fuera
de la política (`/remove:g`), coherente con la validación que trata un Deny
explícito como violación. Cada paso es `ShouldProcess` (`-WhatIf` muestra el plan).

### Runbook (servidor `ADMIN`)

Desde PowerShell elevado en `C:\Users\SMM ADMIN\myc_erp\deploy\windows\developer-broker`,
con el checkout en el commit a desplegar:

0. **Antes de todo (P0)**: obtener de la procedencia oficial de WinSW el
   SHA-256 de la versión usada por `MYCBackend.exe` y compararlo; si no
   coincide o no puede demostrarse, conseguir una copia verificada y usarla
   con `-WinSWSource`. Tratar `MYCBackend.exe`/`MYCFrontend.exe` actuales
   como sospechosos hasta verificarlos.
1. `.\Install-MYCDeveloperBroker.ps1 -PreflightOnly -WinSWExpectedSha256 <hash>` y revisar cada FAIL/WARN.
2. `.\Set-MYCServicesAcl.ps1` (reporte) y, aprobado, `.\Set-MYCServicesAcl.ps1 -Apply`
   (o `-HardenServicesAcl` en el paso 3). Confirmar `MYCBackend`/`MYCFrontend` Running.
3. `.\Install-MYCDeveloperBroker.ps1 -SecretSource Generate -HardenServicesAcl -WinSWExpectedSha256 <hash>`
4. `.\Test-MYCDeveloperBroker.ps1` (todo PASS).
5. Ventana acordada: `Restart-Service MYCBackend` (o reinstalar con
   `-SecretSource Reuse -RestartBackend`).
6. Health end-to-end desde MYC Mobile: `GET /api/mobile/v1/developer/broker/health`
   con DeveloperSession + `developer.system.read` → 200.

Rollback: `.\Uninstall-MYCDeveloperBroker.ps1 -RemoveServiceFiles -RestartBackend`.

## Ausencias deliberadas (DEV-1A, DEV-1B y DEV-1C)

- **Sin shell, sin PowerShell, sin ejecución de procesos**: ni
  `subprocess`, `os.system`, `os.popen`, `shell=True`, `pty`,
  `multiprocessing`, ni binarios de shell. Verificado por AST
  (`test_dev_1a_implementation_executes_no_processes`) y por búsqueda
  textual sobre los archivos tocados.
- Sin API de ejecución arbitraria: no existen `/execute`, `/command`,
  `/powershell`; ningún campo acepta un string de comando.
- Sin sockets, sin puertos (ni 8765, ni 5432, ni 22, ni 3389), sin
  listener TCP/HTTP, sin Cloudflare, sin firewall, sin migraciones. Única
  dependencia nueva (DEV-1B): `pywin32`, sólo Windows. Escaneado por test
  (`test_broker_package_opens_no_network_listener_or_tcp_fallback`).
- DEV-1C agrega **sólo** activos de despliegue fuera del paquete del
  Broker (`deploy/windows/developer-broker/`); `app/developer_broker/` no
  cambia. Sin `ShellSession`, ConPTY/`CreatePseudoConsole`,
  `powershell.exe`, `subprocess`/`Popen`, comandos arbitrarios, Git, SQL,
  `psql`, Database Console, streaming, WebSocket shell, terminal UI, árbol
  de procesos ni helper privilegiado. Verificado por AST sobre el paquete
  del Broker y sobre `broker_deploy.py`
  (`test_no_process_execution_in_broker_or_deployment_python`) y
  `broker.health` sigue siendo la única operación
  (`test_broker_health_remains_the_only_operation`).
- **Sin reutilizar el realtime del ERP**: `app/realtime/`
  (`RealtimeHub`, `InMemoryRealtimeHub`, envelope `myc.realtime.v1`) es
  comunicación del ERP; el Broker IPC tiene su propio protocolo,
  lifecycle y trust boundary. Ninguna `ShellSession` vivirá en rooms
  `user:*`/`conversation:*`.

## Compatibilidad con `ShellSession` (DISEÑO FUTURO, DEV-2+)

DEV-1A/1B/1C no implementan `ShellSession`, pero el contrato no la impide:

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

- **DEV-1C en Windows real**: ejecutar el runbook en `ADMIN` (preflight,
  endurecimiento de `C:\MYC\Services`, instalación, `Test-MYCDeveloperBroker.ps1`,
  reinicio de `MYCBackend`, health end-to-end desde Mobile) y el rollback en
  una ventana controlada. Nada de la parte Windows de DEV-1C (SCM, cuenta
  virtual, `icacls`, `secedit`, WinSW con esta configuración) se ha
  ejecutado todavía. Puntos a confirmar allí: versión de WinSW copiada;
  que el redirector `venv\Scripts\python.exe` arranca el intérprete base con
  las ACL mínimas; que WinSW entrega Ctrl+C al host dentro de
  `stoptimeout`; que `[IO.Directory]::GetFiles('\\.\pipe\')` enumera pipes
  en PowerShell 5.1; salida de `sc.exe showsid` en el idioma del sistema.
- `ShellSession`, PowerShell, streaming (el puerto `exchange` es
  request/response; el streaming requerirá extenderlo o protocolo v2).
- Operaciones estructuradas (`database.*`, `logs.*`, `git.*`,
  `services.*`), cada una con su capacidad Developer granular y sus propios
  derechos del SO (las ACL de DEV-1C no los anticipan).
- Rotación del secreto HMAC con `key_id` (hoy: rotación completa con
  reinicio de ambos servicios).
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
- `backend/tests/test_developer_broker_deployment.py` (DEV-1C,
  cross-platform, **no instala nada**): identidad y layout del servicio,
  cuenta virtual (nunca LocalSystem ni SIDs amplios/compartidos), SID de
  cliente `S-1-5-18`, SID del servicio resuelto en el host (sin SIDs
  versionados), nombres de variables contra `ENVIRONMENT_KEYS` y
  `Settings`, secreto (generación, alfabeto, stdin, reuse, rotación, nunca
  en argumentos/salida/archivos versionados, XML renderizado ignorado por
  Git), bloque gestionado de `.env` (idempotencia, rechazo de claves no
  gestionadas antes de escribir, reescritura in-place), render XML con
  rutas con espacios, plan ACL mínimo, política ACL (hallazgo de producción
  no conforme, endurecido conforme, Users sólo RX), INF de
  `SeServiceLogonRight`, veredicto de servicio incompatible, estructura de
  los scripts (elevación antes de cualquier cambio, preflight completo antes
  de modificar, ERP habilitado sólo tras validar, rollback acotado y
  explícito, sin descargas, sin sombreado de variables, BOM UTF-8 para
  PowerShell 5.1), ausencia de ejecución de procesos y `broker.health`
  como única operación.

## Validación de DEV-1B

Estado vigente: **cerrado y mergeado**.

| Hito | Referencia |
|---|---|
| Implementación inicial | `0b9572d` feat(developer): add Windows named pipe broker transport |
| Corrección de identidad del cliente en Windows | `6a9374c` fix(developer): harden Windows pipe client identity |
| Re-ejecución real en Windows (`test_developer_broker_windows.py`) | **11 passed, 1 skipped, 0 failed** |
| Merge | PR #9 → `main` `05f4c625f5f9cd7620a1a84a543b7f31d787ee27` |
| Producción | backend desplegado en ese `main` |

El único skip es deliberado: el rechazo de clientes remotos
(`PIPE_REJECT_REMOTE_CLIENTS`) requiere un segundo host; un fallo local al
abrir `\\localhost\pipe\…` no distingue el flag de un servicio Server
detenido.

### Evidencia histórica (primera ejecución real, `0b9572d`; NO es el estado actual)

Python 3.14.7 + pywin32: 5 passed, 6 failed, 1 skipped. Ya validó entonces:
import de pywin32 y `load_win32_api`; primera instancia con
`FILE_FLAG_FIRST_PIPE_INSTANCE` y DACL explícita; rechazo de una segunda
"primera instancia" (`pipe_name_in_use`); DACL real con exactamente las dos
ACE (`0x0012019F` / `0x00100083`); `pipe_not_found`; timeout overlapped
real; `server_identity_mismatch` sin escribir ningún byte.

Fallaron las 6 pruebas que pasan por
`NamedPipeBrokerListener._serve_connection`. Causa raíz (confirmada en
Windows): `ImpersonateNamedPipeClient` se llamaba a través de `win32pipe`,
donde no existe (vive en `win32security`); el `AttributeError` caía en el
manejador genérico antes del handler. `6a9374c` lo corrigió
(`win32security`; fallo al suplantar → `client_identity_unverifiable` sin
`RevertToSelf`; `RevertToSelf` exactamente una vez tras suplantar; fallo de
revert → `revert_to_self_failed` y el listener deja de aceptar; prueba
estructural de pertenencia de nombres pywin32 a su módulo), y la
re-ejecución quedó en 11 passed, 1 skipped, 0 failed.
