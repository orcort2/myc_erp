# Núcleo ETS múltiple/evolucionado — Fase 1

> Estado: VIGENTE, implementación `EN REVISIÓN`
>
> Corte: 2026-08-18
>
> Alcance: contratos persistentes y de aplicación; no implementa la lógica técnica completa de cada categoría.

## Autoridades reutilizadas

- `ServiceOrder` continúa siendo el ETS y raíz del expediente.
- `ServiceWorkOrder` continúa siendo la OT institucional. Cambiar de categoría no crea otra OT.
- `Equipment` conserva el flujo de calibración, hojas y certificados. No fue sustituido.
- `Quotation`/`QuotationItem` siguen siendo la autoridad comercial.
- Activity conserva el único sistema de conversación, menciones, eventos y notificaciones.
- El Motor de Resoluciones no se duplicó ni recibió excepciones nuevas.
- `catalog_items.service_kind` y `catalog_item_components` conservan la única expansión de Servicios Compuestos al crear el ETS.
- `operational_category` y el snapshot esquema 2 son la autoridad del origen; nombres y descripciones no deciden la ruta.

## Modelo añadido

### `ServiceUnit`

Identidad estable de una unidad/equipo durante una intervención. La card futura es sólo una proyección visual. La unidad pertenece a un ETS y a una OT, puede enlazar el `Equipment` de calibración y admite identificación parcial (`brand`, `model`, `serial_number`, notas y estado de identificación). `origin_service_order_item_id`, `initial_category` y `evolution_enabled` congelan el origen comercial/operativo de esa unidad: sólo una partida de Servicio General habilita evolución. No representa el activo histórico global del cliente.

### `ServiceStage`

Registro append-only de una etapa. La secuencia es única por unidad y una evolución agrega filas; nunca convierte ni borra la anterior. Categorías Fase 1: diagnóstico, reparación, mantenimiento, calibración, verificación, calificación, validación, capacitación, consultoría y otra.

Estados preparados: `planned`, `pending_quote`, `pending_approval`, `authorized`, `in_progress`, `paused`, `completed`, `client_rejected`, `not_executable`, `exception_closed` y `cancelled`. Una etapa ejecutable requiere una decisión aprobada de partida, salvo el diagnóstico inicial de Servicio General.

La etapa conserva origen, etapa origen, partida, decisión, responsable, fechas, evidencia resumida, resultado y vínculos documentales. `ServiceStageDocument` vincula documentos sin copiar su contenido.

### Solicitud técnica

`TechnicalServiceRequest` conserva:

`ETS → ServiceUnit → ServiceStage origen → solicitud → partida(s) → decisión(es) → etapa(s)`.

El técnico describe la necesidad y categorías; no crea partidas aprobadas. La solicitud admite una o varias partidas y decisiones mixtas.

### Decisión por partida

`QuotationItemDecision` es historial append-only. Una partida acepta una sola decisión inicial `approved` o `rejected`; una restricción única por `quotation_item_id` protege la invariancia incluso bajo concurrencia. La aprobación declara categorías que deben coincidir con el catálogo/snapshot comercial y, en partidas derivadas, con la solicitud técnica origen. El rechazo no crea etapas ejecutables.

La ruta interna exige `quotations.update` y deriva siempre `source=internal` del contexto autenticado. `source` no concede autoridad: valores de portal/app se rechazan. Los futuros portal/app deberán usar endpoints y adaptadores propios con identidad y ownership de cliente; no reutilizarán inseguramente esta ruta interna.

Una partida derivada guarda referencias internas a ETS, unidad, etapa y solicitud. El único snapshot comercial del equipo contiene marca, modelo y serie. No transporta fotografías, evidencias, diagnóstico, timeline ni estado mutable.

Las partidas de una cotización inicial pueden decidirse antes de existir unidades. Posteriormente sirven para sembrar etapas autorizadas de un ETS múltiple.

### Tarea transversal

`ServiceTask` es independiente del mensaje y conserva creador, asignados, estado, fechas y contexto opcional ETS/unidad/etapa. `#tarea` sólo materializa la tarea desde Activity. `source_message_id` único evita duplicación.

## Invariantes

