> Estado: VIGENTE — ETAPA 3
>
> Autoridad: Alta para cargas no confiables

# Política institucional de seguridad de cargas

Toda carga multipart integrada debe pasar por un perfil de
`backend/app/services/file_security.py` antes de parsearse o persistirse.

## Perfiles

| Perfil | Formatos | Límite predeterminado |
| --- | --- | ---: |
| `activity_attachment` | PDF, imágenes, texto/CSV, ZIP, DOCX/XLSX/PPTX | 15 MB |
| `capture_package` | ZIP, XLSX/XLSM | 40 MB comprimidos |
| `certificate_master` | XLSX | 20 MB |
| `certificate_pdf` | PDF | 25 MB |
| `tax_constancy` | PDF/PNG/JPEG | 15 MB |
| `client_import` | CSV/XLSX/XLSM | 20 MB |

Los valores se configuran por entorno en `backend/.env.example`. Reducirlos es
compatible; incrementarlos exige valorar memoria, proxy y almacenamiento.

## Controles obligatorios

- nombre simple sin ruta, NUL ni controles y con longitud acotada;
- extensión admitida y MIME declarado compatible;
- lectura con byte adicional para detectar exceso sin lectura ilimitada;
- contenido no vacío, SHA-256 y firma/estructura real;
- PDF completo, con página y sin cifrado; XML bien formado sin DTD/ENTITY;
- imagen decodificable, completa y bajo el máximo de píxeles;
- texto UTF-8; Office como contenedor OOXML estructural;
- ZIP con límites de miembros, tamaño total e individual descomprimido, ratio,
  profundidad y longitud; sin rutas absolutas/`..`, duplicados normalizados,
  cifrado, symlinks ni dispositivos.

Nunca se extrae un ZIP directamente al destino final. El flujo de Captura lee
miembros validados desde el contenedor y publica cada archivo individual de
forma atómica. Un rechazo no debe dejar archivos parciales ni mutar el estado
funcional del expediente.

## Errores y trazabilidad

413 indica exceso de tamaño; 415 incompatibilidad de tipo/estructura; 422
contenido inseguro o inválido. Los mensajes no exponen rutas internas. Los
dominios conservan sus auditorías vigentes e incorporan checksum cuando su
contrato ya lo admite. No se registra contenido ni credenciales.
