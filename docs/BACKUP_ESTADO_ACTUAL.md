Backup de estado actual - MYC SYSTEM
Fecha: 2026-06-17
Ultima actualizacion: 2026-06-26 17:05:51 CST
Nota: desde esta version, cada actualizacion del backup debe conservar fecha y hora para tener record de cambios.
Ruta actual del proyecto
/Users/saulcortes/Desktop/myc_erp
La carpeta padre antes se llamaba ERP MYC, pero fue renombrada a myc_erp. No hay problema con el cambio. De ahora en adelante todas las rutas deben apuntar a myc_erp.
Git ya esta inicializado.
Ultimo commit conocido:
0223813 se agrego la configuración de adutoria, colocando el front
Commits recientes:
0223813 se agrego la configuración de adutoria, colocando el front
98f971d se agregaron archivos de ayuda, se mejoran botones, se pule css de algunas pestañas
f444882 Complete users management module
d64d834 se instala un pequeño modulo de configuración para la gestion de usuarios
de884e0 se separaon archivos del app principal, cada pestaña vive independiente
Estado Git verificado:
M backend/app/core/permissions.py
M backend/app/main.py
M backend/app/models/__init__.py
M backend/app/models/reference_standard.py
M backend/app/schemas/reference_standard.py
M backend/app/services/field_sheets.py
M backend/app/services/reference_standards.py
M docs/BACKUP_ESTADO_ACTUAL.md
M frontend/src/constants/navigation.js
M frontend/src/pages/App.jsx
M frontend/src/pages/ServiceOrdersPage.jsx
M frontend/src/pages/StandardsPage.jsx
M frontend/src/services/api.js
M frontend/src/styles/global.css
?? backend/app/models/controlled_document.py
?? backend/app/models/reference_standard_certificate.py
?? backend/app/routers/document_interpretations.py
?? backend/app/routers/documents.py
?? backend/app/routers/operational_engines.py
?? backend/app/routers/pattern_selection.py
?? backend/app/routers/reference_standard_certificates.py
?? backend/app/routers/technical_profiles.py
?? backend/app/schemas/controlled_document.py
?? backend/app/schemas/operational_engine.py
?? backend/app/schemas/pattern_selection.py
?? backend/app/schemas/reference_standard_certificate.py
?? backend/app/services/calculation_engine.py
?? backend/app/services/certificate_preparation_engine.py
?? backend/app/services/controlled_documents.py
?? backend/app/services/document_interpretations.py
?? backend/app/services/document_selection_engine.py
?? backend/app/services/folio_engine.py
?? backend/app/services/label_engine.py
?? backend/app/services/operational_flow.py
?? backend/app/services/pattern_selection_engine.py
?? backend/app/services/reference_standard_certificates.py
?? backend/app/services/standards_validation_engine.py
?? backend/app/services/technical_capture_engine.py
?? backend/app/services/technical_profiles.py
?? backend/migrations/versions/a2b3c4d5e6f7_add_reference_standard_certificates.py
?? backend/migrations/versions/f1a2b3c4d5e6_add_documental_core.py
?? frontend/src/pages/DocumentLibraryPage.jsx
frontend/assets/ contiene el logo original disponible localmente. La copia optimizada usada por Vite vive en frontend/src/assets/myc-logo.png.

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
