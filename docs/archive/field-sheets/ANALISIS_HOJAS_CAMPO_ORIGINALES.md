> Estado: HISTÓRICO
>
> Tipo: Histórico
>
> Autoridad: Baja; análisis del corpus original al 2026-07-13
>
> Prevalece sobre: ninguno
>
> Reemplazado para pendientes por: `../../project/OBSERVATIONS_REGISTER.md`. No usar sus preguntas abiertas como pendientes actuales.

# Análisis técnico de las 23 Hojas de Campo originales de MYC

Fecha de análisis: 2026-07-13  
Estado: referencia documental oficial para análisis; sin implementación  
Alcance: estructura, geometría, campos, tablas, páginas, firmas, inconsistencias y riesgos de parametrización

## 1. Corpus revisado y metodología

Se revisaron los 23 PDF entregados como formatos originales:

1. Anemómetro.
2. Angulímetro.
3. Báscula y Balanza.
4. Calibradores.
5. Cronómetro.
6. Detector de Gases.
7. Dimensional.
8. Eléctrica.
9. Flujo.
10. General.
11. Maestro de Altura.
12. Par Torsional.
13. Pesas.
14. Presión.
15. Reglas.
16. Sonido.
17. Tacómetro.
18. Temperatura.
19. TLD 6 Canales.
20. TLD.
21. Válvula de Seguridad.
22. Verificación de Equipos.
23. Copa.

La revisión combinó:

- metadatos físicos y conteo de páginas;
- extracción textual por página;
- detección geométrica de tablas mediante líneas y celdas;
- renderizado visual completo de todas las páginas;
- inspección ampliada de encabezados, cuerpos, tablas, firmas, pies y elementos gráficos.

Resultado físico:

- 23 archivos PDF.
- 27 páginas físicas.
- Todas las páginas son tamaño Carta vertical: 612 x 792 puntos, equivalentes a 215.9 x 279.4 mm.
- 20 archivos contienen una página.
- Eléctrica contiene tres páginas físicas.
- TLD 6 Canales contiene dos páginas.
- TLD contiene dos páginas.

## 2. Conclusión principal

Las hojas no son 23 diseños totalmente independientes. Existe una estructura común muy estable que ocupa aproximadamente dos tercios de la primera página. La variación real se concentra en cuatro zonas:

1. título y subtítulo de la magnitud;
2. uno o dos campos adicionales del instrumento;
3. definición, agrupación y paginación del área de medición;
4. disposición de firmas cuando la tabla consume más o menos altura.

Después de comparar las 23 hojas, se identifican **ocho familias semánticas reales de tablas**. La multiplicidad de formatos proviene principalmente de parámetros de esas familias: cantidad de repeticiones, filas, secciones, orden de roles, encabezados, categorías fijas y continuidad entre páginas.

La hoja de Copa es la única que constituye una composición documental especial completa, no solamente una variante de tabla.

## 3. Estructura visual común

### 3.1 Encabezado institucional

En la primera página de las 23 hojas aparece:

- logotipo MYC en la zona superior izquierda;
- nombre institucional centrado o ligeramente desplazado a la derecha;
- domicilio, teléfono y correo en una o dos líneas;
- título de la hoja en azul;
- subtítulo entre paréntesis cuando la plantilla cubre varios instrumentos.

El bloque ocupa aproximadamente el 12-16 % superior de la página. El título suele ser el elemento de mayor jerarquía después de la razón social.

### 3.2 Referencia documental

En 22 de 23 hojas aparecen dos líneas horizontales:

- Orden de trabajo.
- Certificado No.

La hoja de Verificación omite ambas referencias. La hoja de Copa coloca las fechas inmediatamente después de esas referencias, antes de los datos del usuario.

### 3.3 Datos del usuario

Las 23 hojas contienen tres datos en líneas de ancho completo:

- Atención.
- Empresa.
- Dirección.

