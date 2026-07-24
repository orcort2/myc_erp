> Estado: VIGENTE
>
> Tipo: Vigente (estado operativo)
>
> Autoridad: Media; resumen verificable de operación, migraciones y validaciones
>
> Prevalece sobre: versiones anteriores de este mismo corte operativo
>
> No sustituye a: `project/PROJECT_STATUS.md` para avance ni a `project/DOCUMENTATION_INDEX.md` para jerarquía
>
> Historial anterior: `archive/project/BACKUP_ESTADO_ACTUAL_HISTORICO_2026-07-21.md`
>
> Corte actualizado: 2026-07-24

# Estado operativo actual del ERP MYC

Este archivo contiene únicamente el corte verificable vigente requerido por las reglas operativas del repositorio. La cronología completa fue archivada sin pérdida de información.

## Estado general

- Versión declarada del ERP: `0.4.0`.
- Estado de avance autorizado: [`project/PROJECT_STATUS.md`](project/PROJECT_STATUS.md).
- Único módulo sellado en el corte vigente: Control Documental V1.
- Riesgos bloqueantes actuales: autorización de APIs/registro/tokens/portal, duplicación material en ETS y autenticación de certificados duplicada fuera de Calidad.
- La documentación se mantiene como parte obligatoria de cada cambio según `AGENTS.md` y [`project/DOCUMENTATION_INDEX.md`](project/DOCUMENTATION_INDEX.md).

## Persistencia y migraciones

- Motor: PostgreSQL con SQLAlchemy y Alembic.
- Revisión aplicada y head verificados: `ff7a8b9c0d1e`.
- Cadena Alembic: un único head; no se identificó migración pendiente en el corte auditado.
- Tablas verificadas: 55.
- Catálogos SAT: 16 versiones activas y 151,229 registros en el corte auditado.
- Último respaldo SQL operativo documentado: `backup_erp_myc_antes_prueba.sql`, regenerado y alineado con `ff7a8b9c0d1e`.

La migración `fe6f7a8b9c0d` normalizó `calibration_scope` en catálogo, partidas de cotización/ETS, equipos, interpretaciones y perfiles técnicos. La base local no contenía el texto documental ni `special`; el perfil técnico legacy `accredited` quedó como `accredited_iso_17025`. El respaldo SQL fue regenerado después de aplicar la revisión.

La migración `ff7a8b9c0d1e` agregó `catalog_items.service_kind`, la relación normalizada `catalog_item_components` y el vínculo operativo `service_order_items.catalog_item_id`. Todos los conceptos existentes quedaron como `simple` mediante `server_default`; no se reescribieron cotizaciones ni ETS históricos.

## Validaciones vigentes conocidas

- Suite backend de este corte: 102 pruebas correctas y 7 subpruebas parametrizadas.
- Build frontend de este corte: correcto; permanece advertencia de chunk principal de 859.65 kB.
- `alembic current`: `ff7a8b9c0d1e (head)` verificado el 2026-07-22.
- Gobernanza documental actual: 43 documentos clasificados en la sección Documentación del inventario; los contratos de Calidad, Workbench contextual, acreditación y Servicios Compuestos están incorporados al índice único.
- El generador del inventario fue ejecutado dos veces y produjo el mismo checksum, confirmando regeneración idempotente con preservación de filas revisadas.
- `git diff --check`: correcto.

Estas validaciones tienen fecha de corte 2026-07-21 y no deben presentarse como una ejecución posterior sin volver a correrlas.

## Pendientes actuales prioritarios

1. Cerrar escalación de roles en registro, tipos access/refresh, autorización deny-by-default, aislamiento del portal y secreto JWT seguro.
2. Eliminar duplicación y ruta repetida de firmas en ETS.
3. Mantener a Calidad como único autenticador de certificados.
4. Completar semántica, automatizaciones y E2E de Hojas de Campo/Captura.
5. Cerrar persistencia segura del borrador y flujo fiscal pendiente de Facturación.
6. Alinear roles, permisos, navegación y pruebas 401/403.
7. Resolver deuda vigente de Toolkit, infraestructura, UX y compatibilidad de datos según [`project/TECHNICAL_DEBT.md`](project/TECHNICAL_DEBT.md).

## Documentación y trazabilidad

