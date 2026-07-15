# Catálogos SAT locales

## Arquitectura

`archivo descargado manualmente → adaptador/parser → normalización y validación → importador transaccional → base local versionada → servicios/API de consulta`.

La fuente operativa del ERP es exclusivamente `sat_catalogs`, `sat_catalog_versions` y `sat_catalog_records`. No hay consultas HTTP ni scraping en tiempo de ejecución. Los datos oficiales nunca se modifican: favoritos y alias residen en tablas MYC separadas.

## Jerarquía y fuentes

1. Excel oficial descargado del SAT: fuente de importación vigente.
2. [catalogs.db](/Users/saulcortes/Desktop/myc_erp/backend/resources/sat/catalogs.db) de PhpCfdi: respaldo técnico y fuente de comparación.
3. PostgreSQL: única fuente operativa del ERP.

El frontend y los servicios del ERP nunca leen directamente Excel ni SQLite.

### Excel oficial vigente

El archivo recibido se conserva sin renombrar en `backend/resources/sat/catalogo sat.xlsx`. Aunque el nombre solicitado inicialmente era `catCFDI_V_4_20260703.xls`, el archivo entregado es XLSX; el adaptador rechaza extensiones ajenas a XLS/XLSX y no realiza conversiones. Como el nombre no incluye la versión, la ejecución exige `--version 20260703` explícito.

Checksum SHA-256: `62cc150e10fb16efbda7642e3d65452748e180fafc8149abd65e4bc95205bc16`. El binario está ignorado por Git; la ruta, checksum y comando reproducible quedan documentados aquí. La versión oficial cargada es `20260703`, con fecha de datos `2026-07-03`, tipo de fuente `sat_official_xls` y origen `SAT` registrados en el `report` de cada versión.

El adaptador `backend/app/services/sat_catalogs/sat_xls_source.py` abre archivos sólo en lectura (`openpyxl` para XLSX y `xlrd==2.0.1` para XLS), detecta la fila real de encabezados, descarta títulos/notas/filas vacías y preserva ceros iniciales. No ejecuta fórmulas, macros ni enlaces externos. `c_CodigoPostal` se ensambla desde sus dos hojas oficiales y `c_TasaOCuota` conserva la tasa oficial; cuando una misma tasa pertenece a varias reglas, las reglas adicionales se desambiguan con sus atributos fiscales, mientras que `0.160000` permanece como clave consultable.

### Fuente SQLite inicial

La carga inicial usa [catalogs.db](/Users/saulcortes/Desktop/myc_erp/backend/resources/sat/catalogs.db), una base SQLite 3.x descargada manualmente y abierta con `mode=ro`. La release registrada es `v10.11.20260703`; sus checksums de distribución están en `backend/resources/sat/CHECKSUMS.txt`.

El adaptador `backend/app/services/sat_catalogs/sqlite_source.py` sólo permite leer las tablas CFDI 4.0 mapeadas, exige `id` como clave y convierte sus filas en registros del importador existente. No ejecuta el archivo SQL/SQLite sobre PostgreSQL, ni crea una fuente maestra paralela.

## Importación

Archivos manuales CSV UTF-8, JSON y XLSX:

```bash
cd backend
python scripts/import_sat_catalogs.py currencies /ruta/c_Moneda.csv --version 2026-01-01 --publication-date 2026-01-01 --user-id 1
```

Fuente SQLite inicial:

```bash
cd backend
python scripts/import_sat_sqlite_catalogs.py --source resources/sat/catalogs.db --publication-date 2026-07-03
```

Fuente oficial SAT y reporte previo obligatorio:

```bash
cd backend
python scripts/import_sat_official_xls_catalogs.py \
  --source "resources/sat/catalogo sat.xlsx" \
  --version 20260703 \
  --publication-date 2026-07-03 \
  --compare-only
```

Después de revisar las diferencias, la activación se confirma explícitamente y se ejecuta como una sola transacción:

```bash
python scripts/import_sat_official_xls_catalogs.py \
  --source "resources/sat/catalogo sat.xlsx" \
  --version 20260703 \
  --publication-date 2026-07-03 \
  --activate --allow-differences
```

El comando genera los reportes `resources/sat/reports/sat_official_xls_comparison.json` y `sat_official_xls_import.json`. Las versiones se insertan como `staged`; sólo `--activate` archiva la versión operativa anterior y activa la nueva dentro de la misma transacción. Si falla cualquier catálogo, se revierte toda la carga staged y la versión anterior continúa siendo operativa.

