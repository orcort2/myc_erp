> Estado: VIGENTE
>
> Tipo: Arquitectura vigente
>
> Autoridad: Alta para la matriz declarada; el código sigue siendo la fuente ejecutable
>
> Prevalece sobre: `../archive/security/permisos.md` y matrices de las especificaciones V2/V3
>
> Corte auditado: 2026-07-29 contra `backend/app/core/permissions.py`

# Matriz vigente de roles y permisos

Esta matriz documenta lo declarado en código. No garantiza que todos los endpoints apliquen el permiso: las brechas de enforcement están en [`../project/TECHNICAL_DEBT.md`](../project/TECHNICAL_DEBT.md).

## Roles

| Rol | Alcance declarado | Permisos principales exactos |
| --- | --- | --- |
| Administrador | Acceso total | `*` |
| Comercial | Clientes, cotizaciones, catálogo, documentos, lectura de ETS/SAT y revisión de equipo adicional | Contribución completa a Actividad, `service_orders.additional_equipment.propose/commercial_review`, clasificación/empresa/prefijo y solicitud/aplicación/inspección/reconstrucción de desbloqueo |
| Técnico | Equipos, Hojas de Campo, motores, firmas ETS y equipo adicional | Permisos previos más contribución completa a Actividad y `service_orders.additional_equipment.propose/execute` |
| Captura | Preparación, generación documental y resoluciones propias | Permisos operativos previos más contribución completa a Actividad |
| Calidad | Revisión, aprobación, metrología, control documental y autorización de equipo adicional | Gobierno completo de Actividad y `service_orders.additional_equipment.authorize` |
| Finanzas | Cobranza, facturación, liberación y resoluciones propias | Contribución/resolución de atención en Actividad más permisos financieros vigentes |
| Cliente | Portal limitado previsto | `portal.read`, `quotations.read_own`, `certificates.read_own`, `service_orders.read_own` |
| Desarrollador | Soporte técnico amplio sin comodín global | Gobierno completo de Actividad, `resolution_center.*`, permisos técnicos, folios y solicitud/autorización/aplicación/inspección de desbloqueo |
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
  ordinarios; Administrador conserva `*`.
- Servicios/folios: `services.manage_service_type`,
  `services.manage_linked_company`, `services.manage_certificate_prefix` y
  `folios.manage_sequences`.
- Certificados: lectura, creación, aprobación, captura, carga PDF y override de match.
- Auditoría: `audit_logs.read`.
- Patrones y procedimientos: lectura, creación, actualización y eliminación.
- Control Documental: lectura, creación, actualización, aprobación y archivo; incluye interpretaciones, perfiles y certificados de patrón.
- Metrología: selección de patrones, ejecución y modelos/versiones de incertidumbre.
- Plantillas de Hojas de Campo: lectura, creación, actualización, aprobación, archivo, exportación e importación.
- Configuración: lectura/actualización de parámetros y administración de catálogos maestros.
- ETS: firma y reapertura de ciclos de firma.
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

## Inconsistencias vigentes

1. Hay strings usados en roles que no tienen constante paralela en `PERMISSIONS`, por ejemplo `certificates.generate`, `certificates.quality`, `certificates.release`, `payments.*`, `invoices.*`, `portal.*` y permisos `*_own`.
2. Algunos routers no exigen los permisos declarados o están completamente abiertos.
3. La navegación frontend no refleja de forma consistente las capacidades.
4. Los roles se administran en código; no existe CRUD completo de roles/permisos.

Estas inconsistencias no cambian la matriz declarada; impiden considerarla plenamente aplicada.

## Mantenimiento

Todo cambio a `backend/app/core/permissions.py` debe sincronizar este documento. Una futura matriz generada puede sustituir esta tabla si conserva rol, permiso, endpoint consumidor y cobertura 401/403.
