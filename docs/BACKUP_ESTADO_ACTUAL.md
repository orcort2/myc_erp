Backup de estado actual - MYC SYSTEM
Fecha: 2026-06-17
Ultima actualizacion: 2026-07-08 11:51:30 CST
Version actual: ERP MYC v0.3.0
Nombre de version: Ventas Finalizado
Version anterior: v0.2.0 (Clientes Finalizado)
Nota: desde esta version, cada actualizacion del backup debe conservar fecha y hora para tener record de cambios.
Ruta actual del proyecto
/Users/saulcortes/Desktop/myc_erp
La carpeta padre antes se llamaba ERP MYC, pero fue renombrada a myc_erp. No hay problema con el cambio. De ahora en adelante todas las rutas deben apuntar a myc_erp.
Git ya esta inicializado.
Ultimo commit conocido:
6b4954c Merge branch 'main' of https://github.com/orcort2/myc_erp
Commits recientes:
6b4954c Merge branch 'main' of https://github.com/orcort2/myc_erp
0ab66da revision
87c57cf se corrigio tema de tunel
c95c207 se esta termino de rediseñar el modulo de vetnas
b04e21d se finalizo la contrucción del modulo de clientes
ff72e7c se declara version 3, revisar backup para más info
d584ab8 se mejoro la ux del sistema
3bffe15 se construyo la orden de trbaajo, esta lista para producción
d76489b se establecieron algunos parametros para mejorar la interfaz y la conectividad del sistema, los motores de incertidumbre ya no existen en formato documental
9c368de se puso como experimental el motor de incertiudmbre
Estado Git verificado:
## main...origin/main
M README.md
M backend/app/models/service_order.py
M backend/app/routers/certificates.py
M backend/app/routers/client_portal.py
M backend/app/schemas/service_order.py
M backend/app/services/certificate_authentication.py
M backend/app/services/certificates.py
M backend/app/services/clients.py
M backend/app/services/service_orders.py
M docs/BACKUP_ESTADO_ACTUAL.md
M frontend/.env.local
M frontend/package-lock.json
M frontend/package.json
M frontend/src/pages/QuotationsPage.jsx
M frontend/src/pages/ServiceOrdersPage.jsx
M frontend/src/styles/global.css
?? backend/app/services/storage_service.py
?? backups/erp_myc_2026_07_08_1024.sql
?? backups/erp_myc_2026_07_08_1041.sql
?? backups/erp_myc_2026_07_08_1112.sql
frontend/assets/ contiene el logo original disponible localmente. La copia optimizada usada por Vite vive en frontend/src/assets/myc-logo.png.

Actualizacion 2026-07-07 16:58:10 CST - Catalogo dependiente de categoria:
- Se agregaron categorias que antes existian solo como commodity: Reparacion, Venta y Servicio general.
- Frontend: el formulario de catalogo ya no mantiene commodity como estado editable; deriva el valor legacy desde Categoria.
- Backend: reglas de alcance, leyendas e internal_key del catalogo dependen de Categoria.
- Backend: commodity queda como campo legacy de compatibilidad con base de datos/API y se deriva desde Categoria en el servicio.
- Validacion ejecutada: `npm run build` -> OK con advertencia no bloqueante de chunk mayor a 500 kB.
- Validacion ejecutada: `../venv/bin/python -m compileall app` -> OK.
- Validacion ejecutada: `git diff --check` -> OK.
- Validacion ejecutada: busqueda de textos/confirmaciones prohibidas en frontend -> sin resultados.
Backup:
- Dump SQL generado con scripts/backup-db.sh:
  backups/erp_myc_2026_07_07_1658.sql
- Tamano verificado: 671K, 6907 lineas.

Actualizacion 2026-07-07 16:56:15 CST - Refinamiento Ventas / Cotizaciones sobre ERP MYC v0.2.0:
Objetivo:
- Resolver chequeos tester pendientes de Catalogo dentro de Ventas y Cotizaciones sin crear modulos nuevos, sin reactivar modulos ocultos y sin tocar Clientes, Hojas de Campo, ETS, Certificados ni Facturacion.
Cambios principales:
- Catalogo: se removieron bloques tutoriales, chips informativos y textos operativos innecesarios.
- Catalogo: se compacto la barra de busqueda/filtros y la busqueda cubre nombre, clave, categoria y SAT.
- Catalogo: se oculto el concepto visual de commodity; el valor requerido por backend se deriva internamente desde tipo/categoria.
- Catalogo: el campo Alcance cambia por categoria y se oculta cuando no aplica.
- Catalogo: se retiro Descripcion del alta/edicion de conceptos.
- Catalogo: se mejoro el desglose visual de precio final, tipo de cambio, margen e IVA.
- Catalogo: filas completas abren el modal de edicion; las acciones Guardar, Eliminar y Cerrar quedan en encabezado del modal.
- Cotizaciones: Nueva cotizacion crea borrador y abre directamente la ficha completa.
- Cotizaciones: el cliente se puede ajustar dentro de la ficha en estados editables.
- Cotizaciones: el estado queda visible en el encabezado de la ficha.
- Cotizaciones: las acciones comerciales se muestran solo cuando aplican al estado actual.
- Cotizaciones: se agrego descripcion comercial editable por partida, independiente del catalogo, e imprimible debajo del servicio en PDF.
- Backend: se amplio compatibilidad de alcance en catalogo usando la columna existente `calibration_scope`, sin migracion.
- Backend: `QuotationUpdate` permite ajustar `client_id` en cotizaciones no terminales.
- Backend: `create_quotation` asigna `advisor_id` desde `user_id` si el router se conecta posteriormente a usuario autenticado.
- Permisos: se preparo `quotations.act_as_advisor` para Comercial y Desarrollador.
Validacion ejecutada:
- `npm run build` -> OK con advertencia no bloqueante de chunk mayor a 500 kB.
- `../venv/bin/python -m compileall app` -> OK.
- `rg -n "window\\.confirm|window\\.alert|prompt\\(" frontend/src -g '*.js' -g '*.jsx'` -> sin resultados.
- `rg -n "Commodity|Cada servicio MYC|Duplicados:|Conversion V1|Dar de baja cotización|Leyenda de cotizacion" frontend/src/pages/QuotationsPage.jsx` -> sin resultados.
- `git diff --check` -> OK.
Pendiente tecnico:
- El router de cotizaciones aun no inyecta usuario autenticado; por eso la asignacion automatica real del asesor queda preparada en servicio y permisos, pero requiere conectar `require_permission`/usuario actual en una pasada posterior.
Backup:
- Dump SQL generado con scripts/backup-db.sh:
  backups/erp_myc_2026_07_07_1656.sql
- Tamano verificado: 670K, 6903 lineas.

Actualizacion 2026-07-07 16:45:25 CST - ERP MYC v0.2.0 Clientes Finalizado:
Se declara la version estable ERP MYC v0.2.0 con nombre "Clientes Finalizado".
Version anterior:
- v0.1.0 (MVP funcional).
Estado de version:
- Modulo de clientes considerado finalizado para esta entrega.
- README actualizado para mostrar la version actual.
- frontend/package.json y frontend/package-lock.json pasan de 0.1.0 a 0.2.0.
- La rama local esta en main sincronizada con origin/main.
- Existe un archivo PDF nuevo sin trackear en storage/clientes/cliente_1/ que se conserva como parte del estado local actual y no se elimina.
Backup:
- Dump SQL generado con scripts/backup-db.sh:
  backups/erp_myc_2026_07_07_1645.sql
- Tamano verificado: 669K, 6898 lineas.

Actualizacion 2026-06-29 15:59:18 CST - Reorientacion operativa a certificados externos PDF:
Decision operativa:
- Se cancela como prioridad la generacion automatica de certificados desde el Motor de Incertidumbre.
- Los certificados finales se elaboran manualmente en Excel por Captura y se suben al ERP como PDF.
- El Motor de Incertidumbre queda experimental/no bloqueante; completar hoja de campo ya no ejecuta ni exige calculo de incertidumbre.
Flujo principal aprobado:
- Cliente -> Cotizacion -> Orden de Servicio -> Orden de Trabajo PDF -> Alta de Equipos -> Folio esperado -> Hoja de Campo digital -> Captura Excel -> Calidad -> PDF final -> Matching documental -> Liberacion al cliente.
Backend certificados externos:
- `Certificate` ahora controla certificado esperado y PDF externo.
- Campos agregados: `expected_folio`, `final_pdf_path`, `final_pdf_original_filename`, `final_pdf_uploaded_at`, `final_pdf_uploaded_by_id`, `capture_started_at`, `capture_started_by_id`, `sent_to_quality_at`, `sent_to_quality_by_id`, `quality_reviewed_at`, `quality_reviewed_by_id`, `quality_rejection_reason`, `released_to_client_at`, `released_to_client_by_id`, `external_source`, `match_status`, `match_details`, `client_visible`.
- `certificates.field_sheet_id` ahora permite NULL para reservar folio/certificado esperado antes de tener hoja de campo.
- Estados nuevos soportados: `expected`, `field_sheet_ready`, `capture_pending`, `capture_in_progress`, `ready_for_quality`, `quality_review`, `quality_rejected`, `quality_approved`, `pdf_pending`, `pdf_uploaded`, `released_to_client`, `cancelled`, `suspended`.
- Estados legacy `generated`, `approved`, `released`, `correction_requested` se conservan/mapean para compatibilidad.
Motor de matching documental:
- Nuevo servicio `backend/app/services/certificate_matching_engine.py`.
- Valida sin OCR pesado usando nombre de archivo y metadata: folio esperado, serie, identificacion interna, nombre de equipo y numero de orden de trabajo.
- Resultado guarda `match_status` y `match_details` con score, checks, warnings y errores.
- Estados de match: `pending`, `matched`, `warning`, `mismatch`, `manual_accepted`.
Endpoints nuevos:
- POST /api/certificates/{id}/start-capture
- POST /api/certificates/{id}/send-to-quality
- POST /api/certificates/{id}/quality-approve
- POST /api/certificates/{id}/quality-reject
- POST /api/certificates/{id}/upload-pdf
- POST /api/certificates/{id}/validate-pdf-match
- POST /api/certificates/{id}/release-to-client
- POST /api/certificates/{id}/manual-accept-match
- POST /api/service-orders/{id}/certificate-pdfs
- GET /api/client-portal/quotations
- GET /api/client-portal/service-orders
- GET /api/client-portal/certificates
- GET /api/client-portal/certificates/{id}/pdf
Almacenamiento:
- PDFs finales se guardan bajo `storage/certificados/{work_order_number}/`.
- Se preserva nombre original en `final_pdf_original_filename`.
Migraciones:
- `backend/migrations/versions/d5e6f7a8b9c0_external_certificate_pdf_flow.py`.
- `backend/migrations/versions/e6f7a8b9c0d1_allow_certificate_without_field_sheet.py`.
- Base actual: `e6f7a8b9c0d1 (head)`.
Auditoria:
- `certificate.capture_started`
- `certificate.sent_to_quality`
- `certificate.quality_approved`
- `certificate.quality_rejected`
- `certificate.pdf_uploaded`
- `certificate.pdf_match_validated`
- `certificate.pdf_match_manual_accepted`
- `certificate.released_to_client`
- `certificate.bulk_pdf_upload`
- `client_portal.certificate_downloaded`
Frontend:
- Nuevo modulo `Captura` en `/dashboard#captura`.
- `CapturePage.jsx` lista certificados esperados, permite iniciar captura, enviar a calidad, cargar PDF individual, cargar PDFs masivos por orden y validar match.
- `QualityPage.jsx` se actualizo para flujo externo: revisar listos para calidad, aprobar, rechazar, liberar al cliente y aceptar match manual.
- `FlowTestPage.jsx` ahora valida Cliente -> Cotizacion -> Orden -> Equipo -> Hoja -> Folio esperado -> Captura -> Calidad -> PDF -> Match -> Cliente. Incertidumbre se muestra como experimental/no bloqueante.
- `Incertidumbre` se mantiene como modulo experimental y ya no es parte obligatoria de la navegacion principal.
- `api.js` ahora soporta upload multipart para PDFs y endpoints de matching/carga masiva.
Portal cliente minimo:
- Backend expone cotizaciones visibles, ordenes no canceladas y certificados con `client_visible=true`.
- El cliente no ve hojas de campo desde estos endpoints.
- Descarga de PDF registra auditoria `client_portal.certificate_downloaded`.
Facturacion futura:
- No se implemento timbrado CFDI ni PAC.
- Se confirma preparacion existente de cliente/partidas para razon social, RFC, regimen fiscal, CP fiscal, uso CFDI, correo, domicilio, descripcion, cantidad, unidad interna, clave SAT, unidad SAT, precio, descuento, objeto impuesto, tasa IVA, subtotal/impuesto/total y moneda.
Validacion ejecutada:
- `../venv/bin/python -m compileall app` -> OK.
- `../venv/bin/alembic upgrade head` -> OK.
- `../venv/bin/alembic current` -> `e6f7a8b9c0d1 (head)`.
- `../venv/bin/python -c "from app.main import app; print(app.title, len(app.routes))"` -> `ERP MYC 29`.
- OpenAPI -> 129 paths.
- `npm run build` -> OK con advertencia no bloqueante de chunk mayor a 500 kB.
- `./scripts/myc build` -> OK.
- `./scripts/myc doctor` -> OK.
- `git diff --check` -> OK.
Pendientes / limitaciones:
- No se implemento timbrado CFDI, PAC, OCR pesado, lectura avanzada de PDFs, generacion automatica de certificados, editor Excel, firmas digitales, sellos anti plagio ni portal cliente avanzado.
- Matching actual es documental basico por filename/metadata; queda preparado para OCR futuro.

Actualizacion 2026-06-29 14:05:41 CST - Fase 3.1 refinamiento del motor de incertidumbre:
Se refino el Motor de Incertidumbre para convertirlo en un motor versionable, aprobable, auditable y usable desde frontend para pruebas funcionales del flujo real.
Arquitectura backend:
- Se mantiene `UncertaintyModel` como entidad base del modelo metrologico.
- Se agrego `UncertaintyModelVersion` como version tecnica aprobable del modelo.
- Componentes y formulas ahora soportan `model_version_id` y quedan vinculados a una version especifica.
- `UncertaintyCalculation` ahora guarda `uncertainty_model_version_id` ademas de `uncertainty_model_id`.
- `UncertaintyModelException` ahora soporta `base_model_version_id` y `alternate_model_version_id`; las excepciones activas deben apuntar a version alterna aprobada.
- `calibration_procedures` ahora soporta `uncertainty_model_version_id` para fijar version especifica o resolver automaticamente la version approved vigente desde el modelo.
Migraciones:
- `backend/migrations/versions/b3c4d5e6f7a8_add_uncertainty_engine.py` de Fase 3 sigue como base del motor inicial.
- Nueva migracion `backend/migrations/versions/c4d5e6f7a8b9_version_uncertainty_models.py`.
- Tablas nuevas: `uncertainty_model_versions`.
- Campos nuevos: `uncertainty_components.model_version_id`, `uncertainty_formulas.model_version_id`, `calibration_procedures.uncertainty_model_version_id`, `uncertainty_model_exceptions.base_model_version_id`, `uncertainty_model_exceptions.alternate_model_version_id`, `uncertainty_calculations.uncertainty_model_version_id`.
- La migracion mueve datos existentes de modelo/componentes/formulas hacia una version inicial por modelo.
Reglas implementadas:
- Solo versiones `approved` pueden usarse para calculos automaticos.
- Versiones aprobadas no se editan directamente; se clonan para cambios.
- Versiones `draft` pueden editarse.
- Flujo de estados: `draft`, `in_review`, `approved`, `obsolete`, `archived`.
- Enviar a revision, aprobar, obsoletar, archivar y clonar quedan auditados.
- Los calculos historicos conservan snapshot con codigo de modelo, id/version exacta, estado al calcular, componentes, formulas, entradas, resultados, patron, certificado, incertidumbre, hoja, equipo y procedimiento.
Endpoints nuevos/refinados:
- GET /api/uncertainty/models
- POST /api/uncertainty/models
- GET /api/uncertainty/models/{model_id}
- PATCH /api/uncertainty/models/{model_id}
- GET /api/uncertainty/models/{model_id}/versions
- POST /api/uncertainty/models/{model_id}/versions
- GET /api/uncertainty/model-versions/{version_id}
- PATCH /api/uncertainty/model-versions/{version_id}
- POST /api/uncertainty/model-versions/{version_id}/submit-review
- POST /api/uncertainty/model-versions/{version_id}/approve
- POST /api/uncertainty/model-versions/{version_id}/obsolete
- POST /api/uncertainty/model-versions/{version_id}/archive
- POST /api/uncertainty/model-versions/{version_id}/clone
- POST /api/uncertainty/model-versions/{version_id}/components
- PATCH /api/uncertainty/components/{component_id}
- DELETE /api/uncertainty/components/{component_id}
- POST /api/uncertainty/model-versions/{version_id}/formulas
- PATCH /api/uncertainty/formulas/{formula_id}
- DELETE /api/uncertainty/formulas/{formula_id}
- GET /api/uncertainty/exceptions
- POST /api/uncertainty/exceptions
- GET /api/uncertainty/field-sheets/{field_sheet_id}/preview
Permisos:
- Se agrego `uncertainty_models.approve`.
- Calidad y Desarrollador pueden aprobar, obsoletar y archivar versiones.
- Tecnico y Captura conservan ejecucion de preview/calculo, sin modificar modelos.
Frontend:
- Nueva pagina `frontend/src/pages/UncertaintyPage.jsx`.
- Nuevo modulo/navegacion `Incertidumbre` en `/dashboard#incertidumbre`.
- Permite listar modelos, crear modelo, ver versiones, crear version, agregar componentes, agregar formulas, enviar a revision, aprobar, obsoletar, clonar y probar preview con hoja de campo.
- Nueva pagina `frontend/src/pages/FlowTestPage.jsx`.
- Nuevo modulo/navegacion `Prueba de flujo` en `/dashboard#prueba-flujo`.
- Permite auditar visualmente Cliente -> Cotizacion -> Orden -> Equipo -> Hoja -> Procedimiento -> Perfil -> Patron -> Certificado -> Modelo -> Version -> Preview.
- La vista muestra mensajes claros cuando falta procedimiento, patron, certificado, version aprobada, resultados o incertidumbre aplicable.
- `ProceduresPage.jsx` ahora permite asignar modelo de incertidumbre y version aprobada/resolucion automatica al procedimiento.
- `api.js` queda extendido con endpoints del motor versionado y preview.
Validacion ejecutada:
- `../venv/bin/python -m compileall app` -> OK.
- `../venv/bin/alembic upgrade head` -> OK, aplico `c4d5e6f7a8b9`.
- `../venv/bin/alembic current` -> `c4d5e6f7a8b9 (head)`.
- `../venv/bin/python -c "from app.main import app; print(app.title, len(app.routes))"` -> `ERP MYC 28`.
- `npm run build` en frontend -> OK con advertencia no bloqueante de chunk mayor a 500 kB.
- `./scripts/myc build` -> OK fuera del sandbox por conexion local a PostgreSQL.
- `./scripts/myc doctor` -> OK fuera del sandbox; dentro del sandbox PostgreSQL local fue bloqueado con `Operation not permitted`.
Pendientes / limitaciones:
- No se implemento PDF final de certificado, firmas, sellos, QR, portal cliente, facturacion, OCR, lectura automatica de PDF ni editor visual avanzado tipo Excel.
- La UI de incertidumbre es minima de prueba, no editor avanzado.
- La auditoria visual depende de datos existentes capturados en el ERP; si faltan relaciones, la vista reporta el faltante.

Actualizacion 2026-06-29 13:41:26 CST - Fase 3 motor de incertidumbre:
Se implemento el Motor de Incertidumbre en backend, sin interfaz grafica completa, para calcular automaticamente incertidumbre desde hoja de campo, equipo, procedimiento, patron seleccionado, certificado vigente e incertidumbre aplicable.
Backend nuevo:
- Modelo `UncertaintyModel` en `backend/app/models/uncertainty.py`.
- Modelo `UncertaintyComponent` para componentes configurables por modelo.
- Modelo `UncertaintyFormula` para formulas configurables como expresiones seguras.
- Modelo `UncertaintyModelException` para asociar un modelo alternativo por excepcion tecnica autorizada.
- Modelo `UncertaintyCalculation` para guardar snapshot completo de entradas, componentes, formulas, resultados, advertencias y errores.
- Campo `uncertainty_model_id` en `calibration_procedures` para resolver el modelo desde el servicio/procedimiento.
- Relacion `FieldSheet.uncertainty_calculations`.
Servicios:
- `backend/app/services/uncertainty_engine.py`.
- Preview no persistente por hoja de campo.
- Calculo persistente automatico al completar una hoja de campo.
- Evaluacion segura de expresiones con funciones permitidas: `sqrt`, `combined`, `expanded`, `average`, `abs`, `min`, `max`, `round`, `pow`.
- Componentes automaticos iniciales soportados: incertidumbre del patron, resolucion del patron, resolucion del IBC, repetibilidad, valor fijo y expresion.
- El calculo conserva trazabilidad: equipo, procedimiento, modelo, excepcion aplicada, patron, certificado, incertidumbre seleccionada, filas de medicion, componentes y formulas.
Endpoints nuevos:
- GET /api/uncertainty/models
- POST /api/uncertainty/models
- GET /api/uncertainty/models/{model_id}
- PATCH /api/uncertainty/models/{model_id}
- POST /api/uncertainty/models/{model_id}/components
- PATCH /api/uncertainty/models/{model_id}/components/{component_id}
- POST /api/uncertainty/models/{model_id}/formulas
- PATCH /api/uncertainty/models/{model_id}/formulas/{formula_id}
- GET /api/uncertainty/exceptions
- POST /api/uncertainty/exceptions
- GET /api/uncertainty/field-sheets/{field_sheet_id}/preview
Permisos:
- `uncertainty.execute`
- `uncertainty_models.read`
- `uncertainty_models.create`
- `uncertainty_models.update`
- `uncertainty_models.exception`
- Tecnico y Captura pueden ejecutar preview/calculo.
- Calidad y Desarrollador pueden configurar modelos y excepciones.
Migracion:
- `backend/migrations/versions/b3c4d5e6f7a8_add_uncertainty_engine.py`.
- Ejecutada localmente con `../venv/bin/alembic upgrade head`.
- Resultado: `Running upgrade a2b3c4d5e6f7 -> b3c4d5e6f7a8, add uncertainty engine`.
- `../venv/bin/alembic current` -> `b3c4d5e6f7a8 (head)`.
Validacion ejecutada:
- desde backend: `../venv/bin/python -m compileall app` -> OK.
- desde backend: `../venv/bin/python -c "from app.main import app; print(len(app.routes)); print('OK')"` -> 28, OK.
- consulta DB de `UncertaintyModel` -> OK.
Notas:
- No se implemento editor visual de formulas, interfaz grafica completa, certificados, PDFs, sellos, firmas, liberacion ni flujo de Calidad/Captura.
- `scripts/myc` sigue no rastreado y no fue modificado por esta fase.

Actualizacion 2026-06-26 17:05:51 CST - Fase 2 motor de patrones, certificados de patron y selector inteligente:
Se profundizo el modulo de patrones separando patron fisico de certificado metrologico vigente/historico, manteniendo compatibilidad con `reference_standards` y `reference_standard_uncertainties`.
Backend nuevo:
- Modelo `ReferenceStandardCertificate` en `backend/app/models/reference_standard_certificate.py`.
- Modelo `ReferenceStandardCertificateUncertainty` para incertidumbres por certificado vigente/historico.
- Relacion `ReferenceStandard.certificates` y propiedades resumen de certificado vigente: `current_certificate_id`, `current_certificate_number`, `current_certificate_expiration_date`, `current_certificate_status`.
- Campos historicos en `field_sheet_reference_standards`: `reference_standard_certificate_id`, `selected_uncertainty_id`, `selection_status`, `selection_notes`, `validation_snapshot`.
- Schemas en `backend/app/schemas/reference_standard_certificate.py` y `backend/app/schemas/pattern_selection.py`.
- Servicio `backend/app/services/reference_standard_certificates.py`.
- Servicio `backend/app/services/pattern_selection_engine.py`.
- Routers `backend/app/routers/reference_standard_certificates.py` y `backend/app/routers/pattern_selection.py`.
- Registro de routers en `backend/app/main.py`; la app queda con 27 rutas.
Migracion:
- `backend/migrations/versions/a2b3c4d5e6f7_add_reference_standard_certificates.py`.
- Ejecutada localmente con `../venv/bin/alembic upgrade head`.
- Resultado: `Running upgrade f1a2b3c4d5e6 -> a2b3c4d5e6f7, add reference standard certificates`.
- Verificacion DB: `cert_tables 2`, `snapshot_columns 5`.
Reglas implementadas:
- Un patron puede tener multiples certificados historicos.
- Solo un certificado queda vigente por patron mediante indice unico parcial `uq_reference_standard_current_certificate`.
- Activar certificado marca `is_current=true`, `status=active`, obsoleta/desmarca certificados vigentes anteriores y no permite activar vencidos.
- La incertidumbre aplicable se obtiene desde el certificado vigente, con compatibilidad legada intacta.
- Al agregar patrones a una hoja, si existe certificado vigente se guarda snapshot inicial con certificado e incertidumbre asociada.
Selector inteligente:
- Endpoint `POST /api/pattern-selection/candidates`.
- Endpoint `POST /api/field-sheets/{field_sheet_id}/suggest-patterns`.
- Endpoint `POST /api/field-sheets/{field_sheet_id}/validate-selected-patterns`.
- Evalua magnitud, estado activo, certificado vigente, vencimiento, rango requerido, perfil tecnico, patrones permitidos/preferidos e incertidumbre aplicable.
- Devuelve candidatos, recomendaciones, warnings, errores y explicacion.
Permisos:
- `reference_standard_certificates.read`
- `reference_standard_certificates.create`
- `reference_standard_certificates.update`
- `reference_standard_certificates.approve`
- `pattern_selection.execute`
- Calidad y Desarrollador pueden administrar certificados de patron y ejecutar selector.
- Tecnico y Captura pueden leer certificados de patron y ejecutar selector.
Frontend:
- `StandardsPage.jsx` ahora incluye seccion Certificados del Patron dentro del modal de patron.
- Permite listar, crear, editar, activar y suspender certificados de patron.
- Permite agregar y editar incertidumbres por rango dentro del certificado del patron.
- `ServiceOrdersPage.jsx` agrega botones `Sugerir patrones` y `Validar patrones seleccionados` en la hoja de campo.
- Muestra recomendados, certificados vigentes, vencimientos, incertidumbre aplicable, warnings y errores sin bloquear el flujo.
- API frontend extendida en `frontend/src/services/api.js`.
Auditoria:
- `reference_standard_certificate.created`
- `reference_standard_certificate.updated`
- `reference_standard_certificate.activated`
- `reference_standard_certificate.suspended`
- `reference_standard_certificate.uncertainty.created`
- `reference_standard_certificate.uncertainty.updated`
- `reference_standard_certificate.uncertainty.deactivated`
- `pattern_selection.candidates_generated`
- `field_sheet.patterns_validated`
Validacion ejecutada:
- `venv/bin/python -m compileall backend/app` -> OK.
- desde backend: `../venv/bin/python -c "from app.main import app; print(app.title, len(app.routes))"` -> ERP MYC 27.
- `../venv/bin/alembic upgrade head` -> OK.
- consulta DB -> `cert_tables 2`, `snapshot_columns 5`.
- `npm run build` en frontend -> OK.
Notas:
- No se implemento PDF final de certificado, OCR, IA para leer documentos, sellos ni firmas digitales.
- No se elimino ni modifico destructivamente `reference_standard_uncertainties`; queda como legado compatible.

