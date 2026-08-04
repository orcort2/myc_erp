> Estado: APROBADA Y CERRADA
>
> Fecha de cierre técnico: 2026-08-03
>
> Fecha de aprobación formal: 2026-08-04
>
> Alcance: contención transversal de seguridad, sin cambios de esquema

# Cierre técnico de Contención de Seguridad — Etapa 1

## Dictamen formal

**ETAPA 1 — APROBADA Y CERRADA.** Los seis commits fueron revisados en orden,
la evidencia sigue correspondiendo al alcance autorizado y las suites completas
continúan correctas. No se identificó una regresión ni un pendiente funcional
dentro de la contención comprometida. Este dictamen no amplía la etapa, no
aprueba cambios de esquema y no convierte los diseños de autoridad posteriores
en implementación vigente.

## Resultado

Se cerró el bloque ejecutable de AUD-001, AUD-002 y AUD-003. La API interna
quedó bajo deny-by-default, el portal deriva y valida su cliente sin aceptar un
tenant del request, el IDOR de PDF devuelve 404 seguro y producción rechaza un
secreto JWT inseguro. AUD-011 quedó cerrado para navegación y acciones
principales; AUD-013 quedó cerrado para la matriz HTTP automatizada de esta
etapa. AUD-010 conserva fuera de alcance la revocación/rotación y el
almacenamiento en `localStorage`.

## Evidencia de clasificación

| Categoría | Operaciones finales |
| --- | ---: |
| Pública intencional | 6 |
| Pública firmada | 1 |
| Pública controlada por entorno | 1 |
| Consumidor API Motor | 4 |
| Autenticada | 6 |
| Autenticada con permiso | 270 |
| Autenticada con ownership | 5 |
| Portal con ownership | 4 |
| Administrativa | 9 |
| **Total** | **306** |

El corte anterior reportó 74 operaciones públicas/no protegidas y 15 con actor
opcional. El corte actual tiene seis públicas básicas; al sumar verificación
firmada, portal técnico controlado por entorno y Motor con seguridad propia hay
12 excepciones intencionales. No queda una dependencia de usuario opcional en
routers internos; sólo existe el extractor bearer opcional sin autoridad que
necesita el guard central para distinguir público de 401.

## Controles implementados

- clasificación canónica por operación y prueba que falla con una ruta nueva;
- guard transversal aplicado al incluir todos los routers;
- permisos backend ampliados para capacidades ya existentes y actor obligatorio
  en Cotizaciones/ETS;
- bootstrap público limitado al primer Administrador;
- tipos access/refresh estrictos, firma/expiración/usuario activo verificados;
- validación productiva de longitud, diversidad y entropía de `SECRET_KEY`;
- portal `Cliente` con vínculo único fail-closed, filtros por cliente, ownership
  en descarga y auditoría de accesos válidos;
- navegación, Dashboard, Ajustes, Centro de Resoluciones, Facturación, Clientes,
  Cotizaciones y liberación de Certificados condicionados por permisos efectivos;
- mensajes diferenciados para 401, 403 y fallo de red.

## Validaciones

| Validación | Resultado |
| --- | --- |
| Suite backend completa | 427 passed, 19 subtests passed, 2 warnings |
| Seguridad dirigida | 22 passed |
| Frontend completo con `node --test` | 31 passed |
| Build Vite | correcto; warning preexistente de chunk >500 kB |
| Inventario/conformidad | 306/306 clasificadas; CSV coincide con runtime |
| Dos clientes/IDOR | A→A 200, A→B 404, B→B 200, B→A 404; anónimo 401 |
| Compilación Python | correcta |
| Búsqueda de sesión opcional | sin dependencia opcional de usuario en routers |
| Migraciones/esquema/base compartida | no modificados ni ejecutados |

La aprobación formal del 2026-08-04 repitió la suite backend completa, las 31
pruebas frontend, el build Vite y el gate de inventario. Los resultados fueron
idénticos a los del cierre técnico: 427 pruebas backend y 19 subtests, 31
pruebas frontend y 306/306 operaciones clasificadas.

