# Hojas de Campo MYC — estructura base y catálogo maestro de campos

Estado: definición arquitectónica oficial v1  
Alcance: inventario canónico; todavía no es una implementación ejecutable  
Documento padre: `docs/MDE_SPEC.md`

## 1. Decisiones obligatorias

- Una clave canónica identifica un concepto y no una etiqueta, pantalla o columna física.
- Las claves usan `namespace.field_name`, en inglés, minúsculas y `snake_case`.
- Una plantilla puede sobrescribir etiqueta, ayuda, visibilidad y obligatoriedad, pero no puede cambiar el significado ni el origen de una clave.
- Ninguna plantilla puede inventar campos. Una necesidad nueva debe incorporarse primero a este registro y versionarse.
- Constructor, captura, búsqueda, filtros, PDF y reportes deberán consumir el mismo registro cuando se implemente.
- Los datos variables de medición son campos por rol; no se crean claves por magnitud como `pressure_pattern` o `temperature_pattern`.
- Los nombres planos actuales son alias de transición y no nuevas identidades.
- Las definiciones publicadas y sus snapshots conservarán la versión del registro utilizada.

## 2. Contrato de un campo registrado

Todo campo ejecutable deberá materializar este contrato:

```json
{
  "id": "instrument.brand",
  "label": "Marca",
  "type": "text",
  "category": "instrument",
  "source": "equipment.brand",
  "editable": false,
  "required": true,
  "visible": true,
  "printable": true,
  "searchable": true,
  "filterable": true,
  "scope": "document",
  "status": "available"
}
```

Valores iniciales de `type`: `text`, `textarea`, `integer`, `decimal`, `boolean`, `date`, `datetime`, `email`, `asset`, `signature`, `collection`.

Valores de `scope`:

- `document`: un valor por hoja de campo emitida.
- `row`: un valor por renglón de resultados.
- `runtime`: valor calculado durante renderizado.
- `institution`: configuración institucional compartida.
- `template`: valor controlado por la plantilla o Control Documental.

Valores de `status`:

- `available`: existe una fuente equivalente en el sistema actual.
- `snapshot`: existe en `field_sheets` como dato congelado o de captura.
- `resolver`: debe resolverse desde relaciones o composición de otros datos.
- `planned`: no existe todavía una fuente persistente correcta.
- `runtime`: se calcula al renderizar.

En las tablas siguientes, `E/R/V/P/S/F` significa editable, obligatorio, visible por defecto, imprimible, buscable y filtrable.

## 3. Estructura madre oficial

Identidad:

```json
{
  "key": "field-sheet-base",
  "name": "Estructura base de hoja de campo",
  "version": 1
}
```

Orden base:

| Orden | `block_key` | Tipo oficial | Propósito |
|---:|---|---|---|
| 1 | `documentHeader` | `DocumentHeaderBlock` | Identidad institucional y título variable |
| 2 | `documentReference` | `DocumentReferenceBlock` | Orden de trabajo y certificado |
| 3 | `customerData` | `CustomerDataBlock` | Datos del usuario o cliente |
| 4 | `instrumentData` | `InstrumentDataBlock` | Identificación y características del instrumento |
| 5 | `serviceDates` | `ServiceDatesBlock` | Fechas de recepción, servicio y próxima calibración |
| 6 | `environmentalConditions` | `EnvironmentalConditionsBlock` | Humedad y temperatura inicial/final |
| 7 | `equipmentCondition` | `EquipmentConditionBlock` | Estado general y desviaciones |
| 8 | `observations` | `ObservationsBlock` | Observaciones y unidades |
| 9 | `measurementArea` | `MeasurementAreaBlock` | Región reservada para una familia de tabla |
| 10 | `signatures` | `SignatureBlock` | Firmas configurables por plantilla |
| 11 | `documentFooter` | `DocumentFooterBlock` | Código, revisión y paginación |

`MeasurementAreaBlock` conserva inicialmente `tableDefinition: null`. Las tablas y sus familias quedan fuera de esta fase.

