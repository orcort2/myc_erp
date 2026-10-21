# Integración Fase 3B — evidencia local 2026-10-20

Estado: implementación local, pendiente de revisión final del usuario. Fotografía de la integración; no es un cierre histórico ni autorización de publicación.

## Resultado y límites

Base: main `752394a4d8040033635022d354f921a3209488fd`, sin cambios de HEAD. Se recuperaron selectivamente 19 archivos pendientes de la fuente y se adaptaron los servicios actuales. Los 169 commits exclusivos de main no se sustituyeron. No se ejecutaron merge, rebase, reset, clean, cherry-pick, commit, push ni despliegue.

Se conservan las autoridades actuales de Servicio General, intervenciones, permisos, auditoría y notificaciones. Fuente `/Users/saulcortes/Developer/myc_erp-phase3b` y respaldo `/Users/saulcortes/Developer/myc-phase3b-backup-20261020` sin escrituras por esta tarea; el estado Git fuente conserva sus 13 modificados y 6 nuevos originales. El contenido del respaldo no fue auditado.

## Archivos exactos y justificación

45 archivos: 37 modificados y 8 nuevos (incluidas las cinco correcciones autorizadas). Enlaces relativos al repositorio.

| Archivo | Justificación |
| --- | --- |
| [backend/app/models/__init__.py](../../backend/app/models/__init__.py) | Registra el nuevo modelo sin retirar registros posteriores de main. |
| [backend/app/models/lab_delivery_item.py](../../backend/app/models/lab_delivery_item.py) | Añade relación con impactos sin cascada de borrado. |
| [backend/app/models/lab_delivery_item_correction_impact.py](../../backend/app/models/lab_delivery_item_correction_impact.py) | Nuevo modelo con identidad histórica, FK protectoras, estados y unicidad parcial. |
| [backend/app/routers/lab_work_orders.py](../../backend/app/routers/lab_work_orders.py) | Transporta decisiones por equipo y revisión de cohorte a servicios LAB. |
| [backend/app/schemas/lab_work_order.py](../../backend/app/schemas/lab_work_order.py) | Contratos aditivos para reaperturas directas de OT y hoja; campos extra prohibidos. |
| [backend/app/schemas/operational_ticket.py](../../backend/app/schemas/operational_ticket.py) | Contratos de decisión y revisión para aprobación/resolución de tickets. |
| [backend/app/schemas/service_order_mobile_execution.py](../../backend/app/schemas/service_order_mobile_execution.py) | Contrato ETS de entrega, impacto, estados y revisión; rechaza banderas extra. |
| [backend/app/services/lab_delivery_correction_impacts.py](../../backend/app/services/lab_delivery_correction_impacts.py) | Autoridad común de decisiones, entrega canónica, bloqueo, impacto, auditoría y rollback. |
| [backend/app/services/lab_field_sheets.py](../../backend/app/services/lab_field_sheets.py) | Protege reapertura directa de hoja y avanza revisión optimista dentro de su transacción. |
| [backend/app/services/lab_work_order_deliveries.py](../../backend/app/services/lab_work_order_deliveries.py) | Bloquea recibo final nuevo con invalidación pendiente; conserva Servicio General e intervenciones. |
| [backend/app/services/lab_work_orders.py](../../backend/app/services/lab_work_orders.py) | Impide clonar implícitamente hojas completadas entregadas por edición documental. |
| [backend/app/services/operational_tickets.py](../../backend/app/services/operational_tickets.py) | Valida decisiones en reapertura de cohorte y hojas por ticket; conserva permisos y notificaciones, liga revisiones antes del commit. |
| [backend/app/services/service_order_mobile_administration.py](../../backend/app/services/service_order_mobile_administration.py) | Valida token/decisión bajo bloqueo y engloba traza ETS en rollback del dominio. |
| [backend/app/services/service_order_mobile_execution.py](../../backend/app/services/service_order_mobile_execution.py) | Proyecta entrega e impactos; calcula revisión de todos los miembros y contadores con históricos retirados. |
| [backend/migrations/versions/a3c5e7f9b1d2_lab_delivery_item_correction_impacts.py](../../backend/migrations/versions/a3c5e7f9b1d2_lab_delivery_item_correction_impacts.py) | Migración aditiva desde ffcd7b40ac46 sin backfill ni reescritura de entregas. |
| [backend/tests/test_lab_delivery_correction_impacts.py](../../backend/tests/test_lab_delivery_correction_impacts.py) | 52 casos de impacto, rutas, permisos, revisión, rollback, históricos, recibos y clonación indirecta. |
| [backend/tests/test_lab_delivery_correction_impacts_postgres.py](../../backend/tests/test_lab_delivery_correction_impacts_postgres.py) | Upgrade/downgrade aislados, FK/checks/índice y concurrencia real con un ganador. |
| [backend/tests/test_lab_equipment_soft_delete.py](../../backend/tests/test_lab_equipment_soft_delete.py) | Actualiza únicamente el comentario sobre la nueva regla de reapertura; preserva prueba existente. |
| [backend/tests/test_service_order_mobile_execution.py](../../backend/tests/test_service_order_mobile_execution.py) | Actualiza respuesta proyectada y permite fixture PostgreSQL por esquema exclusivo con limpieza. |
| [docs/BACKUP_ESTADO_ACTUAL.md](../../docs/BACKUP_ESTADO_ACTUAL.md) | Registra estado local verificable, migración sólo probada en aislamiento y pendientes. |
| [docs/PROJECT_FILE_REGISTRY.md](../../docs/PROJECT_FILE_REGISTRY.md) | Registra archivos nuevos y responsabilidades cambiadas; regenerado y revisado. |
| [docs/architecture/ETS_LAB_TECHNICAL_BRIDGE.md](../../docs/architecture/ETS_LAB_TECHNICAL_BRIDGE.md) | Actualiza contrato ETS y elimina la restricción documental obsoleta sin entrega vigente. |
| [docs/architecture/LAB_WORK_ORDERS.md](../../docs/architecture/LAB_WORK_ORDERS.md) | Define reapertura con entregas, transacción, contratos, históricos y pendientes de resolución. |
| [docs/audits/PHASE3B_INTEGRATION_2026-10-20.md](../../docs/audits/PHASE3B_INTEGRATION_2026-10-20.md) | Fotografía de archivos, comandos, resultados, riesgos y estado Git final. |
| [docs/project/BUSINESS_RULES.md](../../docs/project/BUSINESS_RULES.md) | Documenta decisiones, alcance y efectos administrativos sin alterar entrega histórica. |
| [docs/project/CURRENT_PROCESS_FLOW.md](../../docs/project/CURRENT_PROCESS_FLOW.md) | Documenta el flujo de validación, reapertura y notificaciones. |
| [docs/project/CURRENT_SCOPE.md](../../docs/project/CURRENT_SCOPE.md) | Delimita integración y exclusión de resolución/reemisión/reentrega. |
| [docs/project/DECISIONS.md](../../docs/project/DECISIONS.md) | Registra adaptación selectiva y autoridades reutilizadas. |
| [docs/project/DOCUMENTATION_INDEX.md](../../docs/project/DOCUMENTATION_INDEX.md) | Enlaza la evidencia local sin declarar cierre histórico. |
| [docs/project/OBSERVATIONS_REGISTER.md](../../docs/project/OBSERVATIONS_REGISTER.md) | Distingue correcciones verificadas, alcance pendiente y fallos preexistentes. |
| [docs/project/PROJECT_STATUS.md](../../docs/project/PROJECT_STATUS.md) | Marca integración local pendiente de revisión final sin declarar módulo sellado. |
| [docs/project/TECHNICAL_DEBT.md](../../docs/project/TECHNICAL_DEBT.md) | Registra ciclo administrativo pendiente y regresiones preexistentes. |
| [frontend/src/components/ets-mobile/EtsMobileCorrectionDialog.jsx](../../frontend/src/components/ets-mobile/EtsMobileCorrectionDialog.jsx) | Exige impacto para entregados, transporta token y permite recargar tras error. |
| [frontend/src/components/ets-mobile/EtsMobileEquipmentDetail.jsx](../../frontend/src/components/ets-mobile/EtsMobileEquipmentDetail.jsx) | Muestra impacto activo y transmite revisión; recarga con loader existente. |
| [frontend/src/components/ets-mobile/EtsMobileExecutionPanel.jsx](../../frontend/src/components/ets-mobile/EtsMobileExecutionPanel.jsx) | Muestra contadores administrativos, transmite revisión y permite recargar. |
| [frontend/src/components/ets-mobile/correctionDeliveryImpact.js](../../frontend/src/components/ets-mobile/correctionDeliveryImpact.js) | Opciones, validación y constructor de payload compatible con no entregados. |
| [frontend/src/components/ets-mobile/correctionDeliveryImpact.test.js](../../frontend/src/components/ets-mobile/correctionDeliveryImpact.test.js) | Pruebas de opciones y contrato del payload. |
| [frontend/src/components/ets-mobile/etsMobilePanels.test.js](../../frontend/src/components/ets-mobile/etsMobilePanels.test.js) | Comprueba estados/recarga y acota prueba CSS LAB para excluir estilos posteriores de correo. |
| [backend/app/services/lab_field_sheets_external.py](../../backend/app/services/lab_field_sheets_external.py) | Pasa la sesión SQL al validador compartido de captura, preservando LAB Externo en sesiones autorizadas. |
| [frontend/src/components/ets-mobile/mobileExecutionPresentation.js](../../frontend/src/components/ets-mobile/mobileExecutionPresentation.js) | Habilita corrección posterior en draft sólo con authorized_correction_session emitido por LAB. |
| [frontend/src/components/ets-mobile/mobileExecutionPresentation.test.js](../../frontend/src/components/ets-mobile/mobileExecutionPresentation.test.js) | Prueba draft ordinario frente a sesión de corrección persistida. |
| [myc-mobile/app/(technician)/work-orders.tsx](../../myc-mobile/app/(technician)/work-orders.tsx) | Condiciona impresión/descarga a disponibilidad backend y muestra bloqueo administrativo sin revertir entrega física. |
| [myc-mobile/src/types/lab-work-order.ts](../../myc-mobile/src/types/lab-work-order.ts) | Transporta disponibilidad y motivo de bloqueo del acuse en entrega y estado del grupo. |
| [myc-mobile/src/wiring-tests/lab-delivery-flow.wiring.test.ts](../../myc-mobile/src/wiring-tests/lab-delivery-flow.wiring.test.ts) | Comprueba acciones de acuse dependientes de disponibilidad. |
| [scripts/generate_project_file_registry.py](../../scripts/generate_project_file_registry.py) | Conserva clasificaciones y responsabilidades Fase 3B al regenerar el inventario oficial. |