Actualizacion 2026-06-26 16:53:47 CST - Fase 1 nucleo documental y motor base:
Se implemento la base documental del sistema sobre la arquitectura actual, sin crear proyecto nuevo y sin modificar el flujo operativo existente.
Backend nuevo:
- Modelo `ControlledDocument` en `backend/app/models/controlled_document.py`.
- Modelo `ControlledDocumentVersion` con versionamiento documental y una sola version activa por documento.
- Modelo `DocumentInterpretation` para interpretacion ejecutable de documentos.
- Modelo `TechnicalProfile` para perfil tecnico de calibracion.
- Modelo `TechnicalProfileAllowedPattern` conectado inicialmente a `reference_standards` como tabla formal de patrones.
- Schemas en `backend/app/schemas/controlled_document.py`.
- Servicios en `backend/app/services/controlled_documents.py`, `document_interpretations.py` y `technical_profiles.py`.
- Routers en `backend/app/routers/documents.py`, `document_interpretations.py` y `technical_profiles.py`.
- Registro de routers en `backend/app/main.py`; la app queda con 25 rutas.
Migracion:
- `backend/migrations/versions/f1a2b3c4d5e6_add_documental_core.py`.
- Ejecutada localmente con `../venv/bin/alembic upgrade head`.
- Resultado: `Running upgrade e5f6a7b8c9d0 -> f1a2b3c4d5e6, add documental core`.
Datos semilla:
- 7 documentos controlados: MDG-01, FCA-02, PMP-01, FCA-15-7, FPV-01, FCA-22, FCA-18-1.
- 1 perfil tecnico: PT-PRESION-MANOMETRO-ACR-001.
- Verificacion directa en DB: documents 7, profiles 1.
Permisos:
- Se agregaron permisos `documents.*`, `document_interpretations.*` y `technical_profiles.*`.
- Administrador conserva `*`.
- Calidad puede crear/editar/aprobar documentos, interpretaciones y perfiles.
- Tecnico, Captura y Comercial pueden leer la biblioteca documental segun alcance inicial.
Endpoints nuevos:
- GET /api/documents
- GET /api/documents/{document_id}
- POST /api/documents
- PATCH /api/documents/{document_id}
- POST /api/documents/{document_id}/versions
- POST /api/documents/{document_id}/versions/{version_id}/activate
- PATCH /api/documents/{document_id}/archive
- GET /api/document-interpretations
- GET /api/document-interpretations/{interpretation_id}
- POST /api/document-interpretations
- PATCH /api/document-interpretations/{interpretation_id}
- POST /api/document-interpretations/{interpretation_id}/approve
- POST /api/document-interpretations/{interpretation_id}/new-version
- GET /api/technical-profiles
- GET /api/technical-profiles/resolve
- GET /api/technical-profiles/{profile_id}
- POST /api/technical-profiles
- PATCH /api/technical-profiles/{profile_id}
- POST /api/technical-profiles/{profile_id}/approve
- POST /api/technical-profiles/{profile_id}/new-version
Frontend:
- Nuevo modulo visible `Biblioteca Documental` en navegacion.
- Nueva pagina `frontend/src/pages/DocumentLibraryPage.jsx`.
- Pestañas: Documentos, Interpretaciones, Perfiles Tecnicos.
- Permite listar, filtrar, crear/editar documentos, registrar versiones, activar versiones, crear/editar/aprobar interpretaciones, crear/editar/aprobar perfiles y resolver perfil tecnico por coincidencia exacta inicial.
- API frontend extendida en `frontend/src/services/api.js`.
Auditoria:
- Se audita creacion/actualizacion de documento, version creada, version activada, archivado documental, creacion/actualizacion/aprobacion/nueva version de interpretacion, creacion/actualizacion/aprobacion/nueva version de perfil tecnico.
Validacion ejecutada:
- `venv/bin/python -m compileall backend/app` -> OK.
- desde backend: `../venv/bin/python -c "from app.main import app; print(app.title, len(app.routes))"` -> ERP MYC 25.
- `../venv/bin/alembic upgrade head` -> OK.
- consulta DB semilla -> documents 7, profiles 1.
- `npm run build` en frontend -> OK.
Notas:
- No se implemento calculo de incertidumbre, seleccion inteligente real de patrones, generacion de certificados, OCR, IA de lectura PDF, firma digital ni sellos.
- `DocumentTemplate` existente se conserva para plantillas comerciales/PDF; el nuevo nucleo documental vive separado como documento controlado versionable.

Actualizacion 2026-06-26 12:24:12 CST - Fase B motores operativos/documentales:
Se agrego la primera capa backend de motores internos reutilizables sin migraciones nuevas y sin romper APIs existentes.
Archivos nuevos:
- backend/app/schemas/operational_engine.py
- backend/app/routers/operational_engines.py
- backend/app/services/operational_flow.py
- backend/app/services/document_selection_engine.py
- backend/app/services/standards_validation_engine.py
- backend/app/services/folio_engine.py
- backend/app/services/certificate_preparation_engine.py
- backend/app/services/technical_capture_engine.py
- backend/app/services/calculation_engine.py
- backend/app/services/label_engine.py
Se registro el router en backend/app/main.py.
Endpoints nuevos:
- GET /api/operational-engines/flow
- GET /api/operational-engines/field-sheets/{field_sheet_id}/document-selection
- POST /api/operational-engines/field-sheets/{field_sheet_id}/validate-standards
- POST /api/operational-engines/folios/certificates/suggest
- POST /api/operational-engines/field-sheets/{field_sheet_id}/prepare-certificate
- GET /api/operational-engines/field-sheets/{field_sheet_id}/technical-capture
- POST /api/operational-engines/calculation
- GET /api/operational-engines/certificates/{certificate_id}/label
Alcance implementado:
- Motor de flujo operativo: determina etapa actual, siguiente, acciones permitidas y bloqueadas desde OS/equipo/hoja/certificado.
- Motor de seleccion documental: resuelve plantilla de hoja, certificado y etiqueta con criterios basados en procedimiento, magnitud, equipo, servicio y tipo de certificado.
- Motor de validacion de patrones: valida patron activo, vigencia, magnitud, rango, incertidumbre y roles; devuelve VALIDO/ADVERTENCIA/ERROR.
- Motor de folios: sugiere folios MYCA/MYCT por mes, anio y consecutivo, permite fecha/consecutivo/manual y audita sugerencias.
- Motor de preparacion de certificado: crea certificado draft desde hoja completada/en revision/aprobada, sin PDF final.
- Motor de captura tecnica: checklist separado para confirmar procedimiento, plantilla, patrones y folio antes de calculo.
- Motor de calculo superior: consume metrology_engine.py y devuelve promedios, errores, incertidumbres, criterio de aceptacion y tablas estructuradas.
- Motor de etiquetas: prepara payload documental con folio, cliente, equipo, fechas, tipo y estado.
Validacion ejecutada:
- venv/bin/python -m compileall backend/app -> OK
- desde backend: ../venv/bin/python -c "from app.main import app; print(app.title, len(app.routes))" -> ERP MYC 22

Objetivo del sistema
Construir un ERP para MYC orientado al flujo real de calidad y operacion:
Lead
  -> Cotizacion
  -> Agenda
  -> Llamado
  -> Orden de Servicio
  -> Equipos
  -> Hojas de Campo
  -> Certificados
  -> Pago / Factura
  -> Encuesta / Reporte
La entidad raiz operativa debe ser:
service_orders
Todo el sistema debe girar alrededor de la orden de servicio y su expediente operativo, tecnico, documental y financiero.
Stack decidido
Backend:
FastAPI
SQLAlchemy
Alembic
PostgreSQL
Pydantic Settings
Frontend:
React
Vite
Lucide React
History API para rutas simples sin react-router
Archivos:
storage/cotizaciones
storage/certificados
storage/evidencias
storage/facturas
storage/temporales
Entorno virtual
Ya existe entorno virtual en la raiz:
venv/
No esta dentro de backend/.venv.
Para usarlo:
cd /Users/saulcortes/Desktop/myc_erp
source venv/bin/activate
Cuando se active correctamente, la terminal debe mostrar algo parecido a:
(venv) saulcortes@MacBook-Air-de-Saul myc_erp %
Si no aparece (venv) o los comandos usan el Python del sistema de macOS, significa que el entorno virtual no esta activo.
O directamente:
venv/bin/python
venv/bin/pip
venv/bin/uvicorn
Dependencias backend verificadas
Ya estan instaladas en venv/:
fastapi
uvicorn
sqlalchemy
psycopg
alembic
pydantic-settings
email-validator
python-jose
passlib
python-multipart
Jinja2
weasyprint
Dependencias frontend
Ya existe frontend/node_modules/, por lo que npm install ya fue ejecutado localmente.
Existe frontend/package-lock.json, pero esta pendiente de commit.
Para reinstalar o actualizar dependencias:
cd frontend
npm install
Estructura principal actual
backend/
  alembic.ini
  requirements.txt
  .env
  .env.example
  app/
    main.py
    core/
      config.py
      db.py
      permissions.py
      security.py
      folios.py
      init_db.py
    models/
      base.py
      user.py
      client.py
      quotation.py
      service_order.py
      equipment.py
      field_sheet.py
      certificate.py
      catalog_item.py
      document_template.py
      audit_log.py
    schemas/
      auth.py
      module.py
      user.py
      client.py
      quotation.py
      service_order.py
      equipment.py
      field_sheet.py
      certificate.py
      catalog_item.py
      document_template.py
      audit_log.py
    routers/
      auth.py
      health.py
      modules.py
      users.py
      clients.py
      quotations.py
      service_orders.py
      equipment.py
      field_sheets.py
      certificates.py
      catalog_items.py
      document_templates.py
    services/
      auth.py
      modules.py
      users.py
      clients.py
      quotations.py
      service_orders.py
      equipment.py
      field_sheets.py
      certificates.py
      catalog_items.py
      document_templates.py
      work_order_pdfs.py
      field_sheet_pdfs.py
      quotation_pdfs.py
      audit_logs.py
    templates/
      quotation_pdf.html
      work_order_pdf.html
      field_sheet_general_pdf.html
      field_sheet_electrical_pdf.html
    utils/
  migrations/
    env.py
    script.py.mako
    versions/
      c0fa71033b73_create_mvp_schema.py
      917baf3a5378_add_quotation_advisor.py
      5d6e7f8a9b10_expand_service_orders.py
      6f7a8b9c0d11_update_equipment_status.py
      7a8b9c0d1e12_create_field_sheets.py
      8b9c0d1e2f13_create_certificates.py
      9c0d1e2f3a14_add_user_roles.py
      a1b2c3d4e5f6_add_catalog_items.py
      b2c3d4e5f6a7_complete_catalog_items.py
      c3d4e5f6a7b8_add_document_templates.py
      d4e5f6a7b8c9_add_work_orders_and_field_sheet_templates.py

frontend/
  index.html
  package.json
  package-lock.json
  assets/
    Logo sin fondo MYC.png
  node_modules/
  src/
    assets/
      myc-logo.png
      myc-logo.svg
    components/
      ConfirmDialog.jsx
    main.jsx
    pages/App.jsx
    components/ModuleCard.jsx
    pages/settings/
    services/api.js
    styles/global.css
    utils/useConfirmDialog.js

storage/
  cotizaciones/
  certificados/
  evidencias/
  facturas/
  temporales/

docs/
  SISTEMA_ERP_MYC_ESPECIFICACION_V2.md
  SISTEMA_ERP_MYC_V3.md
  base-datos-mvp.md
  flujo-general.md
  reglas-negocio.md
  permisos.md
  BACKUP_ESTADO_ACTUAL.md
Backend actual
Archivo principal:
backend/app/main.py
Routers incluidos:
health
auth
audit_logs
modules
clients
quotations
service_orders
equipment
field_sheets
certificates
catalog_items
document_templates
users
Rutas base:
GET /
GET /api/health
GET /api/audit-logs
GET /api/modules
Auth:
POST /api/auth/register
POST /api/auth/login
POST /api/auth/refresh
GET /api/auth/me
Usuarios / Configuración:
POST /api/users
GET /api/users
GET /api/users/roles
PATCH /api/users/{user_id}
PATCH /api/users/{user_id}/roles
PATCH /api/users/{user_id}/status
Clientes:
GET /api/clients
POST /api/clients
GET /api/clients/{client_id}
PATCH /api/clients/{client_id}
DELETE /api/clients/{client_id}
Cotizaciones:
GET /api/quotations
POST /api/quotations
GET /api/quotations/{quotation_id}
GET /api/quotations/{quotation_id}/pdf
PATCH /api/quotations/{quotation_id}
POST /api/quotations/{quotation_id}/items
PATCH /api/quotations/{quotation_id}/items/{item_id}
DELETE /api/quotations/{quotation_id}/items/{item_id}
POST /api/quotations/{quotation_id}/send
POST /api/quotations/{quotation_id}/waiting
POST /api/quotations/{quotation_id}/accept
POST /api/quotations/{quotation_id}/reject
POST /api/quotations/{quotation_id}/expire
POST /api/quotations/{quotation_id}/cancel
DELETE /api/quotations/{quotation_id}
Ordenes de servicio:
GET /api/service-orders
POST /api/service-orders
GET /api/service-orders/{service_order_id}
GET /api/service-orders/{service_order_id}/work-order-pdf
PATCH /api/service-orders/{service_order_id}
POST /api/service-orders/{service_order_id}/confirm
POST /api/service-orders/{service_order_id}/call
POST /api/service-orders/{service_order_id}/start
POST /api/service-orders/{service_order_id}/capture
POST /api/service-orders/{service_order_id}/quality
POST /api/service-orders/{service_order_id}/pending-payment
POST /api/service-orders/{service_order_id}/release
POST /api/service-orders/{service_order_id}/close
DELETE /api/service-orders/{service_order_id}
Equipos:
GET /api/equipment
POST /api/equipment
GET /api/equipment/{equipment_id}
PATCH /api/equipment/{equipment_id}
POST /api/equipment/{equipment_id}/realizing
POST /api/equipment/{equipment_id}/calibrated
POST /api/equipment/{equipment_id}/labeled
POST /api/equipment/{equipment_id}/not-done
DELETE /api/equipment/{equipment_id}
Hojas de campo:
GET /api/field-sheets
POST /api/field-sheets
GET /api/field-sheets/{field_sheet_id}
GET /api/field-sheets/{field_sheet_id}/pdf
PATCH /api/field-sheets/{field_sheet_id}
POST /api/field-sheets/{field_sheet_id}/complete
POST /api/field-sheets/{field_sheet_id}/review
DELETE /api/field-sheets/{field_sheet_id}
Certificados:
GET /api/certificates
POST /api/certificates
GET /api/certificates/{certificate_id}
PATCH /api/certificates/{certificate_id}
POST /api/certificates/{certificate_id}/generate
POST /api/certificates/{certificate_id}/quality
POST /api/certificates/{certificate_id}/approve
POST /api/certificates/{certificate_id}/release
POST /api/certificates/{certificate_id}/request-correction
POST /api/certificates/{certificate_id}/draft
POST /api/certificates/{certificate_id}/suspend
DELETE /api/certificates/{certificate_id}
Catalogo MYC:
GET /api/catalog-items
POST /api/catalog-items
GET /api/catalog-items/{catalog_item_id}
PATCH /api/catalog-items/{catalog_item_id}
DELETE /api/catalog-items/{catalog_item_id}
Plantillas documentales:
GET /api/document-templates/quotation
PATCH /api/document-templates/quotation
POST /api/document-templates/quotation/restore-defaults
Patrones:
GET /api/reference-standards
POST /api/reference-standards
GET /api/reference-standards/{standard_id}
PATCH /api/reference-standards/{standard_id}
DELETE /api/reference-standards/{standard_id}
POST /api/reference-standards/{standard_id}/uncertainties
PATCH /api/reference-standards/{standard_id}/uncertainties/{uncertainty_id}
DELETE /api/reference-standards/{standard_id}/uncertainties/{uncertainty_id}
Procedimientos:
GET /api/calibration-procedures
POST /api/calibration-procedures
GET /api/calibration-procedures/{procedure_id}
PATCH /api/calibration-procedures/{procedure_id}
DELETE /api/calibration-procedures/{procedure_id}
Motor metrologico:
GET /api/metrology/profiles
POST /api/metrology/calculate-preview
Audit logs:
GET /api/audit-logs
Filtros disponibles:
action
entity
entity_id
user_id
limit
Los DELETE actuales hacen borrado logico, no borrado fisico.
Modulos MVP 1 definidos
auth
users
clients
quotations
service_orders
equipment
audit_logs
Modulos funcionales construidos hasta ahora:
auth
clients
quotations
service_orders
equipment
field_sheets
certificates
quality
audit_logs
catalog_items
reference_standards
calibration_procedures
metrology
document_templates
Tablas iniciales modeladas
users
roles
user_roles
clients
client_contacts
quotations
quotation_items
service_orders
service_order_items
equipment
field_sheets
certificates
audit_logs
catalog_items
reference_standards
reference_standard_uncertainties
calibration_procedures
field_sheet_reference_standards
Auth y Roles
El modulo backend ya existe con schema, service y router.
Archivos principales:
backend/app/models/user.py
backend/app/schemas/auth.py
backend/app/services/auth.py
backend/app/routers/auth.py
backend/app/core/security.py
Tablas:
users
roles
user_roles
Roles iniciales sembrados por migracion:
Administrador
Comercial
Tecnico
Captura
Calidad
Finanzas
Cliente
Desarrollador
Tokens:
access_token JWT
refresh_token JWT
token_type bearer
Hash de password:
pbkdf2_sha256 via passlib
Nota tecnica: se evito bcrypt porque la combinacion instalada passlib + bcrypt 5 falla en este entorno.
Permisos iniciales definidos en codigo:
Administrador -> *
Comercial -> clients.*, quotations.*, service_orders.*
Tecnico -> equipment.*, field_sheets.*
Captura -> certificates.create, certificates.generate, field_sheets.read
Calidad -> certificates.read, certificates.quality, certificates.approve, certificates.release, field_sheets.read, service_orders.read
Finanzas -> payments.*, invoices.*, release.*
Cliente -> portal.read
Desarrollador -> users.read, users.manage, settings.read, settings.manage, standards.*, procedures.*, metrology.execute
Ya existen helpers:
get_current_user()
require_permission(permission)
user_has_permission(user, permission)
Estado actual del modelo de roles:
El sistema sigue usando users.roles mediante user_roles como fuente operativa de permisos.
users.role_id sigue existiendo por compatibilidad legado, pero se sincroniza con el primer rol asignado.
No se elimino role_id para no romper auth, migraciones previas ni frontend existente.
Los endpoints operativos todavia no estan protegidos masivamente para no romper el flujo de desarrollo. La proteccion por permisos se debe aplicar gradualmente al construir Quality y al endurecer acciones sensibles.
Cotizaciones
La cotizacion tiene:
folio
client_id
advisor_id
status
issued_on
valid_until
subtotal
tax_total
total
notes
items
El folio de cotizacion se genera con formato:
MYC-MM-AA-0001
Impuestos de cotizacion:
Las partidas usan tax_rate por linea.
tax_object soportado: iva_16, iva_0, exempt, not_subject.
El total suma subtotal, impuesto y total por partida.
Estados permitidos:
draft
sent
waiting
accepted
rejected
expired
cancelled
Transiciones permitidas:
draft -> sent, cancelled
sent -> waiting, accepted, rejected, expired, cancelled
waiting -> accepted, rejected, expired, cancelled
accepted/rejected/expired/cancelled -> estados terminales, sin edicion
Cada alta, edicion, cambio de estado y baja logica escribe auditoria.
PDF de cotizacion implementado:
Endpoint: GET /api/quotations/{quotation_id}/pdf
Servicio: backend/app/services/quotation_pdfs.py
Plantilla: backend/app/templates/quotation_pdf.html
Motor: WeasyPrint
Respuesta: application/pdf
Content-Disposition: inline; filename="Cotizacion_<folio>_<nombre_cliente>.pdf"
El PDF usa identidad comercial de Metrologia y Servicios MYC, logo, folio, fecha de emision, vigencia, vendedor, datos de cliente, datos fiscales, partidas, leyenda por partida, subtotal, impuestos, total, total con letra, condiciones comerciales, notas y firma/autorizacion.
Control documental de plantilla:
Codigo documental: FCA-23-2
Revision: opcional, configurable desde document_templates
Emision documental: 2025-03-28
Estas variables ahora viven en document_templates y se editan desde la pestaña Plantilla cotizacion.
Ubicacion visual actual: el bloque documental se imprime pegado al extremo derecho utilizable del bloque de titulo, a la misma altura visual de COTIZACION, con padding compacto y texto alineado a la derecha para evitar sensacion de tarjeta flotante. Se retiro del pie de pagina para conservar el diseno actual del PDF y dejar el footer limpio.
El nombre de archivo se sanitiza sin acentos, con espacios reemplazados por guiones y sin caracteres invalidos.
Si la cotizacion no tiene partidas, el PDF se genera con tabla vacia y mensaje "Sin partidas registradas".
Editor de plantilla PDF implementado:
Modelo: backend/app/models/document_template.py
Tabla: document_templates
Schemas: backend/app/schemas/document_template.py
Service: backend/app/services/document_templates.py
Router: backend/app/routers/document_templates.py
Migracion: backend/migrations/versions/c3d4e5f6a7b8_add_document_templates.py
template_key de cotizacion: quotation
Campos editables:
Identidad: nombre comercial, lema, RFC, correo, sitio web, direccion, telefono
Documento: titulo, subtitulo, codigo documental, revision, fecha de emision documental
Terminos: version, condiciones comerciales, metrologicas, legales, aviso de privacidad y texto de aceptacion
Opciones: mostrar resumen, mostrar terminos completos en pagina adicional, mostrar firma de aceptacion
Si no existe registro quotation, el backend crea uno default con los valores actuales.
El PDF ahora lee document_templates y ya no depende de textos fijos en HTML para identidad, control documental ni terminos.
Ordenes de servicio
El modulo backend ya existe con schema, service y router.
Archivos principales:
backend/app/models/service_order.py
backend/app/schemas/service_order.py
backend/app/services/service_orders.py
backend/app/routers/service_orders.py
Campos principales:
folio
work_order_number
client_id
quotation_id
advisor_id
technician_id
status
agenda_date
service_date
total_equipment
completed_equipment
requires_payment
closed_at
notes
Regla nueva:
work_order_number es consecutivo interno de 4 digitos, inicia en 7001, es unico y no se reutiliza.
Estados definidos:
scheduled
confirmed
called
in_progress
technical_review
capture
quality_review
pending_payment
released
closed
cancelled
Al crear una orden desde quotation_id, se valida que la cotizacion pertenezca al cliente y se copian sus partidas activas a service_order_items.
PDF de orden de trabajo implementado:
Endpoint: GET /api/service-orders/{service_order_id}/work-order-pdf
Servicio: backend/app/services/work_order_pdfs.py
Plantilla: backend/app/templates/work_order_pdf.html
Motor: WeasyPrint
Respuesta: application/pdf
Content-Disposition: inline; filename="Orden_Trabajo_<work_order_number>_<cliente>.pdf"
El PDF de orden de trabajo muestra:
- Encabezado institucional MYC.
- Numero interno de orden de trabajo.
- Fecha.
- Cliente.
- Atencion/contacto.
- Direccion si existe en datos del cliente.
- Folio de orden de servicio.
- Tabla de hasta 10 renglones de equipos.
- Observaciones.
- Bloques de recibido, responsable MYC y referencia de cotizacion/pedido.
Equipos
El modulo backend ya existe con schema, service y router.
Archivos principales:
backend/app/models/equipment.py
backend/app/schemas/equipment.py
backend/app/services/equipment.py
backend/app/routers/equipment.py
Regla principal:
Todo equipo debe pertenecer a una service_order activa.
Campos principales:
service_order_id
service_order_item_id
status
name
brand
model
serial_number
internal_id
range_or_capacity
initial_condition
notes
Estados definidos:
registered
realizing
calibrated
labeled
not_done
cancelled
Transiciones principales:
registered -> realizing, not_done, cancelled
realizing -> calibrated, not_done, cancelled
calibrated -> labeled, not_done, cancelled
labeled/not_done/cancelled -> estados terminales
Cada alta, edicion, cambio de estado y baja logica escribe auditoria.
El modulo sincroniza contadores de la orden:
service_orders.total_equipment
service_orders.completed_equipment
Para completed_equipment cuentan equipos activos con estado:
calibrated
labeled
not_done
Hojas de Campo
El modulo backend ya existe con modelo, schema, service y router.
Archivos principales:
backend/app/models/field_sheet.py
backend/app/schemas/field_sheet.py
backend/app/services/field_sheets.py
backend/app/routers/field_sheets.py
Reglas principales:
Una hoja de campo pertenece a un equipo.
Un equipo solo puede tener una hoja de campo activa.
La hoja ahora puede trabajar con plantilla general o electrica.
Cada hoja hereda work_order_number de la orden de servicio.
No se manejan fotos ni archivos binarios en esta fase.
Plantillas soportadas:
general
electrica
Campos tecnicos y documentales actuales:
equipment_id
template_key
work_order_number
status
calibration_place
reception_date
calibration_date
next_calibration_date
environment_humidity_start
environment_humidity_end
environment_temperature_start
environment_temperature_end
equipment_general_condition
consider_equipment_deviations
units
calibrated_by
reviewed_by
report_made_by
purchase_order_or_quotation
initial_condition
final_condition
pattern_used
results
observations
evidence_notes
method
environmental_conditions
technician_notes
results_rows
Tabla nueva de resultados:
field_sheet_results
Cada fila guarda:
field_sheet_id
section_key
row_number
pattern_value
ibc_value_1
ibc_value_2
ibc_value_3
unit
notes
Estados definidos:
draft
in_progress
completed
under_review
approved
rejected
cancelled
Regla para completar:
No se puede completar si falta:
- initial_condition
- final_condition
- al menos una medicion estructurada en results_rows
- observations o evidence_notes
Al completar:
field_sheets.status -> completed
equipment.status -> calibrated
service_orders.completed_equipment se recalcula
audit_log registra el cambio
certificate_ready queda registrado en auditoria como preparacion para certificado futuro
PDF de hoja de campo implementado:
Endpoint: GET /api/field-sheets/{field_sheet_id}/pdf
Servicio: backend/app/services/field_sheet_pdfs.py
Plantillas:
- backend/app/templates/field_sheet_general_pdf.html
- backend/app/templates/field_sheet_electrical_pdf.html
Motor: WeasyPrint
Respuesta: application/pdf
Content-Disposition: inline; filename="Hoja_Campo_<work_order_number>_<equipo>.pdf"
Comportamiento PDF:
- General: 1 pagina con datos de recepcion, calibracion, condiciones, tabla principal de 10 renglones y firmas.
- Electrica: 2 paginas; primera con cabecera y tabla principal de 5 renglones, segunda con 5 secciones complementarias de 5 renglones cada una.
Certificados
El modulo backend ya existe con modelo, schema, service y router.
Archivos principales:
backend/app/models/certificate.py
backend/app/schemas/certificate.py
backend/app/services/certificates.py
backend/app/routers/certificates.py
Relacion principal:
Service Order
  -> Equipment
  -> Field Sheet
  -> Certificate
