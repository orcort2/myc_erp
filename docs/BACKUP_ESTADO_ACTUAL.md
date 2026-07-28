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
- Revisión aplicada y único head verificado: `f9c1d3e5a7b9`.
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
- `f9c1d3e5a7b9` agrega la evidencia propietaria append-only
  `certificate_resolution_operations`, sus constraints, índices y trigger de
  inmutabilidad para el primer vertical de Fase 9.
- El backfill histórico usa únicamente `service_order_items.catalog_item_id`, `quotation_items.catalog_item_id` o `equipment.certificate_master_document_id`; no compara nombres.
- Respaldo vigente: `backup_erp_myc_antes_prueba.sql`.
- Tamaño verificado: 74,218,048 bytes.
- SHA-256 verificado: `1c0c5ed0bd6b8a93acd7d98c665d997ed1a6ef3808958486088c1315154a9dca`.
- El respaldo contiene `alembic_version = f9c1d3e5a7b9`, la tabla propietaria
  y `trg_certificate_resolution_operations_immutable`.

## Equipos y contexto de certificado

- Al crear el ETS, cada partida operativa congela el `expected_certificate_master_id` correspondiente a su identidad estable de catálogo.
- Al dar de alta un equipo, `backend/app/services/equipment.py` consume exclusivamente ese valor de `ServiceOrderItem`; no importa `CatalogItem`, no consulta por `service_name` y no reabre la resolución en el catálogo.
- El snapshot de equipo conserva el Master documental y su versión/archivo/hash/vigencia, además de un contexto JSON versionado con alcance, tipo de certificado, Master esperado, partida ETS y concepto operativo de origen.
- El certificado esperado sigue generándose automáticamente con el mismo mapeo: `accredited_iso_17025 → acreditado`, `traceable → trazable`, `accredited_linked_lab → vinculado`.
- El contador de avance usa internamente `FINISHED_STATUSES = {calibrated, labeled, not_done}`. No cambiaron estados, transiciones ni semántica operativa.
- No se implementó historial transversal de activos. El equipo continúa siendo una ocurrencia del servicio y conserva serie/ID interno sin unicidad global, permitiendo enlazar en el futuro una identidad de activo separada sin reescribir históricos.

## Validaciones ejecutadas

- Suite backend completa: 311 pruebas y 19 subpruebas correctas, 21 fallos y
  dos advertencias. Diecinueve fallos provienen del `JSONB` no portable del
  módulo Actividad al crear metadata SQLite (`TD-023`) y dos del aborto del
  proceso externo LibreOffice; ninguno pertenece a Fase 9.
- Suite específica de Fase 9: 7 pruebas correctas.
- Suite seleccionada de Certificados: 30 pruebas correctas; los cuatro fallos
  restantes corresponden a los dos bloqueos externos anteriores.
- Suite completa del Motor: 208 pruebas correctas, incluidas creación,
  transiciones válidas/inválidas, invariantes, autorización exacta,
  revalidación, concurrencia, persistencia, ejecución, compensación,
  arquitectura, esquema y migraciones.
- Frontend: `package.json` no declara suite; build Vite de producción correcto,
  con la advertencia preexistente por tamaño del chunk principal.
- Compilación de bytecode Python: correcta.
- PostgreSQL: `f9c1d3e5a7b9` aplicó, revirtió a `f8a0b2c4d6e8` y reaplicó a
  head correctamente; el trigger append-only quedó comprobado.
- `alembic heads/current`: único head `f9c1d3e5a7b9`.
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

## Motor de Resoluciones — Fases 8 y 9

- Estado: Fases 0 a 8 `APROBADAS`; primer vertical de Fase 9
  `certificate.resolve_incorrect_release` implementado y `EN REVISIÓN`.
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
- Fase 9 incorpora exclusivamente provider read-only y gateways de ejecución y
  compensación para Certificados; no agrega API, otros dominios, workers,
  schedulers, procesamiento masivo, recuperación, conciliación, retries ni
  compensación automática.
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
- Validaciones de Fase 9: 7 específicas; 208 del Motor; 30 seleccionadas de
  Certificados; backend completo con 311 pruebas y 19 subpruebas correctas,
  19 fallos de `TD-023` y dos abortos de LibreOffice; build Vite y compilación
  Python correctos.
- La migración reversible `f9c1d3e5a7b9` fue probada en
  upgrade→downgrade→upgrade. `alembic check` sólo muestra la deriva histórica
  `TD-021` y ninguna operación sobre `certificate_resolution_operations`.
- El respaldo SQL fue regenerado y coincide con el head.
- Apertura aprobada de Fase 8:
  [`architecture/resolution-engine/21_PHASE_8_OPENING.md`](architecture/resolution-engine/21_PHASE_8_OPENING.md).
- Contrato:
  [`architecture/resolution-engine/22_INTEGRAL_SECURITY.md`](architecture/resolution-engine/22_INTEGRAL_SECURITY.md).
- Cierre:
  [`closures/RESOLUTION_ENGINE_PHASE_8.md`](closures/RESOLUTION_ENGINE_PHASE_8.md).
- Commits aprobados de Fase 8: `73e437d` y
  `661f43a5cbba9070b1f02babd9ebbd5149f62b2b`.
- Apertura oficial de Fase 9:
  [`architecture/resolution-engine/23_PHASE_9_OPENING.md`](architecture/resolution-engine/23_PHASE_9_OPENING.md).
- Contrato implementado del primer vertical:
  [`architecture/resolution-engine/24_PHASE_9_CERTIFICATES_INTEGRATION.md`](architecture/resolution-engine/24_PHASE_9_CERTIFICATES_INTEGRATION.md).
- Cierre técnico en revisión:
  [`closures/RESOLUTION_ENGINE_PHASE_9_CERTIFICATES.md`](closures/RESOLUTION_ENGINE_PHASE_9_CERTIFICATES.md).
- Ningún otro dominio o Fase 10 fue iniciado. API/SDK públicos, distribución e
  IA permanecen fuera de alcance.
- La IA es una posibilidad futura opcional y no constituye dependencia
  arquitectónica u operativa del ERP o del Motor determinista.
