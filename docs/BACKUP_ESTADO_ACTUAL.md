# Backup de estado actual - MYC SYSTEM

Fecha: 2026-06-17
Ultima actualizacion: 2026-06-19 11:50 CST

Nota: desde esta version, cada actualizacion del backup debe conservar fecha y hora para tener record de cambios.

## Ruta actual del proyecto

```text
/Users/saulcortes/Desktop/myc_erp
```

La carpeta padre antes se llamaba `ERP MYC`, pero fue renombrada a `myc_erp`. No hay problema con el cambio. De ahora en adelante todas las rutas deben apuntar a `myc_erp`.

Git ya esta inicializado.

Ultimo commit conocido:

```text
a0051a2 Add auth, roles and permissions foundation
```

Commits recientes:

```text
a0051a2 Add auth, roles and permissions foundation
e53b18d Add equipment and field sheets modules
4546e2c Add service orders and equipment modules
66f8b58 ERP MYC - Base MVP clients and quotations
```

Estado Git verificado:

```text
M backend/app/main.py
M backend/app/schemas/audit_log.py
M backend/app/services/audit_logs.py
M docs/BACKUP_ESTADO_ACTUAL.md
M frontend/src/pages/App.jsx
M frontend/src/services/api.js
M frontend/src/styles/global.css
?? backend/app/routers/audit_logs.py
```

`frontend/assets/` contiene el logo original disponible localmente. La copia optimizada usada por Vite vive en `frontend/src/assets/myc-logo.png`.

## Objetivo del sistema

Construir un ERP para MYC orientado al flujo real de calidad y operacion:

```text
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
```

La entidad raiz operativa debe ser:

```text
service_orders
```

Todo el sistema debe girar alrededor de la orden de servicio y su expediente operativo, tecnico, documental y financiero.

## Stack decidido

Backend:

```text
FastAPI
SQLAlchemy
Alembic
PostgreSQL
Pydantic Settings
```

Frontend:

```text
React
Vite
Lucide React
History API para rutas simples sin react-router
```

Archivos:

```text
storage/cotizaciones
storage/certificados
storage/evidencias
storage/facturas
storage/temporales
```

## Entorno virtual

Ya existe entorno virtual en la raiz:

```text
venv/
```

No esta dentro de `backend/.venv`.

Para usarlo:

```bash
cd /Users/saulcortes/Desktop/myc_erp
source venv/bin/activate
```

Cuando se active correctamente, la terminal debe mostrar algo parecido a:

```text
(venv) saulcortes@MacBook-Air-de-Saul myc_erp %
```

Si no aparece `(venv)` o los comandos usan el Python del sistema de macOS, significa que el entorno virtual no esta activo.

O directamente:

```bash
venv/bin/python
venv/bin/pip
venv/bin/uvicorn
```

## Dependencias backend verificadas

Ya estan instaladas en `venv/`:

```text
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
```

## Dependencias frontend

Ya existe `frontend/node_modules/`, por lo que `npm install` ya fue ejecutado localmente.

Existe `frontend/package-lock.json`, pero esta pendiente de commit.

Para reinstalar o actualizar dependencias:

```bash
cd frontend
npm install
```


## Estructura principal actual

```text
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
      clients.py
      quotations.py
      service_orders.py
      equipment.py
      field_sheets.py
      certificates.py
      catalog_items.py
      document_templates.py
      quotation_pdfs.py
      audit_logs.py
    templates/
      quotation_pdf.html
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
    main.jsx
    pages/App.jsx
    components/ModuleCard.jsx
    services/api.js
    styles/global.css

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
```

## Backend actual

Archivo principal:

```text
backend/app/main.py
```

Routers incluidos:

```text
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
```

Rutas base:

```text
GET /
GET /api/health
GET /api/audit-logs
GET /api/modules
```

Auth:

```text
POST /api/auth/register
POST /api/auth/login
POST /api/auth/refresh
GET /api/auth/me
```

Usuarios / Configuración:

```text
GET /api/users
GET /api/users/roles
PATCH /api/users/{user_id}/roles
PATCH /api/users/{user_id}/status
```

Clientes:

```text
GET /api/clients
POST /api/clients
GET /api/clients/{client_id}
PATCH /api/clients/{client_id}
DELETE /api/clients/{client_id}
```

