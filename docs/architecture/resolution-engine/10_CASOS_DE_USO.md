# 10 · Casos de Uso

# Casos de Uso del Motor de Resoluciones

## Introducción

Este documento describe situaciones concretas en las que el Motor de Resoluciones interviene dentro del ERP MYC.

Los casos de uso no representan flujos normales del sistema.

Representan condiciones extraordinarias en las que:

- el proceso ordinario dejó de ser suficiente;
- existen cambios posteriores a una formalización;
- hay entidades históricas que no pueden modificarse;
- se detectan conflictos de sincronización;
- se requiere autorización institucional;
- deben coordinarse varios módulos;
- la consistencia sólo puede recuperarse mediante una intervención controlada.

Cada caso deberá resolverse mediante:

```text
Problema
    ↓
Contexto
    ↓
Análisis
    ↓
Estrategia
    ↓
Plan
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
```

---

# Clasificación de casos

Los casos de uso podrán agruparse en las siguientes familias:

```text
1. Servicios y ETS
2. Equipos y órdenes de trabajo
3. Firmas y evidencia
4. Hojas de campo
5. Calidad y certificados
6. Cotizaciones y facturación
7. Pagos y liberaciones
8. Sincronización offline
9. Conflictos entre módulos
10. Recuperación técnica con impacto operativo
```

---

# Plantilla de documentación

Cada caso de uso deberá describirse mediante la siguiente estructura:

```text
Identificador
Nombre
Tipo de resolución
Objetivo
Actores
Disparador
Precondiciones
Problema
Contexto requerido
Estrategias posibles
Plan esperado
Autorizaciones
Revalidación
Resultado
Errores y alternativas
Auditoría
```

---

# UC-001 · Agregar equipos adicionales a un ETS activo

## Tipo de resolución

```text
service_order.add_additional_equipment
```

---

## Objetivo

Incorporar equipos no contemplados originalmente a un servicio que todavía se encuentra operativo.

---

## Actores

- Técnico;
- Comercial;
- Administrador;
- Motor de Resoluciones;
- Módulo ETS;
- Módulo Equipos;
- Módulo Órdenes de Trabajo;
- Módulo Hojas de Campo;
- Módulo de Firmas.

---

## Disparador

Durante la ejecución de un servicio, el técnico identifica equipos adicionales que el cliente desea incluir.

---

## Problema

Los equipos no forman parte del alcance original.

Por lo tanto, el sistema no debe incorporarlos silenciosamente como si siempre hubieran pertenecido al servicio.

---

## Contexto requerido

- estado del ETS;
- estado de la cotización;
- existencia y estado de factura;
- estado de certificados;
- cantidad de equipos existentes;
- distribución actual de OT;
- firmas vigentes;
- identidad de los equipos adicionales;
- origen de la solicitud;
- límite autorizado de equipos;
- permisos del solicitante.

---

## Estrategia A · Incorporación directa

Aplica cuando:

- el ETS sigue abierto;
- no existe factura emitida que impida modificar el alcance;
- no existen certificados autenticados afectados;
- la política comercial permite incorporar el nuevo alcance;
- el servicio sigue en condiciones de operación.

---

## Plan conceptual

```text
1. Validar los equipos adicionales.
2. Registrar los equipos en el ETS existente.
3. Solicitar al módulo propietario las identidades oficiales necesarias.
4. Recalcular la distribución de órdenes de trabajo.
5. Crear nuevas OT si el límite de equipos lo requiere.
6. Crear hojas de campo.
7. Determinar si se requiere firma adicional.
8. Actualizar el alcance operativo del servicio.
9. Notificar a los responsables.
```

---

## Estrategia B · Servicio complementario

Aplica cuando la incorporación directa alteraría documentos o entidades inmutables.

```text
1. Crear cotización complementaria.
2. Crear ETS complementario.
3. Vincularlo con el ETS original.
4. Registrar los equipos adicionales.
5. Crear OT.
6. Crear hojas de campo.
7. Obtener firmas.
8. Continuar el flujo de servicio.
```

---

## Autorización

Podrá requerirse autorización de:

- Comercial, por cambio de alcance;
- Administración, por excepción operativa;
- Finanzas, si existe impacto fiscal;
- Calidad, si afecta documentación ya revisada.

---

## Revalidación

Antes de ejecutar se verificará:

- que el ETS siga en el estado esperado;
- que no se haya emitido una factura;
- que no se hayan autenticado certificados;
- que los equipos no hayan sido registrados por otro proceso;
- que la distribución de OT siga siendo aplicable.

---

## Resultado

- equipos registrados;
- OT creadas o actualizadas;
- hojas de campo creadas;
- firmas adicionales solicitadas, si corresponde;
- relaciones históricas preservadas;
- folios generados por sus módulos propietarios.

---

# UC-002 · Agregar equipos capturados offline

## Tipo de resolución

```text
sync.add_offline_equipment
```

---

## Objetivo

Incorporar al servidor equipos registrados por un técnico mientras no tenía conexión.

---

## Actores

- Técnico;
- Aplicación móvil;
- Servicio de sincronización;
- Motor de Resoluciones;
- Módulo Equipos;
- Módulo ETS.

---