La hoja de Copa cambia “Empresa” por “Cliente” y ordena Cliente, Dirección, Atención. Es una variación de etiqueta y orden, no un modelo de datos distinto.

### 3.4 Datos del instrumento

El patrón dominante es una cuadrícula visual de dos columnas:

- izquierda: Instrumento, División mínima, No. Serie, Identificación y Lugar de calibración;
- derecha: Alcance, Marca, Modelo y Ubicación.

Variaciones confirmadas:

- Pesas agrega `Clase`.
- TLD y TLD 6 Canales agregan `Tipo`.
- Válvula de Seguridad agrega `Medida`.
- Verificación elimina Alcance y División mínima.
- Copa conserva los conceptos comunes, añade unidades sugeridas `mm / s / cSt` a Alcance y División mínima y mueve observaciones dentro de esta región.

### 3.5 Fechas

Las 23 hojas tienen tres fechas:

- recepción;
- calibración;
- próxima calibración.

Verificación cambia las dos últimas etiquetas a “Fecha de verificación” y “Próxima verificación”. Los formatos generales muestran la ayuda `aaaa-mm-dd` debajo de la línea.

### 3.6 Condiciones ambientales

Las 23 hojas representan los mismos cuatro valores:

- humedad relativa inicial;
- humedad relativa final;
- temperatura inicial;
- temperatura final.

En 22 hojas se presentan como dos pares de líneas. Copa usa una matriz Inicio/Final con filas Humedad Relativa y Temperatura Ambiente.

### 3.7 Condición y observaciones

En 22 hojas aparecen dos casillas:

- Equipo en buen estado general.
- Considerar desviaciones del equipo.

Junto a ellas aparece un recuadro `Otros` bajo el título `OBSERVACIONES`, seguido de una línea para `Unidades`.

Copa no contiene las dos casillas. Usa un recuadro bilingüe de mayor tamaño:

- Observaciones y condiciones generales del instrumento.
- Observations and general conditions of the instrument.

Las unidades de Copa pertenecen a cada subtabla y no a un único campo general.

### 3.8 Resultados y firmas

Todas las hojas contienen un área de resultados y espacios de firma. Se observaron tres disposiciones recurrentes:

- **riel derecho vertical:** tabla a la izquierda y cuatro líneas apiladas a la derecha;
- **pie 2 x 2:** cuatro líneas debajo de una tabla compacta;
- **pie horizontal:** cuatro líneas distribuidas a lo ancho de la página.

La estructura más común es:

- CALIBRÓ.
- REVISÓ.
- REALIZÓ INFORME (SMM).
- ORDEN DE COMPRA/COTIZACIÓN.

Excepciones:

- Verificación cambia CALIBRÓ por VERIFICÓ.
- Reglas y Sonido dicen ORDEN DE TRABAJO/COTIZACIÓN.
- Copa usa CALIBRÓ TÉCNICO, AUTORIZÓ, CLIENTE y REALIZÓ INFORME.
- En algunos formatos se omite `(SMM)` después de REALIZÓ INFORME.

### 3.9 Pie documental

La intención común es:

- código a la izquierda;
- paginación al centro;
- revisión a la derecha.

La aplicación es inconsistente. Existen `FCA-30`, `FC-30`, `R1`, `R 1` y `R-1`. Cuatro plantillas no muestran paginación visible en la primera página: Anemómetro, Flujo, General y Pesas.

## 4. Cobertura de bloques compartidos

| Bloque conceptual | Cobertura | Observación |
|---|---:|---|
| Identidad institucional de primera página | 23/23 | Eléctrica cambia de identidad en su continuación |
| Título de hoja | 23/23 | Variaciones de ortografía y subtítulos |
| Orden de trabajo y certificado | 22/23 | Verificación los omite |
| Datos del usuario | 23/23 | Copa cambia etiqueta y orden |
| Datos del instrumento | 23/23 | Extra fields por magnitud |
| Tres fechas | 23/23 | Verificación cambia propósito |
| Cuatro condiciones ambientales | 23/23 | Copa usa presentación matricial |
| Dos casillas de condición | 22/23 | Copa las omite |
| Observaciones | 23/23 | Copa usa bloque bilingüe |
| Unidades | 23/23 | General en 22; por subtabla en Copa |
| Área de resultados | 23/23 | Es la principal fuente de variación |
| Firmas/referencias finales | 23/23 | Roles y distribución variables |
| Código documental | 23/23 | Tres convenciones visibles |
| Paginación explícita | 19/23 | Cuatro formatos la omiten |

