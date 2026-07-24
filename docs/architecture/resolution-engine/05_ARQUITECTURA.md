# 05 · Arquitectura

# Arquitectura del Motor de Resoluciones

## Introducción

El Motor de Resoluciones es una capa transversal de orquestación dentro del ERP MYC.

Su función consiste en coordinar la recuperación de consistencia operativa cuando el flujo normal de uno o varios módulos ya no es suficiente para resolver una situación de negocio.

La arquitectura debe permitir que el motor:

- reciba problemas extraordinarios;
- recopile contexto desde diferentes módulos;
- seleccione una estrategia válida;
- construya un Plan de Resolución;
- simule sus consecuencias;
- solicite autorización;
- revalide el estado del sistema;
- coordine la ejecución;
- registre el resultado completo;
- preserve evidencia auditable.

El motor no reemplaza a los módulos del ERP.

Tampoco concentra las reglas de negocio de dichos módulos.

Su responsabilidad se limita a coordinar contratos de dominio de forma controlada, trazable e idempotente.

---

# Objetivos arquitectónicos

La arquitectura del Motor de Resoluciones deberá cumplir los siguientes objetivos:

1. Separar claramente la coordinación de la lógica de negocio.
2. Permitir agregar nuevos tipos de resolución sin modificar el núcleo.
3. Garantizar que ninguna resolución se ejecute sin un plan formal.
4. Permitir simulación previa sin producir efectos persistentes.
5. Detectar cambios de contexto antes de ejecutar.
6. Evitar la duplicidad de efectos.
7. Mantener trazabilidad completa de cada decisión.
8. Integrarse con módulos actuales y futuros mediante contratos estables.
9. Preparar el sistema para operación distribuida y sincronización diferida.
10. Evitar dependencias directas entre resoluciones concretas y detalles internos de otros módulos.

---

# Vista general

La arquitectura se divide en cuatro capas principales:

```text
┌─────────────────────────────────────────────────────────────┐
│                       CAPA DE ENTRADA                        │
│                                                             │
│  API · Interfaz · Eventos · Sincronización · Procesos internos
└──────────────────────────────┬──────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────┐
│                 NÚCLEO DEL MOTOR DE RESOLUCIONES             │
│                                                             │
│  Registro de resoluciones                                   │
│  Construcción de contexto                                   │
│  Selección de estrategia                                    │
│  Construcción del plan                                      │
│  Simulación                                                 │
│  Autorización                                               │
│  Revalidación                                               │
│  Orquestación                                               │
│  Control de estados                                         │
│  Idempotencia y concurrencia                                │
└──────────────────────────────┬──────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────┐
│                  CONTRATOS DE DOMINIO                        │
│                                                             │
│  Servicios · Cotizaciones · Equipos · OT · Hojas de campo  │
│  Calidad · Certificados · Facturación · Pagos · Usuarios   │
└──────────────────────────────┬──────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────┐
│                 PERSISTENCIA Y AUDITORÍA                     │
│                                                             │
│  Resoluciones · Planes · Simulaciones · Autorizaciones     │
│  Ejecuciones · Pasos · Resultados · Eventos · Snapshots    │
└─────────────────────────────────────────────────────────────┘
```

---

# Capa de entrada

## Responsabilidad

La capa de entrada recibe solicitudes para iniciar, consultar, autorizar, cancelar o ejecutar una resolución.

Puede ser utilizada por:

- la interfaz administrativa del ERP;
- la futura aplicación móvil de técnicos;
- procesos automáticos internos;
- mecanismos de sincronización offline;
- eventos emitidos por otros módulos;
- tareas administrativas autorizadas.

La capa de entrada no contiene lógica de resolución.

Únicamente valida:

- identidad del solicitante;
- formato de la solicitud;
- permiso para iniciar el proceso;
- existencia de la entidad principal;
- presencia de los datos mínimos requeridos.

Después delega la operación al núcleo del motor.

---

## Formas de entrada

La arquitectura deberá permitir las siguientes formas de activación:

### Solicitud explícita de usuario

Un usuario solicita una resolución desde la interfaz.

Ejemplo:

```text
Solicitar incorporación de equipos adicionales
```

---

### Detección por un módulo

Un módulo detecta que no puede continuar mediante el flujo normal.

Ejemplo:

```text
Facturación detecta que existe una modificación sobre una factura timbrada.
```

El módulo no ejecuta la solución.

Solicita al Motor de Resoluciones que analice el problema.

---

### Evento de sincronización

Una aplicación remota sincroniza cambios realizados mientras estuvo offline.

Ejemplo:

```text
Un técnico registró equipos adicionales sin folios oficiales.
```

El sincronizador genera un problema de resolución y entrega el contexto provisional disponible.

