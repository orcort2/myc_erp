> Estado: VIGENTE
>
> Tipo: Vigente (canónico)
>
> Autoridad: Alta
>
> Prevalece sobre: `archive/process/flujo-general.md` y secuencias operativas de las especificaciones V2/V3
>
> Corte verificado: 2026-09-02

# Flujo operativo actual

## Mantenimiento

`cotización aprobada/snapshot → ServiceUnit + ServiceStage maintenance + OT → arribo/equipo (laboratorio) o equipo + solicitud/aceptación/programación (campo) → asignado → en mantenimiento ↔ pausado → captura estructurada → técnicamente terminado → reporte versionado → firma vigente → liberación/cierre`.

Un preventivo que descubre correctivo se pausa y solicita decisión comercial; aprobación vinculada u override auditado habilitan el alcance, mientras el rechazo conserva anomalías/recomendaciones y permite terminar el preventivo. Reparación se documenta y vincula a otro ETS. Equipo inoperable abre bloqueo e investigación administrativa.

Este documento describe el flujo que existe en el sistema, no el flujo ideal ni el diseño futuro.

## Motor de Resoluciones

El flujo interno implementado incorpora un único dominio real: Certificados.
El primer vertical de Fase 9 está implementado y aprobado:

```text
[decisión resolution.create exacta] → draft
→ [decisiones de transición y capacidad exactas]
→ contexto → análisis → plan → simulación declarativa
→ autorización exacta → revalidación → ready_for_execution
→ verificación pre-replay y transaccional → reserva idempotente + lock
→ executing
→ checkpoints y acciones por ActionRunner
→ completed | partially_completed | failed | blocked
[si existe plan compensatorio autorizado y elegible]
→ compensating
→ compensated | partially_compensated | compensation_failed
[consulta de auditoría autorizada]
→ reconstrucción → verificación → timeline/reporte
```

El catálogo integral deniega acciones, recursos o permisos no registrados.
Crear exige una intención canónica y `request_key`; un replay exacto recupera
la misma resolución. Transitar Lifecycle exige operación, estado y versión
esperados. Cada mutación consume su decisión append-only dentro de la
transacción: un rollback libera el intento y otra intención queda denegada.
Sólo la máquina de estados calcula el estado. Un plan no autorizado o no revalidado no inicia.
Cada acción se identifica por
ejecución y paso, persiste su intención antes de invocar el adaptador y conserva
resultado/efectos después. Al regresar del handler, el token/TTL se valida y el
checkpoint lo vuelve a validar atómicamente. La decisión de ejecución se
comprueba antes de consultar un replay y dentro de la reserva transaccional.
Una pérdida de lock o resultado
incierto termina en `blocked` sin repetición automática. El outbox se publica
sólo mediante una invocación explícita autorizada, aislada por organización;
congela un lote exacto por operación y conserva la fecha de fallo.

La compensación es un flujo independiente y síncrono. Sólo parte de una
ejecución terminada elegible, usa una decisión `resolution.compensate` para la
ejecución y actor exactos, persiste un plan inmutable y ejecuta en orden inverso
únicamente acciones declaradas reversibles. Una selección parcial se rechaza
antes de persistir si deja activo cualquier dependiente confirmado directo o
transitivo; un efecto no confirmado o ya compensado no bloquea. Punto de no
retorno, duplicado, actor distinto, fallo o pérdida de lock se rechazan o
quedan trazados sin reinvocación. No existe compensación automática.

La auditoría es un flujo read-only separado. Exige una decisión
`resolution.audit.inspect` concedida para la resolución, actor, autenticación,
correlación, contexto, recurso, organización e identidad de consulta exactos.
La concesión `reusable_read` puede repetir esa misma consulta mientras siga
vigente, sin registrar un consumo mutante. Después abre un snapshot consistente, carga el
expediente completo y proyecta su evidencia antes de cerrar la transacción, sin
exponer ORM. Verifica hashes, referencias, pertenencia y secuencia, y genera una
línea de tiempo y un hash deterministas del corte. Una confirmación concurrente
queda enteramente antes o después del reporte, nunca mezclada. Los filtros se
aplican sólo después de verificar el conjunto completo. La consulta no transita
Lifecycle, no ejecuta handlers y no publica outbox.

Fase 9 está aprobada. Fase 10 implementa el flujo público v1:
consumidor autenticado y ligado a organización → contrato estricto →
ActorContext → autorización integral → `ResolutionLifecycleService` para alta
o `AuditQueryService` para consulta → DTO público. La clave de alta se
namespacia por versión/consumidor/organización; un replay exacto recupera el
mismo expediente ya autorizado y una colisión se rechaza. Listado y detalle
exigen `resolution.audit.inspect`, aplican aislamiento organizacional y no
transitan Lifecycle ni ejecutan handlers. El SDK usa exclusivamente HTTP.
El cursor `c1` cifra la posición y vincula contrato, consumidor, organización,
filtros, orden, dirección y tamaño de página; una solicitud divergente se
rechaza antes de continuar el keyset. Fase 10 está aprobada en `dd9a84e`.

Fase 11 agrega un flujo interno asíncrono sin cambiar esa API:
dispatcher → trabajo durable → claim `SKIP LOCKED` → lease cercado → handler
canónico → resultado/evento. Los nodos hacen pull según capacidad y no pueden
reclamar dos trabajos de la misma resolución en paralelo. Heartbeats renuevan
nodo y trabajo durante la operación. Recovery reencola sólo si el posible
efecto no comenzó; si comenzó, deja `blocked` por incertidumbre. Un retry
automático requiere ausencia de efecto declarada y usa backoff exponencial
acotado sin jitter. La Fase 11 está aprobada en `cbde517`.

