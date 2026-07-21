> Estado: AUDITORÍA
>
> Tipo: Auditoría
>
> Autoridad: Baja; fotografía del Toolkit al 2026-07-14
>
> Prevalece sobre: auditorías de Toolkit anteriores al corte
>
> Reemplazado para pendientes vigentes por: `../project/TECHNICAL_DEBT.md`

# Auditoría integral — MYC System Toolkit

Fecha de auditoría: 2026-07-14. Alcance: lectura de scripts y documentación; no se ejecutaron operaciones de arranque, parada, restauración, seed, SAT, `dropdb` ni cambios de configuración.

## 1. Resumen ejecutivo

El Toolkit está compuesto por un wrapper no interactivo, un menú Bash y scripts auxiliares. El punto de entrada de menú real es `scripts/myc.sh`; `scripts/myc` es un wrapper de subcomandos que usa esa ruta para `menu`. Ambos usan la misma ruta absoluta `/Users/saulcortes/Desktop/myc_erp` y no son portables tal como están.

Ya existen operaciones de desarrollo, build, actualización, backup, migraciones, restore y un seed específico de equipos. No existe una inicialización completa del ERP, ni creación/eliminación controlada de base, ni importación SAT en el menú. Hay scripts SAT seguros fuera del Toolkit, listos para integrarse posteriormente.

## 2. Punto de entrada real

| Entrada | Ruta | Tecnología | Uso |
| --- | --- | --- | --- |
| Wrapper CLI | `scripts/myc:1-21` | Bash | `scripts/myc local|tunnel|doctor|…`; `menu` o sin argumento abre el menú. |
| Menú interactivo | `scripts/myc.sh:1-149` | Bash | `scripts/myc.sh` o `scripts/myc menu`. |
| Configuración auxiliar | `scripts/config.sh:1-18` | Bash | La consumen los scripts bajo `scripts/toolkit/`. |

No se encontró instalador de alias o función shell, Makefile, toolkit Windows, `.ps1`, `.bat` o `.cmd`. `venv/bin/Activate.ps1` pertenece al entorno virtual, no es un Toolkit Windows. Hay una sola implementación de menú activa; el wrapper y el menú se solapan parcialmente.

## 3. Archivos relacionados

`scripts/myc`, `scripts/myc.sh`, `scripts/config.sh`, `scripts/{start-local,start-tunnel,stop,restart-local,build,update,backup-db,clean,doctor,status}.sh`, `scripts/toolkit/db/{backup,current,downgrade,heads,history,restore,revision,upgrade}.sh`, `scripts/toolkit/dev/{backend,build,check,frontend}.sh`, `scripts/toolkit/git/{branch,history,status}.sh`, `scripts/toolkit/seed/{equipment.sh,equipment.py}`, `backend/scripts/{import_sat_catalogs,import_sat_sqlite_catalogs,import_sat_official_xls_catalogs}.py`, `README.md`, `backend/.env.example` y `backend/requirements.txt`.

## 4. Menú actual

Transcripción literal de `scripts/myc.sh:104-120`:

```text
1) Desarrollo local
2) Desarrollo túnel
3) Doctor
4) Estado
5) Reiniciar local
6) Build
7) Actualizar
8) Backup BD
9) Limpiar
10) Base de datos
11) Desarrollo
12) Git
13) Seed
0) Salir
```

### Mapa de opciones

| Opción | Etiqueta | Función/bloque | Script/comando final | Entradas | Riesgo |
| --- | --- | --- | --- | --- | --- |
| 1 | Desarrollo local | `case 1` | `start-local.sh` → copia `.env.dev`, Uvicorn con reload, Vite | Ninguna | Medio: modifica `.env.local`, deja backend dependiente de terminal. |
| 2 | Desarrollo túnel | `case 2` | `start-tunnel.sh` → copia `.env.tunnel`, Vite | Ninguna | Medio: modifica `.env.local`; no inicia Cloudflare. |
| 3 | Doctor | `case 3` | `doctor.sh` | Enter posterior | Bajo, aunque consulta DB mediante Alembic. |
| 4 | Estado | `case 4` | `status.sh` | Enter posterior | Bajo. |
| 5 | Reiniciar local | `case 5` | `restart-local.sh` → `stop.sh` → `start-local.sh` | Ninguna | Alto: mata procesos por puerto y cambia `.env.local`. |
| 6 | Build | `case 6` | `build.sh` | Enter posterior | Medio: ejecuta `alembic upgrade head`. |
| 7 | Actualizar | `case 7` | `update.sh` | Enter posterior | Alto: `git pull`, instalaciones y migraciones. |
| 8 | Backup BD | `case 8` | `backup-db.sh` → `pg_dump erp_myc` | Enter posterior | Bajo, pero no verifica fallo/tamaño. |
| 9 | Limpiar | `case 9` | `clean.sh` | Enter posterior | Medio: elimina cachés y `frontend/dist`. |
| 10 | Base de datos | `db_menu` | Submenú documentado abajo | Según opción | Varía. |
| 11 | Desarrollo | `dev_menu` | Submenú documentado abajo | Según opción | Bajo/medio. |
| 12 | Git | `git_menu` | Submenú documentado abajo | Según opción | Bajo; `branch.sh` puede crear/cambiar rama si se invoca directo. |
| 13 | Seed | `seed_menu` | `equipment.sh` → `equipment.py` | ID ETS, cantidad | Medio: inserta equipos de prueba. |

