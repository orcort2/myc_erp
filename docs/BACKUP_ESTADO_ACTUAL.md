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
> Corte actualizado: 2026-07-29

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
- Head único del código: `7b8c9d0e1f2a`.
- Head aplicado en la base PostgreSQL local compartida: `7b8c9d0e1f2a`.
- `6ae1d4877cdb` incorpora Communications sobre el merge de Notificaciones y
  Motor. Es trabajo previo/concurrente, no parte de Fase 14.
- `7b8c9d0e1f2a` agrega a `equipment` el FK BIGINT restrictivo
  `resolution_id`, la conciliación única y el hash de solicitud. Se validó en
  PostgreSQL temporal mediante upgrade completo, downgrade a
  `6ae1d4877cdb` y upgrade de retorno; la base temporal fue eliminada.
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
- `a0d2f4b6c8e1` crea `resolution_api_consumers` para credenciales hasheadas,
  organización, permisos, vigencia y revocación de consumidores de la API v1.
- `c1e3f5a7b9d2` crea nodos, trabajos durables y eventos distribuidos, con
  prioridad, intentos, leases cercados, índice parcial único por resolución e
  índices de despacho/observabilidad; un trigger PostgreSQL protege los eventos
  append-only. Su upgrade→downgrade→upgrade fue validado en una base PostgreSQL
  temporal limpia, luego eliminada.
- `d2f4a6b8c0e3` conserva inmutables identidad y contenido del plan y permite
  únicamente sus transiciones canónicas; protege además cambios de activación
  e invalidación. La cadena completa, downgrade a `c1e3f5a7b9d2` y upgrade de
  retorno se validaron en PostgreSQL temporal, después eliminado.
- El backfill histórico usa únicamente `service_order_items.catalog_item_id`, `quotation_items.catalog_item_id` o `equipment.certificate_master_document_id`; no compara nombres.
- Respaldo vigente: `backup_erp_myc_antes_prueba.sql`.
- Tamaño verificado: 74,253,414 bytes.
- SHA-256 verificado: `8612fb33707aeba36da5005dd9a9c3d74857b73ce88d7a5a265ce9233874e431`.
- El respaldo contiene `alembic_version = 7b8c9d0e1f2a`, las columnas de
  conciliación de Fase 14, la tabla de consumidores v1, la evidencia
  propietaria y los triggers append-only.
- La integración de pagos no agrega migraciones ni modifica datos locales; por
  ello no corresponde regenerar el respaldo SQL y su head permanece vigente.

## Facturación y pagos

- `InvoicePayment` y los endpoints existentes se consumen desde el Resumen
  financiero del Workbench único; no existe pestaña de Pagos.
- El modal registra pagos antes o después del timbrado, valida importe positivo
  y no mayor al saldo, evita doble envío y refresca `Invoice`, cartera y
  readiness del ETS.
- La factura muestra total, pagado, saldo, estado, historial y comprobante PDF.
  Cuentas por cobrar vive en el Dashboard existente y abre el mismo expediente.
- Facturama conserva la condición financiera: después del timbrado deriva
  `issued`, `partially_paid` o `paid` desde los importes persistidos.
- Saldo cero retira la factura de cartera y satisface la compuerta financiera
  de certificados cuando `requires_payment=true`.

## Equipos y contexto de certificado

- Al crear el ETS, cada partida operativa congela el `expected_certificate_master_id` correspondiente a su identidad estable de catálogo.
- Al dar de alta un equipo, `backend/app/services/equipment.py` consume exclusivamente ese valor de `ServiceOrderItem`; no importa `CatalogItem`, no consulta por `service_name` y no reabre la resolución en el catálogo.
- El snapshot de equipo conserva el Master documental y su versión/archivo/hash/vigencia, además de un contexto JSON versionado con alcance, tipo de certificado, Master esperado, partida ETS y concepto operativo de origen.
- El certificado esperado sigue generándose automáticamente con el mismo mapeo: `accredited_iso_17025 → acreditado`, `traceable → trazable`, `accredited_linked_lab → vinculado`.
- El contador de avance usa internamente `FINISHED_STATUSES = {calibrated, labeled, not_done}`. No cambiaron estados, transiciones ni semántica operativa.
- No se implementó historial transversal de activos. El equipo continúa siendo una ocurrencia del servicio y conserva serie/ID interno sin unicidad global, permitiendo enlazar en el futuro una identidad de activo separada sin reescribir históricos.

## Validaciones ejecutadas

- Integración de pagos: frontend Node `13 passed`; build Vite correcto con
  `1695` módulos y advertencia no bloqueante por tamaño del chunk.
- Backend focalizado de pagos, Facturación, documentos, Certificados y
  readiness: `38 passed`; regresión adicional ETS/servicios/contratos:
  `16 passed`, `12 subtests passed`.
- `test_certificate_release_http.py` no recolecta por el `ImportError`
  preexistente de `app.services.activity.list_messages`, ajeno a pagos. El
  backend no puede arrancarse para el E2E visual autenticado hasta resolver
  ese defecto concurrente.
