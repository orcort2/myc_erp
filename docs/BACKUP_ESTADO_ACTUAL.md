> Estado: VIGENTE
>
> Tipo: Snapshot operativo verificable
>
> Autoridad: Media; no define alcance, flujo, reglas, decisiones ni estado de módulos
>
> Corte actualizado: 2026-08-27

# Estado operativo actual del ERP MYC

Este archivo conserva únicamente el corte técnico necesario para reanudar el
trabajo. El estado funcional se consulta en
[`project/PROJECT_STATUS.md`](project/PROJECT_STATUS.md), el alcance en
[`project/CURRENT_SCOPE.md`](project/CURRENT_SCOPE.md), el flujo en
[`project/CURRENT_PROCESS_FLOW.md`](project/CURRENT_PROCESS_FLOW.md) y los
pendientes en [`project/OBSERVATIONS_REGISTER.md`](project/OBSERVATIONS_REGISTER.md)
y [`project/TECHNICAL_DEBT.md`](project/TECHNICAL_DEBT.md).

## Corte operativo

- Versión frontend declarada: `0.4.0`.
- Dictamen vigente: **NO APTO PARA PRODUCCIÓN**.
- Único módulo `SELLADO`: Control Documental V1, dentro de su alcance
  congelado. La clasificación completa pertenece a `PROJECT_STATUS.md`.
- Los contratos transversales obligatorios del Workbench de Facturación,
  acreditación de Calibración y Servicios Compuestos permanecen definidos en
  `docs/architecture/`; este snapshot no los reproduce.
- El Motor de Resoluciones llega a Fase 15 implementada y en revisión. La fase
  agrega Herramientas administrativas ETS sin otro motor ni migración. Su entrada
  normativa es
  [`architecture/resolution-engine/README.MD`](architecture/resolution-engine/README.MD).
- MYC Mobile continúa como LAB temporal aislado del flujo productivo y ahora
  admite staff/cliente mediante `MobileSecurityContext`, conforme a
  [`architecture/MOBILE_SECURITY_CONTEXT.md`](architecture/MOBILE_SECURITY_CONTEXT.md).

## Persistencia y migraciones

- Persistencia principal: PostgreSQL, SQLAlchemy y Alembic.
- Head único vigente: `e7a3c5d9f1b2`
  (`lab_anticipated_work_order_groups`).
- PostgreSQL local quedó en `e7a3c5d9f1b2 (head)` y `alembic check` no detectó
  operaciones nuevas. La columna
  `lab_work_order_group_requests.root_work_order_id` admite `NULL` y conserva
  una FK `ON DELETE RESTRICT` hacia `lab_work_orders.id`.
- La evolución de cohortes LAB no modifica esquema ni datos locales; reutiliza
  `signature_session_id` y la versión por raíz, por lo que no requiere migración
  adicional ni regeneración del respaldo SQL.

## Respaldo oficial

- `backup_erp_myc_antes_prueba.sql` existe, mide `75,546,835` bytes y fue
  regenerado el 2026-08-26 13:45:14 CST.
- SHA-256:
  `f2225f704e0ce906173f9b8f7868c7dc7cb3d6248bb46760f9bcf1e0a746a3a7`.
- Su `alembic_version` verificable es `e7a3c5d9f1b2` y coincide con el head
  único actual del código.

## Validaciones de este corte documental

- Inventario inicial: 165 archivos Markdown versionados, contando `.md` y
  `.MD` sin distinguir mayúsculas.
- Se revisaron rutas, referencias Markdown, duplicados exactos, similitud de
  contenido, jerarquía del índice y responsabilidades del canon.
- Se eliminó la bitácora manual `BACKUP_ESTADO_ACTUAL (1).md`: era un respaldo
  cronológico de 6,669 líneas en una ruta excluida del inventario y no era
  fuente vigente. La trazabilidad permanece en Git, auditorías y cierres.
- Se eliminó `CATALOGO_PERMISOS_ERP_MYC_2026-08-04.md`: era una extracción
  estática de un ZIP anterior, sin autoridad ni referencias activas; la fuente
  vigente es el código y la gobernanza institucional se conserva en los
  contratos de capacidades y seguridad.
