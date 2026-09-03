> Estado: VIGENTE
>
> Tipo: Vigente (canónico)
>
> Autoridad: Máxima para jerarquía, clasificación y resolución de conflictos documentales
>
> Prevalece sobre: cualquier índice, lista de documentos o instrucción de autoridad contenida en documentos anteriores
>
> Corte verificado: 2026-08-24

# Índice único de documentación

Este es el punto de entrada obligatorio para consultar la documentación del ERP MYC. Ningún documento fuera de este índice debe asumirse vigente por su nombre, ubicación o por usar expresiones como “actual”, “final”, “congelado” o “sellado”.

## Orden de prevalencia

Cuando exista conflicto se aplica este orden:

1. **Estado real verificable del código, esquema y comportamiento**, documentado mediante una revisión actual. Si contradice el canon, debe abrirse una corrección documental inmediata; no se debe reinterpretar el código para preservar un texto obsoleto.
2. **Este índice**, para decidir autoridad y clasificación.
3. **Documentos canónicos de `project/`**, con especialidad: `PROJECT_STATUS` para avance, `CURRENT_SCOPE` para alcance, `CURRENT_PROCESS_FLOW` para flujo, `BUSINESS_RULES` para reglas, `DECISIONS` para decisiones, `OBSERVATIONS_REGISTER` para observaciones y `TECHNICAL_DEBT` para deuda.
4. **Arquitectura vigente**, para contratos técnicos específicos.
5. **Documentación vigente de módulos**, sólo dentro de su contrato particular.
6. **Cierres técnicos**, como evidencia de una entrega acotada, nunca como estado global actual.
7. **Auditorías**, como fotografías fechadas y evidencia reproducible.
8. **Diseños futuros**, sólo como propuesta; no generan alcance ni pendientes actuales.
9. **Histórico y Archivo**, únicamente para trazabilidad.

En dos documentos del mismo nivel prevalece el de fecha verificable más reciente y alcance más específico. Si no puede resolverse, se registra el conflicto aquí antes de utilizar cualquiera como autoridad.

## Documentos normativos canónicos

| Documento | Autoridad | Uso autorizado |
| --- | --- | --- |
| [`DOCUMENTATION_INDEX.md`](DOCUMENTATION_INDEX.md) | Máxima | Entrada única, clasificación y conflictos. |
| [`PROJECT_STATUS.md`](PROJECT_STATUS.md) | Máxima | Única fuente del avance actual y módulos sellados. |
| [`CURRENT_SCOPE.md`](CURRENT_SCOPE.md) | Alta | Alcance implementado, parcial y no implementado. |
| [`CURRENT_PROCESS_FLOW.md`](CURRENT_PROCESS_FLOW.md) | Alta | Flujo operativo que existe actualmente. |
| [`BUSINESS_RULES.md`](BUSINESS_RULES.md) | Alta | Reglas funcionales confirmadas. |
| [`DECISIONS.md`](DECISIONS.md) | Alta | Decisiones arquitectónicas/funcionales vigentes y origen. |
| [`OBSERVATIONS_REGISTER.md`](OBSERVATIONS_REGISTER.md) | Alta | Observaciones pendientes, parciales y resueltas. |
| [`TECHNICAL_DEBT.md`](TECHNICAL_DEBT.md) | Alta | Deuda técnica vigente priorizada. |
| [`../PROJECT_FILE_REGISTRY.md`](../PROJECT_FILE_REGISTRY.md) | Alta para inventario | Inventario oficial de archivos; no determina alcance ni avance. |
| [`../BACKUP_ESTADO_ACTUAL.md`](../BACKUP_ESTADO_ACTUAL.md) | Media | Corte operativo vigente de migraciones, validaciones y pendientes; no sustituye los canónicos especializados. |

## Arquitectura vigente

