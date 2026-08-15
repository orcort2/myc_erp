> Estado: VIGENTE
>
> Tipo: Vigente (canónico)
>
> Autoridad: Alta
>
> Prevalece sobre: listas de módulos y fases de las especificaciones V2/V3, `archive/process/flujo-general.md` y propuestas futuras
>
> Corte verificado: 2026-08-14

# Alcance actual del ERP MYC

## Propósito vigente

El ERP controla el expediente operativo de servicios metrológicos desde Cliente y Cotización hasta ETS, equipos, Hojas de Campo, Captura, Calidad, certificados, facturación, pago, liberación y trazabilidad documental. `service_orders` es la raíz operativa del expediente; Cliente y Cotización son sus antecedentes comerciales.

## Dominios con implementación vigente

- Autenticación, usuarios, roles estáticos, permisos efectivos, guard API
  deny-by-default y auditoría.
- Dashboard y navegación principal.
- Clientes, contactos dependientes, datos fiscales, constancias e importación/exportación.
- Cotizaciones, catálogo de conceptos embebido, Servicios Simples/Compuestos, snapshots y PDF. Un compuesto permanece como concepto comercial único y se expande sólo al crear el ETS.
- Primera excepción contextual de Ventas: una cotización aprobada con ETS
  integralmente virgen puede desbloquear todas sus partidas, guardar una nueva
  revisión y reconstruir el ETS con el mismo folio. Administrador desbloquea
  con un solo clic mediante autoridad `*`, sin modal ni captura manual de
  motivo u observación; el sistema registra el motivo institucional. Otros
  roles conservan solicitud y revisión segregadas.
- ETS/Servicios con servicio de aplicación canónico, actor obligatorio desde
  las mutaciones HTTP y excepciones persistentes
  `requested → authorized → executed`; hitos de agenda/llamado, equipos,
  Órdenes de Trabajo y firmas por ciclo.
- Núcleo ETS múltiple/evolucionado Fase 1, `EN REVISIÓN`: unidades estables por
  intervención con partida/categoría origen y capacidad evolutiva por unidad,
  secuencias de etapas sin reemplazo histórico, identificación parcial
  tolerante, solicitudes técnico→comercial separadas del estado técnico,
  decisión interna autorizada por partida con categorías validadas, Activity
  contextual y tareas `#tarea`.
- Acceso móvil backend de sólo lectura para técnicos: ETS, OT, Equipos y Hojas
  de Campo heredan exclusivamente `ServiceOrder.technician_id`, con 404 ante
  recursos ajenos o sin asignación. La aplicación `myc-mobile` no forma parte
  del alcance de esta implementación.
- Hojas de Campo, plantillas, snapshots, captura, PDF y paquetes de Captura.
- Calidad como única superficie de autenticación, revisión consecutiva por contexto OT/ETS, autoridad transaccional de Certificados, verificación pública y liberación separada.
- Control Documental V1 y Plantillas Maestras de Certificado.
- Facturación, resumen contextual dentro del ETS, Workbench compartido, registro e historial de pagos parciales/totales antes o después del timbrado, comprobante PDF, cuentas por cobrar, cobranza administrativa, Facturama Sandbox, XML y PDF institucional.
- Catálogos SAT locales versionados.
- Patrones, procedimientos, perfiles técnicos, metrología e incertidumbre, con exposición e integración todavía parciales.
- Configuración, componentes reutilizables, APIs, scripts, infraestructura y almacenamiento local.
- Portal del Cliente autenticado y aislado por vínculo persistente
  `User`–`ClientPortalMembership`–`Client`, con registro, invitaciones, roles
  propios, administración interna y experiencia frontend visible.
- Actividad institucional transversal sobre entidades existentes: conversación
  humana, eventos, menciones, adjuntos, atención, no leídos, bandeja y
  notificaciones, sin reemplazar auditoría ni datos técnicos.
- Motor de Resoluciones con Fases 0 a 13 aprobadas y Fase 14 `EN REVISIÓN`.
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
  Fase 13 convierte esa superficie en consola oficial: registro institucional
  versionado, formularios declarativos, indicadores backend, expediente
  completo y ejecución real de Certificados después de terminar la sesión.
  Fase 14 incorpora una composición instalada única y el segundo vertical
  `service_order.resolve_additional_equipment@1.0`: propuesta offline/ERP,
  análisis, plan, simulación sin efectos, autorización, revalidación, cola,
  worker, alta idempotente y compensación limitada. La IA no está autorizada.

La existencia en esta lista no implica cierre; el estado autorizado está en [`PROJECT_STATUS.md`](PROJECT_STATUS.md).

## Capacidades parciales o absorbidas

- **Contactos:** relación dependiente de Cliente; no hay agenda autónoma de contactos.
- **Agenda:** fecha e información dentro del ETS; no hay entidad/calendario/folio propio.
- **Llamados:** hito y transición dentro del ETS; no hay módulo ni bitácora autónoma.
- **Catálogo MYC:** backend y editor embebido desde Cotizaciones, incluido el modelo normalizado de Servicios Compuestos; navegación independiente y autorización uniforme todavía no vigentes.
- **ETS múltiple/evolucionado:** el backend y los contratos frontend están
  implementados; la composición visual por cards/tabs, deep-links y workflows
  técnicos específicos de cada categoría no pertenecen a Fase 1.
