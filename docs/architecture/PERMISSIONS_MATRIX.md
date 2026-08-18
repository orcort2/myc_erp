> Estado: VIGENTE
>
> Tipo: Arquitectura vigente
>
> Autoridad: Alta para la matriz declarada; el código sigue siendo la fuente ejecutable
>
> Prevalece sobre: `../archive/security/permisos.md` y matrices de las especificaciones V2/V3
>
> Corte auditado: 2026-08-13 contra `backend/app/core/permissions.py` y el inventario FastAPI

# Matriz vigente de roles y permisos

Esta matriz documenta lo declarado en código. La aplicación transversal se
rige por [`security/API_ACCESS_CONTROL.md`](security/API_ACCESS_CONTROL.md) y
su inventario de 383 operaciones; cada servicio puede exigir controles más
específicos además del mínimo central.

`backend/app/core/permissions.py` es el bootstrap ejecutable y la capa de
compatibilidad temporal de la autoridad actual. No es el modelo administrativo
definitivo. La etapa posterior deberá sustituir su administración estática por
roles/grupos múltiples, overrides allow/deny, alcances por registro, permisos
temporales y protección de capacidades críticas sin cambiar claves por mera
inferencia documental.

## Roles

| Rol | Alcance declarado | Permisos principales exactos |
| --- | --- | --- |
| Administrador | Acceso total | `*` |
| Comercial | Clientes, cotizaciones, catálogo, documentos, creación/actualización de ETS y revisión de equipo adicional | Contribución completa a Actividad, CRUD comercial/catálogo, `service_orders.create/update` y permisos de desbloqueo |
| Técnico | Equipos, Hojas de Campo, motores, firmas ETS, equipo adicional y captura OT LAB temporal | CRUD de equipos, ejecución de motores, Actividad, `service_orders.additional_equipment.propose/execute`, `lab_work_orders.use` y Tickets propios `create/view_own` |
| Captura | Preparación, generación documental y resoluciones propias | Permisos operativos, ejecución de motores y contribución completa a Actividad |
| Calidad | Revisión, aprobación, metrología, control documental, configuración institucional y autorización de equipo adicional | Gobierno completo de Actividad, lectura/actualización institucional, `reference_standard_certificates.delete` y `service_orders.additional_equipment.authorize` |
| Finanzas | Cobranza, facturación, lectura ETS, liberación y resoluciones propias | Contribución/resolución de atención en Actividad más permisos financieros vigentes |
| Cliente | Portal aislado por cliente | `portal.read`, `quotations.read_own`, `certificates.read_own`, `service_orders.read_own`; el tenant se deriva en backend |
| Desarrollador | Soporte técnico amplio sin comodín global | Gobierno de Actividad, `resolution_center.*`, CRUD comercial/técnico, baja lógica de incertidumbre de certificado de patrón, configuración institucional, motores, folios, desbloqueo y `lab_work_orders.use/export` |
| Operador | Operación de resoluciones propias sin autorización | Contribución completa a Actividad, permisos del Centro y equipo adicional |
| Auditor | Expediente institucional read-only | `activity.read`, `activity.view_audit` y permisos de auditoría vigentes |

## Familias declaradas en `PERMISSIONS`

- Usuarios: `users.read`, `users.manage`.
- Clientes: `clients.read`, `clients.create`, `clients.update`.
- Cotizaciones: `quotations.read`, `quotations.create`, `quotations.update`.
- Desbloqueo: `quotations.exceptions.request_unlock`,
  `authorize_unlock`, `apply_unlock`, `inspect` y
  `rebuild_empty_service_order`. La autoautorización exige
  `quotations.exceptions.self_authorize_unlock`, no asignado a roles
  ordinarios; Administrador la satisface mediante `*` y desbloquea
  directamente con un clic, sin modal ni motivo manual. El sistema conserva
  un motivo institucional para la auditoría.
- Servicios/folios: `services.manage_service_type`,
  `services.manage_linked_company`, `services.manage_certificate_prefix` y
  `folios.manage_sequences`.
- Certificados: lectura, creación, aprobación, captura, carga PDF y override de match.
- Auditoría: `audit_logs.read`.
- Patrones y procedimientos: lectura, creación, actualización y eliminación.
- Órdenes de Trabajo productivas: `service_orders.delete` protege
  el borrado físico individual. Sólo Administrador lo obtiene actualmente por
  `*`; `service_orders.update`, nombres de rol en frontend y el permiso LAB no
  conceden esta operación.
