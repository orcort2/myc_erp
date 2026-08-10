> Estado: **TERMINADO — EN REVISIÓN**
>
> Corte: 2026-08-10
>
> Alcance: P0 Integridad de autenticación de Certificados

# Cierre técnico — Integridad de autenticación de Certificados

## Resultado

Calidad quedó como única superficie funcional capaz de autenticar. El endpoint
`POST /certificates/{certificate_id}/authenticate` es un adapter HTTP delgado
y `services/certificate_authentication.py::authenticate_certificate` es la
única autoridad transaccional. ETS conserva lectura, estado, descarga y
liberación, pero ya no presenta ni expone autenticación individual o masiva.

## 1–2. Superficies encontradas y divergencias

Antes de consolidar existían dos caminos mutantes:

```text
QualityPage
→ POST /certificates/{id}/authenticate
→ router certificates
→ authenticate_certificate_pdf(certificate ya cargado)
→ audit
→ commit del router

ServiceOrdersPage
→ POST /service-orders/{ets}/certificates/authenticate-approved
→ router ETS
→ authenticate_certificates_for_service_order
→ loop/skip/rollback/commit por certificado
→ authenticate_certificate_pdf
→ audit
```

Ambos usaban `certificates.approve` y el mismo generador, pero tenían ownership
transaccional distinto. El router individual hacía commit, el lote ETS añadía
sus propios estados de resultado y commits, ninguno publicaba evento formal y
el generador recibía un objeto previamente cargado sin lock. Dos sesiones
podían observar simultáneamente `quality_approved` y producir archivos/audits
duplicados antes del último commit.

La revisión de asignaciones confirmó que ningún worker, listener o integración
del Motor marca un certificado como `authenticated`. El vertical de Fase 9
sólo retira/restaura `client_visible` ante liberación incorrecta y preserva
estado, PDF y evidencia de autenticación.

## 3. Autoridad canónica y justificación

La autoridad es `authenticate_certificate` en
`backend/app/services/certificate_authentication.py` porque ese servicio ya es
propietario de resolución del Master, conversión XLSX→PDF, sello, QR, código,
hash, versionado y mutación documental. Ahora también posee consulta con lock,
validación de actor/origen, audit, evento y commit. La ubicación visual no
contiene reglas de negocio.

Calidad es la única superficie funcional conforme a BR-014, ADR-009 y al
catálogo funcional M22.A03. Certificados continúa siendo el agregado y la API
del recurso; ETS sólo proyecta el resultado.

## 4–5. Código eliminado y adapters

Se eliminaron:

- `authenticate_certificates_for_service_order` y su loop transaccional;
- `POST /service-orders/{service_order_id}/certificates/authenticate-approved`;
- la clasificación especial de ese endpoint;
- el cliente API `authenticateApprovedCertificates`;
- la acción individual, acción masiva y handlers de autenticación en
  `ServiceOrdersPage`.

Permanece un único adapter mutante:

`POST /certificates/{certificate_id}/authenticate`

El adapter exige `certificates.approve`, propaga `current_user.id`, fija origen
`quality` y delega sin consultar el agregado ni ejecutar commit.

## 6. Lifecycle final

```text
Master XLSX identificado
→ quality_review
→ quality_approved (o alias legacy approved)
→ Calidad solicita autenticar
→ lock de Certificate
→ revalidación de estado/no autenticado
→ conversión y sello
→ versión PDF + código/hash/actor/timestamp
→ authenticated
→ audit + evento
→ commit
→ liberación posterior e independiente
```

Autenticar no libera, no cambia `client_visible` y no consulta Facturación. La
liberación exige después PDF autenticado y la compuerta financiera vigente.

## 7–9. Permiso, actor, audit y evento

- Permiso vigente: `certificates.approve`.
- No se crearon capacidades ni se modificó el catálogo congelado. El catálogo
  funcional ya prevé `certificates.authenticate` como futuro, no vigente.
- Actor obligatorio: `user_id: int`, con rechazo de `None`.
- Origen obligatorio: `quality`; otro origen se rechaza antes de consultar.
- Audit: `certificate.pdf_authenticated`, con estado/rutas anteriores, estado,
  Master, código/hash, rutas, match y `origin=quality` nuevos.
- Evento: `certificate.authenticated`, formal, actor, estado anterior/nuevo,
  origen, código y ETS; idempotency key `certificate:{id}:authenticated`.

## 10. Idempotencia y concurrencia

La autoridad adquiere `SELECT ... FOR UPDATE` sobre el certificado activo antes
de validar o generar. La primera solicitud conserva el lock durante conversión,
audit, evento y commit. Una segunda solicitud espera, recarga el estado ya
`authenticated` y responde 409 antes del generador; no duplica PDF, versión,
audit ni evento. El evento añade además unicidad por idempotency key.

## 11. Motor de Resoluciones

No autentica ni invoca el generador. Fase 9 conserva su servicio propietario
para corregir visibilidad de una liberación incorrecta. No se abrió Fase 14 ni
se agregó handler, worker o lógica paralela.

## 12–13. Archivos y pruebas

Código principal: servicio/adapter de autenticación, router y servicio ETS,
guard/inventario API, cliente API, `ServiceOrdersPage` y pruebas relacionadas.

`test_certificate_authentication_integrity.py` caracteriza primero los dos
caminos previos y después protege autoridad única, adapter delgado, ausencia de
endpoint ETS, permiso, actor/origen, lock, audit/evento, doble autenticación y
commit único. `certificateAuthenticationAuthority.test.js` impide reintroducir
acciones ETS o el cliente masivo. Las pruebas del conversor real validan origen
y evento.

## 14. Regresión

| Validación | Resultado |
| --- | --- |
| Caracterización previa | 4 passed |
| Autenticación real + autoridad | 12 passed |
| Certificados/ETS/permisos focal | 35 passed |
| Backend completo | 467 passed, 19 subtests, 3 warnings |
| Frontend completo | 41 passed |
| Vite build | correcto; warning de chunk >500 kB |
| `compileall` / `pip check` / `scripts/myc doctor` | correctos |
| Alembic `check` | sin drift |
| Inventario API | 357 operaciones; coincide con runtime |
| Capability gate | rojo: 20 brechas catálogo y 2 bootstrap; snapshot espera 19/1 |
| `git diff --check` | correcto |

No hubo cambio de esquema o datos; el respaldo oficial permanece alineado con
`e7b62b8a9421` y no requirió regeneración.

## 15. Riesgos y deuda restante

- La capacidad futura `certificates.authenticate` requiere conciliación del
  catálogo/roles; este sprint conserva `certificates.approve`.
- El capability gate continúa rojo por `TD-027`: el inventario contiene 20
  permisos ausentes del catálogo y 2 ausentes del bootstrap (`portal.view` y
  `reference_standard_certificates.delete`), mientras el snapshot espera 19/1.
  La retirada de la ruta ETS no añadió permisos y esta deuda global queda fuera
  del P0.
- La liberación individual y el lote ETS comparten semántica, pero el lote aún
  implementa su propio loop en vez de delegar en `release_to_client`. Es deuda
  separada y no reabre autenticación.
- Los archivos se escriben antes del commit SQL; una falla excepcional de base
  después de la escritura puede dejar un archivo huérfano recuperable por
  mantenimiento de storage. No produce estado autenticado confirmado.
- Permanece pendiente el E2E browser autenticado con datos representativos y la
  verificación pública completa.

No se modificó Facturación, catálogo congelado, Motor ni esquema. No se inició
otra actividad. El sprint queda **EN REVISIÓN**.