## Disparador

La aplicación móvil recupera conexión y envía equipos provisionales.

---

## Problema

El dispositivo contiene información creada con base en un contexto que puede haber cambiado.

Los equipos poseen UUID locales, pero no identidades institucionales.

---

## Contexto requerido

- `offline_operation_uuid`;
- dispositivo;
- técnico;
- fecha local;
- ETS asociado;
- estado actual del ETS en el servidor;
- datos de los equipos;
- estado actual de facturación;
- OT existentes;
- firmas;
- posibles duplicados.

---

## Estrategias

### Aplicar al ETS existente

Cuando el servicio continúa abierto y el contexto permite la incorporación.

### Crear ETS complementario

Cuando el servicio original ya no puede modificarse.

### Rechazar la incorporación

Cuando:

- el ETS fue cancelado;
- los equipos ya existen;
- la información es insuficiente;
- el usuario no estaba autorizado;
- la solicitud presenta conflicto de identidad.

---

## Plan

```text
1. Validar la operación offline.
2. Detectar duplicados.
3. Mapear UUID locales.
4. Crear la resolución operativa correspondiente.
5. Registrar equipos mediante el módulo propietario.
6. Obtener identificadores oficiales.
7. Crear relaciones con OT y hojas.
8. Construir el mapa local_uuid → server_id.
9. Confirmar la sincronización al dispositivo.
```

---

## Restricción

La aplicación móvil no genera:

- folios ETS;
- folios OT;
- folios de certificado;
- documentos oficiales.

---

## Resultado

El dispositivo recibe la relación entre sus identificadores provisionales y las entidades oficiales creadas en el servidor.

---

# UC-003 · Redistribuir equipos entre órdenes de trabajo

## Tipo de resolución

```text
work_order.redistribute_equipment
```

---

## Objetivo

Corregir o reorganizar la distribución de equipos entre órdenes de trabajo sin perder trazabilidad.

---

## Disparador

Se detecta que:

- una OT excede el límite permitido;
- un equipo fue asignado a la OT equivocada;
- se agregaron equipos adicionales;
- una OT debe dividirse;
- una OT no puede ser ejecutada por el técnico asignado.

---

## Contexto requerido

- ETS;
- OT existentes;
- equipos por OT;
- estado de cada equipo;
- hojas de campo;
- firmas;
- técnicos asignados;
- documentos emitidos;
- certificados asociados.

---

## Estrategias

### Redistribución directa

Cuando no existen documentos o ejecuciones que hagan inmutable la asignación.

### Crear OT complementarias

Cuando debe preservarse la OT original.

### No modificar y crear una nueva relación operativa

Cuando el historial de ejecución ya está formalizado.

---

## Plan conceptual

```text
1. Determinar la distribución objetivo.
2. Identificar equipos movibles.
3. Identificar equipos históricamente fijados.
4. Crear las OT requeridas.
5. Reasignar únicamente equipos permitidos.
6. Mantener referencias históricas.
7. Actualizar hojas de campo pendientes.
8. Solicitar firmas adicionales si cambia el alcance firmado.
```

---

## Resultado

La distribución queda consistente sin reescribir evidencia de actividades ya realizadas.

---

# UC-004 · Solicitar firma adicional por cambio de alcance

## Tipo de resolución

```text
service_order.request_additional_signature
```

---

## Objetivo

Obtener una nueva firma cuando el alcance del servicio cambió después de la firma inicial.

---

## Problema

La firma existente acredita un conjunto concreto de OT o equipos.

No debe considerarse automáticamente válida para elementos creados después.

---

## Contexto requerido

- firmas vigentes;
- alcance cubierto por cada firma;
- OT existentes al momento de la firma;
- OT posteriores;
- equipos adicionales;
- firmantes;
- estado del ETS.

---

## Estrategias

### Firma complementaria por OT

La nueva firma cubre únicamente OT creadas después.

### Firma complementaria por equipos

La firma cubre un conjunto específico de equipos adicionales.

### Nueva firma general

Aplica cuando el cambio altera sustancialmente el alcance completo.

---

## Plan

```text
1. Calcular el alcance no cubierto.
2. Crear una solicitud de firma complementaria.
3. Preservar la firma original.
4. Vincular la nueva firma con las entidades adicionales.
5. Actualizar la cobertura documental.
```

---

## Restricción

La firma original no se sustituye ni se expande retroactivamente.

---

# UC-005 · Pausar un servicio en ejecución

## Tipo de resolución

```text
service_order.pause
```

---

## Objetivo

Suspender temporalmente un servicio debido a una condición extraordinaria.

---

## Disparadores posibles

- equipo no disponible;
- acceso denegado;
- condiciones inseguras;
- cliente solicita suspensión;
- patrón no disponible;
- falla técnica;
- documentación incompleta.

---

## Contexto requerido

- estado del ETS;
- equipos en proceso;
- hojas de campo abiertas;
- técnicos asignados;
- ubicación;
- citas futuras;
- evidencia de la causa;
- impacto en certificados;
- compromisos comerciales.

---

## Estrategias

### Pausa operativa simple

Detiene nuevas actividades sin alterar trabajos ya registrados.

### Pausa con reprogramación

