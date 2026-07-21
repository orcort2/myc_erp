> Estado: CIERRE TÉCNICO
>
> Tipo: Cierre técnico
>
> Autoridad: Media; evidencia de la reorganización documental realizada
>
> Prevalece sobre: inventarios documentales anteriores al 2026-07-21
>
> Entrada vigente: `../project/DOCUMENTATION_INDEX.md`

> Actualización posterior: la gobernanza integrada al desarrollo movió la bitácora histórica de `BACKUP_ESTADO_ACTUAL.md` a `archive/project/BACKUP_ESTADO_ACTUAL_HISTORICO_2026-07-21.md` y dejó en la raíz un corte operativo vigente. Para el árbol actual prevalece `DOCUMENTATION_INDEX.md`.

# Reporte de reorganización documental

Fecha: 2026-07-21  
Alcance: `docs/` y sus subcarpetas.  
Intervención: únicamente documentación; no se modificó código de producto, frontend, backend, esquema ni datos.

## Resultado ejecutivo

Se clasificaron todos los documentos Markdown bajo una jerarquía explícita y se creó un canon de ocho documentos en `docs/project/`. Cada documento declara Estado, Tipo, Autoridad y relación de prevalencia o reemplazo. `DOCUMENTATION_INDEX.md` quedó como entrada única y `PROJECT_STATUS.md` como única fuente del avance actual.

No se eliminó contenido histórico. Los documentos sustituidos se movieron a `archive/`, los reportes fechados a `audits/`, las evidencias de entrega a `closures/`, los contratos actuales a `architecture/`/`modules/` y el diseño MDE a `architecture/future/`.

## Documentos vigentes

### Canónicos de proyecto

1. `docs/project/DOCUMENTATION_INDEX.md`
2. `docs/project/PROJECT_STATUS.md`
3. `docs/project/CURRENT_SCOPE.md`
4. `docs/project/CURRENT_PROCESS_FLOW.md`
5. `docs/project/BUSINESS_RULES.md`
6. `docs/project/DECISIONS.md`
7. `docs/project/OBSERVATIONS_REGISTER.md`
8. `docs/project/TECHNICAL_DEBT.md`

### Inventario y arquitectura vigentes

9. `docs/PROJECT_FILE_REGISTRY.md` — autoridad de inventario, no de avance.
10. `docs/BACKUP_ESTADO_ACTUAL.md` — corte operativo vigente, no autoridad de avance.
11. `docs/architecture/CATALOGOS_SAT.md`
12. `docs/architecture/FIELD_SHEET_FIELD_REGISTRY.md`
13. `docs/architecture/PERMISSIONS_MATRIX.md`
14. `docs/modules/control-documental/PLANTILLAS_MAESTRAS.md`

## Documentos archivados e históricos

1. `docs/archive/project/BACKUP_ESTADO_ACTUAL_HISTORICO_2026-07-21.md` — bitácora cronológica íntegra sustituida por el corte operativo raíz.
2. `docs/archive/architecture/SISTEMA_ERP_MYC_ESPECIFICACION_V2.md`
3. `docs/archive/architecture/SISTEMA_ERP_MYC_V3.md`
4. `docs/archive/architecture/base-datos-mvp.md`
5. `docs/archive/field-sheets/ANALISIS_HOJAS_CAMPO_ORIGINALES.md`
6. `docs/archive/field-sheets/FIELD_SHEET_LAB_CONSOLIDATED.md`
7. `docs/archive/field-sheets/sources/IMPLEMENTACION_23_HOJAS_CAMPO_LAB.md`
8. `docs/archive/field-sheets/sources/LABORATORIO_HOJAS_CAMPO.md`
9. `docs/archive/field-sheets/sources/PROJECT_STATUS_PARTIAL_DRAFT_2026-07-21.md`
10. `docs/archive/process/flujo-general.md`
11. `docs/archive/process/reglas-negocio.md`
12. `docs/archive/security/permisos.md`

## Documentos de diseño futuro

1. `docs/architecture/future/MDE_SPEC.md`

MDE quedó separado de arquitectura vigente y expresamente excluido como fuente de pendientes actuales.

## Auditorías conservadas