| Documento | Contrato |
| --- | --- |
| [`../architecture/CATALOGOS_SAT.md`](../architecture/CATALOGOS_SAT.md) | Fuente, importación, versionado y consumo de Catálogos SAT. |
| [`../architecture/FIELD_SHEET_FIELD_REGISTRY.md`](../architecture/FIELD_SHEET_FIELD_REGISTRY.md) | Claves y semántica canónica de campos de Hojas de Campo. |
| [`../architecture/FIELD_SHEET_PDF_RENDERER.md`](../architecture/FIELD_SHEET_PDF_RENDERER.md) | Autoridad única, renderer versionado, compatibilidad legacy y artefacto final inmutable de FieldSheets ERP/LAB. |
| [`../architecture/PERMISSIONS_MATRIX.md`](../architecture/PERMISSIONS_MATRIX.md) | Roles/permisos declarados y brechas de aplicación. |
| [`../architecture/files/INSTITUTIONAL_FILE_STORAGE.md`](../architecture/files/INSTITUTIONAL_FILE_STORAGE.md) | Contrato vigente de rutas, publicación atómica, checksum, temporales y custodia local institucional. |
| [`../architecture/files/UPLOAD_SECURITY_POLICY.md`](../architecture/files/UPLOAD_SECURITY_POLICY.md) | Perfiles, límites y validaciones obligatorias para entradas PDF, imagen, texto, ZIP, OOXML y XML. |
| [`../architecture/files/FILE_OWNERSHIP_AND_DELIVERY.md`](../architecture/files/FILE_OWNERSHIP_AND_DELIVERY.md) | Secuencia obligatoria de identidad, permiso, ownership y entrega contenida de archivos. |
| [`../architecture/CATALOGO_INSTITUCIONAL_FUNCIONAL_ERP_MYC.md`](../architecture/CATALOGO_INSTITUCIONAL_FUNCIONAL_ERP_MYC.md) | Autoridad funcional aprobada y congelada, versión 1.0: 42 módulos, 181 acciones y 657 microacciones con naturaleza, criticidad y alcance permitido; no modifica automáticamente código ni permisos. |
| [`../architecture/CATALOGO_INSTITUCIONAL_CAPACIDADES_PERMISOS_ERP_MYC_2026-08-04.md`](../architecture/CATALOGO_INSTITUCIONAL_CAPACIDADES_PERMISOS_ERP_MYC_2026-08-04.md) | Snapshot técnico reproducible de ETAPA 2B: 36 superficies, 305 operaciones HTTP y 493 campos; no es autoridad funcional posterior a la validación. |
| [`../architecture/security/CAPABILITY_MODEL_GAPS_2026-08-04.md`](../architecture/security/CAPABILITY_MODEL_GAPS_2026-08-04.md) | Brechas verificadas entre Catálogo Institucional, bootstrap `permissions.py` e inventario HTTP; base de revisión previa a cualquier RBAC dinámico. |
| [`../architecture/security/API_ACCESS_CONTROL.md`](../architecture/security/API_ACCESS_CONTROL.md) | Deny-by-default, clasificación de rutas, excepciones públicas, JWT, portal/ownership y relación backend/frontend. |
| [`../architecture/security/API_ENDPOINT_INVENTORY_2026-08-03.csv`](../architecture/security/API_ENDPOINT_INVENTORY_2026-08-03.csv) | Inventario reproducible vigente de 477 operaciones FastAPI; conserva la fecha del archivo de origen y su política mínima verificable. |
| [`../architecture/INVOICE_WORKBENCH_CONTROLLER.md`](../architecture/INVOICE_WORKBENCH_CONTROLLER.md) | Controlador único, contexto explícito y composición obligatoria de la pestaña Facturación del ETS. |
| [`../architecture/CALIBRATION_SCOPE_CONTRACT.md`](../architecture/CALIBRATION_SCOPE_CONTRACT.md) | Claves canónicas, propagación automática y compatibilidad de datos de `calibration_scope`. |
| [`../architecture/COMPOSITE_CATALOG_SERVICES.md`](../architecture/COMPOSITE_CATALOG_SERVICES.md) | Relación normalizada, validaciones y expansión comercial→operativa de Servicios Compuestos. |
| [`../architecture/OPERATIONAL_SERVICE_IDENTITY.md`](../architecture/OPERATIONAL_SERVICE_IDENTITY.md) | Identidad operativa canónica, autoridad histórica del snapshot, compatibilidad legacy y frontera de Hojas de Campo. |
| [`../architecture/ETS_MULTIPLE_EVOLVED_CORE.md`](../architecture/ETS_MULTIPLE_EVOLVED_CORE.md) | Contrato de Fase 1 para unidades estables, etapas append-only, solicitudes, decisiones por partida, tareas y compatibilidad de calibración. |
| [`../architecture/SALE_ETS_EXECUTION.md`](../architecture/SALE_ETS_EXECUTION.md) | Vertical ETS Venta: snapshot, unidades/cantidades, arribo, calibración enlazada, garantía, entregas, portal/MYC Mobile, cierre y permisos; EN REVISIÓN. |
| [`../architecture/MAINTENANCE_ETS_EXECUTION.md`](../architecture/MAINTENANCE_ETS_EXECUTION.md) | Vertical ETS Mantenimiento: snapshot, preventivo/correctivo, laboratorio/campo, captura estructurada, materiales, pausas, reporte, firma y cierre; EN REVISIÓN. |
| [`../architecture/MOBILE_TECHNICIAN_ACCESS.md`](../architecture/MOBILE_TECHNICIAN_ACCESS.md) | Contrato de autenticación, permisos, ownership heredado, 404 opaco y frontera productiva que la app LAB actual no consume. |
| [`../architecture/MOBILE_SECURITY_CONTEXT.md`](../architecture/MOBILE_SECURITY_CONTEXT.md) | Identidad Mobile internal/client, tokens diferenciados, RBAC externo, membresía activa única, scope organizacional, realtime y push. |
| [`../architecture/MOBILE_NOTIFICATIONS_V1.md`](../architecture/MOBILE_NOTIFICATIONS_V1.md) | Contrato de persistencia, dispositivos, eventos, destinatarios, entrega Expo, deep links y sincronización móvil V1. |
| [`../architecture/COMMUNICATIONS_REALTIME.md`](../architecture/COMMUNICATIONS_REALTIME.md) | Contrato final A–I de Comunicaciones: persistencia/orden, REST+WebSocket, seguridad, optimistic UI, sync, typing, recibos, menciones, grupos, push, lifecycle y compuerta multi-worker. |
| [`../architecture/LAB_WORK_ORDERS.md`](../architecture/LAB_WORK_ORDERS.md) | Contrato temporal/removible de OT LAB: grupo histórico, cohortes de cierre grupal/individual, folios 6400–6999, eliminación segura, PDF, exportación multisesión y retiro. |
| [`../architecture/WORK_ORDER_DELETION.md`](../architecture/WORK_ORDER_DELETION.md) | Contrato de eliminación física administrativa de una OT productiva, ownership, recursos compartidos, atomicidad, archivos y exclusión explícita del cliente móvil LAB. |
| [`../architecture/OPERATIONAL_TICKETS_AND_LAB_REOPENING.md`](../architecture/OPERATIONAL_TICKETS_AND_LAB_REOPENING.md) | Lifecycle de Tickets, reapertura versionada, firma histórica/activa, filtros paginados, permisos y auditoría del vertical LAB. |
| [`../architecture/database/SCHEMA_RECOVERY.md`](../architecture/database/SCHEMA_RECOVERY.md) | Contrato reproducible de ciclo Alembic, upgrade histórico, respaldo oficial y restore drill. |
| [`../architecture/ACTIVITY_INSTITUTIONAL.md`](../architecture/ACTIVITY_INSTITUTIONAL.md) | Contrato genérico de conversación, eventos, menciones, adjuntos, atención, no leídos y permisos por entidad. |
| [`../architecture/sales/QUOTATION_CONTROLLED_UNLOCK.md`](../architecture/sales/QUOTATION_CONTROLLED_UNLOCK.md) | Desbloqueo temporal, revisión/delta y reconstrucción física atómica del ETS virgen con el mismo folio. |
| [`../architecture/services/SERVICE_TYPE_AND_LINKED_LABORATORIES.md`](../architecture/services/SERVICE_TYPE_AND_LINKED_LABORATORIES.md) | Taxonomía acreditado/trazable/vinculado, empresas, prefijos y snapshots. |
| [`../architecture/folios/CERTIFICATE_AND_WORK_ORDER_FOLIOS.md`](../architecture/folios/CERTIFICATE_AND_WORK_ORDER_FOLIOS.md) | Formatos compactos, contadores por prefijo/año, pisos 2026 y concurrencia. |
| [`../architecture/resolution-engine/README.MD`](../architecture/resolution-engine/README.MD) | Entrada normativa del Motor de Resoluciones; ordena la lectura de visión, principios, arquitectura, datos, flujos, API, casos, seguridad y Roadmap. |
| [`../architecture/resolution-engine/13_IMPLEMENTATION_MATRIX.md`](../architecture/resolution-engine/13_IMPLEMENTATION_MATRIX.md) | Orden técnico aprobado, dependencias, deuda bloqueante, gates y protocolo de revisión fase por fase del Motor de Resoluciones. |
| [`../architecture/resolution-engine/14_PERSISTENCE_SCHEMA.md`](../architecture/resolution-engine/14_PERSISTENCE_SCHEMA.md) | Contrato implementado del esquema general, versionado, reconstruible e históricamente inmutable de la Fase 2. |
| [`../architecture/resolution-engine/15_SECURITY_GOVERNANCE.md`](../architecture/resolution-engine/15_SECURITY_GOVERNANCE.md) | Contrato implementado de identidad, permisos, políticas, segregación, autorización base y evidencia de seguridad de la Fase 3. |
| [`../architecture/resolution-engine/16_LIFECYCLE_ORCHESTRATION.md`](../architecture/resolution-engine/16_LIFECYCLE_ORCHESTRATION.md) | Contrato implementado de creación, máquina de estados, invariantes, auditoría y orquestación interna sin efectos de la Fase 4. |
| [`../architecture/resolution-engine/17_EXECUTION_RUNTIME.md`](../architecture/resolution-engine/17_EXECUTION_RUNTIME.md) | Contrato implementado de ejecución controlada, acciones, checkpoints, idempotencia, locks y publicación explícita de outbox de la Fase 5. |
| [`../architecture/resolution-engine/18_COMPENSATION_ENGINE.md`](../architecture/resolution-engine/18_COMPENSATION_ENGINE.md) | Contrato implementado de planificación y ejecución compensatoria síncrona, Lifecycle, autorización exacta, checkpoints, idempotencia, locks, auditoría y outbox de la Fase 6. |
| [`../architecture/resolution-engine/19_PHASE_7_OPENING.md`](../architecture/resolution-engine/19_PHASE_7_OPENING.md) | Apertura aprobada, objetivo, alcance, exclusiones, entregables, invariantes y gate de Fase 7 — Auditoría y Evidencia. |
| [`../architecture/resolution-engine/20_AUDIT_EVIDENCE.md`](../architecture/resolution-engine/20_AUDIT_EVIDENCE.md) | Contrato implementado de reconstrucción, evidencia verificable, autorización de consultas, timeline y diagnósticos de integridad de Fase 7. |
| [`../architecture/resolution-engine/21_PHASE_8_OPENING.md`](../architecture/resolution-engine/21_PHASE_8_OPENING.md) | Apertura oficial, alcance, exclusiones, invariantes y gate de Fase 8 — Seguridad integral. |
| [`../architecture/resolution-engine/22_INTEGRAL_SECURITY.md`](../architecture/resolution-engine/22_INTEGRAL_SECURITY.md) | Contrato implementado de controles canónicos, semántica de uso, consumo transaccional anti-replay y protección de límites críticos del Motor en Fase 8. |
| [`../architecture/resolution-engine/23_PHASE_9_OPENING.md`](../architecture/resolution-engine/23_PHASE_9_OPENING.md) | Apertura oficial, integración gradual, ownership, límites, exclusiones y gates de Fase 9 — Integración con ERP MYC. |
| [`../architecture/resolution-engine/24_PHASE_9_CERTIFICATES_INTEGRATION.md`](../architecture/resolution-engine/24_PHASE_9_CERTIFICATES_INTEGRATION.md) | Contrato implementado del primer vertical de Fase 9: Certificados, provider read-only, gateways, servicio canónico, idempotencia y compensación. |
| [`../architecture/resolution-engine/25_PHASE_10_OPENING.md`](../architecture/resolution-engine/25_PHASE_10_OPENING.md) | Apertura oficial de Fase 10: contratos públicos versionados, API institucional, SDK, seguridad, compatibilidad, exclusiones y gate previo a distribución. |
| [`../architecture/resolution-engine/26_PUBLIC_API_SDK.md`](../architecture/resolution-engine/26_PUBLIC_API_SDK.md) | Contrato implementado de la API pública v1, autenticación de consumidores, organización, idempotencia, cursor `c1` opaco ligado a consulta, SDK y compatibilidad de Fase 10. |
| [`../architecture/resolution-engine/27_PHASE_11_OPENING.md`](../architecture/resolution-engine/27_PHASE_11_OPENING.md) | Apertura aprobada, alcance, invariantes, exclusiones y gate de Fase 11 — Motor Distribuido. |
| [`../architecture/resolution-engine/28_DISTRIBUTED_RUNTIME.md`](../architecture/resolution-engine/28_DISTRIBUTED_RUNTIME.md) | Contrato implementado de cola durable, workers, leases/fencing, recovery, retry determinista y observabilidad distribuida. |
| [`../architecture/resolution-engine/29_PHASE_12_RESOLUTION_CENTER.md`](../architecture/resolution-engine/29_PHASE_12_RESOLUTION_CENTER.md) | Apertura y contrato implementado del Centro de Resoluciones: consola, API interna, proyecciones, flujo guiado, permisos y ejecución independiente de sesión. |
| [`../architecture/resolution-engine/30_PHASE_13_RESOLUTION_CENTER_CONSOLIDATION.md`](../architecture/resolution-engine/30_PHASE_13_RESOLUTION_CENTER_CONSOLIDATION.md) | Contrato implementado de registro institucional, formularios dinámicos, indicadores, expediente e integración operativa end-to-end de Fase 13. |
| [`../architecture/resolution-engine/31_PHASE_14_INTEGRATION_EXPANSION.md`](../architecture/resolution-engine/31_PHASE_14_INTEGRATION_EXPANSION.md) | Contrato implementado de composición institucional y segundo vertical determinista de equipo adicional de Fase 14. |
| [`../architecture/resolution-engine/32_PHASE_15_ADMINISTRATIVE_TOOLS.md`](../architecture/resolution-engine/32_PHASE_15_ADMINISTRATIVE_TOOLS.md) | Contrato en revisión de Herramientas administrativas y continuidad ETS mediante restauración, reconstrucción y baja diferenciadas. |
| [`../modules/control-documental/PLANTILLAS_MAESTRAS.md`](../modules/control-documental/PLANTILLAS_MAESTRAS.md) | Contrato técnico vigente de Masters XLSX y snapshots. |
| [`../modules/captura/PAQUETE_CAPTURA.md`](../modules/captura/PAQUETE_CAPTURA.md) | Elegibilidad, diagnóstico y estructura de entrega del Paquete de Captura. |
| [`../modules/calidad/AUTENTICACION_CERTIFICADOS.md`](../modules/calidad/AUTENTICACION_CERTIFICADOS.md) | Contrato vigente de aprobación del Master, generación de PDF y autenticación. |