Cotizaciones:

```text
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
```

Ordenes de servicio:

```text
GET /api/service-orders
POST /api/service-orders
GET /api/service-orders/{service_order_id}
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
```

Equipos:

```text
GET /api/equipment
POST /api/equipment
GET /api/equipment/{equipment_id}
PATCH /api/equipment/{equipment_id}
POST /api/equipment/{equipment_id}/realizing
POST /api/equipment/{equipment_id}/calibrated
POST /api/equipment/{equipment_id}/labeled
POST /api/equipment/{equipment_id}/not-done
DELETE /api/equipment/{equipment_id}
```

Hojas de campo:

```text
GET /api/field-sheets
POST /api/field-sheets
GET /api/field-sheets/{field_sheet_id}
PATCH /api/field-sheets/{field_sheet_id}
POST /api/field-sheets/{field_sheet_id}/complete
POST /api/field-sheets/{field_sheet_id}/review
DELETE /api/field-sheets/{field_sheet_id}
```

Certificados:

```text
GET /api/certificates
POST /api/certificates
GET /api/certificates/{certificate_id}
PATCH /api/certificates/{certificate_id}
POST /api/certificates/{certificate_id}/generate
POST /api/certificates/{certificate_id}/quality
POST /api/certificates/{certificate_id}/approve
POST /api/certificates/{certificate_id}/release
POST /api/certificates/{certificate_id}/suspend
DELETE /api/certificates/{certificate_id}
```

Catalogo MYC:

```text
GET /api/catalog-items
POST /api/catalog-items
GET /api/catalog-items/{catalog_item_id}
PATCH /api/catalog-items/{catalog_item_id}
DELETE /api/catalog-items/{catalog_item_id}
```

Plantillas documentales:

```text
GET /api/document-templates/quotation
PATCH /api/document-templates/quotation
POST /api/document-templates/quotation/restore-defaults
```

Audit logs:

```text
GET /api/audit-logs
```

Los `DELETE` actuales hacen borrado logico, no borrado fisico.

## Modulos MVP 1 definidos

```text
auth
users
clients
quotations
service_orders
equipment
audit_logs
```

Modulos funcionales construidos hasta ahora:

```text
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
document_templates
```

## Tablas iniciales modeladas

```text
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
```

## Auth y Roles

El modulo backend ya existe con schema, service y router.

Archivos principales:

```text
backend/app/models/user.py
backend/app/schemas/auth.py
backend/app/services/auth.py
backend/app/routers/auth.py
backend/app/core/security.py
```

Tablas:

```text
users
roles
user_roles
```

Roles iniciales sembrados por migracion:

```text
Administrador
Comercial
Tecnico
Captura
Calidad
Finanzas
Cliente
```

Tokens:

```text
access_token JWT
refresh_token JWT
token_type bearer
```

Hash de password:

```text
pbkdf2_sha256 via passlib
```

Nota tecnica: se evito `bcrypt` porque la combinacion instalada `passlib` + `bcrypt 5` falla en este entorno.

Permisos iniciales definidos en codigo:

```text
Administrador -> *
Comercial -> clients.*, quotations.*, service_orders.*
Tecnico -> equipment.*, field_sheets.*
Captura -> certificates.create, certificates.generate, field_sheets.read
Calidad -> certificates.quality, certificates.approve, field_sheets.read
Finanzas -> payments.*, invoices.*, release.*
Cliente -> portal.read
```

Ya existen helpers:

```text
get_current_user()
require_permission(permission)
user_has_permission(user, permission)
```

Los endpoints operativos todavia no estan protegidos masivamente para no romper el flujo de desarrollo. La proteccion por permisos se debe aplicar gradualmente al construir Quality y al endurecer acciones sensibles.

## Cotizaciones

La cotizacion tiene:

```text
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
```

El folio de cotizacion se genera con formato:

```text
MYC-MM-AA-0001
```

Impuestos de cotizacion:

```text
Las partidas usan tax_rate por linea.
tax_object soportado: iva_16, iva_0, exempt, not_subject.
El total suma subtotal, impuesto y total por partida.
```

Estados permitidos:

```text
draft
sent
waiting
accepted
rejected
expired
cancelled
```

Transiciones permitidas:

```text
draft -> sent, cancelled
sent -> waiting, accepted, rejected, expired, cancelled
waiting -> accepted, rejected, expired, cancelled
accepted/rejected/expired/cancelled -> estados terminales, sin edicion
```

Cada alta, edicion, cambio de estado y baja logica escribe auditoria.

PDF de cotizacion implementado:

```text
Endpoint: GET /api/quotations/{quotation_id}/pdf
Servicio: backend/app/services/quotation_pdfs.py
Plantilla: backend/app/templates/quotation_pdf.html
Motor: WeasyPrint
Respuesta: application/pdf
Content-Disposition: inline; filename="Cotizacion_<folio>_<nombre_cliente>.pdf"
```

El PDF usa identidad comercial de Metrologia y Servicios MYC, logo, folio, fecha de emision, vigencia, vendedor, datos de cliente, datos fiscales, partidas, leyenda por partida, subtotal, impuestos, total, total con letra, condiciones comerciales, notas y firma/autorizacion.

Control documental de plantilla:

```text
Codigo documental: FCA-23-2
Revision: opcional, configurable desde document_templates
Emision documental: 2025-03-28
```

Estas variables ahora viven en `document_templates` y se editan desde la pestaña Plantilla cotizacion.

Ubicacion visual actual: el bloque documental se imprime pegado al extremo derecho utilizable del bloque de titulo, a la misma altura visual de COTIZACION, con padding compacto y texto alineado a la derecha para evitar sensacion de tarjeta flotante. Se retiro del pie de pagina para conservar el diseno actual del PDF y dejar el footer limpio.

El nombre de archivo se sanitiza sin acentos, con espacios reemplazados por guiones y sin caracteres invalidos.

Si la cotizacion no tiene partidas, el PDF se genera con tabla vacia y mensaje "Sin partidas registradas".

Editor de plantilla PDF implementado:

```text
Modelo: backend/app/models/document_template.py
Tabla: document_templates
Schemas: backend/app/schemas/document_template.py
Service: backend/app/services/document_templates.py
Router: backend/app/routers/document_templates.py
Migracion: backend/migrations/versions/c3d4e5f6a7b8_add_document_templates.py
template_key de cotizacion: quotation
```

Campos editables:

```text
Identidad: nombre comercial, lema, RFC, correo, sitio web, direccion, telefono
Documento: titulo, subtitulo, codigo documental, revision, fecha de emision documental
Terminos: version, condiciones comerciales, metrologicas, legales, aviso de privacidad y texto de aceptacion
Opciones: mostrar resumen, mostrar terminos completos en pagina adicional, mostrar firma de aceptacion
```

Si no existe registro `quotation`, el backend crea uno default con los valores actuales.

El PDF ahora lee `document_templates` y ya no depende de textos fijos en HTML para identidad, control documental ni terminos.

## Ordenes de servicio

El modulo backend ya existe con schema, service y router.

Archivos principales:

```text
backend/app/models/service_order.py
backend/app/schemas/service_order.py
backend/app/services/service_orders.py
backend/app/routers/service_orders.py
```

Campos principales:

```text
folio
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
```

Estados definidos:

```text
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
```

Al crear una orden desde `quotation_id`, se valida que la cotizacion pertenezca al cliente y se copian sus partidas activas a `service_order_items`.

## Equipos

El modulo backend ya existe con schema, service y router.

Archivos principales:

```text
backend/app/models/equipment.py
backend/app/schemas/equipment.py
backend/app/services/equipment.py
backend/app/routers/equipment.py
```

Regla principal:

```text
Todo equipo debe pertenecer a una service_order activa.
```

Campos principales:

```text
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
```

Estados definidos:

```text
registered
realizing
calibrated
labeled
not_done
cancelled
```

Transiciones principales:

```text
registered -> realizing, not_done, cancelled
realizing -> calibrated, not_done, cancelled
calibrated -> labeled, not_done, cancelled
labeled/not_done/cancelled -> estados terminales
```

Cada alta, edicion, cambio de estado y baja logica escribe auditoria.

El modulo sincroniza contadores de la orden:

```text
service_orders.total_equipment
service_orders.completed_equipment
```

Para `completed_equipment` cuentan equipos activos con estado:

```text
calibrated
labeled
not_done
```