Fase 12 expone el flujo operativo interno:

```text
/resolutions → catálogo registrado → alta por Lifecycle
→ contexto → análisis → plan → simulación → autorización → revalidación
→ HTTP 202 / enqueue durable → worker independiente → Executor canónico
→ polling visible de expediente, eventos, intentos, evidencias y resultado
```

La decisión de ejecución se confirma antes de publicar el trabajo. El snapshot
durable del actor no contiene el token HTTP y su concesión por operación no
caduca con la sesión web. Un `work_key` único por resolución evita dos
despachos. La lista y el expediente son proyecciones read-only aisladas por
organización/actor; hashes, nodo y lease requieren permisos técnicos. Fase 12
quedó `APROBADA` mediante `a7bf75f`.

Fase 13 conserva ese flujo y elimina los últimos contratos específicos de
presentación:

```text
registro institucional versionado → formulario derivado del esquema
→ servicios canónicos → cola durable → worker → resultado persistido
→ indicadores/timeline/expediente proyectados por backend
```

Certificados recorre el ciclo completo incluso después de cerrar la sesión.
La decisión de ejecución incluye el estado exacto esperado por Seguridad; el
worker no omite ni reevalúa de forma paralela Lifecycle o políticas. Fase 13
fue aprobada en `bb76e3b`.

Fase 14 agrega un segundo vertical sin cambiar el flujo:

```text
ETS/móvil/Centro → propuesta con reconciliation_id
→ contexto read-only del ETS, catálogo, OT, firmas y facturación
→ análisis y estrategia deterministas → simulación sin folio ni equipo
→ autorización → revalidación de hechos críticos → cola durable
→ worker/Executor → lock de ETS → reutilizar OT o crear OT límite 10
→ equipo + reserva expected + auditoría → resultado reconstruible
```

Un replay exacto recupera el equipo por conciliación. La compensación sólo
cancela equipo `registered`, reserva `expected` y OT propia vacía. La fase
queda `EN REVISIÓN`.

Fase 15 incorpora operaciones extraordinarias ETS sin crear otro flujo:

```text
Herramientas administrativas → seleccionar restaurar / reconstruir / baja
→ contexto y precheck read-only → análisis → plan → simulación
→ autorización separada → revalidación exacta → cola durable → worker
→ servicio propietario ETS bajo transacción → referencias/auditoría/Actividad
```

Restaurar conserva el mismo ETS. Reconstruir usa una cotización aceptada sólo
si no existe ningún ETS previo. Dar de baja sólo retira un ETS prístino sin
cancelar ni reescribir sus OT. La creación ordinaria y el endpoint DELETE no
pueden sustituir este proceso.

Para `certificate.resolve_incorrect_release`, el provider obtiene un snapshot
read-only; análisis, estrategia, plan y simulación son deterministas; el
gateway ejecuta el servicio canónico que bloquea el registro y cambia sólo
`client_visible` de verdadero a falso. El servicio conserva una operación
append-only en la misma transacción. Si se autoriza compensación y no existe
deriva, otro gateway restaura la visibilidad anterior y agrega evidencia
enlazada. Un replay exacto consulta primero la operación histórica y no depende
del certificado actual. Una clave nueva vuelve a comprobarse después del lock;
el snapshot de salida se crea sólo después de `flush/refresh`. Ningún adaptador
modifica Lifecycle ni contiene reglas propietarias.

## Flujo principal

```text
Autenticación
  → Cliente y datos fiscales
  → Cotización y partidas
  → Snapshot operativo congelado por partida/componente
  → Expansión de Servicios Compuestos en partidas operativas del ETS
  → ETS/Servicio vinculado a cliente y opcionalmente a cotización
  → Órdenes de Trabajo (máximo 10 equipos por OT)
  → Equipos y snapshot de Plantilla Maestra/contexto operativo
  → Hoja de Campo por equipo
  → Captura y preparación documental
  → Calidad: revisión y aprobación del Master XLSX
  → Autenticación: generación y sellado del PDF final
  → Certificados autenticados
  → Facturación/pago cuando aplica
  → Liberación del certificado
  → Cierre del ETS
```

## Actividad transversal

En cualquier ficha integrada, el usuario autorizado consulta el hilo por
entidad, publica un comentario, menciona o adjunta evidencia y puede solicitar
atención a una persona/área. La lectura se confirma explícitamente. Los
servicios canónicos publican eventos formales idempotentes dentro de su misma
transacción; Actividad no cambia el estado del dominio. Dashboard consolida no
leídos y atenciones, mientras Notifications conserva el aviso dirigido.

## 1. Acceso

El namespace `/api/mobile/v1/technician` reutiliza el access JWT interno, pero
aplica `service_orders.read_assigned` y ownership en cada consulta. ETS filtra
por técnico; OT y Equipo heredan por `service_order_id`; Hoja de Campo hereda
por `equipment_id → service_order_id` y exige además `field_sheets.read`.
Recursos ajenos, inactivos o sin asignación responden 404. Este flujo no cambia
las rutas internas consumidas por el ERP web.

El usuario inicia sesión y recibe access/refresh JWT con tipos explícitos. Sólo
access autentica solicitudes y refresh se utiliza únicamente para renovar el
par. El registro público no acepta roles solicitados y sólo crea el primer
Administrador cuando no existe ningún usuario. La navegación autenticada carga
los permisos efectivos calculados por backend y oculta módulos/acciones sin
capacidad.

