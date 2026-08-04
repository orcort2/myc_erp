# Plan de corrección — Auditoría integral ERP MYC

**Base:** hallazgos AUD-001 a AUD-040  
**Regla:** no iniciar una etapa si sus gates de entrada no están satisfechos. Cada corrección requiere migración/prueba/documentación y una nueva auditoría de evidencia.

## Principios de ejecución

1. Congelar funcionalidades nuevas y nuevas fases del Motor.
2. Trabajar en ramas pequeñas, con rollback explícito y sin mezclar saneamiento de datos con refactors.
3. Aplicar seguridad deny-by-default; las excepciones públicas serán una allowlist documentada.
4. No autogenerar ni aplicar el drift de Alembic sin clasificación humana de cada operación.
5. No purgar Git, storage o respaldos sin copia cifrada, autorización, inventario y plan de recuperación.
6. Ningún “pasa localmente” sustituye CI, PostgreSQL aislado, E2E por rol y restore drill.

## Etapa 0 — Contención y baseline (P0, 1–3 días)

| Trabajo | Hallazgos | Entregable/gate |
| --- | --- | --- |
| Congelar despliegues y registrar responsables | 001–016 | Decisión y ventana de remediación aprobadas |
| Rotar cualquier secreto potencialmente usado y prohibir default fuera de dev | 003 | Arranque falla con configuración insegura; prueba |
| Inventariar archivos/dump reales y restringir clones/acceso | 008 | Cadena de custodia y respaldo cifrado confirmado |
| Fijar baseline reproducible de 409+29 pruebas y build | 013, 014, 040 | Log CI inicial y artefactos identificables |

## Etapa 1 — Perímetro y autorización (P0, 1–2 semanas)

| Trabajo | Hallazgos | Dependencias | Gate de salida |
| --- | --- | --- | --- |
| Guard global para API interna + allowlist pública mínima | 001 | Catálogo de rutas | Las 306 operaciones tienen política explícita |
| Portal con identidad cliente, ownership y referencias no enumerables | 002 | Diseño auth cliente | Pruebas IDOR multi-cliente pasan |
| Permisos por acción y ámbito de registro; frontend por capacidades | 011 | Guard global | Matriz rol×ruta×registro validada |
| Sesiones revocables, refresh rotation/jti y estrategia segura de cliente | 010 | Modelo sesión | Logout/reset revocan; replay rechazado |
| Rate limits, registro controlado y CORS por entorno | 001, 031 | Proxy/runtime | Pruebas abuso/configuración pasan |
| Suite HTTP 401/403/404 anti-enumeración | 013 | Todo lo anterior | Cobertura automática de cada operación |

## Etapa 2 — Esquema, migraciones y recuperación (P0, 1–2 semanas)

| Trabajo | Hallazgos | Dependencias | Gate de salida |
| --- | --- | --- | --- |
| Versionar/revisar c14/d15/e16 y agregar defaults faltantes | 004, 007 | Dump sanitizado | Inserts ORM/raw y schema audit pasan |
| Clasificar drift: mantener índices especializados necesarios | 005 | Métricas/consultas | `alembic check` limpio sin degradar SAT/búsqueda |
| Reparar downgrade de firmas y probar ciclo completo | 006 | Base aislada | upgrade→downgrade→upgrade pasa |
| Restaurar dump histórico sanitizado y migrarlo | 007 | Evidencia externa | Restore + upgrade + smoke reproducibles |
| Regenerar respaldo oficial sólo con autorización | 007, 008 | Gates anteriores | `alembic_version == head`, checksum y custodia |

## Etapa 3 — Archivos, privacidad y cadena documental (P0/P1, 1–2 semanas)

| Trabajo | Hallazgos | Gate de salida |
| --- | --- | --- |
| Límites request/archivo/entrada ZIP/ratio/total; streaming y cuarentena | 009 | ZIP bomb, MIME falso y archivos grandes rechazados |
| Antivirus/content scanning, cuotas, retención y storage durable | 008, 009, 027 | Política y pruebas de fallo/recuperación |
| Retirar datos operativos del control de versiones y sanear historial de forma autorizada | 008, 037 | DLP limpio, referencias migradas y copia recuperable |
| Identidad versionada y snapshot inmutable por documento | 016 | Reimpresión histórica produce el mismo documento |
| AuditLog general protegido contra edición | 032 | Prueba DB de append-only y acceso mínimo |

## Etapa 4 — Cierre de flujos operativos (P1, 2–4 semanas)

