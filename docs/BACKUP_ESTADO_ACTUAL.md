# Backup de estado actual - ERP MYC

Fecha: 2026-06-17

## Ruta actual del proyecto

```text
/Users/saulcortes/Desktop/myc_erp
```

La carpeta padre antes se llamaba `ERP MYC`, pero fue renombrada a `myc_erp`. No hay problema con el cambio. De ahora en adelante todas las rutas deben apuntar a `myc_erp`.

Nota importante: esta carpeta no tiene repositorio Git activo en este momento. El comando `git status` responde `fatal: not a git repository`.

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
      audit_log.py
    schemas/
      module.py
      client.py
      quotation.py
      audit_log.py
    routers/
      health.py
      modules.py
      clients.py
      quotations.py
    services/
      modules.py
      clients.py
      quotations.py
      audit_logs.py
    utils/
  migrations/
    env.py
    script.py.mako
    versions/
      c0fa71033b73_create_mvp_schema.py
      917baf3a5378_add_quotation_advisor.py

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
modules
clients
quotations
```

Rutas base:

```text
GET /
GET /api/health
GET /api/modules
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
clients
quotations
```

## Tablas iniciales modeladas

```text
users
roles
clients
client_contacts
quotations
quotation_items
service_orders
service_order_items
equipment
audit_logs
```

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

El modelo existe, pero todavia no hay router funcional de ordenes de servicio.

Modelo principal:

```text
service_orders
service_order_items
```

Campos principales:

```text
folio
client_id
quotation_id
status
scheduled_date
closed_at
notes
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
```

La segunda migracion agrega:

```text
quotations.advisor_id
indice ix_quotations_advisor_id
foreign key hacia users.id
```

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

La UI todavia es una base visual. No hay formularios completos conectados para clientes, cotizaciones u ordenes.

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

1. Inicializar Git o confirmar si este proyecto se debe copiar dentro de otro repo existente.
2. Instalar dependencias frontend con `npm install`.
3. Verificar migraciones contra PostgreSQL real.
4. Crear router/servicio/schemas de `service_orders`.
5. Conectar frontend a los endpoints de clientes y cotizaciones.
6. Agregar autenticacion, usuarios y permisos reales.
