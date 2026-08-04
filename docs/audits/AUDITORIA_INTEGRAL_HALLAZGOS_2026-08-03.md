# Registro tabular de hallazgos

## Conteo

| CRÍTICO | ALTO | MEDIO | BAJO | INFORMATIVO | Total |
| ---: | ---: | ---: | ---: | ---: | ---: |
| 3 | 13 | 18 | 4 | 2 | 40 |

Todos los hallazgos son `CONFIRMADO` salvo que se indique `NO VERIFICADO`, `PARCIALMENTE CONFIRMADO` o `DEUDA CONOCIDA`.

## Críticos y altos

| ID / título | Sev. / área / tipo / estado | Evidencia y causa raíz | Impacto, escenario y datos | Archivos | Riesgos S/I/O | Prueba | Corrección futura / dependencias / orden |
| --- | --- | --- | --- | --- | --- | --- | --- |
| AUD-001 API interna sin deny-by-default | CRÍTICO · Seguridad/API · defecto · CONFIRMADO | Introspección: 74 públicas + 15 opcionales; CRUD Clientes/Catálogo/Cotización/ETS/Equipo. Causa: seguridad aplicada router por router | Anónimo lista/modifica/cierra registros; PII, precios, estados, documentos | `main.py`, routers mencionados, `auth.py` | S crítico / I crítico / O crítico | Ausente matriz 306×401/403 | Guard global + allowlist + permisos por acción; depende de catálogo y tests; **1** |
| AUD-002 Portal global e IDOR PDF | CRÍTICO · Portal/privacidad · defecto/ausencia · CONFIRMADO | `client_portal.py` sin auth ni client_id; listados globales por estado; PDF por entero | Enumerar `/certificates/{id}/pdf`; expone cotizaciones, ETS, certificados y datos cliente | router portal, services dominio | S crítico / I alto / O alto | Ausente | Identidad tenant, ownership obligatorio y UUID firmado/rate limit; depende auth; **2** |
| AUD-003 JWT arranca con secreto conocido | CRÍTICO · Auth/config · riesgo · CONFIRMADO | `Settings.secret_key="change-this-secret-key"`; sin guard por environment | Despliegue mal configurado permite forjar access/refresh y rol claim (usuario se recarga, pero token habilita identidad válida) | `core/config.py`, `core/security.py` | S crítico / I crítico / O alto | Ausente | Fallar arranque fuera de dev, secret manager, rotación, jti; **3** |
| AUD-004 16 timestamps NOT NULL sin default | ALTO · BD · defecto · CONFIRMADO | information_schema en base vacía: 8 tablas; mixin ORM espera server default. Causa: migraciones creadoras omitieron `server_default` | Inserts ORM/raw pueden fallar; Activity, linked company e Incertidumbre | migraciones `8c9`, `ae1`, `b3c`; modelos base | S bajo / I alto / O alto | No hay regresión sistemática | Migración única + inspección automática; depende datos históricos; **4** |
| AUD-005 Drift modelos↔BD | ALTO · Migraciones · deuda/defecto · CONFIRMADO | `alembic check` falla con columnas, índices y constraints | Riesgo de deploy impredecible o de eliminar índices especializados | modelos/migraciones múltiples | S medio / I alto / O alto | Check falla | Clasificar diff uno por uno; no autogenerar ciegamente; **5** |
| AUD-006 Downgrade completo roto | ALTO · Migraciones · defecto · CONFIRMADO | `downgrade base` falla en `c3fb...` por índice inexistente | Recuperación/reversión no confiable | `c3fb78821edc_add_service_order_signatures.py` y sucesoras | S bajo / I alto / O alto | Reproducido PostgreSQL | Downgrade idempotente/orden correcto + ciclo completo CI; **6** |
| AUD-007 Backup oficial no coincide con head | ALTO · Backup/BD · inconsistencia · CONFIRMADO | dump `b03...`; código visible `e16...`; tres migraciones no rastreadas | Restore queda atrasado; falsa seguridad y posible pérdida de cambios | backup SQL, BACKUP_ESTADO, migraciones c14/d15/e16 | S alto / I alto / O alto | Sólo lectura; no restaurado | Versionar/sanar migraciones, restaurar dump aislado, luego regenerar con autorización; **7** |
| AUD-008 Archivos reales y backup en Git | ALTO · Privacidad/operación · riesgo · CONFIRMADO | 55 rutas storage, SQL 74 MB, PDFs/XLSX/XML, ZIP y constancias rastreados | Fuga en clones/historial; crecimiento; malware/PII | `storage/`, backup SQL, ZIP | S alto / I medio / O alto | Inventario | Custodia cifrada, purga Git planificada, DLP; depende respaldo externo; **8** |
| AUD-009 Upload/ZIP sin límites uniformes | ALTO · Archivos/DoS · defecto/riesgo · CONFIRMADO | `upload_capture_files` hace `read()` y `archive.read()` completos; clientes públicos procesan XLSX/PDF | ZIP bomb/memoria/disco; endpoint anónimo agrava | capture_packages, clients router/service, storage | S alto / I medio / O crítico | Activity sí prueba límite; captura no | Límite request/entrada/descompresión, streaming, MIME/firma/AV; **9** |
| AUD-010 Tokens persistentes sin revocación | ALTO · Auth · deuda · CONFIRMADO | access/refresh localStorage; refresh 30d sin rotation/jti; sin reset/change password | XSS roba sesión larga; no cierre selectivo | `api.js`, auth/security services | S alto / I alto / O medio | Tipos JWT sí; revocación no | HttpOnly/BFF o storage reducido, refresh rotation, sesiones; **10** |
| AUD-011 Permisos frontend y ámbito por registro ausentes | ALTO · Autorización/UX · defecto · CONFIRMADO | AppLayout muestra toda navigation; muchas rutas sólo sesión; roles static | Escalamiento horizontal/vertical, acciones confusas | navigation/AppLayout, permissions, services | S alto / I alto / O alto | Sin E2E roles | Capacidades backend + scope/ownership + UI derivada; tras AUD-001; **11** |
| AUD-012 CFDI productivo incompleto | ALTO · Facturación/fiscal · ausencia · DEUDA CONOCIDA | sólo Sandbox; sin cancelación/sustitución, PPD/complemento, nota egreso | No operar fiscalmente ni corregir CFDI de forma completa | Facturama services, invoices, Workbench | S medio / I alto / O crítico | Unitarias mapper/reconcile; no E2E externo | Diseñar flujo fiscal propietario, webhooks/conciliación y certificación; **12** |
| AUD-013 Cobertura HTTP/autorización insuficiente | ALTO · Pruebas · ausencia · CONFIRMADO | 409 pasan, pero 4 archivos usan TestClient y pocas aserciones 401/403; no E2E | Regresiones de seguridad no detectadas | tests backend/frontend | S alto / I alto / O alto | Evidencia misma | Matriz generada 306 rutas, roles, IDOR y E2E macro; **13** |
| AUD-014 Sin CI/deploy/readiness/observabilidad | ALTO · Operación · ausencia · CONFIRMADO | no workflows/Docker/E2E/métricas/tracing; health estático | Deploy irreproducible, fallos silenciosos, MTTR alto | scripts, health, repo root | S medio / I medio / O crítico | Doctor local pasa | CI, artefactos, migrations gate, readiness, metrics/logs/alerts; **14** |
| AUD-015 Vulnerabilidad alta PostCSS | ALTO · Dependencias · defecto · CONFIRMADO | `npm audit --omit=dev`: GHSA-r28c-9q8g-f849 | Lectura arbitraria de `.map` bajo condiciones del advisory | package-lock/node_modules | S alto / I bajo / O medio | npm audit | Actualizar lock y regression build; depende compatibilidad Vite; **15** |
| AUD-016 Identidad institucional duplicada | ALTO · Documentos/integridad · deuda · CONFIRMADO | 4 fuentes y logos/hardcodes; sólo Hojas snapshot claro | Regenerar documentos con identidad diferente; riesgo fiscal/contractual | pdf services/templates/settings/frontend | S bajo / I alto / O alto | Parcial por documento | Central versionada + snapshot por documento; **16** |

