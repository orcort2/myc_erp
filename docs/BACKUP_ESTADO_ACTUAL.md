> Estado: VIGENTE
>
> Tipo: Snapshot operativo verificable
>
> Autoridad: Media; no sustituye los documentos canónicos de project/
>
> Corte: 2026-09-25 — DEV-1C EN REVISIÓN (activos de despliegue del servicio Windows `MYCDeveloperBroker` bajo `NT SERVICE\MYCDeveloperBroker`, sin commit; instalación en Windows pendiente) sobre `main` `05f4c625` (DEV-1B mergeado, PR #9)

# Estado operativo actual del ERP MYC

## DEV-1C — dos ajustes posteriores a la validación Windows

- Base de esta revisión: `9b71c21`, worktree `myc_erp-dev1c`, rama
  `feat/mobile-developer-broker-service-dev1c`; estado inicial limpio.
- El usuario confirma instalación/reinstall idempotente, secreto reutilizado,
  ledger 6 y uninstall real/WhatIf validados en Windows, con aislamiento y
  hardening preservados. Ese reporte supera los pendientes de instalación del
  corte anterior que se conserva debajo; estos dos ajustes aún requieren QA Windows.
- Nuevos backups en `DeploymentRoot\acl-backups`; legacy intactos, restaurables
  sólo mediante ruta explícita. Sin migración, borrado histórico ni restore automático.
- Frontera ACL: backups en `persistent_protected`, fuera de `owned`; borrado
  rechazado por `remove-owned-tree`. Misma ACL y compatibilidad legacy.
- Mensaje final WhatIf corregido; ShouldProcess, schema 6 y SeServiceLogonRight intactos.
- DEV-1C: 314 passed (incluye estáticos PowerShell). Regresión Broker:
  262 passed, 12 skipped (Windows). git diff --check OK. Sin operaciones Windows reales, commit ni push en esta revisión.

## DEV-1C — Servicio Windows `MYCDeveloperBroker` / identidad dedicada (EN REVISIÓN)

- Worktree `/Users/saulcortes/Developer/myc_erp-dev1c`, rama
  `feat/mobile-developer-broker-service-dev1c`, base `05f4c625` (= `main`,
  merge PR #9). Sin commit, sin push, sin PR. Producción no se tocó.
- Implementado (sólo activos de despliegue; `backend/app/developer_broker/`
  sin cambios): `deploy/windows/developer-broker/` con plantilla WinSW,
  `broker_deploy.py` (plan/política ACL, veredicto de servicio, INF de
  `SeServiceLogonRight`, render del XML, bloque gestionado de `backend\.env`,
  secreto por generación/stdin/reuse), módulo PowerShell, instalador con
  preflight, desinstalador acotado, validador post-instalación y
  endurecimiento de `C:\MYC\Services`. `.gitignore` excluye cualquier XML
  renderizado bajo `deploy/windows/`.
- Identidad: cuenta virtual `NT SERVICE\MYCDeveloperBroker` registrada con
  `sc.exe create … obj=` (nunca LocalSystem, ni transitoriamente); SID
  resuelto en el host por LSA + SCM; cliente ERP `S-1-5-18` verificado.
- Hallazgo de seguridad de producción: `C:\MYC\Services` con
  `Authenticated Users: Modify` sobre wrappers/XML de servicios LocalSystem.
  Endurecimiento reproducible con respaldo JSON por entrada (SDDL) y
  restauración explícita con `Restore-MYCServicesAcl.ps1` (TD-061);
  **no aplicado todavía** en `ADMIN`.
- Configuración de producción: no existe aún ningún `DEVELOPER_BROKER_*`
  en `backend/.env` del servidor; la escribirá el instalador (bloque
  gestionado, deshabilitado hasta validar el Broker).
- Correcciones de auditoría (2026-09-25, sin commit): ledger de propiedad
  `install-state.json` incremental/atómico (P0: `SeServiceLogonRight`
  `pending`→`added`, nunca si ya era efectivo; uninstall deshace sólo lo
  registrado, también tras instalación parcial); alcance ACL reducido a los
  directorios `developer-broker` (P1: `C:\MYC\Deployment` y
  `C:\MYC\Logs` sólo se inspeccionan); aprovisionamiento XML + `.env`
  transaccional con journal transitorio y recuperación (P1). Tras las
  correcciones: despliegue 150 passed; contrato + named pipe + Windows +
  endpoint 262 passed, 12 skipped; DEV-0 + conformidad 97 passed, 1 skipped.
- Cierre DEV-1C (2026-09-25, sin commit): ledger esquema 6; propiedad del
  bloque de `backend\.env` con marcador no secreto + huella PBKDF2 (un
  `pending` nunca toca un bloque sin prueba; un `owned` alterado se
  rechaza); `acl_grants` por concesión `pending → owned` con verificación
  exacta y revocación sólo de la ACE exacta; reinstalación sin re-proteger
  `ServiceDir`/`LogDir` propios; `Restore-MYCServicesAcl.ps1` para el
  respaldo JSON por entrada (sin `icacls /restore`). Validación en el
  reporte de cierre.
- Quinta ronda de auditoría (2026-09-25, sin commit): ledger esquema 5;
  directorios y bloque `backend\.env` con `none → pending → owned`
  (prueba releída antes de `owned`; `pending` nunca borra); puerta SCM única
  (`Invoke-MYCGuardedScm`) para stop/config/sidtype/description/failure/
  failureflag/auto/start/delete y en el `catch`; hardening sin `/T` (raíz
  primero, "bloquear y luego enumerar"), respaldo SDDL por entrada y borrado
  sin seguir enlaces. Validación: despliegue 263 passed (incluye carreras
  reproducidas con sistema de archivos real para el borrado); DEV-1A/1B 262
  passed, 12 skipped; DEV-0 + conformidad 97 passed, 1 skipped. Residuales:
  TD-062.
- Cuarta ronda de auditoría (2026-09-25, sin commit): SCM re-consultado y
  SID del ledger exigido justo antes de reconfigurar/detener/eliminar;
  uninstall sin ledger es no-op (no toca `backend\.env`); normalización ACL
  elimina Deny explícitos (`/remove:d`); cierre garantizado del handle LSA;
  ejemplos del instalador con `-WinSWExpectedSha256`; config WinSW obsoleta
  eliminada del destino. Validación: despliegue 226 passed; DEV-1A/1B 262
  passed, 12 skipped; DEV-0 + conformidad 97 passed, 1 skipped.
- Tercera ronda de auditoría (2026-09-25, sin commit): propiedad estricta
  del servicio en reinstalación; rollback de `SeServiceLogonRight` como
  único miembro vía LSA (pendiente de validar en Windows); lápida del
  ledger con directorios retenidos; ACE externa exacta + `/grant:r`;
  reinicio de `MYCBackend` como activación controlada (código 3); WinSW
  sólo con SHA-256 de procedencia confiable (**P0 operativo pendiente
  antes de Windows**); recorrido sin `Get-ChildItem -Recurse`; Deny
  explícitos como violación; redacción exacta del manejo del secreto.
  Validación: despliegue 218 passed; DEV-1A/1B 262 passed, 12 skipped;
  DEV-0 + conformidad 97 passed, 1 skipped.
- Segunda ronda de auditoría (2026-09-25, sin commit): propiedad del
  servicio `none|pending|owned` con re-consulta del SCM (ledger esquema 3);
  rechazo de ACE explícitas preexistentes del Broker en repo/venv/Python
  home; rechazo de reparse points antes de operaciones recursivas y en
  rutas externas; reversión verificada de `DEVELOPER_BROKER_ENABLED` en el
  `catch`; código de salida explícito (`Invoke-MYCNativeResult`); limpieza
  de temporales `secedit` en `finally`. Validación: despliegue 179 passed;
  contrato + named pipe + Windows + endpoint 262 passed, 12 skipped; DEV-0
  + conformidad 97 passed, 1 skipped.
- Validación macOS previa a las correcciones (2026-09-25): despliegue
  `test_developer_broker_deployment.py` 109 passed; contrato 102; named
  pipe 146; Windows 12 skipped (no es Windows); endpoint health 14; DEV-0 +
  conformidad 97 passed, 1 skipped; backend completo 1694 passed, 36
  skipped, 1 failed — el fallo es ambiental
  (`test_sat_xls_source.py::…regime_626…`: `backend/resources/sat/catalogo
  sat.xlsx` está en `.gitignore` y no existe en el worktree; con una copia
  temporal del archivo oficial pasa 4/4). `alembic heads` =
  `c4d8e2f1a7b3` (sin migraciones); compileall e import smoke OK; escaneo
  sin ejecución de procesos en el paquete del Broker ni en
  `broker_deploy.py`; `broker.health` única operación; `git diff --check`
  limpio.
- **Pendiente**: ejecutar en Windows real el runbook de
  `architecture/MOBILE_DEVELOPER_BROKER.md` ("Despliegue como servicio
  Windows (DEV-1C)"): preflight, endurecimiento, instalación,
  `Test-MYCDeveloperBroker.ps1`, reinicio de `MYCBackend`, health
  end-to-end desde Mobile, y un ensayo de rollback. Nada de la parte
  Windows de DEV-1C se ha ejecutado.

## DEV-1B — Windows Named Pipe + Broker host (MERGEADO, PR #9)

- `0b9572d` implementación inicial; `6a9374c` corrección de identidad del
  cliente en Windows (`ImpersonateNamedPipeClient`/`RevertToSelf` vía
  `win32security`). Re-ejecución real en Windows de
  `test_developer_broker_windows.py`: **11 passed, 1 skipped, 0 failed** (el
  skip es el rechazo de clientes remotos, que requiere un segundo host).
- PR #9 mergeado; `main` = `05f4c625f5f9cd7620a1a84a543b7f31d787ee27`;
  backend de producción desplegado en ese `main`.
- Implementado: `framing.py`, `pipe_name.py`, `windows_pipe.py`
  (`WindowsNamedPipeTransport`, `NamedPipeBrokerListener`, DACL explícita de
  dos SIDs `0x0012019F`/`0x00100083`, primera instancia exclusiva,
  `PIPE_REJECT_REMOTE_CLIENTS`, identidad del servidor verificada antes de
  escribir, nivel identification, identidad del cliente verificada) y
  `host.py`. Settings `DEVELOPER_BROKER_SERVICE_SID` y
  `DEVELOPER_BROKER_CLIENT_SID`. Dependencia `pywin32==312;
  sys_platform == "win32"`.
- Histórico (no vigente): la primera ejecución real de `0b9572d` dio 5
  passed, 6 failed, 1 skipped por el defecto de módulo pywin32 ya corregido
  en `6a9374c`; detalle en `architecture/MOBILE_DEVELOPER_BROKER.md`
  ("Validación de DEV-1B").

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
