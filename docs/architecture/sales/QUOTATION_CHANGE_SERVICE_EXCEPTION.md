> Estado: SUSTITUIDO el 2026-07-29 por `QUOTATION_CONTROLLED_UNLOCK.md`
>
> Tipo: Arquitectura vigente
>
> Corte verificado: 2026-07-29

# Excepción contextual: cambio de servicio en cotización aprobada

> Evidencia histórica del diseño puntual; no rige el comportamiento vigente.

## Alcance

Esta excepción sólo aplica cuando la cotización está aprobada, existe un ETS
relacionado y todavía no hay equipos registrados. Permite sustituir una partida
de servicio por otro servicio vigente sin abrir la cotización completa, sin
crear otra cotización y sin crear otro ETS.

El flujo implementado es:

```text
Cotización MYC-…
→ solicitar EXV-…
→ revisión de negocio
→ capacidad quotation.change_service_type
→ aplicar una vez
→ misma cotización MYC-… + mismo ETS OSMYC-…
```

## Identificadores visibles

La experiencia humana usa exclusivamente los folios generados por el sistema:

- cotización `MYC-MM-AA-####`;
- ETS `OSMYC-AA-MM-####`;
- excepción `EXV-AAAA-#####`;
- número visible de partida dentro de la cotización;
- clave y nombre visibles del servicio.

Los enteros de base de datos permanecen como claves privadas de integridad
referencial. El usuario no los captura, no los usa para navegar y no se
presentan como referencia de negocio. El comando de solicitud usa
`quotation_line_number` y `requested_service_key`; las rutas resuelven
cotización/excepción por folio y el ETS se obtiene de la relación institucional
de la cotización.

## Expediente y capacidad

`quotation_service_change_requests` conserva:

- cotización, ETS y partida afectada;
- servicio actual y solicitado, con snapshots independientes;
- solicitante, revisor y usuario autorizado para aplicar;
- motivo, observación, comentario de revisión e impacto;
- versión de cotización observada;
- estado, vigencia, consumo y resultado;
- snapshot/revisión resultante.

La capacidad es exactamente `quotation.change_service_type`, está ligada al
expediente, cotización, ETS, partida, par de servicios, usuario y vencimiento.
Sólo puede consumirse una vez. No existe `quotation.editable=true`.

## Estados visibles

| Estado persistente | Etiqueta |
| --- | --- |
| `pending_review` | Pendiente de revisión |
| `information_required` | Información requerida |
| `authorized` | Disponible para aplicar |
| `applying` | Aplicando |
| `completed` | Completada |
| `rejected` | Rechazada |
| `blocked` | Bloqueada |
| `expired` | Vencida |
| `revoked` | Revocada |
| `cancelled` | Cancelada |

La primera entrega produce `pending_review`, `information_required`,
`authorized`, `completed`, `rejected`, `blocked` y `expired`. Los estados
restantes quedan reservados en el contrato; no se expone todavía una operación
de cancelación o revocación.

## Solicitud y autorización

La solicitud valida en backend:

1. permisos específicos y permisos base de Cotización, ETS y Actividad;
2. cotización activa y `accepted`;
3. ETS activo vinculado;
4. ausencia física de cualquier `Equipment`, incluida baja lógica o estado
   cancelado;
5. partida activa vinculada a Catálogo MYC;
6. servicio nuevo distinto, activo, de tipo `service`, clasificable y con
   configuración de alcance cuando corresponde.

La clave activa compuesta evita duplicar clics para la misma cotización, ETS,
partida, servicio actual, servicio nuevo y solicitante.

La autorización exige segregación solicitante/revisor. Sólo el permiso
excepcional `quotations.exceptions.self_authorize_change_service` puede
levantarla; el rol Administrador conserva su comodín institucional. Antes de
conceder se revalida el contexto, se impiden dos capacidades autorizadas para
la misma cotización y se bloquean cambios que alterarían precio, objeto de
impuesto o tasa.

## Aplicación atómica

`apply_change` es la operación propietaria equivalente a
`change_quotation_service_and_sync_service_order(...)`. Dentro de una sola
transacción:

1. bloquea expediente, cotización y ETS mediante `FOR UPDATE`;
2. revalida estado, relación, versión, servicio actual, servicio solicitado,
   vigencia, usuario y ausencia real de equipos;
3. crea snapshot completo previo;
4. actualiza únicamente los campos técnicos dependientes del servicio en la
   partida de cotización;
5. reconstruye sólo las partidas operativas del mismo renglón del mismo ETS,
   reutilizando la expansión canónica de Servicios Compuestos;
6. crea la nueva revisión interna con el mismo folio;
7. consume la capacidad, cierra el expediente y registra auditoría;
8. publica eventos idempotentes en Cotización y ETS y notifica el resultado.

No se modifican cliente, cantidades, precio, descuento, impuestos, condiciones,
folios ni el resto de partidas. Un fallo antes del commit revierte cotización,
ETS, snapshots, capacidad, auditoría y eventos. Si aparece un equipo después de
autorizar, el expediente queda `blocked` sin cambio parcial.

## Permisos

| Permiso | Uso |
| --- | --- |
| `quotations.exceptions.request_change_service` | Solicitar desde la cotización |
| `quotations.exceptions.authorize_change_service` | Autorizar, rechazar o pedir información |
| `quotations.exceptions.apply_change_service` | Consumir la capacidad concedida |
| `quotations.exceptions.inspect_change_service` | Consultar la bandeja y el expediente |
| `quotations.exceptions.self_authorize_change_service` | Excepción explícita a segregación; no asignada a roles ordinarios |

Además se exigen, según la operación, `quotations.read`,
`quotations.update`, `service_orders.read` y `activity.create`.

## Actividad, notificaciones y Motor de Resoluciones

Solicitud, decisión, bloqueo y aplicación publican eventos idempotentes en los
hilos existentes de Cotización y ETS. Notifications entrega avisos dirigidos
con `quotation_folio`, `service_order_folio`, `exception_folio` y ruta frontend.

Se reutilizaron snapshots de Cotización, expansión propietaria de partidas ETS,
auditoría, Actividad, Notifications, permisos y el patrón institucional de
segregación/idempotencia/revalidación. No se creó una definición vertical del
Motor, no se agregó una etapa al Centro de Resoluciones y no se modificó el
runtime, Lifecycle, API pública, worker o Roadmap. La autorización contextual
es deliberadamente una bandeja de negocio simple.

La autorización genera avisos separados de decisión, capacidad disponible y
vigencia próxima; la aplicación vuelve a comprobar el vencimiento aunque el
aviso no sea leído.

## Límites

Esta entrega no permite precio/impuestos, reapertura general, agregar o quitar
equipos, cancelar cotización, modificar Facturación/Pagos ni crear otras
excepciones.
