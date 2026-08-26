# Instrucciones persistentes del repositorio

Al finalizar cualquier cambio de código, esquema, configuración relevante, prueba, recurso operativo o respaldo, actualizar `docs/BACKUP_ESTADO_ACTUAL.md` en el mismo trabajo. El documento debe describir únicamente el estado verificable actual, incluir pendientes y registrar la migración/validaciones aplicables.

`docs/PROJECT_FILE_REGISTRY.md` es la referencia oficial y obligatoria del inventario funcional del repositorio. Todo archivo nuevo debe registrarse inmediatamente, y todo cambio material de responsabilidad de un archivo existente debe actualizar su fila en el mismo trabajo. Cada registro debe conservar el formato único: ruta, módulo, función, responsabilidad detallada, dependencias principales, quién lo utiliza, criticidad y estado.

No se puede dar por terminado ningún desarrollo, corrección, migración, cambio de configuración, prueba, recurso o script sin sincronizar `docs/PROJECT_FILE_REGISTRY.md`. El inventario sólo debe incluir archivos funcionales, configuración, migraciones, recursos oficiales, pruebas, scripts y documentación relevante; se deben excluir artefactos generados o locales como `.DS_Store`, `__pycache__`, `.pytest_cache`, `node_modules`, `dist`, `build`, `output`, `tmp`, `storage`, `backups` y respaldos. Tras cambios de inventario, ejecutar `python3 scripts/generate_project_file_registry.py`, revisar las filas afectadas, comprobar que las rutas existan y ejecutar `git diff --check`.

Si una migración o un cambio de datos modifica la base local, regenerar también `backup_erp_myc_antes_prueba.sql` y confirmar que su `alembic_version` coincide con el head de Alembic. No incluir secretos, credenciales ni contenido sensible de la base en el documento.

El reset destructivo de desarrollo se ejecuta por el menú Base de datos → Resetear BD de desarrollo (el menú solicita la frase de confirmación) o por `scripts/myc reset db` con `MYC_ALLOW_RESET='REINICIAR ERP'`. Ambos reutilizan `scripts/toolkit/system/reset-db.sh`; nunca duplicar ese flujo.

## Procedimiento oficial para auditorías integrales de avance

Toda auditoría de avance del ERP debe revisar el sistema completo y contrastar el código vigente con las decisiones históricas verificables del proyecto. No basta inventariar archivos ni repetir declaraciones de cierre anteriores.

El entregable debe ser un documento Markdown con: resumen ejecutivo; tabla general de todos los módulos; auditoría módulo por módulo; pendientes consolidados; módulos SELLADOS; trabajo restante priorizado; y orden recomendado hasta una versión estable. Para cada módulo debe usar exactamente uno de estos estados: `SELLADO`, `CASI SELLADO`, `EN DESARROLLO`, `PENDIENTE` o `NO INICIADO`.

Cada módulo debe documentar: finalidad y flujo; archivos principales; validaciones frontend/backend, permisos, estados y reglas de negocio existentes; observaciones históricas marcadas como `✅ Resuelta`, `⚠ Parcialmente resuelta` o `❌ Sigue pendiente`; únicamente los pendientes reales para cerrar; riesgos de arquitectura, integridad, UX, mantenimiento o escalabilidad; y los archivos más relevantes, sin convertir el informe en un listado exhaustivo.

La revisión debe cubrir frontend, backend, base de datos, migraciones, APIs, seguridad, integraciones, scripts, infraestructura y componentes reutilizables. Debe incluir cualquier módulo descubierto además de los solicitados y realizar una revisión especial de ETS, Hojas de Campo, Calidad, Certificados, Facturación, Control Documental, Seguridad y Base de datos. En Facturación se deben comprobar Mesa de trabajo, Facturas, borradores, persistencia, emisión, Facturama, PDF institucional MYC, XML, conexión, SAT, impresión, excepciones, historial, pagos, reutilización y consistencia. En Base de datos se deben distinguir tablas obsoletas demostrables, columnas legacy/sin uso verificable, duplicaciones conceptuales, migraciones pendientes e inconsistencias.

No asumir ni inventar funciones. Toda conclusión debe citar evidencia local verificable o declarar explícitamente que no pudo comprobarse. Compilación, existencia de archivos o una declaración histórica de “sellado” no bastan por sí solas. No marcar `SELLADO` cuando exista cualquier pendiente funcional o de UX dentro del alcance acordado. Las mejoras futuras expresamente fuera de alcance no deben mezclarse con los pendientes de cierre.

