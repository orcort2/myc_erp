> Estado: AUDITORÍA
>
> Tipo: Fotografía técnica y funcional
>
> Corte verificado: 2026-07-22
>
> Autoridad: Media; el código vigente prevalece y `../project/PROJECT_STATUS.md` conserva la autoridad sobre avance

# Auditoría de matriz de excepciones del ERP MYC

## 1. Resumen ejecutivo

Se revisaron **60 escenarios** en autenticación, clientes, cotizaciones, Agenda/Llamados, ETS, OT, equipos, firmas, Hojas de Campo, Captura, Calidad, Certificados, Control Documental, Facturación, pagos, crédito, liberación, cancelaciones, metrología e integraciones. El resultado no autoriza implementar cambios.

El sistema posee dos mecanismos que pueden considerarse excepciones controladas, aunque acotadas: aceptación manual de discrepancia de PDF de certificado y excepción de incertidumbre. La operación denominada `service_order.exception_requested` es sólo parcial: cambia el ETS y resincroniza borradores en la misma transacción; no persiste solicitud, aprobación y ejecución como momentos distintos. Se identificaron **18 excepciones faltantes**, **3 parciales**, **24 escenarios con riesgo crítico y prioridad P0**, además de dos escenarios P0 de riesgo alto, y múltiples funciones futuras que no deben disfrazarse de excepciones.

Los módulos más dependientes son ETS/Equipos, porque alimentan OT, firmas, Hojas, folios, Certificados, Calidad, Facturación y Liberación; y Facturación, porque concentra efectos fiscales, saldo y compuerta de entrega. La prioridad recomendada es: (1) cerrar autorización backend y neutralizar mutaciones sensibles abiertas; (2) separar `requested`, `approved` y `executed`; (3) implementar excepciones de alcance/firma; (4) excepciones financieras; (5) fiscales, únicamente después de cerrar cancelación/sustitución y complementos.

### Conteo por clasificación principal

| Clasificación | Escenarios |
| --- | ---: |
| A. Flujo normal | 5 |
| B. Validación automática | 6 |
| C. Bloqueo obligatorio | 6 |
| D. Excepción operativa | 7 |
| E. Excepción administrativa | 10 |
| F. Excepción financiera | 2 |
| G. Excepción fiscal | 4 |
| H. Incidencia técnica | 3 |
| I. Riesgo de integridad de datos | 14 |
| J. Funcionalidad no implementada | 3 |
| **Total** | **60** |

## 2. Criterio y limitaciones

Una excepción es una autorización extraordinaria trazable; no es una validación ordinaria, un error de red, una transición normal ni un mecanismo para borrar historia. Cada fila usa una única clasificación principal A–J, aunque el impacto pueda cruzar dominios. `approved` nunca equivale a `executed`: la ejecución debe ser idempotente, auditable y capaz de fallar sin perder la autorización.

La revisión fue estática y de sólo lectura sobre código, migraciones y documentación. No se cambiaron código, estados, datos ni esquema; no se ejecutaron mutaciones E2E. Agenda y Llamados no tienen entidad propia: se auditan como `agenda_date` y estado `called` del ETS. Crédito, complemento de pago y estado de cuenta no tienen agregado operativo completo. Las reglas no demostrables se marcan como decisión pendiente.

## 3. Estado general por módulo

| Módulo | Estado | Dictamen para excepciones |
| --- | --- | --- |
| Usuarios, roles y permisos | EN DESARROLLO | Matriz en código, pero registro público admite roles y varios routers carecen de control backend. |
| Clientes | CASI SELLADO | Archivo/restauración y elegibilidad están controlados; operaciones principales no exigen permiso uniforme. |
| Cotizaciones | CASI SELLADO | Estados terminales bloquean edición; falta versionado/cambio autorizado posterior a aceptación. |
| Agenda | PENDIENTE | Sólo fecha dentro de ETS; sin reprogramación autorizada ni bitácora propia. |
| Llamados | PENDIENTE | Sólo estado `called`; sin intentos, resultado o reversión controlada. |
| ETS | EN DESARROLLO | Flujo amplio, pero router/servicio duplicados y “excepción” sin aprobación separada. |
| Órdenes de trabajo | CASI SELLADO | Agrupación/cupo existen; faltan reequilibrio, retiro y refirma controlados. |
| Equipos | CASI SELLADO | Estados y capacidad existen; baja/reasignación no propagan efectos posteriores. |
| Firmas | EN DESARROLLO | Ciclos y vínculos OT existen; reapertura/refirma declarada pero no implementada. |
| Hojas de Campo | EN DESARROLLO | Edición y avance auditados; cancelación no valida dependencias posteriores. |
| Captura | EN DESARROLLO | Readiness automático; faltan resolución formal de no identificados y reentrada integral. |
| Calidad | EN DESARROLLO | Corrección y aprobación existen; aceptación manual es excepción real. |
| Certificados | CASI SELLADO | Autenticación/liberación bloqueadas correctamente; cancelación y suspensión requieren mayor contrato. |
| Control Documental V1 | SELLADO | Versionado activo/obsoleto y permisos existen; falta política ante uso histórico de versión suspendida. |
| Facturación | EN DESARROLLO | Workbench y emisión Sandbox existen; cancelación/sustitución y estados de pago presentan huecos críticos. |
| Pagos/CxC/Crédito | EN DESARROLLO | Registro y consultas parciales; corrección, devolución, crédito y complementos están incompletos. |
| Liberación | CASI SELLADO | Compuerta pago/no pago está centralizada; crédito y liberación extraordinaria no existen. |
| Metrología/Incertidumbre | EN DESARROLLO | Excepción de incertidumbre existe, pero motores no están integrados al flujo completo. |
| Integraciones externas | EN DESARROLLO | Facturama Sandbox posee reconciliación; Producción, cancelación y Drive no están implementados. |

## 4. Matriz consolidada

Las tablas siguientes forman una sola matriz; se separan únicamente para mantener legibilidad.

### 4.1 Seguridad, clientes, cotizaciones, Agenda y Llamados