---

### Proceso automático

Un proceso interno detecta una inconsistencia operativa.

Ejemplo:

```text
Existe una entidad huérfana o una relación incompleta después de una operación fallida.
```

Este tipo de detección podrá generar una resolución pendiente de revisión, pero no deberá ejecutar automáticamente cambios institucionales salvo que una política explícita lo permita.

---

# Entidad central: Resolution

## Definición

`Resolution` representa la instancia completa de un proceso de resolución.

Es la entidad principal del motor.

Agrupa todo el ciclo de vida:

- problema;
- contexto;
- estrategia;
- plan;
- simulación;
- autorización;
- revalidación;
- ejecución;
- resultado;
- auditoría.

Toda acción ejecutada por el motor deberá estar vinculada a un `resolution_id`.

---

## Responsabilidades

La entidad `Resolution` deberá conservar:

- identidad única;
- tipo de resolución;
- entidad o proceso afectado;
- origen de la solicitud;
- solicitante;
- estado actual;
- prioridad;
- contexto inicial;
- estrategia seleccionada;
- versión activa del plan;
- resultado final;
- marcas temporales;
- relación con resoluciones anteriores o derivadas;
- metadatos de trazabilidad.

---

## Regla fundamental

Una resolución no debe confundirse con un plan.

La resolución representa el caso completo.

El plan representa una versión concreta del camino propuesto para resolverlo.

Una misma resolución podrá tener varias versiones de plan a lo largo de su ciclo de vida, pero únicamente una versión podrá encontrarse activa para autorización o ejecución.

---

# Núcleo del motor

El núcleo contiene la infraestructura común que administra todas las resoluciones.

No contiene reglas específicas de un caso concreto.

Sus componentes principales son:

```text
ResolutionEngine
├── ResolutionRegistry
├── ResolutionLifecycleService
├── ResolutionContextBuilder
├── ResolutionAnalyzer
├── ResolutionStrategySelector
├── ResolutionPlanBuilder
├── ResolutionSimulator
├── ResolutionAuthorizationService
├── ResolutionRevalidator
├── ResolutionExecutor
├── ResolutionStateMachine
├── ResolutionIdempotencyService
├── ResolutionConcurrencyService
└── ResolutionAuditService
```

---

# ResolutionEngine

## Definición

`ResolutionEngine` es la fachada principal del subsistema.

Expone las operaciones necesarias para controlar el ciclo de vida de una resolución.

No debe implementar directamente las reglas de cada resolución.

Delegará las responsabilidades a los componentes especializados.

---

## Operaciones conceptuales

```text
create_resolution()
build_context()
analyze_resolution()
build_plan()
simulate_plan()
request_authorization()
authorize_resolution()
reject_resolution()
revalidate_resolution()
execute_resolution()
cancel_resolution()
get_resolution()
list_resolution_history()
```

Los nombres concretos podrán variar según la implementación, pero las responsabilidades deberán mantenerse separadas.

---

## Restricción

`ResolutionEngine` no deberá:

- acceder directamente a tablas de otros módulos;
- crear folios;
- crear certificados;
- crear órdenes de trabajo;
- emitir facturas;
- modificar entidades de dominio mediante SQL;
- contener condiciones específicas de cada tipo de resolución.

---

# ResolutionRegistry

## Definición

El registro de resoluciones permite asociar un tipo de problema con sus componentes especializados.

Cada resolución deberá registrarse mediante una clave única y estable.

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

---

## Responsabilidad

El registro deberá localizar los componentes correspondientes:

- proveedor de contexto;
- analizador;
- selector de estrategia;
- constructor de plan;
- simulador;
- revalidador;
- ejecutor;
- política de autorización;
- política de permisos.

---

## Ejemplo conceptual

```text
ResolutionRegistry
    └── service_order.add_additional_equipment
            ├── ContextProvider
            ├── Analyzer
            ├── StrategySelector
            ├── PlanBuilder
            ├── Simulator
            ├── Revalidator
            ├── Executor
            └── AuthorizationPolicy
```

---

## Principio de extensión

Agregar un nuevo tipo de resolución deberá requerir:

1. crear sus componentes especializados;
2. registrarlos;
3. agregar sus pruebas;
4. documentar su contrato.

No deberá requerir modificar la lógica central del motor.

---

# ResolutionLifecycleService

## Definición

Administra el ciclo de vida de una resolución.

Es responsable de coordinar las transiciones de estado y verificar que cada operación se realice en el momento correcto.

---

## Responsabilidades

- crear la resolución;
- validar la transición solicitada;
- asignar el estado correspondiente;
- impedir transiciones inválidas;
- registrar las fechas de cada etapa;
- aplicar reglas de cancelación;
- impedir ejecución prematura;
- impedir modificaciones después del cierre.

