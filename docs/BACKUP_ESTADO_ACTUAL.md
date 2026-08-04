> Estado: VIGENTE
>
> Tipo: Vigente (estado operativo verificable)
>
> Autoridad: Media; no sustituye los documentos canónicos de `project/`
>
> Corte actualizado: 2026-08-04

# Estado operativo actual del ERP MYC

## Dictamen del corte

- Versión declarada: `0.4.0`.
- Estado canónico de módulos: [`project/PROJECT_STATUS.md`](project/PROJECT_STATUS.md); no fue modificado por la auditoría diagnóstica.
- Auditoría integral vigente: [`audits/AUDITORIA_INTEGRAL_ERP_MYC_2026-08-03.md`](audits/AUDITORIA_INTEGRAL_ERP_MYC_2026-08-03.md).
- Dictamen técnico del corte: **NO APTO PARA PRODUCCIÓN**, 49/100.
- Hallazgos: 40 (3 críticos, 13 altos, 18 medios, 4 bajos y 2 informativos).
- La Contención de Seguridad Etapa 1 cerró API sin protección uniforme, portal
  sin aislamiento y secreto JWT productivo inseguro; la revisión de sus seis
  commits y la repetición de pruebas emitieron el dictamen **APROBADA Y
  CERRADA** el 2026-08-04.
- La Etapa 2A corrigió y validó la integridad de esquema y recuperación; la
  Etapa 2B formalizó el snapshot técnico del Catálogo Institucional. La
  validación funcional posterior revisó 36 módulos, 213 acciones y 798 filas y
  produjo el catálogo objetivo de 42 módulos, 181 acciones y 657
  microacciones. Su nomenclatura fue revisada completamente para expresar
  decisiones de negocio comprensibles por administración funcional y la
  versión 1.0 quedó **APROBADA Y CONGELADA COMO AUTORIDAD FUNCIONAL**, con
  naturaleza, criticidad y alcance en las 657 microacciones, sin implementar
  administración dinámica de accesos ni cambiar permisos vigentes.
- Bloqueadores dominantes restantes: sesiones sin revocación/rotación, CFDI
  productivo incompleto y ausencia de CI/E2E/observabilidad; almacenamiento
  durable y antimalware requieren decisión operativa posterior a ETAPA 3.
- ETAPA 3 de archivos y cargas quedó **TERMINADA, EN REVISIÓN**: centraliza
  perfiles, ZIP/Office/PDF/XML/imagen, escritura atómica y entrega contenida;
  retiró datos operativos/dump del índice sin borrar evidencia local.
- El Portal del Cliente quedó **TERMINADO, EN REVISIÓN** con autenticación
  externa separada, registro/verificación, invitaciones, membresías y roles
  propios, aislamiento persistente por cliente, administración interna y
  experiencia frontend. Correo productivo, MFA, recuperación y revocación de
  sesiones permanecen pendientes explícitos.

## Árbol de trabajo preservado

Al inicio de la Etapa 2 ya existían cambios y archivos no rastreados en
frontend, documentación comprimida, auditorías y storage. Se preservaron como
trabajo previo o concurrente y no forman parte de esta etapa.

Las tres migraciones locales pendientes fueron revisadas y adoptadas
oficialmente en la cadena lineal:

- `backend/migrations/versions/c14c5d6e7f80_fix_quotation_service_change_timestamps.py`
- `backend/migrations/versions/d15d6e7f8091_fix_notification_timestamp_defaults.py`
- `backend/migrations/versions/e16e7f8091a2_fix_institutional_folio_timestamp_defaults.py`

Sobre ellas se agregó `f27f8a90b1c3_reconcile_schema_integrity.py`, nuevo head
único y reversible.

## Persistencia y migraciones

- Motor: PostgreSQL, SQLAlchemy y Alembic.
- Head único oficial: `bd2270bc5282`.
- Base local compartida: migrada y verificada en `bd2270bc5282`.
- `alembic check`: **LIMPIO** tanto en la base local como en bases aisladas.
- Ciclo completo vacío `base → head → base → head`: **CORRECTO** en PostgreSQL
  aislado mediante `scripts/toolkit/db/validate-schema-cycle.sh`.
- Upgrade desde el respaldo histórico en `b03b4c5d6e7f` hasta el head:
  **CORRECTO**, con 102 tablas públicas y `alembic check` limpio.
- Se añadieron defaults de servidor `now()` a 16 columnas NOT NULL
  `created_at`/`updated_at` en ocho tablas:
  - `activity_attention_requests`
  - `activity_thread_reads`
  - `linked_companies`
  - `uncertainty_calculations`
  - `uncertainty_components`
  - `uncertainty_formulas`
  - `uncertainty_model_exceptions`
  - `uncertainty_models`