## 4. Registro maestro v1

### 4.1 Institución

| ID | Etiqueta base | Tipo | Fuente canónica | E/R/V/P/S/F | Estado |
|---|---|---|---|---|---|
| `institution.name` | Razón social | text | `institution.config.company_name` | 0/1/1/1/0/0 | planned |
| `institution.address` | Dirección institucional | textarea | `institution.config.address` | 0/0/1/1/0/0 | planned |
| `institution.phone` | Teléfono institucional | text | `institution.config.phone` | 0/0/1/1/0/0 | planned |
| `institution.email` | Correo institucional | email | `institution.config.email` | 0/0/1/1/0/0 | planned |
| `institution.logo_asset` | Logotipo institucional | asset | `institution.config.logo_asset` | 0/1/1/1/0/0 | planned |

La configuración actual de cotizaciones contiene `document_templates.company_name`, pero es específica de ese módulo y no se declara como configuración institucional global.

### 4.2 Documento

| ID | Etiqueta base | Tipo | Fuente canónica | E/R/V/P/S/F | Estado |
|---|---|---|---|---|---|
| `document.title` | Título del documento | text | `template.document_title` | 1/1/1/1/1/0 | template |
| `document.subtitle` | Subtítulo del documento | text | `template.document_subtitle` | 1/0/1/1/0/0 | template |
| `document.code` | Código documental | text | `template.document_code` | 0/1/1/1/1/1 | available |
| `document.revision` | Revisión | text | `template.document_revision` | 0/1/1/1/1/1 | available |
| `document.version` | Versión técnica | integer | `field_sheet.template_definition_version` | 0/1/0/0/1/1 | snapshot |
| `document.status` | Estado | text | `field_sheet.status` | 0/1/0/0/1/1 | available |
| `document.created_at` | Fecha de creación | datetime | `field_sheet.created_at` | 0/1/0/0/1/1 | available |
| `document.updated_at` | Última actualización | datetime | `field_sheet.updated_at` | 0/1/0/0/1/1 | available |
| `document.instance_folio` | Folio de hoja de campo | text | `field_sheet.folio` | 0/0/0/1/1/1 | planned |
| `document.page` | Página | integer | `renderer.page_number` | 0/1/1/1/0/0 | runtime |
| `document.total_pages` | Total de páginas | integer | `renderer.total_pages` | 0/1/1/1/0/0 | runtime |

Convención inicial del pie: `FCA-30`, `Página N de M`, `R1`. No se aceptan variantes sintácticas como `FC-30`, `R-1` o `R 1` para la misma revisión.

### 4.3 Cliente

| ID | Etiqueta base | Tipo | Fuente canónica | E/R/V/P/S/F | Estado |
|---|---|---|---|---|---|
| `customer.name` | Empresa | text | `client.legal_name` → `field_sheet.company` | 0/1/1/1/1/1 | snapshot |
| `customer.contact` | Atención | text | `selected_client_contact.name` → `field_sheet.attention` | 1/0/1/1/1/0 | resolver |
| `customer.address` | Dirección | textarea | dirección compuesta → `field_sheet.address` | 1/0/1/1/1/0 | resolver |
| `customer.city` | Ciudad | text | `client.city` | 0/0/0/0/1/1 | available |
| `customer.state` | Estado | text | `client.state` | 0/0/0/0/1/1 | available |
| `customer.country` | País | text | `client.country` | 0/0/0/0/1/1 | available |

La variante visual de Copa cambia `customer.name` de “Empresa” a “Cliente”; no crea otro campo.

### 4.4 Servicio