- Entrada única: [`project/DOCUMENTATION_INDEX.md`](project/DOCUMENTATION_INDEX.md).
- Estado de módulos: [`project/PROJECT_STATUS.md`](project/PROJECT_STATUS.md).
- Observaciones: [`project/OBSERVATIONS_REGISTER.md`](project/OBSERVATIONS_REGISTER.md).
- Deuda técnica: [`project/TECHNICAL_DEBT.md`](project/TECHNICAL_DEBT.md).
- Bitácora histórica completa: [`archive/project/BACKUP_ESTADO_ACTUAL_HISTORICO_2026-07-21.md`](archive/project/BACKUP_ESTADO_ACTUAL_HISTORICO_2026-07-21.md).

## Actualización de esta tarea

- Servicios Compuestos implementados con tabla padre-hijo normalizada, cantidades enteras y validaciones de servicio activo, mínimo, duplicado, autorreferencia y ciclos. No se usaron JSON ni componentes duplicados en la cotización.
- Cotización y Facturación conservan un único concepto comercial. La creación canónica del ETS expande recursivamente sólo las hojas simples, conserva `quotation_item_id`, registra el `catalog_item_id` operativo y reutiliza el conteo vigente de OTs, Equipos, Hojas y Certificados.
- El Catálogo embebido permite seleccionar Servicio Simple/Compuesto, administrar componentes y cantidades y visualizar la composición; la importación existente continúa creando conceptos simples.
- Migración aplicada: `ff7a8b9c0d1e (head)`. Respaldo `backup_erp_myc_antes_prueba.sql` regenerado, 74,039,801 bytes, SHA-256 `165687bd0be9a6276494f8c395ebe4714b139d4f9528b7c9a9b2f9df9a286600`; su `alembic_version` es `ff7a8b9c0d1e`.
- Validaciones: 14 pruebas focalizadas correctas; suite `unittest discover` completa de 88 pruebas correcta; build Vite correcto con 1,664 módulos. Permanece la advertencia conocida por chunk principal de 871.51 kB.
- `alembic check` confirmó que las tablas y columnas de Servicios Compuestos están aplicadas, pero continúa fallando por deriva histórica ajena a esta migración en índices, constraints y columnas legacy. Se registró como `TD-021`; no se generó una migración masiva automática.

- Se completó una auditoría estática y no mutante de 60 escenarios de excepción en todos los módulos solicitados. El entregable está en `docs/auditorias/AUDITORIA_MATRIZ_EXCEPCIONES_ERP_MYC.md` y contiene matriz de 25 columnas, catálogo, dependencias, diseño futuro, preguntas, fases y archivos revisados.
- Hallazgo central: `register_service_order_exception` no representa todavía una aprobación controlada; modifica el estado ETS y resincroniza borradores durante la solicitud. Se documentó como P0 la separación obligatoria entre `requested`, `approved` y `executed`, sin implementar motor ni cambiar estados.
- Esta tarea sólo modificó documentación e inventario. No cambió código, esquema, configuración, pruebas ni datos; no se ejecutaron migraciones y no corresponde regenerar `backup_erp_myc_antes_prueba.sql`. El head operativo permanece `fe6f7a8b9c0d` según el corte superior vigente.
- Validación documental: 60 filas y 25 columnas funcionales verificadas; clasificación total reconciliada; evidencias principales contrastadas con rutas existentes; generador del registro y `git diff --check` ejecutados al cierre.

- Se corrigió el HTTP 500 de `GET /api/catalog-items?is_active=true`: el schema esperaba por error el texto documental `Certificado / Certificate: L25-313` mientras PostgreSQL conservaba `accredited_iso_17025`.
- `backend/app/schemas/service_scope.py` centraliza `accredited_iso_17025`, `traceable` y `accredited_linked_lab`; catálogo, cotización, ETS, equipos, perfiles técnicos e interpretaciones consumen el mismo contrato. La validación del catálogo además restringe cada alcance a su categoría de servicio.
- La capacidad y creación de equipos conservan la detección automática vigente. El mapeo certificado es `accredited_iso_17025→acreditado`, `traceable→trazable` y `accredited_linked_lab→vinculado`; no se añadió una selección manual libre.
- La migración `fe6f7a8b9c0d` normaliza alias legacy y contenido documental en seis tablas. Si encuentra `special`, falla expresamente para impedir una reclasificación de negocio inventada.
- Validación focalizada: 14 pruebas y 19 subpruebas correctas; el endpoint real mediante `TestClient` respondió `200` con un registro; las seis tablas quedaron sin alias documentales/legacy y `technical_profiles` conserva un registro como `accredited_iso_17025`.
- Suite backend completa: 110 pruebas correctas y 19 subpruebas; sólo fallaron las dos pruebas de conversión real ya conocidas por `LibreOffice returncode=-6`, sin relación con `calibration_scope`. Build Vite final correcto con 1,664 módulos y la advertencia conocida del chunk principal de 867.49 kB.
- Alembic quedó en un único head `fe6f7a8b9c0d`; `backup_erp_myc_antes_prueba.sql` se regeneró después de la migración y fue validado con tamaño no vacío de 71 MB.

