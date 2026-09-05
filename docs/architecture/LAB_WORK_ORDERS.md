> Estado: VIGENTE
>
> Corte verificado: 2026-09-05
>
> Alcance: módulo temporal y removible de Órdenes de Trabajo LAB para `myc-mobile`

# Órdenes de Trabajo LAB

## Catálogo LabClient e importación

`LabClient` es la autoridad temporal de clientes para la operación LAB móvil y
permanece aislado del `Client` productivo. El importador XLSX exige
`CLIENTE`, `CONTACTO` (también `ATENCION`/`ATENCIÓN`) y `DIRECCIÓN`; acepta
opcionalmente `CÓDIGO POSTAL` (`CODIGO POSTAL`, `CP` o `C.P.`), `CIUDAD` y
`ESTADO`. Los encabezados se resuelven sin depender de mayúsculas, acentos,
puntuación o espacios redundantes. `DIRECCIÓN ORIGINAL` y `REVISAR` son
auxiliares y nunca se persisten. La identidad deduplicada sigue siendo
empresa+dirección+atención; código postal, ciudad y estado son metadata
estructurada y no provocan una identidad paralela.

El listado conserva una respuesta directa `LabClient[]` y una sola ruta:
`GET /api/mobile/v1/technician/lab-clients`. Búsqueda, scope organizacional,
activos/inactivos, `limit` (1..100, default 25) y `offset` se aplican en SQL.
El selector de OT no consulta con menos de dos caracteres, usa debounce de
300 ms y solicita cinco filas; el módulo Clientes solicita páginas de 25 y
añade páginas mediante “Cargar más”.

## Grupos anticipados (Bloque 2, 2026-08-26)

Un grupo anticipado reutiliza `root_work_order_id`; no introduce otra identidad para firma, Tickets o PDF. `_allocate_folio_block` toma una sola vez el lock institucional y reserva N folios consecutivos únicamente dentro de la transacción que crea las N filas. Una solicitud externa `pending`/`in_review` no toca el secuenciador. La aprobación bloquea la solicitud, materializa el grupo, guarda `root_work_order_id` y cambia a `approved` antes del commit; un retry devuelve ese grupo.

`operator_client_id` es exclusivamente el tenant derivado de `MobileSecurityContext`; el payload externo no puede elegirlo. `client_name`, dirección y contacto son el snapshot documental del cliente final. Operativo Sr requiere `work_orders.group.request`; Viewer y Jr no la reciben. El listado externo conserva la regla organizacional vigente: un actor autorizado ve las solicitudes de su `operator_client_id`, nunca las de otro tenant. La creación directa y decisiones administrativas usan permisos `lab_work_order_groups.*` y actor `internal`.

Ningún actor `client` puede usar POST de alta individual, grupo directo ni crear una OT adicional. Esta frontera se aplica en router además del RBAC y la UI. Staff autorizado conserva alta individual y puede materializar directamente un grupo desde Web o Mobile reutilizando `create_work_order_group`; no crea `WorkOrderGroupRequest` ni pasa por aprobación.
El rol interno Técnico recibe deliberadamente `lab_work_order_groups.create`,
pero no `lab_work_order_groups.requests.read`, `.claim` ni `.decide`: puede
materializar directamente y no entra al workflow administrativo temporal del
operador externo.

La bandeja administrativa Mobile compone `OperationalTicket` y `WorkOrderGroupRequest` como proyecciones separadas y calcula pendientes accionables con dos consultas acotadas, sin endpoint/modelo agregado nuevo. `WorkOrderGroupRequest` continúa siendo la fuente de verdad. Durante `pending`, `conversation_id` es nulo; el claim atómico asigna handler, crea o reutiliza la conversación, agrega exclusivamente requester/handler y sólo entonces publica mensajes system. Approve/reject reutilizan ese vínculo sin duplicarlo.

## Autoridad y aislamiento

El LAB resuelve captura operativa temporal desde iPhone sin crear ni modificar
`ServiceOrder`, `ServiceWorkOrder`, `Equipment`, `Client`, `Certificate`, Hojas
de Campo, Facturación ni entidades del Motor de Resoluciones. El flujo
productivo no puede depender de tablas, rutas o tipos LAB. La app no consulta
`/api/service-orders/...` para listar, abrir, documentar o eliminar OT LAB.

El namespace protegido es
`/api/mobile/v1/technician/lab-work-orders`. Staff conserva
`lab_work_orders.use`; clientes usan permisos externos por operación y scope
obligatorio de `ClientPortalMembership.client_id`. `lab_work_orders.export` reserva la exportación
integral a autoridad administrativa. `lab_work_orders.delete` reserva el
borrado individual a Administrador mediante su comodín institucional `*`, sin
asignación a roles ordinarios. El guard transversal conserva deny-by-default y
`MobileSecurityContext`; el contrato está en
[`MOBILE_SECURITY_CONTEXT.md`](MOBILE_SECURITY_CONTEXT.md).

## Agregado persistente

- `LabWorkOrder`: datos generales, `client_id` nullable, folio, cadena de
  grupo, estado y PDF final inmutable. El cliente es obligatorio cuando el
  actor es externo y nulo sigue siendo válido para históricos/staff.
- `LabWorkOrderEquipment`: hasta diez equipos exclusivos de la OT; sólo
  instrumento, marca, identificación, serie, informe opcional y condición
  física booleana.
- `LabWorkOrderSignatureSession`: una sesión de recepción versionada por raíz
  histórica, con actor y fecha del servidor. Una raíz puede conservar varias
  sesiones y cada OT referencia la recepción que estaba vigente al iniciar su
  ejecución técnica; la sesión no representa por sí sola un cierre.
- `OperationalTicket` y `LabWorkOrderRevision`: solicitud operativa y snapshot
  documental inmutable de cada cierre anterior.
- `LabWorkOrderSignature`: exactamente una firma de técnico y una de cliente,
  con nombre, fecha declarada, versión y PNG data URL.

Sólo `created_by_user_id` y `signed_by_user_id` referencian `users` para
trazabilidad. No hay FK a agregados productivos.

## Grupo histórico, recepción y cohorte de cierre

La OT raíz se autorreferencia mediante `root_work_order_id`. Las adicionales
conservan además `previous_work_order_id` y `sequence_number`; el folio visible
nunca se usa como FK. Los datos generales se capturan una vez. Mientras existan
hermanas `draft`, una edición general se propaga exclusivamente a esas
integrantes editables; una OT `completed` queda congelada aunque otra hermana
cambie después.

Una OT adicional sólo puede nacer desde la última OT del grupo cuando contiene
10 equipos. Hereda datos generales, empieza con 0/10 y recibe su folio en el
backend. Cada OT conserva su PDF individual.

