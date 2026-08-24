> Estado: VIGENTE, implementación **EN REVISIÓN**
>
> Corte: 2026-08-18
>
> Alcance: identidad y snapshot; no define workflows técnicos por categoría.

# Identidad operativa y snapshots de servicios

## Identidad canónica

`operational_category` es la identidad operativa explícita. Los valores vigentes son `calibration`, `maintenance`, `repair`, `verification`, `qualification`, `validation`, `training`, `consulting`, `general_service`, `sale` y `other`.

`item_type` (`product`/`service`) conserva exclusivamente la clasificación comercial/fiscal. No crea, restringe ni reinterpreta identidad ETS: Producto no implica `sale` y Servicio admite `sale`. `category` conserva la etiqueta estructurada del catálogo, `commodity` conserva la clasificación comercial/API y `calibration_scope` conserva la modalidad o configuración aplicable; ninguno debe reconstruirse desde nombres o descripciones durante la ejecución. La categoría se persiste en `CatalogItem`, `QuotationItem` y `ServiceOrderItem`; `ServiceUnit.initial_category` congela el origen de la unidad y `ServiceStage.category` conserva cada etapa append-only.

En el pipeline metrológico, `Equipment.service_order_item_id` es la asociación
autoritaria entre el equipo y su proceso. Calibración conserva uno de los tres
alcances de acreditación; Verificación conserva alcance nulo y tipo documental
`verification`. Un ETS mixto debe desambiguar la partida al registrar cada
equipo y nunca clasificar la orden completa como una sola modalidad.

Todo concepto nuevo debe enviar `operational_category` explícita. El formulario presenta una sola lista operacional, independiente de Tipo; esa selección gobierna también la aparición de la configuración Venta ya existente. El backend valida correspondencia exacta entre la etiqueta estructurada y la clave canónica, pero nunca sustituye la clave a partir de `item_type`, nombre o descripción.

`general_service` es especial: sólo ese origen habilita `ServiceUnit.evolution_enabled` e inicia en diagnóstico. Una categoría conocida nunca se degrada a Servicio General por falta de coincidencia textual.

## Autoridad histórica

Al seleccionar o sustituir explícitamente un concepto del catálogo, la cotización crea `operational_snapshot` esquema 2. Éste congela por servicio comercial y por hoja operativa: identidad y clave; nombre y descripción; `operational_category`; alcance y tipo; empresa/prefijo vinculados; precio e impuestos; y Master esperado en `template_snapshot`.

Editar otros campos o reenviar el mismo `catalog_item_id` no reconstruye el snapshot. Cambiar explícitamente a otro concepto sí crea configuración desde ese nuevo catálogo. Al crear el ETS, `ServiceOrderItem` consume primero el snapshot; sólo registros legacy sin dato congelado usan el adaptador estructurado de compatibilidad.

Servicios Compuestos congelan la identidad de cada hoja dentro de `operational_items`. La expansión continúa ocurriendo una sola vez al crear el ETS y Facturación conserva el padre comercial.

## Compatibilidad

La migración `a8c0e2f4b6d8` agrega y rellena las tres columnas desde categoría/commodity estructurados y vínculos existentes, sin una rama por `item_type`. La corrección `e2a4c6d8f0b1` realinea únicamente el catálogo vivo cuya categoría histórica exacta demuestra la identidad; no modifica `QuotationItem`, `ServiceOrderItem` ni snapshots. Las columnas permanecen nullable para expedientes legacy ambiguos; el adaptador acepta coincidencias exactas de categoría/commodity históricos y nunca usa `item_type`, nombre o descripción. `ServiceUnit`, `ServiceStage`, calibración y Servicio General no se reescriben.

## Frontera de Hojas de Campo

La propuesta de plantilla permanece en `frontend/src/utils/fieldSheetTemplateResolver.js`, consumida por `ServiceOrdersPage.jsx`. Este contrato no mueve ni replica esa selección dentro de `service_execution.py`; dicho servicio se limita a identidad, origen, etapas y trazabilidad ETS.

## Pendientes

- Revisión funcional/arquitectónica y E2E autenticado antes de aprobar.
- Revisar manualmente conceptos legacy de categoría no reconocida cuya intención no pueda demostrarse; no se reclasifican por haber sido Producto.
- Los workflows particulares de mantenimiento, reparación, validación, calificación, capacitación, consultoría y demás categorías quedan fuera de esta entrega.
- La restauración general de partidas desde `QuotationSnapshot` continúa en OBS-008; esta entrega garantiza que reabrir/editar no refresque el snapshot operativo silenciosamente.
