> Estado: VIGENTE
>
> Tipo: Vigente (canónico)
>
> Autoridad: Alta para reglas funcionales confirmadas
>
> Prevalece sobre: `archive/process/reglas-negocio.md`, reglas de especificaciones V2/V3 y bitácoras cronológicas retiradas conservadas por Git
>
> Corte verificado: 2026-08-26

# Reglas de negocio vigentes

## ETS Mantenimiento

- Nace exclusivamente de `operational_category=maintenance`; sus unidades no usan evolución genérica.
- Tipo, modalidad y materiales base quedan congelados en snapshot.
- Campo no registra arribo; laboratorio sí y conserva custodia MYC durante pausas por refacción.
- Preventivo no cambia a correctivo sin partida aprobada vinculada o override administrativo auditado.
- Mantenimiento no ejecuta Reparación: sólo documenta y vincula un ETS independiente.
- Condición final inoperable bloquea terminación/cierre hasta resolver investigación.
- Material utilizado y requerido son distintos; costos internos nunca aparecen en el reporte del cliente.
- Terminación técnica, reporte, firma y cierre son hitos distintos; la firma identifica la versión.
- Recomendación rechazada no bloquea si el alcance original terminó, quedó documentada y se firmó el reporte vigente.
- Todo bloqueante indica mensaje, sección y campo y debe ser visible/navegable en frontend.

Sólo se incluyen reglas verificadas en la implementación o en una decisión vigente. Las reglas históricas no confirmadas quedan fuera de este documento.