1. El ETS y la OT no cambian por evolución de categoría.
2. La identidad de `ServiceUnit` permanece estable durante toda la intervención.
3. La evolución agrega `ServiceStage`; no muta la categoría ni elimina historial.
4. Sólo una `ServiceUnit` cuyo `operational_category` congelado sea `general_service` tiene `evolution_enabled=true`; puede iniciar diagnóstico y seguir originando solicitudes desde etapas posteriores. La presencia textual o en otra partida no contamina unidades de calibración, mantenimiento u otra categoría conocida.
5. Marca, modelo o serie ausentes no bloquean el alta; se registra identificación parcial.
6. Una etapa `authorized`/`in_progress` debe estar respaldada por una decisión aprobada que incluya esa categoría, salvo el diagnóstico inicial anterior.
7. Una decisión rechazada no habilita etapas.
8. Una decisión existente no se revierte por overwrite; la base impide dos decisiones iniciales y cualquier corrección requiere futura rama formal validada.
9. Activity se contextualiza directamente sobre ETS, unidad o etapa.
10. Los objetos comerciales no reciben evidencia técnica mutable.
11. Crear `TechnicalServiceRequest` sólo crea estado comercial `requested`; no cambia el estado técnico de la etapa. Pausar exige la transición formal `in_progress/authorized → paused`, y los estados terminales no regresan.
12. `enabled_stage_categories` existe para representar una partida compuesta o una necesidad con varias categorías, pero nunca es autoridad por sí sola: se intersecta estrictamente con solicitud, catálogo y snapshot operativo.

## API Fase 1

| Método y ruta | Responsabilidad |
| --- | --- |
| `GET /api/service-orders/{id}/execution-board` | Proyección interna protegida por access JWT y `service_orders.read`; vista Todos, tabs dinámicos, rutas, tareas y solicitudes. |
| `POST /api/service-orders/{id}/service-units` | Alta por lote de unidades con etapas iniciales. |
| `POST /api/service-orders/service-units/{id}/stages` | Agrega una etapa sin reemplazar las anteriores. |
| `PATCH /api/service-orders/stages/{id}` | Aplica el lifecycle explícito de una etapa y registra resultado/evidencia. |
| `POST /api/service-orders/stages/{id}/technical-requests` | Registra la necesidad técnico→comercial. |
| `POST /api/quotations/{id}/items/{item_id}/decision` | Registra decisión por partida y materializa sólo etapas aprobadas. |
| `GET/POST /api/activity/service_unit/{id}` | Activity contextual de unidad. |
| `GET/POST /api/activity/service_stage/{id}` | Activity contextual de etapa y atajo `#tarea`. |

Las rutas reutilizan permisos `service_orders.read`, `service_orders.update`, `quotations.update` y los permisos vigentes de Activity. El board y la decisión declaran además la dependencia en el router, sin depender sólo del inventario transversal. La Fase 1 no agrega claves de permiso.

## Compatibilidad de calibración

La migración base crea una unidad y una etapa de calibración para cada `Equipment` histórico con OT. La corrección `a7c2e5f8b1d4` enlaza su partida cuando existe, congela `initial_category=calibration` desde la primera etapa y deja `evolution_enabled=false`; sólo conserva `true` para unidades cuya etapa inicial ya tenía origen `general_service`. No infiere capacidad evolutiva por inspeccionar el ETS completo ni altera `Equipment`, certificados, hojas, scopes, Masters o estados anteriores.

## Frontend

`frontend/src/services/api.js` expone los contratos del board, unidades, etapas, solicitudes y decisiones. La composición visual por cards/tabs queda para una fase posterior. Cotizaciones implementa el alta rápida sobre el modal ya existente: conserva el borrador actual y selecciona el concepto nuevo en la línea que originó la acción.

## Límites de la fase

- No contiene workflows técnicos particulares de reparación, mantenimiento u otras categorías.
- No implementa portal/app de aprobación parcial; el modelo y endpoint interno quedan preparados.
- No agrega navegación profunda desde notificaciones; Activity ya expone tipo/ID y ruta base.
- No implementa edición/cierre de tareas ni NLP.
- No incorpora candidatos del catálogo de excepciones al Motor sin validación funcional.
