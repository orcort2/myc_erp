> Estado: ACTIVA
>
> Fecha de autorización: 2026-07-28
>
> Autoridad: apertura oficial expresa posterior a la aprobación de Fase 8

# Apertura oficial — Fase 9

## Nombre oficial

**Fase 9 — Integración con ERP MYC**

## Objetivo

Integrar progresivamente el Motor de Resoluciones con los dominios del ERP MYC
para que las decisiones institucionales se coordinen mediante contratos
unificados, consistentes, seguros y auditables, sin transferir al Motor la
propiedad de los datos ni la lógica de negocio de cada módulo.

## Estado de entrada

Las Fases 0 a 8 están aprobadas. La Fase 8 queda cerrada mediante los commits:

- `73e437d` — `feat(resolution-engine): complete phase 8 security`;
- `661f43a5cbba9070b1f02babd9ebbd5149f62b2b` —
  `fix(resolution-engine): bind security decisions to operations`, corrección
  anti-replay reconocida por la aprobación formal bajo la descripción
  `fix(resolution-engine): prevent security decision replay`.

La deuda `TD-023` permanece externa al Motor y no forma parte de esta apertura.

## Alcance autorizado

Únicamente pueden incorporarse, de forma gradual y por caso vertical:

- definiciones verticales versionadas registradas en `ResolutionRegistry`;
- UC-001 y los casos siguientes que sean abiertos expresamente dentro de esta
  fase;
- Fact Providers read-only para construir snapshots canónicos;
- Domain Gateways concretos que invoquen servicios canónicos del módulo
  propietario;
- contratos de integración entre el Motor y dominios participantes;
- coordinación de resoluciones de uno o varios dominios;
- trazabilidad de módulos, responsables, dependencias, evidencia y resultado;
- pruebas de contrato, integración, seguridad, idempotencia, compensación y
  auditoría;
- documentación e inventario.

Esta apertura no selecciona todavía el primer caso vertical ni autoriza una
implementación genérica de todos los módulos. Antes de modificar código para un
caso deberá documentarse su dominio participante, flujo actual, servicio
canónico, actor obligatorio, definición versionada, providers, gateways,
acciones, compensaciones, permisos, evidencia y gate verificable.

## Integración progresiva

Los dominios candidatos del roadmap son Clientes, Cotizaciones, Agenda, ETS,
Equipos, Hojas de Campo, Certificados, Facturación, Pagos, Control Documental,
Inventario, Compras y Recursos Humanos. Su enumeración no los declara
implementados ni autoriza integrarlos simultáneamente.

Cada incorporación deberá completar:

1. análisis verificable del dominio y su flujo actual;
2. definición de contratos y ownership;
3. implementación aislada del caso;
4. validación funcional, transaccional y de seguridad;
5. auditoría y reconstrucción;
6. estabilización antes de abrir el caso siguiente.

## Ownership y límites

- Cada módulo conserva autoridad exclusiva sobre sus datos, reglas, folios,
  documentos y estados propios.
- El Motor puede solicitar información, construir resoluciones, coordinar
  acciones y devolver resultados.
- Un Fact Provider sólo consulta mediante servicios canónicos read-only.
- Un Domain Gateway sólo ejecuta mediante el servicio canónico del módulo
  propietario.
- El Motor no importa ORM, routers, modelos persistentes ni detalles internos
  de un dominio propietario.
- No se duplican reglas de negocio, payloads propietarios ni máquinas de
  estado.

## Bloqueadores corregibles

Sólo podrá corregirse deuda que impida directamente integrar el caso vertical
abierto. La matriz reconoce, para el caso que corresponda:

- actor opcional;
- lógica o mutaciones duplicadas;
- solicitud que ejecuta inmediatamente sin separar solicitud, autorización y
  ejecución;
- superficies propietarias paralelas que impidan identificar un único mutador
  canónico.

La corrección deberá limitarse al servicio o contrato canónico consumido por el
caso. La deuda general del ERP continúa fuera de alcance.

## Invariantes obligatorias

- Lifecycle continúa como única autoridad de estado del Motor.
- Se preserva arquitectura DDD y separación Dominio / Aplicación /
  Infraestructura.
- Las consultas y Fact Providers permanecen read-only y sin efectos laterales.
- Las mutaciones ocurren exclusivamente mediante Domain Gateways explícitos.
- Persistencia, seguridad, auditoría, idempotencia, locks, evidencia,
  compensación, reconstrucción y consistencia transaccional conservan las
  garantías de las Fases 1 a 8.
- No aparecen evaluadores paralelos, accesos directos a tablas propietarias ni
  estados alternos del Motor.
- La compatibilidad del Motor general no depende de ningún caso vertical.

## Fuera de alcance

No se implementan durante esta fase:

- API pública o SDK;
- nuevos routers o transporte público del Motor;
- workers, schedulers, retries automáticos o procesamiento distribuido;
- integraciones externas;
- automatizaciones generales o UI ajena al caso expresamente abierto;
- inteligencia artificial, aprendizaje automático o proveedores de IA.

La IA no es dependencia arquitectónica ni operativa del ERP o del Motor. Su
posible incorporación futura permanece opcional y requerirá una decisión y
apertura independientes; el Motor seguirá funcionando completamente mediante
código determinista, reglas, políticas, permisos, validaciones, Lifecycle,
simulación, ejecución, compensación y auditoría.

## Gate por caso vertical

Cada caso deberá demostrar:

- definición versionada sin condicionales particulares dentro del núcleo;
- snapshots canónicos mediante providers read-only;
- acciones únicamente mediante gateways y servicios propietarios canónicos;
- actor, autorización y decisión de seguridad exactos;
- idempotencia, locks y consistencia transaccional;
- compensación explícita cuando el efecto sea reversible;
- evidencia append-only y reconstrucción determinista;
- ausencia de acceso ORM directo o mutación desde consultas;
- pruebas del Motor, del dominio participante y de integración;
- documentación e inventario sincronizados;
- commit exclusivo.

## Validaciones de fase

Toda entrega deberá ejecutar, según el caso abierto, suite específica de Fase
9, suite completa del Motor, backend completo, frontend, build, compilación
Python, validaciones arquitectónicas, `alembic current`, `alembic heads`,
`alembic check`, inventario, documentación sincronizada y commit exclusivo.

## Restricción

La Fase 10 — SDK y API Pública permaneció `NO INICIADA` durante la
implementación y revisión de esta fase. El dictamen final satisfizo esta
restricción al aprobar Fase 9 y autorizar su apertura posterior.

## Primer caso autorizado y resultado

El primer y único dominio autorizado es **CERTIFICADOS**. Se seleccionó
`certificate.resolve_incorrect_release` y su implementación queda
**APROBADA** conforme al contrato
[`24_PHASE_9_CERTIFICATES_INTEGRATION.md`](24_PHASE_9_CERTIFICATES_INTEGRATION.md).

No se inició otro dominio. El dictamen final aprobó Fase 9 mediante `5abfe2d` y
`901bd85` y autorizó la apertura documental de Fase 10.