## Hojas de Campo

El modulo backend ya existe con modelo, schema, service y router.

Archivos principales:

```text
backend/app/models/field_sheet.py
backend/app/schemas/field_sheet.py
backend/app/services/field_sheets.py
backend/app/routers/field_sheets.py
```

Reglas principales:

```text
Una hoja de campo pertenece a un equipo.
Un equipo solo puede tener una hoja de campo activa.
No se manejan fotos ni archivos en esta primera version.
```

Campos tecnicos principales:

```text
equipment_id
status
initial_condition
final_condition
pattern_used
results
observations
evidence_notes
method
environmental_conditions
technician_notes
```

Estados definidos:

```text
draft
in_progress
completed
under_review
approved
rejected
cancelled
```

Regla para completar:

```text
No se puede completar si falta:
- initial_condition
- final_condition
- pattern_used
- results
- observations o evidence_notes
```

Al completar:

```text
field_sheets.status -> completed
equipment.status -> calibrated
service_orders.completed_equipment se recalcula
audit_log registra el cambio
certificate_ready queda registrado en auditoria como preparacion para certificado futuro
```

## Certificados

El modulo backend ya existe con modelo, schema, service y router.

Archivos principales:

```text
backend/app/models/certificate.py
backend/app/schemas/certificate.py
backend/app/services/certificates.py
backend/app/routers/certificates.py
```

Relacion principal:

```text
Service Order
  -> Equipment
  -> Field Sheet
  -> Certificate
```

Un certificado pertenece a:

```text
service_order_id
equipment_id
field_sheet_id
```

Campos principales:

```text
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
```

Tipos de certificado:

```text
acreditado -> folio MYCA-MM-AAAA-XXXX
trazable -> folio MYCT-MM-AAAA-XXXX
```

Estados definidos:

```text
draft
generated
quality_review
approved
released
cancelled
suspended
```

Reglas principales:

```text
La orden de servicio debe estar activa.
El equipo debe pertenecer a la orden indicada.
El equipo debe estar calibrated o labeled.
La hoja de campo debe pertenecer al equipo indicado.
La hoja de campo debe estar completed, under_review o approved.
Una hoja de campo solo puede tener un certificado activo.
```

## Regla arquitectonica principal

Nada critico se borra realmente.

Las entidades operativas usan:

```text
is_active
deleted_at
deleted_by
```

## Migraciones Alembic

Migraciones actuales:

```text
c0fa71033b73_create_mvp_schema.py
917baf3a5378_add_quotation_advisor.py
5d6e7f8a9b10_expand_service_orders.py
6f7a8b9c0d11_update_equipment_status.py
7a8b9c0d1e12_create_field_sheets.py
8b9c0d1e2f13_create_certificates.py
9c0d1e2f3a14_add_user_roles.py
```

La segunda migracion agrega:

```text
quotations.advisor_id
indice ix_quotations_advisor_id
foreign key hacia users.id
```

La tercera migracion amplia ordenes de servicio:

```text
advisor_id
technician_id
scheduled_date -> agenda_date
service_date
total_equipment
completed_equipment
requires_payment
foreign keys hacia users.id
```

La cuarta migracion actualiza estados iniciales de equipos:

```text
equipment.status: pending -> registered
```

La quinta migracion crea hojas de campo:

```text
field_sheets
foreign key hacia equipment.id
indice unico parcial uq_field_sheets_active_equipment para impedir mas de una hoja activa por equipo
```

La sexta migracion crea certificados:

```text
certificates
foreign keys hacia service_orders.id, equipment.id y field_sheets.id
indice unico parcial uq_certificates_active_field_sheet para impedir mas de un certificado activo por hoja de campo
folio unico
```

La septima migracion agrega roles funcionales:

```text
user_roles
roles iniciales
migracion de users.role_id hacia user_roles cuando exista role_id
```

Estado de PostgreSQL local verificado:

```text
alembic current -> c3d4e5f6a7b8 (head)
```

## Verificacion backend

Verificaciones ejecutadas correctamente:

```text
../venv/bin/python -m compileall app
../venv/bin/alembic heads
../venv/bin/alembic upgrade head --sql
../venv/bin/alembic upgrade head
../venv/bin/alembic current
npm run build
```