## 5. Inventario detallado por hoja

En `Columnas` se cuenta la estructura de captura visible y no las celdas producidas por combinaciones gráficas de encabezado.

| # | Plantilla | Páginas físicas | Tabla o agrupación | Filas de captura | Columnas | Familia |
|---:|---|---:|---|---:|---:|---|
| 1 | Anemómetro | 1 | Patrón + tres lecturas IBC | 10 | 5 | F1 Comparación replicada |
| 2 | Angulímetro | 1 | Patrón + Primera/Segunda/Tercera IBC | 5 | 5 | F1 Comparación replicada |
| 3 | Báscula y Balanza | 1 | Excentricidad + patrón + ciclo IBC + repetibilidad 50 % y 100 % | 6 principales; 5 + 5 repetibilidad | 10 compuestas | F4 Ensayos de masa/balanza |
| 4 | Calibradores | 1 | Exteriores, interiores y profundidades | 7 + 5 + 3 | 5 por sección | F1 con secciones |
| 5 | Cronómetro | 1 | Patrón + cinco lecturas IBC | 5 | 7 | F1 Comparación replicada |
| 6 | Detector de Gases | 1 | Antes y después del ajuste; filas fijas H2S, CO, O2 y %LEL | 4 + 4 | 7 por fase | F3 Comparación por estado |
| 7 | Dimensional | 1 | Patrón + tres lecturas IBC | 10 | 5 | F1 Comparación replicada |
| 8 | Eléctrica | 3 | Seis bloques iguales de Patrón + tres IBC; uno en p.1 y cinco en p.2 | 5 por bloque | 5 | F1 seccionada y continuada |
| 9 | Flujo | 1 | Un valor IBC + tres lecturas de Patrón | 10 | 5 | F1 con roles invertidos |
| 10 | General | 1 | Encabezados alternables Patrón/IBC y tres repeticiones; instrucción para marcar X | 10 | 5 semánticas, 9 celdas gráficas | F1 con roles seleccionables |
| 11 | Maestro de Altura | 1 | Ascendente y descendente; Equipo Patrón + tres lecturas | 10 + 10 | 5 por sección | F2 Ciclo/dirección |
| 12 | Par Torsional | 1 | CW y CCW; Equipo + cinco valores de Patrón | 5 + 5 | 7 por sección | F2 Ciclo/dirección |
| 13 | Pesas | 1 | Patrón + cuatro lecturas IBC + ID | 10 | 7 | F1 con columna adicional |
| 14 | Presión | 1 | IBC + Patrón ascendente/descendente/ascendente | 11 | 5 | F2 Ciclo/dirección |
| 15 | Reglas | 1 | Equipo + cinco valores de Patrón | 15 sin numeración impresa | 7 | F1 Comparación replicada |
| 16 | Sonido | 1 | Patrón + tres lecturas IBC | 10 | 5 | F1 Comparación replicada |
| 17 | Tacómetro | 1 | Patrón + Primera/Segunda/Tercera IBC | 5 | 5 | F1 Comparación replicada |
| 18 | Temperatura | 1 | Un valor IBC + tres lecturas de Patrón | 10 | 5 | F1 con roles invertidos |
| 19 | TLD 6 Canales | 2 | Seis bloques; valor medido + tres pares Patrón/IBC | 5 por bloque | 8 | F5 Matriz multicanal pareada |
| 20 | TLD | 2 | Un bloque; valor medido + tres pares Patrón/IBC; segunda página vacía | 5 | 8 | F5 Matriz multicanal pareada |
| 21 | Válvula de Seguridad | 1 | Filas fijas Disparo/Cierre; referencia + tres lecturas de Patrón | 2 | 5 | F6 Eventos/umbrales |
| 22 | Verificación de Equipos | 1 | Unidades medidas + tres IBC + cumplimiento | 6 | 6 | F7 Verificación/cumplimiento |
| 23 | Copa | 1 | Diámetro, cinco tiempos, patrón/standard, temperatura promedio y gráfico técnico | variable | composición mixta | F8 Copa/viscosidad especializada |

