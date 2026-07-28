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
- Operación, auditoría y cambio de visibilidad confirman o revierten juntos.
- La compensación agrega evidencia y no elimina la operación fuente.
- No se incorporaron routers, API pública, SDK, workers, distribución, UI,
  otros dominios o IA.

## Validaciones

- suite específica de Fase 9: **7 passed**;
- suite completa del Motor: **208 passed**;
- pruebas seleccionadas de Certificados: **30 passed**; dos pruebas del
  conversor abortan por LibreOffice en el entorno y dos pruebas que crean toda
  la metadata SQLite son bloqueadas por `TD-023`;
- backend completo: **311 passed**, **19 subtests passed**, **21 failed**:
  19 fallos por `TD-023` y dos por el aborto externo de LibreOffice;
- frontend: no declara suite en `package.json`; build Vite correcto, con la
  advertencia preexistente de tamaño de chunk;
- compilación Python: correcta;
- migración: upgrade, downgrade y re-upgrade correctos; `current` y `heads`
  coinciden en `f9c1d3e5a7b9`;
- `alembic check`: conserva únicamente la deriva histórica `TD-021`, sin
  operación atribuible a la tabla de Fase 9;
- trigger append-only comprobado en PostgreSQL.

## Restricción

Hasta revisión y aprobación formal:

```text
FASE 9 — EN REVISIÓN
SIGUIENTE DOMINIO — NO INICIADO
FASE 10 — NO INICIADA
```