| ID | Módulo | Regla vigente | Evidencia principal | Decisión aproximada |
| --- | --- | --- | --- | --- |
| BR-001 | Cotizaciones | El folio usa `MYC-MM-AA-####` y no debe colisionar. | `backend/app/services/quotations.py`, `backend/app/core/folios.py` | 2026-06, confirmada 2026-07 |
| BR-002 | Cotizaciones | Sólo se permiten las transiciones definidas; aceptada, rechazada, expirada y cancelada son terminales. | `backend/app/services/quotations.py` | 2026-06 |
| BR-003 | Cotizaciones | Las partidas congelan datos comerciales, fiscales y operativos relevantes. Reabrir o editar conservando el mismo concepto no refresca `operational_snapshot` desde el catálogo vigente; sólo una sustitución explícita de concepto crea configuración nueva. | [`../architecture/OPERATIONAL_SERVICE_IDENTITY.md`](../architecture/OPERATIONAL_SERVICE_IDENTITY.md), `backend/app/services/quotations.py` | 2026-08-18 |
| BR-048 | Cotizaciones / ETS | El desbloqueo `quotation.controlled_unlock` permite editar directamente las partidas de una cotización aprobada sólo cuando su ETS pasa el validador integral de virginidad. Compara revisiones, crea snapshots nuevos y reconstruye físicamente el ETS con el mismo `OSMYC-…`; un cambio operativo bloquea sin mutación parcial. | [`../architecture/sales/QUOTATION_CONTROLLED_UNLOCK.md`](../architecture/sales/QUOTATION_CONTROLLED_UNLOCK.md) | 2026-07-29 |
| BR-004 | ETS | `service_orders` es la raíz operativa del expediente y debe pertenecer a un cliente activo; una cotización vinculada debe ser coherente con ese cliente. | `backend/app/models/service_order.py`, `backend/app/services/service_orders.py` | V3, vigente 2026-07 |
| BR-005 | ETS | El folio usa `OSMYC-AA-MM-####`; el estado sólo cambia mediante la máquina de transiciones vigente. | `backend/app/services/service_orders.py`, `backend/app/core/folios.py` | 2026-06 |
| BR-049 | ETS / Excepciones | Toda excepción operativa ETS sigue `requested → authorized → executed`. Solicitar o autorizar sólo persiste el expediente, actor, timestamps, auditoría y evento; únicamente ejecutar una autorización vigente, tras revalidar el estado ETS congelado, puede cambiar el estado operativo o resincronizar facturas derivadas. Un mismo Administrador puede actuar en las tres etapas, pero cada transición y evidencia permanece separada. | `backend/app/models/service_order_exception.py`, `backend/app/services/service_orders.py`, pruebas de integridad ETS | 2026-08-10 |
| BR-006 | OT/Equipos | Una OT agrupa como máximo 10 equipos; las OT usan consecutivo numérico único. | `WORK_ORDER_EQUIPMENT_LIMIT`, `ServiceWorkOrder` | 2026-07 |
| BR-007 | Firmas ETS | Una captura de firmas cubre las OT activas pendientes del ciclo; una OT posterior requiere otro ciclo. | modelos/servicios de ciclos de firma; cierre ETS 2026-07-10 | 2026-07-10 |
| BR-008 | Equipos | Los equipos adicionales fuera de capacidad requieren el tratamiento de excepción definido; los no realizados deben conservar motivo cuando ese estado se use. | servicios ETS/equipos y cierre ETS | 2026-07 |
| BR-009 | Plantillas Maestras/Equipos | Al crear el ETS, cada partida congela el identificador del Master esperado. Al dar de alta el equipo, éste congela documento, versión, ruta, nombre, hash, vigencia y el contexto operativo —alcance, tipo de certificado, Master y partida/origen— sin resolver por nombre ni volver a consultar el catálogo. | modelos/servicios de ETS y Equipos; migración `8c2d4e6f7a9b` | 2026-07-23 |
| BR-010 | Hojas de Campo | La hoja conserva snapshot de plantilla e identidad; una plantilla no debe cambiar retroactivamente una hoja creada. | modelos/servicios de Hojas de Campo | 2026-07-13 |
| BR-011 | Hojas de Campo | No hay fallback silencioso a plantilla General cuando no existe coincidencia segura; la selección debe ser explícita. | integración operativa auditada 2026-07-13 | 2026-07-13 |
| BR-012 | Certificados | Cada certificado se vincula a un equipo y un ETS. Calibración usa `MYCA`/`MYCT` o el prefijo vinculado congelado seguido por `AAMMNNNN`; Verificación usa obligatoriamente `MYCV-MM-AA-XXXX`, inicia `XXXX` en `0001` por año, no reinicia al cambiar de mes, continúa desde folios MYCV existentes y no admite edición manual. | `backend/app/services/institutional_folios.py`, arquitectura de folios | 2026-08-24 |
| BR-013 | Calidad | La aprobación del Master XLSX es la única compuerta documental para autenticar. Desde `quality_approved` —o el alias legacy `approved`— Autenticar genera el PDF final desde el Master identificado, lo sella, conserva actor/fecha/auditoría/referencia al Master y pasa a `authenticated`. No exige PDF previo, `final_pdf_path` ni `match_status`; un rechazo de Calidad requiere comentario. | `backend/app/services/certificate_authentication.py`, pruebas de autenticación desde Master | 2026-07-21 |
| BR-014 | Certificados | Calidad es la única superficie funcional que puede solicitar autenticación; ETS sólo consulta el estado. `certificate_authentication.authenticate_certificate` es la autoridad transaccional única, exige actor/origen Calidad, bloquea el certificado y persiste audit/evento una sola vez. | `docs/modules/calidad/AUTENTICACION_CERTIFICADOS.md`, cierre P0 y pruebas de integridad | 2026-08-10 |
| BR-015 | Certificados | La vista ordinaria de Certificados sólo muestra PDFs autenticados en estado autenticado o liberado. | frontend de Certificados y servicio de certificados | 2026-07 |
| BR-016 | Liberación | Un certificado queda documentalmente listo cuando está `authenticated` y existe su PDF autenticado. La liberación no consulta `match_status`: si el ETS requiere pago, exige factura pagada y saldo cero; si no requiere pago, la compuerta financiera no bloquea. Autenticar no libera automáticamente. | `release_to_client`, readiness financiero y pruebas HTTP en `backend/app/services/certificates.py` | 2026-07-21 |
| BR-017 | Facturación | Un borrador fiscal congela emisor, receptor, origen, partidas e impuestos para evitar cambios retroactivos. | modelos/servicios de facturación | 2026-07 |
| BR-018 | Facturación | La emisión bloquea duplicados y estados ambiguos; un resultado desconocido se concilia antes de cualquier reintento. | `backend/app/services/facturama/invoices.py` | 2026-07-15 |
| BR-019 | Facturación | PostgreSQL y los archivos persistidos son fuente del expediente fiscal; Catálogos SAT locales son fuente operativa de nomenclaturas. | arquitectura SAT y servicios de facturación | 2026-07 |
| BR-020 | Control Documental | Sólo una versión documental puede permanecer activa; activar una nueva vuelve obsoletas las activas anteriores. | `backend/app/services/controlled_documents.py` | 2026-07-10 |
| BR-021 | Plantillas Maestras | Una versión activa requiere XLSX válido, máximo 20 MB y no caducado. | `backend/app/services/controlled_documents.py` | 2026-07-17 |
| BR-022 | Catálogos SAT | No se consulta SAT por HTTP en ejecución; la fuente operativa es la base local versionada y favoritos/alias MYC no alteran datos oficiales. | [`../architecture/CATALOGOS_SAT.md`](../architecture/CATALOGOS_SAT.md) | 2026-07-14/17 |
| BR-023 | Clientes | La eliminación física sólo procede sin historial funcional; con dependencias se archiva y la auditoría textual se conserva. | `backend/app/services/clients.py`, cierre técnico de Clientes | 2026-07-14 |
| BR-024 | Auditoría | Transiciones críticas deben registrar actor, acción, entidad y valores anterior/nuevo cuando el servicio lo implementa. | servicios de auditoría y dominios | V2/V3, vigente parcial |
| BR-025 | Captura | Una Hoja de Campo es elegible para paquete en `completed`, `under_review` o `approved`; descargar/generar PDF no equivale a completar. | `backend/app/services/capture_packages.py`, motor operativo y constantes frontend | 2026-07-21 |
| BR-026 | Captura | El ZIP ETS agrupa `FOLIO_ETS/OT-####/FOLIO_CERTIFICADO/` y nombra los archivos `Hoja_Campo_{folio}.pdf` y `Master_{folio}.xlsx`; descargar es de sólo lectura. | servicio y prueba del Paquete de Captura | 2026-07-21 |
| BR-027 | Captura | Un Master devuelto e identificado persiste su archivo/validaciones e inicia el certificado en `capture_in_progress` con actor y auditoría; Captura no altera el `match_status` legacy y éste no es compuerta de autenticación. Los auxiliares macOS no se procesan ni cuentan. | servicio y prueba reversible de carga de Captura | 2026-07-21 |
| BR-028 | Captura/Calidad | El envío individual a Calidad exige Master esperado e identificado y cero `mismatch`/`no_coincide`; `no_encontrado` es advertencia permitida. La transición es `capture_in_progress → quality_review`, audita actor/fecha/Master y no exige PDF ni modifica `match_status`. | readiness, transición y pruebas del flujo Master | 2026-07-21 |
| BR-029 | Captura | El tipo de servicio del Master se valida como `accredited` o `traceable` mediante similitud estructural con el snapshot asignado: hojas, dimensiones, fusiones, estilos, fórmulas, etiquetas posicionadas, imágenes y área de impresión. La leyenda o número de acreditación no son identificadores del dominio. | `master_template_fingerprints.py`, parser de paquetes y pruebas | 2026-07-21 |
| BR-030 | Catálogo/ETS/Certificados | Las modalidades canónicas de acreditación son `accredited_iso_17025`, `traceable` y `accredited_linked_lab`. Se configuran en el servicio, se propagan automáticamente por cotización→ETS→equipo y se mapean a certificado `acreditado`, `trazable` o `vinculado`; una leyenda documental nunca sustituye la clave de negocio. | [`../architecture/CALIBRATION_SCOPE_CONTRACT.md`](../architecture/CALIBRATION_SCOPE_CONTRACT.md), schemas y servicio de capacidad | 2026-07-22 |
| BR-053 | Catálogo/Cotizaciones/ETS | `operational_category` es la identidad operativa canónica y viaja catálogo→snapshot→partida ETS→unidad/etapa. `item_type` sólo clasifica Producto/Servicio comercial/fiscal: no implica ni bloquea `sale`. Sólo `general_service` habilita diagnóstico evolutivo; categorías no se infieren por tipo, nombre o descripción. | [`../architecture/OPERATIONAL_SERVICE_IDENTITY.md`](../architecture/OPERATIONAL_SERVICE_IDENTITY.md) | 2026-08-18 |
| BR-031 | Autenticación | Sólo un JWT con `token_type=access` autentica solicitudes; un refresh se acepta únicamente en el endpoint de renovación. El registro público no recibe ni decide roles solicitados por el cliente. | `backend/app/core/security.py`, `backend/app/services/auth.py`, schemas y pruebas de seguridad | 2026-07-24 |
| BR-032 | Motor de Resoluciones | Toda operación protegida se deniega si falta identidad activa, autenticación vigente, política aplicable, permiso exacto o evidencia consistente. Una denegación explícita y una incompatibilidad de segregación prevalecen aun cuando existan permisos. | [`../architecture/resolution-engine/15_SECURITY_GOVERNANCE.md`](../architecture/resolution-engine/15_SECURITY_GOVERNANCE.md) y pruebas de Fase 3 | 2026-07-24 |
| BR-033 | Motor de Resoluciones | Sólo un expediente listo, con plan autorizado y revalidación exacta, puede ejecutarse. Idempotencia y lock se reservan antes del primer efecto; el token se comprueba después del handler y en el checkpoint. Expiración, sustitución o respuesta incierta bloquean y no autorizan repetición automática. | [`../architecture/resolution-engine/17_EXECUTION_RUNTIME.md`](../architecture/resolution-engine/17_EXECUTION_RUNTIME.md) y pruebas de Fase 5 | 2026-07-28 |
| BR-034 | Motor de Resoluciones | Una compensación sólo puede partir de efectos `completed` declarados reversibles y de una decisión `resolution.compensate` exacta. Una selección parcial debe incluir todos sus dependientes confirmados activos, directos o transitivos; efectos sin confirmar o ya compensados no bloquean. Lifecycle gobierna el inicio/cierre; orden, actor, clave, hash y lock permanecen exactos también en replay. Un punto de no retorno, fallo o incertidumbre nunca autoriza repetición automática. | [`../architecture/resolution-engine/18_COMPENSATION_ENGINE.md`](../architecture/resolution-engine/18_COMPENSATION_ENGINE.md) y pruebas de Fase 6 | 2026-07-27 |
| BR-035 | Motor de Resoluciones | Consultar auditoría exige una decisión `resolution.audit.inspect` concedida y ligada a resolución, actor, correlación, recurso y organización exactos. El expediente completo se reconstruye sobre un único snapshot transaccional y se verifica antes de filtrar; evidencia ajena, hash incompatible, referencia ausente o hueco de secuencia produce diagnóstico estable. Una consulta nunca mezcla confirmaciones concurrentes, modifica Lifecycle ni invoca ejecución, compensación o outbox. | [`../architecture/resolution-engine/20_AUDIT_EVIDENCE.md`](../architecture/resolution-engine/20_AUDIT_EVIDENCE.md) y pruebas de Fase 7 | 2026-07-27 |
| BR-036 | Motor de Resoluciones | Toda capacidad institucional usa el catálogo integral de acción, permiso y recurso. Crear/transitar Lifecycle, ejecutar, compensar, consultar auditoría o publicar outbox exige una decisión append-only exacta y vigente antes de exponer replay/datos o producir efectos. Los permisos condicionados sólo aplican cuando su contexto coincide; una decisión histórica sin base canónica verificable no autoriza los límites endurecidos de Fase 8. | [`../architecture/resolution-engine/22_INTEGRAL_SECURITY.md`](../architecture/resolution-engine/22_INTEGRAL_SECURITY.md) y suite de Fase 8 | 2026-07-27 |
| BR-037 | Seguridad API | Toda operación HTTP interna debe tener una clasificación canónica y se deniega por defecto. Sólo las excepciones públicas, firmadas, controladas por entorno o de consumidor del Motor expresamente registradas evitan la sesión interna; una operación nueva sin clasificación no puede aceptarse. | [`../architecture/security/API_ACCESS_CONTROL.md`](../architecture/security/API_ACCESS_CONTROL.md), inventario y prueba de conformidad | 2026-08-03 |
| BR-038 | Portal cliente | El actor de portal nunca elige `client_id`: el backend deriva exactamente un cliente activo desde su identidad, exige `portal.read`, filtra cada consulta y valida ownership antes de detalle o descarga. Ambigüedad se deniega y un recurso ajeno responde 404 seguro. | `backend/app/services/client_portal.py`, router y pruebas A/B | 2026-08-03 |
| BR-039 | Secreto JWT | Producción no puede iniciar con secreto JWT ausente, conocido, de ejemplo, corto o de entropía insuficiente. Desarrollo puede usar el valor local explícito con advertencia que nunca imprime el secreto. | `backend/app/core/config.py` y pruebas de configuración | 2026-08-03 |
| BR-037 | Motor de Resoluciones | Toda decisión declara modo, identidad e intención canónica. Las acciones mutantes y outbox son `single_operation`: su consumo append-only se confirma con el efecto, un rollback no lo conserva, el replay con el mismo ID/hash usa la idempotencia existente y otra intención se deniega. Auditoría es `reusable_read` exclusivamente para la misma resolución y contexto durante la vigencia del actor. | [`../architecture/resolution-engine/22_INTEGRAL_SECURITY.md`](../architecture/resolution-engine/22_INTEGRAL_SECURITY.md), migración `f8a0b2c4d6e8` y pruebas concurrentes de Fase 8 | 2026-07-28 |
| BR-038 | Motor de Resoluciones | Cada integración de Fase 9 preserva el ownership del módulo: obtiene hechos mediante Fact Providers read-only y ejecuta únicamente mediante Domain Gateways hacia servicios canónicos propietarios. El Motor no accede a ORM ajeno, duplica reglas o estados ni depende de IA. Todo caso se abre, valida y estabiliza de forma incremental antes del siguiente. | [`../architecture/resolution-engine/23_PHASE_9_OPENING.md`](../architecture/resolution-engine/23_PHASE_9_OPENING.md) y aprobación formal de Fase 8 | 2026-07-28 |
| BR-046 | Motor / ETS | El equipo adicional sólo se vuelve definitivo después de simulación, autorización y revalidación. Cada OT admite como máximo diez equipos; la simulación no asigna OT ni folio. `reconciliation_id` identifica el replay exacto y la compensación sólo alcanza equipo `registered`, reserva `expected` y OT propia vacía. | [`../architecture/resolution-engine/31_PHASE_14_INTEGRATION_EXPANSION.md`](../architecture/resolution-engine/31_PHASE_14_INTEGRATION_EXPANSION.md) | 2026-07-29 |
| BR-039 | Certificados / Motor de Resoluciones | `certificate.resolve_incorrect_release` sólo puede retirar acceso futuro a un certificado vigente, liberado y visible. Conserva estado, actor, fecha y PDF de la liberación; la operación propietaria, cambio y auditoría son transaccionales y append-only. Un replay con clave, hash, operación y payload exactos devuelve el resultado histórico antes de validar el certificado actual; cualquier colisión se deniega. Para una clave nueva se revalida bajo lock y el snapshot posterior se construye después de `flush/refresh`. | [`../architecture/resolution-engine/24_PHASE_9_CERTIFICATES_INTEGRATION.md`](../architecture/resolution-engine/24_PHASE_9_CERTIFICATES_INTEGRATION.md), servicio canónico y suite concurrente de Fase 9 | 2026-07-28 |
| BR-040 | Motor de Resoluciones / API | Toda operación pública v1 declara versión y liga consumidor, actor, organización, correlación e intención exactos. La API sólo traduce a Lifecycle o auditoría y el SDK sólo encapsula HTTP; ninguno replica reglas, estados o Domain Gateways. La clave externa se namespacia por versión/consumidor/organización: un replay exacto recupera el mismo resultado después de autorizar y una colisión se deniega con `idempotency_conflict`. | [`../architecture/resolution-engine/26_PUBLIC_API_SDK.md`](../architecture/resolution-engine/26_PUBLIC_API_SDK.md), contratos y suite de Fase 10 | 2026-07-28 |
| BR-041 | Motor de Resoluciones / API | Todo cursor público debe ser opaco y representar la consulta completa: versión de sobre/contrato, consumidor, organización, hash de filtros, orden, dirección, tamaño y posición keyset se cifran y autentican juntos. Cambiar cualquiera invalida el cursor. Un formato histórico que revele posición o no pueda probar identidad de consulta se revoca, no se reinterpreta. | [`../architecture/resolution-engine/26_PUBLIC_API_SDK.md`](../architecture/resolution-engine/26_PUBLIC_API_SDK.md), codec `c1` y pruebas negativas de cursor | 2026-07-28 |
| BR-047 | Facturación / Pagos | Un pago se registra sobre `Invoice` con saldo positivo y factura no cancelada, puede ocurrir antes o después del timbrado y nunca puede exceder el saldo. Cada registro recalcula total pagado, saldo y estado; el timbrado conserva esa condición financiera. Saldo cero implica `paid`, retira la factura de Cuentas por cobrar y satisface la compuerta de liberación cuando el ETS requiere pago. | `backend/app/services/invoices.py`, `backend/app/services/facturama/invoices.py`, Workbench y pruebas de pagos/readiness | 2026-07-29 |
| BR-048 | Portal del Cliente | Una cuenta externa sólo obtiene ámbito mediante una membresía activa; el correo, el contacto declarado y cualquier `client_id` enviado por frontend no conceden acceso. La suspensión o revocación se revalida en cada token. | `backend/app/core/portal/security.py`, servicios y pruebas del portal | 2026-08-04 |
| BR-049 | Portal del Cliente | Una membresía puede acumular varios roles del portal, pero los roles internos no se reutilizan. No puede suspenderse, revocarse ni degradarse al último administrador activo de un cliente. | `backend/app/services/portal/membership_service.py` | 2026-08-04 |
| BR-050 | Usuarios y autenticación | `User.status` es la autoridad funcional y `is_active` se sincroniza como habilitación. El username interno es obligatorio, único, normalizado e independiente del correo. Cinco fallos consecutivos bloquean temporalmente la cuenta durante 15 minutos; éxito y expiración reinician el contador sin revelar si la identidad existe. | `backend/app/models/user.py`, `backend/app/core/login_policy.py`, servicios de autenticación y pruebas | 2026-08-05 |
| BR-051 | ETS múltiple/evolucionado | `ServiceUnit` conserva la identidad operativa del equipo, su partida origen, categoría inicial y capacidad evolutiva dentro de una intervención. Permanece ligada al mismo ETS/OT cuando agrega categorías; una card o tab es sólo una proyección. Servicio General en otra partida del ETS no concede evolución. | [`../architecture/ETS_MULTIPLE_EVOLVED_CORE.md`](../architecture/ETS_MULTIPLE_EVOLVED_CORE.md), modelos y pruebas Fase 1 | 2026-08-12 |
| BR-052 | ETS / Etapas | Evolucionar agrega una `ServiceStage` secuencial con origen y etapa origen; no cambia la categoría ni borra una etapa previa. Sólo una unidad nacida de Servicio General puede abrir y continuar una cadena evolutiva. Crear una solicitud comercial no muta el lifecycle técnico; una pausa usa transición formal. | arquitectura y `services/service_execution.py` | 2026-08-12 |
| BR-053 | Cotizaciones / ETS | La aprobación es append-only y única por partida también bajo concurrencia. Una partida aprobada sólo habilita categorías compatibles con solicitud y catálogo/snapshot; una rechazada no genera etapa ejecutable. La ruta interna exige `quotations.update`, deriva `source=internal` y cualquier corrección requiere rama formal futura, nunca overwrite/reset. | `QuotationItemDecision`, migración `a7c2e5f8b1d4`, servicio y pruebas negativas | 2026-08-12 |
| BR-054 | Cotizaciones derivadas | El contexto interno conserva ETS, unidad, etapa y solicitud; el snapshot comercial del equipo contiene únicamente marca, modelo y serie. Evidencias, diagnóstico, timeline y estado mutable no se copian a Ventas. | schema/modelo de partida y arquitectura Fase 1 | 2026-08-12 |
| BR-055 | Activity / Tareas | `#tarea` es un atajo: crea una `ServiceTask` independiente con mensaje origen único, creador, asignados y contexto ETS/unidad/etapa. No sustituye Activity ni convierte el texto en autoridad técnica/comercial. | `services/activity.py`, `services/service_execution.py` y pruebas | 2026-08-12 |
| BR-056 | Acceso móvil / Técnicos | Toda lectura móvil deriva ownership de `ServiceOrder.technician_id == current_user.id`; OT y Equipo heredan por `service_order_id`, y Hoja de Campo por `equipment_id → service_order_id`. Un recurso ajeno, inactivo o sin asignación responde 404. Hojas exige conjuntamente `service_orders.read_assigned` y `field_sheets.read`. | [`../architecture/MOBILE_TECHNICIAN_ACCESS.md`](../architecture/MOBILE_TECHNICIAN_ACCESS.md) y suite de aislamiento | 2026-08-12 |
| BR-057 | OT LAB temporal | Una OT LAB admite máximo 10 equipos y folio backend 6400–6999. Una adicional sólo nace desde la última OT llena, hereda generales y conserva cadena por ID. El grupo completo captura una sola sesión de firmas y la identidad de su borrador móvil es exclusivamente `root_work_order_id`: se conserva entre OT hermanas/refetch/rerender y se vacía al cambiar de raíz, sin caché recuperable. Un tap no cuenta como firma. `signature_required=false` es normal antes de la primera firma y no impide su POST; la aceptación corresponde al backend y la política especial de reapertura a `canSkipSignaturesAfterReopen`. Desde la firma no admite nuevas OT, equipos ni edición. Cada OT conserva PDF individual y toda retirada exige exportación íntegra verificada previa. | [`../architecture/LAB_WORK_ORDERS.md`](../architecture/LAB_WORK_ORDERS.md) y suites LAB/móvil | 2026-08-24 |
| BR-058 | OT productiva | Sólo `service_orders.delete` autoriza la eliminación física de una OT, sin restricción por estado. Deben eliminarse atómicamente sus dependencias operativas exclusivas y conservarse ETS, registros comerciales/financieros, maestros, agregados del Motor, auditoría mínima y todo ciclo de firma aún enlazado a otra OT. Una evidencia inmutable del Motor bloquea antes de mutar. MYC Mobile no consume listado, detalle, documentos ni DELETE productivos en su fase LAB actual. | [`../architecture/WORK_ORDER_DELETION.md`](../architecture/WORK_ORDER_DELETION.md), servicio y suites específicas | 2026-08-17 |
| BR-059 | OT LAB temporal | Sólo `lab_work_orders.delete` autoriza eliminar una OT LAB individual en cualquier estado. Se borran OT, equipos, PDF/revisiones/tickets exclusivos y se conserva cualquier hermana, sesión de firma, ticket, revisión o notificación todavía compartida. Al retirar raíz o eslabón intermedio se repara y compacta la cadena dentro de la misma transacción. La app sólo usa `/mobile/v1/technician/lab-work-orders/{id}` y vuelve a consultar el listado tras `204`/`404`. | [`../architecture/LAB_WORK_ORDERS.md`](../architecture/LAB_WORK_ORDERS.md), servicio y suite LAB | 2026-08-17 |
| BR-060 | Comunicaciones | PostgreSQL/REST es la fuente de verdad. Un mensaje obtiene secuencia canónica bajo lock y sólo se publica por WebSocket después del commit; `client_message_id` hace idempotente el reintento por conversación/remitente. | [`../architecture/COMMUNICATIONS_REALTIME.md`](../architecture/COMMUNICATIONS_REALTIME.md), servicio y suite concurrente | 2026-08-17 |
| BR-061 | Comunicaciones / Seguridad | Listar, leer, sincronizar, escribir, recibir typing y actualizar recibos exige membership vigente comprobada en backend. La identidad procede del access JWT revalidado y un ID ajeno no revela contenido. | Router/servicio Communications, realtime y pruebas IDOR | 2026-08-17 |
| BR-062 | Comunicaciones / Menciones | Una mención individual sólo puede dirigirse a un participante; `@todos` o rol exige perfil Administrador, Desarrollador o Calidad y el rol debe existir dentro del grupo. Recibos y cursores por usuario avanzan sin regresión. | Modelo/servicio Communications y pruebas de menciones/recibos | 2026-08-17 |
| BR-063 | Comunicaciones / Push | Realtime y Expo Push son transporte best-effort, nunca autoridad. La notificación se persiste con vista previa sin cuerpo del mensaje, una falla de entrega no revierte dominio y todo deep link vuelve a consultar REST. | Arquitectura Communications, Notifications V1 y provider móvil | 2026-08-17 |
| BR-064 | ETS / Verificación | Verificación reutiliza OT, Equipment, Hoja de Campo, Captura, Calidad, Certificados, autenticación, versiones y liberación. Usa `operational_category=verification`, `calibration_scope=null` y certificado `verification`; `Equipment.service_order_item_id` impide confundirla con Calibración en un ETS mixto. Cada OT conserva el máximo común de 10 equipos. | Servicios de Equipment/Certificados/Captura, frontend ETS y suite de Verificación | 2026-08-24 |
| BR-065 | Verificación / Masters | El Master del concepto de Verificación es una referencia genérica inicial dentro del bonche. Sólo mientras existe inicial y no existe final, el backend puede resolver una coincidencia única por fingerprint contra Masters activos registrados con `service_type=verification` y congelar documento/versión final, actor, origen e historial. Desde entonces ese final es autoridad histórica: cargas y llamadas idempotentes usan el mismo snapshot sin nueva resolución, historial ni auditoría; A→B se rechaza aunque no exista evidencia identificada. Nombre, código, descripción, revisiones y registro institucional vigentes no reinterpretan el equipo. | Equipment, documentos controlados, Captura y Calidad | 2026-08-25 |
| BR-066 | Cotizaciones / ETS | La transición a `accepted` y la materialización del ETS son una sola operación backend transaccional e idempotente. El lock de Cotización y la búsqueda por `quotation_id` garantizan un solo ETS activo; el frontend no ejecuta una creación adicional. | `quotations.py`, `service_orders.py`, schema de Cotización y suite Venta/Cotizaciones | 2026-08-25 |
| BR-067 | Catálogo / Verificación | Crear o actualizar Verificación exige Master genérico `certificate_master` activo, versión activa no caducada y XLSX disponible. El legacy nulo es legible, pero no actualizable ni materializable en un ETS nuevo; reparar requiere sustitución explícita para no reinterpretar snapshots. | `catalog_items.py`, `service_orders.py`, Catálogo y suite de identidad operacional | 2026-08-25 |
| BR-068 | MYC Mobile | `mobile.access` sólo autoriza entrada. Staff conserva RBAC interno y scope vigente; cliente usa una membership activa única, RBAC externo y `client_id` derivado en backend. Claims o payloads no conceden organización. Viewer sólo lee; Jr/Sr operan LAB sin folios. Las rutas productivas no revisadas permanecen deny para cliente. | [`../architecture/MOBILE_SECURITY_CONTEXT.md`](../architecture/MOBILE_SECURITY_CONTEXT.md), contexto/guards Mobile y suites de scope | 2026-08-26 |

