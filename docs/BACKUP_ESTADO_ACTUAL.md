> Estado: VIGENTE
>
> Tipo: Vigente (estado operativo verificable)
>
> Autoridad: Media; no sustituye los documentos canónicos de `project/`
>
> Corte actualizado: 2026-08-25

# Estado operativo actual del ERP MYC

## Dictamen del corte

- Versión declarada: `0.4.0`.
- Estado canónico de módulos: [`project/PROJECT_STATUS.md`](project/PROJECT_STATUS.md); no fue modificado por la auditoría diagnóstica.
- Auditoría integral vigente: [`audits/auditoria_integral_2026_08_10/AUDITORIA_INTEGRAL_ERP_MYC_2026_08.md`](audits/auditoria_integral_2026_08_10/AUDITORIA_INTEGRAL_ERP_MYC_2026_08.md).
- Dictamen técnico del corte: **NO APTO PARA PRODUCCIÓN**, readiness 61/100.
- Estado agregado: 42 módulos; 1 SELLADO, 9 CASI SELLADOS, 28 EN
  DESARROLLO, 2 PENDIENTES y 2 NO INICIADOS.
- La Contención de Seguridad Etapa 1 cerró API sin protección uniforme, portal
  sin aislamiento y secreto JWT productivo inseguro; la revisión de sus seis
  commits y la repetición de pruebas emitieron el dictamen **APROBADA Y
  CERRADA** el 2026-08-04.
- La Etapa 2A corrigió y validó la integridad de esquema y recuperación; la
  Etapa 2B formalizó el snapshot técnico del Catálogo Institucional. La
  validación funcional posterior revisó 36 módulos, 213 acciones y 798 filas y
  produjo el catálogo objetivo de 42 módulos, 181 acciones y 657
  microacciones. Su nomenclatura fue revisada completamente para expresar
  decisiones de negocio comprensibles por administración funcional y la
  versión 1.0 quedó **APROBADA Y CONGELADA COMO AUTORIDAD FUNCIONAL**, con
  naturaleza, criticidad y alcance en las 657 microacciones, sin implementar
  administración dinámica de accesos ni cambiar permisos vigentes.
- El sprint **Integridad ETS** está **APROBADO CON OBSERVACIONES**: servicio
  único, lifecycle persistente `requested → authorized → executed`, actor
  obligatorio en contratos críticos ETS y autoautorización administrativa en
  tres acciones auditables separadas; regresión completa verde.
- La **Fase 1 ETS múltiple/evolucionado** está **EN REVISIÓN**: unidades
  estables con origen/capacidad por unidad, etapas append-only, lifecycle
  técnico separado de solicitudes comerciales, decisión interna autorizada y
  única por partida, categorías validadas, Activity contextual y tareas
  `#tarea`. No abre workflows técnicos de categorías posteriores.
- La corrección fundacional de identidad operativa está **EN REVISIÓN**:
  `operational_category` distingue categorías conocidas, la cotización congela
  snapshot esquema 2 por componente y editar/reabrir con el mismo concepto no
  consulta el catálogo vigente. Sólo `general_service` habilita diagnóstico
  evolutivo. La propuesta de Hojas de Campo permanece en el resolver frontend.
- El vertical **ETS Venta** está **TERMINADO TÉCNICAMENTE — EN REVISIÓN**:
  materializa unidades o cantidades desde snapshot, registra arribo exclusivo
  del asesor, discrepancias/autorizaciones, calibración sobre la misma unidad,
  garantía y entregas parciales por recolección, paquetería o técnico. Portal y
  MYC Mobile confirman recepción con evidencia. La auditoría tester quedó
  corregida: unidades no evolutivas, vínculo comercial estricto de calibración,
  garantía no terminal por defecto, firma/atestación acotada y PDF escapado.
  Falta aceptación física/browser.
- El vertical **ETS Mantenimiento** está **TERMINADO TÉCNICAMENTE — EN REVISIÓN**:
  crea unidades/etapas no evolutivas desde snapshot, cubre preventivo/correctivo,
  laboratorio/campo, OT/equipo, pausas, captura estructurada, materiales,
  decisión comercial, investigación, reporte versionado, firma y cierre. Los
  bloqueantes web son visibles y navegables; faltan aceptación física/browser
  y las integraciones futuras de Compras/Almacén.
- El acceso móvil técnico backend está **TERMINADO — EN REVISIÓN**: ocho
  lecturas conservan ownership y tres rutas Venta permiten sólo listar, aceptar
  y confirmar entregas asignadas con evidencia. La app LAB no consume
  eliminación productiva.
