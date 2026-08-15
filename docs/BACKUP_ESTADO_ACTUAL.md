> Estado: VIGENTE
>
> Tipo: Vigente (estado operativo verificable)
>
> Autoridad: Media; no sustituye los documentos canónicos de `project/`
>
> Corte actualizado: 2026-08-14

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
- El acceso móvil técnico backend está **TERMINADO — EN REVISIÓN**: ocho
  lecturas aplican asignación ETS, ownership heredado, 404 opaco y doble
  permiso para Hojas de Campo, sin modificar el ERP web ni `myc-mobile`.
- OT LAB móvil está **EN DESARROLLO** con implementación técnica completa:
  agregado aislado, folios 6400–6999, grupos raíz/adicional, máximo 10 equipos,
  una sesión de firma compartida, bloqueo posterior, PDF individual y
  exportación ZIP. Desde el corte 2026-08-14 agrega filtros SQL separados por
  folio/cliente, estado y paginación; Tickets, revisión autorizada, snapshots,
  PDFs por revisión, firma histórica/activa, invalidación automática y control
  optimista. La resolución de Tickets conserva `FOR UPDATE` exclusivamente
  sobre la fila del ticket y rechaza con 409 cualquier segunda decisión; la
  regresión real PostgreSQL cubre ambas políticas de firma, rechazo y carrera
  con un único ganador. La captura y el detalle de Tickets ya respetan safe
  area, agrupan los campos y ocultan
  teléfono/correo; el PDF separa Domicilio, C.P., Ciudad, Estado y orden de
  compra sin `0` por ausencia. Falta aceptación física en iPhone/Expo Go.
- Notifications V1 está **TERMINADO TÉCNICAMENTE — EN REVISIÓN FÍSICA**:
  reutiliza `Notification`, registra `PushDevice`, persiste cinco eventos de
  Tickets con destinatarios por permiso/solicitante, entrega Expo posterior al
  commit y agrega centro, badge, deep links y refresco automático sin polling.
  No hubo build EAS, despliegue ni migración de base compartida.
- El P0 **Integridad de autenticación de Certificados** está **TERMINADO — EN
  REVISIÓN**: Calidad es la única superficie mutante, ETS perdió endpoint/lote
  y acciones, y `certificate_authentication.authenticate_certificate` conserva
  lock, actor, origen, audit, evento y commit únicos.
- La conciliación **TD-027** deja el capability gate **VERDE** en 25/0 y el
  bootstrap cubre 78/78 permisos HTTP. Las diferencias móviles nuevas incluyen
  `lab_work_orders.use/export` y `tickets.create/view_own/review`,
  explícitamente temporales. Portal usa
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
- Head aplicado a la base local compartida: `c6e8a1b4d2f9`.
- Head del código: `e6b8c0d2f4a6`.
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

- `backup_erp_myc_antes_prueba.sql` no está presente actualmente ni en la raíz
  ni en `backend/`; los metadatos históricos de tamaño/hash dejan de describir
  un artefacto verificable local.
- Este sprint no modificó la base compartida (`c6e8a1b4d2f9`), por lo que no
  regeneró un dump. Antes de aplicar `e6b8c0d2f4a6` a esa base debe generarse el
  respaldo oficial y, después del upgrade, confirmar que `alembic_version`
  coincida con el head.
- El procedimiento vigente permanece en
  `architecture/database/SCHEMA_RECOVERY.md`.

## Validaciones ejecutadas

