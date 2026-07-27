> Estado: CIERRE TÉCNICO EN REVISIÓN
>
> Fecha: 2026-07-27
>
> Alcance: Fase 6 — Motor de Compensación síncrono

# Cierre técnico de la Fase 6 del Motor de Resoluciones

## Resultado

La Fase 6 incorpora planificación y ejecución compensatoria total o parcial
sobre efectos confirmados y declarados como reversibles. Conserva intacta la
ejecución original, exige una decisión de seguridad exacta, aplica Lifecycle,
lock, checkpoints, idempotencia, auditoría y outbox. Queda `EN REVISIÓN`.

## Componentes incorporados

- modelo puro de fuente, acción, plan, paso, reserva, resumen y resultado;
- `CompensationEngine`, `CompensationPlanner`, `CompensationExecutor` y
  `CompensationRunner`;
- contratos `CompensationHandler` y `CompensationStore`;
- adaptador `SqlAlchemyCompensationStore`;
- cuatro tablas generales de plan, pasos, ejecución y checkpoints;
- estados, evidencia, invariantes y transiciones de Lifecycle;
- reconstrucción completa mediante `ResolutionRepository`;
- pruebas unitarias, persistentes, arquitectónicas y de migración.

## Invariantes protegidas

1. Sólo se compensan pasos `completed` con contrato explícito.
2. Un punto de no retorno impide la compensación ordinaria.
3. La compensación total incluye todos los efectos confirmados; la parcial
   exige selección explícita.
4. Cada paso original puede pertenecer a un único plan compensatorio.
5. La autorización debe ser `allowed` para la ejecución, resolución,
   organización y actor exactos; se vuelve a validar antes de cualquier replay
   y sólo ese actor puede iniciar la ejecución.
6. Plan y pasos son inmutables y se vinculan por FKs al expediente original.
7. El orden y las dependencias se invierten determinísticamente.
8. Sólo `CompensationRunner` invoca handlers.
9. La pérdida de lock posterior al handler bloquea como incierta y no repite.
10. Sólo Lifecycle cambia el estado raíz.
11. El replay exige la misma clave y hash; una operación en curso no se repite.
12. La ejecución original, auditoría y resultados nunca se eliminan ni
    reinterpretan.

## Estados y transiciones

```text
completed | partially_completed | failed
  → compensating
  → compensated | partially_compensated | compensation_failed
```

Una compensación incierta termina con evidencia `blocked` y raíz
`compensation_failed`. `blocked` original no es elegible sin conciliación.

## Validaciones

- pruebas específicas de compensación: **16 correctas**;
- suite completa del Motor: **151 correctas**;
- backend completo: **275 correctas**, **19 subpruebas** y dos warnings
  preexistentes;
- frontend: **11 correctas**;
- build Vite: correcto, con advertencia preexistente del chunk principal;
- compilación Python: correcta;
- arquitectura y aislamiento del ERP: correctos;
- migración aplicó, revirtió y reaplicó;
- `heads/current`: `d6e8f0a2b4c5`;
- `alembic check`: sólo deriva histórica `TD-021`, ninguna operación
  `resolution_*` atribuible a Fase 6;
- inventario, rutas y `git diff --check`: correctos.

## Migración

`d6e8f0a2b4c5` parte de `c5d7e9f1a3b4`, amplía el constraint de estado de la
raíz y crea:

- `resolution_compensation_plans`;
- `resolution_compensation_plan_steps`;
- `resolution_compensation_executions`;
- `resolution_compensation_step_executions`.

Instala protección append-only/de borrado usando las funciones ya aprobadas del
Motor. No modifica tablas propietarias del ERP.

## Contradicciones y deuda

La apertura confirmó que el roadmap prevalece y resolvió la contradicción
documental anterior. No se encontró otro bloqueo del ERP.

Continúan fuera de alcance: conciliación de incertidumbre, recuperación,
retries, compensación automática, workers, colas, API pública, gateways e
integraciones propietarias. No se alteró `TD-021`.

## Archivos clave

- `domain/compensation.py`, `contracts/compensation.py`;
- `application/compensation.py`, `application/compensation_runner.py`;
- `infrastructure/compensation.py`;
- `infrastructure/persistence/compensation.py`;
- migración `d6e8f0a2b4c5`;
- `test_compensation.py`, `test_compensation_persistence.py` y
  `test_phase_6_migration.py`;
- contrato `18_COMPENSATION_ENGINE.md`.

El inventario oficial contiene el detalle completo de archivos modificados y
dependencias.

## Condición para continuar

La Fase 6 queda `EN REVISIÓN`. No se inicia la Fase 7 hasta recibir aprobación
expresa del commit exclusivo.