### 5.1 Observaciones específicas de geometría

- Báscula y Balanza contiene dos filas visuales adicionales bajo las columnas centrales que no continúan la numeración de la prueba principal. Debe confirmarse si son filas útiles o un defecto de edición.
- Calibradores reutiliza exactamente la misma tabla en tres secciones, cambiando solamente título y cantidad de filas.
- Eléctrica no nombra las seis magnitudes o secciones. La página 2 muestra cinco bloques identificados únicamente por `Unidades`.
- Reglas muestra aproximadamente 15 filas sin números impresos, a diferencia del resto de tablas repetibles.
- TLD 6 Canales distribuye dos bloques en la primera página y cuatro en la segunda.
- TLD normal contiene solo un bloque en la primera página, pero conserva una segunda página prácticamente vacía.

## 6. Ocho familias reales de tablas

### F1. Comparación replicada

Contrato conceptual:

- número o punto;
- referencia o patrón;
- una a cinco lecturas del rol opuesto;
- cantidad configurable de filas.

Incluye Anemómetro, Angulímetro, Calibradores, Cronómetro, Dimensional, Eléctrica, Flujo, General, Pesas, Reglas, Sonido, Tacómetro y Temperatura.

Parámetros necesarios:

- rol de la referencia: Patrón, IBC o Equipo;
- rol de las repeticiones;
- 3, 4 o 5 repeticiones;
- 5, 7, 10 o 15 filas;
- secciones repetidas;
- columna adicional como ID;
- títulos de repetición numéricos u ordinales.

### F2. Ciclo o dirección

Representa mediciones relacionadas por sentido o fase de recorrido:

- Maestro de Altura: secciones Ascendente y Descendente.
- Par Torsional: secciones CW y CCW.
- Presión: columnas Ascendente, Descendente y Ascendente.

No debe modelarse como tres familias independientes. Requiere una lista ordenada de fases y la capacidad de representar fases como columnas o como secciones.

### F3. Comparación antes/después

Detector de Gases usa:

- dos estados: antes y después del ajuste;
- cuatro categorías fijas de gas;
- patrón;
- cinco repeticiones.

La identidad de fila es una categoría fija y no un número libre.

### F4. Ensayos de masa y balanza

Báscula y Balanza combina en una sola región:

- excentricidad;
- patrón;
- ciclo IBC;
- repetibilidad al 50 %;
- repetibilidad al 100 %.

Es una composición de subpruebas con longitudes diferentes. No debe forzarse dentro de una tabla rectangular simple.

### F5. Matriz multicanal pareada

Los dos formatos TLD usan:

- un valor medido por fila;
- tres pares Patrón/IBC;
- cinco filas por bloque;
- uno o seis bloques según la plantilla.

La pareja de columnas es la unidad repetible. El motor debe repetir un grupo de roles, no columnas aisladas.

### F6. Eventos o umbrales

Válvula de Seguridad tiene filas semánticas fijas:

- Disparo.
- Cierre.

Cada fila registra referencia y tres valores del patrón. Las filas no deben agregarse, eliminarse ni renombrarse libremente sin cambiar la plantilla.

### F7. Verificación y cumplimiento

Verificación agrega una salida cualitativa:

- unidad medida;
- tres lecturas;
- cumple con funcionamiento.

