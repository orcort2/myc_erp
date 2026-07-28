> Estado: VIGENTE
>
> Tipo: Vigente (canónico)
>
> Autoridad: Alta
>
> Prevalece sobre: listas de módulos y fases de las especificaciones V2/V3, `archive/process/flujo-general.md` y propuestas futuras
>
> Corte verificado: 2026-07-28

# Alcance actual del ERP MYC

## Propósito vigente

El ERP controla el expediente operativo de servicios metrológicos desde Cliente y Cotización hasta ETS, equipos, Hojas de Campo, Captura, Calidad, certificados, facturación, pago, liberación y trazabilidad documental. `service_orders` es la raíz operativa del expediente; Cliente y Cotización son sus antecedentes comerciales.

## Dominios con implementación vigente

- Autenticación, usuarios, roles estáticos y auditoría.
- Dashboard y navegación principal.
- Clientes, contactos dependientes, datos fiscales, constancias e importación/exportación.
- Cotizaciones, catálogo de conceptos embebido, Servicios Simples/Compuestos, snapshots y PDF. Un compuesto permanece como concepto comercial único y se expande sólo al crear el ETS.
- ETS/Servicios, hitos de agenda/llamado, equipos, Órdenes de Trabajo y firmas por ciclo.
- Hojas de Campo, plantillas, snapshots, captura, PDF y paquetes de Captura.
- Calidad, revisión consecutiva de certificados por contexto OT/ETS, autenticación, verificación pública y liberación.
- Control Documental V1 y Plantillas Maestras de Certificado.
- Facturación, resumen contextual dentro del ETS, Workbench compartido, cobranza administrativa, Facturama Sandbox, XML y PDF institucional.
- Catálogos SAT locales versionados.
- Patrones, procedimientos, perfiles técnicos, metrología e incertidumbre, con exposición e integración todavía parciales.
- Configuración, componentes reutilizables, APIs, scripts, infraestructura y almacenamiento local.
- Backend parcial del portal de cliente.
- Motor de Resoluciones con Fases 0 a 11 aprobadas y Fase 12 `EN REVISIÓN`.
  Además de la fundación, persistencia y
  seguridad aprobadas, existen 29 modelos persistentes generales, relaciones normalizadas,
  constraints, índices, protección de inmutabilidad, outbox estructural,
  repositorio de reconstrucción, migración reversible, identidad canónica,
  autenticación tipada, permisos atómicos, políticas versionadas,
  deny-by-default, segregación configurable, autorización base y auditoría
  append-only de concesiones/denegaciones, creación, Lifecycle, máquina de
  estados, invariantes sobre evidencia reconstruida, auditoría de transiciones,
  control optimista y orquestación versionada de componentes puros hasta
  revalidación. La simulación implementada es declarativa y sin efectos. La
  ejecución síncrona controlada consume sólo planes autorizados/revalidados,
  persiste ejecución y pasos, invoca acciones exclusivamente por `ActionRunner`,
  controla idempotencia y lock exclusivo con validación posterior al handler,
  bloquea resultados si pierde exclusividad, conserva una única identidad de
  revalidación, efectos/resultados y publica outbox únicamente por solicitud
  explícita con fecha de fallo. La compensación síncrona construye planes
  totales o parciales autorizados sobre checkpoints `completed`, invierte
  orden/dependencias, exige clausura transitiva de dependientes activos,
  impide duplicados y puntos de no retorno y conserva
  ejecución, actor, lock, auditoría y outbox sin reinterpretar el efecto
  original. No existe compensación automática.
  Fase 7 — Auditoría y Evidencia está aprobada: añade modelo
  puro, registro de evidencia, verificación de integridad, timeline,
  reconstrucción sobre snapshot transaccional consistente y consultas
  autorizadas sobre el expediente general sin persistir una fuente paralela.
  Fase 8 — Seguridad integral está `APROBADA`: centraliza el
  catálogo de controles en el evaluador vigente y protege creación/transición,
  ejecución, compensación, consultas y outbox mediante decisiones append-only
  exactas. Las mutaciones distinguen replay idempotente de reutilización para
  otra operación mediante identidad/hash y consumo transaccional append-only;
  auditoría conserva una concesión reutilizable de consulta exacta. Fase 9
  integra exclusivamente `certificate.resolve_incorrect_release` mediante una
  definición vertical, Fact Provider read-only y Domain Gateways hacia el
  servicio canónico de Certificados. La mutación oculta el certificado sin
  reescribir su liberación y admite compensación con evidencia append-only.
  Replay histórico, colisiones concurrentes y snapshots confirmados
  pos-flush están cubiertos por la corrección aprobada. Fase 10 implementa
  contratos públicos v1, API institucional, seguridad por
  consumidor/organización, creación Lifecycle, consultas de auditoría con
  filtros y cursor `c1` AES-GCM ligado a consulta, SDK HTTP y portal técnico;
  está aprobada mediante `dd9a84e`. Fase 11 añade cola SQL durable, workers
  pull, capacidad/heartbeat/drenado de nodos, claim con `SKIP LOCKED`,
  exclusividad por resolución, leases con fencing, recuperación, retry
  determinista, eventos append-only y snapshot operacional. Los efectos
  inciertos quedan bloqueados y no se reintentan automáticamente.
  Fase 12 agrega el Centro de Resoluciones en `/resolutions`, API interna v1,
  proyecciones consolidadas, flujo administrativo guiado y worker operativo
  independiente de la sesión. Conserva la API pública/SDK y no agrega estados,
  handlers ni reglas paralelas. El único vertical sigue siendo Certificados.

