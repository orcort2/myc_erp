# 07 · Modelo de Datos

# Modelo de Datos del Motor de Resoluciones

## Introducción

El modelo de datos del Motor de Resoluciones deberá preservar el ciclo de vida completo de cada intervención extraordinaria realizada dentro del ERP MYC.

Su objetivo no consiste únicamente en almacenar el estado actual de una resolución.

Debe permitir reconstruir posteriormente:

- qué problema originó la resolución;
- qué información observó el motor;
- qué análisis realizó;
- qué estrategia seleccionó;
- qué plan propuso;
- qué impactos simuló;
- quién autorizó o rechazó;
- qué cambió antes de ejecutar;
- qué operaciones fueron realizadas;
- qué entidades fueron creadas o relacionadas;
- qué errores ocurrieron;
- cuál fue el resultado final.

La persistencia del motor constituye evidencia operativa e institucional.

Por esta razón, el modelo deberá privilegiar:

- trazabilidad;
- inmutabilidad;
- versionado;
- idempotencia;
- control de concurrencia;
- explicabilidad;
- conservación histórica.

---

# Alcance del modelo

Este documento define el modelo lógico y conceptual de persistencia del Motor de Resoluciones.

No obliga a utilizar nombres exactos de tablas, tipos de datos específicos ni una estructura ORM determinada.

La implementación deberá adaptarse a las convenciones técnicas existentes del ERP MYC.

Sin embargo, deberá conservar las entidades, responsabilidades, relaciones e invariantes descritas en este documento.

---

# Principio rector

La entidad principal del modelo será:

```text
Resolution
```

Toda la información producida durante el ciclo de vida del motor deberá vincularse directa o indirectamente con un `resolution_id`.

---

# Vista general de entidades

```text
Resolution
├── ResolutionProblem
├── ResolutionContextSnapshot[]
├── ResolutionAnalysis[]
├── ResolutionStrategySelection[]
├── ResolutionPlan[]
│   └── ResolutionPlanStep[]
├── ResolutionSimulation[]
├── ResolutionAuthorizationRequest[]
│   └── ResolutionAuthorizationDecision[]
├── ResolutionRevalidation[]
├── ResolutionExecution[]
│   └── ResolutionStepExecution[]
│       └── ResolutionEntityReference[]
├── ResolutionResult
├── ResolutionAuditEvent[]
├── ResolutionLock[]
└── ResolutionIdempotencyRecord[]
```

No todas estas entidades deberán implementarse necesariamente como tablas independientes.

Algunas podrán integrarse como estructuras persistentes dentro de otra entidad cuando ello no afecte la trazabilidad, el versionado ni la capacidad de consulta.

---

# Resolution

## Definición

`Resolution` representa un caso completo administrado por el Motor de Resoluciones.

Es la raíz de agregado del subsistema.

Una resolución comienza cuando se registra un problema extraordinario y termina cuando:

- se completa;
- se rechaza;
- se cancela;
- es sustituida por otra resolución;
- se determina que ya no requiere acción.

---

## Campos conceptuales

```text
Resolution
├── id
├── public_id
├── resolution_type
├── definition_version
├── status
├── priority
├── source
├── subject_type
├── subject_id
├── parent_resolution_id
├── superseded_by_resolution_id
├── requested_by_user_id
├── assigned_to_user_id
├── assigned_role
├── organization_id
├── branch_id
├── correlation_id
├── request_key
├── title
├── description
├── reason
├── current_plan_id
├── current_context_snapshot_id
├── current_strategy_key
├── risk_level
├── requires_authorization
├── created_at
├── updated_at
├── completed_at
├── cancelled_at
├── rejected_at
├── version
└── metadata
```

---

## `id`

Identificador técnico interno.

Podrá ser entero, UUID u otro tipo compatible con las convenciones del ERP.

No deberá utilizarse como folio institucional.

---

## `public_id`

Identificador público de la resolución.

Ejemplo conceptual:

```text
RES-2026-000142
```

Este identificador facilita:

- consulta operativa;
- soporte;
- auditoría;
- comunicación entre usuarios.

El formato definitivo pertenece al módulo del Motor de Resoluciones.

No debe confundirse con los folios de otras entidades del ERP.

---

## `resolution_type`

Clave estable que identifica el tipo de resolución.

Ejemplos:

```text
service_order.add_additional_equipment
service_order.request_additional_signature
service_order.pause
capture.reopen
certificate.replace
invoice.modify_after_issue
sync.resolve_offline_conflict
```

Esta clave deberá corresponder con una definición registrada en el `ResolutionRegistry`.

---

## `definition_version`

Versión de la definición lógica utilizada para procesar la resolución.

Ejemplo:

```text
1.0
1.1
2.0
```

Permite reconstruir posteriormente qué lógica estaba vigente al momento de generar el plan.

---

## `status`

Estado actual de la resolución.

Estados conceptuales:

```text
draft
context_ready
analyzed
plan_ready
simulated
pending_authorization
authorized
revalidating
ready_for_execution
executing
completed
partially_completed
failed
blocked
rejected
cancelled
superseded
no_action_required
```

La implementación deberá utilizar un catálogo o enumeración controlada.

---

## `priority`

Prioridad operativa de atención.

Valores posibles:

```text
low
normal
high
critical
```

La prioridad no deberá modificar las reglas de consistencia.

Únicamente podrá afectar orden de atención, alertas o escalamiento.

---

## `source`

Origen de la resolución.

