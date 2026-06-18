# Backup de estado actual - MYC SYSTEM

Fecha: 2026-06-17
Ultima actualizacion: 2026-06-18 10:37 CST

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
M docs/BACKUP_ESTADO_ACTUAL.md
M frontend/src/pages/App.jsx
M frontend/src/services/api.js
M frontend/src/styles/global.css
```

El cambio backend pendiente es CORS para permitir tambien `http://127.0.0.1:5174` cuando Vite usa puerto alterno.
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
```

Nota: `TestClient` muestra un warning de Starlette sobre `httpx`/`httpx2`, pero no bloquea la prueba.

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

Rutas frontend implementadas:

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
- Resumen economico con subtotal, IVA y total destacado.
- Datos comerciales con emision, vigencia editable, cliente y asesor.
- Notas editables.
- Acciones de estado agrupadas.
Edicion limitada cableada contra PATCH /api/quotations/{id} para vigencia y notas.
Area futura preparada visualmente para Partidas, IVA, PDF e Historial.
Acciones visuales de estado cableadas contra endpoints existentes: send, waiting, accept, reject, expire y cancel.
Las acciones de estado piden confirmacion y se deshabilitan si la transicion no aplica.
Subpestanas internas agregadas al modulo: Cotizaciones y Productos / Servicios.
Productos / Servicios existe como catalogo visual frontend-only, sin backend todavia.
Catalogo visual muestra Nombre, Tipo, Clave SAT, Unidad SAT, Precio base, Costo interno, Estado y Acciones.
Boton Nuevo producto/servicio abre modal Liquid Glass; alta/edicion se guarda solo en memoria de la sesion.
El codigo deja comentario claro de que esta seccion se conectara al backend cuando exista el modulo de catalogo.
No se implemento PDF ni impresion.
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

La UI todavia no tiene CRUD visual completo de clientes. Ese es el siguiente modulo frontend recomendado.

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

1. Decidir si se commitea `frontend/package-lock.json`.
2. Conectar catalogo Productos / Servicios a backend cuando se defina schema y endpoints.
3. Agregar partidas reales a cotizaciones.
4. Crear modulo de calidad para revision formal de certificados.
5. Conectar frontend profundo a ordenes de servicio, equipos, hojas de campo y certificados.
6. Aplicar permisos gradualmente en endpoints sensibles usando `require_permission()`.
