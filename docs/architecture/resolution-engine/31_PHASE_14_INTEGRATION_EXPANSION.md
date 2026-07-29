# Fase 14 — Expansión institucional de integraciones

> Estado: `EN REVISIÓN`
>
> Tipo: contrato técnico vigente
>
> Definición: `service_order.resolve_additional_equipment@1.0`
>
> Apertura: Fase 13 aprobada en
> `bb76e3bba9482517c9dfb870567d6bdfc7b9b135`

## Objetivo y límites

La Fase 14 instala el segundo vertical completo del Motor y demuestra que
Centro, API pública y worker consumen una composición institucional común. No
modifica Domain Model, Lifecycle, políticas, seguridad, auditoría,
compensación, contratos públicos v1 ni SDK. No incorpora IA.

El caso resuelve equipo adicional detectado en un ETS. Una propuesta todavía
no autorizada puede provenir de ERP, móvil u operación fuera de línea y queda
identificada por `reconciliation_id`. Antes de la ejecución no existe equipo
definitivo, OT nueva, certificado esperado ni efecto facturable.

## Composición instalada

`backend/app/resolution_integrations/installed.py` es la única fuente de
integraciones activas. Cada entrada aporta:

- definición canónica y resolver de componentes;
- handlers de acción y compensación;
- presentación y esquema cerrado para el Centro;
- fábrica de solicitud, snapshot e hidratador.

`ResolutionCenterDefinitionRegistry`, el worker y
`ResolutionPublicApi.capabilities/create` consumen esa colección. No existen
imports mágicos, discovery por filesystem ni ramas JavaScript por dominio.

## Solicitud y hechos

La solicitud conserva:

- ETS e identificador estable de conciliación;
- catálogo, nombre, clasificación y cantidad;
- marca, modelo, serie, identificación interna y alcance;
- origen, fecha, notas y OT preferida opcional.

El provider read-only obtiene:

- existencia, actividad, estado y versión observable del ETS;
- cliente, técnico y cotización;
- firmas confirmadas y etapa tardía;
- OTs activas, estado, límite y cupo;
- catálogo activo y coincidencia de `calibration_scope`;
- partida operativa compatible;
- duplicados por serie/identificación o conciliación;
- estados de facturas que exigen revisión comercial.

Las únicas clasificaciones admitidas son las canónicas:
`accredited_iso_17025`, `traceable` y `accredited_linked_lab`.

## Resultados deterministas

| Condición | Estado / razón |
| --- | --- |
| ETS activo y datos válidos | `resolvable` + `requires_authorization` |
| Firma ya confirmada | `requires_signature` |
| Partida ausente o factura activa | `requires_commercial_adjustment` |
| Etapa avanzada | `late_stage_warning` + `requires_manual_review` |
| Conciliación ya aplicada | `already_resolved` |
| Serie o identificación repetida | `duplicate_equipment` + `already_registered` |
| ETS cerrado, cancelado o inactivo | `blocked_service_state` |
| Catálogo ausente/inactivo | `missing_catalog` |
| Clasificación incompatible | `invalid_classification` |

Las estrategias son `attach_existing_work_order`,
`create_new_work_order`, `pending_signature`,
`pending_commercial_adjustment` y `no_action`. El plan genera una acción por
unidad, con claves de conciliación derivadas de forma estable cuando
`quantity > 1`.

## Simulación, autorización y revalidación

La simulación sólo declara impactos: ETS, equipo, clasificación, OT y posición
previstas, referencia provisional de certificado, ausencia de Hoja de Campo,
captura, calidad, firma, revisión comercial/facturación y límites de
reversibilidad. No escribe dominio ni genera folios reales.

La autorización exige permisos granulares de equipo adicional. Si hay impacto
comercial agrega `service_orders.additional_equipment.commercial_review`.
El workflow traduce el permiso vertical de la etapa a la operación canónica
del Motor: Comercial/Operador pueden proponer, Calidad autoriza y
Técnico/Operador ejecutan, sin compartir facultades ni depender del comodín de
Administrador.
Antes de ejecutar se vuelve a construir el contexto; cualquier cambio en
estado, capacidad, duplicados, catálogo, firmas, facturas o versión observable
produce `requires_new_plan`.

## Ejecución propietaria

`register_additional_equipment` opera dentro de la transacción abierta por el
adaptador:

1. recupera un replay exacto por conciliación o bloquea una clave reutilizada;
2. bloquea el ETS y revalida estado, catálogo, clasificación, partida y
   duplicados;
3. bloquea las OTs y selecciona la primera con cupo, respetando la preferida;
4. crea una OT sólo si ninguna admite otro equipo, siempre con límite 10 y
   lock transaccional PostgreSQL para la numeración global;
5. crea `Equipment`, liga `resolution_id` y congela el contexto documental;
6. crea la reserva `Certificate.status = expected`, serializando la numeración
   global de folio en PostgreSQL;
7. actualiza conteos, marca seguimiento de firma y escribe auditoría.