Estos documentos no sustituyen `PROJECT_STATUS.md`: una arquitectura puede estar vigente aunque su implementación esté incompleta.

## Cierres técnicos

| Documento | Alcance del cierre |
| --- | --- |
| [`../closures/CLIENT_DELETION_CLOSURE.md`](../closures/CLIENT_DELETION_CLOSURE.md) | Semántica de eliminación, archivo y restauración de Clientes. |
| [`../closures/IMPLEMENTACION_MOTOR_HOJAS_CAMPO_FASE_1.md`](../closures/IMPLEMENTACION_MOTOR_HOJAS_CAMPO_FASE_1.md) | Entrega de fase 1 del motor base de Hojas de Campo. |
| [`../closures/REPORTE_CARGA_INICIAL_CATALOGOS_SAT.md`](../closures/REPORTE_CARGA_INICIAL_CATALOGOS_SAT.md) | Evidencia de carga inicial SAT. |
| [`../closures/DOCUMENT_REORGANIZATION_REPORT_2026-07-21.md`](../closures/DOCUMENT_REORGANIZATION_REPORT_2026-07-21.md) | Cierre de esta reorganización y matriz de movimientos/conflictos. |
| [`../closures/INTEGRACION_PAGOS_FACTURACION_2026-07-29.md`](../closures/INTEGRACION_PAGOS_FACTURACION_2026-07-29.md) | Integración del registro/historial de pagos, cartera, conservación al timbrar y refresco financiero dentro del Workbench único. |
| [`../closures/ACTIVITY_INSTITUTIONAL_2026-07-29.md`](../closures/ACTIVITY_INSTITUTIONAL_2026-07-29.md) | Cierre técnico de Actividad transversal, pendiente de revisión formal. |
| [`../closures/SALES_UNLOCK_AND_SERVICE_TYPES_2026-07-29.md`](../closures/SALES_UNLOCK_AND_SERVICE_TYPES_2026-07-29.md) | Cierre técnico del desbloqueo, reconstrucción ETS, tipos vinculados y folios institucionales. |
| [`../closures/SECURITY_CONTAINMENT_STAGE_1_2026-08-03.md`](../closures/SECURITY_CONTAINMENT_STAGE_1_2026-08-03.md) | Dictamen aprobado y cerrado de deny-by-default, JWT seguro, portal aislado, permisos frontend y pruebas 401/403/IDOR. |
| [`../closures/SECURITY_STAGE_2A_SCHEMA_RECOVERY_2026-08-04.md`](../closures/SECURITY_STAGE_2A_SCHEMA_RECOVERY_2026-08-04.md) | Cierre técnico de integridad de esquema, reversibilidad Alembic, upgrade histórico, respaldo alineado y restore drill reproducible. |
| [`../closures/SECURITY_STAGE_2B_CAPABILITY_MODEL_2026-08-04.md`](../closures/SECURITY_STAGE_2B_CAPABILITY_MODEL_2026-08-04.md) | Cierre técnico del modelo institucional de capacidades, gobernanza obligatoria y brechas frente al bootstrap/API, sin implementar RBAC. |
| [`../closures/APROBACION_CATALOGO_INSTITUCIONAL_FUNCIONAL_2026-08-04.md`](../closures/APROBACION_CATALOGO_INSTITUCIONAL_FUNCIONAL_2026-08-04.md) | Cierre documental de aprobación y congelamiento de la versión 1.0 del Catálogo Institucional Funcional, con metadatos completos, distribuciones, excepciones y validaciones de identidad. |
| [`../closures/STAGE_3_FILES_AND_UPLOADS_2026-08-04.md`](../closures/STAGE_3_FILES_AND_UPLOADS_2026-08-04.md) | Cierre técnico de ETAPA 3: perfiles de carga, ZIP seguro, almacenamiento/entrega institucional, artefactos Git y validaciones; terminado y en revisión. |
| [`../closures/CLIENT_PORTAL_INTEGRATION_2026-08-04.md`](../closures/CLIENT_PORTAL_INTEGRATION_2026-08-04.md) | Cierre técnico del Portal del Cliente: identidad separada, registro, invitaciones, membresías, roles, aislamiento, frontend y validaciones; terminado y en revisión. |
| [`../closures/PORTAL_USER_ACCESS_ADMINISTRATION_2026-08-05.md`](../closures/PORTAL_USER_ACCESS_ADMINISTRATION_2026-08-05.md) | Cierre correctivo de administración conjunta, multirrol, vinculación, invitaciones, configuración, bloqueo y Usuarios dentro del Portal; terminado y en revisión. |
| [`../closures/MOBILE_SECURITY_CONTEXT_2026-08-26.md`](../closures/MOBILE_SECURITY_CONTEXT_2026-08-26.md) | Cierre técnico de identidad Mobile internal/client, RBAC externo, membership activa única, scope LAB y protección realtime/push. |
| [`../closures/ETS_INTEGRITY_SPRINT_2026-08-10.md`](../closures/ETS_INTEGRITY_SPRINT_2026-08-10.md) | Cierre técnico y micro-sprint final de autoridad única ETS, lifecycle, actor obligatorio, autoautorización administrativa, auditoría/eventos y regresión; aprobado con observaciones. |
| [`../closures/CERTIFICATE_AUTHENTICATION_INTEGRITY_SPRINT_2026-08-10.md`](../closures/CERTIFICATE_AUTHENTICATION_INTEGRITY_SPRINT_2026-08-10.md) | Cierre P0 de autenticación: Calidad única, autoridad transaccional, retiro ETS, actor/audit/evento, concurrencia y regresión; terminado y en revisión. |
| [`../closures/TD_027_CAPABILITY_GATE_RECONCILIATION_2026-08-11.md`](../closures/TD_027_CAPABILITY_GATE_RECONCILIATION_2026-08-11.md) | Conciliación de 20/2 a baseline gobernado 19/0, Portal `portal.read`, delete de certificados de patrón, matriz A–H y decisiones institucionales bloqueantes. |
| [`../closures/ETS_MULTIPLE_EVOLVED_PHASE_1_2026-08-12.md`](../closures/ETS_MULTIPLE_EVOLVED_PHASE_1_2026-08-12.md) | Entrega técnica de Fase 1 ETS múltiple/evolucionado; estado obligatorio `EN REVISIÓN`, sin abrir fase posterior. |
| [`../closures/MOBILE_TECHNICIAN_ACCESS_2026-08-12.md`](../closures/MOBILE_TECHNICIAN_ACCESS_2026-08-12.md) | Cierre técnico de ocho lecturas móviles con scope asignado, permisos compuestos, matriz A/B y compatibilidad web. |
| [`../closures/LAB_WORK_ORDERS_VERTICAL_SLICE_2026-08-13.md`](../closures/LAB_WORK_ORDERS_VERTICAL_SLICE_2026-08-13.md) | Cierre técnico del vertical OT LAB backend/móvil; pendiente de aceptación física en iPhone. |
| [`../closures/LAB_CLOSURE_COHORTS_2026-08-27.md`](../closures/LAB_CLOSURE_COHORTS_2026-08-27.md) | Cierre técnico de firma/finalización grupal o individual por cohorte sin disolver el grupo histórico LAB. |
| [`../closures/LAB_RECEPTION_FIELD_SHEETS_PHASE_3_2026-09-01.md`](../closures/LAB_RECEPTION_FIELD_SHEETS_PHASE_3_2026-09-01.md) | Cierre técnico de recepción LAB, transiciones FieldSheet, permisos Captura, compatibilidad legacy y validaciones Fase 3. |
| [`../closures/LAB_FIELD_SHEETS_PHASE_6_2026-09-01.md`](../closures/LAB_FIELD_SHEETS_PHASE_6_2026-09-01.md) | Cierre técnico de autoridad declarativa, revisiones, PDF inmutable, captura Mobile y bandeja agregada de Hojas de Campo LAB Fase 6. |
| [`../closures/FIELD_SHEET_DSL_PHASES_4_5_2026-09-02.md`](../closures/FIELD_SHEET_DSL_PHASES_4_5_2026-09-02.md) | Cierre técnico del DSL avanzado de tablas, layouts PDF seguros, perfiles MYC/CAPYMET y compatibilidad renderer v1. |
| [`../closures/FIELD_SHEET_CATALOG_PHASE_6A1_2026-09-03.md`](../closures/FIELD_SHEET_CATALOG_PHASE_6A1_2026-09-03.md) | Evidencia de materialización y QA documental de Temperatura/Presión MYC; Fase 6A.1 EN REVISIÓN. |
| [`../closures/LAB_CLIENT_IMPORT_AND_QUERY_2026-09-02.md`](../closures/LAB_CLIENT_IMPORT_AND_QUERY_2026-09-02.md) | Cierre técnico del importador XLSX estructurado y la consulta/paginación eficiente de LabClient en MYC Mobile. |
| [`../closures/WORK_ORDER_DELETION_2026-08-17.md`](../closures/WORK_ORDER_DELETION_2026-08-17.md) | Implementación y validación del borrado físico administrativo de OT productiva con dependencias, firma compartida, rollback y lectura móvil. |
| [`../closures/LAB_GROUP_REQUEST_DELETION_RECONCILIATION_2026-08-26.md`](../closures/LAB_GROUP_REQUEST_DELETION_RECONCILIATION_2026-08-26.md) | Cierre de la reconciliación transaccional entre borrado OT LAB y solicitudes anticipadas aprobadas, sin reutilizar folios. |
| [`../closures/MOBILE_TICKETS_AND_REOPENING_2026-08-14.md`](../closures/MOBILE_TICKETS_AND_REOPENING_2026-08-14.md) | Cierre técnico en revisión manual de filtros, Tickets, reapertura, revisiones y firmas LAB. |
| [`../closures/MOBILE_NOTIFICATIONS_V1_2026-08-14.md`](../closures/MOBILE_NOTIFICATIONS_V1_2026-08-14.md) | Cierre técnico de notificaciones persistentes/push y sincronización automática; pendiente de aceptación física iOS/Android. |
| [`../closures/COMMUNICATIONS_REALTIME_STAGE_A_2026-08-17.md`](../closures/COMMUNICATIONS_REALTIME_STAGE_A_2026-08-17.md) | Cierre técnico de contrato, WebSocket, hub y provider móvil de Comunicaciones Etapa A; pendiente de revisión y gate multi-worker. |
| [`../closures/COMMUNICATIONS_COMPLETE_2026-08-17.md`](../closures/COMMUNICATIONS_COMPLETE_2026-08-17.md) | Cierre técnico A–I de Comunicaciones con topología productiva verificada, modelo persistente, experiencia móvil, pruebas, respaldo y pendientes físicos; en revisión. |
| [`../closures/RESOLUTION_ENGINE_PHASE_0.md`](../closures/RESOLUTION_ENGINE_PHASE_0.md) | Ratificación, matriz, gates, validaciones y condición de aprobación de la Fase 0 del Motor de Resoluciones. |
| [`../closures/RESOLUTION_ENGINE_PHASE_1.md`](../closures/RESOLUTION_ENGINE_PHASE_1.md) | Contratos, catálogos, serialización canónica, runtime, registro versionado, aislamiento y validaciones de la Fase 1 del Motor de Resoluciones. |
| [`../closures/RESOLUTION_ENGINE_PHASE_2.md`](../closures/RESOLUTION_ENGINE_PHASE_2.md) | Modelo ORM, integridad, reconstrucción, inmutabilidad, migración reversible y validaciones de la Fase 2 del Motor de Resoluciones. |
| [`../closures/RESOLUTION_ENGINE_PHASE_3.md`](../closures/RESOLUTION_ENGINE_PHASE_3.md) | Identidad, permisos, políticas, segregación, autorización base, evidencia append-only, bloqueadores de autenticación y validaciones de la Fase 3. |
| [`../closures/RESOLUTION_ENGINE_PHASE_4.md`](../closures/RESOLUTION_ENGINE_PHASE_4.md) | Creación, Lifecycle, transiciones, invariantes, control optimista, orquestación pura y validaciones de la Fase 4. |
| [`../closures/RESOLUTION_ENGINE_PHASE_5.md`](../closures/RESOLUTION_ENGINE_PHASE_5.md) | Ejecución controlada, acciones, persistencia, idempotencia, locks, outbox, límites y validaciones de la Fase 5. |
| [`../closures/RESOLUTION_ENGINE_PHASE_6.md`](../closures/RESOLUTION_ENGINE_PHASE_6.md) | Dominio, contratos, persistencia, Lifecycle, ejecución síncrona, invariantes, límites y validaciones del Motor de Compensación de la Fase 6. |
| [`../closures/RESOLUTION_ENGINE_PHASE_7.md`](../closures/RESOLUTION_ENGINE_PHASE_7.md) | Modelo de auditoría/evidencia, consultas autorizadas, reconstrucción, integridad, pruebas y límites de la Fase 7. |
| [`../closures/RESOLUTION_ENGINE_PHASE_8.md`](../closures/RESOLUTION_ENGINE_PHASE_8.md) | Catálogo integral, autorización exacta, límites protegidos, migración, pruebas y exclusiones de la Fase 8. |
| [`../closures/RESOLUTION_ENGINE_PHASE_9_CERTIFICATES.md`](../closures/RESOLUTION_ENGINE_PHASE_9_CERTIFICATES.md) | Cierre aprobado del vertical Certificados de Fase 9, con correcciones bloqueantes, validaciones y commits oficiales. |
| [`../closures/RESOLUTION_ENGINE_PHASE_10.md`](../closures/RESOLUTION_ENGINE_PHASE_10.md) | Cierre técnico de implementación de API/SDK v1, pendiente de revisión y aprobación formal de Fase 10. |
| [`../closures/RESOLUTION_ENGINE_PHASE_11.md`](../closures/RESOLUTION_ENGINE_PHASE_11.md) | Cierre técnico aprobado de distribución, coordinación multinodo, recuperación y observabilidad de Fase 11. |
| [`../closures/RESOLUTION_ENGINE_PHASE_12.md`](../closures/RESOLUTION_ENGINE_PHASE_12.md) | Cierre técnico aprobado de consola operativa, API interna, proyecciones y flujo end-to-end de Fase 12. |
| [`../closures/RESOLUTION_ENGINE_PHASE_13.md`](../closures/RESOLUTION_ENGINE_PHASE_13.md) | Cierre aprobado de consolidación, patrón universal e integración Certificados end-to-end de Fase 13. |
| [`../closures/RESOLUTION_ENGINE_PHASE_14.md`](../closures/RESOLUTION_ENGINE_PHASE_14.md) | Cierre técnico de expansión institucional, equipo adicional, composición única y validaciones de Fase 14, pendiente de revisión formal. |

