> Estado: AUDITORÍA
>
> Tipo: Auditoría
>
> Autoridad: Media; evidencia del corte indicado
>
> Prevalece sobre: auditorías anteriores sólo para hechos comparables al 2026-07-21
>
> Reemplazado para determinar avance vigente por: `../project/PROJECT_STATUS.md`

# Auditoría integral de avance del ERP MYC

Fecha de corte: 2026-07-21  
Versión declarada: ERP MYC `0.4.0`  
Revisión Alembic aplicada y head: `fd5e6f7a8b9c`  
Alcance: frontend, backend, PostgreSQL local, migraciones, pruebas, documentación histórica, scripts e infraestructura local.

## 1. Criterio de auditoría

Esta auditoría clasifica cada dominio con un único estado:

- **SELLADO:** no se identificó trabajo funcional o de UX pendiente dentro del alcance acordado; las validaciones disponibles son coherentes con ese cierre.
- **CASI SELLADO:** el flujo principal existe, pero queda al menos un cierre verificable acotado.
- **EN DESARROLLO:** existe una implementación relevante, pero faltan partes funcionales, de integración, seguridad o UX necesarias para cerrar el módulo.
- **PENDIENTE:** sólo existe una capacidad parcial, absorbida por otro dominio o documentada sin módulo operativo completo.
- **NO INICIADO:** no se encontró implementación funcional del dominio.

No se tomó como prueba de cierre la sola existencia de archivos, rutas, componentes, tablas, compilación o textos históricos que usen la palabra “sellado”. Un estado sólo se concede cuando el código vigente y las validaciones observables sostienen el cierre.

### Evidencia revisada

- Navegación y páginas React, componentes compartidos, API client y CSS.
- Routers, servicios, schemas, modelos, plantillas PDF y configuración FastAPI.
- Las 55 tablas de PostgreSQL local, únicamente mediante esquema y conteos; no se leyó contenido sensible.
- Cadena Alembic: un único head y base local en `fd5e6f7a8b9c (head)`.
- Los 12 archivos de prueba actuales: **63 pruebas correctas**.
- `npm run build`: correcto; Vite advierte un chunk principal de **852.38 kB** sin comprimir.
- `./scripts/myc doctor`: ejecuta, pero produce falsos negativos por un defecto en su función `check` y declara el puerto frontend `5173`, mientras la sesión y varias referencias operativas usan `5174`.
- Revisión visual acotada de Login y Laboratorio de Hojas de Campo. No se realizó un E2E autenticado de todos los módulos porque no se usaron credenciales ni se alteraron datos para esta auditoría.
- Historial principal: `BACKUP_ESTADO_ACTUAL.md`, especificaciones V2/V3, auditorías de Facturación, Hojas de Campo, Captura, Toolkit, Control Documental y reglas de negocio/permisos.

### Limitaciones explícitas

- No se confirmó una emisión nueva contra Facturama Sandbox ni se probó Producción.
- No se abrió cada modal con una sesión autenticada; donde la UX sólo pudo verificarse por código se indica expresamente.
- La base local está prácticamente vacía en los dominios operativos: 0 ETS, equipos, hojas, certificados y facturas; por ello no permite demostrar un flujo real extremo a extremo con datos vigentes.
- Los conteos históricos de documentos y clientes no coinciden con algunos cortes anteriores porque la base fue reinicializada después; el estado actual observado es la fuente de esta auditoría.

## 2. Resumen ejecutivo

El ERP ya contiene una base funcional amplia: clientes, cotizaciones, ETS, órdenes de trabajo, equipos, hojas de campo, certificados, control documental, patrones, usuarios, SAT y facturación con Facturama Sandbox. La cadena de migraciones está alineada y las pruebas existentes pasan. Sin embargo, **el sistema no está listo para declararse versión estable 1.0**.

Los bloqueadores principales son:

1. **Seguridad de API:** registro público acepta `role_names`; un consumidor directo puede solicitar un rol privilegiado. `get_current_user` no rechaza tokens de refresh usados como bearer. Clientes, cotizaciones, equipos, catálogo MYC, plantillas comerciales, motores operativos, portal cliente y gran parte de ETS exponen rutas sin autenticación o con usuario opcional.
2. **ETS duplicado:** `backend/app/routers/service_orders.py` contiene una copia material de la lógica de `backend/app/services/service_orders.py` y registra dos veces `POST /{service_order_id}/confirm-signatures`. Esto contradice la separación router/servicio y la exigencia de no duplicar acciones.
3. **Calidad no es el único autenticador visible:** Calidad autentica, pero el ETS también expone acciones individuales y masivas de autenticación, incluida la cinta de acciones de Calidad dentro de `ServiceOrdersPage.jsx`.
4. **Hojas de Campo incompletas:** existen 23 definiciones y snapshots, pero persisten pendientes históricos de semántica, cálculos, patrones, aprobación/rechazo propio, filtros, renderer PDF exacto y E2E autenticado.
5. **Facturación incompleta:** el borrador sólo persiste al pulsar guardar y se descarta al cerrar si no se guardó; Producción, cancelación/sustitución, complementos PPD, historial especializado y varias pestañas del expediente siguen ausentes o como placeholder.
6. **Agenda, Llamados, CRM/Leads, encuestas/reportes y Google Drive no existen como módulos completos.** Agenda y Llamado sólo están representados por fecha/estado dentro del ETS.
7. **Toolkit no es confiable como diagnóstico:** `doctor` entrega falsos negativos; sigue habiendo discrepancia de puerto y no existe prueba automatizada de scripts.
8. **Cobertura de pruebas desigual:** no hay pruebas frontend ni suites dedicadas a autenticación, permisos, cotizaciones completas, ETS completo, órdenes de trabajo, equipos, Control Documental, usuarios/roles o Toolkit.

Conclusión: hay un solo cierre defendible dentro de un alcance explícitamente congelado: **Control Documental V1**. El resto requiere al menos un cierre acotado o trabajo material.

## 3. Tabla general de estado