Ejemplos:

```text
user
module
system
sync
mobile_app
scheduled_process
administrator
```

---

## `subject_type` y `subject_id`

Representan la entidad principal afectada.

Ejemplos:

```text
subject_type = service_order
subject_id = 418
```

o:

```text
subject_type = invoice
subject_id = 72
```

Una resolución podrá involucrar múltiples entidades adicionales, pero deberá existir una entidad principal de referencia.

---

## `parent_resolution_id`

Permite relacionar una resolución derivada con otra anterior.

Ejemplos:

- una resolución fallida genera una resolución de recuperación;
- una resolución compleja se divide en subresoluciones;
- un conflicto offline deriva en una resolución operativa específica.

---

## `superseded_by_resolution_id`

Referencia a la resolución que sustituyó a la actual.

Una resolución sustituida deberá quedar preservada.

No deberá eliminarse ni editarse para aparentar que nunca existió.

---

## `request_key`

Clave de idempotencia de la solicitud original.

Debe impedir que la misma solicitud lógica cree múltiples resoluciones activas de forma accidental.

---

## `version`

Versión de concurrencia optimista de la fila.

Deberá incrementarse al modificar el estado mutable de la resolución.

Permitirá detectar actualizaciones simultáneas.

---

# ResolutionProblem

## Definición

Representa el problema original que motivó la creación de la resolución.

El problema describe la situación.

No contiene la solución.

---

## Campos conceptuales

```text
ResolutionProblem
├── id
├── resolution_id
├── problem_code
├── summary
├── description
├── detected_by
├── detected_at
├── reported_by_user_id
├── source_payload
├── external_reference
├── severity
├── observed_state
└── evidence
```

---

## `problem_code`

Código específico del problema detectado.

Ejemplos:

```text
additional_equipment_after_service_start
invoice_already_issued
certificate_already_authenticated
offline_entity_conflict
signature_scope_outdated
```

Una misma clase de resolución podrá responder a varios códigos de problema relacionados.

---

## `source_payload`

Información original recibida desde la interfaz, módulo o dispositivo.

Debe conservarse como evidencia.

No deberá utilizarse sin validación como fuente única de verdad.

---

## `evidence`

Referencias a documentos, imágenes, comentarios, archivos o registros relacionados con el problema.

Los archivos deberán almacenarse mediante el mecanismo documental oficial del ERP.

El Motor de Resoluciones sólo conservará sus referencias.

---

# ResolutionContextSnapshot

## Definición

Representa una fotografía inmutable del contexto utilizado por el motor en un momento determinado.

Una resolución puede tener múltiples snapshots:

- contexto inicial;
- contexto previo a simulación;
- contexto previo a autorización;
- contexto de revalidación;
- contexto final.

---

## Campos conceptuales

```text
ResolutionContextSnapshot
├── id
├── resolution_id
├── snapshot_type
├── sequence
├── context_version
├── context_hash
├── schema_version
├── captured_at
├── captured_by
├── facts
├── entity_versions
├── missing_facts
├── warnings
└── source_references
```

---

## `snapshot_type`

Tipo de captura.

Ejemplos:

```text
initial
analysis
simulation
authorization
revalidation
pre_execution
post_execution
final
```

---

## `facts`

Representación serializada y normalizada de los hechos relevantes.

Ejemplo conceptual:

```json
{
  "service_order": {
    "id": 418,
    "status": "in_progress",
    "updated_at": "2026-07-23T15:48:21-06:00"
  },
  "invoice": {
    "exists": true,
    "status": "draft"
  },
  "certificates": {
    "authenticated_count": 0
  },
  "equipment": {
    "registered_count": 20,
    "expected_count": 20
  }
}
```

---

## `entity_versions`

Mapa de las versiones o marcas de actualización de las entidades observadas.

Ejemplo:

```json
{
  "service_order:418": {
    "version": 12,
    "updated_at": "2026-07-23T15:48:21-06:00"
  },
  "invoice:72": {
    "version": 3,
    "status": "draft"
  }
}
```

Este campo permitirá identificar cambios significativos durante la revalidación.

---

## `context_hash`

Huella calculada sobre los hechos relevantes.

No deberá incluir valores irrelevantes o volátiles que provoquen invalidaciones innecesarias.

Ejemplos de datos que normalmente no deberían invalidar un plan:

- cambio de teléfono del cliente;
- actualización de una descripción no operativa;
- modificación de preferencias visuales.

Ejemplos de datos que sí pueden invalidarlo:

- estado del ETS;
- emisión de una factura;
- autenticación de un certificado;
- cambio en la relación de equipos;
- cambio en la autorización vigente.

---

## Inmutabilidad

Una vez creado, un snapshot no deberá editarse.

Si se detecta información incorrecta o incompleta, deberá generarse un nuevo snapshot.

---

# ResolutionAnalysis

## Definición

Conserva el resultado del análisis realizado sobre un contexto específico.

---

## Campos conceptuales

```text
ResolutionAnalysis
├── id
├── resolution_id
├── context_snapshot_id
├── analysis_version
├── is_resolvable
├── status
├── findings
├── constraints
├── blockers
├── warnings
├── missing_information
├── immutable_entities
├── available_strategies
├── analyzed_at
├── analyzed_by
└── analysis_hash
```

---

## Estados posibles

```text
resolvable
not_resolvable
requires_information
blocked
already_resolved
```

---

## `findings`

Hallazgos explicables producidos por el análisis.

