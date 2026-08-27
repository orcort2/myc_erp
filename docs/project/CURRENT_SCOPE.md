> Estado: VIGENTE
>
> Tipo: Vigente (canónico)
>
> Autoridad: Alta
>
> Prevalece sobre: listas de módulos y fases de las especificaciones V2/V3, `archive/process/flujo-general.md` y propuestas futuras
>
> Corte verificado: 2026-08-26

# Alcance actual del ERP MYC

## ETS Mantenimiento — TERMINADO, EN REVISIÓN (2026-08-18)

Incluye preventivo/correctivo, laboratorio/campo, unidad/equipo/OT institucional, asignación y visita, captura Antes–Intervención–Después–Futuro, pausas tipadas, materiales utilizados/requeridos, cambio comercial preventivo→correctivo, referencia separada a Reparación, investigación por equipo inoperable, reporte automático versionado, firma, liberación, permisos y bloqueantes UX accionables. Excluye Compras, Almacén, mapas/tracking externos y ejecución de Reparación.

## Propósito vigente

El ERP controla el expediente operativo de servicios metrológicos desde Cliente y Cotización hasta ETS, equipos, Hojas de Campo, Captura, Calidad, certificados, facturación, pago, liberación y trazabilidad documental. `service_orders` es la raíz operativa del expediente; Cliente y Cotización son sus antecedentes comerciales.

## Dominios con implementación vigente

- Autenticación, usuarios, roles estáticos, permisos efectivos, guard API
  deny-by-default y auditoría.
- Autenticación específica de MYC Mobile con actores `internal`/`client`,
  `mobile.access`, contexto resuelto desde base, RBAC externo persistido,
  máximo una membresía activa por usuario y scope de cliente sobre OT LAB,
  equipos, firmas, PDF, revisiones, Tickets, push y realtime autorizado.
- Dashboard y navegación principal.
- Clientes, contactos dependientes, datos fiscales, constancias e importación/exportación.
- Cotizaciones, catálogo de conceptos embebido, Servicios Simples/Compuestos, snapshots y PDF. Tipo Producto/Servicio es comercial/fiscal e independiente de `operational_category`; Venta puede seleccionarse con ambos tipos y un Producto con otra categoría no se convierte en `sale`. El snapshot conserva identidad/configuración por componente sin refresco silencioso al reabrir o editar. Un compuesto permanece como concepto comercial único y se expande sólo al crear el ETS.
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
- Eliminación física administrativa de una OT productiva individual desde el
  expediente ETS web, sin restricción por estado. El agregado elimina dependencias
  operativas exclusivas en una transacción, conserva ETS, factura/cotización,
  maestros, Motor y ciclos de firma todavía compartidos, y deja auditoría
  mínima. MYC Mobile no consume esta operación productiva.
- Núcleo ETS múltiple/evolucionado Fase 1, `EN REVISIÓN`: unidades estables por
  intervención con partida/categoría canónica congelada y capacidad evolutiva exclusivamente para Servicio General,
  secuencias de etapas sin reemplazo histórico, identificación parcial
  tolerante, solicitudes técnico→comercial separadas del estado técnico,
  decisión interna autorizada por partida con categorías validadas, Activity
  contextual y tareas `#tarea`.
- Acceso móvil backend de sólo lectura para técnicos: ETS, OT, Equipos y Hojas
  de Campo heredan exclusivamente `ServiceOrder.technician_id`, con 404 ante
  recursos ajenos o sin asignación. La app temporal LAB no consume estas rutas
  productivas en su listado, detalle, documentos ni eliminación.
- Hojas de Campo, plantillas, snapshots, captura, PDF y paquetes de Captura.
- Calidad como única superficie de autenticación, revisión consecutiva por contexto OT/ETS, autoridad transaccional de Certificados, verificación pública y liberación separada.
- Verificación como variante del pipeline metrológico: partida `verification`,
  equipo/OT obligatorios, alcance de acreditación nulo, Certificado de
  Verificación y folio anual `MYCV-MM-AA-XXXX` desde `0001`. Calibración y Verificación pueden
  coexistir en el mismo ETS mediante asociación explícita de cada equipo a su
  `ServiceOrderItem`. Todo concepto nuevo o actualizado de Verificación exige
  un Master genérico inicial activo, vigente y con XLSX disponible; el
  bonche lo entrega junto con las Hojas de Campo terminadas. Captura lo sustituye
  fuera del ERP por el archivo técnico real y, al reingresar el ZIP, el backend
  asocia certificado/equipo por identidad fuerte e identifica de forma única el
  Master registrado de Verificación por fingerprint, congelando automáticamente
  la versión final. Ajuste permanece fuera de alcance.
