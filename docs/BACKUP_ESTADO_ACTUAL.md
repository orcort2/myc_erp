> Estado: VIGENTE
>
> Tipo: Snapshot operativo verificable
>
> Autoridad: Media; no define alcance, flujo, reglas, decisiones ni estado de módulos
>
> Corte actualizado: 2026-09-04

# Estado operativo actual del ERP MYC

Este archivo conserva únicamente el corte técnico necesario para reanudar el
trabajo. El estado funcional se consulta en
[`project/PROJECT_STATUS.md`](project/PROJECT_STATUS.md), el alcance en
[`project/CURRENT_SCOPE.md`](project/CURRENT_SCOPE.md), el flujo en
[`project/CURRENT_PROCESS_FLOW.md`](project/CURRENT_PROCESS_FLOW.md) y los
pendientes en [`project/OBSERVATIONS_REGISTER.md`](project/OBSERVATIONS_REGISTER.md)
y [`project/TECHNICAL_DEBT.md`](project/TECHNICAL_DEBT.md).

## Corte operativo

- Rama verificada: `wip/lab-admin-void-delivery`.
- Working tree previo a este cierre: `213dcb042db143df39713f6419de0b6bcfe7a55c`
  (padre `c7a7adb3ae13c4687f84a208a1db69969547602a`).
- Dictamen global vigente: **NO APTO PARA PRODUCCIÓN**. El push de este cierre
  no es aprobación de merge a `main`; queda pendiente una auditoría
  independiente del SHA resultante.
- Único módulo `SELLADO`: Control Documental V1 dentro de su alcance
  congelado. OT LAB temporal permanece `EN DESARROLLO` hasta QA físico.
- Fase 3 LAB implementa recepción técnico+cliente previa a FieldSheets:
  `draft → received_signed → in_progress → ready_to_close → completed`.
  `ready_for_signatures` queda sólo como compatibilidad histórica.

## Persistencia y migraciones

- Persistencia principal: PostgreSQL, SQLAlchemy y Alembic.
- Head único del código y base local verificado: `7088fa142cc2`
  (`soft-delete LabWorkOrderEquipment (tombstone), partial unique position`),
  con `down_revision = c91f47a8b2d0`.
- La migración agrega `is_active`/`deleted_at`/`deleted_by` (SoftDeleteMixin) a
  `lab_work_order_equipment`, reemplaza `uq_lab_equipment_position` por el
  índice único parcial `uq_lab_equipment_position_active`
  (`WHERE is_active IS TRUE`) y no reescribe ni borra datos: las 14 filas
  existentes en la base local recibieron `is_active=true`.
- El downgrade se niega explícitamente (`RuntimeError`) si existen filas
  tombstone o duplicados de `(work_order_id, position)` que el
  `UniqueConstraint` histórico no admitiría; sin ese conflicto restaura el
  constraint pleno anterior.
- Ciclo `upgrade head → downgrade -1 → upgrade head` verificado contra
  PostgreSQL real (`erp_myc`); `alembic heads`/`current` confirman
  `7088fa142cc2 (head)` único y `alembic check` reporta
  `No new upgrade operations detected`.
- No se regeneró `backup_erp_myc_antes_prueba.sql` en este cierre: la base
  local usada es de desarrollo, no el respaldo oficial de producción.

## Cierre operativo y UX OT LAB — 2026-09-03

- Vinculado con folio se autoriza directamente sólo mediante
  `lab_folios.resolve`; sin esa autoridad conserva Ticket pending y
  `requested_folio`. No se consumen secuencias MYCA/MYCT y una edición
  autorizada resuelve, sin borrar, el Ticket previo.
- La entrega Push sigue usando sonido `default` y canal `operational`; no hay
  notificación self de creación y el requester sí recibe la resolución.
- FieldSheet current `draft`/`in_progress` admite descarte. La primera captura
  puede restaurar `received_signed`; una recaptura restaura la revisión
  completed predecesora. Completed/histórica bloquea descarte y hard delete de
  OT; una OT con sólo borradores reutiliza el descarte y puede eliminarse.
- `LabWorkOrder.reception_date` es autoridad. Sólo staff con
  `work_orders.create` o `lab_work_orders.use` la modifica; se sincronizan sólo
  hojas current editables. `reception_date_change` es informativo y resolverlo
  no aplica la fecha.
