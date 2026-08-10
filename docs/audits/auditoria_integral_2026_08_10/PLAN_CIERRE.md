# Plan de cierre priorizado — 2026-08-10

Este plan no autoriza implementación; ordena el trabajo posterior.

## P0 — Bloqueadores

1. Separar la excepción ETS en `requested`, `approved`, `executed`; impedir
   que solicitar cambie estado o factura.
2. Retirar las implementaciones duplicadas del router ETS después de pruebas
   de caracterización HTTP y dejar `services/service_orders.py` como autoridad.

## P1 — Antes de Producción

1. Propagar actor obligatorio a todas las mutaciones y validar auditoría.
2. Reconciliar Catálogo institucional, inventario HTTP, permisos internos y
   permisos del Portal hasta que el gate pase.
3. Sesiones revocables, refresh rotation, MFA privilegiado, recuperación de
   contraseña y rate limiting distribuido.
4. Actualizar `nanoid`/`postcss` y añadir SCA/secret scanning.
5. Dejar Calidad como único autenticador de certificados.
6. Cerrar Hojas→Captura→Calidad→Certificados con 23 plantillas y E2E real.
7. Completar CFDI: Producción, cancelación/sustitución, PPD/complemento, nota
   fiscal de egreso, conciliación/retries y evidencia Sandbox.
8. Conectar correo institucional del Portal con outbox/retry/telemetría.
9. Implementar storage durable, backup/retención y decisión antimalware.
10. CI/CD, despliegue declarativo, readiness de BD/storage/LibreOffice/PAC/
    worker, métricas, tracing, alertas y runbooks RPO/RTO.
11. E2E browser por rol/tenant y macroflujos comerciales/operativos/fiscales.

## P2 — Deuda importante

1. Paginación y límites en listados `.all()`.
2. Streaming/jobs para lotes documentales según medición.
3. Integrar el productor de Fase 14 desde ETS sin duplicar composición.
4. Retirar compatibilidad OT/firmas/fiscal sólo después de medir históricos.
5. Autosave/confirmación de descarte en Workbench.
6. Converger renderer React/PDF de Hojas.
7. Fuente única de CORS/puertos/configuración.
8. Sustituir bootstrap mutante del Portal por despliegue explícito.
9. Modularizar páginas/API/CSS grandes bajo pruebas.
10. Completar Patrones, Procedimientos, Perfiles e Incertidumbre en el flujo.

## P3 — Mejoras

1. Lazy loading/code splitting y optimización de activos.
2. Sustituir `alert/confirm` nativos y automatizar accesibilidad.
3. Confirmar y retirar archivos huérfanos.
4. Actualizar integraciones deprecadas de tests/Alembic.
5. Definir Agenda, Llamados, CRM y Encuesta sólo si entran formalmente a 1.0.

## Gates recomendados hasta versión estable

| Orden | Gate | Evidencia mínima |
| ---: | --- | --- |
| 1 | Integridad ETS | pruebas HTTP de transición/excepción/auditoría y un solo servicio |
| 2 | Seguridad institucional | catálogo verde, actor íntegro, sesiones/rate limit |
| 3 | Operación técnica | 23 Hojas + Captura/Calidad/Certificados E2E |
| 4 | Operación fiscal | escenarios CFDI Sandbox completos e idempotentes |
| 5 | Portal productivo | correo, recuperación, tenant E2E y sesiones |
| 6 | Plataforma | CI/CD, observabilidad, storage, restore y runbooks |
| 7 | Auditoría de cierre | cero P0/P1 y revisión funcional por rol |

No abrir una fase nueva del Motor ni ampliar el catálogo funcional antes de
pasar los gates 1 y 2.