## Medios

| ID / título | Sev. / área / tipo / estado | Evidencia/causa | Impacto/escenario/datos | Archivos | Riesgos S/I/O | Prueba | Corrección/dependencias/orden |
| --- | --- | --- | --- | --- | --- | --- | --- |
| AUD-017 Motor sólo tiene 2 verticales y productor de origen desconectado | MEDIO · Motor/producto · ausencia · CONFIRMADO | `installed.py` retorna 2; productor additional sólo pruebas | Usuario orquesta desde Centro; redefinición solicitada no cumplida | integrations, additional service, Centro UI | S medio/I medio/O medio | Fases 13/14 pasan | Conectar módulo origen sin duplicar workflow; tras seguridad; 17 |
| AUD-018 Fase 14 en revisión, documentos históricos contradictorios | MEDIO · Motor/docs · inconsistencia · CONFIRMADO | canon dice EN REVISIÓN; README dice no iniciada; cierres viejos conservan gates superados | Confusión de autoridad/roadmap | README, docs Motor/canon | S bajo/I medio/O medio | Búsqueda documental | Corregir docs canónicos después de dictamen; 18 |
| AUD-019 ETS router/servicio duplican reglas | MEDIO · Arquitectura · deuda · DEUDA CONOCIDA | máquinas en router y service; 760/875 líneas | Estados divergen; actor opcional | router/service_orders | S medio/I alto/O alto | Suite pasa | Router transporte puro, service único; congelar E2E antes; 19 |
| AUD-020 Autenticación de certificado duplicada | MEDIO · Calidad/UX · deuda · DEUDA CONOCIDA | Calidad y ETS exponen autenticar | Doble superficie formal/errores de rol | ServiceOrdersPage, QualityPage, certificate services | S medio/I medio/O alto | Unitarias | Dejar Calidad única tras E2E; 20 |
| AUD-021 Snapshot cotización no restaura partidas | MEDIO · Ventas/integridad · defecto · DEUDA CONOCIDA | canon OBS-008 y servicio restore | “Restaurar” no reconstruye propuesta completa | quotations service/schema/UI | S bajo/I alto/O medio | Parcial | Restauración transaccional completa/versionada; 21 |
| AUD-022 Hojas sin cierre metrológico/E2E 23 plantillas | MEDIO · Hojas · ausencia · DEUDA CONOCIDA | cálculos/tolerancias/integración pendientes | Certificación puede depender de captura manual no validada | field_sheets/templates/engines | S medio/I alto/O alto | Focalizadas | Matriz por plantilla y E2E con fixtures; 22 |
| AUD-023 Calidad/Captura sin E2E y bandeja no identificados parcial | MEDIO · Operación · ausencia · DEUDA CONOCIDA | backend funciona; UI/browser no verificados | Bloqueo de operación real y archivos huérfanos | capture/certificates/pages | S bajo/I medio/O alto | Unitarias | Dataset representativo y flujo browser; 23 |
| AUD-024 Notas de crédito son internas, no fiscales | MEDIO · Facturación · ausencia · CONFIRMADO | modelo/endpoint; sin UI/CFDI egreso | Estado “credit_note” puede confundirse con cumplimiento SAT | Invoice/CreditNote/Workbench | S medio/I alto/O alto | Sin específica fiscal | Separar nota interna vs CFDI egreso; depende AUD-012; 24 |
| AUD-025 Agenda/Llamados/CRM/encuesta faltan | MEDIO · Alcance · ausencia · CONFIRMADO | sólo agenda_date/called; no dominios lead/report | Flujo comercial 0→100 incompleto | service_order, docs, README | S bajo/I medio/O alto | Ausente | Decisión explícita de absorción/alcance; 25 |
| AUD-026 Listados completos sin paginación | MEDIO · Rendimiento · deuda · CONFIRMADO | `.all()` en clientes/cotizaciones/ETS/equipo/certificados/patrones | Latencia/memoria crece con datos; dashboard multiplica cargas | services y api.js | S bajo/I bajo/O alto | Sin carga | Keyset/paginación/filtros y agregados backend; 26 |
| AUD-027 Generación documentos síncrona/en memoria | MEDIO · Rendimiento/operación · riesgo · CONFIRMADO | PDF/XLSX/ZIP BytesIO, LibreOffice en request | Timeouts y agotamiento worker | pdf/capture/auth services | S medio/I medio/O alto | Focalizadas | Cola de jobs, cuotas, streaming y almacenamiento duradero; 27 |
| AUD-028 Bundle/páginas/CSS monolíticos | MEDIO · Frontend/mantenibilidad · deuda · CONFIRMADO | JS 977k; ServiceOrders 4598; global.css 8418 | UX lenta, regresiones y revisión difícil | frontend | S bajo/I medio/O medio | Build warning | Code splitting y modularización protegida por E2E; 28 |
| AUD-029 Settings simula capacidades inexistentes | MEDIO · UX/alcance · defecto | 4 ComingSoon + identidad/brand/docs/locations placeholders | Usuario espera configuración que no persiste | settings navigation/components | S bajo/I medio/O medio | Sin UI test | Ocultar/etiquetar y conectar contratos reales; 29 |
| AUD-030 Portal técnico/dev docs público | MEDIO · Seguridad/API · decisión pendiente · CONFIRMADO | `/api/developers/resolution-engine` sin auth | Expone metadatos/capacidades; no secreto por sí solo | router public API | S medio/I bajo/O bajo | Sin | Decidir público vs técnico y aplicar rate/auth; 30 |
| AUD-031 CORS duplicado/no configurable | MEDIO · Configuración · defecto · CONFIRMADO | main hardcode ignora settings.cors_origins | Deploy a origen distinto falla o se cambia código | main/config | S medio/I bajo/O medio | Sin | Usar configuración validada por entorno; 31 |
| AUD-032 AuditLog general no append-only | MEDIO · Auditoría/integridad · riesgo · CONFIRMADO | tabla general sin trigger inmutable; Motor sí protege evidencia | DBA/app puede alterar historial general sin señal | audit_log model/migration/services | S medio/I alto/O medio | Sin | Trigger/rol DB/hash chain/retención; 32 |
| AUD-033 Tests no miden cobertura y Python vuln no verificada | MEDIO · Calidad/deps · ausencia · NO VERIFICADO parcial | no coverage config; pip-audit ausente | Zonas sin ejecutar y CVEs desconocidas | tooling/requirements | S medio/I medio/O medio | pip check pasa | Añadir coverage gate y scanner en CI; 33 |
| AUD-034 Labs/rutas ocultas y bypass de sesión | MEDIO · Frontend/seguridad · riesgo · CONFIRMADO | field-sheet lab evita checkSession; otras páginas importadas sin navegación | Superficie accidental en build productivo | App.jsx, labs/pages | S medio/I bajo/O medio | Sin E2E | Excluir por build/env y exigir auth; 34 |

