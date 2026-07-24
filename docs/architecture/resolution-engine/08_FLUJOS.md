# 08 · Flujos

# Flujos del Motor de Resoluciones

## Introducción

Este documento define los flujos operativos del Motor de Resoluciones.

Mientras la arquitectura describe cómo se organiza el subsistema y el modelo de datos describe qué información conserva, los flujos establecen cómo avanza una resolución desde su detección hasta su conclusión.

Los flujos aquí definidos deberán respetar en todo momento:

- la inmutabilidad histórica;
- la separación entre coordinación y dominio;
- la existencia de un plan formal;
- la simulación previa;
- la autorización explícita cuando corresponda;
- la revalidación antes de ejecutar;
- la idempotencia;
- la auditoría completa.

---

# Flujo general

Toda resolución deberá seguir, conceptualmente, el siguiente flujo:

```text
Detección del problema
        ↓
Creación de resolución
        ↓
Construcción de contexto
        ↓
Análisis
        ↓
Selección de estrategia
        ↓
Construcción de plan
        ↓
Simulación
        ↓
Autorización
        ↓
Revalidación
        ↓
Ejecución
        ↓
Resultado
        ↓
Cierre y auditoría
```

No todas las resoluciones requerirán intervención humana en todas las etapas.

Sin embargo, ninguna resolución podrá omitir las validaciones de consistencia correspondientes.

---

# Estados del flujo principal

```text
draft
  ↓
context_ready
  ↓
analyzed
  ↓
plan_ready
  ↓
simulated
  ↓
pending_authorization
  ↓
authorized
  ↓
revalidating
  ↓
ready_for_execution
  ↓
executing
  ↓
completed
```

Estados alternativos:

```text
blocked
failed
partially_completed
rejected
cancelled
superseded
no_action_required
```

---

# Flujo 1 · Creación de una resolución

## Objetivo

Registrar formalmente un problema extraordinario dentro del motor.

---

## Entradas

La creación puede originarse desde:

- un usuario;
- un módulo del ERP;
- una aplicación móvil;
- un proceso de sincronización;
- un proceso automático;
- una intervención administrativa.

---

## Secuencia

```text
Solicitante
    ↓
ResolutionEngine.create_resolution()
    ↓
Validación inicial
    ↓
Verificación de idempotencia
    ↓
Detección de resolución equivalente activa
    ↓
Creación de Resolution
    ↓
Creación de ResolutionProblem
    ↓
Registro de evento de auditoría
```

---

## Validaciones mínimas

El motor deberá validar:

- tipo de resolución registrado;
- existencia de la entidad principal;
- identidad del solicitante;
- permiso para solicitar;
- datos mínimos obligatorios;
- clave de idempotencia;
- ausencia de duplicidad incompatible.

---

## Posibles resultados

### Resolución creada

```text
status = draft
```

### Resolución equivalente encontrada

El motor podrá:

- devolver la resolución existente;
- vincular la nueva solicitud;
- rechazar la duplicidad;
- crear una resolución derivada, si la política lo permite.

### Solicitud inválida

No se crea resolución.

Debe registrarse un error estructurado, pero no necesariamente un evento de auditoría de resolución, porque la entidad aún no existe.

---

# Flujo 2 · Construcción de contexto

## Objetivo

Obtener la fotografía operativa necesaria para analizar el problema.

---

## Secuencia

```text
Resolution
    ↓
ResolutionContextBuilder
    ↓
Consulta de Fact Providers
    ↓
Normalización de hechos
    ↓
Construcción de snapshot
    ↓
Cálculo de context_hash
    ↓
Persistencia de contexto
    ↓
status = context_ready
```

---

## Reglas

El contexto deberá:

- incluir únicamente hechos relevantes;
- identificar entidades inmutables;
- registrar versiones de entidades;
- registrar datos faltantes;
- conservar referencias de origen;
- ser inmutable después de persistirse.

---

## Resultado

```text
ResolutionContextSnapshot
```

---

## Fallos posibles

### Información faltante

```text
status = blocked
```

o:

```text
analysis.status = requires_information
```

### Módulo no disponible

La resolución deberá quedar bloqueada o reintentable.

### Entidad principal inexistente

La resolución podrá concluir como:

```text
no_action_required
```

o fallar por integridad, según el caso.

---

