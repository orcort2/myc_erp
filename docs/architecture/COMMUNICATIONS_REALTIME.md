> Estado: VIGENTE — EN REVISIÓN
>
> Tipo: Arquitectura vigente
>
> Corte verificado: 2026-08-17 — Etapas A–I implementadas

# Comunicaciones y transporte realtime

## Frontera y fuente de verdad

PostgreSQL y la API REST son la autoridad de conversaciones, mensajes,
secuencias, recibos, menciones, no leídos y notificaciones. WebSocket sólo
reduce latencia: todo evento funcional se publica después del commit y una
desconexión se recupera mediante REST. El cliente nunca usa el reloj ni el
orden de llegada del socket como cursor canónico.

La implementación cubre conversaciones directas internas idempotentes, grupos,
la relación opcional con un Ticket accesible, historial paginado, envío
optimista, reintento, reconciliación, typing efímero, recibos por usuario,
menciones individuales/masivas, bandeja de menciones, notificaciones
persistentes y push best-effort. No se agregó un estado funcional paralelo en
WebSocket ni `localStorage`.

## Topología productiva y puerto del hub

La topología productiva se comprobó el 2026-08-17 sin modificar el servidor:

- Cloudflare publica `api-erp.mycmetrology.com.mx` y `cloudflared` opera como
  servicio;
- `MYCBackend.exe` inicia exactamente un `uvicorn.exe` con
  `app.main:app --host 127.0.0.1 --port 8000`;
- no existe `--workers` y se observó un único listener en
  `127.0.0.1:8000`.

Por tanto, la topología real vigente es de un solo proceso/worker y
`InMemoryRealtimeHub` es correcto para la habilitación actual: no se requiere
backplane. La lógica funcional depende exclusivamente del puerto
`RealtimeHub`; `runtime.py` compone el adaptador y `events.py` publica sin
conocer sus estructuras internas. Aumentar workers, procesos, hosts o réplicas
es un cambio de arquitectura bloqueado hasta sustituir ese adaptador por un
backplane probado entre procesos. Rooms y envelope no deben cambiar.

## Autenticación, autorización y rooms

`WS /api/realtime/ws` negocia `myc.realtime.v1` y
`auth.<access-jwt>`. El token no viaja en URL. Antes de aceptar, el backend
valida firma, expiración y `token_type=access`, y vuelve a resolver un usuario
interno activo. Al expirar cierra con `4401`; MYC Mobile usa exclusivamente
`AuthProvider.refreshSession` y `POST /auth/refresh`, y después reconecta.

Rooms vigentes:

- `user:{id}` se une automáticamente con la identidad server-side y permite
  varios dispositivos del mismo usuario;
- `conversation:{id}` exige participación/ownership en cada subscribe y en
  cada comando; unsubscribe elimina sólo esa membresía.

Un recurso ajeno responde 404 en REST o `conversation_forbidden` en el canal,
sin revelar participantes ni contenido. Grupos sólo admiten usuarios internos
activos. Una relación con Ticket exige ser solicitante o poseer
`tickets.view_all`; Comunicaciones no modifica el dominio de Tickets.

## Persistencia, orden e idempotencia

Cada conversación conserva `next_message_sequence`; el backend bloquea su fila
con `FOR UPDATE`, asigna una secuencia creciente y confirma mensaje, recibos,
menciones y notificaciones en una transacción corta. La restricción
`(conversation_id, sequence)` protege el orden. El par
`(conversation_id, sender_user_id, client_message_id)` hace idempotente el
reintento optimista, incluso bajo dos transacciones PostgreSQL simultáneas.
Sólo la creación ganadora emite realtime y agenda push.

Los recibos `delivered/read` son por mensaje y usuario. Los cursores del
participante avanzan de forma monótona y nunca retroceden cuando dos
dispositivos reportan fuera de orden. Una lectura también marca sus menciones.
Las menciones se guardan estructuradas; una mención individual debe pertenecer
a la conversación. `@todos` y grupos por rol sólo están disponibles para
Administrador, Desarrollador y Calidad, y un rol debe tener participantes
reales en esa conversación.

## API REST

La superficie autenticada `/api/communications` ofrece:

- directorio autorizado, bandeja de menciones y listado de conversaciones;
- creación directa/grupal y detalle;
- historial anterior por `before_sequence` y recuperación posterior por
  `after_sequence`;
- creación idempotente de mensajes;
- avance de recibos `delivered` y `read`.

Los listados calculan último mensaje y no leídos por consultas agrupadas; no
cargan todo el historial. Los cursores y filtros siempre se aplican después de
validar membership.

## Envelope y eventos v1

Todo evento generado por servidor contiene `version`, `event`, `event_id`,
`occurred_at` UTC y `data`. Están vigentes:

- conexión/control: `realtime.connected`, `conversation.subscribed`,
  `conversation.unsubscribed`, `connection.pong`, `realtime.error`;
- persistentes: `message.created`, `message.delivered`, `message.read` y
  `notification.created`;
- efímeros: `typing.started` y `typing.stopped`.

Typing no se persiste y no prueba entrega. El servidor deriva actor y
conversación autorizada; el cliente no puede escoger otro usuario.

## Lifecycle y reconciliación móvil

Existe un `RealtimeProvider` y un `CommunicationsProvider` por sesión. El
envío crea una fila visual `sending` con `client_message_id`; la respuesta
REST o `message.created` la concilia a `sent`, y un error la deja `failed` con
reintento del mismo identificador. La deduplicación usa ID persistente o ID de
cliente, no timestamp.

En apertura se carga REST y se suscribe a la conversación. Tras reconexión el
provider recorre `/sync` desde la última secuencia conocida hasta cerrar todo
hueco, y luego refresca contadores. El historial anterior usa paginación
separada. Al mostrar una conversación se reporta `read`; un mensaje recibido en
otra conversación actualiza no leídos. Typing se limita y expira localmente
para no quedar pegado.

Background/inactive cierra socket y timers; foreground reconecta y
resincroniza. Logout elimina listeners, estado y reconexiones. Un `4401`
intenta una sola renovación mediante la autoridad HTTP; si falla, termina la
sesión.

Las notificaciones persistentes son recuperables por HTTP y usan una vista
previa genérica sin el cuerpo del mensaje. Expo Push se intenta después del
commit sobre todos los dispositivos activos; una falla externa no revierte el
mensaje. El deep link abre la conversación y vuelve a consultar REST.

## Estado, validación y límites

La entrega A–I está **TERMINADA TÉCNICAMENTE — EN REVISIÓN**. Se validaron
backend completo, frontend web, TypeScript/lint/bundle móvil, pruebas de
lifecycle/reconciliación y una carrera real PostgreSQL con cinco escritores y
un reintento duplicado. Alembic y restore drill alcanzan
`f7c9d1e3a5b7`.

Antes de aceptarla físicamente faltan dos dispositivos reales para comprobar
push, background/foreground, escritura simultánea, indicadores y deep links en
iOS/Android. No hubo build EAS ni despliegue. El ERP web conserva su interfaz
existente y no se amplió dentro de este alcance. Cualquier futura topología
multi-worker exige el backplane indicado antes de desplegarla.