Un certificado pertenece a:
service_order_id
equipment_id
field_sheet_id
Campos principales:
folio
service_order_id
equipment_id
field_sheet_id
certificate_type
status
issued_on
released_on
title
notes
Tipos de certificado:
acreditado -> folio MYCA-MM-AAAA-XXXX
trazable -> folio MYCT-MM-AAAA-XXXX
Estados definidos:
draft
generated
quality_review
correction_requested
approved
released
cancelled
suspended
Reglas principales:
La orden de servicio debe estar activa.
El equipo debe pertenecer a la orden indicada.
El equipo debe estar calibrated o labeled.
La hoja de campo debe pertenecer al equipo indicado.
La hoja de campo debe estar completed, under_review o approved.
Una hoja de campo solo puede tener un certificado activo.
Regla arquitectonica principal
Nada critico se borra realmente.
Las entidades operativas usan:
is_active
deleted_at
deleted_by
Migraciones Alembic
Migraciones actuales:
c0fa71033b73_create_mvp_schema.py
917baf3a5378_add_quotation_advisor.py
5d6e7f8a9b10_expand_service_orders.py
6f7a8b9c0d11_update_equipment_status.py
7a8b9c0d1e12_create_field_sheets.py
8b9c0d1e2f13_create_certificates.py
9c0d1e2f3a14_add_user_roles.py
a1b2c3d4e5f6_add_catalog_items.py
b2c3d4e5f6a7_complete_catalog_items.py
c3d4e5f6a7b8_add_document_templates.py
d4e5f6a7b8c9_add_work_orders_and_field_sheet_templates.py
La segunda migracion agrega:
quotations.advisor_id
indice ix_quotations_advisor_id
foreign key hacia users.id
La tercera migracion amplia ordenes de servicio:
advisor_id
technician_id
scheduled_date -> agenda_date
service_date
total_equipment
completed_equipment
requires_payment
foreign keys hacia users.id
La cuarta migracion actualiza estados iniciales de equipos:
equipment.status: pending -> registered
La quinta migracion crea hojas de campo:
field_sheets
foreign key hacia equipment.id
indice unico parcial uq_field_sheets_active_equipment para impedir mas de una hoja activa por equipo
La sexta migracion crea certificados:
certificates
foreign keys hacia service_orders.id, equipment.id y field_sheets.id
indice unico parcial uq_certificates_active_field_sheet para impedir mas de un certificado activo por hoja de campo
folio unico
La septima migracion agrega roles funcionales:
user_roles
roles iniciales
migracion de users.role_id hacia user_roles cuando exista role_id
La migracion d4e5f6a7b8c9_add_work_orders_and_field_sheet_templates.py agrega:
service_orders.work_order_number unico e indexado
backfill consecutivo desde 7001 para ordenes existentes
field_sheets.template_key
field_sheets.work_order_number
field_sheets metadatos documentales y ambientales
field_sheet_results con unicidad por hoja + seccion + renglon
backfill de work_order_number y referencia documental en hojas existentes
siembra de renglones por defecto:
- general -> 10
- electrica -> 30 distribuidos en 6 secciones
Estado de PostgreSQL local verificado:
alembic current -> e5f6a7b8c9d0 (head)
Verificacion backend
Verificaciones ejecutadas correctamente:
../venv/bin/python -m compileall app
../venv/bin/alembic upgrade head
../venv/bin/alembic heads
../venv/bin/alembic current
npm run build
Prueba con fastapi.testclient.TestClient contra la base local:
GET / -> 200
GET /api/health -> 200
GET /api/service-orders -> 200 []
GET /api/equipment -> 200 []
GET /api/field-sheets -> 200 []
GET /api/certificates -> 200 []
Auth rollback: register 200 Tecnico, me 200, login 200 Tecnico, refresh 200 bearer
Flujo rollback: client 201, service_order 201, equipment 201 registered, field_sheet 201 draft, complete_missing 422, patch 200 in_progress, complete 200 completed, equipment_after_complete 200 calibrated, review 200 under_review
Flujo rollback certificado: client 201, service_order 201, equipment 201 registered, field_sheet 201 draft, field_sheet_patch 200 in_progress, field_sheet_complete 200 completed, certificate 201 MYCA-06-2026-0001 draft, generate 200 generated, quality 200 quality_review, approve 200 approved, release 200 released
PDF cotizacion: generate_quotation_pdf -> b'%PDF', endpoint TestClient GET /api/quotations/4/pdf -> 200 application/pdf, filename Cotizacion_MYC-06-26-0004_Demo-MYC.pdf, 44284 bytes. Verificacion HTML: document-control dentro de title=True, document-control en footer=False. Verificacion visual con qlmanage: primera pagina renderizada correctamente con el codigo documental pegado al extremo derecho del bloque de cotizacion.
PDF cotizacion verificacion posterior: generate_quotation_pdf -> b'%PDF', filename Cotizacion_MYC-06-26-0004_Demo-MYC.pdf, 44279 bytes. Verificacion HTML: document-control usa right: 0, text-align: right y padding compacto. Verificacion visual con qlmanage: primera pagina renderizada correctamente con el codigo documental alineado al borde derecho del contenido y sin afectar titulo, subtitulo, folio, emision, vigencia ni vendedor.
Plantilla documental: TestClient GET /api/document-templates/quotation -> 200 FCA-23-2, PATCH document_revision -> 200, PDF posterior -> 200 application/pdf 44275 bytes
Flujo cierre cotizaciones: TestClient creo cliente 201, cotizacion 201, agrego partida 200, edito partida 200, duplico partida 200, elimino partida 200 via DELETE /api/quotations/{quotation_id}/items/{item_id}, genero PDF 200 application/pdf b'%PDF', envio 200, acepto 200 y genero orden de servicio 201 copiando 1 partida activa.
Flujo frontend Ordenes de Servicio/API: TestClient creo cliente 201, cotizacion 201, agrego partida 200, envio 200, acepto 200, genero orden de servicio 201, edito orden con agenda_date/service_date 200, creo equipo 201, cambio equipo a realizing 200, GET /api/service-orders 200 y GET /api/equipment?service_order_id={id} 200 con 1 equipo.
Flujo Hoja de Campo/API: TestClient creo cliente 201, cotizacion 201, agrego partida 200, envio 200, acepto 200, genero orden de servicio 201, creo equipo 201, creo hoja de campo 201, guardo datos tecnicos 200, completo hoja 200, valido equipo_after_complete -> calibrated, envio hoja a revision 200 y queda under_review.
Flujo frontend Certificados/API: TestClient con rollback creo cliente 201, cotizacion 201, agrego partida 200, envio 200, acepto 200, genero orden de servicio 201, creo equipo 201, creo hoja de campo 201, guardo datos tecnicos 200, completo hoja 200, envio a revision 200, valido equipo_after_sheet -> calibrated, creo certificado 201 MYCT-06-2026-0001 draft, generate 200 generated, quality 200 quality_review, approve 200 approved, release 200 released.
Flujo Calidad/API: TestClient con rollback creo cliente 201, cotizacion 201, agrego partida 200, envio 200, acepto 200, genero orden de servicio 201, creo equipo 201, creo hoja de campo 201, completo hoja 200, envio hoja a revision 200, creo certificado 201 draft, generate 200 generated, quality 200 quality_review, approve 200 approved, release 200 released, GET /api/audit-logs?entity=certificates&entity_id={id} -> 200 con acciones certificate.created, certificate.generated, certificate.quality_review, certificate.approved y certificate.released.
Usuarios/Configuracion verificado 2026-06-19: `../venv/bin/python -m compileall app` OK, `../venv/bin/alembic current` -> c3d4e5f6a7b8 (head), `app.openapi()` expone `/api/users`, `/api/users/roles`, `/api/users/{user_id}`, `/api/users/{user_id}/roles` y `/api/users/{user_id}/status`, `ROLE_PERMISSIONS` conserva `Administrador -> *` y `Desarrollador -> users.read/users.manage`, prueba de servicio con usuario temporal: crear usuario -> editar usuario -> cambiar rol -> desactivar -> limpieza final OK.
Auditoria/Configuracion verificado 2026-06-19: `../venv/bin/python -m compileall app` OK, `../venv/bin/alembic current` -> c3d4e5f6a7b8 (head), `app.openapi()` expone `/api/audit-logs` con filtros `action`, `entity`, `entity_id`, `user_id` y `limit`, `npm run build` OK, prueba real con usuario temporal genero `user.created`, `user.updated`, `user.role_changed` y `user.deactivated`; registros eliminados despues de validar para no dejar ruido en base local.
Confirmaciones/Bajas logicas frontend verificado 2026-06-19: `../venv/bin/python -m compileall app` OK, `../venv/bin/alembic current` -> c3d4e5f6a7b8 (head), `npm run build` OK, busqueda `rg -n "window\\.confirm|alert\\(|prompt\\(" frontend/src` sin coincidencias.
Orden de Trabajo + Hoja de Campo documental verificado 2026-06-24:
- `../venv/bin/python -m compileall app` OK.
- `../venv/bin/alembic upgrade head` OK.
- `../venv/bin/alembic current` -> `d4e5f6a7b8c9 (head)`.
- `npm run build` OK.
- Smoke test con `fastapi.testclient.TestClient`:
  - cliente 201
  - service_order 201 con `work_order_number = 7004`
  - equipment 201
  - field_sheet 201 con `template_key = electrica`
  - PATCH field_sheet 200 con `results_rows`
  - complete 200
  - review 200 -> `under_review`
  - GET `/api/service-orders/{id}/work-order-pdf` -> 200 `b'%PDF'` 39303 bytes
  - GET `/api/field-sheets/{id}/pdf` -> 200 `b'%PDF'` 44816 bytes
  - certificate 201 `MYCT-06-2026-0001`
  - generate 200
  - quality 200
  - approve 200
  - release 200 -> `released`
Fase A - Patrones, Procedimientos y Motor Metrológico Base verificado 2026-06-25:
- `../venv/bin/python -m compileall app` OK.
- `../venv/bin/alembic upgrade head` OK.
- `../venv/bin/alembic current` -> `e5f6a7b8c9d0 (head)`.
- `npm run build` OK.
- Smoke test con `fastapi.testclient.TestClient`:
  - register admin/desarrollador 200
  - POST `/api/reference-standards` 201
  - POST `/api/reference-standards/{id}/uncertainties` 201
  - POST `/api/calibration-procedures` 201
  - POST `/api/metrology/calculate-preview` 200 con salida:
    - average 100.133333
    - error 0.133333
    - repeatability_uncertainty 0.033333
    - resolution_uncertainty 0.028868
    - combined_uncertainty 0.048419
    - expanded_uncertainty 0.096839
  - field_sheet creada con `calibration_procedure_id` y `reference_standards`
  - PATCH field_sheet 200 manteniendo relacion procedimiento/patron
  - complete 200
  - review 200
  - certificate 201
  - generate 200
  - quality 200 -> `quality_review`
  - GET `/api/certificates` 200
  - GET `/api/audit-logs` 200
Nota: TestClient muestra un warning de Starlette sobre httpx/httpx2, pero no bloquea la prueba.
Nota PDF: el sistema local no tiene Poppler global instalado, pero Codex uso el runtime empaquetado para revisar PDFs de referencia y validar estructura visual.
Prueba visual en navegador local:
Frontend Vite: http://127.0.0.1:5174/
Backend FastAPI: http://127.0.0.1:8000/
Crear usuario: Isaac Administrador -> dashboard
Dashboard muestra MYC SYSTEM, usuario Isaac Administrador y Rol: Administrador
Dashboard muestra subtitulo Sistema principal
Dashboard carga contadores reales
Dashboard muestra 10 modulos tipo app launcher
Dashboard principal no renderiza sidebar
Vistas de modulo como /dashboard#clientes renderizan sidebar con navegacion completa y fecha/hora visible
Sidebar interno ahora es colapsable/responsive:
- Desktop: visible por defecto, boton para colapsar/expandir, modo colapsado con barra delgada e iconos.
- Tablet/movil: oculto por defecto, boton menu en topbar, abre como overlay Liquid Glass.
- Overlay movil cierra con click fuera, boton X, tecla Escape o al seleccionar modulo.
El contenido principal se expande cuando el sidebar esta colapsado.
Logo cargado desde frontend/src/assets/myc-logo.png
Logout vuelve a /login
Acceso directo a /dashboard sin token vuelve a /login
Login con usuario creado vuelve a /dashboard
Responsive movil validado: dashboard sin sidebar, modulos apilados en una columna
Frontend actual
Pantalla inicial en:
frontend/src/pages/App.jsx
Refactor frontend principal completado:
frontend/src/components/AppLayout.jsx
frontend/src/components/BrandLockup.jsx
frontend/src/pages/ClientsPage.jsx
frontend/src/pages/QuotationsPage.jsx
frontend/src/pages/ServiceOrdersPage.jsx
frontend/src/pages/EquipmentPage.jsx
frontend/src/pages/FieldSheetsPage.jsx
frontend/src/pages/CertificatesPage.jsx
frontend/src/pages/QualityPage.jsx
frontend/src/pages/LoginPage.jsx
frontend/src/pages/DashboardHome.jsx
frontend/src/pages/ModulePage.jsx
frontend/src/utils/routing.js
frontend/src/pages/SettingsPage.jsx
Actualizacion refactor frontend - 2026-06-19
El refactor principal de frontend ya compila correctamente.
Verificacion:
npm run build correcto.
Dashboard levanta sin pantalla blanca.
Clientes levanta sin pantalla blanca.
Cotizaciones levanta sin pantalla blanca.
Ordenes de servicio levanta sin pantalla blanca.
Certificados levanta sin pantalla blanca.
Calidad levanta sin pantalla blanca.
EquipmentPage y FieldSheetsPage ya operan como paginas autonomas con listados reales, filtros y acciones documentales.
Correcciones manuales realizadas:
Se agregaron imports faltantes de React en paginas/componentes extraidos.
Se corrigieron hooks faltantes como useMemo, useEffect y useState.
Se corrigieron imports faltantes como ModulePage, ShieldCheck y mycLogo donde aplicaba.
App.jsx queda como orquestador minimo de sesion, rutas hash, layout y render de paginas.
Ya no hay pantallas blancas por errores de React runtime.
/login
/dashboard
Fase 1 implementada:
Login real contra POST /api/auth/login
Registro inicial contra POST /api/auth/register
Guardado de access_token y refresh_token en localStorage
Obtencion de usuario con GET /api/auth/me
Logout
Proteccion de /dashboard
Sidebar
Topbar
Layout principal
Fase 2 inicial implementada:
Dashboard modular Liquid Glass con branding MYC SYSTEM.
Dashboard muestra logo + MYC SYSTEM + Sistema principal.
Vistas de modulo muestran logo + MYC SYSTEM + fecha/hora.
En /dashboard no hay sidebar; el dashboard queda como launcher principal.
En /dashboard#modulo se activa layout de modulo con navegacion lateral.
La navegacion lateral en modulos puede colapsarse en desktop y abrirse como panel overlay en movil.
Tipografia ajustada para legibilidad: titulos 22px en modulos, descripciones 15px, mejor contraste y sin overflow en desktop/movil.
Span de bienvenida/rol en dashboard ajustado a 16.5px, mayor contraste y fondo translúcido.
Contadores reales visibles en modulos y resumen operativo:
- Clientes
- Cotizaciones
- Ordenes de servicio
- Equipos
- Hojas de campo
- Certificados
Modulo Clientes frontend iniciado:
/dashboard#clientes abre vista real de Clientes.
Consume GET /api/clients para listado.
Vista principal limpia con encabezado, boton Nuevo cliente y tabla/listado.
Tabla principal muestra columnas clave: Cliente, RFC, Contacto, Telefono, Correo, Estado y Acciones.
Listado tiene estados explicitos de carga, vacio y error.
Formulario de cliente se abre en modal Liquid Glass; no queda fijo en pantalla.
Modal de alta/edicion separado en pestanas: Datos generales, Domicilio y Datos fiscales.
Datos generales: Nombre comercial, RFC, Contacto, Telefono, Correo y Estado.
Domicilio preparado en frontend: Calle, Numero exterior, Numero interior, Colonia, Municipio/Ciudad, Estado, Codigo postal y Pais.
Datos fiscales preparados en frontend: Razon social, RFC fiscal, Codigo postal fiscal, Regimen fiscal, Uso CFDI.
Aviso fiscal visible: los datos fiscales completos se conectaran al modulo de facturacion.
Botones visuales preparados: Subir constancia fiscal y Capturar manualmente. No hay extraccion automatica todavia.
Modal de edicion reutiliza el mismo formulario, precarga datos y muestra Guardar cambios.
Validaciones frontend: Nombre comercial requerido, RFC requerido, correo valido si se captura y codigos postales solo numericos.
Botones del modal se deshabilitan durante guardado y el boton principal muestra Guardando...
Alta de cliente cableada contra POST /api/clients.
Edicion de cliente cableada contra PATCH /api/clients/{id}.
Boton Cotizacion por cliente pide confirmacion antes de llamar POST /api/quotations.
Solo se envian al backend campos soportados por schema actual: legal_name, commercial_name, rfc, phone, email, tax_regime y contacts en alta.
Contacto se crea en alta como primer contacto; backend actual no expone PATCH de contactos, domicilio ni campos CFDI dentro de ClientUpdate.
Archivo duplicado frontend/src/styles/global (1).css eliminado; estilos consolidados en frontend/src/styles/global.css.
Preparacion frontend de importacion/exportacion masiva agregada:
- Botones Importar Excel, Exportar Excel y Descargar plantilla.
- Plantilla descargable CSV compatible con Excel con campos comerciales, domicilio y fiscales.
- Exportacion CSV compatible con Excel usando datos actuales disponibles en GET /api/clients.
- Modal visual de importacion con carga de archivo, columnas detectadas/esperadas, registros validos, duplicados y errores.
- Reglas visuales: nombre comercial obligatorio, correo valido si existe, codigo postal numerico.
- Duplicados preparados por RFC, correo y nombre normalizado.
- Boton Confirmar importacion preparado sin enviar datos al backend.
- Descarga visual de errores como CSV corregible.
- Lectura real XLSX queda pendiente de parser/backend; CSV exportado desde Excel ya permite vista previa frontend.
Modulo Cotizaciones frontend iniciado:
/dashboard#cotizaciones abre vista real de Ventas / Cotizaciones.
Consume GET /api/quotations para listado y GET /api/clients para resolver nombres de cliente.
Tabla principal muestra Folio, Cliente, Asesor, Fecha emision, Vigencia, Estado y Total.
El boton Ver fue retirado; cada fila completa es clickeable y abre el detalle de cotizacion.
Las filas tienen hover/focus visible y se pueden abrir con Enter al recibir foco.
Estados visuales implementados: Draft, Sent, Waiting, Accepted, Rejected, Expired y Cancelled.
Boton Nueva cotizacion abre modal Liquid Glass.
Alta de cotizacion cableada contra POST /api/quotations con Cliente, Fecha vigencia y Notas.
Detalle de cotizacion abre modal Liquid Glass reorganizado como ficha premium:
- Encabezado con folio, cliente y badge grande de estado.
- Subpestanas internas: Informacion, Partidas e Historial.
- Resumen economico con subtotal, impuestos y total destacado.
- Datos comerciales con emision, vigencia editable, cliente y asesor.
- Notas editables.
- Acciones de estado agrupadas.
- Botones PDF agregados al modal: Vista PDF, Descargar PDF e Imprimir.
- Vista PDF abre GET /api/quotations/{quotation_id}/pdf en nueva pestana.
- Descargar PDF obtiene blob y descarga Cotizacion_<folio>.pdf.
- Imprimir abre el PDF para usar impresion del navegador.
Edicion limitada cableada contra PATCH /api/quotations/{id} para vigencia y notas.
Pestana Partidas implementada:
- Boton + Agregar partida crea una linea editable dentro de la misma tabla; ya no abre modal adicional.
- Cada linea nueva aparece como Borrador hasta guardarse.
- La linea permite buscar concepto/descripcion con datalist del Catalogo MYC por nombre, categoria o clave.
- Precarga descripcion, unidad, precio unitario, moneda, clave SAT, unidad SAT, impuesto, commodity, alcance de calibracion y leyenda de cotizacion cuando existe concepto.
- Campos editables en linea: descripcion/concepto, cantidad, unidad, precio unitario, descuento %, impuesto y leyenda de cotizacion.
- Acciones por linea borrador: Guardar partida y Cancelar borrador.
- Las partidas existentes ya permiten Editar, Guardar, Cancelar, Duplicar y Eliminar.
- Eliminar partida pide confirmacion y usa DELETE /api/quotations/{quotation_id}/items/{item_id} con baja logica y recalculo de totales.
- Duplicar partida crea un nuevo borrador editable con los mismos datos para revisar antes de guardar.
- Las partidas quedan bloqueadas en estados terminales: accepted, rejected, expired y cancelled.
- Calculo visual en tiempo real: importe, descuento, subtotal partida, impuestos por tasa de cada linea, total y total con letra.
- Integracion backend usando POST, PATCH y DELETE de quotation_items.
- Backend actual guarda service_name, description, quantity, unit, unit_price, descuento, moneda, SAT, commodity, calibration_scope, quotation_legend, tax_object y tax_rate.
- El modal advierte antes de abrir, descargar o imprimir PDF cuando la cotizacion no tiene partidas.
- Si la cotizacion esta accepted, muestra accion Generar orden de servicio.
- Generar orden de servicio llama POST /api/service-orders con client_id, quotation_id y notes; backend copia partidas activas a service_order_items.
Pestana Historial preparada visualmente con fecha de creacion, ultima actualizacion y estado actual.
Acciones visuales de estado cableadas contra endpoints existentes: send, waiting, accept, reject, expire y cancel.
Las acciones de estado piden confirmacion y se deshabilitan si la transicion no aplica.
Subpestanas internas agregadas al modulo: Cotizaciones, Catalogo MYC y Plantilla cotizacion.
Plantilla cotizacion ahora es editor configurable de PDF:
- Carga GET /api/document-templates/quotation.
- Guarda PATCH /api/document-templates/quotation.
- Restaura defaults con POST /api/document-templates/quotation/restore-defaults.
- Si falla la carga, usa valores por defecto en frontend.
- Permite editar identidad, titulo/subtitulo, codigo documental, revision, emision documental, version de terminos, condiciones comerciales, condiciones metrologicas, condiciones legales, aviso de privacidad, firma de aceptacion y opciones de visibilidad.
- Incluye vista previa visual y boton Vista PDF de prueba usando una cotizacion existente.
- La vista previa del editor replica la ubicacion del control documental junto al titulo de cotizacion para coincidir con el PDF.
Catalogo MYC ya esta conectado al backend real /api/catalog-items.
Catalogo MYC separa conceptos por Producto / Servicio y permite filtrar por tipo, categoria, moneda, estado y busqueda por nombre o clave.
Categorias visibles:
- Servicios: Calibracion, Mantenimiento, Calificacion, Validacion, Capacitacion, Consultoria.
- Productos: Patrones, Equipos, Accesorios, Consumibles.
Catalogo visual muestra Tipo, Categoria, Clave interna generada, Nombre, Clave SAT, Precio origen, Precio final MXN, Estado y Acciones.
Botones visuales agregados: Nuevo producto/servicio, Importar Excel, Exportar Excel y Descargar plantilla.
Plantilla de catalogo descargable CSV compatible con Excel.
Importacion de catalogo preparada visualmente por nombre de encabezado, no por posicion.
Validaciones visuales de importacion: nombre obligatorio, tipo obligatorio, categoria obligatoria, precio numerico, moneda valida y duplicados por nombre normalizado, clave interna y categoria + nombre.
Campos de catalogo preparados/conectados: Tipo, Commodity, Categoria, Clave interna generada por backend, Nombre, Descripcion, Clave SAT, Unidad SAT, Unidad interna, Unidad interna personalizada, Precio origen, Moneda origen, Tipo de cambio, Costo interno, Moneda de costo, Margen %, Precio final MXN, Objeto impuesto y Estado.
Reglas visibles: cada servicio MYC debe existir como concepto independiente por magnitud, alcance y precio.
Duplicados preparados visualmente por nombre normalizado, clave interna y categoria + nombre.
Multimoneda preparada en UI:
- Moneda origen.
- Precio origen.
- Tipo de cambio manual.
- Margen %.
- Precio final MXN calculado con precio_origen x tipo_cambio x (1 + margen / 100).
- Aviso visible de que la conversion automatica se conectara despues a proveedor de tipo de cambio.
Boton Nuevo producto/servicio abre modal Liquid Glass; alta/edicion se guarda contra backend.
Boton Desactivar hace baja logica contra DELETE /api/catalog-items/{catalog_item_id}.
Boton Agregar a cotizacion crea una partida borrador dentro de la cotizacion abierta; si no hay cotizacion abierta, pide abrir una primero.
Importacion CSV real conectada para Clientes y Catalogo MYC:
- Lee encabezados por nombre, no por posicion.
- Mantiene vista previa, validos, duplicados y errores.
- Confirmar importacion crea registros validos contra backend.
- Descarga errores o fallas de importacion en CSV corregible.
- XLSX directo queda pendiente; se acepta CSV compatible con Excel en esta fase.
Plantilla visual de cotizacion agregada:
- Documento usa identidad comercial "Metrologia y Servicios MYC"; no usa "MYC SYSTEM" dentro de la cotizacion.
- Logo MYC e informacion comercial de MYC alineados como encabezado institucional superior izquierdo.
- Titulo principal centrado "COTIZACION".
- Subtitulo "Propuesta comercial de servicios, calibracion y soluciones tecnicas".
- Folio, fecha de emision y vigencia en tarjetas destacadas; folio con mayor jerarquia visual.
- Datos del cliente y datos fiscales.
- Tabla de partidas con descripcion, cantidad, unidad, precio unitario, descuento e importe.
- Subtotal, impuestos/IVA, total y total con letra.
- Condiciones comerciales, notas, firmas/autorizacion preparada visualmente.
La plantilla visual ya queda preparada para consumir partidas reales de cotizacion.
PDF real e impresion ya estan conectados desde el modal de cotizacion.
Modulo Ordenes de Servicio frontend iniciado:
/dashboard#ordenes abre vista real de Ordenes de Servicio.
Consume GET /api/service-orders, GET /api/clients, GET /api/quotations, GET /api/equipment, GET /api/field-sheets y GET /api/certificates.
Vista principal muestra tabla clickeable con Folio, Cliente, Cotizacion origen, Estado, Fecha agenda, Fecha servicio, Equipos, Tecnico y Acciones.
Estados visuales implementados: scheduled, confirmed, called, in_progress, technical_review, capture, quality_review, pending_payment, released, closed y cancelled.
Al abrir una orden se muestra modal Liquid Glass con subpestanas:
- Informacion
- Equipos
- Hoja de campo
- Historial
Pestana Informacion muestra folio, cliente, cotizacion origen, asesor, tecnico, fecha agenda, fecha servicio, total de equipos, equipos completados, requiere pago, estado y notas.
Pestana Informacion ahora tambien muestra numero interno de orden de trabajo.
Edicion de orden conectada contra PATCH /api/service-orders/{service_order_id} para agenda_date, service_date, technician_id, requires_payment y notes.
La ficha ya expone acciones PDF de orden de trabajo:
- Ver orden PDF
- Descargar PDF
- Imprimir
usando GET /api/service-orders/{service_order_id}/work-order-pdf.
Acciones de estado conectadas:
- confirm
- call
- start
- capture
- quality
- pending-payment
- release
- close
Las acciones piden confirmacion y se deshabilitan segun transiciones permitidas conocidas.
Pestana Equipos conectada a backend:
- Lista equipos filtrados por service_order_id.
- Alta contra POST /api/equipment.
- Edicion contra PATCH /api/equipment/{equipment_id}.
- Baja logica contra DELETE /api/equipment/{equipment_id}.
- Cambios de estado contra realizing, calibrated, labeled y not-done.
Pestana Hoja de campo conectada:
- Desde cada equipo se puede Abrir Hoja de Campo.
- Si el equipo no tiene hoja activa, crea una con POST /api/field-sheets.
- Si ya tiene hoja activa, la abre con GET /api/field-sheets/{field_sheet_id}.
- Modal Liquid Glass amplio con subpestanas Informacion, Datos tecnicos e Historial.
- Informacion muestra orden de trabajo, orden de servicio, cliente, equipo, marca, modelo, serie, plantilla y estado actual.
- Datos tecnicos ahora conecta:
  - template_key
  - calibration_place
  - reception_date
  - calibration_date
  - next_calibration_date
  - environment_humidity_start / end
  - environment_temperature_start / end
  - equipment_general_condition
  - consider_equipment_deviations
  - units
  - calibrated_by
  - reviewed_by
  - report_made_by
  - purchase_order_or_quotation
  - initial_condition
  - final_condition
  - pattern_used
  - results como resumen libre
  - observations
  - evidence_notes
  - method
  - environmental_conditions
  - technician_notes
  - results_rows como tabla estructurada
- results_rows se presenta segun plantilla:
  - general -> 10 renglones
  - electrica -> 6 secciones, 30 renglones totales
- Guardar usa PATCH /api/field-sheets/{field_sheet_id}.
- Completar valida en frontend condicion inicial/final, resultados estructurados y observaciones o evidencia antes de llamar POST /api/field-sheets/{field_sheet_id}/complete.
- Enviar a revision usa POST /api/field-sheets/{field_sheet_id}/review.
- Al completar, backend cambia equipo a calibrated y recalcula contadores de orden.
- La hoja ya expone acciones PDF:
  - Ver PDF
  - Descargar PDF
  - Imprimir
  usando GET /api/field-sheets/{field_sheet_id}/pdf.
- Si la hoja esta completed, under_review o approved y el equipo esta calibrated o labeled, permite Crear certificado.
- Crear certificado desde Hoja de Campo pide tipo acreditado/trazable con selector y llama POST /api/certificates.
- Si ya existe certificado activo para la hoja, bloquea el boton y muestra Certificado creado.
Pestana Historial muestra creacion, ultima actualizacion, estado actual y cotizacion origen; audit_log queda preparado para conectar despues.
Modulo Equipos frontend implementado:
/dashboard#equipos abre vista autonoma de Equipos.
Consume GET /api/equipment, GET /api/service-orders, GET /api/clients, GET /api/field-sheets y GET /api/certificates.
Resumen superior muestra:
- Total equipos
- Equipos listos
- Equipos con certificado
Vista principal separa por filtros:
- Todos
- Activos
- Listos
- Cerrados
Tabla principal muestra:
- Equipo
- Cliente
- Orden
- OT
- Marca / modelo
- Serie
- Estado
- Hoja
- Certificado
Modulo Hojas de Campo frontend implementado:
/dashboard#hojas abre vista autonoma de Hojas de Campo.
Consume GET /api/field-sheets, GET /api/equipment, GET /api/service-orders, GET /api/clients y GET /api/certificates.
Resumen superior muestra:
- Total hojas
- Listas para certificado
- Con certificado
Vista principal separa por filtros:
- Todas
- Borrador
- En proceso
- Revision
- Canceladas
Tabla principal muestra:
- OT
- Orden
- Cliente
- Equipo
- Plantilla
- Estado
- Certificado
- Actualizado
- Acciones
Las hojas permiten:
- Ver PDF
- Descargar PDF
- Imprimir
- Crear certificado
Modulo Certificados frontend implementado:
/dashboard#certificados abre vista real de Certificados.
Consume GET /api/certificates, GET /api/service-orders, GET /api/equipment, GET /api/field-sheets y GET /api/clients.
Vista principal del modulo separa informacion en pestanas:
- Pendientes
- En revision
- Aprobados
- Liberados
- Todos
Pestana Pendientes muestra hojas de campo con status completed, under_review o approved que todavia no tienen certificado activo.
La vista Pendientes valida que el equipo vinculado este calibrated o labeled antes de permitir crear certificado.
Crear certificado desde Pendientes abre modal Liquid Glass con tipo de certificado acreditado/trazable y notas.
Alta de certificado conectada contra POST /api/certificates con service_order_id, equipment_id, field_sheet_id y certificate_type.
Listado de certificados muestra Folio, Cliente, Orden de Servicio, Equipo, Tipo, Estado, Fecha emision, Fecha liberacion y Acciones.
Las filas de certificados son clickeables y abren ficha de certificado.
Modal de certificado Liquid Glass amplio con subpestanas:
- Informacion
- Datos tecnicos
- Calidad
- Historial
Informacion muestra folio, tipo, cliente, orden de servicio, equipo, hoja de campo, emision, liberacion, estado y notas.
Notas editables contra PATCH /api/certificates/{certificate_id}; se bloquean en released y cancelled.
Datos tecnicos muestra en lectura la hoja de campo: condicion inicial, condicion final, patron utilizado, resultados, observaciones, evidencia/notas, metodo, condiciones ambientales y notas del tecnico.
Calidad conecta acciones:
- Generar -> POST /api/certificates/{id}/generate
- Enviar a calidad -> POST /api/certificates/{id}/quality
- Aprobar -> POST /api/certificates/{id}/approve
- Liberar -> POST /api/certificates/{id}/release
- Solicitar correccion -> POST /api/certificates/{id}/request-correction
- Regresar a borrador -> POST /api/certificates/{id}/draft
- Suspender -> POST /api/certificates/{id}/suspend
Cada accion pide confirmacion, muestra loading, propaga errores claros y refresca certificado/listados.
La ficha de certificado incluye Zona de baja con `Dar de baja certificado` usando DELETE logico /api/certificates/{certificate_id}.
La baja logica cierra modal, recarga listados y muestra notice.
No usa confirmaciones nativas del navegador.
Badges visuales implementados para draft, generated, quality_review, correction_requested, approved, released, cancelled y suspended.
Folios se muestran con jerarquia visual:
- acreditado: MYCA-MM-AAAA-XXXX
- trazable: MYCT-MM-AAAA-XXXX
Historial muestra creacion, ultima actualizacion, estado actual, orden de servicio origen, equipo origen y hoja de campo origen.
Dashboard actualiza contadores reales:
- Total certificados
- Certificados en revision
- Certificados liberados
No se construyo PDF de certificado, firma digital, facturacion, finanzas ni CRM.
Modulo Calidad frontend implementado:
/dashboard#calidad abre vista transversal para supervision de certificados.
Consume GET /api/certificates, GET /api/service-orders, GET /api/equipment, GET /api/field-sheets, GET /api/clients y GET /api/audit-logs.
Vista principal separada en pestanas:
- Pendientes
- En revision
- Aprobados
- Liberados
- Suspendidos
Pendientes muestra certificados en estados generated, quality_review y correction_requested.
Tabla principal muestra:
- Folio
- Cliente
- Orden de Servicio
- Equipo
- Tecnico
- Fecha
- Estado
Cada fila abre modal Liquid Glass de revision.
Ficha de revision incluye pestanas:
- Certificado
- Hoja de Campo
- Equipo
- Historial
Certificado muestra folio, tipo, estado y notas.
Hoja de Campo muestra condicion inicial, condicion final, patron, resultados, observaciones, metodo y condiciones ambientales.
Equipo muestra nombre, marca, modelo, serie y estado.
Historial consume audit_logs reales del backend para entity=certificates y entity_id del certificado.
Historial muestra fecha, usuario, accion, estado anterior y estado nuevo.
Acciones de Calidad conectadas:
- Aprobar -> POST /api/certificates/{id}/approve
- Solicitar correccion -> POST /api/certificates/{id}/request-correction
- Regresar a borrador -> POST /api/certificates/{id}/draft
- Suspender -> POST /api/certificates/{id}/suspend
- Liberar -> POST /api/certificates/{id}/release
Todas las acciones de Calidad usan confirmacion interna MYC; ya no se usa `window.confirm`.
Dashboard actualiza contadores:
- Certificados pendientes calidad
- Certificados aprobados
- Certificados liberados
Confirmaciones internas y bajas logicas frontend - 2026-06-19
Componente global nuevo:
- frontend/src/components/ConfirmDialog.jsx

