> Estado: VIGENTE — EN REVISIÓN
>
> Tipo: Arquitectura vigente
>
> Corte de autenticación BIOMETRIC-1: 2026-09-21

# Contexto de seguridad de MYC Mobile

## Frontera

`User` continúa como identidad única. MYC Mobile admite dos actores sin mezclar
sus autoridades:

```text
internal → roles/permisos internos → scope staff vigente
client   → ClientPortalMembership → roles/permisos externos → un Client
```

No existen `MobileUser`, técnico externo ficticio ni roles internos asignados a
clientes. El permiso `mobile.access` sólo abre la sesión Mobile; cada operación
exige además su capacidad concreta.

## Autenticación y tokens

La autoridad vive en `backend/app/core/mobile/security.py`. Login, refresh,
logout y `/me` conservan `User`, los permisos actuales y el scope
`internal`/`client`. Web y Portal no cambian. El access JWT Mobile incorpora
`auth_context`, `actor_type`, `mobile_session_id` y, para cliente,
`membership_id`/`client_id`. Los claims no conceden scope: se revalidan usuario,
membresía, cliente y permisos en DB. El ID de sesión se valida también contra
usuario, dispositivo, vigencia, revocación y scope persistido.

### Dispositivo y sesión — BIOMETRIC-1

- `MobileTrustedDevice` (`mobile_trusted_devices`) identifica una instalación
  presentada por usuario: UNIQUE `(user_id, device_uuid)`, plataforma iOS/Android,
  metadata y fechas UTC de confianza, uso y revocación. Un registro inactivo o
  revocado nunca se reactiva por login ni migración. `trusted_at` no constituye
  atestación de hardware ni autenticación biométrica.
- `MobileAuthSession` (`mobile_auth_sessions`) representa una generación de
  refresh, asociada a usuario, dispositivo, familia UUID y scope congelado.
  El refresh de 48 bytes aleatorios (`secrets.token_urlsafe`) se entrega una
  sola vez; DB conserva SHA-256, nunca el valor original. El primer registro
  migrado conserva además el hash único del JWT legacy ya consumido.
- Cada login crea una familia nueva. Rotar conserva familia, dispositivo,
  actor, membresía, cliente y vencimiento absoluto; no extiende la vida de la
  familia. Login usa el TTL refresh vigente; una migración conserva el `exp`
  legacy. El TTL access global de ocho horas permanece intacto.
- Cada rotación bloquea primero el dispositivo y después la generación con
  `SELECT ... FOR UPDATE`, crea un único sucesor, revoca el anterior y enlaza
  `replaced_by_id` en la misma transacción. El access anterior deja de ser válido.
  Un refresh consumido marca `reuse_detected_at` y revoca toda la familia antes
  de devolver 401. El bloqueo del dispositivo serializa también logout y reuse
  contra rotaciones de descendientes, incluso entre workers PostgreSQL.
- Los registros consumidos se conservan para detectar reuse. Esta fase no
  incorpora un job de eliminación. La autoridad es PostgreSQL; SQLite se usa
  únicamente en pruebas funcionales sin garantía de locks equivalentes.

### Contratos HTTP

Prefijo `/api/mobile/v1/auth`:

| Operación | Entrada | Respuesta / reglas |
| --- | --- | --- |
| POST `/login` | email, password, device obligatorio | 200 con access_token, refresh_token opaco, token_type=bearer, user. Conserva lock policy y reglas de login. |
| POST `/refresh` opaco | Sólo refresh_token | 200 con rotación. `device` incluso null se rechaza con 422; nunca reasigna el dispositivo. |
| POST `/refresh` legacy | refresh_token JWT + device obligatorio | 200 si migra dentro de la ventana y nunca fue consumido; sin device, 422. |
| POST `/logout` | Bearer access Mobile ligado a sesión; sin payload | 204 tras revocar exclusivamente la familia actual. No revoca otras familias ni el dispositivo. |
| GET `/me` | Bearer access Mobile | Contrato de usuario existente, sujeto a revalidación de sesión. |

`MobileSecurityDeviceInput` se reutiliza en login y migración: `device_uuid`
UUID normalizado, `platform=ios|android`, `device_name` nullable de hasta 160
caracteres y `app_version` nullable de hasta 40. La clasificación JWT usa los
tres segmentos base64url del formato compacto; no sustituye validación de
firma, tipo, expiración ni contexto. Se rechaza base64url no canónico de la
firma legacy para impedir que otra codificación del mismo JWT eluda el hash
de consumo único. Los fallos de credencial, sesión,
vencimiento, dispositivo o permisos en refresh devuelven el mismo 401 genérico.

