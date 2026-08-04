> Estado: VIGENTE
>
> Corte verificado: 2026-08-04
>
> Autoridad: Alta para validación de esquema, respaldo y recuperación

# Integridad de esquema y recuperación

## Contrato

PostgreSQL, metadata SQLAlchemy y la cadena Alembic deben converger en un único
head. Una entrega de persistencia no se considera válida sólo porque `upgrade`
termine: debe pasar `alembic check`, el ciclo vacío completo
`base→head→base→head`, un upgrade desde respaldo histórico y un restore del
respaldo oficial vigente.

Los índices parciales, de expresión, FTS o de patrón creados expresamente por
migraciones PostgreSQL permanecen bajo propiedad de Alembic. Su allowlist vive
en `backend/migrations/env.py`; evita que autogenerate proponga retirarlos por
no ser declaraciones ORM portables. Todo índice ORM portable continúa sujeto a
comparación normal y debe existir físicamente.

## Head vigente

`f27f8a90b1c3` — reconciliación de defaults, soft-delete de fórmulas e índices
ORM faltantes. Las revisiones locales `c14c5d6e7f80`, `d15d6e7f8091` y
`e16e7f8091a2` forman oficialmente parte de la cadena que lo precede.

## Validación de ciclo

```bash
scripts/toolkit/db/validate-schema-cycle.sh
```

El script crea una base con prefijo exclusivo `erp_myc_schema_cycle_`, ejecuta
upgrade/check/downgrade/upgrade/check y la elimina al terminar. Nunca apunta a
la base compartida. `MYC_KEEP_DRILL_DB=1` permite conservarla para diagnóstico;
`MYC_TEMP_DATABASE_BASE_URL` permite elegir otro servidor temporal.

## Restore drill

```bash
scripts/toolkit/db/restore-drill.sh backup_erp_myc_antes_prueba.sql
```

El drill exige un archivo no vacío, crea una base
`erp_myc_restore_drill_*`, restaura con `ON_ERROR_STOP`, migra a head, ejecuta
`alembic check`, reporta sólo revisión y número de tablas y elimina la base. No
imprime filas, credenciales ni datos operativos.

## Evidencia del corte

- ciclo vacío `base→head→base→head`: correcto;
- upgrade histórico `b03b4c5d6e7f→f27f8a90b1c3`: correcto;
- restore del respaldo oficial: `f27f8a90b1c3`, 102 tablas públicas;
- `alembic check`: sin operaciones nuevas;
- respaldo oficial: 74,539,344 bytes; SHA-256
  `7e3d332d93a04ebfa47b1dc78cfa0f5592e1a3386f4381f2d5ceb3d8b92e8e19`.

## Límites

El contrato no autoriza retirar tablas o columnas legacy sólo por coexistencia.
Ese trabajo exige telemetría, análisis de datos, migración reversible y alcance
propio. Tampoco convierte un dump operativo en artefacto publicable: su custodia
debe seguir evitando exposición de información sensible.
