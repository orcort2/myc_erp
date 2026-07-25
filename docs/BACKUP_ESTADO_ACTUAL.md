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
> Corte actualizado: 2026-07-24

# Estado operativo actual del ERP MYC

## Estado general

- Versión declarada del ERP: `0.4.0`.
- Estado de avance autorizado: [`project/PROJECT_STATUS.md`](project/PROJECT_STATUS.md).
- Único módulo `SELLADO`: Control Documental V1.
- Equipos permanece `CASI SELLADO`: la trazabilidad del Master quedó desacoplada del catálogo vivo; continúan pendientes la protección uniforme del router y el E2E autenticado multi-OT.
- Riesgos prioritarios transversales: autorización de APIs/registro/tokens/portal, duplicación material en ETS y autenticación de certificados duplicada fuera de Calidad.

## Persistencia, migración y respaldo

- Motor: PostgreSQL con SQLAlchemy y Alembic.
- Revisión aplicada y único head verificado: `9d3e5f7a1b2c`.
- `9d3e5f7a1b2c` agrega las 21 tablas del modelo persistente del Motor de
  Resoluciones, sus constraints, índices y triggers de inmutabilidad. Su revisión
  padre `8c2d4e6f7a9b` conserva el snapshot operativo de Equipos.
- El backfill histórico usa únicamente `service_order_items.catalog_item_id`, `quotation_items.catalog_item_id` o `equipment.certificate_master_document_id`; no compara nombres.
- Respaldo vigente: `backup_erp_myc_antes_prueba.sql`.
- Tamaño verificado: 74,166,303 bytes.
- SHA-256 verificado: `b713d82da52e48d8c6e4672f1970ef540582e0d8d99cc982b3b44149b69d40c1`.
- El respaldo contiene `alembic_version = 9d3e5f7a1b2c`.

## Equipos y contexto de certificado

- Al crear el ETS, cada partida operativa congela el `expected_certificate_master_id` correspondiente a su identidad estable de catálogo.
- Al dar de alta un equipo, `backend/app/services/equipment.py` consume exclusivamente ese valor de `ServiceOrderItem`; no importa `CatalogItem`, no consulta por `service_name` y no reabre la resolución en el catálogo.
- El snapshot de equipo conserva el Master documental y su versión/archivo/hash/vigencia, además de un contexto JSON versionado con alcance, tipo de certificado, Master esperado, partida ETS y concepto operativo de origen.
- El certificado esperado sigue generándose automáticamente con el mismo mapeo: `accredited_iso_17025 → acreditado`, `traceable → trazable`, `accredited_linked_lab → vinculado`.
- El contador de avance usa internamente `FINISHED_STATUSES = {calibrated, labeled, not_done}`. No cambiaron estados, transiciones ni semántica operativa.
- No se implementó historial transversal de activos. El equipo continúa siendo una ocurrencia del servicio y conserva serie/ID interno sin unicidad global, permitiendo enlazar en el futuro una identidad de activo separada sin reescribir históricos.

## Validaciones ejecutadas

- Suite backend completa: 90 pruebas correctas.
- Dentro de la suite se ejecutaron 8 pruebas de Equipos/Servicios Compuestos y 26 pruebas focalizadas relacionadas con Captura, Calidad, certificados y contrato de alcance.
- Prueba crítica verificada: crear ETS, cambiar después nombre y Master del catálogo, crear equipo y confirmar que conserva el Master congelado, snapshot completo y certificado esperado.
- `alembic upgrade head`: correcto sobre la base local.
- `alembic heads/current`: un único head `8c2d4e6f7a9b`.
- `alembic check` continúa reportando la deriva histórica ya registrada como `TD-021`; no detectó ausencia de las dos columnas ni del índice/FK incorporados por esta migración.
- Compilación de bytecode Python y `git diff --check`: correctos.
- El respaldo SQL fue regenerado después de aplicar la migración.

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

## Motor de Resoluciones — Fase 2

- Estado: Fases 0 y 1 `APROBADAS`; Fase 2 `EN REVISIÓN`; Fase 3 `NO INICIADA`.
- La fundación de Fase 1 permanece aislada. La infraestructura de Fase 2 agrega
  21 modelos persistentes generales, constraints, índices, repositorio de
  reconstrucción, inmutabilidad y outbox estructural.
- El esquema congela tipo/versión de definición, contexto, planes, hashes y
  evidencia. No contiene columnas particulares de ETS, Equipos, Facturación ni
  UC-001.
- Las relaciones críticas son claves foráneas y las dependencias de pasos están
  normalizadas. PostgreSQL protege evidencia append-only y restringe la edición
  de planes/pasos a `draft`.
- No se incorporaron lifecycle, lógica de negocio, seguridad del Motor,
  gateways, API, workers, simulación operativa, autorización ni ejecución.
- Validaciones: 184 pruebas backend y 19 subpruebas correctas; 64 pruebas del
  Motor dentro de esa suite; 11 pruebas frontend correctas; build Vite y
  compilación Python correctos.
- PostgreSQL: 21 tablas, 22 triggers, prueba transaccional de inmutabilidad,
  downgrade completo a `8c2d4e6f7a9b`, upgrade a head y único
  head/current `9d3e5f7a1b2c`.
- `alembic check` conserva exclusivamente la deriva histórica registrada como
  `TD-021`; no propone operaciones sobre el esquema del Motor.
- Cierre detallado:
  [`closures/RESOLUTION_ENGINE_PHASE_2.md`](closures/RESOLUTION_ENGINE_PHASE_2.md).
