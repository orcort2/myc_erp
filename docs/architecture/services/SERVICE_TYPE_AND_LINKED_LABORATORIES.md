> Estado: VIGENTE
>
> Corte verificado: 2026-07-29

# Tipos de servicio y laboratorios vinculados

## Taxonomía

`ServiceType` centraliza tres códigos comerciales:

| Código | Etiqueta | `calibration_scope` operativo |
| --- | --- | --- |
| `accredited` | Acreditado | `accredited_iso_17025` |
| `traceable` | Trazable | `traceable` |
| `linked` | Vinculado | `accredited_linked_lab` |

`calibration_scope` mantiene su contrato técnico vigente; `service_type` no lo
reemplaza. Los aliases históricos sólo se normalizan en
`backend/app/schemas/service_type.py`.

## Empresas vinculadas

`linked_companies` conserva nombre, razón social opcional, abreviatura, prefijo
predeterminado, estado, notas y configuración documental. La migración inicial
crea CAPYMET/CMVG y BESS/BESS. La UI permite registrar otra empresa sin
hardcodearla.

Un servicio `linked` exige empresa activa y prefijo propio normalizado:
mayúsculas, alfanumérico, sin espacios y longitud 2–12. Acreditado y trazable
limpian esos campos.

## Snapshots

La partida congela dentro de `operational_snapshot` identidad/nombre/
descripción/tipo, empresa, prefijo, precio, impuesto, alcance, trazabilidad,
procedimiento y plantilla disponibles. `ServiceOrderItem.service_snapshot`
propaga esa evidencia y Equipo copia tipo, empresa y prefijo. Certificados
vinculados usan exclusivamente `equipment.certificate_prefix_snapshot`; no
reconsultan el catálogo.

Servicios antiguos con alcance vinculado se clasifican como `linked`, pero no
reciben una empresa inventada. Deben completarse antes de una nueva cotización
o reconstrucción.
