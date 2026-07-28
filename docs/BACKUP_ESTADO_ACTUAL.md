> Estado: VIGENTE
>
> Tipo: Vigente (estado operativo)
>
> Autoridad: Media; resumen verificable de operación, migraciones y validaciones
>
> Prevalece sobre: versiones anteriores de este mismo corte operativo
>
> No sustituye a: `project/PROJECT_STATUS.md` para avance ni a `project/DOCUMENTATION_INDEX.md` para jerarquía
>
> Historial anterior: `archive/project/BACKUP_ESTADO_ACTUAL_HISTORICO_2026-07-21.md`
>
> Corte actualizado: 2026-07-27

# Estado operativo actual del ERP MYC

## Estado general

- Versión declarada del ERP: `0.4.0`.
- Estado de avance autorizado: [`project/PROJECT_STATUS.md`](project/PROJECT_STATUS.md).
- Único módulo `SELLADO`: Control Documental V1.
- Equipos permanece `CASI SELLADO`: la trazabilidad del Master quedó desacoplada del catálogo vivo; continúan pendientes la protección uniforme del router y el E2E autenticado multi-OT.
- Riesgos prioritarios transversales: autorización general de APIs y portal,
  secreto JWT de despliegue, duplicación material en ETS y autenticación de
  certificados duplicada fuera de Calidad. La escalación por registro y el uso
  de refresh como access quedaron corregidos.

## Persistencia, migración y respaldo

- Motor: PostgreSQL con SQLAlchemy y Alembic.
- Revisión aplicada y único head verificado: `f8a0b2c4d6e8`.
- `9d3e5f7a1b2c` agrega las 21 tablas del modelo persistente del Motor de
  Resoluciones, sus constraints, índices y triggers de inmutabilidad. Su revisión
  padre `8c2d4e6f7a9b` conserva el snapshot operativo de Equipos.
- `b4c6d8e0f2a3` agrega `resolution_security_decisions`, elimina once FKs del
  Motor a `users.id` y migra identidad/autoridad a actor canónico, funciones y
  snapshots.
- `c5d7e9f1a3b4` agrega exclusivamente
  `resolution_outbox_events.failed_at` para conservar evidencia temporal de
  fallos de publicación.
- `d6e8f0a2b4c5` amplía los estados raíz y agrega cuatro tablas generales de
  compensación con FKs exactas, unicidad de efecto, índices y protección
  histórica.
- `e7f9a1b3c5d7` vincula decisiones de seguridad con revalidación exacta y
  ejecuciones con su decisión institucional mediante FKs compuestas,
  constraint de completitud e índice; las columnas son nulas para históricos.
- `f8a0b2c4d6e8`, después de `fabc2cd495ef`, agrega modo, identidad,
  payload/hash y consumo append-only de operación, además de congelar el lote
  exacto de outbox.
- El backfill histórico usa únicamente `service_order_items.catalog_item_id`, `quotation_items.catalog_item_id` o `equipment.certificate_master_document_id`; no compara nombres.
- Respaldo vigente: `backup_erp_myc_antes_prueba.sql`.
- Tamaño verificado: 74,213,207 bytes.
- SHA-256 verificado: `763b5b262632d06d8bb6eb4433038c1f3009aa2da4e237867fae32c04901db96`.
- El respaldo contiene `alembic_version = f8a0b2c4d6e8`.

## Equipos y contexto de certificado

- Al crear el ETS, cada partida operativa congela el `expected_certificate_master_id` correspondiente a su identidad estable de catálogo.
- Al dar de alta un equipo, `backend/app/services/equipment.py` consume exclusivamente ese valor de `ServiceOrderItem`; no importa `CatalogItem`, no consulta por `service_name` y no reabre la resolución en el catálogo.
- El snapshot de equipo conserva el Master documental y su versión/archivo/hash/vigencia, además de un contexto JSON versionado con alcance, tipo de certificado, Master esperado, partida ETS y concepto operativo de origen.
- El certificado esperado sigue generándose automáticamente con el mismo mapeo: `accredited_iso_17025 → acreditado`, `traceable → trazable`, `accredited_linked_lab → vinculado`.
- El contador de avance usa internamente `FINISHED_STATUSES = {calibrated, labeled, not_done}`. No cambiaron estados, transiciones ni semántica operativa.
- No se implementó historial transversal de activos. El equipo continúa siendo una ocurrencia del servicio y conserva serie/ID interno sin unicidad global, permitiendo enlazar en el futuro una identidad de activo separada sin reescribir históricos.