- Se reconciliaron índices y columnas faltantes del ORM; los índices parciales,
  de expresión y de búsqueda administrados deliberadamente por migraciones
  quedaron excluidos de autogeneración mediante una lista explícita.
- Se corrigieron downgrades históricos de firmas de ETS y la denominación de
  una FK de cotizaciones para asegurar la reversibilidad de la cadena completa.

## Respaldo oficial

- Archivo: `backup_erp_myc_antes_prueba.sql`.
- Tamaño: 74,261,144 bytes.
- `alembic_version` contenido: `bd2270bc5282`.
- SHA-256: `733f3eeaf0da12f0d8b9e5912c6e851fec1b9ade49090487f23a9b12b4ac019b`.
- Estado: **ALINEADO CON EL HEAD OFICIAL**.
- Restore drill: **CORRECTO** en PostgreSQL aislado; restauró 102 tablas,
  confirmó la revisión y dejó `alembic check` limpio. El procedimiento
  reproducible está en `architecture/database/SCHEMA_RECOVERY.md` y el comando
  ejecutable en `scripts/toolkit/db/restore-drill.sh`.

## Validaciones ejecutadas

| Validación | Resultado |
| --- | --- |
| Backend `PYTHONPATH=backend venv/bin/pytest -q backend/tests` | 444 passed, 19 subtests, 3 warnings |
| Pruebas dirigidas ETAPA 3 | 78 passed, 7 subtests |
| Pruebas dirigidas de integridad de esquema | 3 passed, 1 warning deprecado de configuración Alembic |
| Pruebas dirigidas de seguridad | 22 passed |
| Frontend `node --test` | 31 passed |
| Frontend `npm run build` | correcto; warning de chunk >500 kB |
| Backend `compileall` | correcto |
| Inventario FastAPI | 344/344 operaciones clasificadas; CSV coincide con runtime |
| Aislamiento portal A/B | membresía propia 200, recurso ajeno 404, anónimo 401; autenticador interno rechaza token del portal |
| `scripts/myc doctor` | dependencias locales principales disponibles |
| Alembic ciclo vacío base→head→base→head | correcto en PostgreSQL aislado |
| Alembic upgrade desde respaldo histórico | correcto; b03→f27, 102 tablas |
| Alembic check | limpio en local, ciclo y restores aislados |
| Restore del respaldo oficial regenerado | último drill integral correcto en el corte f27; no repetido tras las migraciones ya aplicadas del portal |
| Validador Catálogo Institucional/permissions/API | correcto (`--check`) |
| Conteo Catálogo Funcional | 42 módulos, 181 acciones, 657 microacciones; IDs de acción únicos |
| Metadatos Catálogo Funcional | 657/657 con naturaleza, criticidad y alcance; alineación completa |
| Identidad y permisos del catálogo | microacciones, marcas y celdas de permisos sin cambios frente al corte previo a metadatos |
| `npm audit --omit=dev` | 1 vulnerabilidad alta PostCSS |
| `pip check` | correcto |
| Vulnerabilidades Python | NO VERIFICADAS; `pip-audit` ausente |
| `git diff --check` acotado a Etapa 2 | limpio; el árbol completo conserva espacios finales preexistentes en CSS ajeno a la etapa |

La evidencia histórica de auditoría se conserva en
[`audits/evidence/AUDITORIA_COMANDOS_2026-08-03.txt`](audits/evidence/AUDITORIA_COMANDOS_2026-08-03.txt);
los comandos vigentes de recuperación se documentan en
[`architecture/database/SCHEMA_RECOVERY.md`](architecture/database/SCHEMA_RECOVERY.md).

## Estado funcional verificable

- El ERP implementa clientes, catálogo, cotizaciones, ETS, OT, equipos, Hojas de Campo, Captura, Calidad, Certificados, Facturación, pagos, cartera, control documental, patrones, incertidumbre, Actividad, comunicaciones y ajustes con grados diferentes de cierre.
- Control Documental V1 conserva el único estado canónico `SELLADO`, dentro de su alcance acotado; la seguridad transversal impide inferir aptitud productiva.
- El Workbench de Facturación reutiliza el controlador único, el agregado `Invoice`, el contexto explícito y `EtsBillingTab`.
- Servicios Compuestos usa `service_kind`, `catalog_item_components` y expansión al crear ETS.
- La acreditación de calibración mantiene las claves canónicas del contrato.
- Facturación dispone de borrador, snapshots, intentos PAC, XML/PDF, pagos y cartera, pero Facturama está configurado para Sandbox y faltan cancelación/sustitución, PPD/complemento y nota fiscal de egreso.
- Actividad implementa threads, mensajes, menciones, adjuntos, atención y no
  leídos; sus defaults de BD quedaron alineados y permanece pendiente la
  operación externa/observable.
