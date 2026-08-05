> Estado: VIGENTE
>
> Tipo: Vigente (canónico)
>
> Autoridad: Máxima para determinar el avance actual del ERP
>
> Prevalece sobre: auditorías fechadas, cierres técnicos, bitácoras, especificaciones V2/V3 y cualquier declaración histórica de avance o sellado
>
> Corte verificado: 2026-08-05 — administración de usuarios y accesos del Portal terminada técnicamente y en revisión funcional

# Estado actual del ERP MYC

Este documento contiene sólo el estado vigente. Es la única fuente documental autorizada para responder qué módulos están sellados, casi sellados, en desarrollo, pendientes o no iniciados. La evidencia detallada del corte está en [`../audits/AUDITORIA_INTEGRAL_AVANCE_ERP_MYC_2026-07-21.md`](../audits/AUDITORIA_INTEGRAL_AVANCE_ERP_MYC_2026-07-21.md).

## Resumen

| Estado | Módulos o capacidades |
| --- | --- |
| **SELLADO** | Control Documental V1 |
| **CASI SELLADO** | Dashboard; Clientes; Cotizaciones; Órdenes de Trabajo; Equipos; Certificados; Plantillas Maestras de Certificado; Catálogos SAT; Base de datos y migraciones |
| **EN DESARROLLO** | Motor de Resoluciones (Fases 0–13 aprobadas; Fase 14 `EN REVISIÓN`); Actividad/Notificaciones/Communications; Autenticación; ETS/Servicios; Hojas de Campo; Captura; Calidad; Facturación; Pagos y notas de crédito; Patrones/certificados de patrón/procedimientos; Perfiles técnicos/metrología/selección de patrones/incertidumbre; Administración/Usuarios/Roles/Configuración/Auditoría; Integraciones; Portal de cliente; APIs; Componentes reutilizables y UX; Toolkit/scripts; Infraestructura; Seguridad |
| **PENDIENTE** | Contactos como dominio autónomo; Agenda; Llamados; Catálogo MYC |
| **NO INICIADO** | CRM/Leads; Google Drive; Encuestas y reporte final |

## Módulos sellados

### Control Documental V1

El alcance V1 sellado comprende Lista Maestra, ficha documental, versiones, historial derivado, publicación/activación, obsolescencia y la integración de Plantillas Maestras. El diseñador permanece deshabilitado por decisión expresa y no forma parte del cierre V1. No hay pendientes funcionales o de UX dentro de ese alcance congelado.

## Módulos casi sellados

| Módulo | Pendiente real de cierre |
| --- | --- |
| Dashboard | La visibilidad por permisos está aplicada; falta E2E browser autenticado con datos representativos. |
| Clientes | Las rutas y acciones principales están protegidas; falta ejecutar el ciclo E2E browser por rol. |
| Cotizaciones | Servicios Compuestos conservan un concepto comercial y expanden el ETS. El desbloqueo controlado permite editar directamente partidas de una aprobada, compara revisiones y reconstruye físicamente un ETS virgen con el mismo folio; incluye tipos acreditado/trazable/vinculado, empresas, snapshots y pruebas. Falta completar restauración general desde snapshots, asegurar rutas legacy y ejecutar E2E autenticado en navegador hasta ETS. |
| Órdenes de Trabajo | E2E multi-OT por rol y encapsulado del número legacy. |
| Equipos | La independencia del catálogo vivo, snapshot y protección del router quedaron validados; falta E2E autenticado dentro del ciclo multi-OT. |
| Certificados | Aprobación→autenticación→liberación sin compuerta legacy de match quedó validada; falta retirar la superficie autenticadora duplicada de ETS y completar E2E de verificación pública. |
| Plantillas Maestras | Descarga, carga, identificación, detección semántica por fingerprint, readiness y generación del PDF autenticado desde el Master quedaron validados; falta automatizar el E2E autenticado completo del retorno. |
| Catálogos SAT | Blindar la fuente oficial y completar E2E de consumidores autorizados. |
| Base de datos y migraciones | Integridad, drift, downgrade, upgrade histórico, respaldo y restore están validados; sólo permanece el plan independiente de retiro legacy. |

## Módulos en desarrollo

