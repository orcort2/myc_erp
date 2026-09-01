> Estado: VIGENTE
>
> Corte verificado: 2026-09-01
>
> Alcance: módulo temporal y removible de Órdenes de Trabajo LAB para `myc-mobile`

# Órdenes de Trabajo LAB

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

## API

| Método | Ruta relativa | Efecto |
| --- | --- | --- |
| POST / GET | `/lab-work-orders` | crear raíz / listar con `folio`, `client`, `status`, `offset`, `limit` |
| GET / PATCH | `/lab-work-orders/{id}` | detalle de grupo / propagar generales |
| DELETE | `/lab-work-orders/{id}` | eliminar una OT individual y reparar/conservar el grupo |
| POST | `/{id}/equipment` | agregar hasta 10 |
| PATCH / DELETE | `/{id}/equipment/{equipment_id}` | editar / eliminar antes de firma |
| POST | `/{id}/additional` | crear la siguiente OT del grupo |
| POST | `/{id}/signatures` | firmar la recepción de la cohorte abierta del grupo histórico |
| POST | `/{id}/signatures/individual` | firmar la recepción únicamente de la OT seleccionada |
| POST | `/{id}/complete` | completar la cohorte compartida del folio seleccionado |
| POST | `/{id}/complete/individual` | completar idempotentemente una sesión exclusiva |
| GET | `/{id}/pdf` | entregar PDF individual final |
| GET | `/{id}/revisions` | historial documental |
| GET | `/{id}/revisions/{revision}/pdf` | PDF histórico inmutable |
| GET | `/export` | ZIP integral administrativo |

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