## Gobierno previo de nuevas capacidades

Antes de iniciar una funcionalidad nueva se registra su módulo, acción y
microacción en el Catálogo Institucional. La revisión funcional aprueba o
rechaza la clave propuesta; sólo una clave aprobada puede incorporarse al
bootstrap, roles y usuarios. Este flujo de gobierno no reemplaza las reglas de
estado, ownership ni negocio del módulo.

Antes de entrar a cualquier router interno, el guard transversal clasifica la
operación y exige access JWT, permiso u ownership conforme a su categoría. Las
únicas excepciones anónimas están en una allowlist canónica; la API pública del
Motor conserva su consumidor/organización independiente. Una ruta nueva sin
clasificación impide el arranque y falla la prueba de conformidad.

En el portal, el cliente no elige tenant: el backend exige un JWT de contexto
`client_portal`, permiso base institucional `portal.read` y una membresía activa
única. Los permisos persistidos legacy `portal.view` se normalizan a
`portal.read` al resolver la sesión; el
`client_id` se deriva exclusivamente de `ClientPortalMembership`; listados y
descargas se filtran por ese cliente, un certificado ajeno responde 404 y un
acceso válido queda auditado.

## 2. Cliente y Cotización

El cliente conserva identidad, datos fiscales, contactos dependientes, constancia y perfiles de certificado. La cotización se crea con partidas propias o provenientes del Catálogo MYC, calcula importes, guarda snapshots y puede transitar entre `draft`, `sent`, `waiting` y estados terminales.

La transición institucional a `accepted` materializa automáticamente el ETS en
la misma transacción backend. El backend bloquea la Cotización, reutiliza el
ETS activo si ya existe y construye todas las partidas desde snapshots; un
retry no duplica el expediente. El asesor ya no ejecuta una segunda acción
manual. Agenda continúa siendo una fecha dentro del ETS, no un agregado creado
por esta transición.

Un Servicio Compuesto aparece una sola vez en la cotización y en sus documentos comerciales. Al crear el ETS, el backend recorre su composición normalizada, multiplica las cantidades y genera partidas operativas únicamente para los servicios simples hoja. Esas partidas alimentan sin lógica paralela el conteo de OT, Equipos, Hojas de Campo y Certificados. Servicios simples, conceptos libres y cotizaciones existentes conservan el comportamiento anterior.

En calibración, la partida del catálogo conserva una de tres modalidades canónicas: acreditación propia, trazable/no acreditada o acreditación por laboratorio vinculado. La clave se propaga a la partida cotizada y al ETS. Al registrar equipos, la capacidad configurada resuelve el alcance automáticamente cuando sólo hay una alternativa; si hay varias con cupo, se solicita desambiguar entre ellas. No se deriva la modalidad desde una leyenda o número impreso en el Master.

Al crear el ETS, cada `ServiceOrderItem` congela el identificador del Master esperado mediante el ID estable del concepto operativo. Al registrar el equipo, Equipos lee exclusivamente esa partida y congela alcance, tipo de certificado, Master esperado, partida y origen de catálogo junto con la versión/archivo del Master. Cambiar después el nombre o la selección del catálogo no modifica el expediente; no existe resolución por `service_name`.

Verificación exige Master genérico válido al crear o actualizar el concepto.
Un concepto histórico con nulo permanece consultable, pero la aceptación se
rechaza antes de crear el ETS para impedir una Captura imposible; debe
corregirse el concepto y sustituirse explícitamente la partida para producir un
snapshot nuevo.

Una cotización aprobada con ETS completamente virgen admite:

`Solicitar desbloqueo → autorizar → editar partidas en la ficha → revisar delta
→ confirmar → crear revisión → eliminar ETS virgen → recrear con el mismo
OSMYC → cerrar EXV`.

Cuando el actor posee autoridad explícita de autoautorización —Administrador
mediante `*`— el primer tramo se compacta a
`Desbloquear cotización → editar partidas`: un solo clic, sin modal, motivo ni
observación capturados al usuario. El sistema aporta un motivo estándar; la
solicitud y autorización siguen registrándose como dos evidencias
institucionales dentro del mismo expediente.

Las excepciones operativas del ETS usan siempre tres acciones persistentes:
`solicitar → autorizar → ejecutar`. La solicitud conserva etapa origen/destino,
motivo, actor y estado ETS de referencia, pero no cambia el ETS ni toca
facturas. La autorización agrega decisión, actor y fecha sin efectos
operativos. Sólo la ejecución de un expediente `authorized`, después de
comprobar que el estado ETS no cambió desde la solicitud, aplica la etapa
destino y resincroniza exclusivamente facturas derivadas elegibles. La UI ETS
crea solicitudes incluso para Administrador; autorización y ejecución son
endpoints separados. El mismo Administrador puede ejecutar sucesivamente las
tres acciones, pero el backend no compacta estados: conserva actor, timestamp,
audit log y evento independientes en cada paso.

El ETS se vuelve a construir desde la revisión nueva. Si aparecen equipos,
certificados, archivos, factura, firmas, resolución, OT ejecutada o un estado
operativo, la confirmación se bloquea y no se aplica ninguna mutación.

## 3. Agenda y Llamado dentro de ETS

Agenda y Llamado no son módulos autónomos actuales. La fecha de agenda vive en el ETS y el llamado es el hito `confirmed → called`. No existe actualmente el circuito histórico con folios `AMYC`/`SMYC`, calendario, bitácora y estados independientes.