El Portal del Cliente completó identidad externa, registro/verificación,
invitaciones, membresías, roles propios, aislamiento por cliente, administración
interna unificada en Ajustes y Clientes, bandejas de registro/vinculación,
configuración por cliente y la sección Usuarios autogestionada por permisos del
portal. La entrega **AJUSTES → USUARIOS Y ACCESOS DEL PORTAL** está
**TERMINADA — EN REVISIÓN**;
permanece en el estado canónico `EN DESARROLLO` hasta la revisión funcional y la
conexión del correo productivo, sin declarar aptitud de producción.

Las brechas que impiden su cierre están consolidadas en [`TECHNICAL_DEBT.md`](TECHNICAL_DEBT.md) y [`OBSERVATIONS_REGISTER.md`](OBSERVATIONS_REGISTER.md). Los bloqueos principales son:

El Motor de Resoluciones tiene aprobadas las Fases 0 a 9. El primer y único
vertical de la Fase 9, `certificate.resolve_incorrect_release`, quedó aprobado
mediante `5abfe2d` y `901bd85`. Además de fundación, persistencia, seguridad,
Lifecycle y ejecución, existe compensación total/parcial síncrona de efectos
confirmados declarados reversibles. Plan, autorización, ejecución original,
checkpoints y resultado quedan vinculados y reconstruibles; Lifecycle conserva
la autoridad, la pérdida de lock bloquea sin repetir y todo replay exige actor,
clave y hash exactos. No existen gateways concretos, API, workers, schedulers,
recuperación, conciliación, retries ni compensación automática. Auditoría y
Evidencia reconstruye el expediente completo mediante un adaptador read-only,
abre un snapshot transaccional consistente, verifica hashes, secuencia y
vínculos, exige autorización exacta y produce timeline/reporte deterministas
sin mezclar confirmaciones concurrentes. Seguridad integral añade un catálogo
canónico de controles y exige evidencia exacta en Lifecycle, ejecución,
compensación, consultas y outbox antes de leer replays o producir efectos. Las
mutaciones consumen una operación canónica única; creación recupera el mismo
resultado al repetir la intención, Lifecycle queda ligado a estado/versión y
outbox congela un lote. Auditoría sólo reutiliza la misma consulta read-only.
La integración conserva ownership: un provider read-only obtiene hechos y los
gateways delegan en el servicio canónico de Certificados, que retira sólo la
visibilidad futura y conserva la liberación histórica. La operación y su
compensación son transaccionales, idempotentes y append-only. Las observaciones
bloqueantes de replay dependiente del estado y snapshot previo al flush están
corregidas y aprobadas. Fase 10 — SDK y API Pública está implementada mediante
contratos v1 desacoplados, credenciales por consumidor/organización, creación
por Lifecycle, consultas por auditoría, replay/cursor seguros, SDK HTTP y
portal técnico. El cursor `c1` cifra y autentica toda la consulta, rechaza
cambios de identidad/filtros/orden/versión y no revela la posición interna.
La Fase 10 está aprobada mediante `dd9a84e` y la Fase 11 mediante `cbde517`.
Fase 12 añade el Centro de Resoluciones como módulo principal: lista keyset,
expediente/timeline, catálogo guiado, contexto, análisis, plan, simulación,
autorización, revalidación y aceptación durable. El worker independiente
continúa por la cola de Fase 11 aunque termine la sesión web. La API interna no
modifica la API pública ni el SDK. Fase 12 quedó `APROBADA` mediante `a7bf75f`.
Fase 13 consolida metadata institucional, formularios dinámicos, indicadores,
expediente y el vertical Certificados end-to-end; fue aprobada mediante
`bb76e3b`. Fase 14 instala la composición institucional única y el vertical
`service_order.resolve_additional_equipment@1.0`; está `TERMINADA` y queda
`EN REVISIÓN`. La IA
permanece como posibilidad futura opcional no autorizada.

1. La Contención de Seguridad Etapa 1 quedó **APROBADA Y CERRADA**:
   deny-by-default, JWT productivo seguro, clasificación 306/306 y portal
   aislado. PortalMembership, RBAC administrable, revocación/rotación,
   `localStorage`, rate limit, MFA y E2E browser exhaustivo por rol pertenecen
   a etapas posteriores y no reabren este cierre.
