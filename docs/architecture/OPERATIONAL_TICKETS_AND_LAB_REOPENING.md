> Estado: VIGENTE
>
> Corte verificado: 2026-09-05
>
> Alcance: Tickets operativos y reapertura documental controlada de OT LAB

# Tickets operativos y reapertura controlada de OT LAB

## Flujo canónico

```text
OT completed
  → técnico crea REOPEN_WORK_ORDER
  → ticket pending; la OT permanece cerrada
  → revisor rechaza, o aprueba con preserve/invalidate
  → snapshot inmutable de cada OT de la cohorte de firma y PDF anterior
  → cohorte in_progress (preserve) o draft (invalidate), revisión N+1, ticket in_progress
  → edición con edit_version
  → cambio crítico invalida automáticamente la firma activa
  → nueva recepción técnico+cliente si la sesión fue invalidada
  → captura técnica vuelve a satisfacer FieldSheets cuando aplique
  → cierre genera PDF nuevo y resuelve el ticket
```

`OperationalTicket` es la entidad extensible. El constraint vigente acepta
`reopen_work_order`, `manual_myc_folio`, `linked_folio`, `partial_close`,
`certificate_folio_block`, `field_sheet_template_request`,
`field_sheet_reopen`, `reception_date_change` y `partial_delivery`; sus
estados canónicos son `pending`, `approved`, `rejected`, `in_progress`,
`resolved` y `cancelled`. La aprobación de `reopen_work_order` ejecuta la
reapertura en la misma transacción y deja el ticket directamente
`in_progress`.

`partial_delivery` es el primer tipo que usa realmente `approved` como
aprobación diferida: `approve_partial_delivery_ticket` (mismo permiso
`tickets.review` que aprueba/rechaza cualquier otro ticket, sin autoaprobación)
sólo autoriza el set de `equipment_ids` solicitado — nunca entrega nada. La
ejecución posterior (`POST .../delivery/partial/{ticket_id}`, ver
`LAB_WORK_ORDERS.md`) deja el ticket `resolved` y no es reutilizable; el set
ejecutado debe coincidir exactamente con el aprobado. Ver
`create_partial_delivery_ticket`/`approve_partial_delivery_ticket` en
`app/services/operational_tickets.py`.

## Solicitud informativa de fecha de recepción

`reception_date_change` guarda OT, equipo/hoja opcionales, solicitante, motivo,
descripción y `requested_date`/`current_date`/`field_sheet_id` dentro de
`resolution_snapshot`. Crear o resolver el Ticket no modifica
`LabWorkOrder.reception_date` ni una FieldSheet. Los destinatarios de creación
son usuarios internos con `work_orders.create` o `lab_work_orders.use`, excepto
el solicitante; resolver exige la misma autoridad y notifica al solicitante que
la solicitud fue atendida, sin afirmar que la fecha cambió.

## Reapertura sin hueco operativo (2026-09-05, corregido 2026-09-06)

Retirar la revisión `completed` vigente de una FieldSheet -- EXCLUSIVAMENTE
por el Ticket `field_sheet_reopen` o el endpoint directo "Desbloquear hoja"
(`lab_field_sheets.reopen`), nunca por reabrir la OT completa -- ya NO deja
al equipo sin revisión vigente cuando la retirada no viene acompañada de un
cambio de campo crítico del equipo: en la misma transacción se abre una
revisión N+1 clonada y editable con `status="reopened"`
(`_clone_field_sheet_for_correction`, `app/services/lab_field_sheets.py`),
lista para que el técnico corrija un dato ya capturado (observación,
resultado, evidencia) sin volver a capturar desde cero. `"reopened"` está en
`EDITABLE_STATUSES` (acepta PATCH/complete, nunca cuenta como completed,
bloquea el cierre hasta volver a completed) y es exclusivo del vertical LAB
-- el flujo productivo nunca lo produce. El histórico N permanece
exactamente intacto (`status`/`final_pdf_path`/`final_pdf_sha256` sin
tocar); sólo se clonan campos técnicos editables. Nunca se clona la fila
`FieldSheetSignature` de N (id, `signature_data`, `signed_at` -- evidencia
documental, nunca duplicada como si fuera nueva de N+1) ni la bitácora de
incertidumbre; el atributo `name` de cada slot nuevo de N+1 sí hereda el
texto plano ya clonado como campo técnico genérico
(`calibrated_by`/`reviewed_by`/`report_made_by`), porque para el vertical
LAB ese campo es texto corregible (quién calibró/revisó), no evidencia
firmada -- en LAB estas 3 filas nacen y permanecen siempre sin
`signature_data`/`signed_at` (Mobile no las escribe ni las lee: "Calibró" se
resuelve de la sesión de firma de recepción de la OT, no de esta tabla). Ver
`LAB_WORK_ORDERS.md` ("Estados, Hojas de Campo y reapertura") para el
contrato completo, incluida la acción explícita "Cambiar Hoja de Campo" para
cuando el técnico sí quiere otra plantilla.

