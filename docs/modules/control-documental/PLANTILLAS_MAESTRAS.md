> Estado: VIGENTE
>
> Tipo: Arquitectura vigente
>
> Autoridad: Media para el contrato técnico de Plantillas Maestras; no determina el estado del módulo
>
> Prevalece sobre: propuestas de repositorio paralelo de Masters
>
> Estado vigente relacionado: `../../project/PROJECT_STATUS.md`

# Plantillas Maestras de Certificado

El submódulo vive en **Control Documental → Plantillas Maestras** y reutiliza `ControlledDocument` con `document_type=certificate_master` y `ControlledDocumentVersion`; no crea un modelo paralelo de versiones.

Una alta recibe un XLSX, valida extensión y ZIP interno de Office (`[Content_Types].xml` y `xl/workbook.xml`), limita el archivo a 20 MB, calcula SHA-256 y lo guarda en `storage/certificate-masters/{document_id}/`. Se conserva nombre original, ruta controlada, MIME, hash, tamaño, fecha y usuario. Una versión activa requiere XLSX no caducado.

El selector de catálogo conserva `catalog_items.expected_certificate_master_id`. Al crear un equipo desde una partida cuyo servicio de Calibración coincide con el catálogo, se congela documento, versión, ruta, nombre, hash y vigencia en `equipment`; no existe backfill automático para equipos históricos.

La elegibilidad de Captura comprueba Master activo, versión activa/vigente, XLSX existente y hash del snapshot antes de producir un paquete. Aún no incluye mapeo de celdas, patrones, macros ni interpretación metrológica.

Validación real 2026-07-17: se creó `MC-PRUEBA-001`, versión `1.0`, XLSX de 4,851 bytes, SHA-256 `55cbdec67515b45d675938d608cc17ec9deaac20b82911e5f32386799343d6be`; se vinculó al servicio de calibración de prueba y el equipo nuevo `2` guardó el snapshot de documento `8` y versión `1`. El E2E completo de Hoja de Campo/PDF/paquete sigue pendiente porque requiere completar los datos técnicos de esa Hoja de Campo.