- La eliminación física de OT productiva está **IMPLEMENTADA Y VALIDADA**:
  Administrador usa `service_orders.delete`; el backend elimina el
  agregado exclusivo sin restricción de estado, preserva ETS, factura,
  cotización, Motor y firma compartida, registra auditoría mínima y restaura
  base/archivos ante fallo. MYC Mobile no consume ese DELETE productivo.
- OT LAB móvil está **EN DESARROLLO** con implementación técnica completa:
  agregado aislado, folios 6400–6999, grupos raíz/adicional, máximo 10 equipos,
  una sesión de firma compartida, bloqueo posterior, PDF individual y
  exportación ZIP. Ahora permite eliminar una OT LAB individual con
  `lab_work_orders.delete`, repara raíz/cadena, conserva firmas/tickets/revisiones
  compartidos, confirma/refresca en móvil y estabiliza tarjetas con clientes
  largos. Desde el corte 2026-08-14 agrega filtros SQL separados por
  folio/cliente, estado y paginación; Tickets, revisión autorizada, snapshots,
  PDFs por revisión, firma histórica/activa, invalidación automática y control
  optimista. La resolución de Tickets conserva `FOR UPDATE` exclusivamente
  sobre la fila del ticket y rechaza con 409 cualquier segunda decisión; la
  regresión real PostgreSQL cubre ambas políticas de firma, rechazo y carrera
  con un único ganador. La captura y el detalle de Tickets ya respetan safe
  area, agrupan los campos y ocultan
  teléfono/correo; el PDF separa Domicilio, C.P., Ciudad, Estado y orden de
  compra sin `0` por ausencia. La firma móvil permite orientación dinámica,
  secuencia Cliente → Técnico, strokes normalizados resistentes al resize,
  ownership del gesto Android y contexto exclusivo por `root_work_order_id`.
  El borrador elevado sobrevive refetch, objetos nuevos, rerender, reapertura
  visual y navegación entre hermanas; una raíz distinta lo reemplaza por uno
  vacío y volver al grupo previo no recupera su captura. No conecta el LAB al
  ERP productivo. La guardia incorrecta sobre `signature_required` fue retirada:
  una OT inicial `draft` lleva `false`, llega al POST y el backend decide; tap o
  movimiento despreciable ya no cuenta como firma. Falta aceptación táctil
  completa Android/iOS y una nueva build.
- Notifications V1 está **TERMINADO TÉCNICAMENTE — EN REVISIÓN FÍSICA**:
  reutiliza `Notification`, registra `PushDevice`, persiste cinco eventos de
  Tickets con destinatarios por permiso/solicitante, entrega Expo posterior al
  commit y agrega centro, badge, deep links y refresco automático sin polling.
  No hubo build EAS, despliegue ni migración de base compartida.
- Comunicaciones Etapas A–I está **TERMINADA TÉCNICAMENTE — EN REVISIÓN**:
  REST/PostgreSQL conserva la verdad y WebSocket v1 publica post-commit;
  incorpora orden/idempotencia, sync, optimistic UI/retry, typing, recibos,
  menciones, grupos, multi-dispositivo, push y lifecycle móvil. Producción se
  verificó single-worker, por lo que el hub en memoria es válido; un aumento
  futuro exige backplane. Falta aceptación física en dos dispositivos y no
  hubo build EAS ni despliegue.
- El login de MYC Mobile reproduce la vista aprobada `01_login.png` con el
  emblema institucional existente, layout responsive, teclado/safe areas,
  botón `#003DA5` y versión derivada de Expo. Conserva AuthProvider, endpoint,
  SecureStore, permisos y navegación; recuperación de contraseña continúa sin
  flujo funcional y se muestra deshabilitada. Permanece pendiente revisión en
  dispositivo y el cambio no está committeado por solicitud expresa.
- El P0 **Integridad de autenticación de Certificados** está **TERMINADO — EN
  REVISIÓN**: Calidad es la única superficie mutante, ETS perdió endpoint/lote
  y acciones, y `certificate_authentication.authenticate_certificate` conserva
  lock, actor, origen, audit, evento y commit únicos.
