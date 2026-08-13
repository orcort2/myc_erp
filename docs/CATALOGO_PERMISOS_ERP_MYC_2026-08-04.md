# Catálogo de permisos ERP MYC

Fuente revisada: `backend/app/core/permissions.py` del ZIP `app(23).zip`.

- Roles definidos: **10**
- Permisos declarados en `PERMISSIONS`: **104**
- Permisos concretos usados por roles: **138**
- Permisos usados por roles pero ausentes de `PERMISSIONS`: **35**
- Permisos declarados sin asignación directa: **1**

> El catálogo actual no es completamente canónico: `ROLE_PERMISSIONS` utiliza permisos que `PERMISSIONS` no registra.

## activity

| Permiso | Constante | Roles directos | Estado |
|---|---|---|---|
| `activity.attach_files` | `ACTIVITY_ATTACH_FILES` | Calidad, Captura, Comercial, Desarrollador, Finanzas, Operador, Tecnico | Declarado y asignado |
| `activity.audit` | `—` | Calidad, Desarrollador | Usado por roles, ausente de PERMISSIONS |
| `activity.create` | `ACTIVITY_CREATE` | Calidad, Captura, Comercial, Desarrollador, Finanzas, Operador, Tecnico | Declarado y asignado |
| `activity.delete_own` | `ACTIVITY_DELETE_OWN` | Calidad, Captura, Comercial, Desarrollador, Finanzas, Operador, Tecnico | Declarado y asignado |
| `activity.edit_own` | `ACTIVITY_EDIT_OWN` | Calidad, Captura, Comercial, Desarrollador, Finanzas, Operador, Tecnico | Declarado y asignado |
| `activity.mention` | `ACTIVITY_MENTION` | Calidad, Captura, Comercial, Desarrollador, Finanzas, Operador, Tecnico | Declarado y asignado |
| `activity.moderate` | `ACTIVITY_MODERATE` | Calidad, Desarrollador | Declarado y asignado |
| `activity.read` | `ACTIVITY_READ` | Auditor, Calidad, Captura, Comercial, Desarrollador, Finanzas, Operador, Tecnico | Declarado y asignado |
| `activity.request_attention` | `ACTIVITY_REQUEST_ATTENTION` | Calidad, Captura, Comercial, Desarrollador, Finanzas, Operador, Tecnico | Declarado y asignado |
| `activity.resolve_attention` | `ACTIVITY_RESOLVE_ATTENTION` | Calidad, Desarrollador, Finanzas | Declarado y asignado |
| `activity.view_audit` | `ACTIVITY_VIEW_AUDIT` | Auditor, Calidad, Desarrollador | Declarado y asignado |
| `activity.write` | `—` | Calidad, Captura, Comercial, Desarrollador, Finanzas, Operador, Tecnico | Usado por roles, ausente de PERMISSIONS |

## audit_logs

| Permiso | Constante | Roles directos | Estado |
|---|---|---|---|
| `audit_logs.read` | `AUDIT_LOGS_READ` | Auditor, Calidad, Desarrollador | Declarado y asignado |

## catalog_items

| Permiso | Constante | Roles directos | Estado |
|---|---|---|---|
| `catalog_items.create` | `CATALOG_ITEMS_CREATE` | Comercial, Desarrollador | Declarado y asignado |
| `catalog_items.delete` | `CATALOG_ITEMS_DELETE` | Comercial, Desarrollador | Declarado y asignado |
| `catalog_items.read` | `CATALOG_ITEMS_READ` | Comercial, Desarrollador | Declarado y asignado |
| `catalog_items.update` | `CATALOG_ITEMS_UPDATE` | Comercial, Desarrollador | Declarado y asignado |

## certificates