| ID | Módulo | Submódulo | Entidad | Estado origen | Acción o evento | Flujo normal esperado | Conflicto posible | Clasificación | ¿Requiere excepción? | Tipo de excepción propuesto | Solicitante | Resolutor | Datos requeridos | Impacto | Registros relacionados | Acción al aprobar | Acción al rechazar | Posibilidad de continuar trabajando | Riesgo de integridad | Evidencia en código | Archivos involucrados | Estado actual de implementación | Prioridad | Recomendación |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| EX-001 | Seguridad | Registro | User/Role | Sin sesión | Registrar usuario solicitando rol privilegiado | Alta pública sin privilegios | Escalación directa | I. Riesgo de integridad de datos | No | Ninguna | — | — | identidad | Acceso global | usuarios, roles, auditoría | Bloquear payload privilegiado | Rechazar alta | No | Crítico | `register_user` consume `role_names` | `backend/app/services/auth.py`, `backend/app/routers/auth.py` | Implementado inseguro | P0 | Corregir autorización; no crear excepción. |
| EX-002 | Seguridad | JWT | User | Token refresh | Usarlo como bearer | Aceptar sólo access token | El tipo no se valida en usuario actual | I. Riesgo de integridad de datos | No | Ninguna | — | — | token_type | Acceso a toda API | usuarios | Rechazar | Rechazar | No | Crítico | `get_current_user` decodifica sin exigir `access` | `backend/app/services/auth.py`, `backend/app/core/security.py` | Implementado inseguro | P0 | Bloqueo técnico y pruebas 401. |
| EX-003 | Usuarios | Administración | User/Role | Activo | Cambiar rol/estado | Administrador autorizado; proteger último admin y autocambio | Pérdida de administración | B. Validación automática | No | Ninguna | Admin | Backend | roles, actor | Seguridad | usuarios, roles, audit_logs | Aplicar cambio auditado | 409 | Sí | Bajo | Blindajes de último admin/autodesactivación | `backend/app/services/users.py`, `backend/app/routers/users.py` | Implementado | P1 | Conservar; añadir pruebas de matriz. |
| EX-004 | Clientes | Archivo | Client | Activo con historia | Eliminar cliente | Archivar si hay dependencias; hard delete sólo sin historia | Pérdida de trazabilidad | B. Validación automática | No | Ninguna | Comercial | Backend | conteos de dependencias | Todo el expediente | cotizaciones, ETS, equipos, hojas, certificados, facturas, pagos | Archivar o borrar sólo elegible | Bloquear | Sí | Alto | `get_client_delete_eligibility` | `backend/app/services/clients.py`, `backend/app/routers/clients.py` | Implementado | P1 | Mantener semántica. |
| EX-005 | Clientes | Restauración | Client | Archivado | Restaurar RFC duplicado | Bloquear duplicado | Dos identidades fiscales | C. Bloqueo obligatorio | No | Ninguna | Comercial | Backend | RFC | Fiscal/comercial | clientes | Restaurar sólo sin colisión | Mantener archivado | Sí | Alto | validación RFC en restore | `backend/app/services/clients.py` | Implementado | P1 | No exceptuar unicidad fiscal. |
| EX-006 | Clientes | API | Client/Profile | Cualquiera | Crear/editar/importar sin permiso backend | Exigir permiso explícito | Mutación no autorizada | I. Riesgo de integridad de datos | No | Ninguna | — | — | actor | Comercial/fiscal | clientes, perfiles, archivos | No aplica | 401/403 | No | Crítico | sólo archive/restore/delete usan `require_permission` | `backend/app/routers/clients.py` | Brecha existente | P0 | Deny-by-default. |
| EX-007 | Clientes | Fiscal | Client | Activo | Corregir RFC/razón fiscal tras CFDI | Conservar snapshot histórico y aplicar sólo hacia futuro | Reescritura fiscal retroactiva | E. Excepción administrativa | Sí | Corrección fiscal de maestro | Comercial | Finanzas/Admin | motivo, evidencia, vigencia | Facturas futuras | cliente, invoices, snapshots | Versionar dato; no tocar CFDI emitido | Conservar maestro | Sí | Alto | snapshots fiscales en Invoice; update cliente separado | `backend/app/models/client.py`, `backend/app/models/invoice.py`, `backend/app/services/clients.py` | Faltante | P1 | Excepción con vigencia y alcance explícito. |
| EX-008 | Cotizaciones | Estados | Quotation | draft/sent/waiting | Transición permitida | Usar tabla de transiciones | Salto de estado | A. Flujo normal | No | Ninguna | Comercial | Backend | estado destino | Comercial | cotización, snapshots | Transicionar y auditar | 409 | Sí | Bajo | `ALLOWED_TRANSITIONS` | `backend/app/services/quotations.py`, `backend/app/schemas/quotation.py` | Implementado | P2 | Conservar. |
| EX-009 | Cotizaciones | Aceptada | Quotation | accepted | Editar encabezado/partidas | Inmutable; nueva versión o excepción acotada | ETS/factura ya no coinciden | E. Excepción administrativa | Sí | Corrección comercial postaceptación | Comercial | Admin/Comercial superior | motivo, campos, downstream | ETS, factura | cotización, items, ETS, invoice | Clonar versión y evaluar propagación | Conservar original | Sí, con original | Alto | terminal bloqueado; no hay versionado posterior | `backend/app/services/quotations.py`, `backend/app/models/quotation.py` | Faltante | P1 | Nunca editar historia in-place. |
| EX-010 | Cotizaciones | Snapshots | QuotationSnapshot | Cualquiera | Restaurar snapshot | Recuperar composición completa | Sólo encabezado vuelve; partidas divergen | I. Riesgo de integridad de datos | No | Ninguna hasta corregir restauración | Comercial | — | snapshot completo | Precio/alcance | cotización, items, ETS | Restauración atómica | No ejecutar | Sí | Alto | restore no recompone items | `backend/app/services/quotations.py`, `backend/app/models/quotation.py` | Parcial | P1 | Corregir mecanismo normal antes de exceptuar. |
| EX-011 | Cotizaciones | API | Quotation | Cualquiera | Mutar sin permiso backend | Exigir Comercial autorizado | Cambios anónimos | I. Riesgo de integridad de datos | No | Ninguna | — | — | actor | Comercial/fiscal | cotización, ETS, invoices | No aplica | 401/403 | No | Crítico | usuario opcional/sin `require_permission` | `backend/app/routers/quotations.py` | Brecha existente | P0 | Autorizar todas las mutaciones. |
| EX-012 | Agenda | Reprogramación | ServiceOrder.agenda_date | scheduled/confirmed | Cambiar visita | Reprogramar con motivo y notificación | Firmas/recursos/cliente desalineados | D. Excepción operativa | Sí | Reprogramación de servicio | Comercial/Operación | Coordinador/Admin | fecha previa/nueva, motivo | ETS/técnico/cliente | ETS, técnico, auditoría | Cambiar fecha, auditar, notificar | Mantener fecha | Sí | Medio | campo en ETS; sin entidad Agenda | `backend/app/models/service_order.py`, `backend/app/schemas/service_order.py` | Faltante | P1 | Definir corte desde el que requiere autorización. |
| EX-013 | Llamados | Registro | ServiceOrder | confirmed | Marcar called | Transición normal | No hay intentos ni resultado | A. Flujo normal | No | Ninguna | Operación | Backend | estado | ETS | ETS | Cambiar estado | 409 | Sí | Bajo | transición `confirmed→called` | `backend/app/services/service_orders.py` | Parcial | P2 | Agregar bitácora operativa, no excepción. |
| EX-014 | Llamados | Corrección | ServiceOrder | called | Revertir llamado erróneo | Corrección autorizada trazable | Estado no permite retroceso | D. Excepción operativa | Sí | Corrección de llamado | Operación | Coordinador | motivo/evidencia | Agenda/ETS | ETS, auditoría | Registrar corrección sin borrar evento | Mantener called | Sí | Medio | no existe transición inversa ni entidad | `backend/app/services/service_orders.py` | Faltante | P2 | Resolver con evento compensatorio. |

### 4.2 ETS, OT, equipos y firmas