- **Verificación metrológica** está **IMPLEMENTADA — EN REVISIÓN** como
  variante del pipeline existente: ETS/OT/Equipment/Hoja/Captura/Calidad,
  certificado `verification`, título institucional, folio
  `MYCV-MM-AA-XXXX` con `XXXX` anual desde `0001`, autenticación, versiones y liberación compartidas. La
  asociación por `ServiceOrderItem` conserva coexistencia con Calibración y
  rechaza alcances acreditado/trazable/vinculado. El concepto conserva un
  Master genérico inicial dentro del bonche. Captura lo sustituye fuera del ERP
  por el archivo técnico real y reingresa el ZIP; el backend asocia
  certificado/equipo por identidad fuerte, reconoce de forma única un Master
  activo registrado estructuralmente como Verificación y congela automáticamente
  documento/versión final con historial, actor y origen. Nombre, código y
  descripción no deciden la identidad. Una vez congelado el final, documento,
  versión y ruta snapshot son autoridad histórica: no se vuelve a ejecutar la
  resolución institucional, A→A es idempotente y A→B se rechaza incluso sin
  evidencia identificada. No se agregó esquema ni migración y no se modificó
  la base local.
- La conciliación **TD-027** deja el capability gate **VERDE** en 29/0 y el
  bootstrap cubre 83/83 permisos HTTP. Las diferencias gobernadas incluyen
  `lab_work_orders.use/export/delete` y `tickets.create/view_own/review`,
  además de `service_orders.sales.manage/deliver/authorize`. Portal usa
  `portal.read`; la clave legacy
  `portal.view` quedó inactiva y sin asignaciones, y
  `reference_standard_certificates.delete` se asigna con menor privilegio.
  TD-027 permanece **BLOQUEADO POR DECISIÓN** para granularización institucional.
- Bloqueadores dominantes restantes: mutaciones sin actor auditable fuera de
  ETS, sesiones sin revocación/rotación, decisiones de granularización, CFDI productivo
  incompleto y ausencia de CI/E2E/observabilidad; almacenamiento durable y
  antimalware requieren decisión operativa posterior a ETAPA 3.
- ETAPA 3 de archivos y cargas quedó **TERMINADA, EN REVISIÓN**: centraliza
  perfiles, ZIP/Office/PDF/XML/imagen, escritura atómica y entrega contenida;
  retiró datos operativos/dump del índice sin borrar evidencia local.
- El Portal del Cliente quedó **TERMINADO, EN REVISIÓN** con autenticación
  externa separada, registro/verificación, invitaciones, membresías y roles
  propios, aislamiento persistente por cliente, administración conjunta
  multirrol en Ajustes/Clientes, configuración, bandejas de vinculación y
  sección Usuarios dentro del Portal. Correo productivo, MFA, recuperación y
  revocación de sesiones permanecen pendientes explícitos.

## Árbol de trabajo preservado

Al inicio de la Etapa 2 ya existían cambios y archivos no rastreados en
frontend, documentación comprimida, auditorías y storage. Se preservaron como
trabajo previo o concurrente y no forman parte de esta etapa.

Las tres migraciones locales pendientes fueron revisadas y adoptadas
oficialmente en la cadena lineal:

- `backend/migrations/versions/c14c5d6e7f80_fix_quotation_service_change_timestamps.py`
- `backend/migrations/versions/d15d6e7f8091_fix_notification_timestamp_defaults.py`
- `backend/migrations/versions/e16e7f8091a2_fix_institutional_folio_timestamp_defaults.py`

Sobre ellas se agregó `f27f8a90b1c3_reconcile_schema_integrity.py`, nuevo head
único y reversible.

## Persistencia y migraciones

- Motor: PostgreSQL, SQLAlchemy y Alembic.
- Head aplicado a la base local compartida: `f7c9d1e3a5b7`.
- Head del código: `d1f3a5c7e9b2`.
- `e7b62b8a9421` incorpora `service_order_exception_requests` para conservar
  solicitud, autorización, ejecución, actores, timestamps y estado ETS de
  revalidación sin usar auditoría como almacenamiento de lifecycle.
- `f4a1c9d2e710` incorpora el núcleo ETS múltiple/evolucionado, decisiones por
  partida, solicitudes técnicas, tareas y backfill de equipos históricos con OT.
- `a7c2e5f8b1d4` endurece Fase 1 con origen/categoría/capacidad por unidad y
  unicidad de decisión; su upgrade/downgrade fue correcto en PostgreSQL aislado.
