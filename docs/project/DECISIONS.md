> Estado: VIGENTE
>
> Tipo: Vigente (canónico)
>
> Autoridad: Alta
>
> Prevalece sobre: decisiones incompatibles de especificaciones archivadas y propuestas no ratificadas
>
> Corte verificado: 2026-08-17

# Registro de decisiones vigentes

| ID | Fecha aproximada | Decisión vigente | Documento origen / evidencia | Consecuencia |
| --- | --- | --- | --- | --- |
| ADR-001 | 2026-06, V3 | `service_orders` es la entidad raíz operativa. | `archive/architecture/SISTEMA_ERP_MYC_V3.md`, confirmada por modelos vigentes | Equipos, hojas, certificados, facturas y documentos se navegan desde ETS. |
| ADR-002 | 2026-06/07 | PostgreSQL + SQLAlchemy + Alembic son la persistencia principal; no se simulan datos persistentes en frontend. | V3, código y migraciones | Los labs en memoria no acreditan cierre operativo. |
| ADR-003 | 2026-07 | Agenda y Llamado permanecen actualmente como datos/hitos dentro de ETS, no como módulos completos. | implementación y auditoría 2026-07-21 | La especificación antigua no determina el flujo actual; su cierre requiere decisión futura de absorción o implementación. |
| ADR-004 | 2026-07-10 | Las OT se agrupan en bloques de máximo 10 equipos y las firmas se capturan por ciclos de OT pendientes. | `../archive/project/BACKUP_ESTADO_ACTUAL_HISTORICO_2026-07-21.md`, modelos y servicios vigentes | Una OT posterior no invalida firmas anteriores y requiere ciclo nuevo. |
| ADR-005 | 2026-07-13 | Hojas de Campo usa definiciones declarativas y snapshots inmutables de plantilla/identidad. | análisis, cierre de fase 1 e implementación actual | Cambios de plantilla no alteran documentos históricos. |
| ADR-006 | 2026-07-13 | El catálogo maestro de campos define conceptos canónicos; plantillas no deben inventar nuevas identidades de campo. | [`../architecture/FIELD_SHEET_FIELD_REGISTRY.md`](../architecture/FIELD_SHEET_FIELD_REGISTRY.md) | Captura, filtros, PDF y futuros motores deben converger en claves comunes. |
| ADR-007 | 2026-07-13 | Sin coincidencia segura de plantilla, la selección es manual; no hay fallback silencioso a General. | auditoría de integración de Hojas de Campo | Evita capturar con semántica incorrecta. |
| ADR-008 | 2026-07-17 | Plantillas Maestras reutiliza `ControlledDocument`/versiones y congela el archivo esperado en el equipo. | `modules/control-documental/PLANTILLAS_MAESTRAS.md` | No se crea un segundo sistema documental ni se cambian históricos por actualización del Master. |
| ADR-009 | 2026-07 | Calidad debe ser el único autenticador de certificados. | decisiones funcionales consolidadas y auditoría 2026-07-21 | Las acciones duplicadas en ETS son deuda a retirar. |
| ADR-010 | 2026-07 | Certificados es un expediente de documentos autenticados, no otra bandeja de aprobación. | implementación de Certificados/Calidad | La vista filtra PDFs autenticados; aprobación ocurre en Calidad. |
| ADR-011 | 2026-07 | La liberación documental se rige por `requires_payment`; con pago requerido exige factura pagada y saldo cero. | servicio de certificados | Evita usar una regla histórica absoluta que no contempla servicios sin pago requerido. |
| ADR-012 | 2026-07 | Facturación usa un workbench compartido y snapshots fiscales; el PDF institucional MYC se genera desde datos persistidos y XML cuando existe. | auditorías de Facturación y código vigente | Mesa de trabajo y vista de Facturas deben conservar el mismo contrato. |
| ADR-013 | 2026-07-15 | Una emisión Facturama ambigua no se reintenta automáticamente; primero se concilia. | actualizaciones operativas y servicio Facturama | Reduce doble timbrado. Producción continúa fuera del cierre actual. |
| ADR-014 | 2026-07-14/17 | Catálogos SAT se importan y versionan localmente; no hay consulta remota en ejecución. | [`../architecture/CATALOGOS_SAT.md`](../architecture/CATALOGOS_SAT.md) | Facturación y Cotizaciones consumen una fuente local reproducible. |
| ADR-015 | 2026-07-10 | Control Documental V1 queda sellado con el diseñador deshabilitado. | cierre V1 en `../archive/project/BACKUP_ESTADO_ACTUAL_HISTORICO_2026-07-21.md`, auditoría 2026-07-21 | El diseñador general no es pendiente de V1. |
| ADR-016 | 2026-07 | Liquid Glass y componentes compartidos son el lenguaje UX vigente. | implementación frontend y cierres visuales | Modales y workbenches nuevos deben reutilizar componentes; alertas nativas son deuda. |
| ADR-017 | 2026-07 | Los documentos internos de Facturación se ocultan de la vista ordinaria, pero se conservan para soporte/auditoría protegida. | auditoría de Facturación y UI vigente | No se eliminan archivos fiscales ni trazabilidad. |
| ADR-018 | 2026-07 | El reset de desarrollo tiene una única implementación y exige frase de confirmación. | `AGENTS.md` y Toolkit vigente | No se duplican rutas destructivas. |
| ADR-019 | 2026-07-21 | [`DOCUMENTATION_INDEX.md`](DOCUMENTATION_INDEX.md) es la entrada única; [`PROJECT_STATUS.md`](PROJECT_STATUS.md) es la única autoridad de avance. | reorganización documental | Auditorías, cierres y archivos no pueden volver a declarar el estado actual. |
| ADR-020 | 2026-07 | MDE permanece como Diseño futuro. | `architecture/future/MDE_SPEC.md` | No genera pendientes actuales ni sustituye renderizadores existentes hasta decisión posterior. |
| ADR-021 | 2026-07-21 | La documentación es parte obligatoria de cada cambio y se actualiza en el mismo trabajo sin requerir solicitud adicional. | `AGENTS.md` y `DOCUMENTATION_INDEX.md` | Cada tarea enruta sus impactos al canon, arquitectura, módulo, auditoría o cierre correspondiente y reporta `## Documentación actualizada`. |
| ADR-022 | 2026-07-21 | Paquete de Captura consume hojas técnicamente terminadas (`completed`, `under_review`, `approved`) y organiza entregables por ETS/OT/certificado. | diagnóstico real del ETS 1 y `modules/captura/PAQUETE_CAPTURA.md` | Enviar a Captura no vuelve inelegible la hoja y el ZIP mantiene una jerarquía institucional estable. |
| ADR-023 | 2026-07-21 | La carga del Master persiste su diagnóstico y activa `capture_in_progress`; no modifica el `match_status` legacy y el frontend debe refrescar y mostrar la respuesta inmediatamente. | diagnóstico del POST `/service-orders/{id}/capture-files` y módulo de Captura | Se evita confundir identificación del Excel con estados documentales legacy y se elimina la dependencia de recargar la página. |
| ADR-024 | 2026-07-21 | El documento revisado en Captura→Calidad es el Master XLSX identificado; el PDF final se genera posteriormente durante la autenticación, no se carga manualmente antes de Calidad. | decisión funcional y validación real del Master | Captura elimina carga/indicadores PDF, Calidad descarga el XLSX y warnings no bloquean mientras diferencias explícitas sí. |
| ADR-025 | 2026-07-21 | El tipo acreditado/trazable se detecta identificando la plantilla contra el snapshot Master registrado, no comparando claves internas con texto documental. | corrección semántica y pruebas del fingerprint | Cada nueva plantilla se incorpora vinculando su snapshot al alcance de calibración; el parser reutiliza el mismo extractor y umbral sin duplicar reglas por archivo. |
| ADR-026 | 2026-07-21 | Aprobar y autenticar son operaciones separadas: Calidad aprueba el Master y, sólo desde `quality_approved`/`approved`, Autenticar convierte ese XLSX a PDF, aplica el sello vigente y persiste `authenticated`. La aprobación es la única compuerta; no se consulta PDF previo ni matching PDF–Excel. | corrección Calidad→Autenticación y validación HTTP reversible del certificado `1` | Se conserva el Master como fuente aprobada y su referencia en auditoría; los contadores y tarjetas se refrescan desde el estado persistido. |
| ADR-027 | 2026-07-21 | La dependencia LibreOffice se resuelve de forma multiplataforma mediante `LIBREOFFICE_EXECUTABLE`, comandos `soffice`/`libreoffice` en `PATH` y rutas comunes de macOS, Windows o Linux; el alias `OFFICE_CONVERTER_BINARY` se conserva. | diagnóstico macOS, servicio central y Doctor | Ningún despliegue depende de una ruta única y la ausencia del convertidor se detecta al arrancar o ejecutar Doctor, antes de autenticar. |
| ADR-028 | 2026-07-21 | `match_status` deja de ser compuerta de Certificados/Liberación. `authenticated` más PDF autenticado existente constituye readiness documental; la regla financiera vigente decide si Liberar está habilitado. | corrección Certificados→Liberación y pruebas con `match_status=pending` | Los históricos autenticados no requieren backfill; “Listo para liberar”, “Pendiente de pago” y “Liberado” son estados derivados distintos. |
| ADR-029 | 2026-07-21 | El Workbench de Facturación tiene un único controlador frontend reutilizable; `BillingPage` compone la vista global y los consumidores abren por contexto explícito `invoice_id`/`service_order_id`, sin `localStorage` ni controladores paralelos. | [`../architecture/INVOICE_WORKBENCH_CONTROLLER.md`](../architecture/INVOICE_WORKBENCH_CONTROLLER.md) y Sprint 1 de Facturación | La futura pestaña ETS debe reutilizar el hook, `Invoice`, el endpoint filtrable y `InvoiceWorkbenchDialog`; no debe duplicar payload, emisión, descargas ni refresco. |
| ADR-030 | 2026-07-22 | Los Servicios Compuestos se representan con una relación normalizada padre-hijo y se expanden únicamente al crear el ETS. | [`../architecture/COMPOSITE_CATALOG_SERVICES.md`](../architecture/COMPOSITE_CATALOG_SERVICES.md) | Cotización/Facturación conservan el padre comercial; las hojas simples se vuelven partidas operativas y reutilizan sin cambios OT, Equipos, Hojas y Certificados. |
| ADR-031 | 2026-07-23 | El Master esperado se congela en `ServiceOrderItem` al crear el ETS y Equipos sólo consume esa partida; el alta del equipo conserva además un snapshot versionado del alcance, tipo de certificado, Master y origen operativo. | modelos/servicios de ETS y Equipos; migración `8c2d4e6f7a9b`; prueba de contexto de certificado | Renombrar o cambiar el catálogo después del ETS no altera equipos futuros del expediente. Los históricos se recuperan sólo mediante IDs persistentes y el equipo sigue siendo un evento de servicio apto para vincularse posteriormente a una identidad de activo separada. |
| ADR-032 | 2026-07-24 | El Motor de Resoluciones se implementa estrictamente por fases; sólo la fase activa puede recibir componentes y sólo se corrige deuda que contradiga una dependencia o gate de esa fase. Seguridad, servicios canónicos, idempotencia y separación de solicitud/autorización/ejecución se incorporan antes de la capacidad que los consume, nunca como deuda diferida después del efecto. | [`../architecture/resolution-engine/13_IMPLEMENTATION_MATRIX.md`](../architecture/resolution-engine/13_IMPLEMENTATION_MATRIX.md) y aprobación de Fase 0 | La deuda general del ERP no detiene el Motor; cada fase termina con validación, documentación, commit exclusivo y espera de aprobación. |
| ADR-033 | 2026-07-24 | Las extensiones del Motor se declaran como `ResolutionDefinition` inmutable, identificada por `resolution_type` namespaced y versión explícita, con referencias versionadas a sólo los componentes que necesita. `ResolutionRegistry` permite coexistencia histórica, selección activa explícita y congelamiento; el núcleo no contiene condicionales por tipo. | Implementación y pruebas de Fase 1; [`../closures/RESOLUTION_ENGINE_PHASE_1.md`](../closures/RESOLUTION_ENGINE_PHASE_1.md) | Agregar una resolución no modifica el núcleo. Los IDs del runtime son opacos y nunca sustituyen folios institucionales; persistencia y ejecución siguen fuera de alcance hasta sus fases. |
| ADR-034 | 2026-07-24 | La persistencia del Motor es un expediente general, versionado y reconstruible: congela tipo/versión de definición, snapshots y hashes; normaliza relaciones críticas; protege evidencia append-only; y representa sujetos/entidades sin columnas particulares de un caso de uso. El repositorio no administra transacciones ni lifecycle. | [`../architecture/resolution-engine/14_PERSISTENCE_SCHEMA.md`](../architecture/resolution-engine/14_PERSISTENCE_SCHEMA.md), migración `9d3e5f7a1b2c` y pruebas de Fase 2 | Nuevas resoluciones reutilizan el esquema sin reinterpretar históricos. Las estructuras de simulación, autorización, ejecución, idempotencia, locks y outbox no habilitan todavía comportamiento de fases posteriores. |
| ADR-035 | 2026-07-24 | Toda fase restante del Motor prioriza correctitud arquitectónica, mantenibilidad, legibilidad, extensibilidad y rendimiento, en ese orden; cada componente debe tener responsabilidad única y evitar abstracciones, herencia, metaprogramación u optimización innecesarias. | Directriz permanente incorporada en `AGENTS.md` al abrir la Fase 2 | Antes de cerrar una implementación se verifica que sea comprensible, comprobable, extensible, reemplazable y eliminable; una solución funcional que comprometa evolución o claridad debe rediseñarse. |
| ADR-036 | 2026-07-24 | La seguridad del Motor usa `ActorContext` independiente del ERP, permisos atómicos, políticas versionadas con deny-by-default, segregación configurable y evidencia append-only de concesiones/denegaciones. Toda autorización de plan se vincula a resolución, versión/hash de plan y simulación/hash exactos; adaptadores explícitos traducen la autoridad del host. | [`../architecture/resolution-engine/15_SECURITY_GOVERNANCE.md`](../architecture/resolution-engine/15_SECURITY_GOVERNANCE.md), migración `b4c6d8e0f2a3` y pruebas de Fase 3 | El núcleo no importa usuarios, roles, FastAPI ni módulos propietarios; una política restrictiva prevalece y la evidencia perteneciente a otra resolución se deniega antes de evaluar permisos. |
| ADR-037 | 2026-07-27 | El Lifecycle del Motor es la única autoridad de estado y usa una tabla explícita estado/acción con invariantes sobre evidencia reconstruida. La Fase 4 termina en `ready_for_execution`; orquestación selecciona componentes por tipo/versión, pero no ejecuta ni publica efectos. | [`../architecture/resolution-engine/16_LIFECYCLE_ORCHESTRATION.md`](../architecture/resolution-engine/16_LIFECYCLE_ORCHESTRATION.md) y pruebas de Fase 4 | Cada transición aumenta versión y agrega auditoría; artefactos se persisten antes de avanzar en la misma unidad de trabajo. Executor y publicación explícita corresponden a Fase 5; workers, retries y compensación permanecen posteriores. |
| ADR-038 | 2026-07-28 | La Fase 5 ejecuta sin mantener una transacción abierta durante el efecto propietario: primero persiste intención/idempotencia y después persiste el resultado. `ActionRunner` es el único invocador; un resultado incierto bloquea sin retry. La publicación outbox es explícita y su publicador debe ser idempotente por `event_key`. | [`../architecture/resolution-engine/17_EXECUTION_RUNTIME.md`](../architecture/resolution-engine/17_EXECUTION_RUNTIME.md) y pruebas de Fase 5 | Los adaptadores futuros implementan contratos sin entregar ORM al Motor. Recuperación, retries, compensación, schedulers y workers requieren otra fase aprobada; una operación `in_progress` no se repite automáticamente. |
| ADR-039 | 2026-07-28 | La exclusividad de una acción se acredita validando el lock después del handler y otra vez bajo lock de fila en el checkpoint. Su pérdida convierte cualquier resultado reportado en incierto/bloqueado. El `revalidation_id` preparado se valida optimistamente sin reselección. Las claves idempotentes son globales por scope interno y la futura API debe autorizarlas y namespaciarlas. | Revisión de Fase 5 y [`../architecture/resolution-engine/17_EXECUTION_RUNTIME.md`](../architecture/resolution-engine/17_EXECUTION_RUNTIME.md) | No se confirma un efecto sin token vigente, no se repite el handler, un cambio de revalidación impide iniciar y ningún actor futuro puede obtener replay sólo con conocer una clave. |
| ADR-040 | 2026-07-27 | La Fase 6 modela la compensación como un flujo síncrono separado dentro del expediente original: un plan inmutable referencia checkpoints confirmados, invierte orden/dependencias y se ejecuta sólo mediante `CompensationRunner`. Antes de persistir, toda selección parcial debe ser transitivamente cerrada respecto de dependientes confirmados activos; Lifecycle conserva la autoridad y la decisión de seguridad exacta se revalida antes de preparación, ejecución o replay. | [`../architecture/resolution-engine/18_COMPENSATION_ENGINE.md`](../architecture/resolution-engine/18_COMPENSATION_ENGINE.md), migración `d6e8f0a2b4c5` y pruebas de Fase 6 | No se reescribe la ejecución original, un efecto no se planifica dos veces ni se retira bajo dependientes activos, y perder exclusividad produce evidencia incierta sin reinvocación. Workers, retries, recuperación, conciliación y compensación automática requieren fases posteriores. |
| ADR-041 | 2026-07-27 | El dictamen final aprueba Fase 6 con `74a3de5` y `e1d373e`. Para las fases siguientes prevalecen los nombres/capacidades del roadmap: Fase 7 es Auditoría y Evidencia; la secuencia antigua de API/UC-001 de la matriz queda reemplazada. | Dictamen final de Fase 6, [`../architecture/resolution-engine/12_ROADMAP.md`](../architecture/resolution-engine/12_ROADMAP.md), matriz y [`../architecture/resolution-engine/19_PHASE_7_OPENING.md`](../architecture/resolution-engine/19_PHASE_7_OPENING.md) | Fase 7 permanece `NO INICIADA` hasta aprobar su apertura. API/SDK e integración ERP se conservan para fases posteriores y no pueden adelantarse. |
| ADR-042 | 2026-07-27 | La Fase 7 reutiliza el expediente general como única fuente de verdad y construye proyecciones read-only en vez de persistir un timeline paralelo. Toda consulta exige una decisión `resolution.audit.inspect` exacta y verifica el expediente completo antes de filtrar. Las nuevas decisiones de seguridad conservan su base canónica dentro del JSON existente; bases históricas ausentes se declaran `asserted`. | [`../architecture/resolution-engine/20_AUDIT_EVIDENCE.md`](../architecture/resolution-engine/20_AUDIT_EVIDENCE.md), código y pruebas de Fase 7 | No se requiere migración, no se altera Lifecycle ni se inventa evidencia histórica. API, ERP, workers, firma externa y analítica permanecen posteriores. |
| ADR-043 | 2026-07-27 | Cada reconstrucción de auditoría se materializa dentro de una transacción propia con snapshot estable: `REPEATABLE READ` en PostgreSQL y `SERIALIZABLE` con inicio explícito en SQLite. | Observación bloqueante de Fase 7, prueba concurrente y [`../architecture/resolution-engine/20_AUDIT_EVIDENCE.md`](../architecture/resolution-engine/20_AUDIT_EVIDENCE.md) | Las consultas SQL múltiples sólo pueden observar un expediente enteramente anterior o posterior a un commit concurrente; la proyección termina antes de cerrar el snapshot y Lifecycle permanece ajeno. |
| ADR-044 | 2026-07-27 | Fase 8 conserva `SecurityPolicyEvaluator` como única autoridad y agrega dentro de él un catálogo canónico de controles. Los límites críticos no reevalúan políticas: reutilizan `SqlAlchemySecurityDecisionVerifier` para comprobar la concesión append-only exacta antes de leer replays/expedientes o producir efectos. | [`../architecture/resolution-engine/21_PHASE_8_OPENING.md`](../architecture/resolution-engine/21_PHASE_8_OPENING.md), [`../architecture/resolution-engine/22_INTEGRAL_SECURITY.md`](../architecture/resolution-engine/22_INTEGRAL_SECURITY.md) y pruebas de Fase 8 | Lifecycle sigue decidiendo estados; orquestación pura continúa sin efectos; ejecución, compensación, auditoría y outbox quedan ligados a actor, organización, contexto y evidencia exactos. Fase 9 permaneció prohibida hasta la aprobación registrada por ADR-046. |
| ADR-045 | 2026-07-28 | Cada control declara `single_operation` o `reusable_read`. Las mutaciones se ligan a `operation_id` y hash del payload canónico y reservan un consumo append-only en la transacción del efecto; el replay exacto delega en la idempotencia vigente. Auditoría es la única concesión reutilizable y sólo para una consulta exacta vigente. | Observación bloqueante de Fase 8, [`../architecture/resolution-engine/22_INTEGRAL_SECURITY.md`](../architecture/resolution-engine/22_INTEGRAL_SECURITY.md), migración `f8a0b2c4d6e8` y suite concurrente | Una misma concesión no autoriza dos operaciones; rollback no quema la autorización; creación, Lifecycle y outbox vinculan respectivamente solicitud, versión y lote exactos sin evaluador paralelo. |
| ADR-046 | 2026-07-28 | La revisión formal aprueba Fase 8 mediante `73e437d` y `661f43a5cbba9070b1f02babd9ebbd5149f62b2b` y abre Fase 9 para integración incremental con ERP. Cada dominio conserva ownership; providers son read-only y los gateways consumen servicios canónicos. La IA permanece fuera del alcance actual y sólo puede ser una opción futura prescindible, nunca una dependencia del ERP o del Motor determinista. | Aprobación formal de Fase 8, [`../architecture/resolution-engine/13_IMPLEMENTATION_MATRIX.md`](../architecture/resolution-engine/13_IMPLEMENTATION_MATRIX.md) y [`../architecture/resolution-engine/23_PHASE_9_OPENING.md`](../architecture/resolution-engine/23_PHASE_9_OPENING.md) | Al abrirse, Fase 9 quedó `ACTIVA` sin caso vertical iniciado; ADR-047 registra el primer caso y ADR-049 su aprobación posterior. |
| ADR-047 | 2026-07-28 | El primer vertical de Fase 9 es `certificate.resolve_incorrect_release`. El Motor decide y coordina; Certificados conserva ownership y cambia únicamente la visibilidad mediante un servicio canónico. La evidencia propietaria es append-only, la operación es idempotente y su compensación restaura la visibilidad sólo sin deriva. | Autorización expresa del primer dominio, [`../architecture/resolution-engine/24_PHASE_9_CERTIFICATES_INTEGRATION.md`](../architecture/resolution-engine/24_PHASE_9_CERTIFICATES_INTEGRATION.md) y suite de integración | Al entregarse quedó `EN REVISIÓN`; ADR-048 registra su corrección y ADR-049 su aprobación. No se reemplaza la máquina operativa ordinaria de Certificados ni se incorpora IA. |
| ADR-048 | 2026-07-28 | El replay propietario de Certificados se resuelve por la operación append-only exacta antes de consultar el estado actual. Una primera ejecución usa lookup→lock→segundo lookup; una carrera de unicidad revierte al perdedor y sólo recupera el ganador exacto. La evidencia posterior se construye tras `flush/refresh`. | Observaciones bloqueantes de revisión de Fase 9, contrato `24` y suite concurrente | Replay permanece histórico ante deriva/inactividad, colisiones se deniegan y ejecución/compensación conservan atomicidad. No requiere migración: reutiliza la unicidad y trigger vigentes. |
| ADR-049 | 2026-07-28 | El dictamen final aprueba Fase 9 mediante `5abfe2d` y `901bd85` y abre Fase 10 — SDK y API Pública. La frontera pública será versionada y delgada: traduce a servicios vigentes, conserva seguridad/idempotencia y no expone internals. El SDK no replica reglas. | Dictamen final de Fase 9, roadmap, matriz y [`../architecture/resolution-engine/25_PHASE_10_OPENING.md`](../architecture/resolution-engine/25_PHASE_10_OPENING.md) | En el corte de apertura Fase 10 quedó `ACTIVA` sin implementación; ADR-050 registra su implementación posterior. Fase 11, distribución e IA continúan prohibidas. |
| ADR-050 | 2026-07-28 | La primera superficie pública es `/api/public/resolution-engine/v1`: contratos/errores estables, credencial local de consumidor ligada a una organización, creación por Lifecycle y consultas por auditoría. El SDK sólo importa contratos públicos y `httpx`. Simulación/ejecución/compensación no se exponen hasta contar con un contrato público completo. | [`../architecture/resolution-engine/26_PUBLIC_API_SDK.md`](../architecture/resolution-engine/26_PUBLIC_API_SDK.md), migración `a0d2f4b6c8e1` y suite Fase 10 | Implementación concluida y pendiente de aprobación; Fase 11 permanece no iniciada. |
| ADR-051 | 2026-07-28 | Los cursores públicos usan un sobre `c1` AES-GCM con nonce aleatorio y clave derivada por dominio. El ciphertext contiene identidad completa de consulta y posición keyset; se valida por igualdad exacta antes de paginar. El formato previo se revoca porque exponía el ID y no podía comprobar filtros/versión/orden originales. | Observación bloqueante de revisión, [`../architecture/resolution-engine/26_PUBLIC_API_SDK.md`](../architecture/resolution-engine/26_PUBLIC_API_SDK.md) y suite de Fase 10 | Se preservan keyset, rendimiento y futuras versiones seguras; Fase 10 fue aprobada posteriormente en `dd9a84e`. |
| ADR-052 | 2026-07-28 | La revisión formal aprueba Fase 10 mediante `dd9a84e` y abre Fase 11 — Motor Distribuido. API/SDK y contratos públicos quedan congelados; la distribución es interna y no reinterpreta Lifecycle, seguridad, auditoría, compensación ni históricos. | Aprobación formal de Fase 10 y [`../architecture/resolution-engine/27_PHASE_11_OPENING.md`](../architecture/resolution-engine/27_PHASE_11_OPENING.md) | Fase 11 queda autorizada; Fase 12 e IA continúan prohibidas. |
| ADR-053 | 2026-07-28 | La coordinación distribuida usa PostgreSQL como cola durable compartida: pull con `SKIP LOCKED`, capacidad por nodo, exclusividad por resolución, leases con token/versión, heartbeat, eventos append-only y backoff determinista. Recovery reencola sólo antes del posible efecto; después bloquea por incertidumbre. | [`../architecture/resolution-engine/28_DISTRIBUTED_RUNTIME.md`](../architecture/resolution-engine/28_DISTRIBUTED_RUNTIME.md), migración `c1e3f5a7b9d2` y suite de Fase 11 | Evita broker o máquina de estados paralelos, conserva handlers/servicios canónicos y permite escala horizontal. Fase 11 queda `EN REVISIÓN`. |
| ADR-054 | 2026-07-28 | La revisión formal aprueba Fase 11 mediante `cbde51783870e4b06a4de84c27e05dc2b5ea3de1` y abre Fase 12 — Centro de Resoluciones. La nueva superficie es una consola interna independiente; consume las capacidades vigentes y no modifica API pública, SDK, Domain Model ni reglas propietarias. | Aprobación oficial de Fase 11 y [`../architecture/resolution-engine/29_PHASE_12_RESOLUTION_CENTER.md`](../architecture/resolution-engine/29_PHASE_12_RESOLUTION_CENTER.md) | Fase 12 queda autorizada. Fase 13 e IA permanecen prohibidas. |
| ADR-055 | 2026-07-28 | El Centro separa proyección, workflow, transporte y worker. La autoridad por operación se confirma antes del enqueue y se serializa sin token/caducidad HTTP; el trabajo único por resolución continúa fuera de la sesión. Lista/expediente son proyecciones con aislamiento, cursor opaco y redacción por permisos. | Contrato `29`, API interna, migración `d2f4a6b8c0e3` y suite específica de Fase 12 | Evita una máquina frontend, lógica en routers, doble despacho y ownership de la sesión. Fase 12 queda `EN REVISIÓN`. |
| ADR-056 | 2026-07-28 | La revisión formal aprueba Fase 12 mediante `a7bf75f0f2de23faecb17276aa11d187c654a00c` y abre Fase 13 — Consolidación del Centro. La numeración entonces propuesta para IA fue reemplazada por ADR-058. | Aprobación oficial y contrato `30`; superada parcialmente por ADR-058 | Fase 13 quedó autorizada y posteriormente aprobada. |
| ADR-057 | 2026-07-28 | Toda integración del Centro registra definición canónica, metadata/presentación versionada, fábrica de solicitud e hidratación de snapshot. Frontend deriva campos del esquema cerrado y backend valida nuevamente. Indicadores y expediente son proyecciones; ejecución sigue en el worker/Executor canónicos. | `ResolutionCenterDefinitionRegistry`, contrato `30` y suite Fase 13 | Nuevos dominios no requieren formularios, routers o workflows específicos del Centro; no se duplica lógica ni se aceptan parámetros arbitrarios. |
| ADR-058 | 2026-07-29 | La revisión formal aprueba Fase 13 mediante `bb76e3bba9482517c9dfb870567d6bdfc7b9b135` y abre Fase 14 — Expansión institucional de integraciones. La IA deja de ocupar ese número y permanece como opción futura no autorizada. | Aprobación oficial, roadmap corregido y contrato `31` | Fase 14 queda autorizada sólo para composición institucional y segundo vertical determinista. Fase 15 no se abre. |
| ADR-059 | 2026-07-29 | `build_installed_resolution_integrations` es la única composición activa para Registry, Centro, worker y API pública. El segundo vertical es `service_order.resolve_additional_equipment@1.0`; usa conciliación persistente, lock del ETS, servicios propietarios sin commit interno y compensación conservadora. | [`../architecture/resolution-engine/31_PHASE_14_INTEGRATION_EXPANSION.md`](../architecture/resolution-engine/31_PHASE_14_INTEGRATION_EXPANSION.md), suite Fase 14 y migración `7b8c9d0e1f2a` | El Centro y frontend no agregan ramas por dominio; efectos sólo después de autorización/revalidación y nunca reescriben evidencia consumida. |
| ADR-060 | 2026-07-29 | Pagos se integra exclusivamente dentro del Resumen financiero de `InvoiceWorkbenchDialog`; no existe pestaña, controlador, modelo ni cálculo paralelo. El controlador único registra/refresca `Invoice`, descarga el recibo existente y notifica al ETS para volver a consultar readiness. Cuentas por cobrar permanece en el Dashboard vigente y abre el mismo expediente. | [`../architecture/INVOICE_WORKBENCH_CONTROLLER.md`](../architecture/INVOICE_WORKBENCH_CONTROLLER.md), servicios/endpoints existentes y cierre de integración de pagos | Conserva `Invoice` como fuente de verdad, respeta `payments.manage`, permite prepago y evita que el timbrado sobrescriba `partially_paid`/`paid`. |
| ADR-062 | 2026-07-29 | La primera excepción contextual de Ventas usa un expediente acotado con folio `EXV-…` para solicitar, autorizar y consumir una única reconstrucción controlada de una cotización aprobada. La experiencia identifica Cotización/ETS por `MYC-…`/`OSMYC-…`, nunca por IDs internos, congela la revisión anterior, permite editar directamente las partidas y reconstruye físicamente sólo un ETS realmente virgen conservando su folio visible. La segregación sigue siendo la regla; un actor con autoridad explícita `self_authorize_unlock` puede autorizar en el mismo comando. Administrador la obtiene por `*`, sin pedir permiso a otro usuario. | [`../architecture/sales/QUOTATION_CONTROLLED_UNLOCK.md`](../architecture/sales/QUOTATION_CONTROLLED_UNLOCK.md) y suite específica | Mantiene revalidación transaccional, snapshots, Actividad, auditoría y notificaciones; la autoautorización queda explícita y auditable y no abre otra fase, definición ni máquina del Motor. |
| ADR-063 | 2026-07-29 | En el desbloqueo controlado de Cotizaciones, Administrador puede compactar solicitud y autoautorización bajo la capacidad explícita del dominio. La aplicación de esta regla a las excepciones ETS queda sustituida por ADR-065. | UI contextual de Cotizaciones, arquitectura de desbloqueo y pruebas frontend | La excepción comercial conserva su contrato propio; no autoriza ejecución directa en ETS. |
| ADR-064 | 2026-08-04 | El Catálogo Institucional Funcional versión 1.0 queda aprobado y congelado como autoridad funcional con 42 módulos, 181 acciones y 657 microacciones, todas clasificadas por naturaleza, criticidad y alcance permitido. | [`../architecture/CATALOGO_INSTITUCIONAL_FUNCIONAL_ERP_MYC.md`](../architecture/CATALOGO_INSTITUCIONAL_FUNCIONAL_ERP_MYC.md) y cierre institucional 2026-08-04 | Las microacciones aprobadas son estables; un cambio de significado exige deprecación, nueva microacción y trazabilidad histórica. No implementa RBAC ni modifica permisos vigentes. |
| ADR-065 | 2026-08-10 | Las reglas de órdenes de servicio residen únicamente en `services/service_orders.py`. Una excepción ETS se persiste como expediente acotado y sólo puede producir efectos mediante acciones separadas `requested → authorized → executed`; solicitud/autorización no mutan ETS ni Invoice y ejecución revalida el estado congelado. El mismo Administrador puede realizar las tres acciones, sin compactar transiciones ni evidencias. No se abre una vertical nueva del Motor de Resoluciones. | Sprint Integridad ETS, migración `e7b62b8a9421`, suite `test_service_order_integrity.py` | El router queda limitado al contrato HTTP y actor; las mutaciones críticas exigen actor en su firma y en runtime. La persistencia mínima evita usar auditoría como estado o duplicar el Motor, y conserva audit log/Actividad en la transacción propietaria. |
| ADR-066 | 2026-08-10 | Calidad es la única superficie funcional de autenticación y `certificate_authentication.authenticate_certificate` es la autoridad transaccional única. ETS pierde endpoint, lote y acciones; el adapter de Certificados usa `certificates.approve`, actor y origen `quality`. La autoridad bloquea la fila y conserva generación, estado, audit, evento y commit juntos. | Cierre P0 de Integridad de Autenticación, BR-014 y suites backend/frontend | Evita doble autenticación concurrente y divergencia de commits/permisos. Liberación continúa como decisión posterior y el Motor sólo gobierna visibilidad extraordinaria, sin autenticar. |
| ADR-067 | 2026-08-11 | El capability gate mide drift frente a un baseline gobernado, no exige borrar las 19 diferencias de compatibilidad de Etapa 2B. Portal reutiliza la capacidad funcional `portal.read`; `reference_standard_certificates.delete` entra al bootstrap sólo para Calidad/Desarrollador y Administrador por comodín. Las familias críticas H no se granularizan sin decisión institucional. | Sprint TD-027, Catálogo Funcional 1.0, snapshot 2B y matriz del cierre | Gate verde 19/0 sin ampliar catálogo ni privilegios; TD-027 queda bloqueado por las decisiones de granularización, excepciones ETS y autenticación. |
| ADR-068 | 2026-08-12 | El ETS múltiple/evolucionado extiende `ServiceOrder` con `ServiceUnit` y `ServiceStage`; no crea ETS por categoría ni reemplaza `Equipment`. La OT permanece estable durante una intervención. Cotización conserva la autoridad comercial mediante decisiones append-only por partida y Activity sigue siendo el único canal contextual. | [`../architecture/ETS_MULTIPLE_EVOLVED_CORE.md`](../architecture/ETS_MULTIPLE_EVOLVED_CORE.md), migración `f4a1c9d2e710` y suite Fase 1 | Permite múltiples equipos, categorías iniciales y evolución sin borrar historia; Fase 1 queda en revisión y no autoriza workflows técnicos posteriores ni nuevas excepciones. |
| ADR-069 | 2026-08-12 | El acceso móvil técnico es un namespace backend read-only separado que reutiliza identidad interna, permisos explícitos y ownership relacional. No altera rutas web ni duplica `technician_id` en recursos hijos. | [`../architecture/MOBILE_TECHNICIAN_ACCESS.md`](../architecture/MOBILE_TECHNICIAN_ACCESS.md), inventario API y suite de aislamiento | Ocho endpoints quedan acotados por técnico; sesiones móviles, permisos individuales y asignación multi-técnico permanecen fuera de alcance. |
| ADR-070 | 2026-08-12 | La capacidad evolutiva es una propiedad persistida de `ServiceUnit`, derivada de su `ServiceOrderItem` origen, no una propiedad global del ETS ni de la etapa actual. La solicitud técnica y el lifecycle de etapa son autoridades separadas. La decisión interna deriva actor/origen, valida categorías contra solicitud y catálogo, y una restricción única protege append-only bajo concurrencia. | [`../architecture/ETS_MULTIPLE_EVOLVED_CORE.md`](../architecture/ETS_MULTIPLE_EVOLVED_CORE.md), migración `a7c2e5f8b1d4` y suite Fase 1 endurecida | Cierra contaminación de Servicio General, bypass de lifecycle, payloads comerciales manipulados y doble decisión inicial sin abrir Fase 2 ni crear RBAC/portal paralelos. |
| ADR-071 | 2026-08-13 | Las OT LAB son un agregado temporal aislado. Todas las OT raíz/adicionales de una captura forman un grupo y comparten exactamente una sesión de firma con dos binarios; firmar bloquea el grupo y finalizar genera un PDF por OT. | [`../architecture/LAB_WORK_ORDERS.md`](../architecture/LAB_WORK_ORDERS.md), migración `c6e8a1b4d2f9` y suite LAB | Es una excepción acotada a ADR-004: no cambia ciclos de firma productivos; permite retirar el LAB después de una exportación verificada. |
| ADR-072 | 2026-08-17 | La eliminación definitiva productiva recae sobre `ServiceWorkOrder`, no sobre el ETS ni sobre `LabWorkOrder`. Usa el servicio propietario ETS, permiso exacto administrativo, locks y una sola transacción; elimina ownership exclusivo, desacopla referencias anulables que deben conservarse y retiene auditoría mínima/ciclos compartidos. Los archivos se someten a staging reversible ligado al commit. MYC Mobile no consume este endpoint en la fase LAB. | [`../architecture/WORK_ORDER_DELETION.md`](../architecture/WORK_ORDER_DELETION.md) y suites de eliminación | Evita cascadas globales, borrado accidental de facturas/firmas compartidas y estados parciales; los dominios productivo y LAB permanecen aislados. |
| ADR-073 | 2026-08-17 | Comunicaciones conserva REST como fuente de verdad y añade WebSocket sólo para eventos. `RealtimeHub` separa el contrato del adaptador inicial en memoria; la identidad usa access JWT y usuario revalidado en base, y cada room de conversación exige ownership. | [`../architecture/COMMUNICATIONS_REALTIME.md`](../architecture/COMMUNICATIONS_REALTIME.md), backend y pruebas Etapa A | Permite integrar MYC Mobile sin segundo backend ni esquema. El adaptador no autoriza producción multi-worker; confirmar topología y sustituirlo por backplane si corresponde. |
| ADR-074 | 2026-08-17 | La eliminación administrativa móvil se implementa exclusivamente sobre `LabWorkOrder` con `lab_work_orders.delete`; no reutiliza `service_orders.delete` ni rutas productivas. La OT es el ownership exclusivo; grupo, firma y tickets/revisiones pueden ser compartidos y se conservan/reparentan cuando sobreviven hermanas. PDFs y firmas LAB viven en base, por lo que toda la eliminación es una transacción sin staging de filesystem. | [`../architecture/LAB_WORK_ORDERS.md`](../architecture/LAB_WORK_ORDERS.md), router/servicio LAB y pruebas | Corrige la mezcla de dominios, mantiene folios 6400–6999 y permite eliminar raíz/intermedia/finalizada sin romper cadena, historial o firma compartida. |
| ADR-075 | 2026-08-17 | Comunicaciones persiste secuencia, idempotencia, recibos y menciones en PostgreSQL; REST reconcilia y WebSocket sólo publica eventos post-commit. La topología productiva verificada tiene un único worker, por lo que `InMemoryRealtimeHub` es el adaptador vigente; escalar procesos exige sustituirlo detrás de `RealtimeHub` antes del despliegue. | [`../architecture/COMMUNICATIONS_REALTIME.md`](../architecture/COMMUNICATIONS_REALTIME.md), migración `f7c9d1e3a5b7` y cierre A–I | Evita estados paralelos, pérdida/duplicación visible y acoplamiento del dominio al transporte; mantiene explícita la compuerta de escala. |

