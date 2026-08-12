# Fase 1 — Núcleo ETS múltiple/evolucionado

> Estado final: `FASE 1 ETS MÚLTIPLE/EVOLUCIONADO — EN REVISIÓN`
>
> Fecha: 2026-08-12
>
> No constituye aprobación funcional ni arquitectónica y no abre una fase posterior.

## Resumen técnico

Se agregó un núcleo normalizado para unidades persistentes, etapas append-only, solicitudes técnicas, tareas contextuales y decisiones comerciales por partida. `ServiceOrder`, `ServiceWorkOrder`, `Equipment`, `Quotation` y Activity se reutilizan; no se creó un ETS por categoría ni una OT por evolución.

La revisión correctiva cerró los hallazgos de seguridad e integridad sin abrir Fase 2: board y decisión tienen permisos efectivos; el origen y capacidad evolutiva se congelan por unidad; solicitud comercial y lifecycle técnico quedan separados; las categorías se derivan/validan contra autoridades reales; y la base impide dos decisiones iniciales concurrentes.

## Arquitectura encontrada antes de modificar

- ETS ya era `ServiceOrder`; sus partidas operativas se generaban desde Cotización y Servicios Compuestos.
- La OT ya estaba separada como `ServiceWorkOrder`; `Equipment` pertenecía al ETS y opcionalmente a una OT/partida.
- El lifecycle de `Equipment` estaba acoplado a calibración (`registered → realizing → calibrated → labeled`) y creaba contexto de certificado/hoja.
- Cotización tenía estado global y partidas, pero no decisión persistente por partida ni referencias a una necesidad técnica.
- Activity era genérico por `entity_type/entity_id`, con mensajes, menciones, eventos, notificaciones e idempotencia, pero no conocía unidad/etapa ni tareas.
- El Motor tenía verticales de certificado y equipo adicional; no correspondía introducir automáticamente nuevas excepciones.
- El buscador de Cotizaciones ya convivía con un modal de catálogo, pero no lo abría desde una línea sin coincidencia ni reinyectaba el resultado.

## Entidades y contratos añadidos

- `ServiceUnit`, `ServiceStage`, `ServiceStageDocument`.
- `TechnicalServiceRequest`.
- `QuotationItemDecision` e información de origen/snapshot acotado en `QuotationItem`.
- `ServiceTask` y `ServiceTaskAssignee`.
- Board ETS, altas por lote, evolución/lifecycle, solicitud técnica y decisión por partida.
- Activity para `service_unit` y `service_stage`; `#tarea` idempotente.

El contrato detallado está en [`../architecture/ETS_MULTIPLE_EVOLVED_CORE.md`](../architecture/ETS_MULTIPLE_EVOLVED_CORE.md).

## Migración

`f4a1c9d2e710` sucede a `e7b62b8a9421`, crea siete tablas nucleares, amplía `quotation_items`, índices, constraints y FKs. `a7c2e5f8b1d4` agrega a `ServiceUnit` la partida origen, categoría inicial y bandera evolutiva, y añade unicidad de decisión por partida. Su backfill sólo habilita evolución cuando una partida exacta identificable es Servicio General; no infiere por el ETS completo. Equipos históricos sin OT no se inventan.

## Endpoints afectados

- Nuevos: board, unidades, alta/lifecycle de etapas, solicitudes técnicas y decisión por partida.
- Activity acepta dos nuevos tipos de entidad.
- No se agregaron permisos: board exige `service_orders.read`; decisión exige `quotations.update`; las mutaciones ETS conservan `service_orders.update` y Activity sus permisos vigentes.

## Hallazgos corregidos y causa raíz

1. **Board protegido:** la ruta no declaraba dependencia propia y confiaba sólo en el guard transversal. Ahora exige access JWT y `service_orders.read`; 401/403/200 quedan probados.
2. **Autoridad de decisión:** bastaba autenticación y `source` venía del caller. Ahora la ruta interna exige `quotations.update`, deriva actor y `source=internal`, rechaza contexto portal/app y deja ownership del cliente para futuros endpoints propios.
3. **Servicio General mixto:** se escaneaban todas las partidas del ETS. Ahora cada unidad conserva `origin_service_order_item_id`, `initial_category` y `evolution_enabled`; sólo la partida SG habilita evolución.
4. **Evolución por unidad:** la etapa actual o la presencia global de SG podían abrir flujo. Ahora toda solicitud/etapa dinámica exige `unit.evolution_enabled`; una etapa posterior de esa unidad conserva la capacidad.
5. **Lifecycle único:** `create_technical_request()` asignaba directamente `pending_quote`. Ahora sólo crea `TechnicalServiceRequest.status=requested`; pausar exige `update_service_stage()` y una transición declarada.
6. **Categorías habilitadas:** el payload era autoridad suficiente. Ahora una aprobación debe ser subconjunto de la solicitud y coincidir con la categoría del catálogo, snapshot operativo/compuesto o nombre legacy inequívoco.
7. **Concurrencia:** el patrón consultar→insertar carecía de constraint. Ahora se bloquea la partida y existe `UNIQUE(quotation_item_id)`; una colisión responde 409 sin sobrescribir historia.

## Lifecycle resultante

El estado técnico permanece en `ServiceStage` (`planned`, `authorized`, `in_progress`, `paused`, terminales, etc.). La necesidad adicional usa `TechnicalServiceRequest` (`requested`, `quoting`, `quoted`, `partially_approved`, `approved`, `rejected`, `cancelled`). Crear la segunda no cambia la primera. `completed` continúa terminal y no existe reset, delete ni transición implícita.