- Aceptación de Cotización y materialización idempotente del ETS en una sola
  transacción backend; Cotizaciones sólo permite abrir el ETS ya creado.
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
  Fase 15, `EN REVISIÓN`, incorpora la familia `administrative_tools` y las
  definiciones ETS `restore_soft_deleted`, `rebuild_from_accepted_quotation` y
  `void_preserving_history`; reutiliza el Motor/worker, bloquea dependencias
  consumidas y no incluye todavía reparación estructural genérica ni
  herramientas administrativas de otros dominios.

La existencia en esta lista no implica cierre; el estado autorizado está en [`PROJECT_STATUS.md`](PROJECT_STATUS.md).

## Capacidades parciales o absorbidas

- **Contactos:** relación dependiente de Cliente; no hay agenda autónoma de contactos.
- **Agenda:** fecha e información dentro del ETS; no hay entidad/calendario/folio propio.
- **Llamados:** hito y transición dentro del ETS; no hay módulo ni bitácora autónoma.
- **Catálogo MYC:** backend y editor embebido desde Cotizaciones, incluido el modelo normalizado de Servicios Compuestos; navegación independiente y autorización uniforme todavía no vigentes.
- **ETS múltiple/evolucionado:** el backend y los contratos frontend están
  implementados; la composición visual por cards/tabs, deep-links y workflows
  técnicos específicos de cada categoría no pertenecen a Fase 1. La propuesta
  de Hojas de Campo conserva el resolver frontend actual y no fue redefinida.
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

- Auditoría Anual transversal: apertura/cierre, ciclo, auditor u organismo,
  evidencias, observaciones, hallazgos, no conformidades, acciones correctivas,
  responsables, compromisos, seguimiento, eficacia y conclusiones. Debe
  integrarse en el futuro con Tickets, Motor de Resoluciones, Activity,
  Documentos y permisos; un cierre será histórico e inmutable. No existe motor
  ni reinicio automático en este corte.

- CRM/Leads y conversión de prospectos.
- Encuestas de satisfacción.
- Reporte final de servicio/rentabilidad acordado en documentos tempranos.

## Ampliación temporal verificada 2026-08-13 — OT LAB móvil

- Login interno JWT y almacenamiento de tokens en SecureStore.
- Alta/listado/detalle manual de OT LAB sin entidades productivas.
- Folios backend 6400–6999 con namespace y lock independientes.
- Hasta 10 equipos por OT, edición/eliminación antes de firma y OT adicional
  encadenada con datos generales heredados.
- Una sesión de firma técnico/cliente por cohorte: todas las OT abiertas
  participantes o sólo la seleccionada. La firma bloquea esas integrantes y
  la finalización genera un PDF institucional exclusivamente para cada OT de
  la cohorte.
- Captura secuencial Cliente → Técnico con orientación portrait/landscape,
  strokes normalizados que sobreviven al resize, ownership temporal del gesto
  frente al ScrollView, `hasDrawing`, nombres recortados, lock anti-submit y
  contexto explícito por raíz para grupo y por ID de OT para individual. El
  borrador se conserva en refetch/rerender de la misma cohorte; otra modalidad,
  OT individual o raíz lo reemplaza por una captura vacía, sin recuperar estados
  antiguos al volver. Tap/movimiento despreciable no cuenta como firma.
  `signature_required` se limita a reapertura/invalidez previa y no bloquea el
  POST inicial; la autoridad de aceptación permanece en backend. No existe
  dependencia del frontend ERP.
- Eliminación administrativa individual con `lab_work_orders.delete`, válida
  en cualquier estado. Elimina equipo, PDF, revisiones/tickets exclusivos y la
  OT seleccionada; repara raíz/cadena y conserva firma, tickets, revisiones y
  hermanas todavía compartidos. La app confirma y reconcilia el listado LAB.
- Impresión/compartir mediante APIs Expo Go y exportación administrativa ZIP
  con manifiesto, relaciones, firmas, PDFs y checksums.

Permanece fuera del alcance implementado generar/distribuir una build móvil,
declarar aceptación Android/iOS sin dispositivos, aplicar la migración a producción,
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

## Alcance implementado 2026-08-26 — Seguridad y scope MYC Mobile

- `User` permanece como identidad única; los tokens Mobile distinguen staff y
  cliente sin convertir cuentas externas en roles internos o técnicos falsos.
- Viewer externo, Operativo Jr y Operativo Sr son roles persistidos del RBAC
  externo. `mobile.access` sólo abre sesión; permisos operativos se evalúan por
  endpoint y la autoadministración del Portal no puede otorgarlos.