| Permiso | Constante | Roles directos | Estado |
|---|---|---|---|
| `certificates.approve` | `CERTIFICATES_APPROVE` | Calidad, Desarrollador | Declarado y asignado |
| `certificates.capture` | `CERTIFICATES_CAPTURE` | Captura, Desarrollador | Declarado y asignado |
| `certificates.create` | `CERTIFICATES_CREATE` | Captura, Desarrollador | Declarado y asignado |
| `certificates.generate` | `—` | Captura | Usado por roles, ausente de PERMISSIONS |
| `certificates.match_override` | `CERTIFICATES_MATCH_OVERRIDE` | Calidad, Desarrollador | Declarado y asignado |
| `certificates.quality` | `—` | Calidad, Desarrollador | Usado por roles, ausente de PERMISSIONS |
| `certificates.read` | `CERTIFICATES_READ` | Calidad, Captura, Desarrollador, Finanzas | Declarado y asignado |
| `certificates.read_own` | `—` | Cliente | Usado por roles, ausente de PERMISSIONS |
| `certificates.release` | `—` | Desarrollador, Finanzas | Usado por roles, ausente de PERMISSIONS |
| `certificates.upload_pdf` | `CERTIFICATES_UPLOAD_PDF` | Captura, Desarrollador | Declarado y asignado |

## clients

| Permiso | Constante | Roles directos | Estado |
|---|---|---|---|
| `clients.create` | `CLIENTS_CREATE` | Comercial, Desarrollador | Declarado y asignado |
| `clients.read` | `CLIENTS_READ` | Captura, Comercial, Desarrollador, Finanzas | Declarado y asignado |
| `clients.update` | `CLIENTS_UPDATE` | Comercial, Desarrollador | Declarado y asignado |

## document_interpretations

| Permiso | Constante | Roles directos | Estado |
|---|---|---|---|
| `document_interpretations.approve` | `DOCUMENT_INTERPRETATIONS_APPROVE` | Calidad, Desarrollador | Declarado y asignado |
| `document_interpretations.create` | `DOCUMENT_INTERPRETATIONS_CREATE` | Calidad, Desarrollador | Declarado y asignado |
| `document_interpretations.read` | `DOCUMENT_INTERPRETATIONS_READ` | Calidad, Captura, Desarrollador, Tecnico | Declarado y asignado |
| `document_interpretations.update` | `DOCUMENT_INTERPRETATIONS_UPDATE` | Calidad, Desarrollador | Declarado y asignado |

## documents

| Permiso | Constante | Roles directos | Estado |
|---|---|---|---|
| `documents.approve` | `DOCUMENTS_APPROVE` | Calidad, Desarrollador | Declarado y asignado |
| `documents.archive` | `DOCUMENTS_ARCHIVE` | Calidad, Desarrollador | Declarado y asignado |
| `documents.create` | `DOCUMENTS_CREATE` | Calidad, Desarrollador | Declarado y asignado |
| `documents.read` | `DOCUMENTS_READ` | Calidad, Captura, Comercial, Desarrollador, Tecnico | Declarado y asignado |
| `documents.update` | `DOCUMENTS_UPDATE` | Calidad, Desarrollador | Declarado y asignado |

## equipment

| Permiso | Constante | Roles directos | Estado |
|---|---|---|---|
| `equipment.create` | `EQUIPMENT_CREATE` | Desarrollador, Tecnico | Declarado y asignado |
| `equipment.delete` | `EQUIPMENT_DELETE` | Desarrollador, Tecnico | Declarado y asignado |
| `equipment.read` | `EQUIPMENT_READ` | Desarrollador, Tecnico | Declarado y asignado |
| `equipment.update` | `EQUIPMENT_UPDATE` | Desarrollador, Tecnico | Declarado y asignado |

## field_sheet_templates

