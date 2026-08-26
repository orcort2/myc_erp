> Estado: IMPLEMENTADA — EN REVISIÓN
>
> Corte verificable: 2026-08-25

# Fase 15 — Herramientas administrativas y continuidad ETS

## Contrato

El Centro de Resoluciones incorpora la familia declarativa
`administrative_tools`. La familia no crea otro motor: cada herramienta sigue
el ciclo canónico `contexto → análisis → plan → simulación → autorización →
revalidación → cola durable → worker → resultado/auditoría` y se instala por
`build_installed_resolution_integrations`.

Las primeras herramientas son definiciones distintas y versionadas:

| Definición | Sujeto | Riesgo | Efecto permitido |
| --- | --- | --- | --- |
| `service_order.restore_soft_deleted@1.0` | ETS | HIGH | Reactiva el mismo ETS y sus OT, sin cambiar snapshots, partidas ni folios. |
| `service_order.rebuild_from_accepted_quotation@1.0` | Cotización | CRITICAL | Materializa un ETS sólo si la cotización está aceptada y no existe ETS activo o inactivo. |
| `service_order.void_preserving_history@1.0` | ETS | CRITICAL | Retira un ETS prístino de la operación visible sin borrar ni reescribir sus OT. |

Restaurar, reconstruir y dar de baja no son alias. Si existe un ETS inactivo,
la reconstrucción se bloquea y debe evaluarse restaurar. Si existe un ETS
activo, el replay de reconstrucción devuelve ese mismo ETS. La creación
ordinaria desde una cotización también bloquea ante un ETS inactivo; nunca lo
sustituye silenciosamente.

## Precheck y preservación

El contexto congela `allowed`, `blockers`, `warnings`, entidades afectadas,
cambios propuestos y fecha de actualización. Equipos, certificados, archivos
de Captura, facturas, ciclos/firmas, ejecución de Venta o un estado operativo
distinto de `scheduled` bloquean baja/restauración automática. La revalidación
exige el mismo hash antes del efecto.

La reconstrucción usa exclusivamente la cotización aceptada y sus snapshots
operacionales congelados mediante el servicio propietario de ETS. No consulta
el catálogo para reinterpretar históricos. Servicios Compuestos, categorías,
cantidades, scopes, Masters y configuración de Venta siguen el constructor
canónico vigente.

## Seguridad y ejecución

Cada operación declara permisos separados `.propose`, `.authorize` y
`.execute`. Calidad recibe autorización; Operador recibe propuesta/ejecución;
Desarrollador recibe las claves explícitas para soporte. El permiso general del
Centro no sustituye el permiso de dominio. El Domain Gateway abre una
transacción propia, bloquea el sujeto, delega en
`services/service_order_administration.py` y devuelve efectos que el Motor
registra como referencias append-only.

La baja directa HTTP y `deactivate_service_order` están deshabilitados con
`409 administrative_resolution_required`. La pantalla normal enlaza al Centro.
No se creó migración ni se modificó el esquema.

## Límites abiertos

- Reparación estructural genérica permanece bloqueada: no existe todavía una
  estrategia segura para expedientes con dependencias operativas.
- Las bajas legacy que cancelaron OT sin snapshot previo sólo son restaurables
  automáticamente cuando el ETS es prístino.
- La búsqueda contextual por folio/cliente/cotización dentro de Herramientas
  continúa como P1; la primera versión recibe el ID explícito.
- La autorización secundaria específica para riesgo CRITICAL aún se apoya en
  la segregación solicitante/autorizador del Motor; falta una política de doble
  aprobación configurable.