## Documentación integrada al desarrollo

La documentación es parte obligatoria de toda modificación del ERP y no una tarea posterior u opcional. Esto aplica a funcionalidades, correcciones, refactorizaciones, arquitectura, flujos, reglas de negocio, eliminación de código o módulos, endpoints, permisos, decisiones técnicas, cierres, auditorías, observaciones, UX, base de datos, migraciones, estados, nomenclaturas y cualquier cambio que altere el comportamiento o el estado del sistema.

Antes de dar por terminada cualquier tarea se debe:

1. Identificar los documentos afectados según `docs/project/DOCUMENTATION_INDEX.md`, que es la única autoridad de jerarquía y precedencia documental.
2. Actualizar la documentación en el mismo trabajo, sin esperar una solicitud adicional del usuario.
3. Corregir referencias cruzadas y comprobar que no existan contradicciones, reglas duplicadas, decisiones incompatibles ni estados divergentes.
4. Sincronizar `docs/BACKUP_ESTADO_ACTUAL.md` y `docs/PROJECT_FILE_REGISTRY.md` conforme a las reglas generales de este archivo.

El enrutamiento obligatorio es:

- `docs/project/PROJECT_STATUS.md` cuando cambie el estado de un módulo.
- `docs/project/CURRENT_SCOPE.md` cuando cambie el alcance funcional.
- `docs/project/CURRENT_PROCESS_FLOW.md` cuando cambie el flujo operativo.
- `docs/project/BUSINESS_RULES.md` cuando cambie una regla de negocio.
- `docs/project/DECISIONS.md` cuando se tome o cambie una decisión arquitectónica o funcional.
- `docs/project/OBSERVATIONS_REGISTER.md` cuando una observación aparezca, cambie de estado o quede resuelta.
- `docs/project/TECHNICAL_DEBT.md` cuando aparezca, cambie o desaparezca deuda técnica.
- `docs/architecture/` y `docs/modules/` únicamente cuando cambien sus contratos vigentes.
- `docs/audits/` para revisiones técnicas completas o fotografías fechadas del sistema.
- `docs/closures/` para implementaciones concluidas y validadas.

No crear documentación fuera de la estructura autorizada sin una justificación registrada en `docs/project/DOCUMENTATION_INDEX.md`.

Toda respuesta final de una tarea debe incluir un apartado `## Documentación actualizada` con: documentos modificados; motivo; documentos revisados sin cambios; y cualquier creación, movimiento, fusión o archivo. Si no se requieren cambios documentales, debe indicarse y justificarse expresamente. Una tarea no está terminada hasta realizar esta revisión.

## Arquitectura obligatoria del Workbench de Facturación

Toda apertura, creación/actualización de borrador, emisión, descarga o refresco del Workbench debe reutilizar `frontend/src/components/invoice-workbench/useInvoiceWorkbenchController.js` y el agregado backend `Invoice`. Los contextos se transportan mediante `frontend/src/utils/invoiceWorkbenchContext.js` con `invoice_id` o `service_order_id`. No reintroducir `localStorage`, payloads fiscales duplicados, controladores paralelos, otra máquina de estados ni otro flujo de emisión. El contrato completo está en `docs/architecture/INVOICE_WORKBENCH_CONTROLLER.md`.

La pestaña Facturación del ETS se compone exclusivamente con `frontend/src/components/ets-billing/EtsBillingTab.jsx`. Debe permanecer como consumidor contextual de `useInvoiceWorkbenchController` y `InvoiceWorkbenchDialog`; no puede incorporar llamadas directas a APIs de facturas, payloads fiscales, reglas de estados, descargas ni un modal alternativo.

## Contrato obligatorio de acreditación de calibración

`backend/app/schemas/service_scope.py` es la única fuente de claves de `calibration_scope`. Las modalidades de acreditación son `accredited_iso_17025`, `traceable` y `accredited_linked_lab`; deben propagarse desde la configuración del servicio y resolverse mediante el mecanismo automático vigente. No crear enums paralelos, no convertirlo en una selección manual libre y no usar leyendas, folios, números o textos extraídos de documentos como valores del dominio. El contrato completo está en `docs/architecture/CALIBRATION_SCOPE_CONTRACT.md`.

## Arquitectura obligatoria de Servicios Compuestos