Ejemplo:

```json
[
  {
    "code": "ETS_IN_PROGRESS",
    "severity": "info",
    "message": "El ETS permanece abierto."
  },
  {
    "code": "NO_ISSUED_INVOICE",
    "severity": "info",
    "message": "No existe factura emitida."
  }
]
```

---

## `immutable_entities`

Entidades cuya historia no puede alterarse.

Ejemplo:

```json
[
  {
    "entity_type": "certificate",
    "entity_id": 901,
    "reason": "authenticated"
  }
]
```

---

# ResolutionStrategySelection

## Definición

Registra la estrategia elegida para resolver el problema.

No deberá almacenarse únicamente como un campo mutable dentro de `Resolution`.

Cada selección o cambio deberá conservarse históricamente.

---

## Campos conceptuales

```text
ResolutionStrategySelection
├── id
├── resolution_id
├── analysis_id
├── strategy_key
├── strategy_version
├── selection_mode
├── selected_by_user_id
├── selected_at
├── justification
├── alternatives
├── is_active
└── superseded_at
```

---

## `selection_mode`

Forma en que fue elegida.

```text
automatic
user_selected
policy_selected
system_recommended
```

---

## `alternatives`

Estrategias evaluadas pero no seleccionadas, con su motivo.

Ejemplo:

```json
[
  {
    "strategy_key": "append_to_existing_ets",
    "available": false,
    "reason": "El ETS ya fue cerrado."
  },
  {
    "strategy_key": "create_complementary_ets",
    "available": true,
    "reason": "Preserva la historia del servicio original."
  }
]
```

---

# ResolutionPlan

## Definición

Representa una versión concreta del conjunto de acciones que el motor propone ejecutar.

Una resolución puede tener múltiples versiones de plan.

---

## Campos conceptuales

```text
ResolutionPlan
├── id
├── resolution_id
├── strategy_selection_id
├── context_snapshot_id
├── version
├── schema_version
├── status
├── summary
├── rationale
├── expected_impact
├── preserved_entities
├── warnings
├── blockers
├── authorization_requirements
├── plan_hash
├── created_by
├── created_at
├── activated_at
├── invalidated_at
├── invalidation_reason
└── is_active
```

---

## Estados conceptuales

```text
draft
ready
simulated
pending_authorization
authorized
invalidated
executing
executed
failed
superseded
cancelled
```

---

## Regla de versión

La combinación deberá ser única:

```text
resolution_id + version
```

Ejemplo:

```text
Resolution 84
├── Plan v1
├── Plan v2
└── Plan v3
```

---

## Inmutabilidad del plan

Un plan podrá modificarse mientras permanezca en borrador.

Después de ser:

- simulado;
- presentado para autorización;
- autorizado;
- ejecutado;

no deberá editarse.

Cualquier cambio deberá generar una nueva versión.

---

## `plan_hash`

Huella del contenido completo del plan.

La autorización deberá vincularse a este hash, además del identificador y versión del plan.

Esto evita que un plan sea alterado después de su aprobación.

---

# ResolutionPlanStep

## Definición

Representa una operación declarativa dentro de un plan.

---

## Campos conceptuales

```text
ResolutionPlanStep
├── id
├── plan_id
├── step_key
├── sequence
├── operation_key
├── owner_module
├── description
├── input_payload
├── expected_output
├── preconditions
├── dependencies
├── criticality
├── retry_policy
├── timeout_policy
├── is_compensable
├── compensation_operation_key
├── compensation_payload
├── point_of_no_return
├── requires_separate_authorization
├── created_at
└── step_hash
```

---

## `step_key`

Identificador estable del paso dentro del plan.

Ejemplo:

```text
create_complementary_quotation
create_complementary_service_order
register_additional_equipment
assign_work_orders
create_field_sheets
```

---

## `operation_key`

Contrato de dominio que deberá invocarse.

Ejemplo:

```text
quotation.create_complementary
service_order.create_complementary
equipment.register_batch
work_order.assign_equipment
field_sheet.create_for_equipment
```

---

## `dependencies`

Referencias a pasos previos.

Ejemplo:

```json
[
  "create_complementary_quotation"
]
```

El sistema no deberá depender únicamente del número de secuencia si existen dependencias explícitas.

---

## `criticality`

Clasificación del impacto del paso.

```text
low
normal
high
irreversible
```

---

## `point_of_no_return`

Indica que, una vez completado el paso, la resolución ya no puede revertirse mediante compensaciones ordinarias.

Ejemplos:

- timbrado fiscal;
- autenticación documental;
- emisión de un documento institucional inmutable.

---

# ResolutionSimulation

## Definición

Conserva el resultado de simular una versión exacta del plan.

Una simulación pertenece a un plan específico y a un snapshot de contexto específico.

---

## Campos conceptuales

```text
ResolutionSimulation
├── id
├── resolution_id
├── plan_id
├── context_snapshot_id
├── simulation_version
├── status
├── is_valid
├── expected_actions
├── expected_creations
├── expected_changes
├── preserved_entities
├── warnings
├── blockers
├── required_authorizations
├── estimated_scope
├── simulation_hash
├── simulated_at
├── simulated_by
└── expires_at
```

---

## Estados conceptuales

```text
valid
valid_with_warnings
invalid
blocked
expired
```

---

## `expires_at`

Una simulación podrá tener vigencia limitada.

Su expiración no necesariamente invalida el plan, pero podrá obligar a simular nuevamente antes de solicitar autorización.

