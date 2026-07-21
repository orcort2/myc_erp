> Estado: ARCHIVO
>
> Tipo: Archivo
>
> Autoridad: Ninguna; borrador parcial sustituido durante la reorganización
>
> Prevalece sobre: ninguno
>
> Fusionado en: `../../../project/PROJECT_STATUS.md` y `../../../project/OBSERVATIONS_REGISTER.md`

# Borrador parcial de estado de Hojas de Campo

## Pendientes reales

La integración completa solicitada no debe considerarse cerrada todavía:

1. El navegador de validación no tenía sesión ERP; falta ejecutar el E2E autenticado completo.
2. El PDF operativo backend usa el snapshot correcto, pero todavía se materializa mediante `field_sheet_engine_pdf.html`, no mediante el renderer React exacto.
3. El listado global aún no contiene todos los filtros solicitados ni abre directamente la captura.
4. Faltan acciones backend explícitas para aprobación y rechazo de la hoja, separadas del flujo actual de certificados.

Estos puntos quedaron incorporados al registro canónico de observaciones; este archivo sólo conserva el texto de origen.
