> Estado: VALIDACIÓN TERMINADA — PENDIENTE DE APROBACIÓN INSTITUCIONAL
>
> Fecha de corte: 2026-08-04
>
> Tipo: auditoría funcional documental previa a ETAPA 3
>
> Efecto: no modifica código, permisos, modelos, migraciones, workflows, RBAC, Ajustes, PortalMembership ni Tickets

# Validación funcional del Catálogo Institucional de Capacidades

## 1. Dictamen ejecutivo

El catálogo técnico de ETAPA 2B fue recorrido completo: **36 módulos/superficies,
213 agrupaciones y 798 filas**, compuestas por **305 operaciones HTTP existentes
y 493 campos de schemas**. Era un snapshot reproducible útil para reconciliar
código, pero todavía no podía ser la autoridad funcional de largo plazo porque:

1. convertía campos de entrada y de respuesta en permisos potenciales;
2. usaba nombres de endpoints como intención de negocio;
3. mezclaba módulos, canales, subdominios y servicios técnicos;
4. omitía unidades objetivo sin endpoints actuales —Dashboard, CRM, Agenda,
   Llamados, Archivos y Cargas, Calidad autónoma, Reportes y Encuestas—;
5. concentraba capacidades distintas bajo permisos amplios y proponía claves
   distintas para operaciones que debían compartir una intención.

La revisión produjo
[`CATALOGO_INSTITUCIONAL_FUNCIONAL_ERP_MYC.md`](../architecture/CATALOGO_INSTITUCIONAL_FUNCIONAL_ERP_MYC.md),
con **42 módulos funcionales, 181 acciones y 657 microacciones explícitas**. El
catálogo funcional representa tanto el ERP implementado como el ERP objetivo y
distingue capacidades existentes/parciales, objetivo y reservadas. Está listo
para aprobación, pero ninguna propuesta cambia todavía el bootstrap ni la
ejecución.

### Resultado por entregable

| Entregable | Resultado |
| --- | --- |
| Dictamen funcional | Este documento, secciones 1–8. |
| Catálogo funcional objetivo | Documento canónico propuesto con 42/181/657. |
| Matriz ERP actual vs ERP objetivo | Sección 4, con las 36 superficies originales y los módulos descubiertos. |
| Nuevas microacciones | Sección 6 y catálogo detallado; el catálogo es la lista exhaustiva. |
| Microacciones eliminadas | Sección 5.1; conjunto exacto y reproducible de 493 filas sintéticas, más operaciones técnicas no delegables. |
| Microacciones renombradas/reagrupadas | Secciones 5.2–5.4. |
| Permisos nuevos propuestos | Sección 7 y columna normativa del catálogo funcional. |

## 2. Método y fuentes

Se contrastaron:

- catálogo técnico y validador de ETAPA 2B;
- `permissions.py` y su inventario documental, **sin modificarlos**;
- los 36 routers, servicios y schemas vigentes;
- navegación y superficies frontend;
- canon de alcance, estado, flujo, reglas, decisiones, observaciones y deuda;
- contratos de Facturación, Servicios Compuestos, acreditación, Hojas de Campo,
  Actividad y Motor de Resoluciones;
- especificaciones históricas únicamente para descubrir intención objetivo. Lo
  histórico no se convirtió automáticamente en alcance: se marcó `R` cuando no
  existe ratificación implementada.

Cada fila se evaluó con estas preguntas: intención de negocio, unidad funcional,
duplicación, pertenencia, amplitud, sensibilidad, estado/ownership, necesidad
de permiso y reserva futura. La mera existencia de un endpoint o campo no fue
evidencia suficiente de capacidad institucional.

## 3. Conteo y disposición

| Métrica | Snapshot técnico | Catálogo funcional | Interpretación |
| --- | ---: | ---: | --- |
| Módulos/superficies | 36 | 42 | Se añadieron unidades objetivo y se fusionaron superficies técnicas. |
| Acciones | 213 | 181 | CRUD/HTTP repetido fue reemplazado por intenciones de negocio. |
| Microacciones | 798 | 657 | Se retiró granularidad de schemas y se añadieron capacidades objetivo reales. |
| Filas HTTP existentes | 305 | No se usa como categoría funcional | Sus comportamientos se conservaron, fusionaron o reclasificaron. |
| Filas de campo | 493 | 0 como permisos de campo automáticos | La sensibilidad se gobierna en la acción de negocio correspondiente. |
| Claves propuestas únicas del snapshot | 658 | No se aprueban en bloque | Sólo sobreviven las justificadas en el catálogo funcional. |
| Permisos bootstrap actuales | 140 | 140 sin cambios | No se renombró, eliminó ni agregó ninguna clave en código. |