## Frontend

- `api.js` expone los contratos del núcleo, incluido el lifecycle de etapa.
- Cotizaciones abre el modal existente cuando la búsqueda no coincide, conserva la línea/borrador y selecciona automáticamente el concepto creado.
- Cards, tabs y navegación profunda se posponen; el board ya devuelve categorías y una sola unidad con todas sus etapas para evitar duplicación backend.

## Flujo comercial y aprobación parcial

La solicitud técnica no concede autorización. El asesor crea una o varias partidas derivadas con snapshot exclusivo marca/modelo/serie. Cada partida se decide una sola vez. Sólo `approved` crea las categorías declaradas; `rejected` no crea etapa. Varias partidas de la misma solicitud producen `approved`, `rejected` o `partially_approved` según el conjunto.

## Compatibilidad con calibración

No cambiaron estados, servicios, schemas ni endpoints de `Equipment`; tampoco scopes, Masters, certificados u hojas. La suite vigente de Integridad ETS y Activity siguió verde junto con las pruebas nuevas.

## Escenarios A–H

| Escenario | Evidencia |
| --- | --- |
| A | Lifecycle de calibración permanece registrado y regresiones ETS/Activity pasan. |
| B | Tres unidades de Servicio General, todas con diagnóstico e identidad independiente/parcial tolerada. |
| C | Rutas A reparación, B calibración, C reparación+calibración; misma OT/ETS. |
| D | Una partida aprobada puede habilitar reparación+calibración. |
| E | Reparación aprobada y calibración rechazada crea sólo reparación. |
| F | Etapa pendiente puede persistir, pero `in_progress` sin decisión aprobada responde 409. |
| G | Activity resuelve `ETS → unidad → etapa`; `#tarea` conserva mensaje y asignado. |
| H | Etapa origen→solicitud→partida→decisión→nueva etapa queda reconstruible por FKs. |

## Defectos encontrados

1. `Equipment` continúa semánticamente acoplado a calibración; por eso no se reutilizó como identidad universal.
2. No existía decisión por partida ni forma segura de representar aprobación parcial.
3. El mensaje “crear nueva OT mediante excepción administrativa” del alta legacy no expresa que ya existe un vertical del Motor para equipo adicional; debe revisarse en fase posterior sin duplicarlo.
4. Activity tenía infraestructura genérica suficiente, pero carecía de definiciones para unidad/etapa.
5. La búsqueda de catálogo no conectaba el modal existente con la línea de cotización.

## Deuda y pendientes reales

- Diseñar UI cards/tabs, deep-link de notificaciones y consumo del board.
- Definir lifecycle de edición/cierre de tareas, fechas y asignaciones múltiples fuera del atajo.
- Implementar portal/app para decisión por partida con idempotencia externa y autenticación de intención.
- Definir ramas formales de corrección/sustitución de decisiones; Fase 1 bloquea overwrite.
- Conciliar explícitamente equipos históricos sin OT antes de crear unidades.
- E2E autenticado de browser y validación funcional con usuarios.
- Someter candidatos de excepción a validación; ninguno se implementó.

## Catálogo de excepciones

El catálogo completo está en [`../audits/ETS_PHASE_1_EXCEPTION_CANDIDATES_2026-08-12.md`](../audits/ETS_PHASE_1_EXCEPTION_CANDIDATES_2026-08-12.md). EX-002 quedó como flujo normal; EX-003 como operación prohibida; EX-005 separa custodia normal futura de cierre excepcional; EX-007 se trata primero como idempotencia/reconciliación; EX-008–011 son operaciones no válidas. No se implementó ninguna excepción.

## Validaciones

| Validación | Resultado |
| --- | --- |
| Suite Fase 1 | 10 passed; escenarios A–H más seguridad, mixto SG/calibración/mantenimiento, evolución indebida/legítima posterior, lifecycle, categorías y constraint. |
| Focal ETS/calibración/Activity/cotizaciones/permisos | 53 passed, 2 warnings. |
| Backend completo | 501 passed, 19 subtests y 3 warnings; único fallo ajeno: test de head fijo detecta dos migraciones concurrentes no integradas en el working tree. |
| Frontend unitario | 42 passed. |
| Frontend build | correcto; warning conocido de chunk >500 kB. |
| Compileall | correcto. |
| API deny-by-default | 371/371 rutas clasificadas; decisión regenerada canónicamente con `quotations.update`. |
| Alembic PostgreSQL | base aislada `base → a7c2e5f8b1d4 → f4a1c9d2e710 → a7c2e5f8b1d4`; revisión ETS reversible. `head/check` global quedan pendientes de integrar la migración concurrente ajena `fdc1c503a353`. |
| Respaldo | no regenerado todavía: la base principal no se modificó y permanece en `f4a1c9d2e710`. |
| Catálogo de capacidades | consistente; 72 permisos HTTP, 19 diferencias gobernadas y 0 gaps bootstrap. |

El grafo ETS/comercial conserva la deuda de ordenación documentada. Además, el
working tree contiene una migración concurrente ajena de permisos individuales,
también hija de `f4a1c9d2e710`; debe integrarse/linealizarse antes de declarar un
head global o actualizar la base principal. La fase permanece en revisión.

## Antipatrones confirmados

No se añadieron delete de etapas, overwrite de decisión, reset de estado,
regreso desde `completed`, `force-*`, eliminación de cotización/OT utilizada ni
borrado de documentos/historia. Tampoco se construyó portal/app, workflow
técnico de categorías, Motor de Resoluciones ni Fase 2.
