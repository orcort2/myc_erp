> Estado: CIERRE TÉCNICO EN REVISIÓN
>
> Fecha: 2026-07-27
>
> Alcance: Fase 4 — Lifecycle y orquestación interna sin efectos

# Cierre técnico de la Fase 4 del Motor de Resoluciones

## Resultado

La Fase 4 incorpora creación, máquina de estados, invariantes, transición
auditada, control optimista y selección versionada del flujo. El recorrido
interno llega hasta `ready_for_execution` sin ejecutar acciones externas. La
fase queda `EN REVISIÓN`; no se inicia Fase 5.

## Componentes incorporados

- `ResolutionLifecycle`, evidencias tipadas, acciones, eventos y transiciones
  inmutables;
- `ResolutionStateMachine` como única autoridad de estado;
- comandos y puertos `LifecycleStore` y `ComponentResolver`;
- `ResolutionLifecycleService` para creación y transiciones;
- `ResolutionOrchestrator` para selección exacta de definición y coordinación
  de contexto, análisis, estrategia, plan, simulación declarativa, requisitos de
  autorización y revalidación;
- `SqlAlchemyLifecycleStore` con reconstrucción desde el expediente, auditoría
  append-only y control optimista de versión;
- pruebas del dominio, orquestación, persistencia y arquitectura.

## Estados y transiciones

El flujo principal validado es:

`draft → context_ready → analyzed → plan_ready → simulated →`
`pending_authorization → authorized → revalidating → ready_for_execution`.

También se validaron autorización por política sin aprobación humana,
revalidación que exige nuevo plan, cierre sin acción, bloqueo, rechazo,
cancelación y sustitución. Los estados terminales rechazan cambios y no existe
acción de ejecución en la API implementada.

## Invariantes protegidas

- contexto, análisis, estrategia, plan, simulación, autorización y revalidación
  pertenecen al mismo expediente;
- versiones y hashes exactos de plan/simulación no pueden sustituirse;
- no se autoriza una simulación inválida ni una solicitud no aprobada;
- la revalidación compara contexto del plan y contexto actual;
- razones de gobierno son obligatorias y la sustitución identifica sucesora;
- una versión obsoleta no puede escribir;
- cada transición deja evento correlacionable y hash canónico;
- ningún estado se modifica por servicios de dominio o componentes;
- no existe dependencia con executor, outbox operativo, workers, gateways,
  FastAPI ni módulos propietarios.

## Decisiones arquitectónicas

1. El grafo se expresa como tabla de pares estado/acción, sin condicionales por
   tipo de resolución.
2. El Lifecycle valida referencias persistidas; no interpreta payloads
   propietarios ni duplica lógica de los componentes.
3. Orquestación y transición se separan para que el adaptador que persiste cada
   artefacto mantenga una única unidad de trabajo.
4. La Fase 4 termina en `ready_for_execution`; modelar o disparar ejecución
   corresponde exclusivamente a Fase 5.
5. No se implementa reapertura de `blocked` sin una política versionada
   explícita.

## Pruebas y validaciones

- 109 pruebas específicas del Motor correctas.
- Suite backend completa: 233 pruebas, 19 subpruebas y dos warnings de
  dependencias preexistentes.
- Frontend: 11 pruebas correctas y build Vite correcto; persiste la advertencia
  preexistente por tamaño del chunk principal.
- Compilación Python de `app`, `tests` y `scripts`: correcta.
- Alembic: único head/current `b4c6d8e0f2a3`; no existe migración de Fase 4.
- `alembic check`: conserva la deriva histórica ajena registrada en `TD-021` y
  no propone operaciones sobre tablas `resolution_*`.
- Pruebas arquitectónicas: aislamiento de ERP/framework, dirección de capas,
  ausencia de executor/outbox y mutación de estados confinada.
- Inventario regenerado, rutas verificadas y `git diff --check` correcto.

## Contradicciones

No se detectó una contradicción del ERP que bloqueara la fase. El flujo de
excepción ETS con actor opcional y mutación inmediata no fue consumido ni
modificado: continúa fuera del Motor y reservado para su fase de integración.

## Deuda no abordada

- adaptadores concretos de fact providers y permisos del ERP;
- persistencia especializada de outputs de cada tipo de resolución;
- política versionada de reapertura desde `blocked`;
- ejecución, idempotencia, locks, retries, compensación y outbox operativo;
- API, gateways, workers, frontend y casos de uso concretos;
- deriva histórica Alembic `TD-021`.

## Migraciones

No existen migraciones en Fase 4. La base y el respaldo conservan
`alembic_version = b4c6d8e0f2a3`; las pruebas usan el esquema ya aprobado.

## Archivos

La implementación agrega dominio, contratos, servicios de aplicación, adaptador
SQL y tres archivos de pruebas del Lifecycle/orquestación; actualiza las APIs de
paquete, errores, pruebas arquitectónicas, matriz, canon, inventario, estado
operativo y este cierre. El detalle exhaustivo está en
`docs/PROJECT_FILE_REGISTRY.md`.

## Condición para continuar

La Fase 4 queda `EN REVISIÓN`. La Fase 5 sólo puede iniciar después de la
aprobación expresa del commit exclusivo de esta fase.
