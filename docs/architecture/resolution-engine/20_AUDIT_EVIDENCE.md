> Estado: IMPLEMENTADO — EN REVISIÓN
>
> Fase: 7 — Auditoría y Evidencia
>
> Alcance: dominio, contratos, consultas autorizadas y adaptador SQL read-only

# Auditoría y Evidencia del Motor de Resoluciones

## Propósito

La Fase 7 convierte el expediente persistido por las Fases 1 a 6 en una
reconstrucción explícita, correlacionada y verificable. No crea una segunda
fuente de verdad: proyecta las filas generales existentes a valores puros,
verifica sus relaciones y hashes, y produce un reporte determinista.

## Componentes

- `EvidenceNode`: proyección inmutable de una fila o hecho institucional.
- `EvidenceLink`: relación explícita y, cuando aplica, hash esperado.
- `EvidenceRegistry`: índice por identidad estable, con detección de duplicados.
- `AuditEngine`: verificador puro de alcance, hashes, referencias y secuencia.
- `ResolutionTimeline`: cronología determinista de hechos con timestamp.
- `AuditReport`: resultado reproducible, evidencia, diagnósticos y hash del
  corte consultado.
- `AuditQueryService`: consultas de reporte, timeline y evidencia.
- `AuditRecordStore`: puerto de lectura del expediente normalizado.
- `AuditAccessVerifier`: puerto que exige autorización exacta antes de leer.
- `SqlAlchemyAuditRecordStore`: adaptador read-only sobre el repositorio general.
- `AuditProjector`: traducción SQL→evidencia separada por áreas del expediente.

## Flujo

```text
AuditQuery + security_decision_id
  → validar allowed + acción + resolución + actor + correlación + organización
  → abrir transacción read-only con snapshot consistente
  → cargar ResolutionRecord completo dentro del snapshot
  → proyectar filas ORM a EvidenceNode antes de cerrar la transacción
  → construir EvidenceRegistry
  → verificar alcance, hashes, vínculos y secuencia
  → construir ResolutionTimeline
  → calcular record_hash del corte
  → AuditReport
```

Filtrar por tipo o correlación ocurre después de verificar el expediente
completo. Una consulta parcial no puede ocultar una inconsistencia.

## Consistencia del corte

Cada `AuditReport` representa un único snapshot lógico. El adaptador abre una
conexión y transacción propias para reconstruir el expediente completo:

- PostgreSQL usa aislamiento `REPEATABLE READ`;
- SQLite, usado por las pruebas persistentes, usa `SERIALIZABLE` y un
  `BEGIN` explícito para evitar el modo transaccional legacy del driver.

La raíz, colecciones relacionadas y proyección se leen y materializan antes de
cerrar esa transacción. Una confirmación concurrente puede quedar completamente
fuera o completamente dentro del corte, pero nunca aportar sólo una parte. El
aislamiento pertenece al adaptador SQL; el dominio no conoce conexiones ni
reintenta consultas. La autorización exacta se verifica antes de abrir el
snapshot; su decisión persistida también se reconstruye como evidencia cuando
pertenece al corte.

## Verificaciones

El Motor reporta códigos estables para:

- `duplicate_evidence_key`;
- `foreign_resolution_evidence`;
- `evidence_hash_mismatch`;
- `evidence_link_missing`;
- `evidence_link_crosses_resolution`;
- `evidence_link_hash_mismatch`;
- `audit_sequence_gap`;
- `lifecycle_audit_chain_broken`;
- `lifecycle_audit_prefix_unavailable`;
- `lifecycle_audit_state_mismatch`;
- `lifecycle_audit_version_mismatch`;
- `audit_history_missing`.

`is_valid` sólo es verdadero cuando no existe un error de integridad. El
reporte no repara, elimina ni reinterpreta evidencia.

## Grados de verificación

- `verified`: el payload canónico disponible reproduce exactamente el hash.
- `asserted`: existe hash persistido y sus vínculos se verifican, pero el
  expediente histórico no conserva su base canónica completa.
- `not_hashed`: el registro no tiene hash por contrato.
- `invalid`: el hash calculado contradice el persistido.

Audit events, outbox, nuevos eventos de seguridad y planes/pasos de
compensación conservan bases reproducibles. Las nuevas decisiones de seguridad
guardan `evidence_payload` dentro de su `context_snapshot`; esto no modifica su
semántica ni requiere una columna nueva.

No se inventa información para decisiones históricas previas que no conservaron
la base completa. Se muestran como `asserted`, nunca como `verified`.

## Autorización de consultas

Toda consulta exige una `ResolutionSecurityDecision`:

- `outcome = allowed`;
- `action = resolution.audit.inspect`;
- misma resolución;
- mismo actor;
- misma correlación;
- recurso `resolution` con ID interno o público exacto;
- misma organización cuando la raíz la define.

Desde Fase 8, `AuditQuery` transporta el `ActorContext`, instante y contexto
exactos; la autenticación y permisos deben seguir vigentes y la evidencia debe
contener la política integral y un hash reproducible.

El servicio no codifica roles ni consulta tablas propietarias. La decisión se
produce mediante las políticas generales de seguridad aprobadas.

## Persistencia

No fue necesaria una migración. La Fase 2 ya provee las tablas generales de
auditoría, seguridad, evidencia, outbox, ejecución y compensación. El adaptador:

- sólo lee;
- no abre gateways;
- delimita y cierra su transacción read-only sin confirmar la unidad de trabajo
  del llamador;
- no modifica Lifecycle;
- no persiste proyecciones o timelines derivados.

El `record_hash` identifica un corte reconstruido; puede cambiar cuando avanza
legítimamente un registro operativo mutable. No sustituye hashes históricos ni
firmas externas.

## Invariantes

- Lifecycle continúa como única autoridad del estado.
- La consulta nunca invoca handlers, compensaciones ni publicación outbox.
- Evidencia de otra resolución se rechaza.
- Los vínculos exactos de plan/simulación se validan contra sus hashes.
- Un reporte nunca combina raíz, eventos o evidencia de commits distintos.
- La cronología es estable para el mismo expediente.
- El dominio y la aplicación no importan SQLAlchemy, FastAPI ni ERP.
- API, frontend, gateways, workers, retries y recuperación siguen fuera.