| ID | Módulo | Submódulo | Entidad | Estado origen | Acción o evento | Flujo normal esperado | Conflicto posible | Clasificación | ¿Requiere excepción? | Tipo de excepción propuesto | Solicitante | Resolutor | Datos requeridos | Impacto | Registros relacionados | Acción al aprobar | Acción al rechazar | Posibilidad de continuar trabajando | Riesgo de integridad | Evidencia en código | Archivos involucrados | Estado actual de implementación | Prioridad | Recomendación |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| EX-015 | ETS | Estados | ServiceOrder | No terminal | Avanzar por transición permitida | Respetar máquina de estados | Salto invalida dependencias | A. Flujo normal | No | Ninguna | Operación | Backend | estado destino | Global | ETS y derivados | Transicionar/auditar | 409 | Sí | Medio | `ALLOWED_TRANSITIONS` | `backend/app/services/service_orders.py`, `backend/app/schemas/service_order.py` | Implementado | P1 | Hacer al servicio única fuente. |
| EX-016 | ETS | Excepción actual | ServiceOrder | Cualquiera mapeado | `register_service_order_exception` | Solicitar, aprobar y luego ejecutar | Mutación inmediata sin aprobación | I. Riesgo de integridad de datos | Sí | Cambio extraordinario de etapa | Usuario operativo | Responsable por categoría | origen/destino/motivo/payload | ETS, invoice | ETS, quotation, invoices, audit | Aprobar primero; ejecutar idempotente después | Mantener estado | Sí | Crítico | cambia estado, resincroniza y audita `exception_requested` | `backend/app/routers/service_orders.py`, `backend/app/services/invoices.py` | Parcial e incorrectamente acoplado | P0 | Separar requested/approved/executed. |
| EX-017 | ETS | Arquitectura | ServiceOrder | Cualquiera | Ejecutar reglas duplicadas | Una capa de servicio | Router y servicio divergen | I. Riesgo de integridad de datos | No | Ninguna | — | — | — | Todo ETS | todas las dependencias | No aplica | Bloquear refactor incompleto | Sí | Crítico | lógica material duplicada | `backend/app/routers/service_orders.py`, `backend/app/services/service_orders.py` | Deuda existente | P0 | Consolidar antes del motor. |
| EX-018 | ETS | Firmas | SignatureCycle | Pendiente | Confirmar firmas | Tres firmas completas y OTs pendientes | Ruta duplicada y actor opcional | I. Riesgo de integridad de datos | No | Ninguna | Técnico/cliente | Backend | imágenes, nombres, fechas | Evidencia legal | ETS, OT, ciclos | Crear ciclo una vez | 409 | Sí | Alto | dos rutas `confirm-signatures`; optional user | `backend/app/routers/service_orders.py`, `backend/app/models/service_order.py` | Implementado con duplicidad | P0 | Unificar endpoint y exigir actor. |
| EX-019 | ETS | Pausa | ServiceOrder | in_progress | Pausar/reanudar | Registrar pausa, causa y tiempos | No hay estados/eventos | J. Funcionalidad no implementada | No por ahora | Ninguna hasta definir regla | Operación | — | causa/tiempos | SLA/agenda | ETS, OT | No aplica | No aplica | Sí, fuera del sistema | Medio | estados no incluyen pause | `backend/app/schemas/service_order.py`, `backend/app/services/service_orders.py` | No implementado | P2 | Decidir si es requisito; luego flujo normal. |
| EX-020 | ETS | Cliente | ServiceOrder | Creado | Cambiar cliente | No permitido tras origen comercial salvo corrección autorizada | Toda cadena queda a cliente distinto | E. Excepción administrativa | Sí | Corrección de cliente ETS | Comercial | Admin + Calidad/Finanzas según avance | cliente anterior/nuevo, motivo | Total | quote, equipos, hojas, certificados, invoice | Revalidar/invalidar por etapa; preservar snapshots | Mantener cliente | Sí según etapa | Crítico | update schema no expone client; enlaces rígidos | `backend/app/schemas/service_order.py`, `backend/app/models/service_order.py` | Faltante | P0 | Prohibir después de CFDI/certificado; crear nueva operación si aplica. |
| EX-021 | ETS | Alcance | ServiceOrder | Servicio iniciado | Cambiar alcance | Nueva cotización/versión y evaluación downstream | Firma, hojas, certificado y factura divergen | E. Excepción administrativa | Sí | Cambio de alcance postinicio | Comercial/Técnico | Admin/Comercial superior | delta, motivo, cotización | Total | quote, ETS, OT, equipos, firmas, invoice | Crear delta trazable y tareas compensatorias | Conservar alcance | Sí, sin ejecutar delta | Crítico | no existe mutación de items; excepción salta etapa | `backend/app/models/service_order.py`, `backend/app/services/service_orders.py` | Faltante | P0 | No resincronizar emitidos ni reescribir snapshots. |
| EX-022 | ETS | Cancelación | ServiceOrder | No terminal | Cancelar total | Transición permitida con efectos definidos | Derivados activos quedan vivos | I. Riesgo de integridad de datos | Sí | Cancelación administrativa coordinada | Comercial/Operación | Admin | motivo, alcance, derivados | Total | OT, equipos, hojas, certs, invoices, pagos | Orquestar cancelaciones compatibles | Mantener ETS | Sí según seguridad | Crítico | deactivación sólo ETS/OT | `backend/app/services/service_orders.py`, `backend/app/models/service_order.py` | Parcial | P0 | Diseñar saga y compensaciones. |
| EX-023 | OT | Cupo | ServiceWorkOrder | 10 equipos | Agregar equipo adicional | Crear/rebalancear OT bajo regla | Servicio bloquea con mensaje de excepción | D. Excepción operativa | Sí | OT adicional por exceso | Técnico/Operación | Coordinador | equipo, servicio, cupos | OT/firmas | ETS, OT, equipo, firma | Crear OT, incluir en nuevo ciclo de firma | No crear equipo | Sí, otros equipos | Alto | 409 cuando todas OTs llenas | `backend/app/services/equipment.py`, `backend/app/models/service_order.py` | Faltante | P1 | Automatizar si regla lo permite; si no, aprobar antes del alta. |
| EX-024 | OT | Reasignación | Equipment | Sin documentos | Mover equipo entre OTs | Validar pertenencia y cupo | Firma/carpeta/folio puede quedar ligada a OT previa | D. Excepción operativa | Sí, si ya firmado | Reasignación OT postfirma | Técnico | Coordinador/Calidad | OT origen/destino, motivo | Firma/documentos | equipo, OTs, ciclos, documentos | Mover y crear refirma; conservar historial | Mantener OT | Sí | Alto | sólo valida cupo/pertenencia | `backend/app/services/equipment.py`, `backend/app/models/service_order.py` | Parcial | P1 | Normal antes de firma; excepción después. |
| EX-025 | OT | Legacy | ServiceOrder/ServiceWorkOrder | Cualquiera | Usar número OT legacy y entidad nueva | Fuente única | Dos conceptos pueden divergir | I. Riesgo de integridad de datos | No | Ninguna | — | — | uso real | Documentos/folios | ETS, OT, equipos | No aplica | No aplica | Sí | Alto | `work_order_number` coexiste con OTs | `backend/app/models/service_order.py` | Deuda existente | P1 | Medir/migrar con compatibilidad. |
| EX-026 | Equipos | Alta | Equipment | ETS activo | Agregar dentro de cupo | Validar ETS, partida, OT y capacidad; crear certificado esperado | — | B. Validación automática | No | Ninguna | Técnico | Backend | equipo, item, OT | Cadena técnica | ETS, OT, certificado, snapshot | Crear y sincronizar | 409/422 | Sí | Bajo | `create_equipment` | `backend/app/services/equipment.py` | Implementado | P1 | Conservar. |
| EX-027 | Equipos | Cantidad cotizada | Equipment | ETS activo | Exceder cantidad esperada | Definir si es extra comercial | Factura/cotización no cubren servicio | E. Excepción administrativa | Sí | Equipo adicional no cotizado | Técnico/Comercial | Comercial superior | equipo, diferencia, precio | Comercial/fiscal | quote, ETS, invoice | Crear ajuste comercial y equipo | No crear adicional | Sí | Alto | conteos/cupo OT, sin regla comercial de excedente | `backend/app/services/equipment.py`, `backend/app/models/quotation.py` | Faltante | P1 | Decidir tolerancia y fuente de precio. |
| EX-028 | Equipos | No realizado | Equipment | registered/realizing/calibrated | Marcar `not_done` | Conservar evidencia y excluir de completado facturable según regla | `not_done` cuenta como completado; comentario opcional | D. Excepción operativa | Sí si ya produjo derivados | Retiro/no realizado | Técnico | Coordinador | motivo, evidencia, etapa | ETS/certificado/factura | equipo, hoja, certificado, invoice | Conservar registro, invalidar pendientes compatibles | Mantener estado previo | Sí | Alto | estado terminal y `COMPLETED_STATUSES`; comment opcional | `backend/app/services/equipment.py`, `backend/app/schemas/equipment.py` | Parcial | P1 | Definir efectos y motivo obligatorio. |
| EX-029 | Equipos | Cancelación | Equipment | No terminal | Marcar cancelled | Conservar evidencia y propagar | Derivados quedan activos | D. Excepción operativa | Sí si hay derivados | Cancelación parcial de equipo | Técnico/Comercial | Coordinador/Admin | motivo, derivados | Toda cadena | equipo, hoja, cert, firma, invoice | Cancelar coordinadamente sin borrar | Mantener activo | Sí | Crítico | `deactivate_equipment` sólo baja equipo/sincroniza conteos | `backend/app/services/equipment.py` | Parcial | P0 | No usar baja simple después de hoja/folio. |
| EX-030 | Equipos | Eliminación física | Equipment | Cualquiera | Borrar registro | Nunca con historia | Pérdida probatoria | C. Bloqueo obligatorio | No | Ninguna | — | — | dependencias | Total | toda cadena | No ejecutar | Bloquear | Sí | Crítico | sólo existe soft delete | `backend/app/services/equipment.py`, `backend/app/models/equipment.py` | Bloqueo implícito correcto | P0 | Mantener; distinguir retirar/cancelar. |
| EX-031 | Equipos | Cambio alcance acreditación | Equipment | Certificado activo | Cambiar `calibration_scope` | Bloquear; nueva corrección controlada | Mensaje propone desactivar/recrear certificado | E. Excepción administrativa | Sí | Corrección de modalidad | Técnico/Calidad | Calidad/Admin | valor previo/nuevo, evidencia | Folio/Master/certificado | equipo, snapshot, folio, certificado | Invalidar sólo artefactos no liberados; preservar historial | Mantener modalidad | Sí | Crítico | cambio bloqueado con certificado activo | `backend/app/services/equipment.py`, `backend/app/schemas/service_scope.py` | Bloqueo; excepción faltante | P1 | Nunca resolver borrando certificado histórico. |
| EX-032 | Firmas | Cambio posterior | SignatureCycle | Confirmed | Cambiar técnico/equipo/OT/alcance | Requerir nueva firma cuando cambie lo firmado | Firma ya no representa alcance | D. Excepción operativa | Sí | Reapertura y refirma | Técnico/Operación | Coordinador | delta, ciclo afectado, motivo | Evidencia legal | ETS, OT, equipos, ciclos | Cerrar ciclo anterior y crear adicional | Conservar firma vigente | Sí, salvo actividad afectada | Crítico | permiso/fields de reopen sin servicio; updates no invalidan | `backend/app/core/permissions.py`, `backend/app/models/service_order.py`, `backend/app/services/service_orders.py` | Sólo documentado/parcial | P0 | Refirma general y por OT, sin sobrescribir firmas. |

