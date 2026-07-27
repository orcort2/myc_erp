> Estado: VIGENTE
>
> Tipo: Contrato técnico implementado
>
> Autoridad: Ejecución controlada de la Fase 5
>
> Complementa a: `05_ARQUITECTURA.md`, `08_FLUJOS.md`,
> `13_IMPLEMENTATION_MATRIX.md`, `14_PERSISTENCE_SCHEMA.md`,
> `15_SECURITY_GOVERNANCE.md` y `16_LIFECYCLE_ORCHESTRATION.md`
>
> Corte verificado: 2026-07-28

# Runtime de ejecución del Motor de Resoluciones

## Propósito y frontera

La Fase 5 transforma exclusivamente una resolución `ready_for_execution`, con
plan autorizado y revalidación válida exactos, en una ejecución síncrona,
controlada y durable. Cada acción se invoca una vez mediante `ActionRunner`,
después de persistir su intención, y cada resultado confirmado queda ligado al
paso, plan, ejecución y expediente.

No incorpora compensaciones, reintentos, recuperación automática, schedulers,
workers distribuidos, procesamiento masivo, gateways concretos, módulos del ERP,
API ni adaptadores hacia sistemas externos. Una respuesta incierta bloquea la
ejecución y conserva la evidencia para intervención futura; nunca se interpreta
como ausencia de efecto ni se repite automáticamente.

## Componentes

| Componente | Responsabilidad única |
| --- | --- |
| `ExecutionEngine` | Valida identidad, orden y dependencias del plan; consolida resultados confirmados o inciertos sin infraestructura. |
| `ResolutionExecutor` | Coordina Lifecycle, lock, idempotencia, checkpoints, `ActionRunner` y cierre; no ejecuta reglas propietarias. |
| `ActionRunner` | Único punto que selecciona e invoca un `ActionHandler` registrado por `operation_key`. |
| `ActionHandler` | Puerto para una operación propietaria futura; recibe identidad idempotente y devuelve resultado verificable. |
| `ExecutionStore` | Puerto de checkpoints durables y transaccionales. |
| `SqlAlchemyExecutionStore` | Reconstruye el candidato y persiste inicio, pasos, efectos, resultado, auditoría, Lifecycle y outbox. |
| `SqlAlchemyExecutionControl` | Administra locks e idempotencia dentro de una transacción recibida. |
| `OutboxPublicationService` | Publica únicamente un lote solicitado explícitamente y registra éxito o fallo. |
| `SqlAlchemyOutboxStore` | Lee eventos pendientes y persiste su estado de publicación. |
| `EventPublisher` | Puerto idempotente por `event_key`; su adaptador concreto queda fuera de esta fase. |

## Flujo de ejecución

1. Se valida `ActorContext`, comando, TTL y claves obligatorias.
2. Se reconstruyen Lifecycle, plan activo, versión/hash, última revalidación y
   pasos/dependencias desde el expediente.
3. Se calcula el hash canónico de la solicitud. Una clave ya completada con el
   mismo hash devuelve el resultado persistido antes de calcular otra
   transición; la misma clave con otro hash se rechaza.
4. La máquina valida `ready_for_execution → executing`, incluido plan
   `authorized`, autorización exacta, revalidación `valid` y ausencia de una
   ejecución previa.
5. En una transacción se adquiere el lock exclusivo de la resolución, se crean
   ejecución y pasos pendientes, se reserva idempotencia, se avanza Lifecycle,
   se audita y se agrega el evento outbox.
6. Antes de cada acción se renueva el mismo lock y se persiste el paso
   `running` con su registro idempotente.
7. `ActionRunner` invoca una vez el handler exacto. El adaptador propietario
   debe honrar la clave idempotente recibida.
8. Se persisten respuesta, referencia transaccional, efectos sobre entidades,
   auditoría y evento outbox antes de continuar.
9. El primer fallo confirmado o resultado incierto detiene el recorrido. El
   Engine consolida y el Lifecycle aplica uno de los cierres explícitos.
