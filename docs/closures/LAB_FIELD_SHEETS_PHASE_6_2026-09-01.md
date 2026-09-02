> Estado: CIERRE TÉCNICO VALIDADO
>
> Fecha: 2026-09-01
>
> Alcance: Fase 6 — normalización e integración del Motor de Hojas de Campo LAB

# Cierre técnico Fase 6 — Hojas de Campo LAB

## Resultado

La Fase 6 queda cerrada técnicamente sobre el vertical temporal LAB. Backend es
la única autoridad de plantilla, revisión, persistencia, validación y PDF;
Mobile renderiza el snapshot declarativo y no contiene ramas por instrumento.
No se conectó LAB con ETS, Calidad, Certificados ni otra entidad productiva, y
no se agregó UI LAB operativa a `frontend/**`.

## Arquitectura final

```text
LabWorkOrderEquipment
→ current_field_sheet (is_current=true, única por índice parcial)
→ template_definition_json congelado
→ captura Mobile declarativa
→ resultados estructurados
→ PDF backend versionado
→ final_pdf_path + final_pdf_sha256 inmutables
→ historial N / recaptura N+1
```

`LabWorkOrderEquipment.field_sheets` conserva todo el historial y
`current_field_sheet` es una relación ORM filtrada, read-only y cargable de
forma explícita. El alias compatible `field_sheet` ya no selecciona sobre una
colección que pudiera no estar cargada. PostgreSQL impide dos revisiones
`is_current=true` para el mismo equipo.

## Catálogo y snapshot

El catálogo operativo es el conjunto de 30 claves resolubles por
`TEMPLATE_BLOCK_ASSIGNMENTS`. Las 11 claves exclusivas del prototipo permanecen
no operativas y producen 422; no existe fallback a `general`. Los aliases
legacy se conservan sin agregar equivalencias. Una vez creada la hoja, Mobile,
validación y PDF consumen `template_definition_json`; cambiar el catálogo no
reinterpreta una hoja persistida.

El detalle completo de claves, aliases, familias y deuda humana está en
`docs/architecture/FIELD_SHEET_TEMPLATE_INVENTORY_PHASE_6.md`.

## Captura Mobile y bandeja

`FieldSheetResultsWorkspace` conserva edición local, filas dinámicas, progreso,
scroll horizontal, adaptación portrait/landscape y read-only para completadas.
“Guardar y salir” ahora cierra sólo si `onSave` confirma éxito; un fallo deja el
workspace abierto, mantiene los valores dirty, muestra el error y permite
reintentar.

`GET /api/mobile/v1/technician/lab-field-sheets` entrega una página agregada
con OT, equipo, cliente documental, hoja vigente, plantilla, revisión,
progreso y bucket. La consulta usa únicamente `is_current=true`; Mobile hace
una sola llamada y navega a Mesa Técnica con `workOrderId`, sin duplicar la
captura ni hacer fan-out por OT/equipo.

### Scope de acceso del tray (validado)

`get_lab_field_sheet_tray` está gateado por
`require_internal_mobile_permission("field_sheets.read")`
([mobile_technician.py](../../backend/app/routers/mobile_technician.py)), el
mismo guard interno-only que el resto de `mobile_technician.py`. Ese guard ya
exige `actor_type == "internal"` antes de resolver el permiso, así que un
actor `client`/portal externo nunca alcanza el servicio: recibe 403
(`"Esta capacidad es exclusiva de staff MYC"`), no una lista vacía o
filtrada. Por eso `context.client_id` es siempre `None` para quien entra a
este endpoint.

El servicio pasa ese `None` como `operator_client_id` a
`list_lab_field_sheet_tray`
([lab_field_sheets.py](../../backend/app/services/lab_field_sheets.py)), que
es exactamente el mismo resolver que usan `create_lab_work_order` y
`list_lab_work_orders` en `lab_work_orders.py` (`operator_client_id=context.client_id`).
No se inventó una segunda política de seguridad para el tray. `None` es
**scope interno global deliberado**: LAB no modela un concepto de "hoja de
campo asignada a un técnico" — cualquier staff interno con
`field_sheets.read` ve toda la bandeja, sin filtrar por creador ni por
asignación individual. Un `operator_client_id` no nulo sólo ocurre para
actores externos con organización cliente propia, que en este endpoint
específico nunca llegan a evaluarse porque el guard los rechaza antes.

