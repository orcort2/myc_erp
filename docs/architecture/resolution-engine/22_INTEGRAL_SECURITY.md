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
permisos, contexto, plan, revalidación y hash. Ejecución, compensación,
Lifecycle, auditoría y outbox reutilizan este único verificador.

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

Crear exige una decisión `resolution.create` para la definición versionada y
la fuente exactas. Las transiciones exigen
`resolution.lifecycle.transition` para resolución, actor y acción exactos
antes de reconstruir el expediente. El ID de decisión queda en la evidencia de
creación/transición; sólo `ResolutionStateMachine` calcula el nuevo estado.

### Ejecución

`ExecuteResolutionCommand` porta `security_decision_id`. La decisión
`resolution.execute` debe señalar el plan y la revalidación exactos. Se
verifica antes de consultar un replay y otra vez dentro de la transacción que
reserva idempotencia, lock, ejecución y Lifecycle. Un actor ajeno no puede usar
la clave idempotente para recuperar un resultado.

### Compensación

La preparación y el inicio vuelven a comprobar la misma concesión
`resolution.compensate`, incluida vigencia actual de autenticación/permisos,
actor, organización, ejecución fuente, contexto y hash. No cambia la selección
ni la clausura de dependencias de Fase 6.

### Auditoría

`AuditQuery` transporta el `ActorContext`, el instante y el contexto de
consulta. El acceso se verifica antes de abrir el snapshot read-only. Después
continúan sin cambios la verificación completa, el filtrado posterior y la
reconstrucción determinista de Fase 7.

### Outbox

La publicación explícita exige `resolution.outbox.publish`, queda ligada a
actor, organización y límite del lote, y sólo selecciona eventos cuyas raíces
pertenecen a esa organización. No se agregan workers, scheduler, retry ni
automatización.

## Persistencia

La revisión `e7f9a1b3c5d7` agrega referencias opcionales y compatibles con el
histórico:

- revalidación ID/hash en `resolution_security_decisions`;
- vínculo exacto de `resolution_executions` con la decisión de seguridad;
- FKs compuestas, constraint de completitud e índice.

Las filas históricas permanecen válidas con valores nulos; toda ejecución nueva
del contrato de Fase 8 persiste la decisión exacta.

## Límites

No se incorporan API, routers, integración ERP, gateways de dominio, UI,
workers, distribución, IA ni automatizaciones. La seguridad general del ERP
permanece en su proyecto propio y no se declara resuelta por este contrato.