## Auditorías

| Documento | Fecha / autoridad |
| --- | --- |
| [`../audits/ADMINISTRATIVE_OPERATIONS_INVENTORY_2026-08-25.md`](../audits/ADMINISTRATIVE_OPERATIONS_INVENTORY_2026-08-25.md) | Inventario transversal 2026-08-25 de operaciones extraordinarias, owners, prioridades y límites seguros; fotografía que fundamenta Fase 15. |
| [`../audits/auditoria_integral_2026_08_10/AUDITORIA_INTEGRAL_ERP_MYC_2026_08.md`](../audits/auditoria_integral_2026_08_10/AUDITORIA_INTEGRAL_ERP_MYC_2026_08.md) | Corte integral 2026-08-10; informe principal de ocho entregables con módulos, fases, deuda, seguridad, pruebas, inventario y plan. Fotografía diagnóstica; no sustituye los canónicos sincronizados. |
| [`../audits/AUDITORIA_INTEGRAL_ERP_MYC_2026-08-03.md`](../audits/AUDITORIA_INTEGRAL_ERP_MYC_2026-08-03.md) | Corte integral 2026-08-03; informe principal de una suite de diez entregables diagnósticos, matrices, plan y evidencia reproducible. No modifica por sí mismo el canon. |
| [`../audits/VALIDACION_FUNCIONAL_CATALOGO_INSTITUCIONAL_2026-08-04.md`](../audits/VALIDACION_FUNCIONAL_CATALOGO_INSTITUCIONAL_2026-08-04.md) | Revisión funcional completa previa a ETAPA 3; contrasta las 36 superficies técnicas con el ERP objetivo, documenta diferencias y fundamenta el catálogo funcional propuesto. |
| [`../audits/FILE_SURFACE_INVENTORY_2026-08-04.md`](../audits/FILE_SURFACE_INVENTORY_2026-08-04.md) | Fotografía inicial de cargas, descargas, formatos, límites, ownership, rutas, artefactos y riesgos que fundamenta ETAPA 3. |
| [`../auditorias/AUDITORIA_MATRIZ_EXCEPCIONES_ERP_MYC.md`](../auditorias/AUDITORIA_MATRIZ_EXCEPCIONES_ERP_MYC.md) | Corte transversal de excepciones 2026-07-22; ubicación solicitada expresamente para este entregable, con la misma autoridad de fotografía que `audits/`. |
| [`../audits/AUDITORIA_INTEGRAL_AVANCE_ERP_MYC_2026-07-21.md`](../audits/AUDITORIA_INTEGRAL_AVANCE_ERP_MYC_2026-07-21.md) | Corte integral 2026-07-21; evidencia base del canon actual. |
| [`../audits/AUDITORIA_PAQUETE_CAPTURA_2026-07-17.md`](../audits/AUDITORIA_PAQUETE_CAPTURA_2026-07-17.md) | Diagnóstico puntual de Captura al 2026-07-17. |
| [`../audits/AUDITORIA_TECNICA_FACTURACION_CFDI_4_0.md`](../audits/AUDITORIA_TECNICA_FACTURACION_CFDI_4_0.md) | Corte 2026-07-14 superado por integración posterior. |
| [`../audits/INTEGRACION_OPERATIVA_HOJAS_CAMPO_ESTADO.md`](../audits/INTEGRACION_OPERATIVA_HOJAS_CAMPO_ESTADO.md) | Verificación puntual de integración al 2026-07-13. |
| [`../audits/ACTIVITY_AND_NOTES_AUDIT_2026-07-29.md`](../audits/ACTIVITY_AND_NOTES_AUDIT_2026-07-29.md) | Inventario semántico y corte de integración transversal de Actividad/notas. |
| [`../audits/ETS_PHASE_1_EXCEPTION_CANDIDATES_2026-08-12.md`](../audits/ETS_PHASE_1_EXCEPTION_CANDIDATES_2026-08-12.md) | Catálogo paralelo de candidatos y antipatrones detectados durante Fase 1; no autoriza excepciones. |
| [`../audits/MYC_TOOLKIT_AUDIT.md`](../audits/MYC_TOOLKIT_AUDIT.md) | Corte del Toolkit al 2026-07-14, parcialmente superado. |