## Reglas históricas no vigentes como obligación actual

- Los seguimientos automáticos de Cotización en días 2/4/6 no están implementados y no se consideran regla activa.
- Los folios autónomos de Agenda (`AMYC`) y Llamado (`SMYC`) existen en el generador, pero no hay módulos que los consuman.
- La secuencia histórica estricta `Cotización aceptada → Agenda → Llamado → OT` fue reemplazada en la implementación por hitos y fechas dentro del ETS.
- Un Servicio Compuesto es exclusivamente un concepto comercial: Cotización, PDF e Invoice muestran sólo el padre. Al crear el ETS se expande recursivamente en servicios simples operativos, multiplicando cantidades; éstos alimentan OT, Equipos, Hojas y Certificados. La composición debe usar servicios existentes, cantidad mínima 1, al menos un componente y ningún ciclo o autorreferencia. Evidencia: [`../architecture/COMPOSITE_CATALOG_SERVICES.md`](../architecture/COMPOSITE_CATALOG_SERVICES.md), migración `ff7a8b9c0d1e` y pruebas de integración.
- “Factura timbrada antes de liberar” no describe todos los casos: la regla real depende de `requires_payment` y del estado pagado/saldo.

## Mantenimiento

Una regla nueva debe registrar evidencia y fecha. Si sólo existe en Diseño futuro o Archivo, no puede incorporarse aquí hasta ser confirmada por implementación o decisión explícita.
## Reglas complementarias de Actividad institucional

