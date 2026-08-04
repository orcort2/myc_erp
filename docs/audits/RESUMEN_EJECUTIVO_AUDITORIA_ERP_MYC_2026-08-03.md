# Resumen ejecutivo — Auditoría ERP MYC

**Corte:** 2026-08-03  
**Estado general:** **NO APTO PARA PRODUCCIÓN**  
**Puntuación global ponderada:** **49/100**  
**Hallazgos:** 40: 3 críticos, 13 altos, 18 medios, 4 bajos y 2 informativos.

## Dictamen

El ERP es un producto real y sustancial, no una simulación: existen 306 operaciones HTTP, 101 tablas ORM, un flujo operativo amplio, PDF/XLSX/ZIP, Facturama Sandbox, LibreOffice, Actividad y un Motor de Resoluciones con persistencia, seguridad interna, workers, API y SDK. Las suites actuales pasan: 409 pruebas backend y 29 frontend.

No puede ponerse en producción. El bloqueo dominante no es falta de código, sino ausencia de un perímetro de seguridad coherente: 74 operaciones son públicas y 15 aceptan sesión opcional, incluyendo mutaciones de Clientes, Cotizaciones, ETS y Equipos. El portal de cliente devuelve información global sin identidad de cliente. La configuración permite arrancar con un secreto JWT conocido. Estas tres condiciones constituyen los hallazgos críticos.

La persistencia tampoco está cerrada: `alembic check` falla, el downgrade completo falla y ocho tablas conservan 16 columnas `created_at`/`updated_at` NOT NULL sin `DEFAULT`. El backup oficial declara `b03b4c5d6e7f` mientras el árbol visible llega a `e16e7f8091a2` mediante tres migraciones no rastreadas. No se regeneró el backup por instrucción expresa.

## Decisión recomendada

Congelar nuevas funcionalidades. Ejecutar primero un programa P0 de seguridad y consistencia de datos; después cerrar flujos verticales con E2E autenticado. No abrir otra fase del Motor. Su núcleo debe conservarse, pero hoy sólo dos resoluciones están instaladas y la propuesta de equipo adicional desde el módulo de origen no tiene consumidor de producción.

## Puntuaciones

| Dimensión | Puntos |
| --- | ---: |
| Arquitectura | 62 |
| Backend | 58 |
| Frontend | 55 |
| Base de datos | 52 |
| Migraciones | 40 |
| Seguridad | 24 |
| Permisos | 22 |
| Integridad transaccional | 70 |
| Flujos de negocio | 52 |
| Motor de Resoluciones | 78 |
| Actividad y notificaciones | 67 |
| Documentos y snapshots | 58 |
| Facturación | 56 |
| Pruebas | 65 |
| Documentación | 56 |
| UX | 48 |
| Rendimiento | 45 |
| Operabilidad | 42 |
| Mantenibilidad | 44 |
| Preparación para producción | 28 |

La nota global usa ponderación por riesgo: seguridad/permisos 18%; BD/migraciones/integridad 17%; flujos/facturación/documentos 18%; backend/frontend/arquitectura 18%; pruebas 8%; operación/producción/rendimiento 11%; Motor/Actividad 6%; documentación/UX/mantenibilidad 4%. Los bloqueadores críticos limitan la nota final aunque varias capas aisladas tengan cobertura sólida.

## Bloqueadores inmediatos

1. Aplicar autenticación y autorización deny-by-default a toda la API interna; crear pruebas 401/403 por operación.
2. Rehacer el portal con identidad y filtro obligatorio de cliente; impedir IDOR de PDF.
3. Rechazar arranque no-development con el secreto JWT por defecto y definir rotación/revocación de sesiones.
4. Corregir drift, defaults y downgrade; versionar las migraciones reales; actualizar una base histórica aislada.
5. Alinear backup y head sólo después de autorización y saneamiento de datos.
6. Limitar tamaño/descompresión y validar contenido en cargas; cerrar endpoints públicos de archivo.
7. Cerrar CFDI productivo: cancelación/sustitución, PPD/complementos, nota de egreso, conciliación y E2E Sandbox.
8. Incorporar CI, E2E autenticado, readiness de dependencias, logs estructurados, métricas, recuperación y despliegue reproducible.

## Estado por familias

- **SELLADO:** Control Documental V1, exclusivamente dentro de su alcance congelado; su exposición depende de la seguridad transversal.
- **CASI SELLADO:** ninguno puede conservar este estado operativo mientras existan bloqueadores de seguridad/migración dentro de su alcance desplegable.
- **EN DESARROLLO:** Dashboard, Clientes, Cotizaciones, Catálogo, ETS/OT/Equipos/Firmas, Hojas, Captura, Calidad, Certificados, Facturación/Pagos/CxC/Notas, Patrones/Procedimientos/Incertidumbre, Actividad, Ajustes, portal, Motor, scripts e infraestructura.
- **PENDIENTE:** Agenda y Llamados autónomos, CRM/Leads, encuesta/reporte final, Google Drive, fiscalidad productiva completa.
- **Simulados/placeholders:** cuatro categorías de Ajustes (`Operación`, `Facturación`, `Integraciones`, `Sistema`), diseñador/labs y acciones “Lote próximamente”.

## Motor de Resoluciones

El núcleo es la zona técnicamente más madura: lifecycle, decisiones, snapshots, idempotencia, locks, outbox, compensación, auditoría, cola PostgreSQL, leases/fencing, worker, API v1 y SDK tienen diseño y pruebas específicos. Sin embargo, sólo se instalan dos verticales. Certificados y Equipo adicional pueden ejecutarse desde el Centro, pero el patrón de producto solicitado —iniciar excepción en el módulo de origen, autorizar y ejecutar sin orquestación manual desde el Centro— no está completo: `request_additional_equipment_resolution` no tiene consumidor de producción y no se encontró productor equivalente de Certificados desde su UI de origen.

## Limitaciones verificables

- No se ejecutó E2E de navegador: no existe suite configurada ni credencial/dataset de prueba documentado.
- Facturama producción y webhooks externos no se invocaron; la configuración local está orientada a Sandbox.
- No se probó upgrade desde el backup histórico porque su restauración contiene datos reales y requeriría una copia sanitizada; sí se probó desde vacío.
- Vulnerabilidades Python quedaron **NO VERIFICADAS**: `pip-audit` no está instalado. `pip check` sí pasó.
- El escaneo de secretos fue por patrones de nombres; no hubo herramienta de entropía ni auditoría completa del historial Git.

## Evidencia y entregables

La evidencia reproducible está en [`evidence/AUDITORIA_COMANDOS_2026-08-03.txt`](evidence/AUDITORIA_COMANDOS_2026-08-03.txt). El informe principal, matrices y plan detallan cada conclusión. No se modificó código funcional, esquema ni datos compartidos; sólo documentación de auditoría y sincronización documental obligatoria.