## Decisiones expresamente no confirmadas

- Implementar CRM/Leads, Agenda y Llamados autónomos dentro de 1.0.
- Incluir Google Drive en 1.0.
- Habilitar el diseñador MDE o sustituir todos los PDFs existentes.
- Retirar modelos metrológicos ocultos o declararlos obsoletos sólo porque hoy no tienen datos.

Estas cuestiones deben resolverse modificando [`CURRENT_SCOPE.md`](CURRENT_SCOPE.md); ningún documento histórico puede resolverlas por inferencia.
## ADR-061 — Actividad es infraestructura transversal independiente

**Decisión:** toda conversación interna nueva se implementa con un hilo único
por entidad y el panel reutilizable de Activity. El dominio propietario conserva
sus datos y publica sólo eventos formales idempotentes. Notifications distribuye
avisos; Communications continúa como mensajería independiente. Resoluciones se
adaptan por `public_id` desde Activity sin modificar Motor/API/SDK.

**Motivo:** evitar notas paralelas, duplicación de reglas, acoplamiento al Motor
y pérdida de trazabilidad.

**Fecha:** 2026-07-29.
## D-2026-07-29 — Revisión completa y reconstrucción del ETS virgen

Se sustituye el cambio puntual de servicio por edición directa de la misma
cotización bajo capacidad temporal. Las diferencias se determinan entre
revisiones y no mediante mutaciones parciales del snapshot anterior.

