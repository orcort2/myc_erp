# Snapshot técnico de capacidades, acciones, microacciones y permisos del ERP MYC

> Corte técnico: 2026-08-04
>
> Fuente primaria: backend `app(22).zip`, incluyendo routers, schemas, servicios y política transversal de acceso de la Etapa 1.
>
> Estado: VIGENTE COMO SNAPSHOT TÉCNICO; sustituido como autoridad funcional por
> [`CATALOGO_INSTITUCIONAL_FUNCIONAL_ERP_MYC.md`](CATALOGO_INSTITUCIONAL_FUNCIONAL_ERP_MYC.md).
> Distingue operaciones existentes y permisos granulares propuestos; no afirma
> que todos los permisos propuestos estén implementados ni autoriza aplicarlos
> automáticamente.

> Límite de autoridad: conserva el inventario reproducible de ETAPA 2B y debe
> reconciliarse con `permissions.py`, el inventario
> FastAPI vigente y las reglas de ownership antes de aprobar claves. La matriz
> actual continúa como bootstrap y compatibilidad temporal. Sus 493 filas de
> campos no son microacciones institucionales aprobadas.

## Resumen

- Módulos o superficies clasificadas: **36**
- Agrupaciones de acción: **213**
- Microacciones totales revisadas: **798**
- Operaciones HTTP inventariadas como microacciones existentes: **305**
- Clases de schema inspeccionadas: **233**
- Microacciones de campo propuestas: **493**
- Permisos institucionales propuestos únicos: **658**

Snapshot de consistencia reproducible contra el bootstrap del 2026-08-04:

- Permisos efectivos únicos declarados por `permissions.py`: **140**
- Permisos actuales que coinciden con una propuesta institucional: **61**
- Permisos actuales pendientes de reconciliación funcional: **79**
- Permisos mínimos únicos usados por el inventario HTTP: **72**
- Permisos HTTP actuales pendientes de reconciliación con el catálogo: **20**
- Permisos HTTP catalogados sin declaración bootstrap explícita: **1**
- Permisos propuestos aún no implementados: **597**

## Convención

- **Módulo:** superficie funcional donde vive el comportamiento.
- **Acción:** agrupación institucional de capacidades relacionadas.
- **Microacción:** operación concreta que el sistema ejecuta o campo sensible que puede modificarse.
- **Permiso propuesto:** clave granular recomendada para Ajustes, roles, overrides individuales y Tickets.
- **Origen:** endpoint o schema que demuestra que la microacción existe o que el backend acepta el campo.

## Reglas de uso

1. Un permiso habilita una microacción; las reglas de estado, ownership y negocio siguen siendo obligatorias.
2. El frontend usa permisos para visibilidad y edición; el backend conserva la autoridad.
3. Los permisos heredados por rol pueden recibir `allow` o `deny` individual, salvo prohibiciones institucionales no delegables.
4. Una autorización por Ticket debe ser temporal, contextual y consumible; no reemplaza un permiso permanente.
5. Las microacciones sensibles deben exigir motivo, auditoría o Actividad según su gobierno posterior.

## Gobierno obligatorio desde la Etapa 2

Toda funcionalidad nueva debe clasificarse antes de implementarse mediante la
jerarquía `Módulo → Acción → Microacción`. Ningún permiso nuevo puede agregarse
directamente a `permissions.py`: primero debe existir aquí, superar revisión
funcional y quedar aprobado como permiso institucional. Sólo después puede
incorporarse al bootstrap, asignarse a roles y llegar a usuarios.

```text
Catálogo Institucional
        ↓
Revisión funcional
        ↓
Permiso institucional
        ↓
permissions.py (bootstrap temporal)
        ↓
Roles / grupos
        ↓
Usuarios
```

El catálogo no genera código. Ownership, scopes, denegaciones, temporalidad y
protecciones críticas son dimensiones adicionales de autorización y nunca se
reducen a mostrar u ocultar elementos frontend. Las diferencias verificadas
contra el bootstrap y el guard HTTP se mantienen en
[`security/CAPABILITY_MODEL_GAPS_2026-08-04.md`](security/CAPABILITY_MODEL_GAPS_2026-08-04.md).

# 1. API pública del Motor

## 1.1. Consultar

| Microacción | Método y ruta | Permiso propuesto | Estado |
|---|---|---|---|
| Resolution | `GET /public/resolution-engine/v1/resolutions/{resolution_id}` | `resolution_public_api.read` | Existe en backend |

## 1.2. Crear

| Microacción | Método y ruta | Permiso propuesto | Estado |
|---|---|---|---|
| Resolution | `POST /public/resolution-engine/v1/resolutions` | `resolution_public_api.create` | Existe en backend |

## 1.3. Listar

| Microacción | Método y ruta | Permiso propuesto | Estado |
|---|---|---|---|
| List resolutions | `GET /public/resolution-engine/v1/resolutions` | `resolution_public_api.read` | Existe en backend |

## 1.4. Operar recurso

| Microacción | Método y ruta | Permiso propuesto | Estado |
|---|---|---|---|
| Developer portal | `GET /developers/resolution-engine` | `resolution_public_api.read` | Existe en backend |
| Capabilities | `GET /public/resolution-engine/v1/capabilities` | `resolution_public_api.read` | Existe en backend |

# 2. Actividad

## 2.1. Consultar

| Microacción | Método y ruta | Permiso propuesto | Estado |
|---|---|---|---|
| Entities | `GET /activity/entities` | `activity.read` | Existe en backend |
| Inbox | `GET /activity/inbox` | `activity.read` | Existe en backend |
| Mentionable users | `GET /activity/mentionable-users` | `activity.read` | Existe en backend |
| Resolution target | `GET /activity/resolution-target/{public_id}` | `activity.read` | Existe en backend |
| Entity activity | `GET /activity/{entity_type}/{entity_id}` | `activity.read` | Existe en backend |

## 2.2. Crear

| Microacción | Método y ruta | Permiso propuesto | Estado |
|---|---|---|---|
| Entity read | `POST /activity/{entity_type}/{entity_id}/read` | `activity.create` | Existe en backend |

## 2.3. Gestionar adjuntos

| Microacción | Método y ruta | Permiso propuesto | Estado |
|---|---|---|---|
| Download attachment | `GET /activity/attachments/{attachment_id}/download` | `activity.attachments.manage` | Existe en backend |
| Preview attachment | `GET /activity/attachments/{attachment_id}/preview` | `activity.attachments.manage` | Existe en backend |
| Attachment | `POST /activity/messages/{message_id}/attachments` | `activity.attachments.manage` | Existe en backend |

## 2.4. Gestionar atención

| Microacción | Método y ruta | Permiso propuesto | Estado |
|---|---|---|---|
| Attention resolve | `POST /activity/attention/{attention_id}/resolve` | `activity.attention.resolve` | Existe en backend |
| Attention | `POST /activity/messages/{message_id}/attention` | `activity.attention.request` | Existe en backend |

## 2.5. Gestionar mensajes

| Microacción | Método y ruta | Permiso propuesto | Estado |
|---|---|---|---|
| Message | `DELETE /activity/messages/{message_id}` | `activity.messages.manage` | Existe en backend |
| Message | `PATCH /activity/messages/{message_id}` | `activity.messages.manage` | Existe en backend |
| Withdraw | `POST /activity/messages/{message_id}/withdraw` | `activity.create` | Existe en backend |
| Message | `POST /activity/{entity_type}/{entity_id}/messages` | `activity.messages.manage` | Existe en backend |

## 2.6. Editar campos y atributos

| Microacción de campo | Permiso propuesto | Evidencia | Estado |
|---|---|---|---|
| Modificar assigned area | `activity.fields.assigned_area.update` | `ActivityAttentionCreate.assigned_area` | Requiere granularización |
| Modificar assigned user id | `activity.fields.assigned_user_id.update` | `ActivityAttentionCreate.assigned_user_id` | Requiere granularización |
| Modificar body | `activity.fields.body.update` | `ActivityMessageCreate.body` | Requiere granularización |
| Modificar entity | `activity.fields.entity.update` | `ActivityInboxItemRead.entity` | Requiere granularización |
| Modificar last message | `activity.fields.last_message.update` | `ActivityInboxItemRead.last_message` | Requiere granularización |
| Modificar mentioned user ids | `activity.fields.mentioned_user_ids.update` | `ActivityMessageCreate.mentioned_user_ids` | Requiere granularización |
| Modificar pending attention count | `activity.fields.pending_attention_count.update` | `ActivityInboxItemRead.pending_attention_count` | Requiere granularización |
| Modificar priority | `activity.fields.priority.update` | `ActivityAttentionCreate.priority` | Requiere granularización |
| Modificar thread id | `activity.fields.thread_id.update` | `ActivityInboxItemRead.thread_id` | Requiere granularización |
| Modificar unread count | `activity.fields.unread_count.update` | `ActivityInboxItemRead.unread_count` | Requiere granularización |
| Registrar motivo | `activity.fields.reason.update` | `ActivityMessageUpdate.reason` | Requiere granularización |

# 3. Ajustes · Identidad institucional

## 3.1. Consultar

| Microacción | Método y ruta | Permiso propuesto | Estado |
|---|---|---|---|
| Configuration | `GET /institutional-configuration` | `settings.institutional.read` | Existe en backend |

## 3.2. Modificar

| Microacción | Método y ruta | Permiso propuesto | Estado |
|---|---|---|---|
| Configuration | `PATCH /institutional-configuration` | `settings.institutional.update` | Existe en backend |

## 3.3. Editar campos y atributos

| Microacción de campo | Permiso propuesto | Evidencia | Estado |
|---|---|---|---|
| Cambiar logotipo | `settings.institutional.fields.logo_path.update` | `InstitutionalConfigurationUpdate.logo_path` | Requiere granularización |
| Modificar correo | `settings.institutional.fields.email.update` | `InstitutionalConfigurationUpdate.email` | Requiere granularización |
| Modificar document code | `settings.institutional.fields.document_code.update` | `InstitutionalConfigurationUpdate.document_code` | Requiere granularización |
| Modificar domicilio | `settings.institutional.fields.address.update` | `InstitutionalConfigurationUpdate.address` | Requiere granularización |
| Modificar initial revision | `settings.institutional.fields.initial_revision.update` | `InstitutionalConfigurationUpdate.initial_revision` | Requiere granularización |
| Modificar teléfono | `settings.institutional.fields.phone.update` | `InstitutionalConfigurationUpdate.phone` | Requiere granularización |

## 3.4. Gestionar identidad fiscal y legal

| Microacción de campo | Permiso propuesto | Evidencia | Estado |
|---|---|---|---|
| Modificar razón social | `settings.institutional.fields.legal_name.update` | `InstitutionalConfigurationUpdate.legal_name` | Requiere granularización |

# 4. Auditoría

## 4.1. Consultar

| Microacción | Método y ruta | Permiso propuesto | Estado |
|---|---|---|---|
| Audit logs | `GET /audit-logs` | `audit_logs.read` | Existe en backend |

# 5. Autenticación

## 5.1. Gestionar estado

| Microacción | Método y ruta | Permiso propuesto | Estado |
|---|---|---|---|
| Registration status | `GET /auth/registration-status` | `auth.read` | Existe en backend |

## 5.2. Operar recurso

| Microacción | Método y ruta | Permiso propuesto | Estado |
|---|---|---|---|
| Login | `POST /auth/login` | `auth.create` | Existe en backend |
| Me | `GET /auth/me` | `auth.read` | Existe en backend |
| Refresh | `POST /auth/refresh` | `auth.create` | Existe en backend |

## 5.3. Registrar

| Microacción | Método y ruta | Permiso propuesto | Estado |
|---|---|---|---|
| Register | `POST /auth/register` | `auth.create` | Existe en backend |

## 5.4. Editar campos y atributos

| Microacción de campo | Permiso propuesto | Evidencia | Estado |
|---|---|---|---|
| Modificar refresh token | `auth.fields.refresh_token.update` | `RefreshTokenRequest.refresh_token` | Requiere granularización |

# 6. Catálogo de servicios

## 6.1. Consultar

| Microacción | Método y ruta | Permiso propuesto | Estado |
|---|---|---|---|
| Catalog items | `GET /catalog-items` | `catalog_items.read` | Existe en backend |
| Linked companies | `GET /catalog-items/linked-companies` | `catalog_items.read` | Existe en backend |
| Catalog item | `GET /catalog-items/{catalog_item_id}` | `catalog_items.read` | Existe en backend |

## 6.2. Crear

| Microacción | Método y ruta | Permiso propuesto | Estado |
|---|---|---|---|
| Catalog item | `POST /catalog-items` | `catalog_items.create` | Existe en backend |
| Linked company | `POST /catalog-items/linked-companies` | `catalog_items.create` | Existe en backend |

## 6.3. Eliminar

| Microacción | Método y ruta | Permiso propuesto | Estado |
|---|---|---|---|
| Catalog item | `DELETE /catalog-items/{catalog_item_id}` | `catalog_items.delete` | Existe en backend |

## 6.4. Modificar

| Microacción | Método y ruta | Permiso propuesto | Estado |
|---|---|---|---|
| Catalog item | `PATCH /catalog-items/{catalog_item_id}` | `catalog_items.update` | Existe en backend |

## 6.5. Editar campos y atributos

| Microacción de campo | Permiso propuesto | Evidencia | Estado |
|---|---|---|---|
| Modificar abbreviation | `catalog_items.fields.abbreviation.update` | `LinkedCompanyCreate.abbreviation` | Requiere granularización |
| Modificar calibration scope | `catalog_items.fields.calibration_scope.update` | `CatalogItemBase.calibration_scope` | Requiere granularización |
| Modificar cantidad | `catalog_items.fields.quantity.update` | `CatalogItemComponentCreate.quantity` | Requiere granularización |
| Modificar category | `catalog_items.fields.category.update` | `CatalogItemBase.category` | Requiere granularización |
| Modificar commodity | `catalog_items.fields.commodity.update` | `CatalogItemBase.commodity` | Requiere granularización |
| Modificar component internal key | `catalog_items.fields.component_internal_key.update` | `CatalogItemComponentOut.component_internal_key` | Requiere granularización |
| Modificar component name | `catalog_items.fields.component_name.update` | `CatalogItemComponentOut.component_name` | Requiere granularización |
| Modificar component service kind | `catalog_items.fields.component_service_kind.update` | `CatalogItemComponentOut.component_service_kind` | Requiere granularización |
| Modificar components | `catalog_items.fields.components.update` | `CatalogItemCreate.components` | Requiere granularización |
| Modificar custom internal unit | `catalog_items.fields.custom_internal_unit.update` | `CatalogItemBase.custom_internal_unit` | Requiere granularización |
| Modificar descripción | `catalog_items.fields.description.update` | `CatalogItemBase.description` | Requiere granularización |
| Modificar expected certificate master id | `catalog_items.fields.expected_certificate_master_id.update` | `CatalogItemBase.expected_certificate_master_id` | Requiere granularización |
| Modificar internal key | `catalog_items.fields.internal_key.update` | `CatalogItemOut.internal_key` | Requiere granularización |
| Modificar internal unit | `catalog_items.fields.internal_unit.update` | `CatalogItemBase.internal_unit` | Requiere granularización |
| Modificar item type | `catalog_items.fields.item_type.update` | `CatalogItemBase.item_type` | Requiere granularización |
| Modificar name | `catalog_items.fields.name.update` | `CatalogItemBase.name` | Requiere granularización |
| Modificar notas | `catalog_items.fields.notes.update` | `LinkedCompanyCreate.notes` | Requiere granularización |
| Modificar quotation legend | `catalog_items.fields.quotation_legend.update` | `CatalogItemBase.quotation_legend` | Requiere granularización |
| Modificar sat key | `catalog_items.fields.sat_key.update` | `CatalogItemBase.sat_key` | Requiere granularización |
| Modificar sat unit | `catalog_items.fields.sat_unit.update` | `CatalogItemBase.sat_unit` | Requiere granularización |
| Modificar service kind | `catalog_items.fields.service_kind.update` | `CatalogItemBase.service_kind` | Requiere granularización |

## 6.6. Gestionar acceso y seguridad

| Microacción de campo | Permiso propuesto | Evidencia | Estado |
|---|---|---|---|
| Activar o desactivar | `catalog_items.fields.is_active.update` | `CatalogItemOut.is_active` | Requiere granularización |

## 6.7. Gestionar identidad fiscal y legal

| Microacción de campo | Permiso propuesto | Evidencia | Estado |
|---|---|---|---|
| Modificar razón social | `catalog_items.fields.legal_name.update` | `LinkedCompanyCreate.legal_name` | Requiere granularización |

## 6.8. Redefinir clasificación y alcance

| Microacción de campo | Permiso propuesto | Evidencia | Estado |
|---|---|---|---|
| Cambiar empresa vinculada | `catalog_items.fields.linked_company_id.update` | `CatalogItemBase.linked_company_id` | Requiere granularización |
| Cambiar tipo de servicio | `catalog_items.fields.service_type.update` | `CatalogItemBase.service_type` | Requiere granularización |
| Modificar component catalog item id | `catalog_items.fields.component_catalog_item_id.update` | `CatalogItemComponentCreate.component_catalog_item_id` | Requiere granularización |
| Modificar default certificate prefix | `catalog_items.fields.default_certificate_prefix.update` | `LinkedCompanyCreate.default_certificate_prefix` | Requiere granularización |
| Modificar linked certificate prefix | `catalog_items.fields.linked_certificate_prefix.update` | `CatalogItemBase.linked_certificate_prefix` | Requiere granularización |