2. Duplicación de lógica y acciones en ETS, Calidad y certificados.
3. Hojas de Campo sin cierre semántico, automatizaciones metrológicas y E2E de las 23 plantillas.
4. Facturación ya integra en el Workbench único el registro e historial de pagos, comprobante PDF, saldos/estado en tiempo real, cartera y refresco del readiness financiero del ETS. Permanecen el borrador no autosalvado, notas/documentos internos y el flujo fiscal incompleto para Producción, cancelaciones, PPD y notas fiscales.
5. Administración y roles sin gestión dinámica; el filtrado visual por
   permisos efectivos ya está aplicado en navegación y acciones principales.
   La siguiente etapa de autoridad deberá implementar el diseño obligatorio
   de múltiples roles/grupos, overrides, alcances, temporalidad y protecciones
   críticas, usando el catálogo institucional funcional sólo después de su
   aprobación y de una matriz explícita de compatibilidad.
6. Toolkit, infraestructura y UX con diagnósticos, puertos, pruebas de despliegue, páginas monolíticas y bundle pendientes.
7. Actividad transversal está implementada con permisos, entidad genérica,
   atención, no leídos, adjuntos y eventos; permanece en desarrollo hasta
   completar navegación directa a cada registro y revisión formal del cierre.
8. Etapa 2A y 2B están técnicamente terminadas y cerradas: persistencia
   converge en `f27f8a90b1c3` con recuperación reproducible. La validación
   funcional previa a ETAPA 3 revisó 36/213/798 del snapshot y produjo la
   autoridad aprobada y congelada de 42 módulos, 181 acciones y 657
   microacciones. La aprobación no implementa RBAC ni modifica permisos.

## Módulos pendientes o no iniciados

- **Contactos, Agenda y Llamados:** existen piezas absorbidas por Cliente o ETS, pero no los módulos autónomos acordados. Se requiere decisión formal de absorción o implementación.
- **Catálogo MYC:** el editor embebido ya administra Servicios Simples/Compuestos mediante relación normalizada y expansión ETS; sus endpoints exigen permisos, pero sigue pendiente una experiencia independiente cerrada.
- **CRM/Leads, Encuestas y reporte final:** no se encontró implementación funcional.
- **Google Drive:** no existe integración.

## Deuda técnica vigente prioritaria

| Prioridad | Deuda |
| --- | --- |
| P1 | Completar seguridad de sesión fuera de la Etapa 1: rotación/revocación, almacenamiento de tokens, rate limit, MFA y E2E browser por rol. |
| P0 | Eliminar lógica duplicada y ruta `confirm-signatures` repetida en ETS. |
| P0 | Dejar a Calidad como único autenticador de certificados. |
| P1 | Cerrar Hojas de Campo/Captura y su E2E operativo. |
| P1 | Completar la persistencia y el flujo fiscal de Facturación. |
| P1 | Diseñar e implementar en una etapa separada PortalMembership persistente y RBAC administrable; `permissions.py` permanece bootstrap temporal y el catálogo funcional validado requiere aprobación y matriz de compatibilidad previa. |
| P2 | Retirar compatibilidad legacy verificada y reducir deuda de UX, bundle, scripts e infraestructura. |

## Infraestructura transversal — Archivos y cargas

**Estado de etapa:** `CASI SELLADO` — ETAPA 3 terminada técnicamente y en
revisión. Los flujos vigentes conservan estados, permisos y ownership; las
cargas críticas integradas usan perfiles centrales, los ZIP se inspeccionan
con límites, las publicaciones son atómicas y los artefactos operativos fueron
retirados del índice sin eliminar evidencia local. El cierre formal y la
evidencia están en
[`../closures/STAGE_3_FILES_AND_UPLOADS_2026-08-04.md`](../closures/STAGE_3_FILES_AND_UPLOADS_2026-08-04.md).

Pendientes fuera del cierre técnico: antivirus/proveedor de cuarentena,
almacenamiento durable remoto y streaming de paquetes de salida de gran
volumen; requieren decisión operativa y etapa propia.

## Regla de mantenimiento

Toda auditoría posterior debe actualizar este archivo sólo con conclusiones verificadas. Las auditorías conservan la evidencia y la fecha del corte, pero dejan de ser autoridad de avance en cuanto este documento incorpora un corte posterior.
