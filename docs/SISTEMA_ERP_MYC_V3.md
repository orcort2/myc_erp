# Sistema ERP MYC V3 - Arquitectura congelada

## Estado real actual

```text
ERP MYC
|
|-- Autenticacion
|   `-- Estructura creada
|
|-- Clientes
|   `-- Funcional
|
|-- Auditoria
|   `-- Funcional
|
|-- Cotizaciones
|   `-- API V1 en construccion
|
|-- Ordenes de servicio
|   `-- Modelo creado
|
|-- Equipos
|   `-- Modelo creado
|
`-- Base de datos
    `-- Funcional con PostgreSQL + Alembic
```

## Entidad raiz

La entidad raiz operativa es `service_orders`.

```text
Cotizacion
  -> Agenda
  -> Llamado
  -> Orden de Servicio
  -> Equipos
  -> Hojas de Campo
  -> Certificados
  -> Pago / Factura
  -> Encuesta / Reporte
```

## Regla de persistencia

Nada critico se borra fisicamente.

Todas las entidades operativas deben usar:

```text
is_active
_deleted_at
deleted_by
```

Nota: el campo real se llama `deleted_at`; `_deleted_at` solo representa la idea de borrado logico.

## Estados de cotizacion

Estados permitidos V1:

```text
draft
sent
waiting
accepted
rejected
expired
cancelled
```

Reglas:

- Una cotizacion nace en `draft`.
- Al enviarse pasa a `sent`.
- Puede pasar a `waiting` cuando ya esta en seguimiento.
- Solo `sent` o `waiting` pueden aceptarse.
- Una cotizacion aceptada no debe editarse directamente en fases posteriores; debe versionarse.
- `cancelled`, `rejected` y `expired` son estados terminales comerciales.

## Estados de servicio

Estados iniciales:

```text
open
scheduled
in_progress
paused
technical_closed
capture
quality_review
documentation_ready
payment_pending
payment_validated
released
closed
cancelled
```

## Estados de equipo

Estados iniciales:

```text
pending
realizando
not_done
calibrated
label_pending
label_review
labeled
capture
certificate_review
certificate_authorized
released
```

## Roles base

```text
superadmin
direccion
administracion
comercial
tecnico
captura
calidad
finanzas
consulta
```

## Permisos MVP

Clientes:

```text
clients.read
clients.create
clients.update
clients.deactivate
```

Cotizaciones:

```text
quotations.read
quotations.create
quotations.update
quotations.send
quotations.accept
quotations.reject
quotations.cancel
quotations.expire
```

Ordenes de servicio:

```text
service_orders.read
service_orders.create
service_orders.update
service_orders.close_technical
```

Equipos:

```text
equipment.read
equipment.create
equipment.update_status
```

Auditoria:

```text
audit_logs.read
```

## Folios

```text
Cotizacion: MYC-MM-AA-XXXX
Agenda: AMYC-AA-MM-XXXX
Llamado: SMYC-AA-MM-XXXX
Orden de servicio: OSMYC-AA-MM-XXXX
Certificado: MYC{A|T}-MM-AAAA-XXXX
```

Reglas:

- Los folios son unicos.
- No se reutilizan.
- Se conservan aunque el documento se cancele.

## Auditorias obligatorias

Cotizaciones:

```text
quotation.created
quotation.updated
quotation.sent
quotation.waiting
quotation.accepted
quotation.rejected
quotation.expired
quotation.cancelled
quotation.item_added
quotation.item_updated
quotation.item_deactivated
```

Clientes:

```text
client.created
client.updated
client.deactivated
```

## Prioridad tecnica

1. Completar Quotation API V1.
2. Probar Cliente -> Cotizacion -> audit_log.
3. Construir Service Orders.
4. Crear conversion de cotizacion aceptada a orden de servicio.
5. Agregar equipos a orden de servicio.
