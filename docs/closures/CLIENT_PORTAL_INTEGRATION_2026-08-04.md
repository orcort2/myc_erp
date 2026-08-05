> Estado: TERMINADO — EN REVISIÓN
>
> Corte: 2026-08-04

# Cierre de integración del Portal del Cliente

## Resultado

La integración operativa del Portal del Cliente quedó terminada sobre la arquitectura persistente existente y queda disponible para revisión funcional. Se conservaron las migraciones `120ab33b56f9` y `bd2270bc5282`; no fue necesaria una migración adicional.

La ampliación administrativa posterior está documentada en
[`PORTAL_USER_ACCESS_ADMINISTRATION_2026-08-05.md`](PORTAL_USER_ACCESS_ADMINISTRATION_2026-08-05.md)
y agrega la migración `c8a51e2d7f40`; esta fotografía del 2026-08-04 se conserva
como antecedente técnico.

El acceso interno y el acceso del portal son contextos JWT separados. Las cuentas `client_portal` no pueden autenticarse en `/api/auth/*`; el portal usa `/api/portal/auth/*`. El cliente efectivo se deriva exclusivamente de una `ClientPortalMembership` activa y única. Se retiró la coincidencia de correo con `Client.email` o `ClientContact.email` como autoridad.

## Flujos integrados

- registro público, verificación de correo y reenvío sin exponer tokens en respuestas productivas;
- invitación preautorizada, validación, aceptación de un solo uso y almacenamiento SHA-256 del token;
- revisión interna, solicitud de vínculo, aprobación o rechazo y creación transaccional de membresía;
- varias cuentas por cliente, varios roles por membresía, roles base globales y roles personalizados aislados;
- suspensión, reactivación, revocación, contacto principal y protección del último administrador activo;
- perfil, tablero, empresa, cotizaciones, servicios, equipos, certificados, facturas y pagos filtrados por membresía;
- Ajustes → Usuarios con separación visual entre cuentas internas y accesos de clientes, además del resumen de accesos en Clientes;
- configuración por cliente sin mezclar datos fiscales.

El adaptador de correo conserva un outbox sólo en desarrollo. La entrega productiva requiere conectar el proveedor institucional; los tokens nunca se registran ni persisten en claro. MFA, recuperación de contraseña, sesiones revocables, descarga fiscal especializada y mensajería bidireccional quedan explícitamente fuera de esta integración.

## Seguridad y validación

- 344 operaciones HTTP clasificadas deny-by-default y CSV sincronizado.
- `configure_mappers`: correcto.
- `py_compile` del portal: correcto.
- Backend completo: `444 passed, 19 subtests passed, 3 warnings`.
- Frontend unitario: `31 passed`.
- Frontend: build de producción correcto; permanece el warning informativo de chunk mayor a 500 kB.
- Alembic: `current = heads = bd2270bc5282`; `alembic check` sin operaciones nuevas.
- Catálogo del portal: 20 permisos y 6 roles base.
- Respaldo local regenerado y alineado con `bd2270bc5282`.
- `git diff --check`: requerido como gate del commit documental.

## Dictamen

**PORTAL DEL CLIENTE — TERMINADO — EN REVISIÓN.** No se declara aptitud productiva ni módulo sellado hasta completar la revisión funcional y conectar el correo productivo.
