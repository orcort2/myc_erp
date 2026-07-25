> Estado: CIERRE TÉCNICO EN REVISIÓN
>
> Fecha: 2026-07-24
>
> Alcance: Fase 2 — Persistencia completa

# Cierre técnico de la Fase 2 del Motor de Resoluciones

## Resultado

La Fase 2 incorpora el modelo persistente general del Motor, su repositorio de
reconstrucción, restricciones, índices, inmutabilidad en PostgreSQL, outbox
estructural y una migración reversible. El Motor todavía no toma decisiones ni
produce efectos.

## Componentes entregados

- 21 modelos SQLAlchemy organizados por identidad, planeación, gobierno,
  ejecución futura y evidencia.
- Identidad genérica del sujeto, definiciones versionadas, snapshots con hash,
  relaciones críticas normalizadas e integridad referencial compuesta.
- `ResolutionRepository` con consultas deterministas y reconstrucción completa
  del expediente.
- Migración `9d3e5f7a1b2c`, sucesora de `8c2d4e6f7a9b`, con upgrade y downgrade
  simétricos.
- Triggers que protegen evidencia append-only y limitan la edición de planes,
  pasos y dependencias al estado `draft`.
- Estructuras de idempotencia, locks y outbox sin activar comportamiento de
  ejecución.
- Pruebas de arquitectura, metadata, repositorio y fuente de migración.

## Decisiones arquitectónicas

El esquema no contiene claves particulares de ETS, Equipos, Facturación,
Certificados ni UC-001. La asociación principal usa sujeto tipado y las
entidades afectadas se conservan como referencias. Las variantes de cada
resolución se reconstruyen desde documentos versionados, hashes y relaciones
estructuradas.

La evidencia histórica no usa borrado lógico ni mutación libre. Las tablas que
en fases posteriores necesitarán transición de estado conservan timestamps y
bloqueo de borrado; los artefactos derivados son append-only. El repositorio no
administra transacciones ni lifecycle para mantener una sola responsabilidad.

La directriz permanente de implementación quedó incorporada en `AGENTS.md`:
correctitud arquitectónica, mantenibilidad, legibilidad, extensibilidad y
rendimiento, en ese orden.

## Bloqueador directo atendido

La revisión `8c2d4e6f7a9b`, ya aplicada localmente pero ausente del historial Git,
impedía crear una cadena Alembic reproducible. Se incorporó antes de esta fase
en el commit independiente `80f9d9f`. No se corrigió la deriva histórica ajena
al Motor.

## Validaciones

- Suite backend: 184 pruebas y 19 subpruebas correctas.
- Suite específica de persistencia: incluida en la suite completa; 64 pruebas
  del Motor correctas.
- Frontend: 11 pruebas correctas.
- Build Vite de producción: correcto; conserva la advertencia preexistente por
  tamaño de chunk.
- Compilación Python: correcta.
- PostgreSQL: creación de 21 tablas y 22 triggers verificada.
- Prueba transaccional reversible: inserción reconstruible y bloqueo de
  actualización de problema, edición de plan no draft y borrado de raíz,
  todos con SQLSTATE `55000`.
- `alembic downgrade 8c2d4e6f7a9b`: correcto; dejó cero tablas y funciones del
  Motor.
- `alembic upgrade head`: correcto.
- `alembic heads/current`: único head `9d3e5f7a1b2c`.
- `alembic check`: mantiene la deriva histórica registrada como `TD-021`, sin
  operaciones propuestas sobre tablas, índices o constraints del Motor.
- `git diff --check`: correcto.

## Exclusiones confirmadas

No se implementaron lifecycle, state machine, lógica de negocio, construcción
de contexto vivo, simulación, autorización operativa, revalidación, ejecución,
Domain Gateways, API, workers ni resoluciones concretas.

## Condición para continuar

La Fase 2 queda `EN REVISIÓN`. La Fase 3 no puede iniciar hasta que este commit
sea aprobado expresamente.
