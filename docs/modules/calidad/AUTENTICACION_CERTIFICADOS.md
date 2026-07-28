> Estado: VIGENTE
>
> Tipo: Arquitectura vigente
>
> Autoridad: Alta para el flujo Calidad → Autenticación
>
> Prevalece sobre: descripciones históricas que exijan carga previa de PDF, `final_pdf_path` o matching PDF–Excel para autenticar
>
> Corte verificado: 2026-07-21

# Autenticación de certificados desde Calidad

## Contrato vigente

```text
Master XLSX identificado
→ quality_review
→ Calidad aprueba el Master
→ quality_approved
→ Autenticar habilitado
→ generar PDF final desde el Master aprobado
→ aplicar sello, código y QR
→ authenticated
```

Aprobar y autenticar son operaciones separadas. La única compuerta de Autenticar es que el certificado esté en `quality_approved`; `approved` se admite exclusivamente como alias legacy equivalente. Los estados de Captura, `quality_review`, `rejected`, `cancelled`, `authenticated` y liberado no permiten repetir la acción.

No son requisitos de autenticación: un PDF previamente cargado, `final_pdf_path`, `match_status`, matching PDF–Excel ni validación manual de un PDF. El valor de `match_status` no se modifica durante la autenticación.

## Generación y persistencia

El servicio toma el registro `identified` más reciente de `certificate_capture_files`, conserva ese ID y nombre en la auditoría y resuelve su XLSX. En una copia temporal oculta hojas auxiliares sin área de impresión, convierte el libro mediante el ejecutable resuelto desde `LIBREOFFICE_EXECUTABLE`, PATH o rutas del sistema y no altera el Master original.

La misma operación:

- persiste el PDF final generado y su versión vigente;
- aplica el autenticador lateral/QR existente y persiste el PDF autenticado;
- registra código, hash, actor y fecha de autenticación;
- transita a `authenticated`;
- crea el evento `certificate.pdf_authenticated` con estado anterior/nuevo, rutas y referencia al Master.

Una falla del conversor o un Master ausente cancela la operación con error; no se marca autenticado sin archivos válidos.

## Actualización visual

Tras aprobar o autenticar, Calidad reemplaza el certificado seleccionado con la respuesta persistida y vuelve a consultar certificados, archivos/readiness y agregados. Así actualiza tarjeta, botón y contadores sin recarga manual. La vista ETS replica actualmente la acción y también refresca sus datos; esa duplicación está registrada como `TD-007` y no constituye una segunda regla funcional.

### Navegación consecutiva dentro del modal

El modal reutiliza `client-modal-header` y `client-modal-navigator`, el mismo patrón visual de Clientes. Las flechas operan por índice sobre una fotografía de la lista contextual visible al abrirlo y no cierran ni reconstruyen el modal.

- Prioridad de frontera: misma OT agrupada, después mismo ETS y finalmente lista filtrada visible.
- Primer registro: Anterior deshabilitado; último registro: Siguiente deshabilitado; no hay navegación circular.
- Cada movimiento solicita en paralelo el certificado fresco y sus audit logs. Mientras resuelve, oculta la ficha anterior, muestra carga y bloquea ambas flechas.
- Un identificador de solicitud descarta respuestas superadas; un bloqueo inmediato evita solicitudes duplicadas por clic rápido.
- Si falla, conserva el último certificado válido, muestra `No fue posible cargar el certificado.` y ofrece Reintentar.
- El modal no contiene edición diferida: las acciones persisten inmediatamente, por lo que no existe un borrador silencioso que confirmar antes de navegar.
- Aprobar, rechazar/regresar y autenticar refrescan el certificado activo y mantienen la misma lista/posición contextual.

La navegación muestra y recalcula folio, ETS/OT, equipo, Master, advertencias, diferencias, estado, fechas, actores, historial y acciones. Los controles declaran `aria-label="Certificado anterior"` y `aria-label="Certificado siguiente"`, usan `disabled` real y heredan foco/hover del patrón compartido.

## Readiness y liberación posterior

La autenticación no libera al cliente. Un certificado se interpreta documentalmente “Listo para liberar” cuando su estado es `authenticated` y el PDF autenticado existe y no está vacío. `match_status` puede permanecer `pending` en registros vigentes o históricos y no participa en esta decisión.

