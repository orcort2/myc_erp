> Estado: **APROBADO CON OBSERVACIONES**
>
> Corte: 2026-08-10
>
> Alcance: únicamente Integridad ETS

# Cierre técnico — Sprint Integridad ETS

## Resultado

El sprint consolidó las reglas de órdenes de servicio en
`backend/app/services/service_orders.py`. El router ETS conserva sólo contrato
HTTP, autenticación/permisos, validación y respuesta. Las excepciones operativas
quedaron separadas en solicitud, autorización y ejecución persistentes.

## 1. Archivos modificados

- Modelo/agregado: `backend/app/models/service_order.py`,
  `backend/app/models/service_order_exception.py`, `backend/app/models/__init__.py`.
- Servicio/HTTP/schemas: `backend/app/services/service_orders.py`,
  `backend/app/routers/service_orders.py`, `backend/app/schemas/service_order.py`.
- Persistencia: migración `e7b62b8a9421_add_service_order_exception_lifecycle.py`.
- Pruebas: `backend/tests/test_service_order_integrity.py`, conformidad API y
  head único de esquema.
- Frontend ETS: `ServiceOrdersPage.jsx`, `exceptionAuthority.js` y su prueba.
- Seguridad reproducible al cierre ETS: inventario HTTP de 358 operaciones;
  el P0 posterior de autenticación retiró una ruta duplicada y dejó 357.
- Documentación canónica, estado operativo, inventario de archivos y este cierre.
- Respaldo local regenerado: `backup_erp_myc_antes_prueba.sql`.

## 2. Duplicaciones eliminadas

Se retiraron del router las implementaciones locales y helpers que duplicaban
listado, consulta, creación, actualización, máquina de estados, cierre,
excepción, baja, folios y generación de OT. También se eliminó el sombreado de
imports que hacía que algunas rutas ejecutaran copias divergentes.

## 3. Autoridad canónica

`backend/app/services/service_orders.py` contiene ahora las funciones canónicas
de consulta, creación, actualización, ciclos de firma, transición/cierre,
solicitud/autorización/ejecución de excepción y desactivación. Mantiene la
expansión única de Servicios Compuestos, snapshots, folios, auditoría y eventos.

## 4–6. Lifecycle final y ausencia de mutaciones prematuras

```text
POST /service-orders/{ets}/exceptions
  → requested
  → sin cambio de ServiceOrder.status
  → sin llamada a resincronización de Invoice

POST /service-orders/{ets}/exceptions/{id}/authorize
  → authorized
  → sin cambio operativo ni fiscal

POST /service-orders/{ets}/exceptions/{id}/execute
  → exige authorized
  → revalida ServiceOrder.status contra el snapshot de solicitud
  → aplica target_status cuando corresponde
  → resincroniza sólo facturas draft/pending elegibles
  → executed
```

La tabla `service_order_exception_requests` conserva actores, etapas, estado
destino, estado ETS al solicitar, motivo y timestamps. Ejecutar `requested` o
un expediente cuyo ETS cambió devuelve 409 sin efectos. La UI ETS siempre
solicita; ya no convierte el clic de Administrador en ejecución directa.

## 7. Propagación del actor

Todas las rutas mutantes del router reciben un usuario autenticado y envían
`current_user.id` al servicio: crear, actualizar, confirmar firmas, transitar,
cerrar, solicitar/autorizar/ejecutar excepción, desactivar, cargar Captura y
acciones masivas de certificados. Las pruebas caracterizan creación,
actualización, transición, excepción y baja con `AuditLog.user_id` no nulo.

## 8. Eventos y audit logs

- Transición ordinaria conserva `service_order.status_changed` y su actor.
- Excepciones publican eventos idempotentes
  `service_order.exception_requested`, `.exception_authorized` y
  `.exception_executed` dentro de la transacción propietaria.
- Los audits registran actor, evento/acción, timestamps del agregado,
  estado anterior/nuevo, comentario y efecto ETS ejecutado.
- La resincronización fiscal conserva su audit propietario y recibe el actor de
  ejecución; nunca se invoca durante `requested` o `authorized`.

## 9. Pruebas agregadas o modificadas

`test_service_order_integrity.py` añade ocho pruebas de caracterización e
integridad: audit/evento/actor de transición; actor en crear/actualizar/baja;
inmutabilidad ETS/Invoice en solicitud y autorización; bloqueo de ejecución no
autorizada; ejecución y efectos autorizados; revalidación ante drift; ausencia
de reglas duplicadas en router; y presencia de actor en todas sus mutaciones.
Se actualizaron las pruebas reproducibles del inventario API y head Alembic.

## 10. Regresión

| Validación | Resultado |
| --- | --- |
| ETS focal + contratos relacionados | 16 passed |
| Excepciones, facturación, auditoría/eventos y conformidad API | 54 passed |
| Backend completo final | 458 passed, 19 subtests, 3 warnings |
| Frontend `node --test` | 39 passed |
| Frontend `npm run build` | correcto; warning de chunk >500 kB |
| `scripts/myc doctor` | correcto |
| `scripts/myc build` | correcto |
| Alembic `current` / `heads` / `check` | `e7b62b8a9421`, head único, sin drift |
| Respaldo | regenerado y alineado con `e7b62b8a9421` |

## 11. Capability gate

