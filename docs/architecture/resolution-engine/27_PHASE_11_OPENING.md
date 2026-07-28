> Estado: APERTURA APROBADA — IMPLEMENTACIÓN CONCLUIDA
>
> Fecha: 2026-07-28
>
> Autoridad: aprobación formal de Fase 10 y autorización expresa de Fase 11

# Apertura oficial — Fase 11

## Nombre oficial

**Fase 11 — Motor Distribuido**

## Dependencia satisfecha

La Fase 10 fue aprobada formalmente mediante:

```text
dd9a84ed3ce2e9727fb2b30d8280ed727a25442f
fix(resolution-engine): bind public cursors to queries
```

Los contratos públicos v1, API y SDK permanecen congelados. La distribución es
una capacidad interna y no modifica ni versiona aquella superficie.

## Objetivo autorizado

Permitir procesamiento asíncrono mediante múltiples procesos coordinados,
preservando exclusividad, idempotencia, auditoría, compensación, seguridad,
determinismo y recuperación verificable.

## Alcance

- cola durable y despacho pull;
- workers independientes con registro, capacidad, heartbeat y drenado;
- reclamación concurrente con `FOR UPDATE SKIP LOCKED`;
- exclusividad por resolución;
- leases de nodo y trabajo con fencing token y versión;
- recuperación de nodos y trabajos expirados;
- reintentos deterministas sólo cuando se confirma ausencia de efecto;
- bloqueo explícito ante efecto incierto;
- prioridad, disponibilidad diferida y balanceo por capacidad;
- eventos append-only y snapshot operacional agregado;
- handlers internos inyectables que reutilizan los servicios canónicos.

## Invariantes

- Lifecycle continúa como única autoridad del estado de una resolución.
- El worker no interpreta planes, políticas, permisos ni reglas de dominio.
- Un handler nunca se invoca fuera de un trabajo durable reclamado.
- El mismo `resolution_id` no se reclama simultáneamente por dos trabajos.
- Un propietario obsoleto no puede completar, fallar ni renovar el trabajo.
- Si el lease expira tras iniciar el posible efecto, el trabajo queda
  `blocked`; no se confirma, no se reintenta y requiere conciliación explícita.
- Sólo un fallo declarado `no_effect` puede usar retry automático.
- El backoff se calcula sin jitter: `min(base × 2^(attempt-1), máximo)`.
- Los eventos de distribución son evidencia operacional append-only.
- Domain Model, Lifecycle, Policies, Engine, seguridad, autorización, auditoría,
  compensación, API, SDK y contratos públicos de Fases 1–10 no cambian.

## Exclusiones

- IA, aprendizaje, recomendaciones o adaptación automática;
- nuevos dominios o cambios funcionales del ERP;
- microservicios o separación física obligatoria del Motor;
- broker externo obligatorio;
- reinterpretación de históricos;
- confirmación automática de efectos inciertos;
- cambios incompatibles de API/SDK.

## Gate

La fase sólo puede pasar a revisión con migración reversible, coordinación
multinodo demostrable, pruebas de fencing/recuperación/retry, suite completa,
documentación sincronizada, validación Alembic y commit exclusivo.

Fase 12 permanece `NO INICIADA`.
