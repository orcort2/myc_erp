> Estado: VIGENTE
>
> Tipo: Snapshot operativo verificable
>
> Autoridad: Media; no define alcance, flujo, reglas, decisiones ni estado de módulos
>
> Corte actualizado: 2026-09-02

# Estado operativo actual del ERP MYC

Este archivo conserva únicamente el corte técnico necesario para reanudar el
trabajo. El estado funcional se consulta en
[`project/PROJECT_STATUS.md`](project/PROJECT_STATUS.md), el alcance en
[`project/CURRENT_SCOPE.md`](project/CURRENT_SCOPE.md), el flujo en
[`project/CURRENT_PROCESS_FLOW.md`](project/CURRENT_PROCESS_FLOW.md) y los
pendientes en [`project/OBSERVATIONS_REGISTER.md`](project/OBSERVATIONS_REGISTER.md)
y [`project/TECHNICAL_DEBT.md`](project/TECHNICAL_DEBT.md).

## Corte operativo

- Rama verificada: `wip/lab-field-sheets-integration`.
- Baseline recibido: `22f75e40d14ade3ae19ccf43d2cb74bbae7de502`.
- Dictamen global vigente: **NO APTO PARA PRODUCCIÓN**.
- Único módulo `SELLADO`: Control Documental V1 dentro de su alcance
  congelado. OT LAB temporal permanece `EN DESARROLLO` hasta QA físico.
- Fase 3 LAB implementa recepción técnico+cliente previa a FieldSheets:
  `draft → received_signed → in_progress → ready_to_close → completed`.
  `ready_for_signatures` queda sólo como compatibilidad histórica.

## Persistencia y migraciones

- Persistencia principal: PostgreSQL, SQLAlchemy y Alembic.
- Head único del código verificado: `d7c297902425` (declara
  `down_revision = b71d4a9f2c18`; añade el modelo de revisión/scope de
  equipo LAB de Fase 6 -- ver sección de Fase 6 más abajo).
- La revisión previa `b71d4a9f2c18` declara `down_revision = a3983f9a6ca9` y
  agrega a `field_sheets` renderer/versión, referencia y SHA-256 del PDF
  final, versión de definición congelada y fecha de generación.
- La migración clasifica renderers históricos por su `pdf_template` sin
  reescribir `template_definition_json` ni `template_key`.
- No se aplicó Alembic ni se ejecutaron cambios sobre la base real del usuario;
  por ello no corresponde regenerar `backup_erp_myc_antes_prueba.sql` en este
  trabajo.

## Estado verificable Fase 3 LAB

- La sesión se crea sólo con firma técnico y cliente válidas. La primera firma
  existe únicamente en memoria Mobile hasta el POST final.
- Recepción valida equipos, servicio, MYCA/MYCT, empresa vinculada y cliente
  documental antes de cambiar la cohorte a `received_signed`.
- La recepción firmada congela datos generales, cliente receptor, equipos,
  cliente documental, servicio, empresa vinculada y folios mediante backend.
- Crear la primera FieldSheet cambia a `in_progress`; completar la última
  requerida cambia a `ready_to_close`; el cierre genera `completed` sin otra
  firma.
- Cada FieldSheet conserva la sesión exacta vigente al crearla. Reapertura
  `preserve`/`invalidate` no reescribe firmas ni hojas históricas.
- Una reapertura con firma preservada válida muestra `Continuar proceso` y pasa
  de equipos a captura técnica; `openExisting`, `selectRelated` y realtime no
  tratan su cohorte histórica como firma activa. Si backend vuelve a exigir
  firma, el flujo normal se restablece desde el objeto actualizado, sin flags
  locales nuevos.
- Captura usa `lab_field_sheets.capture` para leer y operar FieldSheets, sin
  capacidades administrativas. El scope externo y su excepción histórica de
  cierre se conservan.
- Mobile presenta revisión de recepción, resumen completo, read-only posterior,
  estados nuevos, cierre sin loop de firmas y contexto de encabezado correcto.
- Después de crear/completar FieldSheet o solicitar folio, Mobile recupera la
  OT desde backend mediante un único helper. La recepción muestra cada OT y sus
  equipos bajo `RECEPCIÓN DE EQUIPOS`; acreditado/trazable presentan el folio
  sistémico en modo informativo y Vinculado conserva su flujo.
- Nuevas FieldSheets fijan `field_sheet_engine` v1. Al completar, el backend
  publica una vez el PDF en storage institucional y persiste SHA-256 y
  procedencia; descargas posteriores verifican y reutilizan el mismo archivo.

## Estado verificable Fase 6 LAB (Hojas de Campo — cierre de validación)

Detalle completo en
[`docs/closures/LAB_FIELD_SHEETS_PHASE_6_2026-09-01.md`](closures/LAB_FIELD_SHEETS_PHASE_6_2026-09-01.md).
Resumen operativo:

- `GET /api/mobile/v1/technician/lab-field-sheets` (bandeja LAB) está
  gateado por `require_internal_mobile_permission("field_sheets.read")`:
  ningún actor `client`/portal externo lo alcanza (403 antes de resolver
  scope). Para staff interno autorizado, `operator_client_id=None` es scope
  interno global deliberado — el mismo resolver que ya usan
  `create_lab_work_order`/`list_lab_work_orders`; no existe (ni se agregó) un
  concepto de "hoja de campo asignada a un técnico" en el modelo LAB.
- El catálogo metrológico no se tocó: 30 claves operativas backend
  (`TEMPLATE_BLOCK_ASSIGNMENTS`), 11 claves prototipo permanecen explícitamente
  `unsupported` (422, sin fallback a `general`). Esa exclusión es una decisión
  deliberada pendiente de trabajo metrológico humano, no un bug resuelto ni
  pendiente de este cierre.
