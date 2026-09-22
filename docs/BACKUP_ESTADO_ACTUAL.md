> Estado: VIGENTE
>
> Tipo: Snapshot operativo verificable
>
> Autoridad: Media; no sustituye los documentos canónicos de project/
>
> Corte: 2026-09-22 — DEV-1B (adapter Windows Named Pipe + host del Broker, sin commit; pendiente de auditoría y de validación en Windows real) sobre DEV-1A ya fusionado en `main` (PR #8, `5bf2349`)

# Estado operativo actual del ERP MYC

## DEV-1B — Windows Named Pipe + Broker host (EN REVISIÓN, sin commit)

- Worktree `/Users/saulcortes/Developer/myc_erp-dev1`, rama
  `feat/mobile-developer-named-pipe-dev1b` creada desde `origin/main`
  `5bf2349` (merge PR #8, DEV-1A). El checkout estable `myc_erp` no se tocó.
- Implementado en código: `framing.py` (uint32 BE + payload),
  `pipe_name.py` (nombre lógico → `\\.\pipe\<nombre>`),
  `windows_pipe.py` (`WindowsNamedPipeTransport`,
  `NamedPipeBrokerListener`, DACL explícita de dos SIDs, primera instancia
  exclusiva, `PIPE_REJECT_REMOTE_CLIENTS`, verificación del SID del servidor
  antes de escribir, nivel identification, verificación del SID del cliente)
  y `host.py` (`python -m app.developer_broker.host`, configuración mínima
  propia desde el entorno). `build_developer_broker_client` crea el
  transporte real en Windows y falla cerrado fuera (`platform_unsupported`).
- Settings nuevos: `DEVELOPER_BROKER_SERVICE_SID`,
  `DEVELOPER_BROKER_CLIENT_SID`.
- Dependencia nueva: `pywin32==312; sys_platform == "win32"` en el
  `requirements.txt` raíz; en macOS pip la ignora y no está instalada.
- **No validado en Windows real**: las 11 pruebas de
  `test_developer_broker_windows.py` se omiten fuera de Windows (skip, no
  pass). La lista de validaciones pendientes está en
  `architecture/MOBILE_DEVELOPER_BROKER.md` ("Validación de DEV-1B").
- Sin shell, PowerShell, ejecución de procesos, sockets/puertos,
  servicio Windows, WinSW, registro, despliegue ni migraciones (head sigue
  `c4d8e2f1a7b3`).
- Corrección post-auditoría: la máscara DACL del Broker pasa de
  `0x00120087` a `0x0012019F` (`FILE_GENERIC_READ` ∪ `FILE_GENERIC_WRITE`
  como derechos específicos; necesaria para crear instancias adicionales con
  `PIPE_ACCESS_DUPLEX`); el cliente sigue en `0x00100083`, sin
  `FILE_CREATE_PIPE_INSTANCE`. Logging del adapter y del host centralizado en
  `loggable_reason` (sólo códigos conocidos). La creación real de instancias
  posteriores sigue **sin validar en Windows**.
- Validación tras la corrección (macOS): named_pipe 127 passed; contrato
  102 passed; endpoint 14 passed; Windows 12 skipped; DEV-0 + conformidad
  97 passed, 1 skipped; backend completo 1567 passed, 36 skipped (24
  previos + 12 Windows), 0 failed; `alembic heads` = `c4d8e2f1a7b3`.
- Validación inicial (macOS, antes de la corrección): Broker DEV-1A+1B 234 passed, 11 skipped (Windows);
  DEV-0 + conformidad 97 passed, 1 skipped; backend completo 1558 passed,
  35 skipped (24 previos + 11 Windows), 0 failed; `alembic heads` =
  `c4d8e2f1a7b3`.

## DEV-1A — Developer Broker boundary (MERGEADO, PR #8)

- Worktree `/Users/saulcortes/Developer/myc_erp-dev1`, rama
  `feat/mobile-developer-shell-broker-dev1`, base `91d7404` (= `origin/main`,
  merge de DEV-0). El checkout estable `myc_erp` (`main`) no se tocó.
- Implementado: paquete `backend/app/developer_broker/` (contrato
  `myc.developer-broker` v1, HMAC-SHA256 canónico con requests y responses
  firmados, anti-replay in-memory acotado, `BrokerServer` con única
  operación `broker.health`, puerto `BrokerTransport` + transporte
  in-memory sólo para pruebas, `BrokerClient`), servicio
  `app/services/developer_broker.py`, configuración opcional
  `DEVELOPER_BROKER_*` (deshabilitada por defecto; el ERP arranca igual) y
  `GET /api/mobile/v1/developer/broker/health` protegido con
  `require_developer_session("developer.system.read")`.
- Pendiente al cierre de DEV-1A (el adapter ya existe en DEV-1B, arriba): adapter Windows Named Pipe + ACL, servicio Windows con
  identidad dedicada (no `LocalSystem`), `ShellSession`. Con el Broker
  habilitado y el transporte `named_pipe`, la ruta falla cerrado (503,
  `named_pipe_adapter_pending`).
- Sin PowerShell, sin ejecución de procesos, sin sockets/puertos, sin
  migraciones (head sigue `c4d8e2f1a7b3`), sin dependencias nuevas.
- Inventario HTTP: 537 operaciones (536 + `broker/health`).
- Validación: `test_developer_broker_contract.py` (73) +
  `test_mobile_developer_broker_health.py` (10) = 83 passed; DEV-0 y
  conformidad (`test_mobile_developer_session.py`, `test_mobile_biometric.py`,
  `test_mobile_security_context.py`, `test_api_access_conformity.py`,
  `test_capability_gate_reconciliation.py`) 97 passed, 1 skipped (PostgreSQL
  real, requiere `LAB_POSTGRES_TEST_URL`); backend completo 1407 passed, 24 skipped, 0 failed
  (baseline antes del cambio: 1324 passed, 24 skipped); `alembic heads` =
  `c4d8e2f1a7b3`.
- Endurecimiento post-auditoría (2026-09-22): ventana temporal half-open
  `(now − 30 s, now + 5 s]` para cerrar el borde replay/freshness; el
  cliente autentica la respuesta antes de interpretarla; contrato exacto
  del resultado `broker.health` (sin campos extra/faltantes, sin `bool`
  como entero, `instance_id` 32 hex); el Control Plane sólo registra
  `exc.code`. Validación tras el endurecimiento: Broker 96 + endpoint 14 = 110 passed;
  DEV-0 + conformidad 97 passed, 1 skipped; backend completo 1434 passed,
  24 skipped, 0 failed; `alembic heads` = `c4d8e2f1a7b3`.
- Detalle: [MOBILE_DEVELOPER_BROKER.md](architecture/MOBILE_DEVELOPER_BROKER.md).

## DEV-0 (contexto previo, fusionado en `main` por PR #7)

## Repositorio y alcance verificado

- Rama de trabajo aislada: `feat/mobile-developer-authority-dev0`, creada
  desde `origin/main` en `c3fc795dbed8c41d600ff95066390967d64fac98` (merge de
  PR #6, que integró `feat/mobile-biometric-login-2` completo: BIOMETRIC-1,
  BIOMETRIC-2 y su endurecimiento posterior).
- Trabajo realizado en un `git worktree` separado
  (`/Users/saulcortes/myc_erp-dev0`), sin tocar el checkout compartido del
  repo principal: la rama `feat/mobile-biometric-login-2` originalmente
  asignada a esta tarea avanzó por otro proceso concurrente
  (`bc316e4 fix(mobile-auth): polish biometric entry and home scroll`, ya en
  `origin`) mientras se exploraba el repo, y el checkout compartido quedó en
  `main`. Se detectó, se reportó y se resolvió trabajando en un worktree
  nuevo en vez de sobrescribir ese trabajo.
- Sin push, merge ni despliegue en este trabajo.
- DEV-0 agrega la autoridad Developer (permisos, `DeveloperSession`,
  desbloqueo biométrico, expiración/revocación, `DeveloperProvider` Mobile,
  pantalla placeholder) sobre BIOMETRIC-2, sin reescribirla: reutiliza
  `resolve_biometric_credential` (extraída de `biometric.py` sin cambiar su
  comportamiento) como única autoridad biométrica. No implementa
  PowerShell, subprocess, shell WebSocket, ejecución SQL, explorador de DB,
  broker de Windows ni el puerto 8765 — todo eso es DEV-1+.
- Endurecimiento 2026-09-22 (worktree sin commit sobre `4685acb`):
  política Developer explícita (`"*"` ya no concede Developer), como máximo
  una `DeveloperSession` activa por dispositivo con supersession
  (`superseded`), binding estricto del token a su `MobileAuthSession`
  (`mobile_session_id`), guard canónico para operaciones DEV-1+
  (`authorize_developer_operation`, no montado) y reconciliación Mobile por
  lifecycle (foreground, entrada al Developer Center, rotación del access
  token, pérdida de capacidad) sin polling.
- Detalle completo: [MOBILE_DEVELOPER_AUTHORITY.md](architecture/MOBILE_DEVELOPER_AUTHORITY.md).

## Base de datos y respaldo

- Revisión inicial local/código: `9970e12e5f0d`, único head (BIOMETRIC-2).
- Migraciones DEV-0: `602a09af6218` (padre `9970e12e5f0d`) y, del
  endurecimiento, `c4d8e2f1a7b3` (padre `602a09af6218`). Head único:
  `c4d8e2f1a7b3`.
- `c4d8e2f1a7b3` es una revisión nueva (no se editó `602a09af6218`, que ya
  está aplicada en la base local `erp_myc`): sanea filas activas duplicadas
  por dispositivo (`superseded`), crea el índice único parcial
  `uq_developer_sessions_active_device (device_id) WHERE revoked_at IS NULL`
  y elimina el UNIQUE redundante `uq_developer_session_token_hash` (queda el
  índice único `ix_developer_sessions_token_hash`, que es lo que declara el
  modelo).
- Verificado en una base PostgreSQL local desechable
  (`myc_dev0_scratch_20260922`, eliminada al terminar): upgrade desde cero,
  saneamiento con duplicados sembrados, rechazo de un segundo activo por el
  índice, downgrade → upgrade, FKs `ON DELETE CASCADE`, y `alembic check` sin
  drift en `developer_sessions`.
- **La base local `erp_myc` NO se migró en este pase**: sigue en
  `602a09af6218`. Pendiente `alembic upgrade head` local cuando se acepte.
- Tabla nueva: `developer_sessions`, con FKs a `users`,
  `mobile_trusted_devices` y `mobile_auth_sessions`, `token_hash` UNIQUE e
  índices de usuario, dispositivo, sesión Mobile, vencimiento y revocación.
- No se modificó ninguna migración histórica (ni BIOMETRIC-1/2 ni
  `602a09af6218`).
- `test_schema_integrity_stage_2a.py::test_current_revision_is_the_single_head`
  en verde: sigue habiendo un único head tras la nueva migración.

## Permisos

Nuevos permisos explícitos en `app/core/permissions.py`, asignados sólo al
rol `Desarrollador`: `developer.access`, `developer.database.read`,
`developer.database.write`, `developer.database.admin`,
`developer.shell.access`, `developer.system.read`, `developer.logs.read`,
`developer.services.execute`, `developer.git.read`.

Política Developer explícita (`app/core/developer_policy.py`,
`myc-mobile/src/permissions/developer-policy.ts`): Developer = actor interno
AND una capacidad Developer exacta (el string exacto de la capacidad, p.ej.
`developer.access`). `"*"` (Administrador) y el wildcard literal
`"developer.*"` ya **no** conceden Developer por sí solos; el riesgo aceptado anterior queda
eliminado. La semántica global de `"*"` en el ERP no cambió
(`user_has_permission` y los guards genéricos intactos). Un Administrador
que necesite infraestructura requiere el rol `Desarrollador` explícito.

## Endpoints nuevos

`POST|GET|DELETE /api/mobile/v1/developer/session`
(`app/routers/mobile_developer.py`), clasificados en el inventario de
acceso HTTP bajo el mismo mecanismo genérico `mobile_context` que el resto
de `/api/mobile/v1/*` (permiso base `mobile.access`); el gate fino de
`developer.access` + actor interno vive en el propio endpoint
(`require_mobile_developer_capability`, política explícita). `GET`/`DELETE`
exigen además el header dedicado `X-MYC-Developer-Token` y sólo reconocen el
token desde la misma `MobileAuthSession` que lo abrió. Sin rutas nuevas
(inventario HTTP: 536 operaciones, sin cambios).

## Validación final (endurecimiento 2026-09-22)

Entorno: venv aislado en el scratchpad de la sesión (el venv del checkout
principal vive en un Desktop sincronizado con iCloud con archivos
`dataless` y colgaba la importación); mismas versiones de paquetes que ese
venv.

- Baseline antes de modificar: backend focalizado 78 passed; backend
  completo 1305 passed, 23 skipped; Mobile 759 passed; `tsc` con los 2
  errores históricos de `realtime-client.ts`; lint sin salida (el warning
  `missing dependency: clearLocal` estaba oculto por `eslint-disable`).
- Backend focalizado (`test_mobile_developer_session.py`,
  `test_mobile_biometric.py`, `test_mobile_security_context.py`,
  `test_api_access_conformity.py`, `test_capability_gate_reconciliation.py`)
  con `LAB_POSTGRES_TEST_URL` apuntando a la base desechable: 98 passed.
  `test_mobile_developer_session.py`: 44 casos (antes 24; se reemplazó
  `test_admin_wildcard_still_grants_developer_access`).
- Backend completo (sin `LAB_POSTGRES_TEST_URL`, igual que el baseline):
  1324 passed, 24 skipped, 0 failed.
- `test_schema_integrity_stage_2a.py::test_current_revision_is_the_single_head`:
  passed; `alembic heads` = `c4d8e2f1a7b3`.
- Mobile completo: 779 passed, 0 failed.
- `npx tsc --noEmit`: exactamente los mismos 2 errores preexistentes en
  `src/realtime/realtime-client.ts` (líneas 205 y 231), ajenos y no tocados.
- `npm run lint`: sin errores ni warnings; `eslint --max-warnings=0` sobre
  los archivos tocados: 0/0, sin `eslint-disable`.
- `git diff --check`: limpio.

## Deuda técnica conocida

- BIOMETRIC-2 (`9970e12e5f0d`) crea el mismo par redundante UNIQUE
  constraint + índice único en `mobile_biometric_credentials.credential_hash`
  (`alembic check` lo reporta como drift). No se tocó por restricción de no
  modificar BIOMETRIC-1/2.
- Una rotación de refresh Mobile termina la `DeveloperSession` (binding por
  generación de `MobileAuthSession`). Con access tokens de 8 h y Developer de
  10 min es infrecuente; el cliente lo reconcilia al cambiar el access token.
- La reconciliación Mobile es fail-closed: un error de red al volver a
  foreground bloquea Developer localmente.

## Validación del corte DEV-0 original (2026-09-21)

- Backend focalizado: `test_mobile_developer_session.py` (24 passed),
  `test_mobile_biometric.py` + `test_mobile_security_context.py` +
  `test_api_access_conformity.py` + `test_capability_gate_reconciliation.py`
  (78 passed en conjunto).
- Backend completo: 1305 passed, 0 failed, 23 skipped (incluye el recurso
  oficial `catalogo sat.xlsx`, ignorado por Git y copiado manualmente a este
  worktree aislado sólo para poder correr la suite completa localmente; no
  es parte de este cambio).
- Mobile focalizado de DEV-0: 27 passed (`DeveloperProvider.test.ts`,
  `technician-home.developer-card.wiring.test.ts`,
  `developer-screen.wiring.test.ts` y el bloque nuevo de
  `mobile-capabilities.test.ts`).
- Mobile completo: 759 passed (antes 732 en el corte BIOMETRIC-2 tras su
  endurecimiento).
- `npx tsc --noEmit`: mismos 2 errores preexistentes en
  `realtime-client.ts`, ajenos a este trabajo y no tocados.
- `npm run lint`: exit 0, sin errores.
- Inventario API regenerado: 536 operaciones (533 + 3 nuevas de
  `/mobile/v1/developer/session`); `docs/architecture/security/API_ENDPOINT_INVENTORY_2026-08-03.csv`
  actualizado y coincide byte a byte con el runtime
  (`test_committed_inventory_matches_runtime`).
- `git diff --check` sin errores.
- Revisado: sin credenciales, tokens Developer, credenciales biométricas,
  perfiles de aprovisionamiento ni artefactos de build en el commit.

## Pendientes y límites

- Resuelto en el endurecimiento 2026-09-22: la política canónica explícita
  "actor interno + capability Developer explícita" ya está implementada;
  `"*"` por sí solo no abre Developer.
- DEV-0 NO está cerrado: pendiente auditoría humana final, commit, merge y
  `alembic upgrade head` en la base local `erp_myc`.
- Invariante para DEV-1+: toda operación privilegiada debe pasar por
  `authorize_developer_operation`/`require_developer_session(capability)`
  (DeveloperSession viva + capacidad granular); nunca confiar en
  `isDeveloperUnlocked` del cliente.
- DEV-1+ (fuera de alcance de esta fase): Shell Broker
  (`MYCDeveloperBroker`) como servicio Windows separado con identidad
  dedicada, `ShellSession` persistente con grace period de 15 minutos,
  Database Console, Logs, Services, Git — contrato de lifecycle ya
  documentado en `architecture/MOBILE_DEVELOPER_AUTHORITY.md` para que DEV-1
  no tenga que re-derivarlo.
- El estado global y pendientes ajenos a esta entrega permanecen bajo
  `project/PROJECT_STATUS.md` y `project/TECHNICAL_DEBT.md`.

## Autoridades documentales

`project/DOCUMENTATION_INDEX.md` rige la jerarquía. La autoridad Developer
está en `architecture/MOBILE_DEVELOPER_AUTHORITY.md`; el contrato de sesión
y biometría Mobile permanece en `architecture/MOBILE_SECURITY_CONTEXT.md`,
sin cambios en esta fase. Inventario en `PROJECT_FILE_REGISTRY.md`. Los
cortes anteriores permanecen trazables en Git.