## 6.9. Redefinir condiciones económicas

| Microacción de campo | Permiso propuesto | Evidencia | Estado |
|---|---|---|---|
| Modificar cost currency | `catalog_items.fields.cost_currency.update` | `CatalogItemBase.cost_currency` | Requiere granularización |
| Modificar costo interno | `catalog_items.fields.internal_cost.update` | `CatalogItemBase.internal_cost` | Requiere granularización |
| Modificar final price mxn | `catalog_items.fields.final_price_mxn.update` | `CatalogItemBase.final_price_mxn` | Requiere granularización |
| Modificar margen | `catalog_items.fields.margin_percent.update` | `CatalogItemBase.margin_percent` | Requiere granularización |
| Modificar origin currency | `catalog_items.fields.origin_currency.update` | `CatalogItemBase.origin_currency` | Requiere granularización |
| Modificar origin price | `catalog_items.fields.origin_price.update` | `CatalogItemBase.origin_price` | Requiere granularización |
| Modificar tasa de impuesto | `catalog_items.fields.tax_rate.update` | `CatalogItemBase.tax_rate` | Requiere granularización |
| Modificar tax object | `catalog_items.fields.tax_object.update` | `CatalogItemBase.tax_object` | Requiere granularización |
| Modificar tipo de cambio | `catalog_items.fields.exchange_rate.update` | `CatalogItemBase.exchange_rate` | Requiere granularización |

# 7. Catálogos SAT

## 7.1. Consultar

| Microacción | Método y ruta | Permiso propuesto | Estado |
|---|---|---|---|
| Sat catalogs | `GET /sat-catalogs` | `sat_catalogs.read` | Existe en backend |
| Aliases | `GET /sat-catalogs/records/{record_id}/aliases` | `sat_catalogs.read` | Existe en backend |
| Sat catalog records | `GET /sat-catalogs/{catalog_code}/records` | `sat_catalogs.read` | Existe en backend |

## 7.2. Crear

| Microacción | Método y ruta | Permiso propuesto | Estado |
|---|---|---|---|
| Alias | `POST /sat-catalogs/records/{record_id}/aliases` | `sat_catalogs.create` | Existe en backend |
| Favorite | `POST /sat-catalogs/records/{record_id}/favorite` | `sat_catalogs.create` | Existe en backend |

## 7.3. Eliminar

| Microacción | Método y ruta | Permiso propuesto | Estado |
|---|---|---|---|
| Favorite | `DELETE /sat-catalogs/records/{record_id}/favorite` | `sat_catalogs.delete` | Existe en backend |

## 7.4. Gestionar versiones

| Microacción | Método y ruta | Permiso propuesto | Estado |
|---|---|---|---|
| Sat catalog versions | `GET /sat-catalogs/{catalog_code}/versions` | `sat_catalogs.read` | Existe en backend |

## 7.5. Operar recurso

| Microacción | Método y ruta | Permiso propuesto | Estado |
|---|---|---|---|
| Remove alias | `DELETE /sat-catalogs/aliases/{alias_id}` | `sat_catalogs.delete` | Existe en backend |

# 8. Certificados

## 8.1. Gestionar certificados

| Microacción | Método y ruta | Permiso propuesto | Estado |
|---|---|---|---|
| Certificates | `GET /certificates` | `certificates.read` | Existe en backend |
| Certificate | `POST /certificates` | `certificates.create` | Existe en backend |
| Capture master readiness list | `GET /certificates/capture-master-readiness` | `certificates.read` | Existe en backend |
| Certificate release readiness | `GET /certificates/release-readiness/{service_order_id}` | `certificates.read` | Existe en backend |
| Certificate | `DELETE /certificates/{certificate_id}` | `certificates.delete` | Existe en backend |
| Certificate | `GET /certificates/{certificate_id}` | `certificates.read` | Existe en backend |
| Certificate | `PATCH /certificates/{certificate_id}` | `certificates.update` | Existe en backend |
| Approve certificate | `POST /certificates/{certificate_id}/approve` | `certificates.approve` | Existe en backend |
| Authenticate certificate | `POST /certificates/{certificate_id}/authenticate` | `certificates.authenticate` | Existe en backend |
| Authenticated certificate pdf | `GET /certificates/{certificate_id}/authenticated-pdf` | `certificates.documents.download` | Existe en backend |
| Download certificate capture master | `GET /certificates/{certificate_id}/capture-master` | `certificates.documents.download` | Existe en backend |
| Return certificate to draft | `POST /certificates/{certificate_id}/draft` | `certificates.quality.return` | Existe en backend |
| Generate certificate | `POST /certificates/{certificate_id}/generate` | `certificates.create` | Existe en backend |
| Manual accept certificate match | `POST /certificates/{certificate_id}/manual-accept-match` | `certificates.match.override` | Existe en backend |
| Original certificate pdf | `GET /certificates/{certificate_id}/original-pdf` | `certificates.documents.download` | Existe en backend |
| Quality certificate | `POST /certificates/{certificate_id}/quality` | `certificates.create` | Existe en backend |
| Quality approve certificate | `POST /certificates/{certificate_id}/quality-approve` | `certificates.quality.approve` | Existe en backend |
| Quality reject certificate | `POST /certificates/{certificate_id}/quality-reject` | `certificates.quality.reject` | Existe en backend |
| Release certificate | `POST /certificates/{certificate_id}/release` | `certificates.release` | Existe en backend |
| Release certificate to client | `POST /certificates/{certificate_id}/release-to-client` | `certificates.release` | Existe en backend |
| Request certificate correction | `POST /certificates/{certificate_id}/request-correction` | `certificates.correction.request` | Existe en backend |
| Return certificate to technician | `POST /certificates/{certificate_id}/return-to-technician` | `certificates.quality.return` | Existe en backend |
| Send certificate to quality | `POST /certificates/{certificate_id}/send-to-quality` | `certificates.create` | Existe en backend |
| Start certificate capture | `POST /certificates/{certificate_id}/start-capture` | `certificates.create` | Existe en backend |
| Suspend certificate | `POST /certificates/{certificate_id}/suspend` | `certificates.suspend` | Existe en backend |
| Upload certificate final pdf | `POST /certificates/{certificate_id}/upload-pdf` | `certificates.create` | Existe en backend |
| Validate certificate pdf match | `POST /certificates/{certificate_id}/validate-pdf-match` | `certificates.create` | Existe en backend |

## 8.2. Editar campos y atributos

| Microacción de campo | Permiso propuesto | Evidencia | Estado |
|---|---|---|---|
| Modificar authenticated pdf path | `certificates.fields.authenticated_pdf_path.update` | `CertificateBatchActionItemRead.authenticated_pdf_path` | Requiere granularización |
| Modificar certificate id | `certificates.fields.certificate_id.update` | `CertificateBatchActionItemRead.certificate_id` | Requiere granularización |
| Modificar comment | `certificates.fields.comment.update` | `CertificateStatusChange.comment` | Requiere granularización |
| Modificar error | `certificates.fields.error.update` | `CertificateBatchActionItemRead.error` | Requiere granularización |
| Modificar expected folio | `certificates.fields.expected_folio.update` | `CertificateUpdate.expected_folio` | Requiere granularización |
| Modificar folio | `certificates.fields.folio.update` | `CertificateBatchActionItemRead.folio` | Requiere granularización |
| Modificar issued on | `certificates.fields.issued_on.update` | `CertificateUpdate.issued_on` | Requiere granularización |
| Modificar notas | `certificates.fields.notes.update` | `CertificateUpdate.notes` | Requiere granularización |
| Modificar title | `certificates.fields.title.update` | `CertificateUpdate.title` | Requiere granularización |
| Registrar motivo | `certificates.fields.reason.update` | `CertificateStatusChange.reason` | Requiere granularización |

## 8.3. Gestionar estado

| Microacción de campo | Permiso propuesto | Evidencia | Estado |
|---|---|---|---|
| Modificar estado | `certificates.fields.status.update` | `CertificateBatchActionItemRead.status` | Requiere granularización |

# 9. Certificados de patrones

## 9.1. Gestionar certificados

| Microacción | Método y ruta | Permiso propuesto | Estado |
|---|---|---|---|
| Reference standard certificates | `GET /reference-standard-certificates` | `reference_standard_certificates.read` | Existe en backend |
| Reference standard certificate uncertainty | `DELETE /reference-standard-certificates/uncertainties/{uncertainty_id}` | `reference_standard_certificates.delete` | Existe en backend |
| Reference standard certificate uncertainty | `PATCH /reference-standard-certificates/uncertainties/{uncertainty_id}` | `reference_standard_certificates.update` | Existe en backend |
| Reference standard certificate | `GET /reference-standard-certificates/{certificate_id}` | `reference_standard_certificates.read` | Existe en backend |
| Reference standard certificate | `PATCH /reference-standard-certificates/{certificate_id}` | `reference_standard_certificates.update` | Existe en backend |
| Activate reference standard certificate | `POST /reference-standard-certificates/{certificate_id}/activate` | `reference_standard_certificates.activate` | Existe en backend |
| Suspend reference standard certificate | `POST /reference-standard-certificates/{certificate_id}/suspend` | `reference_standard_certificates.suspend` | Existe en backend |
| Reference standard certificate uncertainty | `POST /reference-standard-certificates/{certificate_id}/uncertainties` | `reference_standard_certificates.create` | Existe en backend |
| Reference standard certificate | `POST /reference-standards/{standard_id}/certificates` | `reference_standard_certificates.create` | Existe en backend |

## 9.2. Editar campos y atributos

| Microacción de campo | Permiso propuesto | Evidencia | Estado |
|---|---|---|---|
| Modificar accreditation body | `reference_standard_certificates.fields.accreditation_body.update` | `ReferenceStandardCertificateUpdate.accreditation_body` | Requiere granularización |
| Modificar accreditation number | `reference_standard_certificates.fields.accreditation_number.update` | `ReferenceStandardCertificateUpdate.accreditation_number` | Requiere granularización |
| Modificar calibration date | `reference_standard_certificates.fields.calibration_date.update` | `ReferenceStandardCertificateUpdate.calibration_date` | Requiere granularización |
| Modificar certificate number | `reference_standard_certificates.fields.certificate_number.update` | `ReferenceStandardCertificateUpdate.certificate_number` | Requiere granularización |
| Modificar confidence level | `reference_standard_certificates.fields.confidence_level.update` | `ReferenceStandardCertificateUncertaintyUpdate.confidence_level` | Requiere granularización |
| Modificar controlled document id | `reference_standard_certificates.fields.controlled_document_id.update` | `ReferenceStandardCertificateUpdate.controlled_document_id` | Requiere granularización |
| Modificar controlled document version id | `reference_standard_certificates.fields.controlled_document_version_id.update` | `ReferenceStandardCertificateUpdate.controlled_document_version_id` | Requiere granularización |
| Modificar distribution | `reference_standard_certificates.fields.distribution.update` | `ReferenceStandardCertificateUncertaintyUpdate.distribution` | Requiere granularización |
| Modificar environmental conditions | `reference_standard_certificates.fields.environmental_conditions.update` | `ReferenceStandardCertificateUpdate.environmental_conditions` | Requiere granularización |
| Modificar expiration date | `reference_standard_certificates.fields.expiration_date.update` | `ReferenceStandardCertificateUpdate.expiration_date` | Requiere granularización |
| Modificar formula reference | `reference_standard_certificates.fields.formula_reference.update` | `ReferenceStandardCertificateUncertaintyUpdate.formula_reference` | Requiere granularización |
| Modificar issuing laboratory | `reference_standard_certificates.fields.issuing_laboratory.update` | `ReferenceStandardCertificateUpdate.issuing_laboratory` | Requiere granularización |
| Modificar k factor | `reference_standard_certificates.fields.k_factor.update` | `ReferenceStandardCertificateUncertaintyUpdate.k_factor` | Requiere granularización |
| Modificar magnitude | `reference_standard_certificates.fields.magnitude.update` | `ReferenceStandardCertificateUncertaintyUpdate.magnitude` | Requiere granularización |
| Modificar measurement type | `reference_standard_certificates.fields.measurement_type.update` | `ReferenceStandardCertificateUncertaintyUpdate.measurement_type` | Requiere granularización |
| Modificar notas | `reference_standard_certificates.fields.notes.update` | `ReferenceStandardCertificateUncertaintyUpdate.notes` | Requiere granularización |
| Modificar range max | `reference_standard_certificates.fields.range_max.update` | `ReferenceStandardCertificateUncertaintyUpdate.range_max` | Requiere granularización |
| Modificar range min | `reference_standard_certificates.fields.range_min.update` | `ReferenceStandardCertificateUncertaintyUpdate.range_min` | Requiere granularización |
| Modificar received date | `reference_standard_certificates.fields.received_date.update` | `ReferenceStandardCertificateUpdate.received_date` | Requiere granularización |
| Modificar uncertainties | `reference_standard_certificates.fields.uncertainties.update` | `ReferenceStandardCertificateCreate.uncertainties` | Requiere granularización |
| Modificar uncertainty unit | `reference_standard_certificates.fields.uncertainty_unit.update` | `ReferenceStandardCertificateUncertaintyUpdate.uncertainty_unit` | Requiere granularización |
| Modificar uncertainty value | `reference_standard_certificates.fields.uncertainty_value.update` | `ReferenceStandardCertificateUncertaintyUpdate.uncertainty_value` | Requiere granularización |
| Modificar unit | `reference_standard_certificates.fields.unit.update` | `ReferenceStandardCertificateUncertaintyUpdate.unit` | Requiere granularización |

## 9.3. Gestionar acceso y seguridad

| Microacción de campo | Permiso propuesto | Evidencia | Estado |
|---|---|---|---|
| Activar o desactivar | `reference_standard_certificates.fields.is_active.update` | `ReferenceStandardCertificateUncertaintyUpdate.is_active` | Requiere granularización |

## 9.4. Gestionar estado

| Microacción de campo | Permiso propuesto | Evidencia | Estado |
|---|---|---|---|
| Modificar estado | `reference_standard_certificates.fields.status.update` | `ReferenceStandardCertificateUpdate.status` | Requiere granularización |
| Modificar traceability statement | `reference_standard_certificates.fields.traceability_statement.update` | `ReferenceStandardCertificateUpdate.traceability_statement` | Requiere granularización |

# 10. Clientes

## 10.1. Archivar

| Microacción | Método y ruta | Permiso propuesto | Estado |
|---|---|---|---|
| Archive client | `POST /clients/{client_id}/archive` | `clients.archive` | Existe en backend |

## 10.2. Confirmar

| Microacción | Método y ruta | Permiso propuesto | Estado |
|---|---|---|---|
| Confirm import | `POST /clients/import/confirm` | `clients.create` | Existe en backend |

## 10.3. Consultar

| Microacción | Método y ruta | Permiso propuesto | Estado |
|---|---|---|---|
| Clients | `GET /clients` | `clients.read` | Existe en backend |
| Client | `GET /clients/{client_id}` | `clients.read` | Existe en backend |
| Delete eligibility | `GET /clients/{client_id}/delete-eligibility` | `clients.read` | Existe en backend |

## 10.4. Crear

| Microacción | Método y ruta | Permiso propuesto | Estado |
|---|---|---|---|
| Client | `POST /clients` | `clients.create` | Existe en backend |
| Tax constancy | `POST /clients/{client_id}/tax-constancy` | `clients.tax.override` | Existe en backend |

## 10.5. Eliminar

| Microacción | Método y ruta | Permiso propuesto | Estado |
|---|---|---|---|
| Client | `DELETE /clients/{client_id}` | `clients.delete` | Existe en backend |

## 10.6. Exportar

| Microacción | Método y ruta | Permiso propuesto | Estado |
|---|---|---|---|
| Export clients | `GET /clients/export` | `clients.documents.download` | Existe en backend |

## 10.7. Gestionar certificados

| Microacción | Método y ruta | Permiso propuesto | Estado |
|---|---|---|---|
| Certificate profiles | `GET /clients/{client_id}/certificate-profiles` | `clients.certificate_profiles.manage` | Existe en backend |
| Certificate profile | `POST /clients/{client_id}/certificate-profiles` | `clients.certificate_profiles.manage` | Existe en backend |
| Certificate profile | `DELETE /clients/{client_id}/certificate-profiles/{profile_id}` | `clients.certificate_profiles.manage` | Existe en backend |
| Certificate profile | `PATCH /clients/{client_id}/certificate-profiles/{profile_id}` | `clients.certificate_profiles.manage` | Existe en backend |

## 10.8. Modificar

| Microacción | Método y ruta | Permiso propuesto | Estado |
|---|---|---|---|
| Client | `PATCH /clients/{client_id}` | `clients.update` | Existe en backend |

## 10.9. Previsualizar

| Microacción | Método y ruta | Permiso propuesto | Estado |
|---|---|---|---|
| Preview import | `POST /clients/import/preview` | `clients.review` | Existe en backend |
| Preview constancy | `POST /clients/tax-constancy/preview` | `clients.review` | Existe en backend |

## 10.10. Restaurar