Submenú BD (`scripts/myc.sh:10-42`): aplicar migraciones, current, history, heads, crear revisión, downgrade, backup y restore. El downgrade solicita revisión destino; restore solicita ruta de `.sql`. Submenú Desarrollo (`:45-66`): backend, frontend, build y validaciones. Submenú Git (`:69-89`): status, historial y ramas. Seed (`:92-101`) solicita ETS y cantidad.

## 5. Flujo actual

```text
scripts/myc
 ├── local      → scripts/start-local.sh → Uvicorn :8000 + npm run dev
 ├── tunnel     → scripts/start-tunnel.sh → npm run dev
 ├── doctor     → scripts/doctor.sh
 ├── status     → scripts/status.sh
 ├── backup     → scripts/backup-db.sh → pg_dump erp_myc
 └── menu/""    → scripts/myc.sh
                 ├── 10 Base de datos → scripts/toolkit/db/*.sh
                 ├── 11 Desarrollo    → scripts/toolkit/dev/*.sh
                 ├── 12 Git           → scripts/toolkit/git/*.sh
                 └── 13 Seed          → seed/equipment.sh → equipment.py
```

## 6. Funciones internas y reutilizables

| Nombre | Archivo | Responsabilidad / invocador | Reutilizable |
| --- | --- | --- | --- |
| `db_menu` | `scripts/myc.sh:5-42` | Enruta las ocho operaciones DB; invocada por opción 10. | No directamente; es UI interactiva. |
| `dev_menu` | `scripts/myc.sh:45-66` | Enruta backend, frontend, build y checks; opción 11. | No directamente. |
| `git_menu` | `scripts/myc.sh:69-89` | Enruta status, history, branch; opción 12. | No directamente. |
| `seed_menu` | `scripts/myc.sh:92-101` | Solicita parámetros y dispara seed de equipos; opción 13. | No; interactiva. |
| `seed_equipment` | `scripts/toolkit/seed/equipment.py:14-60` | Crea equipos de prueba respetando capacidad de OT. | Sí, sólo para pruebas por ETS. |
| `main` | `seed/equipment.py:63-73`, scripts SAT | Parseo CLI. | Sí, como patrón CLI, no como función shell. |

Los auxiliares de BD y desarrollo no definen funciones Bash: ejecutan una responsabilidad concreta con variables de `config.sh`. Los scripts no usan `set -u`, `pipefail` ni `trap`; sólo DB usa `set -e` (`scripts/toolkit/db/*.sh`).

## 7. Rutas, entorno virtual y compatibilidad

`scripts/config.sh:3-18` exporta `PROJECT_ROOT`, directorios, binarios del venv y puertos. El valor de `PROJECT_ROOT` es absoluto. También lo repiten `myc`, `myc.sh`, `doctor`, `backup-db`, `restart-local`, `clean`, `update`, `build`, `start-local`, `start-tunnel` y `status` (este último en `:17`). El Toolkit sólo funciona desde otro directorio porque cada script hace `cd` o llama rutas absolutas; fallará si el proyecto se mueve o cambia de usuario.

La ruta efectiva de entorno virtual es `ROOT/venv`, usada como `../venv/bin/*` en scripts antiguos y como `$VENV_DIR/bin/*` en auxiliares. `README.md:29-35` instruye crear `backend/.venv`, una discrepancia con el Toolkit. No se hace `source activate`; se invocan binarios directamente. No hay lógica Windows, PowerShell ni Git Bash. El shell declarado es Bash, compatible en macOS si Bash está disponible.