# Flujo 3 · Análisis

## Objetivo

Determinar qué significa el problema dentro del contexto actual y si existe un camino válido de resolución.

---

## Secuencia

```text
ContextSnapshot
    ↓
ResolutionAnalyzer
    ↓
Evaluación de restricciones
    ↓
Detección de bloqueos
    ↓
Detección de entidades inmutables
    ↓
Identificación de estrategias disponibles
    ↓
Persistencia de ResolutionAnalysis
    ↓
status = analyzed
```

---

## Resultados posibles

### Resoluble

```text
is_resolvable = true
```

### Requiere información

```text
status = requires_information
```

### Bloqueado

```text
status = blocked
```

### No resoluble

La resolución puede pasar a:

```text
rejected
```

o:

```text
no_action_required
```

### Ya resuelto

Otra operación corrigió el problema antes del análisis.

La resolución debe cerrarse sin ejecutar acciones.

---

# Flujo 4 · Selección de estrategia

## Objetivo

Elegir el camino institucionalmente válido para resolver el problema.

---

## Selección automática

Se utiliza cuando sólo existe una estrategia válida.

```text
Analysis
    ↓
StrategySelector
    ↓
Estrategia única aplicable
    ↓
Registro de selección
```

---

## Selección asistida por usuario

Se utiliza cuando existen varias estrategias válidas.

```text
Analysis
    ↓
Motor presenta alternativas
    ↓
Usuario autorizado selecciona
    ↓
Motor valida selección
    ↓
Registro de estrategia
```

---

## Reglas

La selección deberá conservar:

- estrategia elegida;
- alternativas consideradas;
- motivos de descarte;
- versión de estrategia;
- usuario o política que decidió;
- justificación.

---

## Resultado

```text
ResolutionStrategySelection
```

---

# Flujo 5 · Construcción del plan

## Objetivo

Traducir la estrategia en una secuencia concreta de operaciones.

---

## Secuencia

```text
StrategySelection
    ↓
ResolutionPlanBuilder
    ↓
Definición de pasos
    ↓
Definición de dependencias
    ↓
Asignación de módulos propietarios
    ↓
Definición de precondiciones
    ↓
Definición de compensaciones
    ↓
Cálculo de plan_hash
    ↓
Persistencia de Plan y Steps
    ↓
status = plan_ready
```

---

## Reglas

Cada plan deberá:

- pertenecer a una resolución;
- referenciar un contexto;
- referenciar una estrategia;
- tener versión;
- ser serializable;
- indicar impactos;
- declarar riesgos;
- definir autorizaciones requeridas;
- identificar puntos de no retorno.

---

## Modificación de plan

Mientras esté en borrador, podrá ajustarse.

Después de simularse o autorizarse:

```text
Plan v1
    ↓
invalidado
    ↓
Plan v2
```

Nunca deberá editarse silenciosamente un plan ya presentado.

---

# Flujo 6 · Simulación

## Objetivo

Determinar las consecuencias esperadas del plan sin modificar el dominio.

---

## Secuencia

```text
ResolutionPlan
    ↓
ResolutionSimulator
    ↓
Validación de precondiciones
    ↓
Evaluación de pasos
    ↓
Cálculo de impactos
    ↓
Detección de bloqueos
    ↓
Identificación de autorizaciones
    ↓
Persistencia de simulación
    ↓
status = simulated
```

---

## La simulación debe responder

- qué acciones se ejecutarán;
- qué entidades se crearán;
- qué entidades se modificarán;
- qué entidades permanecerán intactas;
- qué riesgos existen;
- qué pasos son irreversibles;
- qué autorizaciones se necesitan.

---

## Restricciones

La simulación nunca deberá:

- crear entidades;
- generar folios oficiales;
- reservar secuencias sin contrato explícito;
- cambiar estados;
- enviar notificaciones definitivas;
- ejecutar integraciones externas con efectos reales.

---

## Resultados posibles

```text
valid
valid_with_warnings
invalid
blocked
expired
```

---

# Flujo 7 · Solicitud de autorización

## Objetivo

Presentar un plan exacto para decisión institucional.

---

## Secuencia

```text
Simulation válida
    ↓
ResolutionAuthorizationService
    ↓
Aplicación de AuthorizationPolicy
    ↓
Identificación de autorizadores
    ↓
Creación de AuthorizationRequest
    ↓
Notificación a autorizadores
    ↓
status = pending_authorization
```

