> Estado: VIGENTE
>
> Tipo: Arquitectura vigente
>
> Corte: 2026-07-29

# Actividad institucional

## Propósito y frontera

Actividad es el canal interno común para conversación humana, archivos,
menciones, solicitudes de atención y eventos operativos asociados a registros
existentes del ERP. No reemplaza datos de dominio, auditoría, notificaciones,
Communications ni el Motor de Resoluciones.

La dependencia es unidireccional: los servicios canónicos publican eventos
después de aplicar sus reglas y antes de su commit propietario. Los workers,
routers y componentes de Actividad no ejecutan reglas de Cliente, ETS,
Certificados, Facturación o Resoluciones.

## Modelo persistente

- Un `ActivityThread` único por `(entity_type, entity_id)`.
- `ActivityMessage` humano o de sistema; los eventos formales son inmutables.
- `ActivityMessageRevision` conserva cada texto anterior.
- `ActivityMention` enlaza usuarios y permite revocación.
- `ActivityAttachment` conserva nombre original, ruta segura, MIME, tamaño,
  evidencia oficial y ocultamiento lógico.
- `ActivityThreadRead` conserva el último mensaje leído por usuario.
- `ActivityAttentionRequest` conserva solicitante, usuario/área destino,
  prioridad, estado, resolución, actor y fechas.

La migración `8c9d0e1f2a3b` agrega eventos idempotentes, relaciones opcionales,
lecturas y atenciones. Restricciones SQL validan prioridades, estados, destino
y completitud de resolución.

## Catálogo de entidades

`backend/app/services/activity_entities.py` es la única fuente backend de
tipos, modelo, permiso de lectura, referencia y destino frontend. Contiene:
Cliente, Contacto, Cotización, ETS, Orden de Trabajo, Equipo, Hoja de Campo,
Certificado, Factura, Pago, Nota de crédito, Documento, Interpretación,
Perfil técnico, Patrón, Certificado de patrón, Procedimiento, Modelo de
incertidumbre y Resolución.

Cada lectura exige simultáneamente `activity.read` y el permiso del módulo.
Los registros inactivos conservan acceso histórico; un ID inexistente devuelve
404. Resoluciones se enlazan desde su `public_id` mediante un adaptador interno
de Activity, sin modificar contratos del Centro, Motor, API Pública o SDK.

## Permisos

- `activity.read`
- `activity.create`
- `activity.edit_own`
- `activity.delete_own`
- `activity.moderate`
- `activity.attach_files`
- `activity.mention`
- `activity.request_attention`
- `activity.resolve_attention`
- `activity.view_audit`

El autor puede editar durante 30 minutos y retirar lógicamente sus mensajes.
Moderación no permite modificar eventos formales. Auditoría controla acceso a
revisiones y contenido retirado.

## Eventos

`publish_event`:

- nunca hace commit;
- exige entidad existente;
- crea el hilo sólo al primer mensaje/evento;
- usa `idempotency_key` única con resolución segura de carreras;
- actualiza el orden temporal del hilo;
- no escribe reglas ni estados del dominio.

Se publican transiciones canónicas de Cotización, ETS, Equipo, Hoja de Campo,
Certificado y Factura, además de pago y nota de crédito. Auditoría continúa
siendo la fuente institucional de quién cambió el dominio; Activity presenta
el evento operativo en contexto.

El desbloqueo controlado publica solicitud, decisión, bloqueo y cierre con
claves idempotentes por `EXV-…`. La evidencia principal vive en la Cotización
`MYC-…`; el ETS recreado `OSMYC-…` recibe su evento de reconstrucción. Los IDs
de relación permanecen internos y la narrativa usa folios visibles.

## Adjuntos

Máximo 10 archivos por mensaje y 15 MB por archivo. Se valida:

1. extensión permitida;
2. MIME permitido;
3. correspondencia MIME/extensión;
4. firma real para PDF, imágenes y ZIP/Office;
5. UTF-8 para texto;
6. nombre almacenado UUID + nombre saneado.

Sólo imágenes vigentes ofrecen vista previa. Todo acceso vuelve a comprobar el
permiso de la entidad.

## No leídos, bandeja y atención

Leer el hilo no modifica implícitamente el acuse. El frontend llama
explícitamente `POST /activity/{type}/{id}/read`. Eventos de sistema sin autor
cuentan como no leídos. La bandeja filtra cada hilo por acceso real a entidad.

La atención se liga a un mensaje humano vigente, requiere usuario o área,
genera notificación y sólo puede resolverla el asignado, un resolutor de área o
moderación. La resolución es auditable y cierra la notificación pendiente.

## Compatibilidad

El endpoint anterior `POST /messages/{id}/withdraw` permanece temporalmente
como compatibilidad deprecada; el consumidor vigente usa `DELETE`. Los campos
históricos de notas no se borraron ni migraron masivamente.
