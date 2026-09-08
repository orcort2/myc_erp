> Estado: WIP (rama `wip/mobile-label-printers`, no mezclada a `main`)
>
> Tipo: Arquitectura de MYC Mobile
>
> Corte verificado: 2026-09-07
>
> QA física pendiente -- ver "Estado de soporte" y "Gate de QA física" antes
> de considerar esto listo para producción.

# Impresión de etiquetas térmicas LAB (BLE)

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
                                     // null/pendiente -> "PENDIENTE", nunca bloquea
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

| Campo | Si falta | ¿Bloquea impresión? |
|---|---|---|
| `calibrationDate` | `LabelRenderError('missing_calibration_date')` | Sí -- nunca una etiqueta con la fecha en blanco |
| `nextCalibrationDate` | se imprime `N/A` | No |
| `certificateFolio` | se imprime `PENDIENTE` | No -- el flujo "linked" ya permite capturar sin folio resuelto |

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
| NIIMBOT B1 | `niimbot-b1` | `supported` | Protocolo implementado y probado con dobles de prueba (ver abajo). **Sin validar contra hardware físico todavía.** |
| NELKO PM220 | `nelko-pm220` | `protocol_pending` | Sin SDK/protocolo BLE público confiable. `connect()`/`print()` rechazan explícitamente (`NelkoProtocolPendingError`) -- nunca reutilizan comandos NIIMBOT ni inventan un protocolo. |
| Cualquier otro BLE | -- | (no clasificado) | `PrinterRegistry.classifyDevice` lo reporta `unknown`; la UI nunca lo ofrece como impresora. |

### Diagnóstico NELKO

`adapters/nelko-pm220/nelko-diagnostics.ts` conecta, lee lo que el
dispositivo ya anuncia/expone (nombre, datos de fabricante, servicios,
características y sus propiedades vía `BleTransport.inspect`) y se
desconecta -- **nunca envía un comando propio del protocolo**. Uso exclusivo
de desarrollo durante QA física para caracterizar el PM220 real y poder
construir `NelkoPm220Adapter` con evidencia, no con suposiciones. Expuesto en
la pantalla de configuración sólo para `actor_type === 'internal'`.

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

**Divergencia NO resuelta entre fuentes, documentada explícitamente (no
silenciada)**: niim.blue documenta un conteo real de píxeles negros de 16
bits en el header de cada fila; niimprint (la única librería confirmada
contra hardware B1 real) siempre manda ceros ahí y funciona. Se adoptó la
variante de niimprint por ser la única validada contra hardware real --
validar durante QA física.

`NiimbotFrameAssembler` reensambla notificaciones BLE fragmentadas
(confirmado como riesgo real por la propia wiki de NIIMBOT: "Fragmentation
Warning") y descarta basura/frames corruptos sin perder el resto del stream.

El handshake de identificación posterior a `Connect` (`PrinterStatusData` +
consultas `PrinterInfo`) es **best-effort**: informativo/diagnóstico, nunca
bloquea la conexión si la impresora no responde a tiempo -- 203 dpi y 384px
de ancho imprimible son las especificaciones públicas conocidas del B1, no
se negocian en tiempo real en v1.

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
