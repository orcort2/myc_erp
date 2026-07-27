> Estado: CIERRE TÉCNICO EN REVISIÓN
>
> Fecha: 2026-07-28
>
> Alcance: Fase 5 — ejecución controlada sin recuperación automática

# Cierre técnico de la Fase 5 del Motor de Resoluciones

## Resultado

La Fase 5 transforma un plan autorizado y revalidado en una ejecución
controlada, durable, idempotente y auditada. Incorpora ejecución de acciones por
contrato, lock exclusivo, checkpoints, efectos, resultado y publicación
explícita de outbox. La fase queda `EN REVISIÓN`; no se inicia Fase 6.

## Componentes incorporados

- modelo inmutable de candidato, pasos, solicitudes/resultados de acción,
  certeza, efectos, reserva, resumen y resultado de ejecución;
- `ExecutionEngine` para validar orden/dependencias y consolidar resultados;
- `ResolutionExecutor` como coordinador de Lifecycle, controles, checkpoints y
  acciones;
- `ActionRunner` como único invocador de `ActionHandler`;
- puertos `ExecutionStore`, `ActionHandler`, `OutboxStore` y `EventPublisher`;
- `SqlAlchemyExecutionStore` y `SqlAlchemyExecutionControl` para persistencia,
  idempotencia y locks;
- `OutboxPublicationService` y `SqlAlchemyOutboxStore` para publicación
  solicitada explícitamente;
- cinco acciones/transiciones del Lifecycle y reconstrucción de evidencia de
  ejecución;
- pruebas puras, persistentes y arquitectónicas.

## Arquitectura implementada

El dominio valida el plan y consolida resultados; aplicación coordina; la
infraestructura persiste checkpoints cortos. No se mantiene una transacción SQL
abierta durante la llamada propietaria. Antes de cada efecto se persisten
intención e idempotencia; después se persisten respuesta, entidades, auditoría y
outbox.

El flujo implementado es:

`ready_for_execution → executing → completed | partially_completed | failed |
blocked`.

`blocked` representa una respuesta incierta. No afirma que el efecto no ocurrió
y no vuelve a invocar la acción.

## Invariantes y decisiones relevantes

1. Sólo inicia un plan activo `authorized`, con autorización y revalidación
   exactas y sin ejecución previa.
2. La clave de ejecución se valida contra un hash canónico de resolución, plan,
   versión/hash, revalidación y pasos. Un replay exacto devuelve la respuesta
   persistida; otro payload con la misma clave se rechaza.
3. Cada paso posee ID persistente, `step_execution_key` e idempotencia propia.
4. El lock es exclusivo por resolución y sólo su token vigente puede renovarlo
   o liberarlo.
5. `ActionRunner` es el único punto de invocación de handlers; no existe acceso
   directo desde servicios, routers o infraestructura.
6. Excepción o respuesta inválida del handler se trata como resultado incierto,
   se audita y bloquea sin retry.
7. Los eventos outbox se agregan con el hecho fuente. La publicación exige
   publicador idempotente por `event_key`; un fallo se conserva y no se agenda.
8. La autorización de apertura excluyó expresamente recuperación, retries,
   compensaciones y workers. La matriz se precisó para no atribuirlos a esta
   fase.

## Pruebas ejecutadas y resultados

- Suite específica del Motor: **127 correctas**.
- Suite backend completa: **251 correctas**, **19 subpruebas correctas** y dos
  warnings preexistentes de dependencias.
- Frontend: **11 correctas**.
- Build Vite: correcto; conserva la advertencia preexistente por chunk principal
  mayor a 500 kB.
- Compilación Python de `app`, `tests` y `scripts`: correcta.
- Arquitectura: aislamiento de ERP/framework, dirección de capas, autoridad del
  Lifecycle, invocación exclusiva por Action Runner y ausencia de workers,
  gateways y schedulers: correcta.
- Ejecución: plan autorizado correcto; plan no autorizado rechazado antes de
  acciones; resultados completo, parcial, fallido e incierto comprobados.
- Idempotencia: replay exacto, conflicto de hash, bloqueo de operación en curso
  y claves de paso comprobados.
- Locks: adquisición exclusiva, rechazo de lock activo, renovación por token y
  liberación final comprobados.
- Persistencia: vínculo resolución/plan/revalidación/paso, actor, efectos,
  resultado, auditoría y outbox comprobados sobre SQL con FKs activas.
- Alembic: `heads` y `current` coinciden en `b4c6d8e0f2a3`.
- `alembic check`: conserva exclusivamente la deriva histórica general ya
  registrada en `TD-021`; no detectó operaciones sobre tablas
  `resolution_*` atribuibles a Fase 5.
- Inventario regenerado, rutas verificadas y `git diff --check`: correctos.

## Contradicciones encontradas

No se detectó una contradicción del ERP que bloqueara la fase y no se modificó
ningún módulo propietario. La matriz histórica agrupaba ejecución y
recuperación en Fase 5; la autorización expresa de esta apertura excluyó
recuperación, retries, compensaciones y workers. Se corrigió únicamente esa
delimitación documental.