| Módulo o capacidad | Estado | Dictamen breve |
| --- | --- | --- |
| Autenticación | EN DESARROLLO | JWT y refresh existen, pero hay escalación de roles y separación de tipos de token incompleta. |
| Dashboard | CASI SELLADO | Métricas y accesos existen; falta autorización visual y E2E con datos reales. |
| CRM / Leads | NO INICIADO | Sólo aparece en catálogo documental de módulos; no hay modelo, router ni pantalla operativa. |
| Clientes | CASI SELLADO | Flujo amplio y persistente; endpoints principales están abiertos y falta prueba integral autenticada. |
| Contactos | PENDIENTE | Subentidad de Cliente; no existe flujo independiente de seguimiento. |
| Cotizaciones | CASI SELLADO | Flujo, PDF, autosave y snapshots existen; restauración de partidas y permisos siguen abiertos. |
| Agenda | PENDIENTE | Sólo `agenda_date` dentro de ETS; no hay agenda, folio, estados ni calendario propios. |
| Llamados | PENDIENTE | Sólo transición `called`; no hay entidad, bitácora, folio ni experiencia propia. |
| ETS / Servicios | EN DESARROLLO | Flujo muy amplio, pero duplicación, permisos, acciones repetidas y E2E impiden cierre. |
| Órdenes de Trabajo | CASI SELLADO | Agrupación de hasta 10 equipos, PDFs y firmas existen; gestión y pruebas directas son incompletas. |
| Equipos | CASI SELLADO | Alta, estados, cupos, snapshots y asociación a OT existen; API abierta y módulo no independiente. |
| Hojas de Campo | EN DESARROLLO | Plantillas, captura, snapshots y PDF existen; pendientes funcionales históricos siguen vigentes. |
| Captura | EN DESARROLLO | Flujo de paquetes, carga y envío a Calidad existe; integración E2E y manejo de incidencias faltan. |
| Calidad | EN DESARROLLO | Revisión y aprobación existen; no es autenticador exclusivo y hay acciones duplicadas en ETS. |
| Certificados | CASI SELLADO | La pantalla filtra autenticados y la liberación tiene compuerta; falta cerrar duplicación y E2E. |
| Facturación | EN DESARROLLO | Workbench, Sandbox, XML/PDF y cobranza existen; persisten huecos funcionales críticos. |
| Pagos y notas de crédito | EN DESARROLLO | Backend y vistas globales existen; pestañas por expediente y CFDI relacionados están incompletos. |
| Control Documental V1 | SELLADO | Lista, ficha, versiones, historial, publicación y diseñador deshabilitado coinciden con el cierre V1. |
| Plantillas Maestras de Certificado | CASI SELLADO | Upload/versionado/snapshot existen; falta el E2E real de paquete de Captura. |
| Catálogo MYC | PENDIENTE | Backend existe, pero el módulo independiente está oculto y sus endpoints no tienen permisos. |
| Catálogos SAT | CASI SELLADO | Fuente XLSX, 151,229 registros, versiones, índices y pruebas; SSoT y permisos de consumo requieren cierre. |
| Patrones | EN DESARROLLO | CRUD y certificados/incertidumbres existen; se declara “Renovación” y carece de pruebas integrales. |
| Procedimientos | PENDIENTE | Backend y página existen, pero no están en navegación principal. |
| Perfiles técnicos / motores metrológicos | PENDIENTE | Infraestructura no expuesta como flujo vigente. |
| Incertidumbre | EN DESARROLLO | Motor versionado y UI existen, pero la página está oculta y no está integrada al flujo operativo. |
| Administración / Configuración | EN DESARROLLO | Usuarios, auditoría y plantillas; faltan parámetros generales e identidad institucional visibles. |
| Usuarios | CASI SELLADO | Alta, edición, roles y activación existen; la seguridad de registro y pruebas impide cierre. |
| Roles y permisos | EN DESARROLLO | Roles estáticos y multirol existen; no hay administración de permisos ni cobertura completa de endpoints. |
| Auditoría | CASI SELLADO | Bitácora y consulta protegida existen; cobertura de eventos críticos es desigual. |
| Integración Facturama | EN DESARROLLO | Salud, emisión Sandbox, conciliación y documentos existen; Producción/cancelación/complementos no. |
| Integración Google Drive | NO INICIADO | No se encontró cliente, configuración, endpoint ni UI. |
| Portal de cliente | EN DESARROLLO | Backend existe sin identidad de cliente ni UI; actualmente expone datos globales. |
| APIs | EN DESARROLLO | Contratos amplios, pero política de autenticación inconsistente. |
| Componentes reutilizables / UX | EN DESARROLLO | Hay componentes compartidos; persisten páginas monolíticas, duplicados y un `window.alert`. |
| Toolkit y scripts | EN DESARROLLO | Flujos útiles y reset unificado; `doctor` es defectuoso y no hay pruebas de scripts. |
| Infraestructura | EN DESARROLLO | Local/túnel/config existen; no hay CI visible ni validación de despliegue estable. |
| Seguridad | EN DESARROLLO | Bloqueadores críticos de autorización y gestión de tokens. |
| Base de datos y migraciones | CASI SELLADO | Un head y base alineada; quedan columnas legacy y duplicaciones conceptuales por retirar. |
| Encuestas y reporte final | NO INICIADO | Sólo están en la especificación y flujo documental. |

## 4. Auditoría módulo por módulo

### 4.1 Autenticación — EN DESARROLLO

**Qué controla.** Registro, login, access/refresh JWT y usuario actual. Flujo: registro/login → tokens en `localStorage` → bearer en `api.js` → `/auth/me` → layout autenticado. Archivos: `routers/auth.py`, `services/auth.py`, `core/security.py`, `schemas/auth.py`, `LoginPage.jsx`, `services/api.js`.

**Validaciones existentes.** Email Pydantic, contraseña de 8 a 128 caracteres, hash PBKDF2-SHA256, expiración JWT, usuario activo y refresh con `token_type=refresh`.

**Observaciones históricas.** ✅ Resuelta — Login y refresh implementados. ⚠ Parcialmente resuelta — Roles embebidos en tokens pero autorización consulta roles actuales desde BD. ❌ Sigue pendiente — El registro público admite `role_names`; el frontend no lo usa, pero la API sí permite solicitar `Administrador`. ❌ Sigue pendiente — Un refresh token es aceptado por `get_current_user` porque no se exige `token_type=access`. ⚠ Parcialmente resuelta — Tokens en `localStorage`, expuestos ante XSS. ❌ Sigue pendiente — La clave JWT conserva un default de desarrollo y no se bloquea el arranque inseguro fuera de desarrollo.

**Pendientes actuales.** Cerrar registro privilegiado; distinguir access/refresh; exigir secreto seguro en despliegue; añadir pruebas de auth y revocación/cambio de contraseña según el flujo ya esperado de administración.

**Riesgos.** Crítico: escalación de privilegios, reutilización de refresh como access y compromiso total si se despliega con secreto por defecto.

### 4.2 Dashboard — CASI SELLADO

**Qué controla.** Consolidación de conteos y accesos rápidos a módulos. Archivos: `DashboardHome.jsx`, `navigation.js`, `api.js`, servicios de conteos.

**Validaciones existentes.** Normalización numérica, estados de carga/error y cálculo de avance ETS.

**Observaciones históricas.** ✅ Resuelta — Indicadores ETS, captura, Calidad, autenticación y liberación. ✅ Resuelta — Liquid Glass y accesos reutilizan tarjetas. ⚠ Parcialmente resuelta — Todos los módulos se muestran sin filtrar por permisos del usuario. ⚠ Parcialmente resuelta — No hubo validación autenticada con volumen real.

**Pendientes actuales.** Aplicar visibilidad por capacidad/rol y ejecutar E2E con datos representativos.

**Riesgos.** UX: accesos que terminan en 403 o, en rutas abiertas, permiten operaciones indebidas.

### 4.3 CRM / Leads — NO INICIADO

**Qué controla.** Debería administrar prospectos y su conversión. Sólo existe una definición informativa en `services/modules.py` y especificaciones.

**Validaciones existentes.** Ninguna.

**Observaciones históricas.** ❌ Sigue pendiente — No hay modelos, APIs, pantalla, estados ni conversión. No puede verificarse ninguna decisión de UX.

**Pendientes actuales.** Implementar el módulo acordado o retirar formalmente el dominio del alcance 1.0.

**Riesgos.** El flujo comercial comienza directamente en Cliente/Cotización y no conserva origen del lead.

### 4.4 Clientes — CASI SELLADO

