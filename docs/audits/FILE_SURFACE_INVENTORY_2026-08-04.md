> Estado: FOTOGRAFÍA TÉCNICA DE ENTRADA — ETAPA 3
>
> Corte: 2026-08-04
>
> Autoridad: diagnóstica; la arquitectura vigente está en `../architecture/files/`

# Inventario de superficies de archivos

## Dictamen inicial

La revisión encontró un servicio local de rutas con contención básica contra
path traversal y eliminación por referencias, pero sin política institucional
común de tamaño, MIME, firma, archivos comprimidos ni escritura atómica. El
riesgo crítico estaba en Captura: leía cada carga y cada miembro ZIP completo
en memoria, sin límite de cantidad, expansión, profundidad, cifrado o rutas.
Actividad era la única superficie con tamaño y firma parcial, aunque aceptaba
ZIP sin inspección de seguridad. Plantillas Maestras, PDFs, constancias,
importaciones y documentos recuperados del PAC mantenían validadores aislados
o sólo comprobaban extensión.

## Superficies HTTP y de servicio

| Dominio | Entrada/salida | Formatos | Control previo al corte | Riesgo inicial | Tratamiento de ETAPA 3 |
| --- | --- | --- | --- | --- | --- |
| Actividad | carga, descarga y vista previa de adjuntos | PDF, imágenes, texto, CSV, ZIP y OOXML | 15 MB, MIME/extensión y firma parcial; ownership por entidad | ZIP bomb/slip, Office falso e imagen sobredimensionada | perfil `activity_attachment`, inspección completa y entrega tras ownership existente |
| Clientes | vista previa/carga de constancia | PDF, PNG, JPEG | extensión; extracción PDF | contenido falso, carga sin límite | perfil `tax_constancy`, PDF/imagen estructural y 15 MB |
| Clientes | previsualización/importación | CSV, XLSX/XLSM | parser directo y lectura completa | archivo grande, OOXML inseguro, texto inválido | perfil `client_import`, UTF-8/OOXML y 20 MB |
| Plantillas Maestras | incorporación y descarga | XLSX | 20 MB y dos nombres internos del ZIP | expansión, cifrado, rutas y duplicados | perfil `certificate_master`, contenedor Office completo y escritura atómica |
| Captura | carga individual o lote | ZIP, XLSX/XLSM | lectura total; ZIP sin cotas; ignora auxiliares macOS | **crítico**: agotamiento, zip slip/bomb, cifrado | perfil `capture_package`; cantidad, tamaño comprimido/descomprimido, miembro, ratio, profundidad y rutas |
| Captura | generación/descarga de paquete | ZIP/XLSX/PDF generados | memoria y selección backend | presión de memoria en lotes muy grandes | generación conserva flujo; límites de entrada no alteran reglas funcionales |
| Certificados | carga PDF y descargas original/autenticado | PDF | sólo extensión al cargar; permiso previo | PDF falso/cifrado/truncado | perfil `certificate_pdf`, estructura/páginas y entrega institucional |
| Calidad | XLSX→PDF autenticado | XLSX/PDF | temporal aislado; copia final no atómica | parcial visible ante fallo de copia | publicación final atómica desde temporal |
| Control Documental | descarga de versión | XLSX actual | permiso `documents.read` y ruta local | symlink/archivo no regular | límite de entrega exige archivo regular dentro de storage |
| Facturación/Facturama | recuperación y descarga | XML/PDF base64 | decode y escritura directa | base64/XML/PDF inválido; parcial visible | base64 estricto, XML sin DTD/ENTITY, PDF estructural, escritura atómica |
| Portal | descarga de certificado propio | PDF | identidad Cliente, ownership, visibilidad y auditoría | ruta final no uniforme | se conserva fail-closed; entrega común después de ownership |
| Hojas de Campo/Cotizaciones/OT | generación/stream | PDF/ZIP generados | datos internos, sin carga | no es entrada no confiable | fuera de perfiles de upload; se conserva generación vigente |
| SAT | importación operativa local | XLS/CSV/JSON oficiales | scripts/servicio propietario | fuente administrativa, no multipart ordinario | no se cambia el contrato SAT en esta etapa |
| Respaldos | dump y drills locales | SQL | scripts de recuperación | dato sensible rastreado por Git | se conserva local, se excluye del índice; no se regenera BD |

## Matriz de controles antes y después

| Control | Antes | Después |
| --- | --- | --- |
| tamaño total | sólo Actividad/Master | todos los perfiles multipart integrados |
| nombre y ruta exterior | sanitización al destino | rechazo explícito de rutas, NUL, control y longitud |
| MIME declarado | sólo Actividad | matriz central por extensión, con MIME genérico compatible |
| firma/estructura real | parcial | PDF, imagen, texto, OOXML, ZIP y XML |
| ZIP | apertura directa | miembros, tamaño total/individual, ratio, profundidad, duplicados, cifrado, enlaces y rutas |
| escritura | directa en destino | temporal adyacente, `fsync` y `os.replace` |
| checksum | algunos dominios | SHA-256 producido por la capa común; persiste donde ya existe campo |
| entrega | rutas resueltas de forma dispersa | archivo regular, no symlink, contenido bajo raíz; después de permiso/ownership de dominio |
| temporales | mezcla de temporales seguros y escrituras directas | temporales aislados y limpieza por contexto/finally |

## Artefactos versionados y locales

Al corte se encontraron 55 archivos operativos rastreados bajo `storage/`, el
dump `backup_erp_myc_antes_prueba.sql` (74,539,344 bytes), `docs.zip`, cuatro
archivos raíz vacíos accidentales (`BytesIO`, `from`, `import`, `io`), un ZIP
operativo adjunto y un AppleDouble. También existen `frontend/src.zip`,
`.DS_Store`, `__pycache__` y otros artefactos locales no rastreados.

Clasificación:

- **evidencia operativa recuperable:** dump y contenido `storage/`; permanece
  físicamente en su ubicación local y sólo se retira del índice Git;
- **paquetes generados/locales:** `docs.zip`, `frontend/src.zip`; ignorados;
- **accidentales sin función:** archivos raíz vacíos, `.DS_Store`, `._*`,
  cachés; fuera del inventario funcional y del índice;
- **recursos oficiales:** no se modifican ni confunden con datos operativos.

No se reescribe historia Git y no se elimina evidencia física. El respaldo no
se regenera porque ETAPA 3 no cambia esquema ni datos.

## Ambigüedades y límites

- Los modelos actuales no tienen un agregado universal de metadatos de
  archivo. ETAPA 3 no crea migración: conserva rutas/campos existentes y
  produce checksum desde infraestructura para que cada dominio lo persista
  cuando ya dispone de columna.
- No se incorpora antivirus/servicio externo porque no hay proveedor aprobado.
  La política deja cuarentena como destino reservado y aplica validación
  estructural fail-closed; la integración antimalware queda como endurecimiento
  operativo posterior.
- La generación de ZIP continúa en memoria para preservar contratos HTTP. La
  entrada no confiable sí queda acotada; migrar salidas grandes a streaming
  durable requiere medición y alcance propio.
- Los permisos, estados, folios y ownership no se reinterpretan. La capa de
  entrega sólo opera después de que el dominio autoriza el recurso.
