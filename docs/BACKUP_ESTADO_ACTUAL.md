> Estado: VIGENTE
>
> Tipo: Snapshot operativo verificable
>
> Autoridad: Media; no sustituye los documentos canónicos de project/
>
> Corte: ETS ↔ LAB Fase 3 (Mobile único editor técnico, gobierno ERP y Captura PDF-only) sobre `e4cfb42`, rama `feat/mobile-calibration-authority-2026`; push a origin sin merge ni deploy, pendiente de revisión.

# Estado operativo actual del ERP MYC

## Modalidades iniciales de grupos LAB internos (2026-10-06, sin commit)

- Worktree `myc_erp-lab-group-workflow`, rama
  `fix/mobile-lab-group-workflow-selection`, base y origin `589e53d8b6d275e88ebd4b65012bef35b5a5a56b`;
  limpio al comenzar. Pendiente revisión humana del diff; sin commit/push/merge/deploy.
- Causa: Mobile ocultaba modalidad en grupo directo y la materialización repetía
  el único `workflow_mode`. Confirmadas firma/prevalidación/finalización mixtas
  ya existentes; no se modificaron.
- `LabWorkOrderInternalGroupCreate.member_workflow_modes` opcional valida valores
  y longitud exacta. Router → servicio directo o vinculado → única
  `_materialize_group`, con modalidad por `sequence_number` en la transacción
  inicial. El vínculo ETS sigue siendo uno, a la raíz. `group_materialized`
  registra array ordenado o base homogénea; no genera cambios administrativos.
- Mobile: cantidad, modalidad base, aplicación a todas/manual por OT. Helper puro
  reconcilia posiciones y construye payload; alta individual y solicitud externa
  conservan sus contratos. Sin AsyncStorage, cambios de permisos ni migraciones.
- Rojo/verde: las dos regresiones mixtas (con/sin ETS) fallaron antes con HTTP 422
  `extra_forbidden`; pasaron tras implementar. Casos adicionales verifican
  omitido/null, ambos modos homogéneos, arrays cortos/largos/inválidos, orden,
  auditoría, rollback al fallar segundo miembro/auditoría/commit y aprobación
  externa histórica (siempre `group`).
- Backend focal final: `test_lab_erp_calibration_bridge.py`,
  `test_lab_work_orders.py`, `test_lab_equipment_by_equipment_workflow.py`,
  `test_service_order_lab_links.py`: **219 passed, 16 skipped** (PostgreSQL opt-in).
  Suite completa `python -m pytest -q`: **2228 passed, 45 skipped, 1 failed**,
  además de 23 subtests passed. Único fallo: recurso oficial no versionado ausente
  `backend/resources/sat/catalogo sat.xlsx`, caso `test_official_regime_626_is_read_from_the_xlsx`.
  Reproducido en extracción de `main` (`589e53d8`) dentro de `tmp/main-baseline`:
  `test_sat_xls_source.py` **3 passed, 1 failed** con la misma causa; no corregido.
- Mobile focal: **66/66** (helpers de creación/vínculo/flujo/firma/cierre y wiring
  de workflow); `npm test` completo: **935/935**. El follow-up de cambio de modalidad base
  quedó cubierto por helper + wiring (**33/33**): en configuración manual, cambiar
  la base reinicializa todas las posiciones con la nueva modalidad. Wiring previo
  ajustado únicamente para permitir grupos internos y delegar payload al helper
  funcional probado.
- `npm run lint`: exit 0. ESLint focal `--max-warnings=0`: exit 0.
  `tsc --noEmit`: sólo TS2322 en `src/realtime/realtime-client.ts:205,231`;
  reproducidos idénticos en extracción de `main` con las mismas dependencias.
- Registry y su generador sincronizados; `git diff --check` limpio. Pruebas con
  el venv existente y dependencias Mobile existentes; código ejecutado desde este
  worktree. Sin cambio de BD operativa ni regeneración de respaldo SQL.