## 4. ETS, OT, equipos y firmas

### Núcleo múltiple/evolucionado Fase 1

`Cotización inicial decidida por partida → ETS → ServiceUnit(s) →
ServiceStage(s) autorizadas`, conservando el mismo `ServiceOrder` y la misma
`ServiceWorkOrder` durante la intervención. Una unidad aparece una sola vez en
backend aunque la UI futura la proyecte en varios tabs por categoría.

Cada unidad se liga a su partida operativa origen. Sólo la unidad nacida de
Servicio General inicia como `ServiceUnit(evolution_enabled) → diagnóstico`;
calibración, mantenimiento u otras partidas del mismo ETS conservan su flujo
normal.

En el alta/edición del catálogo, Tipo comercial/fiscal y Categoría operacional
se seleccionan de forma independiente. La clave `operational_category` viaja
explícita en el payload; seleccionar Venta muestra su configuración vigente
sin comprobar Producto/Servicio.

La ruta ETS se decide por `operational_category` congelado en
cotización/partida. Reabrir o editar con el mismo concepto no consulta el
catálogo vigente; una sustitución explícita sí construye un snapshot nuevo. La
propuesta de Hoja de Campo continúa en el resolver frontend vigente y no
pertenece a este flujo.

Después, cualquier etapa de esa misma unidad evolutiva puede originar:

`Etapa origen → TechnicalServiceRequest → una o varias QuotationItem →
QuotationItemDecision por partida → cero, una o varias ServiceStage nuevas`.

La solicitud comercial queda `requested` sin cambiar el estado técnico de la
etapa; una pausa real usa el lifecycle formal. Una aprobación interna exige
`quotations.update`, deriva actor y `source=internal`, y crea únicamente las
categorías que coinciden con solicitud y catálogo/snapshot; un rechazo no crea
etapa ejecutable. Decisiones mixtas conservan `partially_approved`. La nueva
etapa referencia a la anterior y no la convierte ni elimina. La ausencia
física de marca/modelo/serie produce identificación parcial documentada sin
bloquear el alta.

Activity conserva threads directos para ETS, unidad y etapa. Un mensaje con
`#tarea` materializa una tarea independiente, enlazada al mensaje y sus
menciones mediante clave única. El snapshot comercial derivado incluye sólo
marca, modelo y serie; la evidencia técnica permanece en ETS.

El ETS usa la máquina de estados:

```text
scheduled → confirmed → called/in_progress → technical_review
→ capture → quality_review → pending_payment/released → closed
```

`cancelled` es terminal y existen rutas alternativas permitidas por la máquina vigente. Al crear el expediente se generan Órdenes de Trabajo según los cupos; cada OT admite como máximo 10 equipos. Los ciclos de firma vinculan las OT activas pendientes del momento; una OT agregada después requiere un ciclo nuevo.

Un Administrador puede eliminar definitivamente una OT productiva desde el
modal de Órdenes de Trabajo sin importar su estado. El backend bloquea la OT y
su ETS, calcula el grafo real y ejecuta una sola transacción: elimina equipos,
hojas, certificados, unidades/etapas/tareas y vínculos exclusivos; desacopla
referencias anulables de factura/cotización; elimina un ciclo de firma sólo si
ya no tiene otra OT; conserva los recursos compartidos y el evento mínimo de
auditoría. Los archivos exclusivos pasan primero a staging reversible, se
restauran ante rollback y se destruyen después del commit. Una evidencia
inmutable del Motor de Resoluciones bloquea con `409` antes de mutar.

MYC Mobile no lista, abre, descarga ni elimina estas OT productivas. Su pantalla
temporal de Órdenes de Trabajo consume exclusivamente el agregado LAB.

El router ETS conserva sólo transporte HTTP, identidad, permisos, validación y
respuesta. `backend/app/services/service_orders.py` es la única autoridad para
crear, actualizar, transitar, cerrar, solicitar/autorizar/ejecutar excepciones y
desactivar ETS; todas las mutaciones HTTP propagan el actor autenticado.

## 5. Hojas de Campo y Captura

La definición congelada puede describir headers multinivel, grupos de columnas,
spans, labels fijos de fila, anchos/alineación y múltiples secciones. Backend
normaliza y valida la matriz antes de persistir; Mobile interpreta el mismo
contrato con scroll horizontal. Para PDF, Python resuelve `print_layout`, bloques
y perfil organizacional MYC/CAPYMET y entrega un contexto limpio al único
renderer Jinja. Definiciones históricas sin el DSL conservan header plano y
defaults Letter portrait.

Cada equipo puede tener una Hoja de Campo activa con snapshot de plantilla e identidad institucional. Se capturan resultados y firmas, se completa la hoja y se prepara el paquete de Captura por ETS u OT. El paquete depende de una Plantilla Maestra XLSX activa, vigente, existente y cuyo hash coincida con el snapshot del equipo.

Toda hoja nueva fija `field_sheet_engine` versión 1. Mientras está en borrador
o captura, su PDF puede ser preview dinámico; al completar, el backend genera y
publica una vez el PDF final, persiste SHA-256, renderer/versión, versión de
plantilla y fecha, y las descargas posteriores devuelven ese mismo artefacto
verificado. Snapshots históricos que señalan los tres HTML legacy conservan su
renderer y no son reescritos.