La existencia en esta lista no implica cierre; el estado autorizado está en [`PROJECT_STATUS.md`](PROJECT_STATUS.md).

## Capacidades parciales o absorbidas

- **Contactos:** relación dependiente de Cliente; no hay agenda autónoma de contactos.
- **Agenda:** fecha e información dentro del ETS; no hay entidad/calendario/folio propio.
- **Llamados:** hito y transición dentro del ETS; no hay módulo ni bitácora autónoma.
- **Catálogo MYC:** backend y editor embebido desde Cotizaciones, incluido el modelo normalizado de Servicios Compuestos; navegación independiente y autorización uniforme todavía no vigentes.
- **Portal de cliente:** backend sin aislamiento por tenant ni experiencia visible.
- **Google Drive:** mencionado como integración objetivo, sin implementación.

## Capacidades sin implementación funcional

- CRM/Leads y conversión de prospectos.
- Encuestas de satisfacción.
- Reporte final de servicio/rentabilidad acordado en documentos tempranos.

## Fuera del alcance actual implementado

- MYC Document Engine (MDE) completo, su diseñador documental general y el reemplazo transversal de renderizadores. Es un diseño futuro y no genera pendientes de cierre por sí mismo.
- El historial transversal de un mismo activo del cliente a través de múltiples servicios. El modelo actual conserva cada equipo como ocurrencia del ETS, sus identificadores (`serial_number`, `internal_id`) y snapshots sin imponer unicidad global; una evolución futura podrá enlazarlo a una identidad de activo separada sin reescribir el expediente histórico.
- Funcionalidades descritas únicamente en especificaciones archivadas que no estén confirmadas en [`BUSINESS_RULES.md`](BUSINESS_RULES.md), [`DECISIONS.md`](DECISIONS.md) o el código vigente.
- Mejoras aspiracionales de auditorías antiguas no incorporadas al registro vigente de observaciones o deuda técnica.
- Publicar en v1 simulación, autorización de planes, ejecución o compensación
  no forma parte de la superficie concluida: esos servicios internos no se
  reinterpretaron ni duplicaron. La IA permanece
  fuera del alcance vigente y sólo es una posibilidad futura opcional,
  sin dependencia arquitectónica ni operativa del ERP o del Motor.

## Criterio para versión estable 1.0

La versión 1.0 requiere, como mínimo, cerrar los riesgos P0 de seguridad, eliminar duplicaciones que alteran el flujo, completar el circuito operativo Hojas de Campo→Captura→Calidad→Certificados, cerrar el flujo fiscal que se mantenga dentro de alcance y demostrar los recorridos críticos mediante pruebas autenticadas. Una capacidad no iniciada sólo será requisito de 1.0 si se confirma expresamente en este documento.
