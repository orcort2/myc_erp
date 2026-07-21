> Estado: AUDITORÍA
>
> Tipo: Auditoría
>
> Autoridad: Media; verificación puntual del 2026-07-13
>
> Prevalece sobre: ninguno
>
> Reemplazado para estado y pendientes por: `../project/PROJECT_STATUS.md` y `../project/OBSERVATIONS_REGISTER.md`

# Integración operativa de Hojas de Campo - estado verificado

Fecha: 2026-07-13

## Resultado de esta entrega

La identidad institucional ya no se simula. Laboratorio, captura operativa, snapshots nuevos y PDF backend resuelven la información desde `institutional_configurations`; las hojas históricas continúan usando su snapshot.

El flujo ETS existente ya implementaba una hoja activa por equipo, creación con apertura inmediata, captura, guardado, finalización, envío a revisión, resultados estructurados y firmas. Esta entrega amplía el selector y el contrato de creación a las 23 claves oficiales, enviando la definición completa de `officialFieldSheetTemplates.js` como snapshot inmutable.

## Identidad central vigente

- Razón social: METROLOGÍA Y SERVICIOS MYC.
- Código: FCA-30.
- Revisión: R1.
- Domicilio: Av. Cristóbal Colón 6086, Int. 57, San Pedro Tlaquepaque, Jalisco, C.P. 45601.
- Teléfono: 33 5009 2659; celular 33 1398 8169.
- Correo: contacto@mycmetrology.com.mx.
- Logotipo: `frontend/src/assets/myc-logo.png`.

Estos valores permanecen editables en Configuración > Plantillas de hojas > Identidad institucional.

## Cambios operativos

- Selector con las 23 plantillas oficiales.
- Sugerencia declarativa con prioridad servicio, tipo de instrumento, magnitud y nombre de equipo.
- Sin coincidencia segura, selección manual obligatoria; no hay fallback silencioso a General.
- Payload de creación con `template_key`, `template_version` y `template_snapshot`.
- Snapshot institucional backend al crear.
- Permisos backend `field_sheets.read`, `field_sheets.create`, `field_sheets.update` y `field_sheets.review`.
- Auditoría recibe el usuario autenticado en crear, editar, completar, revisar y cancelar.
- La creación abre directamente la pestaña de captura y precarga los datos del equipo seleccionado.
- En modo cliente facturado, empresa y domicilio se copian desde el cliente maestro al snapshot de la hoja; Atención permanece manual y editable.
- Se corrigió el error 500 causado por enviar dos veces `work_order_id` al constructor de la hoja.

## Migraciones

- `f0a1b2c3d4e5`: fundación del motor, configuración institucional, firmas y snapshot institucional.
- `f0b1c2d3e4f5`: completa la identidad real cuando faltaba o contenía un valor simulado.

## Verificación

- Frontend build: correcto.
- Backend: 7 pruebas unitarias correctas.
- Browser: 23 plantillas, identidad real presente, cero textos simulados y cero páginas con overflow.
- PDF evidencia: 23 archivos Carta en `output/pdf/field-sheet-lab/`; 21 de una página y dos de dos páginas.
- Backup: `backups/erp_myc_2026_07_13_1456.sql`.

## Pendientes reales

La integración completa solicitada no debe considerarse cerrada todavía:

1. El navegador de validación no tenía sesión ERP; falta ejecutar el E2E autenticado completo.
2. El PDF operativo backend usa el snapshot correcto, pero todavía se materializa mediante `field_sheet_engine_pdf.html`, no mediante el renderer React exacto.
3. El listado global aún no contiene todos los filtros solicitados ni abre directamente la captura.
4. Faltan acciones backend explícitas para aprobación y rechazo de la hoja, separadas del flujo actual de certificados.

Estos puntos quedan documentados para evitar presentar compilación o evidencia del laboratorio como integración operativa terminada.
