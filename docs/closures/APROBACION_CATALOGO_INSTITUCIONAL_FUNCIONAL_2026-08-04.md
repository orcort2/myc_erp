> Estado: APROBADO Y CERRADO
>
> Fecha: 2026-08-04
>
> Tipo: cierre documental de aprobación institucional
>
> Autoridad aprobada: `CATALOGO_INSTITUCIONAL_FUNCIONAL_ERP_MYC.md`, versión 1.0

# Aprobación del Catálogo Institucional Funcional

## Dictamen

El Catálogo Institucional Funcional del ERP MYC queda **APROBADO Y CONGELADO
COMO AUTORIDAD FUNCIONAL** en su versión 1.0. La aprobación comprende 42
módulos, 181 acciones y 657 microacciones con identificadores únicos y
metadatos completos de naturaleza, criticidad y alcance permitido.

Este cierre es exclusivamente documental. No implementa RBAC dinámico, no
crea roles o asignaciones, no modifica `permissions.py` y no cambia backend,
frontend, modelos, migraciones, datos ni comportamiento.

## Integridad del catálogo aprobado

| Verificación | Resultado |
| --- | ---: |
| Módulos | 42 |
| Acciones | 181 |
| Microacciones | 657 |
| IDs de acción duplicados | 0 |
| Microacciones con naturaleza | 657/657 |
| Microacciones con criticidad | 657/657 |
| Microacciones con alcance | 657/657 |
| Descripciones de microacción modificadas al agregar metadatos | 0 |
| Marcas modificadas al agregar metadatos | 0 |
| Celdas de permisos modificadas al agregar metadatos | 0 |

## Distribución por naturaleza

| Naturaleza | Microacciones |
| --- | ---: |
| lectura | 195 |
| mutación | 105 |
| autorización | 68 |
| ejecución | 171 |
| configuración | 61 |
| administración | 51 |
| efecto automático | 6 |
| **Total** | **657** |

## Distribución por criticidad

| Criticidad | Microacciones |
| --- | ---: |
| N0 pública | 3 |
| N1 operativa | 159 |
| N2 sensible | 264 |
| N3 crítica | 151 |
| N4 gobernanza institucional | 80 |
| **Total** | **657** |

## Distribución por alcance permitido

Una microacción puede admitir más de un alcance; por ello esta tabla cuenta
asociaciones de alcance y su total excede las 657 microacciones.

| Alcance | Microacciones que lo admiten |
| --- | ---: |
| global | 42 |
| organización | 252 |
| sucursal | 0 |
| área | 409 |
| propio | 147 |
| asignado | 363 |
| cliente vinculado | 81 |
| registro explícito | 392 |
| por resolución | 43 |
| no aplica | 9 |
| **Asociaciones totales** | **1,738** |

## Criterios críticos y excepciones documentadas

- Roles, atribuciones y concesiones individuales; folios; manejo de
  credenciales; emisión, cancelación y sustitución fiscal; liberación;
  eliminación definitiva; resoluciones gobernadas; respaldos y recuperación
  se clasificaron como N4.
- Las consultas, descargas o recuperaciones documentales asociadas a una
  capacidad crítica permanecen en N1, N2 o N3 cuando no toman por sí mismas la
  decisión crítica.
- La configuración no confidencial y las pruebas de conexión de integraciones
  son N3; registrar, renovar o revocar credenciales es N4.
- Las eliminaciones restringidas a borradores o sujetas a una política de
  retención no se equiparan automáticamente con eliminación definitiva.
- Las seis microacciones automáticas usan `efecto automático` y `no aplica`.
  Las tres microacciones públicas también usan `no aplica`, porque no existe un
  sujeto organizacional al cual asignarles alcance.
- `sucursal` queda en cero: el catálogo no contiene una frontera funcional
  verificable por sucursal y esta aprobación no inventa asignaciones.
- Los alcances son límites permitidos, no roles ni asignaciones efectivas. El
  estado del registro permanece como precondición funcional independiente.

## Regla de versionado institucional

Toda microacción aprobada es estable. Un cambio de significado exige marcar la
microacción anterior como deprecada, crear una nueva microacción y conservar
la trazabilidad histórica. No se permite reutilizar silenciosamente un
identificador. Las correcciones puramente editoriales sólo conservan el
identificador si no cambian significado, naturaleza, criticidad, alcance o
relación funcional.

## Validaciones documentales

- Conteos y unicidad verificados sobre el catálogo final.
- Alineación uno a uno verificada entre microacciones y sus tres metadatos.
- Vocabularios cerrados de naturaleza, criticidad y alcance verificados.
- Identidad de microacciones, marcas y celdas de permisos comparada con el
  corte temporal previo a la clasificación.
- `python3 scripts/generate_project_file_registry.py` ejecutado después de
  registrar el cierre.
- `git diff --check` documental requerido antes del commit.

## Documentación actualizada

Se actualizaron el catálogo funcional, `DECISIONS.md`,
`DOCUMENTATION_INDEX.md`, `PROJECT_FILE_REGISTRY.md` y
`BACKUP_ESTADO_ACTUAL.md`. Se creó este cierre. No hubo movimientos, fusiones
ni archivos documentales enviados a archivo histórico.
