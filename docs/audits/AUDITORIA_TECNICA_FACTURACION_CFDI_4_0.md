> Estado: AUDITORÍA
>
> Tipo: Auditoría
>
> Autoridad: Baja; fotografía previa al flujo real de Facturama, XML y PDF MYC
>
> Prevalece sobre: ninguno
>
> Reemplazado por: `AUDITORIA_INTEGRAL_AVANCE_ERP_MYC_2026-07-21.md` y `../project/PROJECT_STATUS.md`

SUPERADO: corresponde al estado anterior a la integración Facturama.

# Auditoría técnica del módulo de facturación — ERP MYC

Fecha de revisión: 2026-07-14  
Alcance: inspección estática del repositorio. No se modificaron modelos, schemas, rutas, migraciones, frontend, datos ni se realizaron llamadas externas.

## Dictamen ejecutivo

El ERP ya cuenta con un módulo **administrativo de facturas, cobranza, notas de crédito, PDF interno y configuración básica**. Usa `Decimal`/`Numeric`, tiene relaciones de origen con clientes, cotizaciones, órdenes y certificados, y aplica permisos de servidor para las operaciones existentes.

No es todavía un módulo CFDI 4.0 ni una base apta para timbrar. No hay integración con Facturama/PAC, XML, UUID fiscal, sellos, CSD, estados PAC/SAT, complementos de pago ni cancelación fiscal. El propio PDF lo identifica como “Documento administrativo interno, no CFDI timbrado”.

Conclusión: **reutilizable como antecedente administrativo, pero no debe evolucionarse mediante campos aislados sobre las tablas actuales**. La siguiente etapa debe diseñar una capa fiscal inmutable, con snapshots y trazabilidad PAC/SAT, preservando el módulo actual durante la transición.

## Componentes localizados

| Componente | Estado | Observación |
|---|---|---|
| `Invoice`, `InvoiceItem`, `InvoicePayment`, `CreditNote`, `InvoiceSettings` | Existe | Administrativo; no representa CFDI ni persistencia PAC/SAT. |
| Cliente y constancia fiscal | Parcial | RFC, razón social, régimen, uso CFDI, CP fiscal y archivo de constancia. |
| Catálogo MYC | Parcial | Clave/unidad SAT, precios y una clasificación fiscal simplificada. |
| Cotizaciones | Parcial | Partidas, importes, impuestos simples y snapshots de cotización, sin conversión fiscal. |
| ETS/orden/certificados | Parcial | Se pueden proponer conceptos desde certificados liberados. |
| PDF | Existe | PDF administrativo por WeasyPrint; no XML/PDF CFDI del PAC. |
| Permisos y auditoría | Parcial | RBAC de backend y eventos generales, insuficientes para ciclo fiscal. |
| Facturama/PAC/SAT | Ausente | No se localizaron clientes HTTP, endpoints, variables ni artefactos de integración. |

Archivos principales revisados: `backend/app/models/{invoice,client,catalog_item,quotation,service_order}.py`, `backend/app/schemas/{invoice,client,catalog_item,quotation}.py`, `backend/app/services/{invoices,invoice_pdfs,clients,quotations}.py`, `backend/app/routers/invoices.py`, migraciones y `frontend/src/pages/BillingPage.jsx`.

## Hallazgos críticos y altos

1. **[Crítico] No existe representación CFDI/PAC.** Faltan tipo de comprobante, UUID fiscal, fecha de timbrado, lugar de expedición fiscal, exportación, tipo de cambio de factura, XML/PDF/acuse, request/response PAC, códigos de error, estado PAC/SAT, última sincronización, cancelación SAT y CFDI relacionados.

2. **[Crítico] No hay snapshot fiscal del receptor.** `Invoice` conserva `fiscal_client_id`, pero consulta la entidad `Client` viva. Cambiar RFC, razón social, régimen o CP del cliente modifica retrospectivamente lo que muestra el PDF y lo que se usaría al timbrar. El cliente tampoco guarda fecha, usuario ni estado de validación fiscal.

3. **[Crítico] Impuestos no son modelables a nivel CFDI.** Cada partida sólo tiene `tax_rate` y un total calculado. Faltan `ObjetoImp` SAT, tipo traslado/retención, impuesto, tipo factor, tasa/cuota, base, importe y múltiples impuestos por concepto. Será necesaria una entidad equivalente a `InvoiceItemTax`.

