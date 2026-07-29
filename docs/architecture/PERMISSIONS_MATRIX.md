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
| Comercial | Clientes, cotizaciones, documentos, lectura de ETS/SAT y revisión de equipo adicional | Permisos previos más `service_orders.additional_equipment.propose` y `service_orders.additional_equipment.commercial_review` |
| Técnico | Equipos, Hojas de Campo, motores, firmas ETS y equipo adicional | Permisos previos más `service_orders.additional_equipment.propose` y `service_orders.additional_equipment.execute` |
| Captura | Preparación, generación documental y resoluciones propias | `resolution_center.read`, `clients.read`, `quotations.read`, `service_orders.read`, `field_sheets.read`, `field_sheets.create`, `field_sheets.update`, `field_sheet_templates.read`, `certificates.read`, `certificates.create`, `certificates.generate`, `certificates.capture`, `certificates.upload_pdf`, `standards.read`, `procedures.read`, `documents.read`, `document_interpretations.read`, `technical_profiles.read`, `reference_standard_certificates.read`, `pattern_selection.execute`, `uncertainty.execute` |
| Calidad | Revisión, aprobación, metrología, control documental y autorización de equipo adicional | Permisos previos más `service_orders.additional_equipment.authorize` |
| Finanzas | Cobranza, facturación, liberación y resoluciones propias | `resolution_center.read`, `clients.read`, `certificates.read`, `quotations.read`, `payments.read`, `payments.manage`, `invoices.read`, `invoices.manage`, `integrations.facturama.status`, `certificates.release`, `release.manage`, `sat_catalogs.read`, `sat_catalogs.manage_favorites`, `sat_catalogs.manage_aliases` |
| Cliente | Portal limitado previsto | `portal.read`, `quotations.read_own`, `certificates.read_own`, `service_orders.read_own` |
| Desarrollador | Soporte técnico amplio sin comodín global | `resolution_center.*`, auditoría, usuarios, settings, patrones, procedimientos, metrología, control documental, certificados, liberación, incertidumbre, plantillas de Hojas de Campo, firmas ETS y administración SAT según el conjunto exacto de `ROLE_PERMISSIONS` |
| Operador | Operación de resoluciones propias sin autorización | Permisos del Centro más `service_orders.additional_equipment.propose` y `service_orders.additional_equipment.execute` |
| Auditor | Expediente institucional read-only | Permisos de auditoría más `service_orders.additional_equipment.audit` |

## Familias declaradas en `PERMISSIONS`

- Usuarios: `users.read`, `users.manage`.
- Clientes: `clients.read`, `clients.create`, `clients.update`.
- Cotizaciones: `quotations.read`, `quotations.create`, `quotations.update`.
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
