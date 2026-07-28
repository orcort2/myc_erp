> Estado: IMPLEMENTADO — APROBADO
>
> Fecha: 2026-07-28
>
> Fase: 9 — Integración con ERP MYC
>
> Primer dominio: Certificados

# Integración vertical de Certificados

## Caso seleccionado

El primer y único caso vertical abierto es:

```text
certificate.resolve_incorrect_release
```

Corresponde a UC-037 del catálogo oficial. Ningún otro dominio o caso puede
iniciarse antes de concluir, validar y revisar esta integración.

## Problema institucional

Un certificado fue liberado y quedó visible para el cliente sin cumplir las
condiciones institucionales. La evidencia histórica de la liberación no puede
eliminarse ni reescribirse para simular que nunca ocurrió.

La resolución retira exclusivamente el acceso futuro al documento, conserva
estado, fechas, actores, PDF autenticado, auditoría y evidencia de la liberación
original, y deja trazada la intervención extraordinaria en el expediente
general del Motor.

## Límites del dominio

Certificados conserva ownership sobre:

- estado, folio y visibilidad del certificado;
- PDF autenticado y metadatos documentales;
- validación de precondiciones propietarias;
- mutación transaccional;
- auditoría operativa del certificado;
- idempotencia de la operación propietaria.

El Motor conserva autoridad exclusiva sobre:

- Lifecycle de la resolución;
- contexto, análisis, estrategia, plan y simulación;
- autorización, revalidación y seguridad integral;
- ejecución, locks, checkpoints y resultado;
- evidencia, auditoría y reconstrucción de la resolución;
- preparación y ejecución de compensación.

El Motor no importa ORM de Certificados. El dominio no modifica estados del
Motor.

## Contratos

### Fact Provider

El provider es read-only y obtiene del servicio canónico únicamente:

- ID y folio;
- estado vigente;
- visibilidad al cliente;
- existencia de referencia al PDF autenticado;
- actor y fecha de liberación;
- vigencia del registro;
- versión temporal `updated_at`.

No consulta Facturación, Pagos, ETS, Hojas de Campo ni Clientes.

### Definición vertical

- Tipo: `certificate.resolve_incorrect_release`.
- Versión inicial: `1.0`.
- Subject: `certificate`.
- Estrategia inicial única: `withdraw_client_access`.
- Operación propietaria:
  `certificates.withdraw_incorrect_release`.
- Compensación:
  `certificates.restore_incorrect_release_visibility`.

La definición se registra fuera del núcleo. No agrega condicionales por tipo al
`ResolutionRegistry`, Lifecycle, Executor ni Compensation Engine.

### Domain Gateway

El gateway recibe una acción ya autorizada por el Motor y delega en el servicio
canónico de Certificados. No contiene reglas de negocio ni accede directamente
al ORM.

El servicio canónico bloquea el certificado, valida estado liberado y
visibilidad, conserva el estado histórico y cambia únicamente
`client_visible: true → false`. La operación y su auditoría se confirman en la
misma transacción.

## Idempotencia propietaria

Cada invocación usa la clave entregada por el Motor. Certificados conserva un
registro append-only con:

- acción;
- certificado;
- clave idempotente única;
- hash de intención;
- actor y correlación;
- snapshots anterior y posterior;
- resultado;
- operación fuente cuando se trata de compensación.

La misma clave y el mismo hash devuelven el resultado persistido sin repetir la
mutación. Este replay se resuelve antes de consultar, bloquear o validar el
estado actual del certificado: continúa disponible aunque después cambien el
estado, la visibilidad o la vigencia del registro. Además del hash deben
coincidir operación y payload canónico; cualquier colisión se rechaza.

Para una clave nueva se consulta inicialmente la ausencia de resultado, se
bloquea el certificado y se repite la consulta dentro de la transacción. La
unicidad persistente resuelve carreras entre certificados distintos; si otra
transacción confirma primero, el perdedor revierte íntegramente y recupera
únicamente ese resultado exacto. Dos operaciones distintas no pueden retirar
dos veces la misma visibilidad.

## Snapshot confirmado

El snapshot posterior nunca se toma sólo desde el objeto mutado en memoria. El
servicio aplica el cambio, ejecuta `flush`, refresca la fila desde la base y
después construye `after_snapshot`, `result_payload`, auditoría y efectos.
Así `client_visible`, `updated_at`, estado y cualquier valor ORM/BD generado
coinciden con la fila confirmada. Ejecución y compensación siguen el mismo
protocolo y todo permanece dentro de una única transacción.

## Compensación

La acción es compensable únicamente mientras:

- la operación fuente exista y esté confirmada;
- el certificado conserve el mismo estado histórico liberado;
- continúe oculto;
- no exista deriva propietaria incompatible.

La compensación restaura la visibilidad anterior, no elimina la resolución ni
la auditoría y agrega su propia operación append-only. No altera la fecha,
actor o estado de liberación original.

## Seguridad y autorización

El caso reutiliza íntegramente las decisiones del Motor:

- creación exacta;
- transiciones Lifecycle exactas;
- autorización del plan;
- revalidación;
- ejecución `single_operation`;
- compensación `single_operation`;
- auditoría read-only.

El plan requiere capacidades institucionales de liberación y aprobación de
Certificados. Ningún adaptador crea un evaluador paralelo.

## Flujo completo

```text
solicitud exacta
→ draft
→ snapshot read-only del certificado
→ análisis
→ estrategia withdraw_client_access
→ plan compensable
→ simulación sin efectos
→ autorización
→ revalidación contra snapshot fresco
→ ready_for_execution
→ ejecución mediante ActionRunner y Domain Gateway
→ operación canónica transaccional
→ completed
→ auditoría/reconstrucción

[si se autoriza compensación]
→ compensating
→ restauración canónica idempotente de visibilidad
→ compensated
```

Lifecycle sigue siendo la única autoridad del estado de la resolución. El
servicio de Certificados sigue siendo la única autoridad del estado y los datos
del certificado.

## Gate de salida

La integración deberá demostrar:

- registro versionado sin cambios al núcleo;
- provider sin efectos y sin ORM expuesto;
- componentes puros y deterministas;
- gateway sin lógica de negocio;
- mutación propietaria transaccional e idempotente;
- estado de liberación histórica preservado;
- ejecución y replay exactos;
- compensación y replay compensatorio exactos;
- evidencia operativa y del Motor;
- denegación ante deriva de contexto;
- ausencia de imports circulares, routers, API pública, workers, IA u otros
  dominios;
- suites del caso, Certificados, Motor y backend;
- documentación, inventario y commit exclusivos.

## Resultado verificable

El primer caso vertical quedó implementado y **APROBADO**. La
entrega registra la definición `1.0`, siete componentes deterministas, provider
read-only, gateway de ejecución, gateway de compensación, servicio canónico,
evidencia propietaria append-only y migración reversible
`f9c1d3e5a7b9`.

La suite específica valida el ciclo puro, bloqueo y deriva, atomicidad,
idempotencia histórica, colisiones, concurrencia, rollback, snapshot pos-flush,
ejecución real protegida por la seguridad de Fase 8, compensación y límites
arquitectónicos. No se inició otro caso, dominio o fase.

La aprobación formal conserva como cierre `5abfe2d` y `901bd85`. La apertura
posterior de Fase 10 no amplía ni modifica este vertical.