### 4.3 Hojas, Captura, Calidad, Certificados y documentos

| ID | Módulo | Submódulo | Entidad | Estado origen | Acción o evento | Flujo normal esperado | Conflicto posible | Clasificación | ¿Requiere excepción? | Tipo de excepción propuesto | Solicitante | Resolutor | Datos requeridos | Impacto | Registros relacionados | Acción al aprobar | Acción al rechazar | Posibilidad de continuar trabajando | Riesgo de integridad | Evidencia en código | Archivos involucrados | Estado actual de implementación | Prioridad | Recomendación |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| EX-033 | Hojas de Campo | Edición | FieldSheet | draft/in_progress/rejected/returned | Editar contenido | Sólo estados editables; snapshot de plantilla | — | A. Flujo normal | No | Ninguna | Técnico | Backend | campos/resultados | Técnico | equipo, patrones, certificado | Guardar/auditar | 409 | Sí | Bajo | `EDITABLE_STATUSES` | `backend/app/services/field_sheets.py` | Implementado | P2 | Conservar. |
| EX-034 | Hojas de Campo | Completar | FieldSheet | editable | Completar | Validar campos; calibrar equipo; preparar certificado | Automatización parcial puede adelantar certificado | B. Validación automática | No | Ninguna | Técnico | Backend | readiness | Equipos/Certificados | hoja, equipo, certificado | Cambiar estados atómicamente | 409/422 | Sí | Medio | `complete_field_sheet` | `backend/app/services/field_sheets.py` | Implementado | P1 | Cubrir con E2E por familia. |
| EX-035 | Hojas de Campo | Cancelación | FieldSheet | No terminal | Desactivar hoja | Sólo si no alimentó artefactos posteriores | Certificado/captura queda referenciando hoja inactiva | I. Riesgo de integridad de datos | Sí | Cancelación técnica de hoja | Técnico | Calidad/Coordinador | motivo, derivados | Captura/Calidad | hoja, equipo, certificado, archivo | Invalidar/reabrir derivados permitidos | Mantener hoja | Sí | Alto | `deactivate_field_sheet` no inspecciona certificado | `backend/app/services/field_sheets.py` | Parcial | P1 | Exigir motivo y mapa de impacto. |
| EX-036 | Hojas de Campo | Patrón | FieldSheet | in_progress | Patrón vence durante servicio | Bloquear uso no válido; decidir continuidad de datos ya capturados | Resultado metrológico comprometido | C. Bloqueo obligatorio | Sí sólo para disposición posterior | Patrón vencido detectado después | Técnico | Calidad | patrón, certificado, tiempos | Calidad/certificado | hoja, patrón, certificado patrón, certificado | Evaluar repetición o justificación autorizada | Repetir/bloquear | Parcial | Crítico | vigencia validada al resolver patrones, integración E2E parcial | `backend/app/services/field_sheets.py`, `backend/app/services/pattern_selection_engine.py` | Parcial | P0 | Separar bloqueo previo de disposición posterior. |
| EX-037 | Captura | Identificación | CertificateCaptureFile | Subido | Master no identificado | Quedar en bandeja de incidencia | No hay resolución formal | H. Incidencia técnica | No | Ninguna | Captura | Soporte/Captura | archivo, diagnóstico | Captura | archivo, certificado, Master | Reprocesar tras corrección | Mantener pendiente | Sí | Medio | readiness/fingerprint y pendiente documentado | `backend/app/services/capture_packages.py`, `frontend/src/pages/CapturePage.jsx` | Parcial | P1 | No autorizar saltarse identificación. |
| EX-038 | Captura | Diferencias | Certificate | capture_in_progress | Enviar Master con mismatch bloqueante | Bloquear y corregir | Saltarlo dañaría certificado | C. Bloqueo obligatorio | No | Ninguna | Captura | Backend | diagnóstico | Calidad | certificado, archivo | No ejecutar | Corregir/reprocesar | Sí | Alto | readiness distingue warnings/bloqueantes | `backend/app/services/capture_packages.py` | Implementado | P1 | Warnings pueden seguir según regla actual; diferencias no. |
| EX-039 | Calidad | Corrección | Certificate | ready_for_quality/quality_review/approved | Regresar a Captura | Motivo obligatorio y estado correction_requested | — | A. Flujo normal | No | Ninguna | Calidad | Backend | comentario | Captura | certificado, Master | Registrar retorno | 422 si sin motivo | Sí | Bajo | `return_to_technician` | `backend/app/services/certificates.py` | Implementado | P1 | Conservar. |
| EX-040 | Calidad | Match PDF | Certificate | match_validated mismatch/warning | Aceptar manualmente | Usuario con permiso y auditoría | Aceptar discrepancia injustificada | E. Excepción administrativa | Sí | Aceptación manual de match | Calidad | Calidad autorizada | PDF, score, comentario | Certificado | certificate, match_details, audit | Marcar manual_accepted | Mantener discrepancia | Sí | Alto | `certificates.match_override`; `manual_accept_match` | `backend/app/services/certificates.py`, `backend/app/routers/certificates.py` | Existente | P1 | Hacer comentario obligatorio y mantener evidencia. |
| EX-041 | Calidad | Autenticación | Certificate | quality_approved | Autenticar | Generar desde Master aprobado; fallo no muta estado | Conversión falla | H. Incidencia técnica | No | Ninguna | Calidad | Soporte | error técnico | Documento | certificado, PDF, Master | Reintentar idempotente | Mantener aprobado | Sí | Medio | servicio preserva estado ante conversión | `backend/app/services/certificate_authentication.py`, `backend/app/services/certificates.py` | Implementado | P1 | Monitorear/reintentar; no aprobar excepción. |
| EX-042 | Certificados | Liberación | Certificate | authenticated | Liberar sin pago cuando `requires_payment=true` | Bloqueo financiero central | Entrega con saldo | C. Bloqueo obligatorio | Sí sólo si negocio autoriza crédito/extraordinario | Liberación financiera | Operación | Finanzas | saldo, justificación, garantía | Cliente/finanzas | invoices, payments, certificate | Ejecutar liberación tras autorización separada | Mantener no visible | No para entrega; sí resto | Crítico | `_ensure_payment_allows_release` | `backend/app/services/certificates.py` | Bloqueo implementado; excepción faltante | P0 | No debilitar gate; crear autorización financiera explícita. |
| EX-043 | Certificados | Suspensión | Certificate | múltiples | Suspender/reactivar | Motivo, responsable y destino válido | Retorno genérico a capture_pending pierde contexto | E. Excepción administrativa | Sí | Suspensión de certificado | Calidad | Calidad superior | causa, vigencia, estado retorno | Calidad/cliente | certificado, documentos | Suspender y luego reanudar al estado calculado | Mantener estado | Sí | Alto | transición `suspended→capture_pending/cancelled`; comentario opcional | `backend/app/services/certificates.py` | Parcial | P1 | Persistir causa y estado previo. |
| EX-044 | Certificados | Cancelación | Certificate | No liberado | Cancelar | Conservar folio/documentos y coordinar factura | Cancelación puede ser fiscal/operativa distinta | E. Excepción administrativa | Sí | Cancelación de certificado | Calidad | Calidad/Admin | motivo, folio, dependencias | Calidad/fiscal | hoja, equipo, invoice, PDFs | Marcar cancelado y preservar archivos | Mantener | Sí | Alto | transición permite cancelled; baja separada | `backend/app/services/certificates.py` | Parcial | P1 | Prohibir baja como sustituto de cancelación. |
| EX-045 | Certificados | Baja | Certificate | No liberado | Desactivar | Sólo administrativo con dependencias verificadas | Limpia rutas y puede eliminar PDFs sin referencia | I. Riesgo de integridad de datos | No después de actividad | Ninguna | — | — | dependencias | Histórico | certificado, PDFs, audit | Bloquear | Bloquear | Sí | Alto | `deactivate_certificate` limpia rutas/autenticación y llama `delete_if_unreferenced`; sólo bloquea liberado | `backend/app/services/certificates.py` | Implementado con guardia insuficiente | P1 | Restringir a borrador sin derivados; preservar evidencia documental. |
| EX-046 | Control Documental | Versión | ControlledDocumentVersion | draft | Activar nueva revisión | Obsoletar activa anterior; validar Master XLSX/vigencia | — | B. Validación automática | No | Ninguna | Calidad | Usuario con approve | archivo, revisión, vigencia | Plantillas futuras | documento, versiones | Activar/auditar | 422 | Sí | Bajo | `_activate_document_version` | `backend/app/services/controlled_documents.py`, `backend/app/routers/documents.py` | Implementado | P2 | Conservar snapshots consumidores. |
| EX-047 | Control Documental | Suspensión | ControlledDocument | active | Suspender documento usado por procesos | No reescribir snapshots; impedir nuevos usos | Uso futuro de documento inválido | E. Excepción administrativa | Sí | Suspensión documental | Calidad | Calidad autorizada | motivo, vigencia, consumidores | Captura/certificados | documento, versión, snapshots consumidores | Suspender para nuevos usos y notificar afectados | Mantener activo | Sí según riesgo | Alto | archive cambia status; snapshots existen | `backend/app/services/controlled_documents.py`, `backend/app/models/controlled_document.py` | Parcial | P1 | Definir tratamiento de trabajos en curso. |