- El Motor de Resoluciones tiene núcleo versionado, lifecycle, seguridad, idempotencia, locks, compensación, auditoría, outbox, cola/worker, API y SDK. Sólo dos definiciones están instaladas; la Fase 14 sigue pendiente de dictamen formal y el inicio desde módulos de origen no está cerrado.

## Seguridad y operación

- Inventario introspectado: 306 operaciones HTTP; 6 públicas básicas, 1
  verificación pública firmada, 1 portal técnico controlado por entorno, 4 de
  consumidor del Motor, 6 autenticadas, 270 con permiso, 5 con ownership
  interno, 4 de portal con ownership y 9 administrativas.
- Toda ruta interna pasa por el guard deny-by-default y el arranque/prueba de
  conformidad fallan si aparece una operación sin clasificación.
- Clientes, Catálogo, Cotizaciones, ETS y Equipos exigen access JWT y permiso
  mínimo; no queda dependencia opcional de usuario en routers internos.
- Portal exige rol Cliente, `portal.read` y vínculo único derivado en backend;
  filtra listados, rechaza PDF ajeno con 404 y audita descargas propias.
- Producción rechaza secreto JWT ausente, conocido, corto o de entropía
  insuficiente; desarrollo permite el valor local explícito con advertencia.
- Refresh no autentica como access, access no renueva como refresh, el tipo es
  obligatorio y usuario inactivo/firma/expiración se rechazan.
- Navegación y acciones principales consumen permisos efectivos retornados por
  backend; acceso directo muestra denegación y 403/red tienen mensajes claros.
- Access/refresh se guardan en `localStorage`; no existe revocación/rotación formal de sesiones.
- Captura, imports, Actividad, Masters, PDFs y constancias comparten perfiles
  con tamaño, MIME, estructura y defensas ZIP; Facturama valida XML/PDF antes
  de publicar y las escrituras persistentes integradas son atómicas.
- No existe CI/CD, E2E browser, despliegue declarativo, readiness real,
  métricas, tracing ni alertas. El restore drill local ya está documentado y
  validado, pero aún debe incorporarse a la operación periódica automatizada.

## Pendientes obligatorios antes de producción

1. Programar las etapas posteriores de autoridad (`PortalMembership` y RBAC
   administrable) y sesiones/rate limit; AUD-001, AUD-002 y AUD-003 quedaron
   cerrados formalmente por evidencia sin ampliar la Etapa 1.
2. Someter cualquier capacidad nueva al flujo Catálogo → revisión funcional →
   permiso institucional; no agregar claves directamente a `permissions.py`.
3. Diseñar en una etapa posterior RBAC administrable y `PortalMembership`, sin
   confundirlos con defectos pendientes de las Etapas 1 o 2.
4. Aprobar la custodia durable/antimalware posterior; ETAPA 3 ya protegió
   uploads y retiró datos operativos del índice conservando evidencia local.
5. Completar CFDI productivo y E2E de ETS→Certificado y Facturación→Pago.
6. Incorporar CI, observabilidad, despliegue reproducible y ejecución periódica del restore drill.
7. Mantener el inventario/conformidad de rutas y completar E2E browser por rol.

## Documentación de este corte

La auditoría conserva sus diez entregables como fotografía histórica. La Etapa
2A agregó el contrato de recuperación, el cierre técnico, la migración de
reconciliación y scripts reproducibles; migró la base local y regeneró el
respaldo oficial. La Etapa 2B actualizó el Catálogo Institucional, documentó las
brechas contra bootstrap/API y agregó un validador sin cambiar claves ni
comportamiento de autorización. La validación funcional posterior separó ese
snapshot de la autoridad objetivo, retiró 493 campos sintéticos del plano de
capacidades y documentó diferencias, propuestas y reservas. Se sincronizaron
decisiones, observaciones, alcance, estado canónico, índice e inventario
oficial. La revisión semántica posterior reformuló únicamente los nombres
funcionales de los 42 módulos, 181 acciones y 657 microacciones, conservando
identificadores y permisos. La aprobación institucional posterior clasificó
las 657 microacciones, congeló la versión 1.0, estableció versionado estable y
creó su cierre documental; flujo, reglas y deuda se revisaron sin requerir
cambios.
ETAPA 3 agregó el inventario de superficies, tres contratos de archivos y el
cierre técnico; sincronizó alcance, decisiones, observaciones, deuda, estado,
índice e inventario. No modificó esquema ni datos y, por ello, no regeneró el
respaldo oficial: el archivo local conserva 74,539,344 bytes y head
`f27f8a90b1c3`, aunque ya no se versiona en Git.