**Qué controla.** Personas físicas/morales, datos fiscales, contactos, constancia, perfiles de certificado, importación/exportación, archivo/restauración y eliminación condicionada. Archivos: `ClientsPage.jsx`, `models/client.py`, `routers/clients.py`, `services/clients.py`, `schemas/client.py`.

**Validaciones existentes.** Identidad por tipo de cliente, RFC/CP/correo en importación, duplicados, constancia PDF, régimen/uso SAT, hard delete sólo sin historial, cascadas controladas y auditoría. Pruebas de importación tolerante y eliminación.

**Observaciones históricas.** ✅ Resuelta — Modal fiscal reestructurado. ✅ Resuelta — Persistencia real de importación. ✅ Resuelta — Parser de constancia corregido para persona física/moral. ✅ Resuelta — Eliminación/archivo/restauración consolidados. ✅ Resuelta — Sin duplicar componentes por tipo. ⚠ Parcialmente resuelta — `city` y `legal_name` conservan compatibilidad legacy. ❌ Sigue pendiente — GET/POST/PATCH/importación/exportación/perfiles/constancia no requieren autenticación; sólo archivo/restauración/eliminación exigen permiso.

**Pendientes actuales.** Proteger todas las rutas con permisos coherentes y ejecutar E2E autenticado del ciclo completo.

**Riesgos.** Crítico: lectura y modificación no autorizada de datos personales/fiscales.

### 4.5 Contactos — PENDIENTE

**Qué controla.** `ClientContact` guarda nombre, email, teléfono y puesto dentro de Cliente. No existe módulo autónomo.

**Validaciones existentes.** Relación y cascada con cliente; importación puede crear contacto principal.

**Observaciones históricas.** ✅ Resuelta — Contactos integrados al alta/importación de Cliente. ❌ Sigue pendiente — No hay agenda de contactos, historial de interacción, responsable ni seguimiento.

**Pendientes actuales.** Definir si Contactos queda oficialmente absorbido por Clientes; si no, implementar su flujo acordado.

**Riesgos.** Ambigüedad de ownership y pérdida de trazabilidad comercial.

### 4.6 Cotizaciones — CASI SELLADO

**Qué controla.** Cotización, partidas, catálogo, estados, asesor, PDF, condiciones comerciales, autosave e historial. Archivos: `QuotationsPage.jsx`, `models/quotation.py`, `routers/quotations.py`, `services/quotations.py`, `quotation_pdfs.py`, `quotation_pdf.html`.

**Validaciones existentes.** Estados y transiciones, totales/impuestos/descuentos, snapshots, cliente activo, edición restringida por estado, PDF e identidad institucional.

**Observaciones históricas.** ✅ Resuelta — Selector buscable de cliente. ✅ Resuelta — Asesor automático cuando hay sesión. ✅ Resuelta — Autosave con debounce. ✅ Resuelta — PDF: total legible, CP fiscal y retiro de Uso CFDI. ✅ Resuelta — Navegación contextual ETS ↔ Cotización. ⚠ Parcialmente resuelta — Snapshots guardan partidas, pero la restauración sólo recupera campos comerciales. ❌ Sigue pendiente — Rutas CRUD/estado/PDF aceptan llamadas sin autenticación; el asesor usa usuario opcional.

**Pendientes actuales.** Restaurar partidas desde snapshot o ajustar formalmente el contrato de historial; aplicar permisos a cada transición; E2E del ciclo hasta ETS.

**Riesgos.** Edición anónima y falso sentido de recuperación completa.

### 4.7 Agenda — PENDIENTE

**Qué controla.** Actualmente sólo `service_orders.agenda_date` y campos de fecha dentro del ETS.

**Validaciones existentes.** La UI considera fecha de agenda, servicio y técnico para completar el resumen; no hay máquina de estados propia.

**Observaciones históricas.** ⚠ Parcialmente resuelta — Fecha integrada en ETS. ❌ Sigue pendiente — No existen folio `AMYC`, entidad, calendario, estados, reprogramación, recordatorios ni permisos de Agenda.

**Pendientes actuales.** Implementar la agenda acordada o congelar por decisión explícita su absorción en ETS.

**Riesgos.** Programación sin trazabilidad ni control de colisiones/cambios.

### 4.8 Llamados — PENDIENTE

**Qué controla.** Sólo la transición de ETS `confirmed → called` y la acción `/call`.

**Validaciones existentes.** La máquina de estados del servicio limita la transición.

**Observaciones históricas.** ⚠ Parcialmente resuelta — El hito existe dentro del ETS. ❌ Sigue pendiente — No hay entidad, folio `SMYC`, bitácora, captura de resultado ni módulo visible.

**Pendientes actuales.** Materializar el flujo acordado o documentar que queda absorbido por ETS con evidencia equivalente.

**Riesgos.** Seguimiento comercial/técnico no auditable.

### 4.9 ETS / Servicios — EN DESARROLLO

**Qué controla.** Expediente raíz desde cotización/cliente, etapas, equipos, hojas, Captura, Calidad, certificados, documentos, facturación, firmas y cierre. Archivos: `ServiceOrdersPage.jsx`, `models/service_order.py`, `routers/service_orders.py`, `services/service_orders.py`, `utils/etsStages.js`.

**Validaciones existentes.** Transiciones de servicio, cliente/cotización consistentes, OT automáticas por cupo, cierre, compuertas por etapa, firmas por ciclo, excepciones, paquetes y liberación financiera.

**Observaciones históricas.** ✅ Resuelta — Tablero por etapas y agrupaciones. ✅ Resuelta — Cupos de 10 equipos por OT. ✅ Resuelta — Firmas por ciclo y reapertura. ✅ Resuelta — Paquete de Captura y snapshots de Master. ⚠ Parcialmente resuelta — Excepciones existen como comentario/acción, no como agregado persistente específico. ❌ Sigue pendiente — El router contiene una copia de unas 400 líneas de la lógica del servicio. ❌ Sigue pendiente — `confirm-signatures` está declarado dos veces. ❌ Sigue pendiente — CRUD y transiciones principales carecen de permisos; firmas usan usuario opcional. ❌ Sigue pendiente — Calidad/autenticación también se opera desde ETS. ⚠ Parcialmente resuelta — `ServiceOrdersPage.jsx` tiene 4,579 líneas.

**Pendientes actuales.** Eliminar duplicación y ruta repetida; fijar permisos por acción; centralizar autenticación en Calidad; formalizar excepciones; E2E Cliente → Cotización → ETS → cierre.

**Riesgos.** Arquitectura divergente, aplicación de reglas distintas según ruta, autorización insuficiente y mantenimiento muy costoso.

### 4.10 Órdenes de Trabajo — CASI SELLADO

**Qué controla.** `ServiceWorkOrder` agrupa máximo 10 equipos, numera OT, enlaza ciclos de firmas y genera PDF individual/conjunto.

**Validaciones existentes.** Número único, secuencia, límite, asociación de equipo y hoja, agrupador compartido `WorkOrderFlowGroups`.

**Observaciones históricas.** ✅ Resuelta — Agrupación automática y PDF por OT. ✅ Resuelta — Firma nueva sólo para OT/equipos agregados después del ciclo anterior. ⚠ Parcialmente resuelta — `service_orders.work_order_number` sigue como compatibilidad legacy junto con `service_work_orders`. ❌ Sigue pendiente — No hay suite dedicada ni CRUD/gestión independiente protegida.