| Microacción | Método y ruta | Permiso propuesto | Estado |
|---|---|---|---|
| Restore client | `POST /clients/{client_id}/restore` | `clients.restore` | Existe en backend |

## 10.11. Editar campos y atributos

| Microacción de campo | Permiso propuesto | Evidencia | Estado |
|---|---|---|---|
| Modificar attention | `clients.fields.attention.update` | `ClientCertificateProfileUpdate.attention` | Requiere granularización |
| Modificar available | `clients.fields.available.update` | `ClientTaxConstancyPreviewRead.available` | Requiere granularización |
| Modificar cfdi use | `clients.fields.cfdi_use.update` | `ClientUpdate.cfdi_use` | Requiere granularización |
| Modificar city | `clients.fields.city.update` | `ClientUpdate.city` | Requiere granularización |
| Modificar client type | `clients.fields.client_type.update` | `ClientUpdate.client_type` | Requiere granularización |
| Modificar columns | `clients.fields.columns.update` | `ClientImportPreviewRead.columns` | Requiere granularización |
| Modificar company | `clients.fields.company.update` | `ClientCertificateProfileUpdate.company` | Requiere granularización |
| Modificar contacts | `clients.fields.contacts.update` | `ClientCreate.contacts` | Requiere granularización |
| Modificar correo | `clients.fields.email.update` | `ClientUpdate.email` | Requiere granularización |
| Modificar country | `clients.fields.country.update` | `ClientUpdate.country` | Requiere granularización |
| Modificar curp | `clients.fields.curp.update` | `ClientUpdate.curp` | Requiere granularización |
| Modificar domicilio | `clients.fields.address.update` | `ClientCertificateProfileUpdate.address` | Requiere granularización |
| Modificar duplicate count | `clients.fields.duplicate_count.update` | `ClientImportPreviewRead.duplicate_count` | Requiere granularización |
| Modificar error count | `clients.fields.error_count.update` | `ClientImportPreviewRead.error_count` | Requiere granularización |
| Modificar exterior number | `clients.fields.exterior_number.update` | `ClientUpdate.exterior_number` | Requiere granularización |
| Modificar extracted client type | `clients.fields.extracted_client_type.update` | `ClientTaxConstancyPreviewRead.extracted_client_type` | Requiere granularización |
| Modificar extracted commercial name | `clients.fields.extracted_commercial_name.update` | `ClientTaxConstancyPreviewRead.extracted_commercial_name` | Requiere granularización |
| Modificar extracted curp | `clients.fields.extracted_curp.update` | `ClientTaxConstancyPreviewRead.extracted_curp` | Requiere granularización |
| Modificar extracted exterior number | `clients.fields.extracted_exterior_number.update` | `ClientTaxConstancyPreviewRead.extracted_exterior_number` | Requiere granularización |
| Modificar extracted first last name | `clients.fields.extracted_first_last_name.update` | `ClientTaxConstancyPreviewRead.extracted_first_last_name` | Requiere granularización |
| Modificar extracted first name | `clients.fields.extracted_first_name.update` | `ClientTaxConstancyPreviewRead.extracted_first_name` | Requiere granularización |
| Modificar extracted interior number | `clients.fields.extracted_interior_number.update` | `ClientTaxConstancyPreviewRead.extracted_interior_number` | Requiere granularización |
| Modificar extracted locality | `clients.fields.extracted_locality.update` | `ClientTaxConstancyPreviewRead.extracted_locality` | Requiere granularización |
| Modificar extracted municipality | `clients.fields.extracted_municipality.update` | `ClientTaxConstancyPreviewRead.extracted_municipality` | Requiere granularización |
| Modificar extracted neighborhood | `clients.fields.extracted_neighborhood.update` | `ClientTaxConstancyPreviewRead.extracted_neighborhood` | Requiere granularización |
| Modificar extracted second last name | `clients.fields.extracted_second_last_name.update` | `ClientTaxConstancyPreviewRead.extracted_second_last_name` | Requiere granularización |
| Modificar extracted street | `clients.fields.extracted_street.update` | `ClientTaxConstancyPreviewRead.extracted_street` | Requiere granularización |
| Modificar extracted street type | `clients.fields.extracted_street_type.update` | `ClientTaxConstancyPreviewRead.extracted_street_type` | Requiere granularización |
| Modificar filename | `clients.fields.filename.update` | `ClientTaxConstancyPreviewRead.filename` | Requiere granularización |
| Modificar first last name | `clients.fields.first_last_name.update` | `ClientUpdate.first_last_name` | Requiere granularización |
| Modificar first name | `clients.fields.first_name.update` | `ClientUpdate.first_name` | Requiere granularización |
| Modificar interior number | `clients.fields.interior_number.update` | `ClientUpdate.interior_number` | Requiere granularización |
| Modificar is default | `clients.fields.is_default.update` | `ClientCertificateProfileUpdate.is_default` | Requiere granularización |
| Modificar label | `clients.fields.label.update` | `ClientCertificateProfileUpdate.label` | Requiere granularización |
| Modificar locality | `clients.fields.locality.update` | `ClientUpdate.locality` | Requiere granularización |
| Modificar message | `clients.fields.message.update` | `ClientTaxConstancyPreviewRead.message` | Requiere granularización |
| Modificar municipality | `clients.fields.municipality.update` | `ClientUpdate.municipality` | Requiere granularización |
| Modificar neighborhood | `clients.fields.neighborhood.update` | `ClientUpdate.neighborhood` | Requiere granularización |
| Modificar nombre comercial | `clients.fields.commercial_name.update` | `ClientUpdate.commercial_name` | Requiere granularización |
| Modificar notas | `clients.fields.notes.update` | `ClientUpdate.notes` | Requiere granularización |
| Modificar payment terms | `clients.fields.payment_terms.update` | `ClientUpdate.payment_terms` | Requiere granularización |
| Modificar postal code | `clients.fields.postal_code.update` | `ClientUpdate.postal_code` | Requiere granularización |
| Modificar rows | `clients.fields.rows.update` | `ClientImportPreviewRead.rows` | Requiere granularización |
| Modificar second last name | `clients.fields.second_last_name.update` | `ClientUpdate.second_last_name` | Requiere granularización |
| Modificar street | `clients.fields.street.update` | `ClientUpdate.street` | Requiere granularización |
| Modificar street type | `clients.fields.street_type.update` | `ClientUpdate.street_type` | Requiere granularización |
| Modificar teléfono | `clients.fields.phone.update` | `ClientUpdate.phone` | Requiere granularización |
| Modificar valid count | `clients.fields.valid_count.update` | `ClientImportPreviewRead.valid_count` | Requiere granularización |
| Modificar warning count | `clients.fields.warning_count.update` | `ClientImportPreviewRead.warning_count` | Requiere granularización |

## 10.12. Gestionar estado

| Microacción de campo | Permiso propuesto | Evidencia | Estado |
|---|---|---|---|
| Modificar extracted state | `clients.fields.extracted_state.update` | `ClientTaxConstancyPreviewRead.extracted_state` | Requiere granularización |
| Modificar state | `clients.fields.state.update` | `ClientUpdate.state` | Requiere granularización |

## 10.13. Gestionar identidad fiscal y legal

| Microacción de campo | Permiso propuesto | Evidencia | Estado |
|---|---|---|---|
| Modificar RFC | `clients.fields.rfc.update` | `ClientUpdate.rfc` | Requiere granularización |
| Modificar extracted fiscal postal code | `clients.fields.extracted_fiscal_postal_code.update` | `ClientTaxConstancyPreviewRead.extracted_fiscal_postal_code` | Requiere granularización |
| Modificar extracted legal name | `clients.fields.extracted_legal_name.update` | `ClientTaxConstancyPreviewRead.extracted_legal_name` | Requiere granularización |
| Modificar extracted rfc | `clients.fields.extracted_rfc.update` | `ClientTaxConstancyPreviewRead.extracted_rfc` | Requiere granularización |
| Modificar fiscal country code | `clients.fields.fiscal_country_code.update` | `ClientUpdate.fiscal_country_code` | Requiere granularización |
| Modificar fiscal postal code | `clients.fields.fiscal_postal_code.update` | `ClientUpdate.fiscal_postal_code` | Requiere granularización |
| Modificar razón social | `clients.fields.legal_name.update` | `ClientUpdate.legal_name` | Requiere granularización |

## 10.14. Redefinir condiciones económicas

| Microacción de campo | Permiso propuesto | Evidencia | Estado |
|---|---|---|---|
| Modificar extracted tax regime | `clients.fields.extracted_tax_regime.update` | `ClientTaxConstancyPreviewRead.extracted_tax_regime` | Requiere granularización |
| Modificar extracted tax regimes | `clients.fields.extracted_tax_regimes.update` | `ClientTaxConstancyPreviewRead.extracted_tax_regimes` | Requiere granularización |
| Modificar tax regime | `clients.fields.tax_regime.update` | `ClientUpdate.tax_regime` | Requiere granularización |

# 11. Comunicaciones

## 11.1. Consultar

| Microacción | Método y ruta | Permiso propuesto | Estado |
|---|---|---|---|
| Directory | `GET /communications/directory` | `communications.read` | Existe en backend |

## 11.2. Gestionar conversaciones

| Microacción | Método y ruta | Permiso propuesto | Estado |
|---|---|---|---|
| Conversations | `GET /communications/conversations` | `communications.read` | Existe en backend |
| Conversation | `POST /communications/conversations` | `communications.create` | Existe en backend |
| Conversation detail | `GET /communications/conversations/{conversation_id}` | `communications.read` | Existe en backend |
| Message | `POST /communications/conversations/{conversation_id}/messages` | `communications.messages.manage` | Existe en backend |

## 11.3. Editar campos y atributos

| Microacción de campo | Permiso propuesto | Evidencia | Estado |
|---|---|---|---|
| Cambiar cliente relacionado | `communications.fields.client_id.update` | `CommunicationConversationCreate.client_id` | Requiere granularización |
| Modificar body | `communications.fields.body.update` | `CommunicationMessageCreate.body` | Requiere granularización |
| Modificar conversation type | `communications.fields.conversation_type.update` | `CommunicationConversationCreate.conversation_type` | Requiere granularización |
| Modificar initial message | `communications.fields.initial_message.update` | `CommunicationConversationCreate.initial_message` | Requiere granularización |
| Modificar participant user id | `communications.fields.participant_user_id.update` | `CommunicationConversationCreate.participant_user_id` | Requiere granularización |

# 12. Control documental

## 12.1. Consultar

| Microacción | Método y ruta | Permiso propuesto | Estado |
|---|---|---|---|
| Documents | `GET /documents` | `documents.read` | Existe en backend |
| Document | `GET /documents/{document_id}` | `documents.read` | Existe en backend |

## 12.2. Crear

| Microacción | Método y ruta | Permiso propuesto | Estado |
|---|---|---|---|
| Document | `POST /documents` | `documents.create` | Existe en backend |

## 12.3. Gestionar certificados

| Microacción | Método y ruta | Permiso propuesto | Estado |
|---|---|---|---|
| Certificate master | `POST /documents/certificate-masters` | `documents.create` | Existe en backend |

## 12.4. Gestionar versiones

| Microacción | Método y ruta | Permiso propuesto | Estado |
|---|---|---|---|
| Document version | `POST /documents/{document_id}/versions` | `documents.create` | Existe en backend |
| Activate document version | `POST /documents/{document_id}/versions/{version_id}/activate` | `documents.activate` | Existe en backend |
| Download document version | `GET /documents/{document_id}/versions/{version_id}/download` | `documents.documents.download` | Existe en backend |

## 12.5. Modificar

| Microacción | Método y ruta | Permiso propuesto | Estado |
|---|---|---|---|
| Document | `PATCH /documents/{document_id}` | `documents.update` | Existe en backend |
| Archive document | `PATCH /documents/{document_id}/archive` | `documents.update` | Existe en backend |

## 12.6. Editar campos y atributos

| Microacción de campo | Permiso propuesto | Evidencia | Estado |
|---|---|---|---|
| Modificar allowed patterns | `documents.fields.allowed_patterns.update` | `TechnicalProfileCreate.allowed_patterns` | Requiere granularización |
| Modificar calibration scope | `documents.fields.calibration_scope.update` | `DocumentInterpretationUpdate.calibration_scope` | Requiere granularización |
| Modificar certificate template document id | `documents.fields.certificate_template_document_id.update` | `TechnicalProfileUpdate.certificate_template_document_id` | Requiere granularización |
| Modificar code | `documents.fields.code.update` | `ControlledDocumentUpdate.code` | Requiere granularización |
| Modificar current revision | `documents.fields.current_revision.update` | `ControlledDocumentUpdate.current_revision` | Requiere granularización |
| Modificar data | `documents.fields.data.update` | `DocumentInterpretationUpdate.data` | Requiere granularización |
| Modificar descripción | `documents.fields.description.update` | `ControlledDocumentUpdate.description` | Requiere granularización |
| Modificar digital location | `documents.fields.digital_location.update` | `ControlledDocumentUpdate.digital_location` | Requiere granularización |
| Modificar document type | `documents.fields.document_type.update` | `ControlledDocumentUpdate.document_type` | Requiere granularización |
| Modificar document version id | `documents.fields.document_version_id.update` | `DocumentInterpretationUpdate.document_version_id` | Requiere granularización |
| Modificar effective date | `documents.fields.effective_date.update` | `ControlledDocumentUpdate.effective_date` | Requiere granularización |
| Modificar equipment type | `documents.fields.equipment_type.update` | `DocumentInterpretationUpdate.equipment_type` | Requiere granularización |
| Modificar field sheet template document id | `documents.fields.field_sheet_template_document_id.update` | `TechnicalProfileUpdate.field_sheet_template_document_id` | Requiere granularización |
| Modificar interpretation type | `documents.fields.interpretation_type.update` | `DocumentInterpretationUpdate.interpretation_type` | Requiere granularización |
| Modificar issue date | `documents.fields.issue_date.update` | `ControlledDocumentUpdate.issue_date` | Requiere granularización |
| Modificar last review date | `documents.fields.last_review_date.update` | `ControlledDocumentUpdate.last_review_date` | Requiere granularización |
| Modificar magnitude | `documents.fields.magnitude.update` | `DocumentInterpretationUpdate.magnitude` | Requiere granularización |
| Modificar name | `documents.fields.name.update` | `ControlledDocumentUpdate.name` | Requiere granularización |
| Modificar notas | `documents.fields.notes.update` | `TechnicalProfileUpdate.notes` | Requiere granularización |
| Modificar procedure document id | `documents.fields.procedure_document_id.update` | `TechnicalProfileUpdate.procedure_document_id` | Requiere granularización |
| Modificar procedure interpretation id | `documents.fields.procedure_interpretation_id.update` | `TechnicalProfileUpdate.procedure_interpretation_id` | Requiere granularización |
| Modificar quality level | `documents.fields.quality_level.update` | `ControlledDocumentUpdate.quality_level` | Requiere granularización |
| Modificar retention time | `documents.fields.retention_time.update` | `ControlledDocumentUpdate.retention_time` | Requiere granularización |
| Modificar rules | `documents.fields.rules.update` | `TechnicalProfileUpdate.rules` | Requiere granularización |
| Modificar uncertainty source document id | `documents.fields.uncertainty_source_document_id.update` | `TechnicalProfileUpdate.uncertainty_source_document_id` | Requiere granularización |

## 12.7. Gestionar estado

| Microacción de campo | Permiso propuesto | Evidencia | Estado |
|---|---|---|---|
| Modificar estado | `documents.fields.status.update` | `ControlledDocumentUpdate.status` | Requiere granularización |

## 12.8. Redefinir clasificación y alcance

| Microacción de campo | Permiso propuesto | Evidencia | Estado |
|---|---|---|---|
| Cambiar tipo de servicio | `documents.fields.service_type.update` | `DocumentInterpretationUpdate.service_type` | Requiere granularización |

# 13. Cotizaciones

## 13.1. Aceptar

| Microacción | Método y ruta | Permiso propuesto | Estado |
|---|---|---|---|
| Accept quotation | `POST /quotations/{quotation_id}/accept` | `quotations.status.accept` | Existe en backend |

## 13.2. Cambiar estado

| Microacción | Método y ruta | Permiso propuesto | Estado |
|---|---|---|---|
| Mark quotation waiting | `POST /quotations/{quotation_id}/waiting` | `quotations.create` | Existe en backend |

## 13.3. Cancelar

| Microacción | Método y ruta | Permiso propuesto | Estado |
|---|---|---|---|
| Cancel quotation | `POST /quotations/{quotation_id}/cancel` | `quotations.status.cancel` | Existe en backend |

## 13.4. Consultar

| Microacción | Método y ruta | Permiso propuesto | Estado |
|---|---|---|---|
| Quotations | `GET /quotations` | `quotations.read` | Existe en backend |
| Quotation | `GET /quotations/{quotation_id}` | `quotations.read` | Existe en backend |
| Quotation pdf | `GET /quotations/{quotation_id}/pdf` | `quotations.documents.download` | Existe en backend |

## 13.5. Crear

| Microacción | Método y ruta | Permiso propuesto | Estado |
|---|---|---|---|
| Quotation | `POST /quotations` | `quotations.create` | Existe en backend |
| Quotation item | `POST /quotations/{quotation_id}/items` | `quotations.items.manage` | Existe en backend |