## 8. Base de datos y migraciones

La URL de referencia está en `backend/.env.example:4` y usa PostgreSQL local con base `erp_myc`; `backup-db.sh:13` usa `pg_dump erp_myc` sin URL, usuario ni host explícitos. Restore usa `DATABASE_URL` si está exportada o `postgresql://localhost:5432/erp_myc` (`toolkit/db/restore.sh:18-20`). No hay `createdb`, `dropdb`, `psql` para cerrar conexiones, ni confirmación/backup previo para downgrade o restore.

Alembic se ejecuta desde `backend` mediante `$ALEMBIC` en los auxiliares (`db/upgrade.sh:6-9`, `current.sh:6-13`) y mediante `../venv/bin/alembic` en scripts antiguos (`build.sh:16`, `update.sh:18`, `doctor.sh:24`). `build.sh` y `update.sh` aplican `upgrade head`; por tanto no son verificaciones puramente no mutantes. `current.sh` muestra actual y heads pero no compara ni informa explícitamente si divergen.

## 9. Seed, SAT y configuración institucional

La opción Seed sólo crea equipos de prueba (`equipment.py:14-60`), exige ETS y órdenes activas y no es idempotente: cada ejecución agrega equipos con las mismas secuencias/prefijo y puede agotar capacidad. No crea roles, usuarios, administrador ni configuración institucional.

No existe opción SAT en el menú. Sí existen tres CLI Python:

- `backend/scripts/import_sat_catalogs.py:19-37`: importa un catálogo manual con catálogo, archivo y versión.
- `backend/scripts/import_sat_sqlite_catalogs.py:27-51`: importa SQLite de sólo lectura, por catálogo o todos; emite JSON y evita fuentes repetidas por checksum.
- `backend/scripts/import_sat_official_xls_catalogs.py:38-113`: inspecciona, compara con SQLite, stagea y sólo activa explícitamente; bloquea diferencias sin `--allow-differences` (`:69-70`).

Comando recomendado para la fuente oficial, tras aplicar migraciones y desde `backend`:

```bash
../venv/bin/python scripts/import_sat_official_xls_catalogs.py \
  --source resources/sat/catCFDI_V_4_20260703.xls \
  --sqlite-source resources/sat/catalogs.db \
  --activate
```

El archivo oficial escribe reporte JSON por defecto, diferencia stage/activación y maneja rollback. El Toolkit no conoce versión, fuente ni progreso SAT.

La configuración institucional sí se crea de forma perezosa por `get_or_create_institutional_configuration` cuando la usa el dominio; no hay bootstrap explícito en Toolkit. La creación de administrador existe como servicio/API, no como seed CLI.

## 10. Backups y restore

`scripts/backup-db.sh:3-15` crea `backups/erp_myc_YYYY_MM_DD_HHMM.sql`; no comprime, rota, valida tamaño o valida el exit status de `pg_dump` (el script no usa `set -e`). Restore sólo comprueba que exista un archivo y ejecuta `psql URL -f FILE`; no recrea base, no confirma, no toma backup previo y no ejecuta Alembic después.

Backups detectados: 10 de 2026-07-07, 6 de 2026-07-08, 9 de 2026-07-13 y 6 de 2026-07-14, además de `backup_erp_myc_antes_prueba.sql` en la raíz. Los actuales van de ~432 KB a 125 MB. `clean.sh` no elimina backups.

## 11. Doctor y Estado

Doctor (`scripts/doctor.sh:1-46`) revisa directorios backend/frontend/venv, versión Python, `compileall`, `alembic current`, importación FastAPI, Node/npm, existencia y clave `VITE_API_URL` de `.env.local`, rama y estado Git. No usa `set -e` y sigue mostrando resultados tras fallos; no modifica archivos directamente, pero `alembic current` toca la conexión DB. No revisa PostgreSQL con `pg_isready`, dependencias instaladas, puertos, storage, Cloudflare, SAT, head Alembic, backups, variables backend, administrador o configuración institucional.

Estado (`scripts/status.sh:1-23`) ejecuta `lsof` en 8000, 5173 y Git. No detecta el puerto configurado 5174 (`config.sh:15`), túnel, DB, Alembic, SAT, último backup o logs. Es rápido y no mutante, salvo la lectura Git.

## 12. Procesos, puertos y manejo de errores