Para el Paquete de Captura, `completed`, `under_review` y `approved` representan hojas técnicamente terminadas. La transición `complete` valida condición inicial/final, campos requeridos por plantilla, observaciones o evidencia y resultados estructurados; `Revisó` y `Elaboró informe` pertenecen a etapas posteriores y no bloquean el paquete. El flujo general de Hojas de Campo sigue sin cerrar por semánticas, automatizaciones metrológicas y acciones propias de aprobación/rechazo.

Al devolver el ZIP/Master, cada Excel útil se identifica y persiste con sus validaciones. Si Verificación sólo conserva el Master genérico inicial, el backend resuelve una coincidencia institucional única y congela documento/versión final. Si ese final ya existe, no vuelve a resolver contra el registro vigente: valida exclusivamente contra la ruta y versión congeladas, aunque aparezcan otros Masters o revisiones. El nombre entregado es una ayuda, no una obligación. El primer Master identificado inicia `capture_in_progress` con actor y auditoría; metadatos `._*`, `.DS_Store` y `__MACOSX/` se ignoran. La interfaz muestra el resumen devuelto y vuelve a consultar ETS, certificados y registros de Captura sin exigir recarga manual. `match_status` se conserva como dato legacy y no gobierna la autenticación.

Captura no carga el PDF final. Para cada certificado, `identified` con advertencias `no_encontrado` permite enviar; ausencia de Master identificado o resultados `mismatch`/`no_coincide` bloquean. El envío persiste `capture_in_progress → quality_review` con actor, fecha y referencia al XLSX. Calidad descarga el Master, revisa advertencias/diferencias y puede aprobarlo o regresarlo a Captura.

## 6. Calidad y Certificados

Calibración y Verificación comparten
`OT → Equipo → Hoja de Campo → Captura → Calidad → Certificado → Autenticación → versión PDF/sello/QR → Liberación`.
La partida congelada gobierna cada equipo: Calibración resuelve su
`calibration_scope`; Verificación exige alcance nulo, reserva
`MYCV-MM-AA-XXXX` con consecutivo anual desde `0001` y titula el documento
`Certificado de Verificación`. Su partida puede congelar un Master genérico
inicial. Captura descarga el bonche con Hojas de Campo terminadas y esa
referencia, sustituye fuera del ERP el archivo por el Master técnico real y
reingresa el mismo ZIP. El backend asocia certificado/equipo por identidad
fuerte, reconoce de forma única el Master registrado de Verificación por
fingerprint y congela automáticamente documento/versión final antes de Calidad;
el snapshot JSON conserva ambas identidades, versiones, actor, origen e
historial sin tabla paralela. Las
acciones se filtran por equipo/partida aun cuando ambos procesos conviven en un
ETS. No se calcula automáticamente Cumple/No cumple y Ajuste no forma parte del
flujo vigente.

El flujo normalizado de certificado es:

```text
expected/field_sheet_ready/capture_pending
→ capture_in_progress
→ quality_review (revisión del Master XLSX)
→ quality_approved
→ autenticación genera y sella el PDF final desde el Master aprobado
→ authenticated
→ released_to_client
```

La habilitación de Autenticar depende exclusivamente de `quality_approved` o del alias legacy `approved`. No requiere PDF previo, `final_pdf_path`, carga manual, PDF validado ni `match_status`. Calidad es la única superficie funcional: el endpoint de Certificados delega en `certificate_authentication.authenticate_certificate`, que exige actor y origen, bloquea la fila, revalida, convierte el Master identificado más reciente y persiste versión, audit y evento antes de confirmar. ETS sólo proyecta estado/descargas/liberación y no expone autenticación individual o masiva. El XLSX original no se modifica.

El modal de Calidad conserva la lista visible con la que se abrió y permite navegación secuencial no circular. Cuando la tarjeta pertenece a una agrupación OT, ésa es la frontera prioritaria; si no existe una OT resoluble, se usa el ETS y, en último término, la lista filtrada visible. Cada cambio vuelve a consultar certificado e historial, oculta el contenido anterior durante la carga y recalcula readiness y acciones. Aprobar, regresar a Captura o autenticar mantiene el modal y su posición contextual abiertos mientras refresca el registro activo, la lista y los contadores.

La vista de Certificados muestra únicamente documentos con PDF autenticado y estados autenticado/liberado. `authenticated` con archivo autenticado existente deriva “Listo para liberar”; no es una liberación automática. Si el ETS requiere pago y no está cubierto, el mismo certificado se muestra documentalmente autenticado pero “Pendiente de pago”. Con compuerta financiera cumplida, Liberar persiste actor/fecha/auditoría y transita a `released_to_client`. `match_status` se conserva sólo para trazabilidad legacy y no participa en disponibilidad, agregados, habilitación ni endpoint de liberación.

## 7. Facturación y pago

La Mesa de trabajo puede originar borradores desde ETS/cotización, congelar snapshots fiscales y emitir en Facturama Sandbox. El sistema conserva intentos, identificadores, XML/PDF del PAC y genera PDF institucional MYC. Desde el Resumen financiero de la factura, un usuario con `payments.manage` registra pagos parciales o totales antes o después del timbrado; backend recalcula `amount_paid`, `balance_due`, `last_payment_on` y el estado financiero. El historial permanece dentro de la factura y abre el comprobante PDF existente.

