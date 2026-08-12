# Catálogo de candidatos a excepción — ETS múltiple/evolucionado Fase 1

> Fotografía: 2026-08-12
>
> Estado de todos los registros: `PENDIENTE DE VALIDACIÓN FUNCIONAL`
>
> Este catálogo no autoriza endpoints, resets, borrados ni definiciones del Motor.

## Criterio

Se registraron los puntos extraordinarios encontrados al auditar ETS, OT, Equipos, Cotizaciones, Activity, documentos y Motor. Cuando el lifecycle normal ya ofrece una salida, el candidato se clasifica como posible antipatrón y no como excepción válida.

## EX-ETS-F1-001 — Equipo adicional sin capacidad OT

- Módulo/entidad/estado actual: ETS; `ServiceOrder`/`ServiceWorkOrder`; OT llena.
- Situación y operación solicitada: incorporar equipo adicional y, si corresponde, asignar/crear OT.
- Causa: límite institucional de diez equipos.
- Por qué no se resuelve con lifecycle normal: el alta ordinaria bloquea cuando todas las OT están llenas.
- Solicitante/autorizador posible: Técnico o Comercial / autoridad configurada del Centro.
- Efectos secundarios/documentos: conteos ETS, OT, ciclos de firmas, certificados esperados y facturación contextual.
- Reversibilidad/riesgo: limitada a equipo aún `registered`; alto si ya existe evidencia consumida.
- Alternativa sin excepción: vertical existente `service_order.resolve_additional_equipment@1.0`.
- Propuesta/clasificación: reutilizar vertical existente, nunca endpoint paralelo; excepción operativa ya gobernada.
- Estado: `PENDIENTE DE VALIDACIÓN FUNCIONAL`.

## EX-ETS-F1-002 — Identificación físicamente incompleta

- Módulo/entidad/estado actual: ETS; `ServiceUnit`; alta.
- Situación y operación solicitada: continuar sin marca, modelo o serie legible.
- Causa: placa ausente/ilegible o dato imposible de obtener.
- Por qué no se resuelve con lifecycle normal: sí se resuelve; Fase 1 admite estado `partial` y notas.
- Solicitante/autorizador posible: Técnico / no aplica.
- Efectos secundarios/documentos: los documentos posteriores deben mostrar ausencia documentada, no un valor inventado.
- Reversibilidad/riesgo: editable al obtener dato; riesgo alto sólo si se falsifica identidad.
- Alternativa sin excepción: captura parcial normal.
- Propuesta/clasificación: no crear excepción; posible antipatrón / NO válida como excepción.
- Estado: `PENDIENTE DE VALIDACIÓN FUNCIONAL`.

## EX-ETS-F1-003 — Etapa sin aprobación comercial

- Módulo/entidad/estado actual: ETS; `ServiceStage`; `pending_quote`/`pending_approval`.
- Situación y operación solicitada: ejecutar antes de decisión del cliente.
- Causa: urgencia operativa o demora comercial.
- Por qué no se resuelve con lifecycle normal: el lifecycle permite conservarla pendiente o pausada, pero no ejecutarla.
- Solicitante/autorizador posible: Técnico / por definir institucionalmente; el técnico no autoriza.
- Efectos secundarios/documentos: costos no autorizados, reportes, custodia, facturación y responsabilidad contractual.
- Reversibilidad/riesgo: baja reversibilidad una vez intervenido el equipo; riesgo alto.
- Alternativa sin excepción: obtener aprobación, acotar diagnóstico autorizado o no ejecutar.
- Propuesta/clasificación: candidato de autorización/comercial; no implementar hasta validación.
- Estado: `PENDIENTE DE VALIDACIÓN FUNCIONAL`.

## EX-ETS-F1-004 — Cierre documental imposible

