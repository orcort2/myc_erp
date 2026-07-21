> Estado: CIERRE TÉCNICO
>
> Tipo: Cierre técnico
>
> Autoridad: Media para la evidencia de carga inicial; no determina la versión SAT vigente por sí solo
>
> Prevalece sobre: ninguno
>
> Arquitectura vigente relacionada: `../architecture/CATALOGOS_SAT.md`

# Reporte de carga inicial de Catálogos SAT

Fecha: 2026-07-14  
Fuente: `backend/resources/sat/catalogs.db` (SQLite 3.53.2, abierto en modo sólo lectura)  
Release: `v10.11.20260703` — publicada aparente: 2026-07-03.

## Diagnóstico de la fuente

Se inspeccionó el esquema SQLite sin ejecutarlo ni alterarlo. Las tablas utilizadas son `cfdi_40_*`, todas con clave primaria/columna `id` de tipo `TEXT`; las fechas de vigencia son `TEXT` (`vigencia_desde`, `vigencia_hasta`) y son normalizadas a `DATE` durante la importación. La fuente cubre CFDI 4.0 para los 14 catálogos de la tabla siguiente. No contiene una tabla de motivos de cancelación.

No se encontraron claves vacías ni duplicadas en las tablas mapeadas. Todas las tablas salvo `cfdi_40_tipos_factores` tienen `texto` oficial; ese catálogo no incluye descripción en su propia fuente y se conserva así. Los campos adicionales oficiales se preservan en `data`.

| Catálogo | Tabla origen | Detectados | Válidos | Rechazados | Duplicados | Versión | Checksum SHA-256 | Estado |
|---|---|---:|---:|---:|---:|---|---|---|
| Productos/servicios | `cfdi_40_productos_servicios` | 52,513 | 52,513 | 0 | 0 | v10.11.20260703 | `06e7ef74b42890ee9bc1735ef9558795455f1464ac49ce7134779ab01076b130` | Importado previamente; reintento `skipped` |
| Unidades | `cfdi_40_claves_unidades` | 2,418 | 2,418 | 0 | 0 | v10.11.20260703 | `24e60a4471b09a1c0b745c3b80ee56a3499ac65b0a0cefad7783a6b032989340` | Importado |
| Régimen fiscal | `cfdi_40_regimenes_fiscales` | 19 | 19 | 0 | 0 | v10.11.20260703 | `c9cf372708f8569af8e77d5e5e9d65c070c3845eae6348fac2739b4210902f62` | Importado |
| Uso CFDI | `cfdi_40_usos_cfdi` | 24 | 24 | 0 | 0 | v10.11.20260703 | `be3118e4e88554e5c467c7abb901b03beb2e7efb4f5495cbde46bb8193df7126` | Importado |
| Forma de pago | `cfdi_40_formas_pago` | 22 | 22 | 0 | 0 | v10.11.20260703 | `20bf1b461a5b02ced65f81bd2bcecaae23a0139e3dc95cf7471bfaa516c20f0a` | Importado |
| Método de pago | `cfdi_40_metodos_pago` | 2 | 2 | 0 | 0 | v10.11.20260703 | `4ceccadca860db04477f4be441798c82de966590bb65cb94cf3c286d736be284` | Importado |
| Monedas | `cfdi_40_monedas` | 183 | 183 | 0 | 0 | v10.11.20260703 | `ed37517496c1e1079590e3010cd386435dc3fd4d1dac3ab096b6dcb86c0a70c9` | Importado |
| Países | `cfdi_40_paises` | 250 | 250 | 0 | 0 | v10.11.20260703 | `1cc2fd80af33c8d68a6bb1984157c487dfce724738f641020fff9a053fd0baa3` | Importado |
| Código postal | `cfdi_40_codigos_postales` | 95,748 | 95,748 | 0 | 0 | v10.11.20260703 | `3580f0fb266ef6ba2a572bf24b93423c93756af1e7a527857c2ede125743a5ef` | Importado |
| Objeto de impuesto | `cfdi_40_objetos_impuestos` | 8 | 8 | 0 | 0 | v10.11.20260703 | `c4ae439feeb29f0c30b58947180590a82599b4ea4967ac7328652360cc2ef892` | Importado |
| Tipo de relación | `cfdi_40_tipos_relaciones` | 7 | 7 | 0 | 0 | v10.11.20260703 | `e01b0b879343005ff539c70f8d09a7132fc7c5ba891b8ea4b1fb670b5cc2ac72` | Importado |
| Exportación | `cfdi_40_exportaciones` | 4 | 4 | 0 | 0 | v10.11.20260703 | `9ffe87821ed55980aa0dc496df1b9acc932146dbf68d4310e6cd8f8851639a8b` | Importado |
| Impuestos | `cfdi_40_impuestos` | 3 | 3 | 0 | 0 | v10.11.20260703 | `99f9ad25c152078a44e1ca8a90f87bf2a080d4a6e988c5e27bc59aaf3f2915bb` | Importado |
| Tipo de factor | `cfdi_40_tipos_factores` | 3 | 3 | 0 | 0 | v10.11.20260703 | `00d79bb1a2b1cf88caff69269c705a4cd1f59869875b8b6909f6349240185a19` | Importado |
| Motivos de cancelación | No presente | 0 | 0 | 0 | 0 | — | — | Pendiente de fuente oficial |

## Resultado y decisiones

- Se conservaron 151,204 registros vigentes de 151,204 importados.
- La carga de 14 catálogos tomó 10.263 s; Productos/Servicios ya había concluido correctamente antes de que una descripción extensa de Unidades provocara rollback exclusivo de ese catálogo. Tras ampliar la columna a `TEXT`, el reintento lo detectó por checksum y no lo duplicó.
- El mapeo usa `id → code`, `texto → name`, `vigencia_desde → valid_from`, `vigencia_hasta → valid_until`; el resto se conserva en JSON `data`.
- La fuente es compatible con CFDI 4.0 para los catálogos importados. No se importaron tablas de complementos, comercio exterior, nómina u otras no requeridas.
- Se añadió índice B-tree de clave/versión/vigencia y GIN full-text de PostgreSQL sobre texto normalizado; no se instalaron extensiones.

## Rendimiento de referencia

Mediciones locales de consulta paginada con 20 resultados máximos, realizadas después de la carga: búsqueda de `termometro` en Productos/Servicios: ~381 ms; clave `01000` en Códigos Postales: ~496 ms. Son mediciones de una sola ejecución local y deben volver a medirse bajo carga antes de definir objetivos de producción.

## Riesgos y limitaciones

- Falta la fuente oficial de motivos de cancelación.
- Algunas descripciones oficiales superan 500 caracteres; se migraron a `TEXT` sin truncamiento.
- No se modificaron Clientes, Cotizaciones, Catálogo MYC, Facturación ni se integró Facturama.