La reducción neta de 141 filas no significa pérdida de función. Las 493 filas
sintéticas se retiraron y las operaciones HTTP repetidas se compactaron; a la
vez se incorporaron microacciones de negocio inexistentes o implícitas. No es
correcto calcular “nuevas” por simple resta porque varias filas técnicas se
fusionaron en una acción y otras se dividieron en varias decisiones.

## 4. Matriz ERP implementado vs ERP institucional objetivo

### 4.1. Revisión de las 36 superficies originales

| Superficie ETAPA 2B | ERP implementado verificable | ERP institucional objetivo | Dictamen |
| --- | --- | --- | --- |
| API pública del Motor | Crear, listar, consultar resolución, capacidades y portal técnico. | Canal versionado con consumidores, scopes, credenciales y compatibilidad; no copia el Centro interno. | **Renombrada y completada** como M40. |
| Actividad | Conversación contextual, adjuntos, menciones, atención y lecturas. | Separar mensaje, adjunto, mención, atención y moderación; eventos automáticos sin permiso propio. | **Dividida funcionalmente** en M06.A01–A07. |
| Ajustes · Identidad institucional | Consulta y actualización institucional. | Identidad, parámetros, folios, catálogos maestros y módulos, con capacidades críticas separadas. | **Ampliada** en M04. |
| Auditoría | Consulta de logs. | Consulta, filtros, detalle, exportación y revisión institucional. | **Completada** en M05. |
| Autenticación | Login, refresh, registro y sesión actual. | Identidad/sesiones como capacidad base; recuperación, MFA y revocación reservadas, no CRUD asignable. | **Reclasificada** en M02. |
| Catálogo de servicios | CRUD, vinculadas, clasificación y campos comerciales. | Catálogo MYC simple/compuesto, clasificación metrológica y gobierno económico. | **Renombrada y reagrupada** en M10. |
| Catálogos SAT | Búsqueda, versiones, favoritos y alias. | Separar fuente oficial institucional de preferencias propias. | **Dividida** en M36.A01–A03. |
| Certificados | Expediente, generación, captura, revisión, autenticación y liberación mezclados. | Captura, Calidad y Certificados tienen ownership funcional distinto; verificación es canal público. | **Dividida** entre M21, M22 y M23. |
| Certificados de patrones | CRUD, documento, aprobación y campos extraídos. | Evidencia de vigencia con lifecycle explícito y sin permisos por campo. | **Normalizada** en M28. |
| Clientes | Cuenta, fiscal, contactos, documentos, archivo/import/export. | Conservar Cliente como unidad; Contactos es subdominio hasta decisión autónoma. | **Reagrupada** en M09. |
| Comunicaciones | Conversaciones y mensajes. | Bandejas internas junto con Notificaciones, sin mezclarlas con Actividad contextual. | **Fusionada** en M07. |
| Control documental | Lista Maestra, ficha, versiones, publicación y archivo. | Mantener V1 sellado y reservar MDE fuera de V1. | **Conservada** en M24. |
| Cotizaciones | CRUD, estados, envío, revisiones y campos. | Propuesta, emisión, decisión cliente, ETS y excepciones gobernadas. | **Reagrupada y ampliada** en M11. |
| ETS y órdenes de trabajo | Expediente, OTs, firmas, estados, llamado, pagos, certificados y excepciones. | ETS, OTs y Firmas son unidades separadas; contexto no transfiere ownership. | **Dividida** en M14, M15 y M17. |
| Equipos | CRUD, estado y campos técnicos. | Ocurrencia del ETS; identidad transversal de activo reservada. | **Conservada y ampliada** en M16. |
| Facturación y pagos | Borradores, emisión, PAC, pagos, cartera y notas. | Facturación fiscal separada de Pagos/Cartera/Notas; cada mutación sensible es independiente. | **Dividida** en M34 y M35. |
| Hojas de Campo | CRUD, completar, revisar, firmas y 44 campos. | Crear, capturar, completar, revisar y retirar; cálculo/snapshot como efectos automáticos. | **Normalizada** en M18. |
| Incertidumbre | Modelos, versiones, cálculo, excepción y 35 campos. | Administrar modelos, lifecycle, ejecutar y autorizar excepción. | **Normalizada** en M33. |
| Integraciones | Estado de Facturama. | Estado, configuración, credenciales, prueba, reintento y conciliación por conector; Drive reservado. | **Ampliada** en M37. |
| Interpretaciones documentales | CRUD y versiones. | Interpretación semántica con documento fuente y aprobación. | **Completada** en M26. |
| Metrología | Resolver/ejecutar cálculo. | Ejecución explicable, versionada y con evidencia automática. | **Conservada** en M31. |
| Motores operativos | Endpoints técnicos de resolución/captura/certificados. | Infraestructura interna de Metrología; no módulo visible ni permiso genérico por cada endpoint. | **Fusionada** en M31. |
| Módulos del sistema | Consulta de metadata de módulos. | Configuración de visibilidad/navegación bajo Ajustes. | **Absorbida** por M04.A05. |
| Notificaciones | Listado, creación técnica y lectura. | Bandeja propia en Comunicaciones; la creación automática no se delega. | **Fusionada** en M07. |
| Patrones de referencia | CRUD, estado, incertidumbre y campos. | Inventario, vigencia, disponibilidad y excepción. | **Normalizada** en M27. |
| Perfiles técnicos | CRUD, versiones y aprobación. | Reglas versionadas aplicables y resolución de perfil. | **Conservada** en M30. |
| Plantillas de Hojas de Campo | CRUD, duplicar, importar/exportar, activar y campos. | Diseño, versionado/publicación e intercambio. | **Normalizada** en M19. |
| Plantillas documentales | Configuración, restauración y campos de identidad. | Masters XLSX versionados con fingerprint y vigencia. | **Renombrada** como M25. |
| Portal cliente | Listados/descargas propias mediante vínculo transitorio. | Autoservicio con membership persistente, múltiples vínculos y ownership auditable. | **Conservada y reservada** en M38. |
| Procedimientos de calibración | CRUD, versiones, estado y 15 campos. | Método técnico versionado, aprobado y archivado. | **Normalizada** en M29. |
| Selección de patrones | Obtener candidatos y seleccionar. | Resolver/explicar selección y gobernar excepciones. | **Completada** en M32. |
| Sistema y salud | Health check público. | Operación técnica: readiness, jobs, storage, backup y soporte; no módulo ordinario. | **Reclasificada** en M42. |
| Tickets · Centro de Resoluciones | Flujo guiado completo del Motor. | Resolución institucional, no “ticket” genérico; conserva lifecycle único. | **Renombrada** como M39. |
| Tickets · Excepciones de cotización | Solicitud, preview, revisión y aplicación. | Acción contextual dentro de Cotizaciones y, cuando corresponda, Centro. | **Absorbida** por M11.A07–A08. |
| Usuarios y accesos | Usuario, estado y roles estáticos. | Usuario, roles, capacidades, scopes, overrides, vigencia y explicación efectiva. | **Dividida y ampliada** en M03. |
| Verificación pública de certificados | Verificación por código. | Canal público minimizado del Certificado, sin permiso interno ficticio. | **Absorbida** por M23.A04. |