El generador del inventario también incorpora 57 rutas ya existentes en main que faltaban en el registro previo. No se modificó su código. Las responsabilidades de Fase 3B quedan en el generador para evitar que una ejecución posterior las sustituya por clasificaciones anteriores; se verificó idempotencia y una fila por cada una de las 45 rutas afectadas.

## Autoridad, rutas y atomicidad

- `establish_reopening_decisions` valida el alcance real, la entrega vigente única y la hoja origen bajo bloqueo de cohorte. Usa la autoridad de entregas actual; no elige arbitrariamente una exhibición si hay varias vigentes.
- `_reopen_closed_cohort` valida permisos LAB y política de firmas en servidor. Reapertura directa y aprobación de ticket llegan al mismo núcleo; hojas directas y resolución de tickets pasan por la misma decisión administrativa.
- El endpoint ETS rechaza campos extra. Los contratos de OT y ticket también prohíben extras: `delivery_impact_declared=true` devuelve 422 y no tiene equivalente interno autorizante. Un impacto pending anterior no habilita otra reapertura. Se mantiene la prohibición de autoaprobación.
- `none` se audita con actor, motivo, equipo y hoja/revisión; no genera fila de impacto. Las otras decisiones generan impacto y auditoría. El vínculo a revisión OT se fija antes del commit.
- Una corrección individual decide sólo sobre su equipo. Una reapertura completa exige decisiones por todos los equipos entregados activos de la cohorte y clona exclusivamente correction_equipment_ids; rechaza decisiones fuera del alcance. La selección técnica no se infiere del tipo de decisión administrativa. Los no entregados conservan omisión/none.
- Los coordinadores conservan un único commit de negocio. Decisión, impacto, cambio administrativo del recibo, revisiones, ticket, nueva hoja y auditorías permanecen en esa transacción. `rollback_failed_reopening` revierte también los fallos de flush anteriores al núcleo y limpia la cola transitoria de notificaciones. El despacho posterior al commit conserva su mecanismo existente.
- La edición documental no puede abrir implícitamente otra revisión completed entregada: debe pasar primero por la reapertura administrativa. Las hojas ya abiertas siguen editables.
- `expected_cohort_revision` contrasta todos los pares `(id, edit_version)` después de bloquear/releer. Las reaperturas de hoja avanzan edit_version. Estado, entrega y hoja se revalidan aun si un cliente compatible omite el token.