**Pendientes actuales.** Validar E2E de múltiples OT y retirar/encapsular el número legacy cuando sea seguro; asegurar permisos.

**Riesgos.** Doble fuente de número de OT y errores de agrupación histórica.

### 4.11 Equipos — CASI SELLADO

**Qué controla.** Equipos por ETS/OT, cupos, estados, alcance, identificación y snapshot del Master de Certificado.

**Validaciones existentes.** Pertenencia a ETS/OT, capacidad, estados, unicidad parcial, bloqueo de adicionales y asociación a hojas/certificados.

**Observaciones históricas.** ✅ Resuelta — Modal refinado y alta guiada por cupo. ✅ Resuelta — Snapshot documental del Master. ✅ Resuelta — Estados y asociación por OT. ⚠ Parcialmente resuelta — Página independiente existe pero no tiene entrada activa propia; el flujo real está en ETS. ❌ Sigue pendiente — Todo el router de equipos carece de autenticación/permisos.

**Pendientes actuales.** Proteger API y validar el ciclo multi-OT con snapshots.

**Riesgos.** Modificación anónima de inventario operativo.

### 4.12 Hojas de Campo — EN DESARROLLO

**Qué controla.** Plantillas declarativas, captura persistente, resultados, firmas, snapshots, PDF y relación ETS/equipo/OT. Archivos: `FieldSheetLayout.jsx`, `fieldSheetPagination.js`, `field_sheet*.py`, `field_sheet_engine_pdf.html`, `FieldSheetTemplatesSettingsPanel.jsx`.

**Validaciones existentes.** 23 definiciones, snapshots inmutables por hoja, campos/resultados/firmas, PDF, completar/revisar, pruebas de contrato y motor.

**Observaciones históricas.** ✅ Resuelta — 23 plantillas renderizadas en laboratorio sin overflow según evidencia histórica. ✅ Resuelta — Identidad institucional central. ✅ Resuelta — Captura y snapshots persistentes. ✅ Resuelta — Agrupación por OT. ⚠ Parcialmente resuelta — PDF backend usa Jinja y no el renderer React exacto. ⚠ Parcialmente resuelta — Firmas son soportadas, pero la captura gráfica del formulario y el flujo operativo completo no quedaron demostrados. ❌ Sigue pendiente — Siguen pendientes semánticas de General, Presión, Báscula/Balanza, Eléctrica, Reglas y Verificación. ❌ Sigue pendiente — No hay cálculos, tolerancias, promedios, conversiones, incertidumbre, cumplimiento ni patrón automático conectados. ❌ Sigue pendiente — Falta aprobación/rechazo explícito propio de la hoja. ❌ Sigue pendiente — Listado global sin todos los filtros/acceso directo. ⚠ Parcialmente resuelta — El laboratorio es público, simulado y no persistente; además mostró `Failed to fetch` en identidad durante esta auditoría.

**Pendientes actuales.** Resolver las semánticas ya documentadas; integrar automatizaciones acordadas; unificar renderer; acciones propias de aprobación/rechazo; filtros; E2E autenticado de las 23.

**Riesgos.** Certificados construidos sobre captura manual no validada; divergencia visual React/PDF; falsas conclusiones basadas en el laboratorio.

### 4.13 Captura — EN DESARROLLO

**Qué controla.** Preparación de certificados, descarga de paquete PDF/XLSX por ETS/OT, recepción de XLSX/ZIP, asociación y envío a Calidad.

**Validaciones existentes.** Elegibilidad, nombres Windows-safe, multipart/ZIP, conservación de no identificados, folios reservados y permisos en endpoints del paquete.

**Observaciones históricas.** ✅ Resuelta — `null.zip` corregido. ✅ Resuelta — Descarga multipart interpretada. ✅ Resuelta — Master/snapshot y carga tolerante. ⚠ Parcialmente resuelta — La base actual no tiene casos elegibles. ❌ Sigue pendiente — E2E PDF/XLSX/ZIP sigue expresamente pendiente. ⚠ Parcialmente resuelta — Archivos no identificados quedan como incidencia, pero no existe bandeja formal de resolución.

**Pendientes actuales.** Ejecutar E2E elegible real y cerrar la resolución operativa de archivos no identificados.

**Riesgos.** Paquetes que compilan pero fallan con datos/masters reales.

### 4.14 Calidad — EN DESARROLLO

**Qué controla.** Revisión de PDF, match, aceptación manual, aprobación/rechazo, retorno a técnico y autenticación.

**Validaciones existentes.** Secuencia `ready_for_quality → match_validated → quality_approved → authenticated`, PDF obligatorio, comentario de rechazo, permisos de Calidad y auditoría.

**Observaciones históricas.** ✅ Resuelta — Match previo a aprobación. ✅ Resuelta — Calidad aprueba y autentica. ✅ Resuelta — Retorno a Captura/Técnico. ❌ Sigue pendiente — No es el único autenticador: ETS muestra “6. Autenticar” y acciones masivas; el router de servicios expone autenticación por ETS. ❌ Sigue pendiente — Acciones de Calidad están duplicadas entre `QualityPage.jsx` y `ServiceOrdersPage.jsx`.

**Pendientes actuales.** Dejar autenticación exclusivamente en Calidad; retirar duplicados de ETS y mantener allí sólo estado/lectura.

**Riesgos.** Dos superficies con reglas/UX divergentes y segregación de funciones debilitada.

### 4.15 Certificados — CASI SELLADO

**Qué controla.** Expediente de certificados autenticados, PDF original/versiones, verificación, liberación al cliente y compuerta de pago.

**Validaciones existentes.** La UI filtra por `authenticated_pdf_path` y estados autenticado/liberado; backend exige match aceptado, autenticación y pago; QR/código/hash y ruta pública de verificación.

**Observaciones históricas.** ✅ Resuelta — Sólo muestra certificados autenticados. ✅ Resuelta — Conserva PDF original para auditoría y versiones inmutables. ✅ Resuelta — Liberación sólo desde autenticado y con compuerta financiera. ✅ Resuelta — Verificación pública. ⚠ Parcialmente resuelta — La autenticación ocurre también fuera de Calidad. ⚠ Parcialmente resuelta — No hubo E2E actual porque la base tiene 0 certificados.

**Pendientes actuales.** Centralizar autenticación en Calidad y ejecutar E2E aprobación → autenticación → liberación → verificación.

**Riesgos.** Duplicación de acciones y dependencia de rutas de archivo locales.

### 4.16 Facturación — EN DESARROLLO

**Qué controla.** Mesa de trabajo, borradores, facturas, emisión Facturama, XML, PDF MYC, cobranza, pagos, notas, settings y trazabilidad PAC. Archivos: `BillingPage.jsx`, `invoice-workbench/*`, `models/invoice.py`, `routers/invoices.py`, `services/invoices.py`, `services/facturama/*`, `invoice_pdfs.py`, `invoice_pdf.html`.

**Validaciones existentes.** Totales, snapshots fiscal/origen, catálogos SAT activos, bloqueo de doble factura, estado de emisión, lock, intentos PAC, saneamiento de errores, conciliación estricta, recuperación XML/PDF, XML válido, permisos y pruebas (Facturama/mapper/conciliación/documentos).

