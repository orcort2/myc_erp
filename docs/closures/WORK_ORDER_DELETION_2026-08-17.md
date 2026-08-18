# Cierre técnico — eliminación administrativa de OT productiva

> Fecha: 2026-08-17
>
> Estado: IMPLEMENTADO Y VALIDADO

Se incorporó el endpoint protegido
`DELETE /api/service-orders/work-orders/{id}`, la transacción propietaria, el
tratamiento reversible de archivos y la acción confirmada en el modal de OT.
MYC Mobile no consume este agregado ni su DELETE durante la fase temporal LAB;
la integración productiva móvil introducida inicialmente fue retirada al
confirmarse la frontera de dominio. No se modificó esquema ni base local.

La suite específica comprueba Administrador, 403, 404, estados sin restricción,
dependencias, firma compartida, conservación financiera, ausencia en lecturas
móviles, bloqueo por evidencia inmutable y rollback de base/archivo. La
regresión dirigida cerró con 43 pruebas backend y 5 frontend. La suite backend
completa cerró con 526 passed, 5 skipped y 19 subtests; el inventario
deny-by-default quedó posteriormente en 398 operaciones al incorporar el
DELETE LAB aislado y cuatro rutas concurrentes de Comunicaciones; el endpoint
productivo no cambió.

Riesgo residual: TD-040 registra el barrido operativo todavía no automatizado
para un archivo que, tras commit correcto, no pudiera desvincularse del staging
privado por una falla excepcional del filesystem.

El contrato completo y el mapa de dependencias están en
[`../architecture/WORK_ORDER_DELETION.md`](../architecture/WORK_ORDER_DELETION.md).