- Sprint 2A de Facturación implementado: la pestaña del ETS muestra el `Invoice` contextual para ausencia, borrador, timbrada y cancelada, con folio, UUID, fecha e importe sólo cuando existen.
- Corrección UX de Sprint 2A: `contextLoading/contextResolved` distinguen contexto pendiente, ausencia resuelta y factura real; durante la consulta sólo existe un bloque estable de carga, sin badge ni acciones provisionales. La pestaña permanece montada al alternar carpetas del mismo ETS y reinicia el contexto únicamente al abrir otro expediente.
- `EtsBillingTab.jsx` consume `useInvoiceWorkbenchController` con carga contextual sin overview y monta el mismo `InvoiceWorkbenchDialog`; cerrar conserva el mismo ETS y guardar/emitir actualiza inmediatamente la tarjeta con la respuesta persistida.
- Crear/continuar/ver, PDF MYC y XML reutilizan el controlador del Sprint 1. No se agregaron endpoints, reglas, estados, agregado, modal, pantalla ni controlador paralelo.
- Pagos, cuentas por cobrar, notas de crédito, historial/documentos y liberación financiera permanecen fuera de Sprint 2A y sólo muestran “Disponible en la siguiente fase”.
- Validación: build Vite correcto con 1,664 módulos; 11 pruebas Node correctas para carga no resuelta, ausencia, borrador, timbrada, cancelada y navegación; render SSR inicial sin “Sin factura”/“Crear factura”/badge; y 8 pruebas backend focalizadas correctas para listado filtrado y documentos. Continúa la advertencia conocida por chunk principal de 867.50 kB. La sesión local de navegador sólo presentó Login, por lo que no se usaron credenciales ni se alteraron datos para fabricar escenarios visuales.
- No hubo migración ni cambio de datos; no corresponde regenerar `backup_erp_myc_antes_prueba.sql`. Alembic permanece documentado en `fd5e6f7a8b9c` como último head verificado.

