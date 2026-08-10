# Auditoría integral del ERP MYC — corte 2026-08-10

> Naturaleza: fotografía técnica, funcional y arquitectónica de sólo lectura.
>
> Repositorio: `3490e40` (`respaldo-antes-perfil-nuevo-2026-07-23`).
>
> Dictamen: **NO APTO PARA PRODUCCIÓN**.
>
> Readiness general ponderado: **61/100**.

## Resumen ejecutivo

El ERP tiene una base funcional amplia y comprobable: SPA React, API FastAPI,
PostgreSQL/SQLAlchemy/Alembic, 356 operaciones HTTP clasificadas
deny-by-default, 111 tablas ORM, almacenamiento institucional acotado,
generadores PDF/XLSX/XML/ZIP, Facturama Sandbox, Portal del Cliente aislado y
un Motor de Resoluciones durable. La regresión disponible es verde: 450
pruebas backend y 40 frontend; el build Vite y `compileall` finalizan bien;
la base local, el dump y el código declaran el mismo head
`c8a51e2d7f40`, y `alembic check` no detecta drift.

El sistema todavía no debe operar en Producción. El bloqueador funcional más
grave es el flujo legacy de excepciones ETS: una acción registrada como
`exception_requested` cambia el estado y resincroniza facturas en la misma
operación. Además, el router ETS contiene copias completas de reglas que
también existen en el servicio; las rutas activas pueden ejecutar la versión
del router y omitir efectos presentes en la versión canónica. Varias
mutaciones de Clientes, Catálogo, Equipos y ETS pasan autorización global,
pero no reciben el actor en el endpoint y terminan registrando `user_id=NULL`.

Persisten riesgos de sesión (JWT en `localStorage`, refresh de 30 días sin
rotación/revocación, sin MFA ni recuperación), ausencia de rate limit por IP,
CFDI productivo incompleto, correo del Portal inexistente en Producción,
storage exclusivamente local, falta de antimalware, CI/CD, E2E browser,
observabilidad y readiness real. `npm audit --omit=dev` reporta dos
vulnerabilidades altas (`nanoid` y `postcss`).

La documentación también tiene deriva verificable: el validador obligatorio
del catálogo de capacidades falla (20 permisos del inventario fuera del
catálogo y 2 fuera del bootstrap); `CURRENT_SCOPE` y `CURRENT_PROCESS_FLOW`
todavía describen el Portal anterior a membresías; el README presenta Fases
13/14 obsoletas; y observaciones abiertas contradicen cierres de seguridad.

Resultado de los 42 módulos institucionales: **1 SELLADO, 9 CASI SELLADOS,
28 EN DESARROLLO, 2 PENDIENTES y 2 NO INICIADOS**. Sólo Control Documental V1
está sellado, dentro de su alcance congelado.

## Método, alcance y límites

Se revisaron código backend/frontend, modelos, schemas, routers, servicios,
permisos, migraciones, scripts, pruebas, documentación, configuración,
integraciones, archivos y recursos. Se contrastaron el canon documental, los
commits posteriores a la auditoría del 2026-08-03 y el estado ejecutable.

Reglas aplicadas:

- existencia de código, build verde o cierre histórico no equivalen a cierre;
- cada conclusión cita evidencia local o se marca no verificada;
- no se llamó a Facturama, correo ni servicios productivos;
- no se ejecutó downgrade, restore ni ciclo destructivo por la restricción de
  sólo lectura; se conservó como evidencia histórica el drill fechado;
- no se modificó la base compartida ni se corrigió código;
- `frontend.zip`, ya eliminado al iniciar (`D frontend.zip`), se preservó.

No se verificaron visualmente todos los roles con navegador, 23 plantillas
reales de Hojas de Campo, carga, concurrencia, recuperación ante desastre,
Sandbox Facturama de extremo a extremo, correo productivo ni infraestructura
externa. Estas ausencias impiden elevar módulos a `SELLADO`.

## Inventario verificable

| Superficie | Resultado actual | Evidencia |
| --- | ---: | --- |
| Archivos rastreados | 845 | `git ls-files` |
| Archivos del proyecto excluyendo dependencias/build | 6,673 | `find` con exclusiones |
| Python en `backend/app` | 308 | conteo físico |
| Archivos en `frontend/src` | 169 | conteo físico |
| Migraciones Alembic | 86 | `backend/migrations/versions` |
| Operaciones HTTP | 356 | `iter_route_operations(app)` |
| GET / POST / PATCH / DELETE / PUT | 137 / 163 / 34 / 20 / 2 | introspección FastAPI |
| Operaciones sin clasificación | 0 | guard transversal |
| Tablas / columnas ORM | 111 / 1,811 | `Base.metadata` |
| FKs / índices / `UniqueConstraint` | 322 / 521 / 83 | `Base.metadata` |
| Pruebas backend / frontend | 61 archivos / 10 archivos | inventario de suites |
| Módulos institucionales | 42 | catálogo funcional aprobado |