Evidencia ejecutada en SQLite y PostgreSQL:

- `test_all_routes_require_fresh_decision_and_reject_boolean_bypass` (4 rutas).
- `test_all_routes_reject_stale_revision_and_preserve_history` (4 rutas).
- `test_all_routes_reject_outside_equipment_and_insufficient_permissions` (4 rutas).
- `test_all_routes_rollback_decision_impact_receipt_and_audit_on_commit_failure` (4 rutas): ejecuta `flush()` real antes del fallo; compara OT, versiones, hojas, recibos/bytes/hash, ticket, auditorías, impactos y notificaciones contra el estado previo.
- `test_ets_rolls_back_every_stage_before_commit` (4 etapas): auditoría de impacto ya creado, clonación, vínculo a revisión y auditoría de reapertura.
- Pruebas de autoaprobación, impacto anterior, decisiones incompletas, retiro lógico, clonación indirecta, vouchers, snapshots, hash y recibos.
- `test_concurrent_reopenings_have_one_winner_and_preserve_delivery`: dos sesiones PostgreSQL con estado precargado producen 200 y 409; queda exactamente un impacto y la entrega es idéntica.

La atomicidad cubre la transacción de negocio. Los efectos externos de notificación ocurren después del commit; un fallo de transporte posterior no deshace una transacción confirmada. No se implementó otro mecanismo de notificación.