4. **[Crítico] `InvoicePayment` es cobranza administrativa, no complemento de pago.** No guarda moneda/tipo de cambio del pago, saldo anterior/insoluto por documento relacionado, número de parcialidad, cuentas ordenante/beneficiaria desagregadas, UUID/XML/PDF de complemento ni estado PAC/SAT.

5. **[Alto] Las facturas “issued” siguen editables.** La protección de conceptos sólo bloquea `paid` y `cancelled`; un documento emitido puede cambiar receptor, moneda, condiciones y partidas. Antes de timbrar se requiere inmutabilidad por transición y una versión/snapshot fiscal.

6. **[Alto] El folio administrativo no es seguro para folio fiscal concurrente.** `next_sequence` se incrementa sin bloqueo/transacción de secuencia y el folio es globalmente único. No hay política por serie/sucursal/entorno ni reserva/confirmación tras timbrado.

7. **[Alto] La clasificación `iva_16`, `iva_0`, `exempt`, `not_subject` mezcla tratamiento y ObjetoImp.** Esos valores aparecen como `tax_object` en catálogo y cotización, pero no equivalen directamente a las claves CFDI de ObjetoImp; tampoco distinguen exento de no objeto mediante la estructura requerida.

8. **[Alto] El frontend convierte importes a `Number`.** La persistencia usa `Numeric` y schemas `Decimal`, lo cual es positivo, pero el tránsito JSON desde `Number` puede introducir precisión binaria. La futura captura fiscal debe transportar cadenas decimales y centralizar redondeos conforme CFDI.

## Revisión por dominio

### Emisor

`InvoiceSettings` incluye serie, secuencia, moneda y catálogos JSON; `emitter_data` admite libremente nombre, RFC, régimen, CP, dirección, correo, teléfono y lugar de expedición. `InstitutionalConfiguration` tiene nombre legal, dirección, correo y logo.

Es reutilizable únicamente como configuración administrativa. Faltan una entidad/versionado formal de perfil fiscal de emisor y: sucursal, política de folios, ambiente sandbox/producción, CSD/serie/fecha de vencimiento/estado, referencia segura de credenciales, forma/método/uso/exportación predeterminados y controles de vigencia. Los JSON sin estructura/versionado no deben ser la fuente maestra de catálogos fiscales.

### Receptor / cliente

Existe separación de razón social (`legal_name`) y nombre comercial, RFC, régimen, uso CFDI, correo, contactos, domicilio, país, CP general y `fiscal_postal_code`; puede adjuntarse una constancia y extraerse texto de ella.

Pendiente: validación real de RFC y de combinaciones SAT régimen/uso; asegurar que régimen y uso sean claves vigentes (son texto libre); correo/contacto específicamente de facturación; residencia fiscal, registro tributario extranjero, indicador extranjero; estado/fecha/usuario de validación. Los campos se pueden actualizar aun si existen facturas relacionadas y no hay congelamiento histórico.

### Cotizaciones, ETS y origen

La cotización contiene cliente, asesor, fechas, condiciones, notas, subtotal/impuestos/total y partidas con clave/unidad SAT, precio, descuento porcentual, moneda, clasificación e impuesto simple. También tiene `QuotationSnapshot`, útil como precedente de versionado.

La relación `Invoice.quotation_id` existe, pero no hay servicio ni UI que convierta una cotización en borrador: elegir la cotización sólo almacena la FK. Las partidas no se copian automáticamente ni se toma un snapshot fiscal del cliente/cotización. Las cotizaciones siguen siendo editables; no hay saldo por facturar, facturación parcial ni control de una/múltiples facturas por cotización. Desde ETS, la UI propone renglones desde certificados liberados, con clave/unidad SAT predeterminadas y precio `0.00`; no toma el catálogo ni la cotización como fuente fiscal.

### Catálogo MYC

Almacena clave interna, nombre/descripcion comercial, clave y unidad SAT, unidad interna, precios/costos, moneda/tipo de cambio de costo y tasa. No hay descripción fiscal separada, vigencia/historial, retenciones, IEPS, impuestos locales, tipo factor ni tasas múltiples.

