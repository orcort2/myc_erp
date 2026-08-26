# Cierre técnico — reconciliación de solicitudes al borrar OT LAB

> Fecha: 2026-08-26
>
> Estado: IMPLEMENTADO Y VALIDADO

El borrado administrativo de una raíz LAB fallaba para grupos materializados
desde `LabWorkOrderGroupRequest`: la FK
`lab_work_order_group_requests_root_work_order_id_fkey`, configurada con
`ON DELETE RESTRICT`, todavía apuntaba a la fila que se intentaba eliminar.

`delete_work_order()` ahora bloquea la solicitud vinculada dentro de su misma
transacción. Si existen hermanas, la solicitud apunta a la raíz promovida; si se
retira la última OT, queda con `root_work_order_id=NULL`. No se modifica el
estado `approved`, la decisión, requester, handler, timestamps ni conversación.
Un fallo en cualquier reconciliación conserva el rollback completo y el cliente
sigue recibiendo el error seguro genérico.

No hubo migración: modelo, migración aplicada y PostgreSQL local ya declaran la
columna nullable. Tampoco se modifica `InstitutionalFolioSequence`; las pruebas
demuestran que el alta posterior avanza al siguiente folio.

La evidencia original de folios permanece estructurada en
`AuditLog.new_values` para `lab_work_order.group_materialized`. La proyección de
la solicitud devuelve `folios=[]` cuando no quedan OTs; TD-057 conserva la
decisión pendiente sobre un posible snapshot futuro sin ampliar este P0.

Validación ejecutada: 9 pruebas focales de borrado correctas; 45 pruebas LAB,
Notifications, Communications y Realtime correctas, 6 omitidas por requerir
PostgreSQL opt-in y 1 caso histórico deliberadamente excluido. Ese caso falla
también fuera de este cambio porque espera editar después de firma y el contrato
vigente responde 409. Compilación Python, Alembic current/head/check y
`git diff --check` quedaron correctos.
