> Estado: VIGENTE
>
> Tipo: Vigente (canónico)
>
> Autoridad: Alta para reglas funcionales confirmadas
>
> Prevalece sobre: `archive/process/reglas-negocio.md`, reglas de especificaciones V2/V3 y notas cronológicas de `../archive/project/BACKUP_ESTADO_ACTUAL_HISTORICO_2026-07-21.md`
>
> Corte verificado: 2026-08-03

# Reglas de negocio vigentes

Sólo se incluyen reglas verificadas en la implementación o en una decisión vigente. Las reglas históricas no confirmadas quedan fuera de este documento.

| ID | Módulo | Regla vigente | Evidencia principal | Decisión aproximada |
| --- | --- | --- | --- | --- |
| BR-001 | Cotizaciones | El folio usa `MYC-MM-AA-####` y no debe colisionar. | `backend/app/services/quotations.py`, `backend/app/core/folios.py` | 2026-06, confirmada 2026-07 |
| BR-002 | Cotizaciones | Sólo se permiten las transiciones definidas; aceptada, rechazada, expirada y cancelada son terminales. | `backend/app/services/quotations.py` | 2026-06 |
| BR-003 | Cotizaciones | Las partidas congelan datos comerciales/fiscales relevantes y cada guardado puede producir snapshot. | `backend/app/models/quotation.py`, `backend/app/services/quotations.py` | 2026-07 |
| BR-048 | Cotizaciones / ETS | El desbloqueo `quotation.controlled_unlock` permite editar directamente las partidas de una cotización aprobada sólo cuando su ETS pasa el validador integral de virginidad. Compara revisiones, crea snapshots nuevos y reconstruye físicamente el ETS con el mismo `OSMYC-…`; un cambio operativo bloquea sin mutación parcial. | [`../architecture/sales/QUOTATION_CONTROLLED_UNLOCK.md`](../architecture/sales/QUOTATION_CONTROLLED_UNLOCK.md) | 2026-07-29 |
| BR-004 | ETS | `service_orders` es la raíz operativa del expediente y debe pertenecer a un cliente activo; una cotización vinculada debe ser coherente con ese cliente. | `backend/app/models/service_order.py`, `backend/app/services/service_orders.py` | V3, vigente 2026-07 |
| BR-005 | ETS | El folio usa `OSMYC-AA-MM-####`; el estado sólo cambia mediante la máquina de transiciones vigente. | `backend/app/services/service_orders.py`, `backend/app/core/folios.py` | 2026-06 |
| BR-006 | OT/Equipos | Una OT agrupa como máximo 10 equipos; las OT usan consecutivo numérico único. | `WORK_ORDER_EQUIPMENT_LIMIT`, `ServiceWorkOrder` | 2026-07 |
| BR-007 | Firmas ETS | Una captura de firmas cubre las OT activas pendientes del ciclo; una OT posterior requiere otro ciclo. | modelos/servicios de ciclos de firma; cierre ETS 2026-07-10 | 2026-07-10 |
| BR-008 | Equipos | Los equipos adicionales fuera de capacidad requieren el tratamiento de excepción definido; los no realizados deben conservar motivo cuando ese estado se use. | servicios ETS/equipos y cierre ETS | 2026-07 |
| BR-009 | Plantillas Maestras/Equipos | Al crear el ETS, cada partida congela el identificador del Master esperado. Al dar de alta el equipo, éste congela documento, versión, ruta, nombre, hash, vigencia y el contexto operativo —alcance, tipo de certificado, Master y partida/origen— sin resolver por nombre ni volver a consultar el catálogo. | modelos/servicios de ETS y Equipos; migración `8c2d4e6f7a9b` | 2026-07-23 |
| BR-010 | Hojas de Campo | La hoja conserva snapshot de plantilla e identidad; una plantilla no debe cambiar retroactivamente una hoja creada. | modelos/servicios de Hojas de Campo | 2026-07-13 |
| BR-011 | Hojas de Campo | No hay fallback silencioso a plantilla General cuando no existe coincidencia segura; la selección debe ser explícita. | integración operativa auditada 2026-07-13 | 2026-07-13 |
| BR-012 | Certificados | Cada certificado se vincula a un equipo y un ETS; usa `MYCA`/`MYCT` o el prefijo vinculado congelado, seguido por `AAMMNNNN` sin guiones. | `backend/app/services/institutional_folios.py`, arquitectura de folios | 2026-07-29 |
| BR-013 | Calidad | La aprobación del Master XLSX es la única compuerta documental para autenticar. Desde `quality_approved` —o el alias legacy `approved`— Autenticar genera el PDF final desde el Master identificado, lo sella, conserva actor/fecha/auditoría/referencia al Master y pasa a `authenticated`. No exige PDF previo, `final_pdf_path` ni `match_status`; un rechazo de Calidad requiere comentario. | `backend/app/services/certificate_authentication.py`, pruebas de autenticación desde Master | 2026-07-21 |
| BR-014 | Certificados | Calidad es el único autenticador funcional acordado; ETS sólo debe consultar el estado. La duplicación actual es un defecto, no una segunda regla. | auditoría integral 2026-07-21 | 2026-07 |
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
6. Certificados usan `{PREFIJO}{AA}{MM}{NNNN}` sin guiones. En 2026 comienzan
   o continúan desde 8000; desde cada año nuevo, 1000. OT usa 7000 en 2026 y
   1000 desde cada año posterior. Ningún contador se reinicia por mes.
7. Un actor con `authorize_unlock`, `apply_unlock`,
   `rebuild_empty_service_order`, `inspect` y
   `self_authorize_unlock` obtiene el desbloqueo en el mismo comando.
   Administrador satisface esta autoridad mediante `*`: la interfaz ejecuta
   con un solo clic, no presenta modal ni solicita motivo u observación y el
   sistema registra un motivo institucional estándar. El expediente conserva
   solicitante/revisor, vigencia, Actividad, notificación y auditoría de
   autoautorización. Los roles sin esa combinación mantienen la revisión
   segregada y su formulario de solicitud.