## 13.6. Eliminar

| Microacción | Método y ruta | Permiso propuesto | Estado |
|---|---|---|---|
| Quotation | `DELETE /quotations/{quotation_id}` | `quotations.delete` | Existe en backend |
| Quotation item | `DELETE /quotations/{quotation_id}/items/{item_id}` | `quotations.items.manage` | Existe en backend |

## 13.7. Enviar

| Microacción | Método y ruta | Permiso propuesto | Estado |
|---|---|---|---|
| Send quotation | `POST /quotations/{quotation_id}/send` | `quotations.status.send` | Existe en backend |

## 13.8. Gestionar revisiones y snapshots

| Microacción | Método y ruta | Permiso propuesto | Estado |
|---|---|---|---|
| Quotation snapshots | `GET /quotations/{quotation_id}/snapshots` | `quotations.snapshots.manage` | Existe en backend |
| Restore quotation version | `POST /quotations/{quotation_id}/snapshots/restore` | `quotations.snapshots.restore` | Existe en backend |

## 13.9. Modificar

| Microacción | Método y ruta | Permiso propuesto | Estado |
|---|---|---|---|
| Quotation | `PATCH /quotations/{quotation_id}` | `quotations.update` | Existe en backend |
| Quotation item | `PATCH /quotations/{quotation_id}/items/{item_id}` | `quotations.items.manage` | Existe en backend |

## 13.10. Rechazar

| Microacción | Método y ruta | Permiso propuesto | Estado |
|---|---|---|---|
| Reject quotation | `POST /quotations/{quotation_id}/reject` | `quotations.status.reject` | Existe en backend |

## 13.11. Vencer

| Microacción | Método y ruta | Permiso propuesto | Estado |
|---|---|---|---|
| Expire quotation | `POST /quotations/{quotation_id}/expire` | `quotations.status.expire` | Existe en backend |

## 13.12. Editar campos y atributos

| Microacción de campo | Permiso propuesto | Evidencia | Estado |
|---|---|---|---|
| Cambiar cliente relacionado | `quotations.fields.client_id.update` | `QuotationUpdate.client_id` | Requiere granularización |
| Modificar advisor id | `quotations.fields.advisor_id.update` | `QuotationUpdate.advisor_id` | Requiere granularización |
| Modificar calibration scope | `quotations.fields.calibration_scope.update` | `QuotationItemBase.calibration_scope` | Requiere granularización |
| Modificar cantidad | `quotations.fields.quantity.update` | `QuotationItemBase.quantity` | Requiere granularización |
| Modificar comment | `quotations.fields.comment.update` | `QuotationStatusChange.comment` | Requiere granularización |
| Modificar commodity | `quotations.fields.commodity.update` | `QuotationItemBase.commodity` | Requiere granularización |
| Modificar descripción | `quotations.fields.description.update` | `QuotationItemBase.description` | Requiere granularización |
| Modificar internal unit | `quotations.fields.internal_unit.update` | `QuotationItemBase.internal_unit` | Requiere granularización |
| Modificar issued on | `quotations.fields.issued_on.update` | `QuotationUpdate.issued_on` | Requiere granularización |
| Modificar items | `quotations.fields.items.update` | `QuotationCreate.items` | Requiere granularización |
| Modificar notas | `quotations.fields.notes.update` | `QuotationUpdate.notes` | Requiere granularización |
| Modificar operational snapshot | `quotations.fields.operational_snapshot.update` | `QuotationItemRead.operational_snapshot` | Requiere granularización |
| Modificar payment terms | `quotations.fields.payment_terms.update` | `QuotationUpdate.payment_terms` | Requiere granularización |
| Modificar quotation legend | `quotations.fields.quotation_legend.update` | `QuotationItemBase.quotation_legend` | Requiere granularización |
| Modificar sat key | `quotations.fields.sat_key.update` | `QuotationItemBase.sat_key` | Requiere granularización |
| Modificar sat unit | `quotations.fields.sat_unit.update` | `QuotationItemBase.sat_unit` | Requiere granularización |
| Modificar service name | `quotations.fields.service_name.update` | `QuotationItemBase.service_name` | Requiere granularización |
| Modificar total | `quotations.fields.total.update` | `QuotationItemRead.total` | Requiere granularización |
| Modificar unit | `quotations.fields.unit.update` | `QuotationItemBase.unit` | Requiere granularización |
| Modificar valid until | `quotations.fields.valid_until.update` | `QuotationUpdate.valid_until` | Requiere granularización |

## 13.13. Gestionar acceso y seguridad

| Microacción de campo | Permiso propuesto | Evidencia | Estado |
|---|---|---|---|
| Activar o desactivar | `quotations.fields.is_active.update` | `QuotationItemRead.is_active` | Requiere granularización |

## 13.14. Redefinir clasificación y alcance

| Microacción de campo | Permiso propuesto | Evidencia | Estado |
|---|---|---|---|
| Cambiar servicio del catálogo | `quotations.fields.catalog_item_id.update` | `QuotationItemBase.catalog_item_id` | Requiere granularización |

## 13.15. Redefinir condiciones económicas

| Microacción de campo | Permiso propuesto | Evidencia | Estado |
|---|---|---|---|
| Aplicar o modificar descuento | `quotations.fields.discount_percent.update` | `QuotationItemBase.discount_percent` | Requiere granularización |
| Modificar moneda | `quotations.fields.currency.update` | `QuotationItemBase.currency` | Requiere granularización |
| Modificar precio unitario | `quotations.fields.unit_price.update` | `QuotationItemBase.unit_price` | Requiere granularización |
| Modificar tasa de impuesto | `quotations.fields.tax_rate.update` | `QuotationItemBase.tax_rate` | Requiere granularización |
| Modificar tax object | `quotations.fields.tax_object.update` | `QuotationItemBase.tax_object` | Requiere granularización |
| Modificar tax total | `quotations.fields.tax_total.update` | `QuotationItemRead.tax_total` | Requiere granularización |

# 14. ETS y órdenes de trabajo

## 14.1. Cerrar

| Microacción | Método y ruta | Permiso propuesto | Estado |
|---|---|---|---|
| Close service order | `POST /service-orders/{service_order_id}/close` | `service_orders.status.close` | Existe en backend |

## 14.2. Confirmar

| Microacción | Método y ruta | Permiso propuesto | Estado |
|---|---|---|---|
| Confirm service order | `POST /service-orders/{service_order_id}/confirm` | `service_orders.status.confirm` | Existe en backend |

## 14.3. Consultar

| Microacción | Método y ruta | Permiso propuesto | Estado |
|---|---|---|---|
| Service orders | `GET /service-orders` | `service_orders.read` | Existe en backend |
| Service work order pdf | `GET /service-orders/work-orders/{work_order_id}/pdf` | `service_orders.work_orders.download` | Existe en backend |
| Service order | `GET /service-orders/{service_order_id}` | `service_orders.read` | Existe en backend |
| Service order work order pdf | `GET /service-orders/{service_order_id}/work-order-pdf` | `service_orders.work_orders.download` | Existe en backend |
| Service order work orders pdf | `GET /service-orders/{service_order_id}/work-orders-pdf` | `service_orders.documents.download` | Existe en backend |

## 14.4. Crear

| Microacción | Método y ruta | Permiso propuesto | Estado |
|---|---|---|---|
| Service order | `POST /service-orders` | `service_orders.create` | Existe en backend |

## 14.5. Eliminar

| Microacción | Método y ruta | Permiso propuesto | Estado |
|---|---|---|---|
| Service order | `DELETE /service-orders/{service_order_id}` | `service_orders.delete` | Existe en backend |

## 14.6. Gestionar calidad

| Microacción | Método y ruta | Permiso propuesto | Estado |
|---|---|---|---|
| Quality service order | `POST /service-orders/{service_order_id}/quality` | `service_orders.status.quality` | Existe en backend |

## 14.7. Gestionar captura

| Microacción | Método y ruta | Permiso propuesto | Estado |
|---|---|---|---|
| Capture service order | `POST /service-orders/{service_order_id}/capture` | `service_orders.status.capture` | Existe en backend |
| Capture files | `GET /service-orders/{service_order_id}/capture-files` | `service_orders.capture_files.manage` | Existe en backend |
| Capture files | `POST /service-orders/{service_order_id}/capture-files` | `service_orders.capture_files.manage` | Existe en backend |
| Download capture package | `GET /service-orders/{service_order_id}/capture-package` | `service_orders.capture_package.download` | Existe en backend |
| Capture package summary | `GET /service-orders/{service_order_id}/capture-package-summary` | `service_orders.capture_package.download` | Existe en backend |
| Download work order capture package | `GET /service-orders/{service_order_id}/work-orders/{work_order_id}/capture-package` | `service_orders.capture_package.download` | Existe en backend |

## 14.8. Gestionar certificados

| Microacción | Método y ruta | Permiso propuesto | Estado |
|---|---|---|---|
| Upload service order certificate pdfs | `POST /service-orders/{service_order_id}/certificate-pdfs` | `service_orders.create` | Existe en backend |
| Authenticate service order certificates | `POST /service-orders/{service_order_id}/certificates/authenticate-approved` | `service_orders.create` | Existe en backend |
| Release service order certificates | `POST /service-orders/{service_order_id}/certificates/release-authenticated` | `service_orders.status.release` | Existe en backend |

## 14.9. Gestionar excepciones

| Microacción | Método y ruta | Permiso propuesto | Estado |
|---|---|---|---|
| Service order exception | `POST /service-orders/{service_order_id}/exceptions` | `service_orders.create` | Existe en backend |

## 14.10. Gestionar firmas

| Microacción | Método y ruta | Permiso propuesto | Estado |
|---|---|---|---|
| Confirm service order signatures | `POST /service-orders/{service_order_id}/confirm-signatures` | `service_orders.status.confirm` | Existe en backend |

## 14.11. Gestionar pagos

| Microacción | Método y ruta | Permiso propuesto | Estado |
|---|---|---|---|
| Pending payment service order | `POST /service-orders/{service_order_id}/pending-payment` | `service_orders.status.pending_payment` | Existe en backend |

## 14.12. Iniciar

| Microacción | Método y ruta | Permiso propuesto | Estado |
|---|---|---|---|
| Start service order | `POST /service-orders/{service_order_id}/start` | `service_orders.status.start` | Existe en backend |

## 14.13. Liberar

| Microacción | Método y ruta | Permiso propuesto | Estado |
|---|---|---|---|
| Release service order | `POST /service-orders/{service_order_id}/release` | `service_orders.status.release` | Existe en backend |

## 14.14. Modificar

| Microacción | Método y ruta | Permiso propuesto | Estado |
|---|---|---|---|
| Service order | `PATCH /service-orders/{service_order_id}` | `service_orders.update` | Existe en backend |

## 14.15. Registrar llamado

| Microacción | Método y ruta | Permiso propuesto | Estado |
|---|---|---|---|
| Call service order | `POST /service-orders/{service_order_id}/call` | `service_orders.status.call` | Existe en backend |

## 14.16. Editar campos y atributos

| Microacción de campo | Permiso propuesto | Evidencia | Estado |
|---|---|---|---|
| Modificar advisor id | `service_orders.fields.advisor_id.update` | `ServiceOrderUpdate.advisor_id` | Requiere granularización |
| Modificar agenda date | `service_orders.fields.agenda_date.update` | `ServiceOrderUpdate.agenda_date` | Requiere granularización |
| Modificar calibration scope | `service_orders.fields.calibration_scope.update` | `ServiceOrderItemBase.calibration_scope` | Requiere granularización |
| Modificar cantidad | `service_orders.fields.quantity.update` | `ServiceOrderItemBase.quantity` | Requiere granularización |
| Modificar client acceptance signed name | `service_orders.fields.client_acceptance_signed_name.update` | `ServiceOrderUpdate.client_acceptance_signed_name` | Requiere granularización |
| Modificar client received signed name | `service_orders.fields.client_received_signed_name.update` | `ServiceOrderUpdate.client_received_signed_name` | Requiere granularización |
| Modificar comment | `service_orders.fields.comment.update` | `ServiceOrderStatusChange.comment` | Requiere granularización |
| Modificar completed equipment | `service_orders.fields.completed_equipment.update` | `ServiceOrderUpdate.completed_equipment` | Requiere granularización |
| Modificar items | `service_orders.fields.items.update` | `ServiceOrderCreate.items` | Requiere granularización |
| Modificar notas | `service_orders.fields.notes.update` | `ServiceOrderUpdate.notes` | Requiere granularización |
| Modificar quotation item id | `service_orders.fields.quotation_item_id.update` | `ServiceOrderItemBase.quotation_item_id` | Requiere granularización |
| Modificar requires payment | `service_orders.fields.requires_payment.update` | `ServiceOrderUpdate.requires_payment` | Requiere granularización |
| Modificar service date | `service_orders.fields.service_date.update` | `ServiceOrderUpdate.service_date` | Requiere granularización |
| Modificar service name | `service_orders.fields.service_name.update` | `ServiceOrderItemBase.service_name` | Requiere granularización |
| Modificar source stage | `service_orders.fields.source_stage.update` | `ServiceOrderExceptionCreate.source_stage` | Requiere granularización |
| Modificar target stage | `service_orders.fields.target_stage.update` | `ServiceOrderExceptionCreate.target_stage` | Requiere granularización |
| Modificar technician signed name | `service_orders.fields.technician_signed_name.update` | `ServiceOrderUpdate.technician_signed_name` | Requiere granularización |
| Modificar total equipment | `service_orders.fields.total_equipment.update` | `ServiceOrderUpdate.total_equipment` | Requiere granularización |
| Reasignar técnico | `service_orders.fields.technician_id.update` | `ServiceOrderUpdate.technician_id` | Requiere granularización |
| Registrar motivo | `service_orders.fields.reason.update` | `ServiceOrderExceptionCreate.reason` | Requiere granularización |

## 14.17. Gestionar acceso y seguridad

| Microacción de campo | Permiso propuesto | Evidencia | Estado |
|---|---|---|---|
| Activar o desactivar | `service_orders.fields.is_active.update` | `ServiceOrderItemRead.is_active` | Requiere granularización |

## 14.18. Gestionar estado

| Microacción de campo | Permiso propuesto | Evidencia | Estado |
|---|---|---|---|
| Modificar estado | `service_orders.fields.status.update` | `ServiceOrderItemBase.status` | Requiere granularización |

## 14.19. Gestionar firmas

| Microacción de campo | Permiso propuesto | Evidencia | Estado |
|---|---|---|---|
| Modificar client acceptance signature data url | `service_orders.fields.client_acceptance_signature_data_url.update` | `ServiceOrderUpdate.client_acceptance_signature_data_url` | Requiere granularización |
| Modificar client received signature data url | `service_orders.fields.client_received_signature_data_url.update` | `ServiceOrderUpdate.client_received_signature_data_url` | Requiere granularización |
| Modificar technician signature data url | `service_orders.fields.technician_signature_data_url.update` | `ServiceOrderUpdate.technician_signature_data_url` | Requiere granularización |

## 14.20. Redefinir clasificación y alcance

| Microacción de campo | Permiso propuesto | Evidencia | Estado |
|---|---|---|---|
| Cambiar servicio del catálogo | `service_orders.fields.catalog_item_id.update` | `ServiceOrderItemBase.catalog_item_id` | Requiere granularización |

## 14.21. Ejecutar ETS Mantenimiento

| Microacción | Método y ruta | Permiso propuesto | Estado |
|---|---|---|---|
| Consultar tablero de Mantenimiento | `GET /service-orders/{service_order_id}/maintenance` | `service_orders.read` | Existe en backend |
| Registrar arribo de laboratorio | `POST /service-orders/{service_order_id}/maintenance/{execution_id}/arrival` | `service_orders.maintenance.manage` | Existe en backend |
| Vincular equipo atendido en campo | `POST /service-orders/{service_order_id}/maintenance/{execution_id}/field-equipment` | `service_orders.maintenance.manage` | Existe en backend |
| Preparar y asignar Mantenimiento | `POST /service-orders/{service_order_id}/maintenance/{execution_id}/prepare` | `service_orders.maintenance.manage` | Existe en backend |
| Aceptar visita de campo | `POST /service-orders/{service_order_id}/maintenance/{execution_id}/field-accept` | `service_orders.maintenance.execute` | Existe en backend |
| Iniciar intervención | `POST /service-orders/{service_order_id}/maintenance/{execution_id}/start` | `service_orders.maintenance.execute` | Existe en backend |
| Guardar captura técnica estructurada | `PUT /service-orders/{service_order_id}/maintenance/{execution_id}/capture` | `service_orders.maintenance.execute` | Existe en backend |
| Registrar o resolver pausa | `POST /service-orders/{service_order_id}/maintenance/{execution_id}/pauses[...]` | `service_orders.maintenance.execute` | Existe en backend |
| Documentar material utilizado o requerido | `POST /service-orders/{service_order_id}/maintenance/{execution_id}/materials` | `service_orders.maintenance.execute` | Existe en backend |
| Solicitar cambio de alcance | `POST /service-orders/{service_order_id}/maintenance/{execution_id}/changes` | `service_orders.maintenance.execute` | Existe en backend |
| Resolver cambio de alcance | `POST /service-orders/{service_order_id}/maintenance/{execution_id}/changes/{change_id}/resolve` | `service_orders.maintenance.authorize` | Existe en backend |
| Resolver investigación administrativa | `POST /service-orders/{service_order_id}/maintenance/{execution_id}/investigation/resolve` | `service_orders.maintenance.authorize` | Existe en backend |
| Terminar técnicamente | `POST /service-orders/{service_order_id}/maintenance/{execution_id}/technical-complete` | `service_orders.maintenance.execute` | Existe en backend |
| Generar reporte PDF | `GET /service-orders/{service_order_id}/maintenance/{execution_id}/report.pdf` | `service_orders.maintenance.manage` | Existe en backend |
| Firmar versión del reporte | `POST /service-orders/{service_order_id}/maintenance/{execution_id}/signature` | `service_orders.maintenance.sign` | Existe en backend |
| Cerrar Mantenimiento | `POST /service-orders/{service_order_id}/maintenance/{execution_id}/close` | `service_orders.maintenance.close` | Existe en backend |
| Aplicar override administrativo | `POST /service-orders/{service_order_id}/maintenance/{execution_id}/changes/{change_id}/resolve` | `service_orders.maintenance.authorize` | Existe en backend |

