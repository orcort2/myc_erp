> Estado: HISTÓRICO
>
> Tipo: Histórico
>
> Autoridad: Baja; consolidación del laboratorio al 2026-07-13
>
> Prevalece sobre: las dos fuentes sólo como resumen de consulta
>
> Fuentes fusionadas: `sources/LABORATORIO_HOJAS_CAMPO.md` y `sources/IMPLEMENTACION_23_HOJAS_CAMPO_LAB.md`
>
> Estado y pendientes vigentes: `../../project/PROJECT_STATUS.md` y `../../project/OBSERVATIONS_REGISTER.md`

# Laboratorio de Hojas de Campo — consolidación histórica

Este documento unifica la descripción operativa y el reporte de implementación del laboratorio. Las fuentes originales permanecen íntegras en `sources/` para trazabilidad y no conservan autoridad independiente.

## Alcance validado en la fecha

- Rutas `/dashboard/field-sheet-lab` y `/dashboard/field-sheet-preview`.
- Acceso sin sesión, aislado de ETS, equipos, certificados, API y base de datos.
- 23 plantillas oficiales, datos simulados editables, filas dinámicas y navegación de teclado.
- Inspector de plantilla, versión, familia, bloques, snapshot y JSON vivo.
- Captura, vista PDF e impresión basadas en el mismo `FieldSheetLayout` y estado local.
- Estado exclusivamente en memoria; recargar o reiniciar elimina los cambios.

## Soluciones documentales implementadas

El encabezado separó logotipo, identidad y metadatos y centró título/subtítulo sobre el ancho completo. Las continuaciones usan encabezado compacto. `fieldSheetPagination.js` divide bloques y tablas, repite `thead`, respeta `break_before`, conserva firmas indivisibles, descarta páginas vacías y numera todas las hojas. Se documentó una separación física de 3.4 mm entre cajas Carta para evitar fragmentación por redondeo al imprimir.

## Plantillas y casos especiales

Se registraron Anemómetro, Angulímetro, Báscula y Balanza, Calibradores, Cronómetro, Detector de Gases, Dimensional, Eléctrica, Flujo, General, Maestro de Altura, Par Torsional, Pesas, Presión, Reglas, Sonido, Tacómetro, Temperatura, TLD 6 Canales, TLD, Válvula de Seguridad, Verificación de Equipos y Copa.

- Eléctrica y TLD 6 Canales se validaron en dos páginas; las otras 21, en una.
- Eléctrica se compuso en seis bloques de cinco filas.
- TLD 6 Canales usa seis bloques multicanal; TLD normal eliminó una página residual.
- Copa utiliza composición especializada con diagrama, cuatro subtablas y cuatro firmas.

## Evidencia y validaciones de la fecha

- 23 PDF Carta y 25 páginas PNG bajo los directorios `output` entonces utilizados.
- Selector con 23 opciones; centro geométrico del título sin diferencia; cero overflow en 25 páginas.
- Prueba de crecimiento de Anemómetro a 84 filas y tres páginas con encabezados repetidos y firmas al final.
- Edición conservada entre lienzo y vista PDF; Calibradores con filas dinámicas; navegación por teclado.
- Consola sin errores, build correcto con advertencia de chunk y cinco pruebas `unittest` correctas.

## Límites y pendientes registrados entonces

- No había persistencia ni conexión al flujo operativo/backend.
- No se implementaron cálculos, tolerancias, incertidumbre, cumplimiento ni promedios automáticos.
- Quedaban etiquetas/semánticas ambiguas en General, Presión, Báscula/Balanza, Eléctrica, Reglas y Verificación.
- El diagrama de Copa requería confirmación del activo oficial.
- Los nombres de los seis bloques eléctricos permanecían configurables.

Parte de la integración operativa se implementó después. Por ello esta lista no debe copiarse como pendiente actual; sólo los elementos presentes en el registro canónico de observaciones siguen abiertos.