El Workbench conserva este mismo flujo mediante un controlador frontend único. Puede abrirse con contexto explícito `invoice_id` o `service_order_id`; el contexto ETS consulta el listado existente filtrado y ya no se transporta por `localStorage`. La pestaña Facturación del ETS muestra el `Invoice` asociado, abre el mismo `InvoiceWorkbenchDialog`, registra el pago sin cerrar el expediente y refresca el resumen y el readiness de liberación del ETS. El Dashboard existente consume Cuentas por cobrar y abre la factura correspondiente; al quedar saldo cero, la factura sale de cartera. No existe pestaña independiente de Pagos. Notas de crédito e historial documental especializado permanecen fuera de esta entrega.

Un pago previo no bloquea el timbrado: `partially_paid` y `paid` sin UUID continúan siendo emitibles. Al confirmar el PAC, la emisión conserva pagos y saldo y deriva `issued`, `partially_paid` o `paid` según los importes persistidos. Con `requires_payment=true`, saldo cero y factura pagada satisfacen la compuerta financiera, vuelven liberable el certificado autenticado y permiten continuar el ETS conforme a sus transiciones vigentes.

El circuito fiscal no está cerrado para Producción, cancelación/sustitución, complementos PPD y notas de egreso. Cerrar el modal sin guardar tampoco conserva automáticamente el estado React actual.

## 8. Control Documental

Control Documental V1 administra Lista Maestra, ficha, versiones, activación/publicación y obsolescencia. Plantillas Maestras reutiliza el mismo modelo de documentos controlados; no crea un repositorio paralelo. El diseñador general está deshabilitado en V1.

## 9. Cierre

El ETS puede avanzar a liberado y cerrado tras las compuertas operativas. Encuesta y reporte final no existen en el flujo implementado actual.

## 10. Portal del Cliente

El alta pública crea una cuenta externa pendiente, envía verificación y notifica
a personal interno. La verificación confirma el buzón pero no concede datos de
cliente. MYC revisa el registro, propone un cliente y aprueba o rechaza la
solicitud; sólo la aprobación crea una membresía activa. Como alternativa, una
invitación ya fija cliente y roles y crea la membresía al aceptarse.

El inicio de sesión del portal resuelve una membresía activa única, calcula la
unión de permisos de sus roles y emite un JWT de contexto `client_portal`. Cada
consulta deriva el `client_id` de esa membresía. Suspender o revocar la
membresía corta el siguiente acceso aun si el token no ha expirado.

El personal autorizado administra en Ajustes una bandeja global que distingue
cuenta, registro público, solicitud, membresía e invitación. Comercial propone
un cliente con justificación; Administración toma la solicitud, la aprueba o
rechaza y, sólo al aprobar, asigna uno o varios roles y crea la membresía. Las
acciones de cliente, roles, contacto principal, suspensión, reactivación y
revocación usan endpoints específicos y producen auditoría.

Dentro del Portal, `users.view` habilita la sección Usuarios. `users.invite` y
`users.manage` agregan acciones sin aceptar `client_id`: el backend deriva la
empresa desde la membresía del actor, limita roles a los globales o propios de
esa empresa y protege al último administrador activo.

## Excepciones y rutas laterales

- Cotización aprobada + ETS realmente virgen permite solicitar
  `Desbloquear cotización` desde Ventas. El usuario trabaja con los folios
  `MYC-…`, `OSMYC-…` y `EXV-…`; nunca captura IDs internos. Un revisor distinto
  autoriza, rechaza o pide información. La autorización es temporal, nominativa
  y de un solo uso. El Comercial edita directamente todas las partidas, revisa
  el delta y guarda una nueva revisión. Backend revalida bajo lock, elimina
  físicamente el ETS virgen y sus OT pendientes derivadas, y lo recrea desde la
  nueva revisión conservando exactamente el mismo folio `OSMYC-…`. Equipos,
  capturas, firmas, certificados, facturas, resoluciones o una OT avanzada
  bloquean toda la operación sin cambio parcial.
- Equipos adicionales pueden bloquearse y registrar una solicitud/comentario, pero la excepción no es todavía un agregado persistente especializado.
- Estados legacy de certificados se normalizan para compatibilidad.
- Las firmas directas y el número de OT en `service_orders` siguen presentes como compatibilidad junto a las estructuras vigentes por ciclos y `service_work_orders`.

## Flujo temporal OT LAB móvil

```text
login Mobile
→ backend autentica User
→ internal: permisos internos, sin Client
→ client: membership active única + Client activo + permisos externos
→ exige mobile.access
→ access/refresh conserva actor; cada request revalida base
```

Para cliente, crear/listar/abrir/modificar OT LAB deriva siempre
`context.client_id`; el nombre enviado no decide organización. Detalle, equipo,
firma, PDF, revisión y Ticket de otro cliente responden 404 o 403 según si la
denegación ocurre por ownership o por falta de capacidad. Staff conserva el
scope previo y puede leer históricos sin `client_id`.

```text
Login interno técnico
→ OT's → Generar orden
→ backend asigna folio LAB 6400..6999
→ datos generales manuales una sola vez
→ equipos compactos (máximo 10 por OT)
→ al llenar 10: backend crea OT adicional y hereda generales
→ navegación por todas las OT del mismo root_work_order_id
→ revisión de recepción del grupo histórico y estados por folio
→ elegir recepción grupal o sólo OT {folio}
→ backend valida equipo/servicio/cliente documental y folio/LinkedCompany aplicable
→ firma técnico y firma cliente se conservan localmente hasta estar ambas válidas
→ validación final del contexto + lock anti-submit
→ un único POST grupal o individual crea la sesión completa
→ draft → received_signed; la recepción queda congelada
→ crear la primera FieldSheet → in_progress
→ guardar o descartar la FieldSheet vigente editable
→ al descartar recaptura, restaurar la revisión completed predecesora sin mutarla
→ completar todas las FieldSheets requeridas → ready_to_close
→ cerrar sin pedir otra firma → completed y PDF de la cohorte elegida
→ hermanas abiertas conservan su estado y una completed queda históricamente congelada
→ iOS abre impresión o compartir para el folio seleccionado
→ Administrador puede confirmar y eliminar una OT LAB individual
→ backend repara raíz/cadena y conserva recursos compartidos
→ app cierra detalle y vuelve a consultar el listado LAB
```