- **Portal de cliente:** integración técnica terminada y en revisión. Incluye
  identidad externa separada, registro, verificación, invitaciones, revisión y
  vínculo persistente `User`–`ClientPortalMembership`–`Client`, roles propios,
  administración conjunta desde Ajustes/Clientes con buscador, filtros,
  multirrol, registros públicos, solicitudes, membresías, invitaciones,
  configuración, auditoría y modal de siete pestañas; además incluye la sección
  Usuarios dentro del portal, acotada a la empresa derivada de la membresía, y
  experiencia responsive para empresa, cotizaciones, servicios, equipos,
  certificados, facturas y pagos. Correo
  productivo, MFA, recuperación, sesiones revocables y comunicaciones
  bidireccionales permanecen fuera de esta entrega.
- **Google Drive:** mencionado como integración objetivo, sin implementación.

## Capacidades sin implementación funcional

- CRM/Leads y conversión de prospectos.
- Encuestas de satisfacción.
- Reporte final de servicio/rentabilidad acordado en documentos tempranos.

## Ampliación temporal verificada 2026-08-13 — OT LAB móvil

- Login interno JWT y almacenamiento de tokens en SecureStore.
- Alta/listado/detalle manual de OT LAB sin entidades productivas.
- Folios backend 6400–6999 con namespace y lock independientes.
- Hasta 10 equipos por OT, edición/eliminación antes de firma y OT adicional
  encadenada con datos generales heredados.
- Una sesión de firma técnico/cliente para todo el grupo; la firma bloquea altas
  y edición y la finalización genera un PDF institucional por OT.
- Impresión/compartir mediante APIs Expo Go y exportación administrativa ZIP
  con manifiesto, relaciones, firmas, PDFs y checksums.

Permanece fuera del alcance implementado aplicar la migración a producción,
retirar el LAB, migrar sus datos a entidades productivas o declarar aceptación
física sin ejecutar el recorrido real en iPhone.

## Fuera del alcance actual implementado

- El Catálogo Institucional Funcional describe el ERP objetivo y reserva
  capacidades futuras, pero esta validación documental no incorpora ninguna de
  ellas al alcance implementado. Las marcas objetivo/reservadas sólo podrán
  cambiar de categoría mediante decisión y etapa posterior aprobadas.
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

La versión 1.0 requiere, como mínimo, conservar la contención transversal de
seguridad verificada en la Etapa 1, cerrar los riesgos P0 restantes, eliminar
duplicaciones que alteran el flujo, completar el circuito operativo Hojas de
Campo→Captura→Calidad→Certificados, cerrar el flujo fiscal que se mantenga
dentro de alcance y demostrar los recorridos críticos mediante pruebas
autenticadas. Una capacidad no iniciada sólo será requisito de 1.0 si se
confirma expresamente en este documento.

## Ampliación verificada 2026-07-29 — Ventas y folios

- Cotización aprobada: solicitud, autorización y edición directa excepcional de
  partidas con revisión/delta. Administrador compacta solicitud/autorización en
  un comando auditado y entra inmediatamente a editar.
- ETS virgen: validación integral, eliminación física y recreación atómica con
  el mismo `OSMYC-…`.
- Catálogo: tipos `accredited`, `traceable`, `linked`, empresas vinculadas
  extensibles y prefijo congelado.
- Certificados/OT: formatos compactos y contadores anuales con pisos 2026.
- Fuera de alcance: actualización no destructiva de un ETS con operación y
  excepciones de otros módulos.

## Infraestructura transversal verificada 2026-08-04 — Archivos

- perfiles centrales para adjuntos, Captura, Plantillas Maestras, PDFs de
  certificado, constancias fiscales e importación de Clientes;
- validación acotada de tamaño, MIME, firma/estructura, ZIP/Office, PDF, XML e
  imágenes antes de persistir o parsear;
- almacenamiento local contenido, escritura atómica, checksum y entrega de
  archivo regular después del permiso/ownership vigente;
- recuperación Facturama valida base64/XML/PDF antes de publicar;
- datos operativos, dump y paquetes generados quedan fuera del índice Git sin
  borrar evidencia local.

No forman parte de este alcance: RBAC interno dinámico, cambios de estado/folio
adicionales, almacenamiento remoto, antivirus externo, retención avanzada o
las capacidades reservadas del catálogo funcional. `PortalMembership` sí está
implementado y forma parte del alcance vigente.

## Alcance implementado 2026-08-14 — Tickets/reapertura móvil

- Filtros backend y móviles separados por folio y cliente, combinables,
  case-insensitive para cliente, con estado, debounce y paginación.
- Tickets `REOPEN_WORK_ORDER`, bandeja propia/global y revisión por permiso.
- Reapertura del grupo LAB con folio estable, revisión incremental, snapshot,
  PDF histórico y nueva generación al cerrar.
- Preservación de firma para cambios menores e invalidación backend obligatoria
  para cambios estructurales; las firmas históricas nunca se eliminan.
- Control `edit_version`, auditoría e idempotencia de decisiones/reintentos.

Quedan fuera IA, cálculos metrológicos, otros tipos de Ticket, publicación EAS
y extensión al agregado productivo ETS.

## Alcance implementado 2026-08-14 — Notificaciones móviles V1

- Notificación persistente propia con lectura, paginación y badge derivado de
  `read_at`; dispositivos Expo autenticados, idempotentes y multi-dispositivo.
- Eventos `ticket.created`, `ticket.approved`, `ticket.rejected`,
  `ticket.resolved` y `ticket.signature_required`, con revisores resueltos por
  permiso efectivo `tickets.review` y respuestas dirigidas al solicitante.
- Centro MYC Mobile, deep links a Ticket/OT y refresco por push, foreground,
  foco, mutación local y pull-to-refresh, sin polling periódico.
- Entrega Expo best-effort posterior al commit; falla externa nunca revierte el
  dominio ni elimina la notificación persistente.

Quedan fuera de V1 retries durables/receipts, preferencias, quiet hours,
agrupación, APNs/FCM directos, canales no push y aceptación física iOS/Android.