Hook reusable nuevo:
- frontend/src/utils/useConfirmDialog.js

Reglas visuales implementadas:
- Confirmacion interna Liquid Glass para acciones sensibles.
- Cierre con Escape y click fuera solo si no esta procesando.
- Variante danger para acciones destructivas.
- Mensajes claros de baja logica: no se elimina fisicamente el registro.

Funciones API frontend activas:
- deleteClient(clientId)
- deleteQuotation(quotationId)
- deleteQuotationItem(quotationId, itemId)
- deleteServiceOrder(serviceOrderId)
- deleteEquipment(equipmentId)
- deleteFieldSheet(fieldSheetId)
- deleteCertificate(certificateId)
- deleteCatalogItem(catalogItemId)

Cobertura actual en frontend:
- Clientes: Dar de baja cliente desde tabla y modal.
- Cotizaciones: Dar de baja cotizacion, eliminar partida, desactivar catalogo y confirmaciones de acciones criticas.
- Ordenes de servicio: Dar de baja orden, dar de baja equipo, dar de baja hoja de campo y confirmaciones de cambios de estado.
- Certificados: Dar de baja certificado y confirmaciones de flujo documental.
- Calidad: confirmaciones internas para aprobar, solicitar correccion, suspender y liberar.
- Configuracion/Usuarios: confirmaciones internas para cambio rapido de rol y activacion/desactivacion.

Estado actual:
- No quedan `window.confirm`, `window.alert` ni `prompt` dentro de `frontend/src`.
- Los DELETE siguen siendo logicos y el backend conserva la validacion final.
Modulo backend Audit Logs expuesto:
Router nuevo: backend/app/routers/audit_logs.py
Schema extendido: backend/app/schemas/audit_log.py
Service extendido: backend/app/services/audit_logs.py
Ruta expuesta: GET /api/audit-logs
Filtros soportados:
- entity
- entity_id
- user_id
- limit
La respuesta ahora incluye user_name ademas de user_id para facilitar la lectura en frontend.
Modulo backend Catalogo MYC agregado:
Modelo nuevo: backend/app/models/catalog_item.py
Tabla: catalog_items
Schemas: backend/app/schemas/catalog_item.py
Service: backend/app/services/catalog_items.py
Router: backend/app/routers/catalog_items.py
Router registrado en backend/app/main.py bajo /api/catalog-items.

Endpoints:
GET    /api/catalog-items
POST   /api/catalog-items
GET    /api/catalog-items/{catalog_item_id}
PATCH  /api/catalog-items/{catalog_item_id}
DELETE /api/catalog-items/{catalog_item_id}

Filtros GET:
item_type
commodity
category
origin_currency
tax_object
is_active
search

Search busca en:
name
internal_key
description
category
sat_key
sat_unit

Campos principales:
item_type
commodity
category
internal_key
name
description
sat_key
sat_unit
internal_unit
custom_internal_unit
origin_price
origin_currency
exchange_rate
margin_percent
final_price_mxn
internal_cost
cost_currency
calibration_scope
quotation_legend
tax_object
tax_rate

Reglas implementadas:
- item_type permitido: product, service.
- commodity permitido: calibration, maintenance, repair, sale, general_service.
- calibration_scope permitido: accredited_iso_17025, traceable, accredited_linked_lab o null.
- internal_unit permitido: service, piece, equipment, hour, day, package, lot, meter, kilogram, liter, other.
- tax_object permitido: iva_16, iva_0, exempt, not_subject.
- tax_object default: iva_16.
- tax_rate se normaliza automaticamente: iva_16 -> 16, iva_0/exempt/not_subject -> 0.
- internal_key ya no se captura manualmente; se genera en backend.
- Formatos de internal_key: SER-CAL-0001, SER-MAN-0001, SER-REP-0001, SER-GEN-0001 y PRO-VEN-0001.
- Si item_type = product, commodity debe ser sale.
- Si item_type = service, commodity no debe ser sale.
- Si commodity = calibration, calibration_scope es obligatorio.
- Si commodity != calibration, calibration_scope debe ser null.
- Si internal_unit = other, custom_internal_unit es obligatorio.
- final_price_mxn se calcula como origin_price * exchange_rate * (1 + margin_percent / 100).
- final_price_mxn puede recibirse, pero se recalcula al cambiar origin_price, exchange_rate o margin_percent.
- quotation_legend se autogenera para calibration, maintenance, repair y sale.
- general_service exige quotation_legend manual.
- Alta, edicion y baja logica escriben audit_log.

## Módulo Configuración implementado - 2026-06-19

Ruta activa:

```text
/dashboard#configuracion
Backend actual de usuarios:
backend/app/core/permissions.py
backend/app/schemas/user.py
backend/app/services/users.py
backend/app/routers/users.py
backend/app/services/auth.py
backend/app/models/audit_log.py
backend/app/schemas/audit_log.py
backend/app/services/audit_logs.py
backend/app/routers/audit_logs.py
Endpoints activos:
POST /api/users
GET /api/users
GET /api/users/roles
PATCH /api/users/{user_id}
PATCH /api/users/{user_id}/roles
PATCH /api/users/{user_id}/status
GET /api/audit-logs
Blindajes implementados:
No permite quitarse a si mismo el rol Administrador.
No permite quitar el rol Administrador al ultimo administrador activo.
No permite desactivar al ultimo administrador activo.
No permite que un administrador desactive su propia cuenta.
require_permission() sigue operando con ROLE_PERMISSIONS desde backend/app/core/permissions.py.
Administrador conserva "*".
users.read y users.manage quedan definidos para el rol Desarrollador.
audit_logs.read queda disponible para el rol Desarrollador.
Frontend actual:
frontend/src/pages/SettingsPage.jsx
frontend/src/pages/settings/UsersSettingsPanel.jsx
frontend/src/pages/settings/AuditSettingsPanel.jsx
frontend/src/pages/settings/UserModal.jsx
frontend/src/services/api.js
Funciones frontend activas:
Navegacion interna de Configuracion:Usuarios
Auditoria

Listado real de usuarios y roles.
Boton Nuevo usuario.
Modal de creacion con nombre completo, correo, contraseña y rol.
Modal de edicion por fila con nombre completo, correo, rol y estado activo/inactivo.
Cambio rapido de rol desde selector dentro de la tabla.
Activar/desactivar usuario desde boton rapido.
Guardado contra createUser(payload) y updateUser(userId, payload).
Recarga/actualizacion local del listado y mensajes claros de exito/error.
Estilo visual coherente con el ERP usando modal Liquid Glass, tabla y badges existentes.
Pestaña Auditoria consume GET /api/audit-logs.
Auditoria muestra Fecha, Usuario, Accion, Entidad, ID entidad y Resumen del cambio.
Auditoria filtra por Accion, Entidad, Usuario y Limite.
Auditoria incluye estados de carga, vacio y error.
Auditoria backend de usuarios:
POST /api/users registra user.created.
/api/auth/register registra user.created sin romper bootstrap inicial y sin requerir current_user.
PATCH /api/users/{user_id} registra user.updated cuando cambia nombre o correo.
PATCH /api/users/{user_id}/roles registra user.role_changed.
PATCH /api/users/{user_id}/status registra user.activated o user.deactivated.
Los logs usan:entity = users
entity_id = id del usuario afectado
user_id = usuario que ejecuto el cambio cuando existe
previous_values y new_values sin contraseñas ni hashes

Nunca se guarda password, hashed_password, access_token ni refresh_token en auditoria.
Pendiente inmediato de Configuración:
Evaluar migracion futura si se quiere eliminar por completo role_id.
Mover permisos hardcodeados a base de datos en una fase posterior.
Agregar auditoria a otros modulos sensibles fuera de Usuarios.
Migracion nueva:
backend/migrations/versions/a1b2c3d4e5f6_add_catalog_items.py
backend/migrations/versions/b2c3d4e5f6a7_complete_catalog_items.py
La migracion crea indices:
internal_key
name
item_type
commodity
category
is_active
origin_currency
tax_object
Tambien crea unicidad parcial para internal_key activo cuando internal_key no es null.
quotation_items extendido de forma compatible con columnas opcionales:
catalog_item_id
unit
currency
commodity
calibration_scope
quotation_legend
sat_key
sat_unit
internal_unit
tax_object
tax_rate
discount_percent
tax_total
Cuando se agrega una partida con catalog_item_id, el backend copia datos del catalogo a quotation_items para conservar historico de cotizacion:
description
unit
unit_price
currency
commodity
calibration_scope
quotation_legend
sat_key
sat_unit
internal_unit
tax_object
tax_rate
Los totales de cotizacion se recalculan por linea:
importe = quantity * unit_price
descuento = importe * discount_percent / 100
subtotal_linea = importe - descuento
tax_total_linea = subtotal_linea * tax_rate / 100
total_cotizacion = suma(subtotal_linea) + suma(tax_total_linea)

Modulos visibles en /dashboard:

```text
Clientes
CRM
Ventas / Cotizaciones
Servicios
Ordenes de servicio
Equipos
Hojas de campo
Certificados
Calidad
Patrones
Procedimientos
Finanzas
Configuracion
Estado visual por modulo:
Activo
Pendiente
En desarrollo
Variables visuales principales definidas en frontend/src/styles/global.css:
--myc-primary
--myc-primary-dark
--myc-accent
--myc-bg
--glass-bg
--glass-border
La UI ya tiene CRUD visual inicial de Clientes y modulo Ventas/Cotizaciones con Catalogo MYC conectado al backend.
Comandos de arranque
Backend:
usar este codigo de arrance con entorno activo:
cd /Users/saulcortes/Desktop/myc_erp/backend
../venv/bin/uvicorn app.main:app --reload
Forma recomendada cuando se quiere activar el entorno y trabajar desde backend/:
cd /Users/saulcortes/Desktop/myc_erp
source venv/bin/activate
cd backend
uvicorn app.main:app --reload
Si se ejecuta desde backend/ sin activar el entorno, usar el binario del venv de forma explicita:
cd /Users/saulcortes/Desktop/myc_erp/backend
../venv/bin/uvicorn app.main:app --reload
Frontend:
cd /Users/saulcortes/Desktop/myc_erp/frontend
npm install
npm run dev

para trabajar de forma local. (ambos codigos levantan front y back con los scipts)
cd /Users/saulcortes/Desktop/myc_erp
./scripts/start-local.sh
se puede realizar fuera de entorno virtual 
para levantarlo en tunel 
cd /Users/saulcortes/Desktop/myc_erp
./scripts/start-tunnel.sh
validar con scripts de build. 
./scripts/build.sh

entrar en myc dev tools. 
./scripts/myc.sh


Referencias documentales anexadas - 2026-06-24
Se anexaron PDFs reales de referencia para la siguiente fase documental del ERP:
/Users/saulcortes/Library/Containers/net.whatsapp.WhatsApp/Data/tmp/documents/B7C9F687-FA4B-4038-BD41-FF0ACFF9AADC/MERCEDES BENZ LOPES MATEOS..pdf
/Users/saulcortes/Downloads/FCA-30 R1 HOJA DE CAMPO ELECTRICA (amperimetro, multimetro, megaohmetro).pdf
/Users/saulcortes/Downloads/FCA-30 R1 HOJA DE CAMPO GENERAL.pdf
Uso previsto de estas referencias:
- Orden de Trabajo impresa
- Rediseño del módulo Hojas de Campo
- Plantillas documentales iniciales de hoja de campo:
  - general
  - electrica
- PDF final de hoja de campo
- Base visual previa al PDF de certificados
Contexto técnico confirmado para la siguiente fase:
- Antes del PDF de certificados se debe cerrar:
  Cotizacion -> Orden de Servicio / Orden de Trabajo -> Equipos -> Hojas de Campo -> Calidad documental base
- La Orden de Trabajo debe usar un consecutivo documental independiente:
  work_order_number
- El formato esperado para Orden de Trabajo es un consecutivo numerico de 4 digitos iniciando en 7001.
- El cliente documental sigue siendo el cliente de la Orden de Servicio:
  service_orders.client_id
- No se implementara en esta fase OCR, lectura automatica libre de PDF/Excel ni constructor visual avanzado.
Fase A - Patrones, Procedimientos y Motor Metrológico Base
Backend nuevo:
- Modelo `backend/app/models/reference_standard.py`
- Modelo `backend/app/models/calibration_procedure.py`
- Schemas:
  - `backend/app/schemas/reference_standard.py`
  - `backend/app/schemas/calibration_procedure.py`
  - `backend/app/schemas/metrology.py`
- Services:
  - `backend/app/services/reference_standards.py`
  - `backend/app/services/calibration_procedures.py`
  - `backend/app/services/metrology_engine.py`
  - `backend/app/services/metrology_profiles.py`
- Routers:
  - `backend/app/routers/reference_standards.py`
  - `backend/app/routers/calibration_procedures.py`
  - `backend/app/routers/metrology.py`
- Migracion:
  - `backend/migrations/versions/e5f6a7b8c9d0_add_metrology_foundation.py`
Modelado nuevo:
- `reference_standards`
- `reference_standard_uncertainties`
- `calibration_procedures`
- `field_sheet_reference_standards`
- `field_sheets.calibration_procedure_id`
Campos nuevos en hoja de campo:
- `calibration_procedure_id`
- `reference_standards[]`
La hoja de campo ahora puede guardar:
- procedimiento de calibracion asignado
- uno o varios patrones con `usage_role`
- `measurement_section`
- notas por patron
Motor metrológico base:
- `average(values)`
- `standard_deviation(values)`
- `repeatability_uncertainty(values)`
- `resolution_uncertainty(resolution)`
- `combined_uncertainty(components)`
- `expanded_uncertainty(combined, k)`
- `absolute_error(indication, reference)`
- `relative_error(error, reference)`
- `select_uncertainty_for_value(uncertainty_ranges, value)`
Perfiles iniciales disponibles:
- pressure
- temperature
- humidity
- mass
- dimensional
- torque
- electrical
- time
- velocity
- sound
- gas
- angle
Auditoria nueva:
- `reference_standard.created`
- `reference_standard.updated`
- `reference_standard.deactivated`
- `reference_standard.uncertainty.created`
- `reference_standard.uncertainty.updated`
- `reference_standard.uncertainty.deactivated`
- `calibration_procedure.created`
- `calibration_procedure.updated`
- `calibration_procedure.deactivated`
- `field_sheet.reference_standard_added`
- `field_sheet.reference_standard_removed`
- `field_sheet.procedure_assigned`
- `metrology.preview_calculated`
Frontend nuevo:
- Pagina `frontend/src/pages/StandardsPage.jsx`
- Pagina `frontend/src/pages/ProceduresPage.jsx`
- Navegacion nueva:
  - `/dashboard#patrones`
  - `/dashboard#procedimientos`
- API frontend nueva en `frontend/src/services/api.js` para:
  - patrones
  - incertidumbres por rango
  - procedimientos
  - perfiles metrologicos
  - calculate-preview
- El modal de Hoja de Campo en `frontend/src/pages/ServiceOrdersPage.jsx` ya permite:
  - seleccionar procedimiento
  - agregar patrones
  - definir rol de uso
  - definir seccion de medicion
  - ver estado efectivo del patron
  - ver vigencia y rangos
  - advertencia visual si el patron esta vencido o fuera de servicio
Pendientes inmediatos recomendados
Definir PDF real de certificado y plantilla documental de certificados.
Conectar el motor metrológico a plantillas/documentos de certificado sin eliminar la revision humana.
Aplicar permisos gradualmente en endpoints sensibles usando require_permission().
Evaluar si role_id ya puede retirarse con migración dedicada o si se mantiene como compatibilidad controlada.
Extender audit_logs a clientes, cotizaciones, ordenes, equipos y hojas de campo con el mismo nivel de detalle.
Agregar selector mas inteligente de plantilla de hoja de campo antes del alta inicial cuando el flujo operativo lo requiera.

---

## Reestructuracion operativa hacia ETS y autenticacion PDF

Fecha de actualizacion: 2026-06-30 10:41:28 CST

Objetivo aplicado:
- El flujo operativo visible se reoriento hacia Servicios / ETS como centro del ERP.
- Los certificados siguen siendo externos y elaborados en Excel; el ERP controla expediente, estado, PDF final, matching, autenticacion y publicacion al cliente.
- Procedimientos, Incertidumbre, Biblioteca Documental, Equipos, Hojas, Certificados, Captura, Calidad y Flow Test quedan fuera de la navegacion principal visible.

Navegacion visible actual:
- Dashboard
- Clientes
- Ventas / Cotizaciones
- Catalogo MYC
- Servicios
- Patrones
- Facturacion
- Configuracion

Dashboard:
- Convertido a vista ejecutiva.
- Muestra pendientes operativos:
  - cotizaciones pendientes
  - servicios programados
  - servicios en proceso
  - captura pendiente
  - calidad pendiente
  - certificados por liberar
  - facturacion pendiente
- Muestra indicadores:
  - clientes activos
  - servicios abiertos
  - servicios cerrados
  - certificados pendientes
  - certificados liberados
- Los accesos rapidos usan solo los modulos principales visibles.

Servicios / ETS:
- `frontend/src/pages/ServiceOrdersPage.jsx` se reoriento como Expediente Tecnico del Servicio.
- El listado ahora muestra:
  - Folio OS
  - OT
  - Cliente
  - Estado
  - Responsable
  - Fecha
  - Equipos
  - Hojas
  - Certificados esperados
  - PDFs subidos
  - Captura
  - Calidad
  - Avance
  - Acciones
- Filtros agregados:
  - Todos
  - Programados
  - En proceso
  - Captura
  - Calidad
  - PDF pendientes
  - Liberados
  - Facturacion pendiente
  - Cerrados
- Al abrir un ETS ahora se muestran pestañas:
  - Resumen
  - Equipos
  - Hojas de Campo
  - Captura
  - Calidad
  - Certificados
  - Documentos
  - Historial
  - Facturacion
- Equipos dentro del ETS muestran folio reservado, hoja de campo, certificado esperado y PDF final.
- Captura dentro del ETS permite iniciar captura, subir PDF individual, subir multiples PDFs, validar match y enviar a calidad.
- Calidad dentro del ETS permite aprobar, rechazar, aceptar match manual, autenticar y liberar.
- Certificados dentro del ETS administran certificados externos con PDF original/autenticado, match, visibilidad cliente y codigo de autenticacion.

Motor de Autenticacion de Certificados PDF:
- Implementado `backend/app/services/certificate_authentication.py`.
- Dependencias agregadas a `backend/requirements.txt`:
  - `pypdf==6.4.1`
  - `qrcode==8.2`
  - `reportlab==4.4.6`
- Campos nuevos en `certificates`:
  - `authentication_code`
  - `authentication_hash`
  - `authenticated_pdf_path`
  - `authenticated_pdf_generated_at`
  - `authenticated_by_id`
  - `verification_url`
- Migracion nueva:
  - `backend/migrations/versions/f7a8b9c0d1e2_add_certificate_authentication.py`
- El PDF original se conserva en `final_pdf_path`.
- El PDF autenticado se genera como archivo separado en `authenticated_pdf_path`.
- Se calcula SHA-256 del PDF original.
- Se imprime una capa de autenticacion sobre la ultima pagina con:
  - codigo unico `MYC-AUTH-YYYY-000000`
  - QR
  - folio
  - fecha de liberacion/autenticacion
  - leyenda "Documento autenticado por MYC SYSTEM"
  - hash SHA-256 original
  - URL publica de verificacion
- La liberacion al cliente ejecuta la autenticacion antes de marcar `client_visible=true`.
- Endpoint interno nuevo:
  - `POST /api/certificates/{certificate_id}/authenticate`
- Endpoint publico nuevo:
  - `GET /verify/{authentication_code}`
- Respuesta publica de verificacion:
  - valido/no valido
  - folio
  - cliente
  - equipo
  - serie
  - estado
  - fecha de autenticacion
  - hash documental

Portal cliente:
- `backend/app/routers/client_portal.py` ahora entrega unicamente el PDF autenticado.
- Si no existe `authenticated_pdf_path`, el certificado no se publica para descarga.
- El cliente no recibe hoja de campo, captura, calidad, procedimientos ni incertidumbre.

Configuracion:
- `public_verify_base_url` agregado a `backend/app/core/config.py`.
- Valor default:
  - `https://api-erp.mycmetrology.com.mx`

Validacion ejecutada:
- `../venv/bin/python -m compileall app`
- `npm run build`
- `../venv/bin/python -c "from app.main import app; print(app.title, len(app.routes))"`
- OpenAPI generado con 131 paths y `/verify/{authentication_code}` registrado.
- `../venv/bin/alembic upgrade head`
- `../venv/bin/alembic current`
  - resultado: `f7a8b9c0d1e2 (head)`
- Prueba aislada de estampado PDF:
  - origen: `/tmp/myc-auth-test-original.pdf`
  - autenticado: `/tmp/myc-auth-test-authenticated.pdf`
  - resultado: PDF generado correctamente
- `git diff --check`
- `./scripts/myc build`
- `./scripts/myc doctor`

Observaciones:
- Vite conserva advertencia no bloqueante de chunk mayor a 500 kB.
- No se elimino backend ni migraciones de modulos no operativos.
- El Motor de Incertidumbre permanece como experimental y fuera del flujo visible.
- Procedimientos y Biblioteca Documental quedan ocultos de la navegacion principal.

---

## Refinamiento UX del ETS como expediente digital

Fecha de actualizacion: 2026-06-30 11:10:21 CST

Objetivo aplicado:
- Servicios / ETS se refino para sentirse como expediente digital, no como modal tecnico con pestanas genericas.
- La navegacion principal permanece limpia y no se reactivaron modulos ocultos.
- Se mantienen ocultos:
  - Procedimientos
  - Incertidumbre
  - Biblioteca Documental
  - Equipos
  - Hojas de Campo
  - Certificados
  - Captura
  - Calidad
  - Flow Test

Cambios UX principales:
- Las secciones internas del ETS ahora se presentan como carpetas visuales de expediente:
  - Resumen
  - Equipos
  - Hojas de Campo
  - Captura
  - Calidad
  - Certificados
  - Documentos
  - Historial
  - Facturacion
- La carpeta activa se destaca como seccion abierta.
- En movil las carpetas se acomodan como lista vertical.
- La fila del listado de Servicios mantiene apertura por click completo y se agrego hover/focus visible para indicar que abre el expediente.

Dashboard:
- Corregido calculo seguro para evitar `NaN`, especialmente en `Servicios abiertos`.
- Los indicadores usan valores numericos seguros con fallback a `0`.
- Se mantienen solo accesos principales visibles.

Resumen ejecutivo del ETS:
- Agregado tablero ejecutivo dentro de la carpeta Resumen.
- Muestra:
  - Cliente
  - Folio OS
  - Numero OT
  - Cotizacion origen
  - Responsable/asesor
  - Fecha agenda
  - Fecha servicio
  - Estado actual
  - Progreso global del expediente
- Agregado indicador de avance por etapas:
  - Cotizacion
  - Agenda
  - Equipos
  - Hojas
  - Captura
  - Calidad
  - PDF autenticado
  - Facturacion
  - Cierre
- Contadores seguros agregados:
  - Equipos totales
  - Equipos completados
  - Hojas creadas
  - Hojas completadas
  - Certificados esperados
  - PDFs subidos
  - PDFs autenticados
  - Certificados liberados
  - Pendientes Captura
  - Pendientes Calidad
  - Facturacion pendiente

Captura dentro del ETS:
- Agregado resumen superior con:
  - Certificados esperados
  - PDFs cargados
  - PDFs pendientes
  - Matches automaticos
  - Warnings
  - Mismatches
  - Aceptados manualmente
- Se conservan acciones:
  - Iniciar captura
  - Subir PDF individual
  - Subir PDFs multiples
  - Validar match
  - Enviar a calidad
- Se mantiene mensaje claro cuando no hay certificados esperados:
  - "Crea certificados esperados desde Equipos para iniciar captura."

Calidad dentro del ETS:
- Agregado resumen superior con:
  - Pendientes
  - En revision
  - Aprobados
  - Rechazados
  - Liberables
  - Autenticados
- Se conservan acciones:
  - Aprobar
  - Rechazar
  - Aceptar match manual
  - Autenticar
  - Liberar al cliente

Certificados dentro del ETS:
- La carpeta Certificados ahora muestra:
  - Folio
  - Equipo
  - Serie
  - Identificacion
  - Estado
  - PDF original
  - PDF autenticado
  - Codigo de autenticacion
  - Match
  - Cliente visible
  - Fecha autenticacion
  - Acciones
- Acciones agregadas:
  - Ver PDF autenticado
  - Descargar PDF autenticado
  - Ver autenticacion
  - Validar match
  - Autenticar
  - Liberar al cliente
  - Suspender
- Regla operativa aplicada:
  - La accion principal de descarga usa unicamente PDF autenticado.
  - El PDF original queda como insumo interno, no como documento final de descarga.

Descarga de PDF autenticado:
- Endpoint backend agregado:
  - `GET /api/certificates/{certificate_id}/authenticated-pdf`
- Devuelve:
  - `application/pdf`
  - archivo autenticado
  - nombre sugerido `Certificado_{folio}_{codigo}.pdf`
- Si no existe PDF autenticado responde error claro:
  - "El certificado aun no tiene PDF autenticado"
- Funciones frontend agregadas:
  - `getAuthenticatedCertificatePdfUrl`
  - `downloadAuthenticatedCertificatePdf`

Ver autenticacion:
- Accion agregada en la carpeta Certificados.
- Muestra panel interno con:
  - Codigo de autenticacion
  - URL publica de verificacion
  - Hash SHA-256
  - Estado
  - Fecha de autenticacion

Documentos del ETS:
- La carpeta Documentos se refino como repositorio documental del expediente.
- Muestra:
  - Cotizacion PDF como pendiente si no hay endpoint especifico conectado
  - Orden de Trabajo PDF con ver/descargar/imprimir
  - Hojas de campo internas
  - Certificados PDF autenticados con ver/descargar
  - PDFs pendientes
  - Factura futura
- Internamente se pueden ver hojas de campo; el portal cliente sigue sin exponerlas.

Historial / Timeline:
- La carpeta Historial ahora se presenta como linea de tiempo del expediente.
- Eventos derivados del ETS:
  - Cotizacion vinculada
  - Orden creada
  - Equipo registrado
  - Hoja creada
  - Hoja completada
  - Certificado esperado
  - Captura iniciada
  - PDF subido
  - Enviado a calidad
  - Calidad aprobo/rechazo
  - Certificado autenticado
  - Liberado al cliente
- Muestra fecha/hora, accion, entidad y descripcion.
- Pendiente recomendado:
  - conectar eventos completos desde `audit_logs` cuando se definan permisos/endpoint especifico de ETS.

Estilo:
- Agregados estilos de carpeta:
  - `.ets-folder-tabs`
  - `.ets-folder-tab`
- Agregados badges y barras:
  - `.ets-progress-panel`
  - `.ets-progress-bar`
  - `.ets-stage-strip`
  - `.ets-metric-strip`
  - `.ets-metric-badge`
- Agregado panel de autenticacion:
  - `.ets-auth-panel`
- Agregado timeline:
  - `.ets-timeline`
  - `.ets-timeline-item`
- Agregado hover/focus claro en filas de expediente.

Validacion ejecutada:
- `../venv/bin/python -m compileall app`
- `npm run build`
- `../venv/bin/alembic current`
  - resultado: `f7a8b9c0d1e2 (head)`
- `../venv/bin/python -c "from app.main import app; schema=app.openapi(); print(app.title, len(app.routes)); print('/api/certificates/{certificate_id}/authenticated-pdf' in schema['paths']); print('/verify/{authentication_code}' in schema['paths'])"`
  - resultado: `ERP MYC 30`, endpoint autenticado `True`, verify `True`
- `git diff --check`
- `./scripts/myc build`
- `./scripts/myc doctor`

Limitaciones y pendientes:
- Vite conserva advertencia no bloqueante de chunk mayor a 500 kB.
- Cotizacion PDF queda como tarjeta documental pendiente de endpoint especifico si se requiere descarga directa desde ETS.
- Timeline usa datos cargados del expediente; falta integrarlo con `audit_logs` para eventos de usuario completos y descargas del cliente.
- `storage/certificados/7008/` aparece como directorio no versionado generado por operaciones/pruebas de almacenamiento; no se elimino para evitar perdida documental.

---

## MYC SYSTEM V2 - Alineacion operativa ETS

Fecha de actualizacion: 2026-06-30 16:29:11 CST