---

## Restricción

No decide la estrategia ni ejecuta acciones de dominio.

Únicamente administra el ciclo de vida de la entidad `Resolution`.

---

# ResolutionContextBuilder

## Definición

Construye el contexto requerido para analizar una resolución.

Obtiene información desde los módulos propietarios mediante proveedores de hechos.

---

## Responsabilidades

- identificar qué información requiere cada resolución;
- consultar los contratos de dominio correspondientes;
- normalizar los datos;
- construir un snapshot;
- registrar la versión del contexto;
- calcular una huella de consistencia;
- evitar dependencias directas con modelos internos de otros módulos.

---

## Snapshot de contexto

El contexto deberá almacenarse como evidencia del estado observado.

Este snapshot no sustituye a la información viva del dominio.

Su propósito es permitir responder posteriormente:

```text
¿Qué información utilizó el motor para construir este plan?
```

---

## Huella de contexto

Cada snapshot deberá incluir una huella verificable, por ejemplo:

```text
context_hash
context_version
captured_at
```

La implementación podrá utilizar hashes, versiones optimistas, fechas de actualización o identificadores de revisión.

El objetivo es detectar si la información relevante cambió antes de la ejecución.

---

# Fact Providers

## Definición

Los `Fact Providers` son adaptadores de lectura que permiten al motor obtener hechos desde los módulos del ERP.

No deberán modificar información.

---

## Ejemplos

```text
ServiceOrderFactProvider
QuotationFactProvider
EquipmentFactProvider
WorkOrderFactProvider
FieldSheetFactProvider
CertificateFactProvider
InvoiceFactProvider
PaymentFactProvider
UserFactProvider
AuthorizationFactProvider
```

---

## Responsabilidades

Cada proveedor deberá:

- consultar información del módulo propietario;
- devolver una representación estable;
- ocultar detalles internos de persistencia;
- evitar que el motor dependa de modelos ORM ajenos;
- informar versiones o marcas de actualización;
- manejar ausencia o indisponibilidad de información.

---

## Restricción

El motor no deberá importar directamente repositorios, tablas o modelos de persistencia de otros módulos cuando exista un contrato de dominio disponible.

---

# ResolutionAnalyzer

## Definición

Analiza el problema y el contexto para determinar si existe una resolución válida.

---

## Responsabilidades

- validar que el problema corresponde al tipo registrado;
- detectar restricciones;
- identificar bloqueos;
- reconocer condiciones de inmutabilidad;
- determinar si el flujo normal todavía puede resolver el caso;
- producir hallazgos explicables;
- informar si la resolución es viable, inviable o requiere información adicional.

---

## Resultado conceptual

```text
ResolutionAnalysis
├── is_resolvable
├── findings
├── constraints
├── warnings
├── missing_information
├── immutable_entities
└── available_strategies
```

---

## Restricción

El analizador no ejecuta acciones.

Tampoco selecciona necesariamente la estrategia final si existen varias posibilidades válidas.

---

# ResolutionStrategySelector

## Definición

Selecciona la estrategia aplicable a partir del análisis y el contexto.

---

## Características

La selección deberá ser:

- determinista;
- explicable;
- repetible;
- auditable;
- basada en condiciones explícitas.

---

## Ejemplo

Problema:

```text
Agregar equipos adicionales.
```

Contexto A:

```text
ETS abierto.
Sin factura emitida.
Sin certificados autenticados.
```

Estrategia:

```text
Agregar equipos al ETS existente.
```

Contexto B:

```text
ETS cerrado.
Factura emitida.
Certificados autenticados.
```

Estrategia:

```text
Crear cotización complementaria y ETS complementario.
```

---

## Selección automática y selección humana

La arquitectura podrá permitir dos modalidades:

### Estrategia determinada

El contexto permite una única estrategia válida.

El motor la selecciona automáticamente.

### Estrategias alternativas

Existen varias estrategias institucionalmente válidas.

El motor presenta las alternativas autorizadas para que un usuario competente seleccione una.

En ambos casos, la estrategia elegida deberá quedar registrada con su justificación.

---

# ResolutionPlanBuilder

## Definición

Transforma la estrategia en un Plan de Resolución concreto.

---

## Responsabilidades

- definir los pasos requeridos;
- establecer su orden;
- declarar dependencias;
- identificar el módulo propietario de cada acción;
- describir entradas y salidas esperadas;
- asignar condiciones previas;
- definir efectos esperados;
- definir operaciones compensatorias cuando sean posibles;
- indicar puntos de no retorno;
- producir una versión serializable y auditable del plan.

---

## Estructura conceptual