Crea una nueva programación.

### Cierre parcial y continuación posterior

Preserva los equipos concluidos y deja pendientes los restantes.

---

## Plan

```text
1. Registrar causa y evidencia.
2. Determinar equipos afectados.
3. Detener operaciones pendientes.
4. Preservar datos ya capturados.
5. Actualizar estado operativo.
6. Reprogramar, si corresponde.
7. Notificar a cliente y áreas internas.
```

---

## Resultado

El servicio queda pausado de forma explicable y recuperable.

---

# UC-006 · Reanudar un servicio pausado

## Tipo de resolución

```text
service_order.resume
```

---

## Objetivo

Continuar un servicio previamente pausado, verificando que las condiciones vigentes todavía sean compatibles.

---

## Revalidación requerida

- disponibilidad del técnico;
- vigencia de la programación;
- estado de equipos;
- cambios en cliente;
- cambios en patrones;
- documentos generados durante la pausa;
- alcance pendiente.

---

## Estrategias

### Reanudar el mismo ETS

Cuando no existe ruptura documental.

### Crear continuación complementaria

Cuando el tiempo o los documentos formalizados impiden continuar sobre el mismo alcance.

---

# UC-007 · Reabrir una hoja de campo concluida

## Tipo de resolución

```text
field_sheet.reopen
```

---

## Objetivo

Permitir corrección controlada de una hoja de campo que fue marcada como concluida.

---

## Problema

Una hoja concluida no debería volver a edición ordinaria sin justificación.

---

## Contexto requerido

- estado de la hoja;
- certificado asociado;
- revisión de Captura;
- revisión de Calidad;
- autenticación;
- usuario que solicita;
- campos a corregir;
- motivo;
- evidencia.

---

## Estrategias

### Reapertura directa

Cuando la hoja no ha iniciado revisión formal.

### Nueva versión de hoja

Cuando la hoja ya fue revisada, pero no autenticada.

### Corrección complementaria

Cuando existe evidencia documental inmutable.

---

## Plan

```text
1. Registrar el motivo.
2. Identificar campos afectados.
3. Preservar snapshot anterior.
4. Crear nueva versión editable.
5. Invalidar revisiones dependientes.
6. Reenviar al flujo de captura y calidad.
```

---

## Restricción

La versión anterior debe permanecer disponible para auditoría.

---

# UC-008 · Regresar un certificado a Captura

## Tipo de resolución

```text
quality.return_to_capture
```

---

## Objetivo

Regresar el trabajo a Captura cuando Calidad detecta una inconsistencia.

---

## Contexto requerido

- hoja de campo;
- certificado;
- observaciones de Calidad;
- estado de autenticación;
- revisiones anteriores;
- campos afectados.

---

## Estrategia

### Regreso ordinario

Cuando el certificado aún no ha sido autenticado.

### Corrección complementaria

Cuando ya existe autenticación o liberación.

---

## Plan

```text
1. Registrar observaciones.
2. Cambiar el estado de revisión.
3. Conservar la versión revisada.
4. Habilitar nueva versión de captura.
5. Notificar al responsable.
6. Repetir el flujo de revisión.
```

---

# UC-009 · Sustituir certificado antes de autenticación

## Tipo de resolución

```text
certificate.replace_before_authentication
```

---

## Objetivo

Reemplazar un certificado generado incorrectamente antes de que adquiera carácter documental definitivo.

---

## Precondiciones

- certificado no autenticado;
- certificado no liberado;
- no existe factura o entrega que dependa de esa versión, según política;
- motivo registrado.

---

## Plan

```text
1. Marcar el certificado anterior como sustituido.
2. Preservar su archivo y metadatos.
3. Generar una nueva versión.
4. Reenviar a Calidad.
5. Vincular ambas versiones.
```

---

## Resultado

La versión anterior permanece como evidencia, pero deja de ser la versión activa.

---

# UC-010 · Corregir certificado autenticado

## Tipo de resolución

```text
certificate.correct_authenticated
```

---

## Objetivo

Corregir un certificado después de su autenticación sin alterar el documento histórico.

---

## Problema

Un certificado autenticado es evidencia institucional.

No puede editarse ni reemplazarse silenciosamente.

---

## Estrategias

### Certificado sustituto

Se crea un nuevo certificado que sustituye formalmente al anterior.

### Fe de erratas o documento complementario

Se conserva el certificado y se genera un documento asociado.

### Cancelación documental

Cuando la política documental permite cancelar el certificado previo.

---

## Plan conceptual

```text
1. Identificar el error.
2. Clasificar su impacto.
3. Bloquear liberación, si aún no ocurrió.
4. Preservar certificado original.
5. Crear documento sustituto o complementario.
6. Establecer relación de sustitución.
7. Autenticar el nuevo documento.
8. Notificar a las áreas y al cliente.
```

---

## Autorización

Debe intervenir Calidad.

Según el impacto, también puede requerirse Administración.

---

# UC-011 · Liberar certificado con pago pendiente por excepción

## Tipo de resolución

```text
certificate.release_with_payment_exception
```

---

## Objetivo

Autorizar excepcionalmente la liberación de un certificado aunque la política normal indique pago pendiente.

---

## Problema