| ID | Etiqueta base | Tipo | Fuente canónica | E/R/V/P/S/F | Estado |
|---|---|---|---|---|---|
| `service.order_number` | Orden de trabajo | text | `field_sheet.work_order.work_order_number` → snapshot | 0/1/1/1/1/1 | resolver |
| `service.certificate_number` | Certificado No. | text | `field_sheet.reserved_certificate_folio` | 0/1/1/1/1/1 | resolver |
| `service.received_date` | Fecha de recepción | date | `field_sheet.reception_date` | 0/0/1/1/1/1 | snapshot |
| `service.calibration_date` | Fecha de calibración | date | `field_sheet.calibration_date` | 1/1/1/1/1/1 | snapshot |
| `service.next_calibration_date` | Próxima calibración | date | `field_sheet.next_calibration_date` | 0/0/1/1/1/1 | snapshot |
| `service.location` | Lugar de calibración | text | `field_sheet.calibration_place` | 1/0/1/1/1/1 | snapshot |
| `service.technician` | Técnico | text | `service_order.technician.full_name` | 0/0/0/1/1/1 | resolver |
| `service.advisor` | Asesor | text | `service_order.advisor.full_name` | 0/0/0/0/1/1 | resolver |
| `service.method` | Método | text | `field_sheet.method` | 1/0/0/1/1/1 | snapshot |
| `service.commercial_reference` | Orden de compra/Cotización | text | `field_sheet.purchase_order_or_quotation` | 1/0/1/1/1/1 | snapshot |

Una plantilla de verificación sobrescribe solamente las etiquetas de `service.calibration_date` y `service.next_calibration_date`.

### 4.5 Instrumento

| ID | Etiqueta base | Tipo | Fuente canónica | E/R/V/P/S/F | Estado |
|---|---|---|---|---|---|
| `instrument.name` | Instrumento | text | `equipment.name` | 0/1/1/1/1/1 | available |
| `instrument.brand` | Marca | text | `equipment.brand` | 0/1/1/1/1/1 | available |
| `instrument.model` | Modelo | text | `equipment.model` | 0/0/1/1/1/1 | available |
| `instrument.serial` | No. Serie | text | `equipment.serial_number` | 0/0/1/1/1/1 | available |
| `instrument.internal_id` | Identificación | text | `equipment.internal_id` | 0/0/1/1/1/1 | available |
| `instrument.location` | Ubicación | text | `field_sheet.location` | 1/0/1/1/1/1 | snapshot |
| `instrument.range` | Alcance | text | `equipment.range_or_capacity` | 0/0/1/1/1/1 | available |
| `instrument.resolution` | División mínima | text | `field_sheet.minimum_division` | 1/0/1/1/1/1 | snapshot |
| `instrument.capacity` | Capacidad | text | `equipment.range_or_capacity` | 0/0/0/1/1/1 | resolver |
| `instrument.class` | Clase | text | `equipment.metadata.class` | 0/0/0/1/1/1 | planned |
| `instrument.type` | Tipo | text | `equipment.metadata.type` | 0/0/0/1/1/1 | planned |
| `instrument.measure` | Medida | text | `equipment.metadata.measure` | 0/0/0/1/1/1 | planned |
| `instrument.standard` | Norma/Estándar | text | `equipment.metadata.standard` | 0/0/0/1/1/1 | planned |

`instrument.range` y `instrument.capacity` pueden resolver el mismo dato actual, pero representan etiquetas semánticas distintas. Una plantilla no debe mostrar ambos salvo que el modelo futuro almacene valores separados.

### 4.6 Ambiente

| ID | Etiqueta base | Tipo | Fuente canónica | E/R/V/P/S/F | Estado |
|---|---|---|---|---|---|
| `environment.temperature_start` | Temperatura inicio | decimal | `field_sheet.environment_temperature_start` | 1/1/1/1/0/0 | snapshot |
| `environment.temperature_end` | Temperatura final | decimal | `field_sheet.environment_temperature_end` | 1/1/1/1/0/0 | snapshot |
| `environment.humidity_start` | Humedad relativa inicio | decimal | `field_sheet.environment_humidity_start` | 1/1/1/1/0/0 | snapshot |
| `environment.humidity_end` | Humedad relativa final | decimal | `field_sheet.environment_humidity_end` | 1/1/1/1/0/0 | snapshot |