```text
ResolutionPlan
├── plan_id
├── resolution_id
├── version
├── strategy_key
├── status
├── created_at
├── created_by
├── context_hash
├── summary
├── expected_impact
├── warnings
├── authorization_requirements
└── steps[]
```

---

## Regla de versión

Un plan autorizado no deberá modificarse.

Si el contexto cambia o la estrategia debe ajustarse, deberá generarse una nueva versión del plan.

Ejemplo:

```text
Plan v1 → simulado → autorizado
Cambio de contexto detectado
Plan v1 → invalidado
Plan v2 → construido → simulado → requiere nueva autorización
```

---

# ResolutionStep

## Definición

Representa una operación individual y declarativa dentro de un plan.

---

## Estructura conceptual

```text
ResolutionStep
├── step_id
├── sequence
├── operation_key
├── owner_module
├── description
├── input
├── expected_output
├── preconditions
├── dependencies
├── criticality
├── retry_policy
├── compensation_policy
└── execution_status
```

---

## Características

Cada paso deberá:

- tener una única responsabilidad;
- declarar quién lo ejecuta;
- evitar ambigüedad;
- poder auditarse individualmente;
- registrar su entrada;
- registrar su salida;
- registrar sus errores;
- ser idempotente cuando sea técnicamente posible.

---

## Ejemplo

```text
Paso 1
Operación: quotation.create_complementary
Propietario: QuotationService

Paso 2
Operación: service_order.create_complementary
Propietario: ServiceOrderService
Dependencia: Paso 1

Paso 3
Operación: equipment.register_batch
Propietario: EquipmentService
Dependencia: Paso 2

Paso 4
Operación: work_order.assign_equipment
Propietario: WorkOrderService
Dependencia: Paso 3
```

---

# ResolutionSimulator

## Definición

Evalúa el plan sin producir cambios persistentes en el dominio.

---

## Responsabilidades

- validar precondiciones;
- comprobar disponibilidad de contratos;
- identificar impactos;
- anticipar bloqueos;
- estimar entidades que deberán crearse;
- verificar dependencias;
- calcular requisitos de autorización;
- producir un resumen comprensible para el usuario.

---

## Restricciones

La simulación no deberá:

- generar folios oficiales;
- reservar numeraciones, salvo que el módulo propietario implemente explícitamente una reserva segura;
- crear documentos;
- alterar estados;
- escribir en tablas de dominio;
- provocar efectos externos;
- enviar notificaciones definitivas.

---

## Simulación y folios

La simulación podrá mostrar:

```text
Se creará un ETS complementario.
Se generarán dos órdenes de trabajo.
Se registrarán trece equipos.
Se crearán trece hojas de campo.
```

No deberá inventar:

```text
ETS-2026-0145-C01
OT-2026-0321
MYCA0720260001
```

Los identificadores oficiales únicamente podrán producirse por sus módulos propietarios durante una operación válida.

---

## Resultado conceptual

```text
ResolutionSimulation
├── simulation_id
├── plan_id
├── is_valid
├── expected_actions
├── expected_creations
├── expected_changes
├── preserved_entities
├── warnings
├── blockers
├── required_authorizations
├── simulated_at
└── context_hash
```

---

# ResolutionAuthorizationService

## Definición

Administra la autorización institucional de los planes.

---

## Principio

La autorización se concede sobre una versión exacta del plan.

No se autoriza de manera genérica:

```text
Agregar equipos.
```

Se autoriza:

```text
El Plan v2 de la resolución RES-XXXX, con estos pasos, impactos y advertencias.
```

---

## Responsabilidades

- identificar autorizadores válidos;
- validar permisos;
- verificar segregación de funciones;
- registrar decisión;
- conservar comentarios;
- registrar fecha y usuario;
- impedir autoautorización cuando la política lo prohíba;
- invalidar autorizaciones cuando el plan cambia;
- administrar autorizaciones múltiples o secuenciales.

---

## Políticas posibles

```text
Sin autorización adicional
Una autorización
Autorización por rol
Autorización múltiple
Autorización secuencial
Autorización de área específica
Autorización de administrador
```

---

## Restricción

La autorización no deberá almacenarse únicamente como un campo booleano.

Debe existir como evidencia individual con identidad, fecha, alcance y decisión.

---

# ResolutionRevalidator

## Definición

Verifica que el plan autorizado siga siendo válido inmediatamente antes de su ejecución.

---

## Responsabilidades

- reconstruir los hechos relevantes;
- comparar el contexto actual con el contexto autorizado;
- identificar cambios significativos;
- distinguir cambios tolerables de cambios invalidantes;
- confirmar que las precondiciones continúan vigentes;
- decidir si el plan puede ejecutarse;
- solicitar reconstrucción del plan cuando corresponda.

---

## Resultados posibles