**Observaciones históricas.**

| Observación | Estado verificable |
| --- | --- |
| Persistencia del borrador | ⚠ Parcialmente resuelta — persiste al guardar; cerrar el modal borra el estado React sin advertencia ni autosave. |
| Navegación ETS → Facturación | ✅ Resuelta mediante contexto en `localStorage` y apertura del expediente. |
| PDF institucional MYC | ✅ Resuelta; se genera con plantilla institucional y datos del XML cuando existe. |
| XML fiscal | ✅ Resuelta para XML recuperado y almacenado. |
| Nomenclaturas SAT | ✅ Resuelta en PDF contra catálogos activos; selectores consultan catálogo local. |
| Tamaños tipográficos / estructura PDF | ✅ Resuelta según generación e inspección histórica de una página; no se revalidó visualmente con factura actual porque hay 0 registros. |
| Documentos internos ocultos | ✅ Resuelta en la vista ordinaria; rutas técnicas siguen protegidas y disponibles para soporte. |
| Indicador Facturama | ✅ Resuelta — estado conectado/sin conexión y reintento. |
| UX consistente | ⚠ Parcialmente resuelta — workbench compartido, pero Pagos, CxC, Notas, Documentos e Historial del expediente son placeholders. |
| Emisión Facturama | ⚠ Parcialmente resuelta — Sandbox, idempotencia defensiva y conciliación; Producción deshabilitada. |
| Impresión | ⚠ Parcialmente resuelta — descarga PDF; no hay flujo de impresión específico ni E2E actual. |
| Excepciones e historial | ⚠ Parcialmente resuelta — intentos y auditoría backend; no hay UI especializada del expediente. |

**Pendientes actuales.** Autosave/guardado seguro al cerrar; completar pestañas del expediente o retirar navegación falsa; Producción; cancelación/sustitución; complementos PPD; notas fiscales relacionadas; historial/excepciones visibles; prueba E2E Sandbox actual con emisor configurado.

**Riesgos.** Pérdida de cambios no guardados, confusión por placeholders, divergencia entre estado fiscal y cobranza, dependencia PAC y manejo de datos fiscales sensibles.

### 4.17 Pagos y notas de crédito — EN DESARROLLO

**Qué controla.** Pagos parciales, saldo, recibo PDF, cuentas por cobrar y notas internas ligadas a factura.

**Validaciones existentes.** Importe no superior al saldo, recálculo de estado/saldo y auditoría.

**Observaciones históricas.** ✅ Resuelta — Backend y vistas globales. ⚠ Parcialmente resuelta — Las pestañas dentro del expediente son placeholders. ❌ Sigue pendiente — No existen complementos de pago PPD, notas de egreso CFDI, cancelación/aplicación completa ni routers independientes.

**Pendientes actuales.** Completar las vistas por factura y los documentos fiscales acordados para PPD/notas.

**Riesgos.** Mezcla de cobranza administrativa con estado fiscal.

### 4.18 Control Documental V1 — SELLADO

**Qué controla.** Lista maestra, ficha, versiones, historial derivado, publicación/activación, obsolescencia y Plantillas Maestras. Archivos: `DocumentLibraryPage.jsx`, `models/controlled_document.py`, `routers/documents.py`, `services/controlled_documents.py`.

**Validaciones existentes.** Permisos de lectura/alta/edición/aprobación/archivo, versión activa única, checksum/tamaño en Masters, vigencia, archivo XLSX y auditoría.

**Observaciones históricas.** ✅ Resuelta — Visible como Control Documental. ✅ Resuelta — Lista Maestra y ficha Liquid Glass. ✅ Resuelta — Versiones, historial y publicación. ✅ Resuelta — Diseñador permanece expresamente deshabilitado, como se acordó para V1. ✅ Resuelta — Sin acciones redundantes por fila. ✅ Resuelta — Plantillas Maestras integradas. La integración futura con renderizadores y un diseñador funcional se excluyó explícitamente del cierre V1 y no se cuenta como pendiente actual.

**Pendientes actuales.** Ninguno dentro del alcance V1 sellado. El E2E de uso del Master pertenece a Captura/Plantillas Maestras, no a la lista maestra documental.

**Riesgos.** Bajo-medio: no hay pruebas automatizadas dedicadas; el historial visual se deriva de fechas/versiones y no de toda la bitácora.

### 4.19 Plantillas Maestras de Certificado — CASI SELLADO

**Qué controla.** Registro/versionado de XLSX maestro, vigencia, hash, descarga y snapshot al equipo.

**Validaciones existentes.** Formato XLSX, checksum, tamaño, expiración, versión activa y snapshot en equipo.

**Observaciones históricas.** ✅ Resuelta — Subvista integrada en Control Documental. ✅ Resuelta — Snapshot evita cambios retroactivos. ❌ Sigue pendiente — E2E completo PDF/XLSX/ZIP quedó pendiente.

**Pendientes actuales.** Ejecutar y documentar el E2E de Captura con un caso elegible.

**Riesgos.** Master correcto en catálogo pero no utilizable en paquete real.

### 4.20 Catálogo MYC — PENDIENTE

**Qué controla.** Conceptos, claves internas/SAT, unidad, precios, márgenes, alcance y Master esperado. Backend: `catalog_item.py`, `catalog_items.py`; uso embebido en Cotizaciones/Facturación.

**Validaciones existentes.** Cálculos de precio/margen, campos fiscales y borrado lógico.

**Observaciones históricas.** ⚠ Parcialmente resuelta — Reutilizado por Cotizaciones/Facturación. ❌ Sigue pendiente — Entrada independiente comentada. ❌ Sigue pendiente — Router completo sin autenticación ni permisos. ⚠ Parcialmente resuelta — No hay pruebas dedicadas.

**Pendientes actuales.** Definir experiencia oficial (módulo o administración embebida), proteger endpoints y cubrir reglas con pruebas.

**Riesgos.** Alteración anónima de precios y claves fiscales.

### 4.21 Catálogos SAT — CASI SELLADO

**Qué controla.** Importación/versionado de XLSX oficial, registros normalizados, búsqueda, vigencia, favoritos y alias.

**Validaciones existentes.** 16 versiones activas y 151,229 registros actuales; checksums, índices prefix/full-text, códigos/vigencia y 8 pruebas SAT dentro de la suite.

**Observaciones históricas.** ✅ Resuelta — Fuente XLSX y reporte de carga. ✅ Resuelta — Nomenclaturas reutilizadas en Facturación. ✅ Resuelta — Búsqueda indexada. ⚠ Parcialmente resuelta — `parsers.py` y APIs internas aún aceptan CSV/JSON, por lo que la fuente única estricta no está completamente blindada. ⚠ Parcialmente resuelta — Permisos de lectura están restringidos a roles concretos y deben alinearse con todos los consumidores.

**Pendientes actuales.** Blindar la fuente oficial y validar que todos los roles que facturan/cotizan tengan lectura efectiva.

**Riesgos.** Versiones no oficiales o acceso denegado desde flujos que dependen del catálogo.

### 4.22 Patrones, certificados de patrón y procedimientos — EN DESARROLLO

**Qué controla.** Inventario de patrones, incertidumbres por rango, certificados/vigencias y procedimientos de calibración.

**Validaciones existentes.** CRUD protegido, estados, fechas, rangos, certificados activos y selección/validación técnica en servicios.