1. Cada registro admite como máximo un hilo de Actividad.
2. Leer o escribir exige permiso de Actividad y permiso de lectura del módulo.
3. Los comentarios humanos se editan sólo por su autor durante 30 minutos; el
   retiro es lógico y conserva revisión/auditoría.
4. Eventos de sistema y decisiones formales son inmutables e idempotentes.
5. Una atención requiere usuario o área y sólo el asignado/resolutor autorizado
   o moderación puede cerrarla.
6. Notas técnicas, comerciales, fiscales o documentales permanecen en su
   agregado; no se migran a conversación sin clasificación inequívoca.
7. Un adjunto admite máximo 15 MB y debe coincidir en extensión, MIME y firma.
## Reglas de desbloqueo, servicios y folios — 2026-07-29

1. Una cotización aprobada sólo se edita mediante una autorización
   `quotation.controlled_unlock` vigente, asignada al aplicador y ligada a su
   revisión base y `OSMYC-…`.
2. El ETS sólo se elimina físicamente cuando el validador propietario no
   encuentra operación; las OT automáticas `pending` son derivadas
   reconstruibles, pero cualquier OT que avanzó bloquea.
3. La confirmación es atómica: nueva revisión, partidas, eliminación/recreación,
   auditoría y consumo de autorización se confirman o revierten juntos.
