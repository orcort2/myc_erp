> Tipo: Cierre técnico
>
> Fecha: 2026-07-29

# Desbloqueo de Ventas, tipos de servicio y folios

Se sustituyó la excepción puntual de cambio de servicio por un desbloqueo
controlado de la misma cotización. La edición se realiza en su ficha, el
frontend prepara una revisión completa, muestra el delta y sólo entonces
solicita la operación atómica.

El backend conserva revisión base/resultado, delta, folio ETS y evidencia de
reconstrucción; valida el ETS completo, elimina físicamente el registro virgen
y crea uno nuevo con el mismo folio. El fallo antes del commit revierte todas
las mutaciones.

Se añadieron `ServiceType`, empresas vinculadas extensibles, prefijo
normalizado y snapshots catálogo→cotización→ETS→equipo. Los certificados MYC y
vinculados usan el formato compacto y contadores anuales; OT adopta los pisos
2026/normal anual.

Corrección UX posterior: Administrador no envía una petición a otro usuario.
Al pulsar `Desbloquear cotización`, su autoridad `*` produce solicitud y
autorización auditadas en el mismo comando y abre inmediatamente la edición
excepcional, sin modal ni captura manual de motivo u observación. El sistema
registra un motivo estándar. Comercial y cualquier rol sin
`self_authorize_unlock` conservan la segregación y el formulario.

Migraciones:

- `ae1f2a3b4c5d`: empresas, clasificación, snapshots, contadores y expediente.
- `af2a3b4c5d6e`: snapshot fuente del ETS y restricciones.
- `b03b4c5d6e7f`: pisos institucionales 2026.

Validación registrada: backend completo `409 passed`, `19 subtests passed`
(`9 passed` focalizados); frontend Node `29 passed`; Vite build correcto.
Alembic local quedó en
`b03b4c5d6e7f (head)`. En PostgreSQL temporal se validó
`upgrade head → downgrade 9d0e1f2a3b4c → upgrade head` y después se eliminó
la base. `alembic check` no detectó operaciones nuevas de esta entrega; la
deriva histórica `TD-021` y el E2E autenticado de Ventas→ETS continúan
pendientes.
