> Estado: VIGENTE
>
> Corte verificado: 2026-08-24

# Folios de certificados y órdenes de trabajo

## Certificados

Formato compacto, sin guiones:

- Acreditado: `MYCA{AA}{MM}{NNNN}`.
- Trazable: `MYCT{AA}{MM}{NNNN}`.
- Vinculado: `{PREFIJO_SNAPSHOT}{AA}{MM}{NNNN}`.

Verificación usa el formato institucional distinto y obligatorio
`MYCV-{MM}-{AA}-{XXXX}`. No admite captura ni edición manual del folio.

Ejemplos: `MYCA26078000`, `MYCT26078000`, `CMVG26078000` y `MYCV-08-26-8000`.

Los contadores se separan por `document_type + prefix + year`. El mes impreso
es el real de emisión, pero no particiona el contador. En 2026 el piso es 8000;
desde cada año nuevo es 1000. Cada prefijo vinculado conserva su propio
consecutivo. `MYCV` comparte la misma política anual de secuencia, pero presenta
mes y año con los separadores exigidos por su formato.

## Órdenes de trabajo

La presentación actual de OT se conserva. El contador `OT + año` tiene piso
7000 durante 2026 y 1000 desde cada año posterior; no se reinicia por mes.

## Concurrencia e integridad

`institutional_folio_sequences` tiene unicidad por ámbito. PostgreSQL toma un
`pg_advisory_xact_lock` del ámbito, bloquea la fila y aumenta `next_value`
dentro de la transacción. El rollback también revierte la reserva. Antes de
crear un contador se consulta el máximo existente y nunca se disminuye.

La migración `b03b4c5d6e7f` fija los pisos 2026 para MYCA, MYCT y OT mediante
upsert seguro. Los prefijos vinculados y `MYCV` se inicializan al primer uso. El
downgrade no reduce una secuencia consumida.