**Observaciones históricas.** ✅ Resuelta — Página Patrones visible. ⚠ Parcialmente resuelta — Navegación la etiqueta “Renovación”. ⚠ Parcialmente resuelta — Procedimientos tiene backend/UI pero está oculto. ❌ Sigue pendiente — No hay pruebas integrales ni datos locales para validar vigencias/selección.

**Pendientes actuales.** Cerrar renovación de Patrones, decidir exposición de Procedimientos y probar selección/vigencia extremo a extremo.

**Riesgos.** Uso de patrón vencido o selección no demostrada en operación real.

### 4.23 Perfiles técnicos, metrología, selección de patrones e incertidumbre — EN DESARROLLO

**Qué controla.** Interpretación documental, perfiles técnicos, selección de patrón, cálculos y modelos/versiones de incertidumbre.

**Validaciones existentes.** Permisos, estados de versión, aprobación/obsolescencia, expresiones y previews.

**Observaciones históricas.** ✅ Resuelta — Infraestructura extensa. ⚠ Parcialmente resuelta — `UncertaintyPage.jsx` existe; el resto se consume como motores. ❌ Sigue pendiente — No está expuesto ni conectado como flujo vigente de Hojas de Campo. ❌ Sigue pendiente — Base local sin modelos/versiones/cálculos y sin pruebas del motor completo.

**Pendientes actuales.** Integrar explícitamente con captura/hojas o mantenerlo fuera de 1.0 y desregistrar APIs no autorizadas. Proteger `operational_engines`, hoy abierto.

**Riesgos.** Código complejo no usado, APIs técnicas abiertas y dos fuentes de cálculo manual/automática.

### 4.24 Administración, Usuarios, Roles, Configuración y Auditoría — EN DESARROLLO

**Qué controla.** Usuarios, multirol, activación, bitácora y panel maestro de plantillas. Archivos: `SettingsPage.jsx`, `UsersSettingsPanel.jsx`, `AuditSettingsPanel.jsx`, `routers/users.py`, `core/permissions.py`.

**Validaciones existentes.** Gestión de usuarios protegida, roles activos, auditoría filtrable y permisos estáticos por rol.

**Observaciones históricas.** ✅ Resuelta — Usuarios y multirol. ✅ Resuelta — Auditoría visible. ✅ Resuelta — Panel maestro. ⚠ Parcialmente resuelta — Configuración general sólo reúne tres pestañas; identidad institucional y parámetros de sistema no tienen una experiencia completa. ❌ Sigue pendiente — No existe CRUD de roles/permisos; la matriz vive en código. ❌ Sigue pendiente — El frontend no oculta módulos por permiso. ❌ Sigue pendiente — No hay pruebas dedicadas.

**Pendientes actuales.** Cerrar configuración institucional/parámetros acordados, autorización visual, administración o congelamiento formal de roles y pruebas.

**Riesgos.** Divergencia entre permisos documentados, código y UX; cambios de rol requieren despliegue.

### 4.25 Integraciones — EN DESARROLLO

**Qué controla.** Actualmente sólo Facturama. `integrations.py` expone salud protegida; el cliente se reutiliza durante el lifespan.

**Validaciones existentes.** Health read-only, errores tipados/saneados, Sandbox/Producción seleccionable y timeout.

**Observaciones históricas.** ✅ Resuelta — Indicador de Facturama. ✅ Resuelta — Emisión, conciliación y recuperación de documentos en Sandbox. ❌ Sigue pendiente — Producción rechazada expresamente. ❌ Sigue pendiente — Google Drive no tiene ninguna implementación. ⚠ Parcialmente resuelta — No hay outbox; la conciliación reduce, pero no elimina, riesgo operacional.

**Pendientes actuales.** Completar Facturama requerido para 1.0 y decidir/implementar Google Drive según el alcance acordado.

**Riesgos.** Dependencia externa, indisponibilidad PAC y almacenamiento local sin réplica integrada.

### 4.26 Portal de cliente — EN DESARROLLO

**Qué controla.** Listado de cotizaciones, ETS y certificados visibles, más descarga de PDF autenticado.

**Validaciones existentes.** Certificado requiere `client_visible` y PDF autenticado.

**Observaciones históricas.** ⚠ Parcialmente resuelta — Backend registrado. ❌ Sigue pendiente — No hay UI visible ni autenticación/tenant del cliente. ❌ Sigue pendiente — Las listas devuelven datos globales filtrados sólo por estado, no por identidad del cliente.

**Pendientes actuales.** Aislamiento por cliente, permisos y experiencia de portal, o retirar el router de la versión 1.0.

**Riesgos.** Crítico: exposición transversal de información comercial y operativa.

### 4.27 APIs — EN DESARROLLO

**Qué controla.** Contratos HTTP de todos los dominios.

**Validaciones existentes.** Pydantic, HTTPException, permisos en certificados/facturación/documentos/patrones/usuarios y OpenAPI.

**Observaciones históricas.** ✅ Resuelta — Separación router/servicio en la mayoría de dominios. ❌ Sigue pendiente — Inconsistencia de auth: routers abiertos completos y endpoints opcionales. ❌ Sigue pendiente — Duplicación extrema en router ETS. ⚠ Parcialmente resuelta — Endpoints legacy conviven con estados normalizados.

**Pendientes actuales.** Política deny-by-default, matriz ruta-permiso, pruebas 401/403 y limpieza ETS/legacy.

**Riesgos.** Superficie de ataque amplia y contratos contradictorios.

### 4.28 Componentes reutilizables y UX — EN DESARROLLO

**Qué controla.** Layout, marca, confirmaciones, agrupaciones OT, acciones de selección, firmas, hojas, diseñador y workbench.

**Validaciones existentes.** Build, componentes comunes, responsive CSS, accesibilidad parcial por roles/labels y modales propios.

**Observaciones históricas.** ✅ Resuelta — Liquid Glass consistente en áreas principales. ✅ Resuelta — `ConfirmDialog`, `WorkOrderFlowGroups`, firma y workbench reutilizables. ⚠ Parcialmente resuelta — `ServiceOrdersPage` 4,579 líneas, `QuotationsPage` 2,870 y `ClientsPage` 1,553. ❌ Sigue pendiente — `ServiceOrderSignatureMorph.jsx` conserva `window.alert`. ❌ Sigue pendiente — Existen dos implementaciones de modal/workbench y labs no productivos. ⚠ Parcialmente resuelta — Bundle principal 852.38 kB.

**Pendientes actuales.** Eliminar alerta nativa, consolidar duplicados productivo/lab, dividir páginas monolíticas y aplicar code splitting sin alterar UX.

**Riesgos.** Regresiones visuales, tiempos de carga y cambios difíciles de aislar.

### 4.29 Toolkit y scripts — EN DESARROLLO

**Qué controla.** Desarrollo local/túnel, build, estado, doctor, backup/restore, migraciones, reset, SAT, seed, git y limpieza.

**Validaciones existentes.** Reset destructivo único con frase, backup validado, root portátil, helpers de DB y comandos CLI.