```text
VALID
```

El plan continúa siendo aplicable.

```text
VALID_WITH_WARNINGS
```

Existen cambios que no alteran la estrategia ni los efectos autorizados.

```text
REQUIRES_NEW_PLAN
```

El contexto cambió y debe generarse una nueva versión.

```text
NO_LONGER_RESOLVABLE
```

El problema dejó de existir o ya fue resuelto por otro proceso.

```text
BLOCKED
```

Existe una condición temporal que impide ejecutar.

---

## Ejemplo

Al autorizar:

```text
La factura estaba en borrador.
```

Antes de ejecutar:

```text
La factura ya fue timbrada.
```

El plan original no puede ejecutarse.

El revalidador deberá detener el proceso y ordenar la construcción de una nueva estrategia compatible con la inmutabilidad fiscal.

---

# ResolutionExecutor

## Definición

Coordina la ejecución real de un plan revalidado y autorizado.

---

## Responsabilidades

- bloquear la resolución para evitar ejecución concurrente;
- verificar idempotencia;
- iniciar el registro de ejecución;
- ejecutar los pasos en orden;
- delegar cada operación al servicio de dominio propietario;
- recopilar resultados;
- registrar identificadores producidos por los módulos;
- manejar errores;
- aplicar políticas de reintento;
- ejecutar compensaciones cuando sean válidas;
- determinar el resultado final;
- liberar bloqueos;
- cerrar la resolución.

---

## Restricción fundamental

El ejecutor no implementa directamente operaciones de dominio.

Ejemplo incorrecto:

```text
INSERT INTO service_orders ...
```

Ejemplo correcto:

```text
ServiceOrderService.create_complementary_service_order(...)
```

---

# Contratos de dominio

## Definición

Los contratos de dominio son interfaces estables mediante las cuales el motor solicita operaciones a los módulos propietarios.

---

## Ejemplos conceptuales

```text
QuotationService.create_complementary_quotation()
ServiceOrderService.create_complementary_service_order()
EquipmentService.register_additional_equipment()
WorkOrderService.assign_equipment()
FieldSheetService.create_for_equipment()
CertificateService.reserve_certificate_identity()
InvoiceService.create_complementary_invoice_draft()
SignatureService.request_additional_signature()
```

---

## Responsabilidad del módulo propietario

Cada módulo deberá:

- validar sus reglas;
- verificar permisos internos;
- mantener sus invariantes;
- generar sus folios;
- administrar sus transacciones;
- registrar su propia auditoría;
- devolver un resultado estructurado;
- implementar idempotencia para operaciones llamadas por el motor.

---

## Resultado del contrato

Cada servicio deberá devolver información suficiente para que el motor registre el resultado.

Ejemplo:

```text
DomainOperationResult
├── success
├── operation_key
├── entity_type
├── entity_id
├── institutional_identifier
├── status
├── warnings
├── metadata
└── idempotency_key
```

---

# Ownership de folios e identificadores

## Regla absoluta

El Motor de Resoluciones nunca genera, calcula ni decide folios institucionales.

---

## Propietarios

```text
ServiceOrderService → folios ETS
WorkOrderService    → folios OT
CertificateService  → folios de certificado
InvoiceService      → folios internos de factura
QuotationService    → folios de cotización
```

---

## Flujo correcto

```text
ResolutionExecutor
        │
        ▼
ServiceOrderService.create_complementary_service_order()
        │
        ├── valida reglas
        ├── bloquea secuencia
        ├── genera folio
        ├── persiste ETS
        └── devuelve identificador
```

---

## Beneficio

Si el formato de los folios cambia, el Motor de Resoluciones no requiere cambios.

---

# Adaptadores de dominio

La arquitectura deberá evitar que el núcleo dependa directamente de implementaciones concretas.

Podrán utilizarse adaptadores como:

```text
ResolutionDomainGateway
├── ServiceOrderGateway
├── EquipmentGateway
├── WorkOrderGateway
├── CertificateGateway
├── InvoiceGateway
└── QuotationGateway
```

Estos adaptadores podrán mapear los contratos del motor a los servicios reales existentes en cada módulo.

Esto permitirá integrar gradualmente módulos heredados sin contaminar el núcleo.

---

# ResolutionStateMachine

## Definición

Controla las transiciones válidas de estado.

---