### 4.4 Facturación, pagos, crédito, liberación e integraciones

| ID | Módulo | Submódulo | Entidad | Estado origen | Acción o evento | Flujo normal esperado | Conflicto posible | Clasificación | ¿Requiere excepción? | Tipo de excepción propuesto | Solicitante | Resolutor | Datos requeridos | Impacto | Registros relacionados | Acción al aprobar | Acción al rechazar | Posibilidad de continuar trabajando | Riesgo de integridad | Evidencia en código | Archivos involucrados | Estado actual de implementación | Prioridad | Recomendación |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| EX-048 | Facturación | Borrador | Invoice | draft/pending/issue_failed | Editar factura | Validar coherencia cliente-cotización-ETS | Update cambia IDs sin revalidar conjunto | I. Riesgo de integridad de datos | No | Ninguna | Finanzas | Backend | source IDs | Fiscal/operativo | invoice, quote, ETS, client | Validar y guardar | 409/422 | Sí | Crítico | create valida; update sólo existencia | `backend/app/services/invoices.py`, `backend/app/schemas/invoice.py` | Brecha existente | P0 | Revalidar agregado completo en cada mutación. |
| EX-049 | Facturación | Emisión | Invoice | draft/pending/failed | Timbrar | Intento idempotente, persistir antes de red, reconciliar ambigüedad | Doble CFDI o estado desconocido | B. Validación automática | No | Ninguna | Finanzas | Backend/Facturama | payload, attempt, UUID | Fiscal | invoice, attempts, documentos | Emitir/reconciliar | Rechazar o unknown | Sí salvo issuing/unknown | Crítico | issuing/issue_unknown/reconciliation | `backend/app/services/facturama/invoices.py`, `backend/app/services/invoices.py` | Implementado Sandbox | P0 | Mantener; no reemitir unknown. |
| EX-050 | Facturación | Estado desconocido | Invoice | issue_unknown | Resolver intento | Reconciliar proveedor antes de cualquier reintento | Doble timbrado | H. Incidencia técnica | No | Ninguna | Finanzas | Soporte/servicio | attempt, respuesta, XML | Fiscal | invoice, Facturama | Confirmar resultado técnico | Mantener unknown | Sí, no reemitir | Crítico | reconciliación manual estricta | `backend/app/services/facturama/invoices.py`, `backend/app/routers/invoices.py` | Implementado | P0 | Tratar como incidente, no excepción fiscal. |
| EX-051 | Facturación | Cancelación CFDI | Invoice | issued/partial/paid | Cancelar localmente | Cancelar ante SAT/PAC con motivo; quizá sustituir | Estado local diverge del SAT | G. Excepción fiscal | Sí | Cancelación CFDI | Finanzas | Responsable fiscal | UUID, motivo SAT, relación | Fiscal/pagos/liberación | invoice, payments, XML, certificate | Ejecutar PAC y sólo luego reflejar | Mantener CFDI vigente | Sí, sin cancelar | Crítico | transición local a cancelled sin llamada Facturama | `backend/app/services/invoices.py`, `backend/app/services/facturama/invoices.py` | Faltante/peligroso | P0 | Bloquear cancelación local de emitida hasta flujo fiscal. |
| EX-052 | Facturación | Sustitución | Invoice | issued/cancelled | Sustituir CFDI | Emitir relacionado y cancelar conforme SAT | Relaciones fiscales ausentes | G. Excepción fiscal | Sí | Sustitución CFDI | Finanzas | Responsable fiscal | UUID origen, motivo, nuevo payload | Fiscal | invoices, XML, PAC | Emitir relacionado y confirmar ambos pasos | Conservar origen | Sí | Crítico | no hay endpoint/modelo de sustitución | `backend/app/services/facturama/invoices.py`, `backend/app/models/invoice.py` | No implementado | P0 | Saga fiscal con compensación. |
| EX-053 | Pagos | Registro | Payment | Factura con saldo | Registrar pago válido | Importe positivo ≤ saldo y estado efectivo | Estados pending/refunded cuentan como pagado; factura con saldo cero admite alta | I. Riesgo de integridad de datos | No | Ninguna | Finanzas | Backend | monto, fecha, referencia, estado | Saldo/liberación | invoice, payment, certificate | Recalcular sólo pagos efectivos | 409 | Sí | Crítico | recálculo suma todos salvo cancelled; guardia balance | `backend/app/services/invoices.py`, `backend/app/models/invoice.py` | Implementado incorrectamente | P0 | Corregir contrato antes de excepciones. |
| EX-054 | Pagos | Corrección | Payment | Registrado | Corregir/cancelar/devolver | Evento compensatorio, nunca borrar | No hay endpoints | F. Excepción financiera | Sí | Corrección de pago | Finanzas | Finanzas superior | pago, motivo, evidencia bancaria | Saldo/liberación | payment, invoice, certificate | Crear reverso/ajuste y recalcular | Mantener pago | Sí según saldo | Crítico | sólo create/list; statuses existen | `backend/app/routers/invoices.py`, `backend/app/services/invoices.py` | Faltante | P0 | Idempotencia y doble autorización según monto. |
| EX-055 | Pagos | Duplicado | Payment | Factura abierta | Repetir referencia | Detectar idempotencia/duplicado | Saldo inflado | C. Bloqueo obligatorio | No | Ninguna | Finanzas | Backend | referencia, monto, fecha | Saldo | payments, invoice | Rechazar duplicado | Rechazar | Sí | Alto | no se observó unicidad de referencia | `backend/app/models/invoice.py`, `backend/app/services/invoices.py` | Faltante | P0 | Clave idempotente y criterio bancario. |
| EX-056 | Complementos | PPD | Invoice/Payment CFDI | PPD pagada parcial/total | Generar complemento | CFDI de pago relacionado | No existe | G. Excepción fiscal | No: es flujo fiscal normal | Ninguna | Finanzas | — | pagos, UUID, impuestos | Fiscal | invoice, payments, XML | No aplica hasta implementar | No aplica | Sí operativamente, no fiscalmente | Crítico | sólo settings PUE/PPD | `backend/app/models/invoice.py`, `backend/app/services/facturama/invoices.py` | No implementado | P0 | Implementar como flujo normal, no motor de excepciones. |
| EX-057 | Notas de crédito | Fiscal | CreditNote | Cualquier invoice | Aplicar nota | CFDI egreso válido, límite y relación | Nota administrativa puede exceder saldo y no timbra | G. Excepción fiscal | Sí para emisión/cancelación; no para alta normal | Nota fiscal extraordinaria | Finanzas | Responsable fiscal | motivo, monto, UUID | Saldo/fiscal | credit_note, invoice, CFDI | Timbrar/aplicar dentro de límites | Mantener saldo | Sí | Crítico | endpoint aplica sin PAC ni límite robusto | `backend/app/services/invoices.py`, `backend/app/models/invoice.py` | Parcial no fiscal | P0 | Separar ajuste interno de CFDI egreso. |
| EX-058 | Crédito | Línea/suspensión | Client | Activo | Autorizar/modificar/suspender crédito | Agregado de crédito, movimientos y vigencia | No existe modelo ni saldo disponible | J. Funcionalidad no implementada | No por ahora | Ninguna hasta diseñar crédito | Comercial/Finanzas | — | línea, plazo, garantías | Ventas/liberación | client, quotes, invoices, payments | No aplica | No aplica | Sí contado | Alto | no se hallaron entidades de crédito | `backend/app/models/client.py`, `backend/app/models/invoice.py` | No implementado | P1 | Diseñar crédito antes de excepciones financieras. |
| EX-059 | Liberación | Crédito/saldo | Certificate | authenticated con saldo | Liberar por crédito vigente o extraordinario | Verificar línea/vigencia o autorización específica | Gate actual sólo acepta paid | F. Excepción financiera | Sí | Liberación por crédito/extraordinaria | Operación/Comercial | Finanzas superior | saldo, crédito, vencimiento, motivo | Cliente/cartera | invoice, client, certificate, approval | Registrar obligación y liberar una vez | Mantener bloqueado | No para entrega | Crítico | readiness sólo `paid` o `requires_payment=false` | `backend/app/services/certificates.py` | Faltante | P0 | Dos tipos distintos: por crédito y extraordinaria. |
| EX-060 | Integraciones | Producción/Drive | ExternalIntegration | Sandbox/local | Operar producción o archivar en Drive | Configuración, health, idempotencia y monitoreo | Capacidades no existen/cerradas | J. Funcionalidad no implementada | No | Ninguna | Admin | — | configuración segura | Fiscal/documental | invoices, files | No aplica | No aplica | Sí en Sandbox/local | Alto | Facturama bloquea producción; Drive ausente | `backend/app/services/facturama/invoices.py`, `backend/app/routers/integrations.py`, `backend/app/services/storage_service.py` | No implementado | P1 | Cerrar integración normal antes de diseñar excepciones. |

