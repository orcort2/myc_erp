> Estado: VIGENTE — ETAPA 3
>
> Autoridad: Alta para entrega de archivos

# Ownership y entrega institucional

La existencia de una ruta no autoriza descargarla. La secuencia obligatoria es:

1. resolver identidad con el guard HTTP vigente;
2. exigir el permiso ya declarado para la operación;
3. cargar el registro propietario del archivo;
4. comprobar ownership/tenant, vínculo, visibilidad y precondiciones de estado;
5. resolver el path mediante `require_deliverable_file`;
6. entregar con MIME y nombre derivados del registro autorizado;
7. auditar cuando el contrato del dominio lo requiere.

Actividad conserva `ensure_entity_access`; Portal conserva el cliente derivado
en backend y responde 404 para recursos ajenos; Certificados y Control
Documental conservan sus permisos de lectura. ETAPA 3 no introduce roles,
permisos ni `PortalMembership` y no convierte el path en un identificador
público.

La frontera final rechaza rutas fuera de `STORAGE_ROOT`, symlinks, directorios y
archivos ausentes. Previsualizar no elude ownership y sólo se permite para MIME
de imagen ya validado. Las URLs futuras firmadas deberán ser breves,
revocables, específicas por archivo/operación y emitirse sólo después de esta
misma autorización.
