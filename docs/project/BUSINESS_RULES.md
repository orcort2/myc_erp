> Estado: VIGENTE
>
> Tipo: Vigente (canónico)
>
> Autoridad: Alta para reglas funcionales confirmadas
>
> Prevalece sobre: `archive/process/reglas-negocio.md`, reglas de especificaciones V2/V3 y notas cronológicas de `../archive/project/BACKUP_ESTADO_ACTUAL_HISTORICO_2026-07-21.md`
>
> Corte verificado: 2026-07-28

# Reglas de negocio vigentes

Sólo se incluyen reglas verificadas en la implementación o en una decisión vigente. Las reglas históricas no confirmadas quedan fuera de este documento.

| ID | Módulo | Regla vigente | Evidencia principal | Decisión aproximada |
| --- | --- | --- | --- | --- |
| BR-001 | Cotizaciones | El folio usa `MYC-MM-AA-####` y no debe colisionar. | `backend/app/services/quotations.py`, `backend/app/core/folios.py` | 2026-06, confirmada 2026-07 |
| BR-002 | Cotizaciones | Sólo se permiten las transiciones definidas; aceptada, rechazada, expirada y cancelada son terminales. | `backend/app/services/quotations.py` | 2026-06 |
| BR-003 | Cotizaciones | Las partidas congelan datos comerciales/fiscales relevantes y cada guardado puede producir snapshot. | `backend/app/models/quotation.py`, `backend/app/services/quotations.py` | 2026-07 |
| BR-004 | ETS | `service_orders` es la raíz operativa del expediente y debe pertenecer a un cliente activo; una cotización vinculada debe ser coherente con ese cliente. | `backend/app/models/service_order.py`, `backend/app/services/service_orders.py` | V3, vigente 2026-07 |
| BR-005 | ETS | El folio usa `OSMYC-AA-MM-####`; el estado sólo cambia mediante la máquina de transiciones vigente. | `backend/app/services/service_orders.py`, `backend/app/core/folios.py` | 2026-06 |
| BR-006 | OT/Equipos | Una OT agrupa como máximo 10 equipos; las OT usan consecutivo numérico único. | `WORK_ORDER_EQUIPMENT_LIMIT`, `ServiceWorkOrder` | 2026-07 |
| BR-007 | Firmas ETS | Una captura de firmas cubre las OT activas pendientes del ciclo; una OT posterior requiere otro ciclo. | modelos/servicios de ciclos de firma; cierre ETS 2026-07-10 | 2026-07-10 |
| BR-008 | Equipos | Los equipos adicionales fuera de capacidad requieren el tratamiento de excepción definido; los no realizados deben conservar motivo cuando ese estado se use. | servicios ETS/equipos y cierre ETS | 2026-07 |
| BR-009 | Plantillas Maestras/Equipos | Al crear el ETS, cada partida congela el identificador del Master esperado. Al dar de alta el equipo, éste congela documento, versión, ruta, nombre, hash, vigencia y el contexto operativo —alcance, tipo de certificado, Master y partida/origen— sin resolver por nombre ni volver a consultar el catálogo. | modelos/servicios de ETS y Equipos; migración `8c2d4e6f7a9b` | 2026-07-23 |
| BR-010 | Hojas de Campo | La hoja conserva snapshot de plantilla e identidad; una plantilla no debe cambiar retroactivamente una hoja creada. | modelos/servicios de Hojas de Campo | 2026-07-13 |
| BR-011 | Hojas de Campo | No hay fallback silencioso a plantilla General cuando no existe coincidencia segura; la selección debe ser explícita. | integración operativa auditada 2026-07-13 | 2026-07-13 |
| BR-012 | Certificados | Cada certificado se vincula a un equipo y un ETS; su folio depende del tipo: `MYCA`, `MYCV` o `MYCT`. | `backend/app/services/certificates.py`, `backend/app/core/folios.py` | 2026-06/07 |
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
| BR-033 | Motor de Resoluciones | Sólo un expediente listo, con plan autorizado y revalidación exacta, puede ejecutarse. Idempotencia y lock se reservan antes del primer efecto; una respuesta incierta bloquea y no autoriza repetición automática. | [`../architecture/resolution-engine/17_EXECUTION_RUNTIME.md`](../architecture/resolution-engine/17_EXECUTION_RUNTIME.md) y pruebas de Fase 5 | 2026-07-28 |

## Reglas históricas no vigentes como obligación actual

- Los seguimientos automáticos de Cotización en días 2/4/6 no están implementados y no se consideran regla activa.
- Los folios autónomos de Agenda (`AMYC`) y Llamado (`SMYC`) existen en el generador, pero no hay módulos que los consuman.
- La secuencia histórica estricta `Cotización aceptada → Agenda → Llamado → OT` fue reemplazada en la implementación por hitos y fechas dentro del ETS.
- Un Servicio Compuesto es exclusivamente un concepto comercial: Cotización, PDF e Invoice muestran sólo el padre. Al crear el ETS se expande recursivamente en servicios simples operativos, multiplicando cantidades; éstos alimentan OT, Equipos, Hojas y Certificados. La composición debe usar servicios existentes, cantidad mínima 1, al menos un componente y ningún ciclo o autorreferencia. Evidencia: [`../architecture/COMPOSITE_CATALOG_SERVICES.md`](../architecture/COMPOSITE_CATALOG_SERVICES.md), migración `ff7a8b9c0d1e` y pruebas de integración.
- “Factura timbrada antes de liberar” no describe todos los casos: la regla real depende de `requires_payment` y del estado pagado/saldo.

## Mantenimiento

Una regla nueva debe registrar evidencia y fecha. Si sólo existe en Diseño futuro o Archivo, no puede incorporarse aquí hasta ser confirmada por implementación o decisión explícita.
