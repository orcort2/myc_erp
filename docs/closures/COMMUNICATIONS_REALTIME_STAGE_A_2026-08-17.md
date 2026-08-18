# Cierre técnico — Comunicaciones Realtime Etapa A

**Fecha:** 2026-08-17  
**Estado:** TERMINADA TÉCNICAMENTE — EN REVISIÓN

## Entrega

Se agregó `WS /api/realtime/ws`, autenticación JWT contra usuario real, cierre
por expiración, rooms de usuario/conversación con ownership, envelope v1 y un
hub en memoria detrás del puerto reemplazable `RealtimeHub`. MYC Mobile agrega
un único `RealtimeProvider`, estados de conexión, lifecycle AppState, backoff,
refresh HTTP existente, cleanup y punto de extensión para reconciliación.

REST sigue siendo fuente de verdad. No se cambió el ERP web, esquema, datos,
migraciones, mensajes, typing, lecturas, menciones, push ni Tickets.

## Validación

- Backend focal y basal de seguridad/auth/notificaciones/realtime: `28 passed`.
- Backend completo: `533 passed, 5 skipped, 3 warnings, 19 subtests passed`.
- Realtime backend: `7 passed` para autenticación, rechazos, identidad,
  ownership/IDOR, aislamiento, cleanup y envelope.
- MYC Mobile realtime: `4 passed`.
- MYC Mobile notifications: `4 passed`.
- TypeScript y Expo lint: correctos.
- Expo Doctor: `17/18`; tres dependencias Expo tienen desfase patch
  preexistente/concurrente y no se actualizaron fuera del alcance.
- Transporte Uvicorn real: `websockets 15.0.1` instalado; handshake sin
  credencial rechazado con HTTP `403` por el servidor ASGI mínimo.

## Límites y gate siguiente

El adaptador en memoria sólo funciona dentro de un proceso. Antes de producción
se debe confirmar la topología real; múltiples workers exigen backplane. Etapa
B no debe empezar hasta revisar este cierre. Antes de cualquier migración se
deben resolver el desfase Alembic y el respaldo oficial ausente.
