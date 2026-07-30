> Estado: VIGENTE
>
> Corte verificado: 2026-07-29
>
> Sustituye: `QUOTATION_CHANGE_SERVICE_EXCEPTION.md`

# Desbloqueo controlado de cotización aprobada

## Contrato

La excepción `EXV-AAAA-#####` concede la capacidad temporal
`quotation.controlled_unlock` sobre una cotización `MYC-…` aprobada y su ETS
`OSMYC-…`. La identidad humana y la API contextual usan folios visibles; las
claves primarias sólo enlazan internamente el expediente.

El flujo es:

`aprobada → solicitud → revisión → autorización → edición directa de partidas
→ comparación de revisiones → confirmación → reconstrucción atómica del ETS
virgen → cierre`.

No existe un editor paralelo de “cambiar servicio”. La ficha habitual habilita
agregar, retirar, sustituir o volver a seleccionar servicios, cantidades,
precios, descuentos y observaciones. Cliente, folio, identidad institucional y
campos no comerciales permanecen bloqueados.

## Revisión y delta

La solicitud congela la revisión base y el folio ETS. Al aplicar se exige la
misma revisión y se vuelve a resolver cada `service_key` contra un servicio
activo. Todas las partidas anteriores se desactivan y la revisión excepcional
crea partidas nuevas con snapshots vigentes; la revisión aprobada previa no se
reescribe.

`quotation_revision_diff.py` compara huellas de negocio y produce `removed` y
`added`. Precio, descuento, cantidad, tipo, empresa y prefijo participan en la
comparación. Una operación sin delta se rechaza.

## Reconstrucción física

`can_physically_rebuild_service_order()` es el único validador propietario.
Bloquea equipos, certificados/reservas, archivos de captura, facturas, ciclos
de firma, firmas del ETS, referencias del Motor, estados operativos y OT con
ejecución. Las OT `pending` creadas automáticamente son derivadas
reconstruibles; cualquier cambio de estado las convierte en bloqueo.

Dentro de una transacción se bloquean expediente, cotización y ETS; se
revalidan permiso, usuario, vigencia, revisión, relación, folio y dependencias;
se crea la nueva revisión, se elimina físicamente el ETS virgen y se crea otro
con el mismo `OSMYC-…`. No se consulta un consecutivo ETS. El nuevo registro
parte en `scheduled`, sin técnico, firmas ni ejecución, toma cliente y
partidas de la cotización y conserva un `source_snapshot` de cliente,
domicilio, contactos y datos comerciales.

El expediente conserva folio previo, IDs internos anterior/nuevo, validación,
delta, expansión y confirmación de folio preservado. Actividad, auditoría y
notificaciones quedan fuera del ETS eliminado.

## Permisos

- `quotations.exceptions.request_unlock`
- `quotations.exceptions.authorize_unlock`
- `quotations.exceptions.apply_unlock`
- `quotations.exceptions.inspect`
- `quotations.exceptions.rebuild_empty_service_order`
- `quotations.exceptions.self_authorize_unlock` (no asignado a roles ordinarios)

Comercial solicita, inspecciona y aplica; Desarrollador autoriza y administra.
Administrador conserva `*`. La segregación impide autoautorización salvo
capacidad explícita. Si un mismo actor reúne `authorize_unlock`,
`apply_unlock`, `rebuild_empty_service_order`, `inspect` y
`self_authorize_unlock`, el comando de solicitud registra también la
autorización, asignación y vigencia de 72 horas. Administrador entra por esta
ruta mediante `*`: al pulsar `Desbloquear cotización`, la interfaz no abre
modal ni solicita motivo u observación; envía un motivo institucional estándar,
abre inmediatamente la edición y conserva eventos separados de solicitud y
autorización, notificación y auditoría `quotation.unlock_self_authorized`.
Si ya existía una solicitud administrativa pendiente creada por la versión
anterior, la misma ficha ofrece `Autorizar y editar` y consume el endpoint de
revisión vigente; no obliga a crear otro expediente.

## Límites

No resuelve ETS con operación, no introduce actualización no destructiva, no
crea otras excepciones y no modifica el Motor de Resoluciones.
