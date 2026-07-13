# Motor base de Hojas de Campo MYC - Implementación fase 1

Fecha: 2026-07-13  
Estado: implementado y validado localmente  
Referencia aprobada: `docs/ANALISIS_HOJAS_CAMPO_ORIGINALES.md`

## 1. Diagnóstico del estado previo

El ERP ya contaba con una base funcional que debía conservarse:

- creación, edición y transición de estados de Hojas de Campo;
- asociación con equipo, ETS, orden de trabajo, folio reservado y certificado;
- almacenamiento de mediciones en `field_sheet_results`;
- extensión de cada fila mediante `row_data` JSON;
- definiciones de plantilla versionadas en `field_sheet_template_definitions`;
- snapshot de plantilla en `field_sheets.template_definition_json`;
- generación de PDF mediante Jinja y WeasyPrint;
- bitácora de auditoría para hojas y versiones de plantilla.

Las brechas comprobadas eran:

- las familias existentes no correspondían a las ocho familias aprobadas;
- las geometrías de Anemómetro, Calibradores, Presión y Báscula no reproducían los formatos oficiales;
- identidad institucional escrita directamente en frontend y plantillas PDF;
- ausencia de una configuración institucional central para Hojas de Campo;
- firmas limitadas a tres cadenas de texto heredadas;
- inexistencia de relación de firma con usuario ERP, fecha y dato de firma;
- PDF dividido entre tres composiciones rígidas;
- algunas definiciones históricas mezclaban columnas de error, promedio o resultado sin distinguir que eran de captura manual;
- no había pruebas automatizadas del contrato de plantillas.

## 2. Arquitectura implementada

### 2.1 Motor declarativo

Se creó un módulo puro de datos con:

- estructura documental compartida;
- ocho familias semánticas oficiales;
- bloques reutilizables;
- secciones, filas y columnas declarativas;
- etiquetas configurables;
- geometría fija cuando el PDF original así lo requiere;
- indicador explícito `functional_validation_pending` para datos ambiguos;
- `automation.mode = manual_only` y lista de cálculos vacía;
- layout común y configurable de firmas;
- política de paginación dinámica;
- metadatos compatibles con el futuro Constructor Visual.

Las ocho familias registradas son:

1. `replicated_comparison`.
2. `direction_cycle`.
3. `before_after`.
4. `mass_balance_composite`.
5. `paired_multichannel`.
6. `threshold_event`.
7. `verification_compliance`.
8. `cup_specialized`.

No se crearon componentes React o plantillas PDF independientes por magnitud.

### 2.2 Identidad institucional

Se agregó `institutional_configurations` como fuente central editable.

Valores iniciales:

- razón social: `METROLOGÍA Y SERVICIOS MYC`;
- código: `FCA-30`;
- revisión: `R1`;
- logotipo: activo institucional actual del frontend;
- domicilio, teléfono y correo: configurables y sin copiar las inconsistencias históricas.

La configuración se administra mediante API y desde el panel de Configuración de Plantillas. Los PDF y la captura dejaron de contener domicilio, teléfono y correo escritos directamente.

Cada Hoja de Campo nueva conserva además `institutional_snapshot_json`, para que un cambio institucional futuro no altere la representación histórica ya creada.

### 2.3 Firmas

Se creó `field_sheet_signatures` con el contrato común:

- `role`;
- `display_label`;
- `name`;
- `signature_data`;
- `signed_at`;
- `user_id`;
- `position`.

La interfaz permite nombre, usuario ERP y fecha; el renderer acepta también el dato gráfico de firma. Los campos heredados `calibrated_by`, `reviewed_by` y `report_made_by` se mantienen y se sincronizan como adaptadores para no romper consumidores existentes.

### 2.4 Snapshots y versiones

- Las definiciones publicadas siguen siendo versionadas.
- Modificar una versión activa crea una versión nueva.
- Al crear una hoja se copian la definición y su número de versión.
- Al cambiar de plantilla en borrador se toma un snapshot nuevo.
- Una edición posterior de la plantilla no modifica el JSON almacenado en hojas ya creadas.
- La migración no reescribe `template_definition_json` de hojas históricas.

## 3. Cuatro plantillas piloto

| Plantilla | Familia | Geometría implementada | Validación funcional pendiente |
|---|---|---|---|
| Anemómetro | Comparación replicada | 10 filas, Patrón + IBC 1-3 | No |
| Calibradores | Comparación replicada seccionada | Exteriores 7, interiores 5, profundidades 3 | No |
| Presión | Ciclo o dirección | 11 filas, cuatro columnas configurables | Sí, semántica final de encabezados |
| Báscula y Balanza | Masa/balanza compuesta | Excentricidad/ciclo 6, repetibilidad 50 % 5, repetibilidad 100 % 5 | Sí, semántica final de secciones y encabezados |

Todos los valores son manuales. No se agregó cálculo de error, promedio, incertidumbre, cumplimiento, tolerancia, conversión o selección automática de patrón.

## 4. Compatibilidad

Se conservaron:

- endpoints y payloads de Hojas de Campo;
- `results_rows` y sus columnas heredadas;
- `row_data` para columnas nuevas;
- ETS, equipos, folios y certificados;
- estados y validaciones de finalización;
- auditoría existente;
- generación y descarga de PDF;
- definiciones y snapshots históricos.

Adaptadores agregados:

- columnas declarativas se guardan en `row_data` y, cuando corresponde, también en `pattern_value`, `ibc_value_1`, `ibc_value_2` e `ibc_value_3`;
- firmas comunes sincronizan los tres nombres heredados;
- si una hoja anterior no tiene snapshot institucional, el renderer resuelve la configuración central actual;
- las tres plantillas PDF anteriores consumen ahora identidad institucional y firmas comunes.