No llama `commit()`. El `request_hash` y el índice único de
`resolution_reconciliation_id` protegen reintento, recuperación después de
fallo y concurrencia entre procesos. El lock del Executor conserva exclusión
por resolución y el lock del ETS protege dos resoluciones distintas sobre el
mismo agregado.

## Compensación

La compensación es deliberadamente limitada:

- cancela únicamente equipo todavía `registered`;
- cancela sólo certificados `expected` sin consumo;
- desactiva una OT creada por la misma conciliación si queda vacía;
- retira el indicador de reapertura de firma sólo si pertenece a este flujo.

Bloquea y preserva Hojas de Campo, equipo ya procesado, certificados en otro
estado, firmas históricas, documentos autorizados, folios consumidos, CFDI y
eventos append-only.

## Persistencia

La migración `7b8c9d0e1f2a` añade a `equipment`:

- `resolution_id BIGINT`, FK restrictiva a `resolutions`;
- `resolution_reconciliation_id VARCHAR(160)`, único;
- `resolution_request_hash VARCHAR(64)`.

El downgrade elimina índice, FK y columnas en orden inverso. Fue validado en
PostgreSQL mediante `upgrade head → downgrade 6ae1d4877cdb → upgrade head`.

## Productor

`request_additional_equipment_resolution` es el productor canónico para ETS,
Equipos o sincronización. Requiere el permiso `propose`, es idempotente,
utiliza Lifecycle a través del workflow vigente y sólo crea/recupera la
propuesta. Nunca analiza, autoriza ni ejecuta.

## Excepciones tradicionales

`backend/app/services/service_orders.py::register_service_order_exception`
continúa como flujo legacy para cambios de etapa y resincronización de
facturas no emitidas. No fue ampliado ni llamado por este vertical. Su futura
migración debe hacerse caso por caso; no puede convertirse en un bypass
genérico ni absorber cancelación/sustitución fiscal.

## Inventario priorizado de integraciones futuras

| Prioridad | Dominio / problema | Riesgo y efectos | Autorización | Compensabilidad | Dependencias | Fase sugerida |
| --- | --- | --- | --- | --- | --- | --- |
| P0 | ETS / pausar servicio | Trabajo activo inconsistente; pausa agenda, equipo y captura | Operación + responsable técnico | Sí, antes de efectos documentales | Estados ETS y locks | 15 |
| P0 | ETS / reabrir firma | Nueva OT/equipo después de firmas | Preservar ciclos firmados; abre ciclo nuevo | Calidad + operación | Sí, sólo ciclo pendiente | Ciclos de firma | 15 |
| P0 | ETS / firma adicional y OT nueva | OT sin cobertura de firma | Firma y asignación explícitas | Calidad + cliente/técnico | Parcial | Vertical Fase 14 | 15 |
| P0 | ETS / etapa excepcional | Saltos de estado hoy genéricos | Facturación/captura/calidad | Segregada por destino | Según efectos | Descomponer excepción legacy | 15 |
| P1 | Equipos / retirar equipo | Puede tener Hoja, certificado o factura | Operación + calidad/comercial | Sólo antes de consumo | Evidencia por equipo | 16 |
| P1 | Sincronización / propuesta offline | Duplicado o orden causal incierto | Identidad de dispositivo + operador | Sí antes de ejecución | Idempotencia offline | 16 |
| P1 | Cotización / diferencia de ejecución | Cantidad/servicio real difiere | Impacto comercial y fiscal | Comercial + operación | Parcial antes de CFDI | Agregado Invoice/Quotation | 16 |
| P1 | Facturación / incidente de emisión | Reintento puede duplicar CFDI | Evidencia PAC y estado incierto | Finanzas | No si timbrado confirmado | Intentos Facturama | 17 |
| P1 | Pagos / pago previo a timbrado | Aplicación a documento inexistente | Integridad financiera | Finanzas | Sí antes de aplicación | Pagos + Invoice | 17 |
| P1 | CFDI / timbrado incierto | Timeout con posible efecto externo | Nunca reintento ciego | Finanzas + conciliación PAC | No automática | Consulta por UUID/idempotencia | 17 |
| P1 | CFDI / nota de crédito | Efecto fiscal irreversible por autorización | SAT, saldos y XML/PDF | Finanzas segregada | Flujo fiscal propio | CreditNote canónica | 17 |
| P2 | Certificados / corrección posterior | No reescribir documento autorizado | Calidad + evidencia de versión | Sustitución, no borrado | Versiones y autenticación | 18 |
| P2 | Captura / divergencia Hoja–Master | Datos incompatibles con plantilla | Calidad/metrología | Rehacer snapshot controlado | Registry de campos/Masters | 18 |
| P2 | Documentos / fallo de autenticación o LibreOffice | Resultado incierto de generación | Calidad/soporte | Reintento sólo sin artefacto | Storage y versiones PDF | 18 |

## Gate

La fase queda `EN REVISIÓN`. No abre Fase 15. La IA continúa fuera de alcance
y sin fase autorizada.
