# Hotfix post-PR #4: LAB EXTERNO y folios propios

Fecha: 2026-09-17. Rama: `hotfix/lab-external-ios-crash-and-admin-self-resolve`.
Base verificada: `1083e3ef9863f721882592c7cc68335264d6843b` (main limpio).
Entrega inicial sin merge; los tres commits hasta `4fe5ca3` ya fueron publicados en origin. Cierre técnico acotado; no sella MYC Mobile/LAB.

## Causa y corrección

El test ejecuta el componente real y su manejador Abrir hoja con puertos
React Native/Expo simulados. En la base, linked/289 de OT 6471 con
`template_key=lab_externo`, `template_definition.groups` y sin result_sections
lanza `TypeError: Cannot read properties of undefined (reading 'map')` desde
computeOverallProgress. El cálculo ocurría antes del branch externo.

Ahora LabTechnicalCapture distingue el contrato antes de evaluar helpers de
plantilla interna. LAB EXTERNO reutiliza el formulario canónico completo,
acciones, estados, revisión, guardado, completitud, reapertura y PDF.
LabExternalFieldSheet sólo administra resultados dinámicos y comunica dirty,
readOnly y la hoja persistida. La creación linked muestra carga sin selector interno, y descartar su borrador
vuelve a equipos para recreación automática al abrir. Los guardados de estructura/valores se ordenan
para evitar pérdida de captura; la generación de tablas usa ids únicos entre
grupos. El progreso mantiene la semántica de filas con valores declarados.

La reproducción demuestra el defecto JavaScript y su corrección. No prueba por
sí sola que ese TypeError explique todos los SIGABRT del build 22: no se
inspeccionaron los .ips originales ni se ejecutó una nueva build en iPhone.

## PDF

_render_lab_externo_html prepara exclusivamente grupos/tablas/valores y delega
en _render_html con la definición general oficial. El HTML externo ahora es
un parcial del engine canónico. Comparte todos los campos comunes, tipografía,
firmas y pie; no usa logo y muestra `HOJA DE CAMPO "LAB EXTERNO"`.
Las tablas largas usan flujo paginable fuera del contenedor CSS grid, que
recortaba filas en WeasyPrint. Se comprobaron 100 filas y encabezados repetidos
en tres páginas, además de igualdad semántica de todas las celdas comunes.
Los PDFs finales ya congelados siguen entregándose sin regeneración.

## Autoridad y UX

Una sola función backend exige actor interno, rol Administrador activo y
permiso lab_folios.resolve. Sólo linked_folio/manual_myc_folio pending admiten
resolver por su solicitante; reaperturas, cierres y demás tickets mantienen
TICKET_SELF_APPROVAL_FORBIDDEN. Revisión, fechas, comentario, snapshot,
auditoría, notificación y segundo revisor conservan su flujo.

Mobile no recibía roles internos en su contrato de autenticación. Login,
refresh y me ahora exponen can_resolve_own_lab_folios derivado del backend;
Mobile usa esa capability, permiso, solicitante, estado y tipo. Ausencia de
capability deniega la acción propia; el backend vuelve a comprobar autoridad.

## Validaciones

- Base 1083e3e: test de apertura falla por undefined.map; misma prueba pasa con el hotfix.
- `npx tsc --noEmit`: pasa.
- `npm run lint`: pasa.
- `npm test`: 669 passed.
- `npm run test:wiring`: 92 passed.
- Backend focalizado LAB EXTERNO, tickets propios, contexto Mobile, folios,
  engine general y DSL: 158 passed, 1 skipped.
- Suite backend completa (`pytest tests -q`, desde backend, startup aislado):
  1235 passed, 16 skipped, 19 subtests passed; 34 warnings preexistentes de
  deprecación/SQLAlchemy. La repetición completa pasó sin alterar Mantenimiento.
- PDF: comparación semántica y revisión visual de general y las tres páginas
  externas con datos sintéticos; sin cortes de filas ni logos externos.
- Head Alembic: 6640c526c412. Sin migración ni modificación de la base ERP.
- Inventario regenerado, rutas revisadas y git diff --check.

La ejecución inicial desde la raíz y con sandbox tuvo errores de startup/DB,
LibreOffice y una ruta relativa de prueba. La ejecución correcta parte de
backend, permite LibreOffice y configura una base SQLite temporal sólo para
startup; el resto conserva sus fixtures. No usa la base local ERP.
Una corrida completa detectó el test intermitente preexistente de Mantenimiento:
la aserción busca `80` en todo el HTML y coincide con el timestamp. No se alteró
ese test para ocultar el fallo.

Tests antiguos actualizados exclusivamente por contrato reemplazado: wiring de
la pantalla externa independiente y prohibición absoluta de resolución propia
para el administrador. Se mantiene regresión para tickets sensibles y se añaden
los casos positivos/negativos de folios con roles y permisos reales.

## Pendientes y documentos revisados

