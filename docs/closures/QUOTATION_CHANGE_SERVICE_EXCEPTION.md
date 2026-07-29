> Estado: CIERRE TÉCNICO VALIDADO
>
> Fecha: 2026-07-29

# Cierre técnico — excepción de cambio de servicio

## Diagnóstico anterior

La cotización `accepted` era terminal y sólo podía conservarse bloqueada. No
existía una solicitud contextual, segregación, capacidad limitada ni operación
que sincronizara la misma cotización y el mismo ETS. El Centro de Resoluciones
pedía IDs técnicos y etapas que no corresponden a esta decisión de negocio.

## Entrega

- Expediente `QuotationServiceChangeRequest` con folio `EXV-…`, snapshots de
  servicio, impacto, decisión, usuario aplicador, vigencia y consumo.
- API por folios visibles de cotización/excepción; la solicitud identifica la
  partida por su número visible y el servicio por su clave generada, no por IDs.
- Acción contextual en Cotizaciones y bandeja administrativa de Excepciones.
- Permisos separados para solicitar, inspeccionar, autorizar y aplicar.
- Capacidad exacta `quotation.change_service_type`, nominativa, temporal y de
  un solo uso.
- Snapshot previo y nueva revisión con el mismo folio de cotización.
- Sincronización atómica de las partidas dependientes del mismo ETS `OSMYC-…`.
- Bloqueo si existe cualquier equipo, incluso cancelado o dado de baja lógica.
- Actividad idempotente en Cotización/ETS, auditoría y Notifications.
- Bloqueo de impactos comerciales no autorizados.

## Validaciones

- Suite específica backend: `11 passed`.
- Regresión dirigida de Actividad y Servicios Compuestos: `23 passed`.
- Suite backend completa fuera del sandbox para permitir LibreOffice:
  `411 passed`, `19 subtests passed`; sólo 2 warnings de dependencias.
- Frontend completo: `23 passed`, incluidas 2 pruebas nuevas.
- Build Vite: correcto; conserva el warning previo de chunk mayor a 500 kB.
- Import/compile backend: correcto.
- Alembic: un único head `9d0e1f2a3b4c`, aplicado en PostgreSQL local; backup
  de 71 MB regenerado con el mismo `alembic_version`. `alembic check` conserva
  únicamente la deriva histórica ya registrada en `TD-021`.

## Archivos propietarios

- Modelo: `backend/app/models/quotation_service_change.py`.
- Schemas: `backend/app/schemas/quotation_service_change.py`.
- Solicitud/autorización/aplicación/validadores:
  `backend/app/services/quotation_service_changes.py`.
- Router: `backend/app/routers/quotation_service_changes.py`.
- Migración: `backend/migrations/versions/9d0e1f2a3b4c_quotation_service_change_exception.py`.
- Componentes: `frontend/src/components/sales/QuotationServiceExceptions.jsx`.
- Pruebas backend/frontend:
  `backend/tests/test_quotation_service_change_exception.py` y
  `frontend/src/utils/quotationServiceExceptions.test.js`.
- Contrato: `docs/architecture/sales/QUOTATION_CHANGE_SERVICE_EXCEPTION.md`.

## Límites y deuda

No se implementaron otras excepciones, reapertura completa, alta/baja de
equipos, cancelación, Facturación, Pagos ni otra fase del Motor. Permanece la
deuda transversal de proteger uniformemente los routers legacy.