## Bajos e informativos

| ID / título | Sev. / área / tipo / estado | Evidencia/impacto | Archivos/datos/riesgos | Prueba | Corrección/dependencias/orden |
| --- | --- | --- | --- | --- | --- |
| AUD-035 Componentes/archivos huérfanos | BAJO · Limpieza · deuda · CONFIRMADO | NotificationCenterPage e InvoiceWorkbenchModal sin consumidor | Frontend; S bajo/I bajo/O bajo | Búsqueda símbolos | Retirar tras cobertura; 35 |
| AUD-036 Espacios finales rompen diff check | BAJO · Calidad · defecto · CONFIRMADO | 3 líneas preexistentes | CSS; sin datos; O bajo | `git diff --check` falla | Corregir en cambio separado; 36 |
| AUD-037 Artefactos locales masivos | BAJO · Higiene · deuda · CONFIRMADO | 874 DS_Store/pyc/ZIP fuera deps | Repo local; O medio | Inventario | Limpiar/ignore sin borrar evidencia oficial; 37 |
| AUD-038 Warnings dependencias Python | BAJO · Mantenimiento · deuda · CONFIRMADO | Starlette/httpx y passlib/crypt deprecados | venv/requirements; O futuro | pytest | Plan de actualización; 38 |
| AUD-039 Núcleo Motor técnicamente sólido | INFORMATIVO · Motor · fortaleza · CONFIRMADO | 29 archivos prueba; lifecycle/security/idempotencia/locks/outbox/worker/API/SDK | Datos del Motor; reduce I/O | Suites pasan | Conservar simple; no abrir fase; 39 |
| AUD-040 Upgrade vacío y suites pasan | INFORMATIVO · Calidad · fortaleza · CONFIRMADO | upgrade head, 409+29, compile/build/doctor correctos | Todo repo; no elimina hallazgos | Evidencia E08/E13–E19 | Usar como baseline de corrección; 40 |

## Dependencias entre hallazgos

```text
AUD-001 → AUD-002/AUD-011/AUD-013
AUD-004 + AUD-005 + AUD-006 → AUD-007
AUD-012 → AUD-024
AUD-013 → cierre de todos los flujos
AUD-014 → validación continua de migraciones, dependencias y E2E
AUD-016 → documentos históricos confiables
AUD-017 → producto basado en excepciones desde origen
```
