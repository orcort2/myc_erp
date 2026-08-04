> Estado: VIGENTE
>
> Tipo: Arquitectura vigente de seguridad transversal
>
> Autoridad: Alta para clasificación y enforcement HTTP
>
> Corte verificado: 2026-08-04

# Control de acceso de la API

## Regla central

Toda operación FastAPI registrada debe poder clasificarse mediante
`backend/app/security/api_access.py`. El arranque ejecuta
`assert_all_routes_classified(app)` y falla si aparece una operación sin una
categoría conocida. Además, cada router se incluye con la dependencia
`enforce_api_access`; una ruta que no puede clasificarse responde error de
configuración y nunca se degrada a acceso anónimo.

El inventario reproducible se genera con:

```bash
cd backend
../venv/bin/python ../scripts/generate_api_access_inventory.py --check \
  --output ../docs/architecture/security/API_ENDPOINT_INVENTORY_2026-08-03.csv
```

El CSV es evidencia por operación, no una fuente de autorización paralela.

## Categorías

| Categoría | Identidad/autoridad | Aplicación |
| --- | --- | --- |
| Pública intencional | ninguna | raíz, health y bootstrap/login/refresh expresamente registrados |
| Pública con token firmado | código de autenticación propio | verificación pública de certificado |
| Pública controlada por entorno | flag de configuración | portal técnico; deshabilitado por defecto |
| Autenticada | access JWT y usuario activo | sesión y superficies internas sin acción especializada |
| Autenticada con permiso | access JWT, usuario activo y permiso backend | CRUD y acciones internas |
| Autenticada con ownership | identidad más pertenencia validada por el servicio | conversaciones/recursos con alcance propio |
| Consumidor del Motor | contexto de consumidor y organización | API pública v1 del Motor; no usa la sesión interna |
| Portal cliente | access JWT, rol/permisos de portal y cliente derivado | listados y descargas aisladas por cliente |
| Administrativa | access JWT y permiso administrativo | usuarios, auditoría y configuración institucional |

## Excepciones públicas canónicas

La allowlist básica contiene exactamente seis operaciones: `GET /`,
`GET /api/health`, `GET /api/auth/registration-status`, `POST
/api/auth/register`, `POST /api/auth/login` y `POST /api/auth/refresh`. El
registro sólo permite crear el primer Administrador; después del bootstrap
responde 403.

`GET /verify/{authentication_code}` conserva su validación firmada. Las cuatro
operaciones `/api/public/resolution-engine/v1/*` conservan el
`consumer_context` propietario del Motor. `GET
/api/developers/resolution-engine` sólo existe como excepción controlada por
`ENABLE_DEVELOPER_PORTAL`; el valor por defecto es falso. Swagger, ReDoc y
OpenAPI dependen de `ENABLE_API_DOCS`, también falso por defecto.

## Autenticación interna y JWT

Sólo `token_type=access` puede resolver una identidad HTTP interna. Refresh se
acepta únicamente en renovación; tipo, firma y expiración son obligatorios, y
el usuario se vuelve a resolver desde backend para comprobar actividad y roles
vigentes. El frontend recibe permisos efectivos calculados desde los roles del
backend; no envía ni declara autoridad.

En producción `Settings` rechaza secreto ausente, conocido, de ejemplo, menor
de 32 caracteres, con baja diversidad o con menos de 100 bits de entropía
estimada. Desarrollo puede usar el valor local explícito y el arranque emite
una advertencia sin imprimirlo.

## Portal cliente y ownership

El portal no acepta `client_id`. La identidad debe tener rol `Cliente` activo y
`portal.read`. El backend normaliza el correo del usuario y exige que corresponda
a exactamente un cliente activo, sea por correo principal o contacto activo.
Cero o múltiples coincidencias fallan con 403; esta resolución fail-closed
evita seleccionar tenant desde HTTP sin introducir una migración en esta etapa.

Este mecanismo por correo es una compatibilidad transitoria de la Etapa 1, no
la autoridad definitiva. La siguiente etapa deberá migrarlo a la relación
persistente y auditable `User`–`PortalMembership`–`Client`, conservando la
resolución backend, el fail-closed y el ownership por recurso.

Todos los listados se filtran por el cliente derivado. La descarga de certificado
comprueba primero `certificate.service_order.client_id`, visibilidad y archivo;
una referencia ajena responde 404 para no revelar existencia. Una descarga
válida registra usuario, certificado y folio en auditoría.

## Códigos de respuesta

- `401`: bearer ausente, inválido, expirado, refresh usado como access o usuario
  inactivo.
- `403`: identidad válida sin permiso, rol de portal o vínculo único.
- `404`: recurso de otro cliente/no visible o excepción de entorno deshabilitada.
- `500`: ruta registrada sin clasificación; además, el test de conformidad y el
  arranque impiden aceptar ese estado.

## Frontend

`UserRead.permissions` es la fuente de capacidades presentada a la UI.
`frontend/src/utils/accessControl.js` filtra navegación, tarjetas de Dashboard,
secciones administrativas y acciones sensibles. La navegación directa muestra
`AccessDenied`; una respuesta backend 403 se traduce a un mensaje claro. Estos
controles reducen confusión, pero el backend continúa siendo la única autoridad.

## Límites explícitos

Esta etapa no cambia almacenamiento de tokens, rotación/revocación/jti, rate
limit, MFA, uploads, esquema ni migraciones. Esos controles permanecen en el
registro canónico de deuda y no reducen el enforcement aquí documentado.

Tampoco implementa el modelo administrable de permisos. La matriz de
`permissions.py` continúa como bootstrap/compatibilidad y el catálogo
institucional del 2026-08-04 sólo puede alimentar el diseño posterior después
de revisión; no autoriza cambios automáticos de claves ni reglas vigentes.