La arquitectura real es:

```text
React 19 + routing propio + JWT localStorage
  -> frontend/src/services/api.js (1,805 líneas)
    -> FastAPI (356 operaciones; guard deny-by-default)
      -> routers y services con separación desigual
        -> SQLAlchemy/PostgreSQL/Alembic
        -> storage local + PDF/XLSX/XML/ZIP + LibreOffice
        -> Facturama
        -> Portal con identidad/membresía propias
        -> Motor de Resoluciones + outbox + cola + worker + API/SDK
```

El mapa ampliado está en [`INVENTARIO_PROYECTO.md`](INVENTARIO_PROYECTO.md) y
la clasificación de los 42 módulos en [`ESTADO_MODULOS.md`](ESTADO_MODULOS.md).

## Hallazgos principales

| ID | Severidad | Hallazgo | Evidencia verificable | Impacto |
| --- | --- | --- | --- | --- |
| AI-001 | CRÍTICO | Excepción ETS mezcla solicitud y ejecución | `backend/app/services/service_orders.py:808`; cambia `status`, resincroniza factura y registra `exception_requested` | Bypass de segregación e integridad de estado/factura |
| AI-002 | CRÍTICO | Reglas ETS duplicadas y divergentes | `backend/app/routers/service_orders.py:308-562` duplica crear/actualizar/transitar/excepción/baja de `services/service_orders.py`; el router sombrea imports | Un endpoint puede omitir eventos o resincronización del servicio |
| AI-003 | ALTO | Auditoría sin actor en mutaciones protegidas | rutas de Clientes, Catálogo, Equipos y ETS no inyectan `current_user`; servicios admiten `user_id=None` | Trazabilidad insuficiente para cambios críticos |
| AI-004 | ALTO | Sesiones no revocables y expuestas a XSS | `frontend/src/services/api.js:1-36`; JWT sin `jti`; refresh 30 días | Robo de sesión prolongado y cierre selectivo imposible |
| AI-005 | ALTO | CFDI productivo incompleto | Facturama Sandbox; sin cancelación/sustitución, PPD/complemento ni CFDI egreso | Bloquea operación fiscal completa |
| AI-006 | ALTO | Correo del Portal no existe en Producción | `portal/mail_service.py` sólo agrega outbox fuera de prod | Registro/invitación no entregables en operación real |
| AI-007 | ALTO | Gate institucional de capacidades falla | `validate_capability_catalog.py --check`: 20 gaps catálogo, 2 bootstrap | Cambios de API/Portal no reconciliados con gobierno aprobado |
| AI-008 | ALTO | Dos CVE altas frontend | `npm audit --omit=dev`: `nanoid`, `postcss` | Riesgo de disponibilidad y lectura de sourcemaps según uso/build |
| AI-009 | ALTO | Sin E2E browser/CI/deploy/readiness/observabilidad | no hay Playwright/Cypress/workflows/Docker/métricas; `/api/health` estático | Regresiones de rol, despliegue y proveedor no se detectan |
| AI-010 | MEDIO | Autenticación duplicada fuera de Calidad | batch en router ETS y acción en `ServiceOrdersPage`; Calidad también autentica | Se diluye ownership de Calidad y aumenta regresión UX |
| AI-011 | MEDIO | Almacenamiento local sin AV/retención/replicación | `storage_service.py` protege paths y atomicidad, no durable/AV | Pérdida, acumulación o archivo malicioso estructuralmente válido |
| AI-012 | MEDIO | Listados y paquetes sin presupuesto de escala | 100 usos de `.all()`; ZIP y documentos de salida en memoria | Latencia/memoria crecen con el volumen |
| AI-013 | MEDIO | Frontend monolítico | `ServiceOrdersPage` 4,598; `global.css` 8,472; JS 1,040 kB | Alto costo de cambio y carga inicial |
| AI-014 | MEDIO | Dos candidatos huérfanos confirmados | `NotificationCenterPage.jsx`, `InvoiceWorkbenchModal.jsx` sin importadores | Superficie legacy y confusión de mantenimiento |
| AI-015 | MEDIO | Productor del segundo vertical no conectado a origen | `request_additional_equipment_resolution` sólo aparece en pruebas | Fase 14 no cierra experiencia productiva desde ETS |
| AI-016 | MEDIO | CORS ignora configuración | `main.py:96-105` hardcodea orígenes; `settings.cors_origins` queda paralelo | Deriva de entornos y configuración inefectiva |
| AI-017 | MEDIO | Login sin rate limit global | bloqueo por cuenta 5/15, sin límite por IP/dispositivo | Fuerza bruta distribuida y bloqueo provocado de cuentas |
| AI-018 | MEDIO | Portal siembra permisos/roles al arrancar | `main.py:60-64`, `portal/permission_service.py` hace `commit` | Startup mutante, carrera/desfase y despliegue read-only difícil |
| AI-019 | BAJO | Controles nativos y accesibilidad no automatizada | `window.alert/confirm`; sin axe/E2E | UX inconsistente y barreras no detectadas |
| AI-020 | BAJO | Dos warnings de librerías y Alembic legacy | Starlette/httpx, `crypt`, `prepend_sys_path` | Deuda de actualización futura |

