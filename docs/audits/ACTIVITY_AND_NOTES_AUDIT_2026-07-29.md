> Tipo: Auditoría técnica fechada
>
> Corte: 2026-07-29
>
> Autoridad: evidencia de implementación; no sustituye los documentos canónicos de `project/`

# Auditoría de Actividad, notas y comunicaciones internas

## Resumen ejecutivo

Antes de esta integración existían tres capacidades separadas:

1. `Activity`, limitada a Cliente, ETS y Factura, con comentarios, menciones,
   adjuntos, edición y retiro lógico.
2. `Notifications`, utilizada para menciones.
3. `Communications`, conversación entre usuarios/clientes independiente del
   expediente operativo.

La búsqueda local encontró 434 referencias textuales a `notes`, `comments`,
`observations` o equivalentes entre backend y frontend. Esa cifra es un
inventario técnico, no 434 campos equivalentes. La revisión semántica confirmó
que muchos textos son datos de dominio o contenido documental y no deben
migrarse a conversación.

## Clasificación verificable

| Clasificación | Campos/casos principales | Tratamiento |
| --- | --- | --- |
| Comunicación interna histórica | `Client.notes`, `Quotation.notes`, `ServiceOrder.notes`, `Invoice.internal_comments` | Se conservan. ETS muestra su nota histórica en sólo lectura y toda comunicación nueva usa Actividad. No hubo backfill automático. |
| Dato técnico de dominio | condición inicial/final de Equipo, observaciones/evidencia de Hoja de Campo, notas de patrón, procedimiento e incertidumbre | Permanece en su agregado y formulario canónico. Actividad se añade como canal separado. |
| Contenido comercial/documental | descripción de partida, términos de Cotización, observaciones impresas de Factura, leyendas y resúmenes de cambio documental | Permanece en el documento; no se reinterpreta como comentario interno. |
| Evidencia de decisión | rechazo/corrección de Calidad, autorización, auditoría, cancelación, excepción y pago | Permanece en el flujo propietario. Los cambios de estado relevantes generan eventos de Actividad, sin sustituir auditoría. |
| Conversación humana nueva | seguimiento, aclaraciones, coordinación, menciones y archivos internos | Se registra en `ActivityMessage` bajo hilo único por entidad. |
| Atención operativa | seguimiento asignado a usuario o área | Se registra en `ActivityAttentionRequest`, se notifica y se resuelve con actor/fecha/nota. |

## Superficies auditadas

| Superficie | Estado anterior | Estado al corte |
| --- | --- | --- |
| Cliente | Sin panel institucional | Panel común por cliente |
| Contacto | Dependiente de Cliente; sin ficha autónoma | Backend soportado; se consume al existir una ficha autónoma |
| Cotización | Campo `notes` | Panel común; campo histórico/comercial preservado |
| ETS | Pestaña Notas mutable | Pestaña Actividad; nota previa sólo lectura |
| Orden de Trabajo | Sin ficha autónoma de Actividad | Entidad soportada por catálogo backend |
| Equipo | Notas técnicas | Notas técnicas preservadas + panel común |
| Hoja de Campo | Observaciones técnicas | Observaciones preservadas + panel común |
| Certificado/Calidad | Notas y motivos de flujo | Datos propietarios preservados + panel común |
| Factura/pago/nota de crédito | Activity sólo en Workbench de Factura | Factura conserva panel; pagos/notas generan eventos relacionados |
| Control Documental | Historial derivado | Panel común adicional, sin alterar versiones |
| Patrones/procedimientos/incertidumbre | Notas técnicas | Datos técnicos preservados + panel común |
| Centro de Resoluciones | Sin conversación interna | Panel común mediante adaptador Activity de `public_id`; Motor intacto |
| Dashboard | Sin bandeja transversal | Bandeja de no leídos y atenciones pendientes |

## Módulos no fabricados

- CRM/Leads no tiene implementación funcional.
- Contactos no constituye hoy un módulo autónomo.
- Agenda y Llamados son hitos absorbidos por ETS, no entidades autónomas.
- No existe un dominio Tickets y no se creó ninguno.

Actividad no crea esos dominios. El catálogo sólo registra entidades
persistentes existentes.

## Hallazgos resueltos

- ✅ Resuelta: catálogo limitado a tres tipos de entidad.
- ✅ Resuelta: permisos `read/write/audit` demasiado gruesos.
- ✅ Resuelta: uso directo de `JSONB` en Activity/Notifications que impedía
  crear metadata en SQLite.
- ✅ Resuelta: ausencia de lectura explícita, bandeja y contador no leído.
- ✅ Resuelta: ausencia de atención asignable y resoluble.
- ✅ Resuelta: adjuntos sin correspondencia estricta MIME/extensión/firma.
- ✅ Resuelta: eventos operativos sin idempotencia persistente.
- ✅ Resuelta: catálogo de menciones dependiente de `users.read`.
- ✅ Resuelta: notas históricas de ETS susceptibles de sobrescribirse durante
  la transición; quedan visibles en sólo lectura.

## Límites comprobados

- La bandeja navega al módulo canónico; la selección automática de cada fila
  concreta depende de que la página propietaria consuma `entity_id` en su URL.
- `alembic check` conserva drift histórico global registrado en `TD-021`; no
  detecta operaciones nuevas sobre `activity_*` o `notifications`.
- Las dos pruebas de conversión real LibreOffice continúan dependiendo del
  binario local y abortaron con `returncode=-6`; no pertenecen a Actividad.
