# Laboratorio permanente de Hojas de Campo

Fecha de validación: 2026-07-13

## Acceso

- Ruta principal: `/dashboard/field-sheet-lab`
- Alias: `/dashboard/field-sheet-preview`
- El laboratorio no requiere una sesión activa y no consulta ETS, equipos, certificados, API ni base de datos.

## Alcance disponible

- Plantillas: las 23 hojas oficiales de MYC, desde Anemómetro hasta Copa.
- Datos simulados editables de cliente, instrumento, fechas, unidades, condiciones ambientales, observaciones, resultados y firmas.
- Cambio entre las 23 plantillas sin recargar la página.
- Alta y eliminación de filas por sección.
- Navegación de celdas con `Tab`, `Shift+Tab`, flechas y `Enter`.
- Inspector de plantilla, versión, familia, bloques, tabla, snapshot y JSON vivo.
- Diagrama `Mostrar estructura` generado desde `template.blocks`; no contiene una secuencia paralela escrita a mano.
- Vista PDF e impresión con la misma instancia declarativa de `FieldSheetLayout` que usa el lienzo. No existe un renderer alterno para la vista previa.

## Datos y persistencia

Todo el estado vive en memoria dentro de `FieldSheetLabPage`. Al cambiar de plantilla se crea un documento mock independiente y `Reiniciar` recupera sus valores iniciales. Esta página no crea ni modifica registros persistentes.

El inspector diferencia:

- `Snapshot generado`: copia inmutable de la definición de plantilla al crear el documento local.
- `JSON actual`: valores, filas y firmas que cambian durante la captura.

## Validación ejecutada

- Carga directa sin autenticación ni redirección a login.
- Cambio sucesivo entre las 23 plantillas sin recarga.
- Edición de `Empresa Demo` a `Empresa QA` conservada en lienzo y vista PDF.
- Calibradores: tres secciones visibles; alta de una fila en Exteriores de 7 a 8 filas.
- Navegación con `ArrowRight` desde `Patrón` hacia `IBC 1`.
- Eléctrica y TLD 6 Canales: dos páginas reales con encabezado de continuación.
- TLD: una página, sin hoja residual.
- Copa: composición especializada con diagrama, subtablas y cuatro firmas.
- Vista PDF abierta como diálogo con dos representaciones simultáneas del mismo `FieldSheetLayout` y el mismo estado.
- Estructura ensamblada visible desde `DocumentHeader` hasta `DocumentFooter`.
- Consola del navegador: cero errores.
- `npm run build`: correcto; permanece únicamente la advertencia conocida por tamaño de chunk.

## Límites deliberados

- `Vista PDF` usa impresión del navegador porque esta fase no debe consumir el generador backend. La composición documental sí usa el renderer compartido previsto por el motor.
- Los datos se reinician al recargar la página.
- No se implementan cálculos metrológicos, selección de patrones, criterios ni fórmulas automáticas.
