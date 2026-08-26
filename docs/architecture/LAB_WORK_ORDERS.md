> Estado: VIGENTE
>
> Corte verificado: 2026-08-26
>
> Alcance: módulo temporal y removible de Órdenes de Trabajo LAB para `myc-mobile`

# Órdenes de Trabajo LAB

## Grupos anticipados (Bloque 2, 2026-08-26)

Un grupo anticipado reutiliza `root_work_order_id`; no introduce otra identidad para firma, Tickets o PDF. `_allocate_folio_block` toma una sola vez el lock institucional y reserva N folios consecutivos únicamente dentro de la transacción que crea las N filas. Una solicitud externa `pending`/`in_review` no toca el secuenciador. La aprobación bloquea la solicitud, materializa el grupo, guarda `root_work_order_id` y cambia a `approved` antes del commit; un retry devuelve ese grupo.

`operator_client_id` es exclusivamente el tenant derivado de `MobileSecurityContext`. `client_name`, dirección y contacto son el snapshot documental del cliente final. Operativo Sr requiere `work_orders.group.request`; Viewer y Jr no la reciben. La creación directa y decisiones administrativas usan permisos `lab_work_order_groups.*`.

Ningún actor `client` puede usar POST de alta individual ni crear una OT adicional. Esta frontera se aplica en router además del RBAC y la UI. Staff conserva ambos flujos. La bandeja administrativa compone tickets y solicitudes como proyecciones separadas. `WorkOrderGroupRequest` continúa siendo la fuente de verdad y su conversación sólo contexto; claim garantiza solicitante y handler como participantes.

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
- `LabWorkOrderSignatureSession`: una sesión versionada por grupo, con actor y
  fecha del servidor.
- `OperationalTicket` y `LabWorkOrderRevision`: solicitud operativa y snapshot
  documental inmutable de cada cierre anterior.
- `LabWorkOrderSignature`: exactamente una firma de técnico y una de cliente,
  con nombre, fecha declarada, versión y PNG data URL.

Sólo `created_by_user_id` y `signed_by_user_id` referencian `users` para
trazabilidad. No hay FK a agregados productivos.

## Grupo de captura y firma

La OT raíz se autorreferencia mediante `root_work_order_id`. Las adicionales
conservan además `previous_work_order_id` y `sequence_number`; el folio visible
nunca se usa como FK. Los datos generales se capturan una vez y toda edición
previa a firma se propaga al grupo.

Una OT adicional sólo puede nacer desde la última OT del grupo cuando contiene
10 equipos. Hereda datos generales, empieza con 0/10 y recibe su folio en el
backend. Cada OT conserva su PDF individual.

En el cierre inicial, la firma se captura una sola vez después de revisar todo el grupo. Una única
`LabWorkOrderSignatureSession` conserva los dos binarios y cada OT referencia
esa misma sesión. En cuanto se firma, todas las OT pasan a
`ready_for_signatures`; desde ese momento se rechazan nuevas OT, equipos,
ediciones o eliminaciones operativas. La eliminación administrativa individual
permanece disponible con permiso específico. La finalización genera y congela todos los PDFs y
transiciona el grupo completo a `completed`.

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

## Estados y reapertura

```text
draft → ready_for_signatures → completed
                              ↓ Ticket aprobado
                   snapshot → draft (revisión N+1)
```

La reapertura sólo ocurre al aprobar un Ticket y afecta coherentemente al grupo.
El PDF y la firma anteriores permanecen en la revisión histórica. La política
`preserve` admite cambios no sustantivos; cualquier cambio estructural invalida
automáticamente la firma activa y exige una nueva sesión. El contrato detallado
está en `OPERATIONAL_TICKETS_AND_LAB_REOPENING.md`.

## PDF y app móvil

El render reutiliza el formato institucional `work_order_pdf.html` y su
infraestructura WeasyPrint. Cada PDF muestra folio, datos manuales, hasta diez
equipos, informe, ✓/X y las firmas compartidas. El binario y SHA-256 quedan en
la OT para garantizar exportación futura.

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

El único acceso canónico sigue siendo **Continuar a firmas** dentro de la
revisión LAB. La experiencia móvil reimplementa de forma autónoma la jerarquía
visual MYC como pasos Cliente → Técnico, transición local y guardado real. No
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

La captura temporal se eleva a la pantalla OT y se liga exclusivamente a
`root_work_order_id`, identidad canónica estable del grupo LAB. Refetch,
reemplazo del objeto `workOrder`, rerender, rotación, cierre/reapertura visual
del modal y navegación entre OT hermanas conservan nombres, paso, strokes,
`hasDrawing` y PNG mientras la raíz sea la misma. Ningún `id` de OT individual,
referencia React, versión, timestamp, equipo ni estado visual participa en esa
identidad.

Al recibir una raíz distinta se sustituye el borrador completo por uno vacío ya
asociado al grupo nuevo; por ello Grupo A → Grupo B → Grupo A no recupera la
captura anterior. Iniciar una OT sin raíz, eliminar el contexto o completar el
POST también retira el borrador. Antes del envío se vuelve a comparar la raíz
capturada con la del grupo abierto. Un error de backend conserva nombres y
strokes sólo para reintento en ese mismo grupo; un lock lógico impide doble
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
El servicio bloquea la OT y el grupo, elimina equipos, PDF actual, revisiones y
tickets/notificaciones exclusivos, conserva la auditoría histórica y registra
`lab_work_order.deleted` con folio, raíz y supervivientes.

Si quedan hermanas, conserva sesiones de firma, tickets, revisiones y
notificaciones todavía compartidos. Al borrar la raíz, la primera superviviente
se vuelve raíz y las sesiones del grupo se reparentan; al borrar cualquier
posición se recompone `previous_work_order_id` y se compacta
`sequence_number`. Si era la última OT, elimina también sus sesiones/firmas
exclusivas. PDFs y firmas son binarios dentro de PostgreSQL, no archivos del
filesystem, y todas las mutaciones comparten un commit con rollback explícito.

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
| POST | `/{id}/signatures` | crear una sesión y bloquear el grupo |
| POST | `/{id}/complete` | generar todos los PDFs y completar |
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

El manifiesto registra totales, folios y SHA-256 de PDFs/firmas. Antes de
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