### Compatibilidad legacy temporal

La extensión de `MobileRefreshTokenRequest.device` fue autorizada expresamente.
La transición acredita **posesión de un refresh JWT legacy válido y un UUID
presentado por la instalación actual**. El sistema histórico no permite probar
que ese UUID corresponda al dispositivo que obtuvo originalmente el JWT.
Nunca se infiere desde PushDevice ni se crea un dispositivo ficticio.

El fallback sólo admite los contextos que ya autorizaba Mobile:
`mobile_internal`, `mobile_client` y `internal` para usuarios internos; este
último conserva exclusivamente la compatibilidad Web histórica ya existente.
No admite Portal ni cliente por la vía interna. No emite nuevos refresh JWT.
El JWT firmado no puede contener `mobile_session_id`. Debe estar vigente y su
`exp` no puede superar `LEGACY_REFRESH_DEADLINE`, fijado en
**2026-10-22 00:00 UTC**; desde esa fecha se rechaza toda migración legacy.
La fecha nunca se desplaza al reiniciar. Retirar el fallback tras esa ventana.

El hash legacy único, con lock de usuario `FOR NO KEY UPDATE`, permite una sola migración total,
aunque se presente otro UUID o lleguen requests concurrentes. Este lock es
compatible con las FKs de nuevas generaciones para evitar deadlock con un
refresh concurrente que ya bloqueó el dispositivo. Repetirlo revoca
la familia migrada y devuelve 401. Los access antiguos sin ID de sesión mantienen
su compatibilidad hasta su expiración; no es posible revocarlos retrospectivamente
por dispositivo. Logout server-side requiere un access de la autoridad nueva.

### Mobile y concurrencia

`security-device.ts` genera `Crypto.randomUUID()` y persiste mediante
`expo-secure-store` bajo `myc.security.device_uuid.v1` antes del login o refresh
legacy. La creación concurrente comparte una promesa. Logout no borra este UUID.
SecureStore vacío genera una identidad nueva; iOS puede conservar Keychain tras
reinstalar, por lo que no se promete un UUID nuevo en toda reinstalación.
Se utiliza `expo-crypto` compatible con SDK 54, sin biometría ni IDs privados.

`auth.service.ts` envía metadata siempre en login y sólo en refresh con formato
legacy. `AuthProvider` es el único coordinador: `refreshPromise` comparte el
mismo HTTP y resultado entre 401 concurrentes y RealtimeProvider. Un 401 tardío
reutiliza el access ya renovado. `finally` libera la promesa y un fallo limpia
la sesión. Referencias actuales, versión de sesión y escrituras serializadas
impiden restaurar una sesión cerrada por logout mientras el refresh termina.

Logout ejecuta revocación backend → desactivación push best-effort → limpieza
local incluso ante error de red. Si una renovación ya estaba en vuelo, revoca
su sucesor antes de terminar el logout. La revocación invalida el access usado
por el DELETE push posterior: ese intento puede recibir 401 y no garantiza
baja remota de PushDevice. No se introduce una excepción de autenticación ni se
acopla la autoridad de sesión al subsistema de notificaciones. Sin conexión,
la limpieza local no acredita revocación remota.

### Validación y límites de fase

Pruebas funcionales: `backend/tests/test_mobile_session_authority.py` y la
suite existente de contexto. Pruebas PostgreSQL aisladas con
`MOBILE_AUTH_POSTGRES_TEST_URL`: `test_mobile_session_postgres.py` verifica
migración reversible, refresh concurrente, reuse frente al sucesor, logout
frente a rotación, migración legacy concurrente y login frente a refresh sin
deadlock por FK de usuario. Mobile ejecuta los módulos
reales de AuthProvider, auth service, HTTP y SecureStore con puertos nativos
sustituidos en `AuthProvider.test.ts`; no se limita a inspeccionar fuente.

Fuera de esta fase: Face ID, Touch ID, Android biométrico, claves de dispositivo,
passkeys, TTL Mobile específico, lease administrativo, logout-all, panel de
dispositivos, SSH, SQL Console e Infrastructure Broker. Pendiente aceptación
física iOS/Android con una build que incluya `expo-crypto`.

