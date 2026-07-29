# Cierre técnico — Motor de Resoluciones Fase 14

> Estado: `TERMINADA — EN REVISIÓN`
>
> Alcance: Expansión institucional de integraciones
>
> Definición: `service_order.resolve_additional_equipment@1.0`

## Entrega

La Fase 14 instala el segundo vertical completo sin alterar el núcleo. El
Centro, worker y API pública reciben sus definiciones desde
`build_installed_resolution_integrations`; Certificados deja de estar
hardcodeado en la frontera pública.

El nuevo vertical cubre propuesta ERP/offline, análisis del ETS, duplicados,
catálogo y clasificación, capacidad máxima de diez equipos por OT, firma,
impacto comercial, simulación sin efectos, autorización, revalidación,
ejecución distribuida, reserva de certificado esperado, idempotencia,
concurrencia y compensación limitada.

## Evidencia de validación

- Suite Fases 13–14 seleccionada: `15 passed`.
- Suite Fases 11–14 seleccionada: `36 passed`.
- Suite específica Fase 14: `7 passed`.
- Flujo real: Lifecycle completo, cola durable y worker después de cerrar la
  sesión solicitante.
- Concurrencia: dos sesiones con la misma conciliación producen un solo equipo
  y un solo certificado esperado; locks transaccionales PostgreSQL serializan
  además la numeración global de OT y certificado.
- Segregación E2E: Operador prepara/simula, Calidad autoriza y Técnico ejecuta
  mediante permisos verticales distintos antes de que el worker consuma la
  decisión exacta.
- Migración PostgreSQL:
  `upgrade head → downgrade 6ae1d4877cdb → upgrade head`, actual
  `7b8c9d0e1f2a (head)`.
- Alembic no reporta drift en columnas, índice o FK de Fase 14. El `check`
  global continúa reportando deuda histórica y la tabla Notificaciones no
  cargada en metadata; no pertenece a esta fase.
- Frontend: `3 passed`; build Vite con `1693` módulos.
- Motor completo: `243 passed`, `2 failed`, `14 errors` por el `JSONB`
  concurrente de Notificaciones bajo SQLite.
- Backend completo: `348 passed`, `21 failed`, `14 errors`, `19 subtests
  passed`; no se declara correcto y los fallos restantes son preexistentes de
  TD-023/JSONB y SAT/XLSX.
- `git diff --check`: se valida sobre el conjunto de Fase 14; existen espacios
  finales en CSS concurrente ajeno.

## Límites preservados

- No se introdujo IA.
- No se modificaron API/SDK v1 ni contratos públicos incompatibles.
- No se ejecutan efectos antes de autorización.
- No se asignan folios durante simulación.
- No se borran firmas, Hojas de Campo, certificados consumidos, CFDI ni
  evidencia del Motor.
- No se amplió la excepción genérica de `service_orders.py`.

## Estado de salida

Fase 14 queda `TERMINADA — EN REVISIÓN`. La Fase 15 no está abierta.