## Estados conceptuales

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
superseded
rejected
cancelled
```

La nomenclatura final podrá adaptarse a las convenciones del ERP, pero los significados deberán mantenerse claros.

---

## Flujo principal

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

---

## Estados terminales

```text
completed
rejected
cancelled
superseded
```

`failed` no necesariamente deberá ser terminal si existe una política segura de reintento.

---

## Transiciones inválidas

Ejemplos:

- ejecutar una resolución sin simulación;
- autorizar un plan inexistente;
- modificar un plan autorizado;
- ejecutar una resolución rechazada;
- autorizar una resolución completada;
- reutilizar una autorización para una nueva versión del plan.

---

# Idempotencia

## Definición

La idempotencia garantiza que una misma operación no produzca efectos duplicados.

---

## Niveles de idempotencia

La arquitectura deberá contemplar idempotencia en tres niveles.

### Nivel resolución

La misma solicitud lógica no deberá crear múltiples resoluciones activas sin justificación.

### Nivel ejecución

Una resolución no deberá ejecutarse dos veces.

### Nivel paso

Un paso reintentado no deberá duplicar la entidad producida.

---

## Claves de idempotencia

Podrán utilizarse claves como:

```text
resolution_request_key
execution_key
step_execution_key
domain_operation_key
offline_operation_uuid
```

---

## Ejemplo

Si la comunicación falla después de que `ServiceOrderService` creó el ETS, el reintento deberá recuperar el ETS ya creado y no generar otro.

---

# Concurrencia

## Riesgo

Dos usuarios o procesos pueden intentar resolver el mismo problema simultáneamente.

También puede cambiar el estado de una entidad mientras una resolución se encuentra pendiente.

---

## Medidas requeridas

La arquitectura deberá incluir:

- bloqueo lógico de resolución;
- control de versión;
- comparación de contexto;
- restricciones únicas;
- validación transaccional;
- bloqueo de ejecución;
- detección de resoluciones activas equivalentes;
- control optimista o pesimista según el dominio.

---

## Regla

Ninguna resolución deberá asumir que el contexto permanece estático.

---

# Transacciones

## Principio

Una resolución puede involucrar múltiples módulos y varias transacciones.

No debe asumirse que toda la resolución puede ejecutarse dentro de una única transacción de base de datos.

---

## Estrategia recomendada

Cada módulo será responsable de la atomicidad de su propia operación.

El motor coordinará una secuencia de operaciones persistentes.

Esto se aproxima a un patrón de saga orquestada.

---

## Saga orquestada

```text
Motor
  │
  ├── Ejecuta Paso 1 en Módulo A
  │       └── confirma transacción local
  │
  ├── Ejecuta Paso 2 en Módulo B
  │       └── confirma transacción local
  │
  └── Ejecuta Paso 3 en Módulo C
          └── confirma transacción local
