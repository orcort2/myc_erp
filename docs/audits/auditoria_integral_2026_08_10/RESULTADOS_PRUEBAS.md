# Resultados de validaciones — 2026-08-10

No se modificó la base ni se invocaron proveedores externos. Las pruebas usan
SQLite en memoria/temporal o `tmp_path`; la consulta Alembic fue de sólo
lectura sobre la base local.

| Validación | Resultado | Passed | Failed | Observación |
| --- | --- | ---: | ---: | --- |
| `cd backend && ../venv/bin/python -m pytest -q` | OK | 450 + 19 subtests | 0 | 3 warnings |
| `node --test $(find src ... '*.test.js')` | OK | 40 | 0 | 10 archivos |
| `npm run build` | OK | 1 build | 0 | chunk JS >500 kB |
| `compileall` backend/tests/SDK | OK | 1 | 0 | sin error de sintaxis |
| `pip check` | OK | dependencias consistentes | 0 | cache pip no escribible, no bloquea |
| `npm audit --omit=dev` | FALLÓ | — | 2 altas | nanoid y postcss |
| `scripts/myc doctor` | OK | 10 checks | 0 | PostgreSQL/LibreOffice/Node disponibles |
| `scripts/toolkit/db/current.sh` | OK | head único | 0 | `c8a51e2d7f40` |
| `alembic check` | OK | sin drift | 0 | sólo lectura |
| dump `alembic_version` | OK | alineado | 0 | `c8a51e2d7f40` |
| `validate_capability_catalog.py --check` | FALLÓ | — | 1 gate | 20 gaps catálogo, 2 bootstrap |
| inventario FastAPI runtime↔CSV | OK | 356 | 0 | cubierto por pytest |
| `git diff --check` inicial | OK | — | 0 | árbol sólo tenía `D frontend.zip` |

## Métricas del build

- 1,724 módulos transformados.
- JS: 1,040.31 kB; gzip 264.38 kB.
- CSS: 347.52 kB; gzip 59.50 kB.
- fondo: 2,484.90 kB.

## Warnings backend

1. Starlette depreca la integración actual `httpx`/`TestClient` y recomienda
   `httpx2`.
2. `crypt` usado por passlib será retirado de Python 3.13.
3. Alembic advierte `prepend_sys_path` sin `path_separator`.

## Pruebas no ejecutadas o inexistentes

- no hay script `npm test`, lint ni type-check declarados;
- no hay E2E browser, accesibilidad, carga o concurrencia integral;
- no se ejecutó Facturama Sandbox/Producción, correo, Drive ni API externa;
- no se repitió downgrade/upgrade/restore porque crea/modifica bases; se cita
  el drill exitoso del 2026-08-05 sin presentarlo como ejecución actual;
- `pip-audit` no está instalado; CVE Python no verificadas;
- no se verificó cobertura porcentual.

## Lectura de los resultados

Las suites verdes validan contratos importantes, pero no cubren el camino
HTTP real de todas las mutaciones. Esto explica que la duplicación del router
ETS, el actor nulo y el gate institucional fallido coexistan con 490 tests
aprobados. Ninguna cifra de tests autoriza por sí sola el despliegue.