El ETS virgen se elimina físicamente y se recrea con su mismo folio; la
evidencia vive en cotización, expediente, auditoría y Actividad. Los contadores
institucionales se centralizan por tipo/prefijo/año. Esta decisión no amplía el
Motor de Resoluciones ni autoriza reconstruir ETS con operación.

## D-2026-08-03 — Contención transversal deny-by-default

Toda ruta HTTP se clasifica en un registro central introspectable y se protege
al incluir el router. Las excepciones públicas son una allowlist pequeña; el
Motor público conserva su autenticación de consumidor y la verificación de
certificados conserva su código firmado. Una ruta no clasificada falla al
arrancar y en pruebas.

El portal reutiliza el access JWT sólo junto con una frontera adicional: rol
Cliente, `portal.read`, cliente único derivado en backend y ownership por
recurso. En esta etapa sin migraciones, el vínculo se resuelve por correo
principal/contacto activo y cualquier ambigüedad falla cerrada. Producción
rechaza secretos JWT inseguros; el frontend usa permisos efectivos sólo para
presentación y el backend conserva toda autoridad.

## D-2026-08-04 — Autoridad de portal y administración futura de permisos

La Etapa 1 queda aprobada con su contención sin migraciones. La coincidencia
normalizada por correo principal/contacto continúa únicamente como puente
fail-closed de compatibilidad: no será la autoridad definitiva del portal. La
siguiente etapa debe migrar a una relación persistente y auditable
`User`–`PortalMembership`–`Client`; el cliente efectivo seguirá resolviéndose
en backend y nunca desde un `client_id` suministrado por el consumidor.

