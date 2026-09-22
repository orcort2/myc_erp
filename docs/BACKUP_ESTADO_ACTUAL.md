> Estado: VIGENTE
>
> Tipo: Snapshot operativo verificable
>
> Autoridad: Media; no sustituye los documentos canónicos de project/
>
> Corte: 2026-09-21 — BIOMETRIC-2 / Biometric login (incluye endurecimiento P1/P2)

# Estado operativo actual del ERP MYC

## Repositorio y alcance verificado

- Rama de trabajo: `feat/mobile-biometric-login-2`, creada desde
  `feat/mobile-session-authority-biometric-1` en
  `d94e35ae5a0710c9f31adb0a0c8f3299a4b603c9` (HEAD confirmado limpio antes de
  modificar archivos, con `MobileTrustedDevice`/`MobileAuthSession`/
  `refresh_credentials.py`/`AuthProvider` single-flight ya presentes).
- Sin push, merge ni despliegue en este trabajo.
- BIOMETRIC-2 agrega login biométrico (Face ID/Touch ID/biometría fuerte
  Android) sobre la Mobile Session Authority de BIOMETRIC-1, sin
  reescribirla: `MobileBiometricCredential` es una autoridad opaca separada
  (enroll/exchange/revoke), device-bound al mismo `MobileTrustedDevice`, con
  TTL propio de 90 días y revocación por cambio de contraseña.
- Mobile guarda perfil biométrico (no protegido) y credencial (protegida con
  `requireAuthentication` de SecureStore) en claves separadas; con biometría
  activa deja de persistir el `TokenPair` operativo para cold-start
  automático, sin afectar el comportamiento previo cuando no hay biometría
  habilitada.
- Incluye además la corrección del overscroll observado físicamente en
  iPhone en la Home técnica (`bounces`/`alwaysBounceVertical`/
  `overScrollMode` en su `ScrollView` principal).
- No se guardó contraseña ni dato biométrico nuevo; no se envía biometría al
  backend. PushDevice nunca se usó como autoridad de seguridad. Auth Web,
  Portal y TTL global permanecen sin cambio de implementación. No se
  implementó admin lease, step-up de infraestructura, SSH, SQL Console,
  Infrastructure Broker, passkeys/WebAuthn ni panel de dispositivos.
- Endurecimiento posterior (mismo alcance, segundo commit) corrigió 3
  defectos P1 y una mejora P2 detectados por auditoría: el modal de
  enrolamiento ya no se pierde por navegación inmediata (`login.tsx` navega
  sólo tras la decisión del usuario, con salida explícita si falla
  `enableBiometric()`); `enableBiometric()` ahora elimina
  `myc.internal.session.v1` sólo después de que credencial y perfil
  biométricos quedan guardados, sin tocar la sesión activa en memoria ni
  borrar prematuramente si el almacenamiento falla antes de completarse;
  `enroll_biometric_credential()` serializa por `MobileTrustedDevice` con
  `_lock_device` (misma disciplina de BIOMETRIC-1, sin arquitectura nueva);
  y desactivar biometría en Home exige confirmación nativa antes de
  ejecutar, con manejo explícito de fallo local. Detalle completo en el
  cierre BIOMETRIC-2.

## Base de datos y respaldo

- Revisión inicial local/código: `b10a1c202601`, único head (BIOMETRIC-1).
- Migración nueva y única: `9970e12e5f0d`, padre `b10a1c202601`.
- Upgrade aplicado en este entorno; `alembic current` = `alembic heads` =
  `9970e12e5f0d`.
- Tabla nueva: `mobile_biometric_credentials`, con FKs a `users` y
  `mobile_trusted_devices`, `credential_hash` UNIQUE e índices de usuario,
  dispositivo, vencimiento y revocación.
- Upgrade/downgrade/upgrade verificados contra PostgreSQL local de este
  entorno. No se modificó ninguna migración histórica.
- Este entorno remoto no tenía PostgreSQL en ejecución ni la base `erp_myc`;
  se levantó el cluster local y se creó un rol/BD sólo para esta sesión de
  trabajo. Credenciales en `backend/.env`, ignorado por Git; este documento
  no incluye datos sensibles.

## Validación final

