> Estado: EN REVISIÓN — CORRECCIÓN BLOQUEANTE IMPLEMENTADA
>
> Versión de contrato: 1.0
>
> Fecha: 2026-07-28

# API pública y SDK — Fase 10

## Superficie institucional v1

La primera frontera pública del Motor vive bajo:

```text
/api/public/resolution-engine/v1
```

Expone únicamente:

| Método | Ruta | Servicio canónico |
| --- | --- | --- |
| `GET` | `/capabilities` | Catálogo público de la versión |
| `POST` | `/resolutions` | `ResolutionLifecycleService.create` |
| `GET` | `/resolutions` | selección organizacional + `AuditQueryService` |
| `GET` | `/resolutions/{id}` | `AuditQueryService.inspect` |

El portal técnico está en `/api/developers/resolution-engine`. No ejecuta
operaciones ni incorpora un flujo alterno.

La versión 1.0 inicia y consulta expedientes del único vertical integrado,
`certificate.resolve_incorrect_release`. Simulación, autorización de planes,
ejecución y compensación conservan sus servicios internos aprobados, pero no se
publican en esta primera versión: exponerlos sin un contrato público completo
sería reinterpretar capacidades y seguridad más allá de esta entrega.

## Contratos

`myc_resolution_contracts.v1` contiene DTOs Pydantic estrictos, congelados y
con `extra=forbid`. Los recursos públicos usan `public_id`; nunca exponen IDs
ORM, entidades, repositorios, Domain Gateways o excepciones internas.

Toda respuesta de la superficie v1 declara
`X-MYC-Contract-Version: 1.0`. Los errores controlados usan:

```json
{
  "code": "idempotency_conflict",
  "category": "conflict",
  "message": "Safe public message.",
  "correlation_id": "UUID",
  "details": {}
}
```

Una ruptura futura requiere otra ruta/paquete de versión. La v1 no podrá
reinterpretar campos o históricos.

## Seguridad por consumidor y organización

Cada consumidor se persiste en `resolution_api_consumers` con clave pública,
hash HMAC-SHA256 del secreto, organización única, permisos, vigencia y estado.
El secreto plano sólo se entrega al provisionar y no se persiste.

Encabezados obligatorios:

```text
Authorization: Bearer <consumer_key>.<secret>
X-MYC-Organization-ID: <organization>
X-Correlation-ID: <UUID>
Idempotency-Key: <key>       # sólo POST
```

El adaptador convierte la identidad autenticada en `ActorContext` de tipo
`service`. La organización del encabezado debe coincidir exactamente con la
del consumidor. Crear exige `resolution.create`; consultar exige
`resolution.audit.inspect`. Ambas operaciones atraviesan el evaluador integral
y conservan evidencia append-only. Una búsqueda de otra organización responde
como recurso inexistente.

Los consumidores se provisionan únicamente desde un contexto administrativo
interno:

```python
from app.resolution_public_api.security import provision_consumer

consumer, token = provision_consumer(
    session,
    consumer_key="integration-name",
    name="Institutional integration",
    organization_id="organization-id",
    permissions=("resolution.create", "resolution.audit.inspect"),
)
session.commit()
```

No existe endpoint público de administración de credenciales.

## Idempotencia y replay

La clave externa se transforma en un `request_key` canónico SHA-256 que incluye
versión, consumidor, organización y clave. La solicitud completa conserva otro
hash canónico en metadata del expediente.

- mismo namespace + mismo payload: devuelve el mismo `public_id` mediante una
  consulta autorizada;
- mismo namespace + payload distinto: `409 idempotency_conflict`;
- otra organización o consumidor: namespace distinto;
- ningún replay revela el resultado antes de autenticar, aislar y autorizar.

Lifecycle sigue consumiendo la concesión `single_operation` exacta durante la
creación. Las lecturas reutilizan exclusivamente una concesión
`reusable_read` exacta y el expediente se reconstruye con `AuditQueryService`.

## Consultas

La colección acepta filtros exactos por `status`, `resolution_type`,
`subject_type` y `subject_id`. Usa paginación keyset por
`created_at + id` con orden `created_at_desc` o `created_at_asc`; el límite
permitido es `1..100`.

### Contrato del cursor `c1`

El cursor público no es un payload Base64 firmado. Es un sobre versionado
`c1` cifrado y autenticado mediante AES-GCM. La clave de 256 bits se deriva del
secreto institucional con un dominio exclusivo para cursores y cada token usa
un nonce criptográficamente aleatorio.

Dentro del contenido cifrado se conserva:

- versión del sobre y versión contractual;
- consumidor y organización exactos;
- hash canónico de los cuatro filtros;
- orden de clasificación;
- dirección de paginación (`forward`);
- tamaño de página;
- instante e ID interno requeridos por el keyset.

Al recibir un cursor, el adaptador autentica y descifra el sobre y después
compara toda la identidad de consulta con la solicitud actual. Cualquier cambio
de filtros, consumidor, organización, versión, orden, dirección o límite
produce `422 invalid_cursor` antes de consultar la siguiente página.

La posición y las claves internas existen sólo dentro del ciphertext. El
consumidor puede reconocer la versión externa `c1`, pero no recuperar IDs,
secuencias, filtros o posición.

Los cursores del formato anterior quedan revocados: aquel payload revelaba la
posición y no contenía identidad suficiente para validar la consulta original.
Por política de compatibilidad de seguridad se rechazan con
`cursor_version_unsupported`; reinterpretarlos como `c1` sería inseguro. Las
futuras versiones de sobre deberán coexistir sólo cuando puedan verificar
íntegramente su contrato original.

Cada recurso candidato se autoriza antes de proyectarse. La consulta de datos
no modifica Lifecycle ni ejecuta handlers. La evidencia de autorización que
protege la lectura permanece append-only conforme a Fase 8.

## SDK oficial

`myc_resolution_sdk.ResolutionEngineClient` sólo usa HTTP y los contratos
públicos. No importa `app`, ORM, repositorios, infraestructura, servicios
internos o Domain Gateways.

```python
from myc_resolution_contracts.v1 import CreateResolutionRequest
from myc_resolution_sdk import ResolutionEngineClient

with ResolutionEngineClient(
    base_url="https://erp.example",
    token="consumer.secret",
    organization_id="organization-id",
) as client:
    capabilities = client.capabilities()
    result = client.create_resolution(
        CreateResolutionRequest.model_validate(payload),
        idempotency_key="external-operation-123",
    )
```

## Límites preservados

- Lifecycle continúa como única autoridad de estado.
- La API traduce; no decide ni contiene ORM.
- El SDK transporta; no replica reglas.
- Certificados permanece como único vertical.
- No se incorporaron workers, colas, distribución, múltiples instancias,
  microservicios, autenticación federada, IA o proveedores de IA.
- Fase 11 permanece no iniciada y bloqueada hasta aprobación formal.