La autoridad administrativa futura se gestionará desde Ajustes mediante:

- roles y grupos como conjuntos de permisos;
- múltiples roles o grupos por usuario;
- concesiones y denegaciones individuales;
- alcances por registro;
- permisos temporales;
- protección de roles y capacidades críticas.

`backend/app/core/permissions.py` queda reconocido como bootstrap ejecutable y
compatibilidad temporal, no como el modelo administrativo definitivo. El
archivo
[`../architecture/CATALOGO_INSTITUCIONAL_CAPACIDADES_PERMISOS_ERP_MYC_2026-08-04.md`](../architecture/CATALOGO_INSTITUCIONAL_CAPACIDADES_PERMISOS_ERP_MYC_2026-08-04.md)
se conserva como snapshot técnico reproducible de ETAPA 2B. La autoridad
funcional propuesta pasa a
[`../architecture/CATALOGO_INSTITUCIONAL_FUNCIONAL_ERP_MYC.md`](../architecture/CATALOGO_INSTITUCIONAL_FUNCIONAL_ERP_MYC.md):
ninguna clave, alcance o microacción se traslada automáticamente al código sin
aprobación institucional, reconciliación con el inventario ejecutable y
aprobación arquitectónica.

Esta decisión no implementa Ajustes, modelos, migraciones ni claves nuevas; es
un mandato de diseño para una etapa separada y no un defecto no atendido del
alcance cerrado de Contención de Seguridad Etapa 1.

