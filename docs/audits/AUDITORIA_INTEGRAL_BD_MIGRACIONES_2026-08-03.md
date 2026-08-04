# Auditoría integral de base de datos y migraciones

## Dictamen

| Verificación | Resultado |
| --- | --- |
| Motor | PostgreSQL + SQLAlchemy 2 + Alembic |
| Metadata | 101 tablas; 1,670 columnas; 294 FKs; 458 índices; 76 unique constraints ORM |
| Migraciones visibles | 82 archivos, de los cuales 3 estaban no rastreados al inicio |
| Heads | Único: `e16e7f8091a2` |
| Branch/merge | branch `a0d2f4b6c8e1`; merge `4c7ef14e1391` |
| Upgrade vacío | Correcto en `erp_myc_audit_20260803` |
| Downgrade a base | Falla en `c3fb78821edc` por índice inexistente |
| Re-upgrade | La transacción fallida conservó head; `upgrade head` no requirió cambios |
| `alembic check` | Falla con drift amplio |
| Upgrade histórico | NO VERIFICADO: falta dump sanitizado/autorización para restaurar datos reales |
| Backup oficial | Declara `b03b4c5d6e7f`, no coincide con head visible |

## TimestampMixin: revisión sistemática

La metadata ORM declara `server_default=now()` en las columnas del mixin. La base creada desde cero conserva **16 columnas NOT NULL sin DEFAULT**:

| Tabla | Columnas | Creadora | Migración posterior correctiva | Severidad | Corrección futura |
| --- | --- | --- | --- | --- | --- |
| `activity_attention_requests` | created_at, updated_at | `8c9d0e1f2a3b` | Ninguna | ALTO | ALTER con DEFAULT now(); validar históricos |
| `activity_thread_reads` | created_at, updated_at | `8c9d0e1f2a3b` | Ninguna | ALTO | Igual; agregar prueba insert ORM/raw |
| `linked_companies` | created_at, updated_at | `ae1f2a3b4c5d` | Ninguna | ALTO | Igual; hoy seed funciona porque entrega fechas |
| `uncertainty_calculations` | created_at, updated_at | `b3c4d5e6f7a8` | Ninguna | ALTO | Migración única sistemática |
| `uncertainty_components` | created_at, updated_at | `b3c4d5e6f7a8` | Ninguna | ALTO | Igual |
| `uncertainty_formulas` | created_at, updated_at | `b3c4d5e6f7a8` | Ninguna | ALTO | Igual; además drift soft-delete |
| `uncertainty_model_exceptions` | created_at, updated_at | `b3c4d5e6f7a8` | Ninguna | ALTO | Igual |
| `uncertainty_models` | created_at, updated_at | `b3c4d5e6f7a8` | Ninguna | ALTO | Igual |

Las tres migraciones no rastreadas sí reparan `quotation_service_change_requests`, `notifications` e `institutional_folio_sequences`. No agotan el patrón.

## Drift confirmado

`alembic check` propone, entre otras operaciones:

- agregar `is_active`, `deleted_at`, `deleted_by` a `uncertainty_formulas`;
- agregar índices ORM faltantes en invoices, payments, credit notes, capture files, PDF versions, snapshots y uncertainty;
- remover índices parciales/especializados existentes en Catálogo, Certificados, Hojas, Control Documental, SAT y Patrones porque no están declarados en metadata;
- cambiar unicidad/índice de `service_work_orders.work_order_number`;
- agregar `uq_communication_participant` y remover constraint/índice equivalente existente;
- remover uniques de códigos/template/configuración declarados de forma distinta.

No debe aplicarse automáticamente ese diff: varios “remove index” destruirían índices PostgreSQL especializados que sí son intencionales. La corrección futura requiere clasificar cada diferencia como metadata faltante, migración faltante o exclusión deliberada de autogenerate.

## Downgrade roto

Reproducción: `alembic downgrade base` en una base creada por la misma cadena. Al ejecutar `c3fb78821edc_add_service_order_signatures.py::downgrade`, intenta `DROP INDEX ix_service_order_signatures_service_order_id`; ese índice no existe después de las migraciones posteriores. PostgreSQL aborta con `UndefinedObject`. Esto invalida la afirmación de reversibilidad completa aunque downgrades recientes aislados hayan pasado.

## Matriz modelo/tabla/migración

“Posteriores” es el número de migraciones que mencionan la tabla después de la creadora; no equivale automáticamente a cambio material. Divergencia `DRIFT` se marca cuando `alembic check` reportó operación sobre la tabla; `TS` cuando falta default real.

