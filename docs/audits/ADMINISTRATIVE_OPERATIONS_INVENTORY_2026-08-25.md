> Tipo: Auditoría técnica fechada
>
> Estado: EN REVISIÓN

# Inventario de operaciones extraordinarias y administrativas

## Dictamen ejecutivo

El ERP ya contiene operaciones extraordinarias en servicios propietarios,
permisos y auditoría, pero no existe una cobertura institucional uniforme. El
Motor y el Centro sí ofrecen el armazón reusable; por ello se implementó
primero la familia declarativa `administrative_tools` y el P0 de continuidad
ETS. No se migraron en masa operaciones de otros dominios: hacerlo sin
precheck, ownership y pruebas de cada agregado sería inseguro.

## Inventario priorizado

| Dominio | Operaciones extraordinarias encontradas | Estado/owner actual | Prioridad |
| --- | --- | --- | --- |
| Cotizaciones | restaurar snapshot; cancelar/desactivar; desbloqueo y reconstrucción excepcional | `quotations.py` y `quotation_service_changes.py`; flujo legacy estructurado, separado del Centro | P1: evaluar convergencia sin romper revisión comercial ni reconstrucción con mismo folio |
| ETS | baja soft legacy; eliminación física de OT; excepciones; reapertura de firmas; equipo adicional | baja directa era insegura; OT física conserva contrato propio; equipo adicional ya usa Motor | P0 resuelto para restaurar/reconstruir/baja prístina; P1 reparación estructural |
| Equipos | desactivar; alta adicional por resolución | servicio propietario; adicional ya integrado | P1: incorporar correcciones de identidad/asociación sólo con precheck |
| Hojas de Campo | desactivar/corregir resultados y firmas | servicio propietario, ligado al pipeline metrológico | P1: no mover resolución de Hoja a Captura; diseñar corrección versionada |
| Captura | retorno/reemplazo de ZIP y reconciliación de Master | flujo especializado con fingerprint/matching | P1: bandeja de `unidentified`; no convertir sustitución normal en herramienta admin |
| Calidad/Certificados | rechazar/retornar/autenticar/liberar/desactivar; retiro de liberación incorrecta | lifecycle propietario; retiro incorrecto ya usa Motor | P1: ampliar sólo casos con evidencia y compensación definidas |
| Facturación/Pagos | cancelar/emitir/reintentar/sincronizar; borradores, notas y pagos | agregado `Invoice` y Workbench únicos obligatorios | P0 de diseño: ninguna herramienta puede mutar CFDI fuera de `Invoice`; P1 ciclo fiscal pendiente |
| Clientes/contactos | archivar/restaurar/eliminar permanentemente; perfiles | servicio de Clientes con tratamiento estructurado | P1: actor obligatorio y precheck de dependencias antes de exponer en Centro |
| Usuarios/roles/permisos | activar/desactivar, roles, membresías, invitaciones | dominios internos/Portal separados | P1: no usar `admin.all`; integrar sólo operaciones con alcance y segregación explícitos |
| Control Documental | aprobar/archivar/versionar | lifecycle propietario SELLADO en su alcance | P2: sólo incidentes extraordinarios; no reabrir versionado normal |
| Plantillas/Masters | aprobar/archivar/restaurar defaults | servicios documentales | P1: retiro/sustitución institucional debe preservar versiones usadas |
| Patrones/certificados de patrón | desactivar y versionar vigencias/incertidumbre | servicios metrológicos | P1: precheck contra Hojas/selecciones/snapshots antes de baja |
| Procedimientos | desactivar | servicio de procedimientos | P2: primero cerrar consumo end-to-end |
| Incertidumbre | aprobar/archivar modelos; borrar componentes/fórmulas | motor especializado | P1: evitar borrado cuando exista evidencia calculada |
| Catálogo | baja soft, edición y composición | servicio propietario y snapshots downstream | P1: restauración/corrección explícita sin reinterpretar cotizaciones/ETS históricos |
| Catálogos SAT | aliases/favoritos/importación | servicio SAT | P2: rollback de importación requiere versión y evidencia de fuente |
| Configuración institucional | cambios de parámetros | servicio de configuración | P1: preview de alcance y doble autorización para cambios críticos |
| Integraciones externas | Facturama, Expo, estado y retries parciales | servicios por integración; Expo best-effort | P1: retries idempotentes por conector; no ejecutar efectos fiscales desde Centro directamente |
| Archivos/almacenamiento | limpieza de huérfanos/no referenciados | `storage_service.py` | P1: sólo herramienta técnica con dry-run, contención y autorización CRITICAL |
| Portal cliente | membresías, invitaciones y roles | servicios Portal separados | P2: preservar aislamiento por cliente y tokens de un uso |
| Reparación/Mantenimiento/Venta | cancelación, garantía, autorizaciones y cierres propios | verticales ETS especializadas | P2: no se modificaron; sólo futuras excepciones realmente extraordinarias |
| LAB temporal | borrar OT/equipo; Ticket de reapertura versionada | contrato temporal aislado | P2: no integrar al ETS productivo ni al nuevo vertical administrativo |
| Auditoría/Actividad | consulta, moderación, evidencia | infraestructura transversal | P1: toda herramienta nueva debe publicar referencias y eventos reconstruibles |
| Base de datos/backup/reset | reset de desarrollo y recuperación Alembic | toolkit oficial separado | P0 de seguridad ya contractual: jamás exponer reset destructivo como resolución ERP |

## Hallazgos P0/P1/P2/P3

- P0 corregido: baja ETS sin permiso específico ni precheck; cancelaba OT y
  permitía recreación silenciosa desde cotización aceptada.
- P0 corregido: creación canónica sólo comprobaba ETS activos; ahora un ETS
  inactivo exige resolución administrativa.
- P1: reparación estructural de ETS con operación consumida permanece
  bloqueada; no hay estrategia universal segura.
- P1: desbloqueo comercial de cotización y excepciones ETS previas son
  mecanismos estructurados pero paralelos; requieren evaluación antes de una
  convergencia gradual.
- P1: búsqueda de Herramientas inicia por ID; faltan resolvers declarativos por
  folio, cliente, certificado, factura y cotización.
- P1: permisos globales históricos (`Administrador: *`) permanecen en el
  bootstrap. Las nuevas herramientas usan permisos de dominio explícitos, pero
  la eliminación del wildcard requiere una fase RBAC institucional.
- P2: extender herramientas a documentos, metrología, catálogo, clientes,
  facturación e integraciones, una por una y con servicio propietario.
- P3: sugerencias por IA; no autorizadas ni necesarias para este contrato.

## Dependencias downstream revisadas para ETS

Se verificaron relaciones con cotización, `ServiceOrderItem`, OT, Equipos,
Hojas/Captura vía Equipo/Certificado, Certificados, Facturas, ciclos y campos de
firma, ejecución Venta, referencias del Motor y expansión de Servicios
Compuestos. El precheck inicial bloquea actividad consumida; no borra, mueve ni
reinterpreta esos registros.