4. `service_type` usa `accredited | traceable | linked`;
   `calibration_scope` conserva sus tres claves vigentes.
5. Vinculado exige empresa y prefijo alfanumérico mayúsculo de 2–12
   caracteres. Equipo y certificado usan el snapshot, no el catálogo vivo.
6. Certificados de Calibración usan `{PREFIJO}{AA}{MM}{NNNN}` sin guiones;
   Verificación usa `MYCV-MM-AA-XXXX` y su consecutivo inicia en `0001` cada
   año. Calibración conserva piso 8000 en 2026 y 1000 desde cada año nuevo; OT
   usa 7000 en 2026 y 1000 desde cada año posterior. Ningún contador se
   reinicia por mes y un máximo existente nunca disminuye.
7. Un actor con `authorize_unlock`, `apply_unlock`,
   `rebuild_empty_service_order`, `inspect` y
   `self_authorize_unlock` obtiene el desbloqueo en el mismo comando.
   Administrador satisface esta autoridad mediante `*`: la interfaz ejecuta
   con un solo clic, no presenta modal ni solicita motivo u observación y el
   sistema registra un motivo institucional estándar. El expediente conserva
   solicitante/revisor, vigencia, Actividad, notificación y auditoría de
   autoautorización. Los roles sin esa combinación mantienen la revisión
   segregada y su formulario de solicitud.

