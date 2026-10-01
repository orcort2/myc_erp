# Contactos de cliente y envío de cotizaciones por correo (EMAIL-3)

> Estado: EN REVISIÓN (sin commit). Construye sobre EMAIL-1 (`EmailService`, plantilla `quotation_send`, permiso `quotations.email.send`); no crea otra infraestructura de correo.

## ClientContact

Personas de contacto que **pertenecen a un Client** (`client_contacts`, soft delete). El correo general del cliente (`clients.email`) y el de una persona son datos distintos y no se mezclan.

La edición embebida (`PATCH /clients/{id}` con `contacts`) reemplazaba la lista completa y rompía ids; ahora es un *merge* que conserva ids (match por nombre+correo, actualiza en sitio, **desactiva** —no borra— los no listados). La UI ya no reenvía `contacts` al editar. Endpoints granulares (`/api/clients/{client_id}/contacts`): `GET`, `POST`, `PATCH /{contact_id}`, `DELETE /{contact_id}` (desactiva), `POST /{contact_id}/restore`. Lectura = `clients.read`; escritura = `clients.update`. El contacto debe pertenecer al `client_id` de la ruta (404 en otro caso). Auditoría `client.contact.created|updated|deactivated|restored`.

UI: el modal de cliente tiene la pestaña **Contactos** (lista, nuevo, editar, desactivar/reactivar); el campo "Contacto inicial" solo aparece al crear y no copia el correo/teléfono del cliente.

## Quotation.contact_id

`quotations.contact_id` nullable, FK `client_contacts.id ON DELETE SET NULL` (migración `c3e6a9b2d4f8`, down `b2d5f8a1c3e7`). Representa al interlocutor principal; los datos viven solo en `ClientContact` (lectura expone `contact_name|email|position` de solo lectura). Reglas (422): el contacto debe pertenecer al cliente de la cotización y estar activo **al asignarse**; una cotización histórica conserva un contacto luego desactivado. Si cambia `client_id` sin enviar `contact_id`, se limpia; restaurar una versión nunca deja un contacto ajeno. El snapshot incluye `contact_id`.

PDF: `quotation.contact` es la autoridad (Atención, puesto, y teléfono/correo del contacto con respaldo del cliente); sin `contact_id` se conserva el respaldo histórico (primer contacto activo); sin contactos el PDF se genera igual.

## Envío por correo (separado de `POST /quotations/{id}/send`)

| Endpoint | Permiso |
|---|---|
| `POST /api/quotations/{id}/email/preview` | `quotations.email.send` |
| `POST /api/quotations/{id}/email/send` | `quotations.email.send` |
| `GET /api/quotations/{id}/email/deliveries` | `email.deliveries.read` **y** `quotations.read` |

El cliente solo envía `{to, cc}` (`extra=forbid`: subject/body/HTML/archivos/plantilla se rechazan). El backend construye destinatarios sugeridos (contacto de la cotización → otros contactos activos con correo → `clients.email`; el primero queda seleccionado), valida y deduplica sin distinguir mayúsculas (TO gana sobre CC), arma el contexto (`contact_name` = contacto si el primer TO corresponde a un contacto; si no, nombre comercial/razón social), renderiza con el mismo renderer en preview y envío, y adjunta el PDF de `generate_quotation_pdf` (idéntico al oficial). Se permiten **direcciones manuales** TO/CC: aplican solo a ese envío, no crean contactos ni modifican el cliente y quedan en `EmailDelivery`.

Enviar correo **no cambia `quotation.status`** ("Marcar como enviada" sigue siendo la acción manual). `sent` significa que el relay SMTP aceptó el mensaje, no que el cliente lo recibió.

Historial contextual: solo entregas con `related_entity_type="quotation"` y el id de la cotización, orden descendente, sin BCC ni cuerpo. El historial global `/api/email/deliveries` sigue siendo fail-closed (Administrador/Desarrollador). **Reenviar** (UI) repite el flujo contextual: regenera PDF, renderiza y crea un `EmailDelivery` nuevo; el fallido no se muta ni se usa el retry genérico (los adjuntos no se persisten).

El `EmailDelivery` guarda nombre, tipo, tamaño y SHA-256 del adjunto, no los bytes. No existe una revisión canónica por envío en `QuotationSnapshot`, por lo que la trazabilidad es `quotation_id` + SHA-256 del PDF.

Auditoría: `quotation.email.sent|failed` (folio, delivery_id, estado, SHA-256) además de `email.delivery.*`.