1. `docs/audits/AUDITORIA_INTEGRAL_AVANCE_ERP_MYC_2026-07-21.md`
2. `docs/audits/AUDITORIA_PAQUETE_CAPTURA_2026-07-17.md`
3. `docs/audits/AUDITORIA_TECNICA_FACTURACION_CFDI_4_0.md`
4. `docs/audits/INTEGRACION_OPERATIVA_HOJAS_CAMPO_ESTADO.md`
5. `docs/audits/MYC_TOOLKIT_AUDIT.md`

## Cierres técnicos conservados

1. `docs/closures/CLIENT_DELETION_CLOSURE.md`
2. `docs/closures/IMPLEMENTACION_MOTOR_HOJAS_CAMPO_FASE_1.md`
3. `docs/closures/REPORTE_CARGA_INICIAL_CATALOGOS_SAT.md`
4. `docs/closures/DOCUMENT_REORGANIZATION_REPORT_2026-07-21.md`

## Documentos fusionados

| Fuentes | Resultado | Preservación |
| --- | --- | --- |
| `docs/reglas-negocio.md`, reglas ratificadas de V2/V3 y evidencia vigente | `docs/project/BUSINESS_RULES.md` | Original completo en `docs/archive/process/reglas-negocio.md`. |
| `docs/permisos.md` y `backend/app/core/permissions.py` | `docs/architecture/PERMISSIONS_MATRIX.md` | Original completo en `docs/archive/security/permisos.md`. |
| `LABORATORIO_HOJAS_CAMPO.md` y `IMPLEMENTACION_23_HOJAS_CAMPO_LAB.md` | `docs/archive/field-sheets/FIELD_SHEET_LAB_CONSOLIDATED.md` | Ambos originales íntegros en `sources/`. |
| Borrador parcial `PROJECT_STATUS.md` | `PROJECT_STATUS.md` + `OBSERVATIONS_REGISTER.md` | Texto exacto preservado en `PROJECT_STATUS_PARTIAL_DRAFT_2026-07-21.md`. |
| V2, V3, flujo general, bitácora y auditoría integral | Ocho canónicos de `docs/project/` | Todos los orígenes permanecen completos y clasificados. |

## Documentos reemplazados

| Documento que dejó de ser autoridad | Reemplazo autorizado |
| --- | --- |
| `docs/archive/project/BACKUP_ESTADO_ACTUAL_HISTORICO_2026-07-21.md` para avance y pendientes | `docs/project/PROJECT_STATUS.md`, `OBSERVATIONS_REGISTER.md` y `TECHNICAL_DEBT.md`; el archivo raíz sólo resume el estado operativo |
| `SISTEMA_ERP_MYC_ESPECIFICACION_V2.md` | `CURRENT_SCOPE.md`, `CURRENT_PROCESS_FLOW.md`, `BUSINESS_RULES.md` y `DECISIONS.md` |
| `SISTEMA_ERP_MYC_V3.md` | Los canónicos de `docs/project/`; sus decisiones ratificadas quedaron en `DECISIONS.md` |
| `base-datos-mvp.md` | Modelos/migraciones vigentes y el estado consolidado en `PROJECT_STATUS.md` |
| `flujo-general.md` | `CURRENT_PROCESS_FLOW.md` |
| `reglas-negocio.md` | `BUSINESS_RULES.md` |
| `permisos.md` | `architecture/PERMISSIONS_MATRIX.md` |
| Auditoría de Facturación 2026-07-14 | Auditoría integral 2026-07-21 y canon actual |
| Auditoría Toolkit 2026-07-14 para pendientes | `TECHNICAL_DEBT.md` y `OBSERVATIONS_REGISTER.md` |
| Estado de integración de Hojas de Campo 2026-07-13 | `PROJECT_STATUS.md` y `OBSERVATIONS_REGISTER.md` |
| Declaraciones de cierre aisladas | Sólo `PROJECT_STATUS.md` puede determinar `SELLADO` |

## Conflictos encontrados y resolución

### 1. “Estado actual” mezclado con cronología