- `start-local.sh:7-21` arranca Uvicorn sin `--host` ni `--port` explícitos (depende de defaults), lo deja en segundo plano y ejecuta Vite en primer plano. Si Vite falla, intenta `kill $BACKEND_PID`; no hay `trap` para Ctrl+C.
- `start-tunnel.sh:7-11` sólo cambia `.env.local` y ejecuta Vite; no inicia Cloudflare pese a su etiqueta.
- `stop.sh:5-21` mata todo proceso que escuche en 8000 y 5173. Puede matar servicios ajenos y no cubre 5174 ni tunnel.
- `clean.sh:7-11` usa `rm -rf` sobre `__pycache__`, `frontend/dist` y caché Vite, sin confirmación.
- `update.sh:12-29` y `build.sh:12-30` abortan en errores críticos con `|| exit 1`, pero son mutantes.
- DB auxiliares usan `set -e`; varios además hacen `read`, y el menú vuelve a hacer `read`, dando pausas duplicadas para backup/current/heads/history/upgrade/downgrade/restore.

## 13. Duplicaciones

| Duplicación | Archivos/líneas | Impacto |
| --- | --- | --- |
| Raíz absoluta | `scripts/myc:3`, `myc.sh:3`, `config.sh:3`, scripts antiguos | No portable y requiere edición múltiple. |
| Invocación Alembic | `doctor.sh:24`, `build.sh:16`, `update.sh:18`, `toolkit/db/upgrade.sh:9` | Inconsistencia de binario y comportamiento. |
| Build/check | `build.sh`, `toolkit/dev/build.sh:5`, `toolkit/dev/check.sh:5-9` | Build se reenvía y check solapa compile/build. |
| Backup | `myc.sh:136`, `toolkit/db/backup.sh:7`, `backup-db.sh:13` | Dos capas y pausas repetidas. |
| Detección procesos | `status.sh:8-13`, `stop.sh:5-16` | Puertos distintos de `config.sh`. |
| Carga config | Todos los auxiliares Toolkit usan `source config.sh`; antiguos repiten valores. | Dos convenciones activas. |

## 14. Matriz de capacidades

| Capacidad | Existe | Archivo | Función | Estado | Reutilizable | Observaciones |
| --- | --- | --- | --- | --- | --- | --- |
| Desarrollo local | Sí | `start-local.sh` | script principal | Parcial | Sí, con correcciones | Cambia env y no fija puertos. |
| Desarrollo túnel | Sí | `start-tunnel.sh` | script principal | Parcial | Sí | No inicia túnel. |
| Doctor | Sí | `doctor.sh` | `ok/fail/line` | Parcial | Sí | Sin DB readiness/SAT/head. |
| Estado | Sí | `status.sh` | script principal | Parcial | Sí | Busca 5173, no 5174 configurado. |
| Reiniciar local | Sí | `restart-local.sh` | script principal | Riesgoso | Sí | Mata por puerto. |
| Build | Sí | `build.sh` | script principal | Mutante | Separar check | Aplica migraciones. |
| Actualizar | Sí | `update.sh` | script principal | Mutante | Sí | Pull + installs + migration. |
| Backup | Sí | `backup-db.sh` | script principal | Parcial | Sí | Sin validación de `pg_dump`. |
| Restore | Sí | `toolkit/db/restore.sh` | script principal | Riesgoso | Sí | Sin confirmación/backup previo. |
| Limpiar | Sí | `clean.sh` | script principal | Destructivo limitado | Sí | `rm -rf` sin confirmación. |
| Base de datos | Sí | `myc.sh` | `db_menu` | Parcial | UI no | No crear/eliminar/cerrar conexiones. |
| Migraciones | Sí | `toolkit/db/*.sh` | scripts | Sí | Sí | Upgrade/current/history/heads/revision/downgrade. |
| Seed | Sí | `seed/equipment.py` | `seed_equipment` | Específico | Parcial | Sólo equipos de prueba. |
| Git | Sí | `toolkit/git/*.sh` | scripts | Sí | Sí | Menú sólo lectura. |
| Crear base | No | — | — | Ausente | — | Falta `createdb` controlado. |
| Eliminar base | No | — | — | Ausente | — | Falta flujo confirmado y backup. |
| Cerrar conexiones | No | — | — | Ausente | — | Requerido para reset seguro. |
| Inicializar ERP | No | — | — | Ausente | — | Ver sección 15. |
| Importar SAT | No en Toolkit | scripts SAT Python | `main` | Disponible fuera | Sí | Integrable como submenú. |
| Validar SAT | Parcial fuera | XLS Python | `compare_all_catalog_sources` | Sí | Sí | Sólo CLI/reporte, no menú. |
| Crear administrador | No en Toolkit | API/servicio | `create_user_admin` | Fuera | Sí | No seed CLI. |
| Crear configuración institucional | Parcial | servicio backend | get-or-create | Implícito | Sí | No bootstrap explícito. |
| Verificar Alembic head | Parcial | `db/current.sh` | script | Parcial | Sí | Muestra, no compara. |

