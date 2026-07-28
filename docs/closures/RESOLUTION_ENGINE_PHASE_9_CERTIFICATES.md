> Estado: CIERRE TÉCNICO — EN REVISIÓN
>
> Fecha: 2026-07-28
>
> Alcance: Fase 9, primer y único vertical Certificados

# Cierre técnico — Fase 9 / Certificados

## Resultado

Se implementó `certificate.resolve_incorrect_release` versión `1.0` como primer
caso real del Motor. La resolución retira el acceso futuro del cliente a un
certificado liberado incorrectamente, sin borrar ni reinterpretar su estado,
fecha, actor, PDF autenticado o historia.

La entrega queda **EN REVISIÓN**. Este documento no aprueba la Fase 9, no
habilita otro dominio y no inicia la Fase 10.

## Componentes entregados

- definición vertical y siete componentes puros registrados fuera del núcleo;
- provider de hechos de Certificados exclusivamente read-only;
- contratos de gateway separados de infraestructura;
- gateways de ejecución y compensación sin reglas de negocio;
- servicio canónico propietario con lock, validación, idempotencia y auditoría;
- evidencia propietaria append-only con snapshots anterior/posterior;
- ejecución real mediante `ResolutionExecutor` y seguridad integral de Fase 8;
- compensación real mediante `CompensationRunner`;
- migración reversible `f9c1d3e5a7b9`, con trigger de inmutabilidad en
  PostgreSQL.

## Garantías preservadas

- Lifecycle es la única autoridad de estado del Motor.
- Certificados conserva autoridad sobre sus datos y reglas.
- El núcleo no importa ORM ni servicios de Certificados.
- Consultas y simulación no producen efectos.
- Toda mutación cruza un Domain Gateway hacia el servicio canónico.
- Replay exacto no reinvoca; una intención distinta se rechaza.
- Replay exacto recupera el resultado histórico antes de validar el estado
  actual; una colisión de hash, operación o payload se deniega.
- El snapshot posterior se construye sólo después de `flush` y `refresh`.
- Operación, auditoría y cambio de visibilidad confirman o revierten juntos.
- La compensación agrega evidencia y no elimina la operación fuente.
- No se incorporaron routers, API pública, SDK, workers, distribución, UI,
  otros dominios o IA.

## Validaciones

- suite específica de Fase 9: **12 passed**;
- suite completa del Motor: **213 passed**;
- pruebas seleccionadas de Certificados: **30 passed**; dos pruebas del
  conversor abortan por LibreOffice en el entorno y dos pruebas que crean toda
  la metadata SQLite son bloqueadas por `TD-023`;
- backend completo: **316 passed**, **19 subtests passed**, **21 failed**:
  19 fallos por `TD-023` y dos por el aborto externo de LibreOffice;
- frontend: no declara suite en `package.json`; build Vite correcto, con la
  advertencia preexistente de tamaño de chunk;
- compilación Python: correcta;
- migración: upgrade, downgrade y re-upgrade correctos; `current` y `heads`
  coinciden en `f9c1d3e5a7b9`;
- `alembic check`: conserva únicamente la deriva histórica `TD-021`, sin
  operación atribuible a la tabla de Fase 9;
- trigger append-only comprobado en PostgreSQL.

## Corrección bloqueante de revisión

La revisión posterior a `5abfe2d` identificó que el replay consultaba primero
el certificado vigente y que el snapshot posterior podía preceder al `flush`.
Ambas observaciones quedaron corregidas sin migración:

1. lookup histórico exacto antes del estado actual;
2. segunda comprobación después del lock para la primera ejecución;
3. recuperación del ganador ante colisión concurrente de unicidad;
4. denegación de hash, operación o payload distintos;
5. mutación, `flush`, `refresh` y sólo entonces evidencia posterior;
6. el mismo protocolo para compensación.

La suite reproduce replay tras deriva/inactividad, dos solicitudes concurrentes
exactas, colisiones concurrentes, rollback y equivalencia entre snapshot,
resultado y fila persistida. La Fase 9 continúa `EN REVISIÓN`.

## Restricción

Hasta revisión y aprobación formal:

```text
FASE 9 — EN REVISIÓN
SIGUIENTE DOMINIO — NO INICIADO
FASE 10 — NO INICIADA
```