## Diseño futuro

| Documento | Regla de uso |
| --- | --- |
| [`../architecture/future/MDE_SPEC.md`](../architecture/future/MDE_SPEC.md) | Especificación futura de MDE; no determina alcance, deuda ni pendientes actuales. |

## Histórico y archivo

### Estado operativo

- [`../BACKUP_ESTADO_ACTUAL.md`](../BACKUP_ESTADO_ACTUAL.md): corte operativo vigente requerido por `AGENTS.md`; sólo resume estado verificable, migraciones, validaciones y pendientes.

### Arquitectura histórica

- [`../archive/architecture/SISTEMA_ERP_MYC_ESPECIFICACION_V2.md`](../archive/architecture/SISTEMA_ERP_MYC_ESPECIFICACION_V2.md)
- [`../archive/architecture/SISTEMA_ERP_MYC_V3.md`](../archive/architecture/SISTEMA_ERP_MYC_V3.md)
- [`../archive/architecture/base-datos-mvp.md`](../archive/architecture/base-datos-mvp.md)
- [`../architecture/sales/QUOTATION_CHANGE_SERVICE_EXCEPTION.md`](../architecture/sales/QUOTATION_CHANGE_SERVICE_EXCEPTION.md): contrato sustituido conservado como evidencia.
- [`../closures/QUOTATION_CHANGE_SERVICE_EXCEPTION.md`](../closures/QUOTATION_CHANGE_SERVICE_EXCEPTION.md): cierre sustituido conservado como evidencia.

