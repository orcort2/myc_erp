> Estado: VIGENTE — conflicto abierto, no resuelto
>
> Corte verificado: 2026-09-01
>
> Autoridad: inventario real de claves de plantilla de Hojas de Campo (Fase 6)
>
> Relación: `docs/archive/field-sheets/FIELD_SHEET_LAB_CONSOLIDATED.md`
> (histórico, origen del catálogo de 23) y `FIELD_SHEET_PDF_RENDERER.md`
> (autoridad documental vigente)

# Inventario de plantillas de Hojas de Campo — Fase 6

Fase 6 pidió construir la matriz exacta del catálogo real (no asumir "23
plantillas") y consolidar hacia una única autoridad backend. La matriz reveló
un conflicto objetivo que esta fase **no resuelve** -- ver "Conflicto
detectado" abajo. No se fuerza ninguna plantilla a una familia incorrecta ni
se inventa contenido para cerrarlo artificialmente.

## Tres universos de claves, no dos

1. **Conjunto operativo legacy (30 claves)** --
   `backend/app/services/field_sheet_templates.py::TEMPLATE_BLOCK_ASSIGNMENTS`
   y su espejo exacto `frontend/src/constants/fieldSheetTemplates.js`. Es lo
   que el API/PDF engine/captura realmente ejecutan hoy vía
   `build_fallback_template_definition`.
2. **Conjunto canónico nuevo (23 claves)** --
   `backend/app/schemas/field_sheet.py::FieldSheetTemplateKey` (bloque no
   histórico) y su espejo `frontend/src/constants/officialFieldSheetTemplates.js`,
   usando tipos de bloque que **no existen en el backend**
   (`ReplicatedComparisonTableBlock`, `DirectionalCycleTableBlock`,
   `BeforeAfterTableBlock`, `CompositeTestTableBlock`,
   `PairedChannelMatrixTableBlock`, `ThresholdEventTableBlock`,
   `VerificationComplianceTableBlock`, `CupSpecializedTableBlock`,
   `ControlledDiagramBlock`).
3. **Pilotos oficiales del motor (4 claves)** --
   `backend/app/services/field_sheet_template_engine.py::OFFICIAL_PILOT_TEMPLATES`
   (`anemometro`, `calibradores`, `presion`, `bascula`): las únicas claves
   formalizadas end-to-end en el motor oficial, pero construidas con los
   tipos de bloque **antiguos** (`SimpleComparisonTableBlock`,
   `SectionedTableBlock`, `PressureTableBlock`, `MassBalanceTableBlock`), no
   los nuevos del punto 2.

`officialFieldSheetTemplates.js` **no es código muerto**: `frontend/src/utils/fieldSheets.js::buildFallbackTemplate()`
lo consulta con prioridad sobre el archivo legacy
(`officialFieldSheetTemplates[key] ?? fieldSheetTemplates[key] ?? ...`).

## Origen del conjunto de 23

`docs/archive/field-sheets/FIELD_SHEET_LAB_CONSOLIDATED.md` (histórico, baja
autoridad) documenta que las 23 plantillas fueron un **prototipo aislado**
(`/dashboard/field-sheet-lab`, `/dashboard/field-sheet-preview`), con datos
simulados, sin persistencia ni conexión a backend/base de datos. El esquema
(`FieldSheetTemplateKey`) y `officialFieldSheetTemplates.js` se extrajeron de
ese prototipo hacia el código real sin que el motor backend
(`field_sheet_template_engine.py`) se completara para las 19 claves
restantes -- sólo 4 llegaron a formalizarse, y con los tipos de bloque
antiguos, no los del prototipo.

## Conjunto real de plantillas canónicas activas (lo que funciona hoy)

Las **30 claves del conjunto legacy** son las plantillas canónicas activas
reales: alcanzables por el API, con motor de renderizado PDF funcional
(`field_sheet_engine_pdf.html`), consumidas igual desde ERP y desde Mobile
LAB. De esas 30, **4** (`anemometro`, `calibradores`, `presion`, `bascula`)
tienen además una formalización explícita en `field_sheet_template_engine.py`
(pilotos oficiales); las 26 restantes se sirven vía
`build_fallback_template_definition`/`TEMPLATE_BLOCK_ASSIGNMENTS` sin pasar
por el motor oficial, pero **sí son reales y reachable**, no vestigiales.

## Conflicto detectado (reportado, no resuelto)

### A. 11 claves canónicas nuevas sin ninguna implementación backend

`angulimetro`, `detector_gases`, `maestro_altura`, `par_torsional`, `pesas`,
`reglas`, `tld_6_canales`, `tld`, `valvula_seguridad`,
`verificacion_equipos`, `copa` están en `FieldSheetTemplateKey` y en
`officialFieldSheetTemplates.js`, pero **no existen en
`TEMPLATE_BLOCK_ASSIGNMENTS`** ni en ningún piloto del motor. Una llamada
real al API con cualquiera de estas claves devuelve `422 Plantilla de hoja de
campo no soportada`. Resolverlas exige autorar contenido real (campos,
secciones, columnas, validaciones) para cada una -- una decisión de dominio/
metrología que esta fase no puede tomar unilateralmente sin referencia
autorizada, y que además tocaría probablemente varios de los tipos de bloque
"nuevos" que hoy no tiene ningún renderer PDF backend.

### B. 6 claves con dos cuerpos incompatibles bajo la misma clave

`temperatura`, `tacometro`, `dimensional`, `sonido`, `electrica`,
`cronometro` existen simultáneamente en el archivo legacy (cuerpo real, en
producción) **y** en `officialFieldSheetTemplates.js` (cuerpo distinto, con
los tipos de bloque nuevos). Cuál cuerpo gana depende de qué código lo
consuma: el API/PDF siempre usan el legacy; el fallback del frontend
(`buildFallbackTemplate`) prioriza el nuevo si algún flujo cliente llega a
depender de él sin snapshot backend completo. Fusionar ambos cuerpos exige
decidir cuál es la verdad documental para cada instrumento -- tampoco se
decide aquí.

### C. Alias/duplicados menores (ya corregidos, ver más abajo) y no resueltos

- `regla` (legacy) vs `reglas` (nuevo, sin backend) -- posible mismo concepto,
  nunca vinculados por alias.
- `peso_patron` (legacy) vs `pesas` (nuevo, sin backend) -- ídem.
- `torquimetro` (legacy) vs `par_torsional` (nuevo, sin backend) -- ídem.
- `flujo`: el backend lo alía a `volumen`
  (`TEMPLATE_ALIASES["flujo"] = "volumen"`), pero el fallback legacy del
  frontend no tiene entrada `flujo` en `templateAssignments` y cae a
  `general`; `officialFieldSheetTemplates.js` trae un tercer cuerpo bajo
  `flujo`. Tres resoluciones distintas para la misma clave según el código
  que la procese.

Ninguno de estos se fusionó/renombró en Fase 6: hacerlo sin una decisión de
producto sobre cuál cuerpo es la verdad documental habría sido "forzar una
plantilla a una familia incorrecta para que pase", explícitamente prohibido
por el encargo de esta fase.

## Correcciones seguras aplicadas (sin decisión de contenido)

- `FIELD_SHEET_TEMPLATE_KEYS` (tupla muerta, sin ninguna referencia en el
  resto del backend) tenía `"general"` duplicado -- eliminado.
- `TEMPLATE_ALIASES["luxometro"] = "luxometro"` era un alias-identidad inerte
  (`_resolve_template_key` ya usa la propia clave como default cuando no hay
  alias) -- eliminado, cero cambio de comportamiento.

## Familias oficiales del motor (`field_sheet_template_engine.py`)

| Familia | Claves reales que la usan hoy |
|---|---|
| `replicated_comparison` | `calibradores`, `anemometro` |
| `direction_cycle` | `presion` |
| `mass_balance_composite` | `bascula` |
| `before_after`, `paired_multichannel`, `threshold_event`, `verification_compliance`, `cup_specialized` | Ninguna -- declaradas en el motor, sin piloto backend que las use (sólo asignadas especulativamente a claves del conjunto B en `officialFieldSheetTemplates.js`) |

## Familias legacy (`TABLE_FAMILY_DEFINITIONS`/`TEMPLATE_TABLE_FAMILY`)

| Familia | Claves |
|---|---|
| `direct_comparison` | `general`, `temperatura`, `termometro`, `termohigrometro`, `cronometro`, `tacometro` |
| `multipoint` | `anemometro`, `luxometro`, `sonido`, `sonometro`, `torquimetro`, `dinamometro`, `durometro`, `volumen` |
| `pressure` | `manometro`, `transductor_presion`, `valvula` |
| `dimensional` | `dimensional`, `regla`, `vernier`, `micrometro`, `flexometro` |
| `mass` | `masa`, `balanza`, `bascula`, `peso_patron` |
| `electrical` | `electrica`, `multimetro` |
| `custom` | Fallback por defecto para cualquier clave sin entrada explícita |

No se eliminó ni se remapeó ninguna familia legacy/genérica; conviven con las
oficiales exactamente como ya lo hacían.

## Qué implica esto para Mobile (Fase 6)

El rediseño de captura Mobile (`LabTechnicalCapture`, `FieldSheetResultsWorkspace`)
renderiza genéricamente a partir de `template_definition.blocks`/
`result_sections`, sin saber qué instrumento es. Funciona igual para las 30
claves reales sin depender de qué lado del conflicto se resuelva --
el conflicto es exclusivamente de contenido/autoría de plantilla, no de
arquitectura de renderizado.
