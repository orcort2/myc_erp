# Auditoría integral, exhaustiva y verificable del ERP MYC

**Corte de evidencia:** 2026-08-03  
**Naturaleza:** fotografía técnica diagnóstica; no modifica el canon del proyecto  
**Dictamen:** **NO APTO PARA PRODUCCIÓN**  
**Puntuación global:** **49/100**

## 1. Resumen ejecutivo

El ERP MYC tiene una base funcional sustancial: SPA React, API FastAPI, 101 tablas ORM, 306 operaciones HTTP, generación PDF/XLSX/XML/ZIP, Facturama Sandbox, LibreOffice, control documental, Actividad y un Motor de Resoluciones durable. La base vacía migra hasta el head visible y las suites existentes pasan (409 pruebas backend y 29 frontend).

Ese avance no compensa tres fallos críticos de perímetro: gran parte de la API interna no exige identidad, el portal cliente expone información global y PDF por identificador, y el backend puede arrancar con un secreto JWT conocido. La consistencia de despliegue tampoco está cerrada: existe drift ORM/Alembic, el downgrade completo falla, faltan defaults de servidor y el respaldo oficial no coincide con el head visible.

El inventario detallado, la matriz de módulos, los 40 hallazgos, la auditoría de seguridad, la revisión de identidad y el plan forman parte indivisible de este dictamen:

- [`RESUMEN_EJECUTIVO_AUDITORIA_ERP_MYC_2026-08-03.md`](RESUMEN_EJECUTIVO_AUDITORIA_ERP_MYC_2026-08-03.md)
- [`AUDITORIA_INTEGRAL_COBERTURA_MODULOS_2026-08-03.md`](AUDITORIA_INTEGRAL_COBERTURA_MODULOS_2026-08-03.md)
- [`AUDITORIA_INTEGRAL_HALLAZGOS_2026-08-03.md`](AUDITORIA_INTEGRAL_HALLAZGOS_2026-08-03.md)
- [`AUDITORIA_INTEGRAL_SEGURIDAD_PERMISOS_2026-08-03.md`](AUDITORIA_INTEGRAL_SEGURIDAD_PERMISOS_2026-08-03.md)
- [`AUDITORIA_INTEGRAL_BD_MIGRACIONES_2026-08-03.md`](AUDITORIA_INTEGRAL_BD_MIGRACIONES_2026-08-03.md)
- [`AUDITORIA_IDENTIDAD_INSTITUCIONAL_2026-08-03.md`](AUDITORIA_IDENTIDAD_INSTITUCIONAL_2026-08-03.md)
- [`AUDITORIA_CODIGO_MUERTO_2026-08-03.md`](AUDITORIA_CODIGO_MUERTO_2026-08-03.md)
- [`PLAN_CORRECCION_AUDITORIA_INTEGRAL_2026-08-03.md`](PLAN_CORRECCION_AUDITORIA_INTEGRAL_2026-08-03.md)
- [`evidence/AUDITORIA_COMANDOS_2026-08-03.txt`](evidence/AUDITORIA_COMANDOS_2026-08-03.txt)

## 2. Alcance y método

Se revisaron frontend, backend, ORM, migraciones, APIs, permisos, seguridad, archivos, documentos, pruebas, scripts, dependencias, infraestructura y antecedentes canónicos. La evidencia combinó búsqueda estática, introspección del código, conteos reproducibles, compilación, pruebas, auditoría de dependencias y un ciclo Alembic sobre una base PostgreSQL aislada creada exclusivamente para la auditoría.

Reglas de conclusión:

1. La existencia de código o una declaración histórica no se tomó como cierre.
2. `SELLADO` sólo se asignó cuando no se encontró pendiente funcional dentro del alcance acotado.
3. Lo no reproducible se marca `NO VERIFICADO` o `PARCIALMENTE CONFIRMADO`.
4. No se invocaron servicios productivos, no se alteró la base compartida y no se regeneró el respaldo.
5. Los archivos ya modificados o no rastreados al inicio se trataron como trabajo ajeno y no se corrigieron.

## 3. Inventario verificable

| Elemento | Resultado |
| --- | ---: |
| Archivos físicos del workspace | 19,713 |
| Archivos rastreados por Git | 793 |
| Archivos funcionales aproximados, excluyendo generados | 1,731 |
| Routers FastAPI incluidos | 36 |
| Operaciones HTTP | 306 |
| GET / POST / PATCH / DELETE / PUT | 118 / 137 / 31 / 19 / 1 |
| Tablas ORM | 101 |
| Columnas / FKs / índices / constraints únicos | 1,670 / 294 / 458 / 76 |
| Migraciones Python visibles | 82 |
| Archivos de prueba backend / frontend | 55 / 8 |
| Funciones exportadas por `api.js` | 179 |
| Archivos rastreados dentro de `storage/` | 55 |