Cobertura de test:
- `test_lab_field_sheet_tray_is_aggregated_paginated_and_permission_guarded`
  ([test_lab_phase6_field_sheet_revisions.py](../../backend/tests/test_lab_phase6_field_sheet_revisions.py))
  prueba que un actor interno sin el permiso `field_sheets.read` recibe 403.
- `test_external_actor_cannot_reach_lab_field_sheet_tray`
  ([test_mobile_security_context.py](../../backend/tests/test_mobile_security_context.py))
  prueba que un actor `client`/portal externo autenticado recibe 403 antes de
  llegar al resolver de scope.

## Revisiones, reapertura y PDF

Una reapertura `preserve` mantiene la revisión vigente. Una reapertura
`invalidate` seguida de un cambio técnico crítico retira la revisión completed
como `is_current=false`, sin cambiar su estado, ruta o SHA; la recaptura crea
N+1 con `supersedes_field_sheet_id=N.id`. Cada revisión completed conserva su
propio PDF final. Descargar dos veces la misma revisión devuelve los mismos
bytes y SHA-256.

## Validaciones reproducibles

- Backend focal (FieldSheet/LAB + seguridad Mobile, 10 archivos): `256 passed,
  8 skipped`.
- Backend suite completa: `852 passed, 8 skipped, 2 failed`. Las 2 fallas son
  `test_api_access_conformity.py` (deuda preexistente de inventario de
  endpoints, ya registrada como pendiente separado antes de esta fase;
  confirmada como preexistente vía `git stash` contra `92e5ffb` — falla
  idéntica sin los cambios de este cierre). No está relacionada con
  FieldSheets/LAB ni con el tray.
- Mobile suite completa (`npx tsx --test` sobre los 23 archivos `*.test.ts`
  bajo `src/`): `207 passed, 0 failed`.
- TypeScript (`npx tsc --noEmit`): correcto, sin errores.
- Expo lint (`npm run lint`): correcto, sin errores.
- Expo export iOS (`npx expo export --platform ios`): correcto.
- Expo export Android (`npx expo export --platform android`): correcto.
- Expo export web (`npx expo export --platform web`): correcto, 36 rutas
  estáticas.
- `git diff --check`: sin errores de espacio en blanco.
- PostgreSQL desechable: `upgrade head` correcto desde cero, `current =
  d7c297902425 (head)`, `alembic check` → "No new upgrade operations
  detected."; ciclo `downgrade b71d4a9f2c18 → upgrade head` correcto. Base
  desechable eliminada al terminar; la base `erp_myc` real no fue tocada.
- PostgreSQL aceptó revisión 1 histórica + revisión 2 vigente y rechazó una
  segunda vigente mediante `uq_field_sheets_current_lab_equipment` (Fase 6
  original, no repetido en este cierre).
- QA familias: `general` (`direct_comparison`) y `manometro` (`pressure`)
  completaron prefill, captura, guardado, finalización, congelamiento y doble
  descarga idéntica (Fase 6 original, no repetido en este cierre).

Las cifras de suite completa, export Expo y gates finales se sincronizan en
`docs/BACKUP_ESTADO_ACTUAL.md`.

## Limitaciones deliberadas

- No se inventó contenido para las 11 claves prototipo unsupported.
- Los seis cuerpos prototipo incompatibles requieren decisión documental y
  metrológica humana antes de promoverse.
- El cierre de esta fase técnica no convierte el módulo global de Hojas de
  Campo ni el vertical LAB completo en `SELLADO`: continúan la aceptación
  física iOS/Android y la deuda metrológica transversal registrada.
- La deuda de conformidad del inventario de endpoints
  (`test_api_access_conformity.py`, csv committed vs. runtime) permanece sin
  resolver deliberadamente: es preexistente a este cierre, no la introdujo ni
  la agranda el tray de FieldSheets, y su alcance (regenerar/auditar ~500
  endpoints del ERP completo) excede Fase 6 LAB. Queda como pendiente
  separado, no como bug de este cierre.