No se confirmó SQL injection: las consultas observadas usan SQLAlchemy y los
casos SQL textual del Motor están acotados. Tampoco se encontraron secretos
reales rastreados mediante búsqueda nominal; `backend/.env.example` sólo
contiene placeholders. No se ejecutó un escáner de entropía/historial Git, por
lo que esa conclusión queda **NO VERIFICADA**.

## Auditoría especial de módulos críticos

### ETS, Órdenes de Trabajo, Equipos y firmas

El flujo dispone de estados, cupo de 10 equipos por OT, ciclos de firmas,
folios y snapshots. `confirm-signatures` ya existe una sola vez y delega en el
servicio. Sin embargo, el router aún redefine el resto del agregado ETS y sus
mutaciones principales no propagan actor. La excepción legacy es P0. La
compatibilidad entre `work_order_number` y `service_work_orders`, junto con
campos legacy de firma, sigue activa y no puede calificarse como obsoleta.

### Hojas de Campo y Captura

Hay plantilla/snapshot, resultados, firmas, estados, PDF, paquetes y perfiles
de upload con defensa ZIP. No existe evidencia integral de las 23 plantillas
oficiales, el renderer React y el PDF backend pueden divergir, y la semántica
metrológica/automatizaciones permanece incompleta. El retorno no identificado
carece de resolución formal y no hay E2E HTTP/browser del paquete real.

### Calidad y Certificados

Calidad valida readiness, aprueba el Master y autentica PDF; Certificados
versiona, expone verificación firmada y condiciona liberación al estado
financiero. El Portal deriva cliente desde membresía y prueba IDOR 404. No se
puede cerrar mientras ETS mantenga autenticación batch/individual paralela y
falte E2E de verificación/liberación con documentos representativos.

### Facturación, pagos y documentos fiscales

El Workbench respeta el controlador único y `Invoice`; `EtsBillingTab` es
consumidor contextual. Existen borrador, conceptos, snapshot fiscal, intentos,
reconciliación, XML/PDF PAC, PDF institucional, pagos, recibos, cartera y
preservación de `paid/partially_paid` al emitir. Permanecen: descarte de cambios
no autosalvados, Facturama sólo Sandbox, cancelación/sustitución, PPD,
complemento, nota fiscal de egreso, webhooks/retries y E2E externo. La nota de
crédito actual es administrativa, no CFDI de egreso.

### Control Documental y archivos

Control Documental V1 conserva su `SELLADO`: lista maestra, versiones,
publicación/activación, obsolescencia y Plantillas Maestras. La ETAPA 3 aplica
límites, MIME/firma/estructura, ZIP seguro, paths confinados, checksum y
escritura atómica. El almacenamiento sigue local y falta política operativa de
retención, antivirus y replicación. Es una limitación transversal de
Producción, no una reapertura funcional de V1.

### Seguridad y permisos

La protección real backend mejoró sustancialmente: 356/356 rutas clasificadas,
allowlist anónima de 11 operaciones, JWT productivo con guard de entropía,
Portal con contexto separado y ownership, y navegación frontend por permisos.
La debilidad actual ya no es un API anónimo, sino granularidad y trazabilidad:
permisos amplios, dos claves del inventario fuera del bootstrap, cambios sin
actor, sesión no revocable, falta de rate limiting/MFA y falta de pruebas
browser exhaustivas. Véase [`SEGURIDAD_Y_PERMISOS.md`](SEGURIDAD_Y_PERMISOS.md).

### Base de datos

Existe un head único `c8a51e2d7f40`; base local y dump coinciden; el check ORM
no reporta operaciones. El ciclo base→head→base→head y restore de 112 tablas
figuran como validados el 2026-08-05, pero no se repitieron por la prohibición
de escritura de esta auditoría. No se identificó ninguna tabla demostrablemente
obsoleta. Sí hay columnas/relaciones legacy todavía consumidas (OT, firmas,
catálogos fiscales), por lo que retirarlas ahora sería inseguro.

