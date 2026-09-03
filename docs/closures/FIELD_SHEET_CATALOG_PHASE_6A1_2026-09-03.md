> Estado: FASE 6A.1 — EN REVISIÓN
>
> Corte: 2026-09-03
>
> Alcance: materialización oficial exclusiva de `[MYC] Temperatura` y
> `[MYC] Presión`

# Implementación del catálogo de Hojas de Campo — Fase 6A.1

## Fuentes y definiciones

Los PDFs FCA-30 originales suministrados son la autoridad documental. La
definición `temperatura` queda en versión 2, código FCA-30, revisión impresa
`R-1`, familia `replicated_comparison`, 10 filas y cuatro columnas lógicas:
IBC y tres lecturas de patrón. La definición histórica `presion` evoluciona a
versión 3, código FCA-30, revisión `R1`, familia `direction_cycle`, 11 filas y
el ciclo visible literal `Acendente`, `Descendente`, `Ascendente`.

Ambas tablas declaran una primera fila completa `DATOS DE MEDICION` y su
geometría agrupada mediante `header_rows`. Las firmas reutilizan los roles
existentes `calibrated_by`, `reviewed_by` y `report_made_by`, con labels
`CALIBRÓ`, `REVISÓ`, `REALIZÓ INFORME (SMM)`, dirección vertical, una columna
y `purchase_order_or_quotation` como trailing field. `print_layout` usa Letter
portrait y grid documental de tres columnas para componer tabla|firmas.

## Catálogo y compatibilidad

El eje permanece organización + magnitud + variante; las dos definiciones son
MYC y tienen variante nula. Presión registra sólo manómetro, vacuómetro y
diferencial de presión como `supported_equipment`; Temperatura no inventa un
equipo no documentado. Esa metadata y `search_aliases` sólo intervienen en
búsqueda/presentación. Una prueba HTTP crea y guarda Presión para un equipo no
relacionado, acreditando que no son guards productivos.

No se cambió Mobile: el selector existente produce `[MYC] Temperatura` y
`[MYC] Presión` desde metadata y la captura consume bloques/resultados de forma
declarativa. Tampoco hubo migración, cambio de `FieldSheetResult`, renderer o
componente individual, branches por plantilla/magnitud/equipo ni actualización
masiva. Las hojas creadas conservan `template_definition_json`; la prueba de
Presión verifica que una versión posterior del catálogo no altera el snapshot.

## Evidencia PDF y validación

Se generaron dos PDFs reales con el renderer único. Ambos comienzan con `%PDF`,
tienen una página Letter portrait y fueron renderizados a PNG para inspección
visual contra las fuentes. Temperatura muestra FCA-30/R-1, 10 filas y patrón
1/2/3; Presión muestra FCA-30/R1, 11 filas y los tres labels documentales del
ciclo. Ambos muestran tres firmas verticales y OC/Cotización bajo ellas.

La cobertura ampliada de template engine, layout/PDF, contrato operacional,
captura LAB y revisiones registra `117 passed, 18 warnings`, exit 0.

## Pendiente

Fase 6A.2 y las definiciones oficiales restantes. Fase 6A.1 no declara Fase 6A
completa ni Fase 6 completa; permanece **EN REVISIÓN**.