### Hojas de Campo históricas

- [`../archive/field-sheets/ANALISIS_HOJAS_CAMPO_ORIGINALES.md`](../archive/field-sheets/ANALISIS_HOJAS_CAMPO_ORIGINALES.md)
- [`../archive/field-sheets/FIELD_SHEET_LAB_CONSOLIDATED.md`](../archive/field-sheets/FIELD_SHEET_LAB_CONSOLIDATED.md)
- [`../archive/field-sheets/sources/IMPLEMENTACION_23_HOJAS_CAMPO_LAB.md`](../archive/field-sheets/sources/IMPLEMENTACION_23_HOJAS_CAMPO_LAB.md)
- [`../archive/field-sheets/sources/LABORATORIO_HOJAS_CAMPO.md`](../archive/field-sheets/sources/LABORATORIO_HOJAS_CAMPO.md)
- [`../archive/field-sheets/sources/PROJECT_STATUS_PARTIAL_DRAFT_2026-07-21.md`](../archive/field-sheets/sources/PROJECT_STATUS_PARTIAL_DRAFT_2026-07-21.md)

### Proceso y seguridad históricos

- [`../archive/process/flujo-general.md`](../archive/process/flujo-general.md)
- [`../archive/process/reglas-negocio.md`](../archive/process/reglas-negocio.md)
- [`../archive/security/permisos.md`](../archive/security/permisos.md)