- Documento listo + pago cubierto/no requerido: Liberar habilitado.
- Documento listo + pago pendiente: “Pendiente de pago”, Liberar deshabilitado.
- Documento liberado: `released_to_client`, actor/fecha/auditoría y visibilidad al cliente.

El backend devuelve conflictos estructurados `certificate_not_authenticated`, `authenticated_document_missing`, `payment_pending` o `already_released`. La liberación individual y masiva usan la misma semántica; no requieren `final_pdf_path` ni match aceptado.

El caso real consultado sin mutación fue el certificado `2`, folio `MYCA-07-2026-0002`: `authenticated`, `match_status=pending` y PDF autenticado existente. Su ETS requiere pago y no tiene factura liquidada; por tanto se deriva “Pendiente de pago” y no un bloqueo de match. El escenario con pago habilitado se validó por HTTP automatizado y respondió `200`, persistiendo liberación, actor y fecha.

## Resolución extraordinaria de liberación incorrecta

Fase 9 incorpora el caso interno
`certificate.resolve_incorrect_release`. No cambia el flujo ordinario de
autenticación o liberación: ante una liberación ya consumada, el Motor puede
coordinar el retiro del acceso futuro y el servicio canónico cambia únicamente
`client_visible` a falso. Estado, fecha, actor y PDF autenticado se preservan.

La operación usa lock e idempotencia propietaria, conserva snapshots y
auditoría append-only en la misma transacción y puede compensarse restaurando
la visibilidad sólo si el certificado no presenta deriva. No existe endpoint
nuevo ni lógica del dominio dentro del adaptador del Motor.

Un replay exacto de ejecución o compensación recupera el resultado append-only
antes de consultar el certificado, incluso si después cambió o quedó inactivo.
Hash, operación o payload distintos se rechazan. Para una clave nueva se repite
el lookup después del lock; el snapshot posterior se toma tras `flush` y
`refresh`, por lo que coincide con `updated_at` y el estado realmente
persistidos.

## Evidencia del caso real

La validación reversible del certificado `1` ejecutó:

```text
capture_in_progress
→ quality_review
→ quality_approved
→ authenticated
```

Los tres POST devolvieron HTTP 200. La descarga autenticada devolvió HTTP 200, `application/pdf`, encabezado `%PDF`, 310,443 bytes y tres páginas. El PDF final intermedio tuvo 188,349 bytes y tres páginas; la hoja auxiliar del Master quedó fuera. Actor `1`, fechas, versión y los tres eventos de auditoría conservaron el Master identificado. `match_status` permaneció `pending`. La transacción y las rutas temporales se revirtieron al terminar para no alterar datos históricos.

## Dependencia operativa

Cada entorno debe disponer de un conversor compatible con LibreOffice. La variable canónica es `LIBREOFFICE_EXECUTABLE`; acepta una ruta absoluta o un comando disponible en `PATH`. `OFFICE_CONVERTER_BINARY` continúa aceptándose como alias para instalaciones anteriores.

La resolución se ejecuta en este orden:

1. ruta o comando configurado explícitamente;
2. `soffice` en `PATH`;
3. `libreoffice` en `PATH`;
4. rutas comunes del sistema operativo:
   - macOS: `/Applications/LibreOffice.app/Contents/MacOS/soffice` y LibreOfficeDev;
   - Windows: `C:\Program Files\LibreOffice\program\soffice.exe` y la variante `Program Files (x86)`;
   - Linux: `/usr/bin/soffice` y `/usr/bin/libreoffice`.

`scripts/myc doctor` reporta disponibilidad, ejecutable resuelto, origen y versión. El arranque del backend registra el mismo diagnóstico sin impedir que otros módulos funcionen cuando falta el convertidor. La conversión usa argumentos separados, perfil y directorio temporal aislados, timeout, captura de salida, comprobación de PDF no vacío y limpieza automática. Los detalles técnicos quedan en logs y el frontend recibe un mensaje seguro.

En el ambiente macOS verificado se instaló LibreOffice estable `26.2.4.2` y `backend/.env` fija `LIBREOFFICE_EXECUTABLE=/Applications/LibreOffice.app/Contents/MacOS/soffice`. Doctor lo resuelve con origen `configured_path`, por lo que el backend no depende del `PATH` temporal de Codex. Windows y Linux deben configurar su ruta estable en cada despliegue o garantizar uno de los comandos soportados en `PATH`.