| Permiso | Constante | Roles directos | Estado |
|---|---|---|---|
| `field_sheet_templates.approve` | `FIELD_SHEET_TEMPLATES_APPROVE` | Calidad, Desarrollador | Declarado y asignado |
| `field_sheet_templates.archive` | `FIELD_SHEET_TEMPLATES_ARCHIVE` | Calidad, Desarrollador | Declarado y asignado |
| `field_sheet_templates.create` | `FIELD_SHEET_TEMPLATES_CREATE` | Calidad, Desarrollador | Declarado y asignado |
| `field_sheet_templates.export` | `FIELD_SHEET_TEMPLATES_EXPORT` | Calidad, Desarrollador | Declarado y asignado |
| `field_sheet_templates.import` | `FIELD_SHEET_TEMPLATES_IMPORT` | Calidad, Desarrollador | Declarado y asignado |
| `field_sheet_templates.read` | `FIELD_SHEET_TEMPLATES_READ` | Calidad, Captura, Desarrollador, Tecnico | Declarado y asignado |
| `field_sheet_templates.update` | `FIELD_SHEET_TEMPLATES_UPDATE` | Calidad, Desarrollador | Declarado y asignado |

## field_sheets

| Permiso | Constante | Roles directos | Estado |
|---|---|---|---|
| `field_sheets.create` | `—` | Captura, Tecnico | Usado por roles, ausente de PERMISSIONS |
| `field_sheets.read` | `—` | Calidad, Captura, Tecnico | Usado por roles, ausente de PERMISSIONS |
| `field_sheets.review` | `—` | Calidad, Tecnico | Usado por roles, ausente de PERMISSIONS |
| `field_sheets.update` | `—` | Calidad, Captura, Tecnico | Usado por roles, ausente de PERMISSIONS |

## folios

| Permiso | Constante | Roles directos | Estado |
|---|---|---|---|
| `folios.manage_sequences` | `—` | Desarrollador | Usado por roles, ausente de PERMISSIONS |

## integrations

| Permiso | Constante | Roles directos | Estado |
|---|---|---|---|
| `integrations.facturama.status` | `—` | Finanzas | Usado por roles, ausente de PERMISSIONS |

## invoices

| Permiso | Constante | Roles directos | Estado |
|---|---|---|---|
| `invoices.manage` | `—` | Finanzas | Usado por roles, ausente de PERMISSIONS |
| `invoices.read` | `—` | Finanzas | Usado por roles, ausente de PERMISSIONS |

## metrology

| Permiso | Constante | Roles directos | Estado |
|---|---|---|---|
| `metrology.execute` | `METROLOGY_EXECUTE` | Calidad, Desarrollador | Declarado y asignado |

## operational_engines

| Permiso | Constante | Roles directos | Estado |
|---|---|---|---|
| `operational_engines.execute` | `OPERATIONAL_ENGINES_EXECUTE` | Calidad, Captura, Desarrollador, Tecnico | Declarado y asignado |

## pattern_selection

| Permiso | Constante | Roles directos | Estado |
|---|---|---|---|
| `pattern_selection.execute` | `PATTERN_SELECTION_EXECUTE` | Calidad, Captura, Desarrollador, Tecnico | Declarado y asignado |

## payments

| Permiso | Constante | Roles directos | Estado |
|---|---|---|---|
| `payments.manage` | `—` | Finanzas | Usado por roles, ausente de PERMISSIONS |
| `payments.read` | `—` | Finanzas | Usado por roles, ausente de PERMISSIONS |

## portal

| Permiso | Constante | Roles directos | Estado |
|---|---|---|---|
| `portal.read` | `—` | Cliente | Usado por roles, ausente de PERMISSIONS |

## procedures

| Permiso | Constante | Roles directos | Estado |
|---|---|---|---|
| `procedures.create` | `PROCEDURES_CREATE` | Desarrollador | Declarado y asignado |
| `procedures.delete` | `PROCEDURES_DELETE` | Desarrollador | Declarado y asignado |
| `procedures.read` | `PROCEDURES_READ` | Calidad, Captura, Desarrollador, Tecnico | Declarado y asignado |
| `procedures.update` | `PROCEDURES_UPDATE` | Desarrollador | Declarado y asignado |

