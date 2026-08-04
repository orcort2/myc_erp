> Estado: VIGENTE — ETAPA 3
>
> Autoridad: Alta para almacenamiento local institucional
>
> Corte: 2026-08-04

# Almacenamiento institucional de archivos

`backend/app/services/storage_service.py` es la única frontera para construir,
resolver, escribir y entregar rutas persistentes locales. `STORAGE_ROOT` puede
ser absoluto o relativo al repositorio, pero ningún valor persistido puede
resolver fuera de esa raíz.

## Invariantes

1. El nombre exterior se valida y el nombre persistido se sanea.
2. Toda ruta se normaliza con `resolve()` y debe ser descendiente de la raíz.
3. Una escritura persistente se realiza en un temporal adyacente, se sincroniza
   y se publica con reemplazo atómico.
4. Una entrega sólo acepta archivo regular no simbólico dentro de la raíz.
5. Permiso, ownership, visibilidad, organización y estado se validan en el
   dominio antes de invocar la frontera final de entrega.
6. Los temporales de conversión/descompresión usan directorios aislados y se
   eliminan aunque la operación falle.
7. Las rutas persistidas son relativas cuando el modelo lo permite; la
   compatibilidad con rutas absolutas históricas dentro de la raíz se conserva.

## Operaciones

- `build_storage_path`: construye destino contenido y crea directorio.
- `atomic_write`: publica bytes completos o no publica nada.
- `save_validated_content`: conserva ruta relativa, nombre original, tamaño y
  SHA-256 de una carga previamente validada.
- `require_deliverable_file`: última barrera antes de `FileResponse`/lectura.
- `delete_if_unreferenced`: elimina sólo tras comprobar referencias ORM y deja
  auditoría; no sustituye políticas de retención.

Los datos operativos y respaldos no pertenecen al control de versiones. Git
contiene código, contratos, pruebas y documentación; la raíz de storage y el
dump requieren custodia operativa separada.
