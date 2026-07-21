> Estado: VIGENTE
>
> Tipo: Arquitectura vigente
>
> Autoridad: Alta para composición y reutilización del Workbench de Facturación
>
> Prevalece sobre: implementaciones que vuelvan a concentrar el flujo en una página o creen controladores paralelos
>
> Corte verificado: 2026-07-21

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

Con `loadOverview=false`, un futuro consumidor contextual carga sólo configuración, catálogos y las entidades requeridas por `invoice_id`/`service_order_id`. La página global conserva `loadOverview=true` porque su tabla necesita las colecciones completas.

## Contexto explícito y navegación

`frontend/src/utils/invoiceWorkbenchContext.js` normaliza y serializa el contexto. Las rutas admitidas son:

```text
/dashboard?invoice_id=123#facturacion
/dashboard?service_order_id=45#facturacion
```

`invoice_id` tiene precedencia si ambos identificadores están presentes. Los valores deben ser enteros positivos. La apertura por factura usa `GET /invoices/{id}`; la apertura por ETS usa `GET /service-orders/{id}` y `GET /invoices?service_order_id={id}`. No se usa `localStorage` para transportar contexto.

El botón histórico del ETS conserva su navegación al Centro de Facturación mediante este contrato; esto no implementa la futura pestaña contextual del ETS.

## Backend

`GET /api/invoices` conserva su respuesta y comportamiento sin parámetros. Acepta opcionalmente `service_order_id` para limitar el mismo listado existente. No se agregó endpoint, modelo, tabla ni máquina de estados.

## Invariantes

- `Invoice` sigue siendo la única fuente de verdad.
- Las reglas de creación, edición, emisión y documentos permanecen en los servicios backend vigentes.
- El controlador no define estados ni transiciones alternativas.
- `InvoiceWorkbenchDialog` sigue siendo el modal productivo compartido.
- No deben recrearse en páginas consumidoras el payload fiscal, la validación del emisor, la descarga ni el refresco.
- Un nuevo consumidor debe abrir por contexto explícito y, si no necesita el Centro completo, usar `loadOverview=false`.

## Validación del Sprint 1

- Build Vite correcto: 1,662 módulos.
- Pruebas Node: 3 correctas para el contrato de contexto y 2 recorridos adicionales correctos de navegación secuencial.
- Apertura contextual compatible con el doble ciclo de efectos de `React.StrictMode`; la cancelación del primer ciclo no impide resolver el contexto en el segundo.
- Pruebas backend de filtro, mapper Facturama y documentos: 10 correctas.
- Suite backend completa: 102 correctas y 2 fallos ajenos al Sprint por cierre `-6` del ejecutable LibreOffice en las dos pruebas de conversión real; las pruebas de Facturación permanecen correctas.
- Sin migración ni modificación de datos.
- Permanece la advertencia conocida por tamaño del chunk principal; no fue introducida como cambio funcional de este sprint.
