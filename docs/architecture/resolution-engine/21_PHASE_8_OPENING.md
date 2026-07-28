> Estado: APROBADA
>
> Fecha de autorización: 2026-07-27
>
> Autoridad: apertura oficial expresa posterior a la aprobación de Fase 7

# Apertura oficial — Fase 8

## Nombre oficial

**Fase 8 — Seguridad integral**

## Objetivo

Implementar el endurecimiento transversal del Motor de Resoluciones para
garantizar la protección integral de todas las capacidades construidas durante
las Fases 1 a 7, preservando la coherencia arquitectónica alcanzada. Esta fase
no incorpora nuevas capacidades funcionales del ERP: fortalece las garantías
de seguridad del propio Motor.

## Alcance autorizado

Únicamente pueden implementarse:

- endurecimiento transversal del Motor;
- protección integral del ciclo completo de resolución;
- gobierno de acceso sobre las capacidades existentes;
- fortalecimiento de validaciones institucionales;
- protección de operaciones críticas;
- consolidación de reglas de autorización;
- protección contra usos indebidos;
- pruebas de seguridad;
- documentación.

## Dependencias

Las Fases 1, 2, 3, 4, 5, 6 y 7 están aprobadas. La Fase 8 reutiliza
especialmente la infraestructura de seguridad de Fase 3 y la evidencia
institucional consolidada por Fase 7. Los commits identificables del cierre de
Fase 7 son `4ae25ea` y `768ef6e`.

## Bloqueadores corregibles

Sólo pueden corregirse contradicciones que afecten directamente al Motor. La
deuda general del ERP permanece fuera de alcance y no se realizarán
correcciones ajenas al endurecimiento del Motor.

## Fuera de alcance

No se implementan integración ERP, UC-001, casos verticales, Domain Gateways
concretos, API pública, SDK, FastAPI, routers, workers, procesamiento
distribuido, IA, automatizaciones, UI ni integraciones externas. Esas
capacidades pertenecen a fases posteriores.

## Invariantes

- Lifecycle continúa como única autoridad de estado.
- No se crean evaluadores paralelos de seguridad.
- La autorización de Fase 3 no se debilita.
- La auditoría continúa append-only.
- Las consultas permanecen read-only.
- La reconstrucción permanece determinista.
- Los servicios de consulta no producen efectos laterales.
- Continúan idempotencia, locks, evidencia, compensación y consistencia
  transaccional.
- Se mantiene la separación Dominio / Aplicación / Infraestructura.

## Validaciones de salida

La entrega debe incluir suite específica de Fase 8, suite completa del Motor,
backend completo, frontend, build, compilación Python, validaciones
arquitectónicas, `alembic current`, `alembic heads`, `alembic check`,
inventario, documentación sincronizada y commit exclusivo.

## Restricción cumplida

Durante la ejecución de esta fase, la Fase 9 — Integración con ERP MYC
permaneció `NO INICIADA`. La revisión formal aprobó Fase 8 el 2026-07-28 y
habilitó la apertura vigente
[`23_PHASE_9_OPENING.md`](23_PHASE_9_OPENING.md).