## Alembic y aislamiento

```text
69fc4e5d622e, a1b2c3d4e5f7 -> ffcd7b40ac46 (mergepoint existente)
ffcd7b40ac46 -> a3c5e7f9b1d2 (head único)
```

La migración nueva crea sólo tabla/índices/checks. Antes del upgrade se verificaron tablas y PK de `lab_delivery_items`, `users`, `lab_work_order_revisions` y `field_sheets`. Después se inspeccionaron cinco FK, checks y el índice único parcial. Upgrade desde main, downgrade de tabla vacía y nuevo upgrade pasaron en un esquema desechable. Ninguna migración histórica fue editada.

Clúster PostgreSQL independiente inicializado con `initdb` en `/tmp/myc-phase3b-pg.mfNGOl/data`, puerto 55483, escucha 127.0.0.1, base exclusiva `myc_phase3b_test`. Fixtures sintéticas por esquemas UUID; las pruebas heredadas que requieren public usaron sólo esa base desechable. La fixture específica valida host y nombre de base. Sin conexiones a bases operativas para pruebas o migración. El servidor temporal se detiene al finalizar; no se elimina el respaldo del usuario.

No se regeneró el dump operativo `backup_erp_myc_antes_prueba.sql`: la base local operativa/de desarrollo no fue modificada. No debe aplicarse un downgrade con impactos históricos; el downgrade ejercitado fue exclusivamente sobre una tabla vacía del entorno desechable.

## Resultado vigente de las cinco correcciones autorizadas

Implementadas las cinco correcciones: autoridad persistida para hojas sucesivas (directa, tickets y ETS), separación de selección técnica/decisiones, disponibilidad real del acuse, downgrade conservador y default SQL pending. No se incrementa otra vez revision_number de la cohorte en reaperturas de hoja. Una OT draft sin snapshot histórico se rechaza. La captura posterior de hoja se prueba con firmas preservadas; no se evita la firma requerida al invalidarlas.

La selección se valida antes de efectos; la regresión verifica selección parcial, decisiones administrativas completas, none auditable, equipo ajeno/sin hoja/duplicado, y rechazo de selección omitida cuando hay decisiones. Las nueve combinaciones de decisión × ruta posterior demuestran corrección sucesiva de equipos no entregados sin alterar vouchers ni snapshots. Los fallos tras flush revierten hojas, versiones, impactos, recibos, auditorías y notificaciones. PostgreSQL comprueba una sola ganadora ante correcciones concurrentes, incluidas hojas sucesivas.

La última exhibición física puede confirmarse mientras existe invalidación: sigue completed, con voucher; la respuesta informa final_receipt_available=false y DELIVERY_INVALIDATION_PENDING. No se emite otro recibo ni auditoría de emisión. Mobile conserva el mensaje de entrega completada y oculta acciones del acuse.

El downgrade de tabla poblada se prueba para pending/resolved/cancelled: conserva íntegramente filas, índices, versión Alembic y evidencia de entrega. Tabla vacía permite downgrade/upgrade. El lock ACCESS EXCLUSIVE precede la comprobación y permanece en la transacción PostgreSQL; offline se rechaza. Head único a3c5e7f9b1d2, padre ffcd7b40ac46.

