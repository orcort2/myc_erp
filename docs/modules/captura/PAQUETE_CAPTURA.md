> Estado: VIGENTE
>
> Tipo: Arquitectura vigente
>
> Autoridad: Alta para el contrato del Paquete de Captura
>
> Prevalece sobre: descripciones históricas de elegibilidad y estructura de carpetas del paquete
>
> Estado del módulo: `../../project/PROJECT_STATUS.md`
>
> Corte verificado: 2026-08-25

# Paquete de Captura

La descarga real del ETS `OSMYC-26-07-0001` fue validada el 2026-07-21 tanto directamente contra el servicio como mediante los endpoints HTTP autenticados de diagnóstico y ZIP. Ambos respondieron correctamente y produjeron la jerarquía institucional descrita en este documento.

## Propósito y flujo

El paquete entrega, por equipo elegible, el PDF de la Hoja de Campo y el XLSX Master congelado en el equipo. La selección y el diagnóstico son exclusivamente backend.

La consulta y descarga son operaciones de sólo lectura: no cambian estados ni sobrescriben el nombre snapshot histórico. La carga posterior reconoce tanto el nombre histórico persistido como `Master_{folio}.xlsx`.

```text
capturar y guardar hoja
→ completar hoja
→ opcionalmente enviar a Captura (`under_review`)
→ consultar diagnóstico
→ descargar paquete ETS u OT
→ Captura sustituye fuera del ERP el Master genérico por el técnico real dentro del mismo bonche
→ subir nuevamente el ZIP/Master devuelto
→ identificar de forma única certificado/equipo y Master registrado
→ persistir identificación y validaciones
→ iniciar `capture_in_progress`
→ refrescar ETS, contadores y tarjetas
→ habilitar envío cuando el Master está identificado y sin diferencias bloqueantes
→ enviar `capture_in_progress → quality_review`
→ Calidad descarga y revisa el XLSX
```

Generar o descargar el PDF no completa la hoja ni sustituye la transición persistida.

## Carga y persistencia del Master devuelto

Cada Excel procesado crea una fila en `certificate_capture_files` con certificado/ETS, nombre original, ruta única basada en el ID, estado `identified`/`unidentified`, resultados JSON, actor y fechas. Un Master identificado inicia la transición vigente del certificado a `capture_in_progress`, conserva `capture_started_at`/`capture_started_by_id` y escribe `certificate.capture_started` en auditoría. No modifica `match_status`: es metadato legacy y no es compuerta de autenticación.

En Verificación, el ZIP descargado contiene el Master genérico congelado por el
concepto. Captura puede reemplazar ese miembro sin cambiar el bonche. Al volver
a cargarlo, el backend busca una coincidencia única entre los Masters activos
registrados estructuralmente como `service_type=verification` —interpretación
documental aprobada de la misma versión o perfil técnico activo—, congela ese
documento/versión como Master final del equipo y audita
`selection_source=capture_upload_fingerprint`. Una coincidencia ambigua o
inexistente no crea una identidad nueva ni consulta nombre, código o
descripción.

La búsqueda institucional anterior sólo se ejecuta cuando el equipo conserva
`initial_certificate_master_document_id` y aún no tiene
`final_certificate_master_document_id`. Si ya existe Master final, su documento,
versión y ruta snapshot son autoridad histórica aunque cambien revisiones,
perfiles, interpretaciones o Masters activos. La carga se valida contra ese
snapshot; no lo sustituye. Repetir el mismo Master final no agrega historial ni
auditoría y cualquier intento A→B se rechaza antes de consultar evidencia de
Captura.

La respuesta incluye totales de identificados, no identificados, auxiliares ignorados, advertencias y diferencias. El frontend conserva ese resultado visible, vuelve a consultar certificados y archivos de Captura, actualiza los contadores y muestra en cada tarjeta el estado y las alertas del último Master identificado. `._*`, `.DS_Store` y cualquier contenido dentro de `__MACOSX/` se ignoran antes de persistir y no afectan estadísticas.

## Readiness para Calidad

La fuente canónica es `capture_master_readiness` del backend. Un certificado puede enviarse cuando existe el snapshot del Master esperado, existe un `certificate_capture_files` identificado para ese certificado y sus resultados no contienen `mismatch` ni `no_coincide`. `no_encontrado` se presenta como advertencia no bloqueante.

