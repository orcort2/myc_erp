# 03 · Principios Arquitectónicos

# Principios del Motor de Resoluciones

## Introducción

Los siguientes principios constituyen las reglas fundamentales que gobiernan el diseño, implementación y evolución del Motor de Resoluciones.

No representan recomendaciones.

Representan restricciones arquitectónicas.

Cualquier implementación que contradiga alguno de estos principios deberá considerarse incompatible con la arquitectura del ERP MYC.

---

# Principio 1
## La historia es inmutable

La información que representa evidencia institucional nunca deberá modificarse de forma que altere su significado histórico.

Cuando una entidad ya no pueda cambiar sin comprometer la trazabilidad del sistema, deberá conservarse íntegra.

La resolución deberá construir un nuevo camino operativo en lugar de alterar el existente.

---

# Principio 2
## Resolver es extender, no reemplazar

Una resolución no sustituye la historia.

La complementa.

Siempre que sea posible, el sistema deberá preferir crear nuevas entidades relacionadas antes que modificar entidades históricas.

Este principio garantiza la preservación de la evidencia documental.

---

# Principio 3
## El motor coordina, nunca domina

El Motor de Resoluciones no es propietario de ningún dominio funcional.

No pertenece a Servicios.

No pertenece a Facturación.

No pertenece a Calidad.

No pertenece a Certificados.

Su única responsabilidad consiste en coordinar la ejecución de los módulos especializados.

Cada módulo continúa siendo propietario absoluto de sus propias reglas de negocio.

---

# Principio 4
## Cada módulo conserva su autonomía

Las decisiones específicas del dominio pertenecen exclusivamente al módulo correspondiente.

El Motor nunca implementará reglas fiscales.

Nunca implementará reglas metrológicas.

Nunca implementará reglas de certificados.

Nunca implementará reglas de inventario.

Nunca implementará reglas de numeración.

Cada dominio conserva completamente su responsabilidad.

---

# Principio 5
## El motor nunca genera información institucional

El Motor de Resoluciones nunca deberá generar directamente:

- folios;
- certificados;
- órdenes de trabajo;
- identificadores institucionales;
- numeraciones oficiales;
- documentos finales.

Cuando sea necesario crear alguno de estos elementos, el motor solicitará dicha operación al módulo propietario.

---

# Principio 6
## Toda resolución debe ser planificada

Antes de ejecutar cualquier cambio, el motor deberá construir un Plan de Resolución.

Ninguna resolución podrá ejecutarse directamente.

Todo cambio extraordinario deberá existir primero como una representación formal del proceso que será ejecutado.

---

# Principio 7
## Todo plan debe poder simularse

Antes de solicitar autorización, el motor deberá conocer las consecuencias esperadas de la resolución.

La simulación constituye una validación previa de consistencia.

El usuario nunca deberá autorizar acciones cuya consecuencia desconozca.

---

# Principio 8
## Toda ejecución debe revalidarse

Entre la aprobación de una resolución y su ejecución pueden cambiar las condiciones del sistema.

Por esta razón, toda resolución deberá verificar nuevamente su contexto antes de ejecutarse.

Si las condiciones originales ya no existen, el plan deberá actualizarse o cancelarse.

Nunca deberá ejecutarse un plan sobre información obsoleta.

---

# Principio 9
## La autorización pertenece a la organización

El motor puede proponer estrategias.

Nunca deberá asumir decisiones institucionales.

Cuando una resolución tenga consecuencias operativas, administrativas o documentales, deberá existir autorización explícita por parte de un usuario con los permisos correspondientes.

---

# Principio 10
## Toda resolución debe ser completamente auditable

Cada resolución deberá conservar evidencia suficiente para reconstruir posteriormente:

- el problema original;
- el contexto existente;
- la estrategia elegida;
- la simulación realizada;
- las autorizaciones obtenidas;
- las acciones ejecutadas;
- el resultado final.

La auditoría constituye parte esencial del proceso.

No es una funcionalidad adicional.

---

# Principio 11
## Ninguna resolución debe romper la consistencia

Una resolución únicamente será válida cuando el estado final del sistema sea consistente.

Resolver parcialmente un problema generando nuevas inconsistencias constituye un fallo del motor.

---

# Principio 12
## Las resoluciones deben ser idempotentes

Ejecutar dos veces la misma resolución nunca deberá producir efectos distintos.

El motor deberá ser capaz de identificar resoluciones previamente ejecutadas y evitar duplicidad de operaciones.

Este principio resulta indispensable para escenarios distribuidos y sincronización offline.

---

# Principio 13
## El motor debe ser extensible

La incorporación de nuevas resoluciones no deberá requerir modificaciones al núcleo del motor.

Cada nueva resolución deberá implementarse mediante componentes especializados que respeten los contratos definidos por la arquitectura.

El crecimiento del sistema deberá producirse por extensión y no por modificación.

---

# Principio 14
## Las reglas viven en el dominio

El Motor de Resoluciones únicamente conoce contratos.

Nunca deberá contener lógica específica de un proceso empresarial.

Si una regla pertenece exclusivamente a un módulo, deberá implementarse dentro de dicho módulo.

---

# Principio 15
## La arquitectura prevalece sobre la implementación

Las decisiones tecnológicas podrán cambiar con el tiempo.

Podrán cambiar lenguajes.

Frameworks.

Motores de base de datos.

Infraestructura.

Sin embargo, los principios definidos en este documento deberán permanecer invariantes.

Toda implementación futura deberá adaptarse a estos principios y no al contrario.

---

# Declaración final

Estos principios constituyen la base arquitectónica del Motor de Resoluciones.

Toda decisión de diseño, implementación, mantenimiento o evolución deberá evaluarse a la luz de estos principios.

Cuando exista conflicto entre una implementación y alguno de ellos, deberá prevalecer siempre la arquitectura definida en este documento.