La regla normal bloquea la liberación.

El caso requiere una autorización institucional explícita.

---

## Contexto requerido

- certificado;
- factura;
- saldo;
- cliente;
- acuerdos comerciales;
- historial de crédito;
- autorizaciones previas;
- motivo de la excepción.

---

## Estrategias

### Liberación única

Sólo el certificado seleccionado.

### Liberación de todos los certificados del ETS

Cuando existe autorización comercial amplia.

### Mantener bloqueo

Cuando no existe justificación suficiente.

---

## Autorización

Podrá requerirse:

- Finanzas;
- Administración;
- Dirección, según monto o política.

---

## Plan

```text
1. Registrar motivo.
2. Identificar alcance autorizado.
3. Crear autorización de excepción.
4. Liberar mediante CertificateService.
5. Conservar el saldo pendiente.
6. Registrar seguimiento financiero.
```

---

## Restricción

La liberación no debe marcar la factura como pagada.

---

# UC-012 · Modificar borrador de factura después de cambiar el servicio

## Tipo de resolución

```text
invoice.reconcile_draft_with_service_change
```

---

## Objetivo

Actualizar un borrador de factura cuando la cotización o el servicio cambió antes del timbrado.

---

## Contexto requerido

- factura en borrador;
- cotización;
- ETS;
- conceptos;
- impuestos;
- pagos;
- equipos adicionales;
- usuario solicitante.

---

## Estrategia

Actualizar el borrador conservando el vínculo con la cotización original y registrando el cambio de alcance.

---

## Plan

```text
1. Comparar cotización, servicio y borrador.
2. Detectar conceptos nuevos, retirados o modificados.
3. Construir propuesta de conciliación.
4. Simular importes e impuestos.
5. Solicitar confirmación.
6. Actualizar el borrador mediante InvoiceService.
7. Registrar historial.
```

---

# UC-013 · Cambio solicitado después de timbrar una factura

## Tipo de resolución

```text
invoice.modify_after_issue
```

---

## Objetivo

Resolver una modificación comercial o fiscal después de que la factura ya fue emitida.

---

## Problema

El CFDI timbrado no puede editarse como un borrador.

---

## Contexto requerido

- factura emitida;
- UUID;
- estado ante PAC;
- pagos;
- cotización;
- servicio;
- modificación solicitada;
- motivo fiscal;
- plazo y viabilidad de cancelación;
- documentos relacionados.

---

## Estrategias

### Cancelación y sustitución

Cuando fiscalmente procede.

### Nota de crédito

Cuando debe reducirse el importe.

### Factura complementaria

Cuando debe aumentarse el alcance.

### No proceder

Cuando la modificación no es válida.

---

## Plan de factura complementaria

```text
1. Preservar factura original.
2. Crear cotización complementaria, si corresponde.
3. Crear borrador de factura complementaria.
4. Vincular documentos.
5. Validar información fiscal.
6. Emitir nuevo CFDI mediante InvoiceService.
```

---

## Restricción

El motor no modifica el XML timbrado ni su UUID.

---

# UC-014 · Cancelar una factura con dependencias

## Tipo de resolución

```text
invoice.cancel_with_dependencies
```

---

## Objetivo

Coordinar la cancelación de una factura cuando existen pagos, certificados liberados u otros procesos relacionados.

---

## Contexto requerido

- estado fiscal;
- pagos aplicados;
- certificados liberados;
- saldo;
- CFDI relacionados;
- motivo de cancelación;
- aceptación requerida;
- estado en Facturama o PAC.

---

## Estrategias

- cancelación directa;
- cancelación con sustitución;
- rechazo de cancelación;
- conciliación previa de pagos;
- emisión de nota de crédito.

---

## Plan

El plan deberá declarar claramente qué módulos deben intervenir y en qué orden.

El motor no deberá cancelar primero y analizar después las dependencias.

---

# UC-015 · Registrar pago no conciliado

## Tipo de resolución

```text
payment.reconcile_unmatched
```

---

## Objetivo

Vincular un pago recibido con la factura, cliente o servicio correspondiente.

---

## Problema

Existe un movimiento financiero que no puede asociarse de manera automática.

---

## Contexto requerido

- monto;
- fecha;
- referencia;
- cuenta;
- cliente probable;
- facturas abiertas;
- saldos;
- moneda;
- evidencia bancaria.

---

## Estrategias

### Aplicación a una factura

Cuando existe coincidencia suficiente.

### Distribución entre varias facturas

Cuando el monto cubre varios documentos.

### Anticipo

Cuando no existe factura aplicable.

### Pago no identificado

Cuando la evidencia no es suficiente.

---

## Autorización

Finanzas debe confirmar conciliaciones ambiguas o distribuidas.

---

# UC-016 · Reasignar pago aplicado incorrectamente

## Tipo de resolución

```text
payment.reassign
```

---

## Objetivo

Corregir la aplicación de un pago sin borrar su historia.

---

## Plan conceptual

```text
1. Preservar la aplicación original.
2. Registrar reversión contable u operativa.
3. Restaurar saldos.
4. Crear nueva aplicación.
5. Actualizar estados derivados.
6. Auditar ambas operaciones.
```

---

