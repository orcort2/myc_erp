> Estado: ARCHIVO
>
> Tipo: Archivo
>
> Autoridad: Baja; evidencia de implementación del laboratorio al 2026-07-13
>
> Prevalece sobre: ninguno
>
> Fusionado en: `../FIELD_SHEET_LAB_CONSOLIDATED.md`; se conserva como fuente íntegra

# Implementación de las 23 Hojas de Campo en el laboratorio

Fecha: 2026-07-13

## Resultado

El laboratorio `/dashboard/field-sheet-lab` contiene las 23 hojas oficiales y continúa completamente aislado de ETS, equipos, certificados y base de datos. La captura, la vista PDF y las evidencias usan el mismo componente `FieldSheetLayout` y el mismo estado local.

## Solución de encabezado

El encabezado dejó de ser una cuadrícula de dos columnas con el título dentro de la columna derecha. Ahora tiene tres zonas independientes para logotipo, identidad y metadatos, y una segunda banda que ocupa `grid-column: 1 / -1`. Por ello el título y subtítulo se centran contra el ancho completo de Carta; el código y la revisión no participan en el cálculo de su centro.

Las páginas posteriores usan un `ContinuationHeader` compacto con razón social, título, código, revisión y la palabra Continuación. Esto evita repetir datos comunes y mantiene contexto documental.

## Solución de paginación

`fieldSheetPagination.js` transforma los bloques declarativos en unidades indivisibles:

- los bloques comunes y firmas se mueven completos a la página siguiente cuando no caben;
- cada sección de tabla puede dividir sus filas y genera una nueva tabla con su propio `thead`;
- `break_before` permite conservar continuaciones oficiales como Eléctrica y TLD 6 Canales;
- todas las páginas reciben encabezado, referencias, pie y `Página X de Y`;
- las páginas sin unidades se descartan;
- no se usa `overflow: hidden` para ocultar contenido;
- el algoritmo se ejecuta en el renderer común, tanto en captura como en impresión.

La impresión reserva una separación física de 3.4 mm entre cajas Carta para evitar que Chrome fragmente por redondeo la primera línea del encabezado de continuación.

## Plantillas registradas

| # | Plantilla | Clave | Familia | Páginas esperadas |
|---:|---|---|---|---:|
| 1 | Anemómetro | `anemometro` | Comparación replicada | 1 |
| 2 | Angulímetro | `angulimetro` | Comparación replicada | 1 |
| 3 | Báscula y Balanza | `bascula` | Masa/balanza compuesta | 1 |
| 4 | Calibradores | `calibradores` | Comparación replicada con secciones | 1 |
| 5 | Cronómetro | `cronometro` | Comparación replicada | 1 |
| 6 | Detector de Gases | `detector_gases` | Antes/después | 1 |
| 7 | Dimensional | `dimensional` | Comparación replicada | 1 |
| 8 | Eléctrica | `electrica` | Comparación replicada continuada | 2 |
| 9 | Flujo | `flujo` | Comparación replicada con roles invertidos | 1 |
| 10 | General | `general` | Comparación replicada configurable | 1 |
| 11 | Maestro de Altura | `maestro_altura` | Ciclo/dirección | 1 |
| 12 | Par Torsional | `par_torsional` | Ciclo/dirección | 1 |
| 13 | Pesas | `pesas` | Comparación replicada con ID | 1 |
| 14 | Presión | `presion` | Ciclo/dirección | 1 |
| 15 | Reglas | `reglas` | Comparación replicada | 1 |
| 16 | Sonido | `sonido` | Comparación replicada | 1 |
| 17 | Tacómetro | `tacometro` | Comparación replicada | 1 |
| 18 | Temperatura | `temperatura` | Comparación replicada con roles invertidos | 1 |
| 19 | TLD 6 Canales | `tld_6_canales` | Matriz multicanal pareada | 2 |
| 20 | TLD | `tld` | Matriz multicanal pareada | 1 |
| 21 | Válvula de Seguridad | `valvula_seguridad` | Evento/umbral | 1 |
| 22 | Verificación de Equipos | `verificacion_equipos` | Verificación/cumplimiento | 1 |
| 23 | Copa | `copa` | Copa especializada | 1 |

## Casos especiales

- Eléctrica contiene seis bloques de cinco filas. La primera página conserva datos comunes y el bloque 1; la segunda contiene los bloques 2 a 6, observaciones y firmas. Cada bloque mantiene su campo manual de unidades.
- TLD 6 Canales contiene seis bloques de cinco filas y siete datos por fila: valor medido y tres pares Patrón/IBC. Los canales 1 y 2 quedan en página 1; los canales 3 a 6 en página 2.
- TLD normal conserva un bloque de cinco filas en una sola página; se eliminó la página residual histórica.
- Copa usa una composición propia declarativa: ambiente y observaciones en paralelo, diagrama controlado, cuatro subtablas y el arreglo especial de firmas Cliente + tres roles inferiores.

## Evidencias

- PDFs: `output/pdf/field-sheet-lab/*.pdf`.
- PNG de revisión: `output/pdf/field-sheet-lab/evidence-final/*.png`.
- Total: 23 PDF Carta y 25 páginas PNG.
- Eléctrica y TLD 6 Canales generan dos páginas; las otras 21 plantillas generan una.
- Script reproducible: `scripts/render-field-sheet-lab-pdfs.sh`.

## Validaciones ejecutadas

- 23 opciones visibles en el selector.
- Centro geométrico del título: diferencia de 0 px en todas las páginas.
- `scrollHeight - clientHeight`: 0 en las 25 páginas del laboratorio.
- Separación positiva entre contenido y pie en todas las páginas.
- Prueba de crecimiento: 84 filas de Anemómetro generan tres páginas, repiten `thead` y mueven las firmas completas a la última página.
- Consola del navegador: cero errores.
- Prueba declarativa: 23 plantillas, páginas esperadas y cero páginas residuales -> OK.
- `npm run build` -> OK; advertencia conocida de chunk mayor a 500 kB.
- Backend: `python -m unittest discover -s tests -v` -> 5 pruebas OK.
- `pytest` no está instalado en el entorno virtual; se utilizó la suite `unittest` existente.

## Pendientes funcionales

- Validación de Calidad de etiquetas ambiguas en General, Presión, Báscula y Balanza, Eléctrica, Reglas y Verificación.
- Sustituir el diagrama vectorial controlado de Copa por el activo oficial aprobado cuando Calidad confirme procedencia y versión.
- Confirmar los nombres de los seis bloques eléctricos; hoy permanecen configurables y numerados.
- No se implementaron cálculos, tolerancias, incertidumbre, cumplimiento automático ni promedios.
- No se conectó ninguna plantilla nueva al flujo operativo o al backend de Hojas de Campo.