---

## Restricción

La simulación no deberá almacenar identificadores oficiales inventados.

Podrá registrar cantidades y tipos de entidades esperadas.

Ejemplo correcto:

```json
{
  "entity_type": "work_order",
  "expected_count": 2
}
```

Ejemplo incorrecto:

```json
{
  "folio": "OT-2026-000321"
}
```

salvo que dicho folio haya sido reservado formalmente por el módulo propietario bajo una política explícita.

---

# ResolutionAuthorizationRequest

## Definición

Representa una solicitud de autorización sobre una versión exacta de un plan.

---

## Campos conceptuales

```text
ResolutionAuthorizationRequest
├── id
├── resolution_id
├── plan_id
├── simulation_id
├── policy_key
├── policy_version
├── status
├── requested_by_user_id
├── requested_at
├── expires_at
├── required_approvals
├── authorization_scope
├── plan_hash
├── simulation_hash
└── invalidated_at
```

---

## Estados conceptuales

```text
pending
partially_approved
approved
rejected
expired
cancelled
invalidated
```

---

## `authorization_scope`

Describe qué se está autorizando.

Ejemplo:

```json
{
  "plan_version": 2,
  "strategy": "create_complementary_ets",
  "steps": [
    "create_complementary_quotation",
    "create_complementary_service_order",
    "register_additional_equipment"
  ]
}
```

---

# ResolutionAuthorizationDecision

## Definición

Representa la decisión individual de un autorizador.

No deberá sustituirse por un campo booleano dentro de la solicitud.

---

## Campos conceptuales

```text
ResolutionAuthorizationDecision
├── id
├── authorization_request_id
├── decision
├── approver_user_id
├── approver_role
├── approver_area
├── decided_at
├── comment
├── reason_code
├── signature_reference
├── permission_snapshot
├── actor_ip
├── actor_device
└── metadata
```

---

## `decision`

```text
approved
rejected
abstained
revoked
```

La revocación sólo podrá permitirse antes de la ejecución y deberá quedar registrada como una nueva decisión o evento, no mediante eliminación de la autorización original.

---

## `permission_snapshot`

Evidencia de por qué el usuario estaba autorizado en ese momento.

Ejemplo:

```json
{
  "role": "quality",
  "permissions": [
    "resolution.authorize.certificate"
  ]
}
```

---

## Restricciones

La base de datos deberá impedir o validar:

- decisiones duplicadas del mismo autorizador cuando la política no las permita;
- autorización sobre un plan invalidado;
- autorización después de expiración;
- autorización por un usuario sin permisos;
- autoautorización cuando esté prohibida.

---

# ResolutionRevalidation

## Definición

Registra la comparación entre el contexto autorizado y el contexto existente antes de ejecutar.

---

## Campos conceptuales

```text
ResolutionRevalidation
├── id
├── resolution_id
├── plan_id
├── previous_context_snapshot_id
├── current_context_snapshot_id
├── status
├── changed_facts
├── ignored_changes
├── invalidating_changes
├── warnings
├── result
├── revalidated_at
├── revalidated_by
├── validator_version
└── revalidation_hash
```

---

## Resultados conceptuales

```text
valid
valid_with_warnings
requires_new_plan
no_longer_resolvable
blocked
```

---

## `changed_facts`

Debe explicar las diferencias detectadas.

Ejemplo:

```json
[
  {
    "path": "invoice.status",
    "before": "draft",
    "after": "issued",
    "impact": "invalidating"
  }
]
```

---

## `ignored_changes`

Cambios observados que no afectan el plan.

Ejemplo:

```json
[
  {
    "path": "client.phone",
    "before": "3312345678",
    "after": "3312349999",
    "impact": "none"
  }
]
```

---

# ResolutionExecution

## Definición

Representa un intento real de ejecución de un plan.

Una misma resolución podrá tener múltiples intentos cuando exista un fallo recuperable.

---

## Campos conceptuales

```text
ResolutionExecution
├── id
├── resolution_id
├── plan_id
├── revalidation_id
├── attempt_number
├── status
├── execution_key
├── started_at
├── completed_at
├── executed_by_user_id
├── worker_id
├── lock_token
├── initial_context_hash
├── final_context_hash
├── error_code
├── error_message
├── error_details
├── retryable
├── retry_after
├── correlation_id
└── metadata
```

---

## Estados conceptuales

```text
pending
running
completed
partially_completed
failed
blocked
cancelled
compensating
compensated
```

---

## Restricción de unicidad

La combinación deberá ser única:

```text
resolution_id + attempt_number
```

También deberá existir unicidad sobre `execution_key`.

---

# ResolutionStepExecution

## Definición

Representa la ejecución de un paso individual del plan.

---

## Campos conceptuales

```text
ResolutionStepExecution
├── id
├── execution_id
├── plan_step_id
├── status
├── attempt_number
├── step_execution_key
├── started_at
├── completed_at
├── request_payload
├── response_payload
├── error_code
├── error_message
├── error_details
├── retryable
├── retry_count
├── domain_transaction_reference
├── compensation_status
├── compensation_execution_id
└── metadata
```

---

## Estados conceptuales

```text
pending
running
completed
skipped
failed
blocked
compensating
compensated
compensation_failed
```

---

## Regla de idempotencia

La combinación deberá impedir ejecutar dos veces el mismo paso lógico.

Ejemplo:

```text
plan_step_id + execution_id
```

o mediante:

```text
step_execution_key
```

Cuando un módulo propietario ya haya ejecutado correctamente una operación, el reintento deberá recuperar el resultado previo.

---

# ResolutionEntityReference

## Definición

Registra las entidades de dominio relacionadas, creadas, modificadas, preservadas o consultadas durante la resolución.

---

## Campos conceptuales

```text
ResolutionEntityReference
├── id
├── resolution_id
├── execution_id
├── step_execution_id
├── relationship_type
├── entity_type
├── entity_id
├── public_identifier
├── module
├── before_snapshot
├── after_snapshot
├── created_at
└── metadata
```

---

## `relationship_type`

```text
subject
input
created
modified
preserved
cancelled
superseded
linked
referenced
```

---

## Ejemplo

```text
resolution_id: 84
relationship_type: created
entity_type: service_order
entity_id: 615
public_identifier: ETS-2026-0145-C01
```

El folio es devuelto por el módulo propietario después de crear la entidad.

No es generado por el motor.

---

# ResolutionResult

## Definición

Representa la conclusión consolidada de una resolución.

Deberá existir como máximo un resultado activo por resolución.

---

## Campos conceptuales

```text
ResolutionResult
├── id
├── resolution_id
├── execution_id
├── status
├── summary
├── created_entities
├── modified_entities
├── preserved_entities
├── failed_steps
├── warnings
├── follow_up_actions
├── final_context_snapshot_id
├── completed_at
├── completed_by_user_id
├── result_hash
└── metadata
```

---

## Estados conceptuales

```text
success
partial_success
failed
cancelled
superseded
no_action_required
```

---

## `follow_up_actions`

Acciones necesarias después del cierre.

Ejemplos:

- obtener nueva firma;
- notificar a Calidad;
- generar factura complementaria;
- revisar un paso fallido;
- sincronizar nuevamente un dispositivo.

---

# ResolutionAuditEvent

## Definición

Representa un evento inmutable del ciclo de vida de una resolución.

Es el registro cronológico principal de auditoría.

---

## Campos conceptuales

```text
ResolutionAuditEvent
├── id
├── resolution_id
├── event_type
├── actor_type
├── actor_id
├── actor_role
├── occurred_at
├── previous_state
├── new_state
├── plan_id
├── plan_version
├── execution_id
├── correlation_id
├── source
├── payload
├── payload_hash
├── actor_ip
├── actor_device
└── metadata
```

---

## Tipos de evento

Ejemplos:

```text
resolution.created
resolution.context_captured
resolution.analyzed
resolution.strategy_selected
resolution.plan_created
resolution.plan_invalidated
resolution.simulated
resolution.authorization_requested
resolution.authorization_approved
resolution.authorization_rejected
resolution.revalidation_started
resolution.revalidation_failed
resolution.execution_started
resolution.step_started
resolution.step_completed
resolution.step_failed
resolution.compensation_started
resolution.completed
resolution.partially_completed
resolution.failed
resolution.cancelled
resolution.superseded
```

---

## Inmutabilidad

Los eventos de auditoría:

- no deberán editarse;
- no deberán eliminarse;
- no deberán reemplazarse.

Una corrección deberá registrarse mediante un nuevo evento.

---

# ResolutionIdempotencyRecord

## Definición

Almacena las claves utilizadas para evitar solicitudes y operaciones duplicadas.

---

## Campos conceptuales

```text
ResolutionIdempotencyRecord
├── id
├── scope
├── idempotency_key
├── resolution_id
├── execution_id
├── step_execution_id
├── operation_key
├── status
├── request_hash
├── response_payload
├── created_at
├── completed_at
├── expires_at
└── metadata
```

---

## `scope`

```text
resolution_request
resolution_execution
step_execution
domain_operation
offline_sync
```

---

## Restricción de unicidad

```text
scope + idempotency_key
```

deberá ser único.

---

## Comportamiento esperado

Cuando una operación se repita con la misma clave:

- si sigue en proceso, deberá informarse que ya está siendo atendida;
- si terminó correctamente, deberá devolverse el resultado anterior;
- si falló de forma reintentable, podrá iniciar un nuevo intento controlado;
- si el payload es distinto, deberá rechazarse por conflicto de idempotencia.

---

# ResolutionLock

## Definición

Representa un bloqueo lógico o distribuido utilizado durante operaciones críticas.

---

## Campos conceptuales

```text
ResolutionLock
├── id
├── resolution_id
├── lock_type
├── lock_key
├── owner
├── token
├── acquired_at
├── expires_at
├── released_at
└── metadata
```

---

## Tipos de bloqueo

```text
planning
authorization
execution
compensation
subject_entity
```

---

## Requisitos

El sistema deberá:

- evitar ejecuciones simultáneas;
- permitir expiración controlada de locks abandonados;
- verificar el token antes de liberar;
- registrar adquisiciones y liberaciones;
- diferenciar bloqueo de resolución y bloqueo de entidad de dominio.

---

# Resoluciones equivalentes activas

El modelo deberá permitir detectar resoluciones activas que intenten resolver el mismo problema.

Ejemplo:

```text
resolution_type = service_order.add_additional_equipment
subject_type = service_order
subject_id = 418
status IN estados_activos
```

La política podrá:

- impedir una segunda resolución;
- vincularla a la existente;
- permitirla sólo si afecta un subconjunto distinto;
- exigir cancelación o cierre de la anterior.

No deberá asumirse que toda combinación de tipo y entidad es siempre única.