| Validación | Resultado |
| --- | --- |
| Backend canónico | 518 passed, 5 skipped, 19 subtests passed, 3 warnings deprecados |
| Aislamiento móvil técnico | 21 passed; ETS/OT/Equipo/Hoja A/B, sin asignación, 401, 403 y doble permiso de hojas |
| Escenarios Fase 1 ETS múltiple/evolucionado | 10 passed; A–H, permisos, mixto SG/calibración/mantenimiento, evolución indebida/posterior, lifecycle, categorías y unicidad |
| Regresión focal ETS/calibración/Activity/cotizaciones/permisos | 53 passed, 2 warnings |
| Autenticación real y autoridad canónica | 12 passed; LibreOffice real, adapter HTTP, lock, actor, audit/evento y doble autenticación |
| Pruebas dirigidas Integridad ETS y módulos relacionados | 67 passed, 7 subtests; actor obligatorio, mismo Administrador en tres etapas, audit/eventos, no mutación en requested/authorized, ejecución autorizada, revalidación y router sin reglas |
| Pruebas dirigidas ETAPA 3 | 78 passed, 7 subtests |
| Pruebas dirigidas de integridad de esquema | 3 passed, 1 warning deprecado de configuración Alembic |
| Pruebas dirigidas de seguridad | 22 passed |
| Frontend `node --test` | 42 passed |
| Frontend `npm run build` | correcto; warning de chunk >500 kB |
| Backend `compileall` | correcto |
| Inventario FastAPI | 392/392 operaciones clasificadas; CSV regenerado canónicamente y coincide con runtime |
| OT LAB backend/API/PDF/export/Tickets | 12 passed, 5 skipped sin URL PostgreSQL; cubre filtros, permisos, lifecycle, control optimista, firma preservada/invalidada, nueva firma y PDF histórico |
| Tickets sobre PostgreSQL real | 4 passed en dos bases temporales eliminadas al finalizar: approve preserve, approve invalidate, rechazo definitivo y carrera approve/reject con un único 200 y un 409 |
| Notifications/Tickets/OT focal | 23 passed, 5 skipped; devices idempotentes/multiusuario, ownership, lectura/paginación, eventos create/approve/reject/resolve/signature-required, Expo mock y resiliencia |
| Notifications backend específica | 4 passed; incluye éxito, `DeviceNotRegistered`, proveedor caído y persistencia del dominio/notificación |
| Migración LAB PostgreSQL temporal | `base → c6e8a1b4d2f9`; current correcto; `alembic check` sin operaciones nuevas; asignador concurrente `[6400, 6401]`; carrera de OT adicional: una `6403` y un rechazo `409`; base temporal eliminada |
| `myc-mobile` TypeScript/lint | correcto / correcto con centro, badge, deep links y refresco automático |
| `myc-mobile` política de refresco | 4 passed; eventos, foreground, deduplicación y throttle/mutación local |
| `myc-mobile` Expo Doctor SDK 54 | 18/18 checks |
| Aislamiento portal A/B | membresía propia 200, recurso ajeno 404, anónimo 401; autenticador interno rechaza token del portal |
| `scripts/myc doctor` | dependencias locales principales disponibles |
| Alembic ciclo vacío base→head→base→head | correcto en PostgreSQL aislado |
| Migración correctiva Fase 1 reversible | base aislada `base → a7c2e5f8b1d4 → f4a1c9d2e710 → a7c2e5f8b1d4`; current ETS correcto |
| Alembic upgrade desde respaldo histórico | correcto; b03→f27, 102 tablas |
| Alembic current/check | base principal no modificada en `c6e8a1b4d2f9`; head de código `e6b8c0d2f4a6` validado limpio en base aislada |
| Respaldo oficial regenerado | 74,306,112 bytes; contiene `f4a1c9d2e710`; restore drill no repetido en esta fase |
| Validador Catálogo Institucional/permissions/API | VERDE: 78 permisos HTTP, baseline gobernado 25 brechas literales y 0 de bootstrap; cinco diferencias HTTP pertenecen al vertical móvil temporal LAB/Tickets |
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
- La acreditación de calibración mantiene las claves canónicas del contrato.
- Facturación dispone de borrador, snapshots, intentos PAC, XML/PDF, pagos y cartera, pero Facturama está configurado para Sandbox y faltan cancelación/sustitución, PPD/complemento y nota fiscal de egreso.
- Actividad implementa threads, mensajes, menciones, adjuntos, atención y no
  leídos; sus defaults de BD quedaron alineados y permanece pendiente la
  operación externa/observable.
- El Motor de Resoluciones tiene núcleo versionado, lifecycle, seguridad, idempotencia, locks, compensación, auditoría, outbox, cola/worker, API y SDK. Sólo dos definiciones están instaladas; la Fase 14 sigue pendiente de dictamen formal y el inicio desde módulos de origen no está cerrado.

## Seguridad y operación

- Inventario introspectado: 392 operaciones HTTP, todas clasificadas por el
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
elevó el head a `f4a1c9d2e710` y regeneró el respaldo oficial:
`backup_erp_myc_antes_prueba.sql` conserva 74,306,112 bytes y ese head, sin
versionarse en Git.