## Restricción

No debe eliminarse la relación original como si nunca hubiera existido.

---

# UC-017 · Resolver duplicidad de equipos

## Tipo de resolución

```text
equipment.resolve_duplicate
```

---

## Objetivo

Resolver dos registros que parecen representar al mismo equipo.

---

## Contexto requerido

- cliente;
- identificación;
- marca;
- modelo;
- serie;
- historial de servicios;
- certificados;
- hojas de campo;
- OT;
- origen de cada registro.

---

## Estrategias

### Confirmar que son equipos distintos

Se conserva ambos registros.

### Unificar identidad lógica

Se selecciona un registro principal y se vincula el otro como duplicado histórico.

### Corregir registro provisional

Cuando uno aún no ha generado documentación.

---

## Restricción

No deben trasladarse documentos históricos sin preservar su referencia original.

---

# UC-018 · Resolver equipo registrado en cliente incorrecto

## Tipo de resolución

```text
equipment.correct_client_assignment
```

---

## Objetivo

Corregir la pertenencia de un equipo asignado al cliente equivocado.

---

## Estrategias

### Corrección directa

Cuando el equipo no tiene historial formal.

### Transferencia documentada

Cuando el equipo tiene servicios previos.

### Duplicación controlada de identidad operativa

Cuando los datos no permiten confirmar una única identidad física.

---

# UC-019 · Corregir relación entre ETS y cotización

## Tipo de resolución

```text
service_order.reconcile_quotation_relation
```

---

## Objetivo

Resolver una relación incorrecta o ausente entre una cotización y un ETS.

---

## Contexto requerido

- cotización;
- cliente;
- conceptos;
- ETS;
- factura;
- fechas;
- usuarios;
- origen del vínculo.

---

## Estrategias

- vinculación directa;
- vinculación complementaria;
- creación de nueva cotización;
- rechazo por incompatibilidad;
- resolución manual autorizada.

---

# UC-020 · Resolver dos resoluciones simultáneas sobre la misma entidad

## Tipo de resolución

```text
resolution.resolve_concurrent_cases
```

---

## Objetivo

Evitar que dos resoluciones incompatibles modifiquen el mismo proceso de forma simultánea.

---

## Ejemplo

```text
Resolución A:
Agregar equipos al ETS.

Resolución B:
Cancelar el ETS.
```

---

## Estrategias

### Priorizar una resolución

La otra queda bloqueada o sustituida.

### Fusionar solicitudes

Cuando ambas persiguen un resultado compatible.

### Ejecutar secuencialmente

Cuando el resultado de una es precondición de la otra.

### Rechazar ambas y reconstruir contexto

Cuando el conflicto cambia completamente el problema.

---

## Resultado

Debe quedar registrada la relación entre resoluciones y la razón de la prioridad seleccionada.

---

# UC-021 · Recuperar una ejecución interrumpida

## Tipo de resolución

```text
resolution.recover_interrupted_execution
```

---

## Objetivo

Reconstruir el estado real después de una caída del sistema durante una ejecución.

---

## Contexto requerido

- ejecución;
- pasos registrados;
- claves de idempotencia;
- resultados en módulos;
- locks;
- eventos;
- transacciones confirmadas;
- último heartbeat del worker.

---

## Estrategias

### Continuar

Cuando los pasos previos están confirmados.

### Recuperar resultado previo

Cuando el módulo ejecutó pero el motor no recibió respuesta.

### Reintentar

Cuando se confirma que la operación no ocurrió.

### Bloquear para revisión

Cuando el estado no puede determinarse de forma segura.

### Compensar

Cuando existe una política válida.

---

## Restricción

Nunca se reinicia toda la resolución sin verificar los efectos ya producidos.

---

# UC-022 · Resolver respuesta incierta de un servicio de dominio

## Tipo de resolución

```text
resolution.reconcile_uncertain_domain_operation
```

---

## Disparador

Un módulo recibió una solicitud, pero la conexión terminó antes de devolver el resultado.

---

## Plan

```text
1. Consultar por idempotency_key.
2. Recuperar estado.
3. Si completed, registrar el resultado.
4. Si running, esperar.
5. Si not_found, reintentar.
6. Si failed, aplicar política de error.
```

---

# UC-023 · Resolver un conflicto de versión

## Tipo de resolución

```text
resolution.resolve_version_conflict
```

---

## Objetivo

Responder cuando una entidad cambió después de construir o autorizar el plan.

---

## Ejemplo

```text
Contexto autorizado:
ETS = in_progress

Contexto actual:
ETS = closed
```

---

## Estrategia

No se fuerza la actualización.

El plan se invalida y se construye una nueva estrategia.

---

# UC-024 · Cancelar una resolución antes de ejecutar

## Tipo de resolución

```text
resolution.cancel
```

---

## Objetivo

Detener una resolución que ya no debe continuar.

---

## Precondiciones

- no existe ejecución iniciada;
- el usuario posee permiso;
- se registra el motivo;
- se invalidan autorizaciones pendientes o aprobadas.

---

## Resultado

```text
Resolution = cancelled
```

La resolución permanece consultable.

---

# UC-025 · Cancelar una resolución con ejecución parcial

## Tipo de resolución