## D-2026-08-04 — Integridad reproducible de esquema y recuperación

Toda evolución de persistencia debe conservar un head único, `alembic check`
limpio, ciclo PostgreSQL `base→head→base→head`, upgrade desde respaldo histórico
y restore del respaldo oficial. Los índices PostgreSQL especializados se
declaran como propiedad explícita de migración para impedir propuestas
destructivas de autogenerate; los índices ORM portables sí deben materializarse.
Una revisión sólo revierte los objetos que posee.

## D-2026-08-04 — Gobierno previo de capacidades

Antes de implementar funcionalidad o permiso nuevo es obligatorio clasificar
`Módulo→Acción→Microacción`. El flujo vinculante es Catálogo Institucional →
revisión funcional → permiso institucional → `permissions.py` → roles/grupos →
usuarios. El catálogo es autoridad funcional y no generador de código;
`permissions.py` permanece bootstrap. El modelo posterior deberá soportar
roles/grupos múltiples, herencia, allow/deny individual, ownership, scopes,
temporalidad, capacidades protegidas y `PortalMembership` persistente.

## D-2026-08-04 — Separación entre snapshot técnico y autoridad funcional

El inventario de 36 superficies, 305 operaciones HTTP y 493 campos permanece
congelado como evidencia reproducible de ETAPA 2B. La autoridad funcional se
define por intención de negocio, no por endpoints o schemas, y adopta 42
módulos, 181 acciones y 657 microacciones explícitas. Campos calculados,
identificadores, timestamps, validaciones y efectos automáticos no son permisos
independientes. Las capacidades futuras se reservan sin ampliar alcance. Esta
decisión no renombra claves actuales ni autoriza implementación antes de la
aprobación institucional y la matriz de compatibilidad.

