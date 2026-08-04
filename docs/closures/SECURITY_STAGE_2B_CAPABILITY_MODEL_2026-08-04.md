> Estado: TERMINADA Y TÉCNICAMENTE CERRADA
>
> Fecha: 2026-08-04
>
> Alcance: Etapa 2B — Modelo Institucional de Capacidades

# Cierre técnico de Etapa 2B

## Dictamen

El snapshot técnico fue revisado completamente y estableció el gobierno previo
al código. La jerarquía obligatoria es
`Módulo→Acción→Microacción`; un permiso nuevo debe existir y aprobarse en el
catálogo antes de llegar a `permissions.py`, roles o usuarios. El catálogo no
genera código y `permissions.py` continúa como bootstrap temporal.

## Inventario revisado

| Métrica | Resultado |
| --- | ---: |
| Módulos | 36 |
| Acciones | 213 |
| Microacciones | 798 |
| HTTP existentes | 305 |
| Propuestas granulares de campo | 493 |
| Claves propuestas únicas | 658 |
| Permisos bootstrap actuales | 140 |
| Coincidencias literales | 61 |
| Pendientes de reconciliación | 79 |
| Permisos HTTP únicos | 72 |
| Brechas HTTP catálogo/bootstrap | 19 / 1 |

## Arquitectura futura documentada

El modelo definitivo deberá soportar roles, grupos múltiples, roles múltiples
por usuario, herencia, allow/deny individual, ownership, scopes, temporalidad,
protección crítica y `PortalMembership`. Ninguno de esos modelos fue
implementado aquí.

## Validación

`venv/bin/python scripts/validate_capability_catalog.py --check` recorre las
798 filas y falla si el catálogo, bootstrap o inventario cambian sin
reconciliar el snapshot. La brecha completa, redundancias y amplitudes están en
`CAPABILITY_MODEL_GAPS_2026-08-04.md`.

La validación funcional posterior, previa a ETAPA 3, conservó este inventario
como evidencia reproducible y trasladó la autoridad objetivo a
`CATALOGO_INSTITUCIONAL_FUNCIONAL_ERP_MYC.md`. Esta precisión no reabre ni
modifica el cierre técnico de ETAPA 2B.

La regresión compartida cerró con 430 pruebas backend y 19 subtests, 31 pruebas
frontend, compilación Python correcta y build frontend correcto.

## Exclusiones cumplidas

No se modificó `permissions.py`, no se rediseñó Ajustes, no se implementó RBAC,
no se cambió comportamiento de usuarios, no se renombraron permisos y no se
alteró flujo funcional.