- Suite específica Fase 14: `7 passed`; incluye composición, resultados,
  simulación, autorización granular, productor ERP idempotente, revalidación,
  concurrencia, compensación y E2E completo por worker después de cerrar la
  sesión.
- Suites seleccionadas Fases 13–14: `15 passed`.
- Suites seleccionadas Fases 11–14: `36 passed`.
- Frontend dinámico: `3 passed`; build Vite correcto con `1693` módulos y
  advertencia no bloqueante por tamaño del chunk.
- Compilación de bytecode Python: correcta.
- PostgreSQL temporal: `upgrade head → downgrade 6ae1d4877cdb → upgrade head`;
  `current = 7b8c9d0e1f2a (head)`. Base temporal eliminada.
- PostgreSQL local: se aplicó `6ae1d4877cdb → 7b8c9d0e1f2a` después de
  detectar que el ORM de `Equipment` consultaba columnas todavía ausentes.
  La consulta propietaria devuelve dos equipos y `list_field_sheets()` dos
  Hojas de Campo sin excepción; `/api/health` responde `200` y
  `/api/field-sheets` sin credenciales responde el `401` esperado, no `500`.
- Regresión operativa de Hojas de Campo, plantillas y Fase 14: `20 passed`.
  La prueba adicional de contexto de Equipos conserva dos fallos preexistentes
  por el `JSONB` directo de Activity bajo SQLite, no por PostgreSQL ni por la
  migración aplicada.
- `alembic check` no detectó drift en las columnas, índice o FK de Fase 14.
  Continúa mostrando la deuda histórica `TD-021` y la inconsistencia ajena de
  metadata de Notificaciones.
- Suite completa del Motor: `243 passed`, `2 failed`, `14 errors`. Todos los
  fallos/errores ocurren al crear metadata SQLite por `JSONB` directo de
  Notificaciones, ajeno a esta fase y no corregido para respetar el alcance.
- Backend completo: `348 passed`, `21 failed`, `14 errors` y `19 subtests
  passed`. Los dos fallos y catorce errores del Motor provienen del `JSONB`
  directo de Notificaciones bajo SQLite; los restantes corresponden a
  Activity/SQLite/JSONB y a fixtures SAT/XLSX ya identificados fuera del
  alcance. La suite completa no se declara correcta.
- `git diff --check` se ejecuta sobre el cierre; el árbol contiene espacios
  finales en CSS concurrente ajeno a Fase 14.
- Tras migrar la base local se regeneró `backup_erp_myc_antes_prueba.sql`; su
  `alembic_version` coincide con el head del código.

## Pendientes vigentes

1. Ejecutar el E2E autenticado de Equipos dentro de un expediente multi-OT con datos representativos.
2. Aplicar autorización deny-by-default y permisos explícitos al router de Equipos.
3. Resolver las deudas transversales vigentes en [`project/TECHNICAL_DEBT.md`](project/TECHNICAL_DEBT.md).
4. Implementar historial de activos sólo cuando se incorpore formalmente al alcance; no pertenece a esta entrega.
5. Ejecutar el E2E autenticado Factura→pago→timbrado→liquidación→liberación con datos representativos cuando el backend vuelva a ser arrancable y exista configuración Sandbox.

## Documentación y trazabilidad

- Entrada única: [`project/DOCUMENTATION_INDEX.md`](project/DOCUMENTATION_INDEX.md).
- Estado de módulos: [`project/PROJECT_STATUS.md`](project/PROJECT_STATUS.md).
- Reglas: [`project/BUSINESS_RULES.md`](project/BUSINESS_RULES.md).
- Decisiones: [`project/DECISIONS.md`](project/DECISIONS.md).
- Observaciones: [`project/OBSERVATIONS_REGISTER.md`](project/OBSERVATIONS_REGISTER.md).
- Contrato de alcance: [`architecture/CALIBRATION_SCOPE_CONTRACT.md`](architecture/CALIBRATION_SCOPE_CONTRACT.md).
- Plantillas Maestras: [`modules/control-documental/PLANTILLAS_MAESTRAS.md`](modules/control-documental/PLANTILLAS_MAESTRAS.md).

## Motor de Resoluciones — Fases 9 a 14

- Estado: Fases 0 a 13 `APROBADAS`; Fase 14 — Expansión institucional de
  integraciones `TERMINADA — EN REVISIÓN`. Fase 15 no iniciada.
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
- La API v1 autentica consumidor/organización, namespacia la clave idempotente
  y delega creación en Lifecycle y consultas en auditoría.
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
- La corrección de Fase 10 reemplaza el cursor Base64 firmado por un sobre
  opaco `c1` AES-GCM. Versión, consumidor, organización, filtros, orden,
  dirección, tamaño y posición keyset se cifran/autentican juntos; el formato
  legacy inseguro se rechaza.
- Fase 11 usa `resolution_work_items` como cola durable compartida,
  `resolution_worker_nodes` para capacidad/heartbeat/drenado y
  `resolution_work_events` como secuencia operacional append-only.
