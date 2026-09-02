> Estado: VIGENTE
>
> Corte verificado: 2026-09-01
>
> Autoridad: contrato documental PDF de Hojas de Campo ERP y LAB

# Renderer PDF versionado de Hojas de Campo

`backend/app/services/field_sheet_pdfs.py` es la única autoridad para generar
PDF de `FieldSheet`, tanto productiva como LAB. Mobile no genera documentos.

Toda FieldSheet nueva congela su definición y versión de plantilla y fija
`pdf_renderer_key=field_sheet_engine` con `pdf_renderer_version=1`. El renderer
canónico usa `field_sheet_engine_pdf.html` y compone por `blocks` ordenados por
`print_order`, respetando visibilidad, campos/labels, secciones, columnas,
familia de tabla, títulos, unidades, código/revisión, firmas y metadata de
layout de `template_definition_json`.

Los templates `field_sheet_general_pdf.html`,
`field_sheet_anemometer_pdf.html` y `field_sheet_electrical_pdf.html` quedan
permitidos únicamente mediante claves `legacy:<archivo>` versión 1. No se
reescribe `template_key` ni `template_definition_json` histórico.

`completed`, `under_review` y `approved` son estados documentales finales para
este contrato. Al completar se genera una vez el PDF mediante WeasyPrint, se
publica atómicamente con `storage_service.save_validated_content` y se
persisten ruta relativa, SHA-256, renderer/versión, versión de definición y
fecha. Una descarga posterior lee el archivo protegido y verifica su SHA-256;
si falta o difiere se rechaza y nunca se regenera silenciosamente. Borradores y
hojas `in_progress` conservan preview dinámico.

La migración `b71d4a9f2c18` agrega el contrato persistente y clasifica los
registros existentes por su `pdf_template` sin alterar sus snapshots. Sólo
asigna `field_sheet_engine`/`legacy:<archivo>` versión 1 cuando el snapshot
histórico lo indica sin ambigüedad; el resto queda `NULL`/`NULL` en vez de
reinterpretarse por descarte. `resolve_field_sheet_pdf_renderer()` refleja lo
mismo: una FieldSheet histórica sin renderer inferible devuelve conflicto
(`409`) en vez de asumir el motor canónico.

Fase 6 agrega revisión/versionado a `FieldSheet` LAB (ver
`LAB_WORK_ORDERS.md`) sin tocar este contrato: cada revisión es su propia
fila con su propio `pdf_renderer_key`/`pdf_renderer_version`/
`final_pdf_path`/`final_pdf_sha256`, congelados independientemente al
completarse. Una revisión retirada (`is_current=False`) conserva su PDF
final exactamente como quedó -- nunca se regenera ni se reasigna a la
revisión vigente.