| Modelos/tablas | Migración creadora | Posteriores | Divergencia | Severidad | Corrección futura |
| --- | --- | ---: | --- | --- | --- |
| User, Role, Client, ClientContact, Quotation, QuotationItem, ServiceOrder, ServiceOrderItem, Equipment, AuditLog | `c0fa71033b73` | 0–9 | DRIFT en varios índices; legacy conceptual | ALTO | reconciliar metadata e historial |
| FieldSheet | `7a8b9c0d1e12` | 9 | DRIFT índice parcial | MEDIO | declarar índice o excluirlo |
| Certificate | `8b9c0d1e2f13` | 3 | DRIFT índice activo | MEDIO | igual |
| user_roles | `9c0d1e2f3a14` | 0 | Sin drift detectado | BAJO | mantener |
| CatalogItem | `a1b2c3d4e5f6` | 6 | DRIFT índices parciales/origen | MEDIO | alinear metadata |
| DocumentTemplate | `c3d4e5f6a7b8` | 0 | DRIFT unique | MEDIO | normalizar naming |
| ServiceWorkOrder | `9c1d2e3f4a5b` | 1 | DRIFT unicidad + downgrade relacionado | ALTO | reparar contrato y downgrade |
| Firmas directas/ciclos/relación OT | `27dad4c7a6c8`, `c3fb...`, `e9e...` | varias | downgrade roto/duplicación | ALTO | migración correctiva no destructiva |
| Metrología, Patrones, Procedimientos | `e5f6a7b8c9d0` | 0–2 | DRIFT índices parciales | MEDIO | declarar intencionalidad |
| Control Documental/Perfiles/Interpretaciones | `f1a2b3c4d5e6` | 0–2 | DRIFT unique/índice activo | MEDIO | alinear metadata |
| Incertidumbre (6 tablas) | `b3c4d5e6f7a8`, `c4d5...` | 0–1 | TS + soft-delete + índices | ALTO | migración sistemática y tests |
| Identidad/field templates/signatures | `f0a1b2c3d4e5` | 0–1 | DRIFT unique configuración | MEDIO | alinear metadata |
| Invoicing (Invoice, Item, Payment, CreditNote, Settings) | `0f1e2d3c4b5a` | 0–3 | DRIFT varios índices ORM | MEDIO | migración/index review |
| SAT (5 tablas) | `f6a7b8c9d0e1` + `f8a9...` | 0–3 | DRIFT intenta quitar FTS/pattern indexes | ALTO | declarar índices en metadata/exclusión |
| CaptureFile/PdfVersion | `fc4d...`, `f3b4...` | 0–1 | DRIFT índices ORM | MEDIO | revisar necesidad real |
| Servicios compuestos | `ff7a8b9c0d1e` | 0 | Sin drift detectado | BAJO | mantener |
| Activity base (threads/messages/revisions/mentions/attachments) | `fabc2cd495ef` | 0–1 | Sin TS salvo nuevas tablas | BAJO | mantener |
| Activity institucional (reads/attention) | `8c9d0e1f2a3b` | 0 | TS | ALTO | defaults + regresión |
| Notifications | `b18ac098c1db` + `d15d...` | 1 | Corregida en árbol, no rastreada | ALTO | versionar/revisar |
| Communications | `6ae1d4877cdb` | 0 | DRIFT constraint/índice participante | MEDIO | alinear definición |
| LinkedCompany/FolioSequence/QuotationException | `ae1...`, `9d0...` | 0–2 | TS linked; fixes c14/e16 no rastreados | ALTO | completar serie y versionar |
| Motor raíz: resolutions y 20 tablas | `9d3e5f7a1b2c` | 0–3 | Sin drift relevante reportado | BAJO | conservar; validar triggers en restore |
| Motor seguridad/compensación | `b4c...`, `d6e...`, `e7f...`, `f8a...` | 0–2 | Sin drift relevante reportado | BAJO | conservar |
| API consumer | `a0d2f4b6c8e1` | 0 | Sin drift | BAJO | rotación operacional |
| Runtime distribuido (3 tablas) | `c1e3f5a7b9d2` | 0 | Sin drift | BAJO | prueba multinodo real |
| CertificateResolutionOperation | `f9c1d3e5a7b9` | 0 | Sin drift | BAJO | conservar append-only |
| Additional equipment FK/reconciliation | `7b8c9d0e1f2a` | sobre equipment | Árbol funcional | MEDIO | aprobar fase y conectar productor |

### Inventario completo por creadora

