> Estado: VIGENTE
>
> Tipo: Vigente (canónico)
>
> Autoridad: Máxima para determinar el avance actual del ERP
>
> Prevalece sobre: auditorías fechadas, cierres técnicos, bitácoras, especificaciones V2/V3 y cualquier declaración histórica de avance o sellado
>
> Corte verificado: 2026-07-28

# Estado actual del ERP MYC

Este documento contiene sólo el estado vigente. Es la única fuente documental autorizada para responder qué módulos están sellados, casi sellados, en desarrollo, pendientes o no iniciados. La evidencia detallada del corte está en [`../audits/AUDITORIA_INTEGRAL_AVANCE_ERP_MYC_2026-07-21.md`](../audits/AUDITORIA_INTEGRAL_AVANCE_ERP_MYC_2026-07-21.md).

## Resumen

| Estado | Módulos o capacidades |
| --- | --- |
| **SELLADO** | Control Documental V1 |
| **CASI SELLADO** | Dashboard; Clientes; Cotizaciones; Órdenes de Trabajo; Equipos; Certificados; Plantillas Maestras de Certificado; Catálogos SAT; Base de datos y migraciones |
| **EN DESARROLLO** | Motor de Resoluciones (Fases 0–10 aprobadas; Fase 11 `EN REVISIÓN`); Autenticación; ETS/Servicios; Hojas de Campo; Captura; Calidad; Facturación; Pagos y notas de crédito; Patrones/certificados de patrón/procedimientos; Perfiles técnicos/metrología/selección de patrones/incertidumbre; Administración/Usuarios/Roles/Configuración/Auditoría; Integraciones; Portal de cliente; APIs; Componentes reutilizables y UX; Toolkit/scripts; Infraestructura; Seguridad |
| **PENDIENTE** | Contactos como dominio autónomo; Agenda; Llamados; Catálogo MYC |
| **NO INICIADO** | CRM/Leads; Google Drive; Encuestas y reporte final |

## Módulos sellados

### Control Documental V1

El alcance V1 sellado comprende Lista Maestra, ficha documental, versiones, historial derivado, publicación/activación, obsolescencia y la integración de Plantillas Maestras. El diseñador permanece deshabilitado por decisión expresa y no forma parte del cierre V1. No hay pendientes funcionales o de UX dentro de ese alcance congelado.

## Módulos casi sellados

| Módulo | Pendiente real de cierre |
| --- | --- |
| Dashboard | Visibilidad por permisos y E2E autenticado con datos representativos. |
| Clientes | Proteger todas las rutas y ejecutar el ciclo autenticado completo. |
| Cotizaciones | Servicios Compuestos ya conservan un concepto comercial y expanden el ETS con pruebas; falta completar restauración de partidas desde snapshots, asegurar rutas y ejecutar E2E autenticado hasta ETS. |
| Órdenes de Trabajo | E2E multi-OT, permisos y encapsulado del número legacy. |
| Equipos | La independencia del catálogo vivo y el snapshot operativo quedaron validados; falta proteger el router y completar el E2E autenticado dentro del ciclo multi-OT. |
| Certificados | Aprobación→autenticación→liberación sin compuerta legacy de match quedó validada; falta retirar la superficie autenticadora duplicada de ETS y completar E2E de verificación pública. |
| Plantillas Maestras | Descarga, carga, identificación, detección semántica por fingerprint, readiness y generación del PDF autenticado desde el Master quedaron validados; falta automatizar el E2E autenticado completo del retorno. |
| Catálogos SAT | Blindar la fuente oficial y validar permisos de todos los consumidores. |
| Base de datos y migraciones | Plan de retiro legacy, comparación metadata↔BD y prueba de upgrade desde respaldo. |

## Módulos en desarrollo

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
La Fase 10 está aprobada mediante `dd9a84e`. Fase 11 incorpora cola durable,
workers pull, coordinación multinodo, leases con fencing, exclusividad por
resolución, recuperación, retry determinista y eventos operativos append-only.
Un lease vencido antes del efecto puede reencolarse; después del posible efecto
queda bloqueado como incierto. La fase está `EN REVISIÓN`. Fase 12 e IA siguen
fuera de alcance.

1. Seguridad y autorización incompletas en registro, tokens, routers y portal de cliente.
2. Duplicación de lógica y acciones en ETS, Calidad y certificados.
3. Hojas de Campo sin cierre semántico, automatizaciones metrológicas y E2E de las 23 plantillas.
4. Facturación ya integra el resumen contextual del ETS sobre el Workbench único; permanecen el borrador no autosalvado, las vistas internas de siguiente fase y el flujo fiscal incompleto para Producción, cancelaciones, PPD y notas fiscales.
5. Administración y roles sin gestión dinámica ni filtrado visual por permisos.
6. Toolkit, infraestructura y UX con diagnósticos, puertos, pruebas de despliegue, páginas monolíticas y bundle pendientes.

## Módulos pendientes o no iniciados

- **Contactos, Agenda y Llamados:** existen piezas absorbidas por Cliente o ETS, pero no los módulos autónomos acordados. Se requiere decisión formal de absorción o implementación.
- **Catálogo MYC:** el editor embebido ya administra Servicios Simples/Compuestos mediante relación normalizada y expansión ETS; sigue pendiente una experiencia independiente cerrada y sus endpoints permanecen abiertos.
- **CRM/Leads, Encuestas y reporte final:** no se encontró implementación funcional.
- **Google Drive:** no existe integración.

## Deuda técnica vigente prioritaria

| Prioridad | Deuda |
| --- | --- |
| P0 | Extender autorización deny-by-default a las superficies generales del ERP, aislar portal por cliente y exigir secreto JWT seguro; escalación por registro y separación access/refresh ya fueron corregidas para habilitar el Motor. |
| P0 | Eliminar lógica duplicada y ruta `confirm-signatures` repetida en ETS. |
| P0 | Dejar a Calidad como único autenticador de certificados. |
| P1 | Cerrar Hojas de Campo/Captura y su E2E operativo. |
| P1 | Completar la persistencia y el flujo fiscal de Facturación. |
| P1 | Alinear permisos, roles y navegación. |
| P2 | Retirar compatibilidad legacy verificada y reducir deuda de UX, bundle, scripts e infraestructura. |

## Regla de mantenimiento

Toda auditoría posterior debe actualizar este archivo sólo con conclusiones verificadas. Las auditorías conservan la evidencia y la fecha del corte, pero dejan de ser autoridad de avance en cuanto este documento incorpora un corte posterior.
