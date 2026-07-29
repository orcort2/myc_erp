> Estado: VIGENTE
>
> Tipo: Contrato técnico canónico
>
> Corte verificado: 2026-07-22

# Contrato de `calibration_scope`

## Fuente de verdad

`backend/app/schemas/service_scope.py` define las claves persistentes. Para servicios de calibración, el subconjunto de acreditación contiene exactamente:

| Clave | Significado de negocio | Tipo de certificado |
| --- | --- | --- |
| `accredited_iso_17025` | Acreditación propia ISO/IEC 17025 | `acreditado` / folio `MYCA` |
| `traceable` | Servicio trazable o no acreditado | `trazable` / folio `MYCT` |
| `accredited_linked_lab` | Acreditación por laboratorio vinculado | `vinculado` / prefijo congelado de la empresa vinculada |

La clasificación comercial `accredited | traceable | linked`, las empresas y
los prefijos se rigen por
[`services/SERVICE_TYPE_AND_LINKED_LABORATORIES.md`](services/SERVICE_TYPE_AND_LINKED_LABORATORIES.md).
No modifica las claves operativas de este contrato.

Las leyendas, números o frases impresas en plantillas y certificados —por ejemplo `Certificado / Certificate: L25-313`— son contenido documental. Nunca son claves del dominio, valores de API ni discriminantes persistentes.

## Propagación automática

La clave se configura en la partida del Catálogo MYC y se conserva en la cadena:

```text
Catálogo → partida de Cotización → partida del ETS → capacidad por alcance
         → Equipo → tipo y folio de Certificado → snapshot del Master y contexto
```

El alta de equipo reutiliza `resolve_equipment_calibration_scope`: si sólo existe una modalidad con cupo, se asigna automáticamente; si existen varias, la interfaz solicita únicamente la desambiguación necesaria entre modalidades ya configuradas. No existe una selección libre, no se infiere desde texto documental y no se duplica el cálculo de capacidad.

El ETS congela también `expected_certificate_master_id` en la partida operativa. Equipos deriva de esa misma partida el Master y guarda un contexto versionado con `calibration_scope`, tipo de certificado, identificador del Master y referencias de origen. El catálogo no participa nuevamente en el alta del equipo y `service_name` nunca es llave de resolución.

Perfiles técnicos e interpretaciones documentales consumen el mismo `AccreditationScope`; no mantienen un enum paralelo. `special` no es una modalidad de acreditación y queda fuera del contrato. La migración se niega a reinterpretarlo silenciosamente si aparece en una instalación.

## Validación por categoría

`ServiceScope` también contiene alcances propios de otros servicios —mantenimiento, capacitación, validación, calificación y consultoría— porque la columna histórica `calibration_scope` se reutiliza para ese propósito. `SERVICE_SCOPE_VALUES_BY_CATEGORY` valida que cada clave corresponda a su categoría. El subconjunto de acreditación anterior sólo es válido para `Calibracion`.

## Compatibilidad de datos

La revisión Alembic `fe6f7a8b9c0d` normaliza defensivamente en catálogo, cotizaciones, partidas ETS, equipos, interpretaciones y perfiles técnicos:

- `Certificado / Certificate: L25-313` y `accredited` → `accredited_iso_17025`;
- `linked_lab` → `accredited_linked_lab`.

La normalización es deliberadamente irreversible: el downgrade no reintroduce alias ni contenido documental.

## Consumidores obligatorios

- Backend: schemas operacionales, perfiles técnicos, capacidad de certificados y creación/actualización de equipos.
- Frontend: `frontend/src/constants/catalog.js` y las vistas que presentan capacidad o desambiguación del ETS.
- Datos: las seis tablas normalizadas por la migración.

Toda modalidad futura requiere primero una decisión de negocio y una actualización coordinada de este contrato, Pydantic, capacidad, certificado, frontend, migración y pruebas. No debe añadirse copiando texto de una plantilla.