## Fusiones y reemplazos

| Fuentes | Documento resultante | Tratamiento |
| --- | --- | --- |
| `reglas-negocio.md`, reglas ratificadas de V2/V3 y evidencia reciente | [`BUSINESS_RULES.md`](BUSINESS_RULES.md) | El original se archivó íntegro; sólo reglas confirmadas pasaron al canon. |
| `permisos.md` y matriz ejecutable | [`../architecture/PERMISSIONS_MATRIX.md`](../architecture/PERMISSIONS_MATRIX.md) | El original se archivó; la nueva matriz se auditó contra código. |
| `LABORATORIO_HOJAS_CAMPO.md` + `IMPLEMENTACION_23_HOJAS_CAMPO_LAB.md` | [`../archive/field-sheets/FIELD_SHEET_LAB_CONSOLIDATED.md`](../archive/field-sheets/FIELD_SHEET_LAB_CONSOLIDATED.md) | Consulta consolidada; fuentes íntegras preservadas en `sources/`. |
| V2, V3, flujo general, bitácora y auditoría integral | Los ocho documentos canónicos de `project/` | Se extrajo sólo información vigente; los orígenes conservaron su contenido. |

La bitácora manual `BACKUP_ESTADO_ACTUAL (1).md` y la extracción estática
`CATALOGO_PERMISOS_ERP_MYC_2026-08-04.md` se retiraron el 2026-08-25: no eran
autoridad, no tenían referencias activas y su trazabilidad permanece en Git.
El snapshot operativo y los contratos institucionales vigentes conservan la
información necesaria sin mantener copias manuales.

