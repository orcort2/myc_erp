# Base de datos MVP 1

## Entidad raiz operativa

La entidad raiz del sistema operativo es `service_orders`.

```text
clients
  -> quotations
    -> service_orders
      -> service_order_items
      -> equipment
  -> payments / invoices / certificates en fases posteriores
```

## Tablas iniciales

- `users`
- `roles`
- `clients`
- `client_contacts`
- `quotations`
- `quotation_items`
- `service_orders`
- `service_order_items`
- `equipment`
- `audit_logs`

## Borrado logico

Las tablas operativas usan:

- `is_active`
- `deleted_at`
- `deleted_by`

Ningun registro critico debe borrarse fisicamente. La auditoria conserva cambios de estado, ediciones y desactivaciones.