# 15. Equipos

## 15.1. Cambiar estado

| Microacción | Método y ruta | Permiso propuesto | Estado |
|---|---|---|---|
| Mark equipment calibrated | `POST /equipment/{equipment_id}/calibrated` | `equipment.create` | Existe en backend |
| Mark equipment labeled | `POST /equipment/{equipment_id}/labeled` | `equipment.create` | Existe en backend |
| Mark equipment not done | `POST /equipment/{equipment_id}/not-done` | `equipment.create` | Existe en backend |
| Mark equipment realizing | `POST /equipment/{equipment_id}/realizing` | `equipment.create` | Existe en backend |

## 15.2. Consultar

| Microacción | Método y ruta | Permiso propuesto | Estado |
|---|---|---|---|
| Equipment list | `GET /equipment` | `equipment.read` | Existe en backend |
| Equipment | `GET /equipment/{equipment_id}` | `equipment.read` | Existe en backend |

## 15.3. Crear

| Microacción | Método y ruta | Permiso propuesto | Estado |
|---|---|---|---|
| Equipment | `POST /equipment` | `equipment.create` | Existe en backend |

## 15.4. Eliminar

| Microacción | Método y ruta | Permiso propuesto | Estado |
|---|---|---|---|
| Equipment | `DELETE /equipment/{equipment_id}` | `equipment.delete` | Existe en backend |

## 15.5. Modificar

| Microacción | Método y ruta | Permiso propuesto | Estado |
|---|---|---|---|
| Equipment | `PATCH /equipment/{equipment_id}` | `equipment.update` | Existe en backend |

## 15.6. Editar campos y atributos

| Microacción de campo | Permiso propuesto | Evidencia | Estado |
|---|---|---|---|
| Modificar brand | `equipment.fields.brand.update` | `EquipmentUpdate.brand` | Requiere granularización |
| Modificar calibration scope | `equipment.fields.calibration_scope.update` | `EquipmentUpdate.calibration_scope` | Requiere granularización |
| Modificar certificate master document id | `equipment.fields.certificate_master_document_id.update` | `EquipmentUpdate.certificate_master_document_id` | Requiere granularización |
| Modificar comment | `equipment.fields.comment.update` | `EquipmentStatusChange.comment` | Requiere granularización |
| Modificar initial condition | `equipment.fields.initial_condition.update` | `EquipmentUpdate.initial_condition` | Requiere granularización |
| Modificar internal id | `equipment.fields.internal_id.update` | `EquipmentUpdate.internal_id` | Requiere granularización |
| Modificar model | `equipment.fields.model.update` | `EquipmentUpdate.model` | Requiere granularización |
| Modificar name | `equipment.fields.name.update` | `EquipmentUpdate.name` | Requiere granularización |
| Modificar notas | `equipment.fields.notes.update` | `EquipmentUpdate.notes` | Requiere granularización |
| Modificar range or capacity | `equipment.fields.range_or_capacity.update` | `EquipmentUpdate.range_or_capacity` | Requiere granularización |
| Modificar serial number | `equipment.fields.serial_number.update` | `EquipmentUpdate.serial_number` | Requiere granularización |
| Modificar service order item id | `equipment.fields.service_order_item_id.update` | `EquipmentUpdate.service_order_item_id` | Requiere granularización |
| Modificar work order id | `equipment.fields.work_order_id.update` | `EquipmentUpdate.work_order_id` | Requiere granularización |

# 16. Facturación y pagos

## 16.1. Conciliar

| Microacción | Método y ruta | Permiso propuesto | Estado |
|---|---|---|---|
| Reconcile invoice | `POST /invoices/{invoice_id}/reconcile` | `invoices.reconcile` | Existe en backend |

## 16.2. Confirmar

| Microacción | Método y ruta | Permiso propuesto | Estado |
|---|---|---|---|
| Confirm invoice review | `POST /invoices/{invoice_id}/confirm-review` | `invoices.review` | Existe en backend |

## 16.3. Consultar

| Microacción | Método y ruta | Permiso propuesto | Estado |
|---|---|---|---|
| Invoices | `GET /invoices` | `invoices.read` | Existe en backend |
| Invoice | `GET /invoices/{invoice_id}` | `invoices.read` | Existe en backend |

## 16.4. Crear

| Microacción | Método y ruta | Permiso propuesto | Estado |
|---|---|---|---|
| Invoice | `POST /invoices` | `invoices.create` | Existe en backend |

## 16.5. Emitir

| Microacción | Método y ruta | Permiso propuesto | Estado |
|---|---|---|---|
| Issue invoice | `POST /invoices/{invoice_id}/issue` | `invoices.issue` | Existe en backend |

## 16.6. Gestionar configuración

| Microacción | Método y ruta | Permiso propuesto | Estado |
|---|---|---|---|
| Invoice settings | `GET /invoice-settings` | `invoices.settings.manage` | Existe en backend |
| Invoice settings | `PATCH /invoice-settings` | `invoices.settings.manage` | Existe en backend |

## 16.7. Gestionar estado

| Microacción | Método y ruta | Permiso propuesto | Estado |
|---|---|---|---|
| Change status | `POST /invoices/{invoice_id}/status` | `invoices.create` | Existe en backend |

## 16.8. Gestionar notas de crédito

| Microacción | Método y ruta | Permiso propuesto | Estado |
|---|---|---|---|
| Credit note | `POST /invoices/{invoice_id}/credit-notes` | `invoices.credit_notes.create` | Existe en backend |

## 16.9. Gestionar pagos

| Microacción | Método y ruta | Permiso propuesto | Estado |
|---|---|---|---|
| Invoice payments | `GET /invoice-payments` | `invoices.read` | Existe en backend |
| Invoice payment | `GET /invoice-payments/{payment_id}` | `invoices.read` | Existe en backend |
| Payment receipt pdf | `GET /invoice-payments/{payment_id}/receipt-pdf` | `invoices.documents.download` | Existe en backend |
| Register payment | `POST /invoices/{invoice_id}/payments` | `invoices.payments.register` | Existe en backend |

## 16.10. Modificar

| Microacción | Método y ruta | Permiso propuesto | Estado |
|---|---|---|---|
| Update invoice | `PATCH /invoices/{invoice_id}` | `invoices.update` | Existe en backend |
| Update invoice | `PUT /invoices/{invoice_id}` | `invoices.update` | Existe en backend |

## 16.11. Operar recurso

| Microacción | Método y ruta | Permiso propuesto | Estado |
|---|---|---|---|
| Accounts receivable | `GET /invoices/accounts-receivable` | `invoices.read` | Existe en backend |
| Invoice dashboard | `GET /invoices/dashboard` | `invoices.read` | Existe en backend |
| Released uninvoiced | `GET /invoices/released-uninvoiced` | `invoices.read` | Existe en backend |
| Facturama document | `GET /invoices/{invoice_id}/facturama-documents/{kind}` | `invoices.read` | Existe en backend |
| Invoice fiscal xml | `GET /invoices/{invoice_id}/fiscal-xml` | `invoices.documents.download` | Existe en backend |
| Institutional invoice pdf | `GET /invoices/{invoice_id}/institutional-pdf` | `invoices.documents.download` | Existe en backend |
| Invoice source change | `POST /invoices/{invoice_id}/source-change` | `invoices.create` | Existe en backend |

## 16.12. Recuperar

| Microacción | Método y ruta | Permiso propuesto | Estado |
|---|---|---|---|
| Recover facturama documents | `POST /invoices/{invoice_id}/facturama-documents/recover` | `invoices.create` | Existe en backend |

## 16.13. Editar campos y atributos

| Microacción de campo | Permiso propuesto | Evidencia | Estado |
|---|---|---|---|
| Modificar allow manual folio | `invoices.fields.allow_manual_folio.update` | `InvoiceSettingsUpdate.allow_manual_folio` | Requiere granularización |
| Modificar bank account | `invoices.fields.bank_account.update` | `InvoicePaymentBase.bank_account` | Requiere granularización |
| Modificar bank accounts | `invoices.fields.bank_accounts.update` | `InvoiceSettingsUpdate.bank_accounts` | Requiere granularización |
| Modificar bank name | `invoices.fields.bank_name.update` | `InvoicePaymentBase.bank_name` | Requiere granularización |
| Modificar banks | `invoices.fields.banks.update` | `InvoiceSettingsUpdate.banks` | Requiere granularización |
| Modificar billing emails | `invoices.fields.billing_emails.update` | `InvoiceSettingsUpdate.billing_emails` | Requiere granularización |
| Modificar cancellation reason | `invoices.fields.cancellation_reason.update` | `InvoiceUpdate.cancellation_reason` | Requiere granularización |
| Modificar cantidad | `invoices.fields.quantity.update` | `InvoiceItemBase.quantity` | Requiere granularización |
| Modificar certificate id | `invoices.fields.certificate_id.update` | `InvoiceItemBase.certificate_id` | Requiere granularización |
| Modificar cfdi future parameters | `invoices.fields.cfdi_future_parameters.update` | `InvoiceSettingsUpdate.cfdi_future_parameters` | Requiere granularización |
| Modificar comment | `invoices.fields.comment.update` | `InvoiceStatusChange.comment` | Requiere granularización |
| Modificar credit days | `invoices.fields.credit_days.update` | `InvoiceUpdate.credit_days` | Requiere granularización |
| Modificar default credit days | `invoices.fields.default_credit_days.update` | `InvoiceSettingsUpdate.default_credit_days` | Requiere granularización |
| Modificar default series | `invoices.fields.default_series.update` | `InvoiceSettingsUpdate.default_series` | Requiere granularización |
| Modificar descripción | `invoices.fields.description.update` | `InvoiceItemBase.description` | Requiere granularización |
| Modificar due on | `invoices.fields.due_on.update` | `InvoiceUpdate.due_on` | Requiere granularización |
| Modificar emitter data | `invoices.fields.emitter_data.update` | `InvoiceSettingsUpdate.emitter_data` | Requiere granularización |
| Modificar equipment id | `invoices.fields.equipment_id.update` | `InvoiceItemBase.equipment_id` | Requiere granularización |
| Modificar forma de pago | `invoices.fields.payment_form.update` | `InvoicePaymentBase.payment_form` | Requiere granularización |
| Modificar forms of payment | `invoices.fields.forms_of_payment.update` | `InvoiceSettingsUpdate.forms_of_payment` | Requiere granularización |
| Modificar internal comments | `invoices.fields.internal_comments.update` | `InvoiceUpdate.internal_comments` | Requiere granularización |
| Modificar invoice id | `invoices.fields.invoice_id.update` | `InvoicePaymentRead.invoice_id` | Requiere granularización |
| Modificar issued on | `invoices.fields.issued_on.update` | `InvoiceUpdate.issued_on` | Requiere granularización |
| Modificar items | `invoices.fields.items.update` | `InvoiceCreate.items` | Requiere granularización |
| Modificar legal texts | `invoices.fields.legal_texts.update` | `InvoiceSettingsUpdate.legal_texts` | Requiere granularización |
| Modificar line total | `invoices.fields.line_total.update` | `InvoiceItemRead.line_total` | Requiere granularización |
| Modificar methods of payment | `invoices.fields.methods_of_payment.update` | `InvoiceSettingsUpdate.methods_of_payment` | Requiere granularización |
| Modificar método de pago | `invoices.fields.payment_method.update` | `InvoicePaymentBase.payment_method` | Requiere granularización |
| Modificar next sequence | `invoices.fields.next_sequence.update` | `InvoiceSettingsUpdate.next_sequence` | Requiere granularización |
| Modificar notas | `invoices.fields.notes.update` | `InvoiceItemBase.notes` | Requiere granularización |
| Modificar observations | `invoices.fields.observations.update` | `InvoiceUpdate.observations` | Requiere granularización |
| Modificar paid on | `invoices.fields.paid_on.update` | `InvoicePaymentBase.paid_on` | Requiere granularización |
| Modificar pdf template name | `invoices.fields.pdf_template_name.update` | `InvoiceSettingsUpdate.pdf_template_name` | Requiere granularización |
| Modificar quotation id | `invoices.fields.quotation_id.update` | `InvoiceUpdate.quotation_id` | Requiere granularización |
| Modificar quotation item id | `invoices.fields.quotation_item_id.update` | `InvoiceItemBase.quotation_item_id` | Requiere granularización |
| Modificar reference | `invoices.fields.reference.update` | `InvoicePaymentBase.reference` | Requiere granularización |
| Modificar registered by id | `invoices.fields.registered_by_id.update` | `InvoicePaymentRead.registered_by_id` | Requiere granularización |
| Modificar reset annually | `invoices.fields.reset_annually.update` | `InvoiceSettingsUpdate.reset_annually` | Requiere granularización |
| Modificar sat key | `invoices.fields.sat_key.update` | `InvoiceItemBase.sat_key` | Requiere granularización |
| Modificar sat product keys | `invoices.fields.sat_product_keys.update` | `InvoiceSettingsUpdate.sat_product_keys` | Requiere granularización |
| Modificar sat unit | `invoices.fields.sat_unit.update` | `InvoiceItemBase.sat_unit` | Requiere granularización |
| Modificar sat units | `invoices.fields.sat_units.update` | `InvoiceSettingsUpdate.sat_units` | Requiere granularización |
| Modificar service order id | `invoices.fields.service_order_id.update` | `InvoiceUpdate.service_order_id` | Requiere granularización |
| Modificar source type | `invoices.fields.source_type.update` | `InvoiceItemBase.source_type` | Requiere granularización |
| Modificar unit | `invoices.fields.unit.update` | `InvoiceItemBase.unit` | Requiere granularización |
| Modificar usage cfdi | `invoices.fields.usage_cfdi.update` | `InvoiceUpdate.usage_cfdi` | Requiere granularización |
| Modificar usage cfdi catalog | `invoices.fields.usage_cfdi_catalog.update` | `InvoiceSettingsUpdate.usage_cfdi_catalog` | Requiere granularización |

## 16.14. Gestionar estado

| Microacción de campo | Permiso propuesto | Evidencia | Estado |
|---|---|---|---|
| Modificar estado | `invoices.fields.status.update` | `InvoicePaymentBase.status` | Requiere granularización |

## 16.15. Gestionar identidad fiscal y legal

| Microacción de campo | Permiso propuesto | Evidencia | Estado |
|---|---|---|---|
| Modificar fiscal client id | `invoices.fields.fiscal_client_id.update` | `InvoiceUpdate.fiscal_client_id` | Requiere granularización |

## 16.16. Redefinir clasificación y alcance

| Microacción de campo | Permiso propuesto | Evidencia | Estado |
|---|---|---|---|
| Cambiar tipo de servicio | `invoices.fields.service_type.update` | `InvoiceItemBase.service_type` | Requiere granularización |

## 16.17. Redefinir condiciones económicas

| Microacción de campo | Permiso propuesto | Evidencia | Estado |
|---|---|---|---|
| Modificar currency catalog | `invoices.fields.currency_catalog.update` | `InvoiceSettingsUpdate.currency_catalog` | Requiere granularización |
| Modificar default currency | `invoices.fields.default_currency.update` | `InvoiceSettingsUpdate.default_currency` | Requiere granularización |
| Modificar default tax rate | `invoices.fields.default_tax_rate.update` | `InvoiceSettingsUpdate.default_tax_rate` | Requiere granularización |
| Modificar discount total | `invoices.fields.discount_total.update` | `InvoiceItemBase.discount_total` | Requiere granularización |
| Modificar importe | `invoices.fields.amount.update` | `InvoicePaymentBase.amount` | Requiere granularización |
| Modificar moneda | `invoices.fields.currency.update` | `InvoiceUpdate.currency` | Requiere granularización |
| Modificar precio unitario | `invoices.fields.unit_price.update` | `InvoiceItemBase.unit_price` | Requiere granularización |
| Modificar tasa de impuesto | `invoices.fields.tax_rate.update` | `InvoiceItemBase.tax_rate` | Requiere granularización |
| Modificar tax regime catalog | `invoices.fields.tax_regime_catalog.update` | `InvoiceSettingsUpdate.tax_regime_catalog` | Requiere granularización |
| Modificar tax total | `invoices.fields.tax_total.update` | `InvoiceItemRead.tax_total` | Requiere granularización |

