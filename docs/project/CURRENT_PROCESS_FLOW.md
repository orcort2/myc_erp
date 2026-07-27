> Estado: VIGENTE
>
> Tipo: Vigente (canónico)
>
> Autoridad: Alta
>
> Prevalece sobre: `archive/process/flujo-general.md` y secuencias operativas de las especificaciones V2/V3
>
> Corte verificado: 2026-07-28

# Flujo operativo actual

Este documento describe el flujo que existe en el sistema, no el flujo ideal ni el diseño futuro.

## Motor de Resoluciones

El flujo interno implementado y todavía sin integración concreta con dominios
del ERP es:

```text
draft → contexto → análisis → plan → simulación declarativa
→ autorización exacta → revalidación → ready_for_execution
→ reserva idempotente + lock → executing
→ checkpoints y acciones por ActionRunner
→ completed | partially_completed | failed | blocked
[si existe plan compensatorio autorizado y elegible]
→ compensating
→ compensated | partially_compensated | compensation_failed
[consulta de auditoría autorizada]
→ reconstrucción → verificación → timeline/reporte
```

Un plan no autorizado o no revalidado no inicia. Cada acción se identifica por
ejecución y paso, persiste su intención antes de invocar el adaptador y conserva
resultado/efectos después. Al regresar del handler, el token/TTL se valida y el
checkpoint lo vuelve a validar atómicamente. Una pérdida de lock o resultado
incierto termina en `blocked` sin repetición automática. El outbox se publica
sólo mediante una invocación explícita y conserva la fecha de fallo.

La compensación es un flujo independiente y síncrono. Sólo parte de una
ejecución terminada elegible, usa una decisión `resolution.compensate` para la
ejecución y actor exactos, persiste un plan inmutable y ejecuta en orden inverso
únicamente acciones declaradas reversibles. Una selección parcial se rechaza
antes de persistir si deja activo cualquier dependiente confirmado directo o
transitivo; un efecto no confirmado o ya compensado no bloquea. Punto de no
retorno, duplicado, actor distinto, fallo o pérdida de lock se rechazan o
quedan trazados sin reinvocación. No existen API, workers, schedulers, retries,
recuperación, conciliación ni compensación automática.

La auditoría es un flujo read-only separado. Exige una decisión
`resolution.audit.inspect` concedida para la resolución, actor, correlación,
recurso y organización exactos. Después carga el expediente completo, proyecta
su evidencia sin exponer ORM, verifica hashes, referencias, pertenencia y
secuencia, y genera una línea de tiempo y un hash deterministas del corte. Los
filtros se aplican sólo después de verificar el conjunto completo. La consulta
no transita Lifecycle, no ejecuta handlers y no publica outbox.

## Flujo principal

