> Estado: CIERRE TÉCNICO EN REVISIÓN FÍSICA
>
> Fecha: 2026-09-03
>
> Alcance: cierre operativo + UX de MYC Mobile / OT LAB previo al build

# Cierre operativo y UX OT LAB

## Resultado verificable

- Vinculado autoriza directamente el folio documental con
  `lab_folios.resolve`; sin permiso conserva `requested_folio` y Ticket
  pending. No consume ni genera MYCA/MYCT. La edición autorizada resuelve el
  Ticket previo sin borrar historia.
- Notifications conserva ausencia de self-notification en creación, avisa a
  otro revisor por permiso y notifica al requester al resolver. Expo Push usa
  `sound=default` y `channelId=operational`; la configuración Mobile existente
  del canal no requirió cambio.
- Sólo la FieldSheet current `draft`/`in_progress` es descartable. Primera
  captura restaura `received_signed`; recaptura restaura la completed anterior.
  El hard delete de OT reutiliza esa autoridad sólo para borradores y bloquea
  historia/completed.
- Los 422 FastAPI se traducen a `fieldErrors`; formularios y Resultados
  conservan banner humano, control marcado y limpieza por campo.
- `MycDatePickerField` trabaja con fecha civil `YYYY-MM-DD`; `+6 meses` y
  `+1 año` parten de `calibration_date`, clamping fin de mes/bisiesto. Son
  shortcuts UX experimentales y no una regla metrológica.
- `LabWorkOrder.reception_date` permanece canónica. Staff autorizado sincroniza
  sólo hojas vigentes editables; el Ticket `reception_date_change` es
  informativo y nunca muta la fecha.
- El selector conserva toda la fuente y búsqueda, con scroll interno y viewport
  de cinco filas. `supported_equipment` permanece informativo.
- Captura/cierre usa los primitives canónicos sin convertir launchers reales en
  botones transaccionales. Fase 6A.1 continúa **EN REVISIÓN**.

## Migración

La revisión `9f3a2c7d1e84` parte del head real `b0b560e714db` y sólo reemplaza
`ck_operational_ticket_type` para agregar `reception_date_change` a los siete
tipos anteriores. El downgrade consulta primero si el tipo nuevo tiene filas y
se detiene con error si existen; nunca borra ni reinterpreta datos.

## Validación

- Backend focal: `151 passed, 6 warnings`, 0 failed.
- Backend ampliado LAB/Tickets/Notifications: `327 passed, 8 skipped, 6 warnings`, 0 failed.
- Mobile completo: `330 passed`, 0 failed, duración final `534.482625 ms`.
- TypeScript: `npx tsc --noEmit`, exit 0.
- Expo lint: exit 0, 0 errores y 2 warnings del `useEffect` vigente de
  `FieldSheetResultsWorkspace.tsx`.
- Export iOS: `npx expo export --platform ios`, exit 0; bundle generado con
  1265 módulos y salida `dist`.
- Alembic local: current/head `9f3a2c7d1e84`; constraint consultado con los
  ocho tipos.

Permanece pendiente únicamente el QA físico Android/iPhone previo al build.