---

## Contenido mínimo presentado al autorizador

- problema;
- contexto relevante;
- estrategia;
- versión del plan;
- pasos;
- impactos;
- riesgos;
- advertencias;
- puntos de no retorno;
- entidades preservadas;
- consecuencias de rechazo.

---

## Regla fundamental

La autorización pertenece a:

```text
plan_id + plan_version + plan_hash
```

No pertenece únicamente a la resolución.

---

# Flujo 8 · Decisión de autorización

## Aprobación

```text
Autorizador
    ↓
Validación de identidad y permisos
    ↓
Validación de vigencia
    ↓
Validación de plan_hash
    ↓
Registro de decisión
    ↓
Evaluación de política
    ↓
status = authorized
```

---

## Aprobación parcial

Cuando se requieren múltiples autorizaciones:

```text
pending
    ↓
partially_approved
    ↓
approved
```

---

## Rechazo

```text
Autorizador rechaza
    ↓
Registro de motivo
    ↓
AuthorizationRequest = rejected
    ↓
Resolution = rejected
```

La política podrá permitir reconstrucción del plan, pero deberá generarse una nueva versión y una nueva solicitud.

---

## Expiración

```text
AuthorizationRequest = expired
```

La resolución deberá volver a:

- simulación;
- solicitud de autorización;
- o reconstrucción de contexto, según la política.

---

## Revocación

Sólo podrá ocurrir antes de iniciar la ejecución.

Debe quedar como un nuevo registro de decisión o evento.

Nunca deberá eliminarse la aprobación original.

---

# Flujo 9 · Revalidación

## Objetivo

Verificar que el plan autorizado siga siendo válido inmediatamente antes de ejecutarse.

---

## Secuencia

```text
Resolution autorizada
    ↓
status = revalidating
    ↓
Reconstrucción de contexto actual
    ↓
Nuevo ContextSnapshot
    ↓
Comparación con contexto autorizado
    ↓
Clasificación de cambios
    ↓
Persistencia de Revalidation
```

---

## Clasificación de cambios

### Cambio irrelevante

Ejemplo:

```text
Cambio de teléfono del cliente.
```

Resultado:

```text
valid
```

### Cambio tolerable

Ejemplo:

```text
Cambio de usuario asignado sin alterar permisos ni alcance.
```

Resultado:

```text
valid_with_warnings
```

### Cambio invalidante

Ejemplo:

```text
Factura en borrador → factura emitida.
```

Resultado:

```text
requires_new_plan
```

### Problema ya resuelto

Resultado:

```text
no_longer_resolvable
```

### Bloqueo temporal

Resultado:

```text
blocked
```

---

## Flujo cuando se requiere nuevo plan

```text
Plan autorizado
    ↓
Revalidación inválida
    ↓
Plan marcado como invalidado
    ↓
Autorizaciones invalidadas
    ↓
Nuevo análisis
    ↓
Nueva estrategia, si corresponde
    ↓
Plan v2
    ↓
Nueva simulación
    ↓
Nueva autorización
```

---

# Flujo 10 · Ejecución

## Objetivo

Coordinar las operaciones reales del plan autorizado y revalidado.

---

## Secuencia general

```text
Plan autorizado y válido
    ↓
ResolutionConcurrencyService
    ↓
Adquisición de lock
    ↓
Verificación de idempotencia
    ↓
Creación de ResolutionExecution
    ↓
status = executing
    ↓
Ejecución ordenada de pasos
    ↓
Registro de resultados
    ↓
Construcción de ResolutionResult
    ↓
Liberación de lock
    ↓
status = completed
```

---

# Flujo de ejecución de un paso

```text
ResolutionExecutor
    ↓
Selecciona ResolutionPlanStep
    ↓
Verifica dependencias
    ↓
Verifica precondiciones
    ↓
Genera step_execution_key
    ↓
Consulta idempotencia
    ↓
Invoca Domain Gateway
    ↓
Módulo propietario valida
    ↓
Módulo propietario ejecuta
    ↓
Módulo propietario confirma transacción
    ↓
Devuelve DomainOperationResult
    ↓
Motor registra StepExecution
    ↓
Motor registra EntityReferences
    ↓
Motor registra auditoría
```