`--catalog currencies` limita la carga a uno de los catálogos; por omisión se procesan todos los mapeados. La versión SQLite se obtiene de `VERSION.txt`; la fuente Excel se detecta desde un nombre con fecha o se exige mediante `--version`.

El importador valida archivo/formato, clave obligatoria, claves vacías o duplicadas, checksum y versión. Cada catálogo se inserta en su propia transacción: una falla revierte íntegramente ese catálogo y no borra importaciones previas. El mismo checksum devuelve `skipped`.

## Búsqueda, vigencia e índices

Se almacenan `normalized_code`, `normalized_name` y `search_text` sin acentos, mayúsculas ni puntuación para buscar equivalencias como `termómetro`, `termometro` y `TERMOMETRO`. El nombre y la descripción oficiales se conservan intactos.

Las claves tienen índices B-tree, incluido un índice compuesto de versión y clave normalizada para coincidencias y prefijos; la consulta considera vigencia mediante `valid_from`/`valid_until` e índices por versión-vigencia. PostgreSQL cuenta además con un índice GIN full-text sobre `search_text`, construido sólo con funciones nativas (`simple`); no se habilitaron extensiones `unaccent` ni `pg_trgm` porque el proyecto no las usaba y podrían requerir privilegios operativos adicionales.

`active_only=true` es el valor predeterminado y filtra registros inactivos, futuros o vencidos. Los históricos permanecen consultables con `active_only=false` y seleccionando `version_id`.

## Favoritos y alias MYC

`sat_catalog_favorites` guarda favoritos por usuario y registro, con notas opcionales. `sat_catalog_aliases` guarda alias internos activos, normalizados y únicos por registro; no cambia el contenido oficial SAT. Ambos participan en la búsqueda: los favoritos se priorizan y se puede solicitar `favorites_only=true`.

Permisos:

- `sat_catalogs.read`: consulta de catálogos, versiones, registros y aliases.
- `sat_catalogs.manage_favorites`: marcar o quitar favoritos propios.
- `sat_catalogs.manage_aliases`: crear o eliminar aliases internos.

## API

- `GET /api/sat-catalogs`
- `GET /api/sat-catalogs/{catalog_code}/versions`
- `GET /api/sat-catalogs/{catalog_code}/records?search=...&active_only=true&favorites_only=false&version_id=...&offset=0&limit=50`
- `POST|DELETE /api/sat-catalogs/records/{record_id}/favorite`
- `GET|POST /api/sat-catalogs/records/{record_id}/aliases`
- `DELETE /api/sat-catalogs/aliases/{alias_id}`

No hay endpoint de importación desde frontend.

## Agregar un catálogo

1. Añadir su definición en `backend/app/services/sat_catalogs/definitions.py`.
2. Crear una migración que registre su semilla en `sat_catalogs` si el entorno ya está desplegado.
3. Si hay fuente Excel oficial, agregar un mapeo explícito en `sat_xls_source.py`; si hay respaldo SQLite, agregar también su mapeo en `sqlite_source.py`. Los adaptadores rechazan hojas/tablas incompatibles.
4. No se requieren cambios a las tablas, parser ni API genérica.

## Resultado de la carga oficial 20260703

La importación oficial activó 16 catálogos. El reporte de comparación quedó en [sat_official_xls_import.json](/Users/saulcortes/Desktop/myc_erp/backend/resources/sat/reports/sat_official_xls_import.json): 12 catálogos coincidieron con SQLite; `postal_codes` contiene una clave adicional y `units` presenta diferencias de texto; `voucher_types` y `tax_rates` no existían en el respaldo SQLite y ahora se consultan localmente. El Excel prevalece de forma explícita tras la revisión.

Se validaron, mediante el servicio y los endpoints locales autenticados, `81141504`, `E48`, `I`, `G03`, `601`, `03`, `PUE`, `MXN`, `02`, `002`, `Tasa`, `0.160000`, `01` y `45116`. Las búsquedas posteriores al índice compuesto midieron aproximadamente 2–86 ms para clave exacta y 7 ms para `calibracion` en Productos y servicios en la base local de desarrollo.

## Limitaciones conocidas

`cancellation_reasons`/Motivos de cancelación continúa sin hoja en el archivo oficial recibido y queda preparado para una fuente posterior. Las búsquedas por fragmentos muy cortos pueden requerir ajustes de ranking o `pg_trgm` en un sprint posterior si las métricas reales lo justifican.
