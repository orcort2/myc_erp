# Matriz integral de cobertura por módulo

Estados permitidos: `SELLADO`, `CASI SELLADO`, `EN DESARROLLO`, `PENDIENTE`, `NO INICIADO`. Ningún estado deriva sólo de existencia de archivos o pruebas.

| Módulo/capacidad | Estado | Flujo y evidencia principal | Validaciones/permisos/estados comprobados | Pendiente real y riesgo |
| --- | --- | --- | --- | --- |
| Autenticación/sesiones | EN DESARROLLO | `routers/auth.py` → `services/auth.py` → `models/user.py`; access/refresh tipados | Hash PBKDF2; usuario inactivo rechazado; refresh no sirve como access | Secreto por defecto, registro público permanente, sin revocación/rotación/reset/MFA; tokens en localStorage |
| Usuarios/roles | EN DESARROLLO | Ajustes → `/users` → `services/users.py` → `users/roles/user_roles` | Último administrador protegido; permisos estáticos por rol | No CRUD de roles/permisos; navegación no filtrada; cobertura 401/403 mínima |
| Dashboard | EN DESARROLLO | `DashboardHome.jsx`, agregados calculados por múltiples listados | Carga datos reales y abre cartera/workbench | No autorización visual; consultas completas; sin E2E ni contrato agregador dedicado |
| CRM/Leads | NO INICIADO | No se localizó modelo, router, pantalla ni prueba | NO VERIFICADO por ausencia | Implementar o retirar del flujo 1.0 |
| Clientes/contactos | EN DESARROLLO | `ClientsPage.jsx` → `/clients` → `clients.py` → `clients/client_contacts/profiles` | Parser/importación/exportación, baja/archivo/restauración y auditoría | CRUD/import/export/constancia/perfiles públicos; datos personales expuestos; contactos sin módulo autónomo |
| Catálogo MYC | EN DESARROLLO | Editor dentro de Cotizaciones → `catalog_items`/`catalog_item_components` | Servicios simples/compuestos, linked companies, baja lógica | CRUD público; sin experiencia independiente; hardcodes/duplicación visual |
| Cotizaciones | EN DESARROLLO | `QuotationsPage.jsx` → router/schema/service → quotation/items/snapshots | Máquina de estados, cálculos, PDF, snapshots, desbloqueo EXV y expansión compuesta | Mutaciones aceptan sesión opcional; snapshot restore no restaura partidas; E2E hasta ETS ausente |
| Agenda | PENDIENTE | `service_orders.agenda_date` y UI en ETS | Fecha requerida con servicio/técnico para readiness | Sin entidad, calendario, folio AMYC, reprogramación, recordatorios ni auditoría propia |
| Llamados | PENDIENTE | transición ETS `confirmed → called` | Estado y botón existen | Sin entidad/folio SMYC/resultado/bitácora autónoma |
| ETS/Servicios | EN DESARROLLO | `ServiceOrdersPage.jsx` → router de 760 líneas → servicio → `service_orders/items` | Estados, snapshots, cotización, actividad y auditoría parcial | CRUD/transiciones públicos; lógica duplicada router/servicio; excepciones legacy; página monolítica |
| Órdenes de trabajo | EN DESARROLLO | ETS → `service_work_orders`; PDF individual/lote | Máximo 10 equipos, secuencias y asociación de firmas | Modelo legacy coexistente; downgrade roto en firmas; E2E multi-OT ausente |
| Equipos | EN DESARROLLO | ETS → `/equipment` → snapshot de servicio/Master → `equipment` | Alcance automático, estados y certificado esperado | Router público; alta directa paralela al vertical del Motor; identidad de activo no existe |
| Firmas | EN DESARROLLO | ciclos y relación `service_order_signature_cycle_work_orders` | Firma por ciclos/OT y reapertura con permiso | Endpoint `confirm-signatures` con sesión opcional; legado directo coexistente; downgrade roto |
| Hojas de Campo | EN DESARROLLO | ETS → field-sheets → plantilla/snapshot/resultados/firmas → PDF | Campos requeridos, complete/review, patrón y auditoría | Semánticas y cálculo metrológico incompletos; 23 plantillas sin E2E; renderer PDF distinto de React |
| Captura | EN DESARROLLO | paquete ZIP/XLSX → retorno → fingerprint/readiness → Calidad | Identificación, warnings/mismatch, actividad y auditoría | Carga sin límite/descompresión segura; bandeja no identificados parcial; acciones duplicadas en ETS |
| Calidad | EN DESARROLLO | lista/modal y pestaña ETS → aprobar/regresar/autenticar | Readiness Master, navegación OT→ETS→lista y secuencia no circular | Autenticación duplicada en ETS; página autónoma sin navegación; sin E2E visual |
| Certificados | EN DESARROLLO | expected → captura → quality → auth PDF → release | Estados, PDF versionado, código público, pago como compuerta | Router protegido pero portal público global; E2E de verificación ausente; acción duplicada |
| Facturación CFDI | EN DESARROLLO | Billing/ETS → controller único → Invoice → Facturama/PDF/XML | Borrador persistible, snapshots fiscales, intentos, conciliación, PDF MYC, XML/PDF PAC | Sólo Sandbox; sin cancelación/sustitución/PPD/complemento/nota fiscal; sin autosave ni E2E |
| Pagos | EN DESARROLLO | Workbench → `invoice_payments` → saldo/estado/recibo | Parciales/totales, no exceder saldo, prepago conservado al timbrar | Sin reversos/conciliación bancaria/complemento; pruebas de permiso limitadas |
| Cuentas por cobrar | EN DESARROLLO | Dashboard/Billing → `/accounts-receivable` | Saldo cero retira cartera | Sin aging robusto, exportación, alertas, E2E y paginación |
| Notas de crédito | EN DESARROLLO | endpoint/modelo `CreditNote`; relación en Invoice | Alta interna y estados draft/applied/cancelled | UI especializada y CFDI de egreso ausentes; no sustituye nota fiscal |
| Control Documental V1 | SELLADO | `DocumentLibraryPage` → documentos/versiones → storage | Lista maestra, versiones, activación, archivo, permisos explícitos | Sellado sólo para V1 congelado; seguridad transversal y storage siguen bloqueando producción |
| Plantillas Maestras | EN DESARROLLO | documento controlado → snapshot equipo → captura → auth | Hash/fingerprint, vigencia, versionado y readiness | E2E retorno auténtico y recuperación operativa ausentes |
| Patrones | EN DESARROLLO | `StandardsPage` → standards/certificates/uncertainties | CRUD, vigencia y permisos explícitos | Renovación/selección extremo a extremo no demostrada; listados sin paginar |
| Procedimientos | EN DESARROLLO | página oculta → procedures/metrology profiles | CRUD/versiones/permisos | No accesible desde navegación; integración con hoja incompleta |
| Perfiles/metrología/selección | EN DESARROLLO | endpoints técnicos + motores | Resolver perfil, candidatos y validaciones | Motores operativos legacy públicos; no gobiernan flujo final de Hojas |
| Incertidumbre | EN DESARROLLO | página oculta → modelos/versiones/componentes/fórmulas | Workflow draft/review/approve/archive y permisos | Drift de columnas soft-delete; timestamps sin defaults; integración final incompleta |
| Actividad | EN DESARROLLO | panel genérico → threads/messages/mentions/attention/attachments | Acceso entidad+permiso, idempotencia, retiro, MIME/firma/tamaño de adjunto | Defaults faltantes en attention/read; navegación a registro parcial; auditabilidad DB no append-only total |
| Notificaciones | EN DESARROLLO | provider/bell → notifications | No leídos, lectura, vínculo a Activity y autenticación | Sin entrega externa/retry/observabilidad; `NotificationCenterPage` huérfana |
| Comunicaciones | EN DESARROLLO | centro interno → conversations/messages | Participantes y sesión requerida | Sin canales externos, paginación ni adjuntos; identidad cliente todavía interna |
| Ajustes/configuración | EN DESARROLLO | navegación de settings y configuración institucional | Usuarios, auditoría y panel de plantillas existen | Identidad visual/documental/sedes/ERP son placeholders; 4 categorías ComingSoon |
| Identidad institucional | EN DESARROLLO | `institutional_configurations` + snapshots de Hojas | Snapshot formal en Hojas; configuración auditable | Cotización, OT, factura, recibo, login y frontend usan fuentes/fallbacks distintos |
| Folios/consecutivos | EN DESARROLLO | `institutional_folio_sequences` + locks/constraints | Certificados/OT con prefijo-año y pisos | Timestamps sin default en linked companies; folios Agenda/Llamado sin consumidores; legacy max coexistente |
| Storage/archivos | EN DESARROLLO | `storage_service.py` y rutas por dominio | Sanitización de nombre y confinamiento de path central | Storage local, archivos reales rastreados, cargas sin límite uniforme, sin antivirus/retención/cifrado |
| PDF/XLSX/ZIP | EN DESARROLLO | ReportLab/Jinja/openpyxl/LibreOffice/zipfile | Generación real y pruebas focalizadas | Generación síncrona/en memoria, ZIP bomb, fuentes institucionales divergentes, sin pruebas visuales globales |
| Facturama | EN DESARROLLO | cliente async, health, intentos, reconcile/recover | Incertidumbre evita reemisión; trazabilidad de intentos | Producción no cerrada; sin cancelación/webhook; dependencia externa no probada en auditoría |
| SAT | EN DESARROLLO | catálogos versionados, importador y búsqueda | Índices/favoritos/alias/permisos | `alembic check` propone eliminar índices especializados; fuente y vulnerabilidad operacional pendientes |
| LibreOffice | CASI SELLADO | diagnóstico y conversión XLSX→PDF | Disponible 26.2.4.2; timeout y errores registrados | Punto único síncrono; sin worker/aislamiento/readiness ni despliegue reproducible |
| Motor de Resoluciones núcleo | CASI SELLADO | dominio/contratos/persistencia/lifecycle/security/runtime/audit | Cobertura específica, locks, idempotencia, compensación, outbox y evidencia | Fase 14 no aprobada; operación depende de migraciones generales con drift/downgrade roto |
| Centro/API/SDK/worker | EN DESARROLLO | `/resolutions`, API v1, SDK HTTP, cola durable | Consumidor/organización, cursor ligado, leases/fencing y recovery | Sólo 2 verticales; origen de excepciones no conectado; sin supervisión/despliegue/HA probado |
| Portal cliente | EN DESARROLLO | cuatro endpoints backend | Filtra sólo estados/visibilidad | Sin auth, UI ni tenant; devuelve registros globales e IDOR por id de certificado |
| Toolkit/scripts/backups | EN DESARROLLO | `scripts/myc`, doctor/reset/backup/SAT | Doctor pasa y reset centralizado | Backup/head divergente; artefactos rastreados; scripts sin CI y puerto histórico inconsistente |
| Infraestructura/despliegue | NO INICIADO | ejecución local manual | Health estático | No Docker, CI/CD, TLS/proxy declarativo, readiness, métricas, tracing, alertas ni restore drill |
| Encuesta/reporte final | NO INICIADO | No evidencia local | NO VERIFICADO por ausencia | Definir alcance o retirar del flujo de cierre |
| Google Drive | NO INICIADO | No evidencia local | NO VERIFICADO por ausencia | Integración explícitamente pendiente |