10. En una transacción final se persisten estado, `ResolutionResult` cuando
    existe resultado terminal confirmado, idempotencia, liberación del lock,
    auditoría y outbox.

Los pasos sólo se ordenan cuando sus dependencias existen y apuntan hacia pasos
anteriores. Las precondiciones declarativas forman parte del snapshot autorizado
y revalidado; esta fase no inventa un segundo lenguaje para reevaluarlas.

## Estados y transiciones

| Origen | Acción | Destino | Evidencia exigida |
| --- | --- | --- | --- |
| `ready_for_execution` | `start_execution` | `executing` | Plan activo `authorized`, autorización y revalidación exactas, sin ejecución previa. |
| `executing` | `complete_execution` | `completed` | Todos los pasos confirmados como completados. |
| `executing` | `complete_partial_execution` | `partially_completed` | Al menos un efecto completado y un fallo confirmado. |
| `executing` | `fail_execution` | `failed` | Fallo confirmado sin pasos completados. |
| `executing` | `block_execution` | `blocked` | Resultado incierto que impide afirmar si hubo efecto. |

No existe transición directa ni asignación manual de la raíz desde los servicios
de ejecución. `SqlAlchemyLifecycleStore` aplica cada transición con control
optimista y agrega su evento de auditoría.

## Idempotencia y locks

- La idempotencia de resolución usa alcance `resolution_execution`, clave del
  solicitante y hash de resolución, plan/versión/hash, revalidación y pasos.
- Cada acción obtiene otra clave estable derivada de la ejecución y
  `step_key`; su request hash incluye ejecución, plan exacto y snapshot del
  paso.
- Una operación `in_progress` nunca se repite. Sin recuperación automática, el
  expediente queda conservado para una capacidad posterior explícita.
- El lock `execution` es exclusivo por resolución. Sólo su token vigente puede
  renovarlo o liberarlo; un lock expirado puede marcarse liberado al iniciar una
  nueva reserva válida.
- Lock e idempotencia se persisten antes de cualquier efecto propietario.

## Evidencia y auditoría

La ejecución conserva actor iniciador, correlación, plan, versión/hash,
revalidación, contexto inicial, clave de ejecución, token, tiempos, pasos,
payloads, certeza, errores, referencia transaccional y entidades
creadas/modificadas/preservadas. Los eventos de paso reutilizan identidad, tipo
y fuente del actor iniciador. El resultado final posee hash canónico y sólo se
crea cuando el estado permite afirmar un resultado.

Los eventos `execution_started`, `step_started`, `step_completed|failed|blocked`
y `execution_completed|partially_completed|failed|blocked` permiten reconstruir
la secuencia. Los eventos outbox se agregan en la misma transacción de su hecho
fuente y poseen `event_key` y `payload_hash` estables.

## Publicación de outbox

La publicación es una llamada síncrona y explícita; no existe proceso
automático. El publicador externo debe ser idempotente por `event_key`. Un éxito
marca `published`; una excepción marca `failed`, conserva el error y no agenda
otro intento. Claims distribuidos, backoff, recuperación y workers pertenecen a
una fase posterior expresamente autorizada.

## Transacciones y propiedad

El Executor no recibe una sesión ni conoce SQLAlchemy. El adaptador SQL usa
transacciones cortas alrededor de cada checkpoint, porque una transacción no
debe permanecer abierta mientras se invoca una operación propietaria. Las
reglas del plan, estados y consolidación permanecen en dominio/aplicación; la
infraestructura sólo traduce y persiste.

No existe import de FastAPI, routers, servicios, schemas o modelos propietarios
del ERP. Las futuras integraciones deberán implementar `ActionHandler` y
`EventPublisher` mediante servicios canónicos, sin entregar ORM propietario al
Motor.

## Evolución

Recuperación, conciliación de resultados inciertos, reintentos, compensaciones,
workers, gateways concretos, API y ejecución distribuida continúan fuera de
alcance. Incorporarlos exigirá fase aprobada, políticas explícitas y pruebas que
preserven las claves y evidencia histórica de este contrato.
