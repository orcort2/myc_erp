# Motor de Resoluciones

> Estado: ARQUITECTURA VIGENTE — FASE 4 EN REVISIÓN
>
> Fase vigente: Fase 4 — Lifecycle y orquestación interna, implementación cerrada
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

La Fase 4 quedó implementada y está `EN REVISIÓN`. Incorpora creación,
Lifecycle, máquina de estados, invariantes sobre evidencia reconstruida,
auditoría de transiciones, control optimista y orquestación versionada de
componentes puros hasta revalidación. Su contrato está en
[`16_LIFECYCLE_ORCHESTRATION.md`](16_LIFECYCLE_ORCHESTRATION.md) y su cierre en
[`../../closures/RESOLUTION_ENGINE_PHASE_4.md`](../../closures/RESOLUTION_ENGINE_PHASE_4.md).

Ejecución, gateways, API, publicación outbox, workers, reintentos y
compensaciones permanecen fuera de alcance. La Fase 5 no puede iniciar sin
aprobación expresa.
