> Estado: EN REVISIÓN
>
> Fecha: 2026-07-28

# Cierre técnico — Fase 11 Motor Distribuido

## Resultado

Se implementó un runtime SQL durable, horizontal y agnóstico de dominio:
dispatcher, workers pull, registro/heartbeat/drenado de nodos, balanceo por
capacidad, prioridad, disponibilidad diferida, leases con fencing,
exclusividad por resolución, recovery, retry determinista, eventos append-only
y observabilidad agregada.

## Persistencia

La migración reversible `c1e3f5a7b9d2`, hija del head aprobado de Fase 10
`a0d2f4b6c8e1`, crea:

- `resolution_worker_nodes`;
- `resolution_work_items`;
- `resolution_work_events`.

No modifica tablas, contratos, estados ni evidencia de Fases 1–10.

## Garantías

- claim concurrente mediante `SKIP LOCKED`;
- un único trabajo activo por resolución, reforzado por índice parcial único;
- fencing exacto por nodo, token, versión y vigencia;
- heartbeat durante el handler;
- replay de enqueue por clave/hash;
- retry sólo con ausencia de efecto confirmada;
- backoff exponencial acotado y reproducible;
- lease perdido antes de efecto se recupera;
- lease perdido después de efecto queda bloqueado como incierto;
- eventos de operación append-only;
- handlers inyectados, sin lógica de dominio en worker/store;
- API, SDK, Lifecycle, seguridad, auditoría y compensación preservados.

## Pruebas específicas

La suite `test_phase_11_distributed_runtime.py` cubre política de retry,
idempotencia/colisión, dos nodos, exclusividad por resolución, recuperación,
fencing obsoleto, incertidumbre, ciclo worker y migración reversible.

## Validación

- Fase 11, arquitectura y esquema: `40 passed`.
- Motor completo en árbol aislado: `233 passed`.
- Backend completo compartido: `320 passed`, `23 failed`, `14 errors`; los
  fallos corresponden a deuda previa de Actividad, trabajo concurrente de
  Notificaciones y el binario LibreOffice local, no a Fase 11.
- Backend completo aislado: `335 passed`, `22 failed`; conserva 19 fallos
  SQLite/JSONB de Actividad, dos de LibreOffice y uno por el XLSX SAT ignorado
  que no forma parte de `git archive`.
- PostgreSQL temporal limpio: cadena completa, downgrade
  `c1e3f5a7b9d2 → a0d2f4b6c8e1` y upgrade de retorno correctos; `current` y
  `heads` quedaron en el único head `c1e3f5a7b9d2` y el trigger append-only
  `trg_resolution_work_events_immutable` quedó instalado.
- `alembic check`: sólo deriva histórica `TD-021`, sin operaciones propuestas
  sobre las tres tablas de Fase 11.
- Árbol compartido: el head concurrente no confirmado
  `b18ac098c1db` de Notificaciones ya está aplicado localmente y coexiste con
  `c1e3f5a7b9d2`; Fase 11 no se aplicó a esa base para no mezclar entregas.
- Compilación Python y `git diff --check`: correctos.

## Estado de salida

Fase 11 queda `EN REVISIÓN`. Fase 12 permanece `NO INICIADA` y no recibió
código, contrato ni dependencia.