```

Si un paso falla, el motor decidirá entre:

- reintentar;
- bloquear;
- ejecutar compensación;
- marcar ejecución parcial;
- escalar para intervención.

---

# Compensaciones

## Definición

Una compensación es una operación explícita que reduce o revierte el efecto de un paso previamente ejecutado.

---

## Restricción

No todas las operaciones pueden compensarse.

Ejemplos de operaciones posiblemente compensables:

- eliminar una reserva provisional;
- cancelar una asignación no utilizada;
- desactivar un borrador no formalizado.

Ejemplos de operaciones no reversibles:

- timbrar una factura;
- autenticar un certificado;
- emitir un documento institucional;
- consumir una secuencia oficial, dependiendo de la política del módulo.

---

## Regla

Cada paso deberá declarar:

```text
compensable
compensation_operation
point_of_no_return
```

La ausencia de compensación deberá ser explícita.

---

# Resultados de ejecución

## ResolutionExecution

Cada intento de ejecución deberá almacenarse como una entidad separada.

---

## Estructura conceptual

```text
ResolutionExecution
├── execution_id
├── resolution_id
├── plan_id
├── attempt_number
├── status
├── started_at
├── completed_at
├── executed_by
├── idempotency_key
├── initial_context_hash
├── final_context_hash
├── error
└── step_executions[]
```

---

## ResolutionStepExecution

```text
ResolutionStepExecution
├── step_execution_id
├── execution_id
├── step_id
├── status
├── started_at
├── completed_at
├── request_payload
├── response_payload
├── created_entities
├── warnings
├── error
└── retry_count
```

---

# ResolutionResult

## Definición

Representa la conclusión consolidada de una resolución.

---

## Estructura conceptual

```text
ResolutionResult
├── resolution_id
├── status
├── summary
├── created_entities
├── modified_entities
├── preserved_entities
├── failed_steps
├── warnings
├── follow_up_actions
├── completed_at
└── completed_by
```

---

## Estados de resultado

```text
success
partial_success
failed
cancelled
superseded
no_action_required
```

---

# Auditoría

## Principio

La auditoría no es un efecto secundario.

Forma parte del núcleo del motor.

---

## ResolutionAuditService

Será responsable de registrar:

- creación;
- captura de contexto;
- análisis;
- selección de estrategia;
- creación de plan;
- simulación;
- autorización;
- rechazo;
- revalidación;
- cambio de plan;
- ejecución;
- errores;
- compensaciones;
- cierre;
- cancelación.

---

## Evento de auditoría

```text
ResolutionAuditEvent
├── event_id
├── resolution_id
├── event_type
├── actor_type
├── actor_id
├── occurred_at
├── previous_state
├── new_state
├── plan_version
├── payload
├── correlation_id
└── source
```

---

## Inmutabilidad

Los eventos de auditoría no deberán editarse.

Las correcciones deberán registrarse mediante nuevos eventos.

---

# Seguridad

La arquitectura deberá separar:

- permiso para solicitar;
- permiso para consultar;
- permiso para simular;
- permiso para autorizar;
- permiso para ejecutar;
- permiso para cancelar;
- permiso para consultar evidencia sensible.

No deberá asumirse que un usuario que puede solicitar también puede autorizar o ejecutar.

---

## Segregación de funciones

La política de cada resolución podrá establecer restricciones como:

```text
El solicitante no puede autorizar.
El ejecutor no puede ser el autorizador.
Calidad debe autorizar resoluciones sobre certificados.
Finanzas debe autorizar resoluciones fiscales.
Administrador puede intervenir únicamente mediante una política explícita.
```

---

# Observabilidad

El Motor de Resoluciones deberá producir información operativa suficiente para diagnóstico.

---

## Elementos recomendados

- identificador de correlación;
- logs estructurados;
- métricas de duración;
- número de resoluciones por tipo;
- número de bloqueos;
- tasa de revalidación fallida;
- tasa de ejecución parcial;
- pasos con mayor número de errores;
- tiempo promedio de autorización;
- número de reintentos;
- alertas sobre resoluciones estancadas.

---

## Correlation ID

Toda la actividad de una resolución deberá poder rastrearse mediante:

```text
resolution_id
correlation_id
execution_id
```

---

# Notificaciones

Las notificaciones deberán tratarse como efectos derivados del ciclo de vida.

Ejemplos:

- resolución pendiente de autorización;
- plan invalidado por cambio de contexto;
- ejecución completada;
- ejecución bloqueada;
- intervención requerida.

El envío de una notificación no deberá sustituir el registro persistente del estado.

La falla de una notificación no deberá provocar por sí sola la duplicación de la resolución.

---

# Integración mediante eventos

La arquitectura podrá utilizar eventos internos para desacoplar funciones secundarias.

Ejemplos:

```text
resolution.created
resolution.plan_built
resolution.simulated
resolution.authorization_requested
resolution.authorized
resolution.revalidation_failed
resolution.execution_started
resolution.step_completed
resolution.completed
resolution.failed
```

---

## Restricción

Los eventos no deberán convertirse en un camino alternativo sin auditoría para modificar entidades de dominio.

Las operaciones críticas deberán continuar pasando por contratos autorizados.

---

# Preparación para operación offline

La arquitectura deberá considerar que una solicitud puede originarse fuera de línea.

---

## Requisitos

Una operación offline deberá poder incluir:

```text
offline_operation_uuid
device_id
local_created_at
actor_id
entity_reference
payload
local_context_version
sync_attempt
```

---

## Principio

La aplicación offline podrá registrar hechos provisionales.

No deberá generar folios institucionales ni asumir que el contexto del servidor permanece igual.

---

## Ejemplo

El técnico registra trece equipos adicionales.

La aplicación podrá almacenar:

- identificación local;
- datos del equipo;
- catálogo seleccionado;
- tipo de trazabilidad;
- evidencia;
- marca temporal;
- UUID provisional.

No deberá crear:

- folio ETS;
- folio OT;
- folio de certificado;
- documento oficial.

Al sincronizar:

```text
Sync Service
      ↓
Resolution Engine
      ↓
Revalidación de contexto
      ↓
Plan de incorporación
      ↓
Autorización, si corresponde
      ↓