## Validaciones ejecutadas

- Suite backend completa fuera del sandbox: 306 pruebas y 19 subpruebas
  correctas, 19 fallos y dos advertencias. Los 19 fallos provienen del `JSONB`
  no portable del módulo Actividad al crear metadata SQLite (`TD-023`), fuera
  del alcance del Motor; LibreOffice pasa fuera del sandbox.
- Suite específica de Fase 8: 15 pruebas correctas.
- Suite completa del Motor: 201 pruebas correctas, incluidas creación,
  transiciones válidas/inválidas, invariantes, autorización exacta,
  revalidación, concurrencia, persistencia, ejecución, compensación,
  arquitectura, esquema y migraciones.
- Frontend: 11 pruebas correctas y build Vite de producción correcto; permanece
  la advertencia preexistente por tamaño del chunk principal.
- Compilación de bytecode Python: correcta.
- PostgreSQL: `f8a0b2c4d6e8` aplicó, revirtió a `fabc2cd495ef` y reaplicó a
  head correctamente.
- `alembic heads/current`: único head `f8a0b2c4d6e8`.
- `alembic check` continúa reportando sólo la deriva histórica ajena registrada
  como `TD-021`; no propone operaciones sobre el esquema del Motor.
- `git diff --check`: correcto.
- El respaldo SQL fue regenerado después de aplicar la migración y su
  `alembic_version` coincide con head.

## Pendientes vigentes

1. Ejecutar el E2E autenticado de Equipos dentro de un expediente multi-OT con datos representativos.
2. Aplicar autorización deny-by-default y permisos explícitos al router de Equipos.
3. Resolver las deudas transversales vigentes en [`project/TECHNICAL_DEBT.md`](project/TECHNICAL_DEBT.md).
4. Implementar historial de activos sólo cuando se incorpore formalmente al alcance; no pertenece a esta entrega.

## Documentación y trazabilidad

- Entrada única: [`project/DOCUMENTATION_INDEX.md`](project/DOCUMENTATION_INDEX.md).
- Estado de módulos: [`project/PROJECT_STATUS.md`](project/PROJECT_STATUS.md).
- Reglas: [`project/BUSINESS_RULES.md`](project/BUSINESS_RULES.md).
- Decisiones: [`project/DECISIONS.md`](project/DECISIONS.md).
- Observaciones: [`project/OBSERVATIONS_REGISTER.md`](project/OBSERVATIONS_REGISTER.md).
- Contrato de alcance: [`architecture/CALIBRATION_SCOPE_CONTRACT.md`](architecture/CALIBRATION_SCOPE_CONTRACT.md).
- Plantillas Maestras: [`modules/control-documental/PLANTILLAS_MAESTRAS.md`](modules/control-documental/PLANTILLAS_MAESTRAS.md).

## Motor de Resoluciones — Fase 8

- Estado: Fases 0 a 7 `APROBADAS`; Fase 8 — Seguridad integral
  `EN REVISIÓN`; Fase 9 `NO INICIADA`.
- El Motor conserva expediente, seguridad, Lifecycle y ejecución aprobados e
  incorpora modelo/Engine, Planner, Executor, Runner, contratos, persistencia
  y evidencia de compensación total/parcial síncrona.
- Sólo inicia desde `ready_for_execution` con plan activo `authorized`,
  autorización y revalidación exactas. Los cierres posibles son `completed`,
  `partially_completed`, `failed` y `blocked`.
