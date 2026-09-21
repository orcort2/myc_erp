> Estado: VIGENTE
>
> Tipo: Snapshot operativo verificable
>
> Autoridad: Media; no sustituye los documentos canónicos de project/
>
> Corte: 2026-09-21 — BIOMETRIC-1 / Fase 1

# Estado operativo actual del ERP MYC

## Repositorio y alcance verificado

- Rama de trabajo: `feat/mobile-session-authority-biometric-1`.
- Base: `main` en `57756cdbbbe89d8f65eca56fda1dcb5014f07ab0`, inicialmente
  limpia y alineada con `origin/main`. Un único commit de implementación.
- Sin push, merge ni despliegue en este trabajo.
- Mobile incorpora identidad de instalación independiente, sesiones server-side,
  hashes SHA-256 de refresh opaco, rotación, detección de reuse, logout y
  single-flight compartido con realtime; conserva identidad/permisos/scope.
- La extensión autorizada exige device en migración legacy y lo prohíbe en
  refresh opaco. La migración es de un solo uso, con vencimiento fijo y sin
  asumir prueba retrospectiva del dispositivo original.
- Auth Web, Portal, TTL global y PushDevice permanecen sin cambio de implementación.
  No se implementa biometría ni capacidades de infraestructura.

## Base de datos y respaldo

- Revisión inicial local/código: `6640c526c412`, único head.
- Migración nueva y única: `b10a1c202601`, padre `6640c526c412`.
- Upgrade local aplicado; `alembic current` = `alembic heads` = `b10a1c202601`.
- Tablas nuevas: `mobile_trusted_devices`, `mobile_auth_sessions`, con FKs,
  checks, unicidades e índices de dispositivo, familia, hashes y vigencia.
- Upgrade/downgrade/upgrade verificados en PostgreSQL aislado. Los esquemas
  transitorios de prueba se eliminan al finalizar; no se reseteó la base ERP.
- `backup_erp_myc_antes_prueba.sql` regenerado con `scripts/backup-db.sh`;
  su `alembic_version` se extrajo y coincide con `b10a1c202601`.
  El respaldo permanece local e ignorado por Git. Este documento no incluye datos sensibles.

## Validación final

- Backend focalizado: 66 passed, 2 warnings; incluye seis pruebas PostgreSQL
  reales de migración y concurrencia, además de contexto e inventario API.
- Backend completo: 1269 passed, 16 skipped, 34 warnings, 19 subtests passed.
  Las omisiones pertenecen a otras suites; las nuevas pruebas PostgreSQL corrieron.
- Mobile focalizado: 15 passed. Mobile completo: 680 passed.
- `npx tsc --noEmit` y `npm run lint`: exit 0, sin errores.
- Inventario API regenerado: 530 operaciones, incluido logout autenticado.
- Inventario funcional regenerado y filas revisadas; rutas existentes;
  `git diff --check` sin errores.
- Revisado: sin refresh plaintext en DB, sin nuevas contraseñas persistidas,
  sin cambio de auth Web/TTL ni acoplamiento con PushDevice.
- Evidencia, comandos, contratos y diff:
  [cierre BIOMETRIC-1](closures/BIOMETRIC_1_MOBILE_SESSION_AUTHORITY.md).

## Pendientes y límites

- Aceptación física iOS/Android; la build debe incluir expo-crypto SDK 54.
- Retirar fallback legacy tras 2026-10-22 00:00 UTC, sin prorrogar la ventana.
  Access legacy sin sesión conserva validez hasta su expiración original.
- Logout siempre limpia local, pero red fallida no prueba revocación remota.
  La baja push posterior a la revocación es best-effort y puede recibir 401.
- MYC Mobile permanece EN DESARROLLO como superficie completa. BIOMETRIC-2,
  TTL Mobile propio, panel de dispositivos e infraestructura están fuera de fase.
- El estado global y pendientes ajenos a esta entrega permanecen bajo
  `project/PROJECT_STATUS.md` y `project/TECHNICAL_DEBT.md`.

## Autoridades documentales

`project/DOCUMENTATION_INDEX.md` rige la jerarquía. El contrato de sesión está en
`architecture/MOBILE_SECURITY_CONTEXT.md`; estado, alcance, flujo, reglas y
decisiones se sincronizan en sus canónicos. Inventario en
`PROJECT_FILE_REGISTRY.md`. El corte anterior permanece trazable en Git.