## 15. Riesgos prioritarios

1. Ruta absoluta repetida: mover el repositorio rompe el Toolkit.
2. `status`/`stop` usan 5173 mientras config usa 5174; pueden reportar y dejar procesos incorrectamente.
3. Restore y downgrade no solicitan confirmación reforzada ni crean backup previo.
4. Backup puede imprimir “terminado” tras fallo de `pg_dump`, creando archivo vacío/parcial.
5. `start-local` no controla ciclo de vida con `trap`; hay riesgo de backend huérfano.
6. `stop.sh` mata cualquier proceso que use los puertos objetivo.
7. `start-tunnel` no administra Cloudflare; su nombre sobrepromete el comportamiento.
8. README indica `.venv` bajo backend, mientras Toolkit exige `venv` en raíz.
9. `build` muta DB con migraciones, por lo que no es una prueba segura.
10. Variables de entorno de backend y credenciales no son verificadas por Doctor; no se exponen valores en este reporte.

## 16. Qué falta para las siguientes capacidades

**Inicializar ERP:** validación de precondiciones, crear/confirmar base, ejecutar migrations, crear administrador por entrada segura, materializar configuración institucional, importar/activar SAT, comprobaciones post-inicialización e informe idempotente.

**Reiniciar base de datos:** confirmación explícita con nombre de DB, backup validado, cierre de conexiones, drop/create, migrations, restauración opcional/seed explícito, verificación y rollback/documentación de fallos. Ninguna de esas operaciones existe actualmente como flujo compuesto.

**SAT desde Toolkit:** añadir una entrada que invoque los scripts existentes, pida/valide fuente y versión, permita compare-only/stage/activate, muestre el reporte y evite reimportar sin intención. No hace falta reimplementar el importador.

**Restore seguro:** seleccionar sólo archivos dentro de `backups`, confirmar destino, verificar dump y tamaño, tomar backup previo, decidir recreación de DB, ejecutar restore, `alembic current/heads` y validar resultado.

**Doctor:** extraer comprobaciones de sólo lectura para `pg_isready`, conexión/DB, Alembic head, puertos configurados, backend health, frontend URL, Cloudflare, storage escribible, SAT activo/conteos, backup reciente, variables requeridas, admins y configuración institucional.

## 17. Propuesta mínima de arquitectura futura (sin implementar)

Conservar `scripts/myc` como wrapper y `scripts/myc.sh` como UI por ahora. Extraer en `scripts/toolkit/lib/` una sola carga de configuración y funciones `check_postgres`, `run_migrations`, `backup_database`, `restore_backup`, `start_backend`, `start_frontend`, `stop_ports`, `run_doctor` e `import_sat`. Reutilizar `config.sh`, `toolkit/db/upgrade.sh`, `backup-db.sh`, los tres importadores SAT y `get_or_create_institutional_configuration` como bloques de dominio. Las operaciones mutantes deben requerir confirmación y los checks deben ser separados de acciones.

## 18. Archivos a modificar en una fase posterior

`scripts/myc`, `scripts/myc.sh`, `scripts/config.sh`, `scripts/{start-local,start-tunnel,stop,restart-local,build,update,backup-db,clean,doctor,status}.sh`, `scripts/toolkit/db/{backup,current,downgrade,restore,upgrade}.sh`, nuevos auxiliares bajo `scripts/toolkit/lib/`, y, para integrar SAT, `backend/scripts/import_sat_official_xls_catalogs.py` sólo si se necesita una interfaz de parámetros adicional. Para bootstrap administrativo/institucional: un nuevo CLI backend que reutilice `app.services.users.create_user_admin` y `app.services.institutional_configurations.get_or_create_institutional_configuration`; no modificar esos servicios sin una necesidad demostrada.

## 19. Confirmación de no intervención operativa

No se modificó el comportamiento del Toolkit ni se ejecutaron operaciones destructivas. Este archivo es el único artefacto creado como entregable de documentación solicitado.