- Claim usa prioridad/disponibilidad, `SKIP LOCKED`, exclusión de claims
  existentes y un índice parcial único por `resolution_id`. Nodo, token,
  versión y vigencia forman el fencing obligatorio.
- El worker renueva lease y heartbeat durante el handler y delega en
  `ResolutionExecutor` o `CompensationExecutor`; no interpreta planes,
  Lifecycle, seguridad ni reglas propietarias.
- Recovery reencola únicamente antes del posible efecto. Si
  `effect_started_at` existe, bloquea por incertidumbre. Retry requiere
  ausencia de efecto confirmada y usa backoff exponencial acotado sin jitter.
- Las migraciones reversibles `f9c1d3e5a7b9` y `c1e3f5a7b9d2` fueron
  probadas en upgrade→downgrade→upgrade. `alembic check` sólo muestra la deriva
  histórica `TD-021` y ninguna operación sobre las tablas distribuidas.
- Replay exacto de ejecución/compensación se resuelve antes del certificado
  actual; una clave nueva usa segunda comprobación bajo lock y recuperación del
  ganador concurrente. `after_snapshot` se construye después de
  `flush/refresh`.
- El respaldo SQL coincide con el último head aprobado y aplicado antes del
  trabajo concurrente (`a0d2f4b6c8e1`); la situación temporal de la rama local
  y su regeneración pendiente se describen en Persistencia, migración y
  respaldo.
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
- Cierre aprobado de Fase 9:
  [`closures/RESOLUTION_ENGINE_PHASE_9_CERTIFICATES.md`](closures/RESOLUTION_ENGINE_PHASE_9_CERTIFICATES.md).
- Commits aprobados de Fase 9: `5abfe2d` y `901bd85`.
- Apertura oficial de Fase 10:
  [`architecture/resolution-engine/25_PHASE_10_OPENING.md`](architecture/resolution-engine/25_PHASE_10_OPENING.md).
- Contrato implementado de Fase 10:
  [`architecture/resolution-engine/26_PUBLIC_API_SDK.md`](architecture/resolution-engine/26_PUBLIC_API_SDK.md).
- Fase 10 fue aprobada mediante `dd9a84e`.
- Apertura oficial de Fase 11:
  [`architecture/resolution-engine/27_PHASE_11_OPENING.md`](architecture/resolution-engine/27_PHASE_11_OPENING.md).
- Contrato implementado de Fase 11:
  [`architecture/resolution-engine/28_DISTRIBUTED_RUNTIME.md`](architecture/resolution-engine/28_DISTRIBUTED_RUNTIME.md).
- Cierre técnico:
  [`closures/RESOLUTION_ENGINE_PHASE_11.md`](closures/RESOLUTION_ENGINE_PHASE_11.md).
- Fase 11 fue aprobada mediante
  `cbde51783870e4b06a4de84c27e05dc2b5ea3de1`.
- Fase 12 expone `/resolutions`, API interna v1, catálogo controlado,
  proyecciones de lista/expediente/timeline, flujo guiado y worker independiente
  de sesión. La autoridad se confirma antes del enqueue; el token HTTP no forma
  parte del trabajo durable y un `work_key` único impide doble despacho.
- Contrato de Fase 12:
  [`architecture/resolution-engine/29_PHASE_12_RESOLUTION_CENTER.md`](architecture/resolution-engine/29_PHASE_12_RESOLUTION_CENTER.md).
- Cierre técnico de Fase 12:
  [`closures/RESOLUTION_ENGINE_PHASE_12.md`](closures/RESOLUTION_ENGINE_PHASE_12.md).
- Fase 12 fue aprobada mediante `a7bf75f`.
- Fase 13 incorpora registro institucional versionado, formularios dinámicos,
  indicadores backend, expediente completo, rol Operador e integración
  Certificados end-to-end:
  [`architecture/resolution-engine/30_PHASE_13_RESOLUTION_CENTER_CONSOLIDATION.md`](architecture/resolution-engine/30_PHASE_13_RESOLUTION_CENTER_CONSOLIDATION.md).
- Cierre técnico de Fase 13:
  [`closures/RESOLUTION_ENGINE_PHASE_13.md`](closures/RESOLUTION_ENGINE_PHASE_13.md).
- Fase 13 fue aprobada mediante
  `bb76e3bba9482517c9dfb870567d6bdfc7b9b135`.
- Fase 14 agrega composición instalada única y el vertical
  `service_order.resolve_additional_equipment@1.0`:
  [`architecture/resolution-engine/31_PHASE_14_INTEGRATION_EXPANSION.md`](architecture/resolution-engine/31_PHASE_14_INTEGRATION_EXPANSION.md).
- Cierre técnico de Fase 14:
  [`closures/RESOLUTION_ENGINE_PHASE_14.md`](closures/RESOLUTION_ENGINE_PHASE_14.md).
- Fase 14 queda `EN REVISIÓN`; Fase 15 no está abierta.
- La IA es una posibilidad futura opcional y no constituye dependencia
  arquitectónica u operativa del ERP o del Motor determinista.
