# Cierre técnico — vertical slice OT LAB

**Fecha:** 2026-08-13  
**Estado:** TERMINADO TÉCNICAMENTE — EN REVISIÓN OPERATIVA  
**Estado canónico del módulo:** `EN DESARROLLO`

## Entrega

Se implementó el vertical temporal y removible de OT LAB desde autenticación
interna hasta PDF individual. La jerarquía funcional aplicada es: las OT raíz
y adicionales forman un único grupo; se capturan técnico y cliente una sola
vez; todas las OT referencian la misma sesión; firmar bloquea de inmediato
nuevas OT/equipos; finalizar produce un PDF institucional por folio.

El backend incorpora modelos, schemas, servicio, router, migración, permisos,
auditoría, folios 6400–6999, límite 10, herencia, cadena explícita, PDF final y
exportación ZIP verificable. La app incorpora login JWT, SecureStore,
renovación de token, lista/alta, captura compacta, editor secundario,
navegación por folios relacionados, firma táctil, cierre, impresión y compartir.

## Evidencia

- Backend focal: `38 passed, 1 skipped` para LAB, conformidad API, integridad de
  esquema y scope móvil.
- Suite LAB: `7 passed` en SQLite y `1 passed` concurrente en PostgreSQL;
  incluye 6400/6401, 6999 sin 7000, 10/11 equipos,
  6400→6401→6402, sesión compartida, bloqueo, contenido extraído de ambos PDFs
  y manifiesto.
- Regresión backend completa: `509 passed, 1 skipped`, 19 subtests; sin fallos.
- `python -m compileall app`: correcto.
- PostgreSQL temporal: `base → c6e8a1b4d2f9`, `current` en head y
  `alembic check`: `No new upgrade operations detected`; dos transacciones
  simultáneas recibieron `[6400, 6401]` y dos solicitudes concurrentes de OT
  adicional produjeron una sola `6403` más un rechazo `409`, sin duplicidad.
- Inventario API: `383/383` operaciones clasificadas y CSV coincidente.
- Móvil: `npx tsc --noEmit` correcto; `npm run lint` correcto;
  `npx expo-doctor`: 18/18.

## Alcance preservado

- No se crearon registros ni dependencias hacia entidades productivas.
- No se modificó el Motor de Resoluciones.
- No se modificó `myc-mobile-sdk57-backup`.
- No se aplicó la migración a la base ERP compartida ni se regeneró el respaldo
  oficial; la validación usó una base temporal eliminada al terminar.

## Pendientes de aceptación

1. Aplicar `c6e8a1b4d2f9` en el entorno operativo autorizado y regenerar el
   respaldo oficial conforme al procedimiento del repositorio.
2. Ejecutar el recorrido completo en iPhone físico/Expo Go con backend LAN,
   impresión AirPrint y hoja de compartir.
3. Resolver las 22 vulnerabilidades reportadas por `npm install` mediante una
   actualización controlada; no ejecutar `audit fix --force` sin revisión.