`BACKUP_ESTADO_ACTUAL.md` acumulaba cortes incompatibles y declaraciones antiguas de sellado. Su contenido cronológico se preservó en `archive/project/BACKUP_ESTADO_ACTUAL_HISTORICO_2026-07-21.md`; el archivo raíz contiene ahora únicamente el corte operativo vigente. `PROJECT_STATUS.md` continúa siendo la única autoridad de avance y sólo Control Documental V1 permanece sellado.

### 2. Arquitectura “congelada” que ya no representa el sistema

V3 se titulaba arquitectura congelada pero describía una etapa con pocos módulos y estados tempranos. Se archivó como Histórico. La decisión aún válida —ETS como entidad raíz— se extrajo a `DECISIONS.md`.

### 3. Flujo V2 frente al flujo implementado

V2 y `flujo-general.md` exigían módulos autónomos de Agenda y Llamados y una secuencia lineal hasta Encuesta/Reporte final. El código actual sólo conserva fecha/hito dentro de ETS y no implementa CRM, encuesta ni reporte final. `CURRENT_PROCESS_FLOW.md` describe lo existente; `CURRENT_SCOPE.md` registra lo parcial/no iniciado.

### 4. Reglas comerciales no implementadas

`reglas-negocio.md` declaraba recordatorios de Cotización en días 2/4/6 y creación automática de Agenda al aceptar. No se verificaron en la implementación. Permanecen históricas y no fueron promovidas a regla vigente.

### 5. Regla absoluta de pago

Los textos tempranos exigían pago antes de toda liberación. El servicio vigente condiciona la compuerta a `requires_payment`; si aplica, exige factura pagada y saldo cero. `BUSINESS_RULES.md` documenta la regla ejecutable.

### 6. Folios de certificados

La regla antigua sólo contemplaba prefijos A/T. La implementación vigente también contempla V (`MYCV`) para vinculado. El canon usa los tres tipos y conserva la fuente antigua en Archivo.

### 7. Hojas de Campo: laboratorio versus operación

Los documentos del laboratorio afirmaban aislamiento y no persistencia; una verificación posterior documentó integración operativa parcial. No son mutuamente excluyentes: el laboratorio sigue siendo una superficie simulada y la operación usa otro flujo. Se fusionaron los documentos redundantes del laboratorio como Histórico y el estado operativo quedó en `PROJECT_STATUS.md`.

### 8. MDE como supuesto documento padre

`FIELD_SHEET_FIELD_REGISTRY.md` apuntaba a MDE como padre mientras MDE es Diseño futuro. Se separó el registro de campos como Arquitectura vigente y MDE quedó como consumidor futuro opcional.

### 9. Calidad como único autenticador

La decisión funcional exige Calidad como único autenticador, pero ETS todavía expone acciones duplicadas. Se mantuvo la decisión vigente y se registró la implementación contradictoria como observación/deuda P0; no se ocultó el defecto.

### 10. Facturación antigua versus integración actual

La auditoría del 2026-07-14 antecede a Facturama, XML, PDF MYC y conciliación. Se conservó como Auditoría de autoridad baja y se señaló su reemplazo por el corte integral y el canon.

### 11. Toolkit antiguo versus correcciones posteriores

La auditoría original registraba rutas absolutas y capacidades faltantes posteriormente corregidas, pero Doctor/puertos aún presentan deuda. La auditoría se conserva; sólo la deuda confirmada pasó a `TECHNICAL_DEBT.md`.

### 12. Matriz de permisos declarada versus aplicada

El documento inicial no representaba `core/permissions.py`; además, declarar un permiso no garantiza enforcement. Se creó una matriz auditada y la ausencia de deny-by-default quedó separada como deuda de seguridad.

### 13. Control Documental y Plantillas Maestras

Control Documental V1 está sellado aunque el E2E de uso del Master siga pendiente. Se resolvió el conflicto asignando ese E2E a Captura/Plantillas Maestras, no reabriendo la Lista Maestra V1.

### 14. Base de datos MVP frente al esquema actual

El diseño MVP enumeraba una fracción del esquema. Se archivó; no se declararon tablas obsoletas por ausencia de datos y el estado actual se delegó a la auditoría vigente, modelos y migraciones.

## Movimientos principales