- Módulo/entidad/estado actual: ETS/Documentos; `ServiceStage`; en ejecución o pausada.
- Situación y operación solicitada: cerrar una etapa cuando un reporte/evidencia obligatoria no puede producirse.
- Causa: daño de archivo, imposibilidad física o tercero incumplido.
- Por qué no se resuelve con lifecycle normal: `completed` implicaría falsamente cumplimiento.
- Solicitante/autorizador posible: Técnico o Calidad / Calidad o autoridad documental.
- Efectos secundarios/documentos: reporte de etapa, certificado, hoja, expediente y liberación.
- Reversibilidad/riesgo: cierre excepcional debe ser append-only; riesgo documental alto.
- Alternativa sin excepción: `paused`/`not_executable`, nueva evidencia o repetición controlada.
- Propuesta/clasificación: excepción documental; posible `exception_closed` sólo mediante resolución explícita futura.
- Estado: `PENDIENTE DE VALIDACIÓN FUNCIONAL`.

## EX-ETS-F1-005 — Liberación de custodia con servicio pausado

- Módulo/entidad/estado actual: ETS/Custodia; unidad con etapa `paused`, `client_rejected` o `not_executable`.
- Situación y operación solicitada: devolver físicamente el equipo sin declarar terminado el servicio.
- Causa: rechazo, espera prolongada o solicitud del cliente.
- Por qué no se resuelve con lifecycle normal: no existe contrato persistente de custodia/devolución por unidad.
- Solicitante/autorizador posible: Técnico/Comercial / responsable de custodia.
- Efectos secundarios/documentos: acuse de entrega, firmas, etapas abiertas y responsabilidades.
- Reversibilidad/riesgo: nueva recepción sería otro evento; riesgo medio/alto de pérdida de jurisdicción.
- Alternativa sin excepción: mantener pausado y documentar Activity, insuficiente como autoridad de custodia.
- Propuesta/clasificación: excepción de custodia; requiere antes modelo/flujo de custodia.
- Estado: `PENDIENTE DE VALIDACIÓN FUNCIONAL`.

## EX-ETS-F1-006 — Error de vinculación de unidad, OT o etapa

- Módulo/entidad/estado actual: ETS/Datos; entidad ya persistida sin evidencia consumida.
- Situación y operación solicitada: corregir vínculo capturado equivocadamente.
- Causa: error humano o importación histórica.
- Por qué no se resuelve con lifecycle normal: la identidad y secuencia se protegen para no reescribir historia.
- Solicitante/autorizador posible: Operación / Administrador con revisión de integridad.
- Efectos secundarios/documentos: Activity, tareas, cotizaciones, reportes, certificados y firmas.
- Reversibilidad/riesgo: viable sólo antes de consumo; riesgo alto después.
- Alternativa sin excepción: cancelar/sustituir unidad o agregar etapa correctiva conservando anterior.
- Propuesta/clasificación: corrección de datos; definir resolución con precondiciones estrictas, no SQL/manual.
- Estado: `PENDIENTE DE VALIDACIÓN FUNCIONAL`.

## EX-ETS-F1-007 — Falla de integración durante autorización

- Módulo/entidad/estado actual: Cotización/ETS; decisión registrada o transacción fallida.
- Situación y operación solicitada: conciliar una respuesta externa incierta de portal/app antes de materializar etapas.
- Causa: timeout o entrega repetida.
- Por qué no se resuelve con lifecycle normal: la Fase 1 sólo implementa origen interno; integraciones futuras requieren idempotencia externa.
- Solicitante/autorizador posible: Integración / servicio de conciliación y autoridad comercial.
- Efectos secundarios/documentos: decisión por partida, etapas y notificación.
- Reversibilidad/riesgo: nunca repetir a ciegas; riesgo de duplicar autorizaciones.
- Alternativa sin excepción: clave idempotente y consulta de conciliación del proveedor.
- Propuesta/clasificación: excepción de integración futura; priorizar conciliación determinista.
- Estado: `PENDIENTE DE VALIDACIÓN FUNCIONAL`.

## EX-ETS-F1-008 — Revertir decisión comercial sobrescribiendo historial

