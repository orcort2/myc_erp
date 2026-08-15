> Estado: VIGENTE
>
> Tipo: Arquitectura vigente
>
> Corte verificado: 2026-08-14

# Notificaciones operativas MYC Mobile V1

## Contrato

El backend es la fuente de verdad. Un evento operativo crea primero una
`Notification` persistente e idempotente; después del commit del dominio se
intenta entregar un push a cada `PushDevice` activo mediante Expo Push Service.
El payload push identifica el recurso, pero la app siempre vuelve a consultar
la API antes de presentar su estado. Una falla de Expo no revierte Tickets,
OT, firmas ni la notificación persistida.

```text
transición válida → Notification + event_key → commit
                                             → Expo → dispositivo
API autenticada  ← centro / detalle / contador no leído
```

## Persistencia y ownership

- `Notification` conserva destinatario, actor, tipo, entidad, metadatos
  mínimos, `read_at`, `event_key` único y estado del intento push.
- `PushDevice` asocia un token Expo único con un usuario y admite múltiples
  dispositivos activos por usuario. Un registro repetido actualiza el mismo
  token; si cambia de usuario, queda reasignado exclusivamente al nuevo.
- El logout desactiva el dispositivo autenticado sin borrar historia.
- Listado, contador y lectura reutilizan `/api/notifications`; todos filtran
  por el usuario autenticado. Administrar un dispositivo ajeno responde 404.
- `read_at` es la única autoridad de lectura y el badge se deriva del conteo
  persistente de no leídas. `delivery_status` no demuestra que una persona la
  haya visto.

## Eventos V1 y destinatarios

| Evento | Destinatario |
| --- | --- |
| `ticket.created` | Usuarios internos activos cuyo permiso efectivo incluye `tickets.review`, excepto el actor. |
| `ticket.approved` | Solicitante del Ticket. |
| `ticket.rejected` | Solicitante del Ticket. |
| `ticket.resolved` | Solicitante del Ticket al cerrarse nuevamente la OT. |
| `ticket.signature_required` | Solicitante responsable cuando la reapertura o un cambio crítico requiere nuevas firmas. |

La resolución de revisores está centralizada y no depende del nombre de un
rol. `event_key` impide duplicar una notificación ante reintentos de la misma
transición.

## Entrega push

`ExpoPushNotificationService` es la única integración con Expo; los routers no
invocan al proveedor. El push contiene título operativo breve y los
identificadores `event_type`, `entity_type`, `entity_id`, `ticket_id` y
`work_order_id`, sin datos técnicos o de cliente. `DeviceNotRegistered`
desactiva el token. Errores de red, rate limit o proveedor se registran por ID
de notificación/usuario/categoría, nunca con el token completo.

En V1 el intento es best-effort inmediatamente después del commit y no se
reintenta automáticamente. `push_delivered_at` significa aceptación del ticket
por Expo, no recepción confirmada por APNs/FCM. El worker/outbox del Motor de
Resoluciones no se reutiliza porque su contrato pertenece exclusivamente al
Motor.

## Mobile y sincronización

- Login/restauración solicita permiso sólo cuando sigue `undetermined`; una
  negativa no bloquea la sesión ni el centro persistente.
- iOS usa Expo Notifications y safe areas; Android crea el canal
  `operational` y solicita el permiso aplicable.
- La campana muestra el contador API y abre un centro paginado (25 por página),
  con filtros Todas/No leídas, estado textual, fechas amigables, retry mediante
  pull-to-refresh y acción de marcar todas.
- Al tocar un push, el payload sólo selecciona Ticket u OT. Si falta sesión,
  se conserva el destino hasta restaurarla; la pantalla obtiene el recurso
  actual desde backend.
- Un evento foreground invalida contador, lista y detalle activos. Tickets y
  OT también refrescan al recuperar foco; las mutaciones locales publican una
  invalidación inmediata y no esperan su propio push.
- `NotificationEventDeduper` y `RefreshGate` evitan duplicados y ráfagas. No
  existe `setInterval`, polling global ni recarga completa de la aplicación.
- Pull-to-refresh permanece disponible en Tickets, OT y Notificaciones.

## Endpoints

- `POST /api/mobile/v1/notifications/devices`
- `DELETE /api/mobile/v1/notifications/devices/{device_id}`
- `GET /api/notifications?limit=&offset=&unread_only=`
- `GET /api/notifications/unread-count`
- `POST /api/notifications/{notification_id}/read`
- `POST /api/notifications/read-all`

## Garantías y límites V1

Persistencia, ownership, idempotencia de evento, multi-dispositivo y no
rollback del dominio están cubiertos. Quedan fuera: preferencias, quiet hours,
agrupación, recibos Expo/APNs/FCM, retries durables, APNs/FCM directos, correo,
SMS, WhatsApp, marketing e IA. La aceptación física en iPhone/iPad/Android y
una build TestFlight nueva requieren ejecución manual posterior.
