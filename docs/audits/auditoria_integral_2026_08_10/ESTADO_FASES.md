# Fases y etapas verificadas — 2026-08-10

La tabla usa cierres, código, migraciones y pruebas como evidencia. Un cierre
técnico no equivale por sí solo a módulo sellado.

| Fase/etapa | Objetivo | Estado documentado | Estado real observado | Evidencia | Riesgos/pendientes |
| --- | --- | --- | --- | --- | --- |
| Hojas de Campo Fase 1 | Motor base de plantillas/captura | Cerrada | FUNCIONAL CON DEUDA | cierre, engine, modelos, pruebas | 23 plantillas, semántica, renderer/E2E |
| Seguridad Etapa 1 | Deny-by-default, JWT, Portal IDOR, UI | APROBADA/CERRADA | APROBADA | 356/356 clasificadas; suites 450 | sesiones, rate limit y actor no formaban parte del cierre |
| Seguridad Etapa 2A | Esquema y recuperación | CERRADA | APROBADA, no repetida destructivamente | head/check/dump alineados; drill 2026-08-05 | automatizar restore periódico |
| Seguridad Etapa 2B | Catálogo técnico de capacidades | CERRADA | FUNCIONAL CON REGRESIÓN DOCUMENTAL | catálogo/snapshot/CSV existen | `--check` falla por 20/2 brechas |
| Archivos Etapa 3 | Upload/storage institucional | TERMINADA, EN REVISIÓN | EN REVISIÓN | validadores, atomicidad, suite | storage durable, AV, retención |
| Portal integración | Identidad/membresías/ownership/UI | TERMINADA, EN REVISIÓN | EN REVISIÓN | modelos, routers, Portal React, tests | correo, sesiones, E2E, docs obsoletas |
| Portal usuarios/accesos | Administración multirrol | TERMINADA, EN REVISIÓN | EN REVISIÓN | migración `c8a51e2d7f40`, tests | revisión funcional y gate capacidades |
| Motor Fase 0 | Ratificación y gates | APROBADA | APROBADA | matriz/cierre | ninguno dentro de fase |
| Motor Fase 1 | Contratos y runtime | APROBADA | APROBADA | dominio/registry/tests | ninguno dentro de fase |
| Motor Fase 2 | Persistencia general | APROBADA | APROBADA | ORM/migración/tests | depende de operación general |
| Motor Fase 3 | Seguridad base | APROBADA | APROBADA | políticas/decisiones/tests | históricos `asserted` |
| Motor Fase 4 | Lifecycle | APROBADA | APROBADA | máquina/invariantes/tests | ninguno dentro de fase |
| Motor Fase 5 | Ejecución | APROBADA | APROBADA | checkpoints/idempotencia/outbox | operación externa limitada |
| Motor Fase 6 | Compensación | APROBADA | APROBADA | planes/runner/tests | no automática por diseño |
| Motor Fase 7 | Auditoría/evidencia | APROBADA | APROBADA | reconstrucción/hash/timeline | decisiones antiguas `asserted` |
| Motor Fase 8 | Seguridad integral | APROBADA | APROBADA | catálogo/consumo anti-replay | ninguno dentro de fase |
| Motor Fase 9 | Vertical Certificados | APROBADA | APROBADA | provider/gateways/tests | sólo primer vertical |
| Motor Fase 10 | API pública/SDK | APROBADA | APROBADA | API v1, cursor c1, SDK/tests | despliegue/rotación no demostrados |
| Motor Fase 11 | Runtime distribuido | APROBADA | APROBADA EN CÓDIGO | cola/lease/fencing/recovery/tests | HA/supervisión real no demostrada |
| Motor Fase 12 | Centro de Resoluciones | APROBADA | APROBADA | API interna/UI/worker/tests | operación productiva no demostrada |
| Motor Fase 13 | Consolidación | APROBADA | APROBADA | registry/formularios/E2E de prueba | README está obsoleto |
| Motor Fase 14 | Equipo adicional | TERMINADA, EN REVISIÓN | EN REVISIÓN | segundo vertical y suite | productor sin consumidor productivo en ETS/UI |
| Motor Fase 15 | No abierta | No iniciada | NO INICIADA | apertura inexistente | no iniciar antes de cerrar plataforma |

## Dependencias y contradicciones

- Etapa 2B depende de reconciliar cambios posteriores del Portal; el gate rojo
  impide afirmar que la gobernanza siga cerrada.
- Fase 14 del Motor depende de una integración de origen aún ausente; el
  vertical funciona en pruebas, pero no completa el recorrido del usuario.
- El Portal depende de correo productivo; sin proveedor no termina registro e
  invitación reales.
- El cierre fiscal depende de Facturama y de capacidades no implementadas.
- README contradice el estado de Fases 13/14; el canon y los cierres recientes
  prevalecen.

