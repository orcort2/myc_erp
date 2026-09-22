> Estado: VIGENTE
>
> Tipo: Snapshot operativo verificable
>
> Autoridad: Media; no sustituye los documentos canónicos de project/
>
> Corte: 2026-09-21 — DEV-0 (Developer Authority para MYC Mobile)

# Estado operativo actual del ERP MYC

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
- Detalle completo: [MOBILE_DEVELOPER_AUTHORITY.md](architecture/MOBILE_DEVELOPER_AUTHORITY.md).

## Base de datos y respaldo

- Revisión inicial local/código: `9970e12e5f0d`, único head (BIOMETRIC-2).
- Migración nueva y única: `602a09af6218`, padre `9970e12e5f0d`.
- Upgrade aplicado en este entorno; `alembic current` = `alembic heads` =
  `602a09af6218`.
- Tabla nueva: `developer_sessions`, con FKs a `users`,
  `mobile_trusted_devices` y `mobile_auth_sessions`, `token_hash` UNIQUE e
  índices de usuario, dispositivo, sesión Mobile, vencimiento y revocación.
- Upgrade verificado contra PostgreSQL local de este entorno. No se
  modificó ninguna migración histórica.
- `test_schema_integrity_stage_2a.py::test_current_revision_is_the_single_head`
  en verde: sigue habiendo un único head tras la nueva migración.

## Permisos

Nuevos permisos explícitos en `app/core/permissions.py`, asignados sólo al
rol `Desarrollador`: `developer.access`, `developer.database.read`,
`developer.database.write`, `developer.database.admin`,
`developer.shell.access`, `developer.system.read`, `developer.logs.read`,
`developer.services.execute`, `developer.git.read`. Sólo `developer.access`
se usa en esta fase. `"*"` (Administrador) sigue abriendo Developer por la
semántica global existente del mecanismo de permisos — riesgo aceptado y
documentado explícitamente, no un atajo por email/user-id (ver sección
"Riesgo aceptado" en el documento de arquitectura).

## Endpoints nuevos

`POST|GET|DELETE /api/mobile/v1/developer/session`
(`app/routers/mobile_developer.py`), clasificados en el inventario de
acceso HTTP bajo el mismo mecanismo genérico `mobile_context` que el resto
de `/api/mobile/v1/*` (permiso base `mobile.access`); el gate fino de
`developer.access` + actor interno vive en el propio endpoint
(`require_internal_mobile_permission`), igual patrón que
`mobile_technician.py`. `GET`/`DELETE` exigen además el header dedicado
`X-MYC-Developer-Token`.

## Validación final

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

- Política canónica explícita "actor interno + capability Developer
  explícita, sin bastar `'*'` por accidente" queda pendiente para una fase
  futura (requiere una decisión de producto, no sólo técnica).
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