## 5. Paginación y páginas residuales

- El renderer nuevo usa tamaño Carta vertical.
- La leyenda se genera con contadores: `Página X de Y`.
- No se agregan páginas mediante números fijos ni separadores vacíos.
- Las cuatro plantillas piloto generan una sola página real.
- La definición vigente de Eléctrica declara dos páginas, no tres.
- TLD normal queda definido funcionalmente para una página cuando se implemente su plantilla oficial.
- TLD 6 Canales conservará dos páginas de contenido al implementarse.

Eléctrica y TLD no forman parte de las cuatro plantillas funcionales de esta fase; su geometría detallada continúa pendiente para evitar inventar semántica.

## 6. Migración

Migración aplicada:

`f0a1b2c3d4e5_add_field_sheet_engine_foundation.py`

Incluye:

- tabla `institutional_configurations`;
- columna `field_sheets.institutional_snapshot_json`;
- tabla `field_sheet_signatures`;
- adaptación de nombres de firma históricos;
- publicación de nuevas versiones activas para las cuatro plantillas piloto;
- conservación de snapshots existentes.

Estado local comprobado: `f0a1b2c3d4e5 (head)`.

## 7. Archivos creados

- `backend/app/models/institutional_configuration.py`.
- `backend/app/schemas/institutional_configuration.py`.
- `backend/app/services/institutional_configurations.py`.
- `backend/app/routers/institutional_configurations.py`.
- `backend/app/services/field_sheet_template_engine.py`.
- `backend/app/templates/field_sheet_engine_pdf.html`.
- `backend/migrations/versions/f0a1b2c3d4e5_add_field_sheet_engine_foundation.py`.
- `backend/tests/test_field_sheet_template_engine.py`.
- `backend/scripts/render_field_sheet_pilot_evidence.py`.
- cuatro PDF de evidencia bajo `output/pdf/`.
- cuatro imágenes de evidencia bajo `output/pdf/evidence/`.

## 8. Archivos modificados

- `backend/app/main.py`.
- `backend/app/models/__init__.py`.
- `backend/app/models/field_sheet.py`.
- `backend/app/schemas/field_sheet.py`.
- `backend/app/schemas/field_sheet_template.py`.
- `backend/app/services/field_sheets.py`.
- `backend/app/services/field_sheet_templates.py`.
- `backend/app/services/field_sheet_pdfs.py`.
- las tres plantillas PDF heredadas de Hojas de Campo.
- `frontend/src/services/api.js`.
- `frontend/src/constants/forms.js`.
- `frontend/src/constants/fieldSheetTemplates.js`.
- `frontend/src/utils/fieldSheets.js`.
- `frontend/src/components/field-sheets/FieldSheetLayout.jsx`.
- `frontend/src/components/field-sheets/FieldSheetLayout.css`.
- `frontend/src/pages/ServiceOrdersPage.jsx`.
- `frontend/src/pages/settings/FieldSheetTemplatesSettingsPanel.jsx`.

## 9. Pruebas realizadas

Backend:

- compilación de `app`, migraciones y scripts: correcta;
- cinco pruebas unitarias: correctas;
- validación de las ocho familias: correcta;
- geometría de las cuatro plantillas: correcta;
- filas por defecto compatibles con `results_rows`: correcta;
- copia profunda de definiciones: correcta;
- contrato de firma con usuario ERP: correcto;
- generación OpenAPI: correcta;
- ruta institucional y schema de firma presentes;
- migración aplicada en PostgreSQL;
- cuatro versiones piloto activas verificadas en base de datos.
- prueba transaccional de persistencia de snapshot, `results_rows` y firma: correcta; rollback confirmado sin dejar datos de prueba.

Frontend:

- `npm run build`: correcto;
- 1,632 módulos transformados;
- advertencia no bloqueante existente por bundle mayor a 500 kB.

PDF e impresión:

- cuatro PDF generados mediante el renderer operativo;
- render visual a imagen de todas las páginas;
- inspección de alineación, bordes, tablas, firmas y pies;
- tamaño Carta 612 x 792 pt confirmado;
- una página por plantilla confirmada;
- `Página 1 de 1`, `FCA-30` y `R1` confirmados por extracción;
- sin páginas residuales, recortes ni solapamientos.

## 10. Evidencias visuales

- `output/pdf/evidencia_hoja_campo_anemometro.pdf`.
- `output/pdf/evidencia_hoja_campo_calibradores.pdf`.
- `output/pdf/evidencia_hoja_campo_presion.pdf`.
- `output/pdf/evidencia_hoja_campo_bascula.pdf`.
- imágenes equivalentes en `output/pdf/evidence/`.

Los datos visibles son ficticios y se usan únicamente para revisar geometría y legibilidad.

## 11. Pendientes funcionales

Requieren validación de Calidad antes de fijar semántica:

- encabezados definitivos del ciclo de Presión;
- significado de posiciones, ciclo y repetibilidad de Báscula y Balanza;
- General;
- Eléctrica;
- Reglas;
- Verificación.

También quedan fuera de esta fase:

- captura gráfica de firmas desde este formulario; el modelo y renderer ya aceptan `signature_data`;
- implementación detallada de las otras 19 plantillas;
- automatizaciones metrológicas;
- reglas de aceptación e incertidumbre;
- selección automática de patrones;
- fórmulas y conversiones.

## 12. Confirmación histórica

La migración no actualiza snapshots de plantillas existentes. El PDF usa primero el snapshot almacenado en la Hoja de Campo y sólo consulta la plantilla activa cuando una hoja no cuenta con snapshot. En la base local no había Hojas de Campo persistidas al momento de aplicar la migración, por lo que la compatibilidad histórica se verificó mediante el contrato, la migración y pruebas del comportamiento de copia, no contra casos locales preexistentes.
