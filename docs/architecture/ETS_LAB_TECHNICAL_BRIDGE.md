> Estado: VIGENTE — Fase 1 implementada; Fases 2 y 3 (calibración MYC Mobile, proyección/gobierno ERP y Captura PDF-only) en revisión
>
> Corte: 2026-09-29
>
> Autoridad: contrato acotado del vínculo ERP ETS ↔ LAB

# Vínculo histórico ETS ↔ LAB — Fase 1

## Autoridad y alcance

LAB/MYC Mobile mantiene la autoridad técnica completa. El ERP sólo consulta
candidatos y administra una asociación histórica entre `ServiceOrder` y una
raíz `LabWorkOrder`. Esta referencia es la excepción explícita y acotada a la
separación anterior de dominios; no conecta los pipelines técnicos.

No incluye frontend, Captura, Calidad, Certificados, handoff, paquetes LAB
desde ETS, sincronización de estados, creación de grupos ni cambios Mobile.
No copia datos a `Equipment` ni a `ServiceWorkOrder`; tampoco mapea `Client`
a `LabClient` ni compara sus nombres para decidir elegibilidad.

## Persistencia

`backend/app/models/service_order_lab_link.py` contiene `ServiceOrderLabLink`
en una tabla dedicada. Se separa de `service_order.py` para mantener localizado
el contrato del bridge y evitar ampliar el agregado ETS con otro lifecycle.
`ServiceOrder.lab_links` ofrece el historial ordenado por `linked_at DESC, id DESC`,
sin delete-orphan ni cascada de eliminación. La lectura del activo utiliza una
consulta explícita; no depende de una colección ORM previamente cargada.

Cada registro conserva ETS, raíz LAB, estado, fecha/actor de alta, fecha/actor
baja, motivo, sucesor, `created_at` y `updated_at`. Estados: `active`, `unlinked`,
`replaced`. Desvincular nunca borra la fila ni las OT. Revincular crea una nueva
fila aunque la raíz ya figure en el historial.

- `uq_service_order_lab_link_active_ets`: único por ETS donde `status='active'`.
- `uq_service_order_lab_link_active_root`: único por raíz donde `status='active'`.
- Ambos índices son parciales en PostgreSQL y SQLite; no restringen reutilización histórica.
- Checks: estados permitidos; activo sin campos de baja; inactivo con fecha,
  actor y motivo no vacío; sucesor sólo en `replaced` y distinto de sí mismo.
- FKs `RESTRICT` a ETS, raíz LAB, actores y sucesor. Incluso un vínculo inactivo
  impide purgar físicamente su ETS/raíz mientras exista la referencia histórica.
  No se modificaron los servicios de borrado existentes.
- Validez de raíz y correspondencia del sucesor se gobiernan en el servicio:
  no hay un trigger para validar otra tabla ni para inferir un sucesor.

## Dominio y transacción

`backend/app/services/service_order_lab_links.py` centraliza todas las reglas.
Las mutaciones requieren actor, bloquean el ETS y, para link/replace, la raíz
LAB destino con `FOR UPDATE`. Refrescan el estado persistido tras el lock.
Los índices únicos son la defensa final frente a carreras, incluidas escrituras
que omitan esos locks. Conflictos de esos índices se traducen a HTTP 409.

La raíz se resuelve con `root_work_order_id` si existe, o el ID de la propia OT.
Se aceptan raíces legacy con NULL y raíces que apuntan a sí mismas, como las
creadas por LAB actualmente. Una referencia a una hija de otra raíz se rechaza;
no se recorre una cadena malformada ni se persiste la hija como autoridad.

ETS inexistente: 404. ETS inactivo, `closed` o `cancelled`: 409 en cualquier
mutación, reutilizando `TERMINAL_STATUSES` del dominio ETS. El historial sigue
siendo consultable después del cierre/baja. OT inexistente: 404. Raíz inválida
o cancelada: 409 para link/replace. Los demás estados LAB son vinculables.

- **Link:** misma raíz activa → devuelve la fila actual, sin nueva auditoría;
  otra raíz activa → 409 y exige replace; raíz ocupada por otro ETS → 409.
- **Replace:** exige activo y motivo recortado no vacío (422 si falta). Misma
  raíz → idempotente. Cierra el anterior como `replaced`, hace flush, inserta
  el nuevo y fija `replaced_by_link_id`; una sola transacción incluye auditoría.
  Cualquier fallo revierte cierre, nuevo registro y auditoría.
