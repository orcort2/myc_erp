MYC Document Engine — Especificación funcional y técnica
1. Identidad

Nombre: MYC Document Engine
Abreviatura: MDE
Proyecto: MYC SYSTEM
Estado inicial: Diseño arquitectónico
Responsable funcional: Control Documental

2. Propósito

MYC Document Engine será el motor interno responsable de representar, componer, validar y materializar documentos controlados dentro de MYC SYSTEM.

El MDE no sustituye a los módulos operativos.

Los módulos como Ventas, ETS, Hojas de Campo, Certificados y Facturación seguirán siendo responsables de:

capturar información;
validar reglas operativas;
controlar estados;
almacenar datos del proceso;
gestionar permisos;
conservar trazabilidad operativa.

El MDE será responsable de:

representar la estructura documental;
definir páginas y zonas imprimibles;
administrar objetos documentales;
resolver bindings;
preparar composiciones visuales;
validar layouts;
producir una representación intermedia;
entregar esa representación a renderizadores especializados;
conservar compatibilidad con snapshots documentales.
3. Principio arquitectónico principal

Los módulos operativos no deben diseñar documentos.

Los módulos operativos entregan datos estructurados.

Control Documental define:

identidad documental;
código;
revisión;
versión vigente;
diseño;
objetos documentales;
reglas de impresión;
bindings permitidos.

El MDE interpreta esa definición y genera una representación documental.

El renderer materializa la representación como:

PDF;
HTML;
impresión;
vista previa;
otros formatos futuros.
4. Separación de responsabilidades
Módulo operativo
    ↓
Datos estructurados
    ↓
Control Documental
    ↓
Definición documental publicada
    ↓
MYC Document Engine
    ↓
Árbol documental normalizado
    ↓
Renderer especializado
    ↓
Documento emitido
    ↓
Snapshot + archivo + checksum
5. Responsabilidades del MDE

El motor podrá:

leer una definición documental;
validar su estructura;
normalizar páginas;
normalizar objetos;
resolver posiciones y dimensiones;
resolver bindings declarativos;
aplicar estilos permitidos;
controlar visibilidad;
ordenar objetos por capas;
administrar objetos repetibles;
preparar tablas;
preparar grupos;
manejar saltos de página;
generar una estructura común para renderizado.

El motor no podrá:

consultar directamente la base de datos;
modificar entidades operativas;
ejecutar consultas arbitrarias;
cambiar estados de ETS;
crear cotizaciones;
crear certificados;
generar folios operativos;
validar reglas comerciales;
ejecutar cálculos metrológicos;
ejecutar código libre incluido en una plantilla;
editar documentos publicados;
alterar snapshots históricos.
6. Conceptos fundamentales
6.1 Documento controlado

Es la identidad permanente administrada por Control Documental.

Ejemplos:

FCA-23-2 — Cotización
FCA-22 — Orden de Trabajo
FCA-30 — Hoja de Campo

El documento controlado no contiene datos de una operación concreta.

6.2 Revisión documental

Es la revisión oficial aprobada y visible del documento.

Ejemplos:

R0
R1
R2
Rev. 03

La revisión documental no es equivalente a la versión técnica del layout.

6.3 Versión técnica

Es la versión interna de la definición ejecutable.

Ejemplo:

Revisión documental: R2
Versión técnica del layout: 5

Una revisión oficial puede requerir varias versiones técnicas durante su preparación antes de publicarse.

6.4 Definición documental

Es la estructura declarativa utilizada por el MDE.

Debe contener como mínimo:

metadata;
páginas;
objetos;
estilos;
bindings;
configuración de salida;
versión;
compatibilidad de renderer.
6.5 Documento emitido

Es una instancia concreta generada con datos reales.

Ejemplos:

una cotización específica;
una Orden de Trabajo;
una Hoja de Campo;
una etiqueta;
un recibo.

El documento emitido debe ser trazable e inmutable una vez formalizado.

6.6 Snapshot

Es la copia congelada de:

identidad documental;
revisión;
versión técnica;
definición;
bindings;
configuración;
datos relevantes;
renderer;
fecha de emisión.

Un documento histórico nunca debe regenerarse con una plantilla vigente distinta.

7. Documento MDE

El objeto raíz será document.

Ejemplo conceptual:

{
  "schema_version": "1.0",
  "document": {
    "id": "test-document",
    "name": "Documento de prueba",
    "page_size": "A4",
    "orientation": "portrait",
    "unit": "mm",
    "margins": {
      "top": 12,
      "right": 12,
      "bottom": 12,
      "left": 12
    },
    "background": "#ffffff",
    "show_guides": false,
    "grid": {
      "enabled": true,
      "size": 5
    }
  },
  "pages": [],
  "styles": {},
  "bindings": {},
  "metadata": {}
}
8. Página

Una página representa una superficie documental imprimible.

Propiedades mínimas:

id
size
orientation
width
height
margins
background
objects
repeatable_header
repeatable_footer

Tamaños iniciales:

A4
Carta
Oficio
Media carta
Personalizado

El tamaño personalizado debe permitir:

width
height
unit
9. Unidad de medida

La unidad interna oficial del MDE será:

milímetros

Razones:

corresponde al dominio de impresión;
facilita reproducir formatos físicos;
evita depender de densidad de pantalla;
permite convertir consistentemente a PDF;
permite trabajar con etiquetas y formatos especiales.

React podrá transformar milímetros a píxeles únicamente para visualización.

El almacenamiento nunca debe depender de píxeles de pantalla.

10. Objeto documental

Un objeto documental es una unidad estructural dentro de una página.

Todos los objetos deben compartir un contrato común.

{
  "id": "object-001",
  "type": "text",
  "page_id": "page-1",
  "x": 20,
  "y": 30,
  "width": 80,
  "height": 10,
  "rotation": 0,
  "visible": true,
  "locked": false,
  "z_index": 1,
  "style": {},
  "binding": null,
  "metadata": {}
}
11. Propiedades comunes de objetos

Todos los objetos deberán soportar:

id
type
page_id
x
y
width
height
rotation
visible
locked
z_index
style
binding
metadata

Propiedades futuras opcionales:

repeat_on_pages
keep_together
allow_page_break
conditional_visibility
print_only
screen_only
12. Tipos iniciales de objetos

La primera versión del MDE soportará:

document
page
text
image
line
rectangle
document-code
document-revision
signature-line
group

La segunda etapa incorporará:

binding-field
table
repeater
page-number
institutional-header
institutional-footer
approval-block
13. Objeto de texto

Propiedades específicas:

content
font_family
font_size
font_weight
font_style
text_align
vertical_align
line_height
color
overflow

Ejemplo:

{
  "id": "title",
  "type": "text",
  "page_id": "page-1",
  "x": 20,
  "y": 30,
  "width": 170,
  "height": 12,
  "content": "DOCUMENTO DE PRUEBA",
  "style": {
    "font_size": 16,
    "font_weight": 700,
    "text_align": "center"
  }
}
14. Objeto de imagen

Propiedades específicas:

source_type
source
fit
preserve_aspect_ratio
opacity

source_type podrá ser:

asset
uploaded-file
binding

No se almacenarán archivos binarios dentro del JSON.

El objeto guardará una referencia controlada al recurso.

15. Objeto de línea

Propiedades específicas:

direction
stroke_width
stroke_style
stroke_color

Debe servir para:

separadores;
firmas;
divisiones de secciones;
tablas simples.
16. Código documental y revisión

Los objetos:

document-code
document-revision

serán objetos especializados.

No deberán contener valores escritos manualmente cuando se utilicen dentro de una versión publicada.

Resolverán sus valores desde Control Documental.

Ejemplo:

{
  "id": "document-code",
  "type": "document-code",
  "binding": "document.code"
}
17. Firma

La primera versión utilizará:

signature-line

Este objeto representa:

etiqueta;
línea;
nombre;
puesto;
fecha opcional.

No capturará firma digital en el diseñador.

El diseñador define el espacio.

El módulo operativo proporciona la firma cuando corresponda.

18. Bindings

Un binding conecta un objeto con un dato proporcionado por un módulo operativo.

Ejemplos:

document.code
document.revision
client.commercial_name
quotation.folio
service_order.folio
work_order.number
equipment.serial_number
field_sheet.calibration_date

Los bindings deben:

ser declarativos;
estar incluidos en un contrato conocido;
validarse antes de publicar;
resolverse sin consultas directas desde el layout;
admitir datos de muestra para vista previa.

No se permitirá:

JavaScript arbitrario
SQL
expresiones libres
acceso directo a objetos internos del ORM
19. Contrato de datos

Cada familia documental publicará un contrato.

Ejemplo:

{
  "renderer": "quotation",
  "bindings": {
    "quotation.folio": {
      "type": "string",
      "required": true
    },
    "client.commercial_name": {
      "type": "string",
      "required": true
    },
    "quotation.items": {
      "type": "array",
      "required": false
    }
  }
}

El MDE validará que una plantilla solo utilice bindings permitidos por su renderer.

20. Renderer

El renderer convierte el árbol documental normalizado en una salida.

Renderizadores previstos:

ReactPreviewRenderer
HtmlRenderer
PdfRenderer
PrintRenderer

El renderer no modifica la definición.

El renderer recibe:

document_definition
resolved_data
output_configuration

y entrega:

artifact
warnings
metadata
checksum
21. React Preview Renderer

Será el primer renderer implementado.

Su función será:

representar la página en pantalla;
convertir milímetros a píxeles;
permitir selección;
mostrar guías;
mostrar bordes de selección;
representar objetos sin modificar la definición;
servir como base del Lab.
22. PDF Renderer

No se implementará en la primera etapa.

Cuando se implemente deberá:

consumir la misma definición normalizada;
respetar las mismas dimensiones;
respetar saltos de página;
usar los mismos bindings;
producir resultados equivalentes a la vista previa.
23. Estado del diseñador

El diseñador es únicamente una interfaz de edición del MDE.

El diseñador podrá:

crear objetos;
mover objetos;
redimensionar objetos;
editar propiedades;
bloquear objetos;
duplicar objetos;
eliminar objetos;
cambiar orden de capas;
validar definición;
previsualizar.

El diseñador no podrá:

consultar operaciones reales;
modificar datos de clientes;
cambiar estados;
aprobar revisiones;
publicar directamente sin Control Documental.
24. Persistencia

Durante el Lab, la definición existirá únicamente en memoria.

Posteriormente se guardará como JSON asociado a una versión documental.

No se agregará persistencia hasta validar:

contrato del documento;
contrato de objetos;
unidades;
posiciones;
renderer de vista previa;
serialización;
compatibilidad básica.
25. Versionado del schema

Toda definición MDE incluirá:

{
  "schema_version": "1.0"
}

Cambios futuros deberán usar migradores de definición.

Ejemplo:

1.0 → 1.1
1.1 → 2.0

Nunca se asumirá que una definición histórica tiene la estructura más reciente.

26. Seguridad

El MDE nunca ejecutará contenido arbitrario.

No se permitirán:

scripts;
HTML libre sin sanitización;
consultas;
URLs externas no controladas;
código embebido;
expresiones dinámicas no verificadas.
27. Compatibilidad histórica

Las definiciones publicadas deberán considerarse inmutables.

Cuando cambie el motor:

se conserva schema_version;
se conserva el snapshot;
se usa compatibilidad o migración controlada;
no se modifica silenciosamente la definición histórica.
28. Primera meta del Lab

Construir un documento de prueba con:

página A4;
logo MYC;
nombre institucional;
título;
código FCA-TEST;
revisión R0;
texto libre;
línea de firma;
pie institucional.

La primera meta no incluye:

drag-and-drop;
backend;
PDF;
tablas;
bindings reales;
publicación;
persistencia.
29. Roadmap inicial
MDE 0.1 — Contrato base
Documento.
Página.
Unidades.
Objeto común.
Normalización.
Validación inicial.
MDE 0.2 — React Preview Renderer
Página A4.
Conversión mm → px.
Render de texto.
Render de imagen.
Render de línea.
Render de firma.
MDE 0.3 — Selección y propiedades
Selección.
Panel de propiedades.
Edición local.
Bloqueo.
Orden de capas.
MDE 0.4 — Movimiento y tamaño
Movimiento.
Redimensionamiento.
Grid.
Snap.
Guías.
MDE 0.5 — Bindings
Contratos.
Datos de muestra.
Campos vinculados.
Validación.
MDE 0.6 — Objetos complejos
Grupos.
Encabezados.
Pies.
Tablas.
Repetidores.
Paginación.
MDE 0.7 — Persistencia
Guardar definición.
Versionado.
Integración con Control Documental.
Snapshots.
MDE 0.8 — PDF
Renderer PDF.
Comparación visual.
Impresión.
Checksums.
30. Regla de cierre

Ningún PDF operativo actual será reemplazado hasta que el MDE demuestre:

equivalencia visual;
estabilidad;
versionado;
snapshots;
compatibilidad histórica;
validación de bindings;
generación reproducible.