```text
resolution.stop_partial_execution
```

---

## Objetivo

Detener nuevas acciones cuando algunos pasos ya fueron ejecutados.

---

## Problema

No puede tratarse como una cancelación ordinaria.

---

## Estrategias

- detener y conservar resultados;
- compensar pasos;
- completar pasos críticos mínimos;
- crear una resolución de recuperación.

---

## Resultado

Podrá ser:

```text
partially_completed
compensated
failed
superseded
```

---

# UC-026 · Sustituir una resolución obsoleta

## Tipo de resolución

```text
resolution.supersede
```

---

## Objetivo

Crear una nueva resolución cuando el problema cambió de naturaleza.

---

## Ejemplo

```text
Resolución original:
Modificar borrador de factura.

Nuevo contexto:
Factura ya emitida.
```

La resolución original se marca como sustituida y se crea:

```text
invoice.modify_after_issue
```

---

# UC-027 · Cerrar una resolución sin acción

## Tipo de resolución

```text
resolution.close_no_action
```

---

## Objetivo

Cerrar formalmente una resolución cuando el problema ya no existe o fue resuelto por otro proceso.

---

## Resultado

```text
no_action_required
```

Debe registrarse:

- qué cambió;
- quién lo cambió;
- por qué ya no se necesita ejecutar;
- qué resolución u operación produjo el resultado.

---

# UC-028 · Autorizar una excepción administrativa

## Tipo de resolución

```text
administration.authorize_exception
```

---

## Objetivo

Permitir una acción normalmente bloqueada por política, sin eliminar la regla general.

---

## Ejemplos

- exceder temporalmente un límite;
- liberar con saldo pendiente;
- reabrir una etapa;
- permitir una firma complementaria;
- continuar con información parcial;
- corregir una relación operativa.

---

## Regla

La excepción debe ser:

- específica;
- limitada;
- temporal cuando corresponda;
- autorizada;
- auditable;
- vinculada con el plan exacto.

No debe convertirse en una desactivación global de la regla.

---

# UC-029 · Resolver datos incompletos de cliente provenientes de importación

## Tipo de resolución

```text
client.resolve_incomplete_import
```

---

## Objetivo

Permitir que un registro importado incompleto sea conciliado sin exigir que el archivo externo contenga desde el inicio todos los datos operativos del ERP.

---

## Contexto requerido

- archivo importado;
- cliente probable;
- RFC;
- razón social;
- régimen fiscal;
- datos faltantes;
- cotizaciones o ETS relacionados;
- duplicados posibles.

---

## Estrategias

- vincular con cliente existente;
- crear cliente provisional;
- solicitar complemento de datos;
- rechazar por conflicto;
- separar información comercial y fiscal.

---

## Restricción

Una importación flexible no debe permitir emisión fiscal con datos incompletos.

---

# UC-030 · Resolver discrepancia de régimen fiscal

## Tipo de resolución

```text
client.resolve_fiscal_regime_mismatch
```

---

## Objetivo

Conciliar un régimen fiscal obtenido desde una constancia con los catálogos SAT disponibles en el ERP.

---

## Contexto requerido

- RFC;
- régimen recibido;
- catálogo SAT vigente;
- fecha de publicación;
- factura en preparación;
- fuente de la constancia;
- datos fiscales guardados.

---

## Estrategias

- mapear equivalencia válida;
- actualizar catálogo oficial;
- solicitar revisión;
- bloquear emisión;
- conservar información provisional sin utilizarla fiscalmente.

---

## Restricción

El motor no inventa claves SAT ni modifica el catálogo para forzar coincidencias.

---

# UC-031 · Resolver inconsistencia entre factura y pago

## Tipo de resolución

```text
invoice.reconcile_payment_state
```

---

## Objetivo

Corregir diferencias entre el estado financiero y el estado visible de la factura.

---

## Ejemplos

- factura marcada como pagada sin aplicación;
- pago aplicado, pero saldo no actualizado;
- certificado bloqueado pese a saldo liquidado;
- aplicación duplicada.

---

## Plan

```text
1. Reconstruir movimientos.
2. Calcular saldo mediante PaymentService.
3. Comparar estado derivado.
4. Identificar la operación inconsistente.
5. Ejecutar corrección mediante el módulo propietario.
6. Actualizar bloqueos o liberaciones derivadas.
```

---

# UC-032 · Resolver documento oficial faltante

## Tipo de resolución

```text
document.recover_missing_official_file
```

---

## Objetivo

Recuperar la relación o archivo de un documento oficial que debería existir.

---

## Ejemplos

- PDF institucional de factura no disponible;
- XML fiscal no vinculado;
- certificado autenticado sin archivo accesible;
- paquete documental incompleto.

---

## Estrategias

- regenerar representación a partir de datos oficiales;
- recuperar archivo desde almacenamiento;
- solicitar nuevamente al proveedor externo;
- marcar evidencia como irrecuperable;
- generar un documento de reconstrucción autorizado.

---

## Restricción

La regeneración de una representación no debe alterar el contenido fiscal o metrológico original.

---

# UC-033 · Resolver folio reservado sin entidad final

## Tipo de resolución

```text
identifier.reconcile_orphan_reservation
```

