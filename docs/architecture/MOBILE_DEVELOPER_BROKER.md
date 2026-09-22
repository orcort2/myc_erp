> Estado: EN REVISIÓN — FASE DEV-1A (sin commit; pendiente de auditoría humana, NO cerrado)

> Tipo: Arquitectura vigente

> Corte: 2026-09-22 — DEV-1A: frontera Broker + contrato versionado + esqueleto de transporte local autenticado

# Developer Broker de MYC (DEV-1)

Este documento es la autoridad del **Developer Control Plane ↔ Developer
Broker**. La autoridad de usuario (quién puede operar Developer) sigue
siendo exclusivamente DEV-0:
[`MOBILE_DEVELOPER_AUTHORITY.md`](MOBILE_DEVELOPER_AUTHORITY.md). Este
documento no la redefine.

Cada sección distingue **IMPLEMENTADO (DEV-1A)** de **DISEÑO FUTURO
(DEV-1B+)**. Nada marcado como futuro existe en código.

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
IPC LOCAL AUTENTICADO   (Windows Named Pipe + ACL del SO + HMAC)  ← adapter pendiente
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
| `BrokerTransport` (puerto: `exchange(frame, timeout_seconds) -> frame`) | IMPLEMENTADO |
| `InMemoryBrokerTransport` (entrega el frame a un `BrokerServer` del mismo proceso) | IMPLEMENTADO — **sólo tests/desarrollo del contrato**; la configuración de FastAPI no puede seleccionarlo |
| Windows Named Pipe | **PENDIENTE (DEV-1B)** |

El transporte sólo mueve bytes opacos; la autenticación es extremo a
extremo entre `BrokerClient` y `BrokerServer`. Errores de transporte
(`OSError`, `TimeoutError`) se convierten en `BrokerUnavailableError`.

**Named Pipe no se simuló en macOS** y **no existe fallback TCP/loopback**:
no se abre ningún puerto. Con `DEVELOPER_BROKER_TRANSPORT=named_pipe` y la
configuración completa, `build_developer_broker_client` falla cerrado con
`named_pipe_adapter_pending` → la ruta responde 503.

Decisiones pendientes para el adapter Windows (DEV-1B): implementación
(stdlib `_winapi`/`multiprocessing.connection` vs. dependencia como
`pywin32`, que **no** se agregó), pipe en modo mensaje o framing con
prefijo de longitud, security descriptor explícito (sólo la cuenta del
servicio ERP y la del Broker; sin `Everyone`/`Authenticated Users`),
`PIPE_REJECT_REMOTE_CLIENTS`, verificación del PID/identidad del
servidor al conectar (anti pipe-squatting, complementaria a las
respuestas firmadas) y timeouts. Debe validarse en Windows real.

## Configuración (IMPLEMENTADO)

`app/core/config.py`, patrón `Settings` existente:

| Variable | Default | Nota |
|---|---|---|
| `DEVELOPER_BROKER_ENABLED` | `false` | Opcional en esta fase |
| `DEVELOPER_BROKER_TRANSPORT` | `named_pipe` | Único valor aceptado |
| `DEVELOPER_BROKER_PIPE_NAME` | `""` | Sin rutas de instalación hardcodeadas |
| `DEVELOPER_BROKER_SECRET` | `""` (`SecretStr`) | ≥ 32 bytes; sólo secreto externo |
| `DEVELOPER_BROKER_TIMEOUT_SECONDS` | `5` | |

Sin configuración, el ERP arranca normal (no hay validador que bloquee el
arranque); sólo la ruta Broker falla cerrado. Los problemas de
configuración se registran por código (`disabled`,
`secret_missing_or_too_short`, `pipe_name_missing`,
`named_pipe_adapter_pending`), nunca con el valor del secreto.

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
  configurado, no responde o su respuesta no es auténtica; sin traceback ni
  detalle de configuración.
- Logging del Control Plane: sólo el código estable (`exc.code`) de un
  `BrokerError`, nunca `exc.reason` (podrá contener detalle de transporte en
  DEV-1B). Para configuración sólo se registran los códigos fijos que el
  propio servicio emite (`disabled`, `secret_missing_or_too_short`,
  `pipe_name_missing`, `named_pipe_adapter_pending`, `unknown_transport`);
  cualquier otro valor se registra como `not_configured`. El log interno
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

## Identidad del servicio Windows (DISEÑO FUTURO)

- El Broker **no** debe correr como `LocalSystem` (a diferencia de
  `MYCBackend.exe`; ver invariante en
  [`MOBILE_DEVELOPER_AUTHORITY.md`](MOBILE_DEVELOPER_AUTHORITY.md)).
- Correrá como servicio separado (`MYCDeveloperBroker`) bajo una
  **identidad de servicio dedicada con least privilege** (cuenta virtual
  de servicio o gMSA/cuenta local dedicada), nunca administrador "por
  comodidad".
- Cualquier capacidad elevada futura se diseñará explícitamente **por
  operación**, no concediendo privilegios generales al Broker.
- DEV-1A no requiere privilegios administrativos ni instala servicios.

## Ausencias deliberadas en DEV-1A

- **Sin shell, sin PowerShell, sin ejecución de procesos**: ni
  `subprocess`, `os.system`, `os.popen`, `shell=True`, `pty`,
  `multiprocessing`, ni binarios de shell. Verificado por AST
  (`test_dev_1a_implementation_executes_no_processes`) y por búsqueda
  textual sobre los archivos tocados.
- Sin API de ejecución arbitraria: no existen `/execute`, `/command`,
  `/powershell`; ningún campo acepta un string de comando.
- Sin sockets, sin puertos (ni 8765, ni 5432, ni 22, ni 3389), sin
  Cloudflare, sin firewall, sin despliegue, sin migraciones, sin
  dependencias nuevas.
- **Sin reutilizar el realtime del ERP**: `app/realtime/`
  (`RealtimeHub`, `InMemoryRealtimeHub`, envelope `myc.realtime.v1`) es
  comunicación del ERP; el Broker IPC tiene su propio protocolo,
  lifecycle y trust boundary. Ninguna `ShellSession` vivirá en rooms
  `user:*`/`conversation:*`.

## Compatibilidad con `ShellSession` (DISEÑO FUTURO, DEV-1B+)

DEV-1A no implementa `ShellSession`, pero el contrato no la impide:

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

## Pendiente para DEV-1B+

- Adapter Windows Named Pipe (cliente y servidor) + ACL + validación en
  Windows real; decidir si se requiere dependencia (no agregada).
- Host del Broker como servicio Windows con identidad dedicada (no
  `LocalSystem`), su configuración de secreto y su arranque.
- Rotación del secreto HMAC (p. ej. `key_id` en el envelope → requiere
  versión de protocolo nueva).
- `ShellSession` y su lifecycle; operaciones estructuradas
  (`database.*`, `logs.*`, `git.*`, `services.*`) cada una con su
  capacidad Developer granular vía `require_developer_session`.
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
