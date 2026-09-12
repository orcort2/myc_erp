> Estado: En revisión, rama `fix/lab-reopen-edit-keyboard-niimbot-qa`
>
> Tipo: Arquitectura de MYC Mobile
>
> Corte UX verificado: 2026-09-09, base `f23e65726b9a60f69d053fceed61ed615e1ee445`
>
> QA física pendiente -- ver "Estado de soporte" y "Gate de QA física" antes
> de considerar esto listo para producción.

# Impresión de etiquetas térmicas LAB (BLE)

## Contrato de UX vigente — 2026-09-09

El usuario reportó validación física NIIMBOT B1 previa a esta ronda. Según el
contrato de HEAD, la resolución exitosa de `printLabel` permite presentar
«Etiqueta impresa»; esta tarea no reabre ni modifica el protocolo. El modal
local `PrintSuccessModal` usa Animated (180 ms), Continuar y Reimprimir. El
manejador conserva el payload exitoso y bloquea concurrencia antes del primer
await. Una reimpresión fallida cierra el éxito y conserva la gestión de errores.

El Centro de etiquetado conserva `label-printer-setup.tsx` y la misma ruta de
Expo Router desde Home y hoja LAB. `PrinterNotReadyError` se presenta como
«No hay impresora disponible», conservando la reconexión automática del
servicio. No se encontró evidencia que justifique un workaround del Alert
nativo; su callback se verifica con router simulado, no con hardware en esta
sesión. El Centro ya no importa ni muestra QA V3/diagnóstico NELKO. Se conservan
helpers QA, `printPacketSequenceForQa`, PrinterManager y sus pruebas.

Los apartados de auditoría 2026-09-08 siguientes son antecedentes, no una
orden de repetir QA de protocolo. El gate físico completo no se declara
validado por esta ronda de UX.

## Correcciones de auditoría (2026-09-08)

Una auditoría independiente sobre el corte 2026-09-07 encontró 4 problemas
reales, corregidos en esta revisión:

1. **Regla de negocio de INFORME invertida.** La versión anterior imprimía
   `"PENDIENTE"` cuando `certificateFolio` era null. Corregido: una etiqueta
   FINAL sólo se imprime con folio real -- `certificateFolio` ausente/vacío
   ahora bloquea con `LabelRenderError('missing_certificate_folio')`, tanto
   en la frontera de dominio (`LabelRenderer.buildLabelLines`) como antes de
   tocar BLE (`label-print-service.ts printLabel`). Ver "Contrato v1" abajo.
2. **El raster físico (400px) se enviaba tal cual a un cabezal de 384px.**
   Corregido con `printers/raster-adapt.ts` -- ver "Mapeo 50x30 físico ->
   raster imprimible del B1" abajo.
3. **El ciclo de vida del scan BLE no esperaba a que terminara.**
   `BleManagerTransport.startScan()` sólo esperaba a que el scan NATIVO
   arrancara, no a que terminara -- corregido para resolver recién cuando
   el scan lógico termina (evento `onStopScan`, cancelación explícita, o un
   timer de seguridad), con limpieza de listeners garantizada en las tres
   rutas. La pantalla de configuración ahora también cancela el scan al
   desmontarse.
4. **Un handshake NIIMBOT fallido no desconectaba físicamente.** Si
   `Connect`/`ConnectResult` fallaba después de que la conexión BLE ya se
   había establecido, sólo se limpiaba estado local -- el SO podía seguir
   conectado. Corregido con un único primitivo de limpieza idempotente
   (`teardownConnection`) que también desconecta físicamente cuando
   corresponde, usado tanto por `disconnect()` normal como por un handshake
   fallido.

La observación histórica de esta auditoría sobre `PrintStatusResult` fue
superada por HEAD `f23e657`; ver el contrato UX vigente de este documento.

## Correcciones de auditoría de seguimiento (2026-09-08, integración BLE real)

Dos rondas de seguimiento adicionales, ya sobre integración BLE real (no
sólo reglas de negocio/protocolo), corrigieron 5 problemas más:

**Ronda 1** -- `BleManagerTransport` ya implementaba `requestPermissions()`
e `isBluetoothOn()`, pero nada los invocaba, y un handshake NIIMBOT exitoso
podía quedar a medio inicializar:

1. `PrinterManager.scan()` llamaba `ble.startScan()` directo -- el permiso
   de runtime de Android podía nunca pedirse. Corregido: pide permiso,
   verifica Bluetooth, y sólo entonces escanea, lanzando
   `BluetoothPermissionDeniedError`/`BluetoothDisabledError` si alguno
   falla (ver "Permisos" más abajo en esta sección).
2. `NiimbotB1Adapter.connect()` sólo envolvía el handshake en try/catch. Si
   `ble.connect()` tenía éxito pero `discoverServices()`/
   `subscribeNotifications()` fallaban antes de ese try/catch, la conexión
   BLE física quedaba viva sin que el adaptador la conociera. Corregido:
   toda la configuración posterior a un `ble.connect()` exitoso vive en un
   único try/catch, con un flag `physicalConnectionEstablished` que decide
   si `teardownConnection()` debe desconectar físicamente.

**Ronda 2** -- una auditoría posterior encontró que ese mismo readiness no
se reutilizaba en todos los caminos de conexión, que la identificación
best-effort del B1 tragaba errores reales (no sólo timeouts), y que
cambiar de impresora no tenía una frontera explícita:

3. `connectAndRemember()`/`connectPreferred()` llamaban `adapter.connect()`
   directo, sin el mismo chequeo de permiso/Bluetooth que ya exigía
   `scan()` -- si Android revocaba el permiso entre sesiones, el fallo
   llegaba como error nativo genérico en vez de uno accionable. Corregido:
   `PrinterManager` centraliza el chequeo en `ensureBleReady()`, usado por
   los tres caminos.