### 4.2. Módulos o unidades descubiertas

| Unidad | Evidencia actual | Objetivo | Tratamiento |
| --- | --- | --- | --- |
| Dashboard | Pantalla y agregados existentes. | Panorama autorizado, alertas y trabajo propio. | M01, implementación parcial. |
| CRM/Leads | Sin implementación. | Prospección, conversión y seguimiento. | M08, reservado. |
| Agenda | Campos dentro del ETS. | Programación y reprogramación autónomas. | M12, reservado. |
| Llamados | Hito/transición dentro del ETS. | Seguimiento previo autónomo. | M13, reservado. |
| Órdenes de trabajo | Modelo y emisión dentro de ETS. | Unidad operativa con organización y documento propios. | M15, separada. |
| Firmas | Ciclos/OT existentes y endpoint duplicado. | Conformidad con lifecycle y reapertura gobernada. | M17, separada. |
| Archivos y Cargas | Storage y cargas dispersas por dominio. | Contrato transversal para ETAPA 3. | M20, objetivo; no implementado aquí. |
| Captura | Pantalla, paquetes y retornos existentes. | Bandeja, preparación, retorno, resolución y envío a Calidad. | M21, separada. |
| Calidad | Pantalla y flujo existentes bajo Certificados/ETS. | Único dueño de revisión y autenticación. | M22, separada. |
| Reportes/Encuestas/Cierre | Sin implementación funcional. | Medición posterior y cierre comercial. | M41, reservado. |