Vision aplicada:
- MYC SYSTEM deja de tratarse como ERP tradicional y se alinea como Sistema Integral de Gestion Metrologica.
- El objeto central sigue siendo el Expediente Tecnico de Servicio (ETS).
- El flujo operativo oficial queda orientado a:
  - Cliente
  - Cotizacion
  - Aceptacion
  - ETS
  - Agenda
  - Alta de equipos
  - Reserva automatica de folios
  - Hoja de Campo
  - Captura
  - Calidad
  - Autenticacion
  - Facturacion
  - Liberacion
  - Cierre

Certificado esperado automatico:
- `backend/app/services/equipment.py` se limpio para evitar imports y funciones duplicadas.
- El alta de equipo conserva la creacion automatica del certificado esperado cuando la partida corresponde a calibracion.
- La reserva de folio MYCA/MYCT sigue delegada a `create_certificate`.
- La UI del ETS no expone creacion manual de certificado; el folio reservado se muestra como dato operativo del equipo.

Estado `returned_to_technician`:
- Agregado a `CertificateStatus`.
- Agregado a `FieldSheetStatus`.
- La hoja queda editable nuevamente cuando esta en `returned_to_technician`.
- `complete_field_sheet` acepta hojas en `returned_to_technician`.
- Endpoint agregado:
  - `POST /api/certificates/{certificate_id}/return-to-technician`
- El motivo es obligatorio.
- La accion registra auditoria:
  - `certificate.returned_to_technician`
- Si el certificado tiene hoja vinculada, la hoja pasa a:
  - `returned_to_technician`
- Frontend:
  - etiqueta `Devuelto a tecnico`
  - accion en Calidad `Regresar tecnico`
  - prompt de motivo obligatorio antes de ejecutar la accion

Calidad y autenticacion:
- Calidad mantiene acciones de aprobar/rechazar/regresar a tecnico/autenticar/liberar.
- La autenticacion ahora valida explicitamente:
  - certificado aprobado por calidad
  - PDF original cargado
  - estado permitido
- No se permite autenticar certificados en estados operativos previos.

Sello de autenticacion redisenado:
- `backend/app/services/certificate_authentication.py` cambio el sello de pie de pagina a banda lateral vertical.
- Caracteristicas implementadas:
  - banda lateral derecha
  - ancho aproximado 12-15 mm
  - presente en todas las paginas
  - logo MYC si el asset esta disponible
  - texto "Documento autenticado por MYC SYSTEM"
  - codigo de autenticacion
  - codigo de barras Code128
  - QR
  - adaptacion al tamano de pagina
- Prueba aislada generada:
  - `/tmp/myc-v2-auth-sideband.pdf`

Orden de Trabajo:
- Corregida plantilla `backend/app/templates/work_order_pdf.html`.
- Se elimino HTML invalido que habia dejado `th` dentro de `header` y `td` dentro de `section`.
- La tabla de equipos ahora incluye columna:
  - `Folio cert.`
- `backend/app/services/work_order_pdfs.py` conserva `certificate_folio` por equipo.

Hoja de Campo:
- `backend/app/services/field_sheet_pdfs.py` ahora resuelve el certificado esperado activo del equipo.
- Plantillas actualizadas:
  - `backend/app/templates/field_sheet_general_pdf.html`
  - `backend/app/templates/field_sheet_electrical_pdf.html`
- Se muestra:
  - `Folio certificado`

Frontend ETS:
- Se mantiene arquitectura basada en ETS y no se reactivaron modulos ocultos.
- Se conserva navegacion principal limpia.
- Se agrego accion operativa para regresar a tecnico desde Calidad con motivo.
- Las hojas devueltas a tecnico pueden volver a completarse desde el modal de hoja.

API preservada:
- No se eliminaron endpoints existentes.
- Se agrego endpoint nuevo compatible:
  - `POST /api/certificates/{certificate_id}/return-to-technician`
- Se mantiene:
  - `GET /api/certificates/{certificate_id}/authenticated-pdf`
  - `GET /verify/{authentication_code}`

Validaciones ejecutadas:
- `../venv/bin/python -m compileall app`
- `npm run build`
- OpenAPI:
  - `ERP MYC 30`
  - `/api/certificates/{certificate_id}/return-to-technician`: `True`
  - `/api/certificates/{certificate_id}/authenticated-pdf`: `True`
- Prueba aislada de sello lateral:
  - resultado: PDF generado correctamente
- `git diff --check`
- `./scripts/myc build`
- `./scripts/myc doctor`
- `../venv/bin/alembic current`
  - resultado: `f7a8b9c0d1e2 (head)`

Limitaciones y pendientes:
- El Catalogo MYC aun no controla automaticamente todo el flujo por tipo/categoria/subcategoria de servicio.
- Falta formalizar reglas de catalogo para:
  - requiere equipos
  - genera hojas de campo
  - genera certificados
  - requiere autenticacion
  - tipo de folio
  - documentos requeridos
  - flujo operativo por servicio
- Facturacion, encuestas y portal cliente V2 quedan pendientes de una fase dedicada.
- Vite conserva advertencia no bloqueante de chunk mayor a 500 kB.
- Directorios `storage/certificados/*` no versionados se conservaron para evitar perdida documental.

---

## Auditoria de flujo ETS y correccion urgente de sello PDF

Fecha de actualizacion: 2026-07-01 10:18:58 CST

Alcance:
- Se respeto la arquitectura oficial de Fases 1 y 2.
- No se agregaron modulos nuevos.
- No se reactivaron modulos ocultos.
- Se corrigieron bloqueos puntuales del flujo ETS y la autenticacion visual de certificados.

Correccion urgente de PDF autenticado:
- Archivo ajustado:
  - `backend/app/services/certificate_authentication.py`
- Se elimino el uso de sello inferior.
- No hay referencias a `footer_y` ni `footer_height`.
- El PDF autenticado ahora agrega una banda lateral derecha en un margen propio de la pagina.
- La banda se aplica en todas las paginas.
- Al ampliar el ancho de pagina antes de sellar, el contenido tecnico original no queda invadido.
- La banda incluye:
  - logo MYC cuando existe
  - QR pequeno
  - texto vertical `CERTIFICADO AUTENTICADO`
  - `MYC SYSTEM`
  - codigo `MYC-AUTH`
  - folio
  - codigo de barras Code128 vertical
- El nombre del PDF autenticado ahora usa sufijo `_autenticado_lateral_` para evitar reutilizar archivos visualmente obsoletos.

Flujo ETS corregido:
- `backend/app/services/field_sheets.py`
  - `labeled` ya no bloquea crear o editar hoja de campo.
  - Solo `not_done` y `cancelled` bloquean hoja por equipo terminal.
  - Al completar hoja se crea certificado esperado si no existe.
  - Al completar hoja se vincula `field_sheet_id` al certificado esperado.
  - Al completar hoja el certificado queda en `field_sheet_ready`.
  - Al enviar hoja a Captura, el certificado queda en `capture_pending`.
- `backend/app/services/certificates.py`
  - `pdf_uploaded` puede transicionar a `ready_for_quality`.
  - `send_to_quality` permite `pdf_uploaded` cuando ya existe PDF.
  - `send_to_quality` bloquea envio a Calidad si no hay PDF cargado.
  - Carga masiva de PDFs devuelve error claro si no hay certificados esperados o pendientes.

Frontend ETS:
- `frontend/src/pages/ServiceOrdersPage.jsx`
  - Se elimino `window.prompt` para devolver al tecnico.
  - La devolucion al tecnico usa modal interno con motivo obligatorio.
  - El ETS abierto se refresca con la version actualizada al recargar datos.
  - Inputs de carga masiva, carga individual y reemplazo de PDF se limpian al finalizar para permitir reintentar el mismo archivo.
- Validacion:
  - `rg -n "window\\.confirm|window\\.alert|window\\.prompt|alert\\(|prompt\\(" frontend/src` no reporta prompts/alerts nativos.

Validacion visual de PDF real:
- PDF generado:
  - `/tmp/myc-auth-sideband.pdf`
- Imagenes renderizadas:
  - `/tmp/myc-auth-sideband-1.png`
  - `/tmp/myc-auth-sideband-2.png`
- Resultado visual:
  - pagina 1 sin sello inferior
  - pagina 2 sin sello inferior
  - banda lateral derecha presente en ambas paginas
  - firmas, notas y contenido tecnico libres de invasion inferior
- `pdftoppm` emitio advertencias de Fontconfig por cache no escribible, pero genero las imagenes correctamente.

Validacion ejecutada:
- `../venv/bin/python -m compileall app`
- `../venv/bin/alembic upgrade head`
- `../venv/bin/alembic current`
  - resultado: `a8b9c0d1e2f3 (head)`
- OpenAPI:
  - `ERP MYC 30`
  - `/api/certificates/{certificate_id}/authenticated-pdf`: `True`
  - `/verify/{authentication_code}`: `True`
- `npm run build`
  - OK con advertencia no bloqueante de chunk mayor a 500 kB.
- `git diff --check`
- `./scripts/myc build`
- `./scripts/myc doctor`

Limitaciones y pendientes:
- No se hizo reset destructivo de DB ni de storage documental.
- La prueba visual se realizo con PDF real temporal generado para validar layout del sello.
- La matriz de permisos backend por rol sigue pendiente de endurecimiento formal; en esta fase se mantuvo control frontend y reglas operativas existentes.
- Directorios `storage/certificados/*` no versionados se conservaron para evitar perdida documental.

---

## Ajuste funcional ETS - acciones masivas, hojas max 10 y documentos

Fecha de actualizacion: 2026-07-01 10:57:25 CST

Alcance:
- Se mantuvo todo dentro de Servicios / ETS.
- No se agregaron modulos nuevos.
- No se reactivaron rutas de navegacion ocultas.
- Se corrigieron acciones operativas para Calidad, Documentos, limites de OT y automatizaciones.

Backend:
- `backend/app/services/equipment.py`
  - Se agrego limite operativo de 10 equipos activos por Orden de Trabajo.
  - Al intentar crear el equipo 11 responde 409:
    - `Esta Orden de Trabajo ya tiene 10 equipos. Crea otra OT para continuar.`
- `backend/app/services/field_sheets.py`
  - Al crear/abrir hoja, el equipo en `registered` pasa automaticamente a `realizing`.
- `backend/app/services/service_orders.py`
  - Al guardar agenda + fecha de servicio + tecnico, una orden `scheduled` pasa automaticamente a `confirmed`.
- `backend/app/services/certificates.py`
  - `send_to_quality` mueve la OT a `quality_review` cuando corresponde.
  - Nuevo lote `authenticate_certificates_for_service_order`.
  - Nuevo lote `release_authenticated_certificates_for_service_order`.
  - Los lotes continuan aunque un certificado falle y devuelven resumen por folio.
  - Al liberar todos los certificados, la OT avanza a `pending_payment` o `released` segun facturacion.
- `backend/app/routers/service_orders.py`
  - Nuevo endpoint:
    - `POST /api/service-orders/{service_order_id}/certificates/authenticate-approved`
  - Nuevo endpoint:
    - `POST /api/service-orders/{service_order_id}/certificates/release-authenticated`
- `backend/app/routers/certificates.py`
  - Nuevo endpoint seguro para PDF original:
    - `GET /api/certificates/{certificate_id}/original-pdf`
- `backend/app/schemas/certificate.py`
  - Nuevos schemas de respuesta para acciones masivas:
    - `CertificateBatchActionItemRead`
    - `CertificateBatchActionRead`

Frontend ETS:
- `frontend/src/pages/ServiceOrdersPage.jsx`
  - Calidad ahora usa fila clickeable para abrir modal de revision.
  - El modal de Calidad muestra:
    - certificado
    - equipo
    - hoja vinculada
    - PDF original
    - match status
    - match details
    - estado actual
    - historial minimo
  - Acciones jerarquicas dentro del modal:
    1. Ver PDF original
    2. Validar match
    3. Aceptar match manual
    4. Aprobar / Rechazar
    5. Regresar a tecnico
    6. Autenticar
    7. Liberar
  - Se agregaron acciones masivas:
    - `Autenticar aprobados`
    - `Liberar autenticados`
  - Las acciones masivas usan confirmacion interna y muestran resumen final.
  - Equipos muestra:
    - equipos esperados desde cotizacion
    - equipos registrados
    - capacidad OT `registrados / 10`
    - hojas `X / 10`
  - El boton `Agregar equipo` se deshabilita al llegar a 10 equipos.
  - Resumen ETS deja de depender de `total_equipment` como si fuera conteo real y muestra registrados/esperados.
  - Progreso global ETS ahora usa etapas reales:
    - cotizacion
    - agenda
    - equipos
    - hojas
    - captura
    - calidad
    - autenticacion
    - facturacion
    - cierre
  - Documentos se reorganizo como subcarpetas internas:
    - Cotizacion
    - Orden de trabajo
    - Hojas de campo
    - Certificados originales
    - Certificados autenticados
    - Evidencias
    - Facturacion
    - Cliente / administrativos
  - Certificados originales y autenticados muestran conteos separados.
  - Botones de descarga por lote quedan deshabilitados como `Proximamente` cuando no existe backend de ZIP.
  - Hoja de Campo:
    - patrones se marcan como opcionales.
    - acciones de sugerir/validar patrones se despriorizan como opcionales.
    - se agrego selector rapido de proxima calibracion:
      - Manual
      - 6 meses
      - 12 meses
      - 24 meses
- `frontend/src/services/api.js`
  - Nuevas funciones:
    - `authenticateApprovedCertificates`
    - `releaseAuthenticatedCertificates`
    - `getOriginalCertificatePdfUrl`
- `frontend/src/styles/global.css`
  - Estilos para fila clickeable de Calidad, cinta de acciones y panel de match details.

Validacion ejecutada:
- `../venv/bin/python -m compileall app`
- `../venv/bin/alembic upgrade head`
- `../venv/bin/alembic current`
  - resultado: `a8b9c0d1e2f3 (head)`
- OpenAPI:
  - `ERP MYC 30`
  - `/api/service-orders/{service_order_id}/certificates/authenticate-approved`: `True`
  - `/api/service-orders/{service_order_id}/certificates/release-authenticated`: `True`
  - `/api/certificates/{certificate_id}/original-pdf`: `True`
- `rg -n "window\\.confirm|window\\.alert|window\\.prompt|alert\\(|prompt\\(" frontend/src`
  - sin resultados
- `git diff --check`
- `npm run build`
  - OK con advertencia no bloqueante de chunk mayor a 500 kB.
- `./scripts/myc build`
- `./scripts/myc doctor`

Limitaciones y pendientes:
- No se implemento ZIP de descarga masiva de documentos; los botones quedan como `Proximamente`.
- No se hizo reset destructivo de DB ni se eliminaron archivos de `storage/certificados`.
- La division automatica en varias OT para mas de 10 equipos queda para una fase posterior; por ahora se bloquea el equipo 11 con mensaje claro.

---

## Ajuste de Hojas de Campo - folio reservado, plantillas y cliente de certificado

Fecha de actualizacion: 2026-07-01 15:23:50 CST

Alcance:
- Se mantuvo el uso de Hojas de Campo como captura documental y descarga PDF.
- No se reintrodujo generacion de certificados desde la hoja.
- No se removieron tablas legacy de procedimientos o patrones; solo se sacaron del flujo visual.

Correcciones aplicadas:
- Folio reservado del certificado
  - `FieldSheetRead` ahora expone `reserved_certificate_folio`.
  - `FieldSheet` resuelve el folio activo usando `expected_folio` y, si no existe, `folio`.
  - `get_field_sheet` y `list_field_sheets` cargan relaciones de:
    - `equipment`
    - `equipment.certificates`
    - `equipment.service_order`
    - `equipment.service_order.client`
    - `equipment.service_order.quotation`
  - La vista previa React de la hoja usa primero `reserved_certificate_folio`.
  - El PDF de hoja de campo vuelve a imprimir el mismo folio reservado de forma consistente.

- Persistencia de plantilla
  - Se alinearon claves entre schema y servicio para evitar plantillas validas en frontend que no existian en backend.
  - `FieldSheetTemplateKey` ahora contempla tambien:
    - `electrica`
    - `sonido`
    - `termometro`
    - `transductor_presion`
    - `volumen`
    - `masa`
    - `balanza`
  - `FIELD_SHEET_TEMPLATE_ROWS` ahora incluye al menos:
    - `anemometro`
    - `dimensional`
    - `temperatura`
    - `sonido`
    - `electrica`
  - Se mantuvo `template_key` persistido al crear y actualizar hojas.

- PDF por plantilla
  - `backend/app/services/field_sheet_pdfs.py` valida:
    - `anemometro` -> `field_sheet_anemometer_pdf.html`
    - `electrica` -> `field_sheet_electrical_pdf.html`
    - cualquier otro caso -> `field_sheet_general_pdf.html`

- Cliente del certificado dentro de la hoja
  - Nueva migracion:
    - `backend/migrations/versions/b9c0d1e2f3a4_add_field_sheet_certificate_client.py`
  - Nuevos campos persistidos en `field_sheets`:
    - `certificate_client_mode`
    - `certificate_client_company`
    - `certificate_client_attention`
    - `certificate_client_address`
    - `apply_certificate_client_to_order`
  - Si la hoja usa cliente facturado, el PDF toma el cliente de la orden.
  - Si la hoja usa cliente diferente, esos datos quedan guardados solo en la hoja.
  - Si `apply_certificate_client_to_order` es `true`, futuras hojas de la misma OT heredan ese cliente alterno.
  - No se escribio ese cliente en la tabla principal `clients`.

- Limpieza visual del modulo
  - Se retiraron del flujo visual de la hoja:
    - procedimiento de calibracion
    - seleccion de patrones
    - agregar patron
  - Los campos siguen existiendo en backend/estado interno solo para no romper compatibilidad.
  - La vista de informacion de hoja ahora muestra:
    - plantilla real
    - folio reservado
  - La vista previa React usa tambien cliente alterno si la hoja lo tiene.

Archivos ajustados en esta fase:
- `backend/app/models/field_sheet.py`
- `backend/app/schemas/field_sheet.py`
- `backend/app/services/field_sheets.py`
- `backend/app/services/field_sheet_pdfs.py`
- `backend/app/templates/field_sheet_general_pdf.html`
- `backend/app/templates/field_sheet_electrical_pdf.html`
- `frontend/src/constants/forms.js`
- `frontend/src/utils/fieldSheets.js`
- `frontend/src/pages/ServiceOrdersPage.jsx`
- `backend/migrations/versions/b9c0d1e2f3a4_add_field_sheet_certificate_client.py`

Validacion ejecutada:
- `../venv/bin/python -m compileall app`
- `../venv/bin/alembic upgrade head`
- `../venv/bin/alembic current`
  - resultado: `b9c0d1e2f3a4 (head)`
- OpenAPI:
  - `ERP MYC 31`
  - `/api/field-sheets`: `True`
  - `/api/field-sheets/{field_sheet_id}`: `True`
  - `/api/field-sheets/{field_sheet_id}/pdf`: `True`
- `npm run build`
  - OK con advertencia no bloqueante de chunk mayor a 500 kB.
- `git diff --check`
- `./scripts/myc build`
- `./scripts/myc doctor`

Limitaciones y pendientes:
- No se eliminaron componentes auxiliares de patrones/procedimientos; quedaron fuera de UI, no fuera del dominio.
- Existen archivos y carpetas no versionadas de otras fases en el worktree; no se tocaron para no mezclar cambios ni perder contexto.

---

## Correccion final - folio reservado en Hojas de Campo y campos de captura persistentes

Fecha de actualizacion: 2026-07-01 15:49:29 CST

Alcance:
- Se corrigio la regla operativa para que la hoja de campo solo consuma el certificado esperado activo del equipo.
- No se modifico el motor de folios.
- No se duplicaron certificados.
- No se creo ningun certificado desde `create_field_sheet` ni desde `complete_field_sheet`.

Folio reservado:
- `reserved_certificate_folio` en `FieldSheetRead` ahora depende del certificado activo del equipo.
- La resolucion usa prioridad:
  - `expected_folio`
  - `folio`
- `list_field_sheets` y `get_field_sheet` cargan `equipment.certificates` de forma explicita.
- Esto deja consistente el folio reservado en:
  - `GET /api/field-sheets`
  - `GET /api/field-sheets/{id}`
  - `GET /api/field-sheets/{id}/pdf`

Regla de no crear certificados desde hojas:
- `backend/app/services/field_sheets.py`
  - se elimino la ruta que creaba un certificado esperado durante `complete_field_sheet`.
  - la hoja ahora solo enlaza y actualiza el certificado activo ya existente del equipo.

Campos de captura persistidos:
- Nuevos campos funcionales en `field_sheets`:
  - `minimum_division`
  - `location`
  - `attention`
  - `company`
  - `address`
- Estos campos existen y persisten en:
  - modelo SQLAlchemy
  - `FieldSheetCreate`
  - `FieldSheetUpdate`
  - `FieldSheetRead`
  - migracion `b9c0d1e2f3a4_add_field_sheet_certificate_client.py`
  - `fieldSheetToForm`
  - `buildFieldSheetPayload`
  - `ServiceOrdersPage`
  - `FieldSheetLayout`

Vista previa y PDF:
- La vista previa React usa:
  - `selectedFieldSheet.reserved_certificate_folio`
  - `minimumDivision`
  - `location`
  - `attention`
  - `company`
  - `address`
- Los PDFs general, anemometro y electrica ahora muestran tambien:
  - folio reservado
  - ubicacion
  - division minima
  - atencion
  - direccion
- Si la hoja tiene cliente alterno, ese dato sigue pudiendo reflejarse; si no, se usa el cliente de la orden.

Validacion ejecutada:
- `../venv/bin/python -m compileall app`
- `../venv/bin/alembic upgrade head`
- `../venv/bin/alembic current`
  - resultado: `b9c0d1e2f3a4 (head)`
- OpenAPI:
  - `ERP MYC 31`
  - `/api/field-sheets`: `True`
  - `/api/field-sheets/{field_sheet_id}`: `True`
  - `/api/field-sheets/{field_sheet_id}/pdf`: `True`
- `npm run build`
  - OK con advertencia no bloqueante de chunk mayor a 500 kB.
- `git diff --check`
- `./scripts/myc build`
- `./scripts/myc doctor`

Observacion:
- Se mantuvieron intactos los archivos y carpetas no versionadas de otras fases para no mezclar alcance ni perder trabajo previo.

---

## Refinamiento post Fases 1 y 2 - Dashboard, ETS y trazabilidad

Fecha de actualizacion: 2026-06-30 16:45:53 CST

Alcance:
- Se mantuvo la arquitectura oficial de Fases 1 y 2.
- No se crearon modulos nuevos.
- No se duplicaron funcionalidades.
- Los cambios consolidan experiencia, trazabilidad y automatizacion dentro de Dashboard y ETS.

Dashboard Ejecutivo:
- Se separaron visualmente:
  - centro de control operativo
  - indicadores ejecutivos
  - accesos rapidos
- Agregado avance promedio del ETS como indicador principal.
- Agregados indicadores operativos:
  - Devueltos a tecnico
  - Autenticacion pendiente
  - Certificados autenticados
- Los indicadores ya no representan solo conteos de tablas; ahora consideran estados reales del flujo.
- Se agregaron estilos:
  - `.dashboard-control-panel`
  - `.dashboard-section-block`
  - `.dashboard-progress-summary`
  - `.dashboard-progress-bar`

Trazabilidad formal de devolucion de hojas:
- Nueva migracion:
  - `backend/migrations/versions/a8b9c0d1e2f3_add_field_sheet_return_tracking.py`
- Campos nuevos en `field_sheets`:
  - `returned_to_technician_at`
  - `returned_to_technician_by_id`
  - `returned_to_technician_reason`
- `FieldSheetRead` expone estos campos.
- Al regresar un certificado/hoja al tecnico:
  - la hoja vuelve a `returned_to_technician`
  - queda editable
  - se guarda usuario
  - se guarda fecha
  - se guarda motivo obligatorio
  - se registra auditoria

Automatizacion de flujo:
- Al completar una hoja:
  - el equipo pasa a `calibrated`
  - el certificado esperado vinculado se asocia a la hoja
  - el certificado pasa a `field_sheet_ready`
- Al enviar la hoja a Captura:
  - el certificado esperado vinculado pasa a `capture_pending`
- Esto reduce decisiones manuales y mantiene el folio reservado dentro del expediente.

Validaciones operativas:
- Las hojas en `returned_to_technician` pueden guardarse y completarse nuevamente.
- Se conserva integridad del flujo:
  - no se permite autenticar sin PDF
  - no se permite autenticar sin aprobacion de calidad
  - el motivo de devolucion es obligatorio
- Se mantuvieron endpoints existentes.

Roles y visibilidad de acciones:
- `ServiceOrdersPage` recibe el usuario actual.
- Se agrego visibilidad de acciones por etapa:
  - Administrador: ve todas las acciones.
  - Tecnico: acciones tecnicas de equipos y hojas.
  - Captura: acciones de PDF, matching y envio a calidad.
  - Calidad: aprobar, rechazar, devolver a tecnico, aceptar match, autenticar y liberar.
- La informacion del expediente sigue visible para continuidad operativa.
- Las acciones que no corresponden a la etapa del rol se ocultan en frontend.

UX del ETS:
- Se ajusto texto de envio de hoja:
  - `Enviar a Captura`
- Se mantiene lectura continua del expediente sin sacar al usuario del ETS.
- Se agrego soporte:
  - `ESC` para cerrar ETS/modal activo.
  - `ENTER` para confirmar en `ConfirmDialog`.

Autenticacion dentro del flujo:
- El estado de autenticacion queda reforzado en Dashboard y ETS mediante:
  - autenticacion pendiente
  - certificados autenticados
  - datos del PDF autenticado
  - enlace de verificacion existente
- La autenticacion se mantiene como etapa entre Calidad y Liberacion.

Validacion ejecutada:
- `../venv/bin/python -m compileall app`
- `npm run build`
- `../venv/bin/alembic upgrade head`
- `../venv/bin/alembic current`
  - resultado: `a8b9c0d1e2f3 (head)`
- OpenAPI:
  - `ERP MYC 30`
  - `/api/certificates/{certificate_id}/return-to-technician`: `True`
  - `/api/certificates/{certificate_id}/authenticated-pdf`: `True`
- `git diff --check`
- `./scripts/myc build`
- `./scripts/myc doctor`

Limitaciones y pendientes:
- La restriccion por roles esta aplicada en frontend; falta endurecer permisos backend por accion cuando se formalice matriz final.
- El Catalogo MYC sigue pendiente como cerebro completo de flujo operativo.
- La facturacion real, encuestas y portal cliente V2 siguen pendientes.
- Vite conserva advertencia no bloqueante de chunk mayor a 500 kB.
- Directorios `storage/certificados/*` no versionados se conservaron para evitar perdida documental.

---

## Fix urgente - columnas faltantes en field_sheets

Fecha de actualizacion: 2026-07-01 15:52:39 CST

Causa raiz:
- El modelo `FieldSheet` y los schemas ya referenciaban:
  - `minimum_division`
  - `location`
  - `attention`
  - `company`
  - `address`
- La revision `b9c0d1e2f3a4` ya estaba marcada como aplicada en la base antes de que esas columnas fueran agregadas al archivo de migracion.
- Resultado:
  - SQLAlchemy intentaba consultar columnas inexistentes y FastAPI caia con:
    - `psycopg.errors.UndefinedColumn: column field_sheets.minimum_division does not exist`

Correccion aplicada:
- Se restauro `backend/migrations/versions/b9c0d1e2f3a4_add_field_sheet_certificate_client.py` para que solo contenga lo que realmente habia aplicado:
  - `certificate_client_mode`
  - `certificate_client_company`
  - `certificate_client_attention`
  - `certificate_client_address`
  - `apply_certificate_client_to_order`
- Se creo una migracion correctiva nueva:
  - `backend/migrations/versions/c1d2e3f4a5b6_add_missing_field_sheet_capture_columns.py`
- Esta nueva revision agrega fisicamente:
  - `minimum_division`
  - `location`
  - `attention`
  - `company`
  - `address`

Correcciones funcionales asociadas:
- `complete_field_sheet` ya no crea certificados; solo enlaza el certificado esperado activo si existe.
- Se agrego guard clause para evitar error si por inconsistencia no existe certificado activo al completar hoja.
- Los campos de captura nuevos ya persisten y se reflejan en:
  - modelo
  - schema
  - formularios React
  - vista previa
  - PDF

Validacion ejecutada:
- `../venv/bin/alembic upgrade head`
- `../venv/bin/alembic current --verbose`
  - resultado: `c1d2e3f4a5b6 (head)`
- `../venv/bin/python -m compileall app`
- `npm run build`
- `./scripts/myc build`
- `./scripts/myc doctor`
- `git diff --check`

Resultado:
- El error ASGI por columna faltante queda resuelto.
- `list_certificates`, `list_field_sheets`, `get_field_sheet` y la descarga PDF ya no fallan por ese esquema incompleto.

---

## Actualizacion de respaldo - plantillas de hojas y calibration_scope operativo

Fecha de actualizacion: 2026-07-02 09:20:00 CST

Estado detectado:
- El backup anterior ya incluia la correccion urgente de `field_sheets`, pero todavia no reflejaba cambios posteriores que ya existen en el repositorio y en la base.
- La base local ya no esta en `c1d2e3f4a5b6`; actualmente se encuentra en:
  - `2ffda0c6458f (head)`

Cambios adicionales ya presentes en el proyecto:
- Se agrego el endpoint de catalogo de plantillas de hojas de campo:
  - `GET /api/field-sheet-templates`
  - `GET /api/field-sheet-templates/{template_key}`
- Archivos incorporados para ese flujo:
  - `backend/app/routers/field_sheet_templates.py`
  - `backend/app/schemas/field_sheet_template.py`
  - `backend/app/services/field_sheet_templates.py`
