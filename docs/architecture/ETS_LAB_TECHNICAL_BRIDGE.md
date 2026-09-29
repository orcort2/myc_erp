> Estado: VIGENTE — Fase 1 implementada, en revisión
>
> Corte: 2026-09-28
>
> Autoridad: contrato acotado del vínculo histórico ERP ETS ↔ LAB

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
