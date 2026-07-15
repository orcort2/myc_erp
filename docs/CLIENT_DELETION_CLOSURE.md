# Cierre técnico — clientes: eliminación, archivado e importación

Fecha: 2026-07-14. Alcance: backend de clientes, CLI de diagnóstico y frontend de la acción. No se restauró backup ni se reinició la base.

## Diagnóstico previo

La entrega anterior modificó `backend/app/services/clients.py`, `backend/app/schemas/client.py`, `backend/app/routers/clients.py`, `frontend/src/pages/ClientsPage.jsx`, `frontend/src/services/api.js` y agregó pruebas de importación/eliminación. La implementación inicial sólo contaba cotizaciones, ETS y facturas; devolvía 409 para historial y restauraba por cualquier RFC archivado, incluso uno genérico. Las cuatro pruebas cubrían dos resoluciones SAT/importación y dos casos simples de eliminación.

`AuditLog` no tiene FK a `clients`: conserva `entity="clients"` y `entity_id`, por lo que los eventos sobreviven a un hard delete sin bloquearlo.

## Matriz de relaciones

| Relación | Tipo | Bloquea hard delete | Cascada | Motivo |
| --- | --- | ---: | ---: | --- |
| `client_contacts` | Auxiliar | No | Sí | Relación ORM `delete-orphan`. |
| `client_certificate_profiles` | Auxiliar | No | Sí | Relación ORM `delete-orphan`. |
| `quotations` | Comercial/histórica | Sí | No | FK directa a cliente. |
| `service_orders` / ETS | Operativa | Sí | No | FK directa a cliente. |
| `equipment` | Operativa | Sí | No | Se alcanza por ETS. |
| `field_sheets` | Documental | Sí | No | Se alcanza por equipo y ETS. |
| `certificates` | Documental | Sí | No | Se alcanza por ETS. |
| `invoices` | Financiera | Sí | No | Cliente fiscal o comercial directo. |
| `invoice_payments` | Financiera | Sí | No | Se alcanza por factura. |
| `credit_notes` | Financiera | Sí | No | Se alcanza por factura. |
| `audit_logs` | Auditoría | No | No | Referencia textual, no FK. |

No hay preferencias de cliente ni configuración fiscal auxiliar adicional en el modelo actual. Los archivos de constancia se preservan al archivar; en hard delete se eliminan sólo si ya no tienen referencias activas.

## Semántica final

`get_client_delete_eligibility()` es la única fuente para decidir la transición. Devuelve dependencias bloqueantes y auxiliares en cascada.

- `DELETE /clients/{id}`: elimina físicamente si no hay historial (`status=deleted`, `delete_mode=hard`); con historial archiva en la misma operación (`status=archived`, `delete_mode=archive`) e incluye los conteos bloqueantes.
- `POST /clients/{id}/archive`: archivado idempotente.
- `POST /clients/{id}/restore`: restauración idempotente; bloquea RFC exclusivo si ya pertenece a otro cliente activo.
- Las tres operaciones requieren `clients.update`; los eventos son `client_hard_deleted`, `client_delete_blocked`, `client_archived` y `client_restored`.

La importación crea RFC nuevo, omite RFC activo como duplicado y restaura/actualiza el mismo ID cuando hay un único RFC archivado. Los RFC genéricos `XAXX010101000` y `XEXX010101000` nunca disparan una restauración automática: se clasifican como incidencia ambigua. También se marca ambigüedad si hay más de un archivado para el RFC.

## Diagnóstico administrativo

Comandos de sólo lectura:

```bash
scripts/myc data doctor --json
scripts/myc data duplicates --json
scripts/myc data orphaned --json
scripts/myc data client-delete-eligibility --client-id 123 --json
```

Resultado verificado contra `erp_myc`: 301 clientes activos, 72 archivados, 0 RFC activos duplicados, 0 contactos huérfanos y 0 perfiles de certificado huérfanos.

## Validación

- `alembic current` y `alembic heads`: `660da69de732 (head)`.
- `pytest -q`: 42 pruebas correctas.
- `npm run build`: correcto; sólo permanece la advertencia no bloqueante de bundle Vite >500 kB.
- No se requirió migración: no se agregó una restricción de unicidad sin primero resolver datos activos y política de RFC genéricos.