- `backend/app/main.py` ya registra el router de plantillas para dejar disponible el catalogo desde la API principal.

Plantillas y vista previa:
- Ya existe la plantilla `anemometro` dentro del catalogo funcional de hojas.
- Se incorporo la plantilla PDF:
  - `backend/app/templates/field_sheet_anemometer_pdf.html`
- Se incorporo el layout visual reutilizable del frontend:
  - `frontend/src/components/field-sheets/FieldSheetLayout.jsx`
  - `frontend/src/components/field-sheets/FieldSheetLayout.css`
- El frontend ya consume `reserved_certificate_folio`, `minimum_division`, `location`, `attention`, `company` y `address` dentro de la captura y vista previa de la hoja.

Ajuste operativo en Ordenes de Servicio / Equipos:
- `service_order_items` ahora persiste `calibration_scope` directamente.
- Archivos ajustados:
  - `backend/app/models/service_order.py`
  - `backend/app/schemas/service_order.py`
  - `backend/app/services/service_orders.py`
  - `backend/app/services/equipment.py`
- Esto evita depender de `quotation_items` para determinar el tipo de certificado esperado al registrar equipos.
- La resolucion de tipo de certificado en equipos ahora usa el `calibration_scope` de la partida de orden:
  - `accredited_iso_17025` -> `acreditado`
  - `accredited_linked_lab` -> `vinculado`
  - `traceable` -> `trazable`

Migracion adicional:
- Nueva revision aplicada:
  - `backend/migrations/versions/2ffda0c6458f_add_calibration_scope_to_service_order_.py`
- Esta migracion agrega:
  - `service_order_items.calibration_scope`

Validacion de estado:
- `../venv/bin/alembic current --verbose`
  - resultado: `2ffda0c6458f (head)`
- `../venv/bin/alembic heads`
  - resultado: `2ffda0c6458f (head)`

Resultado:
- El backup queda alineado con el estado actual del repo y de la base local.
- Ya no hay desfase documental respecto al catalogo de plantillas, la persistencia de `calibration_scope` y la cadena de migraciones vigente.

---

## Ajuste ETS - alta de equipos por cupos de certificado, sin seleccion manual de partida

Fecha de actualizacion: 2026-07-02 09:55:00 CST

Objetivo aplicado:
- El alta de equipos dentro del ETS deja de depender operativamente de `service_order_item_id`.
- La Orden de Trabajo ahora se comporta como una bolsa de cupos por tipo de certificado:
  - `traceable`
  - `accredited_iso_17025`
  - `accredited_linked_lab`

Regla implementada:
- El backend calcula cupos por OT a partir de:
  - `service_order_items.quantity` agrupado por `calibration_scope`
  - certificados activos de la OT agrupados por `certificate_type`
- Mapeo usado:
  - `traceable` -> `trazable`
  - `accredited_iso_17025` -> `acreditado`
  - `accredited_linked_lab` -> `vinculado`

Backend:
- Nuevo helper central:
  - `backend/app/services/service_order_certificate_capacity.py`
- Responsabilidades de ese helper:
  - calcular cotizados/usados/disponibles por tipo
  - resolver automaticamente `calibration_scope` para un equipo nuevo
  - devolver `422` si existen varios tipos disponibles y el usuario no especifica cual requiere
  - devolver `409` si ya no hay cupo disponible para el tipo solicitado
  - resolver automaticamente `service_order_item_id` compatible con el scope, solo como dato interno auxiliar

Modelo y schema de equipos:
- `backend/app/models/equipment.py`
  - se agrega `equipment.calibration_scope`
- `backend/app/schemas/equipment.py`
  - `EquipmentCreate`, `EquipmentUpdate` y `EquipmentRead` ya exponen `calibration_scope`

Migracion nueva:
- `backend/migrations/versions/7c9e1f2a3b4c_add_calibration_scope_to_equipment.py`
- Agrega:
  - `equipment.calibration_scope`
- Incluye backfill inicial desde `service_order_items.calibration_scope` cuando existe relacion historica

Servicio de equipos:
- `backend/app/services/equipment.py`
- Cambios aplicados:
  - ya no depende de seleccion manual de partida para determinar el tipo de certificado
  - si el payload trae `calibration_scope`, valida cupo disponible
  - si no trae `calibration_scope` y solo hay un tipo disponible, lo asigna automaticamente
  - si hay varios tipos disponibles y el payload no especifica uno, responde `422`
  - al crear el equipo:
    - guarda `equipment.calibration_scope`
    - asigna `service_order_item_id` automaticamente si encuentra una partida compatible
    - crea el certificado esperado con el `certificate_type` correcto
  - en edicion:
    - se bloquea el cambio de tipo si el equipo ya tiene certificado activo, para no desalinear el folio reservado ya emitido

Servicio de certificados:
- `backend/app/services/certificates.py`
- Cambios aplicados:
  - ya acepta `certificate_type = vinculado`
  - ya evita duplicar certificados activos por equipo
  - el folio esperado para vinculados usa prefijo `MYCV`

Motor de folios:
- `backend/app/core/folios.py`
- El generador ya soporta:
  - `MYCT` para trazables
  - `MYCA` para acreditados
  - `MYCV` para vinculados

Frontend ETS:
- `frontend/src/pages/ServiceOrdersPage.jsx`
- Ajustes visibles:
  - se elimina la dependencia visual de partida en el alta de equipo
  - se agrega selector de tipo de certificado solo cuando la OT tiene mas de un tipo con cupo disponible
  - si solo existe un tipo disponible, se asigna automaticamente y el modal lo muestra bloqueado
  - el ETS muestra consumo por tipo:
    - trazables usados/cotizados
    - acreditados usados/cotizados
    - vinculados usados/cotizados
  - la tabla de equipos ahora muestra el tipo de certificado asignado al equipo

Compatibilidad:
- `service_order_items.calibration_scope` se mantiene como fuente comercial y de trazabilidad de la OT.
- `service_order_item_id` no se elimina del modelo; queda como enlace auxiliar, no como decision manual obligatoria.
- No se modifico el motor general de certificados fuera del soporte necesario para `vinculado`.

Validacion ejecutada:
- `../venv/bin/python -m compileall app`
- `../venv/bin/alembic upgrade head`
- `../venv/bin/alembic current --verbose`
  - resultado: `7c9e1f2a3b4c (head)`
- `../venv/bin/alembic heads`
  - resultado: `7c9e1f2a3b4c (head)`
- `npm run build`
- `./scripts/myc build`
- `git diff --check`

Observacion de validacion:
- La primera corrida paralela de `alembic upgrade head` y `./scripts/myc build` intento aplicar la misma migracion al mismo tiempo y produjo un `DuplicateColumn` transitorio.
- Se confirmo despues que:
  - la columna si quedo creada
  - Alembic quedo en `7c9e1f2a3b4c (head)`
  - la corrida final serial de `./scripts/myc build` paso correctamente

Resultado:
- El alta de equipos en ETS ya opera por cupos reales de certificado y no por seleccion manual de partida.
- El sistema bloquea sobreconsumo por tipo desde backend.
- El frontend solo pide al usuario la decision minima necesaria cuando la OT tiene mas de una bolsa activa.

---

## Fase - motor base de plantillas de hojas de campo

Fecha de actualizacion: 2026-07-03 09:20:00 CST

Objetivo aplicado:
- Se consolido un motor base de plantillas para Hojas de Campo dentro del flujo actual de Servicios / ETS.
- La hoja ya no depende de listas fijas repartidas entre backend, frontend y PDF.
- No se creo un modulo visible nuevo.

Alcance funcional:
- Se centralizo la definicion estructural de plantillas con soporte para:
  - `key`
  - `name`
  - `type`
  - `visible_fields`
  - `result_sections`
  - `columns`
  - `rows`
  - `pdf_template`
- La hoja sigue usando el certificado esperado activo del equipo.
- No se reactivaron procedimientos/patrones como requeridos.
- No se agrego calculo de incertidumbre ni logica avanzada.
- No se crean certificados desde la hoja.

Backend:
- Archivo central:
  - `backend/app/services/field_sheet_templates.py`
- Ahora concentra el registro de plantillas compatibles:
  - `general`
  - `electrica`
  - `anemometro`
  - `dimensional`
  - `temperatura`
  - `sonido`
  - `sonometro`
  - `manometro`
  - `tacometro`
  - `regla`
  - `vernier`
  - `micrometro`
  - `termometro`
  - `termohigrometro`
  - `flexometro`
  - `cronometro`
  - `masa`
  - `balanza`
  - `bascula`
  - `torquimetro`
  - `dinamometro`
  - `durometro`
  - `multimetro`
  - `transductor_presion`
  - `volumen`
- Tambien se mantuvo compatibilidad con claves historicas adicionales del schema:
  - `luxometro`
  - `peso_patron`

Helpers base creados/normalizados:
- `get_field_sheet_template(template_key)`
- `build_default_result_rows(template_key)`

Servicio de hojas:
- `backend/app/services/field_sheets.py`
- Ajustes aplicados:
  - deja de depender de `FIELD_SHEET_TEMPLATE_ROWS`
  - valida la existencia de `template_key` desde el registro central
  - usa `build_default_result_rows(...)` al crear la hoja
  - conserva `template_key` al actualizar
  - si la plantilla cambia en borrador, regenera `results_rows` segun la nueva definicion
  - si la plantilla no existe, devuelve error claro desde backend

Schema de plantillas:
- `backend/app/schemas/field_sheet_template.py`
- Ahora expone:
  - `type`
  - `visible_fields`
  - columnas de resultados con `source`, `width`, `unit` y `editable`

PDF:
- `backend/app/services/field_sheet_pdfs.py`
- Ajustes aplicados:
  - el PDF ya toma la definicion central de plantilla
  - agrupa secciones segun `result_sections`
  - cada seccion usa columnas dinamicas definidas por plantilla
  - sigue mostrando folio reservado y datos persistidos del equipo/cliente/hoja
- Templates actualizados:
  - `backend/app/templates/field_sheet_general_pdf.html`
  - `backend/app/templates/field_sheet_electrical_pdf.html`
  - `backend/app/templates/field_sheet_anemometer_pdf.html`
- En esta fase el PDF ya es dinamico por estructura, sin intentar aun maquetados especializados por magnitud.

Frontend:
- Nueva constante central:
  - `frontend/src/constants/fieldSheetTemplates.js`
- Ahora concentra:
  - opciones del selector
  - nombre visible de plantilla
  - secciones dinamicas
  - columnas de resultados
- `frontend/src/utils/fieldSheets.js`
  - deja de definir plantillas fijas locales
  - ahora deriva filas por default desde la constante central
  - agrega helper para construir secciones de resultados renderizables
- `frontend/src/pages/ServiceOrdersPage.jsx`
  - el selector de plantilla ya lee desde la constante central
  - al cambiar plantilla en borrador regenera `resultsRows`
  - la vista usa el nombre visible centralizado
  - la captura tecnica ya renderiza secciones y columnas segun la plantilla activa
- `frontend/src/components/field-sheets/FieldSheetLayout.jsx`
  - ahora muestra titulos de seccion dinamicos
  - la tabla usa columnas dinamicas por plantilla
  - se corrigio la actualizacion de celdas para plantillas con varias secciones

Compatibilidad preservada:
- creacion de hoja
- edicion de hoja
- completar hoja
- PDF de hoja
- folio reservado
- certificado esperado
- flujo ETS

Validacion ejecutada:
- `../venv/bin/python -m compileall app`
- `../venv/bin/alembic upgrade head`
- `npm run build`
- `./scripts/myc build`
- `git diff --check`

Estado de base:
- No se requirio nueva migracion para esta fase.
- La base permanece en:
  - `7c9e1f2a3b4c (head)`

Resultado:
- El proyecto ya tiene un motor base de plantillas de Hojas de Campo centralizado y reutilizable.
- Backend, frontend y PDF quedaron alineados sobre la misma estructura funcional.
- La siguiente fase puede especializar plantillas por magnitud sin volver a fragmentar la logica.

---

## Fase - motor de familias de tablas y diseñador visual de hojas de campo

Fecha de actualizacion: 2026-07-03 10:35:00 CST

Objetivo aplicado:
- Se evoluciono el motor base de plantillas hacia un esquema por bloques reutilizables y familias de tablas.
- Se agrego un editor interno de plantillas dentro de Configuracion, sin crear un modulo operativo separado del ETS.
- Las hojas nuevas y las existentes con snapshot ya no dependen de una estructura fija de columnas por codigo.

Arquitectura aplicada:
- Bloques soportados:
  - `GeneralDataBlock`
  - `EquipmentDataBlock`
  - `EnvironmentalBlock`
  - `SimpleComparisonTableBlock`
  - `MultiPointTableBlock`
  - `SectionedTableBlock`
  - `RepeatabilityTableBlock`
  - `DimensionalTableBlock`
  - `PressureTableBlock`
  - `MassBalanceTableBlock`
  - `ElectricalTableBlock`
  - `ObservationsBlock`
  - `SignaturesBlock`
- Cada bloque ya puede definir:
  - titulo visible
  - campos visibles
  - columnas
  - secciones
  - filas
  - min/max
  - si permite agregar filas
  - si es obligatorio
  - orden de captura
  - orden de impresion

Persistencia nueva:
- Nueva tabla:
  - `field_sheet_template_definitions`
- Campos implementados:
  - `id`
  - `template_key`
  - `name`
  - `description`
  - `status`
  - `version`
  - `definition_json`
  - `is_active`
  - `created_at`
  - `updated_at`
- Regla aplicada:
  - se conserva una version activa por `template_key`
  - el borrado es logico mediante `is_active/status`

Snapshots en hojas:
- `field_sheets` ahora guarda:
  - `template_definition_json`
  - `template_definition_version`
- Esto congela la definicion usada por cada hoja y evita que cambios posteriores en la plantilla activa alteren retroactivamente hojas ya creadas.

Resultados dinamicos:
- `field_sheet_results` ahora incorpora:
  - `row_data` JSON
- Se conserva compatibilidad con columnas antiguas:
  - `pattern_value`
  - `ibc_value_1`
  - `ibc_value_2`
  - `ibc_value_3`
  - `unit`
  - `notes`
- `row_data` permite ya soportar familias con columnas nuevas como:
  - `nominal_point`
  - `instrument_reading`
  - `error_value`
  - `result_value`
  - `ascending_pattern`
  - `eccentricity_value`
  - `repeatability_value`
  - etc.

Backend:
- Archivo central de logica:
  - `backend/app/services/field_sheet_templates.py`
- Capacidades agregadas:
  - definiciones fallback hardcodeadas por bloque
  - asignacion exacta inicial de plantillas a bloques
  - normalizacion de `definition_json`
  - derivacion automatica de:
    - `visible_fields`
    - `result_sections`
  - resolucion de plantilla activa desde DB con fallback hardcodeado
  - snapshot de plantilla al crear hoja
- CRUD basico implementado:
  - listar plantillas
  - crear plantilla
  - editar plantilla
  - duplicar version
  - activar version
  - archivar plantilla

Endpoints disponibles:
- `GET /api/field-sheet-templates`
- `GET /api/field-sheet-templates/{template_key}`
- `POST /api/field-sheet-templates`
- `PATCH /api/field-sheet-templates/{template_id}`
- `POST /api/field-sheet-templates/{template_id}/duplicate`
- `POST /api/field-sheet-templates/{template_id}/activate`
- `DELETE /api/field-sheet-templates/{template_id}`

Asignacion inicial de plantillas:
- Quedaron cubiertas las familias solicitadas para:
  - `general`
  - `temperatura`
  - `termometro`
  - `termohigrometro`
  - `cronometro`
  - `tacometro`
  - `anemometro`
  - `manometro`
  - `transductor_presion`
  - `valvula`
  - `dimensional`
  - `regla`
  - `vernier`
  - `micrometro`
  - `flexometro`
  - `masa`
  - `balanza`
  - `bascula`
  - `peso_patron`
  - `electrica`
  - `multimetro`
  - `luxometro`
  - `sonido`
  - `sonometro`
  - `torquimetro`
  - `dinamometro`
  - `durometro`
  - `volumen`

Frontend:
- `frontend/src/constants/fieldSheetTemplates.js`
  - ahora incluye familias de bloques, nombres de plantilla, asignaciones fallback y normalizacion de definiciones
- `frontend/src/utils/fieldSheets.js`
  - ahora genera filas por `result_sections`
  - normaliza `row_data`
  - construye payload dinamico para `results_rows`
- `frontend/src/pages/ServiceOrdersPage.jsx`
  - carga plantillas activas desde API
  - el tecnico ya usa la definicion activa al crear hoja
  - la vista tecnica usa snapshot de plantilla si la hoja ya existe
- `frontend/src/pages/SettingsPage.jsx`
  - se agrega la pestana interna `Plantillas de hojas`
- Nuevo panel:
  - `frontend/src/pages/settings/FieldSheetTemplatesSettingsPanel.jsx`
  - permite:
    - listar plantillas
    - editar metadata
    - agregar/quitar bloques
    - ordenar bloques
    - configurar filas y obligatoriedad
    - duplicar version
    - activar version
    - archivar
    - previsualizar la plantilla
- Restriccion de acceso:
  - solo roles administrativos / calidad / desarrollador deben administrarlo
  - el tecnico no ve esta herramienta en su flujo normal

PDF:
- `backend/app/services/field_sheet_pdfs.py`
  - ahora usa preferentemente `field_sheet.template_definition_json`
  - si no existe snapshot, cae al motor activo/fallback
  - el render ya toma valores de `row_data` por columna dinamica
- Los templates HTML existentes siguen reutilizados como base:
  - `field_sheet_general_pdf.html`
  - `field_sheet_electrical_pdf.html`
  - `field_sheet_anemometer_pdf.html`

Migracion nueva:
- `backend/migrations/versions/9a8b7c6d5e4f_add_field_sheet_template_definitions_.py`
- Acciones de migracion:
  - crea `field_sheet_template_definitions`
  - agrega snapshot de plantilla a `field_sheets`
  - agrega `row_data` a `field_sheet_results`
  - siembra 28 plantillas activas iniciales en DB
  - backfill de snapshots para hojas existentes
  - backfill de `row_data` para resultados existentes

Estado confirmado despues de migrar:
- `field_sheet_template_definitions` activos:
  - `28`
- `field_sheets` con snapshot de plantilla:
  - `12`

Validacion ejecutada:
- `../venv/bin/python -m compileall app`
- `../venv/bin/alembic upgrade head`
- `../venv/bin/alembic heads`
  - resultado: `9a8b7c6d5e4f (head)`
- `npm run build`
- `./scripts/myc build`
- `git diff --check`

Observacion operativa:
- En una corrida paralela inicial, `alembic upgrade head` y `./scripts/myc build` se pisaron durante la misma revision y generaron un error transitorio al reintentar crear objetos ya creados.
- La validacion final serial confirma que:
  - la revision quedo aplicada
  - el build completo pasa

Estado de base:
- Revision actual:
  - `9a8b7c6d5e4f (head)`

Resultado:
- MYC SYSTEM ya tiene familias de tablas reutilizables y un diseñador visual base de hojas de campo.
- Las plantillas activas viven en DB con versionado y fallback hardcodeado.
- El ETS sigue operativo sin tocar certificados, autenticacion, folios, cupos, facturacion ni portal cliente.

## ACTUALIZACION - CIERRE DE INFRAESTRUCTURA DE HOJAS DE CAMPO, CONSTRUCTOR VISUAL Y CONFIGURACION MAESTRA

Fecha de actualizacion:
- `2026-07-03`

Objetivo cerrado en esta etapa:
- endurecer el versionado de plantillas
- exponer importacion/exportacion
- consolidar catalogo de bloques y familias
- mover el render de captura/preview hacia un layout mas universal
- preparar Configuracion como panel maestro operativo sin romper ETS

Backend:
- `backend/app/schemas/field_sheet_template.py`
  - la definicion de plantilla ahora soporta:
    - `document_code`
    - `document_revision`
    - `table_family`
    - `validations`
    - `print_config`
    - `pdf_config`
    - `permissions_config`
    - `metadata`
  - los bloques ahora soportan:
    - `block_key`
    - `order`
    - `visible`
    - `fields`
    - `table_config`
    - `print_visible`
    - `capture_visible`
    - `pdf_visible`
    - `allow_remove_rows`
- `backend/app/services/field_sheet_templates.py`
  - se agregaron catalogos internos para:
    - tipos de bloque
    - familias de tabla
    - aliases historicos de plantilla
  - se consolidaron familias:
    - `direct_comparison`
    - `multipoint`
    - `pressure`
    - `dimensional`
    - `mass`
    - `electrical`
    - `repeatability`
    - `custom`
  - la normalizacion ya incorpora:
    - `table_family`
    - `document_code`
    - `document_revision`
    - metadatos y validaciones
  - al editar una plantilla `active` ya no se modifica en sitio:
    - ahora crea una nueva version
    - las hojas historicas conservan su snapshot
  - se agregaron servicios para:
    - exportar JSON de plantilla
    - importar plantilla como nueva version
    - exponer catalogo de bloques/familias
- `backend/app/routers/field_sheet_templates.py`
  - endpoints ahora protegidos por permisos
  - endpoints nuevos:
    - `GET /api/field-sheet-templates/catalog`
    - `GET /api/field-sheet-templates?include_all=true`
    - `POST /api/field-sheet-templates/import`
    - `GET /api/field-sheet-templates/{template_id}/export`
- `backend/app/core/permissions.py`
  - permisos agregados:
    - `field_sheet_templates.read`
    - `field_sheet_templates.create`
    - `field_sheet_templates.update`
    - `field_sheet_templates.approve`
    - `field_sheet_templates.archive`
    - `field_sheet_templates.export`
    - `field_sheet_templates.import`
    - `settings.system_parameters.read`
    - `settings.system_parameters.update`
    - `settings.master_catalogs.manage`
  - asignados a roles:
    - `Calidad`
    - `Desarrollador`
    - `Administrador` ya queda cubierto por `*`

Frontend:
- `frontend/src/constants/fieldSheetTemplates.js`
  - reestructurado para exponer:
    - catalogo de campos
    - familias de tabla
    - familias de bloque
    - fallback templates compatibles con oficiales
- `frontend/src/components/field-sheets/FieldSheetLayout.jsx`
  - deja de depender de una sola maqueta fija
  - ahora renderiza por bloques definidos en la plantilla
  - soporta preview universal de bloques y tablas dinamicas
- `frontend/src/pages/settings/FieldSheetTemplatesSettingsPanel.jsx`
  - el panel ya permite:
    - listar versiones
    - crear borradores desde plantilla base
    - editar metadata documental
    - elegir familia de tabla
    - agregar/quitar/reordenar bloques
    - publicar
    - duplicar
    - archivar
    - exportar JSON
    - importar JSON
    - previsualizar
  - agrega vistas auxiliares de:
    - familias de tablas
    - catalogo de bloques
    - panel maestro de configuracion
- `frontend/src/services/api.js`
  - helpers nuevos:
    - `getFieldSheetTemplateCatalog`
    - `exportFieldSheetTemplate`
    - `importFieldSheetTemplate`
  - `listFieldSheetTemplates` ahora soporta `includeAll`
- `frontend/src/pages/SettingsPage.jsx`
  - la vista ya se presenta como panel maestro operativo

Compatibilidad confirmada:
- se mantiene `row_data`
- se mantiene `template_definition_json`
- se mantiene `template_definition_version`
- se mantiene compatibilidad con `field_sheet_results` legacy
- no se tocaron:
  - motor de incertidumbre
  - certificados desde hojas
  - flujo ETS estructural
  - autenticacion PDF de certificados

Limitaciones reales que siguen intencionalmente fuera de esta etapa:
- no se implementaron calculos automaticos
- no se implemento incertidumbre automatica
- no se agrego drag and drop
- familias, parametros generales, folios y estados quedaron preparados visualmente dentro de Configuracion, pero no se llevo aun toda su persistencia dedicada a tablas nuevas
- el selector de plantillas del flujo tecnico sigue mostrando plantillas activas oficiales; las plantillas nuevas/custom creadas en Configuracion ya pueden versionarse/importarse/exportarse, pero su adopcion operativa total en todos los catalogos puede requerir una etapa adicional si se desea exponerlas como catalogo tecnico abierto

Validaciones ejecutadas en esta etapa:
- `../venv/bin/python -m compileall app`
- `../venv/bin/alembic upgrade head`
- `../venv/bin/alembic heads`
  - `9a8b7c6d5e4f (head)`
- `../venv/bin/alembic current --verbose`
  - revision actual confirmada: `9a8b7c6d5e4f`
- `npm run build`
- `./scripts/myc build`
- `./scripts/myc doctor`
- `git diff --check`

Resultado operativo:
- el sistema queda mas cerca de un motor universal de hojas de campo
- Calidad ya puede administrar versiones, publicar, importar y exportar sin tocar backend
- las hojas existentes no se alteran retroactivamente porque el snapshot/versionado ya quedo endurecido

## ACTUALIZACION - NORMALIZACION COMPLETA DEL MOTOR DE PLANTILLAS EN FRONTEND

Fecha de actualizacion:
- `2026-07-03`

Motivo:
- se detecto fragilidad real en frontend por consumo inconsistente de:
  - `resultSections`
  - `result_sections`
  - `definition`
  - `definition_json`
  - `template_definition`
  - `template_definition_json`
- esto podia provocar pantalla blanca o errores por `map`, `flatMap` o `filter` sobre valores no normalizados

Correccion estructural aplicada:
- se creo `normalizeTemplate(template)` en:
  - `frontend/src/utils/fieldSheets.js`
- desde ahi se centraliza la forma canonica de plantilla para todo el frontend

Forma canonica garantizada por `normalizeTemplate`:
- `template_key`
- `key`
- `name`
- `status`
- `version`
- `blocks`
- `result_sections`
- alias sincronizado `resultSections`
- `visible_fields`
- `document_code`
- `document_revision`
- `table_family`
- `validations`
- `print_config`
- `pdf_config`
- `permissions_config`
- `metadata`
- `definition`
- `definition_json`

Blindajes agregados:
- `safeArray`
- `safeObject`
- `normalizeColumn`
- `normalizeSection`
- `normalizeField`
- `normalizeBlock`
- construccion de secciones desde bloques cuando la plantilla no trae `result_sections`
- resolucion consistente de snapshots, definiciones anidadas y fallbacks

Funciones reforzadas en `frontend/src/utils/fieldSheets.js`:
- `buildDefaultResultsRows()`
- `buildFieldSheetResultSections()`
- `normalizeResultsRows()`
- `fieldSheetToForm()`
- `buildFieldSheetPayload()`
- `updateFieldSheetResultsRowsForTemplate()`
- `hasStructuredFieldSheetResults()`
- `getFieldSheetCompletionErrors()`
- helpers exportados:
  - `getFieldSheetTemplate()`
  - `getFieldSheetTemplateLabel()`

Consumidores migrados al normalizador unico:
- `frontend/src/pages/ServiceOrdersPage.jsx`
  - ya consume `getFieldSheetTemplate`, `getFieldSheetTemplateLabel` y `normalizeTemplate` desde `utils`
  - ya considera `template_definition_json` ademas de `template_definition`
- `frontend/src/pages/FieldSheetsPage.jsx`
  - ya toma etiqueta de plantilla desde `utils`
- `frontend/src/pages/settings/FieldSheetTemplatesSettingsPanel.jsx`
  - ya clona/carga/preview con `normalizeTemplate`
- `frontend/src/components/field-sheets/FieldSheetLayout.jsx`
  - ya normaliza internamente la plantilla recibida
  - ya protege acceso a bloques, secciones y filas

Validacion ejecutada:
- `npm run build`
- `../venv/bin/python -m compileall app`
- `git diff --check`
- `./scripts/myc build`
- prueba directa en Node sobre `normalizeTemplate`, `buildDefaultResultsRows` y `buildFieldSheetResultSections` con entradas:
  - `undefined`
  - plantilla minima
  - plantilla con `resultSections`
  - plantilla con `definition_json.result_sections`
  - bloque electrico con secciones
  - plantilla incompleta sin `blocks`
- verificacion de endpoint real:
  - `GET /api/field-sheet-templates?include_all=true`
  - confirmadas `28` plantillas devueltas por backend local

Observacion de validacion UI:
- el navegador interno quedo limitado para inyectar sesion administrativa por politica del runtime, asi que la verificacion principal de esta correccion se hizo por:
  - build real del frontend
  - resolucion real de datos del endpoint
  - ejecucion del normalizador y constructores con estructuras mixtas
- con esto se elimina la causa estructural de la pantalla blanca derivada de plantillas heterogeneas

## VERIFICACION DE RESPALDO AL DIA

Fecha de verificacion:
- `2026-07-06`

Estado:
- el backup queda actualizado y alineado con el estado actual del arbol de trabajo
- ya incluye:
  - infraestructura de plantillas versionadas
  - snapshots en hojas de campo
  - familias de tablas
  - panel maestro de plantillas
  - importacion/exportacion de plantillas
  - normalizacion estructural del frontend con `normalizeTemplate`

Observaciones operativas:
- en el arbol local existen archivos temporales/no canonicos detectados durante trabajo y validacion, por ejemplo:
  - `.tmp_field_sheet_templates.json`
  - `frontend/src/utils/fieldSheets (1).js`
- esos archivos no forman parte de la arquitectura oficial documentada y no se consideran parte del respaldo funcional del sistema

Validacion final del respaldo:
- el documento `docs/BACKUP_ESTADO_ACTUAL.md` refleja el estado funcional vigente de esta linea de trabajo al `2026-07-06`

## RESPALDO FASE NUEVA - MODULO DE FACTURACION MYC SYSTEM

Fecha de actualizacion:
- `2026-07-06`

Alcance implementado:
- se incorporo la base completa del modulo de facturacion sin crear un sistema CFDI externo ni dependencia con PAC
- la implementacion queda integrada al flujo actual de `Servicios / ETS / Certificados / Liberacion`
- el modulo financiero ya es visible desde navegacion con la seccion `Facturacion`