## 5. Catálogo consolidado de excepciones

### Existentes en código

1. **Aceptación manual de match de PDF** (`EX-040`): permiso específico, evidencia en `match_details` y auditoría. Es la referencia más cercana al patrón correcto, aunque el comentario debería ser obligatorio.
2. **Excepción de incertidumbre**: endpoint protegido por `uncertainty_models.exception`; registra la excepción sobre el modelo/cálculo. Su alcance no sustituye un motor transversal y debe conservarse como adaptador de dominio.

### Parcialmente implementadas

1. **Cambio extraordinario de etapa ETS** (`EX-016`): tiene motivo y auditoría, pero ejecuta antes de una aprobación independiente y el actor puede ser opcional.
2. **OT adicional por capacidad** (`EX-023`): el conflicto se detecta y el mensaje reconoce la necesidad administrativa, pero no hay solicitud ni resolución.
3. **Reapertura de firmas** (`EX-032`): existen permiso y campos de reapertura, sin servicio de ciclo/refirma ni propagación.

### Sólo documentadas o declaradas

- `service_orders.signatures.reopen` y campos `signature_reopen_*`.
- Deuda `TD-014` para persistir excepción ETS con solicitante, autorizador y estado.
- Liberaciones por crédito o extraordinarias aparecen como necesidad funcional auditada, no como capacidad vigente.

