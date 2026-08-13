> Estado: VIGENTE
>
> Corte verificado: 2026-08-04
>
> Alcance: brecha del snapshot técnico de ETAPA 2B; no implementa RBAC ni cambia permisos

# Brechas entre el bootstrap actual y el snapshot técnico de capacidades

## Dictamen

El snapshot técnico contiene 36 módulos, 213 acciones, 798 filas y
658 claves propuestas únicas. `permissions.py` resuelve actualmente 140
permisos únicos entre constantes y roles; 61 coinciden literalmente con una
propuesta y 79 requieren reconciliación funcional. El inventario HTTP utiliza
73 permisos mínimos únicos: 20 todavía usan una clave bootstrap distinta de la
propuesta institucional y una clave catalogada
(`reference_standard_certificates.delete`) no está declarada explícitamente en
el bootstrap, por lo que hoy sólo Administrador la satisface mediante `*`.

Estas diferencias no autorizan renombrar claves. La validación funcional
posterior decide qué propuestas sobreviven; después de aprobación, una matriz
de compatibilidad definirá el backlog de implementación administrativa.

## Permisos bootstrap pendientes de reconciliación

| Familia | Cantidad | Claves actuales |
| --- | ---: | --- |
| Activity | 10 | `activity.attach_files`, `activity.audit`, `activity.delete_own`, `activity.edit_own`, `activity.mention`, `activity.moderate`, `activity.request_attention`, `activity.resolve_attention`, `activity.view_audit`, `activity.write` |
| Certificados | 6 | `certificates.capture`, `certificates.generate`, `certificates.match_override`, `certificates.quality`, `certificates.read_own`, `certificates.upload_pdf` |
| Documentos | 2 | `documents.approve`, `documents.archive` |
| Plantillas de Hojas | 4 | `field_sheet_templates.approve`, `field_sheet_templates.archive`, `field_sheet_templates.export`, `field_sheet_templates.import` |
| Folios | 1 | `folios.manage_sequences` |
| Integraciones | 1 | `integrations.facturama.status` |
| Facturación | 1 | `invoices.manage` |
| Metrología | 1 | `metrology.execute` |
| Motores operativos | 1 | `operational_engines.execute` |
| Selección de patrones | 1 | `pattern_selection.execute` |
| Pagos | 2 | `payments.manage`, `payments.read` |
| Cotizaciones | 11 | `quotations.act_as_advisor`, `quotations.exceptions.apply_change_service`, `quotations.exceptions.apply_unlock`, `quotations.exceptions.authorize_change_service`, `quotations.exceptions.authorize_unlock`, `quotations.exceptions.inspect`, `quotations.exceptions.inspect_change_service`, `quotations.exceptions.rebuild_empty_service_order`, `quotations.exceptions.request_change_service`, `quotations.exceptions.request_unlock`, `quotations.read_own` |
| Certificados de patrón | 1 | `reference_standard_certificates.approve` |
| Liberación | 1 | `release.manage` |
| Centro de Resoluciones | 10 | `resolution_center.*`, `resolution_center.analyze`, `resolution_center.audit`, `resolution_center.authorize`, `resolution_center.execute`, `resolution_center.infrastructure`, `resolution_center.plan`, `resolution_center.prepare`, `resolution_center.read_all`, `resolution_center.simulate` |
| SAT | 3 | `sat_catalogs.manage`, `sat_catalogs.manage_aliases`, `sat_catalogs.manage_favorites` |
| ETS | 9 | `service_orders.additional_equipment.audit`, `service_orders.additional_equipment.authorize`, `service_orders.additional_equipment.commercial_review`, `service_orders.additional_equipment.execute`, `service_orders.additional_equipment.propose`, `service_orders.read_assigned`, `service_orders.read_own`, `service_orders.sign`, `service_orders.signatures.reopen` |
| Servicios | 3 | `services.manage_certificate_prefix`, `services.manage_linked_company`, `services.manage_service_type` |
| Ajustes | 5 | `settings.manage`, `settings.master_catalogs.manage`, `settings.read`, `settings.system_parameters.read`, `settings.system_parameters.update` |
| Incertidumbre | 6 | `uncertainty.execute`, `uncertainty_models.approve`, `uncertainty_models.create`, `uncertainty_models.exception`, `uncertainty_models.read`, `uncertainty_models.update` |
| Usuarios | 1 | `users.manage` |