- Este archivo se redujo de 440 líneas a un snapshot operativo sin repetir el
  estado, alcance, flujo, reglas ni deuda del canon.
- Fase 15 modificó backend/frontend del Centro, permisos, continuidad ETS,
  pruebas, inventario HTTP y documentación. No modificó Mobile, modelos,
  migraciones, esquema, base local ni el respaldo SQL.
- El inventario HTTP se regeneró contra el runtime actual: 477 operaciones
  clasificadas deny-by-default y CSV sincronizado.

## Pendientes operativos

### Corte funcional 2026-08-27 — Cohortes de cierre OT LAB

- `root_work_order_id` conserva parentesco histórico; una
  `LabWorkOrderSignatureSession` identifica exclusivamente la cohorte cerrada.
- Backend admite firma/finalización grupal de las OT abiertas o individual de
  la seleccionada, con doble firma, PDF propio, auditoría explícita y versión
  serializada por lock de raíz. Las completadas quedan congeladas.
- Reapertura por Ticket sigue la sesión y no desbloquea hermanas de otra
  cohorte. Mobile ofrece ambas modalidades y conserva navegación/PDF por folio.
- La regresión de seguridad obsoleta quedó alineada con el contrato vigente:
  Técnico internal crea grupo directo, no usa `group-requests` ni recibe
  capacidades administrativas; Operativo Sr externo solicita pero no crea
  directo. Seguridad Mobile aprobó 21/21 y LAB 30 aprobadas/7 PostgreSQL
  omitidas por entorno. Suite backend completa: 661 aprobadas, 7 omitidas y 19
  subtests, sin fallas. Mobile conserva 85 pruebas, lint, TypeScript y export
  Expo iOS/Android/Web correctos.
- `compileall`, inventario API de 477 operaciones, registro de archivos,
  `alembic heads`, `alembic check` y `git diff --check` quedaron correctos.
- No hubo migración, cambio de datos, commit, push ni despliegue. Permanecen
  pendientes el QA físico Android/iPhone y la concurrencia PostgreSQL opt-in.

### Corte funcional 2026-08-26 — Seguridad MYC Mobile

- Login/refresh Mobile distingue staff y cliente; `mobile.access` es gate de
  sesión y cada operación conserva permiso explícito.
- Viewer/Operativo Jr/Operativo Sr se persisten en RBAC externo. Membership
  activa única se valida en backend y se refuerza con índice parcial.
- OT LAB, equipos, firmas, PDFs, revisiones y Tickets aplican scope de cliente;
  rutas productivas Mobile permanecen exclusivamente internas.
- Realtime exige permiso, participación y mismo cliente; dispositivos/push y
  centro de notificaciones conservan ownership por usuario.
- Validación hasta este corte: 69 tests backend focalizados, 26 de regresión
  adicional, 73 tests Mobile, 9 tests frontend de administración,
  lint/TypeScript Mobile, export Expo iOS/Android/Web, build Vite, migración
  local y SQL Alembic offline correctos. LAB obtuvo 21 passed/5 skipped y una
  falla preexistente reproducida también desde `HEAD`. Falta QA físico; no hubo
  commit, push ni despliegue.

### Corte funcional 2026-08-25 — QA Verificación

- La aceptación de Cotización y la materialización del ETS son transaccionales
  e idempotentes en backend; el frontend retiró la creación manual.
- Verificación exige Master genérico válido en conceptos nuevos/actualizados y
  bloquea antes del ETS los snapshots legacy incompletos, sin alterar su lectura.
- El ETS identifica categorías, separa métricas de Calibración/Verificación,
  oculta la desambiguación de partida cuando sólo existe una opción y conserva
  `Equipment.service_order_item_id`.
- Validación ejecutada: 75 pruebas backend y 12 subtests, 55 pruebas frontend y
  build Vite correctos. El cambio permanece **EN REVISIÓN**; no hubo migración
  ni modificación de la base local o del respaldo SQL.

### Corte funcional 2026-08-25 — Herramientas administrativas ETS