Unidades predeterminadas: temperatura `°C`, humedad `%`. La presentación Inicio/Final de Copa es una variante de layout del mismo bloque.

### 4.7 Estado del instrumento

| ID | Etiqueta base | Tipo | Fuente canónica | E/R/V/P/S/F | Estado |
|---|---|---|---|---|---|
| `equipment.good_condition` | Equipo en buen estado general | boolean | `field_sheet.equipment_general_condition` | 1/0/1/1/0/1 | snapshot |
| `equipment.has_deviations` | Considerar desviaciones del equipo | boolean | `field_sheet.consider_equipment_deviations` | 1/0/1/1/0/1 | snapshot |
| `equipment.observations` | Observaciones del equipo | textarea | `equipment.notes` | 1/0/0/1/1/0 | available |
| `equipment.initial_condition` | Condición inicial | textarea | `field_sheet.initial_condition` | 1/0/0/1/1/0 | snapshot |
| `equipment.final_condition` | Condición final | textarea | `field_sheet.final_condition` | 1/0/0/1/1/0 | snapshot |

“Equipo dañado”, “Equipo incompleto”, “No apto para calibración” y “Requiere ajuste” no se registran en v1 porque todavía no pertenecen a los formatos oficiales revisados.

### 4.8 Captura técnica

| ID | Etiqueta base | Tipo | Fuente canónica | E/R/V/P/S/F | Estado |
|---|---|---|---|---|---|
| `capture.units` | Unidades | text | `field_sheet.units` | 1/0/1/1/0/1 | snapshot |
| `capture.notes` | Otros | textarea | `field_sheet.observations` | 1/0/1/1/1/0 | snapshot |
| `capture.evidence_notes` | Evidencia/Notas | textarea | `field_sheet.evidence_notes` | 1/0/0/0/1/0 | snapshot |
| `capture.technician_notes` | Notas del técnico | textarea | `field_sheet.technician_notes` | 1/0/0/0/1/0 | snapshot |
| `capture.measurements` | Mediciones | collection | `field_sheet.results_rows` | 1/1/0/0/0/0 | available |
| `capture.reference` | Referencia general | text | `field_sheet.results_rows[].row_data.reference` | 1/0/0/1/0/0 | snapshot |
| `capture.pattern` | Patrón utilizado | text | `field_sheet.pattern_used` / `reference_standard_links` | 1/0/0/1/1/1 | resolver |
| `capture.result` | Resultado general | textarea | `field_sheet.results` | 1/0/0/1/1/0 | snapshot |

La variante bilingüe de observaciones de Copa sobrescribe la etiqueta de `capture.notes` y conserva la misma identidad.

### 4.9 Firmas

| ID | Etiqueta base | Tipo | Fuente canónica | E/R/V/P/S/F | Estado |
|---|---|---|---|---|---|
| `signature.operator` | CALIBRÓ | signature | `field_sheet.calibrated_by` | 1/1/1/1/1/0 | snapshot |
| `signature.reviewer` | REVISÓ | signature | `field_sheet.reviewed_by` | 1/1/1/1/1/0 | snapshot |
| `signature.report` | REALIZÓ INFORME (SMM) | signature | `field_sheet.report_made_by` | 1/0/1/1/1/0 | snapshot |
| `signature.customer` | CLIENTE | signature | `field_sheet.signature_customer` | 1/0/0/1/1/0 | planned |
| `signature.authorizer` | AUTORIZÓ | signature | `field_sheet.signature_authorizer` | 1/0/0/1/1/0 | planned |

La etiqueta `VERIFICÓ` es una sobrescritura de `signature.operator`. La configuración de Copa reordena y muestra roles existentes; no crea claves basadas en el texto visible.

### 4.10 Filas de medición

Estos campos tienen `scope: row` y viven dentro de `capture.measurements`.

