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

## Revisiones, reapertura y PDF

Una reapertura `preserve` mantiene la revisión vigente. Una reapertura
`invalidate` seguida de un cambio técnico crítico retira la revisión completed
como `is_current=false`, sin cambiar su estado, ruta o SHA; la recaptura crea
N+1 con `supersedes_field_sheet_id=N.id`. Cada revisión completed conserva su
propio PDF final. Descargar dos veces la misma revisión devuelve los mismos
bytes y SHA-256.

## Validaciones reproducibles

- Backend focal: 93 passed, 8 skipped.
- Mobile focal Fase 6: 73 passed.
- TypeScript: correcto.
- Expo lint: correcto.
- PostgreSQL desechable: `b71d4a9f2c18 → d7c297902425 → b71d4a9f2c18 →
  d7c297902425 → head`, correcto; head `d7c297902425`.
- PostgreSQL aceptó revisión 1 histórica + revisión 2 vigente y rechazó una
  segunda vigente mediante `uq_field_sheets_current_lab_equipment`.
- QA familias: `general` (`direct_comparison`) y `manometro` (`pressure`)
  completaron prefill, captura, guardado, finalización, congelamiento y doble
  descarga idéntica.

Las cifras de suite completa, export Expo y gates finales se registran en
`docs/BACKUP_ESTADO_ACTUAL.md` al finalizar el trabajo.

## Limitaciones deliberadas

- No se inventó contenido para las 11 claves prototipo unsupported.
- Los seis cuerpos prototipo incompatibles requieren decisión documental y
  metrológica humana antes de promoverse.
- El cierre de esta fase técnica no convierte el módulo global de Hojas de
  Campo ni el vertical LAB completo en `SELLADO`: continúan la aceptación
  física iOS/Android y la deuda metrológica transversal registrada.