La última columna debe ser un tipo booleano o enumerado, no texto decimal.

### F8. Copa y viscosidad especializada

Copa combina:

- campo dimensional de diámetro de salida;
- cinco mediciones de tiempo;
- identificación y datos técnicos del estándar;
- viscosidad cinemática a 25 °C;
- designación y tamaño de copa;
- temperatura promedio de calibración;
- diagrama técnico con cotas y orificios;
- observaciones bilingües;
- cuatro roles de firma distintos.

Esta familia requiere un bloque gráfico controlado y varios subformularios. No es razonable representarla como una sola tabla genérica.

## 7. Modificadores reutilizables de tabla

Las siguientes características deben ser parámetros o contenedores, no nuevas familias:

- `sections`: exteriores/interiores/profundidades, CW/CCW, antes/después.
- `repeat_count`: tres, cuatro o cinco lecturas.
- `row_count`: cantidad fija o configurable.
- `fixed_rows`: gases, Disparo/Cierre.
- `role_order`: Patrón -> IBC o IBC -> Patrón.
- `paired_columns`: repetición de pares Patrón/IBC.
- `extra_columns`: ID, cumplimiento, referencia.
- `continuation`: repetir tabla o encabezado en páginas siguientes.
- `signature_placement`: riel derecho, pie 2 x 2 o pie horizontal.
- `unit_scope`: unidad general, por sección o por bloque.

## 8. Bloques documentales reutilizables

### Bloques base

1. `InstitutionHeaderBlock`.
2. `DocumentTitleBlock`.
3. `DocumentReferenceBlock`.
4. `CustomerDataBlock`.
5. `InstrumentDataBlock` con `extraFields` registrados.
6. `ServiceDatesBlock` con sobrescritura de etiquetas.
7. `EnvironmentalConditionsBlock` con presentación lineal o matricial.
8. `EquipmentConditionBlock`.
9. `ObservationsBlock` con variante bilingüe.
10. `MeasurementAreaBlock`.
11. `SignatureBlock` con roles y layout configurables.
12. `DocumentFooterBlock`.

### Bloques complejos adicionales

1. `MeasurementSectionGroup`: agrupa varias instancias de una misma tabla.
2. `FixedCategoryRowsBlock`: filas semánticas no eliminables.
3. `DirectionalCycleBlock`: fases ordenadas como columnas o secciones.
4. `PairedChannelMatrixBlock`: pares de roles repetidos.
5. `CompositeTestBlock`: subpruebas con geometrías distintas.
6. `ReferenceStandardDetailsBlock`: datos técnicos del patrón.
7. `ControlledDiagramBlock`: imagen versionada con leyendas y dimensiones.
8. `CalculatedValueBlock`: promedio o cálculo con fórmula identificada.
9. `ContinuationHeaderBlock`: contexto mínimo para páginas posteriores.

## 9. Inconsistencias institucionales

### 9.1 Razón social y logotipo

- La mayoría usa `METROLOGIA Y SERVICIOS MYC`.
- La página 2 de Eléctrica usa `SERVICIOS METROLÓGICOS MUNDIALES S.A. DE C.V.`.
- Esa misma página sustituye el logotipo MYC por un globo con la marca SMM.

### 9.2 Domicilio

Se encontraron estas variantes:

- Isla Martinica #2710.
- Islas Martinica #2710.
- `martinica# 2710` sin espacio.
- Isla/Islas con mayúsculas y puntuación diferentes.
- Sonido usa `Islas Martinica #2117`.
- La continuación de Eléctrica usa `Islas Vírgenes #2117`.

### 9.3 Teléfono

- Valor dominante: `3350092659`.
- Maestro de Altura usa `3320092659`.
- Eléctrica página 2 usa `01 (33) 1983-6308 / 2265-2197`.

La dirección, teléfono, correo, razón social y logotipo no deben almacenarse dentro de cada plantilla. Deben resolverse desde una configuración institucional versionada.

## 10. Inconsistencias documentales y editoriales

