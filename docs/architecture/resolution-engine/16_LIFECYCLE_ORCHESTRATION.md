> Estado: VIGENTE
>
> Tipo: Contrato técnico implementado
>
> Autoridad: Lifecycle y orquestación interna de la Fase 4
>
> Complementa a: `05_ARQUITECTURA.md`, `08_FLUJOS.md`,
> `13_IMPLEMENTATION_MATRIX.md`, `14_PERSISTENCE_SCHEMA.md` y
> `15_SECURITY_GOVERNANCE.md`
>
> Corte verificado: 2026-07-27

# Lifecycle y orquestación interna del Motor de Resoluciones

## Propósito y límite

La Fase 4 implementa el núcleo determinista que crea una resolución, reconstruye
su estado desde el expediente, valida evidencia, aplica una transición y
coordina componentes puros seleccionados por la definición registrada. Su
frontera de salida es `ready_for_execution`.

No ejecuta operaciones externas, no llama `Executor`, no publica outbox, no
crea workers, no reintenta, no compensa, no reserva recursos y no contiene
integraciones específicas del ERP. Los estados de ejecución que ya existen en
el catálogo y esquema permanecen reservados para Fase 5.

## Componentes

| Componente | Responsabilidad única |
| --- | --- |
| `ResolutionStateMachine` | Resuelve una acción y estado actuales a un único estado destino y valida las invariantes de evidencia. |
| `ResolutionLifecycle` | Proyección inmutable y mínima de una resolución reconstruida. |
| `LifecycleEvidence` | Reúne las referencias exactas vigentes de contexto, análisis, estrategia, plan, simulación, autorización y revalidación. |
| `ResolutionLifecycleService` | Crea resoluciones y obliga a que todo cambio de estado pase por la máquina. |
| `ResolutionOrchestrator` | Selecciona la versión exacta de `ResolutionDefinition` y coordina componentes puros hasta revalidación. |
| `LifecycleStore` | Puerto de creación, reconstrucción y aplicación de una transición validada. |
| `SqlAlchemyLifecycleStore` | Adapta el expediente SQL, aplica control optimista y agrega el evento de auditoría sin administrar commit/rollback. |

La persistencia de un artefacto de contexto, análisis, estrategia, plan,
simulación, autorización o revalidación precede a su transición correspondiente
en la misma unidad de trabajo del consumidor. El Lifecycle no interpreta
payloads propietarios: sólo verifica IDs, versiones, hashes, estado y relaciones
reconstruidas desde las tablas del Motor.

## Creación

`CreateResolutionCommand` recibe sujeto genérico, problema original, actor,
origen, prioridad y metadatos. `ResolutionLifecycleService`:

1. valida identidad activa, autenticación vigente, campos obligatorios y fecha
   consciente de zona;
2. resuelve la versión solicitada o activa en `ResolutionRegistry`;
3. genera un ID técnico opaco;
4. persiste raíz y problema con la versión exacta de definición;
5. agrega `resolution.lifecycle.created` con actor, correlación, fingerprint de
   definición y hash canónico;
6. devuelve el estado reconstruido `draft`, versión `1`.

No crea folios institucionales ni consulta tablas de dominios propietarios.

## Máquina de estados de Fase 4

| Estado origen | Acción | Estado destino | Precondición principal |
| --- | --- | --- | --- |
| `draft` | `record_context` | `context_ready` | Snapshot actual persistido. |
| `context_ready` | `record_analysis` | `analyzed` | Análisis del snapshot actual. |
| `analyzed` | `record_plan` | `plan_ready` | Análisis resoluble, estrategia activa y plan `ready` exactos. |
| `plan_ready` | `record_simulation` | `simulated` | Simulación válida del plan/contexto exactos. |
| `simulated` | `request_authorization` | `pending_authorization` | Autorización humana requerida, solicitud pendiente y alcance exacto. |
| `simulated` | `confirm_authorization` | `authorized` | Política backend `allowed` exacta cuando no se exige aprobación humana. |
| `pending_authorization` | `confirm_authorization` | `authorized` | Solicitud `approved` del plan y simulación exactos. |
| `authorized` | `begin_revalidation` | `revalidating` | Autorización exacta todavía comprobable. |
| `revalidating` | `accept_revalidation` | `ready_for_execution` | Revalidación válida del plan, contexto autorizado y contexto actual. |
| `revalidating` | `require_new_plan` | `plan_ready` | Resultado explícito `requires_new_plan`. |
| `analyzed` / `revalidating` | `mark_no_action` | `no_action_required` | Evidencia explícita de caso ya resuelto/no resoluble. |

`block`, `reject`, `cancel` y `supersede` sólo se admiten desde los estados
declarados por la tabla interna y requieren razón. `supersede` exige además el
ID de la nueva resolución. No existe transición implícita, wildcard ni
condicional por tipo de resolución.

`completed`, `rejected`, `cancelled`, `superseded` y `no_action_required` no
tienen transiciones salientes en esta fase. `blocked` sólo puede cancelarse o
ser sustituido; una reapertura futura requerirá una política explícita, no una
mutación manual.

## Invariantes

- cada análisis señala el contexto actual;
- la estrategia activa señala el análisis vigente;
- el plan activo y `ready` señala contexto y estrategia vigentes;
- la simulación válida señala el plan y contexto exactos;
- la autorización humana señala solicitud, plan/versión/hash y
  simulación/hash exactos;
- cuando no se requiere aprobación humana, una decisión de seguridad
  `resolution.plan.authorize` con resultado `allowed` sustituye sólo ese paso y
  conserva el mismo alcance exacto;
- la revalidación señala plan, contexto autorizado y contexto actual;
- ninguna transición se calcula con evidencia perteneciente a otra resolución;
- la versión raíz aumenta exactamente en uno;
- una escritura con versión o estado obsoletos falla con
  `LifecycleConcurrencyError`;
- cada transición agrega un `ResolutionAuditEvent` con estado anterior/nuevo,
  actor, correlación, acción, versión previa y hash;
- ninguna API de Fase 4 permite entrar a `executing`.

## Orquestación por definición

`ResolutionOrchestrator` resuelve siempre
`resolution_type + definition_version` en `ResolutionRegistry`. Después solicita
al `ComponentResolver` la referencia exacta y valida clase, clave, versión y
método antes de invocarla.

Las operaciones disponibles son construcción de contexto, análisis, selección
de estrategia y plan, simulación declarativa, cálculo de requisitos de
autorización y revalidación. No existe método `execute`. Agregar un tipo de
resolución requiere registrar otra definición y sus componentes; no modifica
la máquina ni agrega condicionales al núcleo.

## Seguridad y transacciones

La autorización protegida se obtiene mediante los servicios de Fase 3 y se
persiste antes de avanzar el Lifecycle. La máquina no reevalúa roles ni permisos:
valida la evidencia exacta resultante. El futuro adaptador de API compondrá la
evaluación de seguridad y el servicio de Lifecycle dentro del backend; el
frontend nunca será autoridad.

`SqlAlchemyLifecycleStore` no ejecuta `commit` ni `rollback`. El consumidor
conserva una sola unidad de trabajo para artefacto, transición y auditoría. Esta
decisión permite integrar políticas y componentes futuros sin acoplar el núcleo
a FastAPI, ORM propietario o transacciones de módulos del ERP.

## Evolución

La Fase 5 consume únicamente resoluciones `ready_for_execution` e incorpora
ejecución controlada, idempotencia, locks y publicación explícita de outbox,
sin debilitar ni evitar estas invariantes. Recuperación, retries, conciliación,
compensación y workers permanecen fuera de esa fase.