4. La identificación post-handshake (`PrinterStatusData`, ver "Protocolo
   NIIMBOT B1") ignoraba **cualquier** error en un `catch {}` mudo -- un
   timeout de esa respuesta debe ignorarse (es informativa), pero una
   desconexión física real o un fallo de transporte en esa ventana hacía
   que `connect()` resolviera "con éxito" mientras el estado interno ya
   había vuelto a "no conectado". Corregido: sólo se ignora
   `NiimbotTimeoutError`; cualquier otro error limpia (`teardownConnection`,
   ya idempotente) y se propaga.
5. `connectAndRemember()` podía conectar una impresora nueva mientras otra
   seguía físicamente conectada -- `deviceId` pasaba a representar la
   nueva sin que la anterior se soltara nunca. Corregido: `PrinterManager`
   desconecta la impresora activa antes de establecer la nueva (después de
   confirmar que el intento puede proceder, para no soltar la impresora en
   uso si el intento nuevo va a fallar de todas formas), y rechaza el
   cambio con `PrinterBusyError` si hay una impresión en curso.

Efecto colateral de la corrección 3: como `scan()` ahora espera
`requestPermissions()`/`isBluetoothOn()` (dos saltos de microtarea) antes
de llegar a `startScan()`, si la pantalla se desmonta (`stopScan()` vía
cleanup) mientras ese readiness sigue pendiente -- un diálogo nativo de
Android no resuelve al instante -- antes no había nada que cancelar: el
scan nativo arrancaba igual en cuanto el permiso se resolvía, aunque quien
lo pidió ya se hubiera ido. Corregido con una sesión de scan interna que
`stopScan()` puede marcar como cancelada antes de que exista un scan
nativo real que detener (ver `scan-lifecycle.test.ts`).

## Contrato v1

La etiqueta física MYC es **50x30 mm** (tamaño físico del medio -- nunca
48x28: eso es sólo el área de contenido segura, ~1 mm de margen por lado).
Contiene: insignia MYC, `FECHA DE CAL`, `PROX. CAL`, `CODIGO`, `O.T.`,
`INFORME`. **Sin QR en v1** -- no se agrega contenido nuevo a la plantilla
sólo porque la arquitectura lo permitiría.

```ts
type LabLabelPayload = {
  calibrationDate: string;        // requerido para imprimir
  nextCalibrationDate?: string | null; // null -> "N/A", nunca bloquea
  equipmentCode: string;          // LabEquipment.identification (CODIGO)
  workOrderFolio: string;         // String(LabWorkOrder.folio) (O.T.)
  certificateFolio?: string | null; // LabEquipment.certificate_folio (INFORME);
                                     // REQUERIDO para imprimir la etiqueta final --
                                     // ver "Comportamiento ante datos ausentes"
};
```

`calibrationKind` (`'CALIBRADO' | 'VERIFICADO'`) **se eliminó**: confirmado
por el usuario que la etiqueta no lo necesita, y la auditoría previa a este
cambio no encontró ningún campo de dominio que lo respaldara (no existe en
`LabFieldSheet`/`LabEquipment` ni en `field-sheet-canonical-contract.ts`).

`INFORME` = `certificateFolio`, el mismo folio de certificado (familia
MYCA/MYCT) que ya usa el resto del flujo LAB -- nunca un `report_number` ni
ningún otro campo de nombre parecido, y Mobile nunca sintetiza/adivina un
folio.

### Comportamiento ante datos ausentes (decisión explícita de esta fase, no una regla preexistente -- el botón nunca fue funcional antes)

**Regla de negocio confirmada (corrección 2026-09-08):** una etiqueta física
FINAL sólo se imprime con datos finales reales. `INFORME` **nunca** se
imprime como `"PENDIENTE"` ni ningún otro placeholder -- si el equipo
todavía no tiene folio de certificado asignado, la impresión se bloquea con
un error explícito, tanto en `LabelRenderer.buildLabelLines` (frontera de
dominio -- ningún llamador futuro puede generar un raster ni un trabajo BLE
sin folio real) como en el manejador de UI (`printFieldSheetLabel`, que
nunca llega a invocar `printLabel`/BLE si la validación falla). Nunca se
sintetiza ni se solicita un folio desde el flujo de impresión.

| Campo | Si falta | ¿Bloquea impresión? |
|---|---|---|
| `calibrationDate` | `LabelRenderError('missing_calibration_date')` | Sí -- nunca una etiqueta con la fecha en blanco |
| `nextCalibrationDate` | se imprime `N/A` | No -- no todo servicio exige recalibración periódica |
| `certificateFolio` | `LabelRenderError('missing_certificate_folio')` | Sí -- nunca `"PENDIENTE"` ni ningún placeholder en la etiqueta final |

El botón "Imprimir etiqueta 50×30" en `LabTechnicalCapture` sólo se ofrece
con `sheet.status === 'completed'` (misma gate que "Ver / descargar PDF").

## Arquitectura

```
LabelPrintService (src/services/label-print-service.ts, composición)
        |
        +-- LabelRenderer (labels/label-renderer.ts) -- puro, determinista
        |         |
        |         +-- LabelProfile (labels/label-profile.ts) -- MYC_50X30
        |         +-- bitmap-canvas.ts + bitmap-font-5x7.ts + myc-badge.ts
        |         +-- produce RasterLabel (labels/label-types.ts)
        |
        +-- PrinterManager (printers/printer-manager.ts)
                  |
                  +-- PrinterRegistry (printers/printer-registry.ts) -- clasifica BLE
                  +-- PreferredPrinterStore (puerto inyectado -- ver abajo)
                  +-- LabelPrinterAdapter (printers/types.ts, contrato)
                            |
                            +-- NiimbotB1Adapter (adapters/niimbot-b1/) -- SOPORTADO
                            +-- NelkoPm220Adapter (adapters/nelko-pm220/) -- protocol_pending
                                      |
                            (ambos dependen sólo de BleTransport, printers/ble-transport.ts;
                             la implementación real, ble-manager-transport.ts, envuelve
                             react-native-ble-manager)
```

Ningún adaptador de impresora conoce el significado de "FECHA DE
CAL"/"CODIGO"/etc.: sólo reciben un `RasterLabel` ya compuesto. Ningún
adaptador importa el protocolo de otro (NIIMBOT y NELKO son completamente
independientes). `BleTransport` es la única superficie que un adaptador ve
del radio BLE -- nunca `react-native-ble-manager` directamente, lo que
permite probar el protocolo/orquestación de cada adaptador con un
transporte de prueba en Node, sin ningún módulo nativo.

### Por qué `PreferredPrinterStore` es un puerto inyectado

`printer-manager.ts` **no importa `expo-secure-store` directamente**.
Confirmado durante esta implementación: importar `expo-secure-store` (o
`react-native-ble-manager`) arrastra transitivamente `react-native/index.js`,
que `tsx`/esbuild no puede transformar fuera del bundler de Metro (falla
con `Unexpected "typeof"`). Por eso `PrinterManager` recibe un puerto
`{ read, write, clear }` inyectado -- producción inyecta
`preferred-printer-storage.ts` real (mismo patrón `expo-secure-store` que
`src/storage/secure-storage.ts`, clave `myc.internal.label-printer.v1`);
los tests inyectan un store en memoria. El mismo motivo explica por qué
`ble-manager-transport.ts` no tiene test unitario directo: su cobertura es
la QA física, no Node.

## Perfil físico y DPI

`MYC_50X30` (`label-profile.ts`) declara el tamaño físico del medio; el DPI
**no** vive en el perfil, vive en `PrinterCapabilities.dpi` de cada
adaptador -- hoy ambas impresoras conocidas son 203 dpi, pero eso es una
coincidencia del hardware actual, nunca una suposición fija del sistema.

`px = round(mm / 25.4 * dpi)`. A 203 dpi: lienzo físico ~400x240 px, área
seguro de contenido ~384x224 px (margen ~8px = 1mm por lado). Verificado en
`label-renderer.test.ts`.

## Renderer

Determinista y 100% testeable en Node (sin Canvas/Skia/dependencia nativa):
un bitmap en memoria (`bitmap-canvas.ts`), una fuente monocromática 5x7 de
autoría propia (`bitmap-font-5x7.ts` -- **no** es una copia de ningún
archivo de fuente de terceros) y una insignia MYC reimplementada a
resolución de impresión (`myc-badge.ts`, ver AGENTS.md: reimplementación
propia inspirada en `frontend/src/assets/myc-logo.svg` como referencia
visual, nunca el asset importado ni compartido entre apps).

Ajuste de texto: escala común calculada por línea para que las 5 líneas
quepan en el área segura; si un valor (CODIGO/O.T./INFORME) no cabe ni a la
escala mínima, se trunca visiblemente con un marcador `>` al final -- nunca
se recorta en silencio, y nunca se trunca la etiqueta (el nombre del campo),
sólo el valor.

## Estado de soporte

| Impresora | `PrinterAdapterId` | `supportStatus` | Notas |
|---|---|---|---|
| NIIMBOT B1 | `niimbot-b1` | `supported` | Protocolo implementado y probado con dobles de prueba (ver abajo). Validación física previa reportada por el usuario; esta ronda no repite ni certifica la matriz física completa. |
| NELKO PM220 | `nelko-pm220` | `protocol_pending` | Sin SDK/protocolo BLE público confiable. `connect()`/`print()` rechazan explícitamente (`NelkoProtocolPendingError`) -- nunca reutilizan comandos NIIMBOT ni inventan un protocolo. |
| Cualquier otro BLE | -- | (no clasificado) | `PrinterRegistry.classifyDevice` lo reporta `unknown`; la UI nunca lo ofrece como impresora. |

### Diagnóstico NELKO

`adapters/nelko-pm220/nelko-diagnostics.ts` conecta, lee lo que el
dispositivo ya anuncia/expone (nombre, datos de fabricante, servicios,
características y sus propiedades vía `BleTransport.inspect`) y se
desconecta -- **nunca envía un comando propio del protocolo**. Uso exclusivo
de desarrollo durante QA física para caracterizar el PM220 real y poder
construir `NelkoPm220Adapter` con evidencia, no con suposiciones. Conservado como herramienta técnica, sin exposición en el Centro de etiquetado.

## Protocolo NIIMBOT B1 (`adapters/niimbot-b1/protocol.ts`)

Ningún comando se inventó: cada uno se cruzó contra 3 implementaciones
open-source independientes y activamente mantenidas antes de escribirse --
ver el bloque "AUDITORÍA DE FUENTES" al inicio de `protocol.ts` para las
URLs exactas y qué confirmó cada una (niim.blue/niimblue wiki, niimprint
-Python, probado en B1 real-, niimbluelib -TypeScript-). Framing:
`55 55 [cmd] [len] [data...] [checksum] AA AA`, `checksum = cmd XOR len XOR
datos` -- confirmado byte a byte contra un vector documentado
(`encodeNiimbotPacket(Connect)` produce exactamente `55 55 C1 01 01 C1 AA
AA`, ver `protocol.test.ts`).

El detalle vigente de paquetes y sondeo de estado es el implementado en
`protocol.ts` y `niimbot-b1-adapter.ts` de HEAD `f23e657`. Las notas anteriores
sobre divergencias de header y aceptación de cualquier respuesta B3 quedaron
superadas por ese HEAD. Esta ronda conserva íntegramente esa implementación.

`NiimbotFrameAssembler` reensambla notificaciones BLE fragmentadas
(confirmado como riesgo real por la propia wiki de NIIMBOT: "Fragmentation
Warning") y descarta basura/frames corruptos sin perder el resto del stream.

El handshake de identificación posterior a `Connect` (`PrinterStatusData` +
consultas `PrinterInfo`) es **best-effort**: informativo/diagnóstico, nunca
bloquea la conexión si la impresora no responde a tiempo -- 203 dpi y 384px
de ancho imprimible son las especificaciones públicas conocidas del B1, no
se negocian en tiempo real en v1.

### Mapeo 50x30 físico -> raster imprimible del B1 (corrección 2026-09-08)

`MYC_50X30` a 203 dpi produce un raster físico de **400x240 px** (ver
"Perfil físico y DPI" arriba) -- pero el cabezal del B1 sólo puede imprimir
**384 px por fila** (`NiimbotB1Adapter.capabilities.printableWidthPx`).
Enviar el raster de 400px tal cual (como hacía la versión anterior de este
archivo) habría producido un `SetPageSize`/filas con dimensiones inválidas
para el cabezal real -- corregido.

**Por qué WIDTH es el eje limitado por el cabezal, nunca HEIGHT** (evidencia
de las fuentes ya auditadas en `protocol.ts`, no una suposición): cada fila
transmitida vía `PrintBitmapRow` lleva un índice de fila (0..heightPx-1, uno
por avance de papel) y una tira de `ceil(widthPx/8)` bytes -- confirmado en
niimprint (`_encode_image`: itera `range(img.height)` filas, cada una con
`ceil(img.width/8)` bytes). El cabezal físico es una fila FIJA de puntos
térmicos perpendicular al avance del papel: ese número fijo de puntos
(384) es exactamente lo que limita `widthPx` (píxeles por fila); `heightPx`
(cuántas filas se mandan) no tiene límite de cabezal, sólo de largo de
página/rollo. `MYC_50X30.physicalWidthMm` (50mm) es por lo tanto el eje que
debe caber en el cabezal.

`printers/raster-adapt.ts` (`cropRasterToPrintableWidth`) recorta el raster
físico completo (400px) al ancho real del cabezal (384px) **quitando
únicamente el margen físico que `LabelRenderer` ya deja vacío** alrededor
del área segura -- 400-384=16px, exactamente los 8px por lado (~1mm) que
`profileSafeAreaPx` ya calcula. Esto no es una coincidencia asumida a
ciegas: la función verifica bit a bit que las columnas que va a recortar
estén realmente vacías antes de recortarlas; si hubiera tinta ahí (un
perfil/impresora futuros donde el margen no alcance), bloquea con
`RasterExceedsPrintableWidthError` en vez de recortar contenido real en
silencio. Nunca escala ni distorsiona -- sólo recorta margen físico vacío.
`heightPx` (eje de avance, sin límite de cabezal) nunca se toca.
`NiimbotB1Adapter.print()` aplica este recorte antes de construir
`SetPageSize`/las filas -- ver `raster-adapt.test.ts` y
`niimbot-b1-adapter.test.ts` para la prueba end-to-end de que el ancho
realmente enviado es 384, nunca 400.

## Decisión de librería BLE

**`react-native-ble-manager@^12.5.2`** (Apache-2.0). Se investigó también
`react-native-ble-plx`, descartada: la oficial (`dotintent`) no tiene
`codegenConfig` (sin migrar a TurboModules/Fabric) y tiene reportes
abiertos de crashes con New Architecture habilitada en RN 0.76+ (issue
#1277); `react-native-ble-manager@12.x` declara explícitamente "RN 0.76+
only the new architecture is supported", trae `codegenConfig`, se construye
contra RN 0.82 (por delante de los 0.81.5 de este proyecto), soporta
iOS 15.1+/Android API23+, y ya implementa chunking/pacing de escritura
(`writeWithoutResponse(..., maxByteSize=20, queueSleepTime=10)`) que
coincide exactamente con el "~10ms" de espaciado que las referencias NIIMBOT
piden para no perder filas por escribir demasiado rápido -- no hubo que
reinventar esa lógica.

Trae su propio plugin de Expo (`react-native-ble-manager/plugin`), registrado
en `app.json` con `neverForLocation: true` (MYC nunca usa BLE para inferir
ubicación, sólo para conectar a una impresora conocida por nombre) e
`isBleRequired: false` (BLE es opcional, la app sigue siendo usable sin
impresora configurada). El plugin declara `NSBluetoothAlwaysUsageDescription`
en iOS y `BLUETOOTH`/`BLUETOOTH_ADMIN`/`BLUETOOTH_SCAN`/`BLUETOOTH_CONNECT`
(+ ubicación sólo hasta SDK 30) en Android -- nunca se editó `Info.plist`/
`AndroidManifest.xml` a mano: este proyecto es managed/CNG (no hay `ios/`/
`android/` versionados), así que un plugin de Expo es el único mecanismo
correcto.

## Permisos

**No se creó ningún permiso backend nuevo** (`lab_labels.print`,
`lab_labels.configure_printer`, etc.). La configuración de impresora es
configuración local del dispositivo (qué impresora física está emparejada
en este teléfono/tablet) -- no un recurso de negocio LAB, mismo criterio ya
usado por otras preferencias puramente locales de la app. La pantalla de
configuración y el botón de impresión reutilizan `canCaptureFieldSheets`
(la misma autoridad que ya gatea la captura de hojas de campo), nunca
`role === 'admin'` ni un atajo de nombre de rol.

## Auditoría de impresión

No se agregó ningún modelo/migración backend para historial de impresión en
esta fase -- no hay evidencia de que el negocio necesite auditar impresiones
de etiquetas hoy, y `docs/architecture/` no tiene ningún precedente de
requerirlo. Si se decide que sí hace falta, un diseño mínimo razonable sería
`{work_order_id, equipment_id, user_id, printer_family, printer_model,
copies, timestamp, result}` -- sin payloads BLE crudos -- pero eso queda
como recomendación separada, no implementado aquí.

## Gate de QA física (obligatorio antes de "listo para producción")

Nada de lo anterior prueba soporte real de impresora. Antes de reportar
NIIMBOT B1 "production ready" debe pasar, con hardware físico real:
descubrimiento en iPhone y Android, conexión, reconexión, medio físico
50x30 sin recorte/mal centrado, insignia MYC y los 5 campos legibles y
completos, 1/5/20 impresiones consecutivas, recuperación tras apagar/prender
la impresora, comportamiento con Bluetooth apagado/permiso denegado/fuera de
rango, recuperación background/foreground. NELKO PM220 no se reporta
soportado hasta tener protocolo confiable + su propia matriz de QA física
equivalente.

### Antecedente físico 2026-09-08

La primera prueba accionó el B1 sin contenido visible. Esa observación motivó
herramientas comparativas y el trabajo de protocolo previo a `f23e657`.
El usuario reporta impresión física validada antes de la ronda UX 2026-09-09;
no se mantiene como pendiente actual repetir los botones QA de aquella etapa.
`qa-row-header-variant.ts`, su test, `protocol.test.ts`,
`niimbot-b1-adapter.test.ts`, `printPacketSequenceForQa()` y
`printerManager.printQaPacketSequence()` permanecen intactos. La retirada de
sus controles visuales no elimina infraestructura técnica.