- El working tree contiene además la migración concurrente ajena
  `fdc1c503a353`, también hija de `f4a1c9d2e710`. La migración LAB
  `c6e8a1b4d2f9` preserva y fusiona ambos heads mientras crea exclusivamente
  tablas LAB; en PostgreSQL temporal quedó como head único y `alembic check`
  limpio. `d4e7a9c2b6f1` agrega Tickets/revisiones LAB y fue validada con
  upgrade/downgrade/upgrade en PostgreSQL aislado; la base compartida permanece
  en `c6e8a1b4d2f9` y no fue modificada por este sprint.
- `e6b8c0d2f4a6` agrega idempotencia/estado de entrega a `notifications` y la
  tabla `push_devices`. En PostgreSQL aislado quedó como head único,
  `alembic check` limpio y navegó `d4e7a9c2b6f1 → e6b8c0d2f4a6 →
  d4e7a9c2b6f1 → e6b8c0d2f4a6`.
- `f7c9d1e3a5b7` completa Comunicaciones con secuencia/idempotencia, grupos,
  cursores de participante, recibos y menciones normalizados y relación
  opcional a Tickets. El ciclo aislado y `alembic check` quedaron limpios.
- `a8c0e2f4b6d8` agrega identidad operativa canónica a Catálogo, Cotizaciones y
  partidas ETS; el ciclo aislado `base → head → f7c9d1e3a5b7 → head` fue
  correcto y `alembic check` no detectó operaciones nuevas; la base temporal
  fue eliminada. La base local compartida se
  conserva en `f7c9d1e3a5b7`; por ello no se regeneró el respaldo oficial.
- `b9d1f3a5c7e9` agrega configuración de Venta, categoría `sale` en etapas y
  las tablas normalizadas de partidas, unidades, autorizaciones y entregas. El
  ciclo aislado `base → head → base → head` y `alembic check` fueron correctos.
  La base compartida y el respaldo permanecen deliberadamente en
  `f7c9d1e3a5b7`; no se modificaron ni regeneraron en este trabajo.
- `c0e2f4a6b8d1` desactiva evolución genérica exclusivamente para unidades
  Venta históricas. No cambia esquema; el ciclo PostgreSQL
  `base → head → base → head` y `alembic check` quedaron correctos contra este
  nuevo head; la base temporal fue eliminada.
- `d1f3a5c7e9b2` agrega configuración congelable de Mantenimiento y las tablas
  normalizadas de ejecución, pausas, materiales y cambios de alcance. El ciclo
  PostgreSQL `base → head → base → head` y `alembic check` quedaron correctos;
  la base temporal fue eliminada y la base compartida/respaldo no se tocaron.
- Ciclo completo vacío `base → head → base → head`: **CORRECTO** en PostgreSQL
  aislado mediante `scripts/toolkit/db/validate-schema-cycle.sh`.
- Upgrade desde el respaldo histórico en `b03b4c5d6e7f` hasta el head:
  **CORRECTO**, con 102 tablas públicas y `alembic check` limpio.
- Se añadieron defaults de servidor `now()` a 16 columnas NOT NULL
  `created_at`/`updated_at` en ocho tablas:
  - `activity_attention_requests`
  - `activity_thread_reads`
  - `linked_companies`
  - `uncertainty_calculations`
  - `uncertainty_components`
  - `uncertainty_formulas`
  - `uncertainty_model_exceptions`
  - `uncertainty_models`
- Se reconciliaron índices y columnas faltantes del ORM; los índices parciales,
  de expresión y de búsqueda administrados deliberadamente por migraciones
  quedaron excluidos de autogeneración mediante una lista explícita.
- Se corrigieron downgrades históricos de firmas de ETS y la denominación de
  una FK de cotizaciones para asegurar la reversibilidad de la cadena completa.

## Respaldo oficial

- `backup_erp_myc_antes_prueba.sql` está presente en la raíz, fue regenerado
  después de aplicar el head y mide 75,050,260 bytes.
- SHA-256 verificable:
  `f2280b0e003f582601462b269f3b3fb1165e58d00acf247d8c8564f691b81b14`.
- El restore drill aislado recuperó 130 tablas públicas y
  `alembic_version=f7c9d1e3a5b7`; la base temporal fue eliminada.
- El procedimiento vigente permanece en
  `architecture/database/SCHEMA_RECOVERY.md`.

## Validaciones ejecutadas

