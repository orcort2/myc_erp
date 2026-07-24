# 04 · Modelo Conceptual

# Modelo Conceptual del Motor de Resoluciones

## Introducción

Todo sistema complejo necesita un lenguaje común.

Antes de definir clases, tablas, endpoints o implementaciones, es necesario establecer los conceptos fundamentales que describen el funcionamiento del Motor de Resoluciones.

Este documento define dichos conceptos.

Cada uno representa una abstracción del dominio y constituye parte del lenguaje oficial del ERP MYC.

Las implementaciones deberán respetar este modelo conceptual independientemente de la tecnología utilizada.

---

# Visión general

El Motor de Resoluciones transforma una situación extraordinaria en un proceso controlado de recuperación de consistencia.

Conceptualmente, el flujo siempre sigue la siguiente secuencia:

Problema

↓

Contexto

↓

Análisis

↓

Estrategia

↓

Plan de Resolución

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

Auditoría

Cada elemento representa un concepto independiente.

---

# Problema (Resolution Problem)

## Definición

Un Problema representa una situación extraordinaria detectada por el ERP que impide continuar el flujo normal de operación.

No representa una excepción técnica.

No representa un error del sistema.

Representa una condición de negocio cuya resolución requiere un proceso controlado.

---

## Ejemplos

Agregar equipos después del inicio del servicio.

Modificar una factura ya emitida.

Reabrir captura.

Solicitar nueva firma.

Sustituir un certificado.

Resolver diferencias de sincronización.

---

## Responsabilidad

El Problema únicamente describe qué ocurrió.

Nunca determina cómo resolverlo.

---

# Contexto (Resolution Context)

## Definición

El Contexto representa la fotografía completa del sistema en el momento en que se analiza un problema.

Incluye toda la información necesaria para tomar una decisión.

El contexto nunca debe modificarse.

Representa únicamente el estado observado.

---

## Ejemplos de información

Servicio.

Cliente.

Estado del ETS.

Facturas existentes.

Certificados.

Equipos.

Órdenes de trabajo.

Firmas.

Pagos.

Usuarios involucrados.

Permisos.

Configuración institucional.

---

## Responsabilidad

El Contexto describe.

Nunca decide.

---

# Estrategia (Resolution Strategy)

## Definición

Una Estrategia representa una forma válida de resolver un problema.

Un mismo problema puede admitir múltiples estrategias.

Ejemplo:

Problema:

Agregar equipos.

Estrategias posibles:

• agregar directamente

• crear ETS complementario

• generar nueva cotización

• crear nuevo servicio

La selección dependerá del contexto.

---

## Responsabilidad

La estrategia responde:

"¿Cuál es el mejor camino?"

No responde:

"¿Cómo se ejecuta?"

---

# Plan de Resolución (Resolution Plan)

## Definición

El Plan constituye la representación formal de una resolución.

Es el documento interno que describe exactamente qué acciones deberán ejecutarse.

Toda resolución deberá poseer un único plan.

---

## Propiedades

Debe ser:

explicable

auditable

serializable

simulable

revalidable

ejecutable

---

## Responsabilidad

El Plan transforma una estrategia en una secuencia concreta de acciones.

---

# Paso (Resolution Step)

## Definición

Un Paso representa una acción individual dentro del Plan.

Cada paso posee una única responsabilidad.

Ejemplos:

Crear ETS complementario.

Solicitar folio.

Generar orden.

Mover estado.

Crear hoja.

Actualizar relación.

Registrar auditoría.

Cada paso deberá poder ejecutarse individualmente.

---

# Simulación

## Definición

La Simulación representa la ejecución lógica del Plan sin modificar el sistema.

Su objetivo consiste en responder:

¿Qué ocurrirá si este plan es aprobado?

---

## Responsabilidad

Validar consistencia.

Mostrar impactos.

Detectar conflictos.

Informar al usuario.

Nunca modifica información.

---

# Autorización

## Definición

La Autorización representa la aceptación institucional del Plan.

No autoriza un problema.

No autoriza una estrategia.

Autoriza un Plan específico.

---

## Responsabilidad

Convertir un plan propuesto en un plan autorizado.

---

# Revalidación

## Definición

Proceso mediante el cual el motor verifica nuevamente que el contexto utilizado para construir el plan continúa siendo válido.

---

## Justificación

Entre la aprobación y la ejecución pueden ocurrir cambios.

Por ejemplo:

Se emitió una factura.

Se autenticó un certificado.

Otro usuario resolvió el problema.

Cambió el estado del servicio.

---

## Responsabilidad

Garantizar que el plan continúa siendo válido.

---

# Ejecución

## Definición

Proceso mediante el cual el Plan autorizado se convierte en acciones reales.

Cada paso es delegado al módulo correspondiente.

El Motor nunca ejecuta directamente lógica de negocio especializada.

---

# Resultado

## Definición

Representa el estado final de la resolución.

Debe responder:

¿La resolución fue exitosa?

¿Qué acciones se ejecutaron?

¿Qué entidades fueron creadas?

¿Qué entidades permanecieron intactas?

¿Qué advertencias surgieron?

---

# Auditoría

## Definición

Registro permanente de todo el ciclo de vida de una resolución.

No registra únicamente el resultado.

Registra el proceso completo.

---

## Debe conservar

Problema.

Contexto.

Plan.

Simulación.

Autorización.

Revalidación.

Ejecución.

Resultado.

Usuario.

Fechas.

Versiones.

---

# Relaciones conceptuales

Problema

↓

requiere

↓

Contexto

↓

permite seleccionar

↓

Estrategia

↓

genera

↓

Plan

↓

se simula

↓

Simulación

↓

si es aprobada

↓

Autorización

↓

antes de ejecutar

↓

Revalidación

↓

si continúa siendo válida

↓

Ejecución

↓

produce

↓

Resultado

↓

queda registrado en

↓

Auditoría

---

# Separación de responsabilidades

Problema

Describe la situación.

---

Contexto

Describe el estado actual.

---

Estrategia

Decide el camino.

---

Plan

Describe las acciones.

---

Simulación

Predice consecuencias.

---

Autorización

Aprueba la ejecución.

---

Revalidación

Verifica que nada cambió.

---

Ejecución

Coordina módulos.

---

Resultado

Describe el estado final.

---

Auditoría

Conserva la evidencia.

---

# Independencia tecnológica

Los conceptos definidos en este documento representan el modelo conceptual del Motor de Resoluciones.

No corresponden necesariamente a clases, tablas o endpoints.

Una implementación podrá dividir, agrupar o extender estos conceptos según las necesidades técnicas.

Sin embargo, ninguna implementación deberá alterar el significado conceptual aquí definido.

Este modelo constituye el contrato semántico del Motor de Resoluciones y deberá mantenerse estable durante toda la evolución del ERP MYC.