# Cierre técnico — acceso móvil acotado para técnicos

> Estado: TERMINADO — EN REVISIÓN
>
> Fecha: 2026-08-12

## Resultado

El backend expone ocho endpoints móviles de sólo lectura para ETS, OT, Equipos
y Hojas de Campo. Todas las listas y detalles aplican ownership desde
`ServiceOrder.technician_id`; recursos ajenos o sin asignación responden `404`.
Hojas de Campo exige además `field_sheets.read`.

No se agregaron columnas ni migraciones. El ERP web conserva sus rutas y el rol
`Tecnico` conserva `service_orders.read`. No se modificó `myc-mobile`, el Motor
de Resoluciones ni ningún endpoint interno vigente.

## Defectos corregidos

1. El inventario y el conteo sólo incluían dos de ocho endpoints.
2. Hojas de Campo no exigía `service_orders.read_assigned`.
3. Las listas de OT, Equipo y Hoja duplicaban SQL dentro del router.
4. La prueba inicial sólo cubría ServiceOrder y activaba el lifespan contra la
   base local, impidiendo el aislamiento SQLite.
5. El baseline del catálogo no reconocía todavía la nueva clave asignada; se
   registró como vigésima diferencia gobernada, sin alterar el catálogo
   funcional congelado.

## Evidencia

| Validación | Resultado |
| --- | --- |
| `python -m compileall app` | correcto |
| `test_mobile_technician_scope.py -q` | 21 passed, 2 warnings conocidos |
| `test_api_access_conformity.py -q` | 4 passed, 1 warning conocido |
| Backend completo | 496 passed, 19 subtests, 3 warnings conocidos |
| Inventario runtime | 371/371 operaciones clasificadas |
| Catálogo/bootstrap/API | 73 permisos HTTP, 20 diferencias gobernadas, 0 gaps de bootstrap |

## Deuda conservada

- La sesión móvil/revocación no pertenece a este alcance; se reutiliza el JWT
  interno vigente.
- No existe todavía asignación multi-técnico por OT.
- `service_orders.read_assigned` requiere decisión institucional posterior
  frente al catálogo funcional congelado; el backend y el inventario ya son
  consistentes y no se sustituyó por un permiso semánticamente más débil.
