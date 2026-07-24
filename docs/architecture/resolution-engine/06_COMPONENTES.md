# 06 · Componentes

# Componentes del Motor de Resoluciones

## Introducción

El Motor de Resoluciones se encuentra dividido en componentes especializados.

Cada componente posee una única responsabilidad claramente definida.

La separación de responsabilidades constituye uno de los pilares fundamentales de la arquitectura.

Ningún componente deberá asumir responsabilidades pertenecientes a otro.

La incorporación de nuevos tipos de resolución deberá realizarse mediante la composición de estos componentes y no mediante modificaciones al núcleo.

---

# Vista General

```text
Resolution
        │
        ▼
ResolutionEngine
        │
        ├────────────── ResolutionRegistry
        │
        ├────────────── ResolutionLifecycleService
        │
        ├────────────── ResolutionContextBuilder
        │
        ├────────────── ResolutionAnalyzer
        │
        ├────────────── ResolutionStrategySelector
        │
        ├────────────── ResolutionPlanBuilder
        │
        ├────────────── ResolutionSimulator
        │
        ├────────────── ResolutionAuthorizationService
        │
        ├────────────── ResolutionRevalidator
        │
        ├────────────── ResolutionExecutor
        │
        ├────────────── ResolutionAuditService
        │
        ├────────────── ResolutionIdempotencyService
        │
        ├────────────── ResolutionConcurrencyService
        │
        └────────────── ResolutionStateMachine
```

Cada uno de estos componentes representa una responsabilidad independiente.

---

# ResolutionEngine

## Propósito

Es la fachada principal del subsistema.

Todo acceso al Motor de Resoluciones deberá comenzar aquí.

---

## Responsabilidades

- iniciar resoluciones;
- consultar resoluciones;
- solicitar simulaciones;
- iniciar autorizaciones;
- iniciar ejecución;
- cancelar resoluciones;
- consultar historial.

---

## No es responsable de

- reglas del negocio;
- folios;
- SQL;
- validaciones específicas;
- generación de planes.

Su única responsabilidad consiste en coordinar el resto de componentes.

---

# ResolutionRegistry

## Propósito

Mantener el catálogo de todos los tipos de resolución disponibles.

---

## Responsabilidades

Registrar:

- ContextProvider
- Analyzer
- StrategySelector
- PlanBuilder
- Simulator
- Revalidator
- Executor
- AuthorizationPolicy

---

## Ejemplo

```text
service_order.add_additional_equipment
```

↓

obtiene

```text
EquipmentContextProvider

EquipmentAnalyzer

EquipmentStrategySelector

EquipmentPlanBuilder

EquipmentSimulator

EquipmentRevalidator

EquipmentExecutor
```

---

# ResolutionLifecycleService

## Propósito

Administrar el ciclo de vida completo de una resolución.

---

## Responsabilidades

Crear.

Abrir.

Cerrar.

Cancelar.

Rechazar.

Completar.

Bloquear.

Reabrir cuando la política lo permita.

---

## Nunca decide

Cómo resolver.

---

# ResolutionContextBuilder

## Propósito

Construir el contexto que utilizará la resolución.

---

## Responsabilidades

Consultar todos los módulos necesarios.

Unificar información.

Construir snapshot.

Calcular contexto.

Versionar contexto.

Generar hash.

---

## No decide

Nada.

Sólo observa.

---

# Fact Providers

## Propósito

Representar la puerta de entrada al conocimiento del dominio.

---

## Responsabilidades

Leer información.

Traducir modelos.

Ocultar persistencia.

Entregar hechos.

---

## Ejemplo

```text
InvoiceFactProvider

↓

Factura emitida

UUID

Estado

Pagos

Fecha
```

---

# ResolutionAnalyzer

## Propósito

Entender el problema.

---

## Responsabilidades

Analizar.

Detectar restricciones.

Detectar bloqueos.

Detectar inconsistencias.

Detectar entidades inmutables.

---

## Produce

```text
AnalysisReport
```

---

# ResolutionStrategySelector

## Propósito

Elegir el mejor camino.

---

## Responsabilidades

Comparar estrategias.

Aplicar reglas.

Elegir estrategia.

Justificar decisión.

---

## Produce

```text
ResolutionStrategy
```

---

# ResolutionPlanBuilder

## Propósito

Construir el Plan de Resolución.

---

## Responsabilidades

Crear pasos.

Ordenarlos.

Definir dependencias.

Asignar responsables.

Definir puntos críticos.

Versionar plan.

---

## Produce

```text
ResolutionPlan
```

---

# ResolutionSimulator

## Propósito

Responder:

¿Qué ocurrirá?

---

## Responsabilidades

Validar.

Simular.

Calcular impactos.

Mostrar entidades nuevas.

Mostrar entidades preservadas.

Detectar conflictos.

---

## Nunca hace

Persistencia.

---

# ResolutionAuthorizationService

## Propósito

Administrar autorizaciones.

---

## Responsabilidades

Solicitar autorización.

Registrar decisión.

Validar permisos.

Registrar comentarios.

Invalidar autorizaciones obsoletas.

---

## Produce

```text
AuthorizationRecord
```

---

# ResolutionRevalidator

## Propósito

Verificar que el plan sigue siendo válido.

---

## Responsabilidades

Reconstruir contexto.

Comparar contexto.

Detectar cambios.

Invalidar plan.

Solicitar reconstrucción.

---

## Produce

```text
RevalidationResult
```

---

# ResolutionExecutor

## Propósito

Coordinar la ejecución real.

---

## Responsabilidades

Ejecutar pasos.

Delegar operaciones.

Registrar resultados.

Registrar errores.

Administrar reintentos.

