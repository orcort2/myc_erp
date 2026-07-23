> Estado: VIGENTE
>
> Tipo: Vigente (canónico)
>
> Autoridad: Alta para el seguimiento de observaciones funcionales y UX
>
> Prevalece sobre: listas de pendientes en auditorías, cierres, bitácoras y documentos archivados
>
> Corte verificado: 2026-07-22

# Registro consolidado de observaciones

Estados permitidos: `pendiente`, `parcial`, `resuelta`. Una observación resuelta se conserva para impedir que vuelva a presentarse como nueva. El estado del módulo se consulta exclusivamente en [`PROJECT_STATUS.md`](PROJECT_STATUS.md).

## Observaciones abiertas

| ID | Módulo | Descripción | Estado | Documento origen |
| --- | --- | --- | --- | --- |
| OBS-001 | Autenticación | El registro público permite solicitar `role_names`; debe impedir escalación de privilegios. | pendiente | Auditoría integral 2026-07-21 |
| OBS-002 | Autenticación | Un refresh JWT puede aceptarse como bearer porque no se exige `token_type=access`. | pendiente | Auditoría integral 2026-07-21 |
| OBS-003 | Autenticación | Tokens en `localStorage` mantienen exposición frente a XSS y no existe cierre demostrado de revocación/cambio de contraseña. | parcial | Auditoría integral 2026-07-21 |
| OBS-004 | Dashboard | La navegación y accesos no se filtran por capacidades del usuario. | parcial | Auditoría integral 2026-07-21 |
| OBS-005 | Clientes | Rutas de lectura, alta, edición, importación, exportación, constancia y perfiles no aplican autorización uniforme. | pendiente | Auditoría integral 2026-07-21 |
| OBS-006 | Clientes | `city` y `legal_name` conservan compatibilidad legacy. | parcial | Cierre técnico Clientes; auditoría integral 2026-07-21 |
| OBS-007 | Contactos | Falta decisión formal: quedar absorbido por Clientes o existir como módulo autónomo. | pendiente | Especificación V2; auditoría integral 2026-07-21 |
| OBS-008 | Cotizaciones | Restaurar un snapshot no recupera las partidas aunque el snapshot las conserva. | parcial | Auditoría integral 2026-07-21 |
| OBS-009 | Cotizaciones | CRUD, estados y PDF no aplican autenticación/permisos de manera uniforme. | pendiente | Auditoría integral 2026-07-21 |
| OBS-010 | Agenda | No existe entidad, calendario, folio, estados, reprogramación ni recordatorios; sólo fecha dentro de ETS. | pendiente | Flujo histórico; auditoría integral 2026-07-21 |
| OBS-011 | Llamados | No existe entidad, folio, bitácora ni captura de resultado; sólo hito dentro de ETS. | pendiente | Flujo histórico; auditoría integral 2026-07-21 |
| OBS-012 | ETS | El router duplica materialmente la lógica del servicio y declara dos veces `confirm-signatures`. | pendiente | Auditoría integral 2026-07-21 |
| OBS-013 | ETS | CRUD/transiciones principales y firmas no aplican autorización/actor obligatorio de manera uniforme. | pendiente | Auditoría integral 2026-07-21 |
| OBS-014 | ETS | Las excepciones existen como acción/comentario, no como agregado persistente especializado. | parcial | Cierre ETS; auditoría integral 2026-07-21 |
| OBS-015 | ETS/UX | `ServiceOrdersPage.jsx` concentra miles de líneas y múltiples dominios. | parcial | Auditoría integral 2026-07-21 |
| OBS-016 | OT | `service_orders.work_order_number` convive con `service_work_orders`; falta validar y encapsular compatibilidad. | parcial | Cierre ETS; auditoría integral 2026-07-21 |
| OBS-017 | Equipos | El router carece de protección uniforme y la vista autónoma no es la experiencia vigente principal. | pendiente | Auditoría integral 2026-07-21 |
| OBS-018 | Hojas de Campo | El PDF backend usa Jinja y no exactamente el renderer React de captura/laboratorio. | parcial | Integración operativa y auditoría integral 2026-07-21 |
| OBS-019 | Hojas de Campo | No se cerraron semánticas de General, Presión, Báscula/Balanza, Eléctrica, Reglas y Verificación. | pendiente | Análisis de originales; implementación laboratorio; auditoría integral 2026-07-21 |
| OBS-020 | Hojas de Campo | Cálculos, tolerancias, promedios, conversiones, incertidumbre, cumplimiento y patrón automático no están conectados al flujo. | pendiente | Análisis de originales; auditoría integral 2026-07-21 |
| OBS-021 | Hojas de Campo | Faltan aprobación/rechazo propios de la hoja, filtros globales y acceso directo completo a captura. | pendiente | Estado de integración; auditoría integral 2026-07-21 |
| OBS-022 | Hojas de Campo | Falta E2E autenticado de las 23 plantillas, firmas gráficas, snapshots y PDF operativo. | pendiente | Estado de integración; `PROJECT_STATUS.md` previo; auditoría integral 2026-07-21 |
| OBS-023 | Captura | Descarga, carga/identificación, servicio por fingerprint y envío XLSX→Calidad quedaron verificados; permanece pendiente una bandeja formal para archivos genuinamente no identificados y cobertura HTTP/browser automatizada. | parcial | Auditoría Paquete de Captura 2026-07-17; diagnósticos del equipo 1 del 2026-07-21 |
| OBS-024 | Calidad | Autenticación y acciones de Calidad están duplicadas en ETS; Calidad aún no es la única superficie autenticadora. | pendiente | Auditoría integral 2026-07-21 |
| OBS-025 | Certificados | Aprobación→autenticación y liberación individual/masiva con `match_status=pending` quedaron validadas por servicio y HTTP; falta completar el E2E hasta verificación pública con datos actuales. | parcial | Auditoría integral y correcciones Calidad→Autenticación→Liberación 2026-07-21 |
| OBS-026 | Facturación | El borrador sólo persiste al guardar; cerrar el modal pierde el estado React sin advertencia/autosave. | parcial | Auditoría integral 2026-07-21 |
| OBS-027 | Facturación | Pagos, CxC, Notas, Documentos e Historial dentro del expediente son placeholders. | parcial | Auditorías de Facturación 2026-07-14/21 |
| OBS-028 | Facturación | Producción Facturama, cancelación/sustitución, complementos PPD y notas fiscales no están cerrados. | pendiente | Auditorías de Facturación 2026-07-14/21 |
| OBS-029 | Facturación | Falta experiencia visible especializada para excepciones/intentos/historial e impresión E2E actual. | parcial | Auditoría integral 2026-07-21 |
| OBS-030 | Catálogo MYC | No existe experiencia oficial independiente y sus endpoints están abiertos. | pendiente | Corte de verdad 2026-07-06; auditoría integral 2026-07-21 |
| OBS-031 | Catálogos SAT | APIs internas todavía admiten CSV/JSON y deben blindarse los roles consumidores/fuente oficial. | parcial | Arquitectura SAT; auditoría integral 2026-07-21 |
| OBS-032 | Patrones/Procedimientos | Falta validar renovación, vigencia y selección extremo a extremo; Procedimientos permanece oculto. | parcial | Auditoría integral 2026-07-21 |
| OBS-033 | Metrología/Incertidumbre | Los motores no están conectados como flujo vigente de Hojas de Campo y un router técnico está abierto. | pendiente | Auditoría integral 2026-07-21 |
| OBS-034 | Administración | Roles/permisos viven en código, no hay CRUD; Configuración institucional/parámetros y pruebas están incompletos. | pendiente | Auditoría integral 2026-07-21 |
| OBS-035 | Portal de cliente | No existe aislamiento por cliente ni UI; listados backend pueden devolver información global por estado. | pendiente | Auditoría integral 2026-07-21 |
| OBS-036 | APIs/Seguridad | No existe política deny-by-default ni matriz verificada ruta→permiso con pruebas 401/403. | pendiente | Auditoría integral 2026-07-21 |
| OBS-037 | UX | Persisten alerta nativa, workbench/modal duplicados, páginas monolíticas y bundle principal grande. | parcial | Auditoría integral 2026-07-21 |
| OBS-038 | Toolkit | `doctor.sh::check` ya conserva todos los argumentos y valida FastAPI/Alembic correctamente; permanece la contradicción entre el puerto 5173 configurado y el 5174 operativo frecuente. | parcial | Auditorías Toolkit y corrección LibreOffice 2026-07-21 |
| OBS-039 | Infraestructura | CORS está duplicado, storage es local y faltan CI, observabilidad y prueba de despliegue. | parcial | Auditoría integral 2026-07-21 |
| OBS-040 | Base de datos | Firmas directas/ciclos, OT legacy/nueva y catálogos fiscales JSON/SAT son duplicaciones conceptuales vigentes. | parcial | Auditoría integral 2026-07-21 |
| OBS-041 | Cierre comercial | CRM/Leads, Encuestas y reporte final no tienen implementación; falta confirmar su inclusión en 1.0. | pendiente | Especificación V2; auditoría integral 2026-07-21 |
| OBS-042 | Integraciones | Google Drive no existe y Facturama se limita a Sandbox. | pendiente | Auditoría integral 2026-07-21 |
| OBS-043 | ETS/Calidad/Certificados UX | Se implementaron y verificaron por estructura/build el orden de pestañas, el flujo vertical del aviso financiero, la presentación única `Pendiente de pago`/`Listo para liberar` y el estilo compartido de Autenticar. Falta únicamente la comprobación visual autenticada en varios anchos: la sesión local disponible sólo mostró Login y no existen credenciales de prueba documentadas. | parcial | Correcciones UX y consistencia de estados 2026-07-21 |
| OBS-044 | Calidad/UX | Navegación Anterior/Siguiente implementada con el patrón de Clientes, contexto OT→ETS→lista visible, carga protegida, reintento y refresco sin cerrar después de acciones. El recorrido unitario `1→2→3→2`, límites y build quedaron verificados; falta E2E autenticado porque la base actual no contiene certificados visibles en Calidad y el navegador local sólo presenta Login. | parcial | Navegación consecutiva de Calidad 2026-07-21 |
| OBS-045 | Excepciones transversales | La auditoría de 60 escenarios confirmó que la acción denominada excepción ETS ejecuta cambio de etapa y resincronización en la solicitud, sin estados independientes de aprobación y ejecución. También faltan excepciones coordinadas de alcance/firma/equipo, corrección de pago y liberación financiera; cancelación/sustitución CFDI deben permanecer como flujos fiscales propios y no como bypass genérico. | pendiente | `../auditorias/AUDITORIA_MATRIZ_EXCEPCIONES_ERP_MYC.md` 2026-07-22 |