- Mobile presenta errores 422 por campo, calendario civil reutilizable,
  shortcuts `+6 meses`/`+1 año` con clamp, selector de todas las hojas en un
  viewport de cinco y botones transaccionales con primitives canónicos.
- Fase 6A.1 permanece **EN REVISIÓN**; no se agregaron plantillas ni se tocó el
  renderer PDF.

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

## Estado verificable DSL de Hojas de Campo — Fases 4 y 5

- `ResultSection` expone headers multinivel, spans, row labels, alineación,
  widths y controles de corte/repetición; la normalización valida una matriz
  completa contra columnas reales y `__row_number__`, incluyendo la posición
  física lógica de cada `column_key`; una clave válida mal ubicada responde 422.
- `print_layout` controla página, márgenes, visibilidad documental, grid,
  spans, orden, títulos, compacidad, bordes, espacios y page breaks mediante
  enums/números seguros. Campos admiten span y label `top|inline`.
- Perfiles allowlisted `myc` y `capymet` alimentan el mismo renderer. MYC usa
  identidad, contacto y logo institucional. CAPYMET usa nombre legal/visible
  CAPYMET y no hereda dirección, teléfono, correo ni logo MYC; esos datos quedan
  vacíos hasta recibir configuración real y no se inventa un asset.
- `field_sheet_engine_pdf.html` continúa como renderer único versión 1. Los
  defaults mantienen Letter portrait, márgenes 12/10/14/10, título/header/footer
  visibles, grid documental 1, grid de bloque 2, borde/título visibles y
  `break-inside: avoid` con excepción `break-auto`; snapshots sin DSL conservan
  header plano y PDFs congelados no se reinterpretan ni regeneran.
- `signature_layout` está tipado: acepta 1..4 columnas, dirección horizontal o
  vertical y campos posteriores allowlisted. Sin propiedades nuevas conserva
  el grid horizontal derivado; `purchase_order_or_quotation` es la única clave
  posterior vigente y reutiliza `FIELD_LABELS`/`_field_value`.
- Mobile consume el mismo contrato mediante una matriz de posiciones calculadas
  para `row`/`column`/`colspan`/`rowspan`; un header de dos filas ocupa exactamente
  dos filas reales y conserva el scroll horizontal, sin branches por template,
  magnitud u organización.
- No se cambió `FieldSheetResult`, no se creó tabla/migración ni se modificó la
  base local; no corresponde regenerar `backup_erp_myc_antes_prueba.sql`.
- Pendiente de Fase 6A.2 y siguientes: catálogo oficial completo,
  magnitudes aprobadas, asset CAPYMET definitivo y QA visual/físico por hoja.

## Fase 6A.1 — Temperatura y Presión MYC (2026-09-03)

- Estado: **EN REVISIÓN**; no declara Fase 6A ni Fase 6 completas.
- `temperatura` versión 2 materializa FCA-30 `R-1`, familia
  `replicated_comparison`, 10 filas y header agrupado completo con
  `DATOS DE MEDICION` y Patrón 1/2/3.
- `presion` conserva su clave histórica y evoluciona a versión 3: FCA-30 `R1`,
  familia `direction_cycle`, 11 filas y labels literales `Acendente`,
  `Descendente`, `Ascendente`.
- Ambas usan Letter portrait, grid declarativo tabla|firmas, tres firmas
  verticales y OC/Cotización posterior mediante `signature_layout`; no existe
  renderer/template branch individual.
- `supported_equipment`/`search_aliases` permanecen exclusivamente en metadata
  y búsqueda Mobile. Una prueba HTTP crea y guarda Presión para un equipo no
  relacionado con respuesta 201; no existen guards de compatibilidad.
- Un snapshot persistido de Presión prevalece frente a una definición activa
  posterior. No hubo migración, reescritura histórica, cambio de
  `FieldSheetResult`, contrato API ni cambio Mobile.
- Se generaron y revisaron visualmente dos PDFs reales en `output/pdf/`; ambos
  son `%PDF`, una página Letter portrait, con geometría/firmas reconocibles
  contra sus fuentes originales.
- Suite backend ampliada relacionada (template engine, DSL/PDF, contrato
  operacional, captura LAB y revisiones): `118 passed, 18 warnings`, exit 0.
- Micro-pase visual global del renderer: radio exterior `1.2mm`, field cells
  normal/compacta de `7.6mm`/`6.8mm`, padding y line-height explícitos,
  `results-frame` sin borde exterior duplicado y fronteras de grid sin margen
  vertical negativo. La comparación visual antes/después y contra las fuentes
  confirma texto libre de cruces, headers agrupados legibles y una página
  Letter portrait para Temperatura y Presión. Renderer version 1, DSL,
  plantillas, snapshots, lifecycle y Mobile permanecen intactos.