- El Paquete de Captura acepta hojas `completed`, `under_review` y `approved`; el ZIP conserva `FOLIO_ETS/OT-####/FOLIO_CERTIFICADO/` y nombres institucionales por folio.
- La carga asigna ruta única, persiste validaciones, inicia `capture_in_progress` con actor/auditoría, ignora auxiliares macOS y refresca ETS, archivos, contadores y tarjetas sin recarga manual.
- Captura→Calidad usa exclusivamente el Master XLSX en esta etapa: no muestra carga/contadores/etiquetas PDF. Readiness exige Master esperado+identificado y cero `mismatch`/`no_coincide`; `no_encontrado` es advertencia permitida.
- `send_to_quality` persiste `capture_in_progress → quality_review`, actor, fecha e ID/nombre del Master. Calidad consulta alertas/diferencias, descarga el XLSX y puede aprobarlo o regresarlo sin exigir PDF ni modificar `match_status`.
- Caso actual: certificado `1` en `capture_in_progress`, Master identificado `8`, tres advertencias, cero diferencias, readiness `true`; archivo `capture/1/8-Master_MYCA-07-2026-0001.xlsx` existente con 210,173 bytes.
- Verificación HTTP autenticada: `GET /api/certificates/capture-master-readiness?service_order_id=1` respondió `200` con un certificado listo, un Master identificado, tres advertencias y cero diferencias; `GET /api/certificates/1/capture-master` respondió `200`, MIME XLSX, nombre institucional y 210,173 bytes.
- El envío se verificó en transacción reversible: actor `1`, fecha, `certificate.sent_to_quality`, referencia al Master, estado temporal `quality_review` y `match_status=pending`; el rollback dejó el registro histórico intacto.
- Los registros históricos conservan sus tres advertencias. El parser vigente reclasificó el mismo archivo sin persistir cambios: `servicio` esperado/detectado `accredited`, score `0.8511`, cinco grupos estructurales; quedan sólo las advertencias de cliente y próxima calibración, fuera de este alcance.
- La detección usa nombres de hojas, dimensiones, fusiones, estilos, fórmulas, etiquetas posicionadas, imágenes y áreas de impresión contra el snapshot registrado. No busca la clave ERP, la frase “Acreditación” ni el número `88795`.
- Se diagnosticó el falso bloqueo del ETS: la API real devolvía certificado `1` en `capture_in_progress`, Master `10` identificado, cero mismatches y `ready=true`, pero la vista exigía localmente `certificate_template_path_snapshot`, campo ausente de `EquipmentRead`. ETS ahora consulta y refresca el readiness backend por `service_order_id`; el frontend servido incorpora la corrección.
- Se corrigió Calidad→Autenticación en frontend y backend. La interfaz y el servicio dejaron de exigir `final_pdf_path`/PDF previo/`match_status`; desde `quality_approved` o el alias `approved`, la acción toma el Master identificado más reciente, genera el PDF final, aplica el autenticador vigente y persiste actor, fecha, versión, auditoría y referencia al Master antes de pasar a `authenticated`.
- El caso real se recorrió por HTTP en una transacción reversible: enviar a Calidad, aprobar y autenticar devolvieron `200`; la descarga del PDF autenticado devolvió `200 application/pdf`, 310,443 bytes y tres páginas. El PDF final intermedio tuvo 188,349 bytes y tres páginas, excluyó la hoja auxiliar y `match_status` permaneció `pending`. El rollback restituyó el certificado `1` a `capture_in_progress` sin rutas y no dejó archivos históricos alterados.
- LibreOffice ahora se resuelve por `LIBREOFFICE_EXECUTABLE` —con alias legacy `OFFICE_CONVERTER_BINARY`—, `soffice`/`libreoffice` en `PATH` y rutas comunes de macOS, Windows y Linux. Doctor y startup reportan disponibilidad, ruta y versión; los errores técnicos se registran sin exponer stdout/stderr al frontend.
- En el macOS actual se instaló LibreOffice estable `26.2.4.2` en `/Applications/LibreOffice.app/Contents/MacOS/soffice` y `backend/.env` configura esa ruta explícitamente. Doctor la reporta como `configured_path`; el endpoint real de prueba produjo HTTP 200 y PDFs válidos. Una prueba negativa demostró que el fallo de conversión conserva `quality_approved`, rutas vacías y ausencia de auditoría/actor.
- Se retiró `match_status` de las compuertas de liberación individual/masiva y de las tarjetas Certificados/ETS. `authenticated` más PDF autenticado real define readiness documental; la UI muestra “Listo para liberar”, “Pendiente de pago” o “Liberado”, y conserva el matching sólo como dato histórico/auditable.
- El endpoint de liberación devuelve códigos específicos `certificate_not_authenticated`, `authenticated_document_missing`, `payment_pending` y `already_released`. La prueba HTTP liberó con `match_status=pending`, conservó el PDF, actor, fecha y auditoría; las pruebas de pago pendiente mantuvieron `authenticated` sin visibilidad al cliente.
- Consulta real no mutante: certificado `2` (`MYCA-07-2026-0002`) está `authenticated`, conserva `match_status=pending` y su PDF autenticado existe. El ETS `2` requiere pago y no tiene factura liquidada, por lo que el único bloqueo vigente es financiero (`payment_status=pending`), no documental ni de match.
- Se corrigió la presentación del ETS sin modificar reglas: Facturación sigue el flujo inmediatamente después de Certificados y Documentos/Notas/Historial cierran la navegación. El aviso financiero de Certificados quedó separado del título mediante un contenedor vertical responsivo, conservando Liquid Glass y sin posicionamiento absoluto.
- La presentación derivada de liberación se centralizó para tarjetas, agrupaciones por OT y pestaña: un autenticado bloqueado muestra `Pendiente de pago` y “Certificado autenticado. Pendiente de liberación por pago.”; con pago cubierto muestra `Listo para liberar`. El estado propio del certificado permanece `Autenticado`.
- Los botones de autenticación de Calidad usan `table-button table-button--primary`, el mismo contrato compartido que las acciones principales, con `disabled` nativo y sin estilos inline ni clase visual exclusiva; la superficie principal ya cumplía y se alineó la acción contextual del ETS.
- La observación UX permanece `parcial`, no `resuelta`, hasta ejecutar la comprobación visual autenticada en varios anchos; estructura, CSS y build sí quedaron verificados.
- Calidad incorporó navegación secuencial dentro del mismo modal reutilizando el encabezado/navegador de Clientes. La frontera se congela al abrir por OT, con fallback a ETS/lista visible; no hay ciclo, las flechas se bloquean durante carga/acciones y un fallo conserva el último certificado válido con Reintentar.
- Aprobar, regresar a Captura y autenticar ya no cierran el modal de Calidad: refrescan certificado, audit logs, readiness, lista y contadores conservando la posición contextual. Durante navegación la ficha anterior se oculta para impedir mezcla de folio, equipo, Master, estado o acciones.
- Validaciones: derivación de estados ejecutada directamente para pago pendiente y cubierto; navegación determinista `1→2→3→2`, límites y contexto OT verificados; build frontend correcto con 1,660 módulos y chunk principal de 859.65 kB. La base local devolvió cero certificados en estados visibles de Calidad y la sesión del navegador sólo presentó Login, por lo que no se alteraron datos para fabricar un E2E. La suite backend vigente continúa en 102 pruebas y 7 subpruebas correctas. No hubo migración ni cambio persistente de datos; no corresponde regenerar el respaldo SQL.
- Sprint 1 de Facturación extrajo de `BillingPage.jsx` el controlador único `useInvoiceWorkbenchController.js`. Apertura, carga, borrador, actualización, emisión, PDF MYC, XML, configuración, refresco, errores y estados de carga conservan los mismos endpoints y reglas sobre `Invoice`; la página quedó como composición del centro global.
- El contexto de apertura dejó de usar `myc_billing_order_id` en `localStorage`. `invoiceWorkbenchContext.js` admite `invoice_id` o `service_order_id` en URL, el listado existente acepta filtro opcional por ETS y el botón histórico del ETS conserva su navegación sin implementar todavía la nueva pestaña.
- Validación del Sprint 1: build Vite correcto con 1,662 módulos; 3 pruebas Node correctas para el contrato de contexto y 2 recorridos adicionales de navegación secuencial; apertura contextual revisada bajo el doble ciclo de efectos de `React.StrictMode`; 10 pruebas backend focalizadas correctas para filtro de facturas, mapper Facturama y documentos. La suite completa obtuvo 102 correctas y 2 fallos ajenos al Sprint porque LibreOffice terminó con `returncode=-6` en las dos pruebas que ejecutan conversión real; no falló ninguna prueba de Facturación. Permanece la advertencia conocida del chunk principal (862.88 kB). No hubo migración ni cambio de datos, por lo que no corresponde regenerar el respaldo SQL.

## Motor de Resoluciones — Fase 1

- Estado: Fase 0 `APROBADA`; Fase 1 `EN REVISIÓN`; Fase 2 `NO INICIADA`.
- La fundación reside en `backend/app/resolution_engine/` y no importa modelos,
  schemas, servicios, routers, FastAPI ni SQLAlchemy.
- `ResolutionDefinition` conserva tipo, versión y referencias versionadas a los
  componentes requeridos. `ResolutionRegistry` admite varias versiones, una
  activa por tipo, resolución histórica exacta y congelamiento.
- La serialización/hash canónicos rechaza datos ambiguos; reloj e IDs técnicos
  son inyectables. Los UUID no generan ni sustituyen folios institucionales.
- No se incorporaron persistencia, lifecycle, seguridad, gateways, API,
  workers, resoluciones concretas ni ejecución.
- Validaciones: 171 pruebas backend y 19 subpruebas correctas; 11 pruebas
  frontend correctas; build Vite correcto; importación con `app.main` correcta;
  único head/current `8c2d4e6f7a9b`.
- Cierre detallado:
  [`closures/RESOLUTION_ENGINE_PHASE_1.md`](closures/RESOLUTION_ENGINE_PHASE_1.md).
