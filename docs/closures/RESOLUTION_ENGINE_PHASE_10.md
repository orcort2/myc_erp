> Estado: APROBADA
>
> Fecha: 2026-07-28

# Cierre técnico de implementación — Fase 10

## Resultado

Se implementó la primera interfaz pública institucional y versionada del Motor:
contratos v1 desacoplados, credenciales por consumidor/organización, API
FastAPI delgada, creación por Lifecycle, consultas por auditoría, idempotencia
namespaced, filtros, cursor opaco ligado a consulta, errores estables, SDK HTTP y portal
técnico.

La revisión formal aprobó la Fase 10 mediante `dd9a84e`.

## Persistencia

La migración reversible `a0d2f4b6c8e1`, hija de `f9c1d3e5a7b9`, crea
`resolution_api_consumers`. No cambia tablas, políticas, Lifecycle, auditoría,
compensación ni el vertical de Certificados.

## Evidencia de validación

- suite específica Fase 10: `10 passed`;
- Fase 10 + vertical Fase 9: `22 passed`;
- suite completa del Motor: `223 passed`;
- backend completo: `328 passed`, `19 failed`, `19 subtests passed`;
- los 19 fallos backend son exclusivamente la incompatibilidad SQLite/JSONB
  de Actividad ya registrada como `TD-023`;
- compilación Python de aplicación, contratos, SDK y suite: correcta;
- frontend Vite: build correcto, con advertencia preexistente de chunk;
- Alembic `current` y `heads`: `b18ac098c1db (head)`, revisión externa de
  Notificaciones aplicada concurrentemente sobre `a0d2f4b6c8e1`; esta
  corrección no agrega ni modifica esquema;
- Alembic `check`: continúa fallando sólo por la deriva histórica `TD-021`;
- respaldo regenerado con el mismo head.

## Garantías comprobadas

- DTOs y SDK no importan `app`;
- router público no importa Motor persistente ni Lifecycle;
- credencial, organización y correlación son obligatorias;
- permiso exacto y evidencia integral preceden altas y lecturas;
- replay exacto recupera el mismo resultado y colisión devuelve `409`;
- otra organización no conoce la existencia del expediente;
- las consultas delegan en `AuditQueryService`;
- la creación delega en `ResolutionLifecycleService`;
- no se añadió lógica de negocio, vertical, IA ni distribución.

## Corrección bloqueante de cursor

La revisión detectó que el cursor inicial firmaba sólo la posición y mantenía
visible la clave interna. La corrección reemplaza ese formato por el sobre
opaco `c1` con AES-GCM y liga versión contractual, consumidor, organización,
hash canónico de filtros, orden, dirección, tamaño de página y posición
keyset. Cualquier divergencia se rechaza.

El formato legacy se revoca deliberadamente porque carece de identidad de
consulta y no puede hacerse seguro mediante reinterpretación. La suite cubre
filtros, consumidores, organizaciones, orden, versión, opacidad, determinismo,
SDK y política legacy.

## Estado de salida

Fase 10 quedó `APROBADA` mediante
`dd9a84ed3ce2e9727fb2b30d8280ed727a25442f`. Fase 11 fue abierta por
autorización formal posterior.