Los Servicios Compuestos se modelan exclusivamente con `catalog_items.service_kind` y la relación normalizada `catalog_item_components`. La cotización y Facturación conservan sólo el concepto comercial padre. La expansión recursiva ocurre una sola vez al crear el ETS mediante `backend/app/services/service_orders.py`; sus hojas simples alimentan las partidas operativas, el cálculo de OT, Equipos, Hojas de Campo y Certificados. No duplicar la expansión en frontend, routers, Facturación u otros servicios, no persistir componentes en JSON y no mostrar componentes al cliente. El contrato completo está en `docs/architecture/COMPOSITE_CATALOG_SERVICES.md`.

## Directriz permanente del Motor de Resoluciones

El Motor de Resoluciones es infraestructura de largo plazo. En todas sus fases
se debe priorizar, en este orden: correctitud arquitectónica, mantenibilidad,
legibilidad, extensibilidad y rendimiento. No se debe optimizar prematuramente.

Las soluciones deben ser simples, explícitas y fáciles de localizar, probar,
depurar, documentar, modificar, reemplazar y eliminar. Cada componente debe
tener una única responsabilidad. Se deben evitar interfaces o clases
innecesarias, herencias profundas, acoplamiento, duplicación, utilidades
genéricas difíciles de mantener, metaprogramación y optimizaciones prematuras.

Cuando existan varias alternativas válidas, se debe elegir la más simple,
mantenible y consistente con la especificación. Antes de cerrar una
implementación del Motor se debe verificar expresamente que el diseño sea fácil
de entender, probar, extender, reemplazar y eliminar; si alguna respuesta es
negativa, el diseño debe reconsiderarse.

El modelo persistente debe ser general para el Motor y no especializarse en el
primer caso de uso. Debe preservar versionado, inmutabilidad histórica,
integridad referencial, reconstrucción completa de una resolución y
compatibilidad con las fases posteriores.

## Directriz permanente de MYC Mobile y operación externa temporal

MYC Mobile es una superficie móvil del ERP MYC y no un sistema operativo
independiente. Su arquitectura de largo plazo debe reutilizar las autoridades
canónicas del ERP para identidad, permisos, clientes, ETS, órdenes de trabajo,
equipos, documentos, comunicaciones y demás dominios compartidos.

MYC Mobile evolucionará progresivamente hacia una versión móvil y acotada del
ERP para staff administrativo y técnicos MYC. No se deben crear dentro de
Mobile motores de negocio, máquinas de estados, generadores de folios,
autoridades documentales ni modelos productivos paralelos cuando exista una
autoridad canónica equivalente en el ERP.

### Operación externa

El acceso de organizaciones/clientes externos mediante MYC Mobile es una
capacidad TRANSITORIA.

Toda funcionalidad exclusiva de operadores externos debe diseñarse para poder
ser eliminada quirúrgicamente en el futuro sin modificar ni degradar las
autoridades productivas permanentes del ERP o la experiencia Mobile destinada
a staff y técnicos MYC.

Se debe separar explícitamente entre:

1. capacidades canónicas y permanentes del ERP;
2. adaptadores, policies y presentación propios de MYC Mobile;
3. capacidades exclusivas y temporales del operador externo.

Una necesidad del operador externo puede reutilizar o motivar una capacidad
genérica útil para MYC, pero la lógica específica del externo no debe
incorporarse dentro de la autoridad canónica.

Ejemplo:

    create_work_order_group()          ← permanente/canónico
        ↑
        ├── Staff MYC                  ← permanente
        └── external request/approval  ← temporal

Al retirar la operación externa deben poder eliminarse sus permisos, requests,
approval workflows, endpoints, UI, notificaciones y policies específicas sin
reescribir creación de OT, numeración, grupos, ETS, firmas, PDFs,
Communications ni las funciones Mobile de staff/técnicos.

No introducir estados específicos del operador externo en entidades canónicas
cuando ese estado pertenezca al workflow temporal externo.

No duplicar autoridades productivas para facilitar la removibilidad: la
removibilidad debe obtenerse mediante desacoplamiento de la capa temporal,
no mediante duplicación del núcleo.

Cuando una implementación temporal requiera modificar una autoridad canónica,
el cambio sólo es aceptable si constituye una mejora genérica, backward
compatible y útil independientemente de la existencia del operador externo.
En caso contrario, implementar la necesidad mediante una capa externa
desacoplada o detenerse y reportar la dependencia.