```text
Autenticación
  → Cliente y datos fiscales
  → Cotización y partidas
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

## 1. Acceso

El usuario inicia sesión y recibe access/refresh JWT con tipos explícitos. Sólo
access autentica solicitudes y refresh se utiliza únicamente para renovar el
par. El registro público no acepta roles solicitados; el backend decide el rol
bootstrap/base. La navegación autenticada carga el usuario actual y sus roles.
Existen brechas de autorización documentadas fuera del Motor; este flujo no debe
interpretarse como evidencia de que todos los endpoints están protegidos.

## 2. Cliente y Cotización

El cliente conserva identidad, datos fiscales, contactos dependientes, constancia y perfiles de certificado. La cotización se crea con partidas propias o provenientes del Catálogo MYC, calcula importes, guarda snapshots y puede transitar entre `draft`, `sent`, `waiting` y estados terminales.

La aceptación de una cotización no crea automáticamente Agenda ni ETS en todos los recorridos. Un ETS puede vincularse a cliente y cotización; esa vinculación debe conservar coherencia entre ambos.

Un Servicio Compuesto aparece una sola vez en la cotización y en sus documentos comerciales. Al crear el ETS, el backend recorre su composición normalizada, multiplica las cantidades y genera partidas operativas únicamente para los servicios simples hoja. Esas partidas alimentan sin lógica paralela el conteo de OT, Equipos, Hojas de Campo y Certificados. Servicios simples, conceptos libres y cotizaciones existentes conservan el comportamiento anterior.

En calibración, la partida del catálogo conserva una de tres modalidades canónicas: acreditación propia, trazable/no acreditada o acreditación por laboratorio vinculado. La clave se propaga a la partida cotizada y al ETS. Al registrar equipos, la capacidad configurada resuelve el alcance automáticamente cuando sólo hay una alternativa; si hay varias con cupo, se solicita desambiguar entre ellas. No se deriva la modalidad desde una leyenda o número impreso en el Master.

Al crear el ETS, cada `ServiceOrderItem` congela el identificador del Master esperado mediante el ID estable del concepto operativo. Al registrar el equipo, Equipos lee exclusivamente esa partida y congela alcance, tipo de certificado, Master esperado, partida y origen de catálogo junto con la versión/archivo del Master. Cambiar después el nombre o la selección del catálogo no modifica el expediente; no existe resolución por `service_name`.

## 3. Agenda y Llamado dentro de ETS

Agenda y Llamado no son módulos autónomos actuales. La fecha de agenda vive en el ETS y el llamado es el hito `confirmed → called`. No existe actualmente el circuito histórico con folios `AMYC`/`SMYC`, calendario, bitácora y estados independientes.

## 4. ETS, OT, equipos y firmas

El ETS usa la máquina de estados:

```text
scheduled → confirmed → called/in_progress → technical_review
→ capture → quality_review → pending_payment/released → closed
```

`cancelled` es terminal y existen rutas alternativas permitidas por la máquina vigente. Al crear el expediente se generan Órdenes de Trabajo según los cupos; cada OT admite como máximo 10 equipos. Los ciclos de firma vinculan las OT activas pendientes del momento; una OT agregada después requiere un ciclo nuevo.

## 5. Hojas de Campo y Captura

Cada equipo puede tener una Hoja de Campo activa con snapshot de plantilla e identidad institucional. Se capturan resultados y firmas, se completa la hoja y se prepara el paquete de Captura por ETS u OT. El paquete depende de una Plantilla Maestra XLSX activa, vigente, existente y cuyo hash coincida con el snapshot del equipo.

Para el Paquete de Captura, `completed`, `under_review` y `approved` representan hojas técnicamente terminadas. La transición `complete` valida condición inicial/final, campos requeridos por plantilla, observaciones o evidencia y resultados estructurados; `Revisó` y `Elaboró informe` pertenecen a etapas posteriores y no bloquean el paquete. El flujo general de Hojas de Campo sigue sin cerrar por semánticas, automatizaciones metrológicas y acciones propias de aprobación/rechazo.

Al devolver el ZIP/Master, cada Excel útil se identifica y persiste con sus validaciones. El primer Master identificado inicia `capture_in_progress` con actor y auditoría; metadatos `._*`, `.DS_Store` y `__MACOSX/` se ignoran. La interfaz muestra el resumen devuelto y vuelve a consultar ETS, certificados y registros de Captura sin exigir recarga manual. `match_status` se conserva como dato legacy y no gobierna la autenticación.

Captura no carga el PDF final. Para cada certificado, `identified` con advertencias `no_encontrado` permite enviar; ausencia de Master identificado o resultados `mismatch`/`no_coincide` bloquean. El envío persiste `capture_in_progress → quality_review` con actor, fecha y referencia al XLSX. Calidad descarga el Master, revisa advertencias/diferencias y puede aprobarlo o regresarlo a Captura.

## 6. Calidad y Certificados

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

La habilitación de Autenticar depende exclusivamente de `quality_approved` o del alias legacy `approved`. No requiere PDF previo, `final_pdf_path`, carga manual, PDF validado ni `match_status`. La conversión usa el Master identificado más reciente, persiste actor/fecha/auditoría/referencia al Master y omite de la exportación las hojas auxiliares sin área de impresión; el XLSX original no se modifica. La implementación aún expone la misma acción desde ETS; retirar esa superficie duplicada continúa como deuda, sin cambiar la regla de que Calidad debe ser el único autenticador funcional.

El modal de Calidad conserva la lista visible con la que se abrió y permite navegación secuencial no circular. Cuando la tarjeta pertenece a una agrupación OT, ésa es la frontera prioritaria; si no existe una OT resoluble, se usa el ETS y, en último término, la lista filtrada visible. Cada cambio vuelve a consultar certificado e historial, oculta el contenido anterior durante la carga y recalcula readiness y acciones. Aprobar, regresar a Captura o autenticar mantiene el modal y su posición contextual abiertos mientras refresca el registro activo, la lista y los contadores.

La vista de Certificados muestra únicamente documentos con PDF autenticado y estados autenticado/liberado. `authenticated` con archivo autenticado existente deriva “Listo para liberar”; no es una liberación automática. Si el ETS requiere pago y no está cubierto, el mismo certificado se muestra documentalmente autenticado pero “Pendiente de pago”. Con compuerta financiera cumplida, Liberar persiste actor/fecha/auditoría y transita a `released_to_client`. `match_status` se conserva sólo para trazabilidad legacy y no participa en disponibilidad, agregados, habilitación ni endpoint de liberación.

## 7. Facturación y pago

La Mesa de trabajo puede originar borradores desde ETS/cotización, congelar snapshots fiscales y emitir en Facturama Sandbox. El sistema conserva intentos, identificadores, XML/PDF del PAC y genera PDF institucional MYC. Los pagos actualizan saldo y estado administrativo.

El Workbench conserva este mismo flujo mediante un controlador frontend único. Puede abrirse con contexto explícito `invoice_id` o `service_order_id`; el contexto ETS consulta el listado existente filtrado y ya no se transporta por `localStorage`. La pestaña Facturación del ETS muestra el `Invoice` asociado, abre el mismo `InvoiceWorkbenchDialog`, actualiza el resumen con la respuesta de guardar/emitir y regresa al mismo ETS al cerrar. No implementa pagos, cuentas por cobrar, notas de crédito, historial/documentos ni liberación financiera; esas tarjetas permanecen informativas para una fase posterior.

El circuito fiscal no está cerrado para Producción, cancelación/sustitución, complementos PPD y notas de egreso. Cerrar el modal sin guardar tampoco conserva automáticamente el estado React actual.

## 8. Control Documental

Control Documental V1 administra Lista Maestra, ficha, versiones, activación/publicación y obsolescencia. Plantillas Maestras reutiliza el mismo modelo de documentos controlados; no crea un repositorio paralelo. El diseñador general está deshabilitado en V1.

## 9. Cierre

El ETS puede avanzar a liberado y cerrado tras las compuertas operativas. Encuesta y reporte final no existen en el flujo implementado actual.

## Excepciones y rutas laterales

- Equipos adicionales pueden bloquearse y registrar una solicitud/comentario, pero la excepción no es todavía un agregado persistente especializado.
- Estados legacy de certificados se normalizan para compatibilidad.
- Las firmas directas y el número de OT en `service_orders` siguen presentes como compatibilidad junto a las estructuras vigentes por ciclos y `service_work_orders`.
- Certificados sin pago pueden liberarse sólo cuando el ETS no requiere pago; no se documentó una excepción financiera general independiente del modelo actual.