En Vinculado, el valor capturado se autoriza directamente sólo si el actor
tiene `lab_folios.resolve`; de lo contrario queda `pending` y se conserva como
`requested_folio` en el Ticket. La fecha de recepción se edita contra
`LabWorkOrder.reception_date`, no contra una hoja aislada: staff autorizado
sincroniza en una transacción las revisiones vigentes editables y el técnico
sólo puede enviar `reception_date_change`. Atender ese Ticket comunica y deja
trazabilidad, pero nunca aplica la fecha automáticamente.

La entrada “Hojas de Campo” consulta una sola página agregada LAB. Backend
selecciona exclusivamente la revisión `is_current=true`, calcula progreso desde
el snapshot y clasifica `pending / in_progress / completed`; Mobile sólo agrupa
y presenta. Al editar Resultados, “Guardar y salir” cierra únicamente tras
confirmación de guardado; ante error conserva valores locales y permite retry.
Los rechazos 422 se normalizan a `fieldErrors`, mantienen un resumen humano y
marcan el input o celda localizable; editar ese control limpia únicamente su
propio error.
Una invalidación técnica retira la revisión vigente completed sin modificarla;
la siguiente captura crea N+1 y cada revisión conserva su PDF/hash propio.

Dentro del canvas, Pointer Events y captura de puntero conservan el stroke y el
scroll nativo se pausa sólo mientras el dedo dibuja; fuera del canvas vuelve a
operar normalmente. Los puntos se guardan normalizados y se repintan con el DPR
actual, por lo que una rotación no borra la firma. Refetch, objetos nuevos y
rerender conservan la captura si no cambia el contexto de cohorte. Grupo usa
`root_work_order_id`; individual usa el ID de la OT. Cambiar modalidad, OT
individual o raíz limpia nombres, strokes, `hasDrawing`, PNG y paso, sin caché
recuperable.
Un tap no habilita avance: `pointerup` elimina strokes sin dos puntos/distancia
`0.01`, emite la captura final y TypeScript repite esa validación. El botón sólo
se habilita después de recibir `postMessage` con un trazo significativo.

La captura móvil muestra Cliente, Domicilio, Atención, C.P., Ciudad, Estado,
Orden de compra/cotización, Observaciones y fechas en grupos desplazables que
respetan el safe area de iOS; teléfono y correo no forman parte de esta vista.
Al generar cada PDF, Domicilio, C.P., Ciudad y Estado se transportan a campos
institucionales independientes y una orden de compra ausente queda vacía.

El retiro futuro sigue `detener altas → exportar → validar conteos/checksums →
custodiar → retirar consumidores/modelos → migración controlada de tablas`. No
existe eliminación automática ni dependencia desde el flujo productivo.

La eliminación LAB exige `lab_work_orders.delete` en guard y router sin mirar
el nombre del rol. No restringe estado, pero sí ownership: equipos, PDF binario,
revisiones y tickets exclusivos desaparecen con la OT; una sesión de firma,
ticket o revisión compartida se conserva. Si se elimina la raíz con hermanas,
la primera superviviente se convierte en raíz, se recompone `previous` y se
compacta `sequence_number`. `204`/`404` cierran el detalle y refrescan desde el
backend; `403`, `409` o red mantienen la OT local. Ninguna llamada usa
`/api/service-orders/...`.

Desde 2026-08-27, una OT `completed` sólo vuelve a edición mediante Ticket. El
técnico solicita; la OT sigue cerrada; Calidad/autoridad rechaza o aprueba una
política de firma; el backend crea snapshots de la cohorte de sesión y abre
revisión N+1 sólo para ella;
cada edición valida `edit_version`; los cambios estructurales invalidan la
firma activa; el cierre exige firma válida, genera PDF nuevo y resuelve el
Ticket. El PDF y firma anteriores permanecen consultables.
Cuando la reapertura conserva una sesión histórica válida
(`canSkipSignaturesAfterReopen=true`), el CTA de equipos continúa directamente
a captura técnica y `openExisting`/`selectRelated`/realtime no interpretan la
coincidencia de cohorte como una captura de firmas activa. Si el backend
invalida después esa condición, el mismo objeto actualizado recupera
automáticamente el flujo normal de firmas, sin un bypass persistente en Mobile.
- Certificados sin pago pueden liberarse sólo cuando el ETS no requiere pago; no se documentó una excepción financiera general independiente del modelo actual.

## Flujo de notificaciones operativas móviles V1

```text
Ticket creado/aprobado/rechazado/resuelto o firma requerida
→ resolver destinatarios por permiso/solicitante
→ persistir Notification con event_key único
→ commit de dominio y notificación
→ intentar Expo Push sobre PushDevice activos
→ MYC Mobile invalida lista, detalle y badge
→ API autenticada devuelve el estado actual
```

