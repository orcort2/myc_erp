> Estado: VIGENTE
>
> Tipo: Contrato técnico implementado
>
> Autoridad: Seguridad y gobierno de la Fase 3
>
> Complementa a: `11_MODELO_SEGURIDAD.md`, `13_IMPLEMENTATION_MATRIX.md` y
> `14_PERSISTENCE_SCHEMA.md`
>
> Corte verificado: 2026-07-24

# Seguridad y gobierno del Motor de Resoluciones

## Propósito

Este contrato describe la capa implementada en la Fase 3. Su responsabilidad es
convertir una identidad autenticada, permisos atómicos y contexto verificable en
una decisión explícita, determinista, reproducible y auditable. No implementa
lifecycle, construcción de planes, simulación real, ejecución, API, workers ni
gateways de dominio.

## Identidad canónica

`ActorContext` separa tres conceptos:

1. `ActorIdentity`: identificador estable, tipo de actor, principal,
   organización, estado y atributos organizacionales.
2. `AuthenticationContext`: método, sesión, nivel de confianza, origen,
   correlación, vigencia y delegación.
3. `PermissionGrant`: capacidad atómica exacta, vigencia, alcance opcional de
   recurso y restricciones declaradas por el proveedor de autoridad.

El Motor no importa `User`, `Role`, routers, schemas ni servicios del ERP. El
puerto `ActorContextProvider` permite que una integración futura traduzca la
identidad autenticada del host sin introducir roles o tablas propietarias en el
nucleo.

Los tokens del ERP distinguen ahora obligatoriamente `token_type=access` y
`token_type=refresh`; las dependencias de usuario rechazan un refresh como
bearer. El registro público tampoco acepta `role_names`: el bootstrap conserva
su regla existente para el primer administrador y los registros posteriores
reciben el rol base decidido por backend.

## Evaluación de políticas

`SecurityPolicyEvaluator` recibe políticas versionadas e independientes. Para
las mismas entradas y el mismo instante produce el mismo resultado y hash de
evidencia. Sus reglas de composición son:

- ninguna política aplicable produce `DENIED`;
- cualquier denegación explícita prevalece;
- un actor inactivo o una autenticación vencida producen denegación;
- sólo la concesión de todas las políticas aplicables produce `ALLOWED`.

Las políticas base implementadas son:

| Política | Versión | Garantía |
| --- | --- | --- |
| `security.require_permissions` | `1.0` | Exige permisos atómicos exactos, vigentes y aplicables al recurso; no hay wildcards ni herencia implícita. |
| `security.same_organization` | `1.0` | Impide que un actor opere evidencia de otra organización. |
| `security.segregation_of_duties` | `1.0` | Evalúa incompatibilidades configurables entre la función actual y participantes históricos. |

Las políticas no conocen tipos concretos de resolución ni roles del ERP. Una
política nueva se agrega como componente reemplazable sin modificar el
evaluador.

## Segregación de funciones

`SegregationRule` vincula una acción con la función actual y las funciones
históricas incompatibles. La política compara el actor estable, no nombres ni
roles visibles. Esto permite exigir, entre otras combinaciones configurables,
que quien solicitó o construyó un plan no lo autorice.

La excepción a una incompatibilidad no es implícita. Deberá expresarse en una
política versionada posterior y producir su propia evidencia; esta fase no
incorpora excepciones concretas ni delegaciones del ERP.

## Autorización de resoluciones y planes

`ResolutionAuthorizationService` ejecuta en este orden:

1. verifica mediante `SecurityResourceVerifier` que plan, versión, hash,
   simulación, hash y solicitud de autorización pertenezcan a la misma
   resolución;
2. ante una discordancia, deniega antes de evaluar permisos;
3. evalúa las políticas aplicables;
4. entrega la decisión tipada;
5. solicita a `SecurityEvidenceStore` conservar la evidencia en la misma unidad
   de trabajo del consumidor.

El servicio no cambia estados, no crea planes, no simula y no ejecuta. El flujo
completo de solicitud/aprobaciones/lifecycle corresponde a la Fase 4.

## Evidencia persistente

`resolution_security_decisions` conserva tanto concesiones como denegaciones:

- actor, tipo, organización y snapshot de identidad;
- contexto de autenticación y correlación;
- acción, recurso y permisos requeridos;
- políticas y versiones evaluadas, condiciones y resultado;
- códigos de razón;
- resolución y, cuando aplica, plan/versión/hash, simulación/hash y solicitud
  exactos;
- instante de evaluación y hash canónico de la evidencia.

Claves foráneas compuestas impiden vincular evidencia válida con un plan,
simulación o solicitud de otra resolución. Un intento inconsistente se conserva
como denegación sin aceptar esas referencias como válidas; el recurso intentado
queda dentro del snapshot de contexto.

PostgreSQL protege la tabla con el trigger append-only compartido del Motor. Las
once referencias históricas a `users.id` fueron migradas a identificadores
canónicos `*_actor_id`, eliminando el acoplamiento del expediente con el modelo
de usuarios del ERP. Los nombres de rol almacenados por el Motor se reemplazaron
por funciones o snapshots de autoridad.

## Contratos para integraciones futuras

- `ActorContextProvider`: autenticación/autoridad del host → `ActorContext`.
- `SecurityResourceVerifier`: evidencia señalada → códigos de inconsistencia.
- `SecurityEvidenceStore`: decisión tipada → registro append-only.

El adaptador SQLAlchemy implementado sólo conoce tablas del Motor. La futura
integración con permisos del ERP deberá vivir fuera del núcleo y no podrá
transformar roles en condicionales distribuidos.

## Invariantes

- ninguna operación protegida se autoriza sin identidad activa y autenticación
  vigente;
- ausencia de política, permiso o evidencia consistente significa denegación;
- una denegación explícita prevalece;
- las políticas se identifican y versionan;
- la segregación puede denegar aun cuando existan todos los permisos;
- autorización de plan/simulación siempre señala versiones y hashes exactos;
- evidencia de otra resolución no puede autorizarse;
- concesiones y denegaciones son reproducibles, correlacionables e inmutables;
- la seguridad del backend no depende del frontend.

## Evolución

Fases posteriores pueden registrar políticas concretas, adaptar la identidad del
ERP y consumir el servicio desde lifecycle o API. No deben crear evaluadores
paralelos, permisos codificados en servicios, booleanos de aprobación ni
accesos directos desde el Motor a `User`, `Role` o módulos propietarios.

Desde Fase 6, preparar o ejecutar una compensación consume una decisión
`resolution.compensate` `allowed` vinculada a la resolución, ejecución fuente,
organización y actor exactos. La evidencia se vuelve a comprobar antes de
resolver idempotencia o replay; conocer una clave no entrega resultados a otro
actor ni sustituye autorización.
