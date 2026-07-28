> Estado: VIGENTE
>
> Tipo: Vigente (canónico)
>
> Autoridad: Máxima para jerarquía, clasificación y resolución de conflictos documentales
>
> Prevalece sobre: cualquier índice, lista de documentos o instrucción de autoridad contenida en documentos anteriores
>
> Corte verificado: 2026-07-28

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
| [`../architecture/PERMISSIONS_MATRIX.md`](../architecture/PERMISSIONS_MATRIX.md) | Roles/permisos declarados y brechas de aplicación. |
| [`../architecture/INVOICE_WORKBENCH_CONTROLLER.md`](../architecture/INVOICE_WORKBENCH_CONTROLLER.md) | Controlador único, contexto explícito y composición obligatoria de la pestaña Facturación del ETS. |
| [`../architecture/CALIBRATION_SCOPE_CONTRACT.md`](../architecture/CALIBRATION_SCOPE_CONTRACT.md) | Claves canónicas, propagación automática y compatibilidad de datos de `calibration_scope`. |
| [`../architecture/COMPOSITE_CATALOG_SERVICES.md`](../architecture/COMPOSITE_CATALOG_SERVICES.md) | Relación normalizada, validaciones y expansión comercial→operativa de Servicios Compuestos. |
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
| [`../closures/RESOLUTION_ENGINE_PHASE_0.md`](../closures/RESOLUTION_ENGINE_PHASE_0.md) | Ratificación, matriz, gates, validaciones y condición de aprobación de la Fase 0 del Motor de Resoluciones. |
| [`../closures/RESOLUTION_ENGINE_PHASE_1.md`](../closures/RESOLUTION_ENGINE_PHASE_1.md) | Contratos, catálogos, serialización canónica, runtime, registro versionado, aislamiento y validaciones de la Fase 1 del Motor de Resoluciones. |
| [`../closures/RESOLUTION_ENGINE_PHASE_2.md`](../closures/RESOLUTION_ENGINE_PHASE_2.md) | Modelo ORM, integridad, reconstrucción, inmutabilidad, migración reversible y validaciones de la Fase 2 del Motor de Resoluciones. |
| [`../closures/RESOLUTION_ENGINE_PHASE_3.md`](../closures/RESOLUTION_ENGINE_PHASE_3.md) | Identidad, permisos, políticas, segregación, autorización base, evidencia append-only, bloqueadores de autenticación y validaciones de la Fase 3. |
| [`../closures/RESOLUTION_ENGINE_PHASE_4.md`](../closures/RESOLUTION_ENGINE_PHASE_4.md) | Creación, Lifecycle, transiciones, invariantes, control optimista, orquestación pura y validaciones de la Fase 4. |
| [`../closures/RESOLUTION_ENGINE_PHASE_5.md`](../closures/RESOLUTION_ENGINE_PHASE_5.md) | Ejecución controlada, acciones, persistencia, idempotencia, locks, outbox, límites y validaciones de la Fase 5. |
| [`../closures/RESOLUTION_ENGINE_PHASE_6.md`](../closures/RESOLUTION_ENGINE_PHASE_6.md) | Dominio, contratos, persistencia, Lifecycle, ejecución síncrona, invariantes, límites y validaciones del Motor de Compensación de la Fase 6. |
| [`../closures/RESOLUTION_ENGINE_PHASE_7.md`](../closures/RESOLUTION_ENGINE_PHASE_7.md) | Modelo de auditoría/evidencia, consultas autorizadas, reconstrucción, integridad, pruebas y límites de la Fase 7. |
| [`../closures/RESOLUTION_ENGINE_PHASE_8.md`](../closures/RESOLUTION_ENGINE_PHASE_8.md) | Catálogo integral, autorización exacta, límites protegidos, migración, pruebas y exclusiones de la Fase 8. |

## Auditorías

