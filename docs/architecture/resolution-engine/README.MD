# Motor de Resoluciones

> Estado: ARQUITECTURA VIGENTE — FASE 8 EN REVISIÓN
>
> Próxima fase: Fase 9 no iniciada
>
> Autoridad de implementación: [`13_IMPLEMENTATION_MATRIX.md`](13_IMPLEMENTATION_MATRIX.md)

Esta carpeta contiene la especificación normativa del Motor de Resoluciones del
ERP MYC. El Motor coordina intervenciones extraordinarias sin apropiarse de los
dominios, sus reglas, sus folios ni sus documentos institucionales.

## Orden de lectura obligatorio

1. [`01_VISION.md`](01_VISION.md)
2. [`02_FILOSOFIA.md`](02_FILOSOFIA.md)
3. [`03_PRINCIPIOS.md`](03_PRINCIPIOS.md)
4. [`04_MODELO_CONCEPTUAL.md`](04_MODELO_CONCEPTUAL.md)
5. [`05_ARQUITECTURA.md`](05_ARQUITECTURA.md)
6. [`06_COMPONENTES.md`](06_COMPONENTES.md)
7. [`07_MODELO_DE_DATOS.md`](07_MODELO_DE_DATOS.md)
8. [`08_FLUJOS.md`](08_FLUJOS.md)
9. [`09_API.md`](09_API.md)
10. [`10_CASOS_DE_USO.md`](10_CASOS_DE_USO.md)
11. [`11_MODELO_SEGURIDAD.md`](11_MODELO_SEGURIDAD.md)
12. [`12_ROADMAP.md`](12_ROADMAP.md)
13. [`13_IMPLEMENTATION_MATRIX.md`](13_IMPLEMENTATION_MATRIX.md)
14. [`14_PERSISTENCE_SCHEMA.md`](14_PERSISTENCE_SCHEMA.md)
15. [`15_SECURITY_GOVERNANCE.md`](15_SECURITY_GOVERNANCE.md)
16. [`16_LIFECYCLE_ORCHESTRATION.md`](16_LIFECYCLE_ORCHESTRATION.md)
17. [`17_EXECUTION_RUNTIME.md`](17_EXECUTION_RUNTIME.md)
18. [`18_COMPENSATION_ENGINE.md`](18_COMPENSATION_ENGINE.md)
19. [`19_PHASE_7_OPENING.md`](19_PHASE_7_OPENING.md)
20. [`20_AUDIT_EVIDENCE.md`](20_AUDIT_EVIDENCE.md)
21. [`21_PHASE_8_OPENING.md`](21_PHASE_8_OPENING.md)
22. [`22_INTEGRAL_SECURITY.md`](22_INTEGRAL_SECURITY.md)

## Regla de precedencia

Los documentos `01` a `11` definen los principios, contratos e invariantes que
la implementación no puede simplificar. `12_ROADMAP.md` conserva la evolución
conceptual de largo plazo. `13_IMPLEMENTATION_MATRIX.md` define el orden técnico
aprobado para este repositorio y resuelve cuándo debe incorporarse cada
capacidad.

La matriz no puede debilitar la arquitectura normativa. Cuando el Roadmap
conceptual pospone un control que otro documento exige por diseño, prevalece la
dependencia de seguridad e integridad más restrictiva.

## Gobierno de las fases

- Se implementa una sola fase a la vez.
- Sólo se corrige deuda que contradiga directamente la fase vigente.
- No se adelantan componentes de fases posteriores.
- Cada fase termina con pruebas completas, validación de integración,
  documentación, inventario y un commit descriptivo.
- Después del commit, el trabajo se detiene hasta recibir aprobación expresa
  para iniciar la siguiente fase.

## Estado actual

Las Fases 0, 1 y 2 fueron aprobadas. La Fase 1 implementó exclusivamente organización de
paquetes, contratos tipados, catálogos controlados, errores, serialización y
hashing canónicos, reloj, identificadores, `ResolutionRegistry` y pruebas
arquitectónicas. Su cierre está en
[`../../closures/RESOLUTION_ENGINE_PHASE_1.md`](../../closures/RESOLUTION_ENGINE_PHASE_1.md).