| Validación | Resultado |
| --- | --- |
| Backend canónico | 575 passed, 5 skipped, 19 subtests passed, 3 warnings deprecados |
| Identidad operativa/snapshot focal | 38 passed, 12 subtests; congelamiento, reapertura, categorías conocidas/Servicio General, compuestos, calibración y Hojas de Campo |
| Comunicaciones/realtime focal | 14 passed; persistencia→evento, deduplicación, sync, recibos, menciones, IDOR, typing y multi-dispositivo |
| Concurrencia Comunicaciones PostgreSQL | 5 escritores conservaron secuencias 1–5; 2 reintentos simultáneos compartieron un solo mensaje/sequence 6; base temporal eliminada |
| Aislamiento móvil técnico | 21 passed; ETS/OT/Equipo/Hoja A/B, sin asignación, 401, 403 y doble permiso de hojas |
| Escenarios Fase 1 ETS múltiple/evolucionado | 10 passed; A–H, permisos, mixto SG/calibración/mantenimiento, evolución indebida/posterior, lifecycle, categorías y unicidad |
| Regresión focal ETS/calibración/Activity/cotizaciones/permisos | 53 passed, 2 warnings |
| Autenticación real y autoridad canónica | 12 passed; LibreOffice real, adapter HTTP, lock, actor, audit/evento y doble autenticación |
| Pruebas dirigidas Integridad ETS y módulos relacionados | 67 passed, 7 subtests; actor obligatorio, mismo Administrador en tres etapas, audit/eventos, no mutación en requested/authorized, ejecución autorizada, revalidación y router sin reglas |
| Pruebas dirigidas ETAPA 3 | 78 passed, 7 subtests |
| Pruebas dirigidas de integridad de esquema | 3 passed, 1 warning deprecado de configuración Alembic |
| Pruebas dirigidas de seguridad | 22 passed |
| Frontend `node --test` | 43 passed |
| Frontend `npm run build` | correcto; warning de chunk >500 kB |
| Backend `compileall` | correcto |
| Backend suite completa del corte | 575 passed, 5 skipped y 19 subtests; head esperado sincronizado en `d1f3a5c7e9b2` |
| ETS Venta/identidad/evolución focal | 31 passed; evolución exclusiva de Servicio General, vínculo comercial de calibración, garantía, evidencia acotada, PDF escapado, Portal/Mobile, parciales y snapshot |
| ETS Mantenimiento focal | 11 passed; preventivo/correctivo, laboratorio/campo, OT/equipo, pausas, materiales, alcance, Reparación separada, investigación, reporte, firma, cierre, snapshot y ETS múltiple |
| Inventario FastAPI | 436/436 operaciones clasificadas; CSV regenerado canónicamente y coincide con runtime |
| Eliminación OT productiva dirigida | 43 passed; admin/403/404, estados, dependencias, bloqueo por evidencia inmutable, firma compartida, factura, lectura móvil y rollback de base/archivo |
| Frontend eliminación OT | 5 passed; capacidad exacta, ocultamiento sin permiso y regresión de access control/autenticación |
| OT LAB backend/API/PDF/export/Tickets/eliminación | 26 passed, 5 skipped sin URL PostgreSQL; cubre autorización, estados, datos exclusivos, raíz/intermedia, hermanas, firma/ticket/revisión compartidos, rollback y conformidad |
| Tickets sobre PostgreSQL real | 4 passed en dos bases temporales eliminadas al finalizar: approve preserve, approve invalidate, rechazo definitivo y carrera approve/reject con un único 200 y un 409 |
| Notifications/Tickets/OT focal | 23 passed, 5 skipped; devices idempotentes/multiusuario, ownership, lectura/paginación, eventos create/approve/reject/resolve/signature-required, Expo mock y resiliencia |
| Notifications backend específica | 4 passed; incluye éxito, `DeviceNotRegistered`, proveedor caído y persistencia del dominio/notificación |
| Migración LAB PostgreSQL temporal | `base → c6e8a1b4d2f9`; current correcto; `alembic check` sin operaciones nuevas; asignador concurrente `[6400, 6401]`; carrera de OT adicional: una `6403` y un rechazo `409`; base temporal eliminada |
| `myc-mobile` TypeScript/lint | correcto / correcto; sin errores ni warnings |
| `myc-mobile` firma LAB y regresión completa | 62 passed: Notifications 8, Realtime 7, Communications 9, eliminación 6, reapertura 5, firma/contexto/handler 23 y push policy 4; incluye frontera raíz, tap inválido, delegación de `applySignatures` y POST con `signature_required=false`; TypeScript/lint verdes; Expo config conserva `orientation=default` |
| Cadena backend LAB de firma | prueba focal existente `1 passed`; diagnóstico efímero: `draft`, `signature_required=false`, sin sesión → POST `/signatures` 200 → `ready_for_signatures`, sesión presente → cierre/PDF correcto. No modificó base local ni imprimió firmas |
| `myc-mobile` eliminación OT LAB | 6 passed; capacidad exacta, aislamiento productivo, cancelar, endpoint LAB, `204/403/404/409`, red, doble envío y contrato de nombres largos |
| `myc-mobile` bundle iOS Expo 54 | correcto; 1,160 módulos, bundle Hermes de 2.97 MB y assets exportados a directorio temporal fuera del workspace |
| `myc-mobile` política de refresco | 4 passed; eventos, foreground, deduplicación y throttle/mutación local |
| `myc-mobile` Communications/realtime | 7 passed; reconciliación/failed, comandos, backoff, resync, refresh por 4401, background/logout y cierres |
| Realtime backend Etapa A+A–I | 14 passed; auth/rechazos, identidad, ownership/IDOR, aislamiento, typing, persistencia/evento, sync, recibos, menciones y multi-dispositivo |
| Transporte WebSocket Uvicorn | `websockets 15.0.1`; handshake ASGI real sin credencial rechazado con HTTP 403 |
| `myc-mobile` Expo Doctor SDK 54 | 17/18 checks; `expo`, `expo-constants` y `expo-file-system` tienen desfase patch preexistente/concurrente |
| Aislamiento portal A/B | membresía propia 200, recurso ajeno 404, anónimo 401; autenticador interno rechaza token del portal |
| `scripts/myc doctor` | dependencias locales principales disponibles |
| Alembic ciclo vacío base→head→base→head | correcto en PostgreSQL aislado |
| Migración correctiva Fase 1 reversible | base aislada `base → a7c2e5f8b1d4 → f4a1c9d2e710 → a7c2e5f8b1d4`; current ETS correcto |
| Alembic upgrade desde respaldo histórico | correcto; b03→f27, 102 tablas |
| Alembic current/check | base principal en `f7c9d1e3a5b7`; código y base aislada en `a8c0e2f4b6d8`; check aislado sin operaciones nuevas |
| Respaldo oficial regenerado/restaurado | 75,050,260 bytes; SHA-256 `f2280b0e…b81b14`; restore drill con 130 tablas y head `f7c9d1e3a5b7` |
| Validador Catálogo Institucional/permissions/API | VERDE: baseline gobernado de 29 brechas literales y 0 de bootstrap; tres capacidades nuevas pertenecen al vertical ETS Venta EN REVISIÓN |
| Conteo Catálogo Funcional | 42 módulos, 181 acciones, 657 microacciones; IDs de acción únicos |
| Metadatos Catálogo Funcional | 657/657 con naturaleza, criticidad y alcance; alineación completa |
| Identidad y permisos del catálogo | microacciones, marcas y celdas de permisos sin cambios frente al corte previo a metadatos |
| `npm audit --omit=dev` | 2 vulnerabilidades altas: nanoid y PostCSS |
| `pip check` | correcto |
| Vulnerabilidades Python | NO VERIFICADAS; `pip-audit` ausente |
| `git diff --check` acotado a Etapa 2 | limpio; el árbol completo conserva espacios finales preexistentes en CSS ajeno a la etapa |