Se observaron artefactos no propios de fuente (`.DS_Store`, AppleDouble, bytecode y ZIP), un dump SQL de aproximadamente 74 MB y documentos operativos rastreados. No se inspeccionó ni reprodujo contenido sensible en estos informes.

## 4. Arquitectura real y trazabilidad

```text
React SPA (routing propio; access/refresh en localStorage)
  -> api.js / fetch
    -> FastAPI / 36 routers
      -> routers y services con separación desigual
        -> SQLAlchemy / PostgreSQL / Alembic
        -> storage local y generadores PDF/XLSX/XML/ZIP
        -> Facturama y LibreOffice
        -> Motor de Resoluciones / outbox / cola / worker / API / SDK
```

La arquitectura prescrita se cumple bien en el Workbench de Facturación, Servicios Compuestos y el núcleo del Motor. Se desvía en la autorización transversal, la mezcla de reglas ETS entre router y servicio, la identidad institucional distribuida, superficies duplicadas de Calidad y los productores de resoluciones desde los módulos de origen.

## 5. Puntuación y criterio

| Dimensión | Nota | Evidencia determinante | Para llegar a 100 |
| --- | ---: | --- | --- |
| Arquitectura | 62 | Contratos sólidos pero monolitos y duplicaciones | Límites de dominio, router delgado y E2E de contratos |
| Backend | 58 | Servicios reales; auth inconsistente | Guard global, permisos/scope y transacciones uniformes |
| Frontend | 55 | Flujos amplios; navegación y páginas monolíticas | Capacidades por rol, accesibilidad, code splitting y E2E |
| Base de datos | 52 | Modelo rico; defaults/drift/artefactos | Esquema reproducible, constraints auditados y restore drill |
| Migraciones | 40 | Upgrade vacío pasa; check/downgrade fallan | Upgrade histórico, check limpio y reversibilidad probada |
| Seguridad | 24 | Tres críticos y upload riesgoso | Deny-by-default, sesiones revocables, DLP y hardening |
| Permisos | 22 | 181 rutas con permiso, muchas sin él | Matriz ejecutable completa y ownership por registro |
| Integridad transaccional | 70 | Locks/snapshots fuertes en dominios clave | Eliminar caminos opcionales y validar concurrencia global |
| Flujos de negocio | 52 | Flujo comercial/operativo parcial | Macro E2E, Agenda/Llamado y cierres sin duplicación |
| Motor de Resoluciones | 78 | Núcleo probado y general | Aprobar fase 14, conectar orígenes y operar workers |
| Actividad/notificaciones | 67 | Conversación institucional implementada | Defaults, entrega externa, navegación y retención |
| Documentos/snapshots | 58 | Versionado desigual | Identidad central versionada y snapshot por documento |
| Facturación | 56 | Draft, PAC, XML/PDF y pagos | CFDI productivo completo y certificación externa |
| Pruebas | 65 | 438 pruebas pasan | Cobertura, HTTP/roles, browser, migraciones y carga |
| Documentación | 56 | Canon amplio pero contradictorio | Resolver conflictos contra evidencia y automatizar checks |
| UX | 48 | Función amplia, rutas ocultas/placeholders | Recorridos por rol, estados vacíos/error y accesibilidad |
| Rendimiento | 45 | Sin paginación amplia; procesos síncronos | Medición, paginación, jobs, streaming y presupuestos |
| Operabilidad | 42 | Doctor local útil | CI/CD, readiness, observabilidad y runbooks probados |
| Mantenibilidad | 44 | Archivos gigantes y APIs concentradas | Modularizar bajo pruebas de caracterización |
| Producción | 28 | No hay perímetro ni deploy reproducible | Cerrar todos los P0/P1 y simulacro operacional |

Ponderación global: seguridad/permisos 18%; BD/migraciones/integridad 17%; flujos/facturación/documentos 18%; backend/frontend/arquitectura 18%; pruebas 8%; operación/producción/rendimiento 11%; Motor/Actividad 6%; documentación/UX/mantenibilidad 4%.

## 6. Estado de módulos

La tabla completa está en la matriz de cobertura. El resultado agregado es:

- `SELLADO`: Control Documental V1, sólo dentro de su alcance congelado.
- `CASI SELLADO`: LibreOffice como dependencia local y núcleo del Motor, sujetos a operación/despliegue general.
- `EN DESARROLLO`: la mayoría de módulos comerciales, operativos, metrológicos, fiscales, transversales y técnicos.
- `PENDIENTE`: Agenda y Llamados autónomos.
- `NO INICIADO`: CRM/Leads, infraestructura declarativa, encuesta/reporte final y Google Drive.

No se atribuye `SELLADO` al sistema ni a un módulo con pendiente funcional o UX dentro de su alcance.

## 7. Seguridad, privacidad y permisos

La introspección clasificó 181 operaciones con permiso explícito, 32 con sesión, 15 con sesión opcional, cuatro de contexto consumidor y 74 públicas. La clasificación no sustituye una prueba dinámica: sí demuestra que no hay protección uniforme. Clientes, Catálogo, Cotizaciones, ETS y Equipos incluyen operaciones sensibles sin identidad obligatoria.

El portal cliente carece de identidad tenant y ownership: lista registros globales y resuelve certificados por ID entero. La clave JWT tiene un default conocido, los tokens se conservan en `localStorage`, el refresh dura 30 días y no existen revocación, rotación, `jti`, cambio/reset de contraseña, MFA ni rate limiting. La navegación tampoco se deriva de permisos. CORS está duplicado y una ruta de configuración usa un permiso de Hojas de Campo no relacionado.

Las cargas de Actividad sí validan tamaño, extensión, MIME y firma. Captura y ciertos imports leen archivos/entradas ZIP completos, sin presupuesto de descompresión. El repositorio contiene documentos reales y respaldo SQL rastreados, con riesgo de privacidad y propagación histórica.

## 8. Base de datos y migraciones

En PostgreSQL aislado, `upgrade head` desde vacío llegó a `e16e7f8091a2`. `alembic check` detectó drift de columnas, índices y constraints. `downgrade base` falló en `c3fb78821edc_add_service_order_signatures.py` al eliminar un índice inexistente. Ocho tablas presentan 16 timestamps NOT NULL sin default de servidor.

El dump oficial registra `b03b4c5d6e7f`; el head visible depende de tres migraciones no rastreadas (`c14`, `d15`, `e16`). No se restauró el dump por contener datos reales y no existir una copia sanitizada autorizada. La compatibilidad SQLite no es completa por JSONB, triggers, búsquedas y locking PostgreSQL.

## 9. Flujos funcionales prioritarios

### ETS, Hojas, Captura, Calidad y Certificados

El dominio tiene estados, OTs, equipos, snapshots, Hojas, paquetes de captura, revisión, autenticación y liberación. Los riesgos de cierre son la autorización pública, reglas duplicadas ETS router/service, semántica/cálculo incompletos para 23 plantillas, ZIP sin límite seguro, doble superficie de autenticación y ausencia de E2E browser con archivos representativos.

### Facturación, pagos y documentos fiscales

El Workbench reutiliza correctamente el controlador único y el agregado `Invoice`; ETS consume `EtsBillingTab`. Existen borrador, snapshots fiscales, intentos PAC, conciliación, XML/PDF, pagos y cartera. Continúa incompleto para producción: Facturama está en Sandbox; faltan cancelación/sustitución, PPD/complemento, nota fiscal de egreso, webhooks/reconciliación robusta, autosave y E2E externo. La `CreditNote` actual es administrativa, no acredita un CFDI de egreso.

### Actividad y Motor de Resoluciones

Actividad implementa threads, mensajes, menciones, adjuntos, atención y no leídos con un buen control de archivos. Faltan defaults de BD, entrega externa y observabilidad. El Motor es el subsistema mejor estructurado: versionado, lifecycle, decisiones, seguridad, idempotencia, locks, compensación, auditoría inmutable, outbox, cola, leases/fencing, recovery, API y SDK. Sólo hay dos definiciones instaladas y el productor de equipo adicional aparece únicamente en pruebas; el patrón de iniciar desde origen aún no está cerrado.

## 10. Frontend, UX, rendimiento y mantenibilidad

La aplicación usa routing propio y concentra 179 llamadas en `api.js`. Hay páginas importadas pero no navegables y laboratorios que evitan la sesión normal. Ajustes presenta placeholders y `ComingSoon`. Los mayores archivos alcanzan 4,598 líneas de JSX, 8,418 de CSS y 1,696 de API; el bundle JS construido es 977.83 kB (249.42 kB gzip) y supera el umbral de 500 kB.