## 5. Listado de eliminaciones, renombres, fusiones y divisiones

### 5.1. Microacciones eliminadas del plano institucional

El conjunto eliminado es **exacto y reproducible**, no una muestra:

1. Las **493 filas** del snapshot técnico cuyo Estado es
   `Requiere granularización`. Son todas las filas bajo “Editar campos y
   atributos”, “Gestionar identidad fiscal y legal”, “Redefinir clasificación y
   alcance”, “Redefinir condiciones económicas”, “Gestionar acceso y seguridad”
   y equivalentes. Permanecen como datos/validaciones, pero dejan de ser
   microacciones o permisos independientes.
2. `Health check` y `Verification` dejan de ser permisos institucionales
   asignables. Continúan como canales con políticas públicas/técnicas.
3. `Login`, `Refresh`, `Me` y `Registration status` dejan de modelarse como
   `auth.create/read`. Son operaciones base de identidad/sesión.
4. Lecturas técnicas repetidas (`Capabilities`, `Definitions`, endpoints de
   estado y previews) dejan de ser capacidades independientes cuando sólo
   materializan una acción ya autorizada.

No se eliminó del ERP ninguna función implementada. Se retiró únicamente su
clasificación incorrecta como capacidad delegable.

### 5.2. Microacciones renombradas

| Nombre técnico anterior | Nombre funcional adoptado | Ubicación |
| --- | --- | --- |
| `Resolution` | Crear/consultar resolución | M39 o M40 según canal. |
| `Entity read` | Marcar conversación contextual como leída | M06.A01. |
| `Message` | Crear, editar o eliminar mensaje | M06.A02. |
| `Attachment` | Adjuntar, previsualizar, descargar o retirar adjunto | M06.A03. |
| `Attention` / `Attention resolve` | Solicitar o resolver atención | M06.A05–A06. |
| `Configuration` | Consultar/editar identidad institucional | M04.A01. |
| `Catalog item` | Servicio simple o compuesto del Catálogo MYC | M10.A02–A03. |
| `Linked company` | Administrar empresa vinculada | M10.A04. |
| `Quotation` | Crear/editar cotización | M11.A02–A03. |
| `Send` | Emitir y enviar propuesta | M11.A04. |
| `Accept/Reject/Cancel/Expire` | Resolver decisión del cliente | M11.A05. |
| `Service order` | Crear/consultar ETS | M14.A01–A02. |
| `Confirm/Start/Call/Close` | Transicionar operación del ETS | M14.A03. |
| `Work orders PDFs` | Emitir OT individual o lote | M15.A03. |
| `Equipment status` | Transicionar estado del equipo | M16.A03. |
| `Field sheet complete/review` | Completar/revisar Hoja de Campo | M18.A04–A05. |
| `Package/return/readiness` | Preparar paquete/recibir retorno/enviar a Calidad | M21.A02–A05. |
| `Approve` de certificado | Aprobar contenido o autenticar, según etapa | M22.A02–A03. |
| `Release` | Liberar certificado/expediente con compuertas | M23.A03 y M14.A06. |
| `Invoice issue/recover/reconcile` | Emitir, recuperar o conciliar CFDI | M34.A04. |
| `Payment` | Registrar/aplicar pago y emitir recibo | M35.A02. |
| `Credit note` | Administrar nota administrativa o fiscal | M35.A06. |
| `Execute` metrológico | Ejecutar cálculo explicable | M31.A01/M33.A04. |
| `User admin` | Administrar identidad de usuario | M03.A02. |
| `User roles` | Asignar o retirar autoridades | M03.A05. |

La tabla registra los cambios semánticos; el catálogo funcional contiene la
lista completa de los 657 nombres adoptados. Ninguna clave actual se renombró.

### 5.3. Acciones fusionadas

| Orígenes | Acción/unidad resultante | Razón |
| --- | --- | --- |
| Comunicaciones + Notificaciones | M07 | Una bandeja/canal, sin invadir Actividad contextual. |
| Motores operativos + Metrología | M31 | Los motores son infraestructura de cálculo, no módulo de negocio. |
| Módulos del sistema + Ajustes | M04.A05 | La metadata sirve a configuración/navegación. |
| Tickets de excepción + Cotizaciones | M11.A07–A08 | La intención nace y termina en la cotización; el Motor puede ejecutarla. |
| Verificación pública + Certificados | M23.A04 | Es un canal del certificado, no un módulo administrativo. |
| Plantillas documentales + Masters | M25 | La intención real es gobernar Masters versionados. |