La evidencia histórica de auditoría se conserva en
[`audits/evidence/AUDITORIA_COMANDOS_2026-08-03.txt`](audits/evidence/AUDITORIA_COMANDOS_2026-08-03.txt);
los comandos vigentes de recuperación se documentan en
[`architecture/database/SCHEMA_RECOVERY.md`](architecture/database/SCHEMA_RECOVERY.md).

La evidencia actual de auditoría, incluidos comandos, módulos, fases, deuda,
seguridad e inventario, se conserva en
[`audits/auditoria_integral_2026_08_10/`](audits/auditoria_integral_2026_08_10/).

## Estado funcional verificable

- El ERP implementa clientes, catálogo, cotizaciones, ETS, OT, equipos, Hojas de Campo, Captura, Calidad, Certificados, Facturación, pagos, cartera, control documental, patrones, incertidumbre, Actividad, comunicaciones y ajustes con grados diferentes de cierre.
- Control Documental V1 conserva el único estado canónico `SELLADO`, dentro de su alcance acotado; la seguridad transversal impide inferir aptitud productiva.
- El Workbench de Facturación reutiliza el controlador único, el agregado `Invoice`, el contexto explícito y `EtsBillingTab`.
- Servicios Compuestos usa `service_kind`, `catalog_item_components` y expansión al crear ETS.
- Cotizaciones/ETS usan `operational_category` y snapshot operativo como autoridad histórica; Servicio General mantiene semántica evolutiva exclusiva.
- La acreditación de calibración mantiene las claves canónicas del contrato.
- Facturación dispone de borrador, snapshots, intentos PAC, XML/PDF, pagos y cartera, pero Facturama está configurado para Sandbox y faltan cancelación/sustitución, PPD/complemento y nota fiscal de egreso.
- Actividad implementa threads, mensajes, menciones, adjuntos, atención y no
  leídos; sus defaults de BD quedaron alineados y permanece pendiente la
  operación externa/observable.
