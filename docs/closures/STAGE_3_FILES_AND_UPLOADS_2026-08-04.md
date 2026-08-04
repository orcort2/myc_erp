> Estado: ETAPA 3 — TERMINADA, EN REVISIÓN
>
> Corte: 2026-08-04
>
> Alcance: archivos, cargas y almacenamiento institucional

# Cierre técnico de ETAPA 3

## Resultado

ETAPA 3 establece una frontera institucional única para validar entradas,
publicar archivos locales y completar entregas ya autorizadas. No cambia
permisos, ownership, estados, folios, modelos, migraciones ni datos. Tampoco
implementa RBAC dinámico, `PortalMembership`, nuevas vistas de Ajustes o
capacidades reservadas del catálogo.

## Implementación cerrada

- perfiles centrales para Actividad, Captura, Plantillas Maestras, PDFs de
  certificado, constancias e importaciones de Clientes;
- lectura acotada y errores 413/415/422 sin rutas internas;
- validación de extensión/MIME/firma y estructura para PDF, imágenes, texto,
  ZIP, OOXML y XML;
- protección ZIP contra traversal, rutas absolutas, duplicados, cifrado,
  enlaces/dispositivos, profundidad, cantidad, tamaño y ratio de expansión;
- escritura atómica con temporal adyacente, `fsync` y `os.replace`;
- SHA-256 y metadatos de tamaño en la frontera de persistencia;
- entrega sólo de archivo regular no symlink bajo `STORAGE_ROOT`, después de
  los controles de dominio existentes;
- validación de base64/XML/PDF al recuperar documentos Facturama;
- publicación atómica del PDF generado/autenticado por Calidad;
- parámetros seguros documentados en `backend/.env.example`;
- retiro del índice Git de 55 archivos `storage/`, el dump de 74,539,344
  bytes, `docs.zip` y cuatro archivos raíz vacíos, conservando físicamente la
  evidencia operativa y sin reescribir historia.

## Validaciones

| Validación | Resultado |
| --- | --- |
| pruebas dirigidas de archivos/seguridad/dominios | 78 passed, 7 subtests |
| suite backend completa fuera del sandbox | 444 passed, 19 subtests, 3 warnings no bloqueantes |
| frontend `node --test` | 31 passed |
| frontend `npm run build` | correcto; warning de chunk >500 kB |
| backend `compileall` | correcto |
| inventario HTTP | coincide con runtime; no se agregaron endpoints |
| Alembic current/check | `f27f8a90b1c3`; sin operaciones nuevas |
| búsquedas de lecturas/escrituras directas | sin cargas multipart no acotadas ni escrituras persistentes directas integradas |
| evidencia operativa tras retirar del índice | dump, `docs.zip` y archivos de storage presentes localmente |
| migraciones/datos/respaldo | sin cambios; no se regeneró dump |

Las dos pruebas reales de LibreOffice fallaron primero con `Abort trap` dentro
del sandbox de macOS; repetidas fuera del sandbox quedaron incluidas en la
suite verde de 444 pruebas. `npm test` no existe como script; la suite oficial
vigente es `node --test`.

## Riesgos y trabajo posterior

- No existe proveedor antimalware aprobado. La validación estructural es
  fail-closed, pero el escaneo/cuarentena externa requiere decisión operativa.
- `STORAGE_ROOT` sigue siendo local. Un backend durable/replicado, cuotas y
  retención avanzada pertenecen a otra etapa.
- Los ZIP de salida se generan en memoria; la entrada no confiable está
  acotada, pero streaming de lotes grandes requiere telemetría y contrato.
- Los modelos sin columna checksum no reciben una migración implícita; la
  frontera lo calcula y los dominios con campo existente lo conservan.
- El warning de bundle frontend y tres deprecaciones de dependencias no son
  regresiones de ETAPA 3.

## Condición de revisión

El cierre técnico puede aprobarse cuando revisión externa confirme: límites
adecuados al volumen real, custodia operativa del dump/storage fuera de Git y
la decisión sobre antimalware/almacenamiento durable. Hasta entonces el estado
es **ETAPA 3 — TERMINADA, EN REVISIÓN**.

## Archivos mínimos para revisión externa

- `backend/app/services/file_security.py`
- `backend/app/services/storage_service.py`
- `backend/app/services/capture_packages.py`
- `backend/app/services/activity.py`
- `backend/app/services/clients.py`
- `backend/app/services/controlled_documents.py`
- `backend/app/services/certificates.py`
- `backend/app/services/certificate_authentication.py`
- `backend/app/services/facturama/invoices.py`
- `backend/tests/test_institutional_file_security.py`
- `docs/architecture/files/INSTITUTIONAL_FILE_STORAGE.md`
- `docs/architecture/files/UPLOAD_SECURITY_POLICY.md`
- `docs/architecture/files/FILE_OWNERSHIP_AND_DELIVERY.md`
- `docs/audits/FILE_SURFACE_INVENTORY_2026-08-04.md`
- este cierre.
