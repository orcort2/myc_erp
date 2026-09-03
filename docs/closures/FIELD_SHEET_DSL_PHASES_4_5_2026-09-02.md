> Estado: CERRADO TÉCNICAMENTE
>
> Fecha: 2026-09-02
>
> Alcance: DSL avanzado de tablas y motor visual PDF declarativo

# Cierre técnico — Hojas de Campo Fases 4 y 5

El snapshot de plantilla admite headers multinivel validados, grupos mediante
`colspan`/`rowspan`, labels fijos de fila, anchos/alineación y geometrías de
múltiples secciones. El modelo persistente `FieldSheetResult` no cambió y no se
creó migración.

El renderer canónico `field_sheet_engine_pdf.html` consume un `print_layout`
tipado para página, documento, bloques y campos, además de perfiles allowlisted
MYC/CAPYMET. La normalización y resolución ocurren en Python; Jinja conserva la
presentación. No existen branches por template, magnitud, instrumento u
organización, ni entrada libre de CSS/HTML/Jinja/URL/path.

Se conserva renderer versión 1 porque todos los defaults reproducen la
interpretación histórica: Letter portrait, márgenes 12/10/14/10, identidad,
título/footer, bloques de una columna y header plano cuando no hay
`header_rows`. Los PDFs finales congelados no se regeneran.

La aceptación automatizada incluye fixtures temporales —no plantillas
oficiales— de Temperatura-like y geometría compleja multisección, generación
real PDF, perfiles MYC/CAPYMET, seguridad del DSL y consumidor Mobile genérico.

Pendiente exclusivo para la fase siguiente: cargar definiciones oficiales del
catálogo y magnitudes aprobadas, incorporar el asset CAPYMET cuando exista y
ejecutar validación visual/física formato por formato.

## Microcierre auditado

- CAPYMET queda aislado del snapshot institucional MYC: nombre legal/visible
  CAPYMET, sin logo y con dirección, teléfono y correo vacíos hasta recibir
  configuración real.
- La geometría Mobile usa posiciones calculadas y `rowspan` real; el fixture de
  temperatura ocupa exactamente dos filas y conserva scroll horizontal.
- Un `column_key` válido pero colocado fuera de su columna lógica se rechaza
  con 422.
- El renderer v1 conserva `.block { break-inside: avoid; }` y la excepción
  `.break-auto`; los defaults completos de página, documento y bloque quedaron
  cubiertos por regresión.

## Validación

- Backend focal ampliado: `101 passed`.
- Backend completo: `935 passed, 8 skipped, 2 failed`; las dos fallas son la
  deuda preexistente del inventario API 477 vs runtime 506, fuera de alcance.
- Mobile focal: `9 passed`; Mobile completo: `313 passed, 1 failed`, por la
  prueba preexistente de identidad `linked_folio` en `request-inbox.test.ts`.
- TypeScript: correcto. Expo lint: 0 errores, 8 warnings preexistentes.

Validación focal del microcierre:

- Backend (`test_field_sheet_layout_dsl.py`,
  `test_field_sheet_template_engine.py`, `test_lab_field_sheets_capture.py`):
  `88 passed`, 12 warnings.
- Mobile (`field-sheet-result-layout.test.ts` y
  `FieldSheetResultsWorkspace.wiring.test.ts`): `9 passed`, 0 fallas.
- TypeScript: correcto, exit code 0.
