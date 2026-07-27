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
- migración reversible `e7f9a1b3c5d7`;
- suite específica de Fase 8.

## Invariantes preservadas

Lifecycle sigue siendo la única autoridad de estado; el nuevo verificador no
evalúa políticas; las consultas siguen read-only; auditoría continúa
append-only; no cambian locks, checkpoints, idempotencia, compensación,
snapshots ni reconstrucción determinista. No se incorporan componentes de Fase
9 o posteriores.

## Validaciones

- Fase 8: **11 passed**.
- Fase 8 + arquitectura/esquema: **40 passed**.
- Suite completa del Motor: **195 passed**.
- Backend completo: **319 passed**, **19 subtests passed**, dos advertencias
  conocidas de dependencias. Las dos pruebas LibreOffice que abortan dentro del
  sandbox pasaron al repetir la misma suite fuera de ese aislamiento.
- Frontend: **11 passed**.
- Build Vite: correcto; permanece el aviso conocido de chunk superior a 500 kB.
- Compilación Python: correcta para `app` y `tests`.
- PostgreSQL: upgrade `d6e8f0a2b4c5 → e7f9a1b3c5d7`, downgrade y reaplicación
  correctos.
- Alembic `current` y `heads`: `e7f9a1b3c5d7 (head)`.
- `alembic check`: conserva exclusivamente la deriva histórica `TD-021`; no
  propone otra operación `resolution_*` atribuible a Fase 8.
- Respaldo regenerado: 74,192,563 bytes, SHA-256
  `7afc23f7996cbea6aaf70870fac0fa1c7649891220aee9917bc7503d545fe6d0`,
  con `alembic_version=e7f9a1b3c5d7`.
- Inventario regenerado mediante el script oficial y rutas verificadas.
- `git diff --check`: correcto.

## Migración

`e7f9a1b3c5d7` es reversible y no obliga a inventar decisiones para
ejecuciones históricas. Las nuevas rutas endurecidas siempre persisten el
vínculo exacto.

## Pendientes

- `TD-022` permanece: decisiones anteriores a Fase 7 sin base canónica completa
  sólo pueden mostrarse como `asserted`; no se migran por inferencia.
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