### Validación vigente

| Ejecución | Resultado |
| --- | --- |
| Regresión backend LAB/ETS/SG/intervenciones, 20 archivos, SQLite en memoria | 512 passed, 18 skipped, 0 failed; 111.96 s |
| Fase 3B/ETS + migración/concurrencia PostgreSQL, 4 archivos | 90 passed, 0 failed; 81.89 s |
| 18 pruebas PostgreSQL omitidas arriba, ejecutadas separadamente | 17 passed, 1 failed preexistente (16/1 + 1/0 en dos comandos) |
| ETS web `node --test` | 35 passed, 0 failed |
| MYC Mobile suite completa `npm test` | 1142 passed, 0 failed |
| Frontend `npm run build` | OK; advertencia existente de chunk >500 kB |
| Mobile `npx tsc --noEmit` | Falla con 2 TS2307: expo-image-manipulator y expo-image-picker ausentes localmente en technical-report-media-expo.ts; ese archivo y package.json no se modificaron |
| Grafo Alembic / compileall / inventario / git diff --check | Un head y padre correctos; compilación Python OK; 45 rutas inventariadas y existentes; diff sin errores |

El fallo PostgreSQL restante es test_postgresql_concurrent_individual_cohorts_get_distinct_versions: LAB_RECEPTION_INCOMPLETE porque su fixture no asigna service_type. Ya fue reproducido en HEAD durante la integración anterior (log /tmp/myc-phase3b-pg.mfNGOl/postgres-baseline.log). No se modifica esa regla ajena a Fase 3B. Los 18 skips de la primera fila no representan omisión de esos casos: están incluidos en las dos ejecuciones PostgreSQL adicionales.

Ejecuciones intermedias, sustituidas por las anteriores: primer comando pytest desde raíz sin PYTHONPATH tuvo 3 errores de importación; corregido cwd a backend. Una regresión intermedia tuvo 18 fallos: 3 expectativas de actor sin lab_folios.resolve y 15 por un llamador LAB Externo del helper de captura pendiente de adaptar. Se corrigieron pruebas/permisos esperados y el llamador, sin ampliar permisos. La primera integración PostgreSQL tuvo los mismos 3 fallos de expectativa, resueltos en el resultado vigente.

### Comandos de esta revisión

Desde backend, SQLite exclusivamente en memoria:

```sh
DATABASE_URL=sqlite:// ../.venv/bin/python -m pytest tests/test_lab_work_orders.py tests/test_lab_work_order_deliveries.py tests/test_lab_equipment_soft_delete.py tests/test_lab_field_sheets_capture.py tests/test_lab_field_sheets_external.py tests/test_general_service_delivery.py tests/test_general_service_closure.py tests/test_technical_interventions.py tests/test_technical_intervention_authority.py tests/test_technical_intervention_api.py tests/test_operational_ticket_self_resolution.py tests/test_service_order_mobile_execution.py tests/test_service_order_mobile_administration.py tests/test_lab_delivery_correction_impacts.py tests/test_service_order_lab_links.py tests/test_service_order_mobile_calibration.py tests/test_lab_capture_packages.py tests/test_lab_delivery_timestamp_defaults.py tests/test_lab_delivery_pdfs_branding.py tests/test_lab_phase6_field_sheet_revisions.py -q -rs --disable-warnings
```

PostgreSQL nuevo, desechable y apagado al terminar, en /tmp/myc-phase3b-fixes.lM37zu/data; cada fixture usa esquema UUID y lo elimina. Sólo se creó metadata en public de esta base desechable para las pruebas preexistentes de folios. Los comandos siguientes apuntaron explícitamente a ella:

```sh
export DATABASE_URL=postgresql+psycopg://saulcortes@127.0.0.1:55484/myc_phase3b_test
MYC_PHASE3B_POSTGRES_TEST_URL="$DATABASE_URL" ../.venv/bin/python -m pytest tests/test_lab_delivery_correction_impacts.py tests/test_lab_delivery_correction_impacts_postgres.py tests/test_service_order_mobile_execution.py tests/test_service_order_mobile_administration.py -q --disable-warnings
LAB_POSTGRES_TEST_URL="$DATABASE_URL" ETS_LAB_POSTGRES_TEST_URL="$DATABASE_URL" ../.venv/bin/python -m pytest tests/test_lab_work_orders.py tests/test_lab_equipment_soft_delete.py tests/test_service_order_lab_links.py tests/test_lab_delivery_timestamp_defaults.py tests/test_lab_phase6_field_sheet_revisions.py -k 'postgres or migrated_schema' -q -rs --disable-warnings
LAB_POSTGRES_TEST_URL="$DATABASE_URL" ../.venv/bin/python -m pytest tests/test_lab_delivery_timestamp_defaults.py::test_lab_delivery_tables_have_real_server_defaults_after_migration -q --disable-warnings
```

