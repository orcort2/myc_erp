> Estado: TERMINADO TÉCNICAMENTE — EN REVISIÓN
>
> Corte verificado: 2026-09-01
>
> Alcance: Fase 3 del vertical temporal LAB, recepción → FieldSheets → cierre

# Cierre técnico Fase 3 LAB

## Resultado

El flujo nuevo queda:

```text
draft
→ recepción técnico + cliente
→ received_signed
→ primera FieldSheet creada
→ in_progress
→ todas las FieldSheets requeridas completas
→ ready_to_close
→ cierre
→ completed
```

La firma acredita recepción y no cierre. Mobile captura las firmas por pasos,
pero la primera permanece sólo en memoria local: el backend recibe un único
payload con técnico y cliente, valida ambas imágenes y crea entonces
`LabWorkOrderSignatureSession`. No existe sesión incompleta persistida.

## Invariantes verificadas

- Prerrequisitos previos: equipo, `service_type`, MYCA/MYCT reservado o
  autorizado, `LinkedCompany` cuando aplica y cliente documental resoluble.
- Recepción grupal transaccional; una integrante inválida bloquea toda la
  cohorte.
- Después de `received_signed`, backend rechaza las mutaciones administrativas
  de OT/equipo/cliente/servicio/empresa vinculada/folio.
- La creación real de la primera FieldSheet es el único punto
  `received_signed → in_progress`.
- Cada FieldSheet conserva el `signature_session_id` vigente de su propia OT en
  el momento de creación; no busca la última sesión del grupo.
- La última hoja requerida completa produce `ready_to_close` dentro de la misma
  transacción. El cierre no vuelve a pedir firma.
- `ready_for_signatures` permanece legacy y conserva sesión/flujo histórico.
- Reapertura `preserve` e `invalidate`, recepción grupal/individual, partial
  close, grupos anticipados, folios, máximo de diez equipos y excepción externa
  histórica conservan sus contratos.
- Captura recibe `lab_field_sheets.capture` para leer y operar hojas, sin alta,
  configuración, firma, folios, cierre, cancelación o resolución de Tickets.
- Mobile muestra revisión de recepción y resumen read-only, presenta estados
  nuevos y evita lenguaje de cierre durante la recepción.

## Validaciones

- Fase 3 backend: `46 passed`.
- LAB backend focal: `132 passed, 8 skipped`.
- Seguridad/permissions focal: `45 passed`.
- Backend completo: `811 passed, 8 skipped, 19 subtests passed, 2 failed`.
  Las dos fallas son la deuda preexistente del inventario API: el runtime tiene
  499 operaciones y el snapshot/test aún fija 477.
- Mobile focal: `42 passed`.
- Mobile completo: `157 passed`.
- `npx tsc --noEmit`: correcto.
- `npm run lint`: correcto.
- `lab-work-order-closure.test.ts`: correcto dentro de focal y suite completa.
- Alembic: único head `a3983f9a6ca9`.
- No se creó ni aplicó migración y no se modificó la base local.

## Pendientes y límites

La Fase 3 permanece **EN REVISIÓN**, no SELLADA, hasta ejecutar QA físico en
Android/iPhone/TestFlight para firma, orientación, teclado, scroll, transición
recepción/captura/cierre, impresión/compartir, errores y refresh/realtime. Los
problemas de contenido/layout/imprimibles de FieldSheets auditados por separado
y NIIMBOT permanecen expresamente fuera de este alcance.