## Hallazgos críticos cerrados por evidencia

| Hallazgo | Dictamen | Evidencia de cierre |
| --- | --- | --- |
| AUD-001 — API interna sin deny-by-default | **CERRADO** | `8f71f0b`; guard transversal, clasificación 306/306, arranque fail-closed y prueba de conformidad. |
| AUD-002 — Portal global e IDOR PDF | **CERRADO** | `00a1ccd` y `54c935c`; identidad Cliente, filtro SQL por tenant, ownership, 404 seguro y pruebas A→B/B→A. |
| AUD-003 — JWT arranca con secreto conocido | **CERRADO** | `27c0b67` y `54c935c`; validación productiva de secreto y pruebas de configuración/tipos JWT. |

El cierre de AUD-002 acredita la contención implementada sin migraciones. No
declara definitivo el vínculo por correo: la sustitución por `PortalMembership`
es una evolución arquitectónica obligatoria de la siguiente etapa.

Los dos warnings backend son deprecaciones de Starlette/httpx y passlib/crypt;
no son fallos de la etapa. El warning Vite corresponde al tamaño del bundle y
permanece fuera del alcance autorizado.

## Riesgos que permanecen fuera de esta etapa

- access/refresh siguen en `localStorage`; no hay jti, rotación, revocación,
  recuperación de contraseña ni MFA;
- no se implementó rate limiting;
- el vínculo del portal se resuelve contra correo principal/contacto porque una
  FK nueva requeriría migración; la ambigüedad se deniega;
- uploads, CORS, CI/CD, observabilidad, CFDI y deuda de esquema permanecen para
  sus etapas propias.

Estos riesgos no impiden el cierre de la contención acotada. Mantienen su
prioridad en el canon general del proyecto y deberán abrirse con alcance,
migraciones y validaciones propios cuando corresponda.

## Decisiones trasladadas a la siguiente etapa

1. El correo deja de ser la autoridad definitiva del portal. La siguiente
   etapa debe diseñar y migrar una relación persistente, auditable y explícita
   `User`–`PortalMembership`–`Client`, sin aceptar el tenant desde el request.
2. Ajustes deberá administrar roles y grupos como conjuntos de permisos,
   múltiples asignaciones por usuario, concesiones y denegaciones individuales,
   alcances por registro, permisos temporales y protección de roles/capacidades
   críticas.
3. `CATALOGO_INSTITUCIONAL_CAPACIDADES_PERMISOS_ERP_MYC_2026-08-04.md` se adopta
   como insumo funcional de diseño. Sus permisos propuestos requieren revisión,
   reconciliación y aprobación; no se aplican automáticamente al código.
4. `backend/app/core/permissions.py` permanece como bootstrap ejecutable y capa
   de compatibilidad temporal, no como modelo administrativo definitivo.

Estas decisiones son trabajo posterior obligatorio y no defectos omitidos de
la Etapa 1. Su implementación deberá abrir una etapa separada; este cierre no
crea modelos, migraciones, CRUD de Ajustes ni nuevas claves de permiso.

## Archivos de evidencia primaria

- `backend/app/security/api_access.py`
- `backend/app/services/client_portal.py`
- `backend/tests/test_api_access_conformity.py`
- `backend/tests/test_security_containment_stage_1.py`
- `docs/architecture/security/API_ENDPOINT_INVENTORY_2026-08-03.csv`
- `docs/architecture/security/API_ACCESS_CONTROL.md`

Los commits formalmente revisados son `27c0b67`, `8f71f0b`, `00a1ccd`,
`0f2d3e8`, `54c935c` y `6b6ae2d`. Con la repetición satisfactoria de pruebas y
la aceptación expresa del alcance, este documento acredita tanto terminación
técnica como aprobación formal: **ETAPA 1 — APROBADA Y CERRADA**.