- El modelo de revisión (current/histórico, duplicado `is_current` rechazado
  por DB, `reopen preserve`/`reopen invalidate → N+1`, PDF histórico intacto)
  y "Guardar y salir" (éxito cierra, fallo permanece abierto con valores
  dirty, reintento exitoso) no cambiaron de arquitectura en este cierre; sólo
  se revalidaron con la suite existente.
- `frontend/**` permanece sin tocar desde `92e5ffb`
  (`git diff 92e5ffb --name-only -- frontend/` vacío).

## Validaciones

### Navegación de reapertura con firma preservada — 2026-09-02

- `npx tsc --noEmit`: correcto, exit code 0.
- `npx tsx --test`: `277 passed, 0 failed`; las 2 expectativas obsoletas de
  `FieldSheetResultsWorkspace.wiring.test.ts` se alinearon con el contrato
  vigente de teclado/insets nativos, `inputRefs`/`focusNext` y ausencia de
  `scrollCellIntoView`, `measureLayout` y `findNodeHandle`. El componente
  `FieldSheetResultsWorkspace.tsx` permaneció intacto.
- `npx expo lint`: exit code 0, 0 errores y 8 warnings (6 imports sin uso en
  `work-orders.tsx` y 2 de hooks en `FieldSheetResultsWorkspace.tsx`), todos
  fuera del cambio funcional aplicado.
- No se modificaron backend, contratos API, esquema ni base local; no
  corresponde regenerar `backup_erp_myc_antes_prueba.sql`.

### Corrección LabClient 2026-09-02

- Importador XLSX compatible con contrato histórico y estructurado, aliases de
  encabezados, auxiliares ignorados y código postal como string.
- `GET /api/mobile/v1/technician/lab-clients` aplica búsqueda, scope,
  activos/inactivos, `limit` y `offset` en SQL; conserva respuesta array.
- Backend focal: `6 passed` (importador), `10 passed` (dominio/listado,
  incluidos búsqueda, paginación, inactivos y permisos) y `1 passed` (scope
  multi-tenant).
- Mobile focal: `17 passed`; suite completa bajo `myc-mobile/src`: `273 passed`.
- TypeScript `npx tsc --noEmit`: correcto. Lint: 0 errores y 6 warnings
  preexistentes en `work-orders.tsx`, fuera del alcance LabClient.
- `git diff --check`: correcto; el generador del registro se ejecutó y las
  filas LabClient afectadas apuntan a rutas existentes.
- No se modificó la base local ni el esquema; no corresponde regenerar el
  respaldo SQL. Los índices existentes cubren `operator_client_id` y
  `company`; no se añadió una migración para el catálogo actual (~1,000 filas).

- Backend focal FieldSheet/LAB + seguridad Mobile (10 archivos): `256 passed,
  8 skipped`.
- Backend suite completa: `852 passed, 8 skipped, 2 failed`. Las 2 fallas
  (`test_api_access_conformity.py`) son deuda preexistente de inventario de
  endpoints (~500 rutas del ERP completo vs. csv committed), confirmada
  idéntica en el baseline `92e5ffb` vía `git stash` — no la introdujo ni la
  agranda este cierre; queda como pendiente separado (ver más abajo).
- Mobile suite completa (23 archivos `*.test.ts` bajo `myc-mobile/src`):
  `207 passed, 0 failed`.
- TypeScript `npx tsc --noEmit`: correcto.
- Lint `npm run lint`: correcto.
- Expo export iOS `npx expo export --platform ios`: correcto.
- Expo export Android `npx expo export --platform android`: correcto.
- Expo export web `npx expo export --platform web`: correcto, 36 rutas.
- `git diff --check`: sin errores de espacio en blanco.
- Alembic sobre base desechable desde cero: `upgrade head` correcto,
  `current = d7c297902425 (head)` y `check = No new upgrade operations
  detected`; ciclo `downgrade b71d4a9f2c18 → upgrade head` correcto.
- La base desechable fue eliminada; la base ERP local real no fue modificada.

## Pendientes operativos

- QA físico Android/iPhone/TestFlight del recorrido completo de recepción,
  doble firma, orientación/teclado/scroll, FieldSheets, cierre, PDF,
  refresh/realtime y errores.
- Resolver por un trabajo separado la deuda del inventario API: el csv
  committed (`docs/architecture/security/API_ENDPOINT_INVENTORY_2026-08-03.csv`,
  477 operaciones) quedó desactualizado contra el runtime actual (500
  operaciones al corte de este documento); produce 2 fallas en
  `tests/test_api_access_conformity.py` no relacionadas con FieldSheets/LAB
  (confirmado preexistente en `92e5ffb` antes del cierre de validación de
  Fase 6, ver
  [`docs/closures/LAB_FIELD_SHEETS_PHASE_6_2026-09-01.md`](closures/LAB_FIELD_SHEETS_PHASE_6_2026-09-01.md)).
- Mantener fuera de esta fase los hallazgos separados de FieldSheets
  (contenido, tabla Valve, overflow, columnas, imprimibles y plantillas),
  NIIMBOT, cambios MYCA/MYCT/rangos, LabClient y Fase 2 sin regresión.

## Regla de mantenimiento

Después de cualquier cambio funcional, esquema, configuración, prueba o
recurso, este snapshot y `PROJECT_FILE_REGISTRY.md` deben sincronizarse en el
mismo trabajo. Si una futura tarea modifica la base local, debe regenerar el
respaldo oficial y comprobar su `alembic_version` contra el head único.