- El Motor de Resoluciones tiene núcleo versionado, lifecycle, seguridad, idempotencia, locks, compensación, auditoría, outbox, cola/worker, API y SDK. Sólo dos definiciones están instaladas; la Fase 14 sigue pendiente de dictamen formal y el inicio desde módulos de origen no está cerrado.

## Seguridad y operación

- Inventario introspectado: 419 operaciones HTTP, todas clasificadas por el
  guard deny-by-default; el CSV canónico coincide con runtime.
- Toda ruta interna pasa por el guard deny-by-default y el arranque/prueba de
  conformidad fallan si aparece una operación sin clasificación.
- Clientes, Catálogo, Cotizaciones, ETS y Equipos exigen access JWT y permiso
  mínimo; no queda dependencia opcional de usuario en routers internos.
- Portal exige contexto propio, permisos efectivos y vínculo único derivado en
  backend; filtra listados y usuarios, rechaza recursos/membresías ajenos con
  404 y audita mutaciones y descargas.
- Producción rechaza secreto JWT ausente, conocido, corto o de entropía
  insuficiente; desarrollo permite el valor local explícito con advertencia.
- Refresh no autentica como access, access no renueva como refresh, el tipo es
  obligatorio y usuario inactivo/firma/expiración se rechazan.
- Navegación y acciones principales consumen permisos efectivos retornados por
  backend; acceso directo muestra denegación y 403/red tienen mensajes claros.
- El borrado de OT productiva exige `service_orders.delete` tanto
  en el guard transversal como en el router; sólo Administrador lo recibe hoy
  por `*` y la UI no infiere autoridad desde nombres de rol.
- Access/refresh se guardan en `localStorage`; no existe revocación/rotación formal de sesiones.
- Captura, imports, Actividad, Masters, PDFs y constancias comparten perfiles
  con tamaño, MIME, estructura y defensas ZIP; Facturama valida XML/PDF antes
  de publicar y las escrituras persistentes integradas son atómicas.
- No existe CI/CD, E2E browser, despliegue declarativo, readiness real,
  métricas, tracing ni alertas. El restore drill local ya está documentado y
  validado, pero aún debe incorporarse a la operación periódica automatizada.

## Pendientes obligatorios antes de producción

1. Programar sesiones revocables/rate limit y la evolución del RBAC
   institucional; PortalMembership y su administración ya están integrados.
2. Someter cualquier capacidad nueva al flujo Catálogo → revisión funcional →
   permiso institucional; no agregar claves directamente a `permissions.py`.
3. Diseñar en una etapa posterior el RBAC institucional dinámico sin mezclar
   roles internos con los roles ya normalizados del Portal.
4. Aprobar la custodia durable/antimalware posterior; ETAPA 3 ya protegió
   uploads y retiró datos operativos del índice conservando evidencia local.
5. Completar CFDI productivo y E2E de ETS→Certificado y Facturación→Pago.
6. Incorporar CI, observabilidad, despliegue reproducible y ejecución periódica del restore drill.
7. Mantener el inventario/conformidad de rutas y completar E2E browser por rol.
8. Automatizar el barrido observable de `.pending-deletions` (TD-040) para el
   caso excepcional de fallo del unlink posterior a un borrado confirmado.
9. Repetir en iOS/Android el checklist físico de eliminación LAB móvil
   para Administrador y usuario sin capacidad, incluidos cancelar, `204`,
   `403`, `404`, `409` y tarjetas con clientes largos (TD-037).
10. Ejecutar en dos dispositivos reales el checklist de Comunicaciones:
    simultaneidad, reconexión, push/deep links, typing, recibos,
    background/foreground y logout (TD-042).
11. Ejecutar el checklist browser/dispositivo/Portal de ETS Venta, incluidas
    entregas parciales, evidencia, garantía y perfil técnico (TD-043).
