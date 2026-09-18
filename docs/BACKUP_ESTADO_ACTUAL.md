> Estado: VIGENTE
>
> Tipo: Snapshot operativo verificable
>
> Autoridad: Media; no sustituye los documentos canónicos de project/
>
> Corte: 2026-09-17 — hotfix post-PR #4

# Estado operativo actual del ERP MYC

## Repositorio y alcance verificado

- Rama: `hotfix/lab-external-ios-crash-and-admin-self-resolve`.
- Base: `main` en `1083e3ef9863f721882592c7cc68335264d6843b`, inicialmente limpia.
- Sin merge ni push. Este trabajo modifica captura/PDF de LAB EXTERNO y
  resolución administrativa de solicitudes propias de folios.
- Mobile usa formulario canónico común y especializa únicamente resultados
  dinámicos; discrimina linked/lab_externo antes de acceder a result_sections.
- El PDF externo comparte renderer, campos y firmas con la hoja general;
  omite logo, cambia título y presenta grupos/tablas con paginación completa.
- Auto-resolución sólo de linked_folio/manual_myc_folio pending para actor
  interno, Administrador activo y lab_folios.resolve. Backend expone la misma
  autoridad a Mobile por login/refresh/me y la revalida al resolver.
- Se conservan grupos, filas, revisiones, validación de completitud y PDF final
  congelado, así como el lifecycle canónico y los controles de otros tickets.

## Migraciones y base de datos

- `alembic heads` del código: `6640c526c412 (head)` único.
- No hay migraciones ni cambios a la base local ERP en este trabajo. Las
  pruebas usan SQLite aislado, incluido el startup de FastAPI; no se ejecutó
  upgrade ni reset sobre la base ERP.
- No se comprobó `alembic current` de la base ERP ni su respaldo. No se
  regeneró `backup_erp_myc_antes_prueba.sql`, porque no se modificó esa base.
- La primera ejecución con sandbox bloqueó conexiones locales del startup;
  se sustituyó ese entorno por una base temporal, sin cambiar los tests para
  ocultar incompatibilidades.

## Validación y pendientes

- Reproducción en la base: el test del componente al abrir linked/289, OT 6471,
  con groups y sin result_sections lanza TypeError al evaluar sections.map.
- Con el hotfix: apertura sin excepción y captura común disponible.
- TypeScript y lint Mobile sin errores; suite Mobile: 669/669; wiring: 92/92.
- Backend focalizado: 158 passed, 1 skipped (concurrencia opt-in).
- Suite backend completa: 1235 passed, 16 skipped, 19 subtests passed.
- Evidencia final: [cierre post-PR #4](closures/LAB_EXTERNAL_POST_PR4_HOTFIX_2026-09-17.md).
- PDF general y externo comparados por campos comunes; 100 filas externas
  completas en tres páginas, encabezados repetidos y firmas; revisión visual
  de todas las páginas de ambos documentos con datos sintéticos.
- Pendiente QA iPhone/TestFlight y concurrencia PostgreSQL opt-in; no se
  verificó aquí una nueva build release ni los archivos .ips originales.
- Deuda preexistente: test de Mantenimiento puede confundir `80` dentro de un
  timestamp con un costo interno. Ver `project/TECHNICAL_DEBT.md`.
- El módulo LAB conserva su estado `EN DESARROLLO`; este corte no lo sella.

## Autoridades documentales

`project/DOCUMENTATION_INDEX.md` rige la jerarquía. Estado global en
`project/PROJECT_STATUS.md`; alcance, flujo, reglas y decisiones en los
canónicos correspondientes. Inventario en `PROJECT_FILE_REGISTRY.md`.
El corte anterior permanece trazable en Git y no se presenta como una
verificación actual de ramas, base o validaciones de trabajos anteriores.
