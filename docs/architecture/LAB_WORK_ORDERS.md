> Estado: VIGENTE
>
> Corte verificado: 2026-08-14
>
> Alcance: módulo temporal y removible de Órdenes de Trabajo LAB para `myc-mobile`

# Órdenes de Trabajo LAB

## Autoridad y aislamiento

El LAB resuelve captura operativa temporal desde iPhone sin crear ni modificar
`ServiceOrder`, `ServiceWorkOrder`, `Equipment`, `Client`, `Certificate`, Hojas
de Campo, Facturación ni entidades del Motor de Resoluciones. El flujo
productivo no puede depender de tablas, rutas o tipos LAB.

El namespace protegido es
`/api/mobile/v1/technician/lab-work-orders`. `lab_work_orders.use` habilita el
flujo operativo a Técnicos y `lab_work_orders.export` reserva la exportación
integral a autoridad administrativa. El guard transversal conserva
deny-by-default y JWT interno; no existe autenticador LAB alterno.

## Agregado persistente

- `LabWorkOrder`: datos generales manuales, folio, cadena de grupo, estado y
  PDF final inmutable.
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
ediciones o eliminaciones. La finalización genera y congela todos los PDFs y
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
- `react-native-webview` con canvas táctil para cada firma;
- `expo-file-system`, `expo-print` y `expo-sharing` para PDF en iOS;
- `react-native-safe-area-context` para respetar notch, status bar y home
  indicator sin offsets por modelo;
- una sola `Modal` nativa; el editor de equipo es un overlay interno.

La captura principal no muestra teléfono ni correo; esos atributos permanecen
opcionales únicamente por compatibilidad del contrato backend. Datos generales
y firmas se agrupan en paneles con jerarquía, espaciado vertical y scrolling;
el editor secundario conserva el patrón sheet sin anidar otro `Modal` nativo.

## API

| Método | Ruta relativa | Efecto |
| --- | --- | --- |
| POST / GET | `/lab-work-orders` | crear raíz / listar con `folio`, `client`, `status`, `offset`, `limit` |
| GET / PATCH | `/lab-work-orders/{id}` | detalle de grupo / propagar generales |
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
El sprint 2026-08-14 de filtros, Tickets y reapertura requiere repetir ese
recorrido antes de distribuirse. Hasta esa evidencia nueva el módulo se
mantiene `EN DESARROLLO`, no `SELLADO`.
