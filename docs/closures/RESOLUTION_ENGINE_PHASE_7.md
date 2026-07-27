> Estado: CIERRE TÉCNICO EN REVISIÓN
>
> Fecha: 2026-07-27
>
> Fase: 7 — Auditoría y Evidencia

# Cierre técnico de la Fase 7

## Resultado

La Fase 7 implementa reconstrucción histórica, verificación interna,
correlación y consultas autorizadas sobre el expediente general. No modifica
Lifecycle, ejecución, compensación ni autorización, y no incorpora API,
frontend, gateways, workers o integraciones ERP.

## Componentes incorporados

- modelo puro `EvidenceNode`, `EvidenceLink`, `EvidenceRegistry`,
  `ResolutionTimeline`, `AuditReport` y `AuditEngine`;
- contrato `AuditRecordStore`;
- contrato `AuditAccessVerifier` y comando `AuditQuery`;
- `AuditQueryService` para reporte, timeline y evidencia;
- `SqlAlchemyAuditRecordStore` read-only;
- `SqlAlchemyAuditAccessVerifier`;
- base canónica reproducible para nuevas decisiones de seguridad dentro del
  JSON ya existente;
- errores de acceso e integridad explícitos;
- pruebas unitarias, persistentes, de seguridad y arquitectura.

## Invariantes protegidas

- el expediente persistido sigue siendo la única fuente de verdad;
- Lifecycle conserva autoridad exclusiva sobre el estado;
- ninguna consulta produce efectos o publica outbox;
- la autorización queda ligada a resolución, actor, correlación, acción,
  recurso y organización exactos;
- ninguna evidencia cruza resoluciones;
- las relaciones y hashes incompatibles generan diagnósticos estables;
- los filtros se aplican después de verificar el expediente completo;
- el mismo corte produce timeline y `record_hash` idénticos;
- todas las consultas que forman un corte comparten el mismo snapshot SQL;
- las bases históricas ausentes no se inventan ni se presentan como
  verificadas.

## Corrección de consistencia transaccional

La observación bloqueante sobre expedientes híbridos quedó corregida en la
frontera SQL. `SqlAlchemyAuditRecordStore` abre una conexión y transacción
propias, aplica `REPEATABLE READ` en PostgreSQL o `SERIALIZABLE` con `BEGIN`
explícito en SQLite, carga todas las filas y termina la proyección antes de
cerrar el snapshot.

La prueba persistente concurrente pausa la lectura tras cargar la raíz,
confirma una transición desde otra sesión y reanuda la reconstrucción. El
reporte en curso coincide por completo con el corte anterior —estado, versión,
nodos, verificaciones, timeline y `record_hash`— y una consulta posterior
coincide por completo con el nuevo estado. Nunca se persiste información ni se
reintenta la reconstrucción.

## Persistencia y migraciones

No existe migración de Fase 7. Las 26 tablas generales aprobadas ya contienen
el expediente necesario. La base canónica de nuevas decisiones de seguridad se
guarda en `context_snapshot.evidence_payload`, preservando el esquema y el
contrato histórico.

## Validaciones

- Fase 7 + arquitectura: **33 passed**.
- Suite completa del Motor: **184 passed**.
- Backend completo: **308 passed**, **19 subtests passed**, dos advertencias
  conocidas de dependencias.
- Frontend: **11 passed**.
- Build Vite: correcto; permanece el aviso conocido de chunk superior a 500 kB.
- Compilación Python: correcta para `app` y `tests`.
- Alembic `current` y `heads`: `d6e8f0a2b4c5 (head)`.
- `alembic check`: conserva exclusivamente la deriva histórica `TD-021`; no
  propone operación sobre `resolution_*` atribuible a esta corrección.
- Arquitectura: capas, aislamiento del snapshot, adaptador read-only, autoridad
  de Lifecycle y ausencia de dependencias posteriores verificadas.
- Inventario: regenerado mediante el script oficial y rutas verificadas.
- `git diff --check`: correcto.

## Contradicciones

No se detectó contradicción del ERP que bloqueara la fase. El esquema general
existente evitó crear tablas o migraciones duplicadas.

## Deuda no abordada

- Decisiones de seguridad históricas anteriores a esta fase pueden carecer de
  su base canónica completa. Se reportan honestamente como `asserted`; no es
  posible convertirlas a `verified` sin inventar permisos o contexto pasado.
- Firma externa, retención, exportación regulatoria, métricas, API y UI
  permanecen fuera del alcance aprobado.

## Archivos incorporados

- `domain/audit.py`;
- `contracts/audit.py`;
- `application/audit.py`;
- `infrastructure/audit.py`;
- `infrastructure/audit_projection.py`;
- `test_audit.py`;
- `test_audit_persistence.py`;
- `20_AUDIT_EVIDENCE.md`;
- este cierre técnico.

También se actualizaron exports del paquete, persistencia de evidencia de
seguridad, pruebas arquitectónicas, matriz, estado, alcance, flujo, reglas,
decisiones, deuda, índice, respaldo operativo e inventario oficial.

## Commit

La implementación original permanece en `4ae25ea`. Esta corrección se agrupa en
un commit posterior y exclusivo cuyo hash se reporta en el cierre operativo.
La fase permanece `EN REVISIÓN` y no autoriza Fase 8.

## Estado

```text
FASE 7
EN REVISIÓN
FASE 8 NO INICIADA
```