Muchos listados cargan `.all()` sin paginación. PDF/XLSX/ZIP y conversiones LibreOffice ocurren síncronamente y en memoria. No hay pruebas de carga, presupuestos de latencia, jobs durables para documentos ni medición RUM/APM.

## 11. Pruebas y operación

Resultados reproducidos:

- Backend: 409 passed, 19 subtests, dos warnings.
- Frontend: 29 passed.
- Build Vite y `compileall`: correctos; Vite advierte chunk grande.
- `scripts/myc doctor`: backend, frontend, venv, PostgreSQL, imports, Alembic, Node, npm y LibreOffice disponibles.
- `npm audit --omit=dev`: una vulnerabilidad alta de PostCSS.
- `pip check`: correcto; vulnerabilidades Python `NO VERIFICADAS` por ausencia de `pip-audit`.

No se encontró CI, Docker/Compose, E2E browser, métricas, tracing, error tracking, readiness real ni runbook de restore demostrado. `/api/health` es estático.

## 12. Documentación, contradicciones y código muerto

El canon es amplio, pero el README del Motor contradice el estado más reciente de fases 13/14. Cierres antiguos se interpretaron sólo como evidencia histórica. Se confirmaron dos archivos frontend huérfanos, rutas ocultas y un productor del Motor sin consumidor productivo. No se recomienda borrar nada antes de tener pruebas de caracterización y confirmar que no existan consumidores externos.

## 13. Bloqueadores de producción

1. AUD-001 a AUD-003: perímetro, portal y secreto JWT.
2. AUD-004 a AUD-007: defaults, drift, downgrade y respaldo/head.
3. AUD-008 a AUD-011: custodia de datos, uploads, sesiones y ownership.
4. AUD-012 a AUD-016: fiscalidad, pruebas HTTP, operación, dependencia vulnerable e identidad documental.
5. CI/E2E/observabilidad/restauración y despliegue reproducible.

Hasta cerrar y volver a auditar esos puntos, cualquier salida a producción aceptaría riesgos críticos conocidos.

## 14. Evidencia externa requerida para cerrar lo no verificable

Se necesita, por canal seguro y con datos anonimizados cuando aplique:

1. Dump PostgreSQL histórico sanitizado que represente el esquema/datos reales, con su valor `alembic_version` y log de respaldo.
2. Inventario de entornos y variables con valores secretos redactados; secretos temporales sólo mediante vault/canal seguro si se autoriza una prueba.
3. Configuración real de reverse proxy, TLS, DNS, procesos/servicios, backups, retención y restore; logs del último simulacro.
4. Usuarios de prueba por rol y dataset sintético/anonimizado para recorridos browser.
5. Cuenta Sandbox Facturama de prueba, documentación contractual vigente, ejemplos anonimizados de XML/PDF, cancelación, sustitución, PPD, complemento y nota de egreso.
6. Plantillas oficiales originales y resultados esperados para las 23 Hojas de Campo; casos metrológicos aprobados por Calidad.
7. Masters XLSX y paquetes de retorno representativos, libres de datos personales, incluidos escenarios mismatch/no identificado.
8. Política institucional de identidad, logos/fuentes oficiales, vigencias y ejemplos aprobados de cotización, OT, certificado, factura y recibo.
9. Contratos y credenciales de prueba para correo, almacenamiento/Drive u otras integraciones externas realmente requeridas.
10. SLO/SLA, volumen esperado, concurrencia, tamaño máximo de archivos, retención, RPO/RTO y requisitos regulatorios aplicables.

No deben adjuntarse credenciales productivas ni datos personales sin saneamiento.

## 15. Limitaciones y falsos positivos evitados

- No hubo E2E de navegador ni invocación PAC productiva.
- No se verificó upgrade desde respaldo histórico.
- No se ejecutó escáner de CVE Python ni análisis de entropía/historial Git.
- Los conteos de auth son estáticos; dependencias indirectas podrían endurecer alguna ruta, pero no eliminan los endpoints confirmados sin guard.
- El drift de Alembic requiere clasificación manual: algunos índices especializados pueden ser intencionales y no deben eliminarse automáticamente.
- Los archivos huérfanos se clasifican como candidatos, no como borrables.

## 16. Conclusión

La estrategia correcta no es reescribir el ERP. Es congelar expansión, cerrar el perímetro, estabilizar el esquema y el respaldo, proteger archivos, completar fiscalidad y demostrar los recorridos críticos con pruebas HTTP, browser y operación repetible. El Motor debe permanecer simple y sin nueva fase hasta que la plataforma que lo aloja alcance ese mínimo.