- `c0fa71033b73`: `audit_logs`, `client_contacts`, `clients`, `equipment`, `quotation_items`, `quotations`, `roles`, `service_order_items`, `service_orders`, `users`.
- `7a8b9c0d1e12`: `field_sheets`; `8b9c0d1e2f13`: `certificates`; `9c0d1e2f3a14`: `user_roles`.
- `a1b2c3d4e5f6`: `catalog_items`; `c3d4e5f6a7b8`: `document_templates`; `d4e5f6a7b8c9`: `field_sheet_results`.
- `e5f6a7b8c9d0`: `calibration_procedures`, `field_sheet_reference_standards`, `reference_standard_uncertainties`, `reference_standards`.
- `f1a2b3c4d5e6`: `controlled_documents`, `controlled_document_versions`, `document_interpretations`, `technical_profiles`, `technical_profile_allowed_patterns`.
- `a2b3c4d5e6f7`: `reference_standard_certificates`, `reference_standard_certificate_uncertainties`.
- `b3c4d5e6f7a8`: `uncertainty_models`, `uncertainty_components`, `uncertainty_formulas`, `uncertainty_model_exceptions`, `uncertainty_calculations`; `c4d5...`: `uncertainty_model_versions`.
- `f0a1b2c3d4e5`: `field_sheet_signatures`, `institutional_configurations`; `f0c1...`: `client_certificate_profiles`; `9a8...`: `field_sheet_template_definitions`.
- `0f1e2d3c4b5a`: `invoices`, `invoice_items`, `invoice_payments`, `credit_notes`, `invoice_settings`; `670...`: `facturama_invoice_attempts`.
- `9c1d2e3f4a5b`: `service_work_orders`; `e9e489637dc8`: `service_order_signature_cycles`, `service_order_signature_cycle_work_orders`.
- `f3b4c5d6e7f8`: `certificate_pdf_versions`; `fc4d5e6f7a8b`: `certificate_capture_files`; `ff7...`: `catalog_item_components`.
- `f6a7b8c9d0e1`: `sat_catalogs`, `sat_catalog_versions`, `sat_catalog_records`; `f8a9...`: `sat_catalog_aliases`, `sat_catalog_favorites`.
- `9d3e5f7a1b2c`: `resolutions`, `resolution_problems`, `resolution_context_snapshots`, `resolution_analyses`, `resolution_strategy_selections`, `resolution_plans`, `resolution_plan_steps`, `resolution_plan_step_dependencies`, `resolution_simulations`, `resolution_authorization_requests`, `resolution_authorization_decisions`, `resolution_revalidations`, `resolution_executions`, `resolution_step_executions`, `resolution_results`, `resolution_audit_events`, `resolution_entity_references`, `resolution_evidence_references`, `resolution_idempotency_records`, `resolution_locks`, `resolution_outbox_events`.
- `d6e8f0a2b4c5`: cuatro tablas `resolution_compensation_*`; `b4c6...`: `resolution_security_decisions`; `f8a0...`: `resolution_security_decision_uses`.
- `f9c1d3e5a7b9`: `certificate_resolution_operations`; `a0d2...`: `resolution_api_consumers`; `c1e3...`: `resolution_worker_nodes`, `resolution_work_items`, `resolution_work_events`.
- `fabc2cd495ef`: `activity_threads`, `activity_messages`, `activity_message_revisions`, `activity_mentions`, `activity_attachments`.
- `b18ac098c1db`: `notifications`; `6ae1d4877cdb`: `communication_conversations`, `communication_messages`, `communication_participants`.
- `8c9d0e1f2a3b`: `activity_thread_reads`, `activity_attention_requests`; `9d0e...`: `quotation_service_change_requests`; `ae1...`: `linked_companies`, `institutional_folio_sequences`.

## Tablas/columnas legacy y obsolescencia

Confirmado por coexistencia, no por suposición:

- `service_orders.work_order_number` y `service_work_orders` representan OT legacy/normalizada.
- firmas directas históricas y ciclos normalizados coexisten.
- JSON fiscales en Invoice/Settings y Catálogos SAT normalizados cubren responsabilidades solapadas.
- `match_status` permanece en Certificados como dato legacy, ya no compuerta.
- `role_id` primario y relación M:N `user_roles` coexisten.

No se clasifica ninguna tabla como eliminable sin telemetría de producción y consulta de datos. Las 101 tablas tienen modelo/metadata o tabla asociativa; no se confirmó una tabla completamente huérfana.

## Riesgos de integridad/concurrencia

- Positivo: Motor y Facturama usan locks, idempotencia y estados de incertidumbre; folios nuevos usan fila/lock y restricciones.
- Negativo: endpoints públicos permiten carreras maliciosas; varias listas/cálculos de máximos legacy no son la fuente única; archivos se escriben antes o alrededor de commits sin compensación uniforme; generation/LibreOffice es síncrona.
- SQLite: tests unitarios usan dobles/SQLite en varias áreas, pero migraciones, triggers, `SKIP LOCKED`, JSONB, índices parciales y FTS requieren PostgreSQL; no hay equivalencia completa. El upgrade vacío PostgreSQL sí fue probado.
