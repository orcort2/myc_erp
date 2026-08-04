> Estado: VIGENTE
>
> Tipo: Arquitectura vigente
>
> Autoridad: Alta para la matriz declarada; el código sigue siendo la fuente ejecutable
>
> Prevalece sobre: `../archive/security/permisos.md` y matrices de las especificaciones V2/V3
>
> Corte auditado: 2026-08-04 contra `backend/app/core/permissions.py` y el inventario FastAPI

# Matriz vigente de roles y permisos

Esta matriz documenta lo declarado en código. La aplicación transversal se
rige por [`security/API_ACCESS_CONTROL.md`](security/API_ACCESS_CONTROL.md) y
su inventario de 306 operaciones; cada servicio puede exigir controles más
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
| Técnico | Equipos, Hojas de Campo, motores, firmas ETS y equipo adicional | CRUD de equipos, ejecución de motores, contribución completa a Actividad y `service_orders.additional_equipment.propose/execute` |
| Captura | Preparación, generación documental y resoluciones propias | Permisos operativos, ejecución de motores y contribución completa a Actividad |
| Calidad | Revisión, aprobación, metrología, control documental, configuración institucional y autorización de equipo adicional | Gobierno completo de Actividad, lectura/actualización institucional y `service_orders.additional_equipment.authorize` |
| Finanzas | Cobranza, facturación, lectura ETS, liberación y resoluciones propias | Contribución/resolución de atención en Actividad más permisos financieros vigentes |
| Cliente | Portal aislado por cliente | `portal.read`, `quotations.read_own`, `certificates.read_own`, `service_orders.read_own`; el tenant se deriva en backend |
| Desarrollador | Soporte técnico amplio sin comodín global | Gobierno de Actividad, `resolution_center.*`, CRUD comercial/técnico, configuración institucional, motores, folios y desbloqueo |
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

## Mantenimiento

Todo cambio a `backend/app/core/permissions.py` debe sincronizar este documento.
El catálogo institucional del 2026-08-04 es insumo funcional de la siguiente
etapa, no reemplazo automático de esta matriz: cada permiso propuesto debe
revisarse contra claves vigentes, endpoint consumidor, ownership y cobertura
401/403 antes de aprobarse.