# 17. Hojas de campo

## 17.1. Completar

| Microacción | Método y ruta | Permiso propuesto | Estado |
|---|---|---|---|
| Complete field sheet | `POST /field-sheets/{field_sheet_id}/complete` | `field_sheets.create` | Existe en backend |

## 17.2. Consultar

| Microacción | Método y ruta | Permiso propuesto | Estado |
|---|---|---|---|
| Field sheets | `GET /field-sheets` | `field_sheets.read` | Existe en backend |
| Field sheet | `GET /field-sheets/{field_sheet_id}` | `field_sheets.read` | Existe en backend |
| Field sheet pdf | `GET /field-sheets/{field_sheet_id}/pdf` | `field_sheets.documents.download` | Existe en backend |

## 17.3. Crear

| Microacción | Método y ruta | Permiso propuesto | Estado |
|---|---|---|---|
| Field sheet | `POST /field-sheets` | `field_sheets.create` | Existe en backend |

## 17.4. Eliminar

| Microacción | Método y ruta | Permiso propuesto | Estado |
|---|---|---|---|
| Field sheet | `DELETE /field-sheets/{field_sheet_id}` | `field_sheets.delete` | Existe en backend |

## 17.5. Modificar

| Microacción | Método y ruta | Permiso propuesto | Estado |
|---|---|---|---|
| Field sheet | `PATCH /field-sheets/{field_sheet_id}` | `field_sheets.update` | Existe en backend |

## 17.6. Revisar

| Microacción | Método y ruta | Permiso propuesto | Estado |
|---|---|---|---|
| Review field sheet | `POST /field-sheets/{field_sheet_id}/review` | `field_sheets.review` | Existe en backend |

## 17.7. Editar campos y atributos

| Microacción de campo | Permiso propuesto | Evidencia | Estado |
|---|---|---|---|
| Modificar apply certificate client to order | `field_sheets.fields.apply_certificate_client_to_order.update` | `FieldSheetUpdate.apply_certificate_client_to_order` | Requiere granularización |
| Modificar attention | `field_sheets.fields.attention.update` | `FieldSheetUpdate.attention` | Requiere granularización |
| Modificar calibrated by | `field_sheets.fields.calibrated_by.update` | `FieldSheetUpdate.calibrated_by` | Requiere granularización |
| Modificar calibration date | `field_sheets.fields.calibration_date.update` | `FieldSheetUpdate.calibration_date` | Requiere granularización |
| Modificar calibration place | `field_sheets.fields.calibration_place.update` | `FieldSheetUpdate.calibration_place` | Requiere granularización |
| Modificar calibration procedure id | `field_sheets.fields.calibration_procedure_id.update` | `FieldSheetUpdate.calibration_procedure_id` | Requiere granularización |
| Modificar capture values | `field_sheets.fields.capture_values.update` | `FieldSheetUpdate.capture_values` | Requiere granularización |
| Modificar certificate client address | `field_sheets.fields.certificate_client_address.update` | `FieldSheetUpdate.certificate_client_address` | Requiere granularización |
| Modificar certificate client attention | `field_sheets.fields.certificate_client_attention.update` | `FieldSheetUpdate.certificate_client_attention` | Requiere granularización |
| Modificar certificate client company | `field_sheets.fields.certificate_client_company.update` | `FieldSheetUpdate.certificate_client_company` | Requiere granularización |
| Modificar certificate client mode | `field_sheets.fields.certificate_client_mode.update` | `FieldSheetUpdate.certificate_client_mode` | Requiere granularización |
| Modificar comment | `field_sheets.fields.comment.update` | `FieldSheetStatusChange.comment` | Requiere granularización |
| Modificar company | `field_sheets.fields.company.update` | `FieldSheetUpdate.company` | Requiere granularización |
| Modificar consider equipment deviations | `field_sheets.fields.consider_equipment_deviations.update` | `FieldSheetUpdate.consider_equipment_deviations` | Requiere granularización |
| Modificar domicilio | `field_sheets.fields.address.update` | `FieldSheetUpdate.address` | Requiere granularización |
| Modificar environment humidity end | `field_sheets.fields.environment_humidity_end.update` | `FieldSheetUpdate.environment_humidity_end` | Requiere granularización |
| Modificar environment humidity start | `field_sheets.fields.environment_humidity_start.update` | `FieldSheetUpdate.environment_humidity_start` | Requiere granularización |
| Modificar environment temperature end | `field_sheets.fields.environment_temperature_end.update` | `FieldSheetUpdate.environment_temperature_end` | Requiere granularización |
| Modificar environment temperature start | `field_sheets.fields.environment_temperature_start.update` | `FieldSheetUpdate.environment_temperature_start` | Requiere granularización |
| Modificar environmental conditions | `field_sheets.fields.environmental_conditions.update` | `FieldSheetUpdate.environmental_conditions` | Requiere granularización |
| Modificar equipment general condition | `field_sheets.fields.equipment_general_condition.update` | `FieldSheetUpdate.equipment_general_condition` | Requiere granularización |
| Modificar evidence notes | `field_sheets.fields.evidence_notes.update` | `FieldSheetUpdate.evidence_notes` | Requiere granularización |
| Modificar final condition | `field_sheets.fields.final_condition.update` | `FieldSheetUpdate.final_condition` | Requiere granularización |
| Modificar initial condition | `field_sheets.fields.initial_condition.update` | `FieldSheetUpdate.initial_condition` | Requiere granularización |
| Modificar location | `field_sheets.fields.location.update` | `FieldSheetUpdate.location` | Requiere granularización |
| Modificar method | `field_sheets.fields.method.update` | `FieldSheetUpdate.method` | Requiere granularización |
| Modificar minimum division | `field_sheets.fields.minimum_division.update` | `FieldSheetUpdate.minimum_division` | Requiere granularización |
| Modificar next calibration date | `field_sheets.fields.next_calibration_date.update` | `FieldSheetUpdate.next_calibration_date` | Requiere granularización |
| Modificar observations | `field_sheets.fields.observations.update` | `FieldSheetUpdate.observations` | Requiere granularización |
| Modificar pattern used | `field_sheets.fields.pattern_used.update` | `FieldSheetUpdate.pattern_used` | Requiere granularización |
| Modificar purchase order or quotation | `field_sheets.fields.purchase_order_or_quotation.update` | `FieldSheetUpdate.purchase_order_or_quotation` | Requiere granularización |
| Modificar reception date | `field_sheets.fields.reception_date.update` | `FieldSheetUpdate.reception_date` | Requiere granularización |
| Modificar reference standards | `field_sheets.fields.reference_standards.update` | `FieldSheetUpdate.reference_standards` | Requiere granularización |
| Modificar report made by | `field_sheets.fields.report_made_by.update` | `FieldSheetUpdate.report_made_by` | Requiere granularización |
| Modificar results | `field_sheets.fields.results.update` | `FieldSheetUpdate.results` | Requiere granularización |
| Modificar results rows | `field_sheets.fields.results_rows.update` | `FieldSheetUpdate.results_rows` | Requiere granularización |
| Modificar reviewed by | `field_sheets.fields.reviewed_by.update` | `FieldSheetUpdate.reviewed_by` | Requiere granularización |
| Modificar technician notes | `field_sheets.fields.technician_notes.update` | `FieldSheetUpdate.technician_notes` | Requiere granularización |
| Modificar template key | `field_sheets.fields.template_key.update` | `FieldSheetUpdate.template_key` | Requiere granularización |
| Modificar template snapshot | `field_sheets.fields.template_snapshot.update` | `FieldSheetCreate.template_snapshot` | Requiere granularización |
| Modificar template version | `field_sheets.fields.template_version.update` | `FieldSheetCreate.template_version` | Requiere granularización |
| Modificar units | `field_sheets.fields.units.update` | `FieldSheetUpdate.units` | Requiere granularización |
| Modificar work order id | `field_sheets.fields.work_order_id.update` | `FieldSheetUpdate.work_order_id` | Requiere granularización |

## 17.8. Gestionar firmas

| Microacción de campo | Permiso propuesto | Evidencia | Estado |
|---|---|---|---|
| Modificar signatures | `field_sheets.fields.signatures.update` | `FieldSheetUpdate.signatures` | Requiere granularización |

# 18. Incertidumbre

## 18.1. Gestionar excepciones

| Microacción | Método y ruta | Permiso propuesto | Estado |
|---|---|---|---|
| Uncertainty exceptions | `GET /uncertainty/exceptions` | `uncertainty.read` | Existe en backend |
| Uncertainty exception | `POST /uncertainty/exceptions` | `uncertainty.create` | Existe en backend |

## 18.2. Gestionar incertidumbre

| Microacción | Método y ruta | Permiso propuesto | Estado |
|---|---|---|---|
| Uncertainty component | `DELETE /uncertainty/components/{component_id}` | `uncertainty.components.manage` | Existe en backend |
| Uncertainty component | `PATCH /uncertainty/components/{component_id}` | `uncertainty.components.manage` | Existe en backend |
| Uncertainty preview | `GET /uncertainty/field-sheets/{field_sheet_id}/preview` | `uncertainty.read` | Existe en backend |
| Uncertainty formula | `DELETE /uncertainty/formulas/{formula_id}` | `uncertainty.formulas.manage` | Existe en backend |
| Uncertainty formula | `PATCH /uncertainty/formulas/{formula_id}` | `uncertainty.formulas.manage` | Existe en backend |
| Uncertainty models | `GET /uncertainty/models` | `uncertainty.read` | Existe en backend |
| Uncertainty model | `POST /uncertainty/models` | `uncertainty.create` | Existe en backend |
| Uncertainty model | `GET /uncertainty/models/{model_id}` | `uncertainty.read` | Existe en backend |
| Uncertainty model | `PATCH /uncertainty/models/{model_id}` | `uncertainty.update` | Existe en backend |

## 18.3. Gestionar versiones

| Microacción | Método y ruta | Permiso propuesto | Estado |
|---|---|---|---|
| Uncertainty model version | `GET /uncertainty/model-versions/{version_id}` | `uncertainty.read` | Existe en backend |
| Uncertainty model version | `PATCH /uncertainty/model-versions/{version_id}` | `uncertainty.update` | Existe en backend |
| Approve uncertainty model version | `POST /uncertainty/model-versions/{version_id}/approve` | `uncertainty.versions.approve` | Existe en backend |
| Archive uncertainty model version | `POST /uncertainty/model-versions/{version_id}/archive` | `uncertainty.versions.archive` | Existe en backend |
| Clone uncertainty model version | `POST /uncertainty/model-versions/{version_id}/clone` | `uncertainty.create` | Existe en backend |
| Uncertainty component | `POST /uncertainty/model-versions/{version_id}/components` | `uncertainty.components.manage` | Existe en backend |
| Uncertainty formula | `POST /uncertainty/model-versions/{version_id}/formulas` | `uncertainty.formulas.manage` | Existe en backend |
| Obsolete uncertainty model version | `POST /uncertainty/model-versions/{version_id}/obsolete` | `uncertainty.versions.obsolete` | Existe en backend |
| Submit uncertainty model version review | `POST /uncertainty/model-versions/{version_id}/submit-review` | `uncertainty.versions.submit_review` | Existe en backend |
| Uncertainty model versions | `GET /uncertainty/models/{model_id}/versions` | `uncertainty.read` | Existe en backend |
| Uncertainty model version | `POST /uncertainty/models/{model_id}/versions` | `uncertainty.create` | Existe en backend |

## 18.4. Editar campos y atributos

| Microacción de campo | Permiso propuesto | Evidencia | Estado |
|---|---|---|---|
| Modificar calculation snapshot | `uncertainty.fields.calculation_snapshot.update` | `UncertaintyPreview.calculation_snapshot` | Requiere granularización |
| Modificar change summary | `uncertainty.fields.change_summary.update` | `UncertaintyModelVersionUpdate.change_summary` | Requiere granularización |
| Modificar code | `uncertainty.fields.code.update` | `UncertaintyModelUpdate.code` | Requiere granularización |
| Modificar component results | `uncertainty.fields.component_results.update` | `UncertaintyPreview.component_results` | Requiere granularización |
| Modificar components | `uncertainty.fields.components.update` | `UncertaintyModelCreate.components` | Requiere granularización |
| Modificar default coverage factor | `uncertainty.fields.default_coverage_factor.update` | `UncertaintyModelUpdate.default_coverage_factor` | Requiere granularización |
| Modificar descripción | `uncertainty.fields.description.update` | `UncertaintyComponentUpdate.description` | Requiere granularización |
| Modificar distribution | `uncertainty.fields.distribution.update` | `UncertaintyComponentUpdate.distribution` | Requiere granularización |
| Modificar divisor | `uncertainty.fields.divisor.update` | `UncertaintyComponentUpdate.divisor` | Requiere granularización |
| Modificar equipment family | `uncertainty.fields.equipment_family.update` | `UncertaintyModelUpdate.equipment_family` | Requiere granularización |
| Modificar errors | `uncertainty.fields.errors.update` | `UncertaintyPreview.errors` | Requiere granularización |
| Modificar expression | `uncertainty.fields.expression.update` | `UncertaintyFormulaUpdate.expression` | Requiere granularización |
| Modificar field sheet id | `uncertainty.fields.field_sheet_id.update` | `UncertaintyPreview.field_sheet_id` | Requiere granularización |
| Modificar formula results | `uncertainty.fields.formula_results.update` | `UncertaintyPreview.formula_results` | Requiere granularización |
| Modificar formulas | `uncertainty.fields.formulas.update` | `UncertaintyModelCreate.formulas` | Requiere granularización |
| Modificar input snapshot | `uncertainty.fields.input_snapshot.update` | `UncertaintyPreview.input_snapshot` | Requiere granularización |
| Modificar key | `uncertainty.fields.key.update` | `UncertaintyComponentUpdate.key` | Requiere granularización |
| Modificar magnitude | `uncertainty.fields.magnitude.update` | `UncertaintyModelUpdate.magnitude` | Requiere granularización |
| Modificar metadata json | `uncertainty.fields.metadata_json.update` | `UncertaintyComponentUpdate.metadata_json` | Requiere granularización |
| Modificar name | `uncertainty.fields.name.update` | `UncertaintyComponentUpdate.name` | Requiere granularización |
| Modificar notas | `uncertainty.fields.notes.update` | `UncertaintyModelUpdate.notes` | Requiere granularización |
| Modificar required | `uncertainty.fields.required.update` | `UncertaintyComponentUpdate.required` | Requiere granularización |
| Modificar result key | `uncertainty.fields.result_key.update` | `UncertaintyFormulaUpdate.result_key` | Requiere granularización |
| Modificar sensitivity coefficient | `uncertainty.fields.sensitivity_coefficient.update` | `UncertaintyComponentUpdate.sensitivity_coefficient` | Requiere granularización |
| Modificar sort order | `uncertainty.fields.sort_order.update` | `UncertaintyComponentUpdate.sort_order` | Requiere granularización |
| Modificar source type | `uncertainty.fields.source_type.update` | `UncertaintyComponentUpdate.source_type` | Requiere granularización |
| Modificar uncertainty model id | `uncertainty.fields.uncertainty_model_id.update` | `UncertaintyPreview.uncertainty_model_id` | Requiere granularización |
| Modificar uncertainty model version id | `uncertainty.fields.uncertainty_model_version_id.update` | `UncertaintyPreview.uncertainty_model_version_id` | Requiere granularización |
| Modificar value expression | `uncertainty.fields.value_expression.update` | `UncertaintyComponentUpdate.value_expression` | Requiere granularización |
| Modificar version | `uncertainty.fields.version.update` | `UncertaintyModelUpdate.version` | Requiere granularización |
| Modificar version number | `uncertainty.fields.version_number.update` | `UncertaintyModelVersionUpdate.version_number` | Requiere granularización |
| Modificar warnings | `uncertainty.fields.warnings.update` | `UncertaintyPreview.warnings` | Requiere granularización |

## 18.5. Gestionar acceso y seguridad

| Microacción de campo | Permiso propuesto | Evidencia | Estado |
|---|---|---|---|
| Activar o desactivar | `uncertainty.fields.is_active.update` | `UncertaintyComponentUpdate.is_active` | Requiere granularización |
| Modificar is active formula | `uncertainty.fields.is_active_formula.update` | `UncertaintyFormulaUpdate.is_active_formula` | Requiere granularización |

## 18.6. Gestionar estado

| Microacción de campo | Permiso propuesto | Evidencia | Estado |
|---|---|---|---|
| Modificar estado | `uncertainty.fields.status.update` | `UncertaintyModelUpdate.status` | Requiere granularización |

# 19. Integraciones

## 19.1. Gestionar estado

| Microacción | Método y ruta | Permiso propuesto | Estado |
|---|---|---|---|
| Facturama status | `GET /integrations/facturama/status` | `integrations.read` | Existe en backend |

# 20. Interpretaciones documentales

## 20.1. Consultar

| Microacción | Método y ruta | Permiso propuesto | Estado |
|---|---|---|---|
| Document interpretations | `GET /document-interpretations` | `document_interpretations.read` | Existe en backend |
| Document interpretation | `GET /document-interpretations/{interpretation_id}` | `document_interpretations.read` | Existe en backend |

## 20.2. Crear