---

## Objetivo

Conciliar una reserva de folio que no terminó vinculada con una entidad formal.

---

## Contexto requerido

- módulo propietario;
- folio;
- reserva;
- operación que lo solicitó;
- transacción;
- entidad esperada;
- política de reutilización.

---

## Estrategias

- vincular con entidad existente;
- cancelar la reserva;
- marcar folio como consumido;
- liberar para reutilización, únicamente si la política del módulo lo permite.

---

## Regla

El Motor de Resoluciones no decide unilateralmente reutilizar folios.

La decisión pertenece al módulo propietario.

---

# UC-034 · Resolver orden de trabajo huérfana

## Tipo de resolución

```text
work_order.resolve_orphan
```

---

## Objetivo

Resolver una OT sin ETS válido, sin equipos o con referencias incompletas.

---

## Estrategias

- restaurar relación correcta;
- vincular con ETS complementario;
- cancelar operativamente;
- preservar como evidencia técnica;
- crear resolución derivada.

---

# UC-035 · Resolver hoja de campo sin equipo válido

## Tipo de resolución

```text
field_sheet.resolve_orphan
```

---

## Objetivo

Atender una hoja de campo cuya relación con el equipo se perdió o es incorrecta.

---

## Restricción

No debe reasignarse automáticamente basándose sólo en similitud de datos.

Debe evaluarse:

- identificación;
- serie;
- OT;
- ETS;
- usuario;
- fecha;
- certificado;
- contenido de la hoja.

---

# UC-036 · Resolver certificado sin hoja de campo aprobada

## Tipo de resolución

```text
certificate.resolve_missing_approved_field_sheet
```

---

## Objetivo

Resolver una inconsistencia en la que existe un certificado sin la evidencia técnica requerida.

---

## Estrategias

- localizar la hoja correcta;
- restaurar vínculo;
- regresar a Captura;
- invalidar el certificado no autenticado;
- crear nueva versión documental;
- bloquear liberación.

---

# UC-037 · Resolver liberación incorrecta de certificado

## Tipo de resolución

```text
certificate.resolve_incorrect_release
```

---

## Objetivo

Atender un certificado liberado sin cumplir las condiciones requeridas.

---

## Estrategias

- retirar acceso futuro sin borrar evidencia de liberación;
- registrar incidente;
- notificar al cliente;
- crear documento sustituto;
- abrir revisión financiera o de Calidad;
- generar resolución derivada.

---

## Restricción

El sistema no debe reescribir el historial para indicar que nunca fue liberado.

---

# UC-038 · Resolver conflicto entre firma y OT nueva

## Tipo de resolución

```text
signature.resolve_new_work_order_scope
```

---

## Objetivo

Determinar la cobertura de una firma cuando se crea una OT después de la firma global inicial.

---

## Regla

La firma original cubre únicamente el alcance existente en el momento en que fue realizada, salvo que el documento firmado establezca explícitamente otra condición.

---

## Estrategias

- firma complementaria de OT;
- firma general renovada;
- firma del cliente únicamente;
- firma técnica adicional;
- bloqueo del inicio de la nueva OT.

---

# UC-039 · Resolver cambio de técnico después de firma

## Tipo de resolución

```text
signature.resolve_technician_change
```

---

## Objetivo

Actualizar la evidencia de responsabilidad cuando cambia el técnico asignado.

---

## Contexto requerido

- técnico que firmó;
- técnico actual;
- trabajos ejecutados por cada uno;
- OT;
- fecha del cambio;
- hojas de campo;
- firma del cliente.

---

## Estrategias

- firma adicional del nuevo técnico;
- división de responsabilidad por OT;
- conservación de firma anterior;
- reasignación sin nueva firma cuando aún no hubo ejecución, según política.

---

# UC-040 · Resolver un servicio cerrado con actividades pendientes

## Tipo de resolución

```text
service_order.resolve_closed_with_pending_work
```

---

## Objetivo

Atender un ETS cerrado que todavía contiene equipos, hojas, certificados o tareas pendientes.

---

## Estrategias

- reabrir mediante excepción;
- crear ETS complementario;
- cancelar pendientes inválidos;
- finalizar entidades faltantes;
- corregir un cierre técnico erróneo.

---

## Autorización

Debe depender del tipo de actividad pendiente y del impacto histórico.

---

# Matriz resumida de casos

| Caso | Tipo | Módulos principales | Riesgo |
|---|---|---|---|
| Equipos adicionales | `service_order.add_additional_equipment` | ETS, Equipos, OT, Hojas | Medio/Alto |
| Captura offline | `sync.add_offline_equipment` | Sync, ETS, Equipos | Alto |
| Firma adicional | `service_order.request_additional_signature` | ETS, Firmas | Medio |
| Reabrir hoja | `field_sheet.reopen` | Hojas, Calidad | Medio/Alto |
| Corregir certificado autenticado | `certificate.correct_authenticated` | Calidad, Certificados | Crítico |
| Liberar con pago pendiente | `certificate.release_with_payment_exception` | Certificados, Pagos | Alto |
| Modificar factura emitida | `invoice.modify_after_issue` | Facturación, PAC | Crítico |
| Reasignar pago | `payment.reassign` | Pagos, Facturas | Alto |
| Recuperar ejecución | `resolution.recover_interrupted_execution` | Motor, módulos involucrados | Alto |
| Conflicto concurrente | `resolution.resolve_concurrent_cases` | Motor | Alto |