`tax_object` usa valores internos (`iva_16`, `iva_0`, `exempt`, `not_subject`) y el servicio fuerza una tasa a partir de ellos. Esto es una simplificación administrativa, no el catálogo `c_ObjetoImp`; debe separarse en la futura capa fiscal para evitar mapeos incorrectos.

### Factura y partidas

La factura ya conserva importes en `Numeric(12,2)`/`Decimal`, descuento, retención total, moneda, forma/método de pago, uso CFDI, cliente, cotización, orden, creador y actualizador. Las partidas guardan una copia de descripción, cantidad, unidad, clave/unidad SAT, precio, descuento, tasa y enlace a partida de cotización/certificado/equipo: esto sí es una buena base de snapshot comercial por concepto.

Falta, entre otros: tipo de comprobante, fecha-hora y zona de emisión, fecha de timbrado, serie/folio fiscal separado del administrativo, UUID, tipo de cambio de factura, exportación, condiciones completas, receptor y emisor serializados, objeto de impuesto, base gravable explícita, total por concepto, número de identificación, relación/fuente completa y almacenamiento de XML/PDF/acuse/PAC.

No se detectaron columnas `float` en los importes almacenados: se usa `Numeric`/`Decimal`. Riesgo moderado: `_money` acepta `float` y la UI envía números JavaScript.

### Impuestos

El cálculo actual es únicamente `base = cantidad × precio − descuento`, IVA/tasa simple y total de línea. `withholding_total` existe sólo como total de cabecera y no se calcula ni desglosa. No existen IVA retenido, ISR, IEPS, locales, cuota, factor, traslados/retenciones ni múltiples impuestos por partida. Este cálculo no debe reutilizarse como motor CFDI salvo como punto de partida aislado y reescrito con precisión/validaciones fiscales.

### Pagos, PPD y notas de crédito

Pagos: fecha, importe, banco/cuenta/referencia, forma/método, estatus y usuario. Se calcula saldo de factura y se bloquea pago superior al saldo. No distingue fiscalmente PUE/PPD ni soporta el complemento.

Notas de crédito: sólo folio administrativo, razón, totales y estados `draft/applied/cancelled`; no hay CFDI de egreso, UUID relacionado, tipo de relación, sustitución, devolución/bonificación estructurada ni XML/PAC. La nota puede afectar el saldo administrativo, pero no equivale a una nota de crédito fiscal.

### Catálogos SAT

Se encontraron listas JSON configurables y valores por defecto muy reducidos para forma/método de pago, uso CFDI, régimen, moneda, claves producto/servicio y unidades. El frontend permite texto libre para forma, método y uso CFDI. No hay tablas locales normalizadas, fuente/importador SAT, fecha de actualización, vigencia ni los catálogos restantes: país, CP, objeto de impuesto, factor, impuestos, exportación, tipo de relación y motivos de cancelación.

## Estados y transiciones

Estados administrativos existentes de factura: `draft`, `pending`, `issued`, `paid`, `partially_paid`, `overdue`, `cancelled`, `credit_note`. Pagos: `pending`, `partial`, `settled`, `refunded`, `cancelled`. Nota: `draft`, `applied`, `cancelled`.

La propuesta fiscal exige `draft`, `ready_to_stamp`, `stamping`, `stamped`, `stamp_error`, `payment_pending`, `partially_paid`, `paid`, `cancellation_pending`, `cancelled`, `substituted`.

Faltan todos los estados de PAC/timbrado y sustitución; `issued` es ambiguo (hoy significa emitida administrativa, no timbrada), `pending` no indica qué espera, `overdue` es cobranza y no estado fiscal, y `credit_note` no debe reemplazar el estado del CFDI origen. Los estados de pago se mezclan con los de documento en el recálculo. Deben bloquearse edición, nuevos pagos administrativos y cancelación directa según el estado fiscal/resultado PAC; la transición a cancelado deberá ser un proceso asíncrono y no una mutación local.

## Rutas, permisos y frontend

El backend protege lectura con `invoices.read`/`payments.read` y creación, edición, cambios de estatus, notas y configuración con `invoices.manage`; pagos usa `payments.manage`. El rol `Finanzas` tiene estos cuatro permisos y `Administrador` acceso total. No existen permisos específicos para timbrar, cancelar ante SAT, descargar XML, ver errores PAC, complementar pagos, notas de crédito fiscales o administrar configuración fiscal. `Desarrollador` no tiene permisos de facturación explícitos.