| Microacción | Método y ruta | Permiso propuesto | Estado |
|---|---|---|---|
| Document interpretation | `POST /document-interpretations` | `document_interpretations.create` | Existe en backend |
| Approve document interpretation | `POST /document-interpretations/{interpretation_id}/approve` | `document_interpretations.approve` | Existe en backend |

## 20.3. Gestionar versiones

| Microacción | Método y ruta | Permiso propuesto | Estado |
|---|---|---|---|
| Document interpretation new version | `POST /document-interpretations/{interpretation_id}/new-version` | `document_interpretations.create` | Existe en backend |

## 20.4. Modificar

| Microacción | Método y ruta | Permiso propuesto | Estado |
|---|---|---|---|
| Document interpretation | `PATCH /document-interpretations/{interpretation_id}` | `document_interpretations.update` | Existe en backend |

# 21. Metrología

## 21.1. Consultar

| Microacción | Método y ruta | Permiso propuesto | Estado |
|---|---|---|---|
| Profiles | `GET /metrology/profiles` | `metrology.read` | Existe en backend |

## 21.2. Crear

| Microacción | Método y ruta | Permiso propuesto | Estado |
|---|---|---|---|
| Calculate preview | `POST /metrology/calculate-preview` | `metrology.review` | Existe en backend |

# 22. Motores operativos

## 22.1. Consultar

| Microacción | Método y ruta | Permiso propuesto | Estado |
|---|---|---|---|
| Document selection | `GET /operational-engines/field-sheets/{field_sheet_id}/document-selection` | `operational_engines.read` | Existe en backend |
| Operational flow | `GET /operational-engines/flow` | `operational_engines.read` | Existe en backend |

## 22.2. Crear

| Microacción | Método y ruta | Permiso propuesto | Estado |
|---|---|---|---|
| Calculation | `POST /operational-engines/calculation` | `operational_engines.create` | Existe en backend |
| Validate standards | `POST /operational-engines/field-sheets/{field_sheet_id}/validate-standards` | `operational_engines.create` | Existe en backend |

## 22.3. Gestionar captura

| Microacción | Método y ruta | Permiso propuesto | Estado |
|---|---|---|---|
| Technical capture | `GET /operational-engines/field-sheets/{field_sheet_id}/technical-capture` | `operational_engines.read` | Existe en backend |

## 22.4. Gestionar certificados

| Microacción | Método y ruta | Permiso propuesto | Estado |
|---|---|---|---|
| Label payload | `GET /operational-engines/certificates/{certificate_id}/label` | `operational_engines.read` | Existe en backend |
| Prepare certificate | `POST /operational-engines/field-sheets/{field_sheet_id}/prepare-certificate` | `operational_engines.create` | Existe en backend |
| Suggest certificate folio | `POST /operational-engines/folios/certificates/suggest` | `operational_engines.create` | Existe en backend |

# 23. Módulos del sistema

## 23.1. Consultar

| Microacción | Método y ruta | Permiso propuesto | Estado |
|---|---|---|---|
| Modules | `GET /modules` | `modules.read` | Existe en backend |

# 24. Notificaciones

## 24.1. Consultar

| Microacción | Método y ruta | Permiso propuesto | Estado |
|---|---|---|---|
| Notifications | `GET /notifications` | `notifications.read` | Existe en backend |
| Notifications unread count | `GET /notifications/unread-count` | `notifications.read` | Existe en backend |

## 24.2. Crear

| Microacción | Método y ruta | Permiso propuesto | Estado |
|---|---|---|---|
| Notifications read all | `POST /notifications/read-all` | `notifications.create` | Existe en backend |
| Notification read | `POST /notifications/{notification_id}/read` | `notifications.create` | Existe en backend |

# 25. Patrones de referencia

## 25.1. Consultar

| Microacción | Método y ruta | Permiso propuesto | Estado |
|---|---|---|---|
| Reference standards | `GET /reference-standards` | `standards.read` | Existe en backend |
| Reference standard | `GET /reference-standards/{standard_id}` | `standards.read` | Existe en backend |

## 25.2. Crear

| Microacción | Método y ruta | Permiso propuesto | Estado |
|---|---|---|---|
| Reference standard | `POST /reference-standards` | `standards.create` | Existe en backend |

## 25.3. Eliminar

| Microacción | Método y ruta | Permiso propuesto | Estado |
|---|---|---|---|
| Reference standard | `DELETE /reference-standards/{standard_id}` | `standards.delete` | Existe en backend |

## 25.4. Gestionar incertidumbre

| Microacción | Método y ruta | Permiso propuesto | Estado |
|---|---|---|---|
| Reference standard uncertainty | `POST /reference-standards/{standard_id}/uncertainties` | `standards.create` | Existe en backend |
| Reference standard uncertainty | `DELETE /reference-standards/{standard_id}/uncertainties/{uncertainty_id}` | `standards.delete` | Existe en backend |
| Reference standard uncertainty | `PATCH /reference-standards/{standard_id}/uncertainties/{uncertainty_id}` | `standards.update` | Existe en backend |

## 25.5. Modificar

| Microacción | Método y ruta | Permiso propuesto | Estado |
|---|---|---|---|
| Reference standard | `PATCH /reference-standards/{standard_id}` | `standards.update` | Existe en backend |

## 25.6. Editar campos y atributos

| Microacción de campo | Permiso propuesto | Evidencia | Estado |
|---|---|---|---|
| Modificar brand | `standards.fields.brand.update` | `ReferenceStandardUpdate.brand` | Requiere granularización |
| Modificar calibrated on | `standards.fields.calibrated_on.update` | `ReferenceStandardUpdate.calibrated_on` | Requiere granularización |
| Modificar calibration laboratory | `standards.fields.calibration_laboratory.update` | `ReferenceStandardUpdate.calibration_laboratory` | Requiere granularización |
| Modificar certificate file path | `standards.fields.certificate_file_path.update` | `ReferenceStandardUpdate.certificate_file_path` | Requiere granularización |
| Modificar certificate number | `standards.fields.certificate_number.update` | `ReferenceStandardUpdate.certificate_number` | Requiere granularización |
| Modificar coverage factor k | `standards.fields.coverage_factor_k.update` | `ReferenceStandardUncertaintyUpdate.coverage_factor_k` | Requiere granularización |
| Modificar descripción | `standards.fields.description.update` | `ReferenceStandardUpdate.description` | Requiere granularización |
| Modificar distribution | `standards.fields.distribution.update` | `ReferenceStandardUncertaintyUpdate.distribution` | Requiere granularización |
| Modificar identification | `standards.fields.identification.update` | `ReferenceStandardUpdate.identification` | Requiere granularización |
| Modificar internal code | `standards.fields.internal_code.update` | `ReferenceStandardUpdate.internal_code` | Requiere granularización |
| Modificar magnitude | `standards.fields.magnitude.update` | `ReferenceStandardUpdate.magnitude` | Requiere granularización |
| Modificar model | `standards.fields.model.update` | `ReferenceStandardUpdate.model` | Requiere granularización |
| Modificar name | `standards.fields.name.update` | `ReferenceStandardUpdate.name` | Requiere granularización |
| Modificar next calibration on | `standards.fields.next_calibration_on.update` | `ReferenceStandardUpdate.next_calibration_on` | Requiere granularización |
| Modificar notas | `standards.fields.notes.update` | `ReferenceStandardUncertaintyUpdate.notes` | Requiere granularización |
| Modificar owner company | `standards.fields.owner_company.update` | `ReferenceStandardUpdate.owner_company` | Requiere granularización |
| Modificar provider | `standards.fields.provider.update` | `ReferenceStandardUpdate.provider` | Requiere granularización |
| Modificar range max | `standards.fields.range_max.update` | `ReferenceStandardUncertaintyUpdate.range_max` | Requiere granularización |
| Modificar range min | `standards.fields.range_min.update` | `ReferenceStandardUncertaintyUpdate.range_min` | Requiere granularización |
| Modificar resolution | `standards.fields.resolution.update` | `ReferenceStandardUpdate.resolution` | Requiere granularización |
| Modificar serial number | `standards.fields.serial_number.update` | `ReferenceStandardUpdate.serial_number` | Requiere granularización |
| Modificar uncertainties | `standards.fields.uncertainties.update` | `ReferenceStandardCreate.uncertainties` | Requiere granularización |
| Modificar uncertainty value | `standards.fields.uncertainty_value.update` | `ReferenceStandardUncertaintyUpdate.uncertainty_value` | Requiere granularización |
| Modificar unit | `standards.fields.unit.update` | `ReferenceStandardUncertaintyUpdate.unit` | Requiere granularización |

## 25.7. Gestionar acceso y seguridad

| Microacción de campo | Permiso propuesto | Evidencia | Estado |
|---|---|---|---|
| Activar o desactivar | `standards.fields.is_active.update` | `ReferenceStandardUncertaintyUpdate.is_active` | Requiere granularización |

## 25.8. Gestionar estado

| Microacción de campo | Permiso propuesto | Evidencia | Estado |
|---|---|---|---|
| Modificar estado | `standards.fields.status.update` | `ReferenceStandardUpdate.status` | Requiere granularización |

# 26. Perfiles técnicos

## 26.1. Consultar

| Microacción | Método y ruta | Permiso propuesto | Estado |
|---|---|---|---|
| Technical profiles | `GET /technical-profiles` | `technical_profiles.read` | Existe en backend |
| Resolved technical profile | `GET /technical-profiles/resolve` | `technical_profiles.read` | Existe en backend |
| Technical profile | `GET /technical-profiles/{profile_id}` | `technical_profiles.read` | Existe en backend |

## 26.2. Crear

| Microacción | Método y ruta | Permiso propuesto | Estado |
|---|---|---|---|
| Technical profile | `POST /technical-profiles` | `technical_profiles.create` | Existe en backend |
| Approve technical profile | `POST /technical-profiles/{profile_id}/approve` | `technical_profiles.approve` | Existe en backend |

## 26.3. Gestionar versiones

| Microacción | Método y ruta | Permiso propuesto | Estado |
|---|---|---|---|
| Technical profile new version | `POST /technical-profiles/{profile_id}/new-version` | `technical_profiles.create` | Existe en backend |

## 26.4. Modificar

| Microacción | Método y ruta | Permiso propuesto | Estado |
|---|---|---|---|
| Technical profile | `PATCH /technical-profiles/{profile_id}` | `technical_profiles.update` | Existe en backend |

# 27. Plantillas de hojas de campo

## 27.1. Activar

| Microacción | Método y ruta | Permiso propuesto | Estado |
|---|---|---|---|
| Activate template | `POST /field-sheet-templates/{template_id}/activate` | `field_sheet_templates.activate` | Existe en backend |

## 27.2. Consultar

| Microacción | Método y ruta | Permiso propuesto | Estado |
|---|---|---|---|
| Template catalog | `GET /field-sheet-templates/catalog` | `field_sheet_templates.read` | Existe en backend |
| Template | `GET /field-sheet-templates/{template_key}` | `field_sheet_templates.read` | Existe en backend |

## 27.3. Crear

| Microacción | Método y ruta | Permiso propuesto | Estado |
|---|---|---|---|
| Template | `POST /field-sheet-templates` | `field_sheet_templates.create` | Existe en backend |

## 27.4. Duplicar

| Microacción | Método y ruta | Permiso propuesto | Estado |
|---|---|---|---|
| Duplicate template | `POST /field-sheet-templates/{template_id}/duplicate` | `field_sheet_templates.create` | Existe en backend |

## 27.5. Exportar

| Microacción | Método y ruta | Permiso propuesto | Estado |
|---|---|---|---|
| Export template | `GET /field-sheet-templates/{template_id}/export` | `field_sheet_templates.documents.download` | Existe en backend |

## 27.6. Importar

| Microacción | Método y ruta | Permiso propuesto | Estado |
|---|---|---|---|
| Import template | `POST /field-sheet-templates/import` | `field_sheet_templates.create` | Existe en backend |

## 27.7. Listar

| Microacción | Método y ruta | Permiso propuesto | Estado |
|---|---|---|---|
| List templates | `GET /field-sheet-templates` | `field_sheet_templates.read` | Existe en backend |

## 27.8. Modificar

| Microacción | Método y ruta | Permiso propuesto | Estado |
|---|---|---|---|
| Template | `PATCH /field-sheet-templates/{template_id}` | `field_sheet_templates.update` | Existe en backend |

## 27.9. Operar recurso

| Microacción | Método y ruta | Permiso propuesto | Estado |
|---|---|---|---|
| Remove template | `DELETE /field-sheet-templates/{template_id}` | `field_sheet_templates.delete` | Existe en backend |

## 27.10. Editar campos y atributos

| Microacción de campo | Permiso propuesto | Evidencia | Estado |
|---|---|---|---|
| Modificar automation | `field_sheet_templates.fields.automation.update` | `FieldSheetTemplateCreate.automation` | Requiere granularización |
| Modificar blocks | `field_sheet_templates.fields.blocks.update` | `FieldSheetTemplateCreate.blocks` | Requiere granularización |
| Modificar code | `field_sheet_templates.fields.code.update` | `FieldSheetTemplateCreate.code` | Requiere granularización |
| Modificar descripción | `field_sheet_templates.fields.description.update` | `FieldSheetTemplateCreate.description` | Requiere granularización |
| Modificar document code | `field_sheet_templates.fields.document_code.update` | `FieldSheetTemplateCreate.document_code` | Requiere granularización |
| Modificar document revision | `field_sheet_templates.fields.document_revision.update` | `FieldSheetTemplateCreate.document_revision` | Requiere granularización |
| Modificar metadata | `field_sheet_templates.fields.metadata.update` | `FieldSheetTemplateCreate.metadata` | Requiere granularización |
| Modificar name | `field_sheet_templates.fields.name.update` | `FieldSheetTemplateCreate.name` | Requiere granularización |
| Modificar pages | `field_sheet_templates.fields.pages.update` | `FieldSheetTemplateCreate.pages` | Requiere granularización |
| Modificar pagination | `field_sheet_templates.fields.pagination.update` | `FieldSheetTemplateCreate.pagination` | Requiere granularización |
| Modificar pdf config | `field_sheet_templates.fields.pdf_config.update` | `FieldSheetTemplateCreate.pdf_config` | Requiere granularización |
| Modificar pdf template | `field_sheet_templates.fields.pdf_template.update` | `FieldSheetTemplateCreate.pdf_template` | Requiere granularización |
| Modificar print config | `field_sheet_templates.fields.print_config.update` | `FieldSheetTemplateCreate.print_config` | Requiere granularización |
| Modificar result sections | `field_sheet_templates.fields.result_sections.update` | `FieldSheetTemplateCreate.result_sections` | Requiere granularización |
| Modificar revision | `field_sheet_templates.fields.revision.update` | `FieldSheetTemplateCreate.revision` | Requiere granularización |
| Modificar table family | `field_sheet_templates.fields.table_family.update` | `FieldSheetTemplateCreate.table_family` | Requiere granularización |
| Modificar template key | `field_sheet_templates.fields.template_key.update` | `FieldSheetTemplateCreate.template_key` | Requiere granularización |
| Modificar validations | `field_sheet_templates.fields.validations.update` | `FieldSheetTemplateCreate.validations` | Requiere granularización |
| Modificar visible fields | `field_sheet_templates.fields.visible_fields.update` | `FieldSheetTemplateCreate.visible_fields` | Requiere granularización |

## 27.11. Gestionar acceso y seguridad

| Microacción de campo | Permiso propuesto | Evidencia | Estado |
|---|---|---|---|
| Modificar permissions config | `field_sheet_templates.fields.permissions_config.update` | `FieldSheetTemplateCreate.permissions_config` | Requiere granularización |

## 27.12. Gestionar estado

| Microacción de campo | Permiso propuesto | Evidencia | Estado |
|---|---|---|---|
| Modificar estado | `field_sheet_templates.fields.status.update` | `FieldSheetTemplateCreate.status` | Requiere granularización |

## 27.13. Gestionar firmas

| Microacción de campo | Permiso propuesto | Evidencia | Estado |
|---|---|---|---|
| Modificar signature layout | `field_sheet_templates.fields.signature_layout.update` | `FieldSheetTemplateCreate.signature_layout` | Requiere granularización |

# 28. Plantillas documentales

## 28.1. Consultar

| Microacción | Método y ruta | Permiso propuesto | Estado |
|---|---|---|---|
| Quotation template | `GET /document-templates/quotation` | `document_templates.read` | Existe en backend |

## 28.2. Modificar

| Microacción | Método y ruta | Permiso propuesto | Estado |
|---|---|---|---|
| Quotation template | `PATCH /document-templates/quotation` | `document_templates.update` | Existe en backend |

## 28.3. Restaurar

| Microacción | Método y ruta | Permiso propuesto | Estado |
|---|---|---|---|
| Restore quotation template | `POST /document-templates/quotation/restore-defaults` | `document_templates.snapshots.restore` | Existe en backend |

## 28.4. Editar campos y atributos

