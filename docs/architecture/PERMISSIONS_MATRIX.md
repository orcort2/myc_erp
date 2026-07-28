> Estado: VIGENTE
>
> Tipo: Arquitectura vigente
>
> Autoridad: Alta para la matriz declarada; el código sigue siendo la fuente ejecutable
>
> Prevalece sobre: `../archive/security/permisos.md` y matrices de las especificaciones V2/V3
>
> Corte auditado: 2026-07-28 contra `backend/app/core/permissions.py`

# Matriz vigente de roles y permisos

Esta matriz documenta lo declarado en código. No garantiza que todos los endpoints apliquen el permiso: las brechas de enforcement están en [`../project/TECHNICAL_DEBT.md`](../project/TECHNICAL_DEBT.md).

## Roles

| Rol | Alcance declarado | Permisos principales exactos |
| --- | --- | --- |
| Administrador | Acceso total | `*` |
| Comercial | Clientes, cotizaciones, documentos, lectura de ETS/SAT y resoluciones propias | `resolution_center.read`, `clients.read`, `clients.create`, `clients.update`, `documents.read`, `quotations.read`, `quotations.create`, `quotations.update`, `quotations.act_as_advisor`, `service_orders.read`, `sat_catalogs.read`, `sat_catalogs.manage_favorites`, `sat_catalogs.manage_aliases` |
| Técnico | Equipos, Hojas de Campo, patrones, procedimientos, motores, firmas ETS y resoluciones propias | `resolution_center.read`, `equipment.read`, `equipment.update`, `field_sheets.read`, `field_sheets.create`, `field_sheets.update`, `field_sheets.review`, `field_sheet_templates.read`, `standards.read`, `procedures.read`, `documents.read`, `document_interpretations.read`, `technical_profiles.read`, `reference_standard_certificates.read`, `pattern_selection.execute`, `uncertainty.execute`, `service_orders.read`, `service_orders.update`, `service_orders.sign` |
| Captura | Preparación, generación documental y resoluciones propias | `resolution_center.read`, `clients.read`, `quotations.read`, `service_orders.read`, `field_sheets.read`, `field_sheets.create`, `field_sheets.update`, `field_sheet_templates.read`, `certificates.read`, `certificates.create`, `certificates.generate`, `certificates.capture`, `certificates.upload_pdf`, `standards.read`, `procedures.read`, `documents.read`, `document_interpretations.read`, `technical_profiles.read`, `reference_standard_certificates.read`, `pattern_selection.execute`, `uncertainty.execute` |
| Calidad | Revisión, aprobación, metrología, control documental y resoluciones propias | `resolution_center.read`, `audit_logs.read`, `certificates.read`, `certificates.quality`, `certificates.approve`, `certificates.match_override`, `field_sheets.read`, `field_sheets.update`, `field_sheets.review`, `service_orders.read`, `service_orders.signatures.reopen`, `standards.read`, `procedures.read`, `metrology.execute`, CRUD/aprobación de documentos, interpretaciones, perfiles, certificados de patrón, modelos de incertidumbre y plantillas de Hojas de Campo |
| Finanzas | Cobranza, facturación, liberación y resoluciones propias | `resolution_center.read`, `clients.read`, `certificates.read`, `quotations.read`, `payments.read`, `payments.manage`, `invoices.read`, `invoices.manage`, `integrations.facturama.status`, `certificates.release`, `release.manage`, `sat_catalogs.read`, `sat_catalogs.manage_favorites`, `sat_catalogs.manage_aliases` |
| Cliente | Portal limitado previsto | `portal.read`, `quotations.read_own`, `certificates.read_own`, `service_orders.read_own` |
| Desarrollador | Soporte técnico amplio sin comodín global | `resolution_center.*`, auditoría, usuarios, settings, patrones, procedimientos, metrología, control documental, certificados, liberación, incertidumbre, plantillas de Hojas de Campo, firmas ETS y administración SAT según el conjunto exacto de `ROLE_PERMISSIONS` |
| Auditor | Expediente institucional read-only | `resolution_center.read`, `resolution_center.read_all`, `resolution_center.audit`, `resolution_center.infrastructure`, `audit_logs.read` |

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

## Inconsistencias vigentes

1. Hay strings usados en roles que no tienen constante paralela en `PERMISSIONS`, por ejemplo `certificates.generate`, `certificates.quality`, `certificates.release`, `payments.*`, `invoices.*`, `portal.*` y permisos `*_own`.
2. Algunos routers no exigen los permisos declarados o están completamente abiertos.
3. La navegación frontend no refleja de forma consistente las capacidades.
4. Los roles se administran en código; no existe CRUD completo de roles/permisos.

Estas inconsistencias no cambian la matriz declarada; impiden considerarla plenamente aplicada.

## Mantenimiento

Todo cambio a `backend/app/core/permissions.py` debe sincronizar este documento. Una futura matriz generada puede sustituir esta tabla si conserva rol, permiso, endpoint consumidor y cobertura 401/403.