## D-2026-08-04 — Aprobación y congelamiento del Catálogo Institucional Funcional

Se aprueba como autoridad funcional la versión 1.0 del catálogo con 42 módulos,
181 acciones y 657 microacciones. Cada microacción declara naturaleza,
criticidad y uno o más alcances permitidos. El estado del registro permanece
como precondición funcional independiente y no forma parte del alcance. Los
efectos automáticos usan naturaleza `efecto automático` y alcance `no aplica`.

Toda microacción aprobada es estable. Si cambia su significado no puede
reutilizarse silenciosamente: debe marcarse como deprecada, crearse una nueva
microacción y conservarse la trazabilidad histórica. Una corrección editorial
sólo conserva el identificador cuando no cambia significado, naturaleza,
criticidad, alcance ni relación funcional.

Esta aprobación no crea roles, asignaciones o permisos; no implementa RBAC
dinámico; no modifica `permissions.py`; y no altera backend, frontend, modelos,
migraciones ni datos. La traducción a controles ejecutables continúa siendo
una etapa posterior y separada.

## D-2026-08-04 — Frontera institucional de archivos y cargas

Toda entrada de archivo no confiable debe validarse mediante un perfil central
antes de parsearse o persistirse. El perfil define formatos, MIME y límites; la
validación comprueba nombre, firma/estructura y, para ZIP/Office, expansión,
miembros, profundidad, cifrado, enlaces y rutas. Una escritura persistente se
publica atómicamente dentro de `STORAGE_ROOT` y produce SHA-256.

