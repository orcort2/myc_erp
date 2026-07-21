> Estado: AUDITORÍA
>
> Tipo: Auditoría
>
> Autoridad: Media; diagnóstico puntual del 2026-07-17
>
> Prevalece sobre: ninguno
>
> Estado vigente relacionado: `../project/PROJECT_STATUS.md` y `../project/OBSERVATIONS_REGISTER.md`

# Auditoría técnica — Paquete de Captura

Fecha: 2026-07-17. Alcance: inspección, sin correcciones nuevas al flujo de descarga.

## Evidencia observada

El ETS de prueba es `OSMYC-26-07-0003`, OT `7006` (id `3`), con equipo `manos` (id `1`). La ejecución directa y de sólo lectura de `package_summary(db, 3)` produjo:

```json
{"service_order_id":3,"folio":"OSMYC-26-07-0003","work_orders":[{"work_order_id":3,"work_order_number":7006,"ready":0,"pending":1,"blocked":[{"equipment_id":1,"equipment_name":"manos","reason":"Falta plantilla esperada de certificado"}]}],"ready_total":0}
```

Campos comprobados: alcance `accredited_iso_17025`, Hoja de Campo `completed`, próxima calibración `2026-07-24`, folio `MYCA-07-2026-0001`, nombre e identificación presentes. El equipo tiene `certificate_master_document_id=null`, `certificate_master_version_id=null`, `certificate_template_path_snapshot=null` y `certificate_template_filename_snapshot=null`. Por ello no existe Master, snapshot ni archivo Excel físico que verificar; el PDF no se intenta generar porque la elegibilidad se detiene antes.

La invocación directa `work_order_package(db, 3, 3)` produjo `HTTPException 409: No hay equipos elegibles para el paquete de Captura`; no hubo bytes, `Content-Type` ni `Content-Disposition` de descarga que puedan existir en este estado.

## Frontend y causa del síntoma

- Botones: `frontend/src/pages/ServiceOrdersPage.jsx`, handler `handleDownloadCapturePackage`.
- Primero ejecuta `getCapturePackageSummary(selectedOrder.id)`. Si `ready_total` es cero, arroja error local y **no** ejecuta `downloadCapturePackage`.
- Por ello las llamadas vistas son sólo `GET /api/service-orders/3/capture-package-summary` con `200 OK`: ese es el contrato válido de resumen bloqueado, no una descarga exitosa. No hay un `useEffect` que llame ese summary; cada llamada procede de un clic del handler.
- Sólo si hay elegibles se llama a `GET /api/service-orders/{id}/capture-package` o a `GET /api/service-orders/{id}/work-orders/{workOrderId}/capture-package`; `downloadRequest` lee Blob, `Content-Type` y `Content-Disposition`, y el handler crea `ObjectURL`. Para multipart usa `downloadMultipartCapture`.

## Backend y contrato actual

| Operación | Método y ruta | Servicio | Éxito | Sin elegibles |
| --- | --- | --- | --- | --- |
| Resumen | `GET /api/service-orders/{id}/capture-package-summary` | `package_summary` | `200 application/json` con listos/bloqueados | `200` con motivos |
| ETS | `GET /api/service-orders/{id}/capture-package` | `service_order_package` | ZIP, `application/zip`, `attachment; filename="{folio}.zip"` | `409` |
| OT | `GET /api/service-orders/{id}/work-orders/{ot}/capture-package` | `work_order_package` | 1 equipo: `multipart/mixed; boundary=MYC-CAPTURE-PACKAGE`; varios: ZIP | `409` |
| Carga | `POST /api/service-orders/{id}/capture-files` | `upload_capture_files` | JSON de archivos procesados | 404 sólo si ETS inexistente |

Para una OT con un elegible, el multipart contiene bytes PDF y bytes de Excel, ambos con `Content-Disposition` individual y el nombre base normalizado. Para varios/ETS, el ZIP agrega pares PDF/Excel, sin carpetas de OT vacías. No se pudo verificar esos bytes en la base actual porque no existe ningún equipo elegible.

## Master y snapshots

El Master se relaciona en catálogo mediante `catalog_items.expected_certificate_master_id`; al alta de equipo, `equipment.py::_snapshot_certificate_master` persiste documento, versión, ruta y nombre de plantilla. Un Master asignado al catálogo después de crear un equipo **no** completa snapshots históricos; esos equipos quedan bloqueados hasta una acción de migración/asignación explícita. `capture_packages.py::eligibility_for_equipment` comprueba además que la ruta snapshot resuelva dentro de storage y que el archivo exista antes de generar paquete.

## Diferencias, correcciones futuras y riesgos

La razón actual de que no haya descarga es de datos: falta Master/snapshot en el equipo de prueba; no es una respuesta 200 vacía de descarga. Antes de modificar frontend o backend se debe asignar un Master activo con versión y Excel real, crear o actualizar de forma controlada el snapshot del equipo, y probar PDF/Excel reales. Riesgo: poblar snapshots históricos incorrectos rompe trazabilidad documental.

Pruebas para la siguiente intervención: crear equipo nuevo desde servicio Calibración con Master activo; validar resumen `ready_total=1`; inspeccionar Network de OT única (status 200, boundary, disposiciones y tamaños); abrir ambos adjuntos; crear segundo equipo y verificar ZIP; verificar ETS ZIP y estructura; probar 409 sin elegibles; y comprobar que errores de PDF/archivo reporten bloqueo explícito.