- **Unlink:** exige activo y motivo; conserva fila como `unlinked`. Sin activo
  devuelve 409. No requiere que el grupo siga siendo elegible para vincular,
  por lo que permite desvincular un grupo cancelado posteriormente en LAB.
- **Relink:** usa link ordinario y conserva todos los registros anteriores.

Cada servicio de mutación controla commit/rollback de la sesión de la petición,
siguiendo el patrón ETS existente. No debe componerse con cambios ajenos pendientes
en la misma sesión. La lectura del vínculo no habilita ninguna escritura técnica.

## API y permisos

Base: `/api/service-orders/{service_order_id}`. Autenticación ERP normal,
`require_permission(...)` y clasificación API access; sin `MobileSecurityContext`.

| Método | Sufijo | Permiso | Contrato |
| --- | --- | --- | --- |
| GET | `/lab-link` | `service_orders.read` | Vínculo activo o JSON null si no existe; ETS inexistente 404. |
| GET | `/lab-link/history` | `service_orders.read` | Todos los registros, más recientes primero; desempate por ID. |
| POST | `/lab-link` | `service_orders.create` **y** `service_orders.update` | `{"work_order_id": 123}`; devuelve fila activa (200). |
| POST | `/lab-link/replace` | `service_orders.create` **y** `service_orders.update` | `{"work_order_id": 456, "reason": "Corrección"}`. |
| POST | `/lab-link/unlink` | `service_orders.create` **y** `service_orders.update` | `{"reason": "Desvinculación"}`; devuelve fila histórica. |
| GET | `/lab-candidates?q=6401&limit=50` | `service_orders.read` | Resumen por raíz; limit 1–100 y q de hasta 40 caracteres. |

POST unlink sigue el patrón de acciones ETS con payload y evita un body DELETE.
Los permisos ya están en catálogo/roles; no se agregan códigos ni seeds.

### Revisión de cierre: autorización estructural

Preflight del cierre: rama `feat/ets-lab-technical-bridge`, worktree limpio y
HEAD igual a `origin/feat/ets-lab-technical-bridge` en
`108c713ed9cab08214dcf09da504904f2a0c0f4a`.

Inventario exacto de las capacidades relevantes declaradas en
`backend/app/core/permissions.py` al inicio de la revisión (sin cambios de roles):

| Rol (clave exacta) | service_orders.read | service_orders.create | service_orders.update |
| --- | --- | --- | --- |
| Administrador | vía `*` | vía `*` | vía `*` |
| Comercial | directo | directo | directo |
| Tecnico | directo | no | directo |
| Captura | directo | no | no |
| Calidad | directo | no | no |
| Finanzas | directo | no | no |
| Cliente | no | no | no |
| Desarrollador | directo | directo | directo |
| Operador | no | no | no |
| Auditor | no | no | no |

`auth.user_has_permission` consulta los roles activos de la BD y acepta permiso
literal, `*` o comodín de módulo. Ningún rol actual tiene `service_orders.*`.
La composición es aditiva: Técnico+Comercial o Técnico+Desarrollador satisface
ambas capacidades; Técnico+Calidad no. Roles inactivos no conceden autoridad.
Cliente sólo tiene `service_orders.read_own`, que no equivale a `read`.
Los overrides individuales persistidos no participan en `require_permission`.

**Decisión de cierre:** las tres mutaciones requieren **create AND update**.
`update` solo se concede al Técnico para edición operativa y no basta para
alterar el contexto estructural ETS↔LAB. El catálogo institucional M14.A02
("Crear y completar contexto") y M11.A06 ("Abrir expediente de servicio"), junto
con la matriz Comercial/Desarrollador, permiten usar `service_orders.create`
como capacidad adicional de gestión del contexto. Es una política compuesta
acotada a este bridge, no una equivalencia general entre crear ETS y gestionar
LAB. No existe una clave específica de vínculo LAB en el catálogo y no se crea
una nueva; tampoco se reutilizan permisos de borrado, Tickets o excepciones.

El guard central clasifica `create` como mínimo y cada ruta exige explícitamente
`create` y `update` mediante `require_permission`. Por ello el inventario CSV
expone el mínimo `create`; el requisito adicional `update` está en el router.
Ambos se prueban incluso sin el guard central. Lectura sigue en `read`.
Comercial, Desarrollador y Administrador conservan gestión; Técnico puro obtiene
403 para link/replace/unlink y conserva su edición ETS y lectura anteriores.
No se modifican catálogo, seeds, asignaciones ni autenticación. Los tokens de
contexto Mobile siguen siendo inválidos para estas rutas ERP.