## Cierre quirúrgico acumulativo — 2026-09-04

Cierre sobre `wip/lab-admin-void-delivery`, partiendo de `213dcb0` (que ya
consolidaba el fix P0 de DELETE/storage, el endurecimiento anti-spoofing
`@OT`, notificaciones, observaciones y el admin delete histórico). Este cierre:

- **Preserva sin tocar**: el fix P0 de DELETE/storage (limpieza best-effort
  post-commit, nunca un 409 falso), el endurecimiento `@OT`, el set exacto de
  permisos de Captura (`lab_field_sheets.capture`, `tickets.create`,
  `tickets.view_own`; explícitamente sin `tickets.review`/`view_all`/admin),
  el diseño de Delivery con IDs nulificables/`SET NULL`/snapshot de
  `da6ad5a90e57`, y el contrato de observations.
- **Corrige un bug nuevo confirmado**: `DELETE
  /api/mobile/v1/technician/lab-work-orders/{id}/equipment/{equipment_id}`
  devolvía `500` cuando el equipo tenía una FieldSheet histórica completed y
  la OT había sido reabierta. Causa: `LabWorkOrder.equipment` con
  `cascade="all, delete-orphan"` emitía `UPDATE field_sheets SET
  lab_equipment_id = NULL` antes del DELETE físico, violando
  `ck_field_sheets_exactly_one_equipment_owner`. Detalle arquitectónico
  completo en [`project/DECISIONS.md`](project/DECISIONS.md)
  (D-2026-09-04) y en
  [`architecture/LAB_WORK_ORDERS.md`](architecture/LAB_WORK_ORDERS.md#retiro-de-equipo-individual-tombstone-no-delete-físico).
- Retirar equipo ahora es siempre un tombstone (`SoftDeleteMixin`), nunca un
  DELETE físico; `LabWorkOrder.active_equipment` es la única fuente para
  Mobile, máximo de 10, firmas, cierre técnico y PDF final. FieldSheet
  histórica, `final_pdf_path`/`final_pdf_sha256`, `lab_equipment_id` y el
  historial de Delivery (`LabDeliveryItem`) permanecen intactos al retirar
  equipo. `position` usa un índice único parcial
  (`uq_lab_equipment_position_active`, `WHERE is_active IS TRUE`) y permite
  reutilizar la posición liberada.
- **Deuda de inventario API resuelta** (la pendiente registrada en el corte de
  Fase 6, ver más abajo): se agregó `GET
  /api/communications/work-order-mentions/search` (búsqueda `@OT`,
  checkpoint `c7a7adb`) a `api_access.py` (`_communications_policy`) y se
  regeneró `API_ENDPOINT_INVENTORY_2026-08-03.csv` — el runtime (518
  operaciones) y el CSV committed vuelven a coincidir exactamente
  (`test_committed_inventory_matches_runtime` pasa).
- **Cuatro tests backend previamente rojos, auditados y corregidos en la
  autoridad** (no con xfail/skip/debilitamiento):
  - `test_api_access_conformity.py` (ambos): el conteo `517→518` y la
    igualdad CSV/runtime se corrigieron regenerando el inventario real, no
    ajustando el test a un valor arbitrario.
  - `test_lab_work_orders.py::test_ticket_preserves_minor_change_and_versions_pdf`:
    esperaba `403` de Captura sobre `tickets.create` porque el contrato
    vigente ya le otorga ese permiso (ver arriba); el test ahora prueba que
    Captura SÍ puede crear un ticket y NO puede aprobarlo
    (`tickets.review`/`view_all` siguen fuera de su alcance).
  - `test_schema_integrity_stage_2a.py::test_current_revision_is_the_single_head`:
    tenía hardcodeada una revisión (`b0b560e714db`) de una cadena de
    migraciones anterior; se reescribió para verificar `len(heads) == 1`, la
    garantía real detrás del nombre del test, sin acoplarse a un id concreto.
  - Efecto en cascada: `test_capability_gate_reconciliation.py` subió de 32 a
    33 gaps gobernados al aparecer `lab_work_orders.use` por primera vez en
    el inventario (mismo patrón que la familia `lab_work_order_groups.*`/
    `service_orders.sales.*` ya documentada ahí).
- **Mobile — brecha de descubrimiento de tests corregida de forma acotada**:
  `src/services/lab-equipment-configured-payload.test.ts` no estaba en la
  lista explícita de `package.json#scripts.test` y nunca se ejecutaba bajo
  `npm test`; se agregó a esa lista. Se confirmó explícitamente que
  `deep-link-work-order.wiring.test.ts` (cubierto por el glob
  `src/wiring-tests/*.test.ts`) sigue corriendo. **Hallazgo fuera de alcance,
  no corregido aquí**: al auditar la lista completa se encontraron ~20
  archivos `*.test.ts` adicionales (fuera de `src/wiring-tests/`) que tampoco
  están en `npm test` y uno de ellos falla al ejecutarse por primera vez
  (`MobileSignatureFlow.wiring.test.ts`); ampliar el descubrimiento a esos
  archivos requeriría investigar y corregir esa falla preexistente, fuera del
  alcance de este cierre (LAB equipment delete) — se deja como tarea separada.
- Nueva migración `7088fa142cc2` (detalle en la sección de Persistencia).
- Nuevos tests: `backend/tests/test_lab_equipment_soft_delete.py` (10 casos
  SQLite + 1 regresión PostgreSQL real obligatoria vía `LAB_POSTGRES_TEST_URL`,
  ejecutada y verde contra un schema aislado en `erp_myc` local).

## Validaciones

### Cierre quirúrgico acumulativo — 2026-09-04

- Suite focal nueva (`test_lab_equipment_soft_delete.py`): `10 passed, 1
  skipped` sin `LAB_POSTGRES_TEST_URL`; con la variable exportada contra
  PostgreSQL local (`erp_myc`), `11 passed` (incluye la regresión Postgres
  obligatoria, en schema aislado por test).
- Backend suite completa (sin `LAB_POSTGRES_TEST_URL`, patrón estándar de
  este repositorio): `1137 passed, 12 skipped`, 0 fallas.
- Backend suite completa CON `LAB_POSTGRES_TEST_URL` apuntando a `erp_myc`
  local: `1147 passed, 2 failed`. Las 2 fallas
  (`test_postgresql_concurrent_individual_cohorts_get_distinct_versions`,
  `test_postgresql_concurrent_folio_allocation_is_unique`) son ajenas a este
  cambio y dependientes del estado no-pristino de esa base local (folios ya
  consumidos por trabajo manual previo; una prueba no aísla su schema).
  Confirmado idéntico contra el baseline `213dcb0` vía `git stash` antes de
  restaurar los cambios — no las introdujo ni las agrava este cierre.
- Alembic: `heads`/`current` = `7088fa142cc2 (head)` único; `check` = `No new
  upgrade operations detected`; ciclo `downgrade -1 → upgrade head` correcto.
- Mobile `npm test`: `253 passed, 0 failed`; confirmado explícitamente que
  `lab-equipment-configured-payload.test.ts` y
  `deep-link-work-order.wiring.test.ts` corrieron (sus casos aparecen
  nominalmente en la salida).
- `npx tsc --noEmit -p .`: correcto, sin salida.
- `npm run lint` (`expo lint`, comando canónico de `package.json`): correcto,
  sin errores reportados.
- `git diff --check`: limpio. Se detectó y corrigió un problema de higiene
  antes de este corte: la regeneración de
  `API_ENDPOINT_INVENTORY_2026-08-03.csv` en un paso previo de este mismo
  trabajo había introducido terminadores `\r\n` en todo el archivo
  (`csv.DictWriter` por defecto) contra el `\n` original, produciendo un diff
  de 518 líneas para un cambio real de una sola fila; se normalizó a `\n` y el
  diff quedó mínimo (la fila `@OT` nueva únicamente).
- QA físico Mobile: **pendiente**. No se ejecutó ni se reclama validación en
  dispositivo físico ni simulador para este cierre.

### Cierre operativo y UX OT LAB — 2026-09-03

- Backend focal: `151 passed, 6 warnings`, 0 fallas; backend ampliado
  LAB/Tickets/Notifications: `327 passed, 8 skipped, 6 warnings`, 0 fallas.
- Mobile completo: `330 passed`, 0 fallas, duración final `534.482625 ms`.
- `npx tsc --noEmit`: correcto, exit code 0.
- `npx expo lint`: exit code 0, 0 errores y 2 warnings del hook vigente en
  `FieldSheetResultsWorkspace.tsx`.
- `npx expo export --platform ios`: correcto, exit code 0; bundle de 1265
  módulos exportado a `dist`.
- Alembic local: upgrade aplicado desde `b0b560e714db`; `current`, `heads`,
  constraint de ocho tipos y respaldo regenerado confirman
  `9f3a2c7d1e84`.
- Pendiente verificable: QA físico Android/iPhone previo al build.

### DSL de Hojas de Campo — Fases 4 y 5 (2026-09-02)

- Suite focal backend (`test_field_sheet_layout_dsl.py`,
  `test_field_sheet_template_engine.py`, `test_field_sheet_operational_contract.py`,
  `test_lab_field_sheets_capture.py`, `test_lab_phase6_field_sheet_revisions.py`):
  `101 passed`, 11 warnings.
- Suite backend completa: `935 passed, 8 skipped, 2 failed`, 13 warnings y
  19 subtests passed. Las dos fallas son las preexistentes de
  `test_api_access_conformity.py`: el runtime tiene 506 operaciones frente al
  inventario histórico de 477 y el CSV committed no coincide; esta fase no
  agregó endpoints ni modificó ese inventario.
- Pruebas Mobile focales del workspace/intérprete: `9 passed, 0 failed`.
- Suite Mobile completa: `313 passed, 1 failed` (314 total). La falla ajena es
  `request-inbox.test.ts` (`la solicitud linked_folio presenta identidad real
  del equipo al Admin`) contra `tickets.tsx`, ambos intactos en esta fase.
- `npx tsc --noEmit`: correcto, exit code 0.
- `npx expo lint`: exit code 0, 0 errores y 8 warnings preexistentes (6 imports
  sin uso en `work-orders.tsx` y 2 advertencias de hook en
  `FieldSheetResultsWorkspace.tsx`).
- Fixtures de aceptación temporales Temperatura-like y multisección compleja
  validan HTML con spans y generación real `%PDF`; no se registraron como
  templates oficiales.
- Microcierre focal: backend `88 passed`, 12 warnings; Mobile `9 passed`, 0
  fallas; `npx tsc --noEmit` correcto (exit code 0). Cubrió aislamiento CAPYMET,
  posición lógica de `column_key`, rowspan Mobile real y defaults completos v1.
- Micro-extensión de firmas previa a 6A.1: suite focal backend `112 passed`,
  18 warnings de deprecación, exit code 0. Cubrió default horizontal derivado,
  tres firmas verticales, campo posterior, rechazos 422 y PDF real `%PDF`.

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
  refresh/realtime, retiro de equipo tras reapertura y errores. **No
  ejecutado**; ningún cierre reciente (incluido el de 2026-09-04) lo reclama
  como hecho.
- Inventario API (`API_ENDPOINT_INVENTORY_2026-08-03.csv`) resuelto en el
  cierre de 2026-09-04: runtime y CSV committed vuelven a coincidir (518
  operaciones); `test_api_access_conformity.py` pasa sin excepciones.
- Mobile: ampliar `npm test` para descubrir el resto de archivos
  `*.test.ts` fuera de `src/wiring-tests/` (hoy sólo se ejecutan los listados
  explícitamente en `package.json`); requiere primero investigar y corregir
  la falla preexistente descubierta en `MobileSignatureFlow.wiring.test.ts`
  al ejecutarla por primera vez (ver cierre 2026-09-04). Tarea separada, no
  causada por LAB equipment delete.
- `test_postgresql_concurrent_individual_cohorts_get_distinct_versions` y
  `test_postgresql_concurrent_folio_allocation_is_unique` fallan contra la
  base local `erp_myc` por estado no-pristino/no aislado (ver Validaciones
  2026-09-04); requieren una base Postgres efímera dedicada o aislar su
  schema, no relacionado con LAB equipment delete.
- Mantener fuera de esta fase los hallazgos separados de FieldSheets
  (contenido, tabla Valve, overflow, columnas, imprimibles y plantillas),
  NIIMBOT, cambios MYCA/MYCT/rangos, LabClient y Fase 2 sin regresión.

## Regla de mantenimiento

Después de cualquier cambio funcional, esquema, configuración, prueba o
recurso, este snapshot y `PROJECT_FILE_REGISTRY.md` deben sincronizarse en el
mismo trabajo. Si una futura tarea modifica la base local, debe regenerar el
respaldo oficial y comprobar su `alembic_version` contra el head único.
