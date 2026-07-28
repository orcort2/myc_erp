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
> Corte actualizado: 2026-07-28

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
- Revisión aplicada en la base local compartida: `b18ac098c1db`. Esa revisión
  y su archivo no confirmado pertenecen al trabajo concurrente de
  Notificaciones. El árbol visible tiene dos heads:
  `b18ac098c1db` y `d2f4a6b8c0e3`; el índice exclusivo de Fase 12 conserva un
  único head `d2f4a6b8c0e3`, hijo de `c1e3f5a7b9d2`.
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
- Tamaño verificado: 74,222,078 bytes.
- SHA-256 verificado: `de180a35da5553851297d5c6b145059e7bf0a9722e9fca0bbbd9d305beff6c7c`.
- El respaldo contiene `alembic_version = a0d2f4b6c8e1`, la tabla de
  consumidores v1, la evidencia propietaria y los triggers append-only.

## Equipos y contexto de certificado

- Al crear el ETS, cada partida operativa congela el `expected_certificate_master_id` correspondiente a su identidad estable de catálogo.
- Al dar de alta un equipo, `backend/app/services/equipment.py` consume exclusivamente ese valor de `ServiceOrderItem`; no importa `CatalogItem`, no consulta por `service_name` y no reabre la resolución en el catálogo.
- El snapshot de equipo conserva el Master documental y su versión/archivo/hash/vigencia, además de un contexto JSON versionado con alcance, tipo de certificado, Master esperado, partida ETS y concepto operativo de origen.
- El certificado esperado sigue generándose automáticamente con el mismo mapeo: `accredited_iso_17025 → acreditado`, `traceable → trazable`, `accredited_linked_lab → vinculado`.
- El contador de avance usa internamente `FINISHED_STATUSES = {calibrated, labeled, not_done}`. No cambiaron estados, transiciones ni semántica operativa.
- No se implementó historial transversal de activos. El equipo continúa siendo una ocurrencia del servicio y conserva serie/ID interno sin unicidad global, permitiendo enlazar en el futuro una identidad de activo separada sin reescribir históricos.

## Validaciones ejecutadas

- Suite específica Fase 12: `11 passed`.
- Suite completa del Motor sobre el índice exclusivo de Fase 12:
  `244 passed`, dos advertencias de dependencias; incluye Fases 1–12.
- Suite backend completa sobre la fotografía exclusiva: `348 passed`,
  `20 failed`, `19 subtests passed`. Diecinueve fallos son la deuda conocida
  SQLite/`JSONB` de Actividad (`TD-023`); el vigésimo sólo refleja que el XLSX
  SAT ignorado no entra en la fotografía Git. La prueba SAT ejecutada contra el
  recurso local oficial terminó `4 passed`; por tanto el estado verificable con
  ese recurso es `349 passed`, `19 failed`. Ningún fallo apunta a Fase 12.
- La suite del Motor sobre el árbol compartido fue contaminada por el modelo
  concurrente de Notificaciones (`JSONB` no portable): alcanzó `226 passed`
  antes de `2 failed` y `14 errors`. La fotografía exclusiva elimina esa causa
  ajena y termina completa.
- Frontend: pruebas Node específicas `2 passed`; build Vite de producción
  correcto (`1675` módulos), con advertencia no bloqueante por tamaño del chunk.
- Compilación de bytecode Python: correcta.
- PostgreSQL temporal limpio: cadena completa aplicada hasta
  `d2f4a6b8c0e3`, downgrade a `c1e3f5a7b9d2` y upgrade nuevamente correctos;
  `current` y `heads` mostraron un único `d2f4a6b8c0e3`.
- `alembic heads/current` del árbol compartido: heads `b18ac098c1db` y
  `d2f4a6b8c0e3`; base local en `b18ac098c1db`. Fase 12 no se aplicó sobre esa
  rama ajena para no mezclar ni alterar el trabajo de Notificaciones.
- `alembic check` continúa reportando sólo la deriva histórica ajena registrada
  como `TD-021`; no detectó una operación propia de Fase 12.
- `git diff --check`: correcto.
- El respaldo conserva `alembic_version = a0d2f4b6c8e1`. No se regeneró:
  Fase 12 se validó en una base temporal y no modificó la base local; la
  sincronización de `b18ac098c1db` pertenece al trabajo externo de
  Notificaciones. Al integrar ambas ramas Alembic deberá definirse un único
  descendiente/merge y entonces aplicar Fase 12 y regenerar el respaldo.

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

## Motor de Resoluciones — Fases 9 a 12

- Estado: Fases 0 a 11 `APROBADAS`; Fase 12 — Centro de Resoluciones
  `EN REVISIÓN`. Fase 13 no iniciada.
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
- Fase 12 queda `EN REVISIÓN`; Fase 13 e IA permanecen fuera de alcance.
- La IA es una posibilidad futura opcional y no constituye dependencia
  arquitectónica u operativa del ERP o del Motor determinista.
