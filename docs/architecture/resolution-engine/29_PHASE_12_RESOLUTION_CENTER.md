> Estado: IMPLEMENTADO — EN REVISIÓN
>
> Fase: 12 — Centro de Resoluciones
>
> Autoridad: contrato técnico de la interfaz operativa e integración end-to-end
>
> Corte: 2026-07-28

# Centro de Resoluciones

## Apertura y objetivo

La aprobación formal de la Fase 11 en
`cbde51783870e4b06a4de84c27e05dc2b5ea3de1` autorizó la Fase 12. Esta fase
convierte las capacidades ya aprobadas del Motor en una consola transversal del
ERP. No modifica Domain Model, Lifecycle, políticas, seguridad, auditoría,
compensación, API pública ni SDK. Fase 13 permanece prohibida.

## Fronteras

El Centro se divide en cuatro adaptadores explícitos:

1. `ResolutionOperationsQueryService` compone lista, expediente y timeline
   desde las fuentes canónicas. Sus proyecciones nunca son fuente de verdad.
2. `ResolutionCenterWorkflowService` traduce acciones guiadas a Registry,
   Orchestrator, Lifecycle y Security. El router no muta ORM.
3. la API interna `/api/resolution-center/v1` es distinta de la API pública v1;
4. el worker independiente consume la cola durable y delega en
   `ResolutionExecutor`. No contiene reglas de certificados ni handlers
   alternativos.

El único vertical habilitado es
`certificate.resolve_incorrect_release@1.0`, ya aprobado en Fase 9. El catálogo
de definiciones declara objeto, versión, capacidades, permisos, advertencias y
esquema cerrado de parámetros. No se admiten comandos ni campos arbitrarios.

## Flujo

```text
crear por Lifecycle
  → preparar snapshot por provider
  → analizar
  → seleccionar estrategia y persistir plan
  → simular sin efectos
  → autorizar mediante decisión canónica
  → revalidar contra hechos actuales
  → publicar una unidad durable
  → worker pull
  → ResolutionExecutor
  → resultado, auditoría y eventos append-only
```

Cada etapa HTTP responde sólo después de la transición confirmada. `execute`
responde `202` con “Resolución aceptada para ejecución”; no espera el efecto.
El `work_key` es único por organización y resolución, por lo que replays o dos
usuarios concurrentes recuperan el mismo trabajo y no publican otro.

## Independencia de sesión

La petición web autentica al usuario y produce una decisión de seguridad exacta
por operación. Antes del enqueue, esa decisión se confirma. El payload durable
conserva el snapshot del actor y una concesión de consumo único; no conserva el
token HTTP ni hereda su expiración. Cerrar navegador, cambiar de módulo,
perder conexión o expirar la sesión no cancela el trabajo aceptado.

El worker se ejecuta separadamente con:

```bash
python -m app.resolution_center.worker
```

El proceso registra nodo, renueva heartbeats y leases, ejecuta recovery seguro
y respeta fencing, backoff determinista e incertidumbre bloqueante de Fase 11.

## Lectura y privacidad

La lista utiliza cursor opaco ligado a actor, organización, filtros, orden y
tamaño. Admite búsqueda funcional y filtros de solicitante, autorizador, tipo,
objeto, estados, resultado, fechas, reintentos, bloqueo y compensación. Un
usuario sin `read_all` sólo consulta resoluciones propias.

El expediente compone resumen, objeto, Lifecycle, estado distribuido, plan,
simulación, resultado, timeline y evidencia. IDs internos, lease token y claves
primarias no salen. Los roles con `resolution_center.audit` ven decisiones,
snapshots, revalidaciones y referencias; hashes, facts, nodo y lease sólo salen
con `resolution_center.infrastructure`.

## Permisos

| Permiso | Capacidad |
| --- | --- |
| `resolution_center.read` | abrir módulo y resoluciones permitidas |
| `resolution_center.read_all` | consultar toda la organización |
| `resolution_center.create` | crear desde catálogo controlado |
| `prepare`, `analyze`, `plan`, `simulate` | etapa canónica correspondiente |
| `resolution_center.authorize` | autorizar si cumple además requisitos del plan |
| `resolution_center.execute` | aceptar ejecución distribuida |
| `resolution_center.audit` | consultar evidencia y actores |
| `resolution_center.infrastructure` | ver nodo, lease y hashes técnicos |

Administrador conserva `*`. Desarrollador recibe `resolution_center.*`.
Auditor sólo recibe lectura global, auditoría e infraestructura. Los roles
operativos reciben lectura propia. La interfaz consume capabilities del backend
y no decide autoridad por nombre de rol.

## Interfaz

`/resolutions` es un módulo principal. La tabla contiene todos los datos
operativos mínimos, filtros y paginación estable. El expediente amplio muestra
el flujo y sólo ofrece la acción válida para el estado real. El polling ocurre
únicamente si hay resoluciones activas, la pestaña está visible y no existe otra
carga simultánea. No se incorporan WebSocket, SSE ni almacenamiento local.

## Persistencia y migración

La revisión `d2f4a6b8c0e3` no crea tablas. Corrige el trigger PostgreSQL de planes:
mantiene identidad y contenido inmutables, pero permite únicamente transiciones
de estado canónicas. Cambios de activación o invalidación quedan restringidos a
sus estados válidos. El downgrade restaura el guard anterior.

## Límites

No existen controles para forzar estados, reasignar workers, editar leases,
borrar eventos/evidencia, repetir efectos inciertos, desbloquear, compensar
manualmente o cancelar genéricamente. No se agregaron IA, dominios nuevos,
cambios funcionales al ERP, ni cambios a API pública/SDK.

## Validación

La suite específica cubre flujo end-to-end hasta cola, aislamiento, cursor,
idempotencia, despacho único, redacción, reconstrucción del actor, migración y
límites del router. Las suites previas del Motor continúan siendo autoridad para
retries, recovery, fencing, compensación y replay del ejecutor canónico. El
cierre reproducible se registra en
`../../closures/RESOLUTION_ENGINE_PHASE_12.md`.