Módulos propietarios generan identidades oficiales
```

---

# Organización recomendada del código

La ubicación exacta deberá adaptarse a la estructura real del backend.

Como referencia conceptual:

```text
backend/
└── app/
    └── resolution_engine/
        ├── __init__.py
        ├── domain/
        │   ├── models.py
        │   ├── enums.py
        │   ├── value_objects.py
        │   ├── events.py
        │   └── exceptions.py
        │
        ├── application/
        │   ├── engine.py
        │   ├── lifecycle_service.py
        │   ├── context_builder.py
        │   ├── analyzer.py
        │   ├── plan_service.py
        │   ├── simulation_service.py
        │   ├── authorization_service.py
        │   ├── revalidation_service.py
        │   ├── execution_service.py
        │   ├── idempotency_service.py
        │   └── audit_service.py
        │
        ├── contracts/
        │   ├── context_provider.py
        │   ├── strategy.py
        │   ├── plan_builder.py
        │   ├── simulator.py
        │   ├── revalidator.py
        │   ├── executor.py
        │   └── domain_gateways.py
        │
        ├── infrastructure/
        │   ├── persistence/
        │   ├── repositories/
        │   ├── registry.py
        │   ├── locking.py
        │   ├── idempotency.py
        │   └── event_publisher.py
        │
        ├── resolutions/
        │   ├── service_order/
        │   │   └── add_additional_equipment/
        │   │       ├── context_provider.py
        │   │       ├── analyzer.py
        │   │       ├── strategy.py
        │   │       ├── plan_builder.py
        │   │       ├── simulator.py
        │   │       ├── revalidator.py
        │   │       ├── executor.py
        │   │       └── policy.py
        │   │
        │   └── ...
        │
        └── api/
            ├── router.py
            ├── schemas.py
            └── dependencies.py
```

---

# Dependencias permitidas

```text
API
 ↓
Application
 ↓
Domain / Contracts
 ↑
Infrastructure
```

Las implementaciones específicas deberán depender de los contratos del núcleo.

El núcleo no deberá depender de implementaciones concretas de infraestructura.

---

# Dependencias prohibidas

No deberá existir una dependencia como:

```text
ResolutionEngine
    └── importa directamente Invoice ORM Model
```

Tampoco:

```text
ResolutionEngine
    └── genera folio de certificado
```

Ni:

```text
ResolutionEngine
    └── modifica tablas de Equipos con SQL
```

La integración deberá realizarse siempre mediante contratos o gateways explícitos.

---

# Fallos y recuperación

La arquitectura deberá distinguir al menos:

### Error de validación

El plan no es válido.

### Error de autorización

El usuario no puede aprobar o ejecutar.

### Cambio de contexto

El plan debe reconstruirse.

### Error temporal

Un servicio o recurso no está disponible.

### Error de dominio

El módulo propietario rechaza la operación.

### Error parcial

Algunos pasos se ejecutaron y otros no.

### Error de integridad

El sistema detecta una inconsistencia que impide continuar.

---

## Regla de manejo

Cada error deberá producir:

- estado coherente;
- registro auditable;
- mensaje técnico interno;
- mensaje comprensible para el usuario;
- indicación de si puede reintentarse;
- indicación de si requiere intervención;
- preservación de los resultados ya producidos.

---

# Determinismo

Ante:

- el mismo tipo de problema;
- el mismo contexto relevante;
- la misma versión de reglas;
- la misma configuración institucional;

el motor deberá producir el mismo análisis, estrategia y plan.

---

## Versionado de lógica

Para mantener reproducibilidad, cada resolución podrá registrar:

```text
resolution_definition_version
strategy_version
plan_schema_version
policy_version
```

Esto permitirá explicar por qué una resolución histórica produjo un plan determinado aunque las reglas actuales hayan cambiado.

---

# Evolución del núcleo

El núcleo del motor deberá mantenerse pequeño y estable.

Las nuevas necesidades deberán resolverse preferentemente mediante:

- nuevas resoluciones;
- nuevas estrategias;
- nuevos contratos;
- nuevos adaptadores;
- nuevas políticas;
- nuevas versiones de plan.

No mediante condicionales acumulados dentro del `ResolutionEngine`.

---

# Criterios de conformidad arquitectónica

Una implementación será compatible con esta arquitectura únicamente si cumple todo lo siguiente:

- existe una entidad central `Resolution`;
- toda ejecución pertenece a una resolución;
- existe un plan previo;
- el plan se simula;
- la autorización se vincula a una versión concreta;
- el contexto se revalida;
- los pasos se delegan a módulos propietarios;
- el motor no genera folios;
- el motor no ejecuta SQL de dominio;
- existen mecanismos de idempotencia;
- existen controles de concurrencia;
- las acciones son auditables;
- las nuevas resoluciones pueden registrarse sin modificar el núcleo;
- los resultados parciales quedan documentados;
- los cambios de contexto pueden invalidar el plan;
- la historia institucional permanece preservada.

---

# Declaración final

La arquitectura del Motor de Resoluciones se fundamenta en una separación estricta entre coordinación y dominio.

El motor conoce el problema, el contexto, la estrategia, el plan y el ciclo de resolución.

Los módulos conocen sus reglas, sus documentos, sus transacciones y sus identificadores.

Esta separación permite que el ERP MYC atienda situaciones extraordinarias sin concentrar lógica de negocio, sin destruir evidencia y sin comprometer la evolución futura del sistema.

Toda implementación deberá preservar esta frontera arquitectónica.