**Observaciones históricas.** ✅ Resuelta — Rutas absolutas principales corregidas. ✅ Resuelta — Build ya no migra. ✅ Resuelta — Reset reutiliza un único flujo. ✅ Resuelta — Backup elimina archivos incompletos. ❌ Sigue pendiente — `doctor.sh::check` sólo ejecuta `$2`, descarta los demás argumentos y por ello reporta falsos negativos. ❌ Sigue pendiente — Puerto frontend default `5173` contradice operación documentada frecuente en `5174`. ⚠ Parcialmente resuelta — No hay pruebas automatizadas Bash ni CI.

**Pendientes actuales.** Corregir Doctor, unificar puerto, probar comandos no destructivos y validar tunnel/status/stop.

**Riesgos.** Diagnósticos engañosos, procesos en puerto equivocado y errores operativos durante mantenimiento.

### 4.30 Infraestructura — EN DESARROLLO

**Qué controla.** FastAPI/Uvicorn, React/Vite, PostgreSQL, storage local y scripts de túnel.

**Validaciones existentes.** Backend importable, DB accesible, build correcto, CORS explícito y health endpoint.

**Observaciones históricas.** ✅ Resuelta — Entorno local funcional. ⚠ Parcialmente resuelta — CORS en `main.py` duplica valores en vez de usar `settings.cors_origins`. ⚠ Parcialmente resuelta — Storage es local. ❌ Sigue pendiente — No se encontró CI, pruebas de despliegue, observabilidad central ni verificación actual de túnel/dominios.

**Pendientes actuales.** Configuración única de CORS/puertos, pipeline de validación y prueba de despliegue 1.0.

**Riesgos.** Diferencias local/producción y pérdida o inaccesibilidad de archivos.

### 4.31 Seguridad — EN DESARROLLO

**Qué controla.** Identidad, roles, permisos, endpoints, secretos, archivos y auditoría.

**Validaciones existentes.** Hash de contraseña, JWT firmado, usuarios activos, permisos en dominios sensibles, saneamiento de errores PAC y rutas de storage normalizadas.

**Observaciones históricas.** ✅ Resuelta — Facturación, certificados, documentos, patrones y usuarios aplican permisos. ❌ Sigue pendiente — Registro permite role injection. ❌ Sigue pendiente — Refresh usable como access. ❌ Sigue pendiente — Routers de Clientes, Cotizaciones, Equipos, Catálogo MYC, Plantillas de cotización y Motores operativos abiertos. ❌ Sigue pendiente — Portal cliente sin aislamiento. ⚠ Parcialmente resuelta — Rutas de laboratorio evitan sesión. ⚠ Parcialmente resuelta — Default JWT inseguro.

**Pendientes actuales.** Los cinco cierres P0: registro, tipos JWT, deny-by-default, portal/tenant y secreto de producción; pruebas 401/403 por router.

**Riesgos.** Críticos y bloqueantes para cualquier exposición pública.

### 4.32 Base de datos y migraciones — CASI SELLADO

**Qué controla.** Persistencia PostgreSQL con SQLAlchemy y evolución Alembic.

**Validaciones existentes.** 55 tablas, un head, `alembic current=head`, FKs, índices, soft delete en entidades operativas y SAT cargado.

**Observaciones históricas.** ✅ Resuelta — Cadena lineal y base alineada. ✅ Resuelta — Snapshots de cotización, hoja, factura y Master. ✅ Resuelta — Auditoría y versiones documentales/PDF. ⚠ Parcialmente resuelta — Dos migraciones consecutivas se llaman `add_service_order_signatures` más una correctiva; la cadena funciona pero refleja deuda. ⚠ Parcialmente resuelta — Columnas legacy confirmadas: `clients.city`; `service_orders.work_order_number`; campos de firma directos en `service_orders` conviven con ciclos. ⚠ Parcialmente resuelta — `InvoiceSettings` mantiene varios catálogos JSON mientras SAT ya está normalizado. ⚠ Parcialmente resuelta — Modelos documentales/metrológicos tienen 0 datos y su uso real no puede inferirse de conteos. No se encontró una migración pendiente.

**Tablas obsoletas.** No se puede declarar ninguna tabla físicamente obsoleta sólo por estar vacía. `document_templates` es una plantilla comercial legacy aún usada; los motores documentales/metrológicos están ocultos, no demostrablemente obsoletos.

**Columnas sin uso.** Se confirman como legacy por comentarios/código `clients.city` y `service_orders.work_order_number`. Las firmas directas de `service_orders` aún son leídas por compatibilidad y no pueden eliminarse sin migración de datos.

**Modelos duplicados.** No hay dos clases ORM para una misma tabla, pero sí duplicación conceptual: firma directa + ciclo de firmas; OT principal legacy + `service_work_orders`; catálogos fiscales JSON + SAT normalizado.

**Pendientes actuales.** Plan de retiro legacy con telemetría/consultas, constraints de integridad donde falten, comparación automática metadata↔DB y prueba de upgrade desde backup.

**Riesgos.** Ambigüedad de fuente de verdad y mantenimiento creciente.

### 4.33 Encuestas y reporte final — NO INICIADO

**Qué controla.** Sólo se describe en especificaciones y `flujo-general.md`.

**Validaciones existentes.** Ninguna.

**Observaciones históricas.** ❌ Sigue pendiente — No hay modelo, API, UI o automatización.

**Pendientes actuales.** Implementar si forma parte de 1.0 o retirarlo formalmente del alcance.

**Riesgos.** El cierre comercial acordado queda incompleto.

## 5. Auditorías especiales consolidadas

### ETS

| Tema | Resultado |
| --- | --- |
| Estados | ⚠ Parcialmente resuelta — Máquina de estados existe; conviven nomenclaturas legacy y acciones sin permisos. |
| Flujo completo | ⚠ Parcialmente resuelta — Implementado por etapas; no demostrado E2E con datos actuales. |
| OT | ✅ Resuelta — Generación por bloques de 10 y PDFs; ⚠ Parcialmente resuelta — número principal legacy. |
| Equipos | ✅ Resuelta — Cupos, estados y snapshots; ❌ Sigue pendiente — API abierta. |
| Firmas | ✅ Resuelta — Ciclos y asignación a nuevas OT; ❌ Sigue pendiente — ruta duplicada y acción con usuario opcional. |
| Excepciones | ⚠ Parcialmente resuelta — Acción auditada/comentario; no entidad o bandeja formal. |
| Agrupaciones | ✅ Resuelta — Componente compartido por OT. |
| Documentos | ✅ Resuelta — PDF OT, paquetes y Masters; ⚠ Parcialmente resuelta — E2E elegible pendiente. |

### Hojas de Campo

| Tema | Resultado |
| --- | --- |
| Plantillas | ✅ Resuelta — 23 definiciones; ⚠ Parcialmente resuelta — semánticas de seis familias/casos sin aprobación final. |
| Captura | ✅ Resuelta — Persistente; ⚠ Parcialmente resuelta — automatizaciones ausentes. |
| Snapshots | ✅ Resuelta — Definición e identidad congeladas. |
| PDFs | ⚠ Parcialmente resuelta — Operativos con Jinja, no renderer React exacto. |
| Firmas | ⚠ Parcialmente resuelta — Modelo/renderer; flujo gráfico operativo no demostrado. |
| Agrupación OT | ✅ Resuelta — Relación y agrupadores. |
| Generación automática | ❌ Sigue pendiente — No existe para cálculos, tolerancias, incertidumbre o patrones. |

### Calidad y Certificados

