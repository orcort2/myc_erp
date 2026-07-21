> Estado: VIGENTE
>
> Tipo: Vigente (canónico)
>
> Autoridad: Alta para deuda técnica actual
>
> Prevalece sobre: propuestas de refactorización o riesgos contenidos en auditorías y documentos históricos
>
> Corte verificado: 2026-07-21

# Deuda técnica vigente

No incluye funcionalidades futuras. Cada elemento corresponde a una condición presente que afecta seguridad, integridad, mantenimiento, operación o UX del alcance implementado.

| ID | Prioridad | Impacto actual | Archivos afectados principales | Propuesta de solución |
| --- | --- | --- | --- | --- |
| TD-001 | P0 | Escalación de privilegios mediante registro público con roles solicitados. | `backend/app/routers/auth.py`, `backend/app/services/auth.py`, schemas auth | Ignorar roles del payload público; permitir asignación sólo a un administrador autorizado y cubrir con pruebas. |
| TD-002 | P0 | Refresh token aceptable como bearer de acceso. | `backend/app/core/security.py`, dependencias auth | Exigir `token_type=access` en usuario actual y `refresh` sólo en refresh; agregar pruebas negativas. |
| TD-003 | P0 | Routers completos permiten lectura/escritura sin autorización uniforme. | routers de Clientes, Cotizaciones, Equipos, Catálogo MYC, plantillas comerciales y motores operativos | Aplicar dependencia autenticada deny-by-default y permiso explícito por operación; matriz 401/403 automatizada. |
| TD-004 | P0 | Portal backend sin aislamiento por tenant expone datos entre clientes. | `backend/app/routers/client_portal.py`, servicio y auth de portal | Derivar `client_id` de identidad autenticada, eliminar filtros suministrados por usuario y probar aislamiento. |
| TD-005 | P0 | Secreto JWT de desarrollo puede llegar a un despliegue. | `backend/app/core/config.py`, configuración de arranque | Rechazar defaults inseguros fuera de desarrollo y documentar rotación. |
| TD-006 | P0 | Lógica ETS duplicada y ruta `confirm-signatures` repetida pueden divergir. | `backend/app/routers/service_orders.py`, `backend/app/services/service_orders.py` | Mantener reglas sólo en el servicio, eliminar ruta duplicada y añadir pruebas de contrato/transiciones. |
| TD-007 | P0 | Calidad y ETS autentican certificados desde superficies distintas. | `frontend/src/pages/QualityPage.jsx`, `frontend/src/pages/ServiceOrdersPage.jsx`, router ETS/certificados | Conservar mutación únicamente en Calidad; ETS sólo lectura/estado y enlace contextual. |
| TD-008 | P1 | Renderer React y PDF backend de Hojas de Campo pueden producir documentos distintos. | `FieldSheetLayout.jsx`, `fieldSheetPagination.js`, `field_sheet_engine_pdf.html`, servicios PDF | Definir un contrato/snapshot único y pruebas visuales/de contenido por plantilla; converger renderizado sin romper históricos. |
| TD-009 | P1 | Semántica y automatizaciones incompletas permiten captura manual no validada. | definiciones de plantillas, servicios de Hojas de Campo, metrología/incertidumbre | Cerrar el registro canónico, conectar motores aprobados y probar cada familia con casos reales. |
| TD-010 | P1 | Los archivos genuinamente no identificados carecen de resolución formal y carga/envío/descarga XLSX no tienen E2E HTTP/browser automatizado. | servicios de paquetes/readiness, UI Captura y Calidad | Agregar resolución explícita y E2E autenticado; persistencia, readiness, transición, acceso XLSX y detección semántica del servicio ya tienen pruebas y caso real verificable. |
| TD-011 | P1 | Cerrar borrador fiscal puede perder cambios y varias pestañas son placeholders; el controlador ya está desacoplado pero estas capacidades funcionales no cambiaron. | `useInvoiceWorkbenchController.js`, `frontend/src/components/invoice-workbench/*` | Autosave/confirmación de descarte; implementar vistas reales o retirar pestañas hasta estar disponibles reutilizando el controlador único. |
| TD-012 | P1 | Producción, cancelación/sustitución, PPD y notas fiscales no cierran el ciclo fiscal existente. | servicios Facturama, invoices, modelos y UI | Diseñar estados idempotentes sobre el agregado actual, persistir respuestas/documentos y cubrir Sandbox antes de habilitar Producción. |
| TD-013 | P1 | Roles/permisos documentados pueden divergir del código y la UI muestra módulos no autorizados. | `backend/app/core/permissions.py`, `frontend/src/config/navigation.js`, Settings | Generar matriz desde código, filtrar navegación por capacidad y decidir CRUD o congelamiento formal de roles. |
| TD-014 | P1 | Excepciones ETS y actor opcional reducen trazabilidad. | modelos/schemas/servicios ETS, routers | Persistir excepción con estado, solicitante, autorizador, motivo y auditoría; exigir actor en mutaciones protegidas. |
| TD-015 | P1 | Compatibilidad de OT/firmas y catálogos fiscales mantiene fuentes conceptuales dobles. | modelos `service_order.py`, `invoice.py`, migraciones y consumidores | Medir uso, migrar históricos, encapsular lectura legacy y retirar columnas sólo con migración reversible. |
| TD-016 | P2 | Páginas monolíticas, componentes duplicados, alerta nativa y bundle grande elevan regresiones/tiempo de carga. El controlador del Workbench ya fue extraído de `BillingPage`, pero permanecen los demás focos. | `ServiceOrdersPage.jsx`, `QuotationsPage.jsx`, `ClientsPage.jsx`, `ServiceOrderSignatureMorph.jsx`, labs/workbench, Vite | Continuar extrayendo dominios, usar `ConfirmDialog`, consolidar componentes y aplicar lazy loading/code splitting con pruebas visuales; no revertir el controlador compartido de Facturación. |
| TD-017 | P2 | Los puertos no tienen una fuente única y pueden divergir entre Toolkit, frontend y documentación. | `scripts/config.sh`, scripts status/start y documentación | Centralizar puertos y probar comandos no destructivos; el forwarding de Doctor ya fue corregido y tiene diagnóstico LibreOffice verificable. |
| TD-018 | P2 | CORS duplicado y storage local dificultan despliegue reproducible. | `backend/app/main.py`, config, `storage_service.py`, scripts de despliegue | Consumir una sola configuración CORS, validar entorno y definir persistencia/backup de archivos para despliegue. |
| TD-019 | P2 | No hay pipeline reproducible de validación/despliegue ni cobertura suficiente de seguridad y flujos críticos. | configuración del repositorio y suites backend/frontend | Añadir CI con build, pruebas, `alembic heads/current`, auditoría de rutas y E2E autenticados no destructivos. |
| TD-020 | P2 | Registro de campos de Hojas de Campo refiere al MDE futuro y puede confundirse con implementación. | `docs/architecture/FIELD_SHEET_FIELD_REGISTRY.md`, definiciones frontend/backend | Mantener el registro como contrato vigente independiente y marcar MDE sólo como consumidor futuro opcional. |

## Criterio de retiro

Una deuda se elimina sólo cuando la condición deja de existir y la validación queda registrada. Si la solución propuesta cambia el alcance funcional, primero debe actualizarse [`CURRENT_SCOPE.md`](CURRENT_SCOPE.md); no se debe convertir una mejora futura en deuda vigente.
