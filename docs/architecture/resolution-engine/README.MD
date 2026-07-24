# Motor de Resoluciones

> Estado: ARQUITECTURA VIGENTE — FASE 0 EN REVISIÓN
>
> Fase vigente: Fase 0 — Preparación arquitectónica, cerrada técnicamente
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

La Fase 0 formalizó la arquitectura, su matriz de implementación y sus gates. No
incorporó modelos, APIs, ejecución, autorización ni cambios funcionales del ERP.
La Fase 1 permanece `NO INICIADA` hasta recibir aprobación expresa.