Total: **79** claves actuales. Permanecen válidas mientras sean necesarias para
compatibilidad; sólo una decisión funcional podrá mapearlas, dividirlas o
retirarlas.

## Redundancias y amplitudes candidatas

| Situación | Evidencia | Tratamiento posterior |
| --- | --- | --- |
| Alias de compatibilidad | `activity.write` coexiste con `activity.create`; `activity.audit` con `activity.view_audit`. | Definir alias oficial y ventana de retiro antes de migrar asignaciones. |
| Liberación duplicada | Roles contienen `certificates.release` y el guard exige `release.manage`. | Elegir capacidad institucional sin cambiar aún el flujo. |
| Administración amplia | `users.manage`, `settings.manage`, `invoices.manage`, `payments.manage` agrupan mutaciones distintas. | Dividir sólo después de aprobar microacciones y protección crítica. |
| Portal legacy | `*_read_own` convive con el guard `portal.read` más ownership backend. | Integrar scopes `linked_client_only` con PortalMembership persistente. |
| Comodines | Administrador usa `*` y Desarrollador `resolution_center.*`. | Declarar roles protegidos y límites no delegables antes del RBAC dinámico. |
| Duplicación textual | `service_orders.read` aparece dos veces en el set fuente de Técnico. | Limpieza posterior sin efecto funcional, acompañada de prueba de matriz. |

El guard transversal concentra además varias microacciones bajo permisos
amplios: `uncertainty_models.update` protege 16 operaciones,
`activity.read` 15, `resolution_center.read` 13, `certificates.read` 11,
`clients.update` 11, `invoices.manage` 11 y `service_orders.update` 11. Esto no
es un bypass —los servicios pueden reforzar reglas—, pero sí demuestra dónde
la futura granularización debe comenzar.

## Faltantes estructurales del modelo definitivo

El bootstrap no puede representar todavía:

- múltiples roles y grupos por usuario con precedencia explícita;
- overrides individuales `allow`/`deny`;
- scopes por registro (`all`, área, asignado, propio, cliente vinculado o set
  explícito);
- permisos temporales con vigencia, motivo, emisor y revocación;
- capacidades críticas y roles institucionales protegidos;
- evidencia de resolución efectiva y explicación de por qué se permitió o
  denegó;
- `PortalMembership` persistente y auditable.

## Regla de transición

Durante la preparación arquitectónica no se renombra ni elimina una clave
vigente. La futura etapa de implementación deberá publicar una matriz de
compatibilidad por clave, migrar asignaciones de manera reversible y conservar
deny-by-default, ownership y auditoría. El catálogo es autoridad funcional; el
backend seguirá siendo autoridad de ejecución.

## Validación reproducible

Ejecutar:

```bash
venv/bin/python scripts/validate_capability_catalog.py --check
```

El gate analiza todas las tablas del catálogo y falla si cambian sus conteos,
si aparece una clave inválida o si `permissions.py`/inventario cambian sin
actualizar el snapshot institucional.

## Conciliación posterior — 2026-08-11

El cierre `TD_027_CAPABILITY_GATE_RECONCILIATION_2026-08-11.md` preserva esta
fotografía de Etapa 2B y concilia el drift posterior. `portal.view` se reemplazó
por la capacidad funcional existente `portal.read`; la clave catalogada
`reference_standard_certificates.delete` se declaró y asignó con menor
privilegio. El gate queda verde con 142 permisos actuales, 62 coincidencias,
80 gaps actuales, 73 permisos HTTP, 20 diferencias literales catálogo, 0 gaps
de bootstrap y 596 permisos propuestos aún no implementados. Las diferencias de
compatibilidad no se migran sin decisión institucional.

## Ampliación temporal — 2026-08-13

El vertical removible OT LAB agrega `lab_work_orders.use` y
`lab_work_orders.export`. El baseline reproducible pasa a 144 permisos actuales,
82 diferencias frente al catálogo objetivo, 75 permisos HTTP, 22 diferencias
literales y 0 gaps de bootstrap. Estas dos claves no se promueven al Catálogo
Institucional permanente: deben desaparecer con el retiro controlado del LAB
después de su exportación íntegra.
