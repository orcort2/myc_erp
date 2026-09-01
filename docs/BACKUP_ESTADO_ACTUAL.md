> Estado: VIGENTE
>
> Tipo: Snapshot operativo verificable
>
> Autoridad: Media; no define alcance, flujo, reglas, decisiones ni estado de módulos
>
> Corte actualizado: 2026-09-01

# Estado operativo actual del ERP MYC

Este archivo conserva únicamente el corte técnico necesario para reanudar el
trabajo. El estado funcional se consulta en
[`project/PROJECT_STATUS.md`](project/PROJECT_STATUS.md), el alcance en
[`project/CURRENT_SCOPE.md`](project/CURRENT_SCOPE.md), el flujo en
[`project/CURRENT_PROCESS_FLOW.md`](project/CURRENT_PROCESS_FLOW.md) y los
pendientes en [`project/OBSERVATIONS_REGISTER.md`](project/OBSERVATIONS_REGISTER.md)
y [`project/TECHNICAL_DEBT.md`](project/TECHNICAL_DEBT.md).

## Corte operativo

- Rama verificada: `wip/lab-field-sheets-integration`.
- Baseline recibido: `22f75e40d14ade3ae19ccf43d2cb74bbae7de502`.
- Dictamen global vigente: **NO APTO PARA PRODUCCIÓN**.
- Único módulo `SELLADO`: Control Documental V1 dentro de su alcance
  congelado. OT LAB temporal permanece `EN DESARROLLO` hasta QA físico.
- Fase 3 LAB implementa recepción técnico+cliente previa a FieldSheets:
  `draft → received_signed → in_progress → ready_to_close → completed`.
  `ready_for_signatures` queda sólo como compatibilidad histórica.

## Persistencia y migraciones

- Persistencia principal: PostgreSQL, SQLAlchemy y Alembic.
- Head único del código verificado: `a3983f9a6ca9`.
- La revisión `a3983f9a6ca9` declara `down_revision = ab31cd42ef53`.
- Fase 3 no agrega migraciones ni modifica datos locales. Reutiliza
  `LabWorkOrder.signature_session_id`,
  `FieldSheet.lab_signature_session_id` y los estados ya incluidos por la
  revisión vigente.
- No se aplicó Alembic ni se ejecutaron cambios sobre la base real del usuario;
  por ello no corresponde regenerar `backup_erp_myc_antes_prueba.sql` en este
  trabajo.

## Estado verificable Fase 3 LAB

- La sesión se crea sólo con firma técnico y cliente válidas. La primera firma
  existe únicamente en memoria Mobile hasta el POST final.
- Recepción valida equipos, servicio, MYCA/MYCT, empresa vinculada y cliente
  documental antes de cambiar la cohorte a `received_signed`.
- La recepción firmada congela datos generales, cliente receptor, equipos,
  cliente documental, servicio, empresa vinculada y folios mediante backend.
- Crear la primera FieldSheet cambia a `in_progress`; completar la última
  requerida cambia a `ready_to_close`; el cierre genera `completed` sin otra
  firma.
- Cada FieldSheet conserva la sesión exacta vigente al crearla. Reapertura
  `preserve`/`invalidate` no reescribe firmas ni hojas históricas.
- Captura usa `lab_field_sheets.capture` para leer y operar FieldSheets, sin
  capacidades administrativas. El scope externo y su excepción histórica de
  cierre se conservan.
- Mobile presenta revisión de recepción, resumen completo, read-only posterior,
  estados nuevos, cierre sin loop de firmas y contexto de encabezado correcto.

## Validaciones

- Backend Fase 3: `46 passed`.
- Backend LAB focal adicional: `132 passed, 8 skipped`.
- Backend seguridad/permisos focal: `45 passed`.
- Backend completo: `811 passed, 8 skipped, 19 subtests passed, 2 failed`.
  Las dos fallas son deuda preexistente del inventario API: runtime 499 frente
  al snapshot/test fijado en 477; no corresponden a Fase 3.
- Mobile focal: `42 passed`.
- Mobile completo: `157 passed`.
- TypeScript `npx tsc --noEmit`: correcto.
- Lint `npm run lint`: correcto.
- `lab-work-order-closure.test.ts`: correcto.
- `python -m alembic heads`: `a3983f9a6ca9 (head)`.

## Pendientes operativos

- QA físico Android/iPhone/TestFlight del recorrido completo de recepción,
  doble firma, orientación/teclado/scroll, FieldSheets, cierre, PDF,
  refresh/realtime y errores.
- Resolver por un trabajo separado la deuda del inventario API 477/499.
- Mantener fuera de esta fase los hallazgos separados de FieldSheets
  (contenido, tabla Valve, overflow, columnas, imprimibles y plantillas),
  NIIMBOT, cambios MYCA/MYCT/rangos, LabClient y Fase 2 sin regresión.

## Regla de mantenimiento

Después de cualquier cambio funcional, esquema, configuración, prueba o
recurso, este snapshot y `PROJECT_FILE_REGISTRY.md` deben sincronizarse en el
mismo trabajo. Si una futura tarea modifica la base local, debe regenerar el
respaldo oficial y comprobar su `alembic_version` contra el head único.