La regla dependerá de la definición concreta de cada resolución.

---

# Relaciones con usuarios

Las referencias a usuarios deberán conservar el identificador del usuario autenticado.

Cuando la identidad histórica sea relevante, también deberán conservarse snapshots mínimos como:

```text
user_id
display_name
role
area
```

Esto evita que cambios posteriores en el perfil eliminen la capacidad de interpretar una autorización histórica.

El snapshot no deberá sustituir al usuario como entidad oficial.

---

# Referencias a archivos y evidencia

Los archivos no deberán almacenarse directamente dentro de payloads JSON de gran tamaño.

El motor deberá conservar referencias a:

- documentos;
- fotografías;
- firmas;
- PDFs;
- archivos importados;
- evidencia de sincronización.

Ejemplo conceptual:

```text
ResolutionEvidenceReference
├── resolution_id
├── evidence_type
├── document_id
├── storage_reference
├── checksum
├── uploaded_by
└── uploaded_at
```

Esta entidad podrá integrarse con el sistema documental existente.

---

# Datos estructurados y JSON

El modelo podrá utilizar columnas JSON para almacenar:

- snapshots;
- payloads;
- hallazgos;
- advertencias;
- metadatos;
- entradas y salidas de pasos;
- diferencias de revalidación.

Sin embargo, no deberá utilizar JSON para ocultar información que requiera:

- integridad referencial;
- filtros frecuentes;
- restricciones únicas;
- relaciones estables;
- autorización;
- control de estado;
- auditoría individual.

---

## Debe modelarse de forma estructurada

Como mínimo:

- resolución;
- planes;
- pasos;
- autorizaciones;
- decisiones;
- ejecuciones;
- ejecuciones de pasos;
- eventos de auditoría;
- referencias de entidades;
- idempotencia;
- relaciones entre resoluciones.

---

## Puede almacenarse como JSON

- contexto normalizado;
- hallazgos;
- advertencias;
- payload de entrada;
- payload de salida;
- diferencias;
- metadatos variables;
- evidencia descriptiva.

---

# Tamaño y sensibilidad de payloads

Los snapshots y payloads podrán crecer significativamente.

La implementación deberá:

- evitar almacenar archivos binarios dentro de JSON;
- limitar el tamaño máximo;
- excluir secretos;
- excluir credenciales;
- excluir tokens de autenticación;
- ocultar datos sensibles no necesarios;
- utilizar redacción o cifrado cuando corresponda;
- comprimir o externalizar evidencia pesada si es necesario.

---

# Integridad referencial

Las relaciones internas del motor deberán utilizar claves foráneas.

Ejemplos:

```text
ResolutionPlan.resolution_id
ResolutionPlanStep.plan_id
ResolutionSimulation.plan_id
ResolutionAuthorizationRequest.plan_id
ResolutionExecution.plan_id
ResolutionStepExecution.execution_id
ResolutionAuditEvent.resolution_id
```

Las referencias a entidades externas deberán seguir la estrategia de integración existente del ERP.

Cuando no sea viable una clave foránea entre módulos, deberá conservarse al menos:

```text
entity_type
entity_id
module
```

---

# Eliminación

## Regla general

Las resoluciones y su evidencia no deberán eliminarse físicamente durante la operación normal.

---

## Estados en lugar de eliminación

Cuando una resolución deje de ser válida deberá utilizarse:

```text
cancelled
rejected
superseded
no_action_required
```

No deberá eliminarse para ocultar su existencia.

---

## Excepciones

La eliminación física sólo podrá contemplarse para:

- datos creados por error técnico antes de formalizar la resolución;
- ambientes de desarrollo o pruebas;
- obligaciones legales de depuración;
- procesos de anonimización autorizados.

Toda eliminación deberá respetar la política institucional de conservación de datos.

---

# Índices recomendados

La implementación deberá evaluar al menos los siguientes índices:

```text
Resolution.public_id
Resolution.resolution_type
Resolution.status
Resolution.subject_type + Resolution.subject_id
Resolution.requested_by_user_id
Resolution.created_at
Resolution.correlation_id
Resolution.request_key
Resolution.parent_resolution_id
Resolution.superseded_by_resolution_id
```

También:

```text
ResolutionPlan.resolution_id + version
ResolutionPlan.status
ResolutionSimulation.plan_id
ResolutionAuthorizationRequest.status
ResolutionAuthorizationDecision.approver_user_id
ResolutionExecution.resolution_id + attempt_number
ResolutionExecution.execution_key
ResolutionStepExecution.step_execution_key
ResolutionAuditEvent.resolution_id + occurred_at
ResolutionIdempotencyRecord.scope + idempotency_key
ResolutionEntityReference.entity_type + entity_id
```

---

# Restricciones de unicidad recomendadas

```text
Resolution.public_id
Resolution.request_key, cuando aplique
ResolutionPlan(resolution_id, version)
ResolutionExecution(resolution_id, attempt_number)
ResolutionExecution.execution_key
ResolutionIdempotencyRecord(scope, idempotency_key)
ResolutionStepExecution.step_execution_key
```

Podrá existir una restricción para un único plan activo por resolución.

Ejemplo conceptual:

```text
UNIQUE resolution_id WHERE is_active = true
```

La sintaxis dependerá del motor de base de datos.

---

# Restricciones de consistencia

La capa de aplicación deberá garantizar como mínimo:

