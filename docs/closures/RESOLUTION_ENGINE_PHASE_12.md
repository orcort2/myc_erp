# Cierre técnico — Motor de Resoluciones Fase 12

## Estado

`APROBADA`. La revisión formal aprobó la Fase 12 mediante
`a7bf75f0f2de23faecb17276aa11d187c654a00c` y autorizó la apertura de la Fase
13 — Consolidación del Centro de Resoluciones.

## Entrega

- módulo principal `/resolutions` integrado al diseño vigente;
- API interna versionada y separada de la API pública;
- catálogo controlado y flujo guiado completo;
- proyección de lista, expediente y timeline;
- permisos explícitos para administración, operación y auditoría;
- aceptación durable, worker independiente y continuidad sin sesión web;
- polling visible/controlado;
- migración reversible `d2f4a6b8c0e3`;
- pruebas específicas de backend, frontend y arquitectura.

## Invariantes demostradas

Los routers no importan infraestructura del Motor ni mutan tablas. Workflow,
consulta, frontend y worker tienen responsabilidades distintas. Lifecycle,
Security, Orchestrator, Executor y runtime distribuido siguen siendo los
servicios canónicos. El frontend no crea estados, no ejecuta handlers y no
conserva trabajo en `localStorage`.

El despacho es único por resolución. La autoridad durable se persiste antes de
encolar y su consumo exacto no depende de la sesión HTTP. La lectura aplica
organización y propiedad, cifra/ata el cursor y redacta hashes e infraestructura
sin permiso.

## Migración

`d2f4a6b8c0e3` desciende de `c1e3f5a7b9d2`. No crea ni modifica datos de
negocio. Ajusta sólo el trigger de inmutabilidad de `resolution_plans` para
permitir estados canónicos sin permitir reescritura de contenido.

## Validaciones

- Fase 12: `11 passed`.
- Motor completo en índice exclusivo: `244 passed`.
- Backend exclusivo: `348 passed`, `20 failed`; 19 son `TD-023` y uno es el
  XLSX SAT ignorado ausente de la fotografía. Con el recurso local, su suite
  dedicada terminó `4 passed`.
- frontend: `2 passed` y build Vite correcto (`1675` módulos);
- compilación Python: correcta;
- PostgreSQL: único head `d2f4a6b8c0e3`, cadena completa,
  downgrade→upgrade correcto;
- `alembic check`: conserva exclusivamente la deriva histórica `TD-021`;
- inventario regenerado sobre el índice exclusivo y `git diff --check`
  correctos.

El detalle reproducible y el estado concurrente están en
`../BACKUP_ESTADO_ACTUAL.md`.

## Exclusiones

No se incluyeron IA, nuevos dominios, cambios de API pública/SDK, operaciones
administrativas genéricas, cancelación, desbloqueo, retry manual, edición de
evidencia o compensación manual. Los cambios concurrentes de Actividad y
Notificaciones del árbol compartido no pertenecen a esta entrega y se excluyen
del commit.
