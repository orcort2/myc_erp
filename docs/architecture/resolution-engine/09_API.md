# 09 · API

# API del Motor de Resoluciones

## Introducción

El Motor de Resoluciones expone un conjunto de operaciones mediante las cuales el resto del ERP puede interactuar con él.

Estas operaciones representan el contrato público del subsistema.

No describen una implementación específica en HTTP, REST, GraphQL o RPC.

Definen únicamente las capacidades que el Motor debe ofrecer.

La implementación tecnológica podrá adaptarse mientras preserve el comportamiento descrito en este documento.

---

# Objetivos

La API del Motor deberá permitir:

- crear resoluciones;
- consultar resoluciones;
- obtener contexto;
- obtener planes;
- ejecutar simulaciones;
- solicitar autorizaciones;
- aprobar o rechazar planes;
- ejecutar resoluciones;
- cancelar resoluciones;
- consultar auditoría;
- consultar resultados.

Nunca deberá permitir modificar directamente información perteneciente a los módulos de dominio.

---

# Principios

La API deberá cumplir los siguientes principios:

- determinista;
- idempotente cuando aplique;
- auditable;
- segura;
- desacoplada del dominio;
- orientada a capacidades;
- extensible.

---

# Recursos principales

```text
Resolution

ResolutionProblem

ResolutionContext

ResolutionAnalysis

ResolutionPlan

ResolutionSimulation

Authorization

Execution

Result

Audit
```

---

# Operaciones principales

## Crear resolución

```text
POST /resolutions
```

### Objetivo

Registrar un nuevo problema extraordinario.

---

### Request conceptual

```json
{
  "resolution_type": "...",
  "subject": {},
  "reason": "...",
  "payload": {}
}
```

---

### Response

```json
{
  "resolution_id": "...",
  "status": "draft"
}
```

---

# Consultar resolución

```text
GET /resolutions/{resolution_id}
```

Devuelve:

- estado;
- tipo;
- prioridad;
- estrategia;
- plan activo;
- resultado;
- fechas.

---

# Buscar resoluciones

```text
GET /resolutions
```

Filtros posibles:

- estado
- tipo
- entidad
- usuario
- fecha
- prioridad

---

# Obtener contexto

```text
GET /resolutions/{id}/context
```

Devuelve el snapshot utilizado por el motor.

---

# Obtener análisis

```text
GET /resolutions/{id}/analysis
```

Incluye:

- restricciones
- advertencias
- estrategias disponibles

---

# Obtener plan

```text
GET /resolutions/{id}/plan
```

Devuelve:

- versión
- pasos
- dependencias
- riesgos
- impactos

---

# Simular

```text
POST /resolutions/{id}/simulate
```

Produce una nueva simulación.

---

### Response

```json
{
  "simulation_id": "...",
  "status": "valid",
  "warnings": [],
  "expected_actions": []
}
```

---

# Solicitar autorización

```text
POST /resolutions/{id}/authorization
```

Genera una solicitud de autorización.

---

# Aprobar

```text
POST /authorizations/{id}/approve
```

---

# Rechazar

```text
POST /authorizations/{id}/reject
```

---

# Revalidar

```text
POST /resolutions/{id}/revalidate
```

Compara nuevamente el contexto.

---

# Ejecutar

```text
POST /resolutions/{id}/execute
```

Inicia la ejecución del plan autorizado.

---

# Cancelar

```text
POST /resolutions/{id}/cancel
```

---

# Consultar resultado

```text
GET /resolutions/{id}/result
```

---

# Consultar auditoría

```text
GET /resolutions/{id}/audit
```

---

# Consultar ejecuciones

```text
GET /resolutions/{id}/executions
```

---

# Consultar pasos

```text
GET /executions/{id}/steps
```

---

# Estados HTTP sugeridos

| Código | Significado |
|---------|-------------|
|200|Operación exitosa|
|201|Recurso creado|
|202|Aceptado para procesamiento|
|204|Sin contenido|
|400|Solicitud inválida|
|401|No autenticado|
|403|Sin permisos|
|404|No encontrado|
|409|Conflicto|
|412|Precondición incumplida|
|422|Regla de negocio violada|
|423|Resolución bloqueada|
|500|Error interno|

---

# Idempotencia

Las operaciones que crean recursos deberán aceptar:

```text
Idempotency-Key
```

Ejemplos:

- crear resolución
- ejecutar
- registrar autorización
- sincronización offline

---

# Versionado

La API deberá ser versionable.

Ejemplo:

```text
/api/v1/resolutions
```

---

# Seguridad

Todas las operaciones deberán requerir autenticación.

Los permisos dependerán del tipo de resolución.

Ejemplo:

```text
resolution.request.*

resolution.view.*

resolution.execute.*

resolution.authorize.*
```

---

# Eventos emitidos

La API podrá publicar eventos como:

```text
resolution.created

resolution.simulated

resolution.authorized

resolution.completed

resolution.failed
```

---

# Compatibilidad

Las futuras versiones no deberán romper clientes existentes sin un proceso formal de deprecación.

---

# Declaración final

La API del Motor de Resoluciones constituye el contrato oficial entre el subsistema de resolución y el resto del ERP.

Toda interacción deberá realizarse mediante estas capacidades, evitando el acceso directo a componentes internos o a la lógica de negocio de los módulos propietarios.