1. Una autorización sólo puede pertenecer a un plan de la misma resolución.
2. Una simulación sólo puede autorizar el plan que simuló.
3. Una ejecución sólo puede usar un plan autorizado y revalidado.
4. Una decisión de autorización no puede cambiar el plan.
5. Un plan invalidado no puede ejecutarse.
6. Una resolución completada no puede volver a ejecutarse.
7. Un paso no puede ejecutarse antes que sus dependencias.
8. Una ejecución parcial debe conservar todos sus resultados.
9. Una entidad creada debe vincularse con el paso que la produjo.
10. Toda transición de estado debe generar un evento de auditoría.
11. Todo cambio de plan debe invalidar las autorizaciones anteriores.
12. Toda revalidación debe compararse contra un contexto persistido.
13. Toda operación de dominio debe utilizar una clave de idempotencia.
14. Ningún snapshot histórico deberá sobrescribirse.
15. Ningún evento de auditoría deberá editarse.

---

# Concurrencia optimista

Las entidades mutables deberán incluir un campo de versión.

Ejemplo:

```text
version = version + 1
```

Toda actualización deberá comprobar la versión esperada.

Si la versión cambió, la operación deberá fallar con un conflicto de concurrencia y reconstruir el contexto cuando corresponda.

---

# Concurrencia pesimista

La ejecución podrá requerir bloqueos transaccionales sobre:

- la resolución;
- el plan activo;
- la entidad principal;
- secuencias propiedad de módulos de dominio.

El Motor de Resoluciones no deberá bloquear directamente secuencias de folios de otros módulos.

Dichos bloqueos pertenecen al servicio propietario.

---

# Transacciones

## Transacciones locales del motor

Las operaciones internas deberán ser atómicas cuando sea posible.

Ejemplo:

```text
crear decisión de autorización
+
actualizar solicitud
+
cambiar estado de resolución
+
registrar evento de auditoría
```

deberán confirmarse en una sola transacción local.

---

## Transacciones de dominio

Cada módulo propietario administrará su propia transacción.

El motor registrará el resultado después de recibir confirmación.

---

## Fallo entre dominio y motor

Existe un escenario crítico:

1. El módulo de dominio confirma una operación.
2. La comunicación se interrumpe.
3. El motor no alcanza a registrar el resultado.

La recuperación deberá basarse en:

- claves de idempotencia;
- consulta del resultado previo;
- referencias de transacción;
- reconciliación;
- reintentos seguros.

Nunca deberá asumirse que una falta de respuesta significa que la operación no ocurrió.

---

# Outbox e integración por eventos

Cuando la implementación utilice eventos, se recomienda un patrón Outbox.

La misma transacción que actualiza el estado del motor deberá registrar el evento pendiente de publicación.

Ejemplo:

```text
resolution.completed
```

La publicación externa podrá ocurrir después sin perder el evento.

El uso de eventos no reemplaza el modelo de auditoría.

---

# Sincronización offline

El modelo deberá soportar operaciones creadas fuera de línea.

Podrá existir una entidad adicional:

```text
OfflineResolutionRequest
├── id
├── offline_operation_uuid
├── device_id
├── actor_user_id
├── local_created_at
├── received_at
├── subject_type
├── subject_local_id
├── subject_server_id
├── resolution_type
├── payload
├── local_context_version
├── status
├── resolution_id
├── sync_attempts
└── last_error
```

---

## Restricción de unicidad

```text
offline_operation_uuid
```

deberá ser único globalmente.

---

## Estados conceptuales

```text
received
validated
resolution_created
applied
rejected
conflict
failed
```

---

## Identificadores provisionales

Las entidades capturadas offline podrán utilizar UUID locales.

Ejemplo:

```text
local_equipment_uuid
```

Al sincronizar, deberá conservarse un mapa:

```text
local_uuid → server_entity_id
```

Este mapa permitirá reconciliar referencias sin que la aplicación móvil genere folios institucionales.

---

# Retención histórica

Las resoluciones deberán conservarse durante el periodo definido por la política institucional, fiscal, documental y de calidad aplicable.

El sistema deberá permitir:

- consulta histórica;
- exportación de auditoría;
- trazabilidad por entidad;
- trazabilidad por usuario;
- trazabilidad por fecha;
- reconstrucción de decisiones.

---

# Modelo relacional conceptual

```text
Resolution
    1 ───── 1 ResolutionProblem

Resolution
    1 ───── N ResolutionContextSnapshot

Resolution
    1 ───── N ResolutionAnalysis

Resolution
    1 ───── N ResolutionStrategySelection

Resolution
    1 ───── N ResolutionPlan

ResolutionPlan
    1 ───── N ResolutionPlanStep

ResolutionPlan
    1 ───── N ResolutionSimulation

ResolutionPlan
    1 ───── N ResolutionAuthorizationRequest

ResolutionAuthorizationRequest
    1 ───── N ResolutionAuthorizationDecision

ResolutionPlan
    1 ───── N ResolutionRevalidation

Resolution
    1 ───── N ResolutionExecution

ResolutionExecution
    1 ───── N ResolutionStepExecution

ResolutionStepExecution
    1 ───── N ResolutionEntityReference

Resolution
    1 ───── 0..1 ResolutionResult

Resolution
    1 ───── N ResolutionAuditEvent

Resolution
    1 ───── N ResolutionIdempotencyRecord

Resolution
    1 ───── N ResolutionLock
```

---

# Ejemplo: equipos adicionales

## Resolución

