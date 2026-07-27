> Estado: VIGENTE
>
> Tipo: Contrato técnico implementado
>
> Autoridad: Esquema persistente de la Fase 2
>
> Complementa a: `07_MODELO_DE_DATOS.md` y `13_IMPLEMENTATION_MATRIX.md`
>
> Corte verificado: 2026-07-28

# Persistencia del Motor de Resoluciones

## Propósito

Este contrato describe la infraestructura persistente incorporada en la Fase 2.
El esquema conserva la evidencia necesaria para reconstruir una resolución sin
depender del estado vivo de un módulo propietario. No implementa lifecycle,
simulación, lifecycle de autorización ni ejecución. La Fase 3 agregó la
evidencia de evaluación de seguridad descrita en
[`15_SECURITY_GOVERNANCE.md`](15_SECURITY_GOVERNANCE.md). Las fases 4 a 6
activaron Lifecycle, ejecución y compensación sin alterar la generalidad del
expediente.

## Criterios de diseño

- El agregado raíz se identifica mediante `public_id` técnico opaco y
  `request_key` idempotente, sin reutilizar folios de los dominios.
- `resolution_type` y `definition_version` congelan la definición aplicable.
- El sujeto se representa mediante `subject_type` y `subject_id`; no existen
  columnas particulares de ETS, Equipos, Facturación u otro primer caso.
- El contexto, análisis, estrategias, planes, simulaciones y evidencias
  conservan versión, hash y payload reproducible.
- Las relaciones críticas son claves foráneas; las dependencias entre pasos son
  aristas normalizadas, no listas embebidas en JSON.
- JSONB se reserva para documentos variables versionados. Identidad, orden,
  estado, hashes y relaciones permanecen en columnas estructuradas.
- La raíz usa `version` para concurrencia optimista futura.
- No existe borrado lógico. La evidencia histórica se conserva y los registros
  derivados son append-only.

## Tablas por responsabilidad

| Grupo | Tablas |
| --- | --- |
| Identidad y decisión | `resolutions`, `resolution_problems`, `resolution_context_snapshots`, `resolution_analyses`, `resolution_strategy_selections` |
| Planeación | `resolution_plans`, `resolution_plan_steps`, `resolution_plan_step_dependencies`, `resolution_simulations` |
| Gobierno y seguridad | `resolution_authorization_requests`, `resolution_authorization_decisions`, `resolution_security_decisions`, `resolution_revalidations` |
| Ejecución | `resolution_executions`, `resolution_step_executions`, `resolution_entity_references`, `resolution_results` |
| Compensación | `resolution_compensation_plans`, `resolution_compensation_plan_steps`, `resolution_compensation_executions`, `resolution_compensation_step_executions` |
| Evidencia e infraestructura | `resolution_audit_events`, `resolution_idempotency_records`, `resolution_locks`, `resolution_outbox_events`, `resolution_evidence_references` |

El esquema reúne 26 tablas generales. Su creación en Fase 2 no habilitó
comportamiento: cada capacidad se activó únicamente en su fase aprobada. Las
cuatro tablas compensatorias agregadas en Fase 6 son igualmente independientes
de módulos propietarios.

Desde Fase 3, las referencias de identidad usan IDs canónicos de actor sin FK a
`users.id`. `resolution_security_decisions` conserva evaluaciones reales de
políticas; las solicitudes y decisiones de aprobación continúan sin lifecycle
hasta Fase 4.

## Versionado y reconstrucción

Una reconstrucción carga la raíz y todas sus filas asociadas mediante
`ResolutionRepository.load_record()`. El resultado incluye:

1. problema y snapshots de contexto;
2. análisis y selecciones de estrategia;
3. todas las versiones de plan, pasos y dependencias;
4. simulaciones, solicitudes y decisiones de autorización;
5. revalidaciones, intentos y pasos de ejecución;
6. planes, pasos, intentos y checkpoints de compensación;
7. referencias a entidades, resultado, auditoría, decisiones de seguridad,
   idempotencia, locks, outbox y evidencia externa.

Las autorizaciones apuntan al plan y simulación exactos junto con sus hashes.
La ejecución apunta a la revalidación y plan exactos. Las claves foráneas
compuestas impiden mezclar evidencia perteneciente a otra resolución. Cada
paso compensatorio apunta al checkpoint confirmado y al paso de plan que
originaron el efecto; su unicidad impide volver a planificar el mismo efecto.

## Inmutabilidad

PostgreSQL aplica las siguientes defensas mediante triggers de la migración:

- las tablas de evidencia derivada no admiten `UPDATE` ni `DELETE`;
- las tablas cuyo estado deberá avanzar en fases posteriores no admiten
  `DELETE`;
- un plan sólo puede editarse mientras su estado anterior sea `draft`;
- la identidad y versión de un plan no pueden cambiar;
- los pasos y dependencias sólo pueden insertarse, editarse o eliminarse
  mientras su plan permanezca en `draft`.

La raíz conserva referencias explícitas al contexto, estrategia y plan
vigentes. Estas referencias se agregan después de crear las tablas para romper
el ciclo de dependencias sin debilitar la integridad referencial.

## Índices e invariantes

- una sola estrategia activa por resolución;
- un solo plan activo por resolución;
- una sola clave de lock activa por alcance;
- unicidad de versiones, secuencias, intentos y claves idempotentes dentro de
  su agregado;
- hashes SHA-256 validados por longitud;
- estados y tipos restringidos mediante `CHECK`;
- claves foráneas internas con `ON DELETE RESTRICT`.

## Repositorio

`ResolutionRepository` es deliberadamente pequeño: agrega filas a una sesión,
consulta por ID público o request key y reconstruye el expediente completo. No
inicia ni confirma transacciones, no cambia estados y no contiene reglas de
negocio. La unidad de trabajo y el ciclo de vida pertenecen a servicios
especializados posteriores al esquema.

## Evolución compatible

Nuevos tipos de resolución reutilizan el mismo esquema mediante definiciones y
documentos versionados. Una relación nueva sólo debe convertirse en columna
cuando sea una invariante transversal consultable; los datos especializados
permanecen en snapshots o referencias tipadas. Desde Fase 5, el outbox, los
locks y la idempotencia tienen comportamiento mediante adaptadores explícitos.
La corrección de revisión `c5d7e9f1a3b4` agrega `failed_at` nullable al outbox
para conservar la fecha exacta de una publicación fallida sin introducir
reintentos. La migración `d6e8f0a2b4c5` agrega evidencia compensatoria
inmutable y estados raíz de compensación; su ejecución permanece síncrona y
gobernada por Lifecycle.

La migración de Fase 8 `e7f9a1b3c5d7` no agrega tablas: relaciona las
decisiones de seguridad con la revalidación exacta y cada nueva ejecución con
su decisión autorizante mediante FKs compuestas, constraint de completitud e
índice. Las columnas permanecen nulas para históricos y no se inventa
autoridad retrospectiva.