- Calidad **no es el único autenticador**: ETS contiene acciones individuales y masivas.
- Sí existen acciones duplicadas de revisión/autenticación entre `QualityPage.jsx` y `ServiceOrdersPage.jsx`.
- Certificados sí filtra la pantalla a elementos con PDF autenticado y estado autenticado/liberado.
- La liberación sí exige autenticación, match y pago cuando aplica.
- El flujo acordado está implementado en backend, pero no puede considerarse cerrado mientras la autenticación permanezca duplicada.

### Facturación

- Mesa de trabajo y vista Factura comparten `InvoiceWorkbenchDialog`; existen componentes de laboratorio/legacy adicionales no usados por la página productiva.
- El borrador se persiste sólo con Guardar; no hay autosave ni advertencia de cambios al cerrar.
- Facturama implementa salud, emisión Sandbox, traza, bloqueo de reemisión ambigua, conciliación y recuperación XML/PDF.
- Producción, cancelación/sustitución y complementos PPD no están implementados.
- PDF institucional MYC y XML fiscal están expuestos con nombres públicos estables; los documentos técnicos del PAC están ocultos en la UX ordinaria.
- La nomenclatura SAT del PDF se resuelve desde la versión activa.
- Las pestañas Pagos, CxC, Notas, Documentos e Historial dentro del expediente son placeholders, aunque existan capacidades globales/backend.

### Control Documental

- Lista maestra, ficha, historial, versiones y publicación están implementados.
- El diseñador está deshabilitado y rotulado “Próximamente”, tal como se acordó para V1.
- La consistencia visual usa los patrones compartidos del ERP.
- El alcance V1 puede conservar su sello; Plantillas Maestras queda casi sellado por el E2E pendiente en Captura.

### Seguridad

| Prioridad | Hallazgo | Evidencia |
| --- | --- | --- |
| P0 | Escalación en registro | `UserRegister.role_names` llega a `register_user` sin autorización. |
| P0 | Refresh válido como bearer | `get_current_user` sólo decodifica `sub`; no rechaza `token_type=refresh`. |
| P0 | APIs operativas abiertas | Routers de clientes, cotizaciones, equipos, catálogo y motores sin dependencia de auth. |
| P0 | Portal sin tenant | Listas globales por estado, sin usuario/cliente actual. |
| P0 | Secreto JWT de fallback | `secret_key = "change-this-secret-key"`. |
| P1 | Autorización visual ausente | Navegación no se filtra por permisos. |
| P1 | Labs sin sesión | Hojas y otros labs tienen bypass intencional en `App.jsx`. |

### Base de datos

- **Migraciones pendientes:** ninguna detectada; current y head son `fd5e6f7a8b9c`.
- **Heads múltiples:** no; existe uno.
- **Tablas obsoletas:** ninguna declarable con evidencia suficiente.
- **Columnas legacy:** `clients.city`, `service_orders.work_order_number`, firma directa del ETS.
- **Duplicaciones conceptuales:** OT legacy/nueva, firma directa/ciclos, settings SAT JSON/catálogos SAT.
- **Inconsistencias:** documentación histórica conserva conteos/dictámenes superados; la base actual tiene 0 entidades operativas principales y no demuestra E2E.

## 6. Lista consolidada de pendientes reales

### P0 — bloquean exposición y versión 1.0

1. Corregir registro público con roles y separar tipos access/refresh.
2. Aplicar autenticación/permisos deny-by-default a todos los routers operativos.
3. Aislar o retirar `client_portal` hasta tener identidad de cliente.
4. Exigir secreto JWT seguro fuera de desarrollo.
5. Eliminar lógica duplicada y ruta repetida de `routers/service_orders.py`.
6. Dejar a Calidad como único autenticador y retirar acciones duplicadas de ETS.

### P1 — cierran el flujo operativo principal

7. Ejecutar E2E Cliente → Cotización → ETS multi-OT → Hojas → Captura → Calidad → Certificado → Facturación/liberación.
8. Resolver pendientes funcionales documentados de Hojas de Campo y su renderer PDF.
9. Completar Captura con caso elegible real y bandeja de archivos no identificados.
10. Cerrar restauración completa de snapshots de Cotización o acotar formalmente su promesa.
11. Completar persistencia segura del borrador de Facturación y sus pestañas de expediente.
12. Completar Facturama requerido para 1.0: Producción, cancelación/sustitución, PPD/complementos e historial de excepciones.
13. Corregir `scripts/myc doctor` y unificar puerto frontend.

### P2 — cierran dominios parciales comprometidos

14. Decidir e implementar/absorber formalmente Agenda, Llamados y Contactos.
15. Cerrar Patrones/Procedimientos/selección e integración de Incertidumbre.
16. Completar Configuración institucional/parámetros y política de roles.
17. Definir el módulo oficial del Catálogo MYC y protegerlo.
18. Implementar Google Drive si continúa dentro del alcance 1.0.
19. Decidir CRM/Leads y Encuestas/Reporte final para 1.0.
20. Añadir pruebas frontend, 401/403 por router, scripts y E2E.

## 7. Módulos SELLADOS

Sólo puede considerarse **SELLADO**:

- **Control Documental V1**, limitado al alcance expresamente congelado de lista maestra, ficha, versiones, historial, publicación, obsolescencia y diseñador deshabilitado.

No se incluye Plantillas Maestras en el sello porque su consumo E2E desde Captura sigue pendiente. Tampoco se conserva el sello histórico de Equipos porque su router actual está abierto y no cumple el cierre de seguridad.

## 8. Orden recomendado hasta versión estable 1.0

1. **Cierre de seguridad y API:** registro, tokens, secreto, portal, permisos y pruebas 401/403.
2. **Saneamiento ETS/Calidad:** quitar duplicación de router/servicio, ruta repetida y autenticación fuera de Calidad.
3. **E2E operativo mínimo:** crear datos controlados y recorrer Cotización → ETS multi-OT → equipos/firmas → hojas → Captura → Calidad → Certificados.
4. **Cierre de Hojas de Campo y Captura:** semánticas aprobadas, renderer, cálculos acordados, filtros, aprobación/rechazo y paquetes reales.
5. **Cierre fiscal:** persistencia de borrador, expediente completo, Facturama Producción/cancelación/PPD, excepciones y E2E fiscal.
6. **Cierre metrológico:** Patrones, Procedimientos, perfiles, selección e Incertidumbre integrados o formalmente fuera de 1.0.
7. **Cierre administrativo:** configuración institucional, roles/permisos, Catálogo MYC y auditoría completa.
8. **Definición de alcance faltante:** Agenda, Llamados, Contactos, CRM/Leads, Google Drive y Encuestas/Reporte; implementar o retirar explícitamente de 1.0.
9. **Operación estable:** reparar Toolkit, CI, code splitting, pruebas frontend/E2E, upgrade desde backup y smoke test de despliegue.

## 9. Dictamen final

El ERP MYC tiene una implementación sustancial y coherente en varios flujos, pero su madurez real es **pre-1.0**. Las pruebas verdes y el head de Alembic alineado son señales positivas, no evidencia de cierre integral. La prioridad inmediata no es agregar módulos: es cerrar autorización, eliminar duplicaciones del ETS, restablecer la segregación de Calidad y demostrar el flujo completo con datos reales controlados.