Backend incorporado:
- nuevo modelo `backend/app/models/invoice.py` con:
  - `Invoice`
  - `InvoiceItem`
  - `InvoicePayment`
  - `CreditNote`
  - `InvoiceSettings`
- relacion de facturas enlazada a `ServiceOrder`
- nuevo router `backend/app/routers/invoices.py`
- nuevos schemas `backend/app/schemas/invoice.py`
- nuevos servicios:
  - `backend/app/services/invoices.py`
  - `backend/app/services/invoice_pdfs.py`
- nuevas plantillas PDF:
  - `backend/app/templates/invoice_pdf.html`
  - `backend/app/templates/invoice_payment_receipt_pdf.html`
- router registrado en `backend/app/main.py`

Capacidades backend activas:
- listado y detalle de facturas
- creacion de factura desde orden de servicio
- conceptos ligados a orden, cotizacion y certificados liberados
- validacion para evitar doble facturacion de certificados activos sin autorizacion operativa
- cambio de estatus:
  - `draft`
  - `pending`
  - `issued`
  - `partially_paid`
  - `paid`
  - `overdue`
  - `cancelled`
- registro de pagos parciales y recalculo de saldo
- notas de credito internas
- cuentas por cobrar
- dashboard financiero
- servicios liberados sin factura
- configuracion de series, folios, impuestos, moneda, bancos y textos legales
- PDF de factura interna
- PDF de comprobante de pago

Endpoints incorporados:
- `GET /api/invoices/dashboard`
- `GET /api/invoices/accounts-receivable`
- `GET /api/invoices/released-uninvoiced`
- `GET /api/invoices`
- `GET /api/invoices/{invoice_id}`
- `POST /api/invoices`
- `PATCH /api/invoices/{invoice_id}`
- `POST /api/invoices/{invoice_id}/status`
- `POST /api/invoices/{invoice_id}/payments`
- `POST /api/invoices/{invoice_id}/credit-notes`
- `GET /api/invoices/{invoice_id}/pdf`
- `GET /api/invoice-payments`
- `GET /api/invoice-payments/{payment_id}`
- `GET /api/invoice-payments/{payment_id}/receipt-pdf`
- `GET /api/invoice-settings`
- `PATCH /api/invoice-settings`

Frontend incorporado:
- nueva pagina `frontend/src/pages/BillingPage.jsx`
- nueva integracion en `frontend/src/pages/App.jsx`
- modulo `finance` activado en `frontend/src/constants/navigation.js`
- integracion desde `frontend/src/pages/ServiceOrdersPage.jsx` para crear factura desde ETS
- nuevas funciones API en `frontend/src/services/api.js`

Capacidades frontend activas:
- tablero financiero operativo
- lista de facturas
- formulario de alta de factura
- registro de pagos
- creacion de notas de credito
- vista de cuentas por cobrar
- configuracion de facturacion
- accion directa desde ETS para abrir facturacion contextual con la orden seleccionada

Permisos y roles:
- el rol `Finanzas` ya cuenta con:
  - `payments.read`
  - `payments.manage`
  - `invoices.read`
  - `invoices.manage`
  - `release.manage`
- los endpoints financieros quedaron protegidos por permisos operativos y no expuestos como rutas abiertas

Correccion estructural relevante:
- se corrigio conflicto real de migraciones Alembic
- la migracion de facturacion quedo registrada como:
  - `backend/migrations/versions/0f1e2d3c4b5a_create_invoicing_module.py`
- se elimino el choque con una revision previa que ya usaba `a1b2c3d4e5f6`

Validacion ejecutada:
- `../venv/bin/python -m compileall app`
- `../venv/bin/alembic heads`
- `../venv/bin/alembic upgrade head`
- `npm run build`
- `./scripts/myc build`
- `git diff --check`

Limitaciones conscientes de esta fase:
- no se genero CFDI timbrado
- no se integro PAC
- no se genero XML fiscal SAT
- la facturacion implementada es interna/operativa y deja preparado el terreno para integracion fiscal posterior

Estado del respaldo:
- el backup queda actualizado al `2026-07-06` incluyendo la fase de facturacion ya integrada a la base oficial del proyecto

## AJUSTE DE RESPALDO - PREFABRICACION COMPLETA DE FACTURACION

Fecha de ajuste:
- `2026-07-06`

Fuente de referencia:
- instruccion `FASE NUEVA - PREFABRICACION COMPLETA DEL MODULO DE FACTURACION MYC SYSTEM`

Criterio de este ajuste:
- se alinea el backup al estado real del codigo
- se separa claramente:
  - lo ya implementado
  - lo parcialmente resuelto
  - lo aun no fabricado como pieza independiente

Estado real actual del modulo frente a la prefabricacion solicitada:

Ya implementado:
- modulo visible `Facturacion` en ruta `/dashboard#facturacion`
- integracion con navegacion principal
- pagina `frontend/src/pages/BillingPage.jsx`
- integracion desde ETS para crear factura contextual
- modelos activos:
  - `Invoice`
  - `InvoiceItem`
  - `InvoicePayment`
  - `CreditNote`
  - `InvoiceSettings`
- endpoints operativos para:
  - facturas
  - pagos
  - notas de credito dentro de factura
  - cuentas por cobrar
  - dashboard financiero
  - servicios liberados sin factura
  - configuracion de facturacion
- PDF interno de factura
- PDF de recibo de pago
- validacion para evitar doble facturacion de certificados activos
- folio interno configurable para facturas
- permisos operativos para rol `Finanzas`

Parcialmente resuelto:
- configuracion de facturacion:
  - hoy existe centralizada en `InvoiceSettings`
  - aun no esta separada en entidades dedicadas tipo:
    - `BillingSeries`
    - `BillingBankAccount`
    - `BillingPaymentMethod`
- servicios no facturados:
  - existe `GET /api/invoices/released-uninvoiced`
  - cubre el objetivo funcional de servicios/certificados liberados sin factura
  - aun no usa la ruta propuesta `GET /api/billing/unbilled-services`
- dashboard financiero:
  - existe `GET /api/invoices/dashboard`
  - entrega metricas base financieras
  - aun no esta expuesto bajo ruta separada `GET /api/billing/dashboard`
- cuentas por cobrar:
  - existe `GET /api/invoices/accounts-receivable`
  - cubre el listado funcional
  - aun no esta publicado como `GET /api/accounts-receivable`
- notas de credito:
  - hoy se crean dentro del contexto de una factura
  - aun no tienen router independiente completo con:
    - listado global
    - detalle
    - apply
    - cancel
- ETS / Facturacion:
  - ETS ya puede abrir facturacion y crear factura
  - falta una vista mas completa dentro de la carpeta ETS con:
    - facturas relacionadas
    - pagos
    - saldo
    - vencimiento
    - acciones administrativas completas

Pendiente como infraestructura separada:
- `CreditNoteItem`
- `BillingSettings` con nombre de dominio separado de `InvoiceSettings`
- `BillingSeries`
- `BillingBankAccount`
- `BillingPaymentMethod`
- routers separados:
  - `invoice_payments.py`
  - `credit_notes.py`
  - `billing.py`
- endpoints DELETE/PATCH dedicados para pagos y notas de credito
- endpoints semanticos separados:
  - `mark-pending`
  - `issue`
  - `cancel`
- motor documental administrativo de facturacion incrustado en `Configuracion / Panel Maestro`
- indicadores financieros integrados al Dashboard principal ejecutivo

Ajuste de redaccion importante:
- donde el backup anterior decia "base completa del modulo de facturacion", debe entenderse como:
  - base operativa funcional ya integrada
  - no como cierre al 100 por ciento de toda la prefabricacion administrativa solicitada en la nueva fase

Estado final del respaldo tras este ajuste:
- el backup queda al dia respecto de la nueva instruccion
- el modulo de facturacion existe y funciona
- la prefabricacion total solicitada sigue parcialmente abierta en los puntos listados arriba

## CORTE DE VERDAD ACTUAL - MODULOS Y CAPACIDADES NO DISPONIBLES EN EL SISTEMA VISIBLE

Fecha de corte:
- `2026-07-06`

Regla de lectura obligatoria para este backup:
- este documento contiene historial de fases y por eso hay entradas antiguas donde algunos modulos o motores aparecen como activos, visibles o en construccion
- a partir de esta seccion, cualquier referencia historica previa que contradiga el estado actual debe leerse como antecedente historico, no como disponibilidad vigente
- si una capacidad existe en codigo pero no esta visible, no forma parte del sistema disponible para operacion diaria

### 1. Comentado u oculto en navegacion principal

Estos elementos existen en codigo o fueron trabajados en fases previas, pero hoy no estan disponibles como modulos visibles del sistema:

- `Catalogo MYC` como modulo independiente:
  - en `frontend/src/constants/navigation.js` esta comentado
  - no existe como modulo visible en la navegacion principal
  - su infraestructura de conceptos/catalogo sigue viva en codigo y se usa de forma parcial desde cotizaciones/facturacion

- `Biblioteca Documental` como modulo independiente:
  - existe `frontend/src/pages/DocumentLibraryPage.jsx`
  - `frontend/src/pages/App.jsx` lo importa
  - hoy no tiene entrada activa en `modules`/`navigation`
  - por lo tanto no esta disponible como modulo visible para usuario final

- `Procedimientos` como modulo independiente:
  - existe `frontend/src/pages/ProceduresPage.jsx`
  - `frontend/src/pages/App.jsx` lo importa
  - hoy no tiene entrada activa en `modules`/`navigation`
  - no esta disponible como modulo visible del sistema

- `Incertidumbre` como modulo independiente:
  - existe `frontend/src/pages/UncertaintyPage.jsx`
  - `frontend/src/pages/App.jsx` lo importa
  - hoy no tiene entrada activa en `modules`/`navigation`
  - no esta disponible como modulo visible del sistema

- `FlowTest`:
  - existe `frontend/src/pages/FlowTestPage.jsx`
  - `frontend/src/pages/App.jsx` lo importa
  - hoy no tiene entrada activa en `modules`/`navigation`
  - no esta disponible para operacion normal

### 2. Disponible en backend o en archivos, pero no expuesto como experiencia vigente del sistema

Los siguientes componentes siguen presentes en codigo y/o API, pero no deben considerarse disponibles como parte del sistema visible actual:

- `client_portal`:
  - router registrado en `backend/app/main.py`
  - no existe experiencia visible integrada en la UI principal actual
  - el portal cliente avanzado debe considerarse no disponible como producto vigente

- `documents` / `document_templates` / `document_interpretations`:
  - routers activos en backend
  - existen servicios y modelos
  - no estan expuestos hoy como modulo principal visible para operacion general
  - deben considerarse infraestructura residual/oculta, no modulo vivo del sistema

- `technical_profiles`:
  - router activo en backend
  - sin modulo principal visible en la UI actual
  - debe considerarse fuera del sistema visible

- `uncertainty`:
  - router activo en backend
  - pagina frontend existente pero no visible en navegacion actual
  - debe considerarse motor/infraestructura en codigo, no modulo operativo disponible

- `metrology`:
  - router activo en backend
  - sin modulo visible actual
  - debe considerarse soporte tecnico en codigo, no capacidad visible del sistema

- `pattern_selection`:
  - router activo en backend
  - sin experiencia visible independiente actual
  - no debe asumirse como flujo disponible al usuario final

- `operational_engines`:
  - router activo en backend
  - corresponde a infraestructura de apoyo
  - no es modulo visible disponible para operacion diaria

### 3. Infraestructura interna que sigue existiendo pero no debe leerse como flujo vigente

Estos elementos no se eliminaron del codigo, pero tampoco deben entenderse como flujo activo o requisito visual del sistema actual:

- motores documentales heredados
- perfiles tecnicos auxiliares
- calculos/metodos de metrologia no visibles en la UX actual
- piezas heredadas de incertidumbre
- componentes auxiliares de procedimientos no visibles como modulo principal
- pruebas de flujo tipo `FlowTest`

### 4. Estado actual que si debe prevalecer

Lo disponible y visible hoy en el sistema principal es:
- `Dashboard`
- `Clientes`
- `Ventas / Cotizaciones`
- `Servicios`
- `Patrones`
- `Facturacion`
- `Configuracion`

Adicionalmente:
- varias capacidades tecnicas siguen existiendo en backend y archivos fuente
- mientras no tengan entrada activa en navegacion o flujo visible oficial, deben tratarse como:
  - comentadas
  - ocultas
  - residuales
  - solo en codigo

### 5. Instruccion de mantenimiento para futuras actualizaciones del backup

En este documento:
- toda funcionalidad que permanezca en codigo pero ya no este disponible en el sistema visible debe anotarse como:
  - `comentada`
  - `oculta`
  - `solo en codigo`
  - `infraestructura no expuesta`
- no debe volver a listarse como modulo activo salvo que reaparezca realmente en la navegacion o en el flujo oficial del sistema

## ACTUALIZACION 2026-07-06 - CLIENTES CHEQUEOS #039 #040 #041

Estado actualizado del modulo `Clientes`:
- se corrigio el flujo de `Constancia de Situacion Fiscal`
- se simplifico visualmente el modal de importacion
- la importacion de clientes ya persiste realmente en backend

### Constancia de Situacion Fiscal

Implementado:
- nuevo preview real de constancia fiscal antes de guardar:
  - `POST /api/clients/tax-constancy/preview`
- lectura basica de PDF usando `pypdf`
- intento de extraccion controlada de:
  - razon social
  - RFC fiscal
  - codigo postal fiscal
  - regimen fiscal
- si el archivo no es PDF:
  - el sistema responde mensaje honesto indicando que la extraccion automatica aun no esta disponible para ese tipo de archivo
- si el PDF no permite extraer datos:
  - el sistema responde mensaje honesto indicando que no se pudieron extraer datos fiscales automaticamente
- el formulario sigue permitiendo captura manual directa
- el archivo pendiente puede:
  - mantenerse para guardar despues
  - descartarse antes de guardar

Disponible en backend:
- `POST /api/clients/{client_id}/tax-constancy`
  - guarda la constancia en almacenamiento local del sistema

### Importacion de clientes

Implementado:
- plantilla oficial ajustada a encabezados `snake_case`:
  - `nombre_comercial`
  - `razon_social`
  - `rfc`
  - `contacto`
  - `telefono`
  - `correo`
  - `pais`
  - `calle`
  - `numero_exterior`
  - `numero_interior`
  - `colonia`
  - `municipio_ciudad`
  - `estado`
  - `codigo_postal`
  - `regimen_fiscal`
  - `uso_cfdi`
  - `estado_cliente`
- compatibilidad mantenida con encabezados historicos anteriores para no romper archivos previos
- endpoint real de preview:
  - `POST /api/clients/import/preview`
- endpoint real de confirmacion:
  - `POST /api/clients/import/confirm`
- la importacion persiste clientes en base de datos
- valida:
  - `nombre_comercial` obligatorio
  - `RFC` obligatorio
  - correo valido si existe
  - codigo postal numerico si existe
  - duplicado por RFC
- si un registro falla:
  - no rompe toda la importacion
  - se omite y el proceso continua

### Modal de importacion

Ajuste UX aplicado:
- se removio la presentacion extensa y saturada
- se dejo flujo visual mas limpio con:
  - titulo
  - selector de archivo
  - texto minimo de formato esperado
  - boton `Descargar plantilla`
  - boton `Importar`
  - resultado final simple

No queda como experiencia vigente:
- chips grandes de columnas detectadas
- paneles amplios de previsualizacion
- bloques de estadisticas visuales innecesarias
- textos redundantes tipo tutorial largo

### Validacion ejecutada

Validacion tecnica:
- `npm run build`
- `../venv/bin/python -m compileall app`
- `./scripts/myc build`

Validacion funcional real:
- se genero plantilla CSV de prueba con 2 clientes
- `POST /api/clients/import/preview` devolvio `2` registros validos
- `POST /api/clients/import/confirm` importo `2` clientes reales
- una segunda carga del mismo archivo detecto duplicados por RFC
- `POST /api/clients/tax-constancy/preview` extrajo datos fiscales desde PDF de prueba
- `GET /api/clients?include_inactive=true` confirmo presencia de clientes importados en la tabla de datos

Actualizacion 2026-07-07 11:40:15 CST - Mejora estructural definitiva del modulo Clientes:

Decision aplicada:
- el modulo Clientes deja de operar como formulario fiscal generico unico
- ahora se soporta estructura formal por tipo de contribuyente dentro de la misma arquitectura existente
- no se duplicaron componentes ni se creo un modulo nuevo

### Modelo de datos

Nuevos campos persistidos en `clients`:
- `client_type`
- `curp`
- `first_name`
- `first_last_name`
- `second_last_name`
- `street_type`
- `locality`
- `municipality`

Campos existentes que se conservan por compatibilidad:
- `legal_name`
- `commercial_name`
- `rfc`
- `tax_regime`
- `cfdi_use`
- `street`
- `exterior_number`
- `interior_number`
- `neighborhood`
- `city`
- `state`
- `postal_code`
- `country`
- `fiscal_postal_code`

Regla operativa vigente:
- `legal_name` sigue siendo el identificador legal canonico en backend
- para `persona_fisica` se compone desde `first_name + first_last_name + second_last_name`
- para `persona_moral` se usa razon social
- `city` se mantiene por compatibilidad con flujo legado, pero el dato operativo nuevo es `municipality`

Migracion aplicada:
- `backend/migrations/versions/2b3c4d5e6f7a_add_client_type_and_constancy_fields.py`
- `../venv/bin/alembic upgrade head` -> OK

### Formulario dinamico

Implementado en `frontend/src/pages/ClientsPage.jsx`:
- selector obligatorio `Tipo de cliente`
- formulario dinamico en el mismo modal
- `Persona Fisica` muestra:
  - RFC
  - CURP
  - Nombre(s)
  - Primer apellido
  - Segundo apellido
  - Nombre comercial
- `Persona Moral` muestra:
  - RFC
  - Razon social
  - Nombre comercial
- ambos tipos mantienen:
  - contacto
  - telefono
  - correo
  - domicilio
  - regimen fiscal
  - uso CFDI
  - constancia fiscal

### Lectura de constancia fiscal

Se amplio el lector backend en `backend/app/services/clients.py`.

Ahora intenta extraer:
- tipo de cliente
- razon social
- nombre comercial
- RFC
- CURP
- nombres
- apellidos
- codigo postal
- tipo de vialidad
- calle
- numero exterior
- numero interior
- colonia
- localidad
- municipio
- estado
- regimen fiscal

Reglas activas:
- si detecta `CURP` + `Nombre(s)` + `Primer Apellido`, clasifica `persona_fisica`
- si detecta `Denominacion/Razon Social` + `Regimen de Capital`, clasifica `persona_moral`
- si detecta un solo regimen fiscal, se asigna automaticamente
- si detecta varios regimenes, frontend obliga a elegir uno mediante selector visible
- si el PDF no permite extraer datos, se mantiene el mensaje honesto y no se simula exito

Endpoint involucrado:
- `POST /api/clients/tax-constancy/preview`

### Importacion y exportacion

La plantilla oficial ahora acepta tambien:
- `tipo_cliente`
- `curp`
- `nombres`
- `primer_apellido`
- `segundo_apellido`
- `tipo_vialidad`
- `localidad`
- `municipio`

Sigue vigente:
- `POST /api/clients/import/preview`
- `POST /api/clients/import/confirm`
- `GET /api/clients/export`

Nueva regla de importacion:
- el sistema acepta cliente mientras exista identidad suficiente
- no exige que todos los datos opcionales existan
- sigue bloqueando errores reales:
  - RFC faltante
  - correo invalido
  - codigo postal no numerico
  - duplicados por RFC/correo/nombre

### Listado y acciones

Cambios visibles en listado:
- la fila sigue siendo completamente cliqueable
- se muestra tipo de cliente por fila
- se agrega indicador `Informacion pendiente` con tooltip
- el tooltip reporta faltantes criticos:
  - RFC
  - nombre comercial
  - codigo postal
  - regimen fiscal
  - constancia fiscal
  - CURP / nombre completo cuando aplica

Cambios de lenguaje:
- se elimina el texto `Dar de baja` dentro del modulo Clientes
- la accion visible ahora es `Eliminar`
- se agrego eliminacion masiva visible sobre seleccion

### Verificacion real ejecutada

Validacion tecnica:
- `../venv/bin/python -m compileall app` -> OK
- `npm run build` -> OK
- `../venv/bin/alembic upgrade head` -> OK
- `../venv/bin/python -c "from app.main import app; print(app.title, len(app.routes))"` -> `ERP MYC 32`

Validacion funcional real sobre FastAPI/TestClient:
- `POST /api/clients` -> `201`
- `GET /api/clients?include_inactive=true` -> `200`
- `PATCH /api/clients/{id}` -> `200`
- `POST /api/clients/tax-constancy/preview` con PDF real de prueba -> `200`
- `DELETE /api/clients/{id}` -> `204`

Resultado confirmado:
- el backend responde con los nuevos campos
- el flujo de creacion/edicion no quedo desconectado
- la deteccion de `persona_fisica` desde constancia respondio correctamente en prueba real

### Codigo existente pero ya no expuesto visualmente

Debe mantenerse en contexto para futuras fases:
- el campo legacy `city` sigue en modelo, schemas y flujos de exportacion por compatibilidad; visualmente ya no es el dato principal frente a `municipality`
- `legal_name` sigue siendo obligatorio en backend aunque en `persona_fisica` ya no se captura como campo visible principal, porque se resuelve desde nombres/apellidos
- el archivo de constancia sigue guardandose con:
  - `tax_constancy_filename`
  - `tax_constancy_path`
  - `tax_constancy_uploaded_at`
- la desactivacion backend sigue usando auditoria `client.deactivated`; visualmente el modulo ya habla de `Eliminar`, pero la semantica fisica de borrado no cambio
- se conserva compatibilidad con encabezados historicos de importacion aunque la plantilla oficial ya evoluciono

Estado final de esta actualizacion:
- el backup queda alineado al estado actual del modulo Clientes y a la migracion ya aplicada en base local

Actualizacion 2026-07-07 11:52:00 CST - Correccion determinista del parser de Constancia de Situacion Fiscal:

Problema corregido:
- el lector del PDF ya estaba funcionando
- el error real estaba en el parser de etiquetas dentro de `backend/app/services/clients.py`
- la funcion anterior `_extract_label_value()` reutilizaba un `stop_labels` global y eso permitia que varios campos absorbieran texto del siguiente bloque

Cambio aplicado:
- se elimino el uso del `stop_labels` general para estas extracciones
- `_extract_label_value()` ahora recibe:
  - etiqueta de inicio
  - etiqueta de cierre especifica para ese campo
- cada lectura de constancia define sus propios limites inmediatos

Campos ajustados de forma explicita:
- razon social:
  - inicio: `Denominacion/Razon Social`
  - cierre: `Regimen Capital`
- nombre comercial:
  - inicio: `Nombre Comercial`
  - cierre: `Fecha inicio de operaciones`
- municipio:
  - inicio: `Nombre del Municipio o Demarcacion Territorial`
  - cierre: `Nombre de la Entidad Federativa`
- estado:
  - inicio: `Nombre de la Entidad Federativa`
  - cierre: `Entre Calle`

Resultado validado:
- `METROLOGIA Y SERVICIOS MYC` ya no arrastra `Regimen Capital`
- `METROLOGIA Y SERVICIOS MYC` ya no arrastra `Fecha inicio de operaciones`
- `SAN PEDRO TLAQUEPAQUE` ya no arrastra `Nombre de la Entidad Federativa`
- `JALISCO` ya no arrastra `Entre Calle`

Validacion ejecutada:
- prueba dirigida sobre `_extract_label_value()` con texto realista de constancia -> OK
- `../venv/bin/python -m compileall app` -> OK

Nota de mantenimiento:
- esta correccion fue intencionalmente puntual y determinista
- no se agregaron nuevas listas globales de corte para `Fecha inicio`, `Obligaciones`, `Estatus`, `Actividades Economicas` u otras etiquetas lejanas

Verificacion adicional posterior:
- se valido el parser completo con caso representativo de `persona_moral`
- se valido el parser completo con caso representativo de `persona_fisica`
- se corrigieron dos colisiones adicionales detectadas en esa prueba:
  - `CP` podia engancharse dentro de `CURP`
  - `street` podia arrancar desde el valor `Calle` de `Tipo de Vialidad`

Estado verificado final:
- `persona_moral` extrae correctamente:
  - razon social
  - nombre comercial
  - codigo postal
  - tipo de vialidad
  - calle
  - municipio
  - estado
  - regimen fiscal
- `persona_fisica` extrae correctamente:
  - RFC
  - CURP
  - nombres
  - apellidos
  - nombre comercial
  - codigo postal
  - tipo de vialidad
  - calle
  - municipio
  - estado
  - regimen fiscal

Validacion adicional con constancias reales del usuario:
- constancia moral real:
  - `Csf_MSM180712686.pdf`
  - resultado correcto para:
    - `client_type = persona_moral`
    - razon social
    - nombre comercial
    - domicilio
    - municipio
    - estado
    - regimen fiscal
- constancia fisica real:
  - `constancia orcort.pdf`
  - obligo ajuste adicional porque venia como:
    - `Nombre (s)` con espacio antes del parentesis
    - `Nombre Comercial` seguido por `Datos del domicilio registrado` en lugar de cerrar con `Fecha inicio de operaciones`
  - despues del ajuste:
    - `client_type = persona_fisica`
    - RFC
    - CURP
    - nombres
    - apellidos
    - nombre comercial
    - domicilio
    - municipio
    - estado
    - regimenes fiscales

Nota tecnica:
- en la fase de extraccion pura de constancia fisica, `legal_name` puede venir `None`
- eso no rompe el flujo actual porque el backend compone `legal_name` despues desde:
  - `first_name`
  - `first_last_name`
  - `second_last_name`

## Actualizacion 2026-07-07 17:23:14 CST - Refinamiento Ventas / Cotizaciones chequeos #032-#038

Alcance aplicado:
- Se atendieron chequeos tester del modulo `Ventas / Cotizaciones`.
- No se tocaron Clientes como modulo funcional.
- No se tocaron ETS/Servicios, Hojas de Campo, Certificados ni Facturacion.
- Se mantuvo estilo Liquid Glass.
- No se usaron `window.confirm`, `window.alert` ni `prompt`.

Chequeos resueltos:
- `#032 Selector de cliente en cotizacion`:
  - Se elimino el select largo de cliente dentro de la ficha.
  - Se agrego boton `Elegir cliente`.
  - El boton abre modal de busqueda de clientes activos.
  - La busqueda cubre nombre comercial, razon social, RFC, contacto y correo.
  - Al seleccionar cliente, se actualiza la cotizacion y se cierra el modal.
  - El cliente actual permanece visible dentro de la ficha.
- `#033 Asesor no se asigna`:
  - El router de cotizaciones conecta usuario autenticado opcional.
  - Al crear cotizacion, si hay sesion, `advisor_id` se asigna desde el usuario autenticado.
  - Si no hay token, se conserva compatibilidad de desarrollo sin romper llamadas antiguas.
  - `QuotationRead` expone `advisor_name`.
  - Frontend muestra nombre de asesor cuando existe.
  - No se pide asesor manualmente.
- `#034 TOTAL ilegible en PDF`:
  - En el PDF, el texto `Total` dentro del recuadro azul oscuro ahora se imprime en blanco.
  - No se modifico importe ni fondo.
- `#035 Autosave y recuperacion de versiones en cotizacion`:
  - La ficha de cotizacion ahora autosalva cambios con debounce.
  - Autosave aplica a:
    - cliente
    - vigencia
    - notas
    - condiciones de pago
  - Se agrego tabla `quotation_snapshots`.
  - Se escriben snapshots al crear, editar y modificar partidas.
  - Endpoints nuevos:
    - `GET /api/quotations/{quotation_id}/snapshots`
    - `POST /api/quotations/{quotation_id}/snapshots/restore`
  - UI minima de historial permite ver versiones y restaurar datos comerciales.
  - Pendiente tecnico controlado:
    - los snapshots guardan tambien datos de partidas, pero la restauracion actual se limita a campos comerciales de ficha; queda preparada la estructura para ampliar restauracion completa de partidas.
- `#036 Codigo postal fiscal no imprime correctamente en PDF`:
  - PDF usa `client.fiscal_postal_code`.
  - Si no existe, usa `client.postal_code`.
  - Ya no imprime `-` cuando existe alguno de esos datos.
- `#037 Quitar Uso CFDI del PDF de cotizacion`:
  - Se retiro `Uso CFDI` solamente del PDF de cotizacion.
  - No se elimino el dato del cliente ni de facturacion.
- `#038 Condiciones de pago no editables`:
  - Se agrego `payment_terms` a cotizaciones.
  - Se agrego campo editable `Condiciones de pago` en ficha.
  - Se imprime en PDF.
  - Si no hay valor, imprime `Por definir`.

Backend:
- `backend/app/models/quotation.py`
  - agrega `payment_terms`
  - agrega relacion `advisor`
  - agrega propiedad `advisor_name`
  - agrega modelo `QuotationSnapshot`
- `backend/app/schemas/quotation.py`
  - expone `payment_terms`
  - expone `advisor_name`
  - agrega schemas para snapshots/restauracion
- `backend/app/services/quotations.py`
  - crea cotizacion con `advisor_id = user_id` cuando hay usuario autenticado
  - escribe snapshots en crear/editar/partidas
  - lista snapshots
  - restaura snapshot comercial
- `backend/app/routers/quotations.py`
  - conecta `get_optional_current_user`
  - pasa `user_id` a crear, editar, partidas, cambios de estado y baja logica
  - agrega endpoints de snapshots
- `backend/app/services/auth.py`
  - agrega dependencia `get_optional_current_user`
- `backend/app/models/__init__.py`
  - registra `QuotationSnapshot`
