> Estado: IMPLEMENTACIÓN CONCLUIDA — PENDIENTE DE REVISIÓN FORMAL
>
> Fecha: 2026-07-28
>
> Autoridad: dictamen final de Fase 9 y roadmap oficial

# Apertura oficial — Fase 10

## Nombre oficial

**Fase 10 — SDK y API Pública**

## Dependencia satisfecha

Las Fases 0 a 9 están aprobadas. Fase 9 queda cerrada mediante:

```text
5abfe2d788c2a5d641d8a25037ffd2cfbad914ce
901bd85454f3d88ed8f988c71c3475a568d94cd8
```

La implementación autorizada quedó concluida. Su contrato verificable está en
[`26_PUBLIC_API_SDK.md`](26_PUBLIC_API_SDK.md) y el cierre técnico en
[`../../closures/RESOLUTION_ENGINE_PHASE_10.md`](../../closures/RESOLUTION_ENGINE_PHASE_10.md).
La fase todavía no cuenta con aprobación formal y Fase 11 permanece bloqueada.

## Objetivo

Exponer el Motor mediante contratos públicos, una API institucional versionada
y un SDK oficial, sin filtrar su implementación interna ni debilitar seguridad,
determinismo, Lifecycle, idempotencia, auditoría, evidencia o compensación.

## Alcance autorizado

Únicamente podrán implementarse capacidades directamente necesarias para:

- contratos públicos versionados de comandos, consultas, resultados y errores;
- API institucional para iniciar y consultar resoluciones, simular, ejecutar
  operaciones autorizadas, recuperar resultados y consultar evidencia;
- autenticación y autorización de consumidores externos mediante el modelo de
  seguridad vigente;
- identidad canónica de consumidor, actor, organización, correlación y
  operación;
- idempotencia namespaced por consumidor y organización;
- control optimista y conflictos públicos estables;
- filtros y paginación deterministas para consultas read-only;
- SDK oficial y client libraries del alcance público aprobado;
- compatibilidad y política de versionado;
- especificación, ejemplos, guía de integración y documentación técnica;
- portal técnico para desarrolladores sólo si consume los mismos contratos
  públicos y no crea lógica o flujo paralelo;
- pruebas contractuales, de seguridad, compatibilidad e integración.

FastAPI, routers y schemas de transporte sólo quedan autorizados como adaptador
de esta API institucional. No pueden contener políticas, reglas, Lifecycle,
acceso ORM directo ni otra máquina de estados.

## Contrato de frontera

```text
consumidor autorizado
→ contrato público versionado
→ autenticación + ActorContext
→ autorización integral exacta
→ comando/consulta interna del Motor
→ Lifecycle / servicios vigentes
→ resultado o error público estable
```

- La API traduce; no decide.
- El SDK encapsula transporte; no replica reglas, permisos o estados.
- Los comandos reutilizan servicios de aplicación y decisiones de seguridad.
- Las consultas reutilizan servicios read-only y nunca producen efectos.
- Los Domain Gateways permanecen internos; no se exponen adaptadores
  propietarios ni ORM.
- Certificados continúa siendo el único vertical ERP integrado y aprobado.

## Seguridad e idempotencia

Toda operación pública deberá quedar ligada a consumidor, actor, organización,
recurso, intención, payload, correlación y versión de contrato exactos.

Una clave idempotente externa se normalizará en un namespace institucional por
consumidor y organización antes de construir el comando interno. Un replay
exacto podrá recuperar únicamente el mismo resultado autorizado; una colisión
de identidad, versión, payload o hash se denegará sin producir otro efecto.

La exposición pública no podrá revelar replays, existencia de resoluciones,
evidencia, errores internos o datos de otra organización antes de autorizar.

## Compatibilidad

- La primera superficie pública deberá declarar una versión explícita.
- Los contratos no expondrán clases ORM, excepciones internas ni estructuras
  incidentales de persistencia.
- Los errores públicos tendrán código, categoría, mensaje seguro y detalles
  contractuales controlados.
- Una ruptura futura requerirá nueva versión, documentación y pruebas de
  compatibilidad; no se reinterpretarán históricos.

## Invariantes obligatorias

- Motor completamente determinista y sin dependencia de IA.
- Lifecycle como única autoridad de estado.
- Seguridad integral y deny-by-default.
- DDD y separación Dominio / Aplicación / Infraestructura / Transporte.
- Persistencia transaccional, locks e idempotencia.
- Auditoría append-only y evidencia inmutable.
- Reconstrucción determinista.
- Compensación explícita y gobernada.
- Domain Gateways internos y providers read-only.
- Ausencia de lógica de negocio en routers, schemas, clientes o SDK.
- Ausencia de dependencias circulares.
- Compatibilidad completa con las Fases 1 a 9.

## Fuera de alcance

No se implementan durante esta fase:

- procesamiento distribuido o coordinación multinodo;
- workers, colas, schedulers o retries automáticos;
- múltiples instancias coordinadas, alta disponibilidad o balanceo;
- microservicios o extracción del Motor fuera del proceso actual;
- nuevos dominios ERP o nuevos casos verticales;
- integraciones externas concretas ajenas al consumo de la API;
- automatización general del ERP;
- inteligencia artificial, aprendizaje automático o proveedores de IA;
- capacidades de Fase 11 o posteriores.

## Validaciones requeridas

Toda entrega de Fase 10 deberá incluir:

- suite específica de contratos/API/SDK;
- pruebas negativas de autenticación, autorización, aislamiento y replay;
- pruebas de compatibilidad y versionado;
- suite completa del Motor;
- backend completo;
- frontend y build cuando exista portal técnico;
- compilación Python y del SDK correspondiente;
- validaciones arquitectónicas y de dependencias;
- Alembic `current`, `heads` y `check`;
- respaldo actualizado cuando corresponda;
- documentación y especificación pública sincronizadas;
- inventario actualizado;
- lista completa de archivos modificados;
- commit exclusivo.

## Gate de salida

La Fase 10 sólo podrá aprobarse cuando los contratos públicos sean estables,
versionados, seguros y consumibles mediante el SDK sin exponer internals ni
duplicar reglas del Motor.

## Restricción

La Fase 11 — Motor Distribuido permanece `NO INICIADA`. No puede comenzar hasta
que Fase 10 concluya, sea revisada y reciba aprobación formal.