12. Registrar el Master institucional de Verificación con identidad estructurada
    y ejecutar un E2E autenticado con ETS mixto Calibración + Verificación,
    descarga, sustitución externa y retorno del mismo ZIP (TD-049).
13. Diseñar en etapas finales Auditoría Anual y su integración con Tickets,
    Resoluciones, Activity, Documentos y permisos. Un cierre será inmutable y
    cualquier cambio de ciclo distinguirá RESET DE CONTADORES de BORRADO DE
    DATOS, que queda prohibido (TD-050); el motor actual no depende de ello.

## Validaciones del corte 2026-08-25

- Backend focal ampliado: `144 passed`, `19 subtests passed`; cubrió
  Verificación, Calibración compartida, Captura/Calidad, Equipment,
  Master/fingerprint, autenticación, identidad/snapshots, Servicios Compuestos,
  ETS evolucionado, Venta, Mantenimiento y Reparación.
- Suite propia de Verificación: `14 passed`, incluidos inicial→final,
  idempotencia A→A, bloqueo A→B sin evidencia, candidato B vigente, archivo B,
  revisión posterior de A y ambigüedad sin mutación.
- El caso nuevo de retorno sustituye el Master genérico dentro de un ZIP,
  comprueba asociación al certificado por identidad, resolución única del
  Master específico registrado por fingerprint y congelación automática del
  snapshot final. No se dispuso de un Master institucional productivo ni se
  simuló su aceptación física.
- Frontend relevante con `node --test`: `6 passed` para independencia
  Tipo/Categoría y contrato de Verificación/Captura.
- `npm run build`: correcto; Vite transformó 1746 módulos y conservó el aviso
  no bloqueante del bundle mayor a 500 kB.
- No hubo cambio de esquema, migración ni datos locales; por ello no se
  regeneró `backup_erp_myc_antes_prueba.sql`.

## Documentación de este corte

La auditoría conserva sus diez entregables como fotografía histórica. La Etapa
2A agregó el contrato de recuperación, el cierre técnico, la migración de
reconciliación y scripts reproducibles; migró la base local y regeneró el
respaldo oficial. La Etapa 2B actualizó el Catálogo Institucional, documentó las
brechas contra bootstrap/API y agregó un validador sin cambiar claves ni
comportamiento de autorización. La validación funcional posterior separó ese
snapshot de la autoridad objetivo, retiró 493 campos sintéticos del plano de
capacidades y documentó diferencias, propuestas y reservas. Se sincronizaron
decisiones, observaciones, alcance, estado canónico, índice e inventario
oficial. La revisión semántica posterior reformuló únicamente los nombres
funcionales de los 42 módulos, 181 acciones y 657 microacciones, conservando
identificadores y permisos. La aprobación institucional posterior clasificó
las 657 microacciones, congeló la versión 1.0, estableció versionado estable y
creó su cierre documental; flujo, reglas y deuda se revisaron sin requerir
cambios.
ETAPA 3 agregó el inventario de superficies, tres contratos de archivos y el
cierre técnico. Los sprints posteriores llevaron el esquema a `e7b62b8a9421`.
TD-027 concilió datos bootstrap del Portal. Fase 1 ETS múltiple/evolucionado
elevó primero el esquema a `f4a1c9d2e710`; los sprints LAB, Notifications y
Comunicaciones lo llevaron finalmente a `f7c9d1e3a5b7`. El respaldo oficial
vigente conserva 75,050,260 bytes, coincide con ese head y superó restore
drill, sin versionarse en Git.
La identidad operativa, ETS Venta y ETS Mantenimiento elevaron el head del
código a `d1f3a5c7e9b2`; los ciclos se validaron en PostgreSQL temporal sin
tocar la base compartida ni el respaldo oficial. Ambos verticales quedan
**EN REVISIÓN**.
El ajuste de Verificación sincronizó flujo, alcance, reglas, ADR-078,
observaciones, deuda, estado, arquitectura de identidad, contrato de Captura e
inventario: el Master específico deja de requerir selección manual y se
resuelve al retornar el bonche mediante identidad estructurada y fingerprint.
El P1 del 2026-08-25 acotó esa resolución a equipos con inicial sin final; un
final ya congelado conserva documento/versión históricos, valida contra su
snapshot y bloquea A→B sin depender de evidencia `identified`.
El vertical permanece **EN REVISIÓN** hasta probarlo con el Master institucional
y un E2E autenticado físico/browser.