- Pendientes: revisión del diff, QA visual/táctil en dispositivo y suites opt-in
  de locks PostgreSQL. Contrato vigente en
  [LAB_WORK_ORDERS.md](architecture/LAB_WORK_ORDERS.md#modalidades-iniciales-de-grupos-directos-internos-2026-10-06).

## Hoja de campo Mobile al regresar a foreground (2026-10-06)

- Base `f377b511e5d18d408ef48690d17c45342c70cdeb`, rama
  `fix/mobile-field-sheet-foreground-navigation`.
- Causa confirmada: `app.foreground` refrescaba la OT y reconciliaba `technical`
  a `capture` por su status `draft`, desmontando `LabTechnicalCapture` y su hoja local.
- El resolver canónico recibe el `workflow_mode` recién refrescado desde sus dos
  consumidores y conserva sólo `equipment_by_equipment + technical + draft`.
  Firmas y estados terminales mantienen su autoridad. Apertura por status y
  selección de otra OT conservan su inferencia vigente.
- Regresión rojo/verde: 43/45 antes (fallaban los dos casos críticos por cohorte),
  45/45 después. Pruebas relacionadas OT/notificaciones/realtime: 81/81;
  suite Mobile completa: 919/919. Lint focal y `git diff --check`: sin errores.
- TypeScript (`npx tsc --noEmit`) falla con TS2322 en
  `src/realtime/realtime-client.ts:205,231` (`number | Timeout`). Mismos dos errores
  reproducidos con iguales dependencias en una extracción de `main` (`f377b511`)
  dentro de este directorio, sin cambiar de rama ni usar otro worktree.
- Sin migraciones ni cambios de backend, API, persistencia o componentes de captura.
- Pendiente: prueba manual en dispositivo del ciclo otra app → Mobile. La suite
  verifica el resolver y cableado fuente, no montaje React Native.
  Los errores TypeScript quedan fuera de alcance; no se encontró segunda causa
  concurrente de expulsión durante la auditoría focal.

## Endurecimiento edición de recepción LAB / autosave FieldSheet (2026-10-02)

- Base `84f895f`, rama `fix/mobile-lab-reception-editing-hardening`; sin commit/push/migraciones.
- Backend: `update_configured_equipment` calcula el diff autoritativo de servicio; sin cambio no
  toca servicio/folio. Cambio explícito antes de firma reasigna folio con
  `_release_equipment_certificate_folio` (pool externo → `released`; interno se quema).
  Siguen 409: recepción firmada, folio `authorized`, hoja completada.
- Mobile: autosave silencioso con debounce 800 ms, flush en blur/acciones sensibles,
  single-flight + seq/generación contra respuestas obsoletas; cambiar `reception_date`
  ya no reemplaza la captura local. El autosave no envía resultados ni crea revisiones.
- Validación: backend `tests/test_lab_phase2_integrated_alta.py` 77 passed; suite completa
  2204 passed, 1 fallo preexistente (`test_sat_xls_source`, falta `catalogo sat.xlsx`);
  Mobile 890/890. `tsc` sólo conserva 2 errores preexistentes en `realtime-client.ts`.

## Representación documental LAB en el ERP (2026-09-29)

- Preflight limpio: HEAD = origin = `29d788924639c485ff6ea466e35be02291bc9ad0`.
- PDF oficial de OT LAB accesible desde el ETS (`/mobile-execution/work-orders/{id}/pdf`,
  reutiliza `get_pdf`, sin regenerar). Captura LAB incluye por OT `OT-<folio>.pdf` +
  Hojas de Campo y bloquea con `LAB_WORK_ORDER_FINAL_PDF_MISSING`. Inventario API: 551.
- Vistas Ejecución/Captura/detalle alineadas al design system del ERP (`.ets-lab-*`
  sólo layout); geometría verificada con el CSS real a 1080/300 px.
- Backend focalizado 44 passed; frontend 113/114 (fallo preexistente
  `notificationNavigation`); build correcto. Sin migraciones ni cambios en Mobile,
  vínculo, folios, corrección, entregas, Certificate, XLSX o Calidad.

## Cierre UX ETS ↔ LAB Fase 3 (2026-09-29)

- Preflight limpio: HEAD = origin = `6a0e53e5f86680bd9f375a8b37393e686f2bb3bb`.
- Captura Mobile: pestaña, franja del Resumen y panel comparten el resumen LAB
  (`useMobileCaptureSummary`); se corrige "BLOQUEADA" con LAB lista. ZIP LAB plano
  `OT-<folio>/Hoja_Campo_<folio certificado>.pdf` (legacy sin cambios).
- Proyección con `report_number`, observaciones, condición, empresa vinculada y cliente
  documental; detalle read-only único para Ejecución y Captura con datos completos de
  hoja, `row_data` dinámico, revisiones/PDF y "Enviar a corrección" por permiso.
- Layout propio con container queries; geometría verificada con el CSS real en un arnés
  local (`tmp/lab-authority-validation/ui/harness.html`, retirable).
- Sin migraciones, sin cambios en Mobile, dominio de corrección, vínculo, folios,
  Certificate/Calidad/XLSX.
- Backend focalizado 37 passed; frontend `node --test` 107/108 (fallo preexistente
  `notificationNavigation`); `npm run build` correcto.

## ETS ↔ LAB Fase 3 — Mobile único editor técnico (2026-09-29)

- Preflight: worktree limpio, rama `feat/mobile-calibration-authority-2026`,
  HEAD = origin = `e4cfb42c2535c33d6f658e6d0d677c4d4150aab1`. Sin rama/worktree nuevos,
  merge ni deploy.
- Buscador OT LAB en Mobile: backend correcto en SQLite y PostgreSQL 16 real (folio
  exacto/parcial, cliente case-insensitive, q+estado, paginación). Corregido en cliente
  el anexado heredado del estado de carga (búsqueda durante "Cargar más") con
  `src/sync/work-order-list-query.ts`; el servidor confirma `q` con
  `X-MYC-Search-Applied` y Mobile reporta un backend que lo ignore (anterior a `9cd8796`,
  causa plausible del síntoma físico; no verificable sin el dispositivo/servidor usados).
- Catálogo: `expected_certificate_master_id` LEGACY; Calibración/Verificación sin Master;
  ETS acepta Verificación sin Master; paquete legacy de Verificación sin Master genérico
  va sólo con PDF. Sin migración ni borrado de datos.
- Proyección READ-ONLY `/mobile-execution` (+ detalle de hoja y PDF final), acciones
  administrativas ERP (enviar a corrección, cancelar/restaurar OT) sobre el dominio LAB,
  Captura LAB PDF-only con bloqueos estructurados y vista web correspondiente.
  [Contrato](architecture/ETS_LAB_TECHNICAL_BRIDGE.md#fase-3--mobile-único-editor-técnico-erp-proyecta-gobierna-y-entrega-a-captura-2026-09-29).
- Sin migraciones: head Alembic sin cambios (`e8f1a3c5d7b9`); no se regeneró
  `backup_erp_myc_antes_prueba.sql` ni se usó la BD compartida.
- Backend full (SQLite): 2080 passed, 42 skipped, 0 failed tras ajustar el conteo
  gobernado de `test_capability_gate_reconciliation` (+`work_orders.reopen`,
  +`lab_work_orders.cancel`). Focalizado bridge/proyección/admin/Captura con
  `ETS_LAB_POSTGRES_TEST_URL` en PostgreSQL 16 aislado (`tmp/lab-authority-validation`,
  puerto 55442, recurso de esta ejecución y retirable): 152 passed, 0 skipped.
  Inventario API regenerado: 550 operaciones.
- Frontend `node --test`: 96 passed, 1 failed preexistente (`notificationNavigation`,
  archivo sin cambios); `npm run build` correcto. Mobile: 869/869, `tsc` y lint limpios.
- Pendiente: TD-068 (validación visual/física), fase documental XLSX → Certificate LAB
  (TD-066) y simetría PDF-only legacy (TD-069).

## ETS ↔ LAB Fase 2 — calibración ejecutada en MYC Mobile (2026-09-29)

- Cierre de auditoría sobre `b375fb6`: Resumen web Mobile sin métricas ni accesos ERP
  a equipos/hojas y guard de navegación; capacidades web sólo con partidas activas;
  candidatos Mobile filtrados por calibración exclusiva en SQL (LIMIT exacto);
  advertencia no bloqueante de cliente ERP ≠ cliente LAB en Mobile.
- Preflight: worktree limpio, `feat/mobile-calibration-authority-2026` = origin =
  `8b6da02` (contiene `39ed4bc` y `3a7648b`), divergencia con `origin/main` 0/0.
  Sin rama/worktree nuevos, push, merge ni deploy.
- ETS nuevo sólo de calibración: `work_order_number` NULL, sin `ServiceWorkOrder`,
  sin consumir la secuencia OT. Mixtos/otras categorías/históricos sin cambios.
  Frontera 409 `CALIBRATION_TECHNICAL_FLOW_MANAGED_BY_MOBILE` en backend. Selector Mobile
  de ETS de calibración (solo lectura) y creación OT/grupo directo + vínculo en una
  transacción; externos sin cambios. Shell web del ETS con Resumen “Ejecución técnica
  MYC Mobile”. [Contrato](architecture/ETS_LAB_TECHNICAL_BRIDGE.md#fase-2--ets-de-calibración-ejecutado-en-myc-mobile-2026-09-29).
- Migración `e8f1a3c5d7b9` sobre `d7e9a1c3b5f0`, único head. PostgreSQL 16 aislado
  (`tmp/mobile-calibration-validation`, puerto 55441): upgrade desde vacío,
  downgrade, upgrade; el downgrade se niega con ETS de número NULL (verificado) y dos
  NULL coexisten bajo el índice único. `alembic check`: sólo la diferencia preexistente
  TD-063. La BD compartida no se utilizó ni migró.
- `backup_erp_myc_antes_prueba.sql` (ignorado por Git) generado desde la BD **aislada**
  de validación en `e8f1a3c5d7b9`; no contiene datos operativos ni sustituye un respaldo
  de la base compartida.
- Backend (BD aislada): focalizado bridge Fase 1 + Fase 2 + ETS Mobile **146 passed**,
  0 skipped (incluye concurrencia PostgreSQL real). Full final: **2051 passed,
  10 failed, 19 skipped, 12 errors**; todos los fallos/errores existen en la línea base
  exacta de `8b6da02` (11 failed, 12 errors, mismo entorno); ninguno nuevo. Dos pruebas
  que asumían OT en calibración exclusiva se adaptaron a la regla (compuesto de
  calibración y autoasignación en ETS histórico).
- Mobile: 859/859, `tsc` y lint limpios. Frontend: `node --test` 83 passed, 1 failed
  preexistente (`notificationNavigation`), build correcto.
- Pendiente: validación visual/física (TD-065) y Captura LAB (TD-066).

## PDF de Cotizaciones — 2026-09-29

- Preflight limpio: HEAD y origin/feat/ets-lab-technical-bridge en
  `39ed4bc08115d53aae01a2756e57f0c18e119cd2`; origin/main en
  `439278282328d79535494d59db4346900ab387f0`, ahead 2 / behind 0.
- Causa: navegación directa a API sin Bearer en tres botones; resumen comercial
  incondicional aunque show_summary_terms fuera false.
  Descargar PDF, Imprimir y Vista PDF de prueba reutilizan downloadQuotationPdf/getAccessToken.
  Pestaña reservada antes de fetch, Blob autenticado, cierre ante errores,
  impresión tras carga y liberación diferida de URLs. Nombre de descarga intacto.
- La plantilla condiciona todo el resumen y su versión; Notas, términos completos
  y firma conservan controles independientes. Las tres flags ya persistían por
  API/BD; no se cambian modelos, schemas, migraciones, permisos ni ETS/LAB.
- Backend dirigido: 36 passed y 12 subtests passed (incluye 8 combinaciones PDF
  reales y 401/403/200), con un warning existente de Starlette.
- Revisión de lifecycle PDF: observación de carga limitada explícitamente a
  60 segundos; timers eliminados al cargar, cerrar durante la espera, fallar
  navegación o vencer el plazo. pagehide no persistido libera el Blob; visores
  aislados y páginas en caché lo conservan hasta la liberación del documento
  creador por el navegador. Sin polling indefinido ni revocación por caducidad.
- Generador de inventario restaurado exactamente a HEAD y ejecutado de nuevo;
  conserva las filas descriptivas existentes según su comportamiento original.
- Revalidación: quotation PDF backend 9 passed (ocho combinaciones y 401/403/200);
  frontend dirigido 23 passed (PDF y quotationsVerificationQa); build correcto.
- Validación anterior, antes de esta revisión de lifecycle:
  frontend dirigido 19 passed (PDF y quotationsVerificationQa); build correcto.
  Suite completa node --test: 74 passed, 1 failed.
  PDFs de las ocho combinaciones generados y rasterizados; inspección visual
  de muestras sin resumen, con términos completos y con resumen/firma.
  npm run lint y npm test no se ejecutan porque package.json no define esos
  scripts. Se usa node --test; su suite completa conserva un fallo ajeno en
  notificationNavigation.test.js (work_order espera /communications, obtiene
  /dashboard?work_order_id=12#servicios), con archivos idénticos a HEAD.
- Validación PDF sobre SQLite en memoria; no se modifica la BD local persistente
  ni se requiere migración o regeneración de respaldo SQL.
- Pendiente: validación manual autenticada de los cuatro botones y del diálogo
  nativo de impresión en el navegador de destino. Visores que aíslan su documento
  o no notifican carga mantienen el PDF abierto y muestran alternativa manual.
- Sin commit, push, merge ni deploy; cambios preparados para revisión.

## Cierre acotado ETS ↔ LAB sobre `108c713` (corte anterior)

- Preflight completo aprobado: worktree limpio, rama correcta y
  `HEAD = origin/feat/ets-lab-technical-bridge = 108c713ed9cab08214dcf09da504904f2a0c0f4a`.
- Auditoría de autorización: `service_orders.update` se concede directamente
  a Comercial, Tecnico y Desarrollador; Administrador lo satisface por `*`.
  Los demás seis roles no lo reciben. La unión de roles activos es aditiva;
  los overrides individuales no intervienen en `require_permission`.
- Decisión justificada antes del cambio: link/replace/unlink requieren
  **service_orders.create AND service_orders.update**. M14.A02/M11.A06 y la
  matriz vigente distinguen autoridad de creación/completado del contexto
  ETS de edición operativa. No se agrega permiso ni se cambia catálogo,
  asignaciones o autenticación. Técnico puro recibe 403; Comercial,
  Desarrollador y Administrador conservan gestión; composición e inactividad
  de roles quedan probadas. Guard central mínimo create y doble control explícito
  en cada ruta. Lectura conserva read. Inventario exacto en el
  [contrato del bridge](architecture/ETS_LAB_TECHNICAL_BRIDGE.md).
- `/lab-candidates` sigue siendo exclusivamente búsqueda por folio de grupos
  LAB. No es el flujo Mobile de selección de cotización/ETS, reservado para
  una fase posterior. No se cambia el endpoint ni el dominio técnico LAB.
- Sin defectos adicionales de dominio en las invariantes revisadas. Se mantienen
  modelo, servicio, schema y migración `d7e9a1c3b5f0` de Fase 1. No hay frontend,
  Mobile, Captura, Calidad, Certificados, paquetes, sincronización o creación
  de grupos en este cierre.
- Gate focalizado: **118 passed, 0 failed, 0 skipped**, tres warnings existentes
  de Starlette/reflexión SQLite, en 13.64 s. Comando desde backend con `.venv`:
  `python -m pytest tests/test_service_order_lab_links.py tests/test_service_order_integrity.py tests/test_api_access_conformity.py -q`.
  `DATABASE_URL` y `ETS_LAB_POSTGRES_TEST_URL` apuntaron a la BD aislada UTF-8
  en puerto 55439. Los cinco escenarios concurrentes PostgreSQL pasaron;
  cada uno utiliza un esquema aleatorio propio que se elimina al terminar.
- Cobertura: exclusividad raíz/ETS con constraints, hija y siblings a una sola
  raíz, bloqueo link/replace/unlink por ETS closed/cancelled/inactive,
  rechazo link/replace por raíz cancelada, unlink después de cancelación LAB,
  historial/sucesor, rollback completo y carrera de dos reemplazos competidores
  conservando intacto el vínculo del perdedor. Se probaron los diez roles,
  composiciones y ausencia de cualquiera de los dos permisos, incluso sin guard
  central. La suite suma 104 pruebas bridge, 10 integridad ETS y 4 conformidad API.
- Inventario API regenerado y verificado (543 rutas); registro funcional
  regenerado y rutas comprobadas; compileall y `git diff --check` correctos.
  Sin migración ni cambios persistentes de datos operativos; la BD compartida
  no se utilizó. La suite full y Alembic global no se repiten en este cierre
  acotado: sus hallazgos preexistentes TD-063/TD-064 siguen documentados abajo.
- Documentación sincronizada: contrato, matriz, reglas, alcance, decisiones,
  corte operativo e inventarios. Índice, estado, flujo, observaciones y deuda
  revisados sin cambios de responsabilidad/estado. No se crean, mueven ni archivan
  documentos. Commit de cierre separado; sin push, merge ni deploy.

## ETS ↔ LAB técnico — Fase 1 (2026-09-28)

- Preflight completo: worktree limpio en `feat/ets-lab-technical-bridge`,
  HEAD y origin/main en `439278282328d79535494d59db4346900ab387f0`.
  Trabajo exclusivo en `myc_erp-dev1c`; sin crear worktree/rama, push, merge ni deploy.
- Implementados modelo/tabla `ServiceOrderLabLink`, relación histórica del ETS,
  schemas y servicio dedicado, seis endpoints ERP (activo, historial, link,
  replace, unlink y candidatos), permisos existentes `service_orders.read/update`
  y auditoría canónica. LAB mantiene su autoridad técnica; frontend y Mobile
  no se modifican. [Contrato completo](architecture/ETS_LAB_TECHNICAL_BRIDGE.md).
- Exclusividad por ETS y raíz mediante índices únicos parciales; FKs RESTRICT,
  checks de estado/lifecycle, locks ETS/raíz y rollback completo de reemplazo.
  Motivo obligatorio, actores, idempotencia y revinculación con nuevo historial.
- Migración `d7e9a1c3b5f0` sobre único head previo `c4d8e2f1a7b3`.
  Upgrade desde vacío y ciclo upgrade/downgrade/upgrade verificados con PostgreSQL
  16 aislado en `tmp/ets-lab-validation`; migración SQLite también probada.
  La base compartida por defecto quedó intacta en `602a09af6218`.
- Respaldo local ignorado por Git `backup_erp_myc_antes_prueba.sql` regenerado
  desde la BD **aislada de validación**, sin datos operativos del usuario.
  Su `alembic_version` coincide con `d7e9a1c3b5f0`; no sustituye un backup de
  la base compartida. Los logs de validación son locales bajo `tmp/ets-lab-validation`.
- `alembic check` ejecutado: diferencia preexistente
  `uq_mobile_biometric_credential_hash` (TD-063). Reproducida con el código exacto
  `4392782` y su head `c4d8e2f1a7b3` en un snapshot de archivos dentro de tmp,
  además del head nuevo. No hay diferencias adicionales del bridge.
- Validación focalizada final: `python -m pytest tests/test_service_order_lab_links.py
  tests/test_service_order_integrity.py tests/test_api_access_conformity.py -q`
  desde backend con `.venv`: **69 passed** (55 bridge, 10 integridad ETS,
  4 conformidad API); incluye cuatro escenarios concurrentes PostgreSQL,
  constraints SQLite, rollback por fallo de inserción/auditoría/commit y
  ciclo SQLite upgrade/downgrade. `ETS_LAB_POSTGRES_TEST_URL` apunta a la
  base aislada UTF-8 en puerto 55439; no hubo skips en este gate.
- Suite completa: `python -m pytest tests -q` desde backend, con `DATABASE_URL`,
  `ETS_LAB_POSTGRES_TEST_URL` y `LAB_POSTGRES_TEST_URL` apuntando a PostgreSQL
  aislado: **1966 passed, 6 failed, 19 skipped**, 19 subtests passed. Incluye
  suites ETS y LAB. Esta ejecución precedió dos pruebas adicionales del bridge
  (rechazo de token Mobile y roundtrip SQLite), ambas aprobadas en el gate final.
- Contraste con snapshot exacto del commit base `4392782`, mismo comando full:
  **1912 passed, 7 failed, 19 skipped**, 19 subtests passed. Los seis fallos
  de la rama están reproducidos en la base: una prueba LAB de cohortes con
  equipo sin `service_type`, cuatro aserciones de logging del Developer Broker
  y el XLS SAT oficial ausente. El fallo adicional de la base es
  `test_postgresql_concurrent_folio_allocation_is_unique`: esa prueba reutiliza
  la BD indicada por `LAB_POSTGRES_TEST_URL` y exige folios iniciales 6400/6401,
  pero la ejecución anterior ya consumió la secuencia (obtuvo 6404/6405).
  No se modifican esos módulos/pruebas ajenos. Lista exacta en TD-064 y logs
  `full-backend.log` / `baseline-full.log` del directorio local de validación.
- `python -m compileall` sobre archivos Python afectados, inventario API `--check`,
  generador de registro, verificación de rutas y `git diff --check`: correctos.
  No existe configuración de lint/formato Python en el backend; no se instaló
  ni se introdujo una herramienta nueva para esta fase.
- Inventario API: 543 operaciones y seis rutas nuevas clasificadas.
  Registro funcional regenerado; también reconcilia dos scripts Windows ya
  versionados y retira la referencia al XLS SAT ausente en este worktree.
  Sin modificaciones a esos scripts ni a recursos SAT.
- Revisión documental: actualizado contrato LAB/bridge, permisos, canónicos de
  alcance/flujo/reglas/decisiones/estado, índice, deuda e inventarios.
  `OBSERVATIONS_REGISTER.md` revisado sin cambios: no se cierran observaciones
  funcionales/UX existentes. Se crea sólo el contrato arquitectónico del bridge;
  no se mueven ni archivan documentos.
- Pendientes fuera de Fase 1: frontend, Captura/Calidad/Certificados, handoff,
  paquetes LAB desde ETS, sincronización y creación automática de grupos.
  Aplicar migración en el entorno destino antes de habilitar endpoints.

## MYC Mobile — refetch no destructivo y selector modal de cliente OT (2026-09-28, en revisión)

- `fix/mobile-refetch-and-lab-client-modal` mergeada en `main` `807c957`.
  Corrección de `FadeIn` en rama `fix/mobile-fadein-reduce-motion` sin
  commit/push. Sin migraciones, sin cambios backend ni de permisos.
- Listas de OT, Tickets y Clientes: la revalidación (filtro, focus, realtime,
  pull, renovación de sesión) conserva los datos mostrados; spinner sólo en la
  primera carga (`src/sync/list-load-state.ts`). `authorizedFetch` conserva
  identidad ante renovaciones y los disparadores usan `user.id`.
- OT LAB: cliente receptor mediante `LabClientPickerModal`; “Cambiar cliente”
  no borra el cliente previo; alta contextual con el término buscado; Back de
  Android en el alta vuelve a búsqueda. Al elegir cliente, sus datos derivados
  no mezclan valores del anterior (`lab-work-order-client.ts`). Equipos
  conservan el selector inline.
- Solicitudes: tarjetas con título flexible multilínea y badge de estado
  estable; verificado visualmente en simuladores MYC iPhone 16e y SE 3.
- `FadeIn`: causa física confirmada en iPhone 16e con “Reducir movimiento”
  activo (contenido envuelto invisible). Ahora sólo anima `translateY`;
  opacity 1 permanente; sin animación con Reduce Motion o preferencia aún
  desconocida. Pendiente revalidar en el 16e con Reduce Motion activado.
- Validación: Mobile 846/846, lint OK; TypeScript sólo con los 2 errores
  preexistentes de `src/realtime/realtime-client.ts` (idénticos en `056cdbe`);
  tras regenerarse los tipos locales de Expo (`expo-env.d.ts`, `.expo/types`,
  no versionados) `tsc --noEmit` termina sin errores.
  Pendiente validación en iPhone 17e Simulator e iPhone 16e físico (OBS-047).

## OT LAB — buscador y cabecera compacta (2026-09-25, en revisión)

- Implementados `q` compatible y accesos de generación horizontales; contrato
  en `architecture/LAB_WORK_ORDERS.md#api`. Sin migraciones ni cambios de permisos.
- Validación: filtros backend 3 passed; Mobile 784/784; lint y TypeScript OK.
  Suite ampliada LAB/seguridad: 472 passed, 16 skipped y un fallo por ejecutar
  desde raíz un test que lee rutas relativas a backend; repetido desde backend:
  1 passed. No hay fallos funcionales pendientes en las suites ejecutadas.
  `git diff --check` OK.
- Teclado previo conservado; usuario reporta validación en iPhone 17e Simulator,
  iOS 26.5. Pendiente revisión visual de la nueva cabecera y desplegar backend
  con soporte `q` antes de usar esta versión móvil. Sin commit/push.

## DEV-1B — Windows Named Pipe + Broker host (EN REVISIÓN)

## DEV-1C — dos ajustes posteriores a la validación Windows

- Base de esta revisión: `9b71c21`, worktree `myc_erp-dev1c`, rama
  `feat/mobile-developer-broker-service-dev1c`; estado inicial limpio.
- El usuario confirma instalación/reinstall idempotente, secreto reutilizado,
  ledger 6 y uninstall real/WhatIf validados en Windows, con aislamiento y
  hardening preservados. Ese reporte supera los pendientes de instalación del
  corte anterior que se conserva debajo; estos dos ajustes aún requieren QA Windows.
- Nuevos backups en `DeploymentRoot\acl-backups`; legacy intactos, restaurables
  sólo mediante ruta explícita. Sin migración, borrado histórico ni restore automático.
- Frontera ACL: backups en `persistent_protected`, fuera de `owned`; borrado
  rechazado por `remove-owned-tree`. Misma ACL y compatibilidad legacy.
- Mensaje final WhatIf corregido; ShouldProcess, schema 6 y SeServiceLogonRight intactos.
- DEV-1C: 314 passed (incluye estáticos PowerShell). Regresión Broker:
  262 passed, 12 skipped (Windows). git diff --check OK. Sin operaciones Windows reales, commit ni push en esta revisión.

## DEV-1C — Servicio Windows `MYCDeveloperBroker` / identidad dedicada (EN REVISIÓN)

- Worktree `/Users/saulcortes/Developer/myc_erp-dev1c`, rama
  `feat/mobile-developer-broker-service-dev1c`, base `05f4c625` (= `main`,
  merge PR #9). Sin commit, sin push, sin PR. Producción no se tocó.
- Implementado (sólo activos de despliegue; `backend/app/developer_broker/`
  sin cambios): `deploy/windows/developer-broker/` con plantilla WinSW,
  `broker_deploy.py` (plan/política ACL, veredicto de servicio, INF de
  `SeServiceLogonRight`, render del XML, bloque gestionado de `backend\.env`,
  secreto por generación/stdin/reuse), módulo PowerShell, instalador con
  preflight, desinstalador acotado, validador post-instalación y
  endurecimiento de `C:\MYC\Services`. `.gitignore` excluye cualquier XML
  renderizado bajo `deploy/windows/`.
- Identidad: cuenta virtual `NT SERVICE\MYCDeveloperBroker` registrada con
  `sc.exe create … obj=` (nunca LocalSystem, ni transitoriamente); SID
  resuelto en el host por LSA + SCM; cliente ERP `S-1-5-18` verificado.
- Hallazgo de seguridad de producción: `C:\MYC\Services` con
  `Authenticated Users: Modify` sobre wrappers/XML de servicios LocalSystem.
  Endurecimiento reproducible con respaldo JSON por entrada (SDDL) y
  restauración explícita con `Restore-MYCServicesAcl.ps1` (TD-061);
  **no aplicado todavía** en `ADMIN`.
- Configuración de producción: no existe aún ningún `DEVELOPER_BROKER_*`
  en `backend/.env` del servidor; la escribirá el instalador (bloque
  gestionado, deshabilitado hasta validar el Broker).
- Correcciones de auditoría (2026-09-25, sin commit): ledger de propiedad
  `install-state.json` incremental/atómico (P0: `SeServiceLogonRight`
  `pending`→`added`, nunca si ya era efectivo; uninstall deshace sólo lo
  registrado, también tras instalación parcial); alcance ACL reducido a los
  directorios `developer-broker` (P1: `C:\MYC\Deployment` y
  `C:\MYC\Logs` sólo se inspeccionan); aprovisionamiento XML + `.env`
  transaccional con journal transitorio y recuperación (P1). Tras las
  correcciones: despliegue 150 passed; contrato + named pipe + Windows +
  endpoint 262 passed, 12 skipped; DEV-0 + conformidad 97 passed, 1 skipped.
- Cierre DEV-1C (2026-09-25, sin commit): ledger esquema 6; propiedad del
  bloque de `backend\.env` con marcador no secreto + huella PBKDF2 (un
  `pending` nunca toca un bloque sin prueba; un `owned` alterado se
  rechaza); `acl_grants` por concesión `pending → owned` con verificación
  exacta y revocación sólo de la ACE exacta; reinstalación sin re-proteger
  `ServiceDir`/`LogDir` propios; `Restore-MYCServicesAcl.ps1` para el
  respaldo JSON por entrada (sin `icacls /restore`). Validación en el
  reporte de cierre.
- Quinta ronda de auditoría (2026-09-25, sin commit): ledger esquema 5;
  directorios y bloque `backend\.env` con `none → pending → owned`
  (prueba releída antes de `owned`; `pending` nunca borra); puerta SCM única
  (`Invoke-MYCGuardedScm`) para stop/config/sidtype/description/failure/
  failureflag/auto/start/delete y en el `catch`; hardening sin `/T` (raíz
  primero, "bloquear y luego enumerar"), respaldo SDDL por entrada y borrado
  sin seguir enlaces. Validación: despliegue 263 passed (incluye carreras
  reproducidas con sistema de archivos real para el borrado); DEV-1A/1B 262
  passed, 12 skipped; DEV-0 + conformidad 97 passed, 1 skipped. Residuales:
  TD-062.
- Cuarta ronda de auditoría (2026-09-25, sin commit): SCM re-consultado y
  SID del ledger exigido justo antes de reconfigurar/detener/eliminar;
  uninstall sin ledger es no-op (no toca `backend\.env`); normalización ACL
  elimina Deny explícitos (`/remove:d`); cierre garantizado del handle LSA;
  ejemplos del instalador con `-WinSWExpectedSha256`; config WinSW obsoleta
  eliminada del destino. Validación: despliegue 226 passed; DEV-1A/1B 262
  passed, 12 skipped; DEV-0 + conformidad 97 passed, 1 skipped.
- Tercera ronda de auditoría (2026-09-25, sin commit): propiedad estricta
  del servicio en reinstalación; rollback de `SeServiceLogonRight` como
  único miembro vía LSA (pendiente de validar en Windows); lápida del
  ledger con directorios retenidos; ACE externa exacta + `/grant:r`;
  reinicio de `MYCBackend` como activación controlada (código 3); WinSW
  sólo con SHA-256 de procedencia confiable (**P0 operativo pendiente
  antes de Windows**); recorrido sin `Get-ChildItem -Recurse`; Deny
  explícitos como violación; redacción exacta del manejo del secreto.
  Validación: despliegue 218 passed; DEV-1A/1B 262 passed, 12 skipped;
  DEV-0 + conformidad 97 passed, 1 skipped.
- Segunda ronda de auditoría (2026-09-25, sin commit): propiedad del
  servicio `none|pending|owned` con re-consulta del SCM (ledger esquema 3);
  rechazo de ACE explícitas preexistentes del Broker en repo/venv/Python
  home; rechazo de reparse points antes de operaciones recursivas y en
  rutas externas; reversión verificada de `DEVELOPER_BROKER_ENABLED` en el
  `catch`; código de salida explícito (`Invoke-MYCNativeResult`); limpieza
  de temporales `secedit` en `finally`. Validación: despliegue 179 passed;
  contrato + named pipe + Windows + endpoint 262 passed, 12 skipped; DEV-0
  + conformidad 97 passed, 1 skipped.
- Validación macOS previa a las correcciones (2026-09-25): despliegue
  `test_developer_broker_deployment.py` 109 passed; contrato 102; named
  pipe 146; Windows 12 skipped (no es Windows); endpoint health 14; DEV-0 +
  conformidad 97 passed, 1 skipped; backend completo 1694 passed, 36
  skipped, 1 failed — el fallo es ambiental
  (`test_sat_xls_source.py::…regime_626…`: `backend/resources/sat/catalogo
  sat.xlsx` está en `.gitignore` y no existe en el worktree; con una copia
  temporal del archivo oficial pasa 4/4). `alembic heads` =
  `c4d8e2f1a7b3` (sin migraciones); compileall e import smoke OK; escaneo
  sin ejecución de procesos en el paquete del Broker ni en
  `broker_deploy.py`; `broker.health` única operación; `git diff --check`
  limpio.
- **Pendiente**: ejecutar en Windows real el runbook de
  `architecture/MOBILE_DEVELOPER_BROKER.md` ("Despliegue como servicio
  Windows (DEV-1C)"): preflight, endurecimiento, instalación,
  `Test-MYCDeveloperBroker.ps1`, reinicio de `MYCBackend`, health
  end-to-end desde Mobile, y un ensayo de rollback. Nada de la parte
  Windows de DEV-1C se ha ejecutado.

## DEV-1B — Windows Named Pipe + Broker host (MERGEADO, PR #9)

- `0b9572d` implementación inicial; `6a9374c` corrección de identidad del
  cliente en Windows (`ImpersonateNamedPipeClient`/`RevertToSelf` vía
  `win32security`). Re-ejecución real en Windows de
  `test_developer_broker_windows.py`: **11 passed, 1 skipped, 0 failed** (el
  skip es el rechazo de clientes remotos, que requiere un segundo host).
- PR #9 mergeado; `main` = `05f4c625f5f9cd7620a1a84a543b7f31d787ee27`;
  backend de producción desplegado en ese `main`.
- Implementado: `framing.py`, `pipe_name.py`, `windows_pipe.py`
  (`WindowsNamedPipeTransport`, `NamedPipeBrokerListener`, DACL explícita de
  dos SIDs `0x0012019F`/`0x00100083`, primera instancia exclusiva,
  `PIPE_REJECT_REMOTE_CLIENTS`, identidad del servidor verificada antes de
  escribir, nivel identification, identidad del cliente verificada) y
  `host.py`. Settings `DEVELOPER_BROKER_SERVICE_SID` y
  `DEVELOPER_BROKER_CLIENT_SID`. Dependencia `pywin32==312;
  sys_platform == "win32"`.
- Histórico (no vigente): la primera ejecución real de `0b9572d` dio 5
  passed, 6 failed, 1 skipped por el defecto de módulo pywin32 ya corregido
  en `6a9374c`; detalle en `architecture/MOBILE_DEVELOPER_BROKER.md`
  ("Validación de DEV-1B").

## DEV-1A — Developer Broker boundary (MERGEADO, PR #8)

- Worktree `/Users/saulcortes/Developer/myc_erp-dev1`, rama
  `feat/mobile-developer-shell-broker-dev1`, base `91d7404` (= `origin/main`,
  merge de DEV-0). El checkout estable `myc_erp` (`main`) no se tocó.
- Implementado: paquete `backend/app/developer_broker/` (contrato
  `myc.developer-broker` v1, HMAC-SHA256 canónico con requests y responses
  firmados, anti-replay in-memory acotado, `BrokerServer` con única
  operación `broker.health`, puerto `BrokerTransport` + transporte
  in-memory sólo para pruebas, `BrokerClient`), servicio
  `app/services/developer_broker.py`, configuración opcional
  `DEVELOPER_BROKER_*` (deshabilitada por defecto; el ERP arranca igual) y
  `GET /api/mobile/v1/developer/broker/health` protegido con
  `require_developer_session("developer.system.read")`.
- Pendiente al cierre de DEV-1A (el adapter ya existe en DEV-1B, arriba): adapter Windows Named Pipe + ACL, servicio Windows con
  identidad dedicada (no `LocalSystem`), `ShellSession`. Con el Broker
  habilitado y el transporte `named_pipe`, la ruta falla cerrado (503,
  `named_pipe_adapter_pending`).
- Sin PowerShell, sin ejecución de procesos, sin sockets/puertos, sin
  migraciones (head sigue `c4d8e2f1a7b3`), sin dependencias nuevas.
- Inventario HTTP: 537 operaciones (536 + `broker/health`).
- Validación: `test_developer_broker_contract.py` (73) +
  `test_mobile_developer_broker_health.py` (10) = 83 passed; DEV-0 y
  conformidad (`test_mobile_developer_session.py`, `test_mobile_biometric.py`,
  `test_mobile_security_context.py`, `test_api_access_conformity.py`,
  `test_capability_gate_reconciliation.py`) 97 passed, 1 skipped (PostgreSQL
  real, requiere `LAB_POSTGRES_TEST_URL`); backend completo 1407 passed, 24 skipped, 0 failed
  (baseline antes del cambio: 1324 passed, 24 skipped); `alembic heads` =
  `c4d8e2f1a7b3`.
- Endurecimiento post-auditoría (2026-09-22): ventana temporal half-open
  `(now − 30 s, now + 5 s]` para cerrar el borde replay/freshness; el
  cliente autentica la respuesta antes de interpretarla; contrato exacto
  del resultado `broker.health` (sin campos extra/faltantes, sin `bool`
  como entero, `instance_id` 32 hex); el Control Plane sólo registra
  `exc.code`. Validación tras el endurecimiento: Broker 96 + endpoint 14 = 110 passed;
  DEV-0 + conformidad 97 passed, 1 skipped; backend completo 1434 passed,
  24 skipped, 0 failed; `alembic heads` = `c4d8e2f1a7b3`.
- Detalle: [MOBILE_DEVELOPER_BROKER.md](architecture/MOBILE_DEVELOPER_BROKER.md).

## DEV-0 (contexto previo, fusionado en `main` por PR #7)

## Repositorio y alcance verificado

- Rama de trabajo aislada: `feat/mobile-developer-authority-dev0`, creada
  desde `origin/main` en `c3fc795dbed8c41d600ff95066390967d64fac98` (merge de
  PR #6, que integró `feat/mobile-biometric-login-2` completo: BIOMETRIC-1,
  BIOMETRIC-2 y su endurecimiento posterior).
- Trabajo realizado en un `git worktree` separado
  (`/Users/saulcortes/myc_erp-dev0`), sin tocar el checkout compartido del
  repo principal: la rama `feat/mobile-biometric-login-2` originalmente
  asignada a esta tarea avanzó por otro proceso concurrente
  (`bc316e4 fix(mobile-auth): polish biometric entry and home scroll`, ya en
  `origin`) mientras se exploraba el repo, y el checkout compartido quedó en
  `main`. Se detectó, se reportó y se resolvió trabajando en un worktree
  nuevo en vez de sobrescribir ese trabajo.
- Sin push, merge ni despliegue en este trabajo.
- DEV-0 agrega la autoridad Developer (permisos, `DeveloperSession`,
  desbloqueo biométrico, expiración/revocación, `DeveloperProvider` Mobile,
  pantalla placeholder) sobre BIOMETRIC-2, sin reescribirla: reutiliza
  `resolve_biometric_credential` (extraída de `biometric.py` sin cambiar su
  comportamiento) como única autoridad biométrica. No implementa
  PowerShell, subprocess, shell WebSocket, ejecución SQL, explorador de DB,
  broker de Windows ni el puerto 8765 — todo eso es DEV-1+.
- Endurecimiento 2026-09-22 (worktree sin commit sobre `4685acb`):
  política Developer explícita (`"*"` ya no concede Developer), como máximo
  una `DeveloperSession` activa por dispositivo con supersession
  (`superseded`), binding estricto del token a su `MobileAuthSession`
  (`mobile_session_id`), guard canónico para operaciones DEV-1+
  (`authorize_developer_operation`, no montado) y reconciliación Mobile por
  lifecycle (foreground, entrada al Developer Center, rotación del access
  token, pérdida de capacidad) sin polling.
- Detalle completo: [MOBILE_DEVELOPER_AUTHORITY.md](architecture/MOBILE_DEVELOPER_AUTHORITY.md).

## Base de datos y respaldo

- Revisión inicial local/código: `9970e12e5f0d`, único head (BIOMETRIC-2).
- Migraciones DEV-0: `602a09af6218` (padre `9970e12e5f0d`) y, del
  endurecimiento, `c4d8e2f1a7b3` (padre `602a09af6218`). Head único:
  `c4d8e2f1a7b3`.
- `c4d8e2f1a7b3` es una revisión nueva (no se editó `602a09af6218`, que ya
  está aplicada en la base local `erp_myc`): sanea filas activas duplicadas
  por dispositivo (`superseded`), crea el índice único parcial
  `uq_developer_sessions_active_device (device_id) WHERE revoked_at IS NULL`
  y elimina el UNIQUE redundante `uq_developer_session_token_hash` (queda el
  índice único `ix_developer_sessions_token_hash`, que es lo que declara el
  modelo).
- Verificado en una base PostgreSQL local desechable
  (`myc_dev0_scratch_20260922`, eliminada al terminar): upgrade desde cero,
  saneamiento con duplicados sembrados, rechazo de un segundo activo por el
  índice, downgrade → upgrade, FKs `ON DELETE CASCADE`, y `alembic check` sin
  drift en `developer_sessions`.
- **La base local `erp_myc` NO se migró en este pase**: sigue en
  `602a09af6218`. Pendiente `alembic upgrade head` local cuando se acepte.
- Tabla nueva: `developer_sessions`, con FKs a `users`,
  `mobile_trusted_devices` y `mobile_auth_sessions`, `token_hash` UNIQUE e
  índices de usuario, dispositivo, sesión Mobile, vencimiento y revocación.
- No se modificó ninguna migración histórica (ni BIOMETRIC-1/2 ni
  `602a09af6218`).
- `test_schema_integrity_stage_2a.py::test_current_revision_is_the_single_head`
  en verde: sigue habiendo un único head tras la nueva migración.

## Permisos

Nuevos permisos explícitos en `app/core/permissions.py`, asignados sólo al
rol `Desarrollador`: `developer.access`, `developer.database.read`,
`developer.database.write`, `developer.database.admin`,
`developer.shell.access`, `developer.system.read`, `developer.logs.read`,
`developer.services.execute`, `developer.git.read`.

Política Developer explícita (`app/core/developer_policy.py`,
`myc-mobile/src/permissions/developer-policy.ts`): Developer = actor interno
AND una capacidad Developer exacta (el string exacto de la capacidad, p.ej.
`developer.access`). `"*"` (Administrador) y el wildcard literal
`"developer.*"` ya **no** conceden Developer por sí solos; el riesgo aceptado anterior queda
eliminado. La semántica global de `"*"` en el ERP no cambió
(`user_has_permission` y los guards genéricos intactos). Un Administrador
que necesite infraestructura requiere el rol `Desarrollador` explícito.

## Endpoints nuevos

`POST|GET|DELETE /api/mobile/v1/developer/session`
(`app/routers/mobile_developer.py`), clasificados en el inventario de
acceso HTTP bajo el mismo mecanismo genérico `mobile_context` que el resto
de `/api/mobile/v1/*` (permiso base `mobile.access`); el gate fino de
`developer.access` + actor interno vive en el propio endpoint
(`require_mobile_developer_capability`, política explícita). `GET`/`DELETE`
exigen además el header dedicado `X-MYC-Developer-Token` y sólo reconocen el
token desde la misma `MobileAuthSession` que lo abrió. Sin rutas nuevas
(inventario HTTP: 536 operaciones, sin cambios).

## Validación final (endurecimiento 2026-09-22)

Entorno: venv aislado en el scratchpad de la sesión (el venv del checkout
principal vive en un Desktop sincronizado con iCloud con archivos
`dataless` y colgaba la importación); mismas versiones de paquetes que ese
venv.

- Baseline antes de modificar: backend focalizado 78 passed; backend
  completo 1305 passed, 23 skipped; Mobile 759 passed; `tsc` con los 2
  errores históricos de `realtime-client.ts`; lint sin salida (el warning
  `missing dependency: clearLocal` estaba oculto por `eslint-disable`).
- Backend focalizado (`test_mobile_developer_session.py`,
  `test_mobile_biometric.py`, `test_mobile_security_context.py`,
  `test_api_access_conformity.py`, `test_capability_gate_reconciliation.py`)
  con `LAB_POSTGRES_TEST_URL` apuntando a la base desechable: 98 passed.
  `test_mobile_developer_session.py`: 44 casos (antes 24; se reemplazó
  `test_admin_wildcard_still_grants_developer_access`).
- Backend completo (sin `LAB_POSTGRES_TEST_URL`, igual que el baseline):
  1324 passed, 24 skipped, 0 failed.
- `test_schema_integrity_stage_2a.py::test_current_revision_is_the_single_head`:
  passed; `alembic heads` = `c4d8e2f1a7b3`.
- Mobile completo: 779 passed, 0 failed.
- `npx tsc --noEmit`: exactamente los mismos 2 errores preexistentes en
  `src/realtime/realtime-client.ts` (líneas 205 y 231), ajenos y no tocados.
- `npm run lint`: sin errores ni warnings; `eslint --max-warnings=0` sobre
  los archivos tocados: 0/0, sin `eslint-disable`.
- `git diff --check`: limpio.

## Deuda técnica conocida

- BIOMETRIC-2 (`9970e12e5f0d`) crea el mismo par redundante UNIQUE
  constraint + índice único en `mobile_biometric_credentials.credential_hash`
  (`alembic check` lo reporta como drift). No se tocó por restricción de no
  modificar BIOMETRIC-1/2.
- Una rotación de refresh Mobile termina la `DeveloperSession` (binding por
  generación de `MobileAuthSession`). Con access tokens de 8 h y Developer de
  10 min es infrecuente; el cliente lo reconcilia al cambiar el access token.
- La reconciliación Mobile es fail-closed: un error de red al volver a
  foreground bloquea Developer localmente.

## Validación del corte DEV-0 original (2026-09-21)

- Backend focalizado: `test_mobile_developer_session.py` (24 passed),
  `test_mobile_biometric.py` + `test_mobile_security_context.py` +
  `test_api_access_conformity.py` + `test_capability_gate_reconciliation.py`
  (78 passed en conjunto).
- Backend completo: 1305 passed, 0 failed, 23 skipped (incluye el recurso
  oficial `catalogo sat.xlsx`, ignorado por Git y copiado manualmente a este
  worktree aislado sólo para poder correr la suite completa localmente; no
  es parte de este cambio).
- Mobile focalizado de DEV-0: 27 passed (`DeveloperProvider.test.ts`,
  `technician-home.developer-card.wiring.test.ts`,
  `developer-screen.wiring.test.ts` y el bloque nuevo de
  `mobile-capabilities.test.ts`).
- Mobile completo: 759 passed (antes 732 en el corte BIOMETRIC-2 tras su
  endurecimiento).
- `npx tsc --noEmit`: mismos 2 errores preexistentes en
  `realtime-client.ts`, ajenos a este trabajo y no tocados.
- `npm run lint`: exit 0, sin errores.
- Inventario API regenerado: 536 operaciones (533 + 3 nuevas de
  `/mobile/v1/developer/session`); `docs/architecture/security/API_ENDPOINT_INVENTORY_2026-08-03.csv`
  actualizado y coincide byte a byte con el runtime
  (`test_committed_inventory_matches_runtime`).
- `git diff --check` sin errores.
- Revisado: sin credenciales, tokens Developer, credenciales biométricas,
  perfiles de aprovisionamiento ni artefactos de build en el commit.

## Pendientes y límites

- Resuelto en el endurecimiento 2026-09-22: la política canónica explícita
  "actor interno + capability Developer explícita" ya está implementada;
  `"*"` por sí solo no abre Developer.
- DEV-0 NO está cerrado: pendiente auditoría humana final, commit, merge y
  `alembic upgrade head` en la base local `erp_myc`.
- Invariante para DEV-1+: toda operación privilegiada debe pasar por
  `authorize_developer_operation`/`require_developer_session(capability)`
  (DeveloperSession viva + capacidad granular); nunca confiar en
  `isDeveloperUnlocked` del cliente.
- DEV-1+ (fuera de alcance de esta fase): Shell Broker
  (`MYCDeveloperBroker`) como servicio Windows separado con identidad
  dedicada, `ShellSession` persistente con grace period de 15 minutos,
  Database Console, Logs, Services, Git — contrato de lifecycle ya
  documentado en `architecture/MOBILE_DEVELOPER_AUTHORITY.md` para que DEV-1
  no tenga que re-derivarlo.
- El estado global y pendientes ajenos a esta entrega permanecen bajo
  `project/PROJECT_STATUS.md` y `project/TECHNICAL_DEBT.md`.

## Facturación: emisión en Producción y PDF de borrador (sin commit)

- `issue_invoice` ya no bloquea `FACTURAMA_ENVIRONMENT=production`; persiste el
  ambiente real antes de llamar al PAC y `_mark_issued`/auditoría lo conservan.
- `reconcile_invoice` falla con `facturama_environment_mismatch` (409, sin
  peticiones ni cambios) si el ambiente persistido (NULL = sandbox legado) no
  coincide con `FacturamaClient.environment`.
- PDF institucional: el receptor se lee del `fiscal_snapshot`; un borrador se
  presenta como «BORRADOR · SIN TIMBRAR» sin QR/sellos/cadena.
- UI: «Generar CFDI» / «Generando CFDI…». Sin migraciones.
- Validaciones: tests backend de Facturama/facturas y `node --test` focal.
- Pendiente: validar en Producción real con un CFDI controlado (no ejecutado).

## EMAIL-1: infraestructura institucional de correo (sin commit)

- Nuevo subsistema `backend/app/services/email/` (catálogo de plantillas,
  renderer, `SmtpTransport`, `send_email`/`preview_email`/`retry_delivery`),
  modelos `EmailTemplate`/`EmailDelivery`, router `/api/email` (7 operaciones;
  inventario API 558) y permisos `email.*`, `quotations.email.send`,
  `invoices.email.send`.
- Migración `a1c4e7b9d2f6` (down `e8f1a3c5d7b9`), único head: tablas
  `email_templates` y `email_deliveries`. Pendiente aplicar `alembic upgrade head`
  en la base local; el respaldo SQL no se regeneró.
- Portal: `mail_service.py` es adapter hacia `EmailService`; `development_outbox`
  sólo en no producción. Config nueva: `EMAIL_*`, `SMTP_*`, `PORTAL_PUBLIC_BASE_URL`.
- Pendientes: EMAIL-2/3/4, UI de plantillas, validar `billing_emails` (TD-EMAIL-1),
  probar el relay real de Google Workspace en despliegue.

## EMAIL-2: recuperación de contraseña (sin commit)

- `POST /api/auth/forgot-password` y `/reset-password` (públicos; inventario API 560),
  `PasswordResetToken`, `users.auth_version` y migración `b2d5f8a1c3e7`
  (down `a1c4e7b9d2f6`, único head). Pendiente `alembic upgrade head` local.
- Reset: token hash SHA-256, TTL 30 min, one-shot atómico; incrementa
  `auth_version`, revoca sesiones Mobile y biometría (no dispositivos de
  confianza). Frontend `/forgot-password` y `/reset-password`.
- Config: `PUBLIC_APP_BASE_URL` (fallback `PORTAL_PUBLIC_BASE_URL`),
  `PASSWORD_RESET_EXPIRE_MINUTES`, `PASSWORD_RESET_COOLDOWN_SECONDS`.
- Pendientes: rate limit anónimo/IP (TD-EMAIL-2), `auth_version` en otros
  cambios de credencial, definir `PUBLIC_APP_BASE_URL` en despliegue.

## EMAIL-3: contactos de cliente y correo de cotizaciones (sin commit)

- Endpoints `/api/clients/{id}/contacts` (5) y `/api/quotations/{id}/email/{preview,send,deliveries}` (3);
  inventario API 568. `Quotation.contact_id` y migración `c3e6a9b2d4f8`
  (down `b2d5f8a1c3e7`, único head). Pendiente `alembic upgrade head` local.
- Frontend: pestaña Contactos del cliente, selector de contacto principal,
  modal "Enviar por correo" y pestaña Correos en la cotización.
- El envío por correo no cambia `quotation.status`. Pendientes: EMAIL-4 (facturas),
  TD-EMAIL-3 (PDF histórico), UI de plantillas.

## Autoridades documentales

`project/DOCUMENTATION_INDEX.md` rige la jerarquía. La autoridad Developer
está en `architecture/MOBILE_DEVELOPER_AUTHORITY.md`; el contrato de sesión
y biometría Mobile permanece en `architecture/MOBILE_SECURITY_CONTEXT.md`,
sin cambios en esta fase. Inventario en `PROJECT_FILE_REGISTRY.md`. Los
cortes anteriores permanecen trazables en Git.