| Documento | Fecha / autoridad |
| --- | --- |
| [`../auditorias/AUDITORIA_MATRIZ_EXCEPCIONES_ERP_MYC.md`](../auditorias/AUDITORIA_MATRIZ_EXCEPCIONES_ERP_MYC.md) | Corte transversal de excepciones 2026-07-22; ubicación solicitada expresamente para este entregable, con la misma autoridad de fotografía que `audits/`. |
| [`../audits/AUDITORIA_INTEGRAL_AVANCE_ERP_MYC_2026-07-21.md`](../audits/AUDITORIA_INTEGRAL_AVANCE_ERP_MYC_2026-07-21.md) | Corte integral 2026-07-21; evidencia base del canon actual. |
| [`../audits/AUDITORIA_PAQUETE_CAPTURA_2026-07-17.md`](../audits/AUDITORIA_PAQUETE_CAPTURA_2026-07-17.md) | Diagnóstico puntual de Captura al 2026-07-17. |
| [`../audits/AUDITORIA_TECNICA_FACTURACION_CFDI_4_0.md`](../audits/AUDITORIA_TECNICA_FACTURACION_CFDI_4_0.md) | Corte 2026-07-14 superado por integración posterior. |
| [`../audits/INTEGRACION_OPERATIVA_HOJAS_CAMPO_ESTADO.md`](../audits/INTEGRACION_OPERATIVA_HOJAS_CAMPO_ESTADO.md) | Verificación puntual de integración al 2026-07-13. |
| [`../audits/MYC_TOOLKIT_AUDIT.md`](../audits/MYC_TOOLKIT_AUDIT.md) | Corte del Toolkit al 2026-07-14, parcialmente superado. |

## Diseño futuro

| Documento | Regla de uso |
| --- | --- |
| [`../architecture/future/MDE_SPEC.md`](../architecture/future/MDE_SPEC.md) | Especificación futura de MDE; no determina alcance, deuda ni pendientes actuales. |

## Histórico y archivo

### Estado operativo y bitácora histórica

- [`../BACKUP_ESTADO_ACTUAL.md`](../BACKUP_ESTADO_ACTUAL.md): corte operativo vigente requerido por `AGENTS.md`; sólo resume estado verificable, migraciones, validaciones y pendientes.
- [`../archive/project/BACKUP_ESTADO_ACTUAL_HISTORICO_2026-07-21.md`](../archive/project/BACKUP_ESTADO_ACTUAL_HISTORICO_2026-07-21.md): cronología acumulada anterior, conservada íntegra y sin autoridad actual.

### Arquitectura histórica

- [`../archive/architecture/SISTEMA_ERP_MYC_ESPECIFICACION_V2.md`](../archive/architecture/SISTEMA_ERP_MYC_ESPECIFICACION_V2.md)
- [`../archive/architecture/SISTEMA_ERP_MYC_V3.md`](../archive/architecture/SISTEMA_ERP_MYC_V3.md)
- [`../archive/architecture/base-datos-mvp.md`](../archive/architecture/base-datos-mvp.md)

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

## Reglas para futuras consultas y auditorías

1. Empezar siempre aquí.
2. Consultar `PROJECT_STATUS.md` antes de buscar pendientes en auditorías o cierres.
3. No convertir un límite histórico, diseño futuro o propuesta en pendiente vigente si no aparece en `OBSERVATIONS_REGISTER.md`, `TECHNICAL_DEBT.md` o `CURRENT_SCOPE.md`.
4. No declarar un módulo sellado desde un cierre técnico; sólo `PROJECT_STATUS.md` puede hacerlo.
5. Toda nueva auditoría debe quedar en `audits/`, incluir fecha y declarar que es una fotografía. La carpeta `auditorias/` se reconoce sólo para `AUDITORIA_MATRIZ_EXCEPCIONES_ERP_MYC.md`, porque su ruta fue un entregable explícito; no crea una segunda jerarquía ni autoriza nuevos documentos allí por defecto.
6. Todo documento sustituido debe moverse a `archive/` o conservar clasificación histórica, sin borrar su contenido.
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