### Excepciones faltantes prioritarias

Las 18 faltantes son: corrección fiscal de cliente; cotización aceptada; reprogramación; corrección de llamado; cambio cliente ETS; cambio de alcance; cancelación coordinada ETS; OT adicional; reasignación postfirma; equipo extra no cotizado; no realizado con derivados; cancelación parcial de equipo; corrección de modalidad; refirma; cancelación de hoja; suspensión documental; corrección/cancelación de pago; liberación financiera. Cancelación/sustitución de CFDI requieren además flujos fiscales propios y no deben resolverse con un bypass genérico.

### Duplicidades

- Reglas ETS duplicadas entre router y servicio, y dos rutas de confirmación de firmas.
- Campos directos de firma y ciclos formales; número OT legacy y entidad OT.
- Alias de acciones de Certificados (`approve`, `release`) junto con rutas canónicas.
- Estados legacy de Certificados conviven con estados vigentes.

### “Excepciones” que no deberían existir

- Saltarse identificación de Master, mismatch bloqueante, autenticación, unicidad fiscal o pago mediante un override genérico.
- Reemitir una factura en `issue_unknown`.
- Eliminar físicamente equipo, hoja, certificado, pago o CFDI para corregir una operación.
- Convertir fallas de red/conversión/PAC en solicitudes administrativas.

### Acciones sensibles sin autorización backend suficiente

- Registro público con roles solicitados.
- Mutaciones principales de Clientes, Cotizaciones, Equipos y gran parte de ETS con ausencia de `require_permission` o actor opcional.
- Confirmación de firmas y excepción ETS con usuario opcional.
- Portal cliente sin aislamiento demostrable por identidad, conforme a auditoría vigente.

## 6. Mapa de dependencias y efectos

```text
Cotización aceptada
  → ETS → OT → equipo → firma → hoja de campo → Master de captura
  → certificado esperado → Calidad → PDF autenticado → liberación
  → factura → pago/crédito → compuerta financiera

Equipo adicional o retirado
  → recalcular cupo OT y conteos ETS
  → invalidar o crear ciclo de firma, nunca sobrescribirlo
  → crear/cancelar hoja y reserva de folio según etapa
  → crear/cancelar certificado sin borrar evidencia
  → resincronizar sólo borrador fiscal compatible
  → conservar CFDI emitido y abrir ajuste fiscal/comercial separado

Pago corregido
  → recalcular saldo y antigüedad
  → revaluar crédito disponible
  → revocar sólo una liberación aún no ejecutada
  → nunca ocultar un certificado ya entregado sin proceso formal
```

| Excepción | Recalcular | Invalidar/reabrir | Notificar | Conservar sin cambios |
| --- | --- | --- | --- | --- |
| Cambio de alcance/equipo | cupos, conteos, importe borrador | firma/hoja/certificado no liberado según etapa | Comercial, Técnico, Calidad, Finanzas | snapshots, auditoría, CFDI emitido |
| Reasignación OT | cupos y paquetes | firma de OT y rutas documentales pendientes | Técnico/cliente firmante | ciclo anterior |
| Corrección cliente/modalidad | readiness y documentos futuros | artefactos no emitidos/autenticados | Calidad/Finanzas | certificados/CFDI emitidos |
| Cancelación ETS/equipo | conteos, saldo si aún borrador | trabajos pendientes | todos los responsables downstream | evidencia técnica y fiscal histórica |
| Corrección de pago | saldo, aging, crédito | autorización de liberación no ejecutada | Finanzas/Calidad | pago original más reverso |
| Liberación extraordinaria | exposición/cartera | nada ya autenticado | Finanzas/Calidad/cliente | factura, saldo y evidencia de autorización |

## 7. Diseño propuesto del subsistema futuro

Agregar un agregado único `ExceptionRequest`, sin alterar todavía los agregados de dominio:

- identidad: `id`, `type`, `category`, `source_module`, `entity_type`, `entity_id`;
- gobierno: `requested_by`, `resolver_id`, `reason`, `priority`, `status`;
- evidencia: `payload`, adjuntos, estado previo/hash, relaciones afectadas;
- decisión: `approved_at/by`, `rejected_at/by`, comentario y caducidad;
- ejecución: `execution_status`, `executed_at/by`, clave idempotente, efectos ejecutados y error;
- auditoría/notificación: eventos inmutables y destinatarios.

Estados sugeridos de solicitud: `requested → under_review → approved | rejected | cancelled | expired`. Estados de ejecución independientes: `not_started → executing → executed | execution_failed | compensated`. Un registro `approved` puede permanecer `not_started` o terminar `execution_failed`; nunca debe marcarse `executed` por el solo hecho de aprobar.

Cada tipo debe delegar la mutación al servicio canónico del dominio dentro de una transacción, verificar que el registro aún conserva el estado esperado y registrar efectos. No debe haber un endpoint genérico capaz de escribir directamente cualquier entidad. Separación de funciones sugerida: solicitante operativo; resolutor por matriz de categoría; ejecutor de sistema o usuario autorizado; auditor de sólo lectura. Para cambios P0 debe impedirse que solicitante y resolutor sean la misma persona.

## 8. Preguntas funcionales para el propietario

1. ¿`not_done` cuenta como equipo terminado para avance del ETS, aunque no deba facturarse ni certificarse?
2. ¿Qué cambio posterior a firma exige refirma general y cuál sólo refirma de la OT afectada?
3. ¿Puede crearse automáticamente una OT 11+ o siempre requiere autorización?
4. ¿Cómo se cobra un equipo adicional no cotizado: adenda, nueva cotización o factura independiente?
5. ¿Quién puede retirar/cancelar un equipo y hasta qué etapa sin autorización superior?
6. ¿Existe una circunstancia válida para cambiar cliente del ETS, o siempre debe cancelarse y recrearse?
7. ¿Qué usuarios resuelven excepciones operativas, administrativas, financieras y fiscales?
8. ¿Qué límite de monto exige doble aprobación financiera?
9. ¿Liberación por crédito vigente y liberación extraordinaria son permisos separados?
10. ¿Una liberación extraordinaria permite saldo vencido o sólo falta temporal de aplicación del pago?
11. ¿Cuál es el tratamiento de un certificado ya liberado cuando después se revierte el pago?
12. ¿La nota de crédito actual es sólo ajuste administrativo o debe ser siempre CFDI de egreso?
13. ¿Se requieren PUE y PPD ambos en producción, y cuál es la política de complementos parciales?
14. ¿Suspender un documento/Master invalida trabajos en curso o sólo nuevas asignaciones?
15. ¿Agenda y Llamados serán módulos formales o seguirán como eventos internos del ETS?

## 9. Fases recomendadas