### 10.1 Código y revisión

- Código dominante: `FCA-30`.
- Anemómetro, General y Pesas imprimen `FC-30`.
- Revisión dominante: `R1`.
- Maestro de Altura y Copa imprimen `R 1`.
- Temperatura imprime `R-1`.
- Par Torsional y Reglas no muestran claramente la revisión en el pie.

### 10.2 Paginación

- Anemómetro, Flujo, General y Pesas no muestran `Página 1 de 1`.
- Eléctrica declara internamente `Hoja 1 de 2`, pero el PDF contiene tres páginas y además imprime `Página 1 de 3`.
- La página 3 de Eléctrica está prácticamente vacía; solo conserva elementos de pie.
- TLD normal declara dos páginas, pero la segunda está prácticamente vacía.
- Sonido presenta un `1` aislado como paginación visual en lugar de la convención completa.

### 10.3 Ortografía y nomenclatura

Ejemplos observados:

- `METROLIGIA` en Flujo.
- `Aperimetro` en Eléctrica.
- `Asdcendente` en Báscula y Balanza.
- `Acendente` en Presión.
- Angulímetro, Báscula, Tacómetro, Válvula, Próxima, Atención y División mínima aparecen frecuentemente sin acento.
- `DirecciÓn` mezcla mayúsculas de forma incorrecta.
- Se alterna `Resultados de Calibración` con `Resultados de la Calibración`.
- Se alterna `DATOS DE MEDICIÓN`, `DATOS DE MEDICION` y encabezados sin sección.

Estas diferencias no deben conservarse como variantes legítimas de plantilla. Deben normalizarse en el catálogo de etiquetas.

### 10.4 Firmas y referencias comerciales

- Se alterna ORDEN DE COMPRA/COTIZACIÓN con ORDEN DE TRABAJO/COTIZACIÓN.
- REALIZÓ INFORME aparece con y sin `(SMM)`.
- CALIBRÓ/VERIFICÓ depende correctamente del propósito, pero hoy está codificado visualmente.
- Los espacios no distinguen firma, nombre, fecha ni rol de usuario.

## 11. Inconsistencias y ambigüedades de tablas

1. General muestra encabezados Patrón/IBC seleccionables mediante una `X`, pero la relación exacta entre columnas no queda inequívoca en el PDF.
2. Presión usa Ascendente, Descendente y Ascendente. Debe confirmarse si la tercera fase es realmente un segundo ascenso o una etiqueta equivocada.
3. Báscula y Balanza contiene `Asdcendente` y filas centrales sin numeración coherente.
4. Eléctrica no identifica qué magnitud corresponde a cada uno de sus seis bloques.
5. TLD usa repetidamente “Valores medidos” para conceptos de nivel distinto: valor de fila, grupo y pares Patrón/IBC.
6. Reglas no numera sus filas de captura.
7. Verificación deja una letra `K` aislada debajo de la tabla.
8. Cronómetro incluye una fórmula y el texto `DRAFT SOP 24-NIST`; debe determinarse si es una regla oficial, una nota temporal o contenido obsoleto.
9. Copa incluye un diagrama técnico de Ford Viscosity Cup cuya procedencia, permiso de reproducción, resolución y versión deben controlarse.

## 12. Problemas para convertir los PDF en plantillas editables

### 12.1 La geometría actual no contiene semántica

Los PDF muestran líneas y texto, pero no declaran:

- qué campo proviene del ERP;
- qué celda es editable;
- qué columna es patrón o instrumento;
- qué valor es decimal, booleano o texto;
- qué filas son fijas;
- qué cálculos deben realizarse;
- qué campos son obligatorios.

Copiar la geometría sin modelar estos conceptos produciría un editor visual atractivo pero operativamente ambiguo.

### 12.2 Tablas asimétricas y celdas combinadas

Báscula, General, TLD y Copa usan encabezados combinados, grupos repetibles o regiones con diferentes alturas. Un modelo de tabla limitado a `columns[]` no es suficiente. Se necesitan roles, grupos de columnas, secciones y subpruebas.

