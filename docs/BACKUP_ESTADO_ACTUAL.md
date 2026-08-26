> Estado: VIGENTE
>
> Tipo: Snapshot operativo verificable
>
> Autoridad: Media; no define alcance, flujo, reglas, decisiones ni estado de módulos
>
> Corte actualizado: 2026-08-25

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
- MYC Mobile continúa como LAB temporal aislado del flujo productivo, conforme
  a [`../myc-mobile/AGENTS.md`](../myc-mobile/AGENTS.md).

## Persistencia y migraciones

- Persistencia principal: PostgreSQL, SQLAlchemy y Alembic.
- Head único derivado de las 107 revisiones versionadas:
  `c4e0ead1af28` (`fix_repair_timestamp_defaults`).
- La consulta de `alembic current` contra la base local no respondió dentro de
  30 segundos durante esta auditoría documental; por tanto, no se afirma un
  head local sin evidencia.
- Este cambio no modificó modelos, migraciones, esquema ni datos.

## Respaldo oficial

- `backup_erp_myc_antes_prueba.sql` existe, mide `75,050,260` bytes y fue
  modificado por última vez el 2026-08-17 18:53:35 CST.
- SHA-256:
  `f2280b0e003f582601462b269f3b3fb1165e58d00acf247d8c8564f691b81b14`.
- Su `alembic_version` verificable es `f7c9d1e3a5b7`; no coincide con el head
  actual del código `c4e0ead1af28`.
- La discrepancia queda pendiente: se debe actualizar primero la base local de
  forma controlada y regenerar el respaldo conforme a
  [`architecture/database/SCHEMA_RECOVERY.md`](architecture/database/SCHEMA_RECOVERY.md).
  Esta auditoría no alteró la base y por ello no regeneró el dump.

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
- El inventario HTTP se regeneró contra el runtime actual: 456 operaciones
  clasificadas deny-by-default y CSV sincronizado.

## Pendientes operativos

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
  y 57 pruebas frontend correctas; conformidad de seguridad sincronizada a 456
  rutas, build Vite y compilación Python correctos. `git diff --check` se
  ejecuta después de la sincronización final del inventario.
- Estado: **IMPLEMENTADA — EN REVISIÓN**. Sin commit ni push.

1. Resolver la divergencia entre el head del código y el respaldo oficial
   registrada como TD-051.
2. Completar los bloqueadores de producción registrados en
   `TECHNICAL_DEBT.md`, especialmente sesiones/RBAC, CFDI productivo,
   E2E físico/browser, CI/CD, observabilidad y almacenamiento durable.
3. Mantener las validaciones físicas pendientes de Mobile, Comunicaciones,
   ETS Venta, Mantenimiento y Verificación según sus TD vigentes.

## Regla de mantenimiento

Actualizar este archivo sólo cuando cambien migraciones, respaldo, validaciones
o pendientes operativos del corte. No copiar aquí contratos completos ni
declarar estados de módulos: esas responsabilidades pertenecen a los documentos
canónicos enlazados al inicio.
