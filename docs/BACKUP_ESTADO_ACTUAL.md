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
- Revisión aplicada y único head verificado: `b4c6d8e0f2a3`.
- `9d3e5f7a1b2c` agrega las 21 tablas del modelo persistente del Motor de
  Resoluciones, sus constraints, índices y triggers de inmutabilidad. Su revisión
  padre `8c2d4e6f7a9b` conserva el snapshot operativo de Equipos.
- `b4c6d8e0f2a3` agrega `resolution_security_decisions`, elimina once FKs del
  Motor a `users.id` y migra identidad/autoridad a actor canónico, funciones y
  snapshots.
- El backfill histórico usa únicamente `service_order_items.catalog_item_id`, `quotation_items.catalog_item_id` o `equipment.certificate_master_document_id`; no compara nombres.
- Respaldo vigente: `backup_erp_myc_antes_prueba.sql`.
- Tamaño verificado: 74,170,125 bytes.
- SHA-256 verificado: `e97094f59a094023a39dfa89049cf49f9e4bf8625274f65265d42598779dcb9e`.
- El respaldo contiene `alembic_version = b4c6d8e0f2a3`.

## Equipos y contexto de certificado

- Al crear el ETS, cada partida operativa congela el `expected_certificate_master_id` correspondiente a su identidad estable de catálogo.
- Al dar de alta un equipo, `backend/app/services/equipment.py` consume exclusivamente ese valor de `ServiceOrderItem`; no importa `CatalogItem`, no consulta por `service_name` y no reabre la resolución en el catálogo.
- El snapshot de equipo conserva el Master documental y su versión/archivo/hash/vigencia, además de un contexto JSON versionado con alcance, tipo de certificado, Master esperado, partida ETS y concepto operativo de origen.
- El certificado esperado sigue generándose automáticamente con el mismo mapeo: `accredited_iso_17025 → acreditado`, `traceable → trazable`, `accredited_linked_lab → vinculado`.
- El contador de avance usa internamente `FINISHED_STATUSES = {calibrated, labeled, not_done}`. No cambiaron estados, transiciones ni semántica operativa.
- No se implementó historial transversal de activos. El equipo continúa siendo una ocurrencia del servicio y conserva serie/ID interno sin unicidad global, permitiendo enlazar en el futuro una identidad de activo separada sin reescribir históricos.

## Validaciones ejecutadas

- Suite backend completa: 233 pruebas y 19 subpruebas correctas.
- Suite específica del Motor: 109 pruebas correctas, incluidas creación,
  transiciones válidas/inválidas, invariantes, autorización exacta,
  revalidación, concurrencia, persistencia, orquestación, arquitectura, esquema
  y migraciones.
- Frontend: 11 pruebas correctas y build Vite de producción correcto; permanece
  la advertencia preexistente por tamaño del chunk principal.
- Compilación de bytecode Python: correcta.
- PostgreSQL: `b4c6d8e0f2a3` aplicó, revirtió a `9d3e5f7a1b2c` y reaplicó a
  head; `resolution_security_decisions` rechazó mutación con SQLSTATE `55000`.
- `alembic heads/current`: único head `b4c6d8e0f2a3`.
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

## Motor de Resoluciones — Fase 4

- Estado: Fases 0, 1, 2 y 3 `APROBADAS`; Fase 4 `EN REVISIÓN`; Fase 5
  `NO INICIADA`.
- El Motor conserva el expediente y seguridad aprobados e incorpora creación,
  Lifecycle, máquina estado/acción, evidencias tipadas, eventos internos,
  auditoría append-only y control optimista.
- El flujo principal llega de `draft` a `ready_for_execution`; autorización y
  revalidación exigen resolución, IDs, versiones y hashes exactos.
- `ResolutionOrchestrator` selecciona la definición registrada exacta y
  coordina contexto, análisis, estrategia, plan, simulación declarativa,
  requisitos de autorización y revalidación sin efectos.
- Una transición inválida, evidencia discordante, razón de gobierno ausente o
  versión obsoleta se rechaza explícitamente.
- No se incorporaron ejecución externa, gateways, API, workers, publicación
  outbox, retries, compensaciones ni integraciones específicas del ERP.
- No existe migración de Fase 4. La base y el respaldo conservan
  `alembic_version = b4c6d8e0f2a3`; `alembic check` sólo muestra `TD-021` y
  ninguna deriva del Motor.
- Contrato:
  [`architecture/resolution-engine/16_LIFECYCLE_ORCHESTRATION.md`](architecture/resolution-engine/16_LIFECYCLE_ORCHESTRATION.md).
- Cierre:
  [`closures/RESOLUTION_ENGINE_PHASE_4.md`](closures/RESOLUTION_ENGINE_PHASE_4.md).