## quotations

| Permiso | Constante | Roles directos | Estado |
|---|---|---|---|
| `quotations.act_as_advisor` | `—` | Comercial, Desarrollador | Usado por roles, ausente de PERMISSIONS |
| `quotations.create` | `QUOTATIONS_CREATE` | Comercial | Declarado y asignado |
| `quotations.exceptions.apply_change_service` | `—` | Comercial, Desarrollador | Usado por roles, ausente de PERMISSIONS |
| `quotations.exceptions.apply_unlock` | `—` | Comercial, Desarrollador | Usado por roles, ausente de PERMISSIONS |
| `quotations.exceptions.authorize_change_service` | `—` | Desarrollador | Usado por roles, ausente de PERMISSIONS |
| `quotations.exceptions.authorize_unlock` | `—` | Desarrollador | Usado por roles, ausente de PERMISSIONS |
| `quotations.exceptions.inspect` | `—` | Comercial, Desarrollador | Usado por roles, ausente de PERMISSIONS |
| `quotations.exceptions.inspect_change_service` | `—` | Comercial, Desarrollador | Usado por roles, ausente de PERMISSIONS |
| `quotations.exceptions.rebuild_empty_service_order` | `—` | Comercial, Desarrollador | Usado por roles, ausente de PERMISSIONS |
| `quotations.exceptions.request_change_service` | `—` | Comercial, Desarrollador | Usado por roles, ausente de PERMISSIONS |
| `quotations.exceptions.request_unlock` | `—` | Comercial, Desarrollador | Usado por roles, ausente de PERMISSIONS |
| `quotations.read` | `QUOTATIONS_READ` | Captura, Comercial, Desarrollador, Finanzas | Declarado y asignado |
| `quotations.read_own` | `—` | Cliente | Usado por roles, ausente de PERMISSIONS |
| `quotations.update` | `QUOTATIONS_UPDATE` | Comercial, Desarrollador | Declarado y asignado |

## reference_standard_certificates

| Permiso | Constante | Roles directos | Estado |
|---|---|---|---|
| `reference_standard_certificates.approve` | `REFERENCE_STANDARD_CERTIFICATES_APPROVE` | Calidad, Desarrollador | Declarado y asignado |
| `reference_standard_certificates.create` | `REFERENCE_STANDARD_CERTIFICATES_CREATE` | Calidad, Desarrollador | Declarado y asignado |
| `reference_standard_certificates.delete` | `REFERENCE_STANDARD_CERTIFICATES_DELETE` | Calidad, Desarrollador | Declarado y asignado |
| `reference_standard_certificates.read` | `REFERENCE_STANDARD_CERTIFICATES_READ` | Calidad, Captura, Desarrollador, Tecnico | Declarado y asignado |
| `reference_standard_certificates.update` | `REFERENCE_STANDARD_CERTIFICATES_UPDATE` | Calidad, Desarrollador | Declarado y asignado |

## release

| Permiso | Constante | Roles directos | Estado |
|---|---|---|---|
| `release.manage` | `—` | Desarrollador, Finanzas | Usado por roles, ausente de PERMISSIONS |

## resolution_center