| Origen anterior | Ubicación actual |
| --- | --- |
| `docs/PROJECT_STATUS.md` | `docs/project/PROJECT_STATUS.md` |
| `docs/FIELD_SHEET_FIELD_REGISTRY.md` | `docs/architecture/FIELD_SHEET_FIELD_REGISTRY.md` |
| `docs/MDE_SPEC.md` | `docs/architecture/future/MDE_SPEC.md` |
| `docs/CATALOGOS_SAT.md` | `docs/architecture/CATALOGOS_SAT.md` |
| `docs/PLANTILLAS_MAESTRAS.md` | `docs/modules/control-documental/PLANTILLAS_MAESTRAS.md` |
| Auditorías en raíz/`archive/` | `docs/audits/` |
| Cierres de Clientes/Hojas/SAT | `docs/closures/` |
| V2, V3 y base MVP | `docs/archive/architecture/` |
| Flujo y reglas anteriores | `docs/archive/process/` |
| Análisis/laboratorio de Hojas | `docs/archive/field-sheets/` |
| Permisos iniciales | `docs/archive/security/permisos.md` |

## Nueva jerarquía documental

```text
docs/
├── BACKUP_ESTADO_ACTUAL.md
├── PROJECT_FILE_REGISTRY.md
├── project/
│   ├── DOCUMENTATION_INDEX.md
│   ├── PROJECT_STATUS.md
│   ├── CURRENT_SCOPE.md
│   ├── CURRENT_PROCESS_FLOW.md
│   ├── BUSINESS_RULES.md
│   ├── DECISIONS.md
│   ├── OBSERVATIONS_REGISTER.md
│   └── TECHNICAL_DEBT.md
├── architecture/
│   ├── CATALOGOS_SAT.md
│   ├── FIELD_SHEET_FIELD_REGISTRY.md
│   ├── PERMISSIONS_MATRIX.md
│   └── future/
│       └── MDE_SPEC.md
├── modules/
│   └── control-documental/
│       └── PLANTILLAS_MAESTRAS.md
├── audits/
│   ├── AUDITORIA_INTEGRAL_AVANCE_ERP_MYC_2026-07-21.md
│   ├── AUDITORIA_PAQUETE_CAPTURA_2026-07-17.md
│   ├── AUDITORIA_TECNICA_FACTURACION_CFDI_4_0.md
│   ├── INTEGRACION_OPERATIVA_HOJAS_CAMPO_ESTADO.md
│   └── MYC_TOOLKIT_AUDIT.md
├── closures/
│   ├── CLIENT_DELETION_CLOSURE.md
│   ├── IMPLEMENTACION_MOTOR_HOJAS_CAMPO_FASE_1.md
│   ├── REPORTE_CARGA_INICIAL_CATALOGOS_SAT.md
│   └── DOCUMENT_REORGANIZATION_REPORT_2026-07-21.md
└── archive/
    ├── project/
    │   └── BACKUP_ESTADO_ACTUAL_HISTORICO_2026-07-21.md
    ├── architecture/
    │   ├── SISTEMA_ERP_MYC_ESPECIFICACION_V2.md
    │   ├── SISTEMA_ERP_MYC_V3.md
    │   └── base-datos-mvp.md
    ├── field-sheets/
    │   ├── ANALISIS_HOJAS_CAMPO_ORIGINALES.md
    │   ├── FIELD_SHEET_LAB_CONSOLIDATED.md
    │   └── sources/
    │       ├── IMPLEMENTACION_23_HOJAS_CAMPO_LAB.md
    │       ├── LABORATORIO_HOJAS_CAMPO.md
    │       └── PROJECT_STATUS_PARTIAL_DRAFT_2026-07-21.md
    ├── process/
    │   ├── flujo-general.md
    │   └── reglas-negocio.md
    └── security/
        └── permisos.md
```

Los `.DS_Store` locales no forman parte de la documentación ni del inventario funcional y se excluyen del árbol.

## Confirmación del índice único

`docs/project/DOCUMENTATION_INDEX.md` quedó como referencia principal obligatoria. Define prioridad, conflicto, documentos normativos, arquitectura vigente, cierres, auditorías, futuro, histórico, fusiones y reemplazos. Toda consulta futura debe comenzar allí.
