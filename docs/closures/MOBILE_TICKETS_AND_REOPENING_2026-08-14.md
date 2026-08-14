# Cierre técnico — Tickets y reapertura controlada OT LAB

Fecha: 2026-08-14
Estado: TERMINADO — EN REVISIÓN MANUAL

Se implementaron búsqueda backend/móvil por folio y cliente, filtros de estado,
debounce y paginación; módulo Tickets; aprobación/rechazo por permiso;
reapertura grupal con snapshot; preservación condicionada o invalidación de
firmas; control optimista; PDF versionado y auditoría.

La migración `d4e7a9c2b6f1` fue probada en PostgreSQL aislado mediante
`base → head`, `head → c6e8a1b4d2f9` y `c6e8a1b4d2f9 → head`. La suite focal
backend cubre filtros, seguridad, lifecycle, firma histórica, nueva firma y
PDF histórico. TypeScript y Expo lint quedan verdes.

Pendiente antes de distribuir: checklist manual completo en Android/iPhone,
incluyendo dos sesiones concurrentes, impresión/compartir de revisión anterior
y actual, y UX de bandeja con cuentas Técnico y Calidad. No se ejecutó
`eas build`, `eas submit` ni publicación.