Schemas dedicados exponen ID, ETS, raíz/folio, estado, fechas/actores/nombres,
motivo y sucesor, sin serializar colecciones técnicas. Los nombres y folio de
lectura son relaciones actuales; la auditoría conserva el folio del evento.

Candidatos: búsqueda literal parcial/exacta de folio (también hija), una fila
por raíz, orden folio/ID. Devuelve folios de todo el grupo histórico, snapshot
`client_name` de la raíz, estado de raíz, cantidad de OT, equipos activos,
ETS actualmente asociado e indicador de asociación a otro ETS. Incluye grupos
cancelados identificados por su estado; intentar vincularlos retorna 409. No
filtra por identidad comercial ni carga firmas, hojas, PDFs o entregas.

`/lab-candidates` es exclusivamente un buscador de **grupos LAB por folio**.
No constituye el flujo Mobile de búsqueda/selección de cotización o ETS. La
integración **Mobile → cotización/ETS** corresponde a una fase posterior; no
se amplía este endpoint ni se implementa esa integración en este cierre.

## Auditoría

`write_audit_log` registra en `service_orders`:

- `service_order.lab_group_linked`;
- `service_order.lab_group_replaced`;
- `service_order.lab_group_unlinked`.

`user_id` identifica al actor. `entity_id` y snapshots incluyen ETS, link, raíz,
folio y estado; reemplazo/baja conservan `previous_values`, motivo en `new_values`
y `comment`. El historial registra además actores y fechas de cierre y sucesor.
Reintentos idempotentes no generan eventos ficticios.

## Migración y validación

Revisión nueva `d7e9a1c3b5f0`, padre `c4d8e2f1a7b3` (único head anterior).
Upgrade crea exclusivamente la tabla, FKs, checks e índices; downgrade elimina
esa tabla y sus índices. No modifica migraciones históricas.

La validación usa PostgreSQL 16 aislado dentro de `tmp/ets-lab-validation` y
SQLite con FKs activadas. La base compartida por defecto permanece intacta.
Resultados y pendientes reproducibles: [corte operativo](../BACKUP_ESTADO_ACTUAL.md).
Pruebas: `backend/tests/test_service_order_lab_links.py`; concurrencia habilitada
con `ETS_LAB_POSTGRES_TEST_URL` en una base de pruebas (cada caso crea y elimina
un esquema aleatorio propio).

Una cancelación/cierre posterior en LAB no sincroniza ni cierra el vínculo ERP.
La Fase 1 preserva la referencia; no cambia la autoridad técnica ni introduce
una máquina de estados compartida. El despliegue deberá aplicar la migración
antes de habilitar estas rutas. No se realizó despliegue ni integración visual.

## Fase 2 — ETS de calibración ejecutado en MYC Mobile (2026-09-29)