- `backend/app/templates/quotation_pdf.html`
  - corrige color de `Total`
  - corrige CP fiscal
  - elimina Uso CFDI
  - imprime condiciones de pago desde cotizacion

Migracion:
- Nueva revision:
  - `backend/migrations/versions/3c4d5e6f7a8b_add_quotation_payment_terms_and_snapshots.py`
- Agrega:
  - `quotations.payment_terms`
  - tabla `quotation_snapshots`
- Base actual:
  - `3c4d5e6f7a8b (head)`

Frontend:
- `frontend/src/pages/QuotationsPage.jsx`
  - reemplaza select de cliente por modal `Elegir cliente`
  - agrega buscador de clientes activos
  - agrega autosave de ficha
  - muestra `advisor_name`
  - agrega `Condiciones de pago`
  - muestra historial de snapshots y accion de restauracion
- `frontend/src/services/api.js`
  - agrega:
    - `listQuotationSnapshots`
    - `restoreQuotationSnapshot`
- `frontend/src/constants/forms.js`
  - agrega `paymentTerms` al formulario de cotizacion
- `frontend/src/styles/global.css`
  - agrega estilos Liquid Glass para selector de cliente e historial de snapshots

Validacion ejecutada:
- `npm run build` -> OK con advertencia no bloqueante de chunk mayor a 500 kB.
- `../venv/bin/python -m compileall app` -> OK.
- `../venv/bin/alembic upgrade head` -> OK.
- `../venv/bin/alembic current` -> `3c4d5e6f7a8b (head)`.
- OpenAPI:
  - `ERP MYC 32`
  - `/api/quotations/{quotation_id}/snapshots` -> registrado
  - `/api/quotations/{quotation_id}/snapshots/restore` -> registrado
- `git diff --check` -> OK.
- `rg -n "window\\.confirm|window\\.alert|prompt\\(" frontend/src` -> sin resultados.

Backup:
- Dump SQL generado con `scripts/backup-db.sh`:
  - `backups/erp_myc_2026_07_07_1723.sql`
- Tamano verificado:
  - `679K`
- Lineas verificadas:
  - `7025`

## Actualizacion 2026-07-07 17:30:07 CST - Verificacion de impresion real PDF de cotizacion

Objetivo:
- Confirmar que los datos obligatorios de la cotizacion no solo esten en frontend/backend, sino que lleguen realmente al HTML renderizado y al PDF final generado por WeasyPrint.

Validacion ejecutada:
- Se creo una cotizacion temporal dentro de una transaccion con rollback.
- Se genero el HTML real mediante `backend/app/services/quotation_pdfs.py`.
- Se genero un PDF real mediante `generate_quotation_pdf`.
- Se extrajo texto del PDF generado con `pypdf` para confirmar impresion final.
- El archivo temporal generado para la prueba fue:
  - `/tmp/myc_quotation_print_check.pdf`

Campos confirmados en HTML y PDF final:
- Folio de cotizacion.
- Vendedor / asesor autenticado.
- Cliente, razon social, RFC, contacto, telefono y correo.
- Regimen fiscal.
- Codigo postal fiscal usando `client.fiscal_postal_code` y fallback a `client.postal_code`.
- Condiciones de pago desde `quotation.payment_terms`.
- Servicio / concepto de partida.
- Descripcion comercial de partida.
- Leyenda de cotizacion de partida.
- Clave SAT y unidad SAT.
- Subtotal, IVA/impuestos y total.
- Total con letra.
- Condiciones comerciales.
- Notas de cotizacion.

Campo confirmado como removido del PDF:
- `Uso CFDI` no aparece en el HTML ni en el texto extraido del PDF.

Resultado de prueba:
- `PDF_RENDER_CHECK_OK 45123 Cotizacion_MYC-PDF-TEST-PRINT_Cliente-PDF.pdf`
- `PDF_TEXT_CHECK_OK 45123 2 Cotizacion_MYC-PDF-TEST-PRINT_Cliente-PDF.pdf /tmp/myc_quotation_print_check.pdf`

Backup:
- Dump SQL generado con `scripts/backup-db.sh`:
  - `backups/erp_myc_2026_07_07_1730.sql`
- Tamano verificado:
  - `679K`
- Lineas verificadas:
  - `7025`

## Actualizacion 2026-07-08 10:24:00 CST - Cobertura CSS en Cotizaciones

Objetivo:
- Revisar que las clases usadas en Ventas / Cotizaciones y en el PDF de cotizacion tengan cobertura CSS real.

Revision ejecutada:
- Se cruzaron clases estaticas de `frontend/src/pages/QuotationsPage.jsx` contra `frontend/src/styles/global.css`.
- Se cruzaron clases del template `backend/app/templates/quotation_pdf.html` contra sus estilos embebidos.
- El template PDF quedo confirmado con clases cubiertas.
- En frontend solo quedaron prefijos dinamicos esperados:
  - `status-`
  - `import-row--`
- Las variantes reales de esos prefijos ya tienen reglas de estilo.

Ajustes CSS aplicados:
- `frontend/src/styles/global.css`
  - Se agrego cobertura para `quotation-modal`.
  - Se agrego cobertura para `quotations-workspace`.
  - Se agrego cobertura para `quotation-detail-form`.
  - Se agrego cobertura para `empty-state`.
  - Se agrego cobertura para `import-row--valid`.

Validacion ejecutada:
- Cruce automatico de clases de `QuotationsPage.jsx` contra `global.css` -> sin clases estaticas faltantes.
- Cruce automatico de clases de `quotation_pdf.html` contra estilos embebidos -> OK.
- `npm run build` -> OK con advertencia no bloqueante de chunk mayor a 500 kB.
- `git diff --check` -> OK.

Backup:
- Dump SQL generado con `scripts/backup-db.sh`:
  - `backups/erp_myc_2026_07_08_1024.sql`
- Tamano verificado:
  - `603K`
- Lineas verificadas:
  - `6629`

## Actualizacion 2026-07-08 10:41:55 CST - Politica central de almacenamiento y cierre Ventas Finalizado

Decision de version:
- Se declara `ERP MYC v0.3.0`.
- Nombre de version: `Ventas Finalizado`.
- Version anterior: `v0.2.0 (Clientes Finalizado)`.
- El modulo `Ventas / Cotizaciones` queda cerrado y sellado como modulo finalizado para esta entrega.

Objetivo aplicado:
- Ningun archivo fisico debe permanecer en `storage/` si ya no existe una referencia activa dentro del sistema.
- La regla queda preparada para Clientes, Cotizaciones, Ordenes de servicio, Equipos, Hojas de campo, Certificados, Facturacion, Evidencias y modulos futuros.
- No se corrio una purga historica masiva automatica sobre archivos existentes; se dejo preparada la herramienta central para ejecucion controlada.

Servicio central nuevo:
- `backend/app/services/storage_service.py`

Responsabilidades implementadas:
- Guardar archivos con nombre seguro.
- Resolver rutas relativas contra `storage/`.
- Verificar existencia dentro del almacenamiento permitido.
- Contar referencias activas en modelos SQLAlchemy registrados.
- Eliminar archivo fisico solo cuando no tenga referencias activas.
- Registrar auditoria por eliminacion fisica.
- Exponer barrido controlado de archivos huerfanos mediante `delete_orphaned_files()`.

Regla de referencias:
- El conteo revisa columnas de texto/ruta registradas en modelos ORM, incluyendo:
  - `file_path`
  - `certificate_file_path`
  - `tax_constancy_path`
  - `final_pdf_path`
  - `authenticated_pdf_path`
  - columnas terminadas en `_path`
- Si el modelo tiene `is_active`, solo cuenta registros activos.
- Si el modelo tiene `deleted_at`, ignora registros eliminados logicamente.
- Nunca elimina un archivo que todavia tenga al menos una referencia activa.

Integraciones realizadas:
- Clientes:
  - La constancia fiscal se guarda mediante el servicio central.
  - Al reemplazar constancia, la anterior se elimina fisicamente si queda sin referencias.
  - Al dar de baja cliente, se limpian referencias de constancia y se elimina el archivo si queda huerfano.
- Certificados:
  - El PDF final se guarda mediante el servicio central.
  - Al reemplazar PDF final, se limpian autenticaciones obsoletas asociadas al PDF anterior.
  - Al reemplazar PDF final, el PDF anterior y su PDF autenticado anterior se eliminan si quedan sin referencias.
  - Al dar de baja certificado no liberado, se limpian referencias documentales y se eliminan archivos sin referencias.
  - Al regenerar PDF autenticado, la version autenticada anterior se elimina si queda sin referencias.
- Descargas:
  - Los endpoints de PDF original, PDF autenticado y portal cliente resuelven rutas con el servicio central.

Auditoria:
- Toda eliminacion fisica controlada registra `storage.file_deleted`.
- Se guarda:
  - usuario
  - modulo
  - entidad
  - id de registro
  - nombre de archivo
  - ruta
  - motivo
- Motivo base aplicado:
  - `Archivo eliminado automaticamente por quedar sin referencias.`

Validacion ejecutada:
- `../venv/bin/python -m compileall app` -> OK.
- Prueba funcional con base local:
  - archivo temporal creado en `storage/temporales`
  - referencia activa creada en cliente temporal
  - eliminacion bloqueada mientras existia referencia activa
  - referencia limpiada
  - archivo eliminado al quedar sin referencias
  - resultado: `STORAGE_POLICY_CHECK_OK 1 0 True`
- Prueba de rutas de almacenamiento sin base:
  - resultado: `STORAGE_PATH_CHECK_OK temporales/storage_path_check.txt`
- `../venv/bin/python -c "from app.main import app; print(app.title, len(app.routes))"` -> `ERP MYC 32`.
- `npm run build` -> OK con advertencia no bloqueante de chunk mayor a 500 kB.
- `./scripts/myc build` -> OK durante la fase.
- `git diff --check` -> OK.

Observacion de validacion:
- Despues del ajuste final de preparacion de rutas, se intento repetir la prueba funcional con base local, pero la aprobacion automatica del runtime fue rechazada por limite de creditos del workspace.
- No se intento evadir esa restriccion.
- La validacion final se completo con compile, import de app, build frontend, prueba de rutas y diff-check.

Backup:
- Dump SQL generado con `scripts/backup-db.sh`:
  - `backups/erp_myc_2026_07_08_1041.sql`
- Tamano verificado:
  - `609K`
- Lineas verificadas:
  - `6649`

## Actualizacion 2026-07-08 11:02:14 CST - Corte real de backup posterior a Ventas Finalizado

Objetivo de esta actualizacion:
- Alinear el backup con el estado real del arbol de trabajo al momento del corte.
- No declarar como implementada ninguna fase que no exista todavia en codigo.
- Registrar expresamente que la instruccion adjunta sobre `Servicios / ETS` queda pendiente de ejecucion tecnica.

Estado real de version:
- Version actual del sistema:
  - `ERP MYC v0.3.0`
- Nombre de version:
  - `Ventas Finalizado`
- `frontend/package.json` confirma:
  - `"version": "0.3.0"`
- Base local Alembic verificada:
  - `3c4d5e6f7a8b (head)`
- Aplicacion importada:
  - `ERP MYC 32`

Estado Git real verificado:
```text
## main...origin/main
 M README.md
 M backend/app/routers/certificates.py
 M backend/app/routers/client_portal.py
 M backend/app/services/certificate_authentication.py
 M backend/app/services/certificates.py
 M backend/app/services/clients.py
 M docs/BACKUP_ESTADO_ACTUAL.md
 M frontend/.env.local
 M frontend/package-lock.json
 M frontend/package.json
 M frontend/src/pages/QuotationsPage.jsx
 M frontend/src/styles/global.css
?? backend/app/services/storage_service.py
?? backups/erp_myc_2026_07_08_1024.sql
?? backups/erp_myc_2026_07_08_1041.sql
```

Cambios reales presentes en el arbol:
- `README.md`
  - actualizado para reflejar la version vigente.
- `frontend/package.json` y `frontend/package-lock.json`
  - version actualizada a `0.3.0`.
- `backend/app/services/storage_service.py`
  - servicio central nuevo de politica de almacenamiento.
- `backend/app/services/clients.py`
  - integra almacenamiento central para constancia fiscal y limpieza controlada al reemplazar/eliminar.
- `backend/app/services/certificates.py`
  - integra almacenamiento central para PDF original, PDF autenticado y limpieza de referencias documentales.
- `backend/app/services/certificate_authentication.py`
  - ajusta resolucion/limpieza del PDF autenticado con la politica central de almacenamiento.
- `backend/app/routers/certificates.py`
  - descarga de PDF original/autenticado resuelta con servicio central.
- `backend/app/routers/client_portal.py`
  - descarga de certificado publicado resuelta con servicio central.
- `frontend/src/pages/QuotationsPage.jsx`
  - ajuste menor pendiente dentro del modulo Ventas / Cotizaciones.
- `frontend/src/styles/global.css`
  - cobertura CSS agregada para Cotizaciones.
- `frontend/.env.local`
  - archivo local modificado; no debe asumirse como cambio funcional versionable sin revision manual.

Backups SQL presentes al corte:
- `backups/erp_myc_2026_07_08_1024.sql`
  - tamano observado: `603K`
  - corresponde a cobertura CSS de Cotizaciones.
- `backups/erp_myc_2026_07_08_1041.sql`
  - tamano observado: `609K`
  - corresponde a politica central de almacenamiento y cierre `Ventas Finalizado`.

Validacion ejecutada en este corte:
- `../venv/bin/alembic current` -> `3c4d5e6f7a8b (head)`
- `../venv/bin/python -c "from app.main import app; print(app.title, len(app.routes))"` -> `ERP MYC 32`
- `rg -n "window\\.confirm|window\\.alert|window\\.prompt|alert\\(|prompt\\(" frontend/src` -> sin resultados

Validaciones heredadas de la fase inmediata anterior:
- `../venv/bin/python -m compileall app` -> OK.
- `npm run build` -> OK con advertencia no bloqueante de chunk mayor a 500 kB.
- `./scripts/myc build` -> OK durante la fase.
- `git diff --check` -> OK.

Estado de la instruccion adjunta sobre `Servicios / ETS`:
- La instruccion recibida pide trabajar unicamente sobre `Servicios / ETS` y refinar el expediente guiado por etapas.
- Al revisar el arbol real de cambios, no existen modificaciones actuales en:
  - `frontend/src/pages/ServiceOrdersPage.jsx`
  - `backend/app/services/service_orders.py`
  - `backend/app/routers/service_orders.py`
  - `backend/app/schemas/service_order.py`
  - `backend/app/models/service_order.py`
- Por lo tanto, esa fase no debe documentarse como implementada.
- Queda pendiente ejecutar tecnicamente los puntos de ETS:
  - eliminar columna `Acciones` y boton `Abrir ETS`
  - mostrar asesor/tecnico por nombre, no por ID
  - selector de tecnico por usuario
  - cinta superior de acciones del modal
  - reemplazar textos `Dar de baja` por `Eliminar`
  - retirar botonera global de estados
  - avance visual por pestaña/etapa
  - completar/reabrir etapas con auditoria cuando aplique
  - permitir Captura y Calidad en paralelo sin esperar el 100% de hojas

Regla de mantenimiento:
- Este backup queda alineado al estado real del repositorio al `2026-07-08 11:02:14 CST`.
- Este fue un corte previo a la implementacion tecnica de `Servicios / ETS`.
- La actualizacion posterior de `2026-07-08 11:12:28 CST` deja registrado el refinamiento ETS ya aplicado.

## Actualizacion 2026-07-08 11:12:28 CST - Refinamiento operativo Servicios / ETS guiado por etapas

Alcance aplicado:
- Se trabajo unicamente sobre el modulo visible `Servicios / ETS`.
- No se crearon modulos nuevos.
- No se reactivaron modulos ocultos.
- No se modifico Facturacion ni Clientes.
- Hojas de Campo solo recibio ajustes de texto/flujo visual dentro del ETS para no romper enlaces existentes.
- No se agrego migracion; se mantuvo compatibilidad con `service_orders.status` actual.
- Se mantuvo estilo Liquid Glass.
- No se usaron `window.confirm`, `window.alert` ni `prompt`.

Backend:
- `backend/app/models/service_order.py`
  - Se agregaron propiedades calculadas:
    - `advisor_name`
    - `technician_name`
  - Ambas devuelven nombre completo o correo del usuario relacionado.
- `backend/app/schemas/service_order.py`
  - `ServiceOrderRead` ahora expone:
    - `advisor_name`
    - `technician_name`
- `backend/app/services/service_orders.py`
  - `list_service_orders` y `get_service_order` cargan relaciones:
    - `advisor`
    - `technician`
  - Esto evita mostrar IDs internos en frontend y mantiene compatibilidad con `advisor_id` / `technician_id`.

Frontend ETS:
- `frontend/src/pages/ServiceOrdersPage.jsx`
  - Se elimino la columna `Acciones` del listado de Servicios / ETS.
  - Se elimino el texto/boton `Abrir ETS`.
  - La fila completa sigue abriendo el ETS con click y conserva accesibilidad por teclado al ser boton.
  - El listado ya muestra responsable por nombre:
    - `technician_name`
    - fallback a usuario cargado
    - fallback final `Sin asignar`
  - Dentro del modal ETS, `Asesor` ya muestra nombre y no `#id`.
  - El tecnico ya no se captura con input numerico.
  - El tecnico se selecciona desde lista de usuarios activos cuando el rol del usuario actual permite leer usuarios.
  - Si la lista de usuarios no esta disponible por permisos, el sistema conserva el tecnico actual y muestra nombre/fallback sin romper PATCH.
  - Se agrego cinta superior de acciones del modal:
    - Ver orden PDF
    - Descargar PDF
    - Imprimir
    - Guardar cambios
    - Cerrar
  - Se retiro la botonera global `Acciones de estado`.
  - Se retiraron botones globales de cambio de estado:
    - Confirmar
    - Llamar
    - Iniciar
    - Captura
    - Calidad
    - Pendiente pago
    - Liberar
    - Cerrar
  - El flujo visual ahora se guia por pestañas/etapas del expediente.
  - Las pestañas muestran badge de etapa:
    - Lista
    - En proceso
    - Disponible
    - Pendiente
    - Bloqueada
    - Reabierta
  - Se agrego `Marcar resumen listo`.
    - Se habilita solo con:
      - fecha de agenda
      - fecha de servicio
      - tecnico asignado
    - Reutiliza el PATCH actual de la orden.
    - Si la orden esta `scheduled`, el servicio backend ya la confirma automaticamente al guardar esos campos.
  - Se agrego `Siguiente: Equipos` cuando Resumen esta listo.
  - Se agrego `Marcar equipos listos` cuando existen equipos registrados y no se excede el limite de 10 por OT.
  - Se agrego accion visual administrativa para:
    - reabrir Resumen
    - reabrir Equipos
  - La reapertura queda como preparacion visual; auditoria formal requiere endpoint dedicado si se quiere persistir.
  - Se reemplazo lenguaje visual `Dar de baja` por `Eliminar` en el ETS:
    - orden
    - equipo
    - hoja de campo
  - Los mensajes aclaran que la eliminacion es operativa/visual y conserva trazabilidad; el backend mantiene baja logica.
  - En Hojas de Campo dentro del ETS se agrego nota de flujo paralelo:
    - Captura puede avanzar con hojas utilizables o certificados esperados disponibles.
    - El tecnico puede seguir completando hojas mientras Captura trabaja.
  - En Captura se agrego nota operativa:
    - la carga de PDFs no espera el cierre total de hojas.
    - cada certificado puede avanzar conforme este listo.
  - Se mantuvieron acciones internas por pestaña:
    - Equipos: editar/estado/abrir hoja/eliminar.
    - Captura: iniciar, subir PDF, validar, enviar a calidad.
    - Calidad: revisar, autenticar aprobados, liberar autenticados.
  - Esto evita depender de una botonera global sin romper flujos existentes.

CSS:
- `frontend/src/styles/global.css`
  - Se ajusto grid del listado `service-orders-table` a 13 columnas reales.
  - Se corrigio grid de `equipment-table` para la columna `Acciones`.
  - Se agregaron estilos:
    - `.ets-modal-action-ribbon`
    - `.ets-stage-badge`
    - `.ets-inline-stage`
    - `.ets-stage-note`
  - Las etapas usan colores/badges claros:
    - verde para listo
    - azul para en proceso
    - rojo claro para bloqueada
    - amarillo para reabierta

Puntos resueltos:
- #1 Listado sin columna `Acciones` ni boton `Abrir ETS`.
- #2 Asesor y tecnico visibles por nombre cuando existe dato disponible.
- #3 Selector visual de tecnico por usuario, compatible con `technician_id`.
- #4 Cinta superior del ETS con acciones principales.
- #5 Lenguaje `Eliminar` en lugar de `Dar de baja` dentro del ETS.
- #6 Retiro de seccion `Acciones de estado` y botonera global de transiciones.
- #7 Modelo visual inicial de avance por etapa en pestañas.
- #8 Boton `Marcar resumen listo` con requisitos minimos.
- #9 Equipos como etapa con boton `Marcar equipos listos` y limite 10 visible.
- #10 Flujo paralelo Hojas / Captura documentado visualmente.
- #11 Captura / PDFs / Calidad preparados para avanzar por certificado disponible.

Puntos parcialmente preparados:
- #9 Firma de Orden de Trabajo:
  - Se dejo mensaje visual `Orden de trabajo pendiente de firma`.
  - No se agrego campo persistente porque la fase pidio no romper backend y no habia campo existente.
- #12 Reabrir etapas:
  - Se agrego accion visual para Administrador/Desarrollador.
  - No se persiste ni audita todavia; queda pendiente un endpoint/campo formal si se requiere trazabilidad completa.
- Selector de usuarios:
  - Usa `GET /api/users` cuando el usuario tiene permiso.
  - Si un rol operativo no puede leer usuarios, se conserva compatibilidad visual con el nombre ya expuesto por `ServiceOrderRead` o `Sin asignar`.

Validacion ejecutada:
- `npm run build` -> OK con advertencia no bloqueante de chunk mayor a 500 kB.
- `../venv/bin/python -m compileall app` -> OK.
- `../venv/bin/alembic current` -> `3c4d5e6f7a8b (head)`.
- No hubo migracion nueva; no se ejecuto `alembic upgrade head`.
- OpenAPI:
  - `ERP MYC 32`
  - `ServiceOrderRead.advisor_name` -> `True`
  - `ServiceOrderRead.technician_name` -> `True`
- `git diff --check` -> OK.
- `rg -n "window\\.confirm|window\\.alert|window\\.prompt|alert\\(|prompt\\(" frontend/src` -> sin resultados.
- Busqueda especifica en ETS:
  - `Dar de baja`
  - `Acciones de estado`
  - `Abrir ETS`
  - `ID de usuario tecnico`
  - sin resultados en `frontend/src/pages/ServiceOrdersPage.jsx`.

Backup:
- Dump SQL generado con `scripts/backup-db.sh`:
  - `backups/erp_myc_2026_07_08_1112.sql`
- Tamano verificado:
  - `610K`
- Lineas verificadas:
  - `6654`

## Actualizacion 2026-07-08 11:51:30 CST - Segunda pasada ETS como tablero operativo

Alcance aplicado:
- Se continuo trabajando exclusivamente sobre `Servicios / ETS`, salvo una integracion minima en `Ventas / Cotizaciones` para abrir la cotizacion origen desde el ETS.
- No se modifico el modulo independiente de Hojas de Campo.
- No se agregaron migraciones ni endpoints nuevos.
- Se mantuvo compatibilidad con backend existente.
- No se usaron `window.confirm`, `window.alert` ni `prompt`.

Cambios principales en Servicios / ETS:
- Selector de tecnico:
  - Se elimino el `<select>` HTML tradicional del resumen ETS.
  - Se agrego selector visual tipo buscador, equivalente al selector de cliente usado en cotizaciones.
  - Muestra tarjetas de usuarios operativos por nombre, correo y rol.
  - Permite dejar `Sin asignar`.
  - Si hay mas de 15 usuarios, pagina en bloques de 5 manteniendo busqueda.
  - El payload sigue enviando `technician_id` al PATCH existente.
- Buscador interno del ETS:
  - Se agrego buscador dentro del expediente abierto.
  - Filtra por OT, equipo, marca, modelo, serie, identificacion interna, hoja, certificado, PDF, codigo de autenticacion y folios.
  - Aplica a tarjetas de equipos y listados de certificados/captura/calidad.
- Resumen clickeable:
  - `Cotizacion origen` abre el modulo de cotizaciones y carga la cotizacion vinculada.
  - `Equipos registrados` abre la pestaña Equipos.
  - `Hojas creadas` abre Hojas de Campo.
  - `Certificados esperados` abre Certificados.
  - `PDFs subidos` abre Documentos.
  - `Ordenes de trabajo` ahora se presenta como lista clickeable de OT.
- Soporte visual para varias OT:
  - El resumen agrupa ordenes relacionadas por cotizacion cuando existen.
  - Cada OT muestra numero de trabajo y conteo de equipos.
  - Al hacer clic en una OT, abre Hojas de Campo filtrando por esa OT.
  - Limitacion: el modelo backend vigente sigue representando cada OT como `service_order`; no se agrego una entidad padre nueva de Orden de Servicio con varias OT.
- Equipos:
  - Se reemplazo la tabla tradicional por tarjetas clickeables.
  - Cada tarjeta muestra instrumento, marca, modelo, serie, ID interno, tipo de certificado, estado, folio reservado, hoja, certificado y PDF.
  - Se retiro la botonera visible del listado:
    - Editar
    - Realizando
    - Calibrado
    - Etiquetado
    - No realizado
    - Abrir hoja
    - Eliminar
  - Las acciones ahora viven dentro del detalle del equipo.
- Detalle de equipo:
  - Nueva ficha/modal interna con datos operativos.
  - Concentra acciones de editar, cambiar estado, abrir/crear hoja y eliminar.
  - Mantiene la logica existente sin eliminar funciones.
- Agregar equipo:
  - Los cupos de certificado se redisenaron en filas independientes:
    - Trazables
    - Acreditados
    - Vinculados
  - Se agregaron botones rapidos en Condicion inicial:
    - `Buen estado general` -> `Equipo recibido en buen estado general.`
    - `Mal estado` -> `Equipo recibido con anomalías visibles.`
  - Las observaciones particulares siguen en `Notas`.
- Flujo paralelo:
  - Captura sigue disponible cuando existe una hoja utilizable o certificado esperado.
  - No se exige cerrar todas las hojas para permitir Captura.
  - Calidad y Certificados siguen trabajando por certificado disponible.

Integracion minima con Cotizaciones:
- `frontend/src/pages/QuotationsPage.jsx`
  - Lee `sessionStorage.myc:openQuotationId` al abrir el modulo.
  - Si encuentra la cotizacion, abre la ficha correspondiente.
  - Esto permite que `Cotizacion origen` en ETS lleve al usuario al documento editable cuando el estado lo permita.

Archivos modificados en esta pasada:
- `frontend/src/pages/ServiceOrdersPage.jsx`
- `frontend/src/pages/QuotationsPage.jsx`
- `frontend/src/styles/global.css`
- `docs/BACKUP_ESTADO_ACTUAL.md`

Puntos resueltos:
- #1 Selector de tecnico visual con buscador, tarjetas y paginacion.
- #2 Buscador interno dentro del ETS.
- #3 Tarjetas principales del resumen clickeables.
- #5 Hojas de Campo filtrables al abrir desde una OT.
- #6 Listado de equipos redisenado como tarjetas.
- #7 Botonera visible de equipos retirada del listado y movida al detalle.
- #8 CSS de folios/cupos disponibles redisenado en filas.
- #9 Botones rapidos de condicion inicial.
- #11 Flujo paralelo Hojas / Captura / Certificados preservado.
- #12 Cotizacion origen abre la cotizacion vinculada.

Puntos parcialmente implementados:
- #4 Soporte para varias Ordenes de Trabajo:
  - Resuelto visualmente usando ordenes relacionadas por cotizacion.
  - Requiere decision funcional si se desea una entidad padre explicita `Orden de Servicio -> varias OT` en backend.
- #10 Finalizacion real de cada etapa:
  - Se conservan los controles existentes `Marcar resumen listo`, `Marcar equipos listos` y `Reabrir`.
  - Resumen persiste mediante PATCH actual.
  - Equipos/Reabrir siguen siendo control visual porque no existe endpoint/campo formal de etapa.
- #12 Edicion completa de cotizacion desde ETS:
  - Se abre la cotizacion real en su modulo.
  - No se duplico el editor completo dentro del modal ETS para evitar bifurcar logica de Ventas.

Decisiones funcionales pendientes:
- Definir si el sistema debe crear una entidad persistente para agrupar varias OT bajo una misma Orden de Servicio.
- Definir campos/endpoints formales para cierre y reapertura auditada por etapa.
- Definir si la edicion de partidas de cotizacion debe incrustarse dentro del ETS o seguir centralizada en `Ventas / Cotizaciones`.

Validacion ejecutada:
- `npm run build` -> OK con advertencia no bloqueante de chunk mayor a 500 kB.
- `../venv/bin/python -m compileall app` -> OK.
- `../venv/bin/alembic current` -> `3c4d5e6f7a8b (head)`.
- No hubo migracion nueva; no se ejecuto `alembic upgrade head`.
- `git diff --check` -> OK.
- `rg -n "window\\.confirm|window\\.alert|window\\.prompt|alert\\(|prompt\\(" frontend/src` -> sin resultados.
- Revision especifica de ETS:
  - No queda `<select>` para tecnico.
  - No queda botonera de equipos en el listado principal.
  - Las acciones de equipo viven en el detalle.

Backup:
- Dump SQL generado con `scripts/backup-db.sh`:
  - `backups/erp_myc_2026_07_08_1151.sql`
- Tamano verificado:
  - `610K`
- Lineas verificadas:
  - `6654`
