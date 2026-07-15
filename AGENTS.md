# Instrucciones persistentes del repositorio

Al finalizar cualquier cambio de código, esquema, configuración relevante, prueba, recurso operativo o respaldo, actualizar `docs/BACKUP_ESTADO_ACTUAL.md` en el mismo trabajo. El documento debe describir únicamente el estado verificable actual, incluir pendientes y registrar la migración/validaciones aplicables.

`docs/PROJECT_FILE_REGISTRY.md` es la referencia oficial y obligatoria del inventario funcional del repositorio. Todo archivo nuevo debe registrarse inmediatamente, y todo cambio material de responsabilidad de un archivo existente debe actualizar su fila en el mismo trabajo. Cada registro debe conservar el formato único: ruta, módulo, función, responsabilidad detallada, dependencias principales, quién lo utiliza, criticidad y estado.

No se puede dar por terminado ningún desarrollo, corrección, migración, cambio de configuración, prueba, recurso o script sin sincronizar `docs/PROJECT_FILE_REGISTRY.md`. El inventario sólo debe incluir archivos funcionales, configuración, migraciones, recursos oficiales, pruebas, scripts y documentación relevante; se deben excluir artefactos generados o locales como `.DS_Store`, `__pycache__`, `.pytest_cache`, `node_modules`, `dist`, `build`, `output`, `tmp`, `storage`, `backups` y respaldos. Tras cambios de inventario, ejecutar `python3 scripts/generate_project_file_registry.py`, revisar las filas afectadas, comprobar que las rutas existan y ejecutar `git diff --check`.

Si una migración o un cambio de datos modifica la base local, regenerar también `backup_erp_myc_antes_prueba.sql` y confirmar que su `alembic_version` coincide con el head de Alembic. No incluir secretos, credenciales ni contenido sensible de la base en el documento.
