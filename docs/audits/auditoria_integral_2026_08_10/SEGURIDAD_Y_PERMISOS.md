# Auditoría de seguridad y permisos — 2026-08-10

## Dictamen

El perímetro es sustancialmente más seguro que en el corte 2026-08-03, pero la
postura sigue siendo **REQUIERE CORRECCIONES ANTES DE PRODUCCIÓN**. No se
confirmó una ruta interna anónima ni un IDOR del Portal en la revisión actual.

## Inventario de acceso real

| Tipo | Operaciones |
| --- | ---: |
| Permiso interno | 270 |
| Administrativa | 36 |
| Portal + ownership | 20 |
| Ownership interno | 5 |
| Autenticada | 6 |
| Pública intencional | 11 |
| Pública firmada | 3 |
| Pública controlada por entorno | 1 |
| Consumidor Motor/organización | 4 |
| Sin clasificación | 0 |

La protección visual no se contó como seguridad. El backend aplica
`enforce_api_access` a todos los routers incluidos; cualquier ruta nueva sin
política falla en startup/test. El frontend filtra módulos y acciones, pero el
backend sigue siendo autoridad.

## Controles comprobados

- JWT access/refresh con `token_type` y contexto interno/Portal separado.
- Producción rechaza secretos conocidos, cortos o de baja entropía.
- Usuario inactivo/suspendido y membresía inactiva se rechazan.
- Portal deriva un cliente único desde `ClientPortalMembership`; no acepta
  tenant suministrado por el navegador.
- PDF/documentos del Portal se filtran por cliente y recursos ajenos devuelven
  404 en pruebas A/B.
- 5 fallos bloquean la cuenta 15 minutos y los eventos se auditan.
- Uploads tienen límites, MIME/firma/estructura, defensas ZIP, confinamiento y
  publicación atómica.
- Facturama redacta headers/valores sensibles en diagnósticos.
- No se encontraron credenciales reales rastreadas mediante búsqueda nominal.

## Brechas

| Área | Resultado | Riesgo |
| --- | --- | --- |
| Sesiones | refresh 30 días, sin `jti`, rotación ni revocación; tokens localStorage | ALTO |
| MFA/reset | no implementados | ALTO para cuentas privilegiadas |
| Rate limit | lock por cuenta, no IP/dispositivo/distribuido | MEDIO |
| Auditoría de actor | mutaciones autorizadas pueden guardar `user_id=NULL` | ALTO |
| Granularidad | permisos amplios; 20 gaps catálogo, 2 bootstrap | ALTO |
| Segregación ETS | excepción solicita y ejecuta | CRÍTICO |
| CORS | hardcodeado y duplicado con settings | MEDIO |
| Headers | no se observó CSP/HSTS/frame policy en app; proxy no disponible | NO VERIFICADO/MEDIO |
| CSRF | bearer no-cookie reduce exposición; futuro cambio a cookies exigiría protección | NO APLICA actualmente |
| XSS | React escapa por defecto; localStorage amplifica cualquier XSS | MEDIO |
| SQL injection | ORM predominante; no se confirmó concatenación explotable | NO CONFIRMADA |
| Files | sin antivirus, storage durable ni política de retención | ALTO operativo |
| Dependencias | 2 advisories altos npm; Python CVE no escaneado | ALTO/NO VERIFICADO |
| Secretos históricos | sin escáner de entropía/historial | NO VERIFICADO |

## Ownership y permisos por dominio

- Portal: protección real por membresía/cliente; `portal.view` y permisos
  propios se resuelven desde BD.
- Comunicaciones: política de participante en el guard; revisar además
  paginación y adjuntos futuros.
- Interno: la mayoría protege por permiso de módulo, no por scope de registro;
  el catálogo funcional define scopes que el bootstrap no representa aún.
- Motor: consumidor/organización, decisiones exactas, idempotencia y replay
  están separados de JWT interno.

## Recomendación de secuencia

1. Separar excepción ETS y exigir actor en toda mutación crítica.
2. Reconciliar catálogo/Portal/bootstrap sin relajar deny-by-default.
3. Implementar sesiones revocables, rotación, MFA privilegiado y rate limit.
4. Actualizar dependencias altas y añadir SAST/SCA/secret scanning en CI.
5. Añadir E2E 401/403/404 por rol/tenant y pruebas browser.
6. Definir reverse proxy, TLS, headers, logs, retención, AV y respuesta a
   incidentes antes de Producción.

