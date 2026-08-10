# Registro consolidado de deuda técnica — 2026-08-10

| ID | Tipo | Módulo | Descripción | Severidad | Impacto / riesgo futuro | Recomendación |
| --- | --- | --- | --- | --- | --- | --- |
| DT-A01 | arquitectura/backend | ETS | Router duplica crear/actualizar/transitar/excepción/baja del servicio | CRÍTICO | Divergencia de reglas y efectos | Caracterizar rutas, dejar servicio único, pruebas HTTP |
| DT-A02 | integridad/seguridad | ETS | `exception_requested` cambia estado y factura | CRÍTICO | Bypass de segregación | Separar requested/approved/executed con revalidación |
| DT-A03 | auditoría/backend | transversal | Mutaciones protegidas no propagan actor | ALTO | Cambios con `user_id=NULL` | Inyectar actor y exigirlo en servicios críticos |
| DT-A04 | seguridad | autenticación | JWT localStorage, sin rotación/revocación/MFA/reset | ALTO | Secuestro de sesión persistente | Sesiones revocables, rotación, cookies/BFF evaluado |
| DT-A05 | seguridad | autenticación | Sólo lock por cuenta; sin rate limit IP/dispositivo | MEDIO | Brute force y lockout provocado | Limitador distribuido y telemetría |
| DT-A06 | permisos/docs | institucional | Validador de capacidades falla 20/2 | ALTO | Gobierno y API divergen | Versionar/reconciliar catálogo, bootstrap y Portal |
| DT-A07 | fiscal | Facturación | Cancelación/sustitución, PPD, complemento y egreso ausentes | ALTO | No apto fiscalmente | Implementar sobre `Invoice` y Workbench únicos |
| DT-A08 | integración | Portal | Adaptador productivo de correo ausente | ALTO | Registro/invitación incompletos | Proveedor institucional con retry/outbox/observabilidad |
| DT-A09 | seguridad/dependencias | frontend | `nanoid` y `postcss` con advisory alto | ALTO | DoS/path disclosure según superficie | Actualizar lockfile y repetir build/audit |
| DT-A10 | pruebas | transversal | Sin E2E browser por rol ni macroflujo | ALTO | Regresiones no detectadas | Playwright/Cypress con PostgreSQL aislado |
| DT-A11 | infraestructura | transversal | Sin CI/CD, deploy declarativo ni readiness real | ALTO | Despliegues no reproducibles | Pipeline, health de dependencias y gates |
| DT-A12 | observabilidad | transversal | Sin métricas, tracing, alertas ni error tracking | ALTO | Fallos silenciosos y MTTR alto | Instrumentación, SLO y alertas |
| DT-A13 | archivos | transversal | Storage local, sin AV/retención/replicación | ALTO | Pérdida/acumulación/malware | Backend durable, cuarentena, cuotas y lifecycle |
| DT-A14 | arquitectura/UX | Calidad | Autenticación también disponible en ETS | ALTO | Ownership y UX divergentes | Calidad único mutador; ETS lectura/contexto |
| DT-A15 | técnico | Hojas de Campo | React/PDF y semántica de 23 plantillas no cerrados | ALTO | Documento inconsistente | Snapshot/render único y casos aprobados |
| DT-A16 | técnico/UX | Captura | No identificados y retorno real sin E2E | ALTO | Expedientes bloqueados/manuales | Resolución formal y pruebas con Masters reales saneados |
| DT-A17 | frontend | Facturación | Borrador puede descartarse sin autosave | MEDIO | Pérdida de trabajo | Autosave o confirmación uniforme |
| DT-A18 | rendimiento | backend | 100 `.all()` y listados globales | MEDIO | Memoria/latencia creciente | Paginación y límites por contrato |
| DT-A19 | rendimiento | documentos | ZIP/PDF/XLSX síncronos/en memoria | MEDIO | Bloqueo de workers | Streaming/jobs según medición |
| DT-A20 | mantenibilidad | frontend | Archivos 8,472/4,598/3,475/1,805 líneas | MEDIO | Alto riesgo de regresión | Extracción incremental bajo pruebas |
| DT-A21 | frontend | bundle | JS 1,040.31 kB, warning >500 kB | MEDIO | Carga inicial alta | Lazy loading y chunks medidos |
| DT-A22 | configuración | CORS | Lista hardcodeada ignora `settings.cors_origins` | MEDIO | Deriva de entornos | Fuente única validada |
| DT-A23 | arquitectura/BD | Portal | Catálogo se siembra/commitea en startup | MEDIO | Startup mutante/race | Migración/bootstrap explícito e idempotente |
| DT-A24 | Motor | Fase 14 | Productor adicional no consumido por router/UI | MEDIO | Vertical inaccesible desde origen | Integrar mediante composición existente |
| DT-A25 | legado | frontend | Dos archivos sin consumidor confirmado | BAJO | Ruido y mantenimiento | Confirmar consumidores externos antes de retirar |
| DT-A26 | BD | transversal | Columnas/relaciones legacy aún activas | MEDIO | Conceptos dobles | Medir uso y migrar reversiblemente; no eliminar aún |
| DT-A27 | UX/accesibilidad | frontend | Alert/confirm nativos y sin axe | BAJO | Experiencia inconsistente | Componentes comunes y auditoría a11y |

## Deuda retirada respecto del corte 2026-08-03

- API interna anónima: corregida por guard deny-by-default.
- Portal global/IDOR: corregido por identidad/membresía/ownership.
- secreto JWT productivo conocido: corregido por validación de entorno.
- drift, defaults, downgrade y respaldo/head: corregidos y verificados.
- uploads/ZIP sin política uniforme: corregidos en ETAPA 3.