---

## Regla

El paso no se considera completado porque el motor lo intentó.

Se considera completado únicamente cuando el módulo propietario devuelve un resultado verificable o cuando un reintento recupera evidencia de que la operación ya ocurrió.

---

# Flujo 11 · Ejecución exitosa

```text
Paso 1 completado
    ↓
Paso 2 completado
    ↓
Paso 3 completado
    ↓
Todos los pasos completados
    ↓
Captura de contexto final
    ↓
ResolutionResult = success
    ↓
Resolution = completed
    ↓
Evento resolution.completed
```

---

## Resultado mínimo

- pasos ejecutados;
- entidades creadas;
- entidades modificadas;
- entidades preservadas;
- folios devueltos por módulos;
- advertencias;
- acciones posteriores.

---

# Flujo 12 · Fallo reintentable

## Ejemplos

- timeout;
- servicio temporalmente no disponible;
- bloqueo transitorio;
- error de red;
- respuesta incierta de un módulo.

---

## Secuencia

```text
Paso falla
    ↓
Clasificación del error
    ↓
retryable = true
    ↓
Registro del intento
    ↓
Liberación o conservación controlada del lock
    ↓
Programación de reintento
```

---

## Antes del reintento

El motor deberá:

- consultar idempotencia;
- verificar si la operación ya ocurrió;
- revalidar precondiciones relevantes;
- incrementar el número de intento;
- evitar duplicidad.

---

## Regla crítica

Una falta de respuesta no significa que el módulo no ejecutó la operación.

El motor deberá reconciliar antes de repetir.

---

# Flujo 13 · Fallo no reintentable

## Ejemplos

- regla de dominio violada;
- plan inválido;
- autorización insuficiente;
- entidad inmutable;
- cambio de contexto irreversible;
- operación prohibida.

---

## Secuencia

```text
Paso falla
    ↓
retryable = false
    ↓
Registro del error
    ↓
Evaluación de compensación
    ↓
Resolution = failed o partially_completed
```

---

# Flujo 14 · Ejecución parcial

## Definición

Ocurre cuando algunos pasos se completaron y un paso posterior no puede continuar.

---

## Ejemplo

```text
1. Cotización complementaria creada
2. ETS complementario creado
3. Registro de equipos falla
```

---

## Secuencia

```text
Pasos previos confirmados
    ↓
Paso actual falla
    ↓
Motor identifica efectos persistentes
    ↓
Evalúa compensaciones
    ↓
Conserva entidades creadas
    ↓
ResolutionResult = partial_success
    ↓
Resolution = partially_completed
```

---

## Reglas

El sistema no deberá:

- ocultar entidades ya creadas;
- marcar la resolución como totalmente fallida sin explicar efectos;
- eliminar evidencia;
- repetir pasos completados sin idempotencia;
- asumir rollback global.

---

# Flujo 15 · Compensación

## Objetivo

Reducir o revertir efectos de pasos previos cuando exista una operación compensatoria válida.

---

## Secuencia

```text
Fallo detectado
    ↓
Evaluación de pasos ejecutados
    ↓
Identificación de pasos compensables
    ↓
Autorización adicional, si corresponde
    ↓
status = compensating
    ↓
Ejecución inversa controlada
    ↓
Registro de compensaciones
    ↓
Resultado final
```

---

## Ejemplo compensable

```text
Crear borrador temporal
    ↓
Falla paso posterior
    ↓
Cancelar borrador temporal
```

---

## Ejemplo no compensable

```text
Factura timbrada
```

No puede tratarse como un simple rollback.

Se deberá iniciar una nueva resolución fiscal, por ejemplo cancelación o sustitución.

---

## Resultado posible

```text
compensated
compensation_failed
partially_compensated
```

---

# Flujo 16 · Cancelación

## Cancelación antes de autorización

Puede realizarse si la política lo permite.

```text
draft / analyzed / plan_ready / simulated
    ↓
cancelled
```

---

## Cancelación después de autorización

Requiere:

- verificar que no exista ejecución iniciada;
- invalidar la autorización;
- registrar motivo;
- notificar a los involucrados.

---

## Cancelación durante ejecución

No deberá tratarse como una cancelación simple.

Debe evaluarse como:

- interrupción controlada;
- ejecución parcial;
- compensación;
- bloqueo.

