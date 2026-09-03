> Estado: VIGENTE
>
> Corte verificado: 2026-09-02
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

## DSL estructural vigente (Fases 4 y 5)

`ResultSection` conserva `key`, `title`, `rows` y `columns`, y puede declarar
`header_rows`, `row_labels`, `layout.row_number_width`, `repeat_header`,
`break_inside` y `page_break_before`. Cada celda de header admite `label`,
`column_key` opcional, `colspan`, `rowspan`, `alignment`, `width` y `metadata`.
El backend valida spans positivos, claves reales o `__row_number__`, cobertura
completa de la matriz, ausencia de overlap y que cada `column_key` esté ubicado
en su posición física lógica (`__row_number__` en la columna 0 y las columnas
de resultados en el orden declarado). Si `header_rows` no existe o está vacío,
el renderer conserva el header plano histórico.

La geometría vive exclusivamente en el snapshot declarativo. `FieldSheetResult`
continúa persistiendo sólo `id`, `section_key`, `row_number` y `row_data`;
`row_labels` cambia la presentación de la identidad técnica, no la identidad.

`print_layout` tipa página (`letter|a4`, `portrait|landscape`, márgenes en mm),
visibilidad documental y número de columnas del grid. Cada bloque tipa orden,
span, grid de campos, título, modo compacto, borde, espacios, cortes de página,
posición de label y ocultamiento de campos vacíos. Cada campo puede ajustar su
span y su label `top|inline`. No admite HTML, CSS, Jinja, URLs, scripts, paths ni
propiedades desconocidas; las únicas longitudes de tablas permitidas usan
unidades allowlisted.

`signature_layout` es un contrato tipado. Conserva los slots históricos y
admite `columns` entre 1 y 4, `direction=horizontal|vertical` y
`trailing_fields`. Cuando `columns` no se declara, el renderer deriva el número
de columnas del total de firmas, reproduciendo el comportamiento horizontal
anterior; `direction` usa `horizontal` y `trailing_fields` queda vacío por
default. Los campos posteriores se limitan a claves allowlisted (actualmente
`purchase_order_or_quotation`), y Python resuelve su label y valor mediante las
mismas autoridades que cualquier otro campo antes de entregar datos limpios a
Jinja. Claves o propiedades desconocidas responden 422 en definiciones nuevas.
Los snapshots históricos sin estas propiedades no se reescriben.

La identidad visual se resuelve en Python mediante
`ORGANIZATION_PRINT_PROFILES`. Existen perfiles `myc` y `capymet`; MYC reutiliza
el logo y contacto institucional vigentes. CAPYMET usa nombre legal/visible
CAPYMET, no hereda dirección, teléfono, correo ni logo de MYC y mantiene esos
datos vacíos hasta contar con configuración real; por ahora usa encabezado
textual sin inventar un asset. El mismo `field_sheet_engine_pdf.html` consume
ambos perfiles y todas las geometrías, sin branches por template, magnitud o
instrumento.

Mobile calcula una matriz lógica de posiciones para `header_rows` y renderiza
cada celda con `row`, `column`, `colspan` y `rowspan` sobre un contenedor de
altura exacta. Un header de dos filas con celdas `rowspan=2` ocupa dos filas
reales, sin filas espaciadoras; el `ScrollView` horizontal se conserva.

Se conserva `CANONICAL_PDF_RENDERER_VERSION = 1`: los defaults nuevos equivalen
al comportamiento anterior (Letter portrait, márgenes 12/10/14/10, header,
título, footer y grid documental de una columna; los bloques conservan grid de
dos columnas, borde/título visibles y `break-inside: avoid`; `break-auto`
permite la excepción declarada). Los headers planos también se preservan. La
interpretación avanzada sólo se activa cuando el snapshot declara sus
propiedades, por lo que no cambia el significado material de snapshots v1
históricos ni sus PDFs ya congelados.

La micro-extensión de Fase 6A.1 no cambia el renderer versionado: permite que
un `SignaturesBlock` use una o varias columnas, flujo vertical/horizontal y
campos posteriores seguros dentro del mismo bloque. Las definiciones oficiales
MYC de Temperatura (FCA-30 `R-1`) y Presión (FCA-30 `R1`) ya la consumen con
tres firmas verticales y `purchase_order_or_quotation`; sus tablas agrupadas y
composición tabla|firmas se expresan sólo mediante `header_rows`,
`print_layout` y `signature_layout`. `field_sheet_engine_pdf.html` continúa
siendo el único renderer y los snapshots históricos no se reinterpretan.

## Acabado visual global de impresión

El renderer canónico aplica el mismo estándar a toda hoja nueva, sin ramas por
template, magnitud o equipo:

- radio exterior de `1.2mm` en controles y bloques con borde;
- las tablas usan `.results-frame` con borde/radio/recorte, mientras la tabla
  interna usa bordes separados y omite sus extremos para evitar duplicación;
- `.field-cell` usa altura mínima `7.6mm`, padding `1.1mm 1.4mm` y line-height
  `1.2`; en modo compacto conserva `6.8mm` y padding `.95mm 1.2mm`;
- label usa line-height `1.15` y separación inferior `.45mm`; los campos
  inline mantienen separación horizontal sin introducir salto adicional;
- headers/resultados usan alturas mínimas efectivas de `5.4mm`/`5.2mm`,
  padding `.8mm`/`.7mm .8mm`, centrado vertical, wrapping y line-height
  `1.15`/`1.2`;
- firmas y trailing fields declaran line-height/padding propios para que sus
  labels y valores no toquen las líneas.

El grid de campos dibuja una sola frontera superior/izquierda y cada celda
aporta únicamente frontera derecha/inferior. Esto sustituye el margen negativo
vertical que podía cruzar texto al crecer una línea, mantiene continuidad y
evita bordes dobles. WeasyPrint renderiza el radio mediante wrappers con
`overflow: hidden`; no se redondea cada celda. Temperatura y Presión conservan
una página Letter portrait y su composición declarativa aprobada.