## Reglas de Tickets y reapertura móvil — 2026-08-14

1. Una OT LAB cerrada no es editable ni cambia a borrador sin Ticket aprobado.
2. Aprobar crea revisión nueva del grupo sin cambiar folios ni sobrescribir PDF.
3. `preserve` sólo conserva firma mientras no cambien cliente, fechas,
   domicilio, composición o identidad/condición del equipo; el backend invalida
   ante esos cambios aunque el revisor haya solicitado preservar.
4. `signature_required=true` impide cerrar sin una sesión de firma nueva.
5. Los filtros `folio` y `client` son independientes, combinables y se ejecutan
   en base de datos; limpiar uno no altera el otro.

## Reglas de notificaciones móviles V1 — 2026-08-14

1. El push sólo identifica un recurso; `Notification` y la API autenticada son
   la fuente de verdad.
2. `ticket.created` se entrega a usuarios internos activos con permiso efectivo
   `tickets.review`; las demás transiciones notifican al solicitante.
3. `event_key` hace idempotente cada evento/destinatario y `read_at` es la única
   autoridad de lectura y badge.
4. Un usuario sólo lista/lee sus notificaciones y administra sus dispositivos;
   el `user_id` nunca se acepta desde el payload.
5. Una falla de Expo ocurre después del commit y nunca revierte Ticket, OT,
   firma ni notificación persistente. `DeviceNotRegistered` desactiva el token.