La ruta no concede acceso. Identidad, permiso, ownership, tenant, visibilidad y
estado continúan bajo el servicio propietario y se revalidan antes de la
frontera final de entrega. Los archivos operativos, respaldos y paquetes
generados no se versionan en Git; retirarlos del índice no autoriza borrarlos ni
reescribir historia. Esta decisión no crea permisos, modelos o migraciones y no
implementa almacenamiento remoto ni antivirus externo.

## D-2026-08-04 — Identidad, membresía y autoridad del Portal del Cliente

El Portal del Cliente usa cuentas `client_portal`, autenticación y tokens con
contexto propio; una cuenta externa no puede entrar por el autenticador interno.
La única autoridad de ámbito es `User → ClientPortalMembership activa →
client_id`. La coincidencia de correo con Cliente o Contacto queda retirada como
mecanismo de acceso y ningún endpoint del portal acepta un `client_id` del
consumidor para decidir ownership.

Los roles y permisos del portal permanecen separados del RBAC interno, se
normalizan mediante `ClientPortalRolePermission` y
`ClientPortalMembershipRole`, y no admiten excepciones individuales en esta
entrega. Una empresa puede tener varias cuentas y cada membresía varios roles;
el último administrador activo no puede retirarse. Los tokens de verificación e
invitación se conservan exclusivamente como hash y son de un solo uso.