| ID | Etiqueta base | Tipo | Fuente canónica | E/R/V/P/S/F | Estado |
|---|---|---|---|---|---|
| `measurement.reference` | Referencia | text | `field_sheet_result.row_data.reference` | 1/0/1/1/0/0 | snapshot |
| `measurement.reading_1` | Lectura 1 | decimal | `field_sheet_result.row_data.reading_1` | 1/0/1/1/0/0 | snapshot |
| `measurement.reading_2` | Lectura 2 | decimal | `field_sheet_result.row_data.reading_2` | 1/0/1/1/0/0 | snapshot |
| `measurement.reading_3` | Lectura 3 | decimal | `field_sheet_result.row_data.reading_3` | 1/0/1/1/0/0 | snapshot |
| `measurement.reading_4` | Lectura 4 | decimal | `field_sheet_result.row_data.reading_4` | 1/0/0/1/0/0 | snapshot |
| `measurement.reading_5` | Lectura 5 | decimal | `field_sheet_result.row_data.reading_5` | 1/0/0/1/0/0 | snapshot |
| `measurement.result` | Resultado | decimal | `field_sheet_result.row_data.result` | 1/0/0/1/0/0 | snapshot |
| `measurement.unit` | Unidad | text | `field_sheet_result.row_data.unit` / `unit` | 1/0/0/1/0/0 | available |
| `measurement.notes` | Observaciones | textarea | `field_sheet_result.row_data.notes` / `notes` | 1/0/0/1/0/0 | available |
| `measurement.section` | Sección | text | `field_sheet_result.section_key` | 0/1/0/0/0/0 | available |
| `measurement.row_number` | Renglón | integer | `field_sheet_result.row_number` | 0/1/0/0/0/0 | available |

Los campos físicos legacy `pattern_value` e `ibc_value_1..3` continúan para compatibilidad histórica, pero las definiciones nuevas deben escribir claves canónicas en `row_data`.

## 5. Roles de tabla

Una columna futura se define por rol, etiqueta y binding; no por el nombre de la magnitud:

```json
{
  "role": "measurement",
  "label": "IBC",
  "binding": "measurement.reading_1"
}
```

Roles iniciales:

| Rol | Significado | Bindings permitidos inicialmente |
|---|---|---|
| `reference` | Valor o entidad contra la que se compara | `measurement.reference` |
| `measurement` | Lectura capturada | `measurement.reading_1..5` |
| `result` | Resultado declarado o calculado | `measurement.result` |
| `unit` | Unidad del renglón | `measurement.unit` |
| `notes` | Observación del renglón | `measurement.notes` |

“Patrón”, “Equipo”, “IBC”, “Indicación” y “Referencia” son etiquetas de una instancia de columna. No son roles ni claves nuevas.

## 6. Composición de bloques

| Bloque | Campos base |
|---|---|
| `DocumentHeaderBlock` | `institution.name`, `institution.address`, `institution.phone`, `institution.email`, `institution.logo_asset`, `document.title`, `document.subtitle` |
| `DocumentReferenceBlock` | `service.order_number`, `service.certificate_number` |
| `CustomerDataBlock` | `customer.contact`, `customer.name`, `customer.address` |
| `InstrumentDataBlock` | `instrument.name`, `instrument.range`, `instrument.resolution`, `instrument.brand`, `instrument.serial`, `instrument.model`, `instrument.internal_id`, `instrument.location`, `service.location`; admite `extraFields` registrados |
| `ServiceDatesBlock` | `service.received_date`, `service.calibration_date`, `service.next_calibration_date` |
| `EnvironmentalConditionsBlock` | los cuatro campos `environment.*` |
| `EquipmentConditionBlock` | `equipment.good_condition`, `equipment.has_deviations` |
| `ObservationsBlock` | `capture.notes`, `capture.units` |
| `MeasurementAreaBlock` | `capture.measurements`; `tableDefinition: null` en la base |
| `SignatureBlock` | `signature.operator`, `signature.reviewer`, `signature.report`, `service.commercial_reference` |
| `DocumentFooterBlock` | `document.code`, `document.revision`, `document.page`, `document.total_pages` |