### 12.3 Paginación dependiente del contenido

El motor deberá decidir:

- qué bloque puede partirse;
- qué encabezado se repite;
- dónde continúan las firmas;
- cómo conservar unidades y referencias en una continuación;
- cómo evitar páginas vacías causadas por áreas de impresión heredadas.

### 12.4 Filas fijas frente a filas configurables

- Gases y Válvula requieren filas fijas con identidad.
- La comparación simple puede admitir cantidad configurable.
- TLD requiere cinco filas dentro de cada canal.
- Verificación necesita un tipo de resultado cualitativo.

El editor debe impedir operaciones que destruyan la semántica de una plantilla oficial.

### 12.5 Roles de columna

Flujo y Temperatura invierten el papel de Patrón e IBC respecto de Anemómetro o Sonido. General pretende que el usuario marque cuál rol ocupa cada encabezado. Esto confirma que las columnas deben construirse por roles y bindings, no por nombres físicos fijos.

### 12.6 Fórmulas y validaciones

El diseño visual no especifica formalmente:

- tolerancia del cronómetro;
- promedios o conversiones de Copa;
- cumplimiento de Verificación;
- reglas antes/después de ajuste;
- ciclos de Presión;
- criterios de repetibilidad de Báscula.

Las fórmulas deben ser definiciones controladas y versionadas, nunca texto decorativo ni código libre dentro de una plantilla.

### 12.7 Gráficos especiales

Copa requiere una estrategia para activos gráficos:

- asset controlado y versionado;
- resolución de impresión;
- texto alternativo;
- licencia o autorización de uso;
- relación entre la figura y los campos de captura.

### 12.8 Firmas

Las líneas actuales no definen si se captura nombre, firma manuscrita, usuario ERP, fecha o sello. El bloque de firmas debe separar rol, identidad, evidencia de firma y presentación.

### 12.9 Compatibilidad histórica

Los formatos emitidos deben conservar su snapshot. Corregir domicilio, código o revisión en una plantilla nueva no debe alterar documentos históricos.

## 13. Decisiones que requieren confirmación funcional

Antes de implementar las tablas deben resolverse estas preguntas:

1. ¿Cuál es la razón social, domicilio, teléfono, correo y logotipo institucional vigente?
2. ¿El código oficial único es `FCA-30` y la revisión oficial única es `R1`?
3. ¿Las páginas vacías de Eléctrica y TLD son errores de exportación o páginas reservadas intencionalmente?
4. ¿Cuáles son las seis magnitudes de los bloques de Eléctrica y en qué orden aparecen?
5. ¿Qué significan exactamente los encabezados seleccionables de General?
6. ¿La secuencia de Presión es Ascendente -> Descendente -> Ascendente?
7. ¿Cuántas filas oficiales debe tener Reglas y deben numerarse?
8. ¿Qué representan las filas centrales sin número en Báscula y Balanza?
9. ¿Debe conservarse la fórmula `DRAFT SOP 24-NIST` de Cronómetro?
10. ¿Qué representa la `K` aislada de Verificación?
11. ¿El diagrama de Copa puede reproducirse y cuál es su fuente oficial?
12. ¿Las firmas capturan solo nombre o también trazo, usuario, fecha y autorización?

## 14. Recomendación arquitectónica

La referencia oficial debe dividirse en tres capas:

1. **Contenido normativo:** campos, roles, filas, fases, firmas, fórmulas y reglas que deben preservarse.
2. **Sistema visual común:** página Carta, márgenes, tipografía, color, jerarquía, encabezado, pie y bloques reutilizables.
3. **Correcciones controladas:** domicilio, teléfonos, ortografía, código, revisión, paginación y páginas vacías que no deben perpetuarse como variantes.

No se recomienda convertir cada PDF en una plantilla independiente dibujada manualmente. La solución sostenible es:

- una estructura base compartida;
- ocho familias de tabla;
- modificadores declarativos;
- un registro único de campos;
- activos gráficos controlados;
- layouts de firma configurables;
- reglas de paginación y continuación;
- snapshots inmutables por versión.

## 15. Estado al cierre del análisis

- Las 23 hojas fueron revisadas completamente.
- No se modificó código, base de datos, modelos, endpoints, plantillas activas, PDF operativo ni constructor visual.
- Este documento registra conclusiones técnicas; no aprueba por sí solo las correcciones señaladas.
- La implementación debe permanecer detenida hasta recibir instrucciones sobre las decisiones funcionales pendientes.

## 16. Identidad de los archivos analizados

Los siguientes SHA-256 fijan exactamente la colección usada como referencia:

| Plantilla | SHA-256 |
|---|---|
| Anemómetro | `b02342d599a81fc0c234759935a3aef415e81137b6d34495c4ee4f91f4137560` |
| Angulímetro | `d2bbb168f9be584690d65be8b4c9096929bfa73c4f2745de40e7110d0951f5b8` |
| Báscula y Balanza | `a60e4710fa23d1105b724d3f7c8fd765e7a0a32ea38b5d03c0ecef59d33a32b6` |
| Calibradores | `49324e7fc62b0b98edca60c2d5b07622951175333f55c6bfa165f9acf86c9b12` |
| Cronómetro | `8e0e6587aace66c44de0f234670d8510722917df978e82c2b7bfb2088366a0df` |
| Detector de Gases | `1d4d9af4e0cef2d9fd3f9cecf5b1ee8a89c0aa20042e5a51bb3fd8ce4d39ceb1` |
| Dimensional | `111b84da25c10e593813588421f9d6d0afaad42d043b954a1ea29dcac5df1f2c` |
| Eléctrica | `1e78e317475e5c0661c5cea5c8e309615db8c4741644605ab97b6291c9faaba5` |
| Flujo | `2f7f5136c1925042d3500f334686e8bf86e32bbe01943d97e7fd6f602e4de27d` |
| General | `cf66a7adb165277a61e8837f938db226de15c31f478989620d8af5d45db2a71f` |
| Maestro de Altura | `972c14bdd3afb97541997057feed7ce651901548f7eaab38dca838f9c2eacafe` |
| Par Torsional | `7078fce55876c33e0e93a0f162f4fe6953f527b4ca40f5dedd07e8e7cdcf75c3` |
| Pesas | `547baafc561cac0c9b05aecb147d6e15352ae172020b2e7cd16c065ae9934ad2` |
| Presión | `8c737a461d3e0f81f91eaebdcaf7445a55836df187a2f35ce9086ee5020874f0` |
| Reglas | `8d5bfaf0f4d85d3e5a4610658b3b79d4b79eb9fbb791293954755f2f395f9663` |
| Sonido | `9ce23a995e03ed773bd1af4bf2888c7efe80618fb045126ca673d807b679dab5` |
| Tacómetro | `f6dbda4e43e9eecc8c5da6f3e1d288d5b416c4494789f9261df976fe54ed3c0f` |
| Temperatura | `d9a69275d2989fb9ae8d8a8c46ab85ddd74784ba0a08f928f0545acf754d8111` |
| TLD 6 Canales | `93b2bb730c56e4074139f3405283a245666010d2d1ec77e2b343fdb215f49ae1` |
| TLD | `f94f2114c673a9cd696c6a483f804c8505f0c1e66df64382e1ae80c5ec78d0a6` |
| Válvula de Seguridad | `fdde66209d0c2ecd18d1810ca0a6e3e12ef132c547ab9cfc6bc05e2dba4a8369` |
| Verificación de Equipos | `917290b4c44f5d4ae35595179959aeed353005bfbcf147e2760b8321b17b2ce8` |
| Copa | `a7ff42e4a1489aefcc2dcb2ee54089eef3141f69985cb19c20e72928777d3bd9` |