---

# Casos que no pertenecen al motor

No toda validación o error debe convertirse en resolución.

No pertenecen al Motor de Resoluciones:

- campos obligatorios faltantes antes de guardar;
- credenciales incorrectas;
- permisos ordinarios insuficientes;
- error de formato;
- búsqueda sin resultados;
- validaciones normales de catálogo;
- transición ordinaria de estados;
- creación normal de cotización;
- creación normal de ETS;
- emisión normal de factura;
- revisión normal de Calidad;
- liberación normal de certificados.

Estos casos pertenecen a sus módulos y flujos ordinarios.

---

# Criterio para crear un nuevo caso de uso

Un nuevo caso deberá incorporarse al Motor de Resoluciones cuando cumpla una o varias condiciones:

1. El flujo ordinario no puede continuar.
2. Se requiere coordinar varios módulos.
3. Existe historia que no puede alterarse.
4. Hay más de una estrategia válida.
5. La intervención requiere autorización.
6. Debe simularse el impacto antes de actuar.
7. Existe riesgo de duplicidad.
8. Se requiere revalidación de contexto.
9. Puede producirse una ejecución parcial.
10. La decisión debe conservarse como evidencia institucional.

---

# Caso de uso de referencia para la primera implementación

La primera implementación recomendada es:

```text
service_order.add_additional_equipment
```

Este caso permite probar prácticamente todas las capacidades del motor:

- solicitud desde usuario o móvil;
- contexto transversal;
- estrategias alternativas;
- creación de plan;
- simulación;
- autorización;
- revalidación;
- ejecución en varios módulos;
- generación de folios por propietarios;
- idempotencia;
- concurrencia;
- firma complementaria;
- sincronización offline;
- auditoría;
- resultado parcial;
- recuperación ante fallos.

---

# Escenario completo de referencia

## Situación inicial

```text
ETS: en ejecución
Equipos originales: 20
OT existentes: 2
Factura: borrador
Certificados autenticados: 0
Firma global: realizada
```

El técnico registra trece equipos adicionales desde la aplicación móvil.

---

## Contexto inicial

El motor determina:

- el ETS continúa abierto;
- los equipos no existen;
- la factura no ha sido emitida;
- la firma original no cubre los nuevos equipos;
- deben crearse nuevas OT;
- deben generarse hojas de campo.

---

## Plan v1

```text
1. Registrar 13 equipos.
2. Crear 2 OT adicionales.
3. Distribuir los equipos.
4. Crear 13 hojas de campo.
5. Solicitar firma complementaria.
```

---

## Simulación

```text
Entidades esperadas:
13 equipos
2 OT
13 hojas de campo
1 solicitud de firma
```

No se presentan folios definitivos.

---

## Autorización

Comercial autoriza el cambio de alcance.

---

## Cambio de contexto

Antes de ejecutar, Finanzas emite la factura.

---

## Revalidación

```text
invoice.status:
draft → issued
```

Resultado:

```text
requires_new_plan
```

---

## Plan v2

```text
1. Crear cotización complementaria.
2. Crear ETS complementario.
3. Registrar 13 equipos.
4. Crear 2 OT.
5. Crear 13 hojas de campo.
6. Solicitar nuevas firmas.
7. Vincular el ETS complementario con el original.
```

---

## Nueva autorización

El Plan v2 requiere autorización de Comercial y Finanzas.

---

## Ejecución

Cada módulo ejecuta sus propias operaciones y devuelve:

- identificadores;
- folios;
- estados;
- advertencias;
- claves de idempotencia.

---

## Resultado final

```text
Resolution = completed
```

Se preservan:

- ETS original;
- factura original;
- firma original;
- alcance original.

Se crean:

- cotización complementaria;
- ETS complementario;
- OT;
- equipos;
- hojas;
- firmas complementarias.

---

# Criterios de aceptación de casos de uso

Cada caso de uso deberá:

- identificar claramente el problema;
- distinguir flujo ordinario y extraordinario;
- declarar el contexto requerido;
- definir estrategias posibles;
- establecer condiciones de aplicabilidad;
- describir el plan;
- identificar autorizaciones;
- definir datos de revalidación;
- indicar resultados;
- describir fallos posibles;
- preservar historia;
- asignar operaciones a módulos propietarios;
- evitar generación de folios por el motor;
- producir evidencia auditable.

---

# Declaración final

Los casos de uso del Motor de Resoluciones representan intervenciones extraordinarias, no atajos administrativos.

Cada caso deberá demostrar por qué el flujo ordinario dejó de ser suficiente y cómo la resolución recuperará la consistencia sin destruir historia, eliminar evidencia ni transferir reglas de negocio al motor.

El valor del Motor de Resoluciones no consiste en permitir cualquier modificación.

Consiste en permitir únicamente intervenciones explicables, autorizadas, revalidables y auditables cuando el ERP enfrenta una situación que el flujo normal ya no puede resolver.