- La familia `administrative_tools` instala restauración, reconstrucción y baja
  como definiciones versionadas distintas sobre el Motor/worker existente.
- La baja ordinaria quedó cerrada; la creación automática no sustituye un ETS
  inactivo y dirige al Centro. Baja/restauración sólo operan sobre ETS prístino;
  reconstrucción sólo procede cuando no existe ningún ETS previo.
- El Centro presenta las vistas Pendientes, En revisión, Requieren autorización,
  Ejecutadas, Fallidas y Herramientas. La pantalla ETS enlaza al precheck con su
  ID contextual.
- Validación focal/regresión ejecutada: 167 pruebas backend, 7 subtests backend
  y 57 pruebas frontend correctas; conformidad de seguridad sincronizada a 463
  rutas, build Vite y compilación Python correctos. `git diff --check` se
  ejecuta después de la sincronización final del inventario.
- Estado: **IMPLEMENTADA — EN REVISIÓN**. Sin commit ni push.

1. Completar los bloqueadores de producción registrados en
   `TECHNICAL_DEBT.md`, especialmente sesiones/RBAC, CFDI productivo,
   E2E físico/browser, CI/CD, observabilidad y almacenamiento durable.
2. Mantener las validaciones físicas pendientes de Mobile, Comunicaciones,
   ETS Venta, Mantenimiento y Verificación según sus TD vigentes.

## Regla de mantenimiento

Actualizar este archivo sólo cuando cambien migraciones, respaldo, validaciones
o pendientes operativos del corte. No copiar aquí contratos completos ni
declarar estados de módulos: esas responsabilidades pertenecen a los documentos
canónicos enlazados al inicio.

## Corte 2026-08-26 — Grupos anticipados OT LAB

- Alembic local: `e7a3c5d9f1b2 (head)`; renombra ownership LAB a `operator_client_id` y crea solicitudes estructuradas.
- Validado: materialización N, aprobación idempotente, aislamiento Mobile, capability Sr y builds.
- Pendiente: QA físico y concurrencia PostgreSQL opt-in.

Corrección quirúrgica de revisión: capabilities separadas por actor, endpoints Mobile internal, conversación creada sólo en claim, bandeja/contador Mobile agregado, modal/deep links reparados y páginas Web ajenas restauradas. La suite backend completa obtuvo 655 aprobadas, 6 omitidas y 19 subtests; conserva una falla preexistente de edición posterior a firma fuera del alcance del Bloque 2. Las regresiones focales quedaron verdes (21 de seguridad y 43 LAB/Communications/Notifications/Realtime, con 6 omisiones PostgreSQL), Web aprobó 2 pruebas y Mobile 80. Vite transformó 1,747 módulos; typecheck explícito, Expo lint y export iOS/Android/Web fueron correctos. El inventario clasifica 475 rutas. No se modificó la base ni se creó migración adicional sobre `e7a3c5d9f1b2`; el respaldo oficial permanece vigente.

## Corte 2026-08-26 — Borrado de grupos anticipados OT LAB

- `delete_work_order()` bloquea y reconcilia la solicitud aprobada dentro de la
  misma transacción: nueva raíz cuando hay hermanas o `NULL` al borrar la última.
- Solicitud, estado `approved`, handler, timestamps y conversación sobreviven;
  el secuenciador LAB no cambia y los folios eliminados no se reutilizan.
- La FK física causante era
  `lab_work_order_group_requests_root_work_order_id_fkey` (`ON DELETE RESTRICT`);
  la columna ya admite `NULL`, por lo que no se creó migración.
- Validación: borrados focales `9 passed`; regresión LAB/Notifications/
  Communications/Realtime `45 passed, 6 skipped, 1 deselected`; compilación
  Python correcta; Alembic local/head `e7a3c5d9f1b2` y `alembic check` limpio.
  La expectativa antigua de edición crítica posterior a firma fue corregida
  posteriormente para exigir el bloqueo 409 vigente; la suite global actual
  está verde.
- Pendiente: TD-057 registra que la proyección visual queda sin folios cuando ya
  no existen OTs, aunque auditoría y conversación conservan la evidencia.