## `MobileSecurityContext`

La dependencia canónica expone:

- `user`;
- `actor_type: internal | client`;
- `permissions` efectivos;
- `client_id` y `membership_id`, nulos para staff;
- `mobile_session_id` para access nuevo; nulo en compatibilidad legacy.

`require_mobile_permission` aplica capacidad explícita. Los endpoints
productivos Mobile de ETS/equipos/Hojas de Campo/Venta siguen usando
`require_internal_mobile_permission`: no se exponen a clientes hasta que cada
regla productiva tenga un adapter y ownership aprobados.

## Scope externo implementado

La superficie externa habilitada en esta fase es OT LAB temporal, sus equipos,
firmas, PDF, revisiones y Tickets asociados. `LabWorkOrder.client_id` es nullable:
las OT históricas/internas permanecen legibles para staff y las creadas por un
actor cliente se vinculan obligatoriamente a su organización. El nombre de
cliente enviado por la app no es autoritativo; el backend usa el `Client`
resuelto.

Listas filtran por `client_id`; detalles y subrecursos validan el padre y
responden `404` fuera de scope. Los writes verifican permiso antes de ownership,
por lo que un Viewer obtiene `403` sin inferir recursos. Exportación y borrado
LAB permanecen exclusivamente internos.

## Membresía activa única

La regla es:

```text
un Client → muchos usuarios
un usuario externo → máximo una membership active
```

El backend bloquea la fila `User` y valida la regla en alta administrativa,
reactivación, aprobación de vínculo y aceptación de invitación. PostgreSQL la
refuerza con el índice parcial único
`uq_client_portal_memberships_active_user (user_id) WHERE status='active'`.
Membresías `pending`, `suspended`, `revoked` o `rejected` conservan historia.
La migración aborta con mensaje explícito si detecta duplicados activos
preexistentes; no reasigna organizaciones silenciosamente.

## Roles externos persistidos

| Rol | Permisos |
| --- | --- |
| Viewer externo | `mobile.access`, `work_orders.read_organization`, `equipment.read`, `field_sheets.read` |
| Operativo Jr | Viewer + `work_orders.create`, `work_orders.execute`, `equipment.write`, `field_sheets.capture`, `signatures.capture`, `mobile_tickets.create`, `mobile_tickets.read` |
| Operativo Sr | Igual a Jr durante este bloque; no contiene permisos de folios |

Los paquetes se materializan en `ClientPortalRole`,
`ClientPortalPermission`, `ClientPortalRolePermission` y
`ClientPortalMembershipRole`. El startup idempotente existente reconcilia el
catálogo persistido. Sólo staff MYC puede listar/asignar perfiles que contengan
`mobile.access`; la autoadministración del Portal los excluye.

## Realtime, Comunicaciones y push

Realtime acepta JWT Mobile, conserva actor/scope y sólo permite rooms de
conversación cliente cuando el actor tiene permiso de Comunicaciones, participa
y `conversation.client_id` coincide. Nunca admite rooms internas o de otro
cliente. Los roles Mobile iniciales no incluyen Comunicaciones.

Push y Notificaciones usan endpoints Mobile y ownership por `user_id`; el
payload no acepta usuario ni cliente. Un dispositivo externo no requiere ser
staff y no puede desactivar dispositivos ajenos. Los destinatarios continúan
derivándose de cada evento de dominio, no de topics enviados por la app.

## Límites

No se implementaron folios, solicitudes/reposición, eventos realtime de folios
ni cambios a ETS/Cotizaciones productivos. El grupo de rutas `(technician)` se
conserva sólo como nombre organizativo. Los endpoints productivos Mobile quedan
deny para `client`; exponerlos requiere una fase posterior con contrato por
recurso, no sólo agregar permisos.

## Autoridad de folios propios (2026-09-17)

`MobileUserRead.can_resolve_own_lab_folios` se deriva en login, refresh y `/me`
de la misma función backend que usa Tickets: actor interno, Administrador activo
y `lab_folios.resolve`. No se infiere de account_type por sí solo, ni se confía
en roles suministrados por Mobile. Su ausencia equivale a false. La capability
sólo habilita presentación de solicitudes propias pending de linked_folio o
manual_myc_folio; backend revalida rol/permiso vigente al ejecutar.