```text
Resolution
resolution_type = service_order.add_additional_equipment
subject_type = service_order
subject_id = 418
status = pending_authorization
```

---

## Problema

```text
El técnico detectó 13 equipos adicionales no contemplados originalmente.
```

---

## Contexto inicial

```json
{
  "service_order": {
    "id": 418,
    "status": "in_progress"
  },
  "invoice": {
    "exists": true,
    "status": "draft"
  },
  "certificates": {
    "authenticated_count": 0
  },
  "additional_equipment": {
    "count": 13
  }
}
```

---

## Estrategia

```text
append_to_existing_service_order
```

---

## Plan v1

```text
1. Validar equipos adicionales.
2. Registrar equipos en el ETS existente.
3. Crear o redistribuir órdenes de trabajo.
4. Crear hojas de campo correspondientes.
5. Solicitar firma adicional cuando el alcance lo requiera.
```

---

## Cambio de contexto

Antes de ejecutar:

```text
invoice.status = issued
```

---

## Revalidación

```text
requires_new_plan
```

---

## Plan v2

```text
1. Crear cotización complementaria.
2. Crear ETS complementario.
3. Registrar los 13 equipos.
4. Crear órdenes de trabajo.
5. Crear hojas de campo.
6. Vincular el ETS complementario con el ETS original.
```

---

## Autorizaciones

La autorización del Plan v1 queda invalidada.

El Plan v2 requiere una nueva simulación y una nueva autorización.

---

## Ejecución

Los módulos propietarios devuelven:

```text
quotation_id = 901
quotation_folio = COT-2026-0901

service_order_id = 615
service_order_folio = ETS-2026-0145-C01
```

Estos folios son producidos por sus respectivos módulos.

El Motor de Resoluciones únicamente los registra como resultado.

---

# Modelo mínimo de implementación

La primera versión funcional del motor podrá comenzar con las siguientes tablas:

```text
resolutions
resolution_context_snapshots
resolution_analyses
resolution_strategy_selections
resolution_plans
resolution_plan_steps
resolution_simulations
resolution_authorization_requests
resolution_authorization_decisions
resolution_revalidations
resolution_executions
resolution_step_executions
resolution_entity_references
resolution_results
resolution_audit_events
resolution_idempotency_records
```

Los bloqueos podrán implementarse inicialmente mediante mecanismos de base de datos o infraestructura, sin requerir una tabla persistente, siempre que mantengan trazabilidad suficiente.

---

# Elementos que no deben simplificarse

Aunque la implementación inicial sea incremental, no deberán reducirse a simples campos booleanos los siguientes conceptos:

- autorización;
- simulación;
- ejecución;
- resultado;
- auditoría;
- versión del plan;
- revalidación.

Ejemplos incorrectos:

```text
resolution.approved = true
resolution.executed = true
resolution.simulated = true
```

Estos campos por sí solos no conservan suficiente evidencia.

---

# Migraciones

Toda implementación deberá incluir migraciones explícitas.

Las migraciones deberán:

- crear restricciones;
- crear índices;
- definir claves foráneas;
- respetar convenciones de nombres;
- permitir reversión segura cuando sea viable;
- evitar pérdida de información existente;
- documentar cualquier transformación de datos.

---

# Seeds y catálogos

Los tipos de resolución no deberán depender necesariamente de una tabla editable por usuarios.

La definición funcional deberá permanecer en código y en el `ResolutionRegistry`.

Podrán existir catálogos persistentes para:

- etiquetas;
- descripciones;
- visibilidad;
- estado habilitado;
- prioridad predeterminada;
- configuración de interfaz.

La existencia de una fila en catálogo no deberá ser suficiente para habilitar una resolución sin una implementación registrada.

---

# Protección de datos

Los snapshots, payloads y eventos deberán excluir:

- contraseñas;
- tokens JWT;
- claves de API;
- secretos del PAC;
- credenciales de servicios;
- datos técnicos innecesarios;
- archivos binarios completos.

Cuando exista información sensible necesaria para auditoría, deberá protegerse según las políticas de seguridad del ERP.

---

# Criterios de aceptación del modelo

El modelo de datos será considerado compatible con la arquitectura cuando permita:

1. reconstruir el ciclo completo de una resolución;
2. conservar múltiples versiones de contexto y plan;
3. vincular autorizaciones a planes exactos;
4. invalidar autorizaciones al cambiar el plan;
5. registrar cada intento de ejecución;
6. registrar cada paso individual;
7. recuperar resultados de operaciones idempotentes;
8. detectar concurrencia;
9. conservar entidades creadas y modificadas;
10. explicar cambios de contexto;
11. registrar ejecuciones parciales;
12. preservar auditoría inmutable;
13. rastrear resoluciones derivadas o sustitutas;
14. soportar solicitudes offline;
15. evitar que el motor genere folios de otros dominios;
16. impedir eliminación operativa de evidencia histórica.

---

# Declaración final

El modelo de datos del Motor de Resoluciones no deberá limitarse a representar estados.

Debe representar decisiones, versiones, evidencia, autorizaciones, intentos, resultados y relaciones.

Una resolución correctamente almacenada deberá poder comprenderse años después sin depender de recuerdos, conversaciones externas ni interpretación manual del código.

La persistencia del motor constituye la memoria institucional de las intervenciones extraordinarias realizadas dentro del ERP MYC.

Por esta razón, toda implementación deberá preservar su integridad, trazabilidad e inmutabilidad.