| Permiso | Constante | Roles directos | Estado |
|---|---|---|---|
| `resolution_center.*` | `—` | Desarrollador | Usado por roles, ausente de PERMISSIONS |
| `resolution_center.analyze` | `RESOLUTION_CENTER_ANALYZE` | Operador | Declarado y asignado |
| `resolution_center.audit` | `RESOLUTION_CENTER_AUDIT` | Auditor | Declarado y asignado |
| `resolution_center.authorize` | `RESOLUTION_CENTER_AUTHORIZE` | — | Declarado sin asignación directa |
| `resolution_center.create` | `RESOLUTION_CENTER_CREATE` | Operador | Declarado y asignado |
| `resolution_center.execute` | `RESOLUTION_CENTER_EXECUTE` | Operador | Declarado y asignado |
| `resolution_center.infrastructure` | `RESOLUTION_CENTER_INFRASTRUCTURE` | Auditor | Declarado y asignado |
| `resolution_center.plan` | `RESOLUTION_CENTER_PLAN` | Operador | Declarado y asignado |
| `resolution_center.prepare` | `RESOLUTION_CENTER_PREPARE` | Operador | Declarado y asignado |
| `resolution_center.read` | `RESOLUTION_CENTER_READ` | Auditor, Calidad, Captura, Comercial, Finanzas, Operador, Tecnico | Declarado y asignado |
| `resolution_center.read_all` | `RESOLUTION_CENTER_READ_ALL` | Auditor | Declarado y asignado |
| `resolution_center.simulate` | `RESOLUTION_CENTER_SIMULATE` | Operador | Declarado y asignado |

## sat_catalogs

| Permiso | Constante | Roles directos | Estado |
|---|---|---|---|
| `sat_catalogs.manage` | `SAT_CATALOGS_MANAGE` | Desarrollador | Declarado y asignado |
| `sat_catalogs.manage_aliases` | `SAT_CATALOGS_MANAGE_ALIASES` | Comercial, Finanzas | Declarado y asignado |
| `sat_catalogs.manage_favorites` | `SAT_CATALOGS_MANAGE_FAVORITES` | Comercial, Finanzas | Declarado y asignado |
| `sat_catalogs.read` | `SAT_CATALOGS_READ` | Comercial, Desarrollador, Finanzas | Declarado y asignado |

## service_orders

| Permiso | Constante | Roles directos | Estado |
|---|---|---|---|
| `service_orders.additional_equipment.audit` | `SERVICE_ORDERS_ADDITIONAL_EQUIPMENT_AUDIT` | Auditor, Desarrollador | Declarado y asignado |
| `service_orders.additional_equipment.authorize` | `SERVICE_ORDERS_ADDITIONAL_EQUIPMENT_AUTHORIZE` | Calidad, Desarrollador | Declarado y asignado |
| `service_orders.additional_equipment.commercial_review` | `SERVICE_ORDERS_ADDITIONAL_EQUIPMENT_COMMERCIAL_REVIEW` | Comercial, Desarrollador | Declarado y asignado |
| `service_orders.additional_equipment.execute` | `SERVICE_ORDERS_ADDITIONAL_EQUIPMENT_EXECUTE` | Desarrollador, Operador, Tecnico | Declarado y asignado |
| `service_orders.additional_equipment.propose` | `SERVICE_ORDERS_ADDITIONAL_EQUIPMENT_PROPOSE` | Comercial, Desarrollador, Operador, Tecnico | Declarado y asignado |
| `service_orders.create` | `SERVICE_ORDERS_CREATE` | Comercial, Desarrollador | Declarado y asignado |
| `service_orders.read` | `SERVICE_ORDERS_READ` | Calidad, Captura, Comercial, Desarrollador, Finanzas, Tecnico | Declarado y asignado |
| `service_orders.read_own` | `—` | Cliente | Usado por roles, ausente de PERMISSIONS |
| `service_orders.sign` | `SERVICE_ORDERS_SIGN` | Desarrollador, Tecnico | Declarado y asignado |
| `service_orders.signatures.reopen` | `SERVICE_ORDERS_SIGNATURES_REOPEN` | Calidad, Desarrollador | Declarado y asignado |
| `service_orders.update` | `SERVICE_ORDERS_UPDATE` | Comercial, Desarrollador, Tecnico | Declarado y asignado |

## services

| Permiso | Constante | Roles directos | Estado |
|---|---|---|---|
| `services.manage_certificate_prefix` | `—` | Comercial, Desarrollador | Usado por roles, ausente de PERMISSIONS |
| `services.manage_linked_company` | `—` | Comercial, Desarrollador | Usado por roles, ausente de PERMISSIONS |
| `services.manage_service_type` | `—` | Comercial, Desarrollador | Usado por roles, ausente de PERMISSIONS |