## Auditoría de semántica de reapertura (2026-09)

**OT (cohorte completa).** `_reopen_closed_cohort` (núcleo compartido por la
aprobación del ticket `reopen_work_order` y `reopen_work_order_directly`, la
reapertura directa sin ticket) ya NO regresa la OT a `"draft"` para ambas
políticas -- reabrir una OT no es volver a recepción:

- `preserve`: la firma sigue vigente (`signature_session_id` conservado,
  `signature_required=false`) -- el status de dominio correcto es
  `"in_progress"`, el mismo que ya representa "recepción firmada, trabajo
  técnico en curso". Esto reutiliza sin duplicar la máquina de estados
  existente: `_complete_lab_field_sheet_uncommitted` ya sincroniza
  `in_progress → ready_to_close` cuando se completa la última FieldSheet
  pendiente, exactamente igual que en el primer cierre.
- `invalidate`: la firma se invalida (`signature_session_id=None`,
  `signature_required=true`) -- ahí sí hace falta repetir recepción/firma,
  así que `"draft"` (pre-firma) sigue siendo correcto, sin cambios.

Este era el bug de producción de la OT 6443: Mobile interpretaba
`"draft"` siempre como "falta recepción" y volvía a mostrar esa pantalla,
aunque la OT reabierta con `preserve` conservara sus 5 FieldSheets
`completed` intactas en BD. Con `preserve → "in_progress"`, Mobile ya usa el
mismo mapeo de status que la captura técnica normal
(`inferStepForStatus`), sin necesitar lógica de reopen especial ahí. La
edición general de datos/equipo tras un reopen preserve (agregar equipo,
corregir `client_name`) sigue funcionando: `_ensure_members_editable` acepta
`in_progress` cuando `reopened_at` no es `None` (señal agnóstica de ticket
vs. directa -- `reopen_ticket_id` es `None` en una reapertura directa), sin
exigir además `signature_preserved` (un cambio estructural puede invalidar
la firma a mitad de la corrección sin cerrar la ventana de edición).
`_closable_status` tiene el carve-out equivalente para cerrar directamente
una corrección puramente general que nunca tocó ninguna FieldSheet.

**FieldSheet individual ("Desbloquear hoja" vs. "Solicitar desbloqueo").**
Desbloquear una FieldSheet `completed` mientras la OT sigue abierta ahora
tiene DOS caminos que comparten el mismo núcleo de dominio
(`_reopen_field_sheet_uncommitted`, `app/services/lab_field_sheets.py`) para
no duplicar la regla:

- **Directo** (`POST /{work_order_id}/equipment/{equipment_id}/field-sheet/reopen`,
  `reopen_lab_field_sheet_directly`): exige el permiso `lab_field_sheets.reopen`
  (autoridad administrativa directa, hoy Administrador/Desarrollador --
  deliberadamente distinta de `lab_folios.resolve` y de `tickets.review`).
  Ejecuta en una sola llamada, sin crear ni autoaprobar ningún Ticket; motivo
  obligatorio, auditado como `lab_field_sheet.reopened_directly`.
- **Mediado por ticket** (`field_sheet_reopen`, sin cambios de flujo):
  `resolve_operational_ticket` exige el MISMO permiso `lab_field_sheets.reopen`
  para resolverlo (ya no `lab_folios.resolve`) -- un usuario sin esa
  autoridad directa pero con `tickets.create` puede seguir solicitando vía
  ticket; la hoja permanece `completed`/bloqueada hasta la aprobación.

Ambos caminos exigen que la OT dueña siga abierta
(`received_signed`/`in_progress`/`ready_to_close`) -- una OT ya
`completed`/`partially_closed` no admite desbloquear una hoja suelta, primero
hay que reabrir la OT completa (misma frontera que ya exigía
`create_field_sheet_reopen_ticket`). Un segundo intento de desbloqueo sobre
el mismo equipo es idempotente por construcción: en cuanto la revisión
vigente deja de ser `completed` (ya es `"reopened"`), el guard
`current.status != "completed"` rechaza el reintento con 409 sin crear una
revisión N+2.

## Inmutabilidad y revisiones

Antes de reabrir, cada integrante de la cohorte que comparte la
`signature_session_id` genera un
`LabWorkOrderRevision` con snapshot de datos/equipos, sesión de firma, PDF,
checksum y número de revisión. El registro activo incrementa
`revision_number`, limpia únicamente su PDF corriente y conserva el folio.
Los PDFs históricos se descargan por revisión y nunca se sobrescriben.

Las firmas históricas tampoco se borran. Las FieldSheets históricas conservan
el `lab_signature_session_id` exacto con el que nacieron y nunca se reescriben
hacia una sesión posterior. Una sesión individual reabre sólo su
OT; una sesión compartida reabre sólo sus integrantes. Las hermanas de otra
cohorte bajo la misma raíz no reciben snapshot, revisión ni desbloqueo. La
versión continúa siendo única por `(root_work_order_id, version)`.