- Módulo/entidad/estado actual: Cotizaciones; `QuotationItemDecision`; decidida.
- Situación y operación solicitada: cambiar aprobada↔rechazada sobre la misma decisión.
- Causa: cambio de opinión o captura incorrecta.
- Por qué no se resuelve con lifecycle normal: la decisión es append-only y pudo habilitar trabajo.
- Solicitante/autorizador posible: Comercial/cliente / autoridad comercial por definir.
- Efectos secundarios/documentos: etapas, costos, PDF, aceptación e historial.
- Reversibilidad/riesgo: alto; el trabajo físico puede ser irreversible.
- Alternativa sin excepción: nueva versión/decisión formal compensatoria y cancelación de etapas no iniciadas.
- Propuesta/clasificación: posible antipatrón / NO válida como reset; diseñar rama comercial formal.
- Estado: `PENDIENTE DE VALIDACIÓN FUNCIONAL`.

## EX-ETS-F1-009 — Eliminar etapa histórica

- Módulo/entidad/estado actual: ETS; `ServiceStage`; cualquier estado.
- Situación y operación solicitada: borrar etapa errónea o ya no requerida.
- Causa: error de planeación o rechazo posterior.
- Por qué no se resuelve con lifecycle normal: borrar destruye la ruta y referencias.
- Solicitante/autorizador posible: Operación / no debe autorizarse como delete.
- Efectos secundarios/documentos: solicitudes, Activity, tareas, partidas, decisiones y reportes.
- Reversibilidad/riesgo: no reversible; riesgo crítico de integridad.
- Alternativa sin excepción: `cancelled`, `client_rejected`, sustitución o nueva etapa.
- Propuesta/clasificación: posible antipatrón / NO válida como excepción.
- Estado: `PENDIENTE DE VALIDACIÓN FUNCIONAL`.

## EX-ETS-F1-010 — Eliminar cotización aprobada u OT utilizada

- Módulo/entidad/estado actual: Ventas/OT; documento aceptado u OT con expediente.
- Situación y operación solicitada: borrar o regresar estado para rehacer el flujo.
- Causa: corrección tardía.
- Por qué no se resuelve con lifecycle normal: rompe antecedentes comerciales, firmas y trazabilidad.
- Solicitante/autorizador posible: Comercial/Operación / no aplica para borrado.
- Efectos secundarios/documentos: todos los descendientes ETS, fiscales, técnicos y documentales.
- Reversibilidad/riesgo: no reversible; riesgo crítico.
- Alternativa sin excepción: cancelación, sustitución, revisión, reapertura controlada o compensación.
- Propuesta/clasificación: posible antipatrón / NO válida como excepción.
- Estado: `PENDIENTE DE VALIDACIÓN FUNCIONAL`.

## EX-ETS-F1-011 — Borrar documento autenticado o resetear proceso terminado

- Módulo/entidad/estado actual: Certificados/ETS; autenticado, liberado o cerrado.
- Situación y operación solicitada: eliminar evidencia o regresar mediante reset directo.
- Causa: error descubierto después del cierre.
- Por qué no se resuelve con lifecycle normal: la evidencia autenticada y estados terminales son históricos.
- Solicitante/autorizador posible: Calidad/Operación / Motor y autoridad vigente según caso ya definido.
- Efectos secundarios/documentos: autenticación pública, liberación, facturación y auditoría.
- Reversibilidad/riesgo: crítico; afecta autenticidad e integridad.
- Alternativa sin excepción: retiro futuro, sustitución, nueva versión o vertical existente de certificado incorrectamente liberado.
- Propuesta/clasificación: posible antipatrón / NO válida como `force-delete/reset/close`.
- Estado: `PENDIENTE DE VALIDACIÓN FUNCIONAL`.

## Antipatrones explícitos

`EX-ETS-F1-002`, `008`, `009`, `010` y `011` están clasificados como posible antipatrón / NO válidos como excepción en su forma solicitada. Tampoco se autoriza ningún `force-delete`, `force-reset` o `force-close`.