## Flujo macro y transiciones

| Transición | Precondición/estado | Responsable/permiso real | Efecto y trazabilidad | Reversibilidad/prueba/hueco |
| --- | --- | --- | --- | --- |
| Lead → Cliente | Lead inexistente | Endpoint Clientes público | Crea cliente y audit log sin actor | No hay CRM; alta no autorizada |
| Cliente → Cotización | cliente activo | POST opcional, sin permiso | Quotation/items/snapshot/activity | Pruebas servicio; seguridad ausente |
| Cotización → Aprobada | estado permitido | POST opcional | status accepted, audit/activity | Cancel/reject existen; 401/403 ausente |
| Aprobada → ETS | coherencia cliente/cotización | POST ETS público | service_order/items/OT/snapshots | No automático en todos los recorridos |
| ETS → Confirmado/Llamado | agenda/servicio/técnico | rutas públicas | cambia status, audit/activity | Máquina duplicada router/servicio |
| ETS → OT/Equipos | partidas y cupo 10 | rutas públicas | OT/equipment/cert expected | Vertical Motor alterno no conectado al origen |
| Equipo → Hoja | equipo elegible | `field_sheets.create` | snapshot/fields/signatures | Cálculo y E2E 23 plantillas pendientes |
| Hoja → Captura | complete/review | permisos field_sheets | paquete XLSX/ZIP | Upload de retorno sin límite seguro |
| Captura → Calidad | Master identificado, sin mismatch | `certificates.capture` | status quality_review, actor/audit | warnings permiten; UI duplicada |
| Calidad → Autenticado | quality_approved | `certificates.approve` | LibreOffice/PDF/version/audit | Síncrono; acción también en ETS |
| Autenticado → Liberado | compuerta financiera | `release.manage` | client_visible/status/audit | Portal público global invalida aislamiento |
| ETS → Factura | cotización aprobada/orden coherente | `invoices.manage` | Invoice/items/snapshot fiscal | CFDI productivo incompleto |
| Factura → Pago | saldo >0, no cancelada | `payments.manage` | payment/saldo/status/activity/audit | Sin reverso/conciliación/complemento |
| Pago → Cierre ETS | certificados liberados y compuertas | ruta ETS pública | released/closed | Cierre existe, pero no hay E2E macro ni encuesta |

## Arquitectura real

```text
React SPA monolítica (routing propio por path/hash, tokens localStorage)
  └─ api.js (179 funciones; fetch)
      └─ FastAPI (36 routers incluidos; 306 operaciones)
          ├─ routers con mezcla desigual de auth y lógica
          ├─ services de dominio y generadores síncronos
          ├─ SQLAlchemy ORM (101 tablas) → PostgreSQL/Alembic
          ├─ storage local → PDF/XLSX/XML/ZIP
          ├─ Facturama HTTP + LibreOffice local
          └─ Motor de Resoluciones
              ├─ dominio/lifecycle/security/audit/compensation
              ├─ persistencia/outbox/cola PostgreSQL/worker
              ├─ Centro interno + API pública v1 + SDK
              └─ 2 integraciones instaladas
```

La arquitectura declarada de servicios, snapshots y controladores únicos se cumple mejor en Workbench, Servicios Compuestos y Motor. Diverge en autorización general, identidad institucional, ETS router/service, rutas técnicas legacy, superficies de Calidad y productores del Motor.
