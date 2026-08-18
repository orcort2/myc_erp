# Acceso móvil acotado para técnicos

> Estado: vigente en backend; aplicación LAB aislada de estas rutas productivas
>
> Corte verificado: 2026-08-17

## Propósito

El namespace `/api/mobile/v1/technician` es una superficie de sólo lectura para
usuarios internos con asignación técnica. Reutiliza el access JWT interno y no
modifica ni sustituye `/api/service-orders`, `/api/equipment` o
`/api/field-sheets` del ERP web.

## Autoridad y permisos

- ETS, OT y equipos exigen `service_orders.read_assigned`.
- Hojas de Campo exigen conjuntamente `service_orders.read_assigned` y
  `field_sheets.read`.
- `service_orders.read` permanece en el rol `Tecnico` por compatibilidad del ERP
  web; no concede acceso al namespace móvil.
- La autenticación sin permiso responde `403`; la ausencia o invalidez del
  access JWT responde `401`.

## Ownership

La única asignación es `ServiceOrder.technician_id == current_user.id`. Los
recursos hijos heredan el ámbito mediante joins ejecutados en backend:

```text
ServiceWorkOrder.service_order_id → ServiceOrder.technician_id
Equipment.service_order_id → ServiceOrder.technician_id
FieldSheet.equipment_id → Equipment.service_order_id → ServiceOrder.technician_id
```

No existen ni se permiten columnas `technician_id` duplicadas en OT, Equipo u
Hoja de Campo. Un recurso existente de otro técnico, inactivo o perteneciente a
un ETS sin asignación se trata como ausente y responde `404`.

## Fronteras

Los routers sólo resuelven autenticación, permisos y transporte. Las consultas
de lista viven en `services/mobile_technician.py` y los lookups individuales
con ownership en `services/mobile_technician_scope.py`. Cada detalle vuelve a
validar el ámbito; nunca confía en una lista previa ni en el cliente móvil.

El namespace técnico no agrega escritura, sesión móvil, revocación, permisos
por usuario, asignación multi-técnico por OT ni cambios al Motor. La fase LAB
actual de `myc-mobile` no consume estos endpoints para listado, detalle,
documentos o eliminación; opera sólo sobre su namespace LAB temporal.

Cuando un Administrador elimina una OT productiva desde web, las
consultas móviles no usan caché persistente: el siguiente listado deja de
incluirla y cualquier detalle conservado por un consumidor productivo responde
`404`. La operación revoca notificaciones semánticas de esa OT. La pantalla
móvil vigente consulta `LabWorkOrder`, no presenta recursos productivos y su
DELETE administrativo pertenece al router/permiso LAB independiente.

## Endpoints

| Método | Ruta | Permiso | Ownership |
| --- | --- | --- | --- |
| GET | `/api/mobile/v1/technician/service-orders` | `service_orders.read_assigned` | ETS asignados |
| GET | `/api/mobile/v1/technician/service-orders/{id}` | `service_orders.read_assigned` | ETS asignado o 404 |
| GET | `/api/mobile/v1/technician/work-orders` | `service_orders.read_assigned` | OT por ETS asignado |
| GET | `/api/mobile/v1/technician/work-orders/{id}` | `service_orders.read_assigned` | OT por ETS asignado o 404 |
| GET | `/api/mobile/v1/technician/equipment` | `service_orders.read_assigned` | Equipo por ETS asignado |
| GET | `/api/mobile/v1/technician/equipment/{id}` | `service_orders.read_assigned` | Equipo por ETS asignado o 404 |
| GET | `/api/mobile/v1/technician/field-sheets` | ambos permisos | Hoja→Equipo→ETS asignado |
| GET | `/api/mobile/v1/technician/field-sheets/{id}` | ambos permisos | Hoja→Equipo→ETS asignado o 404 |
