> Estado: TERMINADA — EN REVISIÓN
>
> Fecha: 2026-08-04
>
> Alcance: Etapa 2A — integridad de esquema y recuperación

# Cierre técnico de Etapa 2A

## Dictamen

El bloque está técnicamente terminado. ORM, Alembic y PostgreSQL convergen en
`f27f8a90b1c3`; `alembic check` está limpio, el downgrade completo fue reparado,
las tres migraciones locales quedaron incorporadas a la cadena, el respaldo
histórico migra al head y el respaldo oficial regenerado fue restaurado en una
base temporal con 102 tablas.

## Cambios

- 16 `server_default=now()` completados en ocho tablas;
- `uncertainty_formulas` alineada con su mixin soft-delete;
- 17 índices ORM faltantes creados físicamente;
- índices PostgreSQL especializados protegidos mediante allowlist explícita;
- ownership de downgrade corregido en `28eed747a29b`/`c3fb78821edc`;
- FK histórica de asesor con nombre determinista y downgrade ejecutable;
- scripts reproducibles de ciclo y restore;
- respaldo oficial regenerado y alineado.

## Validaciones

| Gate | Resultado |
| --- | --- |
| Head único | `f27f8a90b1c3` |
| `alembic check` base local | limpio |
| Vacío `base→head→base→head` | correcto |
| Upgrade histórico | `b03b4c5d6e7f→f27f8a90b1c3` correcto |
| Restore oficial | correcto; 102 tablas; head vigente |
| Pruebas específicas 2A | 3 passed |
| Regresión backend completa | 430 passed, 19 subtests |
| Frontend | 31 passed; build correcto |
| Respaldo | 74,539,344 bytes; revisión y checksum documentados |

## Límites

No se retiraron tablas/columnas legacy, no se alteraron flujos del ERP y las
pruebas destructivas se ejecutaron exclusivamente en bases temporales con
prefijos validados. El estado permanece en revisión hasta el dictamen del
usuario.