Desde frontend: `node --test src/components/ets-mobile/*.test.js` y `npm run build`. Desde myc-mobile: `npm test` y `npx tsc --noEmit`. Desde raíz: `python3 scripts/generate_project_file_registry.py` y `git diff --check`.

Logs temporales: /tmp/phase3b-fixes-regression-final.log, /tmp/phase3b-fixes-pg-final.log, /tmp/phase3b-fixes-pg-extra.log, /tmp/phase3b-fixes-pg-defaults.log, /tmp/phase3b-fixes-web.log, /tmp/phase3b-fixes-mobile.log, /tmp/phase3b-fixes-build.log, /tmp/phase3b-fixes-tsc.log. No forman parte del producto.

Riesgos restantes: ciclo administrativo de resolución/reemisión/reentrega fuera de alcance; no QA manual en dispositivo ni navegador autenticado; un fallo PostgreSQL de fixture y dos errores TypeScript de dependencias locales impiden declarar toda la regresión general verde. Sin commit, push, despliegue ni migraciones operativas; worktree fuente y respaldo intactos.

## Resultados anteriores a las cinco correcciones

| Ejecución | Resultado |
| --- | --- |
| Regresión backend LAB/ETS/Servicio General/intervenciones, 19 archivos | 474 passed, 17 skipped, 0 failed; 97.91 s |
| Los 17 casos PostgreSQL omitidos, ejecutados por separado | 16 passed, 1 failed; 17.63 s |
| Fase 3B + ETS + migración/concurrencia, PostgreSQL | 68 passed, 0 failed, 0 skipped; 59.46 s |
| ETS Mobile Node | 34 passed, 0 failed |
| Frontend completo disponible con Node, 33 archivos | 177 passed, 2 failed; 179 casos/unidades reportados |
| Vite build | Correcto; advertencia existente de chunks mayores de 500 kB |
| Inventario | Generación idempotente; 39 rutas existentes con fila única |
| git diff --check | Exit 0, sin salida |

Los conjuntos se solapan; no se suman como pruebas únicas.

### Fallos restantes, reproducidos en HEAD

1. PostgreSQL: `test_postgresql_concurrent_individual_cohorts_get_distinct_versions` construye equipo sin tipo de servicio y falla antes de la operación de concurrencia con `LAB_RECEPTION_INCOMPLETE`. Mismo fallo en una copia temporal de HEAD: 1 failed, 3.42 s. No se relajó la regla de recepción.
2. Frontend: `notificationNavigation.test.js` espera `/communications`, pero la autoridad vigente devuelve `/dashboard?work_order_id=12#servicios`.
3. Frontend: `clients.test.js` importa `vitest`, no disponible en el entorno/dependencias actuales; no se ejecutaron sus assertions con ese runner.

Los dos últimos y la prueba CSS LAB preexistente se reprodujeron en copia temporal de HEAD: 17 passed, 3 failed. La prueba CSS se corrigió en el archivo ETS ya intervenido: antes incluía todo el CSS posterior de correo; ahora limita el bloque LAB. Los otros fallos permanecen fuera del alcance autorizado.

Durante la adaptación también se corrigieron: una expectativa fuente de elegir la última entrega ambigua (contraria a main), los tokens de fixture para rutas Mobile y un lanzamiento inicial desde la raíz que impedía a una prueba heredada encontrar `app/routers/lab_work_orders.py`. Los resultados finales backend se ejecutaron desde `backend/`.

## Comandos ejecutados

Directorio backend: `/Users/saulcortes/Developer/myc_erp/backend`. Variables de conexión usadas únicamente para el clúster temporal:

```sh
export DATABASE_URL=postgresql+psycopg://saulcortes@127.0.0.1:55483/myc_phase3b_test
export PYTHONPATH=.
```

Regresión SQLite (las fixtures sustituyen la sesión por bases en memoria; no se activa la variante PostgreSQL):