## Deuda técnica no abordada

- deriva histórica Alembic `TD-021`, ajena al Motor;
- adaptadores concretos de acciones/eventos e integración con servicios
  canónicos de dominios;
- conciliación y recuperación de operaciones `in_progress` o inciertas;
- retries, compensaciones, schedulers y workers;
- claims distribuidos del outbox y operación multinodo;
- API, frontend y casos de uso concretos.

Estas capacidades permanecen fuera de alcance; no se reinterpretan como defecto
de la ejecución síncrona aprobada.

## Migraciones

No existen migraciones de Fase 5. Se reutilizan las entidades, FKs, constraints,
índices y protección histórica creados en Fases 2 y 3. La base local no fue
modificada y conserva `alembic_version = b4c6d8e0f2a3`; no fue necesario
regenerar el respaldo SQL.

## Archivos modificados

### Implementación

- APIs de paquete:
  `backend/app/resolution_engine/{__init__.py,application/__init__.py,contracts/__init__.py,domain/__init__.py,infrastructure/__init__.py}`;
- dominio:
  `domain/{exceptions.py,execution.py,lifecycle.py}`;
- contratos y aplicación:
  `contracts/execution.py`,
  `application/{action_runner.py,execution.py,outbox.py}`;
- infraestructura:
  `infrastructure/{execution.py,execution_control.py,lifecycle.py,outbox.py}`;
- pruebas:
  `test_architecture.py`, `test_execution.py`,
  `test_execution_persistence.py` y `test_lifecycle.py`;
- inventario:
  `scripts/generate_project_file_registry.py`.

### Documentación

- matriz, README y contratos arquitectónicos `13`, `16` y nuevo `17`;
- canon: índice, estado, alcance, flujo, reglas y decisiones;
- estado operativo e inventario;
- este cierre técnico.

El detalle de responsabilidad y dependencias de cada ruta está sincronizado en
`docs/PROJECT_FILE_REGISTRY.md`.

## ARCHIVOS CLAVE PARA REVISIÓN ARQUITECTÓNICA

| Ruta completa | Responsabilidad arquitectónica | Relevancia para revisión |
| --- | --- | --- |
| `/Users/saulcortes/Desktop/myc_erp/backend/app/resolution_engine/application/execution.py` | Executor/Execution Service que coordina el caso completo. | Permite revisar que plan autorizado, Lifecycle, checkpoints, lock e idempotencia se compongan sin acoplamiento SQL/ERP. |
| `/Users/saulcortes/Desktop/myc_erp/backend/app/resolution_engine/domain/execution.py` | Execution Engine y modelo puro de runtime. | Contiene orden, identidad, certeza, efectos y consolidación determinista. |
| `/Users/saulcortes/Desktop/myc_erp/backend/app/resolution_engine/application/action_runner.py` | Action Runner único. | Demuestra selección explícita e invocación exclusiva del adaptador de acción. |
| `/Users/saulcortes/Desktop/myc_erp/backend/app/resolution_engine/contracts/execution.py` | Contratos de Execution Store, Action Handler, Outbox y publisher. | Define la frontera reemplazable para integraciones futuras sin ERP en el núcleo. |
| `/Users/saulcortes/Desktop/myc_erp/backend/app/resolution_engine/infrastructure/execution.py` | Adaptador/Runtime SQL de ejecución. | Centraliza checkpoints transaccionales, persistencia de efectos, resultado, auditoría y coordinación con Lifecycle/outbox. |
| `/Users/saulcortes/Desktop/myc_erp/backend/app/resolution_engine/infrastructure/execution_control.py` | Locks e idempotencia SQL. | Permite auditar exclusión mutua, tokens, hashes, replay y conflictos. |
| `/Users/saulcortes/Desktop/myc_erp/backend/app/resolution_engine/application/outbox.py` | Servicio explícito de publicación outbox. | Verifica el límite sin scheduler, worker ni retry. |
| `/Users/saulcortes/Desktop/myc_erp/backend/app/resolution_engine/infrastructure/outbox.py` | Persistencia y adaptador del outbox. | Permite revisar atomicidad del alta, identidad de eventos y estados de publicación. |
| `/Users/saulcortes/Desktop/myc_erp/backend/app/resolution_engine/domain/lifecycle.py` | Transiciones e invariantes de ejecución. | Confirma que ningún estado cambia fuera del Lifecycle y que la evidencia terminal concuerda. |
| `/Users/saulcortes/Desktop/myc_erp/backend/tests/resolution_engine/test_execution_persistence.py` | Prueba integral del runtime persistente. | Reproduce autorización, acciones, idempotencia, locks, efectos, auditoría y outbox sobre SQL. |

## Condición para continuar

La Fase 5 queda `EN REVISIÓN`. La Fase 6 sólo puede iniciar después de la
aprobación expresa del commit exclusivo de esta fase.