### 5.4. Acciones divididas

| Acción amplia anterior | División aprobada |
| --- | --- |
| ETS y órdenes de trabajo | ETS M14; OTs M15; Firmas M17; Equipo M16. |
| Certificados | Captura M21; Calidad M22; Certificados/liberación M23. |
| Facturación y pagos | Facturación fiscal M34; pagos/cartera/notas M35. |
| `invoices.manage` | Borrador, validar, emitir, conciliar, cancelar/sustituir y PPD/complementos. |
| `payments.manage` | Registrar, aplicar, reversar, reasignar, conciliar y administrar notas. |
| `users.manage` | Identidad, estado, credenciales, roles, overrides y grants. |
| `service_orders.update` | Contexto, transiciones, OTs, equipos, firmas y excepciones. |
| `activity.messages.manage` del snapshot | Crear, editar propio, retirar propio, eliminar propio y moderar. |

## 6. Nuevas microacciones propuestas

La lista exhaustiva son las **657 microacciones** de la columna
“Microacciones funcionales” del catálogo; cada una tiene ID de acción estable.
Las adiciones que no podían aparecer en un inventario de endpoints se agrupan
así:

| Área | Microacciones nuevas principales |
| --- | --- |
| Dashboard | Alertas autorizadas, trabajo propio y preferencias. |
| Sesiones | Revocar sesiones propias; recuperación y MFA reservados. |
| Gobierno de acceso | CRUD de roles, protección, scopes, overrides allow/deny, vigencia y explicación efectiva. |
| Configuración | Parámetros por familia, folios gobernados, catálogos maestros y visibilidad de módulos. |
| Auditoría | Exportar evidencia y registrar revisión. |
| Actividad | Retirar adjunto, aceptar/reasignar/reabrir atención y restaurar moderación. |
| CRM | Lead, calificación, conversión y seguimiento reservados. |
| Clientes | Ciclo completo de contactos, constancias, importación y eliminación bajo política. |
| Catálogo MYC | Composición explícita, política de precio/descuento y vigencias. |
| Cotizaciones | Emisión/entrega, restauración completa y preview de excepción. |
| Agenda/Llamados | Programar, reprogramar, confirmar, preparar y cerrar, reservados. |
| ETS/OT/Firmas | Transiciones específicas, emisión OT y reapertura segregada. |
| Equipos | Estados explícitos e identidad transversal de activo reservada. |
| Hojas | Reapertura con motivo y anulación controlada. |
| Archivos y Cargas | Carga segura, versiones, clasificación, cuarentena, retención e incidencias. |
| Captura/Calidad | Confirmar retorno, resolver no identificado, enviar/retirar de Calidad y autenticar como acción propia. |
| Documentos | Restauración, distribución controlada futura y lifecycle de interpretaciones/Masters. |
| Metrología | Explicación de cálculo, caso patrón y excepción de selección. |
| Facturación | Autosave/descartar, cancelación/sustitución, PPD y complementos. |
| Pagos | Reverso, reasignación, conciliación bancaria, aging/export y nota fiscal. |
| Integraciones | Credenciales, activación, prueba, retry/conciliación y Drive reservado. |
| Portal | Interacciones y PortalMembership reservados. |
| Resoluciones | Rechazo/revocación de autorización y compensación explícita. |
| Reportes | Encuestas, rentabilidad, tiempos, programación y cierre comercial reservados. |
| Sistema | Jobs, storage, restore drill y soporte temporal gobernado. |

## 7. Permisos institucionales nuevos propuestos

No se cambió ningún permiso actual. Las claves propuestas están marcadas
`(nuevo)` en cada acción del catálogo funcional; las familias siguientes son su
índice consolidado:

| Familia propuesta | Capacidades que cubre |
| --- | --- |
| `dashboard.*` | Panorama y preferencias. |
| `access.*` | Roles, permisos, scopes, overrides, grants y explicación. |
| `settings.modules.*`, `folios.*` | Módulos y secuencias granulares. |
| `audit_logs.export`, `audit_logs.review` | Exportación/revisión. |
| `communications.*` | Conversaciones, canales y entrega. |
| `leads.*` | CRM reservado. |
| `clients.contacts.*`, `clients.tax_documents.*`, `clients.import/export` | Subcapacidades de Cliente. |
| `catalog_items.components/pricing/*` | Composición y gobierno económico. |
| `quotations.issue/send/status/revisions.*` | Emisión, decisión y restauración. |
| `service_agenda.*`, `service_calls.*` | Agenda/Llamados reservados. |
| `service_orders.status/release/reopen`, `work_orders.*`, `service_order_signatures.*` | Operación separada de ETS. |
| `equipment.status.*`, `client_assets.*` | Estados e identidad futura. |
| `field_sheets.complete/reopen/delete` | Lifecycle granular de Hojas. |
| `files.*`, `file_ingestions.*` | ETAPA 3 de Archivos y Cargas. |
| `capture.*`, `certificates.authenticate/visibility.*` | Captura, Calidad y autenticación. |
| `master_templates.restore`, `document_interpretations.archive` | Lifecycle documental faltante. |
| `standards.exception.*`, `procedures.approve/archive`, `technical_profiles.archive` | Gobierno metrológico. |
| `operational_engines.manage/test`, `pattern_selection.exception.*`, `uncertainty_models.activate/archive` | Motores y excepciones. |
| `invoices.drafts/validate/issue/reconcile/cancellation/replacement/ppd.*` | Ciclo fiscal dividido. |
| `payments.create/apply/reverse/reallocate/receipt/resolve`, `accounts_receivable.*`, `payment_reconciliation.*`, `credit_notes.*` | Cobranza y notas. |
| `integrations.*`, `integrations.google_drive.*` | Gobierno de conectores. |
| `portal.interactions.*`, `portal_memberships.*` | Portal objetivo. |
| `resolution_center.reject/authorization.*`, `resolution_public_api.*` | Gobierno adicional del Motor/API. |
| `surveys.*`, `reports.*`, `commercial_close.*` | Postservicio reservado. |
| `system.jobs/storage/backups/support.*` | Operación técnica protegida. |

Las expresiones con `*` son familias de diseño, no comodines aprobados para
asignación. La clave exacta de cada capacidad deberá aprobarse en la matriz de
compatibilidad de la etapa de implementación.

## 8. Capacidades reservadas para el futuro

Quedan reservadas y **no autorizadas para implementación por este documento**:

- recuperación de acceso, MFA y revocación/rotación completa de sesiones;
- RBAC dinámico, roles/grupos múltiples, overrides, scopes y grants temporales;
- CRM/Leads, Agenda y Llamados autónomos;
- historial transversal de activos;
- cuarentena, retención y eliminación avanzada de archivos;
- MDE general y distribución de copias controladas fuera de V1;
- canales externos, Google Drive y administración integral de integraciones;
- PortalMembership e interacciones del portal;
- consumidores administrables de API pública;
- encuestas, reportes finales/rentabilidad y cierre comercial;
- jobs, storage, backups y soporte operativo administrables desde el ERP.

## 9. Riesgos y decisiones que aún requieren aprobación

1. Qué capacidades serán no delegables y qué roles serán protegidos.
2. Qué acciones exigirán motivo, doble autorización o segregación.
3. Límites cuantitativos de descuentos, precios, pagos y folios.
4. Mapeo exacto de las 140 claves actuales, incluida compatibilidad de
   `activity.write/audit`, `certificates.release/release.manage`, `*.read_own`,
   `invoices.manage`, `payments.manage`, `users.manage` y comodines.
5. Qué módulos reservados entran realmente al alcance y en qué etapa.

Estas decisiones no impiden declarar terminada la validación funcional; sí
impiden implementar el catálogo sin aprobación y sin matriz de transición.

## 10. Validaciones realizadas

- Recuento reproducible del snapshot: 36 módulos, 213 acciones, 798 filas,
  305 HTTP y 493 campos.
- Recuento del catálogo funcional: 42 módulos, 181 acciones y 657
  microacciones; IDs de acción únicos.
- Revisión de las 36 superficies y de diez unidades descubiertas.
- Revisión de permisos actuales por intención, sin renombrar ni modificar
  `permissions.py`.
- Confirmación de que las propuestas no alteran contratos de Workbench,
  acreditación, Servicios Compuestos, Motor, Actividad ni Control Documental.

## Documentación actualizada

Se creó esta auditoría y el Catálogo Institucional Funcional. Se actualizaron
el índice documental, el estado del proyecto, el alcance, decisiones,
observaciones, el snapshot técnico, el estado operativo y el registro oficial
de archivos. Se revisaron flujo, reglas de negocio y deuda técnica; no requieren
cambio porque no se modificó comportamiento, alcance implementado ni deuda de
código.