Coordinar compensaciones.

Cerrar ejecución.

---

## Nunca hace

Reglas del negocio.

---

# ResolutionStateMachine

## Propósito

Controlar el estado de la resolución.

---

## Responsabilidades

Permitir únicamente transiciones válidas.

Impedir estados imposibles.

Registrar cambios.

---

## Ejemplo

```text
draft

↓

context_ready

↓

plan_ready

↓

simulated

↓

authorized

↓

executing

↓

completed
```

---

# ResolutionAuditService

## Propósito

Registrar evidencia permanente.

---

## Responsabilidades

Guardar eventos.

Guardar cambios.

Guardar usuario.

Guardar fecha.

Guardar payload.

Guardar contexto.

Guardar plan.

Guardar resultado.

---

## Nunca modifica

Eventos existentes.

---

# ResolutionIdempotencyService

## Propósito

Evitar duplicidad.

---

## Responsabilidades

Detectar solicitudes repetidas.

Detectar pasos repetidos.

Detectar ejecuciones repetidas.

Recuperar resultados anteriores.

---

# ResolutionConcurrencyService

## Propósito

Controlar ejecución simultánea.

---

## Responsabilidades

Bloqueos.

Locks.

Versiones.

Resoluciones activas.

Conflictos.

---

# Domain Gateway

## Propósito

Representar la comunicación entre el motor y cada módulo del ERP.

---

## Responsabilidades

Traducir contratos.

Ocultar implementación.

Invocar servicios.

Recibir resultados.

---

## Nunca contiene

Lógica del negocio.

---

# Strategy

## Propósito

Representar una forma válida de resolver un problema.

---

## Responsabilidades

Declarar cuándo aplica.

Construir decisiones.

Describir ventajas.

Describir limitaciones.

---

## Ejemplo

```text
DirectEquipmentInsertionStrategy

ComplementaryETSStrategy

ComplementaryQuotationStrategy
```

---

# ContextProvider

## Propósito

Construir el contexto específico para un tipo de resolución.

---

## Responsabilidades

Consultar únicamente la información relevante.

No consultar información innecesaria.

Reducir acoplamiento.

---

# PlanBuilder

## Propósito

Construir un plan específico para una estrategia.

---

## Ejemplo

La estrategia

```text
Complementary ETS
```

podrá generar

```text
Paso 1

Crear cotización complementaria

↓

Paso 2

Crear ETS complementario

↓

Paso 3

Registrar equipos

↓

Paso 4

Crear hojas

↓

Paso 5

Actualizar relaciones
```

---

# Simulator

## Propósito

Simular exclusivamente un tipo de resolución.

---

## Responsabilidades

Detectar conflictos específicos.

Mostrar impactos específicos.

Validar estrategia específica.

---

# Executor

## Propósito

Ejecutar una resolución concreta.

---

## Responsabilidades

Invocar contratos.

Registrar identificadores.

Reportar resultados.

No decidir reglas.

---

# AuthorizationPolicy

## Propósito

Definir quién puede autorizar.

---

## Ejemplo

```text
Una autorización

Dos autorizaciones

Calidad

Finanzas

Administrador
```

---

# Revalidator

## Propósito

Verificar únicamente los cambios relevantes para un tipo de resolución.

---

## Ejemplo

Agregar equipos.

No importa:

Cambio de teléfono del cliente.

Sí importa:

Factura emitida.

Nuevo certificado.

Cambio de estado del ETS.

---

# Componentes especializados

Cada resolución concreta deberá implementar únicamente los componentes que necesite.

Ejemplo:

```text
service_order

└── add_additional_equipment

        ContextProvider

        Analyzer

        StrategySelector

        PlanBuilder

        Simulator

        Revalidator

        Executor

        AuthorizationPolicy
```

Otra resolución podrá reutilizar algunos componentes y reemplazar otros.

La arquitectura favorece la composición sobre la duplicación.

---

# Dependencias

Los componentes deberán comunicarse únicamente mediante contratos públicos.

Nunca deberán acceder a los detalles internos de otros componentes.

Esto garantiza:

- bajo acoplamiento;
- alta cohesión;
- facilidad de pruebas;
- evolución independiente.

---

# Ciclo completo

```text
Problema

↓

ResolutionEngine

↓

Registry

↓

ContextBuilder

↓

Analyzer

↓

StrategySelector

↓

PlanBuilder

↓

Simulator

↓

AuthorizationService

↓

Revalidator

↓

Executor

↓

AuditService

↓

Resultado
```

---

# Principio de responsabilidad única

Cada componente deberá responder únicamente a una pregunta.

| Componente | Pregunta que responde |
|------------|-----------------------|
| ContextBuilder | ¿Qué está ocurriendo? |
| Analyzer | ¿Qué significa? |
| StrategySelector | ¿Cuál es el mejor camino? |
| PlanBuilder | ¿Qué acciones deben ejecutarse? |
| Simulator | ¿Qué ocurrirá? |
| AuthorizationService | ¿Puede ejecutarse? |
| Revalidator | ¿Sigue siendo válido? |
| Executor | ¿Cómo se ejecuta? |
| AuditService | ¿Qué ocurrió? |

Si un componente comienza a responder dos preguntas distintas, deberá dividirse.

---

# Declaración final

La arquitectura del Motor de Resoluciones se basa en la colaboración de componentes pequeños, especializados y desacoplados.

Cada componente posee una única responsabilidad claramente definida y se comunica con el resto mediante contratos estables.

Esta organización permite que el sistema evolucione mediante la incorporación de nuevas resoluciones y nuevos comportamientos sin incrementar la complejidad del núcleo ni comprometer la consistencia arquitectónica del ERP MYC.