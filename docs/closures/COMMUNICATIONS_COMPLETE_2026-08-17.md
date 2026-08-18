# Cierre técnico de Comunicaciones — 2026-08-17

## Resultado

Las Etapas A–I de Comunicaciones quedan **TERMINADAS TÉCNICAMENTE — EN
REVISIÓN**. REST y PostgreSQL permanecen como fuente de verdad; WebSocket v1
entrega cambios posteriores al commit y el cliente recupera cualquier hueco
por secuencia. No hubo despliegue, build EAS ni commit.

## P0 de topología

La inspección read-only de producción confirmó Cloudflare/`cloudflared`, un
único comando Uvicorn sin `--workers` y un único listener
`127.0.0.1:8000`. La topología real es single-worker, por lo que el adaptador
en memoria es suficiente y no corresponde introducir un backplane. El puerto
`RealtimeHub`, su composición de runtime y el publicador desacoplado conservan
el cambio futuro localizado. Escalar a múltiples procesos/hosts queda
prohibido hasta instalar y validar ese backplane.

## Capacidades entregadas

- Conversaciones directas idempotentes, grupos internos y vínculo opcional a
  Ticket con acceso backend.
- Historial paginado, sync incremental por secuencia y conteos no leídos.
- Mensajes optimistas con `client_message_id`, reconciliación, deduplicación,
  error y reintento seguro.
- Orden canónico bajo lock, recibos delivered/read monótonos y soporte de
  múltiples dispositivos.
- Typing efímero autorizado y con expiración; menciones individuales, `@todos`
  y rol con validación de participantes/perfiles.
- Notificación persistente sin cuerpo sensible, push Expo best-effort y deep
  link recuperado desde REST.
- JWT mediante subprotocolo, revalidación de usuario, rooms `user:{id}` y
  `conversation:{id}`, ownership/IDOR y cierre `4401` con refresh HTTP.
- Lifecycle foreground/background/logout, backoff y resync completo tras
  reconexión.

## Datos y migración

La migración `f7c9d1e3a5b7` agrega secuencia e idempotencia, cursor de
participante, recibos y menciones normalizados, grupos y relación opcional con
Ticket. El ciclo aislado base→head→base→head, `alembic check` y restore drill
terminaron en `f7c9d1e3a5b7`. La base local quedó en head y el respaldo oficial
se regeneró con 75,050,260 bytes y SHA-256
`f2280b0e003f582601462b269f3b3fb1165e58d00acf247d8c8564f691b81b14`.

## Validaciones verificadas

- Backend completo: 547 passed, 5 skipped y 19 subtests passed.
- Comunicaciones/realtime focalizado: 14 passed.
- PostgreSQL real concurrente: cinco mensajes simultáneos conservaron
  secuencias 1–5; dos reintentos simultáneos compartieron un solo mensaje 6.
- Frontend web: 43 pruebas y build productivo correctos.
- MYC Mobile: 17 pruebas relevantes, TypeScript y lint correctos; export iOS
  Expo correcto (1,156 módulos, bundle 2.95 MB).
- Esquema: migración reversible, restore de respaldo y 398/398 operaciones
  FastAPI clasificadas.

Las advertencias no bloqueantes fueron las deprecaciones existentes de
Starlette/passlib/Alembic, el aviso de chunk web mayor a 500 kB y Expo Doctor
17/18 por tres paquetes Expo un patch por debajo de la recomendación de SDK
54.

## Archivos y arquitectura

Backend concentra el dominio en modelos, schemas, servicio y router de
Comunicaciones; realtime conserva autenticación, contratos, puerto, runtime y
router separados. MYC Mobile agrega servicio REST, tipos, provider de estado,
reconciliador puro, bandeja/detalle y consumo de notificaciones. El inventario
oficial contiene el detalle por archivo.

## Riesgos y deuda restante

El cierre no equivale a aceptación física. Falta validar con dos dispositivos
reales iOS/Android el push, los deep links, background/foreground, escritura
simultánea, typing y recibos. También quedan pendientes los patches Expo ya
registrados. Un aumento futuro de workers exige backplane antes del cambio;
no es deuda de la topología vigente, sino una compuerta operativa.

No se modificaron flujos ni reglas funcionales de OT/ETS. La migración local
aplicó también revisiones ya existentes que estaban pendientes antes de
Comunicaciones, sin editar esos frentes.