La Fase 2 quedó implementada y aprobada. Incorpora modelos
persistentes, restricciones, índices, repositorio de reconstrucción, migración
reversible, inmutabilidad y outbox estructural. Su contrato implementado está
en [`14_PERSISTENCE_SCHEMA.md`](14_PERSISTENCE_SCHEMA.md) y el cierre técnico
en
[`../../closures/RESOLUTION_ENGINE_PHASE_2.md`](../../closures/RESOLUTION_ENGINE_PHASE_2.md).

La Fase 3 quedó implementada y aprobada. Incorpora identidad canónica,
contexto de autenticación, permisos atómicos, políticas deterministas,
deny-by-default, segregación, autorización base y evidencia append-only de
concesiones y denegaciones. Su contrato está en
[`15_SECURITY_GOVERNANCE.md`](15_SECURITY_GOVERNANCE.md) y su cierre en
[`../../closures/RESOLUTION_ENGINE_PHASE_3.md`](../../closures/RESOLUTION_ENGINE_PHASE_3.md).

La Fase 4 quedó implementada y aprobada. Incorpora creación,
Lifecycle, máquina de estados, invariantes sobre evidencia reconstruida,
auditoría de transiciones, control optimista y orquestación versionada de
componentes puros hasta revalidación. Su contrato está en
[`16_LIFECYCLE_ORCHESTRATION.md`](16_LIFECYCLE_ORCHESTRATION.md) y su cierre en
[`../../closures/RESOLUTION_ENGINE_PHASE_4.md`](../../closures/RESOLUTION_ENGINE_PHASE_4.md).

La Fase 5 quedó implementada y aprobada. Incorpora Engine y Executor
de ejecución, Action Runner, contratos de adaptadores, checkpoints durables,
idempotencia, locks, efectos/resultado, auditoría y publicación explícita de
outbox. Su contrato está en
[`17_EXECUTION_RUNTIME.md`](17_EXECUTION_RUNTIME.md) y su cierre en
[`../../closures/RESOLUTION_ENGINE_PHASE_5.md`](../../closures/RESOLUTION_ENGINE_PHASE_5.md).

La Fase 6 quedó implementada y aprobada mediante `74a3de5` y `e1d373e`.
Incorpora definición
declarativa, planificación total/parcial, relación exacta con efectos
confirmados, ejecución compensatoria síncrona, Lifecycle, checkpoints,
idempotencia, lock, auditoría y outbox. Su contrato está en
[`18_COMPENSATION_ENGINE.md`](18_COMPENSATION_ENGINE.md) y su cierre en
[`../../closures/RESOLUTION_ENGINE_PHASE_6.md`](../../closures/RESOLUTION_ENGINE_PHASE_6.md).

La Fase 7 fue implementada y aprobada mediante `4ae25ea` y `768ef6e`. Incorpora un modelo puro de
evidencia, `AuditEngine`, `EvidenceRegistry`, `ResolutionTimeline`, consultas
autorizadas, correlación y un adaptador SQL read-only. Reutiliza el esquema
general y no requiere migración. Su contrato está en
[`20_AUDIT_EVIDENCE.md`](20_AUDIT_EVIDENCE.md) y su cierre en
[`../../closures/RESOLUTION_ENGINE_PHASE_7.md`](../../closures/RESOLUTION_ENGINE_PHASE_7.md).

La Fase 8 está implementada y `EN REVISIÓN`. Consolida el catálogo de
controles dentro del evaluador de Fase 3 y exige decisiones persistidas exactas
en Lifecycle, ejecución, compensación, consultas de auditoría y publicación de
outbox. Su apertura está en
[`21_PHASE_8_OPENING.md`](21_PHASE_8_OPENING.md), su contrato en
[`22_INTEGRAL_SECURITY.md`](22_INTEGRAL_SECURITY.md) y su cierre en
[`../../closures/RESOLUTION_ENGINE_PHASE_8.md`](../../closures/RESOLUTION_ENGINE_PHASE_8.md).

API, gateways concretos, integraciones propietarias, workers, schedulers,
recuperación, reintentos, conciliación y compensación automática permanecen
fuera de alcance. La Fase 9 no fue iniciada.