Las dos superficies de Captura consumen esa misma fuente. La vista del ETS no debe reconstruir la existencia del snapshot desde `EquipmentRead`, porque ese contrato público no expone `certificate_template_path_snapshot`; hacerlo produjo un falso “No existe un Master esperado” aunque el backend respondía `ready=true`. Desde la corrección del 2026-07-21, el ETS consulta `GET /certificates/capture-master-readiness?service_order_id={id}` junto con los archivos y usa ese resultado para métricas, tarjeta, Calidad y habilitación del botón.

```text
identified + warnings + 0 mismatches → listo
sin identificado → bloqueado
mismatch/no_coincide → bloqueado
```

`send_to_quality` no exige `final_pdf_path` y no modifica `match_status`. Persiste actor/fecha y audita `capture_in_progress → quality_review` con ID y nombre del Master. Para cargas históricas ya identificadas que aún estén `capture_pending`, la misma acción registra primero `capture_pending → capture_in_progress` y después la transición a Calidad, dentro de la misma transacción. No existe actualmente una acción masiva por OT/ETS; el envío implementado es individual y la lista de readiness permite verificar cualquier alcance sin enviar elementos incompletos.

Captura ya no muestra carga individual/masiva de PDF, contadores PDF ni matching PDF–Excel. Calidad consulta advertencias/diferencias y descarga el XLSX mediante `GET /certificates/{id}/capture-master`; aprobar el Master tampoco exige PDF ni cambia `match_status`.

## Continuación Calidad → Autenticación

La aprobación persiste `quality_review → quality_approved`. A partir de ese estado, Autenticar usa el Master identificado más reciente como fuente, genera el PDF final mediante el conversor de oficina configurado, excluye hojas auxiliares sin área de impresión, aplica el sello/código/QR vigente y persiste `authenticated`, actor, fecha, versiones y auditoría con ID/nombre del Master. No exige `final_pdf_path` previo ni consulta `match_status`. El Master original permanece intacto.

En el caso real del certificado `1`, la consulta HTTP autenticada devolvió un Master esperado e identificado, tres advertencias persistidas por el parser anterior, cero diferencias y `ready=true`. La descarga autenticada del Master devolvió `200`, MIME XLSX, `Master_MYCA-07-2026-0001.xlsx` y 210,173 bytes, por lo que el mismo documento queda disponible para la revisión de Calidad. Los diagnósticos históricos no se reescriben; una nueva carga usa el detector vigente descrito abajo.

## Diagnóstico de validaciones del caso real

Los campos ordinarios continúan buscando sus valores esperados en el contenido del libro. `servicio` es la excepción semántica: ya no busca `accredited_iso_17025` ni una leyenda documental. Para Calibración compara contra el snapshot congelado y traduce el alcance ERP a `accredited` o `traceable`; para Verificación compara primero contra el registro estructurado de Masters de Verificación y, tras la coincidencia única, valida contra el nuevo snapshot final como `verification`.

El fingerprint combina ocho indicadores: nombres de hojas, dimensiones, rangos fusionados, distribución de celdas con estilo, posiciones de fórmulas, etiquetas con coordenada, anclajes de imágenes/logotipos y áreas de impresión. Exige umbral `0.72`, coincidencia de hojas/dimensiones y al menos tres grupos estructurales con evidencia; ninguna frase aislada decide la clasificación.

Para `Master_MYCA-07-2026-0001.xlsx` se comprobó:

- `cliente`: el ERP espera `LEONARDO AGUILAR LERMA`, pero el libro contiene `LAVATELCHOCHO`; es una diferencia real de contenido.
- `proxima_calibracion`: el ERP espera `2027-09-28`, mientras la fórmula/caché de `J33` contiene `2027-07-28`; es una diferencia real de fecha.
- `servicio`: esperado `accredited`, detectado `accredited`, `coincide`; score estructural `0.8511`, cinco grupos de evidencia y cero diferencias bloqueantes. Cambiar la leyenda/número de acreditación no impide reconocer la plantilla en la prueba automatizada.

