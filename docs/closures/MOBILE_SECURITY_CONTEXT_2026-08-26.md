> Estado: TERMINADO TÉCNICAMENTE — EN REVISIÓN
>
> Fecha: 2026-08-26

# Cierre técnico — identidad y scope MYC Mobile

## Resultado

MYC Mobile dejó de interpretar `lab_work_orders.use` como autorización general.
La sesión canónica usa `mobile.access` y un `MobileSecurityContext` que resuelve
en base actores staff o cliente. `User` sigue siendo la identidad única; el
cliente usa `ClientPortalMembership` y roles externos persistidos.

Se agregaron Viewer externo, Operativo Jr y Operativo Sr sin permisos de
folios. La regla una cuenta externa→una organización activa se aplica en altas,
reactivación, aprobación e invitaciones y se refuerza con índice parcial único.
La migración conserva memberships históricas no activas.

El scope externo implementado se limita al agregado temporal LAB: OT, equipos,
firmas, PDFs, revisiones y Tickets. Las rutas productivas ETS/OT/Equipos/Hojas
de Campo/Venta quedan exclusivas de staff. Notificaciones/push usan ownership
por usuario; realtime exige permiso de Comunicaciones, participación y mismo
cliente.

## Migración

- revision: `d6f2a4c8e0b1`;
- down revision: `c4e0ead1af28`;
- columna nullable: `lab_work_orders.client_id`;
- índice: `ix_lab_work_orders_client_id`;
- índice parcial único:
  `uq_client_portal_memberships_active_user WHERE status='active'`;
- preflight PostgreSQL: aborta si existen usuarios con más de una membership
  activa, sin reasignar ni borrar historia.

## Validaciones

- backend focalizado de seguridad Mobile/Portal/realtime/API: `69 passed`;
- regresión adicional de contención/Venta/eliminación: `26 passed`;
- regresión LAB: `21 passed`, `5 skipped` y una falla preexistente reproducida
  sin cambios desde `HEAD` (`test_original_critical_edit_before_close_still_invalidates_signature`);
- pruebas Mobile: `73 passed`;
- frontend administración: `9 passed`;
- lint MYC Mobile: correcto;
- TypeScript MYC Mobile: correcto;
- export Expo iOS/Android/Web: correcto;
- Vite build: correcto con warning de chunks preexistente;
- Alembic head: `d6f2a4c8e0b1` único;
- SQL PostgreSQL upgrade/downgrade de la revisión: correcto;
- migración local aplicada: `d6f2a4c8e0b1 (head)`;
- respaldo oficial regenerado: 75,534,807 bytes, SHA-256
  `b23598cfcc3a728ab09734d01d0750eda681dde60061c86bda2cdec18addfcbc`,
  con `alembic_version=d6f2a4c8e0b1`.

Quedan QA físico y retiro futuro de compatibilidad para JWT internos ya
emitidos. La falla LAB citada pertenece a la máquina de estados previa y queda
fuera de esta corrección de seguridad. La generación offline completa
`base→head` conserva la limitación histórica registrada como TD-054; no afecta
el upgrade online ni el SQL acotado de esta revisión. No hubo folios, commit,
push, build EAS ni despliegue.