`root_work_order_id`, `previous_work_order_id`, `sequence_number` y los folios
representan parentesco operativo/histórico; nunca se recalculan por cerrar una
cohorte. `_group()` conserva expresamente esa semántica completa.

La recepción ofrece dos operaciones backend explícitas. La recepción grupal
toma las OT `draft` abiertas de la raíz, exige al menos un equipo configurado
en cada participante y crea una sesión Cliente + Técnico sólo para ellas. La
recepción individual exige equipo configurado únicamente en la OT elegida y
crea una sesión exclusiva. En ambos casos la sesión lleva versión única
`(root_work_order_id, version)`; el servicio bloquea primero la raíz histórica
para serializar `max(version) + 1`. El payload exige las dos firmas: Mobile
mantiene la primera únicamente en estado local y el backend no persiste una
sesión incompleta.

El cierre conserva cohortes independientes del parentesco histórico y de la
modalidad de recepción. Opera sobre las OT no completadas que comparten la
sesión del folio seleccionado y que ya satisfacen su estado técnico. Sólo esas
filas reciben PDF, hash, fecha y `completed`; las hermanas abiertas conservan
su propio avance y una OT ya completada no se regenera ni invalida. Agregar una
OT evolutiva continúa permitido sólo desde la última OT `draft` con diez
equipos. La eliminación administrativa individual permanece disponible con
permiso específico.

Auditoría distingue `individual_signed`/`individual_completed` de los eventos
grupales y registra raíz, sesión, IDs participantes y `scope`. No se infiere la
modalidad por el número de integrantes: el detalle proyecta `signature_scope`
desde esa evidencia para que Mobile reanude el endpoint correcto tras refetch.
Sólo sesiones legacy sin evento estructurado usan el tamaño de la sesión como
fallback compatible.

Este contrato es una excepción temporal y aislada a los ciclos de firma del
ETS productivo descritos por ADR-004/BR-007; no los modifica.

## Folios y concurrencia

El LAB reutiliza `institutional_folio_sequences` con namespace independiente:

```text
document_type = lab_work_order
prefix = LAB
year = 0
range = 6400..6999
```

PostgreSQL serializa la asignación mediante advisory transaction lock y lock
de fila del contador. También contrasta el máximo persistido. `6999` es válido;
el siguiente alta responde `409` y nunca usa `7000`. La secuencia productiva
`work_order/OT/año` permanece intacta.

### Folios de certificado LAB (MYCA/MYCT)

Namespace independiente, también sobre `institutional_folio_sequences`, para el
folio de certificado que se asigna a cada equipo LAB (`_allocate_lab_certificate_folio`,
`app/services/lab_work_orders.py`):

```text
document_type = lab_certificate
prefix = MYCA | MYCT
year = 0            # sentinel fijo, no particiona por año calendario
range MYCA = 4700..7999
range MYCT = 1640..7999
```

El formato del folio es el mismo dashed `MYCA-{MM}-{AA}-{XXXX}` /
`MYCT-{MM}-{AA}-{XXXX}` que usa el motor genérico de certificados (ver
`docs/architecture/folios/CERTIFICATE_AND_WORK_ORDER_FOLIOS.md`), pero es una
secuencia **completamente independiente**: mismo mecanismo de
`pg_advisory_xact_lock` + `FOR UPDATE`, mismo piso/techo aplicados en código
(no hay `CheckConstraint` de rango en `lab_work_order_equipment.certificate_folio`,
a diferencia del folio numérico de OT que sí lo tiene), y el mismo folio nunca
se reutiliza tras cancelación o reasignación de servicio.

