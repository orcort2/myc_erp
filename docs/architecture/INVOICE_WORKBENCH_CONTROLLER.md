> Estado: VIGENTE
>
> Tipo: Arquitectura vigente
>
> Autoridad: Alta para composición y reutilización del Workbench de Facturación
>
> Prevalece sobre: implementaciones que vuelvan a concentrar el flujo en una página o creen controladores paralelos
>
> Corte verificado: 2026-07-22

# Controlador reutilizable del Workbench de Facturación

## Propósito

`useInvoiceWorkbenchController` es el único controlador frontend del expediente de Facturación. Centraliza carga, apertura, borrador, actualización, emisión, descargas, refresco, errores y estados de carga sobre el agregado backend `Invoice` existente.

`BillingPage.jsx` conserva únicamente la composición del Centro de Facturación: filtros, métricas, tabla, dashboard, configuración y montaje de `InvoiceWorkbenchDialog`. Otros módulos deben consumir el mismo controlador; no deben copiar sus llamadas API, payload de borrador ni transición de emisión.

## Contrato público

El controlador vive en `frontend/src/components/invoice-workbench/useInvoiceWorkbenchController.js` y expone:

- carga global opcional mediante `loadOverview`;
- apertura desde una fila ya resuelta con `openWorkspace`;
- apertura explícita con `openWorkspaceByContext`;
- contexto por `invoice_id` o `service_order_id`;
- creación/actualización con `saveWorkspaceDraft`;
- emisión con `issueWorkspaceInvoice`;
- descarga de PDF MYC y XML;
- refresco del centro y estado Facturama;
- estado seleccionado, draft, loading, saving, error y aviso;
- catálogos, configuración y mapas necesarios por los componentes actuales.

Con `loadOverview=false`, un consumidor contextual carga sólo configuración, catálogos y las entidades requeridas por `invoice_id`/`service_order_id`. La página global conserva `loadOverview=true` porque su tabla necesita las colecciones completas.

El controlador admite `openInitialContext=false` y expone `contextInvoice`, `contextLoading`, `contextResolved` y `loadContextSummary`. Esta modalidad resuelve el mismo contexto sin abrir todavía el modal y permite presentar un resumen de sólo lectura. `null` en `contextInvoice` no significa “sin factura” hasta que `contextResolved=true`; durante la consulta, `contextLoading=true` impide resolver cualquier presentación provisional. `resolveContextSelection` es la única resolución interna para resumen y Workbench, por lo que ambos recorridos no pueden seleccionar facturas distintas.

## Contexto explícito y navegación

`frontend/src/utils/invoiceWorkbenchContext.js` normaliza y serializa el contexto. Las rutas admitidas son:

```text
/dashboard?invoice_id=123#facturacion
/dashboard?service_order_id=45#facturacion
```

`invoice_id` tiene precedencia si ambos identificadores están presentes. Los valores deben ser enteros positivos. La apertura por factura usa `GET /invoices/{id}`; la apertura por ETS usa `GET /service-orders/{id}` y `GET /invoices?service_order_id={id}`. No se usa `localStorage` para transportar contexto.

## Pestaña Facturación del ETS

`frontend/src/components/ets-billing/EtsBillingTab.jsx` es la composición exclusiva de esta pestaña. Monta el mismo hook con `loadOverview=false` y `openInitialContext=false`, muestra el `Invoice` contextual y abre el mismo `InvoiceWorkbenchDialog` mediante `service_order_id`. Al cerrar el diálogo no navega ni desmonta el expediente: el usuario regresa a la misma pestaña del mismo ETS.

La tarjeta adapta únicamente su presentación:

- sin factura: mensaje y acceso `Crear factura` al flujo existente de borrador;
- borrador u otro estado preparatorio: `Continuar factura`;
- emitida/timbrada y estados administrativos posteriores con CFDI: `Ver factura`, PDF MYC y XML mediante las funciones del controlador;
- cancelada: `Ver detalle`, sin descargas desde la pestaña.

Pagos, cuentas por cobrar, notas de crédito, historial/documentos y liberación financiera sólo aparecen como tarjetas de siguiente fase. La pestaña no contiene llamadas directas a `api.js`, payload fiscal, transición, emisión, descarga ni lógica backend.

La carga contextual usa un bloque estático con altura mínima equivalente al contenido final, sin transición ni animación. La etiqueta de estado, el resumen y sus acciones sólo se montan después de resolver el contexto. `ServiceOrdersPage` conserva montada la pestaña después de su primera apertura y sólo la oculta al alternar carpetas del mismo ETS; así no reinicia la consulta ni reproduce el salto al regresar. Abrir otro ETS reinicia correctamente el contexto.

## Backend

`GET /api/invoices` conserva su respuesta y comportamiento sin parámetros. Acepta opcionalmente `service_order_id` para limitar el mismo listado existente. No se agregó endpoint, modelo, tabla ni máquina de estados.

## Invariantes

- `Invoice` sigue siendo la única fuente de verdad.
- Las reglas de creación, edición, emisión y documentos permanecen en los servicios backend vigentes.
- El controlador no define estados ni transiciones alternativas.
- `InvoiceWorkbenchDialog` sigue siendo el modal productivo compartido.
- No deben recrearse en páginas consumidoras el payload fiscal, la validación del emisor, la descarga ni el refresco.
- Un nuevo consumidor debe abrir por contexto explícito y, si no necesita el Centro completo, usar `loadOverview=false`.
- El resumen contextual debe conservar `contextInvoice` al cerrar el diálogo y actualizarlo con la respuesta de guardar o emitir.
- `contextInvoice=null` sólo puede presentarse como “Sin factura” con `contextResolved=true`; `isLoading` no sustituye este contrato porque también representa dependencias generales del Workbench.

## Validación del Sprint 2A

- Build Vite correcto: 1,664 módulos.
- Pruebas Node: 11 correctas; cubren contexto no resuelto sin presentación, ausencia resuelta, borrador, timbrada, cancelada, navegación contextual y retorno.
- Pruebas backend focalizadas del listado filtrado y documentos: 8 correctas.
- No se modificaron backend, endpoints, reglas, estados, esquema ni datos.
- `InvoiceWorkbenchDialog` continúa siendo la única interfaz productiva de edición y `useInvoiceWorkbenchController` la única ruta frontend de creación, guardado, emisión, refresco y descargas.
- Corrección de estabilidad visual: el render SSR inicial contiene únicamente `ets-billing-tab__loading`, sin “Sin factura”, “Crear factura” ni badge; la auditoría CSS no encontró transiciones heredadas sobre el bloque y la animación de `InvoiceWorkbenchDialog` no fue modificada.

## Validación del Sprint 1

- Build Vite correcto: 1,662 módulos.
- Pruebas Node: 3 correctas para el contrato de contexto y 2 recorridos adicionales correctos de navegación secuencial.
- Apertura contextual compatible con el doble ciclo de efectos de `React.StrictMode`; la cancelación del primer ciclo no impide resolver el contexto en el segundo.
- Pruebas backend de filtro, mapper Facturama y documentos: 10 correctas.
- Suite backend completa: 102 correctas y 2 fallos ajenos al Sprint por cierre `-6` del ejecutable LibreOffice en las dos pruebas de conversión real; las pruebas de Facturación permanecen correctas.
- Sin migración ni modificación de datos.
- Permanece la advertencia conocida por tamaño del chunk principal; no fue introducida como cambio funcional de este sprint.