`venv/bin/python scripts/validate_capability_catalog.py --check` continúa
fallando. El resultado no cambió por este sprint: 20 permisos del inventario no
están en el catálogo técnico y 2 no están en el bootstrap evaluado. Las dos
capacidades concretas son `portal.view` y
`reference_standard_certificates.delete`. Las rutas ETS nuevas reutilizan el
permiso vigente `service_orders.update`, por lo que el fallo es deuda
independiente `TD-027`, no una regresión ETS.

## 12. Riesgos y deuda pendiente

- Autorización y ejecución son acciones HTTP distintas, pero ambas permanecen
  bajo la capacidad gruesa vigente `service_orders.update`; granularizar RBAC
  exige reconciliar primero el Catálogo Institucional y queda fuera del sprint.
- La superficie de autenticación de certificados duplicada entre ETS y Calidad
  no fue modificada por este sprint y quedó resuelta después en
  `CERTIFICATE_AUTHENTICATION_INTEGRITY_SPRINT_2026-08-10.md`.
- El restore drill del respaldo regenerado no se repitió; Alembic local y el
  contenido/versionado del dump sí fueron verificados.
- `npm audit` mantiene dos vulnerabilidades altas (`nanoid`, `postcss`) ajenas
  a ETS; no se aplicó `npm audit fix`.

No se inició otro P0/P1, refactor visual ni fase del Motor de Resoluciones.

## Micro-sprint de cierre final — 2026-08-10

### 1. Contratos de actor cerrados

Las mutaciones críticas ETS ya no aceptan omitir `user_id` y rechazan además
un `None` explícito antes de tocar persistencia. El contrato obligatorio cubre
creación, actualización, firmas, transición/cierre, baja, solicitud,
autorización y ejecución de excepciones, carga de Captura, carga de PDF,
autenticación y liberación individual/masiva de certificados desde ETS. Los
routers entregan siempre `current_user.id` y los llamadores internos cubiertos
por pruebas crean o propagan un actor real.

Se preservaron actores opcionales únicamente donde no representan una mutación
humana directa: `_ensure_active_user`, cuyo parámetro identifica al asesor o
técnico asignado; y `create_certificate`, porque el certificado también nace
automáticamente al crear Equipos o desde integraciones técnicas. El resto del
lifecycle institucional de Certificados —edición, estados, Captura, Calidad,
match, carga, autenticación, liberación y baja— exige actor. Esto no modifica
la duplicación de superficies que pertenece al P0 separado de Certificados.

### 2. Autoautorización administrativa formalizada

Un mismo usuario con rol Administrador puede solicitar, autorizar y ejecutar
la misma excepción ETS. Esto no compacta comandos ni estados: persisten tres
acciones consecutivas y cada una conserva actor, timestamp, audit log y evento
propios. El expediente mantiene motivo, comentario de autorización y estado
ETS congelado; la ejecución conserva el resultado operativo. La prueba de
contrato usa el mismo `user_id` en los tres pasos y verifica la evidencia
independiente.

### 3. Ausencia de efectos anticipados

Las pruebas vuelven a demostrar que `requested` y `authorized` no cambian
`ServiceOrder.status`, no alteran `Invoice`, no invocan resincronización y no
ejecutan efectos derivados. Sólo `executed`, después de revalidar el estado
congelado, aplica el destino y llama a la resincronización con el actor.

### 4. Revisión read-only del catálogo de capacidades

Las tres rutas actuales usan el permiso vigente `service_orders.update`. El
catálogo técnico congelado sólo describe la solicitud histórica con
`service_orders.create`; no contiene capacidades genéricas separadas para
solicitar, autorizar y ejecutar. `service_orders.additional_equipment.*` y
`quotations.exceptions.*` pertenecen a otros dominios y no son equivalentes
reutilizables. La recomendación futura es gobernar tres capacidades semánticas
ETS separadas antes de incorporarlas a catálogo/bootstrap/roles; este sprint
no propone claves, no modifica el catálogo congelado y no relaja el permiso
actual.

### 5. Pruebas y regresión final

| Validación | Resultado |
| --- | --- |
| ETS/Certificados/Facturación focal | 67 passed, 7 subtests |
| Backend completo | 460 passed, 19 subtests, 3 warnings |
| Frontend `node --test` | 39 passed |
| Frontend `npm run build` | correcto; warning de chunk >500 kB |
| `compileall` / `pip check` / `scripts/myc doctor` | correctos |
| Alembic `check` | sin operaciones nuevas |
| Capability gate | falla: 20 brechas catálogo y 2 bootstrap |

El gate conserva como brechas de bootstrap `portal.view` y
`reference_standard_certificates.delete`; es `TD-027`, independiente de ETS.
El cierre posterior `TD_027_CAPABILITY_GATE_RECONCILIATION_2026-08-11.md`
reemplaza este resultado histórico con gate verde 19/0 y decisiones pendientes.
No hubo cambio de esquema o datos en el micro-sprint, por lo que no correspondió
regenerar el respaldo ya alineado con `e7b62b8a9421`.

### 6. Dictamen

Las dos observaciones del micro-sprint quedan cerradas. El sprint pasa de
**EN REVISIÓN** a **APROBADO CON OBSERVACIONES** por deudas independientes que
no invalidan la integridad entregada: granularidad futura de capacidades ETS,
capability gate global divergente y el P0 separado de superficie autenticadora
de Certificados.
