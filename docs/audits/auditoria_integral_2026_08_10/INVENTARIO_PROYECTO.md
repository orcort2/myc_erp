# Inventario real del proyecto — 2026-08-10

## Componentes

| Capa | Componentes principales | Estado |
| --- | --- | --- |
| API | FastAPI, 47 routers incluidos, 356 operaciones | Funcional con deuda |
| Seguridad | guard global, JWT, permisos bootstrap, Portal ownership | Funcional con deuda |
| Dominio comercial | Clientes, Catálogo, Cotizaciones | Funcional con observaciones |
| Dominio operativo | ETS, OT, Equipos, Firmas, Hojas, Captura, Calidad, Certificados | Funcional con correcciones |
| Dominio financiero | Invoice, Facturama, pagos, CxC, notas administrativas | Parcial para Producción |
| Documental | Control V1, Masters, interpretaciones, PDFs/XLSX/XML/ZIP | Funcional con deuda operativa |
| Metrología | patrones, certificados, procedimientos, perfiles, selección, incertidumbre | Parcialmente integrado |
| Transversal | Actividad, notificaciones, comunicaciones, auditoría | Funcional con deuda |
| Portal | registro, invitación, membresía, roles, vistas propias | En revisión |
| Resoluciones | dominio, persistencia, Centro, worker, API/SDK, dos verticales | En revisión |
| Datos | PostgreSQL, 111 tablas ORM, 86 migraciones, head único | Casi sellado |
| Frontend | React 19/Vite, routing propio, 169 archivos src | Funcional con deuda |
| Toolkit | `scripts/myc`, DB/reset/backup/drills/SAT | Funcional local |
| Infraestructura | ejecución local, storage local, LibreOffice | No lista para Producción |

## Directorios y responsabilidades

| Ruta | Responsabilidad |
| --- | --- |
| `backend/app/routers` | HTTP; hoy mezcla endpoints delgados y lógica ETS duplicada |
| `backend/app/services` | reglas de dominio, documentos e integraciones |
| `backend/app/models` | ORM SQLAlchemy |
| `backend/app/schemas` | contratos Pydantic |
| `backend/app/security` | política API transversal |
| `backend/app/core/portal` | identidad y constantes del Portal |
| `backend/app/resolution_engine` | núcleo general del Motor |
| `backend/app/resolution_center` | consola/orquestación interna |
| `backend/app/resolution_integrations` | verticales certificados/equipo adicional |
| `backend/myc_resolution_contracts` | contratos públicos versionados |
| `backend/myc_resolution_sdk` | cliente HTTP oficial |
| `backend/migrations/versions` | cadena Alembic de 86 revisiones |
| `backend/tests` | 61 archivos de pruebas |
| `frontend/src/pages` | páginas/routing propio |
| `frontend/src/components` | UI reusable y workbenches |
| `frontend/src/portal` | SPA del cliente |
| `frontend/src/services/api.js` | cliente HTTP central (1,805 líneas) |
| `scripts/toolkit` | operación local controlada |
| `docs/project` | canon vigente |
| `docs/architecture` | contratos técnicos |
| `docs/audits` | fotografías fechadas |
| `storage` | artefactos locales fuera de Git |

## Modelos/tablas por familias

- Identidad: `users`, `roles`, `user_roles`, logs.
- Portal: cuentas, registros, solicitudes, invitaciones, memberships,
  membership roles, roles, permisos y configuración.
- Comercial: clientes/contactos/perfiles, catálogo/componentes, cotizaciones,
  partidas, snapshots y excepciones.
- Operativo: service orders/items/work orders, equipos, ciclos de firma, Hojas,
  resultados, firmas, archivos de captura y certificados/versiones.
- Documental/metrología: documentos/versiones, templates/interpretaciones,
  patrones/certificados, procedimientos, perfiles e incertidumbre.
- Fiscal: invoices/items/settings, intentos Facturama, payments, credit notes y
  SAT catalogs/versions/records/aliases/favorites.
- Transversal: activity threads/messages/revisions/mentions/attachments,
  attention/reads, notifications y communications.
- Resoluciones: 29 modelos generales más consumidores/integraciones.

## Rutas API por método y política

- GET 137, POST 163, PATCH 34, DELETE 20, PUT 2.
- 306 operaciones requieren permiso administrativo o de módulo.
- 25 aplican ownership Portal/interno.
- 6 requieren sólo autenticación.
- 19 pertenecen a allowlist/firmadas/entorno/consumidor.
- 0 sin política.

## Integraciones y motores

| Componente | Estado |
| --- | --- |
| Facturama | cliente async, timeout, sanitización, intentos/reconcile; Sandbox |
| LibreOffice | disponible 26.2.4.2; conversión síncrona |
| Correo Portal | sólo outbox en desarrollo; ausente en Producción |
| SAT | catálogos locales versionados e índices especializados |
| Google Drive | no iniciado |
| Motor Resoluciones | dos definiciones instaladas; worker/cola/API/SDK |
| Motores técnicos | selección, metrología, incertidumbre y cálculo parciales |

## Código legado y huérfano

- `NotificationCenterPage.jsx` e `InvoiceWorkbenchModal.jsx` no tienen
  importadores en `frontend/src`.
- páginas Captura/Calidad/Certificados/Equipos/Procedimientos/Incertidumbre se
  importan, pero varias no tienen entrada en `modules`; algunas funciones se
  absorben en ETS.
- `request_additional_equipment_resolution` no tiene consumidor productivo.
- compatibilidad OT/firmas/catálogos sigue conectada; no es código muerto.
- LABs existen y están protegidos por `settings.manage`; no deben confundirse
  con flujo productivo.

No se recomienda eliminar ningún candidato sin caracterización y búsqueda de
consumidores externos.

