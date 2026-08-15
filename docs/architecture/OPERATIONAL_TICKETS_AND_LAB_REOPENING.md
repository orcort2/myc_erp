> Estado: VIGENTE
>
> Corte verificado: 2026-08-14
>
> Alcance: Tickets operativos y reapertura documental controlada de OT LAB

# Tickets operativos y reapertura controlada de OT LAB

## Flujo canónico

```text
OT completed
  → técnico crea REOPEN_WORK_ORDER
  → ticket pending; la OT permanece cerrada
  → revisor rechaza, o aprueba con preserve/invalidate
  → snapshot inmutable de cada OT del grupo y PDF anterior
  → grupo draft, revisión N+1, ticket in_progress
  → edición con edit_version
  → cambio crítico invalida automáticamente la firma activa
  → firma nueva si es requerida
  → cierre genera PDF nuevo y resuelve el ticket
```

`OperationalTicket` es la entidad extensible. En este corte sólo acepta
`reopen_work_order`; sus estados canónicos son `pending`, `approved`,
`rejected`, `in_progress`, `resolved` y `cancelled`. La aprobación ejecuta la
reapertura en la misma transacción y deja el ticket directamente
`in_progress`; `approved` queda reservado para una futura aprobación diferida.

## Inmutabilidad y revisiones

Antes de reabrir, cada integrante del grupo genera un
`LabWorkOrderRevision` con snapshot de datos/equipos, sesión de firma, PDF,
checksum y número de revisión. El registro activo incrementa
`revision_number`, limpia únicamente su PDF corriente y conserva el folio.
Los PDFs históricos se descargan por revisión y nunca se sobrescriben.

Las firmas históricas tampoco se borran. La restricción de sesión cambia de
una sesión única por raíz a una versión única por `(root_work_order_id,
version)`, permitiendo una nueva sesión sin duplicar firmas dentro de una
misma revisión.

## Clasificación determinista de cambios

Pueden preservar firma: contacto, teléfono, correo, código postal, ciudad,
estado, orden de compra, observaciones y `report_number` de equipo.

Invalidan automáticamente la firma activa del grupo: cliente, fechas,
domicilio, agregar/eliminar OT o equipo, instrumento, marca, identificación,
serie y condición física. La autorización `preserve` no puede evitar esta
regla backend. La autorización `invalidate` exige nuevas firmas desde el
inicio.

Toda edición de una revisión reabierta debe enviar `expected_edit_version`.
Una versión ausente u obsoleta responde `409 REVISION_CONFLICT`.

## Permisos

- `tickets.create`: crear solicitudes.
- `tickets.view_own`: consultar solicitudes propias.
- `tickets.view_all`: ampliar la bandeja a todas las solicitudes.
- `tickets.review`: aprobar o rechazar.
- `work_orders.reopen`: capacidad funcional de reapertura.
- `work_orders.reopen_preserve_signatures`: aprobar preservación condicionada.
- `work_orders.reopen_invalidate_signatures`: exigir firma nueva.

El Técnico recibe creación y consulta propia. Calidad recibe consulta global,
revisión y ambas políticas. Desarrollador recibe el conjunto explícito;
Administrador conserva su comodín. El frontend sólo oculta acciones; cada
decisión sensible vuelve a validarse en el backend.

## API móvil

Base: `/api/mobile/v1/technician`.

- `POST /tickets`
- `GET /tickets?status=&search=&offset=&limit=`
- `GET /tickets/{id}`
- `POST /tickets/{id}/approve`
- `POST /tickets/{id}/reject`
- `GET /lab-work-orders/{id}/revisions`
- `GET /lab-work-orders/{id}/revisions/{revision}/pdf`

No existe un endpoint alterno de reapertura directa: aprobar el Ticket es el
único camino para crear snapshots y habilitar edición.

## Búsqueda y paginación

`GET /lab-work-orders` admite `folio`, `client`, `status`, `offset` y `limit`.
Folio usa coincidencia parcial textual, cliente usa `ILIKE`, ambos filtros se
combinan con AND y se ejecutan en SQL. La respuesta continúa siendo una lista
para no romper la build TestFlight vigente; el móvil pagina con bloques de 25
y acción “Cargar más”. Los dos inputs tienen debounce de 400 ms y limpieza
independiente o conjunta.

## Auditoría y concurrencia

Se auditan creación, rechazo, aprobación/reapertura, campos modificados,
invalidación automática, firma, cierre y actores. La resolución adquiere un
`FOR UPDATE` exclusivamente sobre la fila de `operational_tickets`; las
relaciones eager-loaded se consultan después dentro de la misma transacción y
no forman parte del lock. Sólo un ticket `pending` puede resolverse: cualquier
segundo approve/reject, incluso si esperó el lock de otra transacción, responde
409 `TICKET_ALREADY_RESOLVED`. El cierre repetido del grupo permanece
idempotente.

## Eventos de notificación

Las transiciones válidas publican, dentro de su misma transacción,
`ticket.created`, `ticket.approved`, `ticket.rejected`, `ticket.resolved` y,
cuando corresponde, `ticket.signature_required`. Notifications consume el
resultado sin cambiar locks, policies de firma, revisiones ni resolución
única. La entrega Expo ocurre después del commit conforme al contrato
[`MOBILE_NOTIFICATIONS_V1.md`](MOBILE_NOTIFICATIONS_V1.md).

## Límite vigente

Este contrato se aplica al agregado temporal OT LAB. No cambia ServiceOrder,
ServiceWorkOrder, firmas ETS, Motor de Resoluciones ni el ERP web. La revisión
manual del nuevo sprint en dispositivos físicos y TestFlight sigue pendiente;
no se ejecutó build EAS ni publicación.
