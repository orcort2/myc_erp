# Autoridad permanente de MYC Mobile

Este archivo debe leerse completo antes de crear, editar, reparar, refactorizar,
eliminar, mover, integrar, reformar o auditar con intención de modificar
cualquier código dentro de `myc-mobile/`.

## Expo SDK 54

Read the exact versioned docs at https://docs.expo.dev/versions/v54.0.0/ before writing any code.

Todo cambio relacionado con Expo, React Native, orientación o configuración
nativa debe contrastarse con esa versión exacta antes de implementarse.

## Naturaleza temporal del LAB

MYC Mobile funciona actualmente como LAB operativo temporal para crear,
capturar, firmar y cerrar OT LAB. Todavía no es la aplicación conectada de
forma definitiva al flujo productivo real del ERP y será retirada o reemplazada
cuando esa integración sea autorizada e implementada.

## Aislamiento arquitectónico

`myc-mobile/` debe permanecer conceptual y técnicamente aislado de `frontend/`
y de todos los flujos productivos del ERP. El código productivo sólo puede
consultarse como referencia visual, UX o conceptual cuando la tarea lo solicite
expresamente. Esa consulta no autoriza copiar lógica, importar componentes,
compartir estado o servicios, crear dependencias cruzadas, reutilizar endpoints
o modelos productivos ni trasladar reglas de negocio.

Una referencia visual del ERP significa reimplementar la experiencia dentro de
React Native/Expo y MYC Mobile; nunca conectar el componente web al móvil.

## Firmas LAB

La implementación móvil de firmas es autónoma. Su estado, persistencia,
endpoints `/mobile/v1/technician/...`, validaciones, sesión grupal, ciclo de
vida y política de reapertura pertenecen exclusivamente al LAB móvil existente,
aunque la presentación tome como referencia visual el sistema de firmas del
ERP. No se deben trasladar controladores, estados, servicios, endpoints ni
reglas productivas.
