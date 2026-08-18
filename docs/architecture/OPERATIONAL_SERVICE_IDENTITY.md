> Estado: VIGENTE, implementación **EN REVISIÓN**
>
> Corte: 2026-08-18
>
> Alcance: identidad y snapshot; no define workflows técnicos por categoría.

# Identidad operativa y snapshots de servicios

## Identidad canónica

`operational_category` es la identidad operativa explícita. Los valores vigentes son `calibration`, `maintenance`, `repair`, `verification`, `qualification`, `validation`, `training`, `consulting`, `general_service`, `sale` y `other`.

`category` conserva la etiqueta estructurada del catálogo, `commodity` conserva la clasificación comercial/API y `calibration_scope` conserva la modalidad o configuración aplicable; ninguno debe reconstruirse desde nombres o descripciones durante la ejecución. La categoría se persiste en `CatalogItem`, `QuotationItem` y `ServiceOrderItem`; `ServiceUnit.initial_category` congela el origen de la unidad y `ServiceStage.category` conserva cada etapa append-only.

`general_service` es especial: sólo ese origen habilita `ServiceUnit.evolution_enabled` e inicia en diagnóstico. Una categoría conocida nunca se degrada a Servicio General por falta de coincidencia textual.

## Autoridad histórica

Al seleccionar o sustituir explícitamente un concepto del catálogo, la cotización crea `operational_snapshot` esquema 2. Éste congela por servicio comercial y por hoja operativa: identidad y clave; nombre y descripción; `operational_category`; alcance y tipo; empresa/prefijo vinculados; precio e impuestos; y Master esperado en `template_snapshot`.

Editar otros campos o reenviar el mismo `catalog_item_id` no reconstruye el snapshot. Cambiar explícitamente a otro concepto sí crea configuración desde ese nuevo catálogo. Al crear el ETS, `ServiceOrderItem` consume primero el snapshot; sólo registros legacy sin dato congelado usan el adaptador estructurado de compatibilidad.

Servicios Compuestos congelan la identidad de cada hoja dentro de `operational_items`. La expansión continúa ocurriendo una sola vez al crear el ETS y Facturación conserva el padre comercial.

## Compatibilidad

La migración `a8c0e2f4b6d8` agrega y rellena las tres columnas desde categoría/commodity estructurados y vínculos existentes. Las columnas permanecen nullable para expedientes legacy ambiguos; el adaptador acepta coincidencias exactas de campos históricos y nunca hace búsqueda por fragmentos en nombre/descripción. `ServiceUnit`, `ServiceStage`, calibración y Servicio General no se reescriben.

## Frontera de Hojas de Campo

La propuesta de plantilla permanece en `frontend/src/utils/fieldSheetTemplateResolver.js`, consumida por `ServiceOrdersPage.jsx`. Este contrato no mueve ni replica esa selección dentro de `service_execution.py`; dicho servicio se limita a identidad, origen, etapas y trazabilidad ETS.

## Pendientes

- Revisión funcional/arquitectónica y E2E autenticado antes de aprobar.
- Los workflows particulares de mantenimiento, reparación, validación, calificación, capacitación, consultoría y demás categorías quedan fuera de esta entrega.
- La restauración general de partidas desde `QuotationSnapshot` continúa en OBS-008; esta entrega garantiza que reabrir/editar no refresque el snapshot operativo silenciosamente.