**Deuda conocida, aceptada explícitamente:** al usar `year = 0` (perpetuo, no
particionado por año calendario), el rango LAB no vuelve a su piso cada enero
como sí lo hace el motor genérico (`_initial_value`, `institutional_folios.py`).
Esto significa que, en teoría, a partir de 2027 los números que emite este
rango temporal podrían coincidir numéricamente con los que emite el motor
genérico para el mismo prefijo/año en otra tabla (`certificates.folio` vs.
`lab_work_order_equipment.certificate_folio`, con unicidad solo dentro de cada
tabla). No se corrige rediseñando la clave de secuencia porque el vertical LAB
es temporal por diseño (ver `myc-mobile/AGENTS.md`, "Naturaleza temporal del
LAB") y se espera que sea retirado antes de que ese solape se vuelva relevante
en la práctica.

#### Cliente operativo externo: pool obligatorio para accredited/traceable

**Bug corregido (2026-09-05):** `_assign_equipment_service_core` resolvía el
folio MYCA/MYCT de un actor externo buscando un ticket `certificate_folio_block`
`resolved` de su `operator_client_id`; si no encontraba folio libre (sin
ticket, o pool agotado), caía en silencio a `folio_status="pending"` --
indistinguible del `pending` legítimo de Vinculado. Ahora, para
`service_type in (accredited, traceable)` y actor externo, la ausencia de un
folio disponible responde `409` con
`{"code": "LAB_CERTIFICATE_FOLIOS_UNAVAILABLE", "service_type", "required_prefix",
"operator_client_id"}` y no persiste equipo/service_type/edit_version
parcial (mismo rollback que el agotamiento de la secuencia interna).
`linked` permanece exento -- sigue pudiendo quedar `pending` sin bloqueo. El
staff interno (`external=False`) tampoco se ve afectado: siempre resuelve
vía `_allocate_lab_certificate_folio`.

**"Distribuir folios disponibles"** (`preview_pending_certificate_folio_distribution`
/ `distribute_pending_certificate_folios`, `app/services/lab_work_orders.py`)
repara equipo que quedó `pending` desde antes de este fix. Opera sobre UNA
OT: sólo equipo activo, `accredited`/`traceable`, `certificate_folio IS NULL`,
`folio_status="pending"`. Fuente única: tickets `certificate_folio_block`
`resolved` del mismo `operator_client_id`, excluyendo folios ya `used` --
nunca la secuencia institucional interna, nunca el pool de otro tenant.
Preview (`GET .../certificate-folios/preview`) es sólo lectura y devuelve
conteos pending/disponibles por prefijo y la asignación propuesta
(`equipment_id`/`position`/`instrument`/`prefix`/`folio`, orden `position
ASC`). Distribute (`POST .../certificate-folios/distribute`) es todo-o-nada
por prefijo: si el pool no alcanza, `409 LAB_CERTIFICATE_FOLIOS_INSUFFICIENT`
(`prefix`/`required`/`available`) sin mutar nada; si alcanza, asigna TODO en
una transacción, marca cada folio `used` en su ticket y registra
`AuditLog` `lab_work_order.pending_certificate_folios_distributed`. Locking:
mismo `SELECT ... FOR UPDATE` sobre las filas de ticket ya usado por el
alta -- dos distribuciones concurrentes nunca consumen el mismo folio
(regresión PostgreSQL real en `test_lab_certificate_folio_distribution.py`).
Idempotente: un segundo run no encuentra equipo pending que reasignar.
Permiso: reutiliza `lab_work_orders.cancel` + actor interno, mismo criterio
que "Cambiar modalidad de trabajo" -- ninguna capacidad nueva para Captura,
Técnico o externos.

### Folio documental Vinculado

`LabWorkOrderEquipment.report_number` es el único input del folio documental
Vinculado. Si el actor tiene `lab_folios.resolve`, el backend valida unicidad,
normaliza el texto y fija `certificate_folio`/`folio_status=authorized` sin
crear Ticket ni tocar `institutional_folio_sequences`. Si no tiene el permiso,
el equipo queda `pending` y `linked_folio.requested_folio` conserva lo escrito.
Una edición posterior autorizada resuelve el Ticket pendiente, registra actor,
fecha, snapshot y notifica al solicitante cuando es otra persona; el Ticket no
se elimina. La omisión del folio conserva el pending normal.

## Estados, Hojas de Campo y reapertura

```text
draft
  → firma de recepción técnico + cliente
  → received_signed
  → creación real de la primera FieldSheet
  → in_progress
  → todas las FieldSheets requeridas completas
  → ready_to_close
  → cierre
  → completed
```

`ready_for_signatures` queda exclusivamente como compatibilidad histórica: un
registro previo puede cerrarse sin convertirse artificialmente a
`received_signed`, sin otra firma y sin reasignar su sesión. El flujo nuevo no
produce ese estado.

La firma exige: al menos un equipo por OT participante; `service_type` en cada
equipo; MYCA/MYCT `reserved` o `authorized` para acreditado/trazable;
`LinkedCompany` para vinculado, cuyo folio puede seguir pendiente; y cliente
documental resoluble por el snapshot vigente. La validación precede a la
creación de la sesión y el lock de grupo evita una recepción parcial.

Después de `received_signed`, datos generales, cliente receptor, composición e
identidad de equipos, cliente documental, servicio, empresa vinculada y folios
quedan congelados por backend con `409`. Sólo crear realmente la primera
`FieldSheet` cambia la OT a `in_progress`; abrir, consultar, navegar o refrescar
no cambia estado. La hoja guarda exactamente
`work_order.signature_session_id` al crearla y nunca se reancla buscando la
última versión de la raíz. Completar la última hoja requerida mueve, en la
misma transacción, `in_progress → ready_to_close`.

Una revisión vigente `draft` o `in_progress` se puede descartar por el endpoint
DELETE de la hoja. En primera captura se eliminan sólo sus dependencias
exclusivas y, cuando ya no queda otra captura técnica, la OT vuelve a
`received_signed`. En recaptura se elimina N+1 y se restaura N como
`is_current=true`; la revisión completed, su PDF y SHA permanecen inmutables.
Una hoja completed nunca muestra ni acepta descarte. El hard delete de OT
reutiliza esta operación sólo cuando todas sus hojas son borradores vigentes;
una completed o cualquier revisión histórica produce conflicto legible.

`LabWorkOrder.reception_date` sigue siendo la autoridad. La edición directa
exige actor interno con `work_orders.create` o el fallback legacy
`lab_work_orders.use`; actualiza la OT y únicamente las FieldSheets current
`draft`/`in_progress` en una transacción auditada. Completed e históricas no se
tocan. Sin autoridad, Mobile presenta la fecha readonly y permite crear el
Ticket informativo `reception_date_change`, cuya creación/resolución nunca
modifica la fecha.

Después del POST de creación, Mobile vuelve a leer la OT y reemplaza su
proyección con la respuesta backend; no infiere `in_progress`. La misma lectura
reutilizable se ejecuta al completar hoja y al solicitar folio. Acreditado y
Trazable presentan el folio como generado por sistema y nunca como informe
opcional editable; Vinculado conserva su flujo específico.

El rol Captura obtiene únicamente `lab_field_sheets.capture` para leer la OT y
crear/editar/completar sus hojas después de recepción. No recibe por esa clave
alta o edición de OT/equipo, firma, folios, cierre, cancelación ni revisión de
Tickets. Los actores externos no reciben ese permiso interno y conservan
tenant scope y la excepción histórica de cierre sin hojas.

La reapertura sólo ocurre al aprobar un Ticket y afecta a la cohorte histórica
identificada por la `signature_session_id` de la OT solicitada. Una sesión
individual reabre sólo esa OT; una sesión compartida reabre sólo sus
participantes, nunca hermanas de otra cohorte.
El PDF y la firma anteriores permanecen en la revisión histórica. La política
`preserve` admite cambios no sustantivos; cualquier cambio estructural invalida
automáticamente la firma activa y exige una nueva sesión. El contrato detallado
está en `OPERATIONAL_TICKETS_AND_LAB_REOPENING.md`.

Fase 6 agrega un modelo de revisión propio para `FieldSheet` (distinto de
`LabWorkOrderRevision`, que versiona la OT). `field_sheets.lab_equipment_id`
dejó de tener una `UniqueConstraint` plana: un índice único parcial
(`uq_field_sheets_current_lab_equipment`) exige exactamente una revisión
`is_current=True` por equipo. Si una reapertura invalida la firma y el
técnico corrige un campo crítico del equipo
(`instrument`/`brand`/`model`/`range_or_capacity`/`identification`/
`serial_number`/`is_good_condition`) sobre una FieldSheet ya `completed`,
esa revisión se retira (`is_current=False`) sin tocar su
`status`/`final_pdf_path`/`final_pdf_sha256`; `create_lab_field_sheet` abre
la siguiente (`revision_number` incremental, `supersedes_field_sheet_id`
apuntando a la anterior) con normalidad en cuanto la OT vuelve a estar
firmada -- este caso SÍ deja el equipo temporalmente sin revisión vigente,
porque la identidad del equipo cambió y una hoja en blanco es lo correcto.
Una reapertura `preserve` nunca retira ni versiona nada -- el trabajo
técnico se conserva tal cual. Ningún documento histórico se sobrescribe ni
se reinterpreta.

**Corrección "reapertura sin hueco operativo" (2026-09-05):** cuando la
retirada de una revisión `completed` NO viene acompañada de un cambio de
campo crítico -- el técnico sólo quiere corregir un dato ya capturado
(observación, resultado, evidencia) vía el Ticket `field_sheet_reopen` o el
equipo objetivo de una reapertura de cohorte completa -- retirar la
revisión ya NO deja un hueco: `_clone_field_sheet_for_correction`
(`app/services/lab_field_sheets.py`) abre de inmediato, en la MISMA
transacción, la revisión N+1 como clon editable de N (`status="draft"`,
`revision_number=N+1`, `supersedes_field_sheet_id=N.id`). Se clonan todos
los campos técnicos editables (template, snapshot institucional,
condiciones, resultados fila por fila, evidencia, notas, capture_values) y
`observations` vuelve a leerse VIGENTE del equipo en ese momento (mismo
contrato ya descrito arriba, "Snapshot de observaciones"). Nunca se clonan
`FieldSheetSignature` (una firma ligada a N no puede atestiguar N+1) ni
`UncertaintyCalculation` (bitácora propia de su revisión). `equipment.field_sheet`
nunca resuelve a `None` en este camino -- Mobile ve "Continuar captura" de
inmediato, nunca "Seleccionar Hoja de Campo", y el técnico corrige sin
volver a capturar desde cero.

Si en cambio el técnico quiere **cambiar de plantilla** (no corregir un
dato, sino usar otra Hoja de Campo), la acción explícita es
`POST .../equipment/{equipment_id}/field-sheet/change-template`
(`change_lab_field_sheet_template`): retira sólo la revisión editable
vigente (nunca una `completed` histórica, mismo guard que el DELETE de
descarte) y abre la siguiente con la plantilla elegida, en una sola
operación atómica. No es "DELETE + POST" en dos peticiones: el DELETE de
descarte restaura la revisión anterior `completed` como vigente, y
`create_lab_field_sheet` rechazaría entonces un POST posterior con 409
("El equipo ya tiene una hoja de campo") -- un callejón sin salida que esta
acción evita por construcción.

## PDF y app móvil

El render reutiliza el formato institucional `work_order_pdf.html` y su
infraestructura WeasyPrint. Cada PDF muestra folio, datos manuales, hasta diez
equipos, informe, ✓/X y las firmas compartidas. El binario y SHA-256 quedan en
la OT para garantizar exportación futura.

Los PDFs propios de FieldSheet no se generan en Mobile: reutilizan
`field_sheet_pdfs.py`. Las hojas nuevas fijan `field_sheet_engine` versión 1 y
al completar congelan ruta, SHA-256, versión de renderer/definición y fecha en
el storage institucional. Las descargas posteriores verifican y devuelven el
mismo archivo. Los tres HTML anteriores permanecen sólo para snapshots legacy;
el contrato completo está en `FIELD_SHEET_PDF_RENDERER.md`.

El adaptador LAB conserva separados los campos institucionales: `address` se
imprime únicamente en DOMICILIO; `postal_code`, `city` y `state_name` se
imprimen en C.P., CIUDAD y ESTADO; `purchase_order` alimenta ORDEN DE COMPRA /
COTIZACIÓN y su ausencia produce una línea vacía, nunca `0`. Este override no
altera el armado de domicilio de las OT productivas.

`myc-mobile` usa Expo SDK 54 y componentes disponibles en Expo Go:

- `expo-secure-store` para access/refresh token;
- `react-native-webview` con canvas táctil autónomo para cada firma;
- `expo-file-system`, `expo-print` y `expo-sharing` para PDF en iOS;
- `react-native-safe-area-context` para respetar notch, status bar y home
  indicator sin offsets por modelo;
- una sola `Modal` nativa; el editor de equipo es un overlay interno.
- `MycDatePickerField` para fechas civiles `YYYY-MM-DD`, con día seleccionado,
  hoy diferenciado y shortcuts opcionales `+6 meses`/`+1 año` calculados desde
  la fecha de calibración y clampeados al último día válido. Son UX
  experimental, no defaults ni política metrológica.

La captura principal no muestra teléfono ni correo; esos atributos permanecen
opcionales únicamente por compatibilidad del contrato backend. Datos generales
y firmas se agrupan en paneles con jerarquía, espaciado vertical y scrolling;
el editor secundario conserva el patrón sheet sin anidar otro `Modal` nativo.

### Contrato móvil de captura de firmas

`myc-mobile/app.json` usa `orientation=default`; portrait y landscape quedan
permitidos por la política nativa de Expo SDK 54. Cualquier binario instalado
que todavía contenga el lock portrait requiere una build nativa posterior para
recibir este cambio; esta intervención no genera ni distribuye esa build.

El acceso canónico es **Continuar a recepción de equipos** antes de la captura
técnica. La experiencia móvil reutiliza la jerarquía visual MYC como pasos de
firma técnico/cliente, transición local y un único guardado real. No
importa componentes, CSS, estado, servicios ni endpoints de `frontend/` y no
reproduce el morph del botón web.

El canvas conserva strokes como puntos normalizados independientes del bitmap.
Un `ResizeObserver` ajusta el backing store al DPR y repinta esos vectores al
cambiar ancho, alto u orientación; después vuelve a serializar el PNG que ya
espera el backend LAB. Por ello portrait → landscape → portrait no depende de
un bitmap que se borra al cambiar `canvas.width`/`height`.

Pointer Events con captura de puntero gobiernan down/move/up/cancel, salida del
área y rechazo de multitouch secundario. `touch-action:none` protege el canvas;
el `ScrollView` nativo conserva `nestedScrollEnabled` y se deshabilita sólo
durante un stroke activo, volviendo a habilitarse al terminar o cancelar. El
estado `hasDrawing` sólo nace con un stroke; **Limpiar** elimina vectores, PNG y
validez. Un stroke sólo es significativo con al menos dos puntos y distancia
normalizada acumulada mínima de `0.01`; un tap o movimiento despreciable se
retira antes de `postMessage`, y la validación TypeScript vuelve a comprobar la
misma condición antes de habilitar avance o envío.

La captura temporal se eleva a la pantalla OT y se liga al contexto de recepción:
`root_work_order_id` para recepción grupal y `work_order.id` para recepción individual.
Refetch, rerender y rotación conservan el borrador sólo si ese contexto no
cambia. Cambiar de modalidad o elegir otra OT individual descarta la captura,
evitando aplicar firmas a una cohorte distinta.

Al recibir un contexto distinto se sustituye el borrador completo por uno vacío
y no existe caché recuperable. Antes del envío se vuelve a comparar el contexto
capturado con la modalidad y OT activas. Un error backend conserva nombres y
strokes sólo para reintento en esa misma cohorte; un lock lógico impide doble
transición y doble POST.

`signature_required` no autoriza la firma inicial. Una OT LAB nueva `draft`
nace con ese flag en `false`; el valor pasa a `true` cuando una sesión previa
fue invalidada y debe renovarse. La UI de reapertura interpreta ese caso sólo
mediante `canSkipSignaturesAfterReopen`. Si el flujo permite capturar ambas
firmas y la raíz sigue siendo la misma, MYC Mobile intenta siempre el POST LAB;
el backend conserva la autoridad sobre estado editable, equipo, sesión previa
y conflictos. Un rechazo del backend conserva el borrador para corrección o
reintento y muestra su detalle, sin limpiarlo por flags de refetch.

## Eliminación administrativa individual

`DELETE /api/mobile/v1/technician/lab-work-orders/{id}` exige
`lab_work_orders.delete` y acepta `draft`, `ready_for_signatures` o `completed`.
El servicio vigente acepta además los estados Fase 3
`received_signed`, `in_progress` y `ready_to_close`; el permiso, ownership y la
conservación/reparentado transaccional siguen siendo obligatorios.
El servicio bloquea la OT y el grupo, elimina equipos, PDF actual, revisiones y
tickets/notificaciones exclusivos, conserva la auditoría histórica y registra
`lab_work_order.deleted` con folio, raíz y supervivientes.

Si quedan hermanas, conserva sesiones de firma, tickets, revisiones y
notificaciones todavía compartidos. Al borrar la raíz, la primera superviviente
se vuelve raíz y las sesiones del grupo se reparentan. Si el grupo nació de una
`LabWorkOrderGroupRequest`, esa solicitud se bloquea en la misma transacción y
su `root_work_order_id` apunta a la nueva raíz; al borrar la última OT queda en
`NULL`, sin cambiar `approved`, handler, decisión, conversación ni trazabilidad.
Al borrar cualquier posición se recompone `previous_work_order_id` y se compacta
`sequence_number`. Si era la última OT, elimina también sus sesiones/firmas
exclusivas. PDFs y firmas son binarios dentro de PostgreSQL, no archivos del
filesystem, y todas las mutaciones comparten un commit con rollback explícito.

El borrado nunca modifica `InstitutionalFolioSequence`: los folios consumidos no
se compactan ni reutilizan. El evento estructurado
`lab_work_order.group_materialized` conserva la lista original de folios. La
proyección actual de una solicitud sin raíz devuelve `folios=[]`; decidir si la
UI histórica requiere un snapshot propio permanece como deuda separada y no
forma parte de la reconciliación referencial.

La app muestra la acción sólo con la capacidad efectiva, usa confirmación
nativa con folio/cliente, impide doble envío y vuelve a consultar el listado
LAB tras `204` o `404`. `403`, `409` y errores de red conservan el detalle.

## Retiro de equipo individual (tombstone, no DELETE físico)

`DELETE /{id}/equipment/{equipment_id}` nunca borra físicamente la fila. Retira
el equipo de la composición operativa vigente mediante `SoftDeleteMixin`
(`is_active=false`, `deleted_at`, `deleted_by`); el registro permanece en
`lab_work_order_equipment` para siempre. Antes de este fix, la relación ORM
`LabWorkOrder.equipment` (`cascade="all, delete-orphan"`) emitía un DELETE
físico que, vía SQLAlchemy, hacía `UPDATE field_sheets SET lab_equipment_id =
NULL` antes de borrar -- si el equipo tenía una FieldSheet histórica
(`completed`), eso violaba `ck_field_sheets_exactly_one_equipment_owner` y
producía un 500 crudo. El caso concreto: OT completada, reabierta vía ticket
(`reopen_ticket_id` asignado), y se intenta retirar un equipo cuya FieldSheet
ya se completó antes del cierre.

Invariantes garantizados por el tombstone:

- La FieldSheet histórica (`status`, `final_pdf_path`, `final_pdf_sha256`,
  `lab_equipment_id`) nunca se toca ni se pierde.
- `LabWorkOrder.active_equipment` (equipo con `is_active=true`) es la única
  fuente para: Mobile (`LabWorkOrderRead.equipment`), el máximo de 10 equipos,
  el cierre técnico (`_missing_completed_sheets`/`_draft_field_sheet_targets`),
  las firmas de grupo/individual y el PDF final -- todos ignoran el equipo
  retirado. `LabWorkOrder.equipment` (la colección completa) sigue existiendo
  para purga administrativa (`DELETE /lab-work-orders/{id}`), `export_all` y
  auditoría/histórico.
- `position` usa un índice único parcial (`uq_lab_equipment_position_active`,
  `WHERE is_active IS TRUE`) en vez de un `UniqueConstraint` pleno -- un
  equipo retirado puede compartir posición con uno nuevo. Retirar un equipo
  compacta las posiciones activas restantes (1..N contiguos); agregar equipo
  nuevo reutiliza el primer hueco libre.
- Retirar equipo sobre una OT ya reabierta (`reopen_ticket_id` no nulo) es un
  cambio estructural: invalida la firma vigente (`signature_required=true`)
  igual que agregar equipo, incluso bajo política `preserve`.
- Delivery, `LabDeliveryItem` y sus columnas `*_snapshot` nunca se tocan al
  retirar equipo -- ni siquiera cuando el equipo retirado ya fue entregado en
  una exhibición histórica.
- `expected_edit_version` sólo se exige (409 `REVISION_CONFLICT` si no
  coincide) cuando la OT ya tiene `reopen_ticket_id`; una OT nunca reabierta
  no impone control de concurrencia optimista en este endpoint.

Ver migración `7088fa142cc2_soft_delete_lab_equipment` y
`backend/tests/test_lab_equipment_soft_delete.py` (incluye una regresión
PostgreSQL real vía `LAB_POSTGRES_TEST_URL`, obligatoria porque el bug
original sólo se manifestaba contra un motor con FK/CHECK reales).

## Modalidad de trabajo: `group` vs `equipment_by_equipment`

`LabWorkOrder.workflow_mode` (migración `6640c526c412`, `CheckConstraint IN
('group', 'equipment_by_equipment')`, default/backfill siempre `group`) es
autoridad backend persistente, elegida al crear la OT y nunca reinterpretada
para históricos. No es un segundo agregado ni una máquina de estados
paralela: reutiliza exactamente `LabWorkOrder`/`LabWorkOrderEquipment`/
`FieldSheet`/`LabWorkOrderSignatureSession`/Delivery.

**`group`** (default) conserva sin ninguna excepción el flujo descrito
arriba: recepción firmada primero, captura técnica después. Ninguna regla
nueva de esta sección aplica a una OT `group`.

**`equipment_by_equipment`** soporta el trabajo real de campo (equipo →
servicio → Hoja de Campo → siguiente equipo):

- `_ensure_capture_allowed` permite crear/editar FieldSheet con la OT todavía
  `draft` (antes de firmar recepción) para este modo -- la OT NUNCA finge
  `received_signed`; permanece `draft` durante toda la captura previa. Es
  captura real (referencias, resultados, condiciones, observaciones,
  evidencia), no sólo "preparar" una hoja vacía.
- `complete_lab_field_sheet` bloquea explícitamente formalizar una hoja
  individualmente mientras la OT siga `draft` en este modo: la frontera
  documental sigue siendo la firma final, nunca antes. Antes de firmar:
  `lab_signature_session_id` es `NULL`, no hay `status=completed` ni PDF/SHA
  final para ninguna hoja de esta OT.
- El estado de cada equipo se reconstruye SIEMPRE desde
  `field_sheet_id`/`field_sheet_status` (nunca desde un evento Mobile
  efímero de "acabo de guardar"): sin hoja → "Seleccionar Hoja de Campo";
  `draft`/`in_progress` → "Continuar captura"; `completed` → lista. Esto
  funciona igual tras refresh, tras cerrar/reabrir la app, y para equipo que
  ya existía antes de un cambio de `workflow_mode`.
- `GET /{id}/equipment-by-equipment/prevalidate` es sólo lectura: antes de
  abrir la pantalla de firma, valida cada equipo activo (`_validate_ready_to_complete`,
  la MISMA autoridad que usa completar una hoja o el autocompletar de
  cierre -- nunca una segunda política) y el folio (`_unresolved_folio_equipment`).
  Devuelve blockers estructurados por equipo; Mobile nunca abre la firma si
  hay alguno.
- `POST /{id}/equipment-by-equipment/finalize` (`finalize_equipment_by_equipment_work_order`)
  es la única operación de cierre: UNA transacción, un solo commit al final,
  encadena firma (`_sign_members_uncommitted`), asignación explícita de
  `lab_signature_session_id` a cada FieldSheet vigente, completar cada hoja
  ya capturada (`_complete_lab_field_sheet_uncommitted`), cerrar la OT
  (`_finish_complete_members_uncommitted` -- PDF/SHA final, notificación
  `work_order.completed` a Captura, resolución de tickets de reapertura) y
  registrar una entrega FULL (`_create_delivery_event`/`_finalize_delivery`)
  reutilizando EXACTAMENTE las mismas firmas Cliente/Técnico ya capturadas
  (`delivered_by_signature_data_url`/`recipient_signature_data_url`,
  `recipient_name` del firmante cliente). Nunca pide una segunda firma de
  entrega. Un fallo en cualquier paso hace rollback completo (incluida la
  limpieza de cualquier PDF de FieldSheet ya escrito a disco, mismo patrón
  que el autocompletar de `_complete_members`) y no deja firma/hoja/OT/
  entrega parcial. Es idempotente ante retry: si la OT ya quedó
  `completed`/`partially_closed`, devuelve la lectura actual sin repetir
  nada -- no existe estado intermedio persistible porque no hay commit
  antes del final.
- `sign_group`/`sign_individual` rechazan explícitamente una OT
  `equipment_by_equipment` que nunca haya pasado por `finalize` (`reopen_ticket_id`
  nulo): esos endpoints son exclusivos de `group`. Tras una reapertura
  posterior (`reopen_ticket_id` ya asignado), el sistema normal de firma/
  reapertura vuelve a aplicar sin excepción.
- `list_lab_field_sheet_tray` excluye explícitamente una OT
  `equipment_by_equipment` todavía `draft`: esas FieldSheets pertenecen al
  técnico que está trabajando en campo, nunca aparecen prematuramente como
  bandeja de Captura.
- Una OT adicional (`create_additional_work_order`) puede elegir SU PROPIA
  `workflow_mode`, independiente de la OT que la origina (parámetro opcional
  `workflow_mode` en `POST /{id}/additional`; sin él, hereda la de `source`
  por compatibilidad hacia atrás). No se valida ni se toca la modalidad de
  ninguna otra OT del grupo.
- Retirar equipo (tombstone) se comporta idéntico en ambos modos: un equipo
  retirado nunca bloquea `finalize`, nunca cuenta contra el máximo de 10 y
  nunca entra a la nueva entrega.

### Tres autoridades separadas (cierre "grupos mixtos", 2026-09-04)

`workflow_mode`, la firma y la entrega son conceptos independientes que
nunca deben confundirse entre sí:

1. **`workflow_mode`** (por OT): define CÓMO ejecuta esa OT su trabajo
   técnico -- `group` o `equipment_by_equipment`. Ver arriba.
2. **`signature_scope`** (independiente de `workflow_mode`): define CUÁNTAS
   OT comparten UNA sesión de firma -- `individual` o `group`. Una OT
   `equipment_by_equipment` puede firmar sola, varias `equipment_by_equipment`
   pueden compartir una firma grupal, y una cohorte MIXTA de
   `equipment_by_equipment` + `group` también puede compartir una sola firma
   grupal cuando el contrato de cada miembro lo permite (ver más abajo).
3. **Delivery**: representa qué equipo se entrega FÍSICAMENTE en un evento
   dado. Una firma grupal NUNCA implica por sí sola que todo el equipo
   firmado se entregó.

**Un mismo `root_work_order_id` puede mezclar libremente `group` y
`equipment_by_equipment` entre sus miembros** -- no existe ninguna
constraint de igualdad por root, ninguna actualización en cascada y ninguna
validación que rechace automáticamente modalidades distintas dentro de la
misma cohorte histórica.

### Cambio administrativo de modalidad: `POST /{id}/workflow-mode`

Acción administrativa explícita (`change_lab_work_order_workflow_mode`,
permiso `lab_work_orders.cancel` -- reutilizado, nunca un permiso nuevo;
nunca otorgado a Captura/Técnico/externos por defecto; sólo actor interno) --
nunca confundir con `service_type` (accredited/traceable/linked), un
contrato distinto. Requiere `reason` no vacío (trim; vacío o sólo espacios
se rechaza) y escribe un `AuditLog` (`lab_work_order.workflow_mode_changed`)
con `work_order_id` (`entity_id`), `previous_values.workflow_mode`,
`new_values.workflow_mode`/`reason`, `user_id` y `timestamp` (`created_at`
del propio `AuditLog`, autoridad canónica -- nunca duplicado dentro de
`new_values`).

Guard: sólo procede mientras la OT sigue `draft` y sin ninguna sesión de
firma vigente (`signature_session_id is None`) -- esa única condición ya
excluye por construcción `completed`/`partially_closed`/`received_signed`/
`in_progress`/`ready_to_close` y cualquier Delivery real (que exige la OT ya
cerrada). Reinterpretar una OT ya formalizada sigue siendo exclusivamente el
sistema normal de Tickets/reapertura -- esta acción NUNCA es un atajo
alterno. Actúa sobre EXACTAMENTE la OT indicada, nunca cascada a sus
hermanas del mismo root.

**`group` → `equipment_by_equipment`** conserva ID de OT, todos los IDs de
equipo, posición, instrumento, marca, serie, identificación, `service_type`,
folios, observaciones y cliente documental -- nunca recrea equipo. Cada
equipo existente ofrece de inmediato "Seleccionar Hoja de Campo" (sin
FieldSheet) reconstruido desde backend. Ver el caso productivo de 5 equipos
preexistentes en `backend/tests/test_lab_equipment_by_equipment_workflow.py`
(incluye su regresión PostgreSQL real).

**`equipment_by_equipment` → `group`** (con una FieldSheet ya en captura)
NUNCA borra ni recrea esa FieldSheet: mismo ID, mismo `template_key`,
mismos `capture_values`/resultados/observaciones/evidencia/referencias,
mismo estado `draft`/`in_progress` sin formalizar. Tras el cambio la OT
obedece el contrato `group`: sin recepción firmada, la captura adicional
sigue bloqueada (`_ensure_capture_allowed`, y el mismo guard en
`update_lab_field_sheet` para una hoja que sobrevivió al cambio); una vez
firmada la recepción, el técnico continúa exactamente la MISMA hoja -- nunca
se le pide capturar dos veces. El cambio de modalidad nunca completa/congela
nada por sí mismo.

Un equipo retirado (tombstone, `is_active=False`) nunca se ve afectado por
un cambio de modalidad: sigue sin reaparecer, sin exigir FieldSheet, sin
bloquear el cambio, sin poder entrar a una nueva entrega; su historial
permanece intacto.

### Firma grupal mixta: `POST /{id}/signature-group/finalize`

Cuando el usuario decide cerrar/firmar COMO GRUPO una cohorte que puede
mezclar miembros `group` y `equipment_by_equipment`, Cliente y Técnico
firman UNA sola vez, produciendo EXACTAMENTE una `LabWorkOrderSignatureSession`
compartida -- nunca una sesión por OT, nunca un segundo lienzo de firma.
`GET /{id}/signature-group/prevalidate` (sólo lectura) resuelve primero el
scope exacto de miembros editables y despacha la validación de CADA UNO
según su PROPIO `workflow_mode`: un miembro `equipment_by_equipment` se
valida como "listo para terminar" (misma autoridad que
`_equipment_by_equipment_finalize_blockers`/`_validate_ready_to_complete`);
un miembro `group` se valida sólo como "listo para aceptar recepción" (misma
autoridad que `_ensure_reception_prerequisites`), NUNCA se le exige
FieldSheets completas. Si CUALQUIER miembro falla su propio chequeo, ni la
prevalidación ni la firma proceden -- ninguna mutación ocurre.

`finalize_lab_signature_group` es UNA sola transacción/commit (mismo patrón
atómico que `finalize_equipment_by_equipment_work_order`, reutilizado, no
duplicado): firma la sesión compartida (`_sign_members_uncommitted`) y,
ADEMÁS, cada miembro `equipment_by_equipment` completa sus FieldSheets y
cierra técnicamente (`_complete_lab_field_sheet_uncommitted`/
`_finish_complete_members_uncommitted`); cada miembro `group` sólo queda
`received_signed` y continúa su flujo normal de captura/cierre después --
**"UNA firma NO implica el mismo estado final para todas las OT"**. La
entrega FULL automática de ese evento incluye ÚNICAMENTE el equipo de los
miembros `equipment_by_equipment` recién cerrados -- nunca el de un miembro
`group` que sigue físicamente en el laboratorio (`_finalize_delivery` recibe
siempre la cohorte completa del grupo, nunca sólo el subconjunto recién
entregado, para que el recibo final de grupo no se genere prematuramente
mientras un miembro siga pendiente). Un fallo en cualquier paso revierte
firma + hojas completadas + cierre + entrega por completo (incluida la
limpieza de PDFs huérfanos ya escritos a disco) -- nunca un estado parcial.
Idempotente ante retry, igual que el finalize individual.

Caso de referencia: OT1 y OT2 `equipment_by_equipment` con captura ya lista
+ OT3 convertida administrativamente a `group` ("Equipo trasladado al
laboratorio"). Una sola firma grupal: OT1/OT2 quedan `completed` con su
propia Delivery; OT3 queda `received_signed`, sin Delivery de este evento, y
continúa después su flujo `group` normal (captura → cierre técnico →
entrega) de forma completamente independiente.

### Snapshot de observaciones (`FieldSheet.observations`)

`create_lab_field_sheet` congela `FieldSheet.observations =
normalizado(LabWorkOrderEquipment.observations)` al MOMENTO DE CREAR esa
revisión (trim; `None`/`""`/sólo espacios → `None`). Es un snapshot inicial,
nunca un vínculo vivo: editar `LabWorkOrderEquipment.observations` después
nunca modifica una FieldSheet ya creada (draft, in_progress o completed). La
FieldSheet puede seguir editando su PROPIO campo `observations` mientras
siga editable, igual que cualquier otro campo de captura. En una reapertura/
recaptura, la revisión N conserva el valor que congeló al crearse; la
revisión N+1 vuelve a leer el valor VIGENTE del equipo en ese momento --
nunca se reescribe la N para "corregirla" retroactivamente. Nunca se mezcla
con `certificate_folio`/`report_number`: el renglón de observación por
equipo del PDF de OT usa el formato `INSTRUMENTO -> IDENTIFICACIÓN :
OBSERVACIÓN` (fuente: `LabWorkOrderEquipment.observations`), mientras que la
sección "Observaciones" del PDF de FieldSheet usa exclusivamente
`FieldSheet.observations` -- dos fuentes distintas, nunca intercambiables.

## API

| Método | Ruta relativa | Efecto |
| --- | --- | --- |
| POST / GET | `/lab-work-orders` | crear raíz / listar con `folio`, `client`, `status`, `offset`, `limit` |
| GET / PATCH | `/lab-work-orders/{id}` | detalle de grupo / propagar generales |
| PATCH | `/lab-work-orders/{id}/reception-date` | actualizar fecha canónica y sincronizar hojas vigentes editables |
| DELETE | `/lab-work-orders/{id}` | eliminar una OT individual y reparar/conservar el grupo |
| POST | `/{id}/equipment` | agregar hasta 10 |
| PATCH / DELETE | `/{id}/equipment/{equipment_id}` | editar / retirar (tombstone lógico, ver abajo) |
| DELETE | `/{id}/equipment/{equipment_id}/field-sheet` | descartar únicamente la revisión vigente editable |
| POST | `/{id}/equipment/{equipment_id}/field-sheet/change-template` | "Cambiar Hoja de Campo": retira la editable vigente y abre otra con nueva plantilla, atómico |
| POST | `/{id}/additional?workflow_mode=` | crear la siguiente OT del grupo; `workflow_mode` opcional elige SU PROPIA modalidad (sin él, hereda la de origen) |
| POST | `/{id}/signatures` | firmar la recepción de la cohorte abierta del grupo histórico |
| POST | `/{id}/signatures/individual` | firmar la recepción únicamente de la OT seleccionada |
| POST | `/{id}/complete` | completar la cohorte compartida del folio seleccionado |
| POST | `/{id}/complete/individual` | completar idempotentemente una sesión exclusiva |
| GET | `/{id}/equipment-by-equipment/prevalidate` | sólo lectura: blockers antes de abrir la firma (`equipment_by_equipment`, scope individual) |
| POST | `/{id}/equipment-by-equipment/finalize` | firma única + completar hojas + cerrar OT + entrega FULL, atómico (`equipment_by_equipment`, scope individual) |
| GET | `/{id}/signature-group/prevalidate` | sólo lectura: blockers de TODO el scope grupal mixto, cada miembro según su propio `workflow_mode` |
| POST | `/{id}/signature-group/finalize` | firma grupal única que puede mezclar miembros `group`/`equipment_by_equipment`; cada uno avanza según su propia modalidad |
| POST | `/{id}/workflow-mode` | acción administrativa "Cambiar modalidad de trabajo" -- motivo obligatorio, sólo pre-firma, nunca cascada a hermanas |
| GET | `/{id}/certificate-folios/preview` | sólo lectura: "Distribuir folios disponibles" -- conteos y asignación propuesta para equipo pending accredited/traceable |
| POST | `/{id}/certificate-folios/distribute` | ejecutar la distribución todo-o-nada; sólo folios ya resueltos del mismo `operator_client_id` |
| GET | `/{id}/pdf` | entregar PDF individual final |
| GET | `/{id}/revisions` | historial documental |
| GET | `/{id}/revisions/{revision}/pdf` | PDF histórico inmutable |
| GET / POST | `/{id}/delivery` | estado de entrega del grupo / registrar entrega normal (todos los pendientes) |
| POST | `/{id}/delivery/partial/{ticket_id}` | ejecutar una entrega parcial ya aprobada |
| GET | `/{id}/delivery/{delivery_id}/pdf` | acuse de una exhibición |
| GET | `/{id}/delivery/final-receipt/pdf` | resumen final consolidado del grupo |
| POST | `/{id}/delivery/{delivery_id}/void` | anular una exhibición (no destruye historial) |
| GET | `/export` | ZIP integral administrativo |

## Entrega física (Delivery)

Cierre técnico (`completed`/`partially_closed`) y entrega física de equipos
son conceptos distintos: cerrar la OT nunca fija `departure_date`. La entrega
vive a nivel de GRUPO/cohorte (`root_work_order_id`), no por OT individual,
porque un cliente puede recoger equipos de varias OT del mismo grupo en un
solo acto.

Cada acto de entrega es una **exhibición** (`LabWorkOrderDelivery`, evento
inmutable numerado consecutivamente por grupo, nunca reutilizado) con sus
propios `LabDeliveryItem` (un renglón por equipo, con snapshot histórico de
instrumento/marca/identificación/serie/folio — nunca recalculado desde el
equipo mutable). Cada exhibición lleva firma de quien entrega (usuario MYC
autenticado, `full_name` + firma capturada) y firma de quien recibe (nombre
libre prellenado con el contacto de la OT + firma), método (`direct` /
`client_pickup`, enum extensible a futuro) y su propio voucher PDF congelado.

**Entrega normal** incluye automáticamente TODOS los equipos aún pendientes
del grupo (no requiere selección) y sólo puede registrarse cuando ninguna OT
relevante del grupo (se excluyen las `cancelled`) sigue sin cerrar
técnicamente (`completed` o `partially_closed`). "Completar entrega" tras una
exhibición parcial es la misma operación: una nueva exhibición `full` con lo
que quede pendiente.

**Entrega parcial** es excepcional: requiere primero un `OperationalTicket`
`partial_delivery` (equipos solicitados + motivo, `pending`), aprobado por
`tickets.review` (mismo permiso ya usado por aprobar/rechazar cualquier otro
tipo de ticket) sin autoaprobación — la aprobación sólo autoriza el set
(`status=approved`), nunca entrega nada. La ejecución posterior debe coincidir
EXACTAMENTE con el set aprobado (ni agrega ni omite equipos) y consume el
ticket (`resolved`); un ticket ya ejecutado no es reutilizable.

`departure_date` de una OT individual se deriva, nunca se captura a mano: es
la fecha de la exhibición en la que su ÚLTIMO equipo pendiente quedó
entregado, proyectada independientemente por OT dentro del mismo grupo.

El grupo está completo cuando no quedan equipos pendientes; en ese momento se
congela un **resumen final** (`LabDeliveryGroupReceipt`, versionado) que lista
cronológicamente cada exhibición y usa "Mismo contacto" cuando el nombre del
receptor coincide (comparación exacta normalizada: trim + casefold + espacios
colapsados, nunca fuzzy) con el primer receptor del grupo — la firma histórica
de cada exhibición se conserva siempre, sólo el texto se abrevia. `N` cuenta
únicamente exhibiciones `completed` (una `voided` no cuenta).

Anular una exhibición (`void`, nunca delete) devuelve sus equipos a
pendientes, recalcula `departure_date` de las OT afectadas y, si rompe la
completitud del grupo, marca el resumen final vigente como superseded sin
borrar sus bytes; la siguiente entrega completa genera una nueva versión. Un
equipo con `LabDeliveryItem` vigente (entrega `completed` no anulada) bloquea
tanto reabrir como cancelar esa OT — si el equipo regresa físicamente a MYC
después de entregado, el contrato es una OT nueva, nunca reabrir la anterior.
Un `departure_date` heredado de datos históricos previos a este dominio (sin
`LabWorkOrderDelivery`/`LabDeliveryItem` reales) es sólo metadata legacy: no
se interpreta como entrega digital ni genera acuse/voucher retroactivo.

Evidencia fotográfica y tracking de paquetería quedan deliberadamente fuera de
esta V1 (el enum `delivery_method` ya es extensible para ese futuro).

## Exportación y retiro controlado

`GET .../export` genera un ZIP en memoria con:

```text
manifest.json
work_orders.json
equipment.json
signatures/session-{id}.json
signatures/session-{id}-{type}.png
pdf/OT-{folio}.pdf
```

El ZIP admite varias sesiones/versiones para una misma raíz y cada fila de
`work_orders.json` conserva su `signature_session_id`. El manifiesto registra
totales, folios y SHA-256 de PDFs/firmas. Antes de
retirar el LAB se debe: bloquear nuevas altas; exportar; comparar total de OT y
equipos; verificar checksums y abrir muestras; custodiar el ZIP; después
retirar app, rutas, servicios, permisos y modelos; y sólo al final ejecutar una
migración explícita de drop. La migración actual nunca elimina datos.

## Límites verificados

La versión operativa previa fue validada en Android/iPhone físicos y TestFlight.
Los sprints posteriores —incluida la reparación de firma/orientación del
2026-08-24— requieren repetir el recorrido completo en Android e iPhone antes
de distribuirse. Hasta esa evidencia nueva el módulo se mantiene `EN
DESARROLLO`, no `SELLADO`.