```sh
../.venv/bin/python -m pytest tests/test_lab_work_orders.py tests/test_lab_work_order_deliveries.py tests/test_lab_equipment_soft_delete.py tests/test_lab_field_sheets_capture.py tests/test_lab_field_sheets_external.py tests/test_general_service_delivery.py tests/test_general_service_closure.py tests/test_technical_interventions.py tests/test_technical_intervention_authority.py tests/test_technical_intervention_api.py tests/test_operational_ticket_self_resolution.py tests/test_service_order_mobile_execution.py tests/test_service_order_mobile_administration.py tests/test_lab_delivery_correction_impacts.py tests/test_service_order_lab_links.py tests/test_service_order_mobile_calibration.py tests/test_lab_capture_packages.py tests/test_lab_delivery_timestamp_defaults.py tests/test_lab_delivery_pdfs_branding.py -q -rs --disable-warnings
```

Fase 3B PostgreSQL:

```sh
MYC_PHASE3B_POSTGRES_TEST_URL="$DATABASE_URL" ../.venv/bin/python -m pytest tests/test_lab_delivery_correction_impacts.py tests/test_service_order_mobile_administration.py tests/test_service_order_mobile_execution.py tests/test_lab_delivery_correction_impacts_postgres.py -q -rs --disable-warnings
```

Pruebas heredadas previamente omitidas (antes se creó metadata vacía en public de la base desechable para la prueba de asignación de folios):

```sh
LAB_POSTGRES_TEST_URL="$DATABASE_URL" ETS_LAB_POSTGRES_TEST_URL="$DATABASE_URL" ../.venv/bin/python -m pytest tests/test_lab_work_orders.py::test_postgresql_concurrent_direct_groups_do_not_duplicate_folios tests/test_lab_work_orders.py::test_postgresql_concurrent_individual_cohorts_get_distinct_versions tests/test_lab_work_orders.py::test_postgresql_concurrent_lab_certificate_folio_allocation_is_unique tests/test_lab_work_orders.py::test_postgresql_ticket_approval_locks_only_ticket_row tests/test_lab_work_orders.py::test_postgresql_ticket_rejection_cannot_be_resolved_again tests/test_lab_work_orders.py::test_postgresql_concurrent_ticket_resolution_allows_one_winner tests/test_lab_work_orders.py::test_postgresql_concurrent_folio_allocation_is_unique tests/test_lab_equipment_soft_delete.py::test_postgresql_equipment_soft_delete_preserves_constraints_and_history tests/test_service_order_lab_links.py::test_postgres_concurrent_requests_preserve_invariants tests/test_service_order_lab_links.py::test_postgres_competing_replacements_leave_loser_history_intact tests/test_lab_delivery_timestamp_defaults.py::test_lab_delivery_tables_have_real_server_defaults_after_migration tests/test_lab_delivery_timestamp_defaults.py::test_full_delivery_on_migrated_schema_never_sends_manual_timestamps tests/test_lab_delivery_timestamp_defaults.py::test_partial_delivery_on_migrated_schema_never_sends_manual_timestamps -q -rs --disable-warnings
```

Grafo, sin ejecutar migraciones operativas:

```sh
../.venv/bin/python -m alembic heads
../.venv/bin/python -m alembic history -r ffcd7b40ac46:head
```

Frontend, directorio `/Users/saulcortes/Developer/myc_erp/frontend`:

```sh
node --test src/components/ets-mobile/*.test.js
npm run build
```

La ejecución completa usó esta expansión determinista de archivos:

```python
files = sorted(str(p) for p in pathlib.Path('src').rglob('*.test.js'))
subprocess.run(['node', '--test', *files])
```

Baseline: se extrajeron `backend`, `frontend/src` y `frontend/package.json` de HEAD mediante `git archive` a `/tmp/myc-phase3b-pg.mfNGOl/baseline`; allí se ejecutaron los tres tests frontend indicados y el único test PostgreSQL fallido, usando el mismo intérprete y base desechable. No se alteró main ni la fuente para esa comparación.

Desde la raíz del repositorio:

```sh
python3 scripts/generate_project_file_registry.py
git status --short --branch
git diff --check
```

Logs de esta ejecución: `/tmp/myc-phase3b-pg.mfNGOl/` (`regression-final.log`, `postgres-final.log`, `postgres-extra.log`, `postgres-baseline.log`, `frontend.log`, `frontend-all.log`, `frontend-baseline.log`, `build-final.log`). Son evidencia temporal local, no artefactos productivos.

## Riesgos y pendientes