QA físico iPhone/TestFlight y pruebas de concurrencia PostgreSQL opt-in siguen
pendientes. El test intermitente de Mantenimiento se registra como deuda previa.
No se añaden migraciones, motores de negocio ni estados paralelos.

PROJECT_STATUS y OBSERVATIONS_REGISTER se revisaron sin cambios: LAB permanece
EN DESARROLLO; la evidencia de resolución vive aquí y la deuda de validación en
TECHNICAL_DEBT. DOCUMENTATION_INDEX registra este cierre; alcance, flujo,
reglas, decisiones y contratos afectados se sincronizan en el mismo trabajo.
BACKUP_ESTADO_ACTUAL se consolida a un corte verificable; los cortes anteriores
permanecen en Git. Se crean este cierre y dos tests; no se mueven ni archivan archivos.

## Archivos modificados

- `backend/app/core/mobile/security.py`
- `backend/app/routers/mobile_auth.py`
- `backend/app/schemas/mobile_auth.py`
- `backend/app/services/auth.py`
- `backend/app/services/field_sheet_pdfs.py`
- `backend/app/services/operational_tickets.py`
- `backend/app/templates/field_sheet_engine_pdf.html`
- `backend/app/templates/field_sheet_lab_externo_pdf.html`
- `backend/tests/test_lab_field_sheets_capture.py`
- `backend/tests/test_lab_field_sheets_external.py`
- `backend/tests/test_mobile_security_context.py`
- `backend/tests/test_operational_ticket_self_resolution.py`
- `docs/BACKUP_ESTADO_ACTUAL.md`
- `docs/PROJECT_FILE_REGISTRY.md`
- `docs/architecture/FIELD_SHEET_PDF_RENDERER.md`
- `docs/architecture/LAB_WORK_ORDERS.md`
- `docs/architecture/MOBILE_SECURITY_CONTEXT.md`
- `docs/architecture/OPERATIONAL_TICKETS_AND_LAB_REOPENING.md`
- `docs/closures/LAB_EXTERNAL_POST_PR4_HOTFIX_2026-09-17.md`
- `docs/project/BUSINESS_RULES.md`
- `docs/project/CURRENT_PROCESS_FLOW.md`
- `docs/project/CURRENT_SCOPE.md`
- `docs/project/DECISIONS.md`
- `docs/project/DOCUMENTATION_INDEX.md`
- `docs/project/TECHNICAL_DEBT.md`
- `myc-mobile/app/(technician)/tickets.tsx`
- `myc-mobile/src/components/lab/LabExternalFieldSheet.tsx`
- `myc-mobile/src/components/lab/LabExternalFieldSheet.wiring.test.ts`
- `myc-mobile/src/components/lab/LabTechnicalCapture.render.test.ts`
- `myc-mobile/src/components/lab/LabTechnicalCapture.tsx`
- `myc-mobile/src/permissions/mobile-capabilities.test.ts`
- `myc-mobile/src/permissions/mobile-capabilities.ts`
- `myc-mobile/src/services/lab-field-sheet-external.test.ts`
- `myc-mobile/src/services/lab-field-sheet-external.ts`
- `myc-mobile/src/types/auth.ts`
- `scripts/generate_project_file_registry.py`


## Corrección de auditoría final sobre 4fe5ca3

La primera regresión sólo comprobaba secciones y apertura: no detectó que
canonicalFieldsForDefinition(undefined) devolvía cero campos. La auditoría
identificó ese bloqueo. LabTechnicalCapture ahora selecciona explícitamente
CANONICAL_FIELDS para LAB EXTERNO, sin copiar arrays ni cambiar el filtro de
plantillas internas. Se conservan los 24 campos realmente canónicos, incluidos
condición general/desviaciones y observaciones; initial_condition/final_condition
siguen clasificados como legacy especializados por la autoridad existente.

El test de render ampliado falla antes de la corrección y pasa después:
comprueba título, campos representativos y todos los descriptores canónicos,
edición con permiso, readonly sin permiso y de snapshots, actualización de un
valor ambiental, renderer externo y cero llamadas a computeOverallProgress.
Validación de esta corrección: tsc sin errores, lint sin errores, npm test
671/671, wiring 92/92 y git diff --check limpio. Backend y PDF no se modifican;
no se requiere repetir sus suites. Se conserva pendiente el QA físico.

Documentos revisados sin cambios adicionales: DOCUMENTATION_INDEX,
PROJECT_STATUS, CURRENT_SCOPE, CURRENT_PROCESS_FLOW, BUSINESS_RULES, DECISIONS,
OBSERVATIONS_REGISTER y TECHNICAL_DEBT: esta corrección cumple el contrato ya
aprobado y no cambia alcance, reglas ni estado del módulo. Se actualizan este
cierre, LAB_WORK_ORDERS, BACKUP_ESTADO_ACTUAL y el inventario. No se crean,
mueven, fusionan ni archivan archivos. Se añade un único commit; no se
reescriben los tres anteriores ni se mergea.