1. **Precondiciones P0:** autorización backend, token type, actor obligatorio, servicio ETS único, pagos efectivos e integridad del agregado Invoice.
2. **Núcleo auditable:** tablas de solicitud/eventos/efectos, separación aprobación/ejecución, idempotencia, matriz de resolución y notificaciones.
3. **ETS y firma:** alcance, OT adicional, reasignación, retiro/cancelación parcial y refirma por ciclo.
4. **Técnico/documental:** hoja cancelada, patrón detectado tarde, modalidad de acreditación y suspensión documental.
5. **Finanzas:** corrección de pago y liberación por crédito/extraordinaria, después de implementar el agregado de crédito.
6. **Fiscal:** cancelación, sustitución, CFDI egreso y complementos mediante servicios fiscales propios; el motor sólo autoriza, nunca sustituye al PAC.
7. **Validación:** pruebas de permisos 401/403, concurrencia, idempotencia, rechazo, aprobación sin ejecución, fallo de ejecución, compensación y E2E por cadena dependiente.

## 10. Pendientes consolidados y módulos SELLADOS

P0: seguridad de rutas/tokens, duplicidad ETS, excepción ETS inmediata, confirmación de firmas duplicada, cancelaciones parciales, coherencia Invoice, cómputo/corrección de pagos y flujos fiscales. P1: versionado comercial, reprogramación, OT adicional, refirma, cancelación de hoja, suspensión documental y diseño de crédito. P2: Agenda/Llamados formales y mejoras operativas no críticas.

El único módulo `SELLADO` observado es **Control Documental V1**, dentro de su alcance congelado. Estar sellado no impide que una decisión futura sobre suspensión de documentos en uso amplíe el alcance; esa decisión no se presenta aquí como defecto del cierre V1.

Orden recomendado hasta una base estable: Seguridad → consolidación ETS → integridad equipos/firmas → Hojas/Captura/Calidad → Invoice/pagos → crédito/liberación → ciclo fiscal → integraciones → Agenda/Llamados.

## 11. Archivos revisados

### Backend

`backend/app/core/permissions.py`, `backend/app/core/security.py`, `backend/app/models/audit_log.py`, `backend/app/models/certificate.py`, `backend/app/models/client.py`, `backend/app/models/controlled_document.py`, `backend/app/models/equipment.py`, `backend/app/models/field_sheet.py`, `backend/app/models/invoice.py`, `backend/app/models/quotation.py`, `backend/app/models/reference_standard.py`, `backend/app/models/service_order.py`, `backend/app/models/uncertainty.py`, `backend/app/models/user.py`, `backend/app/schemas/certificate.py`, `backend/app/schemas/client.py`, `backend/app/schemas/equipment.py`, `backend/app/schemas/field_sheet.py`, `backend/app/schemas/invoice.py`, `backend/app/schemas/quotation.py`, `backend/app/schemas/service_order.py`, `backend/app/schemas/service_scope.py`, `backend/app/schemas/uncertainty.py`, `backend/app/services/auth.py`, `backend/app/services/capture_packages.py`, `backend/app/services/certificate_authentication.py`, `backend/app/services/certificates.py`, `backend/app/services/clients.py`, `backend/app/services/controlled_documents.py`, `backend/app/services/equipment.py`, `backend/app/services/facturama/invoices.py`, `backend/app/services/field_sheets.py`, `backend/app/services/invoices.py`, `backend/app/services/pattern_selection_engine.py`, `backend/app/services/quotations.py`, `backend/app/services/service_orders.py`, `backend/app/services/storage_service.py`, `backend/app/services/uncertainty_engine.py`, `backend/app/routers/auth.py`, `backend/app/routers/certificates.py`, `backend/app/routers/clients.py`, `backend/app/routers/documents.py`, `backend/app/routers/equipment.py`, `backend/app/routers/field_sheets.py`, `backend/app/routers/integrations.py`, `backend/app/routers/invoices.py`, `backend/app/routers/quotations.py`, `backend/app/routers/service_orders.py`, `backend/app/routers/uncertainty.py`, `backend/app/routers/users.py`.

Se revisaron además los nombres y cadena de migraciones de `backend/migrations/versions/` para localizar estados, columnas legacy, ciclos de firma, Invoice/pagos y contratos vigentes; no se modificó ni ejecutó ninguna migración.

### Frontend

`frontend/src/constants/navigation.js`, `frontend/src/pages/BillingPage.jsx`, `frontend/src/pages/CapturePage.jsx`, `frontend/src/pages/CertificatesPage.jsx`, `frontend/src/pages/ClientsPage.jsx`, `frontend/src/pages/DocumentLibraryPage.jsx`, `frontend/src/pages/EquipmentPage.jsx`, `frontend/src/pages/QualityPage.jsx`, `frontend/src/pages/QuotationsPage.jsx`, `frontend/src/pages/ServiceOrdersPage.jsx`, `frontend/src/pages/StandardsPage.jsx`, `frontend/src/pages/settings/UsersSettingsPanel.jsx`, `frontend/src/components/invoice-workbench/InvoiceWorkbenchDialog.jsx`, `frontend/src/components/invoice-workbench/useInvoiceWorkbenchController.js`, `frontend/src/components/ets-billing/EtsBillingTab.jsx`, `frontend/src/services/api.js`.

### Documentación y pruebas

`AGENTS.md`, `docs/project/DOCUMENTATION_INDEX.md`, `docs/project/PROJECT_STATUS.md`, `docs/project/CURRENT_SCOPE.md`, `docs/project/CURRENT_PROCESS_FLOW.md`, `docs/project/BUSINESS_RULES.md`, `docs/project/DECISIONS.md`, `docs/project/OBSERVATIONS_REGISTER.md`, `docs/project/TECHNICAL_DEBT.md`, `docs/architecture/PERMISSIONS_MATRIX.md`, `docs/architecture/INVOICE_WORKBENCH_CONTROLLER.md`, `docs/architecture/CALIBRATION_SCOPE_CONTRACT.md`, `docs/audits/AUDITORIA_INTEGRAL_AVANCE_ERP_MYC_2026-07-21.md`, `docs/audits/AUDITORIA_TECNICA_FACTURACION_CFDI_4_0.md`, `backend/tests/test_capture_packages.py`, `backend/tests/test_capture_quality_master_flow.py`, `backend/tests/test_certificate_operational_flow.py`, `backend/tests/test_certificate_release_http.py`, `backend/tests/test_facturama_infrastructure.py`, `backend/tests/test_facturama_invoice_mapper.py`, `backend/tests/test_facturama_reconciliation.py`, `backend/tests/test_field_sheet_operational_contract.py`, `backend/tests/test_invoice_documents.py`, `backend/tests/test_invoice_listing.py`, `backend/tests/test_service_scope_contract.py`. No se encontró una suite dedicada de matriz completa de permisos; esa ausencia se trató como falta de cobertura, no como evidencia funcional.

## 12. Trazabilidad de observaciones históricas

- ✅ Resuelta: archivo/restauración de Clientes; ciclos de firma base; snapshots de equipos/Hojas; Captura XLSX; autenticación y compuerta financiera; controlador único del Workbench; contrato `calibration_scope`.
- ⚠ Parcialmente resuelta: permisos por rol, Hojas de Campo, Captura, Calidad, Facturación, pagos/notas, OT/firmas legacy y portal cliente.
- ❌ Sigue pendiente: seguridad deny-by-default, excepción ETS persistente, refirma/reapertura, cancelación/sustitución CFDI, complementos PPD, crédito y liberaciones por crédito/extraordinarias.

## 13. Conclusión

La primera implementación no debe empezar por una tabla genérica de excepciones: debe cerrar los P0 que hoy permitirían mutar datos sin autorización o con contratos inconsistentes. Después, el motor debe orquestar servicios canónicos y conservar evidencia; nunca debe convertirse en una segunda máquina de estados ni en un bypass de validaciones fiscales, técnicas o financieras.