- Resolución/cancelación administrativa, reemisión y reentrega expresamente fuera de alcance. Los impactos quedan pending; la invalidación bloquea nuevos recibos finales mientras persista. No existe transición automática por cierre técnico.
- Tres fallos preexistentes detallados arriba impiden declarar toda la regresión general verde. La suite específica de integración sí pasa.
- No se realizó QA manual autenticado en navegador ni despliegue; frontend validado con tests Node y build.
- La migración no está aplicada a ninguna base operativa. La revisión final no autoriza por sí sola commit, publicación o migración.
- Los contratos de reapertura por ticket/directa aceptan decisiones; las interfaces nativas ajenas a ETS que no las envíen recibirán el rechazo seguro cuando haya entregas. Se adapta la pantalla existente de entrega de MYC Mobile para mostrar disponibilidad del acuse; no se añaden pantallas de resolución administrativa.

## Documentación actualizada

Actualizados estado operativo, inventario, contratos LAB/ETS, alcance, reglas, flujo, decisiones, estado de proyecto, observaciones y deuda; el índice enlaza esta fotografía. No se alteraron cierres históricos ni se crearon estados de resolución ficticios. Revisados sin cambios en esta revisión: `AGENTS.md`, `myc-mobile/AGENTS.md` y `docs/project/DOCUMENTATION_INDEX.md` (mantiene la referencia existente). No se movieron ni archivaron documentos. Única nueva evidencia documental: este archivo.

## Estado Git al finalizar

```text
## main...origin/main
 M backend/app/models/__init__.py
 M backend/app/models/lab_delivery_item.py
 M backend/app/routers/lab_work_orders.py
 M backend/app/schemas/lab_work_order.py
 M backend/app/schemas/operational_ticket.py
 M backend/app/schemas/service_order_mobile_execution.py
 M backend/app/services/lab_field_sheets.py
 M backend/app/services/lab_field_sheets_external.py
 M backend/app/services/lab_work_order_deliveries.py
 M backend/app/services/lab_work_orders.py
 M backend/app/services/operational_tickets.py
 M backend/app/services/service_order_mobile_administration.py
 M backend/app/services/service_order_mobile_execution.py
 M backend/tests/test_lab_equipment_soft_delete.py
 M backend/tests/test_service_order_mobile_execution.py
 M docs/BACKUP_ESTADO_ACTUAL.md
 M docs/PROJECT_FILE_REGISTRY.md
 M docs/architecture/ETS_LAB_TECHNICAL_BRIDGE.md
 M docs/architecture/LAB_WORK_ORDERS.md
 M docs/project/BUSINESS_RULES.md
 M docs/project/CURRENT_PROCESS_FLOW.md
 M docs/project/CURRENT_SCOPE.md
 M docs/project/DECISIONS.md
 M docs/project/DOCUMENTATION_INDEX.md
 M docs/project/OBSERVATIONS_REGISTER.md
 M docs/project/PROJECT_STATUS.md
 M docs/project/TECHNICAL_DEBT.md
 M frontend/src/components/ets-mobile/EtsMobileCorrectionDialog.jsx
 M frontend/src/components/ets-mobile/EtsMobileEquipmentDetail.jsx
 M frontend/src/components/ets-mobile/EtsMobileExecutionPanel.jsx
 M frontend/src/components/ets-mobile/etsMobilePanels.test.js
 M frontend/src/components/ets-mobile/mobileExecutionPresentation.js
 M frontend/src/components/ets-mobile/mobileExecutionPresentation.test.js
 M myc-mobile/app/(technician)/work-orders.tsx
 M myc-mobile/src/types/lab-work-order.ts
 M myc-mobile/src/wiring-tests/lab-delivery-flow.wiring.test.ts
 M scripts/generate_project_file_registry.py
?? backend/app/models/lab_delivery_item_correction_impact.py
?? backend/app/services/lab_delivery_correction_impacts.py
?? backend/migrations/versions/a3c5e7f9b1d2_lab_delivery_item_correction_impacts.py
?? backend/tests/test_lab_delivery_correction_impacts.py
?? backend/tests/test_lab_delivery_correction_impacts_postgres.py
?? docs/audits/PHASE3B_INTEGRATION_2026-10-20.md
?? frontend/src/components/ets-mobile/correctionDeliveryImpact.js
?? frontend/src/components/ets-mobile/correctionDeliveryImpact.test.js
```

`git diff --check`: exit 0, sin salida. Cambios sin stage/commit; HEAD permanece en `752394a4d8040033635022d354f921a3209488fd`.
