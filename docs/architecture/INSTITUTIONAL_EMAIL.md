# Infraestructura institucional de correo (EMAIL-1)

> Estado: EN REVISIÓN (sin commit). Alcance: infraestructura central. Sin consumidores de recuperación de contraseña, cotizaciones ni facturas.

## Capas

```
Dominio (Portal, futuro: password reset, cotización, factura)
        ↓  send_email / preview_email / retry_delivery
EmailService  (backend/app/services/email/service.py)
        ↓  render_email (renderer.py)   ← única autoridad preview == envío
        ↓  SmtpTransport (transport.py) ← único módulo que habla SMTP
Relay SMTP (producción: Google Workspace smtp-relay.gmail.com:587 + STARTTLS)
```

Ningún dominio importa `smtplib`. `portal/mail_service.py` es un adapter delgado hacia `send_email`.

## Configuración (sólo variables de entorno)

`EMAIL_ENABLED` (false), `SMTP_HOST`, `SMTP_PORT` (587), `SMTP_USE_STARTTLS` (true), `SMTP_USERNAME`/`SMTP_PASSWORD` (opcionales: relay por IP sin AUTH), `EMAIL_FROM_ADDRESS`, `EMAIL_FROM_NAME`, `EMAIL_REPLY_TO`, `EMAIL_TIMEOUT_SECONDS` (15) y `PUBLIC_APP_BASE_URL` (origen web para construir enlaces; fallback legado `PORTAL_PUBLIC_BASE_URL`; sin default productivo y obligatoria `https://` en producción con `EMAIL_ENABLED=true`). En producción con `EMAIL_ENABLED=true` el arranque falla si falta `SMTP_HOST` o `EMAIL_FROM_ADDRESS` (con `@` y sin espacios; la validación completa de la dirección es del transporte) o si `SMTP_USE_STARTTLS=false`. Ningún secreto se guarda en BD ni se devuelve por API.

## Plantillas

`email_templates` guarda asunto y cuerpo humano con marcadores `{variable}`. `services/email/catalog.py` es la autoridad en código de las variables permitidas por plantilla (`portal_email_verification`, `portal_invitation`, `password_reset`, `quotation_send`, `invoice_send`), su tipo (`text`/`url`) y cuáles son secretas. El HTML lo genera el sistema; no hay Jinja, `eval` ni `format`. Marcadores desconocidos, llaves anidadas o contexto extra se rechazan. Los valores se escapan, las URL deben ser http(s) y el asunto se aplana a una línea. Los defaults se crean con get-or-create idempotente y nunca sobrescriben ediciones.

## Entrega y estados

`email_deliveries` conserva snapshot deliberado (asunto, texto, HTML, destinatarios, metadatos de adjuntos). Estados: `pending → sending → sent | failed`. `sent` significa **el relay aceptó el mensaje**. Con `EMAIL_ENABLED=false` no se envía: queda `failed` con `failure_code=email_disabled`, `attempt_count=0` (sólo cuentan intentos SMTP reales) y `last_error` explícito; ese fallo **no es reintentable** (se genera un nuevo envío). No se añadió un quinto estado. El servicio hace commit en cada transición, nunca relanza fallas de transporte y siempre cierra en `sent`/`failed`; los errores de validación se lanzan antes de persistir. **El llamador debe confirmar su operación de negocio antes de `send_email`.**

Las variables secretas (`verification_url`, `invitation_url`, `reset_url`) se redactan (`[enlace protegido]`) en snapshot y auditoría; el mensaje real se arma en memoria. Consecuencia: plantillas con secreto **no se reintentan** (se genera una nueva solicitud) y tampoco las entregas con adjuntos (sólo se guardan nombre, tipo, tamaño y SHA-256). Máximo 5 intentos.

## RBAC y alcance

Permisos: `email.templates.read|manage`, `email.deliveries.read|retry`, `email.transport.status`, `quotations.email.send`, `invoices.email.send` (asignación por rol en `permissions.py`).

**Historial global fail-closed.** Cotizaciones y facturas no exponen una función de autorización por registro (sólo `quotations.read`/`invoices.read`), por lo que un mapeo tipo→permiso no probaría acceso al `related_entity_id`. Los endpoints globales de entregas (listado, detalle y `retry`) exigen además `email.templates.manage` (Administrador y Desarrollador); los demás roles reciben lista vacía o 404 aunque tengan `email.deliveries.read`/`retry`. Esas capacidades quedan reservadas para los endpoints contextuales de EMAIL-3/EMAIL-4, que mostrarán el historial desde la cotización/factura una vez autorizada la entidad. Las entregas guardan `failure_code` (`email_disabled`, `transport_failed`).

API (`/api/email`): `GET/PATCH templates`, `GET deliveries[/id]`, `POST deliveries/{id}/retry`, `GET transport/status` (sólo configuración; no abre conexión). No hay preview genérico: se servirá desde cada dominio con contexto construido por el backend.

## Pendientes futuros

EMAIL-2 ya implementado (ver `PASSWORD_RESET.md`), EMAIL-3 (cotizaciones), EMAIL-4 (facturas), UI de plantillas, outbox/worker asíncrono, retención de adjuntos regenerables, activación de `PORTAL_PUBLIC_BASE_URL` por despliegue.