## 7. Alias actuales y migración futura

| Clave plana actual | ID canónico |
|---|---|
| `work_order_number` | `service.order_number` |
| `reserved_certificate_folio`, `certificate_number` | `service.certificate_number` |
| `attention` | `customer.contact` |
| `company` | `customer.name` |
| `address` | `customer.address` |
| `instrument`, `equipment` | `instrument.name` |
| `scope` | `instrument.range` |
| `minimum_division` | `instrument.resolution` |
| `brand` | `instrument.brand` |
| `serial_number` | `instrument.serial` |
| `model` | `instrument.model` |
| `internal_id` | `instrument.internal_id` |
| `location` | `instrument.location` |
| `calibration_place` | `service.location` |
| `reception_date` | `service.received_date` |
| `calibration_date` | `service.calibration_date` |
| `next_calibration_date` | `service.next_calibration_date` |
| `humidity_start`, `environment_humidity_start` | `environment.humidity_start` |
| `humidity_end`, `environment_humidity_end` | `environment.humidity_end` |
| `temperature_start`, `environment_temperature_start` | `environment.temperature_start` |
| `temperature_end`, `environment_temperature_end` | `environment.temperature_end` |
| `equipment_general_condition` | `equipment.good_condition` |
| `consider_equipment_deviations` | `equipment.has_deviations` |
| `initial_condition` | `equipment.initial_condition` |
| `final_condition` | `equipment.final_condition` |
| `method` | `service.method` |
| `units` | `capture.units` |
| `observations` | `capture.notes` |
| `evidence_notes` | `capture.evidence_notes` |
| `technician_notes` | `capture.technician_notes` |
| `pattern_used` | `capture.pattern` |
| `calibrated_by` | `signature.operator` |
| `reviewed_by` | `signature.reviewer` |
| `report_made_by` | `signature.report` |
| `purchase_order_or_quotation` | `service.commercial_reference` |

Los alias permiten planear una migración compatible. No autorizan cambiar ahora payloads, snapshots, modelos o PDFs existentes.

## 8. Brechas confirmadas en el código actual

1. `frontend/src/constants/fieldSheetTemplates.js` contiene `fieldSheetFieldCatalog` con claves planas y metadatos mínimos; no es todavía el registro maestro.
2. `backend/app/schemas/field_sheet_template.py` y `backend/app/services/field_sheet_templates.py` usan familias de bloque anteriores (`HeaderBlock`, `ClientBlock`, `EquipmentBlock`, etc.). Los once tipos oficiales aún no son contratos ejecutables.
3. No existe una configuración institucional global con nombre, domicilio, teléfono, correo y logotipo. La configuración de plantillas de cotización no debe reutilizarse silenciosamente.
4. No existen hoy `service.contact_name` ni `service.address`; contacto y dirección deben resolverse desde cliente/contacto y congelarse en la hoja.
5. `Equipment` no almacena todavía resolución, ubicación, clase, tipo, medida, estándar, fecha de recepción o próxima calibración como campos propios.
6. `FieldSheet` no tiene un folio propio distinto de su ID.
7. Las firmas de cliente y autorizador para Hoja de Campo no existen en el modelo actual.
8. Las tablas actuales mezclan nombres semánticos (`pattern_value`, `ibc_value_*`) con `row_data`; la migración a roles debe conservar compatibilidad histórica.

## 9. Frontera de esta fase

Esta definición no modifica todavía:

- modelos ni migraciones;
- schemas o endpoints;
- plantillas activas y snapshots;
- el constructor visual;
- captura operativa de Hojas de Campo;
- renderizadores PDF;
- familias de tablas.

El siguiente paso técnico deberá convertir este inventario en un módulo de datos puro y validado, con resolución de alias y pruebas de unicidad, antes de conectarlo a cualquier pantalla.
