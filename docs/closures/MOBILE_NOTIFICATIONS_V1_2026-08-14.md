# Cierre técnico — MYC Mobile Notifications V1

**Fecha:** 2026-08-14  
**Estado:** TERMINADO TÉCNICAMENTE — EN REVISIÓN FÍSICA

## Entrega

Se reutilizó `Notification` como registro persistente y se agregó
`PushDevice`, entrega desacoplada a Expo, eventos idempotentes de Tickets,
centro móvil, badge, deep links y sincronización por push, foreground, foco,
mutación local y pull-to-refresh. No se alteraron las invariantes de Tickets,
OT LAB, firmas, ERP web ni Motor de Resoluciones.

La migración `e6b8c0d2f4a6` se validó sobre PostgreSQL aislado con
upgrade/downgrade/upgrade y `alembic check`. No se aplicó sobre la base
compartida/productiva, no se generó build EAS y no se desplegó código.

## Evidencia automática

- Backend: `518 passed, 5 skipped, 3 warnings, 19 subtests passed`.
- Pruebas focales backend Notifications/Tickets/OT: `23 passed, 5 skipped`.
- Mobile: TypeScript y Expo lint sin errores; 4/4 pruebas de política de
  refresco; Expo Doctor 18/18.
- Inventario API regenerado: 392 operaciones clasificadas.

## Pendiente de aceptación

Ejecutar los checklists físicos iOS y Android: permiso concedido/denegado,
foreground/background/terminated, recepción multi-dispositivo, deep links con
sesión vigente/expirada, badge, canal Android, logout→otro usuario y flujos
create/approve/reject/resolve/signature-required. Después podrá decidirse una
build manual EAS/TestFlight.

## Deuda consciente

La entrega V1 es best-effort posterior al commit: no existe cola durable ni
retry automático, no se consultan receipts finales de Expo y no existen
preferencias, quiet hours o agrupación. Estos límites no afectan la
persistencia ni hacen del push la fuente de verdad.