## D-2026-08-05 — Administración unificada de cuentas y estado de acceso

La administración visual reúne usuarios internos, cuentas externas, registros,
solicitudes e invitaciones, pero conserva separados sus dominios y roles. Toda
mutación organizacional se ejecuta mediante endpoints de negocio de membresía,
vinculación o invitación; un formulario genérico nunca cambia el cliente.

`User.status` es la autoridad funcional y `is_active` su reflejo de
habilitación. `role_id` continúa únicamente como compatibilidad primaria; la
relación `user_roles` es la autoridad multirrol. El bloqueo de autenticación se
centraliza en una política común de cinco intentos y quince minutos, con
auditoría y respuesta genérica para los contextos interno y del portal.

## D-2026-08-14 — Reapertura versionada del LAB

Se adopta `OperationalTicket` como solicitud extensible y
`LabWorkOrderRevision` como snapshot documental, sin conectar el LAB al ETS
productivo. Aprobar el Ticket es el único camino de reapertura. La política
humana de preservación queda subordinada a una clasificación determinista
backend. Se preserva el folio y se versionan PDF/sesión de firma; auditoría no
es el almacenamiento único del lifecycle.

## D-2026-08-14 — Notificaciones persistentes y Expo best-effort

Se extiende el modelo `Notification` existente y se agrega `PushDevice`; no se
crea una bandeja paralela. El evento y su notificación se confirman junto con
la transición de dominio, y Expo se invoca sólo después del commit. Como el
repositorio no tiene una cola genérica canónica, V1 usa un intento síncrono
best-effort acotado; no reutiliza el outbox/worker del Motor de Resoluciones,
cuya responsabilidad es exclusiva del Motor. La app invalida recursos por
eventos y lifecycle de navegación, sin polling. Cola durable, receipts y
preferencias requieren una fase posterior explícita.
