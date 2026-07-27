> Estado: IMPLEMENTADO — EN REVISIÓN
>
> Tipo: Contrato técnico de Fase 6
>
> Autoridad: Motor de Compensación síncrono
>
> Complementa a: `15_SECURITY_GOVERNANCE.md`, `16_LIFECYCLE_ORCHESTRATION.md`
> y `17_EXECUTION_RUNTIME.md`
>
> Corte verificado: 2026-07-27

# Motor de Compensación

## Propósito y límite

La Fase 6 agrega nuevos hechos capaces de neutralizar efectos confirmados de
una ejecución anterior. No borra ni reescribe el plan, la ejecución, sus pasos,
efectos, auditoría o resultado. La compensación es un flujo síncrono
independiente, gobernado por Lifecycle y limitado a operaciones declaradas
explícitamente como compensables.

No existen workers, colas, retries, recuperación automática, selección
automática, gateways del ERP ni adaptadores propietarios concretos.

## Componentes

- `CompensationEngine`: valida selección total/parcial, impide atravesar un
  punto de no retorno, invierte el orden y las dependencias y consolida el
  resultado.
- `CompensationPlanner`: reconstruye efectos confirmados, exige autorización
  exacta y persiste un plan compensatorio inmutable.
- `CompensationExecutor`: aplica transiciones, lock, checkpoints, idempotencia,
  auditoría y outbox alrededor de cada acción.
- `CompensationRunner`: único componente autorizado para invocar un
  `CompensationHandler`.
- `SqlAlchemyCompensationStore`: reconstruye el origen y persiste planes,
  ejecuciones y pasos en transacciones cortas.

## Contrato declarativo

Cada `ResolutionPlanStep` conserva:

```text
is_compensable
compensation_operation_key
compensation_payload
point_of_no_return
requires_separate_authorization
```

Sólo un `ResolutionStepExecution` con estado `completed` es elegible. Un paso
fallido, bloqueado, pendiente o incierto nunca se compensa por inferencia. La
ausencia de operación compensatoria es una declaración no compensable.

La relación queda normalizada:

```text
ResolutionExecution
  → ResolutionStepExecution confirmado
  → ResolutionCompensationPlan
  → ResolutionCompensationPlanStep
  → ResolutionCompensationExecution
  → ResolutionCompensationStepExecution
```

`source_step_execution_id` es único en los planes compensatorios. Por ello el
mismo efecto confirmado no puede planificarse dos veces.

## Planificación

Un plan total debe incluir todos los pasos completados y todos deben ser
compensables. Un plan parcial selecciona explícitamente un subconjunto de pasos
compensables. Si la ejecución alcanzó un `point_of_no_return`, no se construye
una compensación ordinaria.

Para una dependencia original `B depende de A`, el orden compensatorio es
inverso: compensar `B` antes de `A`. El contenido completo del plan produce un
`plan_hash` canónico; la clave de preparación no puede reutilizarse con otro
hash.

Una selección parcial debe ser cerrada respecto de todos los efectos
confirmados que continúan activos. Seleccionar un paso obliga a incluir cada
dependiente activo directo o transitivo. Los pasos sin efecto `completed` y los
checkpoints compensatorios con resultado `compensated` se excluyen del
conjunto activo antes de validar.

La clausura se comprueba en `CompensationEngine.build_plan()` antes de invocar
la persistencia. Una infracción produce
`CompensationDependencyClosureError`, con código estable, paso seleccionado,
dependientes activos y rutas transitivas expresadas mediante IDs exactos de
checkpoint. Ningún plan semánticamente abierto llega a la base.

## Seguridad

Preparar un plan exige una `ResolutionSecurityDecision` persistida con:

- resultado `allowed`;
- acción `resolution.compensate`;
- recurso `resolution_execution` con el ID exacto de la ejecución original;
- misma resolución, organización y actor del comando.

La autorización original de ejecución no autoriza implícitamente la
compensación. La decisión se revalida incluso en replay de preparación y el
actor que inicia o consulta el replay de ejecución debe ser el actor exacto del
plan autorizado. Los adaptadores futuros deberán solicitar esta decisión
mediante las políticas de Fase 3; el Motor no conoce roles ni tablas del ERP.

## Lifecycle

Transiciones nuevas:

```text
completed | partially_completed | failed
  → start_compensation
  → compensating
  → compensated | partially_compensated | compensation_failed
```

`blocked` no inicia compensación porque primero exige conciliación de efectos,
capacidad fuera de esta fase. `compensation_failed` representa tanto fallo
confirmado como resultado incierto; la evidencia del intento distingue
`failed` de `blocked`.

Ningún adaptador modifica el estado raíz directamente. Sólo
`ResolutionStateMachine` valida y `SqlAlchemyLifecycleStore` aplica cada
transición con versión optimista y auditoría.

## Ejecución y exclusividad

Cada paso persiste intención antes del handler. El lock de tipo `compensation`
se renueva antes de la acción, se valida al regresar del handler y nuevamente
bajo lock de fila en el checkpoint. Si expira o cambia después de un posible
efecto, el resultado se conserva como `uncertain/blocked`, no se confirma y el
handler no se reinvoca.

El plan tiene una sola ejecución. `execution_key`, `request_hash` y
`step_execution_key` impiden duplicados y permiten replay sólo de resultados
terminales exactos. No existe retry automático.

## Evidencia y outbox

El expediente reconstruye planes, pasos, ejecución, checkpoints, actor,
autorización, hashes, causa, respuestas, referencias transaccionales,
auditorías y eventos outbox. Los planes y pasos compensatorios son append-only
en PostgreSQL; ejecuciones y checkpoints pueden avanzar de estado, pero no
eliminarse.

El outbox se agrega en la misma transacción del checkpoint o cierre. Su
publicación continúa siendo explícita conforme al contrato de Fase 5.

## Extensibilidad

Agregar una operación compensatoria requiere declarar sus datos en el paso y
registrar un `CompensationHandler` mediante composición. El núcleo no contiene
condicionales por módulo, imports del ERP, FastAPI, ORM propietario ni lógica
de negocio institucional.
