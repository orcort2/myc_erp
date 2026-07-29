> Estado: CONCLUIDA Y VALIDADA
>
> Tipo: Cierre técnico acotado
>
> Fecha: 2026-07-29

# Integración de pagos en Facturación

## Alcance concluido

El flujo existente de `InvoicePayment` quedó integrado en el Resumen financiero del Workbench único, sin crear pestaña de Pagos, modelos, tablas, migraciones, endpoints, permisos, auditoría ni máquina de estados paralelos.

La factura permite registrar pagos parciales o totales antes y después del timbrado, muestra total, pagado, saldo, estado e historial, y descarga el comprobante PDF existente. El Dashboard vigente muestra Cuentas por cobrar y abre el mismo expediente. El consumidor ETS refresca la compuerta financiera después del pago.

## Defectos corregidos

- Facturama confirmaba siempre `issued` y borraba la condición administrativa `partially_paid` o `paid`; ahora deriva el estado desde `amount_paid` y `balance_due`.
- Backend aceptaba intentar un pago nuevo con saldo cero; ahora lo rechaza expresamente.
- La sesión no exponía permisos efectivos al frontend; `UserRead` los deriva de la matriz canónica para ocultar la acción sin duplicar roles.
- Cuentas por cobrar no devolvía `amount_paid`, aunque el dato ya existía en `Invoice`.

## Validación

- Frontend Node: `13 passed`.
- Build Vite: correcto, `1695` módulos; permanece la advertencia preexistente por chunk mayor a 500 kB.
- Backend focalizado de pagos, facturación, documentos, certificados y readiness: `38 passed`.
- Regresión adicional ETS/servicios/contratos: `16 passed`, `12 subtests passed`.
- La prueba HTTP `test_certificate_release_http.py` no pudo recolectarse por el defecto preexistente `ImportError: app.services.activity.list_messages`, ajeno a esta integración.
- No hubo migración ni cambio de datos; no corresponde regenerar el respaldo SQL.

## Pendientes fuera de este cierre

- E2E autenticado contra Facturama y datos representativos requiere un backend arrancable y credenciales/configuración de Sandbox.
- Producción, cancelación/sustitución, complementos PPD, CFDI tipo P, conciliación bancaria, reversión y evidencias bancarias permanecen expresamente fuera de alcance.
