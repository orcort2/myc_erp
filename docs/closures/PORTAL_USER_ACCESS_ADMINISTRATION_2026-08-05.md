> Estado: TERMINADO — EN REVISIÓN
>
> Corte: 2026-08-05

# Administración de usuarios y accesos del Portal del Cliente

## Resultado

`Ajustes → Usuarios y accesos del Portal` quedó terminado técnicamente y listo
para revisión funcional. La solución amplía la arquitectura existente; no crea
un dominio alterno ni mezcla roles internos con roles del portal.

## Alcance verificado

- tabla conjunta con búsqueda, filtros, paginación, identidad, estados,
  empresa, cliente, roles, verificación y fechas;
- modal estable con Perfil, Acceso, Roles y permisos, Organización,
  Comunicaciones, Actividad y Seguridad; Organización distingue empresa
  declarada, razón social, nombre comercial, aprobador y origen verificables;
- username interno explícito, editable, normalizado y distinto del correo;
- múltiples roles internos y múltiples roles por membresía/invitación/vínculo;
- bandejas globales de registros y solicitudes con revisión, aprobación,
  rechazo y cancelación; la aprobación crea la membresía transaccionalmente;
- notificación persistente a las partes interesadas al aprobar o rechazar una
  solicitud de vínculo;
- acciones específicas y auditadas para roles, contacto principal, suspensión,
  reactivación y revocación;
- invitaciones con varios roles, reenvío, cancelación, revocación y enlace sólo
  en desarrollo;
- configuración administrativa de `ClientPortal`, sin simular MFA ni carga de
  logotipo;
- sección Usuarios del Portal condicionada por permisos y acotada al cliente
  derivado de la membresía;
- política común de bloqueo: 5 fallos, 15 minutos, reinicio al autenticar y
  respuesta genérica.

## Persistencia y API

La migración reversible `c8a51e2d7f40` incorpora a `users` teléfono, puesto,
área, idioma y zona horaria, y alinea `is_active` con `status`. El inventario
deny-by-default contiene 356 operaciones. Se añadieron operaciones objetivas
para actividad de usuario, revisión/cancelación de solicitudes, reenvío de
invitación y administración autogestionada bajo `/api/client-portal/users`.

## Validaciones

- focalizadas backend: 25 aprobadas;
- regresión backend completa: 450 aprobadas y 19 subtests;
- focalizadas frontend: 10 aprobadas; regresión frontend completa: 40 aprobadas;
- build Vite: correcto, con warning informativo de chunk principal >500 kB;
- Alembic: `current = heads = c8a51e2d7f40`; `alembic check` limpio;
- respaldo oficial restaurado en PostgreSQL aislado: 112 tablas y revisión
  `c8a51e2d7f40`;
- navegador autenticado: tabla, filtros, modal, siete pestañas, multirrol,
  bandejas, contador global, configuración y navegación Usuarios comprobados;
- datos temporales de validación eliminados al terminar.

## Límites explícitos

Correo productivo, MFA, recuperación de contraseña, revocación persistente de
sesiones y comunicaciones bidireccionales permanecen fuera de esta entrega. No
se muestran IP, dispositivos o sesiones porque no existe persistencia real.

## Dictamen

**AJUSTES → USUARIOS Y ACCESOS DEL PORTAL — TERMINADO — EN REVISIÓN.**
