> Estado: CIERRE TÉCNICO EN REVISIÓN
>
> Fecha: 2026-07-24
>
> Alcance: Fase 3 — Seguridad, identidad, gobierno y evidencia

# Cierre técnico de la Fase 3 del Motor de Resoluciones

## Resultado

La Fase 3 incorpora la capa central de seguridad y gobierno del Motor. Toda
decisión protegida parte de un actor autenticado, evalúa permisos y políticas
versionadas, aplica segregación configurable, valida la pertenencia exacta de la
evidencia y conserva concesiones o denegaciones como registros append-only. La
fase queda `EN REVISIÓN`; no se inicia Fase 4.

## Componentes incorporados

- valores inmutables de identidad, autenticación, permisos, recursos,
  solicitudes, resultados de política y decisiones;
- puertos `ActorContextProvider`, `SecurityResourceVerifier` y
  `SecurityEvidenceStore`;
- evaluador deny-by-default con prioridad de denegación explícita;
- políticas de permisos exactos, límite organizacional y segregación;
- `ResolutionAuthorizationService` sin lifecycle ni efectos de dominio;
- verificador y almacén SQLAlchemy limitados a persistencia del Motor;
- tabla `resolution_security_decisions` con referencias exactas y trigger
  append-only;
- migración reversible `b4c6d8e0f2a3`;
- separación obligatoria de access/refresh y cierre de roles solicitables desde
  registro público.

## Invariantes protegidas

- identidad activa y autenticación vigente antes de autorizar;
- ausencia de política o permiso equivale a denegación;
- una política restrictiva prevalece;
- el actor no atraviesa límites organizacionales;
- funciones incompatibles no se concentran cuando la regla aplica;
- plan, versión, hash, simulación, hash y solicitud pertenecen a una misma
  resolución;
- un intento con evidencia ajena o alterada se deniega y audita;
- concesiones y denegaciones conservan actor, política, condiciones, resultado,
  correlación y hash reproducible;
- el núcleo no depende de roles, usuarios, FastAPI, routers, schemas ni
  servicios propietarios.

## Contradicciones corregidas

1. El registro público aceptaba `role_names`, permitiendo solicitar autoridad.
   Se eliminó ese campo del contrato público y se prohibieron campos extra.
2. Las dependencias de usuario aceptaban cualquier JWT decodificable, incluido
   refresh. Access y refresh llevan tipos explícitos y sólo access autentica
   requests.
3. La persistencia de Fase 2 mantenía once FKs directas a `users.id` y nombres
   de rol. Se migraron a IDs canónicos de actor, funciones y snapshots mediante
   una revisión acotada.

No se corrigió autorización general de routers, portal de cliente, secreto JWT,
roles dinámicos ni deuda ajena a las dependencias directas de esta fase.

## Pruebas y validaciones

- 81 pruebas específicas del Motor correctas: identidad, permisos,
  deny-by-default, concesiones, denegaciones, límite organizacional, actor
  revocado, segregación, prioridad restrictiva, evidencia ajena, hashing,
  arquitectura, esquema y migraciones.
- Suite backend completa: 205 pruebas y 19 subpruebas correctas.
- Frontend: 11 pruebas correctas y build Vite correcto; conserva la advertencia
  preexistente por tamaño del chunk principal.
- Compilación Python: correcta para `app`, `tests` y scripts.
- PostgreSQL: upgrade, downgrade y nuevo upgrade correctos; evidencia de
  seguridad inmutable verificada con SQLSTATE `55000`.
- Alembic: único head/current `b4c6d8e0f2a3`; `alembic check` no propone
  operaciones del Motor y conserva la deriva histórica ajena `TD-021`.
- Inventario regenerado, rutas registradas existentes y `git diff --check`
  correcto.
- Respaldo SQL regenerado con `alembic_version = b4c6d8e0f2a3`.

## Migración

`b4c6d8e0f2a3` sucede a `9d3e5f7a1b2c`. Fue validada mediante upgrade,
downgrade completo a la revisión padre y nuevo upgrade a head. La tabla nueva
rechaza `UPDATE` y `DELETE` con SQLSTATE `55000`. `alembic check` conserva sólo
la deriva histórica ajena registrada como `TD-021`; no propone deriva del
Motor.

## Deuda no abordada

- autorización uniforme de routers y aislamiento del portal;
- secreto JWT de producción y gobierno general de sesiones;
- actor obligatorio en la excepción ETS;
- lifecycle, simulación real, revalidación, ejecución, API y workers;
- adaptador concreto entre roles/permisos ERP y `ActorContext`;
- políticas concretas de cada tipo de resolución.

## Archivos de implementación

- Núcleo/puertos: `domain/security.py`, `contracts/security.py`,
  `application/security.py` y sus APIs de paquete.
- Persistencia: modelos `core.py`, `planning.py`, `governance.py`,
  `execution.py`, `evidence.py`, repositorio y adaptador
  `infrastructure/security.py`.
- Integración indispensable: `core/security.py`, `schemas/auth.py` y
  `services/auth.py`.
- Esquema: migración `b4c6d8e0f2a3`.
- Pruebas: seguridad del Motor, arquitectura, esquema, migración y bloqueadores
  auth.
- Operación/documentación: respaldo SQL, matriz, contratos de arquitectura,
  canon de proyecto, inventario y este cierre.

## Condición para continuar

La Fase 3 queda `EN REVISIÓN`. La Fase 4 sólo puede iniciar después de la
aprobación expresa del commit exclusivo de esta fase.
