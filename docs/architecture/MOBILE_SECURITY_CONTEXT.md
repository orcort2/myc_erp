> Estado: VIGENTE — EN REVISIÓN
>
> Tipo: Arquitectura vigente
>
> Corte verificado: 2026-08-26

# Contexto de seguridad de MYC Mobile

## Frontera

`User` continúa como identidad única. MYC Mobile admite dos actores sin mezclar
sus autoridades:

```text
internal → roles/permisos internos → scope staff vigente
client   → ClientPortalMembership → roles/permisos externos → un Client
```

No existen `MobileUser`, técnico externo ficticio ni roles internos asignados a
clientes. El permiso `mobile.access` sólo abre la sesión Mobile; cada operación
exige además su capacidad concreta.

## Autenticación y tokens

`POST /api/mobile/v1/auth/login`, `/refresh` y `GET /me` son la autoridad
Mobile. Los JWT nuevos distinguen `mobile_internal` y `mobile_client`. Los de
cliente incluyen `membership_id` y `client_id`, pero esos claims no conceden
scope: cada request vuelve a resolver usuario, membresía activa única, cliente
activo y permisos efectivos desde base.

Los access/refresh internos ya emitidos con `auth_context=internal` se aceptan
temporalmente en endpoints Mobile para no romper instalaciones vigentes; nunca
se interpretan como cliente. Un token `mobile_client` es rechazado por las
dependencias internas. Portal conserva `client_portal` y no concede Mobile por
tener `portal.read`.

## `MobileSecurityContext`

La dependencia canónica expone:

- `user`;
- `actor_type: internal | client`;
- `permissions` efectivos;
- `client_id` y `membership_id`, nulos para staff.

`require_mobile_permission` aplica capacidad explícita. Los endpoints
productivos Mobile de ETS/equipos/Hojas de Campo/Venta siguen usando
`require_internal_mobile_permission`: no se exponen a clientes hasta que cada
regla productiva tenga un adapter y ownership aprobados.

## Scope externo implementado

La superficie externa habilitada en esta fase es OT LAB temporal, sus equipos,
firmas, PDF, revisiones y Tickets asociados. `LabWorkOrder.client_id` es nullable:
las OT históricas/internas permanecen legibles para staff y las creadas por un
actor cliente se vinculan obligatoriamente a su organización. El nombre de
cliente enviado por la app no es autoritativo; el backend usa el `Client`
resuelto.

Listas filtran por `client_id`; detalles y subrecursos validan el padre y
responden `404` fuera de scope. Los writes verifican permiso antes de ownership,
por lo que un Viewer obtiene `403` sin inferir recursos. Exportación y borrado
LAB permanecen exclusivamente internos.

## Membresía activa única

La regla es:

```text
un Client → muchos usuarios
un usuario externo → máximo una membership active
```

El backend bloquea la fila `User` y valida la regla en alta administrativa,
reactivación, aprobación de vínculo y aceptación de invitación. PostgreSQL la
refuerza con el índice parcial único
`uq_client_portal_memberships_active_user (user_id) WHERE status='active'`.
Membresías `pending`, `suspended`, `revoked` o `rejected` conservan historia.
La migración aborta con mensaje explícito si detecta duplicados activos
preexistentes; no reasigna organizaciones silenciosamente.

## Roles externos persistidos

| Rol | Permisos |
| --- | --- |
| Viewer externo | `mobile.access`, `work_orders.read_organization`, `equipment.read`, `field_sheets.read` |
| Operativo Jr | Viewer + `work_orders.create`, `work_orders.execute`, `equipment.write`, `field_sheets.capture`, `signatures.capture`, `mobile_tickets.create`, `mobile_tickets.read` |
| Operativo Sr | Igual a Jr durante este bloque; no contiene permisos de folios |

Los paquetes se materializan en `ClientPortalRole`,
`ClientPortalPermission`, `ClientPortalRolePermission` y
`ClientPortalMembershipRole`. El startup idempotente existente reconcilia el
catálogo persistido. Sólo staff MYC puede listar/asignar perfiles que contengan
`mobile.access`; la autoadministración del Portal los excluye.

## Realtime, Comunicaciones y push

Realtime acepta JWT Mobile, conserva actor/scope y sólo permite rooms de
conversación cliente cuando el actor tiene permiso de Comunicaciones, participa
y `conversation.client_id` coincide. Nunca admite rooms internas o de otro
cliente. Los roles Mobile iniciales no incluyen Comunicaciones.

Push y Notificaciones usan endpoints Mobile y ownership por `user_id`; el
payload no acepta usuario ni cliente. Un dispositivo externo no requiere ser
staff y no puede desactivar dispositivos ajenos. Los destinatarios continúan
derivándose de cada evento de dominio, no de topics enviados por la app.

## Límites

No se implementaron folios, solicitudes/reposición, eventos realtime de folios
ni cambios a ETS/Cotizaciones productivos. El grupo de rutas `(technician)` se
conserva sólo como nombre organizativo. Los endpoints productivos Mobile quedan
deny para `client`; exponerlos requiere una fase posterior con contrato por
recurso, no sólo agregar permisos.