Prueba con `fastapi.testclient.TestClient` contra la base local:

```text
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
```

Nota: `TestClient` muestra un warning de Starlette sobre `httpx`/`httpx2`, pero no bloquea la prueba.

Nota PDF: `pdftoppm`/`pdfinfo` no estan instalados en esta Mac, por lo que no se hizo render PNG con Poppler desde Codex.

Prueba visual en navegador local:

```text
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
```

## Frontend actual

Pantalla inicial en:

```text
frontend/src/pages/App.jsx
```

Refactor frontend principal completado:

```text
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
```

## Actualizacion refactor frontend - 2026-06-19

El refactor principal de frontend ya compila correctamente.

Verificacion:
- `npm run build` correcto.
- Dashboard levanta sin pantalla blanca.
- Clientes levanta sin pantalla blanca.
- Cotizaciones levanta sin pantalla blanca.
- Ordenes de servicio levanta sin pantalla blanca.
- Certificados levanta sin pantalla blanca.
- Calidad levanta sin pantalla blanca.
- EquipmentPage y FieldSheetsPage existen como paginas separadas, pero por ahora conservan placeholder visual mediante ModulePage.

Correcciones manuales realizadas:
- Se agregaron imports faltantes de React en paginas/componentes extraidos.
- Se corrigieron hooks faltantes como `useMemo`, `useEffect` y `useState`.
- Se corrigieron imports faltantes como `ModulePage`, `ShieldCheck` y `mycLogo` donde aplicaba.
- `App.jsx` queda como orquestador minimo de sesion, rutas hash, layout y render de paginas.
- Ya no hay pantallas blancas por errores de React runtime.

```text
/login
/dashboard
```

Fase 1 implementada:

```text
Login real contra POST /api/auth/login
Registro inicial contra POST /api/auth/register
Guardado de access_token y refresh_token en localStorage
Obtencion de usuario con GET /api/auth/me
Logout
Proteccion de /dashboard
Sidebar
Topbar
Layout principal
```

Fase 2 inicial implementada:

```text
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
```

Modulo Clientes frontend iniciado:

```text
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
```

Modulo Cotizaciones frontend iniciado:

```text
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
```

Modulo Ordenes de Servicio frontend iniciado:

```text
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
Edicion de orden conectada contra PATCH /api/service-orders/{service_order_id} para agenda_date, service_date, technician_id, requires_payment y notes.
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
- Informacion muestra orden, cliente, equipo, marca, modelo, serie y estado actual.
- Datos tecnicos conecta initial_condition, final_condition, pattern_used, results, observations, evidence_notes, method, environmental_conditions y technician_notes.
- Guardar usa PATCH /api/field-sheets/{field_sheet_id}.
- Completar valida en frontend condicion inicial/final, patron, resultados y observaciones o evidencia antes de llamar POST /api/field-sheets/{field_sheet_id}/complete.
- Enviar a revision usa POST /api/field-sheets/{field_sheet_id}/review.
- Al completar, backend cambia equipo a calibrated y recalcula contadores de orden.
- Si la hoja esta completed, under_review o approved y el equipo esta calibrated o labeled, permite Crear certificado.
- Crear certificado desde Hoja de Campo pide tipo acreditado/trazable con selector y llama POST /api/certificates.
- Si ya existe certificado activo para la hoja, bloquea el boton y muestra Certificado creado.
Pestana Historial muestra creacion, ultima actualizacion, estado actual y cotizacion origen; audit_log queda preparado para conectar despues.
```

Modulo Certificados frontend implementado:

```text
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
- Suspender -> POST /api/certificates/{id}/suspend
Cada accion pide confirmacion, muestra loading, propaga errores claros y refresca certificado/listados.
Badges visuales implementados para draft, generated, quality_review, approved, released, cancelled y suspended.
Folios se muestran con jerarquia visual:
- acreditado: MYCA-MM-AAAA-XXXX
- trazable: MYCT-MM-AAAA-XXXX
Historial muestra creacion, ultima actualizacion, estado actual, orden de servicio origen, equipo origen y hoja de campo origen.
Dashboard actualiza contadores reales:
- Total certificados
- Certificados en revision
- Certificados liberados
No se construyo PDF de certificado, firma digital, facturacion, finanzas ni CRM.
```

