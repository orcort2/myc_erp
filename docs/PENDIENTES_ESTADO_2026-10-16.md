# ERP MYC — Estado consolidado de pendientes

**Corte:** 2026-10-16  
**Alcance:** seguimiento operativo y de desarrollo.  
**Fuente de verdad técnica:** código, migraciones, pruebas y despliegue real; este documento no sustituye una auditoría de producción.

> Convención: **Cerrado en Git** significa merge comprobado en `main`, no despliegue ni QA en producción. **Por verificar** significa que no hay evidencia suficiente para declararlo resuelto. **Pendiente** significa que todavía requiere trabajo o validación.

## Prioridad principal

| Tema | Estado al corte | Próxima acción verificable |
| --- | --- | --- |
| Correo institucional ERP y recuperación de contraseña | **EMAIL-1/entrega real confirmadas; recuperación pendiente principal** | SMTP productivo y entrega a bandejas confirmados el 2026-10-13: Windows MYC → WireGuard → Vultr/Postfix (10.77.0.1:25) → Google Workspace Relay (smtp-relay.gmail.com:587, TLS). `EMAIL_ENABLED=true`, `MYCBackend` reiniciado/Running. Falta validar el ciclo completo de `forgot-password` → correo → enlace → `reset-password` → acceso nuevo y revocación de sesiones. No repetir auditoría SMTP sin fallo nuevo. |
| Auditoría y cierre funcional de facturación/pagos | **Pendiente principal / por verificar** | Revisar casos P0, estados CFDI y pagos, consistencia cotización → ETS → factura, y condiciones de cierre. Validar con datos reales antes de tocar BD. |
| Pendiente principal identificado como punto 6 en recuento del 2026-10-06 | **Por identificar y verificar** | Recuperar el enunciado original antes de implementar; el recuento indica expresamente «verificar antes de continuar», pero no describe aquí el tema. |
| Pendiente principal identificado como punto 9 en recuento del 2026-10-06 | **Por identificar** | Recuperar el enunciado original y criterios de aceptación; no inventar alcance. |

## Facturación — cambios recientes

| Cambio | Estado comprobado | Lo que falta |
| --- | --- | --- |
| Descripción fiscal comercial derivada de cotización, preservando descripción persistida | **Integrado en `main`** — PR #23, merge `94998d1` | QA con borradores existentes, confirmación de payload y representación fiscal real; comprobar que no se sobreescriban personalizaciones. |
| Eliminación del campo editable «Descripción fiscal del concepto» | **Integrado en `main`** — PR #23 | Verificar interfaz desplegada. |
| Modal de correo de facturas alineado visualmente con cotizaciones | **Integrado en `main`** — PR #23 y PR #24, merge `24d52ec` | QA visual en producción, interacción de destinatarios, Para/CC, vista previa, borrador/timbrada y adjuntos. |
| Folio duplicado `MYCF-MYCF-...` en encabezado del modal | **Corrección integrada en `main`** — PR #24 | Verificar después del despliegue. |
| Descripciones de facturas históricas/borradores | **Por verificar** | Se realizaron intervenciones SQL sobre borradores concretos en una sesión anterior; no consta aquí validación definitiva de `COMMIT`, respuesta API ni visualización final. No repetir SQL sin consulta previa. |
| Despliegue de PR #23 y #24 al ERP público | **No verificado** | Comprobar versión/commit efectivamente servido por producción antes de atribuirle el nuevo comportamiento. |

**Aclaración operativa (2026-10-16):** el usuario confirma recepción real en bandejas y solicita dejar SMTP/entrega como resueltos. El pendiente principal de correo queda limitado a validar recuperación de contraseña.\n\n**Evidencia reciente:** build frontend Vite correcto, 1,767 módulos; pruebas focales de descripción fiscal 3/3. Esto no sustituye pruebas de envío SMTP ni QA de producción.

## LAB, MYC Mobile y operación documental

| Tema | Estado | Próxima acción |
| --- | --- | --- |
| Selección de modalidad individual/grupal en creación de grupos LAB internos | **Por verificar integración** | Revisar rama `fix/mobile-lab-group-workflow-selection`, diff, commit, merge, build distribuido y QA de grupo mixto; el snapshot del 2026-10-06 la describía sin commit. |
| Regreso de hoja de campo al foreground | **Corrección documentada; cierre de despliegue por verificar** | Confirmar versión de Mobile distribuida y prueba física para los escenarios relevantes. El snapshot incluye QA iOS favorable para un caso posterior. |
| MYC Mobile iOS / TestFlight | **Build subido según seguimiento del 2026-10-06** | Verificar versión disponible, revisión/distribución y QA; «subido» no equivale a publicado. |
| Reporte técnico de instalación en servicio general | **Implementación inicial documentada; no cerrado** | Verificar migración, alta/edición, evidencias, firmas, PDF, folio institucional, permisos y despliegue. |
| Regeneración de documentos de OT tras cambios autorizados de BD | **Pendiente funcional** | Diseñar botón «Regenerar documento» con permisos, auditoría, validación de cambios, versiones y protección contra alteración de documentos liberados. |
| PDF/OT concretas intervenidas en producción | **Por verificar por OT** | Comprobar PDF vigente tras modificaciones de folios/equipos. En seguimiento previo se reportaron regeneraciones de 6501/6502/6506 y pendientes 6504/6505; no asumir que siguen pendientes sin consultar. |
| Integración ETS ↔ LAB y paridad administrativa | **Avances documentados; cierre integral por verificar** | Contrastar ramas/commits actuales con contrato funcional y validación física. |

## Prioridad secundaria y seguimiento

| Tema | Estado | Próxima acción |
| --- | --- | --- |
| Pendiente secundario identificado como punto 10 del recuento del 2026-10-06 | **Prioridad media; alcance por recuperar** | Localizar descripción original y registrar criterio de cierre. |
| Pendiente identificado como punto 7 del recuento del 2026-10-06 | **Necesita contexto** | Aclarar el alcance antes de priorizar. |
| Acceso remoto privilegiado al servidor Windows | **Diseño/propuesta, no cierre comprobado** | Validar arquitectura de broker, controles de privilegios, auditoría, expiración y revocación antes de exposición. |
| Advertencia Vite por bundles >500 kB | **No bloqueante** | Optimización de rendimiento separada; no mezclar con correcciones funcionales P0. |

## Temas declarados cerrados en el recuento del 2026-10-06

El seguimiento del usuario marcó como **cerrados** los puntos **1, 5, 8, 11 y 13**; el **2** correspondía a un problema de uso/acceso, **no a un bug**; el **4** era el mismo trabajo de correo/restablecimiento del punto 3. No reabrirlos sin evidencia nueva. Los puntos **14 en adelante** no están íntegramente identificados en este corte y requieren contraste con su texto original.

## Reglas de mantenimiento

1. No equiparar `commit`, `push`, `merge`, `deploy`, QA y cierre operativo.
2. No declarar corregidos incidentes de producción solo por cambios de código.
3. No editar datos de producción ni regenerar documentos fiscales/operativos sin consulta previa, autorización y trazabilidad.
4. Mantener cambios Git por alcance acotado y registrar PR, commit de merge, despliegue, pruebas y responsable de validación.
5. Actualizar este corte cuando se confirme un hecho nuevo, sin borrar los snapshots históricos de `docs/BACKUP_ESTADO_ACTUAL.md`.
