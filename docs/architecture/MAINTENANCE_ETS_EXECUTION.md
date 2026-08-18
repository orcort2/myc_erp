# ETS Mantenimiento — contrato vigente

Estado: **TERMINADO — EN REVISIÓN**.

## Autoridades y nacimiento

Una partida aprobada con `operational_category=maintenance` materializa, al crear el ETS, una `ServiceUnit` no evolutiva, una `ServiceStage(category=maintenance)` y un `MaintenanceExecution` por equipo. Conserva la `ServiceOrder`, la OT institucional y el `ServiceOrderItem` de origen. No existe inferencia por nombre ni motor paralelo.

El catálogo configura exactamente un `maintenance_type` (`preventive` o `corrective`), una modalidad (`laboratory` o `field`) y, sólo para correctivo, materiales base. La cotización congela estos valores en `maintenance_configuration_snapshot`; la ejecución copia ese snapshot y no consulta posteriormente el catálogo. Los snapshots históricos anteriores conservan su contenido y se materializan con el adaptador explícito `legacy_structured_default` preventivo/laboratorio, sin reescribir la cotización.

## Modalidades y lifecycle

- Laboratorio: `pending_arrival → pending_assignment → assigned → in_maintenance`.
- Campo: nace `pending_assignment`, requiere equipo vinculado, dirección, solicitud al técnico, aceptación y programación antes de `in_maintenance`; no registra arribo ni custodia MYC.
- Ambas modalidades: `in_maintenance ↔ paused → technically_completed → pending_release → closed`.

La OT no distingue laboratorio/campo. Una refacción pendiente conserva custodia MYC sólo en laboratorio; en campo el expediente indica que el equipo permanece con el cliente.

Las pausas son entidades trazables y tipadas: refacción, autorización, segunda intervención, revisión comercial e investigación administrativa. Registran motivo, responsable, fecha tentativa, resolución, actor y timestamps.

## Captura y materiales

`MaintenanceExecution` conserva cuatro bloques estructurados:

1. Antes: condición inicial, descripción, hallazgos, severidad, clasificación y evidencias.
2. Intervención: acción, componente, resultado, materiales y evidencias.
3. Después: condición final, resultado funcional, conclusión y evidencias.
4. Futuro: recomendaciones y decisión aceptada, rechazada o pendiente.

`MaintenanceMaterial` diferencia `used` de `required`. Puede conservar costo unitario interno, pero el tablero y el PDF público no lo exponen. El contrato deja `source` y campos de cantidad/unidad preparados para integrar existencias, compras, ubicaciones, lotes/series y escaneo sin obligar a serializar todo consumible.

## Cambios de alcance e investigación

Un preventivo que descubre correctivo crea `MaintenanceChangeRequest`; no muta silenciosamente. La aprobación exige una `QuotationItem` aprobada cuyo `source_service_order_id`, `source_service_unit_id` y `source_stage_id` coincidan exactamente. Un override requiere permiso administrativo, justificación y auditoría. El rechazo conserva la recomendación, permite terminar el preventivo original y exige firma sobre el reporte vigente.

Reparación nunca se ejecuta dentro del Mantenimiento. Sólo se documenta y se vincula posteriormente a un ETS independiente. Un equipo inoperable crea una pausa administrativa e investigación bloqueante; puede vincular una etapa diagnóstica/Servicio General, pero no puede cerrar hasta resolución administrativa.

## Reporte, firma y cierre

El PDF se fabrica desde la captura estructurada: equipo, OT, tipo/modalidad, condición inicial, hallazgos, acciones, materiales relevantes, condición final, recomendaciones, técnico, fechas, firmante y decisión. Omite bitácora interna y costos. Todo texto dinámico se escapa antes de WeasyPrint.

La terminación técnica no cierra. Cada generación incrementa `report_version`; la firma queda unida a `signed_report_version`. Sólo puede cerrar la unidad cuando la versión vigente está firmada y no existen pausas, autorizaciones, investigación, captura o reporte pendientes.

## Bloqueantes y permisos

El backend devuelve bloqueantes con `severity`, `message`, `section`, `field` y `execution_id`. El frontend presenta un banner persistente y cada bloqueante navega/enfoca la sección responsable. Se diferencian las capacidades:

- `service_orders.maintenance.manage`;
- `service_orders.maintenance.execute`;
- `service_orders.maintenance.authorize`;
- `service_orders.maintenance.sign`;
- `service_orders.maintenance.close`.

El backend y no la interfaz es autoridad de ownership, transición, aprobación y cierre.

## Compatibilidad y pendiente de aceptación

Calibración, Venta, Servicio General evolutivo, servicios compuestos, ETS múltiples, OT y propuesta de Hojas de Campo no cambian. Mantenimiento + Calibración conserva partidas, unidades, etapas y entregables independientes.

Pendiente para aceptación: recorrido autenticado en navegador, campo en dispositivo físico, almacenamiento institucional real de fotografías/firma y validación con usuarios operativos. No se implementaron mapas/tracking, Compras, Almacén ni Reparación.
