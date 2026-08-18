> Estado: VIGENTE
>
> Corte verificado: 2026-08-17

# Eliminación administrativa de Orden de Trabajo productiva

## Identidad y frontera

La entidad eliminable es `ServiceWorkOrder`. `ServiceOrder` es el ETS padre y
`LabWorkOrder` es un agregado temporal aislado: ninguno se elimina mediante
este flujo. La ruta `DELETE /api/service-orders/work-orders/{work_order_id}`
exige access JWT interno y `service_orders.delete`. Actualmente
sólo Administrador satisface esa capacidad mediante `*`; frontend sólo decide
visibilidad y el backend vuelve a autorizar obligatoriamente.

## Mapa de ownership

Se eliminan cuando pertenecen a la OT objetivo:

- `Equipment` y sus `FieldSheet`, resultados, firmas, vínculos a patrones y
  cálculos de incertidumbre;
- `Certificate`, versiones PDF, capturas identificadas y archivos exclusivos;
- `ServiceUnit`, `ServiceStage`, documentos de etapa, solicitudes técnicas,
  tareas y asignaciones;
- vínculos de ciclo de firma, hilos Activity propios y notificaciones
  semánticas que ya no deben abrir la OT.

Se conservan:

- el ETS, cliente, cotización, partidas, usuarios y catálogos/maestros;
- facturas e ítems financieros; sus punteros anulables a equipo/certificado se
  limpian sin borrar el concepto;
- cotizaciones derivadas; sus punteros anulables a unidad/etapa/solicitud se
  limpian;
- resoluciones generales referenciadas desde equipos;
- un ciclo de firma mientras conserve al menos otra OT;
- `audit_logs`, incluido `service_work_order.deleted` con actor, fecha, ID,
  número de OT e ID del ETS, sin copiar cliente ni contenido operativo.

`CertificateResolutionOperation` es evidencia inmutable del Motor y su FK es
restrictiva. Si existe para un certificado de la OT, el servicio responde
`409 WORK_ORDER_DELETE_BLOCKED` antes de aplicar cambios.

## Atomicidad y archivos

La OT y el ETS se bloquean para actualización. Todas las mutaciones de base de
datos, desacoplamientos y auditoría comparten un commit; cualquier excepción
ejecuta rollback y responde con error controlado. No se introducen cascadas
globales.

Los archivos exclusivos dejan primero su ruta publicable mediante un
`os.replace` hacia `.pending-deletions` dentro de `STORAGE_ROOT`. Si el commit
falla, vuelven a su ubicación original. Tras commit se destruyen; un archivo
con otra referencia activa no se mueve ni elimina.

Una falla excepcional del `unlink` posterior al commit deja el archivo fuera
de rutas publicables dentro de `.pending-deletions`. El barrido automatizado y
observable de ese staging está registrado como TD-040; no afecta el rollback
de base ni permite descargar el archivo desde las rutas institucionales.

## Consumidores

El modal de Órdenes de Trabajo muestra la acción sólo con la capacidad exacta,
incluye OT y cliente en una confirmación destructiva y refresca todo el
expediente tras éxito.

MYC Mobile no consume el listado, detalle, documentos ni DELETE de
`ServiceWorkOrder` durante su fase LAB temporal. Su eliminación administrativa
usa `LabWorkOrder`, `lab_work_orders.delete` y el namespace móvil LAB; no envía
IDs LAB a `/api/service-orders/work-orders/{id}`. Ambos contratos permanecen
separados y el backend/ERP web productivo conserva esta implementación.