La UI muestra creación, emisión administrativa, pagos, notas, PDF interno y configuración. La autorización efectiva es del backend; no se encontró una matriz de capacidades de facturación aplicada en el frontend. La separación futura recomendada incluye al menos: `billing.drafts.*`, `billing.stamp`, `billing.cancel`, `billing.xml.read`, `billing.pdf.read`, `billing.pac_errors.read`, `payment_complements.*` y `fiscal_settings.manage`.

## Auditoría y seguridad

`AuditLog` puede registrar actor, acción, entidad, antes/después JSON, comentario y fecha. Ya se registran creación/edición de factura, cambio de estatus, pago y nota. No cubre con suficiente detalle importación desde fuente, snapshot fiscal, cambios por partida/impuesto, request/response PAC (redactado), intento/resultado de timbrado, descarga de XML/PDF, cancelación/acuse/sustitución ni complemento de pago.

La búsqueda global no encontró integración Facturama/PAC/SAT, certificados `.cer/.key/.pfx/.pem` ni variables PAC/SAT. Riesgo observado: `backend/app/core/config.py` y `.env.example` mantienen una clave JWT por defecto de desarrollo; si se despliega sin sobreescribirla, compromete autenticación. Debe exigirse una variable de entorno/secret manager en producción. También hay respaldos SQL dentro del workspace: deben tratarse como información sensible y mantenerse fuera de repositorios/distribución pública. No se exponen valores de secretos en este reporte.

## Diseño técnico preliminar para la siguiente fase

1. Mantener el módulo actual como administrativo o definir una migración de compatibilidad explícita; no etiquetar sus PDFs/folios como CFDI.
2. Diseñar un agregado fiscal independiente: borrador y partidas fiscales inmutables, snapshot de emisor/receptor/origen, impuestos por partida, relaciones CFDI y archivos/bitácora PAC.
3. Separar estado documental fiscal de cobranza. Usar una máquina de estados con transiciones auditables, idempotencia y bloqueo de edición desde `ready_to_stamp`.
4. Normalizar o versionar catálogos SAT y reglas de vigencia; validar claves y combinaciones antes de `ready_to_stamp`.
5. Diseñar `InvoiceItemTax` (o equivalente) para cada traslado/retención y un modelo de aplicaciones de pago para complemento PPD.
6. Crear perfiles fiscales de emisor/sucursal con referencias cifradas a certificados/credenciales; nunca guardar secretos PAC/CSD en JSON de configuración ni enviarlos al frontend.
7. Definir adaptador Facturama desacoplado, outbox/idempotency key, almacenamiento de request/response saneado y reintentos controlados. Esto queda fuera de esta auditoría.

## Priorización recomendada

| Prioridad | Entregable posterior |
|---|---|
| P0 | Modelo fiscal/snapshots, impuestos por partida, máquina de estados y permisos finos. |
| P0 | Emisor/receptor fiscal validable y catálogos SAT versionados. |
| P1 | Borradores desde cotización, ETS, cliente y manual con trazabilidad de origen. |
| P1 | Complementos PPD, CFDI relacionados/egreso y cancelación/sustitución. |
| P2 | Adaptador Facturama, XML/PDF/acuse, consultas PAC/SAT y observabilidad. |

## Evidencia relevante

- Modelo administrativo y campos actuales: `backend/app/models/invoice.py`.
- Cálculo y transiciones administrativas: `backend/app/services/invoices.py`.
- PDF interno: `backend/app/services/invoice_pdfs.py` y `backend/app/templates/invoice_pdf.html`.
- Flujo desde ETS y conversión de importes a `Number`: `frontend/src/pages/BillingPage.jsx`.
- Simplificación de impuesto en catálogo: `backend/app/schemas/catalog_item.py` y `frontend/src/constants/catalog.js`.
- Permisos: `backend/app/core/permissions.py`; rutas protegidas: `backend/app/routers/invoices.py`.
- Migración que creó el módulo: `backend/migrations/versions/0f1e2d3c4b5a_create_invoicing_module.py`.