| Microacción de campo | Permiso propuesto | Evidencia | Estado |
|---|---|---|---|
| Modificar acceptance text | `document_templates.fields.acceptance_text.update` | `DocumentTemplateUpdate.acceptance_text` | Requiere granularización |
| Modificar commercial terms | `document_templates.fields.commercial_terms.update` | `DocumentTemplateUpdate.commercial_terms` | Requiere granularización |
| Modificar company address | `document_templates.fields.company_address.update` | `DocumentTemplateUpdate.company_address` | Requiere granularización |
| Modificar company email | `document_templates.fields.company_email.update` | `DocumentTemplateUpdate.company_email` | Requiere granularización |
| Modificar company name | `document_templates.fields.company_name.update` | `DocumentTemplateUpdate.company_name` | Requiere granularización |
| Modificar company phone | `document_templates.fields.company_phone.update` | `DocumentTemplateUpdate.company_phone` | Requiere granularización |
| Modificar company tagline | `document_templates.fields.company_tagline.update` | `DocumentTemplateUpdate.company_tagline` | Requiere granularización |
| Modificar company website | `document_templates.fields.company_website.update` | `DocumentTemplateUpdate.company_website` | Requiere granularización |
| Modificar document code | `document_templates.fields.document_code.update` | `DocumentTemplateUpdate.document_code` | Requiere granularización |
| Modificar document issued on | `document_templates.fields.document_issued_on.update` | `DocumentTemplateUpdate.document_issued_on` | Requiere granularización |
| Modificar document revision | `document_templates.fields.document_revision.update` | `DocumentTemplateUpdate.document_revision` | Requiere granularización |
| Modificar document subtitle | `document_templates.fields.document_subtitle.update` | `DocumentTemplateUpdate.document_subtitle` | Requiere granularización |
| Modificar document title | `document_templates.fields.document_title.update` | `DocumentTemplateUpdate.document_title` | Requiere granularización |
| Modificar legal terms | `document_templates.fields.legal_terms.update` | `DocumentTemplateUpdate.legal_terms` | Requiere granularización |
| Modificar metrological terms | `document_templates.fields.metrological_terms.update` | `DocumentTemplateUpdate.metrological_terms` | Requiere granularización |
| Modificar name | `document_templates.fields.name.update` | `DocumentTemplateUpdate.name` | Requiere granularización |
| Modificar privacy notice | `document_templates.fields.privacy_notice.update` | `DocumentTemplateUpdate.privacy_notice` | Requiere granularización |
| Modificar show full terms | `document_templates.fields.show_full_terms.update` | `DocumentTemplateUpdate.show_full_terms` | Requiere granularización |
| Modificar show summary terms | `document_templates.fields.show_summary_terms.update` | `DocumentTemplateUpdate.show_summary_terms` | Requiere granularización |
| Modificar terms version | `document_templates.fields.terms_version.update` | `DocumentTemplateUpdate.terms_version` | Requiere granularización |

## 28.5. Gestionar firmas

| Microacción de campo | Permiso propuesto | Evidencia | Estado |
|---|---|---|---|
| Modificar show acceptance signature | `document_templates.fields.show_acceptance_signature.update` | `DocumentTemplateUpdate.show_acceptance_signature` | Requiere granularización |

## 28.6. Gestionar identidad fiscal y legal

| Microacción de campo | Permiso propuesto | Evidencia | Estado |
|---|---|---|---|
| Modificar company rfc | `document_templates.fields.company_rfc.update` | `DocumentTemplateUpdate.company_rfc` | Requiere granularización |

# 29. Portal cliente

## 29.1. Consultar

| Microacción | Método y ruta | Permiso propuesto | Estado |
|---|---|---|---|
| Client portal quotations | `GET /client-portal/quotations` | `portal.read` | Existe en backend |
| Client portal service orders | `GET /client-portal/service-orders` | `portal.read` | Existe en backend |

## 29.2. Gestionar certificados

| Microacción | Método y ruta | Permiso propuesto | Estado |
|---|---|---|---|
| Client portal certificates | `GET /client-portal/certificates` | `portal.read` | Existe en backend |
| Client portal certificate pdf | `GET /client-portal/certificates/{certificate_id}/pdf` | `portal.documents.download` | Existe en backend |

# 30. Procedimientos de calibración

## 30.1. Consultar

| Microacción | Método y ruta | Permiso propuesto | Estado |
|---|---|---|---|
| Calibration procedures | `GET /calibration-procedures` | `procedures.read` | Existe en backend |
| Calibration procedure | `GET /calibration-procedures/{procedure_id}` | `procedures.read` | Existe en backend |

## 30.2. Crear

| Microacción | Método y ruta | Permiso propuesto | Estado |
|---|---|---|---|
| Calibration procedure | `POST /calibration-procedures` | `procedures.create` | Existe en backend |

## 30.3. Eliminar

| Microacción | Método y ruta | Permiso propuesto | Estado |
|---|---|---|---|
| Calibration procedure | `DELETE /calibration-procedures/{procedure_id}` | `procedures.delete` | Existe en backend |

## 30.4. Modificar

| Microacción | Método y ruta | Permiso propuesto | Estado |
|---|---|---|---|
| Calibration procedure | `PATCH /calibration-procedures/{procedure_id}` | `procedures.update` | Existe en backend |

## 30.5. Editar campos y atributos

| Microacción de campo | Permiso propuesto | Evidencia | Estado |
|---|---|---|---|
| Modificar acceptance criteria | `procedures.fields.acceptance_criteria.update` | `CalibrationProcedureUpdate.acceptance_criteria` | Requiere granularización |
| Modificar certificate type | `procedures.fields.certificate_type.update` | `CalibrationProcedureUpdate.certificate_type` | Requiere granularización |
| Modificar code | `procedures.fields.code.update` | `CalibrationProcedureUpdate.code` | Requiere granularización |
| Modificar decision rule | `procedures.fields.decision_rule.update` | `CalibrationProcedureUpdate.decision_rule` | Requiere granularización |
| Modificar descripción | `procedures.fields.description.update` | `CalibrationProcedureUpdate.description` | Requiere granularización |
| Modificar issuer company | `procedures.fields.issuer_company.update` | `CalibrationProcedureUpdate.issuer_company` | Requiere granularización |
| Modificar magnitude | `procedures.fields.magnitude.update` | `CalibrationProcedureUpdate.magnitude` | Requiere granularización |
| Modificar name | `procedures.fields.name.update` | `CalibrationProcedureUpdate.name` | Requiere granularización |
| Modificar notas | `procedures.fields.notes.update` | `CalibrationProcedureUpdate.notes` | Requiere granularización |
| Modificar profile key | `procedures.fields.profile_key.update` | `CalibrationProcedureUpdate.profile_key` | Requiere granularización |
| Modificar required readings | `procedures.fields.required_readings.update` | `CalibrationProcedureUpdate.required_readings` | Requiere granularización |
| Modificar uncertainty model id | `procedures.fields.uncertainty_model_id.update` | `CalibrationProcedureUpdate.uncertainty_model_id` | Requiere granularización |
| Modificar uncertainty model version id | `procedures.fields.uncertainty_model_version_id.update` | `CalibrationProcedureUpdate.uncertainty_model_version_id` | Requiere granularización |
| Modificar version | `procedures.fields.version.update` | `CalibrationProcedureUpdate.version` | Requiere granularización |

## 30.6. Gestionar estado

| Microacción de campo | Permiso propuesto | Evidencia | Estado |
|---|---|---|---|
| Modificar estado | `procedures.fields.status.update` | `CalibrationProcedureUpdate.status` | Requiere granularización |

# 31. Selección de patrones

## 31.1. Gestionar patrones

| Microacción | Método y ruta | Permiso propuesto | Estado |
|---|---|---|---|
| Suggest field sheet patterns | `POST /field-sheets/{field_sheet_id}/suggest-patterns` | `pattern_selection.create` | Existe en backend |
| Validate field sheet patterns | `POST /field-sheets/{field_sheet_id}/validate-selected-patterns` | `pattern_selection.create` | Existe en backend |
| Pattern selection candidates | `POST /pattern-selection/candidates` | `pattern_selection.create` | Existe en backend |

# 32. Sistema y salud

## 32.1. Operar recurso

| Microacción | Método y ruta | Permiso propuesto | Estado |
|---|---|---|---|
| Health check | `GET /health` | `system.read` | Existe en backend |

# 33. Tickets · Centro de resoluciones

## 33.1. Analizar

| Microacción | Método y ruta | Permiso propuesto | Estado |
|---|---|---|---|
| Analyze | `POST /resolution-center/v1/resolutions/{public_id}/analyze` | `resolution_center.create` | Existe en backend |

## 33.2. Autorizar

| Microacción | Método y ruta | Permiso propuesto | Estado |
|---|---|---|---|
| Authorize | `POST /resolution-center/v1/resolutions/{public_id}/authorize` | `resolution_center.approve` | Existe en backend |

## 33.3. Construir

| Microacción | Método y ruta | Permiso propuesto | Estado |
|---|---|---|---|
| Build plan | `POST /resolution-center/v1/resolutions/{public_id}/build-plan` | `resolution_center.create` | Existe en backend |

## 33.4. Consultar

| Microacción | Método y ruta | Permiso propuesto | Estado |
|---|---|---|---|
| Resolution | `GET /resolution-center/v1/resolutions/{public_id}` | `resolution_center.read` | Existe en backend |
| Timeline | `GET /resolution-center/v1/resolutions/{public_id}/timeline` | `resolution_center.read` | Existe en backend |

## 33.5. Crear

| Microacción | Método y ruta | Permiso propuesto | Estado |
|---|---|---|---|
| Resolution | `POST /resolution-center/v1/resolutions` | `resolution_center.create` | Existe en backend |

## 33.6. Ejecutar

| Microacción | Método y ruta | Permiso propuesto | Estado |
|---|---|---|---|
| Execute | `POST /resolution-center/v1/resolutions/{public_id}/execute` | `resolution_center.create` | Existe en backend |

## 33.7. Listar

| Microacción | Método y ruta | Permiso propuesto | Estado |
|---|---|---|---|
| List resolutions | `GET /resolution-center/v1/resolutions` | `resolution_center.read` | Existe en backend |

## 33.8. Operar recurso

| Microacción | Método y ruta | Permiso propuesto | Estado |
|---|---|---|---|
| Capabilities | `GET /resolution-center/v1/capabilities` | `resolution_center.read` | Existe en backend |
| Definitions | `GET /resolution-center/v1/definitions` | `resolution_center.read` | Existe en backend |
| Indicators | `GET /resolution-center/v1/indicators` | `resolution_center.read` | Existe en backend |

## 33.9. Preparar

| Microacción | Método y ruta | Permiso propuesto | Estado |
|---|---|---|---|
| Prepare context | `POST /resolution-center/v1/resolutions/{public_id}/prepare-context` | `resolution_center.create` | Existe en backend |

## 33.10. Simular

| Microacción | Método y ruta | Permiso propuesto | Estado |
|---|---|---|---|
| Simulate | `POST /resolution-center/v1/resolutions/{public_id}/simulate` | `resolution_center.create` | Existe en backend |

# 34. Tickets · Excepciones de cotización

## 34.1. Gestionar excepciones

| Microacción | Método y ruta | Permiso propuesto | Estado |
|---|---|---|---|
| Requests | `GET /quotation-service-exceptions` | `quotations.exceptions.read` | Existe en backend |
| Request | `POST /quotation-service-exceptions/quotations/{quotation_folio}` | `quotations.exceptions.create` | Existe en backend |
| Quotation context | `GET /quotation-service-exceptions/quotations/{quotation_folio}/context` | `quotations.exceptions.read` | Existe en backend |
| Apply | `POST /quotation-service-exceptions/{exception_folio}/apply` | `quotations.exceptions.create` | Existe en backend |
| Preview | `POST /quotation-service-exceptions/{exception_folio}/preview` | `quotations.exceptions.review` | Existe en backend |
| Review | `POST /quotation-service-exceptions/{exception_folio}/review` | `quotations.exceptions.review` | Existe en backend |

## 34.2. Editar campos y atributos

| Microacción de campo | Permiso propuesto | Evidencia | Estado |
|---|---|---|---|
| Modificar cantidad | `quotations.exceptions.fields.quantity.update` | `QuotationUnlockItem.quantity` | Requiere granularización |
| Modificar comment | `quotations.exceptions.fields.comment.update` | `QuotationServiceChangeReview.comment` | Requiere granularización |
| Modificar decision | `quotations.exceptions.fields.decision.update` | `QuotationServiceChangeReview.decision` | Requiere granularización |
| Modificar descripción | `quotations.exceptions.fields.description.update` | `QuotationUnlockItem.description` | Requiere granularización |
| Modificar items | `quotations.exceptions.fields.items.update` | `QuotationUnlockPreview.items` | Requiere granularización |
| Modificar observation | `quotations.exceptions.fields.observation.update` | `QuotationServiceChangeCreate.observation` | Requiere granularización |
| Modificar service key | `quotations.exceptions.fields.service_key.update` | `QuotationUnlockItem.service_key` | Requiere granularización |
| Modificar validity hours | `quotations.exceptions.fields.validity_hours.update` | `QuotationServiceChangeReview.validity_hours` | Requiere granularización |
| Registrar motivo | `quotations.exceptions.fields.reason.update` | `QuotationServiceChangeCreate.reason` | Requiere granularización |

## 34.3. Redefinir condiciones económicas

| Microacción de campo | Permiso propuesto | Evidencia | Estado |
|---|---|---|---|
| Aplicar o modificar descuento | `quotations.exceptions.fields.discount_percent.update` | `QuotationUnlockItem.discount_percent` | Requiere granularización |
| Modificar precio unitario | `quotations.exceptions.fields.unit_price.update` | `QuotationUnlockItem.unit_price` | Requiere granularización |

# 35. Usuarios y accesos

## 35.1. Consultar

| Microacción | Método y ruta | Permiso propuesto | Estado |
|---|---|---|---|
| Users | `GET /users` | `users.read` | Existe en backend |

## 35.2. Crear

| Microacción | Método y ruta | Permiso propuesto | Estado |
|---|---|---|---|
| User admin | `POST /users` | `users.create` | Existe en backend |

## 35.3. Gestionar estado

| Microacción | Método y ruta | Permiso propuesto | Estado |
|---|---|---|---|
| User status | `PATCH /users/{user_id}/status` | `users.status.manage` | Existe en backend |

## 35.4. Gestionar roles

| Microacción | Método y ruta | Permiso propuesto | Estado |
|---|---|---|---|
| Roles | `GET /users/roles` | `users.read` | Existe en backend |
| User roles | `PATCH /users/{user_id}/roles` | `users.roles.assign` | Existe en backend |

## 35.5. Modificar

| Microacción | Método y ruta | Permiso propuesto | Estado |
|---|---|---|---|
| User admin | `PATCH /users/{user_id}` | `users.update` | Existe en backend |

## 35.6. Editar campos y atributos

| Microacción de campo | Permiso propuesto | Evidencia | Estado |
|---|---|---|---|
| Modificar correo | `users.fields.email.update` | `UserAdminCreate.email` | Requiere granularización |
| Modificar nombre del usuario | `users.fields.full_name.update` | `UserAdminCreate.full_name` | Requiere granularización |

## 35.7. Gestionar acceso y seguridad

| Microacción de campo | Permiso propuesto | Evidencia | Estado |
|---|---|---|---|
| Activar o desactivar | `users.fields.is_active.update` | `UserStatusUpdate.is_active` | Requiere granularización |
| Asignar roles | `users.fields.role_names.update` | `UserRolesUpdate.role_names` | Requiere granularización |
| Definir contraseña | `users.fields.password.update` | `UserAdminCreate.password` | Requiere granularización |

# 36. Verificación pública de certificados

## 36.1. Gestionar certificados

| Microacción | Método y ruta | Permiso propuesto | Estado |
|---|---|---|---|
| Verify certificate | `GET /verify/{authentication_code}` | `verification.read` | Existe en backend |

# Anexo A. Arquitectura mínima para administrar el catálogo

```text
Permission
Role
RolePermission
UserRole
UserPermissionOverride (allow | deny)
RecordScopePolicy
PortalMembership
TemporaryCapabilityGrant / Ticket authorization
```

Resolución efectiva recomendada:

```text
prohibición institucional
→ deny individual
→ allow individual
→ permisos heredados por roles/grupos
→ deny-by-default
```

# Anexo B. Alcances por registro

| Alcance | Significado |
|---|---|
| `all` | Todos los registros permitidos por la organización. |
| `department` | Registros del área del usuario. |
| `assigned_only` | Registros asignados al usuario. |
| `own_created` | Registros creados por el usuario. |
| `linked_client_only` | Registros del cliente vinculado al usuario de portal. |
| `explicit_set` | Registros concedidos expresamente o por Ticket. |

# Anexo C. Decisiones pendientes para revisión funcional

- Qué microacciones son no delegables incluso para overrides individuales.
- Qué permisos admiten límite cuantitativo, por ejemplo descuento máximo o variación de precio.
- Qué acciones requieren motivo obligatorio, doble autorización o segregación de funciones.
- Qué acciones deben publicar evento de Actividad además de auditoría técnica.
- Qué permisos deben ser permanentes y cuáles sólo deben concederse mediante Ticket contextual.
- Qué roles del sistema serán protegidos y cuáles podrán editarse libremente desde Ajustes.

## Documentación actualizada

Este archivo es un nuevo catálogo consolidado y fue adoptado el 2026-08-04 como
insumo funcional obligatorio de diseño. No sustituye
`backend/app/core/permissions.py`, no cambia contratos vigentes y no aplica sus
permisos propuestos sin revisión funcional y arquitectónica.