## Clasificación determinista de cambios

Pueden preservar firma: contacto, teléfono, correo, código postal, ciudad,
estado, orden de compra, observaciones y `report_number` de equipo.

Invalidan automáticamente la firma activa de los miembros abiertos afectados:
cliente, fechas,
domicilio, agregar/eliminar OT o equipo, instrumento, marca, identificación,
serie y condición física. La autorización `preserve` no puede evitar esta
regla backend. La autorización `invalidate` exige nuevas firmas desde el
inicio.

Toda edición de una revisión reabierta debe enviar `expected_edit_version`.
Una versión ausente u obsoleta responde `409 REVISION_CONFLICT`.

## Permisos

- `tickets.create`: crear solicitudes.
- `tickets.view_own`: consultar solicitudes propias.
- `tickets.view_all`: ampliar la bandeja a todas las solicitudes.
- `tickets.review`: aprobar o rechazar.
- `work_orders.reopen`: capacidad funcional de reapertura.
- `work_orders.reopen_preserve_signatures`: aprobar preservación condicionada.
- `work_orders.reopen_invalidate_signatures`: exigir firma nueva.
- `lab_field_sheets.reopen`: desbloquear directamente una FieldSheet
  `completed` ("Desbloquear hoja") o resolver un ticket `field_sheet_reopen`
  -- hoy sólo Administrador (comodín) y Desarrollador.

El Técnico recibe creación y consulta propia. Calidad recibe consulta global,
revisión y ambas políticas de reapertura de OT (no `lab_field_sheets.reopen`,
que es autoridad de mutación documental, no de triage). Desarrollador recibe
el conjunto explícito; Administrador conserva su comodín. El frontend sólo
oculta acciones; cada decisión sensible vuelve a validarse en el backend.

## API móvil

Base: `/api/mobile/v1/technician`.

- `POST /tickets`
- `GET /tickets?status=&search=&offset=&limit=`
- `GET /tickets/{id}`
- `POST /tickets/{id}/approve`
- `POST /tickets/{id}/reject`
- `POST /tickets/reception-date-change`
- `POST /tickets/partial-delivery`
- `POST /tickets/{id}/approve-partial-delivery`
- `POST /tickets/{id}/resolve`
- `GET /lab-work-orders/{id}/revisions`
- `GET /lab-work-orders/{id}/revisions/{revision}/pdf`

Además del Ticket, existen dos endpoints de reapertura DIRECTA (misma
autoridad, mismo núcleo de dominio que el ticket correspondiente, nunca una
segunda política) documentados en `LAB_WORK_ORDERS.md`:
`POST /lab-work-orders/{id}/reopen` (OT completa, `work_orders.reopen` +
política) y `POST /lab-work-orders/{id}/equipment/{equipment_id}/field-sheet/reopen`
(una FieldSheet, `lab_field_sheets.reopen`). Ninguno crea ni autoaprueba un
Ticket artificial.

## Búsqueda y paginación

`GET /lab-work-orders` admite `folio`, `client`, `status`, `offset` y `limit`.
Folio usa coincidencia parcial textual, cliente usa `ILIKE`, ambos filtros se
combinan con AND y se ejecutan en SQL. La respuesta continúa siendo una lista
para no romper la build TestFlight vigente; el móvil pagina con bloques de 25
y acción “Cargar más”. Los dos inputs tienen debounce de 400 ms y limpieza
independiente o conjunta.

## Auditoría y concurrencia

Se auditan creación, rechazo, aprobación/reapertura de la cohorte, campos modificados,
invalidación automática, firma, cierre y actores. La resolución adquiere un
`FOR UPDATE` exclusivamente sobre la fila de `operational_tickets`; las
relaciones eager-loaded se consultan después dentro de la misma transacción y
no forman parte del lock. Sólo un ticket `pending` puede resolverse: cualquier
segundo approve/reject, incluso si esperó el lock de otra transacción, responde
409 `TICKET_ALREADY_RESOLVED`. El cierre repetido del grupo permanece
idempotente.

## Eventos de notificación

Las transiciones válidas publican, dentro de su misma transacción,
`ticket.created`, `ticket.approved`, `ticket.rejected`, `ticket.resolved` y,
cuando corresponde, `ticket.signature_required`. Notifications consume el
resultado sin cambiar locks, policies de firma, revisiones ni resolución
única. La entrega Expo ocurre después del commit conforme al contrato
[`MOBILE_NOTIFICATIONS_V1.md`](MOBILE_NOTIFICATIONS_V1.md).

## Límite vigente

Este contrato se aplica al agregado temporal OT LAB. No cambia ServiceOrder,
ServiceWorkOrder, firmas ETS, Motor de Resoluciones ni el ERP web. La revisión
manual del nuevo sprint en dispositivos físicos y TestFlight sigue pendiente;
no se ejecutó build EAS ni publicación.
