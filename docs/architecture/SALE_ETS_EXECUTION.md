> Estado: VIGENTE · EN REVISIÓN
>
> Corte verificable: 2026-08-18

# ETS Venta

## Autoridad y frontera

Venta usa el motor ETS vigente. `ServiceOrder` conserva el expediente; `ServiceOrderItem` conserva la partida operativa; cada pieza serializada usa una `ServiceUnit`; y `ServiceStage` mantiene el recorrido append-only. Las tablas `sale_*` son una proyección específica de arribos y entregas, no un segundo motor ETS.

Este contrato no implementa workflows de Mantenimiento, Reparación, Validación, Calificación, Capacitación o Consultoría. Tampoco cambia la propuesta/selección de Hojas de Campo.

La propuesta vigente permanece en
`frontend/src/utils/fieldSheetTemplateResolver.js`, consumida por
`ServiceOrdersPage.jsx`; la persistencia/validación posterior sigue en
`backend/app/services/field_sheets.py`. `service_execution.py` no selecciona
plantillas.

## Causa corregida

Venta sólo estaba representada por la partida comercial y el ETS genérico: no
existía un agregado persistente para distinguir unidades físicas, saldos por
cantidad, arribos, garantías ni entregas parciales. Intentar derivarlo del
catálogo vigente habría roto la autoridad histórica del snapshot y tratar una
unidad vendida con calibración como dos equipos habría duplicado identidad y
certificados.

## Configuración y snapshot

Un concepto de catálogo con identidad `sale` puede definir:

- `requires_individual_identification`;
- marca, modelo y especificación cotizados;
- `included_calibration_catalog_item_id`, que debe apuntar a un servicio activo con identidad `calibration`.

`quotations.py` congela estos valores en `sale_configuration_snapshot`, incluyendo el snapshot completo de la calibración incluida. Al crear o reconstruir un ETS, `SaleOrderItem.frozen_configuration` se materializa sólo desde `ServiceOrderItem.service_snapshot`; el catálogo vigente no se consulta para reinterpretar la Venta histórica.

## Nacimiento y granularidad

Al aprobar una cotización con al menos una partida `sale` se crea idempotentemente un ETS. La acción manual histórica de “Generar orden” devuelve el mismo ETS y no duplica el expediente.

- Venta serializada: cantidad N crea N `ServiceUnit`, N etapas iniciales `sale/planned` y N `SaleUnitState` en `pending_arrival`.
- Venta no serializada: conserva saldo por cantidad en `SaleOrderItem`; no obliga a crear Equipos.
- Una individualización excepcional sólo se permite antes del primer movimiento y consume una `SaleAuthorization` administrativa.

La proyección automática sin movimientos se considera derivada y reconstruible. Cualquier arribo, autorización o entrega bloquea la reconstrucción física controlada del ETS.

## Arribo

Sólo el asesor asignado —o una autoridad administrativa— registra arribos. El alta compara marca, modelo y especificación con el snapshot. Una discrepancia persiste `commercial_review` y bloquea el alta hasta consumir una autorización de sustitución; nunca modifica el catálogo histórico.

Una unidad serializada crea un único `Equipment` y enlaza ese mismo ID a `ServiceUnit` y `SaleUnitState`. La serie puede marcarse desconocida. Una partida no serializada incrementa `arrived_quantity` sin crear equipos.

## Calibración

Una calibración incluida agrega una etapa `calibration/authorized` sobre la misma `ServiceUnit`, conserva el mismo `Equipment` y genera el único certificado esperado del componente de Calibración. La Venta pura no genera certificado.

La entrega queda bloqueada mientras esa etapa no termine en `completed`, `not_executable` o `exception_closed`. Una calibración posterior con costo requiere una partida `calibration` aprobada; una de costo cero consume autorización administrativa auditada.

## Garantía, entrega y recepción

`warranty_return` conserva el arribo/equipo y bloquea entrega/cierre. Su resolución formal es administrativa y deja la unidad `resolved` con auditoría.

Las modalidades persistidas son:

- `courier`: guía preparada, envío, confirmación manual de paquetería y firma/evidencia posterior;
- `client_pickup`: nota y notificación en las superficies existentes del portal;
- `myc_technician`: técnico, dirección congelada, solicitud, notificación, aceptación y fecha; MYC Mobile lista, acepta y confirma estas entregas.

No hay mapas, Waze, tracking externo ni Gmail. La nota se genera como PDF institucional básico desde el agregado de entrega.

`SaleDeliveryLine` enlaza una unidad serializada o una cantidad no serializada. La recepción registra persona, fecha, actor, modalidad, firma/evidencia y actualiza únicamente esas líneas; por ello admite entregas parciales.

## Estados y cierre

La operación conserva estado en ETS, partida, unidad y entrega. Los estados de unidad relevantes son `pending_arrival`, `commercial_review`, `arrived`, `calibration_pending`, `ready_for_delivery`, `delivery_prepared`, `warranty_return`, `delivered` y `resolved`.

El cierre exige simultáneamente:

- todas las cantidades entregadas o formalmente resueltas;
- calibraciones obligatorias cerradas;
- ausencia de revisión comercial y garantía abiertas;
- ausencia de entregas abiertas sin firma/evidencia.

El endpoint de cierre revalida estos bloqueantes dentro de la transacción y
completa las partidas Venta. Sólo cierra el `ServiceOrder` cuando no hay
partidas ajenas abiertas; un ETS mixto continúa vigente para los otros flujos.

## Seguridad y auditoría

- `service_orders.sales.manage`: Comercial/Desarrollador; además se verifica asesor asignado.
- `service_orders.sales.deliver`: Técnico/Desarrollador y ownership por técnico asignado.
- `service_orders.sales.authorize`: Administrador por wildcard y Desarrollador explícito.
- Portal: `services.view` más ownership derivado de la membresía; el cliente no envía `client_id`.

Arribos, discrepancias, autorizaciones, garantía, entregas, recepción y cierre escriben `AuditLog`; los eventos/notificaciones reutilizan Activity y `Notification`.

## Compatibilidad y despliegue

La migración `b9d1f3a5c7e9` sigue a `a8c0e2f4b6d8`, agrega configuración Venta,
categoría de etapa `sale` y las tablas `sale_*`. Un ETS histórico abierto sin
proyección conserva su estado al consultarse; el asesor puede inicializarlo
explícita e idempotentemente desde su snapshot. No se aplicó la migración a la
base local compartida durante esta entrega; el respaldo oficial conserva el
head anterior hasta el despliegue controlado.