La creación directa interna admite modalidades iniciales distintas por miembro,
con el mismo `_materialize_group` y un único vínculo a la raíz en la transacción
existente. [Contrato de modalidades LAB](LAB_WORK_ORDERS.md#modalidades-iniciales-de-grupos-directos-internos-2026-10-06).

### Regla estructural

Durante 2026, un ETS **nuevo** cuya composición activa (`ServiceOrderItem.operational_category`,
nunca nombres ni textos) es exclusivamente `calibration` se ejecuta técnicamente en
LAB/MYC Mobile. `create_service_order` y la reconstrucción excepcional deciden la
estrategia con `assign_productive_work_orders` después de congelar partidas:

- calibración exclusiva → `work_order_number = NULL`, `work_orders = []`, sin consumir la
  secuencia institucional OT;
- cualquier otra composición, incluida la **mixta** o sin partidas → flujo actual idéntico.

No existe `execution_mode`, selector ni fuente técnica persistida.
`backend/app/services/service_order_technical_flow.py` es la única política: reconoce el ETS
Mobile por la realidad estructural (calibración exclusiva + número NULL + sin
`ServiceWorkOrder`). Los ETS históricos siempre traen número (la columna era NOT NULL) y
no se reinterpretan. `ServiceOrderRead.calibration_flow_managed_by_mobile` es sólo una
proyección de lectura de esa política.

`service_orders.work_order_number` es `INT UNIQUE NULLABLE` (migración `e8f1a3c5d7b9` sobre
`d7e9a1c3b5f0`), sin backfill ni renumeración; nunca 0/-1/sentinel. El downgrade se niega
mientras existan ETS con número NULL.

### Frontera técnica (HTTP 409 `CALIBRATION_TECHNICAL_FLOW_MANAGED_BY_MOBILE`)

La política se aplica en servicios, no en routers: alta de `Equipment` productivo,
`FieldSheet` productiva (defensivo; depende de Equipment), firmas técnicas ETS (PATCH de
campos de firma y confirmación de ciclo), `Certificate` productivo que reservaría folio
propio, equipo adicional por Resoluciones (código de error equivalente) y PDF de OT ERP
(`/work-order-pdf`, `/work-orders-pdf`). No se bloquean lecturas históricas, Captura,
Calidad, Facturación, pagos, auditoría ni Activity. La reconstrucción física de un ETS se
bloquea mientras exista cualquier `ServiceOrderLabLink` (FK RESTRICT).

Compatibilidad con la fase documental siguiente: no se crean `Equipment` falsos. El futuro
`Certificate` LAB seguirá `equipment_id XOR lab_equipment_id` (como `FieldSheet`), con
`service_order_id` = ETS, `lab_equipment_id`, la `FieldSheet` LAB real y el folio ya
reservado por LAB, sin reservar otro.

### Selección desde MYC Mobile y creación atómica

`GET /api/mobile/v1/technician/lab-work-orders/erp-calibration-candidates?q=&limit=` es de
solo lectura, en el namespace Mobile (`MobileSecurityContext`, actor `internal`, permisos
Mobile existentes `work_orders.create`/`lab_work_orders.use`). Busca en servidor por folio
de cotización, folio ETS o nombre comercial/legal del cliente (mínimo 2, límite 20–25) y
sólo devuelve ETS activos, abiertos, con cotización activa `accepted` y calibración
exclusiva Mobile. No expone importes. Un ETS ya vinculado se devuelve con
`active_lab_root_id/folio` y `available=false`. `purchase_order` no es identificador.
El filtro de calibración exclusiva (al menos una partida activa y ninguna activa con
categoría distinta o nula) y la ausencia de `ServiceWorkOrder` se resuelven en SQL, de
modo que el `LIMIT` es exacto y ETS no elegibles nunca ocultan candidatos válidos.

El cliente del ETS no se relaciona con `LabClient` ni con `client_name` de LAB: no hay FK
ni comparación bloqueante ni sobrescritura. Mobile muestra el cliente ERP junto al
vínculo y advierte (sin bloquear) si difiere del cliente capturado en la OT. La
validación fuerte cliente/equipo/documento corresponde a la fase de ingestión documental.

`POST /lab-work-orders` y `POST /lab-work-orders/groups` aceptan `service_order_id`
**opcional** mediante schemas internos (`LabWorkOrderInternalCreate`,
`LabWorkOrderInternalGroupCreate`); el contrato externo `LabWorkOrderGroupCreate` y el flujo
de solicitud/aprobación no cambian. Sin `service_order_id` la creación legacy es idéntica.
Con él (`app/services/lab_erp_calibration.py`): bloquear ETS (antes de asignar folios) →
revalidar candidato y ausencia de vínculo → crear OT o grupo → `link_lab_root_in_transaction`
a la raíz (auditoría `origin=mobile_lab_creation`) → un solo commit. Cualquier fallo
revierte OT, grupo, vínculo, auditorías y secuencia LAB. Conflictos: 409
`SERVICE_ORDER_ALREADY_LINKED_TO_LAB` o `SERVICE_ORDER_NOT_MOBILE_CALIBRATION_CANDIDATE`.

`link_lab_root_in_transaction` es el núcleo sin commit compartido; los wrappers
`POST lab-link`, `replace` y `unlink` conservan contratos y la política `create`+`update`.
El Técnico sólo vincula al crear; reemplazar/desvincular sigue siendo administrativo en el
ERP. Una OT individual es su propia raíz; un grupo vincula sólo su raíz; las OT adicionales
heredan por `root_work_order_id` sin crear filas. `ServiceOrderLabLinkRead` agrega la
proyección `group_work_order_count`.

### Web

Para `calibration_flow_managed_by_mobile`, la página ETS conserva Resumen, Captura, Calidad,
Certificados, Facturación, Documentos, Actividad e Historial; no ofrece Equipos, Hojas de
Campo, firma técnica ni PDF/listado de OT ERP. Resumen muestra “Ejecución técnica MYC
Mobile” (folio raíz, OT del grupo y estado) o “Esperando OT MYC Mobile”, junto con
equipos esperados, Captura, Calidad, certificados, facturación y accesos a actividad/
documentos; no muestra métricas ERP de equipos u hojas. `openTabFromSummary` rechaza
cualquier pestaña no visible y un efecto devuelve a Resumen si quedara activa una pestaña
inexistente en un ETS Mobile. Las capacidades web se calculan sólo con partidas activas,
igual que `is_calibration_only`. Históricos y mixtos conservan la UI.

Fuera de alcance: paquete técnico LAB desde ETS, ingestión XLSX, cambios a Certificate,
Calidad/autenticación LAB, verticales Mobile distintas de calibración, sincronización de
estados, migración LabEquipment→Equipment y cualquier backfill.


## Fase 3 — Mobile único editor técnico; ERP proyecta, gobierna y entrega a Captura (2026-09-29)

### Autoridad (ciclo 2026)

**MYC Mobile es la ÚNICA interfaz de escritura técnica** de los servicios ejecutados
por la vertical LAB: OT/servicio, grupos y OT adicionales, equipos, recepción, flujo
técnico, firmas, hojas de campo, resultados, condiciones/observaciones, folios de
certificado, reaperturas/correcciones, cierre técnico y entrega LAB.

El ERP **gobierna pero no edita**: consulta/supervisión, trazabilidad, vínculo ETS ↔ LAB,
acciones administrativas de dominio (solicitar corrección/reapertura, cancelar/restaurar),
Captura documental, Calidad, autenticación, facturación, pagos y auditoría. No existe
ningún formulario ni endpoint ERP que modifique resultados, identidad técnica, firmas,
valores metrológicos o folios LAB. Nunca hay dos autoridades de escritura sobre el mismo dato.

### Proyección READ-ONLY

`backend/app/services/service_order_mobile_execution.py`: ETS → `ServiceOrderLabLink`
activo → raíz → grupo completo (`coalesce(root_work_order_id, id)`) → equipo **activo**
→ `current_field_sheet`. Consulta LAB directamente; no copia a `Equipment`,
`ServiceWorkOrder` ni tablas espejo y no persiste snapshots. `source="lab"` deja el
contrato abierto a futuras verticales Mobile sin asumir que todo servicio es calibración.

| Método | Ruta (`/api/service-orders/{id}`) | Permiso | Contrato |
| --- | --- | --- | --- |
| GET | `/mobile-execution` | `service_orders.read` | Grupo/OT/equipo (identidad, `report_number`, `is_good_condition`, observaciones de recepción, `service_type`, empresa vinculada, cliente documental `order`/`different` con snapshots, `certificate_folio`, `folio_status`) y resumen de hoja (id, revisión, estado, plantilla, PDF final, timestamps). Sin valores técnicos; tombstones sólo contados. Sin vínculo: `linked=false`. |
| GET | `/mobile-execution/equipment/{eq}/field-sheet` | `service_orders.read` + `field_sheets.read` | Detalle de la revisión vigente (`FieldSheetRead`) e historial de revisiones; 409 `LAB_LINK_REQUIRED`, 404 fuera del grupo o tombstone. |
| GET | `/mobile-execution/work-orders/{wo}/pdf` | `service_orders.read` | PDF oficial congelado de la OT (`LabWorkOrder.final_pdf`, `OT-<folio>-r<rev>.pdf`) reutilizando `lab_work_orders.get_pdf`; 404 si la OT no pertenece al grupo vinculado, 409 sin vínculo o antes del cierre. La proyección expone `has_final_pdf`/`final_pdf_generated_at` por OT. |
| GET | `/mobile-execution/field-sheets/{sheet}/pdf` | `service_orders.read` + `field_sheets.read` | PDF final congelado (vigente o histórico) tras validar SHA-256; nunca regenera. |

### Matriz de acciones administrativas LAB (auditoría)

| Acción | Servicio existente | Permiso de dominio | Estados admitidos | Preserva histórico | ERP |
| --- | --- | --- | --- | --- | --- |
| Cancelar OT | `lab_work_orders.cancel_work_order` | `lab_work_orders.cancel` (staff) | Cualquiera sin entrega física vigente; idempotente | Sí (`previous_status`; no toca equipo/hojas/firmas/PDF) | **Expuesta** |
| Restaurar OT | `restore_work_order` | `lab_work_orders.cancel` | `cancelled` con `previous_status` | Sí | **Expuesta** |
| Reabrir OT por ticket | `create_reopen_ticket` / `approve_reopen_ticket` | `tickets.create`; aprobar `work_orders.reopen` + política, sin autoaprobación | `completed`/`partially_closed`, sin entrega vigente | Sí (`LabWorkOrderRevision`, PDF OT archivado) | No (flujo de tickets Mobile) |
| Reapertura directa de OT | `operational_tickets.reopen_work_order_directly` | `work_orders.reopen` + `reopen_preserve/invalidate_signatures` | Cohorte cerrada, sin entrega vigente | Sí | Sólo dentro de "Enviar a corrección" (OT cerrada) |
| Reapertura de FieldSheet por ticket | `create_field_sheet_reopen_ticket` + `resolve_operational_ticket` | `lab_folios.resolve` | OT `received_signed`/`in_progress`/`ready_to_close`, hoja `completed` | Sí (N intacta, N+1 clon) | No (equivalente directo) |
| Reapertura directa de FieldSheet | `lab_field_sheets.reopen_lab_field_sheet_directly` | `lab_folios.resolve` | Igual que el ticket | Sí | Sólo dentro de "Enviar a corrección" (OT abierta) |
| Cambiar workflow mode | `change_lab_work_order_workflow_mode` | `lab_work_orders.cancel` | `draft` sin sesión de firma | Sí (auditoría) | No: decisión de captura previa a la firma (Mobile) |
| Retirar equipo | `void_equipment_entry` | `lab_work_orders.cancel` | OT editable, motivo y `expected_edit_version` | Sí (tombstone) | No: depende de la sesión de edición Mobile |
| Eliminar OT | `delete_work_order` | `lab_work_orders.delete` | Sin entrega vigente; hojas protegidas sólo si cancelada | **No** (DELETE físico) | No: el ERP usa cancelar; la raíz vinculada además está protegida por FK RESTRICT |
| Anular entrega | `void_lab_delivery` | `lab_work_orders.cancel` | Entrega `completed` | Sí (`void_reason`, voucher) | No: entrega LAB es autoridad Mobile |
| Entrega parcial | `create_partial_delivery_ticket` / `execute_partial_delivery` | tickets / `lab_work_orders.use` | Según ticket | Sí | No |
| Descartar revisión editable | `discard_lab_field_sheet` | captura LAB | Hoja editable | Sí (sólo descarta borrador) | No: técnica |
| Cambiar plantilla | `change_lab_field_sheet_template` | captura LAB | Hoja editable | Sí | No: técnica |
| Resolver folios | `resolve_operational_ticket` (`manual_myc_folio`/`linked_folio`) | `lab_folios.resolve` | Ticket `pending` | Sí | No: folio LAB es autoridad Mobile |
| Distribuir folios | `distribute_pending_certificate_folios` | `lab_work_orders.cancel` | MYCA/MYCT `pending` | Sí | No |
| Tickets operativos | router `/mobile/v1/technician/tickets` | `tickets.*` | Por tipo | Sí | No (bandeja Mobile) |

### Acciones ERP expuestas

`backend/app/services/service_order_mobile_administration.py` valida que el objetivo
pertenece al grupo vinculado, exige staff interno y ETS activo/no terminal, traza en el
ETS (`service_order.mobile_correction_requested`, `service_order.mobile_work_order_cancelled`,
`service_order.mobile_work_order_restored`: actor, motivo, `origin=erp`) y delega en el
**mismo** servicio de dominio, que vuelve a verificar su autoridad y hace el commit; si
el dominio rechaza, la sesión se descarta sin trazas huérfanas.

| Método | Ruta | Guard | Dominio |
| --- | --- | --- | --- |
| POST | `/mobile-execution/equipment/{eq}/request-correction` `{reason, signature_policy}` | `service_orders.read` + `work_orders.reopen` | OT abierta → `reopen_lab_field_sheet_directly` (además `lab_folios.resolve`); OT cerrada → `reopen_work_order_directly(equipment_id=…)` (+ política de firmas) |
| POST | `/mobile-execution/work-orders/{wo}/cancel` `{reason}` | `service_orders.read` + `lab_work_orders.cancel` | `cancel_work_order` |
| POST | `/mobile-execution/work-orders/{wo}/restore` | `service_orders.read` + `lab_work_orders.cancel` | `restore_work_order` |

**Enviar a corrección en MYC Mobile** nunca edita la hoja: sólo procede sobre una hoja
`completed`; la revisión N queda intacta (`status`, `final_pdf_path`, `final_pdf_sha256`
y el archivo) y `_clone_field_sheet_for_correction` abre N+1 editable, que Mobile ve como
vigente. `reopen_work_order_directly` recibe el `equipment_id` opcional que su núcleo
`_reopen_closed_cohort` ya soportaba para el ticket; la ruta Mobile no lo envía. Con los
roles actuales: Administrador corrige en OT abierta o cerrada; Calidad y Desarrollador
sólo en OT cerrada (no poseen `lab_folios.resolve`); Técnico, Captura, Comercial y
Finanzas reciben 403. No se crean códigos de permiso ni se modifican roles.

### Captura LAB-backed (PDF-only)

"Captura" en el ERP es un handoff **documental**. `capture_packages.py` conserva un
contrato público con dos estrategias: A. legacy ERP (sin cambios: Equipment/FieldSheet/
Certificate y Master XLSX) y B. LAB-backed (`lab_capture_packages.py`) para ETS Mobile.

Readiness por equipo activo: `certificate_folio` presente y resuelto
(`equipment_certificate_folio_resolved`, la misma regla del cierre LAB), hoja vigente
`completed`, `final_pdf_path` + `final_pdf_sha256`, archivo presente y hash coincidente;
además, cada OT no cancelada del grupo debe estar técnicamente final
(`completed`/`partially_closed`) y conservar su PDF oficial `LabWorkOrder.final_pdf`
(si falta: `LAB_WORK_ORDER_FINAL_PDF_MISSING`, una vez por OT; sus equipos cuentan como
pendientes). Contenido incompleto bloquea aunque la OT esté cerrada.
No se exigen Master, `certificate_master_*` ni plantilla.

- `GET capture-package-summary` → `source="lab"`, `ready`, `ready_total`,
  `pending_total`, `root_folio`, `groups` y `blockers` estructurados:
  `LAB_LINK_REQUIRED`, `LAB_NO_ACTIVE_EQUIPMENT`, `LAB_WORK_ORDER_NOT_FINAL`,
  `LAB_WORK_ORDER_FINAL_PDF_MISSING`,
  `LAB_CERTIFICATE_FOLIO_MISSING`, `LAB_CERTIFICATE_FOLIO_NOT_READY`,
  `LAB_FIELD_SHEET_MISSING`, `LAB_FIELD_SHEET_NOT_COMPLETED`, `LAB_FINAL_PDF_MISSING`,
  `LAB_FINAL_PDF_HASH_MISMATCH`. Sin efectos: no muta el lifecycle del ETS.
- `GET capture-package` → ZIP todo-o-nada nombrado `<folio ETS>.zip`; por OT su PDF
  oficial y sus Hojas de Campo finales: `OT-<folio>/OT-<folio>.pdf`
  (`LabWorkOrder.final_pdf` persistido) y `OT-<folio>/Hoja_Campo_<certificate_folio>.pdf`
  (p. ej. `OT-6438/OT-6438.pdf` y `OT-6438/Hoja_Campo_MYCA-09-26-4721.pdf`), sin carpeta
  ETS ni por folio, nombres sanitizados, nunca regenerados (SHA-256 validado en hojas); 409 `LAB_CAPTURE_PACKAGE_BLOCKED` con bloqueos.
  No incluye XLSX/Master, no crea Certificate, no reserva ni consume folios y no crea
  Equipment ERP.
- Paquete por OT ERP y carga XLSX responden 409 estructurado
  (`LAB_CAPTURE_USES_SERVICE_ORDER_PACKAGE`, `LAB_CAPTURE_INGESTION_NOT_AVAILABLE`).

**Divergencia documentada:** el paquete legacy conserva PDF + Master XLSX porque su
ingestión (identificación por fingerprint de Master, validación de identidad y avance de
Certificate) depende de ese archivo; convertirlo a PDF-only rompería contratos
verificados sin necesidad. Única adecuación legacy: una Verificación sin Master genérico
inicial (catálogo 2026) viaja sólo con su PDF y su Master final se identifica por el
fingerprint registrado ya existente.

`LabWorkOrderEquipment.certificate_folio` es la autoridad del folio: nombra carpeta y
archivo y será la llave del matching XLSX. No se copia a otra tabla ni se reserva un folio
ERP. Fase siguiente (no implementada, sin cerrar su arquitectura): XLSX → folio LAB →
pertenencia ETS/raíz/equipo → identidad/contenido → `Certificate` LAB-backed
(`equipment_id XOR lab_equipment_id`) → Calidad → autenticación.

### Catálogo: Master desconectado

`expected_certificate_master_id` es LEGACY. Calibración y Verificación nuevas se crean sin
Master; editar un concepto histórico con Master inactivo/caducado procede mientras el
cambio no intente asignar otro Master (que sí se valida por compatibilidad API). El ETS ya
no rechaza Verificación sin Master. No se eliminó columna, valor, `ControlledDocument` ni
se migró nada. La ejecución de Verificación permanece en el ERP hasta su propia fase.

### Vínculo y web

`ServiceOrderLabLink` sigue siendo la única autoridad: el vínculo nacido en Mobile
(creación atómica) y el creado después desde el ERP convergen en la misma tabla; los
permisos `create`+`update` se conservan. El Resumen del ETS ofrece "Vincular servicio MYC
Mobile" sin vínculo o "Abrir ejecución técnica" con vínculo: vista grupo → OT → equipo,
detalle de hoja sin inputs, PDF final, cambio/desvinculación con motivo y acciones
administrativas según permisos. La pestaña Captura de un ETS Mobile muestra LISTA/
BLOQUEADA, bloqueos y la descarga PDF; los ETS históricos/mixtos conservan su UI.

### Cierre UX web (2026-09-29)

- Readiness de Captura para ETS Mobile: una sola autoridad visual, el resumen LAB,
  cargado una vez por `useMobileCaptureSummary` en la página y compartido por la
  pestaña Captura (badge), la franja de etapas del Resumen y el panel; `null` →
  VALIDANDO, `ready` → LISTA, en otro caso BLOQUEADA. "Actualizar", correcciones,
  cancelaciones y cambios de vínculo refrescan ese mismo loader. No muta el ETS.
  Los ETS legacy siguen con `getCaptureStageStatus`.
- Layout con clases propias `.ets-lab-*` (antes `.ets-mobile-*`), `minmax(0, …)` y
  container queries por ancho del contenedor; las clases legacy no se modificaron.
- La identidad del equipo ("1. BÁSCULA · Ver detalle") y el estado de la hoja en Captura
  abren el MISMO detalle read-only (`EtsMobileEquipmentDetail`): equipo, cliente
  documental, datos de hoja (fechas, lugar, ubicación, unidades, método, división
  mínima, condiciones ambientales, condición, desviaciones, responsables, notas,
  `capture_values` con labels de plantilla y `results_rows` con columnas de plantilla y
  `row_data` dinámico), revisiones vigente/histórica con PDF final. Sin inputs ni PATCH.
  "Enviar a corrección" aparece en el detalle con `work_orders.reopen` y modo válido y
  abre el diálogo único existente.

### Representación documental ERP-native (2026-09-29)

La OT LAB es un documento de primer nivel en el ERP: cada OT muestra, separados,
"Documentos" (Ver / Imprimir / Descargar OT sobre el PDF oficial congelado, o "OT final
no disponible") y "Administración" (cancelar/restaurar, según permiso). Ver e imprimir
reutilizan el helper autenticado de ventanas PDF del ERP (`quotationPdfWindow.js`), que
abre el PDF oficial en el visor del navegador; nunca se imprime el DOM ni HTML. La
cabecera de OT muestra folio, raíz/miembro, estado, cliente, recepción, salida, equipos,
hojas completadas y PDF finales. Captura lista por OT sus documentos (OT final + Hojas
de Campo) con Ver OT / Ver detalle equipo / Ver hoja. La presentación usa el design
system del ERP (`quotation-section`, `section-heading`, `read-only-grid`,
`glass-card-mini`, `ets-metric-strip`, `quotation-status`, `table-button`,
`toolbar-actions`); las clases `.ets-lab-*` sólo resuelven layout.

### Navegación futura "Servicios" (preparación, no implementada)

Para staff MYC la pantalla principal Mobile evolucionará de "OT" a "Servicios" con
verticales (Calibración, Mantenimiento, Reparación, Verificación, Venta…); los usuarios
operativos externos conservan la vista y flujo actuales. Los contratos nuevos usan
nombres neutrales (`mobile-execution`, `source`) donde representan esa abstracción futura,
sin abstraer el modelo LAB actual. Las demás verticales quedan para fases posteriores.