## Reglas para futuras consultas y auditorías

1. Empezar siempre aquí.
2. Consultar `PROJECT_STATUS.md` antes de buscar pendientes en auditorías o cierres.
3. No convertir un límite histórico, diseño futuro o propuesta en pendiente vigente si no aparece en `OBSERVATIONS_REGISTER.md`, `TECHNICAL_DEBT.md` o `CURRENT_SCOPE.md`.
4. No declarar un módulo sellado desde un cierre técnico; sólo `PROJECT_STATUS.md` puede hacerlo.
5. Toda nueva auditoría debe quedar en `audits/`, incluir fecha y declarar que es una fotografía. La carpeta `auditorias/` se reconoce sólo para `AUDITORIA_MATRIZ_EXCEPCIONES_ERP_MYC.md`, porque su ruta fue un entregable explícito; no crea una segunda jerarquía ni autoriza nuevos documentos allí por defecto.
6. Un documento sustituido se mueve a `archive/` cuando conserva evidencia
   única; puede eliminarse cuando no contiene información única, no es una
   instrucción operativa, la autoridad vigente está identificada y Git preserva
   la trazabilidad.
7. Toda contradicción nueva debe resolverse actualizando este índice y la relación `prevalece/reemplazado por` de ambos documentos.

## Mantenimiento documental obligatorio

La documentación forma parte del desarrollo. Toda tarea que modifique comportamiento, arquitectura, flujo, datos, permisos, estados, UX, scripts, pruebas o alcance debe revisar y actualizar en el mismo trabajo los documentos afectados; no se requiere una solicitud adicional del usuario.

| Cambio observado | Documento obligatorio cuando corresponda |
| --- | --- |
| Estado de un módulo | `PROJECT_STATUS.md` |
| Alcance funcional | `CURRENT_SCOPE.md` |
| Flujo operativo | `CURRENT_PROCESS_FLOW.md` |
| Regla de negocio | `BUSINESS_RULES.md` |
| Decisión arquitectónica o funcional | `DECISIONS.md` |
| Observación nueva, parcial o resuelta | `OBSERVATIONS_REGISTER.md` |
| Deuda técnica nueva, modificada o retirada | `TECHNICAL_DEBT.md` |
| Contrato técnico | `architecture/` o `modules/` |
| Revisión integral o fotografía fechada | `audits/` |
| Implementación concluida y validada | `closures/` |
| Estado operativo, migraciones y validaciones | `BACKUP_ESTADO_ACTUAL.md` |
| Archivo nuevo o responsabilidad material | `PROJECT_FILE_REGISTRY.md` |

Antes de finalizar se deben corregir referencias cruzadas y comprobar ausencia de contradicciones, reglas duplicadas, decisiones incompatibles y estados divergentes. Toda respuesta final debe contener `## Documentación actualizada`, incluso cuando la conclusión sea que no hubo cambios documentales, en cuyo caso debe incluir la justificación.

Auditoría vigente del Bloque 2 OT LAB: [`../audits/MOBILE_WORK_ORDER_GROUPS_BLOCK_2_AUDIT_2026-08-26.md`](../audits/MOBILE_WORK_ORDER_GROUPS_BLOCK_2_AUDIT_2026-08-26.md).
