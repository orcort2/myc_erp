> Estado: VIGENTE
>
> Tipo: Vigente (canónico)
>
> Autoridad: Alta
>
> Prevalece sobre: listas de módulos y fases de las especificaciones V2/V3, `archive/process/flujo-general.md` y propuestas futuras
>
> Corte verificado: 2026-07-21

# Alcance actual del ERP MYC

## Propósito vigente

El ERP controla el expediente operativo de servicios metrológicos desde Cliente y Cotización hasta ETS, equipos, Hojas de Campo, Captura, Calidad, certificados, facturación, pago, liberación y trazabilidad documental. `service_orders` es la raíz operativa del expediente; Cliente y Cotización son sus antecedentes comerciales.

## Dominios con implementación vigente

- Autenticación, usuarios, roles estáticos y auditoría.
- Dashboard y navegación principal.
- Clientes, contactos dependientes, datos fiscales, constancias e importación/exportación.
- Cotizaciones, catálogo de conceptos embebido, snapshots y PDF.
- ETS/Servicios, hitos de agenda/llamado, equipos, Órdenes de Trabajo y firmas por ciclo.
- Hojas de Campo, plantillas, snapshots, captura, PDF y paquetes de Captura.
- Calidad, revisión consecutiva de certificados por contexto OT/ETS, autenticación, verificación pública y liberación.
- Control Documental V1 y Plantillas Maestras de Certificado.
- Facturación, cobranza administrativa, Facturama Sandbox, XML y PDF institucional.
- Catálogos SAT locales versionados.
- Patrones, procedimientos, perfiles técnicos, metrología e incertidumbre, con exposición e integración todavía parciales.
- Configuración, componentes reutilizables, APIs, scripts, infraestructura y almacenamiento local.
- Backend parcial del portal de cliente.

La existencia en esta lista no implica cierre; el estado autorizado está en [`PROJECT_STATUS.md`](PROJECT_STATUS.md).

## Capacidades parciales o absorbidas

- **Contactos:** relación dependiente de Cliente; no hay agenda autónoma de contactos.
- **Agenda:** fecha e información dentro del ETS; no hay entidad/calendario/folio propio.
- **Llamados:** hito y transición dentro del ETS; no hay módulo ni bitácora autónoma.
- **Catálogo MYC:** backend y consumo desde Cotizaciones/Facturación; navegación independiente no vigente.
- **Portal de cliente:** backend sin aislamiento por tenant ni experiencia visible.
- **Google Drive:** mencionado como integración objetivo, sin implementación.

## Capacidades sin implementación funcional

- CRM/Leads y conversión de prospectos.
- Encuestas de satisfacción.
- Reporte final de servicio/rentabilidad acordado en documentos tempranos.

## Fuera del alcance actual implementado

- MYC Document Engine (MDE) completo, su diseñador documental general y el reemplazo transversal de renderizadores. Es un diseño futuro y no genera pendientes de cierre por sí mismo.
- Funcionalidades descritas únicamente en especificaciones archivadas que no estén confirmadas en [`BUSINESS_RULES.md`](BUSINESS_RULES.md), [`DECISIONS.md`](DECISIONS.md) o el código vigente.
- Mejoras aspiracionales de auditorías antiguas no incorporadas al registro vigente de observaciones o deuda técnica.

## Criterio para versión estable 1.0

La versión 1.0 requiere, como mínimo, cerrar los riesgos P0 de seguridad, eliminar duplicaciones que alteran el flujo, completar el circuito operativo Hojas de Campo→Captura→Calidad→Certificados, cerrar el flujo fiscal que se mantenga dentro de alcance y demostrar los recorridos críticos mediante pruebas autenticadas. Una capacidad no iniciada sólo será requisito de 1.0 si se confirma expresamente en este documento.
