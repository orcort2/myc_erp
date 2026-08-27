> Estado: IMPLEMENTADO — EN REVISIÓN
>
> Corte verificado: 2026-08-27
>
> Alcance: cierre/firma parcial del agregado temporal OT LAB

# Cierre técnico — cohortes de cierre OT LAB

## Auditoría inicial

El código vigente confirmó los ocho supuestos: `_group()` devuelve la raíz y
todas sus hermanas; la validación editable, la invalidación, la firma y la
finalización operaban sobre ese grupo completo; cada `LabWorkOrder` ya poseía
`signature_session_id` y PDF/hash/fechas propios; y
`LabWorkOrderSignatureSession` ya versionaba por raíz. El modelo existente era
suficiente y no se creó migración.

## Solución aplicada

- Se mantuvo `_group()` como parentesco histórico y se añadieron helpers
  explícitos para miembros abiertos/editables y cohorte por sesión.
- Firma/finalización individual usan endpoints propios; el contrato grupal
  excluye OT `completed` y firma sólo las participantes abiertas.
- La raíz histórica se bloquea antes de calcular `max(version) + 1`, evitando
  versiones repetidas en PostgreSQL.
- Edición, equipo, invalidación y alta adicional nunca mutan una hermana
  completada. Datos generales sólo se propagan a integrantes `draft`.
- Reapertura por Ticket sigue la sesión: una cohorte individual reabre una OT;
  una compartida reabre exclusivamente sus participantes.
- Mobile muestra estado por folio, ofrece cierre grupal/individual, explica OT
  sin equipo y cambia al paso/PDF correspondiente al seleccionar una hermana.
- Auditoría registra raíz, sesión, participantes y scope explícito. La
  exportación conserva múltiples sesiones de una misma raíz.

## Evidencia automatizada

La suite nueva demuestra grupo anticipado 1/0/0, rechazo grupal, cierre
individual, edición posterior de hermanas, congelamiento binario/hash/fechas de
la completada, cierre grupal restante con otra sesión, export multisesión,
idempotencia, ausencia de equipo, reapertura individual, tenant scope y flujo
de OT sin hermanas. La prueba de concurrencia real queda opt-in mediante
`LAB_POSTGRES_TEST_URL`.

Mobile prueba cálculo de opciones, exclusión de completadas, contextos de
captura distintos, rutas explícitas y transición de estado al navegar folios.

Resultados finales tras alinear la regresión de seguridad con el permiso
deliberado de Técnico: seguridad Mobile 21 aprobadas, LAB 30 aprobadas/7
omitidas y suite backend global con 661 aprobadas, 7 omitidas y 19 subtests, sin
fallas. Mobile aprobó 85 pruebas, lint, TypeScript y export Expo para
iOS/Android/Web. Compilación Python, inventarios, Alembic y diff check fueron
correctos.

## Límites pendientes

Falta ejecutar la concurrencia opt-in con PostgreSQL y repetir QA físico en
Android/iPhone: ambas modalidades, orientación, scroll/firma, teclado,
selección de hermanas, PDF, errores y red. No hubo commit, push, deploy ni
modificación de base local.