---

## Regla

Una resolución con efectos persistentes no puede desaparecer mediante cancelación.

Debe conservar el resultado de lo ya ejecutado.

---

# Flujo 17 · Sustitución de resolución

## Objetivo

Reemplazar una resolución por otra cuando el caso original cambió de naturaleza.

---

## Ejemplo

Una resolución de:

```text
Agregar equipos al ETS existente
```

se vuelve inválida porque el ETS fue cerrado.

Se crea una nueva resolución:

```text
Crear ETS complementario
```

---

## Secuencia

```text
Resolución A
    ↓
Cambio estructural del problema
    ↓
Resolución B creada
    ↓
A.superseded_by_resolution_id = B
    ↓
A.status = superseded
```

---

## Regla

La resolución anterior permanece íntegra.

No se transforma retroactivamente en la nueva.

---

# Flujo 18 · Resolución sin acción requerida

## Escenario

El problema dejó de existir antes de ejecutar.

Ejemplo:

- otro usuario corrigió el caso;
- la sincronización ya fue aplicada;
- la entidad fue cancelada legítimamente;
- el supuesto conflicto no existía.

---

## Secuencia

```text
Análisis o revalidación
    ↓
Problema inexistente
    ↓
ResolutionResult = no_action_required
    ↓
Resolution = no_action_required
```

---

## Requisito

Debe explicarse por qué no se ejecutó ninguna acción.

---

# Flujo 19 · Resolución bloqueada

## Definición

La resolución no puede continuar temporalmente, pero tampoco debe cerrarse.

---

## Causas

- módulo indisponible;
- dato requerido faltante;
- documento pendiente;
- conflicto de concurrencia;
- autorización externa pendiente;
- inconsistencia detectada;
- lock activo;
- dependencia no cumplida.

---

## Secuencia

```text
Etapa actual
    ↓
Bloqueo detectado
    ↓
status = blocked
    ↓
Registro de motivo
    ↓
Definición de condición de desbloqueo
```

---

## Desbloqueo

```text
Condición resuelta
    ↓
Reconstrucción de contexto
    ↓
Reanudación desde etapa válida
```

No deberá reanudarse automáticamente desde un punto obsoleto.

---

# Flujo 20 · Resolución iniciada por sincronización offline

## Objetivo

Procesar hechos capturados por un técnico sin conexión.

---

## Secuencia

```text
Aplicación móvil
    ↓
Registra operación local con UUID
    ↓
Sincronización con servidor
    ↓
Validación de offline_operation_uuid
    ↓
Verificación de idempotencia
    ↓
Mapeo de entidades locales
    ↓
Construcción de problema
    ↓
Creación de Resolution
    ↓
Construcción de contexto actual del servidor
    ↓
Análisis
    ↓
Plan
    ↓
Autorización, si corresponde
    ↓
Ejecución
    ↓
Mapeo local_uuid → server_id
    ↓
Respuesta al dispositivo
```

---

## Regla

El servidor no deberá confiar en el estado local como contexto vigente.

La información offline es evidencia del hecho capturado, no una autorización para modificar el dominio.

---

# Flujo 21 · Equipos adicionales sin folio offline

## Escenario

El técnico detecta trece equipos adicionales durante un servicio sin conexión.

---

## Captura local

La aplicación guarda:

```text
local_equipment_uuid
catálogo seleccionado
marca
modelo
serie
identificación
tipo de trazabilidad
evidencia
fecha local
usuario
```

No genera:

- folio de certificado;
- folio de OT;
- folio ETS;
- orden de trabajo definitiva.

---

## Sincronización

```text
13 equipos provisionales
    ↓
Sync Service
    ↓
Resolution:
service_order.add_additional_equipment
    ↓
Contexto actual del ETS
```

---

## Estrategia posible A

ETS abierto y sin afectación documental irreversible:

```text
Registrar equipos en ETS existente
    ↓
Asignar OT
    ↓
Crear hojas
    ↓
Solicitar firma adicional, si corresponde
```

---

## Estrategia posible B

ETS cerrado o documentación inmutable:

```text
Crear cotización complementaria
    ↓
Crear ETS complementario
    ↓
Registrar equipos
    ↓
Crear OT
    ↓
Crear hojas
```

---

## Respuesta al dispositivo

