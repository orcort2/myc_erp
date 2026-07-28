> Estado: CIERRE TÉCNICO EN REVISIÓN
>
> Fecha: 2026-07-27
>
> Fase: 8 — Seguridad integral

# Cierre técnico de la Fase 8

## Resultado

La Fase 8 endurece transversalmente las capacidades construidas en las Fases 1
a 7 sin incorporar una capacidad vertical, integración ERP ni transporte
público. El evaluador aprobado en Fase 3 conserva autoridad única; los límites
críticos reutilizan una verificación común de su evidencia persistida.

## Componentes

- catálogo canónico y versionado de controles/risgo;
- permisos condicionados por contexto y ventana completa de autenticación;
- validación exhaustiva de recursos y revalidación;
- verificador común de decisiones append-only;
- protección de creación/transiciones de Lifecycle;
- protección pre-replay y transaccional de ejecución;
- endurecimiento de preparación/inicio compensatorio;
- consulta de auditoría con contexto de actor vigente;
- publicación de outbox autorizada y aislada por organización;
- semántica `single_operation`/`reusable_read`, intención canónica y consumo
  append-only transaccional;
- creación idempotente exacta, transición ligada a estado/versión y lote
  outbox congelado;
- migraciones reversibles `e7f9a1b3c5d7` y `f8a0b2c4d6e8`;
- suite específica de Fase 8.

## Invariantes preservadas

Lifecycle sigue siendo la única autoridad de estado; el nuevo verificador no
evalúa políticas; las consultas siguen read-only; auditoría continúa
append-only; no cambian locks, checkpoints, idempotencia, compensación,
snapshots ni reconstrucción determinista. No se incorporan componentes de Fase
9 o posteriores.

## Validaciones

- Fase 8: **15 passed**.
- Fase 8 + arquitectura/esquema: **45 passed**.
- Suite completa del Motor: **201 passed**.
- Backend completo fuera del sandbox: **306 passed**, **19 subtests passed** y
  **19 failed**. Todos los fallos nacen antes del caso probado porque
  `activity_messages.metadata_json` usa `JSONB` no portable al crear la
  metadata SQLite; se registra como `TD-023` y no se corrige por ser deuda
  general ajena al Motor. Las dos pruebas LibreOffice sí pasan fuera del
  sandbox.
- Frontend: **11 passed**.
- Build Vite: correcto; permanece el aviso conocido de chunk superior a 500 kB.
- Compilación Python: correcta para `app` y `tests`.
- PostgreSQL: upgrade `fabc2cd495ef → f8a0b2c4d6e8`, downgrade y reaplicación
  correctos.
- Alembic `current` y `heads`: `f8a0b2c4d6e8 (head)`.
- `alembic check`: conserva exclusivamente la deriva histórica `TD-021`; no
  propone otra operación `resolution_*` atribuible a Fase 8.
- Respaldo regenerado: 74,213,207 bytes, SHA-256
  `763b5b262632d06d8bb6eb4433038c1f3009aa2da4e237867fae32c04901db96`,
  con `alembic_version=f8a0b2c4d6e8`.
- Inventario regenerado mediante el script oficial y rutas verificadas.
- `git diff --check`: correcto.

## Migración

`f8a0b2c4d6e8` es reversible y lineal después del head de Actividad
`fabc2cd495ef`. Las decisiones históricas reciben identidad legacy estructural
sin inventar intención verificable. Las nuevas rutas persisten modo, operación,
payload/hash y consumo exactos.

## Pendientes

- `TD-022` permanece: decisiones anteriores a Fase 7 sin base canónica completa
  sólo pueden mostrarse como `asserted`; no se migran por inferencia.
- `TD-023` bloquea la suite backend completa por el `JSONB` no portable del
  módulo Actividad; su corrección pertenece a ese módulo, no al Motor.
- La seguridad general de routers, portal y demás ERP sigue fuera de esta fase.
- La Fase 9 requiere aprobación formal expresa.

## Commit

La implementación y este cierre se agrupan en un commit exclusivo de Fase 8.
Su hash se reporta en el cierre operativo y no se incrusta aquí para evitar una
referencia circular.

## Estado

```text
FASE 8
EN REVISIÓN
FASE 9 NO INICIADA
```