Modulo Calidad frontend implementado:

```text
/dashboard#calidad abre vista transversal para supervision de certificados.
Consume GET /api/certificates, GET /api/service-orders, GET /api/equipment, GET /api/field-sheets, GET /api/clients y GET /api/audit-logs.
Vista principal separada en pestanas:
- Pendientes
- En revision
- Aprobados
- Liberados
- Suspendidos
Pendientes muestra certificados en estados generated y quality_review.
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
- Solicitar correccion -> POST /api/certificates/{id}/suspend con comentario de correccion
- Suspender -> POST /api/certificates/{id}/suspend
- Liberar -> POST /api/certificates/{id}/release
Nota tecnica: Solicitar correccion hoy reutiliza la transicion suspend porque el backend todavia no tiene un estado separado para correccion solicitada.
Dashboard actualiza contadores:
- Certificados pendientes calidad
- Certificados aprobados
- Certificados liberados
```

Modulo backend Audit Logs expuesto:

```text
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
```

Modulo backend Catalogo MYC agregado:

```text
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

Se inició el módulo Configuración en `/dashboard#configuracion`.

Backend agregado:
- `backend/app/schemas/user.py`
- `backend/app/services/users.py`
- `backend/app/routers/users.py`
- Router registrado en `backend/app/main.py`.

Endpoints disponibles:
- `GET /api/users`
- `GET /api/users/roles`
- `PATCH /api/users/{user_id}/roles`
- `PATCH /api/users/{user_id}/status`

Frontend agregado:
- `frontend/src/pages/SettingsPage.jsx`
- Funciones nuevas en `frontend/src/services/api.js`:
  - `listUsers()`
  - `listRoles()`
  - `updateUserRoles(userId, roleNames)`
  - `updateUserStatus(userId, isActive)`

Estado funcional:
- Configuración ya aparece en el dashboard.
- Solo usuarios con permiso suficiente pueden acceder.
- Administrador puede ver usuarios.
- Administrador puede cambiar rol desde selector.
- Administrador puede activar/desactivar usuarios.
- Se agregó CSS visual para tabla, select de rol, badges de estado y botones de acción.
- Se validó visualmente en navegador local sin pantalla blanca.

Pendiente inmediato:
- Evitar que se desactive o cambie de rol al último Administrador activo.
- Registrar en audit_logs los cambios de rol y estado de usuarios.
- Activar botón Nuevo usuario con modal.
- Crear vista de Auditoría dentro de Configuración.
- Después mover permisos hardcodeados a base de datos.

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
```

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
Finanzas
Configuracion
```

Estado visual por modulo:

```text
Activo
Pendiente
En desarrollo
```

Variables visuales principales definidas en `frontend/src/styles/global.css`:

```text
--myc-primary
--myc-primary-dark
--myc-accent
--myc-bg
--glass-bg
--glass-border
```

La UI ya tiene CRUD visual inicial de Clientes y modulo Ventas/Cotizaciones con Catalogo MYC conectado al backend.

## Comandos de arranque

Backend:

```bash
cd /Users/saulcortes/Desktop/myc_erp
venv/bin/uvicorn backend.app.main:app --reload
```

Forma recomendada cuando se quiere activar el entorno y trabajar desde `backend/`:

```bash
cd /Users/saulcortes/Desktop/myc_erp
source venv/bin/activate
cd backend
uvicorn app.main:app --reload
```

Si se ejecuta desde `backend/` sin activar el entorno, usar el binario del venv de forma explicita:

```bash
cd /Users/saulcortes/Desktop/myc_erp/backend
../venv/bin/uvicorn app.main:app --reload
```

Frontend:

```bash
cd /Users/saulcortes/Desktop/myc_erp/frontend
npm install
npm run dev
```

## Pendientes inmediatos recomendados

1. Hacer commit del estado actual estable.
2. Blindar último Administrador activo.
3. Registrar auditoría para cambios de usuarios/roles.
4. Activar modal Nuevo usuario en Configuración.
5. Crear pestaña Auditoría dentro de Configuración.
6. Separar en backend/frontend la acción Solicitar corrección de Suspender.
7. Definir PDF real de certificado y plantilla documental de certificados.
8. Aplicar permisos gradualmente en endpoints sensibles usando `require_permission()`.