```text
local_equipment_uuid → equipment_id
local_equipment_uuid → certificate_identity, cuando proceda
local_operation_uuid → resolution_id
```

---

# Flujo 22 · Autorización múltiple

## Ejemplo

Una resolución fiscal requiere aprobación de:

- Finanzas;
- Administrador.

---

## Secuencia

```text
AuthorizationRequest
    ↓
Finanzas aprueba
    ↓
status = partially_approved
    ↓
Administrador aprueba
    ↓
status = approved
    ↓
Resolution = authorized
```

---

## Rechazo de uno de los autorizadores

```text
Una decisión = rejected
    ↓
AuthorizationRequest = rejected
    ↓
Resolution = rejected
```

La política podrá variar, pero deberá estar definida explícitamente.

---

# Flujo 23 · Autorización secuencial

## Ejemplo

Primero debe aprobar Calidad y después Administración.

---

## Secuencia

```text
Etapa 1: Calidad
    ↓
Aprobada
    ↓
Etapa 2: Administración
    ↓
Aprobada
    ↓
Plan autorizado
```

Administración no deberá poder aprobar antes de Calidad si la política es secuencial.

---

# Flujo 24 · Cambio de plan después de autorización

## Escenario

El plan fue aprobado, pero se requiere agregar o modificar un paso.

---

## Secuencia

```text
Plan v1 autorizado
    ↓
Cambio requerido
    ↓
Plan v1 invalidado
    ↓
Autorizaciones v1 invalidadas
    ↓
Plan v2 creado
    ↓
Nueva simulación
    ↓
Nueva autorización
```

---

## Regla

Nunca deberá modificarse un plan autorizado conservando la aprobación anterior.

---

# Flujo 25 · Recuperación después de caída del sistema

## Escenario

El sistema se interrumpe durante la ejecución.

---

## Secuencia de recuperación

```text
Worker reinicia
    ↓
Busca ejecuciones running sin actividad
    ↓
Verifica lock
    ↓
Consulta StepExecutions
    ↓
Consulta idempotencia en módulos
    ↓
Reconstruye estado real
    ↓
Clasifica:
    ├── continuar
    ├── reintentar
    ├── marcar completado
    ├── bloquear
    └── compensar
```

---

## Regla

El sistema no deberá reiniciar toda la resolución desde el principio.

Debe continuar desde el último estado confirmado.

---

# Flujo 26 · Reconciliación de resultado incierto

## Escenario

El motor invoca una operación de dominio y pierde la conexión antes de recibir la respuesta.

---

## Secuencia

```text
Operación enviada
    ↓
Timeout
    ↓
Estado incierto
    ↓
Consulta por idempotency_key
    ↓
Módulo responde:
    ├── completed
    ├── not_found
    ├── running
    └── failed
```

---

## Resultado

### Completed

El motor recupera el resultado y marca el paso como completado.

### Not found

Puede reintentar de forma segura.

### Running

Espera o consulta nuevamente.

### Failed

Registra el error y aplica la política correspondiente.

---

# Flujo 27 · Cierre

## Objetivo

Consolidar el resultado y dejar la resolución en un estado terminal.

---

## Secuencia

```text
Ejecución concluida
    ↓
Captura de contexto final
    ↓
Construcción de ResolutionResult
    ↓
Registro de entidades relacionadas
    ↓
Registro de auditoría
    ↓
Emisión de eventos
    ↓
Notificaciones
    ↓
Estado terminal
```

---

## Estados terminales

```text
completed
rejected
cancelled
superseded
no_action_required
```

`partially_completed` y `failed` podrán ser terminales o recuperables según la política del tipo de resolución.

---

# Flujo de auditoría transversal

La auditoría deberá ejecutarse durante todo el ciclo.

```text
Crear resolución
    → audit

Capturar contexto
    → audit

Analizar
    → audit

Seleccionar estrategia
    → audit

Crear plan
    → audit

Simular
    → audit

Solicitar autorización
    → audit

Autorizar o rechazar
    → audit

Revalidar
    → audit

Ejecutar paso
    → audit

Compensar
    → audit

Cerrar
    → audit
```

La auditoría no deberá realizarse únicamente al final.

---

# Flujo de notificaciones

Las notificaciones deberán derivarse de eventos persistidos.

Ejemplo:

```text
resolution.authorization_requested
    ↓
Notification Service
    ↓
Correo / interfaz / alerta
```

La falla de notificación:

- no invalida la resolución;
- no duplica la solicitud;
- debe quedar registrada;
- puede reintentarse independientemente.

---

# Flujo de permisos

Cada operación deberá validar un permiso específico.

```text
Crear:
resolution.request.<type>

Consultar:
resolution.view.<scope>

Simular:
resolution.simulate.<type>

Autorizar:
resolution.authorize.<type>

Ejecutar:
resolution.execute.<type>

Cancelar:
resolution.cancel.<type>
```

Los nombres exactos podrán adaptarse al esquema vigente del ERP.

---

# Flujo de segregación de funciones

Ejemplo:

```text
Solicitante
    ↓
No puede autorizar
    ↓
Autorizador
    ↓
No ejecuta
    ↓
Ejecutor autorizado
```

La política podrá permitir coincidencias en resoluciones de bajo riesgo, pero deberá ser explícita.

---

# Flujo resumido de estados

```text
draft
  │
  ▼
context_ready
  │
  ▼
analyzed
  │
  ├─────────────► no_action_required
  │
  ├─────────────► blocked
  │
  └─────────────► rejected
  ▼
plan_ready
  │
  ▼
simulated
  │
  ├─────────────► blocked
  │
  └─────────────► invalidated
  ▼
pending_authorization
  │
  ├─────────────► rejected
  │
  ├─────────────► expired
  │
  └─────────────► cancelled
  ▼
authorized
  │
  ▼
revalidating
  │
  ├─────────────► plan_ready
  │
  ├─────────────► blocked
  │
  └─────────────► no_action_required
  ▼
ready_for_execution
  │
  ▼
executing
  │
  ├─────────────► completed
  │
  ├─────────────► partially_completed
  │
  ├─────────────► failed
  │
  └─────────────► compensating
```

---

# Reglas globales de flujo

1. Ninguna resolución puede ejecutarse sin plan.
2. Ningún plan puede autorizarse sin simulación válida.
3. Ninguna autorización puede reutilizarse para otro plan.
4. Ninguna ejecución puede iniciar sin revalidación.
5. Ningún paso puede ejecutarse antes que sus dependencias.
6. Ninguna operación de dominio puede ejecutarse sin idempotencia.
7. Ningún error parcial puede ocultar efectos ya producidos.
8. Ninguna compensación puede asumirse posible sin contrato explícito.
9. Ninguna resolución terminal puede reabrirse silenciosamente.
10. Ningún cambio de contexto invalidante puede ignorarse.
11. Ninguna operación offline genera autoridad institucional por sí sola.
12. Ningún folio oficial puede producirse durante la simulación.
13. Toda transición debe ser auditable.
14. Todo plan sustituido debe conservarse.
15. Toda autorización revocada o invalidada debe permanecer registrada.

---

# Criterios de aceptación

Los flujos serán considerados correctamente implementados cuando permitan:

- iniciar resoluciones desde distintos orígenes;
- detectar duplicidad;
- construir contexto inmutable;
- analizar viabilidad;
- seleccionar estrategias;
- versionar planes;
- simular sin efectos;
- autorizar planes exactos;
- revalidar antes de ejecutar;
- ejecutar pasos de forma idempotente;
- recuperar operaciones inciertas;
- gestionar fallos parciales;
- aplicar compensaciones explícitas;
- procesar solicitudes offline;
- conservar auditoría transversal;
- cerrar con resultados explicables.

---

# Declaración final

El flujo del Motor de Resoluciones no debe entenderse como una secuencia rígida de pantallas.

Es un ciclo institucional de decisión, autorización, ejecución y evidencia.

Cada etapa existe para reducir un riesgo específico:

- el contexto evita decidir a ciegas;
- el análisis evita aplicar soluciones incorrectas;
- la estrategia evita improvisación;
- el plan evita acciones ambiguas;
- la simulación evita consecuencias inesperadas;
- la autorización evita decisiones no institucionales;
- la revalidación evita ejecutar sobre información obsoleta;
- la idempotencia evita duplicidad;
- la auditoría evita pérdida de memoria.

Una resolución sólo estará completa cuando el sistema recupere la consistencia y pueda explicar, de principio a fin, cómo lo hizo.