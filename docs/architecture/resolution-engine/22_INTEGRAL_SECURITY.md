> Estado: IMPLEMENTADO — EN REVISIÓN
>
> Fase: 8 — Seguridad integral
>
> Fecha: 2026-07-27

# Seguridad integral del Motor de Resoluciones

## Autoridad única

`SecurityPolicyEvaluator` continúa siendo el único evaluador de políticas. La
Fase 8 incorpora dentro de él `IntegralSecurityControlPolicy`, un catálogo
canónico versionado que asigna a cada capacidad protegida su acción, permiso
atómico, tipo de recurso y nivel de riesgo. Una acción desconocida, un tipo de
recurso distinto o cualquier reducción/cambio del permiso esperado se deniega
antes de evaluar las políticas institucionales.

`SqlAlchemySecurityDecisionVerifier` no reevalúa políticas ni decide autoridad.
Comprueba que una concesión append-only ya emitida por el evaluador conserva
exactamente actor, autenticación, organización, correlación, acción, recurso,
permisos, contexto, plan, revalidación, semántica de uso, operación e intención
canónica. Ejecución, compensación, Lifecycle, auditoría y outbox reutilizan
este único verificador.

## Semántica de uso y replay

El catálogo central versión `1.1` declara una de dos semánticas por acción:

- `single_operation`: toda mutación y publicación crítica queda ligada a un
  `operation_id`, un payload de intención y su hash canónico;
- `reusable_read`: sólo `resolution.audit.inspect`; permite repetir la misma
  consulta exacta mientras identidad, autenticación, permisos y contexto sigan
  vigentes.

Una decisión `single_operation` se reserva en
`resolution_security_decision_uses` dentro de la misma transacción que inicia
el cambio. La unicidad por decisión impide consumirla para otra operación; la
unicidad por organización, acción y `operation_id` impide representar una
misma operación con concesiones divergentes. Un rollback revierte también la
reserva. Un reintento con el mismo ID y hash continúa por la idempotencia del
límite; el mismo ID con otra intención o la misma decisión con otra operación
se deniega.

## Controles transversales

El catálogo protege `resolution.create`,
`resolution.lifecycle.transition`, construcción de contexto, análisis,
selección de estrategia, plan, simulación, autorización, revalidación,
ejecución, compensación, consulta de auditoría y publicación de outbox.

Las etapas puras de orquestación no leen ni mutan persistencia y sólo resuelven
componentes versionados sobre entradas entregadas por el llamador. La decisión
institucional se exige en las fronteras que crean/cambian el expediente,
producen o compensan efectos, exponen evidencia o publican mensajes. No existe
otra ruta persistente autorizada.

## Reglas reforzadas

- La autenticación se rechaza antes de `authenticated_at`, al vencer o si el
  actor deja de estar activo.
- Los `PermissionGrant.constraints` deben coincidir con el contexto exacto de
  la operación; conocer el nombre del permiso no basta.
- Plan, simulación y revalidación exigen pares completos de ID/hash y versiones
  positivas.
- El verificador de recursos comprueba raíz, organización, public ID, plan,
  versión/hash, simulación, revalidación, autorización y ejecución.
- La evidencia canónica persistida se recalcula y compara con
  `evidence_hash`; evidencia histórica incompleta conserva la clasificación
  honesta establecida en Fase 7 y no autoriza límites endurecidos nuevos.

## Límites críticos

### Lifecycle

Crear exige `request_key` y una decisión `resolution.create` ligada al comando
canónico completo: definición/versión/fingerprint, fuente, sujeto, problema y
metadatos. Repetir exactamente la misma solicitud devuelve la misma resolución;
cambiar cualquier parte no puede reutilizar la concesión. Las transiciones
incluyen resolución, acción, estado y versión esperados, contexto e identidad
única de operación. Una concesión de una versión anterior no autoriza otra
transición. Sólo `ResolutionStateMachine` calcula el nuevo estado.

### Ejecución

`ExecuteResolutionCommand` porta `security_decision_id`. La decisión
`resolution.execute` debe señalar el plan y la revalidación exactos. Se
verifica antes de consultar un replay y se consume dentro de la transacción que
reserva idempotencia, lock, ejecución y Lifecycle. La clave idempotente es
también la identidad de operación: el replay exacto recupera el resultado y un
actor o intención distintos no pueden tantearlo.

### Compensación

La preparación consume y el inicio vuelve a comprobar la misma concesión
`resolution.compensate`, incluida vigencia actual de autenticación/permisos,
actor, organización, ejecución fuente, estrategia, razón, selección exacta,
contexto e identidad idempotente. No cambia la clausura de dependencias ni la
recuperación idempotente de Fase 6.

### Auditoría

`AuditQuery` transporta el `ActorContext`, el instante, `operation_id` y el
contexto de consulta. Su concesión `reusable_read` puede reutilizarse sólo para
la misma resolución y contexto exactos, durante la vigencia de la
autenticación. No crea un consumo mutante. El acceso se verifica antes de abrir
el snapshot read-only.

### Outbox

La publicación explícita exige `resolution.outbox.publish`, `operation_id`,
actor, organización y límite. La primera reserva congela los IDs exactos del
lote y los marca con esa operación; un replay devuelve el reporte del mismo
lote y nunca selecciona los siguientes pendientes. No se agregan workers,
scheduler, retry ni automatización.

## Persistencia

La revisión `e7f9a1b3c5d7` agrega referencias opcionales y compatibles con el
histórico:

- revalidación ID/hash en `resolution_security_decisions`;
- vínculo exacto de `resolution_executions` con la decisión de seguridad;
- FKs compuestas, constraint de completitud e índice.

La corrección `f8a0b2c4d6e8`, posterior al head de Actividad
`fabc2cd495ef`, agrega:

- modo de uso, identidad, payload y hash de operación a cada decisión;
- `resolution_security_decision_uses` como consumo append-only con unicidad
  transaccional;
- `publication_operation_id` para congelar cada lote de outbox.

Las decisiones históricas reciben marcadores `legacy-decision:*` para conservar
integridad estructural, pero no adquieren retrospectivamente una intención
verificable ni autorizan límites endurecidos nuevos.

## Límites

No se incorporan API, routers, integración ERP, gateways de dominio, UI,
workers, distribución, IA ni automatizaciones. La seguridad general del ERP
permanece en su proyecto propio y no se declara resuelta por este contrato.
