# Backup de estado actual - ERP MYC

Fecha: 2026-06-17
Ultima actualizacion: 2026-06-17 14:05:41 CST

## Ruta actual del proyecto

```text
/Users/saulcortes/Desktop/myc_erp
```

La carpeta padre antes se llamaba `ERP MYC`, pero fue renombrada a `myc_erp`. No hay problema con el cambio. De ahora en adelante todas las rutas deben apuntar a `myc_erp`.

Git ya esta inicializado.

Ultimo commit conocido:

```text
66f8b58 ERP MYC - Base MVP clients and quotations
```

Nota importante: despues de ese commit existen cambios backend pendientes de commit para `auth`, `service_orders`, `equipment`, `field_sheets`, `certificates`, migraciones y este backup.

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
source venv/bin/activate
```

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
```

## Dependencias frontend

Pendiente:

```bash
cd frontend
npm install
```

No existe verificacion de `frontend/node_modules` como instalado.

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
    services/
      auth.py
      modules.py
      clients.py
      quotations.py
      service_orders.py
      equipment.py
      field_sheets.py
      certificates.py
      audit_logs.py
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

frontend/
  index.html
  package.json
  src/
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
modules
clients
quotations
service_orders
equipment
field_sheets
certificates
```

Rutas base:

```text
GET /
GET /api/health
GET /api/modules
```

Auth:

```text
POST /api/auth/register
POST /api/auth/login
POST /api/auth/refresh
GET /api/auth/me
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
PATCH /api/quotations/{quotation_id}
POST /api/quotations/{quotation_id}/items
PATCH /api/quotations/{quotation_id}/items/{item_id}
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

IVA configurado en codigo:

```text
16%
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
alembic current -> 9c0d1e2f3a14 (head)
```

## Verificacion backend

Verificaciones ejecutadas correctamente:

```text
../venv/bin/python -m compileall app
../venv/bin/alembic heads
../venv/bin/alembic upgrade head --sql
../venv/bin/alembic upgrade head
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
```

Nota: `TestClient` muestra un warning de Starlette sobre `httpx`/`httpx2`, pero no bloquea la prueba.

## Frontend actual

Pantalla inicial en:

```text
frontend/src/pages/App.jsx
```

Renderiza un shell con sidebar, flujo principal y tarjetas de modulos:

```text
CRM y Leads
Cotizaciones
Agenda
Llamados
Ordenes de servicio
Calidad
Certificados
Finanzas
```

La UI todavia es una base visual. No hay formularios completos conectados para auth, clientes, cotizaciones, ordenes, equipos, hojas de campo o certificados.

## Comandos de arranque

Backend:

```bash
cd /Users/saulcortes/Desktop/myc_erp
venv/bin/uvicorn backend.app.main:app --reload
```

Si se ejecuta desde `backend/`, usar:

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

1. Hacer commit de los cambios backend pendientes.
2. Instalar dependencias frontend con `npm install`.
3. Crear modulo de calidad para revision formal de certificados.
4. Conectar frontend a los endpoints de clientes, cotizaciones, ordenes de servicio, equipos, hojas de campo y certificados.
5. Aplicar permisos gradualmente en endpoints sensibles usando `require_permission()`.
