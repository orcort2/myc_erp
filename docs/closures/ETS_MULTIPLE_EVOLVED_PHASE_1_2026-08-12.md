# Fase 1 — Núcleo ETS múltiple/evolucionado

> Estado final: `FASE 1 ETS MÚLTIPLE/EVOLUCIONADO — EN REVISIÓN`
>
> Fecha: 2026-08-12
>
> No constituye aprobación funcional ni arquitectónica y no abre una fase posterior.

## Resumen técnico

Se agregó un núcleo normalizado para unidades persistentes, etapas append-only, solicitudes técnicas, tareas contextuales y decisiones comerciales por partida. `ServiceOrder`, `ServiceWorkOrder`, `Equipment`, `Quotation` y Activity se reutilizan; no se creó un ETS por categoría ni una OT por evolución.

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

`f4a1c9d2e710` sucede a `e7b62b8a9421`, crea siete tablas nucleares, amplía `quotation_items`, índices, constraints y FKs. Backfill: cada equipo histórico con OT obtiene una unidad y etapa de calibración sin mutar el dominio legacy. Equipos históricos sin OT no se inventan.

## Endpoints afectados

- Nuevos: board, unidades, alta/lifecycle de etapas, solicitudes técnicas y decisión por partida.
- Activity acepta dos nuevos tipos de entidad.
- No se agregaron permisos: se reutilizan `service_orders.read/update`, `quotations.update` y Activity.

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

El catálogo completo, incluidos candidatos operativos, comerciales, documentales, de custodia, autorización, integración, corrección de datos y antipatrones, está en [`../audits/ETS_PHASE_1_EXCEPTION_CANDIDATES_2026-08-12.md`](../audits/ETS_PHASE_1_EXCEPTION_CANDIDATES_2026-08-12.md). Antipatrones explícitos: identificación parcial como excepción, overwrite/reset de decisiones, borrado de etapas, cotizaciones/OT usadas, documentos autenticados y procesos terminados.

## Validaciones

| Validación | Resultado |
| --- | --- |
| Suite Fase 1 | 4 passed; escenarios A–H y nacimiento múltiple. |
| Backend completo | 475 passed, 19 subtests, 3 warnings conocidos. |
| Frontend unitario | 42 passed. |
| Frontend build | correcto; warning conocido de chunk >500 kB. |
| Compileall | correcto. |
| API deny-by-default | 363/363 rutas clasificadas e inventario idéntico al runtime. |
| Alembic PostgreSQL | base aislada `base → f4a1c9d2e710 → e7b62b8a9421 → f4a1c9d2e710`; current en head y check sin drift. |
| Respaldo | regenerado, 74,306,112 bytes, `alembic_version=f4a1c9d2e710`. |
| Catálogo de capacidades | consistente; 72 permisos HTTP, 19 diferencias gobernadas y 0 gaps bootstrap. |

`alembic check` conserva un warning de ordenación por ciclos referenciales del
grafo ETS/comercial, documentado como deuda de mantenimiento; no detecta
operaciones nuevas. La fase permanece en revisión aunque las validaciones
técnicas sean verdes.