## settings

| Permiso | Constante | Roles directos | Estado |
|---|---|---|---|
| `settings.institutional.read` | `SETTINGS_INSTITUTIONAL_READ` | Calidad, Desarrollador | Declarado y asignado |
| `settings.institutional.update` | `SETTINGS_INSTITUTIONAL_UPDATE` | Calidad, Desarrollador | Declarado y asignado |
| `settings.manage` | `—` | Desarrollador | Usado por roles, ausente de PERMISSIONS |
| `settings.master_catalogs.manage` | `SETTINGS_MASTER_CATALOGS_MANAGE` | Desarrollador | Declarado y asignado |
| `settings.read` | `—` | Desarrollador | Usado por roles, ausente de PERMISSIONS |
| `settings.system_parameters.read` | `SETTINGS_SYSTEM_PARAMETERS_READ` | Desarrollador | Declarado y asignado |
| `settings.system_parameters.update` | `SETTINGS_SYSTEM_PARAMETERS_UPDATE` | Desarrollador | Declarado y asignado |

## standards

| Permiso | Constante | Roles directos | Estado |
|---|---|---|---|
| `standards.create` | `STANDARDS_CREATE` | Desarrollador | Declarado y asignado |
| `standards.delete` | `STANDARDS_DELETE` | Desarrollador | Declarado y asignado |
| `standards.read` | `STANDARDS_READ` | Calidad, Captura, Desarrollador, Tecnico | Declarado y asignado |
| `standards.update` | `STANDARDS_UPDATE` | Desarrollador | Declarado y asignado |

## technical_profiles

| Permiso | Constante | Roles directos | Estado |
|---|---|---|---|
| `technical_profiles.approve` | `TECHNICAL_PROFILES_APPROVE` | Calidad, Desarrollador | Declarado y asignado |
| `technical_profiles.create` | `TECHNICAL_PROFILES_CREATE` | Calidad, Desarrollador | Declarado y asignado |
| `technical_profiles.read` | `TECHNICAL_PROFILES_READ` | Calidad, Captura, Desarrollador, Tecnico | Declarado y asignado |
| `technical_profiles.update` | `TECHNICAL_PROFILES_UPDATE` | Calidad, Desarrollador | Declarado y asignado |

## uncertainty

| Permiso | Constante | Roles directos | Estado |
|---|---|---|---|
| `uncertainty.execute` | `UNCERTAINTY_EXECUTE` | Calidad, Captura, Desarrollador, Tecnico | Declarado y asignado |

## uncertainty_models

| Permiso | Constante | Roles directos | Estado |
|---|---|---|---|
| `uncertainty_models.approve` | `UNCERTAINTY_MODELS_APPROVE` | Calidad, Desarrollador | Declarado y asignado |
| `uncertainty_models.create` | `UNCERTAINTY_MODELS_CREATE` | Calidad, Desarrollador | Declarado y asignado |
| `uncertainty_models.exception` | `UNCERTAINTY_MODELS_EXCEPTION` | Calidad, Desarrollador | Declarado y asignado |
| `uncertainty_models.read` | `UNCERTAINTY_MODELS_READ` | Calidad, Desarrollador | Declarado y asignado |
| `uncertainty_models.update` | `UNCERTAINTY_MODELS_UPDATE` | Calidad, Desarrollador | Declarado y asignado |

## users

| Permiso | Constante | Roles directos | Estado |
|---|---|---|---|
| `users.manage` | `USERS_MANAGE` | Desarrollador | Declarado y asignado |
| `users.read` | `USERS_READ` | Desarrollador | Declarado y asignado |

## Comodines de autoridad

- `*`: asignado a **Administrador**, otorga acceso global.
- `resolution_center.*`: asignado a **Desarrollador**, otorga autoridad sobre el Centro de Resoluciones mediante el control de comodines.
