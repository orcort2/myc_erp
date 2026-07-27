> Estado: APERTURA APROBADA — IMPLEMENTACIÓN CERRADA EN REVISIÓN
>
> Fase: 7 — Auditoría y Evidencia
>
> Autoridad de nombre y capacidad: `12_ROADMAP.md`
>
> Autorización: dictamen expreso de apertura de Fase 7

# Apertura formal de la Fase 7

## Nombre oficial

**Fase 7 — Auditoría y Evidencia**

## Objetivo arquitectónico

Convertir la evidencia ya persistida por las Fases 1 a 6 en una capacidad
institucional explícita para reconstruir, verificar, correlacionar y consultar
el ciclo completo de cualquier resolución sin depender del estado vivo del ERP.

La fase no sustituye la auditoría append-only existente. La organiza mediante
servicios de dominio/aplicación verificables y proyecciones deterministas.

## Alcance incluido

- modelo canónico de eventos y evidencias consultables;
- `AuditEngine` para verificar completitud, secuencia e integridad;
- `EvidenceRegistry` sobre referencias y hashes ya persistidos;
- `ResolutionTimeline` determinista;
- servicio de trazabilidad entre contexto, estrategia, plan, simulación,
  autorización, ejecución, compensación, resultado, auditoría y outbox;
- reconstrucción explicable del expediente y diagnóstico explícito de
  evidencia faltante o inconsistente;
- contratos de almacenamiento/consulta independientes del ERP;
- pruebas unitarias, persistentes, de arquitectura e integridad;
- migración únicamente si el análisis demuestra una carencia estructural que
  no pueda resolverse con el esquema general vigente.

## Fuera de alcance

- API institucional o pública;
- frontend, timeline visual o pantallas operativas;
- gateways e integraciones específicas del ERP;
- workers, colas, publicación automática o procesamiento distribuido;
- recuperación, retries, conciliación o compensación automática;
- analítica predictiva, métricas de negocio, recomendaciones o aprendizaje;
- retención, archivado externo, firma externa o exportación regulatoria;
- rediseño de identidad, políticas o Lifecycle;
- modificación de semántica de ejecución o compensación aprobada.

## Entregables esperados

1. modelo de dominio de auditoría/evidencia y taxonomía estable;
2. contratos explícitos de registro, consulta, verificación y reconstrucción;
3. `AuditEngine`, `EvidenceRegistry`, `ResolutionTimeline` y servicio de
   trazabilidad;
4. adaptadores persistentes generales, si son necesarios;
5. diagnóstico de integridad reproducible con errores de dominio;
6. pruebas de reconstrucción completa desde Fases 1 a 6;
7. pruebas de evidencia faltante, ajena, alterada o fuera de secuencia;
8. documentación arquitectónica y cierre técnico;
9. validación integral y commit exclusivo.

## Invariantes heredadas de las Fases 1 a 6

- separación Dominio / Aplicación / Infraestructura;
- núcleo independiente de FastAPI, frontend y módulos propietarios;
- Lifecycle como única autoridad del estado raíz;
- snapshots, versiones y hashes exactos sin reinterpretación histórica;
- evidencia perteneciente a otra resolución nunca se mezcla;
- identidad, autorización y segregación continúan explícitas;
- auditoría y planes/evidencias históricas permanecen append-only;
- idempotencia, locks, checkpoints y outbox conservan sus contratos;
- ejecución y compensación no se reinvocan por una consulta o reconstrucción;
- ninguna proyección de auditoría se convierte en nueva fuente de verdad;
- reconstrucción determinista desde el expediente persistido;
- extensibilidad por contratos y definiciones, no por condicionales del ERP.

## Consistencia documental verificada

- `12_ROADMAP.md` define Fase 7 como **Auditoría y Evidencia**.
- `13_IMPLEMENTATION_MATRIX.md` fue alineada con ese nombre; tras el dictamen
  de apertura registra la implementación como `EN REVISIÓN`.
- Las Fases 2, 3, 4, 5 y 6 ya producen auditoría/evidencia base. Fase 7 debe
  formalizar verificación, correlación, timeline y consultabilidad; no duplicar
  tablas o eventos existentes.
- API pública corresponde a una fase posterior del roadmap; UC-001 y gateways
  concretos corresponden a Integración con ERP MYC, también posterior.
- La autorización expresa fue recibida antes de escribir código de Fase 7.

## Gate propuesto

La fase podrá cerrarse sólo cuando un expediente completo pueda reconstruirse
y verificarse de extremo a extremo, con timeline estable, correlaciones exactas
y diagnósticos explícitos ante evidencia faltante o inconsistente, sin consultar
tablas vivas de módulos propietarios.

## Estado de control

```text
FASE 7
EN REVISIÓN
IMPLEMENTACIÓN: 20_AUDIT_EVIDENCE.md
```