| Vertical | Hallazgos/pendientes | Gate de salida |
| --- | --- | --- |
| Cotización→ETS | 019, 021, 025 | Restauración completa, estados únicos y E2E autenticado |
| ETS→OT→Equipo | 019, 017 | Router delgado, transacción única y origen Motor conectado |
| Hoja→Captura→Calidad | 022, 023 | Matriz de 23 plantillas con fixtures y E2E visual |
| Certificado→Liberación | 020, 002 | Calidad única, compuerta financiera e identidad cliente |
| Actividad/notificaciones | 004 y entrega externa | Defaults, retry, navegación, métricas y retención |
| Agenda/Llamados | 025 | Decisión: dominio formal o exclusión explícita de 1.0 |

## Etapa 5 — Facturación y fiscalidad (P1, 2–4 semanas)

| Trabajo | Hallazgos | Gate de salida |
| --- | --- | --- |
| Certificar Workbench único con E2E borrador→timbrado→descarga | 012, 013 | Persistencia y recuperación sin doble emisión |
| Cancelación, sustitución y conciliación/webhooks | 012 | Sandbox y casos de error aprobados |
| PPD y complemento de pago | 012 | XML validado y saldos conciliados |
| Nota de crédito fiscal separada de nota administrativa | 024 | CFDI egreso y estados no ambiguos |
| PDF/recibo/identidad fiscal inmutables | 016 | Snapshot y regresión visual/documental |

## Etapa 6 — Plataforma de entrega y observabilidad (P1, 2–3 semanas)

| Trabajo | Hallazgos | Gate de salida |
| --- | --- | --- |
| CI con lint, test, build, coverage, Alembic y dependency scan | 013–015, 033 | Ningún merge omite gates |
| Artefacto/despliegue declarativo, TLS/proxy y configuración validada | 014, 031 | Staging se crea desde cero |
| Readiness real de DB, storage, LibreOffice y PAC | 014 | Dependencia caída impide tráfico útil |
| Logs estructurados, métricas, tracing, alertas y SLO | 014, 027 | Fallos detectados y trazables |
| Backups automáticos y restore drill con RPO/RTO | 007, 014 | Simulacro documentado exitoso |

## Etapa 7 — Rendimiento, UX y mantenibilidad (P2, 3–6 semanas)

| Trabajo | Hallazgos | Gate de salida |
| --- | --- | --- |
| Paginar/buscar listados y crear agregados de dashboard | 026 | Carga objetivo dentro de presupuesto |
| Jobs/streaming para documentos y conversiones | 027 | Sin bloqueo de worker ni memoria no acotada |
| Code splitting y descomposición de páginas/API/CSS | 028 | Bundle y complejidad reducidos sin regresión E2E |
| Eliminar/ocultar placeholders, labs y rutas huérfanas | 029, 034–037 | Navegación coherente por rol |
| Accesibilidad, errores, estados vacíos y responsive | UX | Auditoría WCAG y E2E visual |

## Etapa 8 — Motor de Resoluciones (después de P0/P1)

1. Obtener dictamen formal de Fase 14 y corregir contradicciones documentales (AUD-018).
2. Conectar el productor de equipo adicional desde ETS y el de certificado desde Calidad, sin duplicar lifecycle ni máquina de estados (AUD-017).
3. Validar workers distribuidos, supervisión, retry, recovery y HA en staging.
4. Abrir una fase nueva sólo cuando el origen inicie la excepción, el Centro autorice y el Motor ejecute sin orquestación manual impropia.

## Orden crítico y dependencias

```text
Contención
  -> perímetro/portal/sesiones
  -> migraciones/restore
  -> archivos/identidad
  -> E2E de verticales
  -> fiscalidad completa
  -> plataforma/observabilidad
  -> rendimiento/UX/mantenibilidad
  -> expansión del Motor
```

Seguridad y datos pueden avanzar en paralelo sólo si usan bases/fixtures aislados. Facturación depende del perímetro y de un esquema estable. La limpieza de código depende de E2E de caracterización. La expansión del Motor depende de que sus módulos de origen y la operación de workers estén cerrados.

## Criterio de producción

La versión será candidata a producción únicamente si:

- no quedan críticos ni altos abiertos;
- toda operación HTTP tiene política y prueba por rol/ownership;
- upgrade histórico, downgrade soportado, check y restore pasan;
- datos reales no viven en Git y uploads están acotados;
- flujos ETS/certificados/facturación tienen E2E con rollback/fallo;
- Facturama y fiscalidad requerida están certificadas;
- CI/CD, readiness, métricas, alertas y backup/restore operan;
- la documentación canónica coincide con código y evidencia.

Después deberá ejecutarse una auditoría independiente de cierre; no basta marcar tareas como completadas.
