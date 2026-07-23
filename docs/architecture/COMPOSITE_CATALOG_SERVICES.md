> Estado: VIGENTE
>
> Tipo: Arquitectura funcional y técnica
>
> Corte verificado: 2026-07-22

# Servicios compuestos del Catálogo MYC

## Objetivo

Un servicio compuesto es un único concepto comercial que se descompone en servicios simples operativos al crear el ETS. Cotización, PDF comercial y Facturación conservan exclusivamente el concepto padre; Equipos, OT, Hojas de Campo y Certificados consumen las partidas operativas expandidas del ETS.

## Modelo normalizado

`catalog_items.service_kind` admite `simple` y `composite`; la migración asigna `simple` a todo registro existente. Los productos siempre son `simple`.

`catalog_item_components` representa la composición:

| Campo | Contrato |
| --- | --- |
| `parent_catalog_item_id` | Servicio compuesto propietario. |
| `component_catalog_item_id` | Servicio existente del catálogo. |
| `quantity` | Multiplicador entero mayor o igual que 1. |

La relación impide padre=hijo, duplicado padre/componente y cantidad menor que uno. El servicio valida además que cada componente esté activo, sea de tipo `service`, que el compuesto tenga al menos un componente y que el grafo no sea circular.

`service_order_items.catalog_item_id` conserva el servicio simple operativo que originó la partida. `quotation_item_id` sigue apuntando al concepto comercial padre, permitiendo navegar ambos contextos sin duplicar conceptos en la cotización.

## Expansión

La única expansión ocurre en `backend/app/services/service_orders.py` cuando el ETS se crea desde una cotización y ésta no envía partidas operativas explícitas:

```text
QuotationItem: 2 × Equipo Especial
  → Componente Manómetro ×2    = ServiceOrderItem ×4
  → Componente Termómetro ×3   = ServiceOrderItem ×6
  → Componente Báscula ×1      = ServiceOrderItem ×2
```

La expansión es recursiva para permitir composición reutilizable, agrega hojas repetidas dentro de una misma partida comercial y multiplica cantidades en cada nivel. Un ciclo detectado en configuración o en datos bloquea la operación. Un componente inactivo o un compuesto sin componentes activos también bloquea la creación del ETS para evitar un expediente incompleto.

Los servicios simples siguen copiando el nombre, alcance y cantidad congelados en la partida de cotización; por tanto, el comportamiento histórico no cambia. Las cotizaciones sin `catalog_item_id` también conservan el flujo anterior.

## Integración downstream

No existe una segunda lógica de OT, Equipos, Hojas o Certificados:

1. El creador del ETS genera `service_order_items` expandidos.
2. El contador existente suma sus cantidades y determina OTs de máximo 10 equipos.
3. Equipos selecciona las mismas partidas operativas.
4. Hojas de Campo y Certificados continúan naciendo desde cada equipo.
5. Facturación sigue usando las partidas comerciales de la cotización y nunca los componentes.

## API y frontend

`CatalogItemCreate/Update/Out` exponen `service_kind` y `components`. Cada componente de salida incluye identidad, nombre, clave y tipo del servicio referenciado. El editor embebido del Catálogo muestra “Servicio Simple/Compuesto”, permite agregar servicio y cantidad, evita duplicados en la vista y delega autorreferencia/ciclos al backend autoritativo.

La importación histórica omite estos campos y continúa creando servicios simples. No se codifican composiciones en JSON ni se agregan componentes a `quotation_items`.

## Migración y compatibilidad

Migración: `ff7a8b9c0d1e_add_composite_catalog_services.py`.

- agrega `service_kind` con `server_default='simple'`;
- crea `catalog_item_components` con claves foráneas y restricciones;
- agrega el vínculo operativo `service_order_items.catalog_item_id`;
- no reescribe cotizaciones ni ETS históricos;
- downgrade retira únicamente la capacidad nueva.

## Invariantes para cambios futuros

- El padre compuesto nunca debe aparecer como partida técnica del ETS.
- Los componentes nunca deben aparecer en Cotización, PDF comercial o Invoice.
- La expansión pertenece al servicio canónico de creación del ETS; no debe copiarse a frontend, router, Equipos o Facturación.
- Una composición inválida debe bloquear la creación del ETS, no degradarse silenciosamente al concepto padre.
- No sustituir la tabla normalizada por JSON.
