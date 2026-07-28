> Estado: VIGENTE — IMPLEMENTADO
>
> Fase: 11 — Motor Distribuido
>
> Fecha: 2026-07-28

# Runtime distribuido del Motor de Resoluciones

## Frontera

La distribución envuelve la invocación de los servicios canónicos sin cambiar
su semántica:

```text
productor interno
→ DistributedDispatcher
→ resolution_work_items
→ worker pull
→ handler registrado
→ Executor / Compensation / Outbox vigentes
→ resultado durable + evento operacional
```

El payload durable transporta referencias e intención, pero el handler
registrado sigue siendo el único adaptador autorizado para reconstruir el
comando interno y llamar al servicio canónico. La cola no decide permisos,
estados, estrategias, acciones ni compensaciones.

## Modelo persistente

### `resolution_worker_nodes`

Conserva identidad de nodo y de instancia de proceso, capacidad, estado
`active|draining|offline`, inicio, último heartbeat y expiración. Un `node_id`
vivo no puede ser tomado por otro `instance_id`; después de expirar puede
registrarse una nueva instancia.

### `resolution_work_items`

Es la proyección mutable mínima de despacho. Conserva clave única, resolución,
organización, tipo controlado, payload/hash, correlación, prioridad,
disponibilidad, intentos, política de retry, propietario, token, versión y
expiración del lease, inicio posible del efecto y cierre.

La clave `work_key` es idempotente: un replay con el mismo hash devuelve el
mismo trabajo; una colisión se rechaza.

### `resolution_work_events`

Registra de forma append-only y secuencial:

- alta;
- reclamación;
- inicio posible de efecto;
- retry programado;
- éxito o fallo;
- bloqueo incierto;
- recuperación/reencolado.

Cada evento liga trabajo, resolución, intento, nodo, versión de lease,
correlación, instante, payload y hash canónico. En PostgreSQL el trigger
`trg_resolution_work_events_immutable` rechaza `UPDATE` y `DELETE`.

## Reclamación y balanceo

Cada nodo usa pull hasta su `capacity`. PostgreSQL selecciona por:

1. `priority DESC`;
2. `available_at ASC`;
3. `id ASC`.

La selección usa `FOR UPDATE SKIP LOCKED`. Además excluye cualquier trabajo cuya
resolución tenga otro claim y el índice parcial único
`uq_resolution_work_items_claimed_resolution` cierra en base la carrera entre
snapshots concurrentes. Agregar nodos aumenta consumidores sin particionar ni
reinterpretar el historial; la cola común distribuye carga por capacidad
disponible.

## Leases y fencing

Cada claim asigna `node_id`, token opaco, `lease_version + 1` y expiración.
Renovar, iniciar efecto, completar o fallar exige coincidencia exacta de:

- ID del trabajo;
- estado `claimed`;
- nodo;
- token;
- versión;
- vigencia temporal.

El worker mantiene en segundo plano el lease del trabajo y el heartbeat del
nodo mientras opera. El Executor y Compensation Executor conservan además sus
locks internos: la cola no los sustituye.

## Recuperación

El recovery marca nodos vencidos como `offline` y reclama únicamente trabajos
con lease expirado:

- sin `effect_started_at`: vuelve a `retry_wait` si conserva intentos;
- con `effect_started_at`: pasa a `blocked` por incertidumbre;
- sin intentos: termina `failed`.

El propietario anterior queda cercado por token/versión y no puede confirmar
un resultado tardío.

## Reintentos

Un handler puede declarar `RetryableDistributedWorkError` sólo si comprobó que
no hubo efecto. El siguiente instante es:

```text
failed_at + min(base_delay × 2^(attempt_count - 1), maximum_delay)
```

No existe jitter, azar ni reevaluación adaptativa. Excepciones no clasificadas
o `DistributedWorkUncertainError` bloquean como inciertas. La idempotencia del
servicio canónico continúa siendo obligatoria aunque la cola impida duplicados.

## Observabilidad

`snapshot()` agrega por estado de trabajo y nodo, opcionalmente aislado por
organización para trabajos. La secuencia de eventos permite conocer nodo,
intento, tiempos, recuperación y desenlace sin usar memoria del proceso.

## Operación controlada

El supervisor de proceso:

1. construye stores y handlers;
2. registra un `node_id`/`instance_id` únicos;
3. invoca `run_once()` dentro de su ciclo operativo;
4. solicita `drain()` antes de retirar el nodo;
5. ejecuta periódicamente `DistributedRecoveryService.recover()`.

La construcción concreta de handlers permanece en composición interna. No se
publica un endpoint, contrato SDK ni selección manual de implementación.

## Límites

- no confirma alta disponibilidad de la base de datos; ésta es responsabilidad
  de infraestructura PostgreSQL;
- no convierte el Motor en microservicio;
- no agrega scheduler de negocio;
- no reintenta un efecto incierto;
- no automatiza compensaciones;
- no incorpora Fase 12.
