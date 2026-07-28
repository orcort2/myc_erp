# Fase 13 — Consolidación del Centro de Resoluciones

## Estado

`EN REVISIÓN`. Fase 12 fue aprobada formalmente mediante
`a7bf75f0f2de23faecb17276aa11d187c654a00c`. Fase 14 no se inició.

## Contrato

El Centro de Resoluciones es la consola oficial del Motor. Presentación,
transporte, proyecciones y composición de aplicación permanecen separados del
dominio, Lifecycle, Seguridad, runtime distribuido y operaciones propietarias.

`ResolutionCenterDefinitionRegistry` vincula cada definición canónica con
metadata institucional inmutable y versionada:

- nombre, descripción, dominio, objeto y versión;
- permisos y nivel de riesgo;
- capacidades, simulación y compensación;
- esquema cerrado de parámetros y etiquetas de presentación;
- fábrica de solicitud, hidratador de snapshot y serializador de solicitud.

Una integración futura registra esos contratos y los componentes canónicos del
Motor. No modifica routers, formularios, tabla, expediente ni máquina de
estados del Centro.

## Formularios

El frontend obtiene `/resolution-center/v1/definitions` y genera los campos
desde `parameter_schema`. Sólo transporta claves declaradas; el backend vuelve
a validar tipo, obligatoriedad, longitud y `additionalProperties=false`.
Etiquetas, ayuda, advertencias, riesgo y capacidades provienen del mismo
contrato. No existen payloads fiscales, comandos arbitrarios ni ramas por
dominio.

## Superficie operativa

La API interna incorpora indicadores calculados en backend y conserva filtros,
búsqueda, cursor ligado a consulta, timeline y aislamiento organizacional. El
expediente proyecta:

- resumen, objeto y parámetros;
- análisis, plan aprobado y simulación;
- timeline Lifecycle/distribuido;
- resultado, intentos y pasos;
- recuperación y reintentos;
- compensaciones;
- auditoría, snapshots y evidencias.

Datos técnicos se mantienen redactados salvo permiso de infraestructura.

## Flujo end-to-end

Certificados demuestra el ciclo:

```text
crear → contexto → analizar → plan → simular → autorizar
      → cola durable → worker canónico → resultado → expediente
```

La decisión `resolution.execute` incluye el contexto exacto esperado por el
Executor. El worker reclama la cola, reconstruye el actor durable y delega en
`ResolutionExecutor`; no ejecuta reglas del dominio. Cerrar sesión, abandonar
el módulo o perder conexión no cancela ni posee el trabajo.

## Permisos

- Administrador: acceso total mediante el comodín institucional.
- Auditor: lectura global, auditoría e infraestructura; no muta.
- Operador: lectura/creación/preparación/análisis/plan/simulación/ejecución de
  resoluciones propias; no autoriza.
- Usuario normal: sólo lectura propia cuando su rol la declara.

Cada endpoint exige su permiso y el Motor vuelve a comprobar decisiones
exactas. Ocultar un botón no se considera control de seguridad.

## Límites

No cambia API pública, SDK, Domain Model, Lifecycle, auditoría, compensación,
determinismo ni contratos de fases anteriores. No agrega IA, nuevos dominios,
retry manual, edición de evidencia ni operación paralela.