- Backend focalizado (con `MOBILE_AUTH_POSTGRES_TEST_URL` real): 25 passed
  (`test_mobile_biometric.py`, `test_mobile_session_postgres.py` y la nueva
  `test_mobile_biometric_postgres.py` de concurrencia real de enroll).
- Backend completo: 1285 passed, 3 failed, 16 skipped, 34 warnings, 19
  subtests passed. Los 3 fallos son preexistentes y dependen de un
  LibreOffice funcional no disponible en este sandbox (conversión
  XLSX→PDF, ajenos a Mobile/biometría); el cuarto fallo intermitente del
  corte anterior no se reprodujo en esta corrida. Ninguno toca código
  modificado en esta entrega. Detalle en el cierre BIOMETRIC-2.
- Mobile focalizado de BIOMETRIC-2 (con el endurecimiento): 51 passed
  (AuthProvider + AuthProvider biométrico + servicio nativo + storage
  biométrico + login-biometric-enrollment + technician-home.disable-biometric
  + wiring overscroll).
- Mobile completo: 722 passed (antes 682 en el corte BIOMETRIC-1, 709 en la
  entrega inicial de BIOMETRIC-2; se corrigió además un problema de
  infraestructura de pruebas preexistente en la harness de
  `AuthProvider.test.ts` que hacía fallar sus 11 tests al cargar un nuevo
  import transitivo, sin tocar su lógica de aserciones).
- `npx tsc --noEmit`: 2 errores preexistentes en `realtime-client.ts`, ajenos
  a este trabajo y no tocados.
- `npm run lint`: exit 0, sin errores.
- Inventario API regenerado: 533 operaciones (sin cambio en este pase; el
  endurecimiento no tocó contratos ni endpoints), incluidos enroll/exchange/
  delete biométricos; `exchange` es público intencional como login.
- Inventario funcional regenerado y filas revisadas; `git diff --check` sin
  errores.
- Cada uno de los 3 P1 y el P2 se verificó negativamente: se revirtió la
  corrección temporalmente y se confirmó que su(s) test(s) nuevo(s) fallan
  por la causa exacta esperada, antes de restaurar el código corregido.
- Revisado: sin contraseña ni dato biométrico nuevo persistido, sin
  biometría enviada al backend, sin cambio de auth Web/TTL ni uso de
  PushDevice como autoridad.
- Evidencia, comandos, contratos y diff completo:
  [cierre BIOMETRIC-2](closures/BIOMETRIC_2_BIOMETRIC_LOGIN.md). El corte
  BIOMETRIC-1 permanece en
  [su propio cierre](closures/BIOMETRIC_1_MOBILE_SESSION_AUTHORITY.md).

## Pendientes y límites

- Validación física iOS/Android pendiente (checklist detallado en el cierre
  BIOMETRIC-2): Face ID/Touch ID/huella, cancelación, cold start, "Usar otra
  cuenta", overscroll corregido, rotación de pantalla y fallback sin PIN
  silencioso en Android.
- Retirar fallback legacy de BIOMETRIC-1 tras 2026-10-22 00:00 UTC sigue
  pendiente, sin cambios por este trabajo.
- `disableBiometric()` limpia local aunque el `DELETE` remoto falle por red
  (riesgo aceptado, documentado como TD-059); enrolar una cuenta distinta a
  la ya recordada no puede revocar server-side la credencial de la cuenta
  anterior (TD-060).
- MYC Mobile permanece EN DESARROLLO como superficie completa. Admin lease,
  step-up de infraestructura, SSH, SQL Console, Infrastructure Broker,
  passkeys/WebAuthn, claves device-bound, terminal embebida, panel de
  dispositivos y selector multi-cuenta biométrico están fuera de fase.
- El estado global y pendientes ajenos a esta entrega permanecen bajo
  `project/PROJECT_STATUS.md` y `project/TECHNICAL_DEBT.md`.

## Autoridades documentales

`project/DOCUMENTATION_INDEX.md` rige la jerarquía. El contrato de sesión y
biometría está en `architecture/MOBILE_SECURITY_CONTEXT.md`; estado, alcance,
flujo, reglas y decisiones se sincronizan en sus canónicos. Inventario en
`PROJECT_FILE_REGISTRY.md`. El corte anterior permanece trazable en Git.
