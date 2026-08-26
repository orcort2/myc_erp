# Auditoría e implementación — Bloque 2 de grupos anticipados OT LAB

> Corte verificable: 2026-08-26. Estado: implementado, pendiente de aceptación física Mobile/Web.

## Auditoría inicial

El folio LAB ya tenía autoridad correcta en `InstitutionalFolioSequence` y `_allocate_folio`: rango 6400–6999, lock transaccional PostgreSQL, reconciliación con el máximo y unicidad en base. La identidad de grupo vigente era `root_work_order_id`, con cadena `previous_work_order_id` y `sequence_number`; firma, cierre, Tickets y PDFs ya consumían esa identidad y no debían rediseñarse.

No existía solicitud estructurada, aprobación, creación anticipada N, bandeja administrativa ni permiso externo específico. `LabWorkOrder.client_id`, agregado en Bloque 1, era el tenant operador, pero el servicio sustituía además `client_name` por el nombre del tenant, mezclando ownership con el snapshot documental del cliente final.

Comunicaciones ya ofrecía conversaciones por tenant, secuencia bloqueada, mensajes `system`, receipts y notificaciones. Realtime dispone de rooms por usuario y publicación posterior al commit; no existe room de tenant. El frontend productivo no tenía superficie administrativa LAB.

## Solución y owners

| Hallazgo | Causa | Solución | Owner |
| --- | --- | --- | --- |
| Sin grupo N transaccional | asignador unitario | reserva de bloque bajo el mismo lock y materialización de N OTs enlazadas antes del commit | Backend |
| Retry duplicable | no existía entidad/estado | solicitud `FOR UPDATE`; `approved + root_work_order_id` devuelve el resultado existente | Backend |
| Tenant y cliente final mezclados | nombre ambiguo y overwrite | `operator_client_id`; `client_name` permanece snapshot documental | Backend/migración |
| Sin capacidad específica | roles heredaban sólo operación | `work_orders.group.request` únicamente en Operativo Sr | Backend/Mobile |
| Sin superficies | flujo inexistente | solicitud/estatus Mobile y Workbench Web de alta directa y decisiones | Mobile/Web |
| Sin contexto de atención | sin agregado | conversación por solicitud, handler participante, mensajes system y notificaciones | Backend |

## Invariantes verificadas

- `pending`/`in_review` no reservan folios; rechazo exige motivo.
- Aprobar crea todas las OTs, actualiza la solicitud y consume el bloque en una transacción.
- El rango completo se valida antes de incrementar el secuenciador.
- Folios consecutivos, misma raíz, secuencia 1..N y cliente final congelado.
- Reintentar una aprobación completada no crea otra raíz.
- El flujo evolutivo adicional, máximo 10 equipos, firma grupal, Tickets, revisión y PDF no cambió.

## Legacy y riesgos

La migración renombra la columna sin perder valores. Filas de Bloque 1 conservan tenant; si `client_name` fue sobrescrito antes del corte, el cliente final no puede reconstruirse automáticamente y se conserva literalmente. Realtime sigue in-memory y por usuario. Falta aceptación física iPhone/Android/navegador con perfiles reales.

## Correcciones posteriores al QA físico

1. La alta individual seguía expuesta porque Jr/Sr conservaban `work_orders.create` y Mobile derivaba el botón sólo de esa capacidad. Se retiró del RBAC externo, la UI exige actor `internal` y el router devuelve 403 a cualquier actor `client`; la OT adicional también queda reservada a staff.
2. La experiencia administrativa sólo presentaba solicitudes de grupo. La pantalla ahora es una bandeja con secciones independientes para `OperationalTicket` y `WorkOrderGroupRequest`, sin fusionar modelos ni duplicar decisiones.
3. Aunque el vínculo `conversation_id` se persistía, faltaban identidad visible y navegación. Claim crea o reutiliza la conversación bajo el lock de la solicitud, agrega sólo solicitante/handler y los mensajes system derivan nombre, cantidad, folios o motivo desde el evento backend.
4. El navegador de notificaciones no conocía las entidades nuevas y Mobile esperaba terminar el marcado como leído antes de navegar. Los resolvers Web/Mobile usan `entity_type`, `entity_id` y metadata estructurada; el intento de lectura ya no impide abrir el destino.
