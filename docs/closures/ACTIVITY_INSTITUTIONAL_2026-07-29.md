> Tipo: Cierre técnico
>
> Estado: IMPLEMENTADO — PENDIENTE DE REVISIÓN FORMAL
>
> Fecha: 2026-07-29

# Cierre técnico — Actividad institucional

## Entrega

- Catálogo genérico de 19 tipos de entidad.
- Conversación humana con permisos finos, menciones, edición acotada, retiro
  lógico, revisiones y auditoría.
- Adjuntos seguros y vista previa de imágenes.
- Eventos formales idempotentes desde servicios canónicos.
- Lecturas explícitas, contador no leído y bandeja Dashboard.
- Atención por usuario/área, prioridad, notificación y resolución.
- Integración reutilizable en Cliente, Cotización, ETS, Equipo, Hoja de Campo,
  Certificado/Calidad, Factura, Control Documental, Patrones, Procedimientos,
  Incertidumbre y Centro de Resoluciones.
- Notas técnicas/documentales preservadas; nota histórica de ETS sólo lectura.
- `JSONB` portable corregido en Activity y Notifications.

## Persistencia

- Head único: `8c9d0e1f2a3b`.
- PostgreSQL temporal: upgrade completo, downgrade a `7b8c9d0e1f2a` y
  re-upgrade correctos.
- PostgreSQL local: `8c9d0e1f2a3b (head)`.
- Respaldo `backup_erp_myc_antes_prueba.sql` regenerado y verificado con la
  misma `alembic_version`.
- `alembic check`: mantiene drift histórico global `TD-021`; cero operaciones
  específicas nuevas de Activity/Notifications.

## Pruebas

- Activity backend: `8 passed`.
- Backend completo: `398 passed`, `2 failed`, `19 subtests passed`. Los dos
  fallos son conversión real LibreOffice con `returncode=-6`.
- Frontend Node: incluye pruebas de rutas/capacidades de Activity.
- Build Vite: correcto; advertencia no bloqueante de chunk grande.
- Compilación Python: correcta.

## Exclusiones respetadas

- No se creó Tickets, CRM, Agenda ni Llamados.
- No se modificó ningún archivo del Motor de Resoluciones.
- No se inició una fase nueva del Motor.
- No se alteraron Lifecycle, seguridad, compensación, API Pública o SDK.
- No se migraron textos cuyo significado de dominio no era inequívoco.