- Control Documental: lectura, creación, actualización, aprobación y archivo; incluye interpretaciones, perfiles y certificados de patrón.
- Metrología: selección de patrones, ejecución y modelos/versiones de incertidumbre.
- Plantillas de Hojas de Campo: lectura, creación, actualización, aprobación, archivo, exportación e importación.
- Configuración: lectura/actualización de parámetros y administración de catálogos maestros.
- ETS: firma y reapertura de ciclos de firma.
- OT LAB temporal: `lab_work_orders.use` para captura y
  `lab_work_orders.export` para retiro verificable;
  `lab_work_orders.delete` protege el borrado físico individual y sólo
  Administrador lo recibe mediante `*`. No forman parte del dominio productivo
  y deben eliminarse con el módulo temporal.
- Tickets/reapertura LAB: `tickets.create`, `tickets.view_own`,
  `tickets.view_all`, `tickets.review`, `work_orders.reopen`,
  `work_orders.reopen_preserve_signatures` y
  `work_orders.reopen_invalidate_signatures`. Técnico crea/consulta propios;
  Calidad revisa todos y decide política; backend conserva autoridad final.
- SAT: lectura, administración, favoritos y alias.
- Centro de Resoluciones: `read`, `read_all`, `create`, `prepare`, `analyze`,
  `plan`, `simulate`, `authorize`, `execute`, `audit` e `infrastructure`.
- Equipo adicional: `propose`, `authorize`, `execute`, `commercial_review` y
  `audit`, bajo `service_orders.additional_equipment`.
- Actividad: `read`, `create`, `edit_own`, `delete_own`, `moderate`,
  `attach_files`, `mention`, `request_attention`, `resolve_attention` y
  `view_audit`. Todo acceso combina el permiso Activity con lectura del módulo.

En las etapas crear, autorizar y ejecutar, el router exige sesión con lectura
del Centro y el workflow aplica después el permiso específico de la definición.
Para Equipo adicional esto permite segregación real entre Comercial/Operador,
Calidad y Técnico; para definiciones sin permiso vertical equivalente se
conserva el permiso canónico `resolution_center.*` de la etapa.

## Límites vigentes

1. Hay strings usados en roles que no tienen constante paralela en
   `PERMISSIONS`, por ejemplo `certificates.generate`, `payments.*`,
   `invoices.*`, `portal.*` y permisos `*_own`.
2. El guard central aplica el mínimo clasificado; ownership y reglas de estado
   específicas continúan en el servicio propietario.
3. Los roles se administran en código como bootstrap temporal; la administración
   definitiva desde Ajustes es trabajo obligatorio de la etapa posterior.
4. El frontend filtra navegación y acciones principales, pero no constituye
   autoridad y aún requiere E2E browser por rol para todos los módulos.

Estos límites no reabren el acceso anónimo: toda ruta interna exige identidad y
su permiso mínimo antes de ejecutar el endpoint.

## Comunicaciones

Comunicaciones no agrega permisos bootstrap ni confía en el frontend. Todas
las rutas REST exigen usuario interno autenticado y el servicio filtra por
membership; WebSocket vuelve a validar usuario, ownership y suscripción en
cada room/comando. Administrador, Desarrollador y Calidad pueden usar
menciones masivas; esa regla de dominio no concede acceso a conversaciones
ajenas. Vincular un Ticket exige ser solicitante o tener `tickets.view_all`.

## Mantenimiento

Todo cambio a `backend/app/core/permissions.py` debe sincronizar este documento.
Además, ningún permiso nuevo puede agregarse directamente a ese archivo: debe
existir primero en el Catálogo Institucional bajo la jerarquía
`Módulo→Acción→Microacción`, superar revisión funcional y quedar aprobado como
permiso institucional. El catálogo es autoridad funcional, pero no reemplaza
ni genera automáticamente esta matriz ejecutable. Las dos capacidades LAB son
la excepción temporal, explícita y removible de ADR-071; se gobiernan como
brecha de compatibilidad y no alteran el catálogo objetivo permanente.

La reconciliación verificable se ejecuta con
`venv/bin/python scripts/validate_capability_catalog.py --check`. Al corte se
mantienen 82 claves bootstrap pendientes de reconciliación documental y 22
permisos HTTP de compatibilidad sin coincidencia literal en el snapshot
técnico. Las 75 claves HTTP están declaradas en bootstrap:
`reference_standard_certificates.delete` se asigna a Calidad/Desarrollador y
Portal usa `portal.read`. Las brechas restantes no autorizan renombrados;
su clasificación está en el cierre TD-027 y en
[`security/CAPABILITY_MODEL_GAPS_2026-08-04.md`](security/CAPABILITY_MODEL_GAPS_2026-08-04.md).