### Motor de Resoluciones

Fases 0–13 tienen cierres aprobados; Fase 14 está terminada técnicamente y en
revisión. El Motor conserva versionado, inmutabilidad, lifecycle, seguridad,
idempotencia, locks, compensación, evidencia, outbox, worker, API/SDK y dos
verticales. Sigue sin cerrarse la integración de origen del equipo adicional,
la operación/supervisión del worker y la revisión formal de Fase 14. El diseño
es localizable y reemplazable por capas; `resolution_center/workflow.py` con
1,289 líneas es el foco de crecimiento a vigilar, sin justificar refactor
prematuro.

## Desviaciones documentación ↔ código

1. `CURRENT_SCOPE.md` y `CURRENT_PROCESS_FLOW.md` describen coincidencia de
   correo y `PortalMembership` futuro; el código usa membresía persistente,
   multirrol, Portal frontend y administración desde el 2026-08-05.
2. `README.md` dice Fase 13 en revisión y Fase 14 no iniciada; los cierres y el
   código sitúan 13 aprobada y 14 terminada/en revisión.
3. `BACKUP_ESTADO_ACTUAL.md` afirma que el validador de capacidades pasa; la
   ejecución actual falla con 20/2 brechas.
4. `OBSERVATIONS_REGISTER.md` mantiene abiertas OBS-004/005 sobre navegación y
   Clientes no autorizados, contradiciendo OBS-R58/R61 y las 356 rutas.
5. `TECHNICAL_DEBT.md` afirma ruta `confirm-signatures` repetida; hoy hay una
   ruta, aunque la duplicación sustantiva router/servicio continúa.
6. El catálogo funcional M38 aún dice que administración de vínculos está
   reservada; la funcionalidad ya existe. El catálogo está congelado y no se
   reescribe sin un proceso de versión, por lo que se registra la desviación.
7. El índice refería un respaldo histórico archivado que no existe físicamente
   en el workspace; se marcó como referencia pendiente, sin inventar contenido.

## Readiness 0–100

Escala usada: 0–19 ausente; 20–39 prototipo; 40–59 funcional incompleto;
60–79 operativo con deuda; 80–94 listo sujeto a validación; 95–100 cerrado y
operado. Las notas no se derivan de cantidad de archivos.

| Dimensión | Nota | Evidencia determinante |
| --- | ---: | --- |
| Arquitectura | 70 | contratos fuertes en Workbench/Compuestos/Motor; duplicación ETS y monolitos |
| Backend | 70 | API y servicios amplios, guard global; actor ausente y transacciones desiguales |
| Frontend | 63 | flujos principales y Portal; bundle/monolitos, sin E2E/accesibilidad |
| Base de datos | 82 | head/check/dump alineados; restore actual no repetido y legacy activo |
| Seguridad | 60 | perímetro/Portal/JWT corregidos; sesiones, rate limit, CVE y headers pendientes |
| Permisos | 58 | 356 rutas clasificadas y UI filtrada; gate fallido, claves amplias y trazabilidad |
| Pruebas | 68 | 490 tests verdes; sin E2E, carga, cobertura ni proveedores reales |
| Documentación | 61 | canon extenso; varias contradicciones y validador divergente |
| Observabilidad | 32 | logs puntuales; sin métricas, tracing, alertas ni readiness real |
| Mantenibilidad | 52 | servicios claros en varios dominios; archivos gigantes y duplicación ETS |
| Integraciones | 48 | Facturama/LibreOffice/API/SDK presentes; correo/Producción/Drive incompletos |
| Preparación para producción | 44 | esquema y seguridad base sólidos; P0/P1 operativos/fiscales pendientes |

Promedio ponderado: **61/100**. Seguridad/permisos, producción, integraciones y
pruebas operativas reciben mayor peso que estética o cantidad de código.

## Conclusión

El ERP ya no presenta los tres críticos de perímetro del corte 2026-08-03 y su
esquema es reproducible según evidencia actual e histórica. El riesgo se ha
movido al interior: consistencia del agregado ETS, trazabilidad de actor,
sesiones, fiscalidad y operación. La ruta a una versión estable es cerrar
AI-001/002, hacer íntegra la auditoría de mutaciones, reconciliar capacidades,
completar el circuito CFDI y demostrar los recorridos críticos por rol en una
plataforma observable y recuperable. No se recomienda abrir nuevas fases antes
de esos gates.

Los comandos y resultados están en [`RESULTADOS_PRUEBAS.md`](RESULTADOS_PRUEBAS.md),
la deuda en [`DEUDA_TECNICA.md`](DEUDA_TECNICA.md) y el orden de cierre en
[`PLAN_CIERRE.md`](PLAN_CIERRE.md).