- Un usuario externo conserva una sola membership `active`; suspendidas,
  revocadas, rechazadas y pendientes permanecen como historia.
- OT LAB creadas por cliente se vinculan al `Client` derivado y todas sus
  listas, detalles y subrecursos aplican scope. Staff conserva el flujo previo.
- Las superficies productivas Mobile de ETS, OT, Equipos, Hojas de Campo y
  Venta permanecen bloqueadas para `client` hasta una fase explícita.

Quedan fuera folios Mobile, reposición, eventos realtime de folios, cambio de
organización, revocación server-side por JTI y renombrado del route group
`(technician)`.

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

## Alcance implementado 2026-08-17 — Comunicaciones Etapas A–I

- Canal `WS /api/realtime/ws` autenticado por subprotocolo JWT, usuario
  revalidado, envelope v1 y rooms autorizadas por usuario/conversación.
- REST canónico para conversaciones directas y grupales, historial paginado,
  mensajes idempotentes, sync por secuencia, recibos, directorio y menciones.
- Persistencia normalizada de secuencia, `client_message_id`, recibos por
  usuario, menciones estructuradas y no leídos; relación opcional con un Ticket
  al que el actor ya tiene acceso.
- MYC Mobile con bandeja/detalle, envío optimista, reconciliación, error/retry,
  deduplicación, typing, recibos, menciones, grupos, push/deep links,
  multi-dispositivo, AppState, backoff, refresh HTTP y logout.
- Topología productiva comprobada single-worker; `RealtimeHub` mantiene la
  implementación desacoplada y un backplane es compuerta previa sólo si la
  topología aumenta procesos/instancias.

Quedan fuera la ampliación del ERP web, adjuntos/llamadas, una nueva política
de permisos, cambios funcionales en Tickets/OT/ETS, build EAS y despliegue. La
aceptación física en dos dispositivos permanece pendiente; por eso el frente
queda **EN REVISIÓN**.

## Alcance implementado 2026-08-26 — Grupos anticipados OT LAB

Solicitud externa, claim, aprobación/rechazo, creación directa Web/Mobile internal, materialización transaccional de N folios, conversación posterior al claim, notificación, realtime y visualización Mobile/Web. No se alteran ETS productivo, firma LAB, Tickets, PDF ni límite de 10 equipos.

La alta individual, grupo directo y adicional LAB quedan fuera del alcance de actores externos; sólo staff autorizado conserva esas operaciones. Las bandejas Web/Mobile presentan tickets y requests sin normalizarlos artificialmente. Mobile compone ambas fuentes en UI para evitar otro contrato backend y usa el mismo servicio de decisión existente.

## Alcance implementado 2026-08-27 — Cohortes de cierre OT LAB

El parentesco histórico permanece en `root_work_order_id`. Una sesión de firma
representa una cohorte: puede abarcar todas las OT `draft` abiertas y equipadas
del grupo o únicamente la OT seleccionada. La finalización, PDF, hash,
invalidación y reapertura se limitan a esa sesión; las completadas quedan
congeladas y las hermanas abiertas siguen editables. Mobile ofrece ambas
modalidades cuando existe grupo real y explica por qué el cierre grupal se
bloquea si alguna participante carece de equipos.

No se incorporan estados, tablas ni migraciones; no cambian folios, cadena,
firmas productivas, ETS, Certificados ni Facturación. La aceptación física
Android/iPhone de este alcance permanece pendiente.

## Alcance implementado 2026-08-18 — ETS Venta

- Configuración estructurada de Venta en catálogo: identificación individual,
  marca/modelo/especificación esperados y calibración incluida opcional.
- Snapshot comercial autoritativo y creación automática/idempotente del ETS;
  ningún arribo o reapertura consulta el catálogo vigente.
- Unidades serializadas o cantidades, arribos parciales, discrepancia con
  autorización, garantía y entregas parciales por recolección, paquetería o
  técnico MYC, con nota PDF, Portal y superficie móvil acotada.
- Inicialización de ETS históricos sólo mediante acción explícita y desde el
  snapshot. En ETS mixtos, cerrar Venta no cierra otras partidas.
- Endurecimiento tester: Venta sin evolución genérica, Calibración posterior
  ligada al ETS/cotización, tres resultados de garantía, firma/evidencia
  tipada y acotada, y escape integral del HTML de nota de entrega.

Quedan fuera mapas/rastreo externo, Gmail, una plantilla institucional avanzada
de nota, aceptación física y workflows de categorías distintas. El frente
queda **EN REVISIÓN**.