La comparación estructural está centralizada en `backend/app/services/master_template_fingerprints.py` y la orquestación del retorno en `capture_packages.py`. Una plantilla futura no requiere una rama por nombre: Calibración la congela con su `calibration_scope`; Verificación la registra explícitamente con `service_type=verification`. No existe un Master trazable ni un Master específico institucional de Verificación real en el repositorio actual, por lo que ambos recorridos conservan pendiente la validación física con sus primeros archivos oficiales.

## Estados elegibles de Hoja de Campo

El paquete reconoce los estados vigentes que representan una hoja técnicamente terminada:

- `completed`: completada por el técnico.
- `under_review`: enviada a Captura/revisión documental.
- `approved`: aprobada, conservada por compatibilidad del flujo vigente.

`draft`, `in_progress`, `rejected`, `returned_to_technician` y `cancelled` no son elegibles.

## Condiciones acumulativas de elegibilidad

1. El equipo está activo, pertenece al ETS/OT consultado y su partida es `calibration` con `calibration_scope`, o `verification` con alcance nulo.
2. Existe una Hoja de Campo activa asociada al equipo.
3. Su estado pertenece a `completed`, `under_review` o `approved`.
4. Existe certificado activo con `expected_folio` o `folio`.
5. El equipo tiene nombre e identificación interna.
6. La hoja tiene fecha de próxima calibración.
7. El equipo conserva `certificate_master_document_id`, `certificate_master_version_id` y ruta snapshot.
8. Documento y versión Master están activos; la versión no está caducada.
9. El archivo snapshot existe, es `.xlsx` y su SHA-256 coincide cuando existe checksum congelado.
10. El PDF de la Hoja de Campo puede generarse correctamente.

Firmas `Revisó` y `Elaboró informe` no son condiciones del paquete. Tampoco se vuelven a validar allí los campos técnicos: la transición `complete` ya exige condición inicial/final, campos requeridos por plantilla, observaciones o evidencia y al menos un resultado estructurado.

## Diagnóstico

`package_summary` agrupa equipos por OT:

- `ready`: cantidad que cumple todas las condiciones.
- `pending`: cantidad bloqueada.
- `blocked`: equipo y primera razón de bloqueo encontrada.
- `ready_total`: suma de `ready` de todas las OT activas.

La lógica reside en `backend/app/services/capture_packages.py`: `_load_equipment`, `eligibility_for_equipment`, `_eligible_with_pdf` y `package_summary`.

## Estructura del ZIP ETS

```text
FOLIO_ETS/
└── OT-####/
    └── FOLIO_CERTIFICADO/
        ├── Hoja_Campo_FOLIO_CERTIFICADO.pdf
        └── Master_FOLIO_CERTIFICADO.xlsx
```

Caso verificado:

```text
OSMYC-26-07-0001/
└── OT-7002/
    └── MYCA-07-2026-0001/
        ├── Hoja_Campo_MYCA-07-2026-0001.pdf
        └── Master_MYCA-07-2026-0001.xlsx
```

## Incidencia corregida el 2026-07-21

La hoja `1` pasó de `in_progress` a `completed` y luego a `under_review`. El diagnóstico sólo aceptaba literalmente `completed`, aunque frontend, motor operativo y preparación de certificados ya trataban `under_review`/`approved` como hojas terminadas. Se alineó la elegibilidad con ese contrato sin omitir campos, firmas, Master, snapshot, hash ni generación PDF.

Validación real: `ready=1`, `pending=0`, `blocked=[]`, `ready_total=1`; ZIP de 364,648 bytes con los dos miembros esperados. La descarga no creó auditoría ni cambió el snapshot histórico.

La carga real se reprodujo dentro de una transacción reversible: creó una fila identificada con ruta única, conservó las tres advertencias, ignoró dos auxiliares macOS, cambió temporalmente el certificado `capture_pending → capture_in_progress` con actor `1` y auditoría, y dejó la base histórica sin cambios después del rollback de prueba.

El caso real posterior quedó en `capture_in_progress` con Master `8`: readiness `true`, tres advertencias y cero diferencias. Un envío reversible creó `certificate.sent_to_quality`, actor `1`, fecha, referencia al Master y estado `quality_review`; el XLSX asociado existe con 210,173 bytes y la base volvió al estado previo tras el rollback.