6. La app refresca por evento, foreground, foco y mutación local, con
   deduplicación/throttle y pull-to-refresh; se prohíbe polling agresivo.

## Reglas de ETS Venta — 2026-08-18

1. El catálogo configura una Venta nueva; el snapshot de cotización gobierna
   toda operación creada y no se refresca silenciosamente.
2. Una partida identificable crea una `ServiceUnit` por unidad; una partida no
   identificable conserva cantidades agregadas y parciales.
3. Sólo el asesor asignado registra arribos. Una discrepancia contra los datos
   congelados bloquea hasta autorización.
4. Venta nunca habilita evolución genérica. Sólo Servicio General inicia con
   diagnóstico evolutivo; Calibración posterior usa el contrato Venta y exige
   partida aprobada vinculada al ETS/unidad o autorización del mismo ETS.
5. Paquetería y recolección exigen firma PNG/JPEG válida de máximo 250 KiB.
   Entrega técnica admite firma o atestación tipada del técnico asignado; JSON
   arbitrario no es evidencia.
6. Garantía distingue retorno al flujo, reemplazo pendiente y cancelación
   comercial definitiva. Sólo la última descuenta la obligación sin entrega.
   Garantías y revisiones abiertas bloquean el cierre; completar Venta en un
   ETS mixto no cierra partidas de otras categorías.
7. La inicialización histórica es explícita, idempotente, auditada y usa sólo
   el snapshot, nunca el catálogo actual.

## Reglas de herramientas administrativas ETS — 2026-08-25

1. Una cotización aceptada con ETS inactivo no puede materializar otro ETS por
   el flujo ordinario; debe abrir una resolución administrativa.
2. Restaurar, reconstruir y dar de baja son definiciones distintas. Restaurar
   conserva ID, folio, snapshots y partidas; reconstruir sólo procede cuando
   no existe ETS activo ni inactivo; la baja conserva historia y estado de OT.
3. Equipos, certificados, Captura, facturas, firmas/ciclos, ejecución de Venta
   o estado distinto de `scheduled` bloquean el efecto automático.
4. Toda herramienta exige permiso de dominio por etapa, análisis, simulación,
   autorización, revalidación y ejecución durable. El permiso general del
   Centro no sustituye `.propose`, `.authorize` o `.execute`.
5. La reconstrucción usa exclusivamente la cotización aceptada y su snapshot
   congelado; nunca reinterpreta históricos con el catálogo vigente.