- Sólo checkpoints originales `completed` y declarados compensables forman un
  plan. La estrategia total cubre todos; la parcial exige selección explícita;
  un punto de no retorno impide el flujo ordinario.
- La decisión `resolution.compensate` debe pertenecer a ejecución, resolución,
  organización y actor exactos. Se comprueba también antes de preparación,
  ejecución y replay.
- Lifecycle transita `completed|partially_completed|failed → compensating →
  compensated|partially_compensated|compensation_failed`; ningún handler
  modifica la raíz.
- Cada acción persiste intención antes del handler y resultado después. El lock
  se comprueba al volver y en el checkpoint; pérdida o incertidumbre bloquean
  sin confirmar ni reinvocar.
- Plan hash, claves de preparación/ejecución/paso y unicidad del checkpoint
  fuente impiden conflicto, replay ajeno y compensación duplicada.
- Una selección parcial debe incluir todos los dependientes confirmados activos,
  directos o transitivos. La infracción se rechaza antes de persistir con error
  estructurado; efectos sin confirmar o ya compensados no bloquean.
- El outbox se publica sólo mediante una invocación explícita autorizada,
  aislada por organización y un publicador idempotente por `event_key`; un
  fallo conserva `failed_at`, intentos y error, sin scheduler ni reintento.
- La clave idempotente interna tiene namespace global por scope. Una futura API
  deberá autorizarla y namespaciarla por cliente/organización antes de construir
  el comando interno.
- No se incorporaron API, gateways concretos, integraciones propietarias,
  workers, schedulers, procesamiento masivo, recuperación, conciliación,
  retries ni compensación automática.
- La Fase 7 incorpora modelo puro, `AuditEngine`, `EvidenceRegistry`,
  `ResolutionTimeline`, consultas autorizadas y adaptador SQL read-only.
  Verifica pertenencia, hashes reproducibles, vínculos exactos y secuencia; no
  cambia Lifecycle, ejecución, compensación ni outbox.
- La reconstrucción completa se materializa en un único snapshot transaccional:
  `REPEATABLE READ` en PostgreSQL y `SERIALIZABLE` explícito en SQLite. La
  prueba concurrente confirma que una transición intercalada nunca produce un
  expediente híbrido.
- Fase 8 agrega el catálogo integral dentro del evaluador de Fase 3. Lifecycle,
  ejecución, compensación, auditoría y outbox comparten un único verificador de
  decisiones persistidas y deniegan antes de replay, lectura o efecto.
- El catálogo `1.1` declara `single_operation` para mutaciones y
  `reusable_read` sólo para auditoría exacta. Creación liga `request_key` e
  intención completa, Lifecycle incluye estado/versión y outbox congela IDs.
  El consumo se confirma con la transacción; rollback no quema la concesión.
- La autenticación futura/expirada, permisos fuera de contexto, downgrade de
  permiso, recursos falsos y evidencia/hash alterados se rechazan.
- Validaciones: 15 pruebas específicas; 45 pruebas específicas/arquitectónicas;
  201 pruebas del Motor; backend completo con 306 pruebas y 19 subpruebas
  correctas y 19 fallos ajenos registrados como `TD-023`; 11
  pruebas frontend; build Vite y compilación Python correctos.
- La migración reversible `f8a0b2c4d6e8` fue probada en
  upgrade→downgrade→upgrade. `alembic check` sólo muestra la deriva histórica
  `TD-021` y ninguna operación `resolution_*` adicional atribuible a Fase 8.
- El respaldo SQL fue regenerado y coincide con el head.
- Apertura aprobada de Fase 8:
  [`architecture/resolution-engine/21_PHASE_8_OPENING.md`](architecture/resolution-engine/21_PHASE_8_OPENING.md).
- Contrato:
  [`architecture/resolution-engine/22_INTEGRAL_SECURITY.md`](architecture/resolution-engine/22_INTEGRAL_SECURITY.md).
- Cierre:
  [`closures/RESOLUTION_ENGINE_PHASE_8.md`](closures/RESOLUTION_ENGINE_PHASE_8.md).