## Observaciones resueltas que deben conservar trazabilidad

| ID | Módulo | Descripción resuelta | Estado | Documento origen |
| --- | --- | --- | --- | --- |
| OBS-R01 | Clientes | Modal fiscal reorganizado sin superposición; parser de constancia, importación y eliminación/archivo/restauración corregidos. | resuelta | `../archive/project/BACKUP_ESTADO_ACTUAL_HISTORICO_2026-07-21.md`; cierre técnico Clientes |
| OBS-R02 | Cotizaciones | Selector buscable, asesor automático, autosave, navegación ETS y correcciones del PDF institucional. | resuelta | Cierres Ventas 2026-07-07/08; auditoría integral |
| OBS-R03 | ETS/OT | Tablero por etapas, agrupación automática, máximo 10 equipos, firmas por ciclo y paquetes por OT. | resuelta | Cierres ETS 2026-07-08/10 |
| OBS-R04 | Equipos | Alta por cupo, modal, estados/OT y snapshot de Master. | resuelta | Cierres ETS y Plantillas Maestras |
| OBS-R05 | Hojas de Campo | Se incorporaron 23 plantillas, identidad institucional, snapshots persistentes y agrupación por OT. | resuelta | Implementaciones Hojas de Campo 2026-07-13 |
| OBS-R06 | Captura | Se corrigió `null.zip`, se interpreta multipart y se valida Master/snapshot. | resuelta | Auditoría Paquete de Captura; `../archive/project/BACKUP_ESTADO_ACTUAL_HISTORICO_2026-07-21.md` |
| OBS-R07 | Calidad | Revisión del Master, aprobación, autenticación posterior y retorno a Captura/Técnico existen; el matching legacy no es compuerta de autenticación. | resuelta | Auditoría integral y corrección Calidad→Autenticación 2026-07-21 |
| OBS-R08 | Certificados | La vista muestra sólo autenticados, conserva originales/versiones, aplica compuerta financiera y verificación pública. | resuelta | Auditoría integral 2026-07-21 |
| OBS-R09 | Facturación | Navegación ETS, PDF MYC, XML, nomenclaturas SAT, estructura/tipografía histórica, ocultamiento de internos e indicador Facturama. | resuelta | Auditorías Facturación 2026-07-14/21 |
| OBS-R10 | Control Documental | Lista Maestra, ficha, historial/versiones/publicación, visual Liquid Glass y diseñador deshabilitado quedan cerrados en V1. | resuelta | Cierres 2026-07-10; auditoría integral |
| OBS-R11 | Catálogos SAT | Fuente oficial, carga local versionada, búsqueda indexada y reutilización en Facturación implementadas. | resuelta | Arquitectura y reporte de carga SAT |
| OBS-R12 | Toolkit | Rutas principales portables, build sin migración, reset único y backup incompleto seguro. | resuelta | Auditoría Toolkit y actualizaciones 2026-07 |
| OBS-R13 | Captura | La elegibilidad dejó de bloquear hojas `under_review`/`approved`; el caso ETS 1, OT 7002 produjo `ready_total=1` y el ZIP con jerarquía ETS/OT/certificado. | resuelta | Diagnóstico y pruebas de Paquete de Captura 2026-07-21 |
| OBS-R14 | Captura | La carga ZIP ahora persiste con ruta única, inicia `capture_in_progress` con auditoría, ignora auxiliares macOS y refresca ETS, contadores, tarjetas y resumen visible sin recarga manual. | resuelta | Diagnóstico de carga de Captura 2026-07-21 |
| OBS-R15 | Captura/Calidad | Se retiró el PDF del flujo normal de Captura; readiness y envío dependen del Master XLSX identificado, warnings permiten continuar, diferencias bloquean y Calidad puede descargar/revisar/aprobar o regresar el XLSX. | resuelta | Corrección Captura→Calidad 2026-07-21 |
| OBS-R16 | Captura | `servicio` dejó de comparar la clave ERP contra una leyenda: clasifica `accredited`/`traceable` mediante el fingerprint estructural del snapshot Master registrado y conserva diagnóstico por indicadores. | resuelta | Corrección semántica de servicio 2026-07-21 |
| OBS-R17 | Captura/ETS | El botón permanecía bloqueado en ETS porque el frontend recalculaba readiness con un path de snapshot no expuesto por Equipos; ahora consume el readiness autoritativo del backend y lo refresca con los archivos de Captura. | resuelta | Diagnóstico de habilitación Captura→Calidad 2026-07-21 |
| OBS-R18 | Calidad/Certificados | “Autenticar” permanecía bloqueado porque Calidad y ETS exigían PDF/match en frontend y el servicio backend exigía un `final_pdf_path` cargado. Ahora basta la aprobación del Master; la acción genera y sella el PDF desde XLSX, conserva actor/fecha/auditoría/Master y refresca estados sin recarga. | resuelta | Corrección Calidad→Autenticación 2026-07-21 |
| OBS-R19 | Infraestructura/Calidad | El conversor sólo se resolvía desde un valor `soffice`/PATH y fallaba fuera del runtime que lo aportaba. Ahora acepta configuración explícita, PATH y rutas comunes de macOS/Windows/Linux; Doctor y startup informan ruta/versión, y un fallo no muta el certificado. | resuelta | Corrección multiplataforma de LibreOffice 2026-07-21 |
| OBS-R20 | Certificados/Liberación | Certificados autenticados con `match_status=pending` quedaban bloqueados en backend, Certificados y ETS. La liberación ahora exige sólo estado/archivo autenticado y compuerta financiera; la UI distingue Listo para liberar, Pendiente de pago y Liberado. | resuelta | Corrección de readiness documental 2026-07-21 |
| OBS-R21 | Facturación/Arquitectura | `BillingPage.jsx` era el único propietario de apertura, borrador, emisión, documentos y refresco, y la navegación contextual dependía de `localStorage`. El Sprint 1 extrajo un controlador único reutilizable, contexto explícito por factura/ETS y filtro opcional del listado existente, sin cambiar reglas ni UI. | resuelta | Sprint 1 del Workbench y arquitectura vigente 2026-07-21 |
| OBS-R22 | ETS/Facturación | El placeholder administrativo del ETS fue sustituido por un resumen contextual de `Invoice` que cubre ausencia, borrador, timbrada y cancelada; creación, edición, guardado, emisión, PDF y XML reutilizan el controlador y diálogo únicos del Sprint 1. | resuelta | Sprint 2A de Facturación contextual 2026-07-22 |
| OBS-R23 | ETS/Facturación UX | `contextInvoice=null` se interpretaba como “Sin factura” durante la ventana entre carga de dependencias y resolución contextual, y el bloque provisional tenía menor altura. Ahora `contextLoading/contextResolved` separan los tres estados, un bloque estable evita el salto y la pestaña permanece montada al alternar carpetas del mismo ETS. | resuelta | Corrección de parpadeo Sprint 2A 2026-07-22 |
| OBS-R24 | Catálogo/ETS/Certificados | El schema de respuesta sustituyó `accredited_iso_17025` por el texto documental `Certificado / Certificate: L25-313`, mientras la base conservó la clave canónica, causando HTTP 500 en `GET /api/catalog-items`. Se centralizaron las tres modalidades, se alinearon schemas/capacidad/frontend/datos y se añadió normalización defensiva. | resuelta | Corrección del contrato `calibration_scope` 2026-07-22 |
| OBS-R25 | Catálogo/Cotizaciones/ETS | Servicios Simples y Compuestos usan `service_kind` y una relación padre-hijo normalizada. La cotización conserva el padre único y la creación del ETS expande hojas, cantidades y OTs sin duplicar lógica downstream; autorreferencia, ciclos, mínimos y compatibilidad simple quedaron cubiertos por pruebas. | resuelta | Servicios Compuestos y arquitectura vigente 2026-07-22 |

## Regla de cierre

Una observación sólo pasa a `resuelta` con evidencia verificable y, si afecta el avance, con actualización simultánea de [`PROJECT_STATUS.md`](PROJECT_STATUS.md). Las observaciones de documentos archivados que no aparecen aquí no son pendientes vigentes.
