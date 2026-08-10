# Estado verificable de módulos — 2026-08-10

Se usan exclusivamente los estados canónicos exigidos por el repositorio:
`SELLADO`, `CASI SELLADO`, `EN DESARROLLO`, `PENDIENTE` y `NO INICIADO`.
El dictamen de auditoría es un segundo eje: `APROBADO`, `APROBADO CON
OBSERVACIONES`, `EN REVISIÓN`, `REQUIERE CORRECCIONES` o `BLOQUEADO`.

## Resumen

| Estado canónico | Cantidad |
| --- | ---: |
| SELLADO | 1 |
| CASI SELLADO | 9 |
| EN DESARROLLO | 28 |
| PENDIENTE | 2 |
| NO INICIADO | 2 |
| **Total** | **42** |

## Matriz consolidada

| ID | Módulo | Estado | Backend | Frontend | BD | Permisos | Tests | Riesgo | Dictamen / acción necesaria |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| M01 | Panorama y trabajo pendiente | CASI SELLADO | Agrega listados reales | Dashboard y accesos | Sin agregado dedicado | UI filtrada | Unitarias indirectas | MEDIO | APROBADO CON OBSERVACIONES; E2E y paginación |
| M02 | Acceso personal | EN DESARROLLO | JWT access/refresh, lock 5/15 | Login interno/Portal | Usuarios y auditoría | Separación de contextos | Auth focalizada | ALTO | REQUIERE CORRECCIONES; revocación, MFA, recuperación, rate limit |
| M03 | Usuarios y acceso institucional | EN DESARROLLO | Usuarios multirrol; bootstrap estático | Ajustes operativo | Roles internos + portal | Guard y `*`; gate divergente | Portal/admin | ALTO | REQUIERE CORRECCIONES; RBAC institucional y reconciliación |
| M04 | Configuración institucional y folios | EN DESARROLLO | CRUD, folios con locks | Varias secciones placeholder | Persistencia y secuencias | Administrativa | Focalizadas | MEDIO | EN REVISIÓN; cerrar identidad/configuración y E2E |
| M05 | Auditoría institucional | EN DESARROLLO | `audit_logs` consultable | Panel en Ajustes | Log mutable/normal | Permiso administrativo | Cobertura indirecta | ALTO | REQUIERE CORRECCIONES; actor obligatorio/exportación/inmutabilidad |
| M06 | Actividad | EN DESARROLLO | Threads, eventos, adjuntos, atención | Paneles y bandeja | Modelo completo | Permisos finos | Suite focalizada | MEDIO | EN REVISIÓN; navegación, retención y operación externa |
| M07 | Comunicaciones y notificaciones | EN DESARROLLO | Conversaciones/notificaciones internas | Centro y bell | Persistente | Ownership/sesión | Parcial | MEDIO | EN REVISIÓN; canales externos, paginación, observabilidad |
| M08 | Prospección comercial | NO INICIADO | Ausente | Ausente | Ausente | Ausente | Ausente | BAJO | BLOQUEADO por alcance no confirmado |
| M09 | Clientes y contactos | CASI SELLADO | CRUD, import/export, constancia, perfiles | Página completa | Clientes/contactos | Guard activo | Varias unitarias | MEDIO | APROBADO CON OBSERVACIONES; actor, E2E y decisión contactos |
| M10 | Catálogo MYC de servicios | EN DESARROLLO | Simples/compuestos/empresas | Editor embebido | Normalizado | Guard activo | Compuestos | MEDIO | REQUIERE CORRECCIONES; actor y experiencia independiente |
| M11 | Cotizaciones | CASI SELLADO | Estados, revisiones, PDF, desbloqueo | Flujo amplio | Snapshots/items | Guard y excepción segregada | Suite focalizada | MEDIO | APROBADO CON OBSERVACIONES; restore de partidas y E2E hasta ETS |
| M12 | Agenda de servicios | PENDIENTE | Sólo fecha ETS | Sin calendario | Sin entidad | Hereda ETS | Ausente | MEDIO | BLOQUEADO por decisión funcional |
| M13 | Llamados y seguimiento previo | PENDIENTE | Sólo hito ETS | Sin módulo | Sin entidad | Hereda ETS | Ausente | MEDIO | BLOQUEADO por decisión funcional |
| M14 | ETS | EN DESARROLLO | Flujo principal, pero router/servicio duplicados | Página de 4,598 líneas | Agregado amplio | Guard activo; actor omitido | Varias indirectas | CRÍTICO | REQUIERE CORRECCIONES; eliminar duplicación y excepción ejecutora |
| M15 | Órdenes de trabajo | CASI SELLADO | Multi-OT/cupo/PDF | Integrado en ETS | Normalizado + legacy | Hereda ETS | Focalizadas | MEDIO | APROBADO CON OBSERVACIONES; E2E y retiro legacy medido |
| M16 | Equipos del servicio | CASI SELLADO | CRUD/snapshot/capacidad | Integrado en ETS | Equipo y reservas | Guard activo; actor omitido | Focalizadas | MEDIO | APROBADO CON OBSERVACIONES; E2E y conexión con Motor |
| M17 | Firmas de servicio | EN DESARROLLO | Ciclos/OT/reapertura | Firma integrada | Normalizado + legacy | Permisos específicos | Focalizadas | ALTO | REQUIERE CORRECCIONES; retirar camino legacy y E2E multi-OT |
| M18 | Hojas de Campo | EN DESARROLLO | Plantilla/snapshot/resultados/PDF | Layout y captura | Persistente | Permisos | Suites de contrato | ALTO | REQUIERE CORRECCIONES; semántica, 23 plantillas y renderer único |
| M19 | Plantillas de Hojas de Campo | EN DESARROLLO | Versiones/import/export | Ajustes y LAB | Definiciones | Permisos amplios | Engine focalizado | MEDIO | EN REVISIÓN; cierre funcional y pruebas visuales |
| M20 | Gestión de archivos | CASI SELLADO | Perfiles, ZIP, atomicidad, confinamiento | Consumida por dominios | Metadata desigual | Después de permiso/ownership | 78 históricas incluidas | ALTO | APROBADO CON OBSERVACIONES; storage durable, AV y retención |
| M21 | Captura | EN DESARROLLO | Paquetes/retorno/fingerprint/readiness | Página e integración ETS | Archivos/versiones | Guard activo | Focalizadas | ALTO | REQUIERE CORRECCIONES; no identificados y E2E real |
| M22 | Calidad | EN DESARROLLO | Review/aprobación/autenticación | Página + superficie ETS | Estados certificados | Permiso Calidad | Focalizadas | ALTO | REQUIERE CORRECCIONES; único autenticador y E2E |
| M23 | Certificados | CASI SELLADO | Expediente/PDF/auth/release/verificación | Integrado y Portal | Versiones/códigos | Guard + ownership | Amplia focalizada | ALTO | APROBADO CON OBSERVACIONES; retirar duplicación Calidad/ETS |
| M24 | Control Documental | SELLADO | Lista/versiones/estados | Biblioteca | Documentos/versiones | Permisos | Focalizadas | BAJO | APROBADO dentro de V1 congelado |
| M25 | Plantillas Maestras documentales | CASI SELLADO | Hash/fingerprint/generación | Flujo Captura/Calidad | Versionado | Permisos | Caso real focalizado | MEDIO | APROBADO CON OBSERVACIONES; E2E retorno y recuperación |
| M26 | Interpretaciones documentales | EN DESARROLLO | CRUD/versionado | Sin superficie cerrada | Persistente | Permisos | Limitada | MEDIO | EN REVISIÓN; integración y UX |
| M27 | Patrones de referencia | EN DESARROLLO | CRUD/vigencia | Patrones | Persistente | Permisos | Indirecta | MEDIO | EN REVISIÓN; renovación/E2E/paginación |
| M28 | Certificados de patrón | EN DESARROLLO | CRUD/aprobación | Integrado en Patrones | Persistente | Permisos | Limitada | MEDIO | EN REVISIÓN; ciclo de vigencia y documentos |
| M29 | Procedimientos de calibración | EN DESARROLLO | CRUD/versiones | Página no navegable | Persistente | Permisos | Limitada | MEDIO | REQUIERE CORRECCIONES; navegación e integración |
| M30 | Perfiles técnicos | EN DESARROLLO | CRUD/aprobación | Parcial | Persistente | Permisos | Limitada | MEDIO | EN REVISIÓN; gobernar flujo final |
| M31 | Cálculos metrológicos | EN DESARROLLO | Motores disponibles | Absorbido/oculto | Resultados parciales | Permiso técnico | Unitarias | ALTO | REQUIERE CORRECCIONES; contrato end-to-end con Hojas |
| M32 | Selección de patrones | EN DESARROLLO | Motor y excepciones | Parcial | Persistente | Permisos | Unitarias | ALTO | REQUIERE CORRECCIONES; incorporar al flujo operativo |
| M33 | Incertidumbre | EN DESARROLLO | Modelo/versiones/cálculo | Página no navegable | Persistente | Permisos amplios | Unitarias | ALTO | REQUIERE CORRECCIONES; integración, UX y E2E |
| M34 | Facturación | EN DESARROLLO | Invoice, PAC, docs, conciliación | Workbench único | Persistencia amplia | Permisos amplios | Varias suites | ALTO | BLOQUEADO para Producción por CFDI incompleto |
| M35 | Pagos, cartera y notas de crédito | EN DESARROLLO | Pagos/saldos/recibos/CxC | Workbench/Dashboard | Persistente | Permisos amplios | Suite de pagos | ALTO | REQUIERE CORRECCIONES; reversos, conciliación, complemento, egreso |
| M36 | Catálogos SAT | CASI SELLADO | Fuente/versiones/búsqueda | Consumidores Workbench | Índices especializados | Permisos | Importador/fuente | MEDIO | APROBADO CON OBSERVACIONES; blindar fuente y E2E |
| M37 | Integraciones | EN DESARROLLO | Facturama/LibreOffice; correo incompleto | Estados parciales | Intentos PAC | Permisos | Mocks/focalizadas | ALTO | BLOQUEADO para Producción; correo/PAC/Drive/operación |
| M38 | Portal de cliente | EN DESARROLLO | Identidad, membresía, roles, ownership | Portal funcional | 10+ tablas | Catálogo propio | Suites backend/frontend | ALTO | EN REVISIÓN; correo, sesiones, E2E y reconciliar catálogo |
| M39 | Centro de Resoluciones | EN DESARROLLO | Flujo completo y worker | Consola | Persistencia general | Decisiones exactas | 29 archivos históricos | MEDIO | EN REVISIÓN; Fase 14 e inicio desde origen |
| M40 | Integración externa de resoluciones | EN DESARROLLO | API v1/SDK/consumer | Portal técnico controlado | Consumidores/idempotencia | Organización/consumer | Suite Fase 10 | ALTO | EN REVISIÓN; operación, rotación y despliegue |
| M41 | Reportes, encuestas y cierre comercial | NO INICIADO | Ausente | Ausente | Ausente | Ausente | Ausente | BAJO | BLOQUEADO por alcance no confirmado |
| M42 | Continuidad operativa del ERP | EN DESARROLLO | Doctor/backup/reset/drills | Sin consola operativa | Dump/head alineados | Administrativa parcial | Scripts manuales | ALTO | BLOQUEADO para Producción; CI/CD, monitoreo, RPO/RTO y restore periódico |

## Módulos sellados

Sólo `M24 Control Documental`, limitado a V1. La infraestructura transversal
de seguridad, storage o Producción no amplía ni reabre ese alcance funcional,
pero sí condiciona el despliegue del sistema completo.

## Observaciones históricas destacadas

- ✅ Resuelta: API anónima y Portal global/IDOR del corte 2026-08-03.
- ✅ Resuelta: secreto JWT productivo conocido y drift/downgrade/backup.
- ✅ Resuelta: perfiles institucionales de upload y ZIP seguro.
- ⚠ Parcialmente resuelta: permisos frontend; existe filtrado, pero falta E2E
  por rol y el catálogo/gate no está reconciliado.
- ⚠ Parcialmente resuelta: Portal; membresías/UI existen, falta correo y
  seguridad de sesión productiva.
- ❌ Sigue pendiente: excepción ETS que ejecuta al solicitar.
- ❌ Sigue pendiente: Calidad como único autenticador.
- ❌ Sigue pendiente: cierre semántico/E2E de Hojas y Captura.
- ❌ Sigue pendiente: CFDI productivo completo.