Al login/restaurar sesión se registra el token Expo del dispositivo físico. Al
logout se desactiva esa asociación. En foreground el evento actualiza los
recursos activos; al volver desde background o recuperar foco se hace un
refetch acotado; una mutación local invalida inmediatamente. El toque de un
push conserva el destino durante la restauración de sesión, pero nunca usa el
payload como detalle permanente. Pull-to-refresh sigue disponible y no existe
polling global.

## Flujo LabClient Mobile — 2026-09-02

```text
Admin importa XLSX LAB
→ normalizar encabezados y resolver aliases
→ validar CLIENTE/CONTACTO/DIRECCIÓN
→ conservar postal_code/city/state opcionales como strings recortados
→ ignorar DIRECCIÓN ORIGINAL/REVISAR
→ deduplicar por empresa+dirección+atención
→ persistir y auditar en una transacción

selector OT vacío o con 1 carácter → no request
selector OT con 2+ caracteres → debounce 300 ms → search + limit=5 en SQL
módulo Clientes → search + limit=25 + offset → reemplazar o Cargar más
```

Ambas superficies consumen `GET /api/mobile/v1/technician/lab-clients` y
mantienen permisos, scope de `operator_client_id` y filtro de inactivos.

## Flujo de Comunicaciones — Etapas A–I

```text
sesión Mobile válida (staff o cliente autorizado)
→ RealtimeProvider ofrece protocolo v1 + access JWT
→ backend valida JWT y vuelve a resolver User en base
→ acepta socket y une exclusivamente user:{id}
→ emite realtime.connected con envelope v1
→ provider queda connected

conversation.subscribe(conversation_id)
→ backend consulta permiso, participación y ownership
→ cliente exige conversation_type=client y mismo client_id
→ autorizado: une conversation:{id}
→ ajeno: realtime.error sin unirse

usuario envía mensaje
→ MYC Mobile crea optimistic row con client_message_id
→ REST valida membership y bloquea la conversación
→ asigna sequence, persiste mensaje/recibos/menciones/notificaciones
→ commit
→ publica message.created y notification.created
→ app concilia por client_message_id o conserva failed para retry

usuario abre/lee conversación
→ REST avanza receipt/cursor sin permitir regresión
→ publica message.delivered o message.read
→ todos los dispositivos actualizan estado

typing.started / typing.stopped
→ backend vuelve a validar membership y suscripción
→ publica evento efímero en conversation:{id}
→ cliente limita frecuencia y expira indicador localmente

desconexión recuperable / regreso a foreground
→ reconnecting con backoff
→ nuevo realtime.connected
→ resynchronizing
→ GET /sync desde la última sequence hasta cerrar todos los huecos
→ refresco REST de conversaciones/no leídos
→ connected
```

Background y logout cierran socket, timers y listeners. Si expira el access
JWT, el servidor cierra `4401`; la app usa el refresh HTTP existente, reconecta
y resincroniza. Push y realtime sólo despiertan/invalidan; el detalle se vuelve
a obtener por REST.

## Flujo ETS Venta — 2026-08-18

```text
cotización aceptada con operational_category=sale
→ creación idempotente del ETS
→ materialización desde operational_snapshot
→ partida por cantidad o ServiceUnit por unidad identificable
→ arribo exclusivo del asesor
→ coincidencia con snapshot o revisión comercial/autorización
→ calibración incluida sobre la misma unidad/equipo, cuando aplica
→ garantía: retorno al flujo / reemplazo pendiente / cancelación comercial
→ entrega parcial: recolección / paquetería / técnico MYC
→ firma obligatoria o atestación técnica estructurada según modalidad
→ cierre de Venta; el ETS sólo cierra si no quedan partidas ajenas abiertas
```

Un ETS histórico sin proyección de Venta no se modifica al consultarlo. El
asesor ejecuta una inicialización explícita que usa únicamente el snapshot. La
propuesta/selección de Hojas de Campo continúa en su servicio vigente.
Venta conserva `evolution_enabled=false`; Calibración posterior valida el
vínculo comercial exacto y no pasa por el motor evolutivo de Servicio General.

## Flujo implementado 2026-08-26 — Grupo anticipado OT LAB

`Operativo Sr → pending (0 folios, 0 conversación) → claim/in_review + handler + conversación requester/handler → aprobar → lock solicitud + secuenciador → N OTs enlazadas → approved + root → commit → mensaje/notificación/realtime`. Rechazo exige motivo y no toca el secuenciador. Staff internal con `lab_work_order_groups.create` usa la misma materialización directamente desde Web/Mobile, sin request ni aprobación.

`actor_type=client → POST alta individual/grupo directo/adicional → 403`; `actor_type=internal → POST external group-request → 403`. En Mobile administrativo, Solicitudes presenta separadamente reaperturas y grupos, con claim/decisión sujetos a permiso y handler. El Home suma sólo reaperturas y grupos `pending` que el actor puede procesar. La notificación `requested` abre esa bandeja y el request exacto; `in_review/approved/rejected` abre el detalle externo con folios o motivo.

El borrado administrativo LAB bloquea OT, grupo y, cuando se retira la raíz,
la `LabWorkOrderGroupRequest` vinculada. Con hermanas sobrevivientes promueve la
primera y reparenta solicitud/cadena/recursos compartidos; sin sobrevivientes
deja la raíz de la solicitud en `NULL` y conserva `approved`, decisión,
participantes y conversación. Todo ocurre antes del `DELETE` y dentro del mismo
commit. El secuenciador no se reduce ni reutiliza folios eliminados.
