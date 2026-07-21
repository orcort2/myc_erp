> Estado: HISTÓRICO
>
> Tipo: Histórico
>
> Autoridad: Baja; especificación aspiracional de una etapa anterior
>
> Prevalece sobre: ninguno
>
> Reemplazado por: `../../project/CURRENT_SCOPE.md`, `../../project/CURRENT_PROCESS_FLOW.md`, `../../project/BUSINESS_RULES.md` y `../../project/DECISIONS.md`

# Sistema ERP MYC - Especificacion V2 basada en flujo de calidad

## 1. Proposito del sistema

El sistema ERP MYC debe controlar y gestionar cada proceso operativo indicado en el sistema de calidad de la empresa, desde la captacion del lead hasta el cierre del servicio, liberacion de certificados, facturacion, cobranza, encuesta de satisfaccion y reportes finales de rentabilidad.

El sistema no debe ser solo un control administrativo. Debe ser una plataforma operativa donde cada area trabaje sobre el mismo expediente de servicio, con trazabilidad completa por cliente, equipo, cotizacion, llamado, orden de servicio, certificado, pago y factura.

## 2. Areas cubiertas

### Comercial

Responsable del inicio del servicio:
- Captacion de leads desde pagina web, landing pages, chat o captura manual.
- Registro de datos fiscales y de contacto.
- Creacion y envio de cotizaciones.
- Seguimiento de cotizaciones.
- Control de estados comerciales.
- Confirmacion de servicios aprobados.
- Comunicacion con cliente durante el flujo.

### Tecnica

Responsable de la ejecucion en campo o laboratorio:
- Recepcion o alta de equipos.
- Registro de condiciones iniciales.
- Captura de datos tecnicos.
- Seleccion de patrones de calibracion.
- Captura de resultados de calibracion o mantenimiento.
- Evidencia fotografica.
- Impresion y validacion de etiquetas.
- Cierre tecnico del servicio.

### Captura

Responsable de convertir la informacion tecnica en certificados:
- Revision de informacion capturada por tecnico.
- Validacion de marca, modelo, serie e identificacion interna.
- Revision de evidencias.
- Seleccion de plantilla master.
- Validacion de trazabilidad.
- Validacion de incertidumbres.
- Generacion de certificado.

### Calidad

Responsable de validacion final:
- Revision de certificados.
- Validacion de incertidumbres.
- Autorizacion documental.
- Liberacion a documentacion.
- Seguimiento de satisfaccion del cliente.
- Informacion disponible para auditorias.

### Documentacion

Responsable del expediente documental:
- Reportes de mantenimiento.
- Certificados de calibracion.
- Comprobantes de pago.
- Prefacturas.
- Facturas timbradas.
- Evidencias.
- Documentos finales liberados al cliente.

### Financiera

Responsable de cobranza, facturacion y control economico:
- Seguimiento de pagos.
- Validacion de comprobantes.
- Control de servicios pagados y pendientes.
- Prefacturacion.
- Timbrado.
- Historico real de facturacion mensual.
- Control de atrasos.

## 3. Glosario operativo

| Concepto | Definicion |
| --- | --- |
| Cliente | Comprador o receptor del servicio. |
| Usuario | Colaborador interno que opera el sistema e interactua con el cliente. |
| Tecnico | Colaborador de campo o laboratorio que ejecuta el servicio. |
| Cotizacion | Documento comercial con servicios, equipos, precios y condiciones. |
| Agenda | Pre-servicio creado cuando una cotizacion es aceptada. |
| Llamado | Seguimiento tecnico donde se recolecta la informacion de equipos. |
| Orden de servicio | Servicio formal en proceso con equipos dados de alta individualmente. |
| Equipo | Unidad individual a calibrar, mantener, revisar o atender. |
| Hoja de campo | Vista imprimible y editable donde el tecnico registra datos del equipo. |
| Realizando | Estado del equipo cuando ya esta dentro de una orden de servicio activa. |
| Calibrado | Estado del equipo cuando los datos tecnicos fueron completados. |
| Etiquetado | Estado del equipo cuando la etiqueta fue impresa, pegada y validada. |
| Cerrar servicio | Accion que termina la etapa tecnica y envia a captura/calidad. |
| Certificado de calibracion | Producto documental final de una calibracion. |
| Plantilla master | Formato que transforma hoja de campo en certificado con calculos, incertidumbres y resultados. |
| Patron de calibracion | Equipo patron usado para realizar la calibracion. |
| Egreso por servicio | Gasto adicional asociado al servicio: material, externo, viaticos u otro. |

## 4. Codigos y folios

### Cotizacion

Formato:

```text
MYC-MM-AA-XXXX
```

Reglas:
- Lo genera el sistema.
- Debe ser unico.
- Se crea al guardar o enviar la cotizacion.
- Da origen a una oportunidad de venta.
- No se reutiliza aunque la cotizacion sea cancelada.

### Agenda

Formato:

```text
AMYC-AA-MM-XXXX
```

Reglas:
- Se crea al aceptar una cotizacion.
- Representa un pre-servicio programable.
- Hereda datos del cliente, servicios y partidas aprobadas.
- Permite modificar datos de emision de certificados cuando el resultado debe salir a otro nombre.

### Llamado o seguimiento

Formato:

```text
SMYC-AA-MM-XXXX
```

Reglas:
- Se crea desde la agenda.
- Controla la recoleccion de informacion de equipos.
- Debe generar espacios de captura segun la cantidad de equipos cotizados y aprobados.
- Puede recibir equipos agregados mediante flujo de autorizacion.

### Orden de servicio

Formato:

```text
OSMYC-AA-MM-XXXX
```

Reglas:
- Se crea cuando el llamado se cierra.
- Coloca los equipos individuales en estado Realizando.
- Es el identificador operativo del servicio en proceso.

### Certificado de calibracion

Formato:

```text
MYC{A|T}-MM-AAAA-XXXX
```

Donde:
- A = servicio acreditado.
- T = servicio trazable.

Reglas:
- Se genera cuando el equipo pasa a Calibrado.
- Esta asociado a un equipo individual.
- Se conserva aunque el certificado sea cancelado o reemitido.
- Debe aparecer en el certificado final.

### Identificador interno de certificado

Reglas:
- Debe existir ademas del folio visible.
- Se usa para codigo de barras.
- Se imprime en los costados de todas las hojas.
- Debe permitir validar autenticidad y version.

## 5. Estados principales

### Estados de lead

- Nuevo
- Contactado
- En cotizacion
- Cotizado
- Descartado
- Convertido a cliente

### Estados de cotizacion

- Borrador
- Enviada
- En espera
- Recordatorio 2 dias
- Por vencer
- Cancelada por vencimiento
- Revigenteada
- Aceptada
- Rechazada
- Convertida a agenda

### Estados de agenda

- Creada
- Pendiente de programacion
- Fecha propuesta
- Confirmada por cliente
- Confirmada por usuario
- Convertida a llamado
- Cancelada

### Estados de llamado

- Abierto
- Capturando equipos
- Solicitud de agregado pendiente
- Agregado autorizado
- Pendiente de firma del cliente
- Cerrado
- Convertido a orden de servicio
- Cancelado

### Estados de orden de servicio

- Abierta
- En proceso
- En pausa
- Cierre tecnico pendiente
- Cerrada tecnicamente
- En captura
- En calidad
- Documentacion lista
- Pendiente de pago
- Pago validado
- Certificados liberados
- Cerrada comercialmente
- Finalizada
- Cancelada

### Estados de equipo

- Pendiente de alta
- Realizando
- No realizado
- Calibrado
- Etiqueta pendiente
- Etiqueta en validacion
- Etiquetado
- En captura
- Certificado en revision
- Certificado autorizado
- Liberado

### Estados de certificado

- Pendiente
- En captura
- En revision de calidad
- Autorizado
- Liberado
- Activo
- Suspendido
- Cancelado
- Reemitido

### Estados financieros

- Pendiente de pago
- Comprobante recibido
- Pago en validacion
- Pago validado
- Prefactura generada
- Prefactura aprobada por cliente
- Listo para timbrar
- Timbrado
- Factura liberada
- Vencido

## 6. Flujo completo del servicio

### 6.1 Captacion del lead

Origenes:
- Pagina web.
- Landing page.
- Chat.
- Captura manual por asesor.
- Cliente existente.

Funciones:
- Recibir lead en tiempo real.
- Notificar a asesor.
- Abrir conversacion o expediente comercial.
- Solicitar constancia de situacion fiscal cuando aplique.
- Permitir carga de documento por el cliente.
- Extraer datos fiscales y de contacto.
- Borrar documento fiscal despues de extraer datos, conservando solo informacion necesaria.

Reglas:
- El asesor debe poder cotizar en tiempo real desde el expediente del lead.
- Si el cliente ya existe, el sistema debe sugerir empatarlo con el registro existente.
- La informacion sensible debe estar protegida por permisos.

### 6.2 Cotizacion

Funciones:
- Crear cotizacion desde lead o cliente.
- Seleccionar servicios del catalogo.
- Definir cantidad de equipos por servicio.
- Registrar condiciones comerciales.
- Generar PDF.
- Enviar por correo.
- Imprimir o compartir dentro del chat.
- Crear oportunidad de venta.

Reglas:
- Al enviar cotizacion inicia el reloj de seguimiento.
- Toda cotizacion enviada debe quedar almacenada.
- Cada cotizacion debe tener responsable comercial.
- Toda actualizacion debe generar version.

Automatizaciones:
- Dia 0: cotizacion enviada, estado En espera.
- Dia 2 sin cambio: reenviar recordatorio al cliente y notificar al usuario creador.
- Dia 4 sin cambio: enviar recordatorio gentil de proximo vencimiento.
- Dia 6 sin cambio: cancelar folio comercialmente y enviar mensaje con boton para actualizacion.
- Si el cliente solicita actualizacion: crear acceso a dashboard y pedir registro.
- Al registrarse: reconocer cotizacion y pedir confirmacion del usuario para anclar cliente a cuenta.
- Cotizacion revigenteada: nueva vigencia de 15 dias.

### 6.3 Aceptacion de cotizacion y agenda

Cuando el cliente acepta:
- La cotizacion cambia a Aceptada.
- Se crea codigo de servicio.
- Se crea Agenda.
- Se traslada informacion del cliente.
- Se habilita edicion de datos de emision documental.
- Se programa fecha.
- La fecha puede ser confirmada por cliente o usuario.

Reglas:
- Una cotizacion aceptada no debe editarse directamente; debe versionarse.
- La agenda conserva liga con la cotizacion original.
- Cambios de razon social o receptor de certificado deben quedar en bitacora.

### 6.4 Llamado y alta de equipos

Al confirmar agenda:
- Se crea el codigo de llamado.
- Se generan espacios de equipos segun cantidad cotizada y aprobada.
- El tecnico o usuario captura informacion de cada equipo.

Datos minimos del equipo:
- Servicio asociado.
- Descripcion del equipo.
- Marca.
- Modelo.
- Numero de serie.
- Identificacion interna.
- Rango o alcance.
- Ubicacion.
- Condicion inicial.
- Observaciones.
- Fotos de evidencia.

Reglas:
- La cantidad de espacios iniciales debe coincidir con la cotizacion aprobada.
- No se puede cerrar llamado sin capturar equipos obligatorios o justificar faltantes.
- El cliente debe firmar conformidad de equipos autorizados para servicio.

### 6.5 Agregado de equipos

Escenario: cliente solicita agregar mas equipos.

Flujo:
1. Tecnico solicita agregado.
2. Sistema pregunta si el agregado corresponde a servicios ya cotizados.
3. Si corresponde a servicios cotizados, tecnico selecciona servicio aprobado y cantidad.
4. Si no corresponde, tecnico selecciona servicio nuevo desde catalogo.
5. Sistema crea partidas agregadas en estado Pendiente de autorizacion.
6. Sistema notifica al usuario que creo la cotizacion.
7. Usuario actualiza cotizacion.
8. Usuario envia cotizacion actualizada al cliente.
9. Cliente confirma desde dashboard o de forma verbal.
10. Usuario puede confirmar manualmente si existe autorizacion expresa.
11. Tecnico queda habilitado para grabar informacion de equipos agregados.

Reglas:
- Un equipo agregado no puede pasar a Realizando sin autorizacion comercial.
- Toda confirmacion verbal debe registrar comentario, usuario, fecha y evidencia si existe.
- La cotizacion actualizada debe quedar ligada al llamado.

### 6.6 Cierre de llamado y creacion de orden de servicio

Condiciones para cerrar llamado:
- Equipos capturados o justificados.
- Agregados autorizados o rechazados.
- Firma de conformidad del cliente.

Al cerrar:
- Se genera orden de servicio OSMYC-AA-MM-XXXX.
- Cada equipo se convierte en registro individual.
- Cada equipo entra en estado Realizando.
- Se habilita hoja de campo por equipo.

### 6.7 Ejecucion tecnica y hoja de campo

El tecnico:
- Busca equipo por numero de serie, identificacion interna o folio.
- Abre hoja de campo.
- Valida informacion precargada.
- Captura informacion faltante.
- Toma fotos visibles de marca, modelo, numero de serie y estado fisico.
- Selecciona patron de calibracion.
- Define tipo de servicio: acreditado o trazable.
- Captura resultados.
- Guarda cambios.

Reglas de evidencia:
- Si no existe marca, modelo, serie u otro dato visible, tecnico debe registrar comentario justificando la ausencia.
- La hoja de campo debe ser imprimible.
- La hoja de campo debe conservar historial de cambios.

Equipos no realizados:
- Si el cliente decide no realizar un equipo o existe causa mayor, tecnico marca No realizado.
- Sistema notifica al usuario comercial.
- El equipo no realizado queda en historial y no genera certificado.
- Finanzas debe recibir impacto para ajuste si aplica.

### 6.8 Patrones de calibracion

El sistema debe administrar patrones con:
- Identificacion del patron.
- Descripcion.
- Marca.
- Modelo.
- Serie.
- Alcance.
- Incertidumbre.
- Vigencia.
- Certificado vigente.
- Estado.
- Servicio compatible.

Reglas:
- No se puede seleccionar patron vencido.
- No se puede seleccionar patron fuera de alcance.
- El patron usado debe quedar ligado al equipo y al certificado.
- Cambios en datos de patron deben quedar auditados.

### 6.9 Calibracion, folio de certificado y etiqueta

Al guardar resultados completos:
- Equipo pasa a Calibrado.
- Sistema genera folio de certificado.
- Se habilita impresion de etiqueta.

Etiqueta:
- Debe contener datos minimos del equipo.
- Debe contener folio o identificador de certificado.
- Debe indicar fecha de calibracion y vigencia cuando aplique.
- Debe poder imprimirse.

Validacion de etiqueta:
1. Tecnico imprime y pega etiqueta.
2. Tecnico toma foto de etiqueta pegada.
3. Sistema envia validacion a segundo usuario disponible.
4. Validador revisa datos generales y foto.
5. Si aprueba, equipo pasa a Etiquetado.
6. Si rechaza, vuelve a Etiqueta pendiente con motivo.

Reglas:
- La validacion de etiqueta debe hacerla un usuario distinto al tecnico cuando sea posible.
- No se puede cerrar servicio si existen equipos calibrados sin etiqueta validada, salvo justificacion autorizada.

### 6.10 Cierre tecnico del servicio

Condiciones:
- Todos los equipos estan Etiquetados, No realizados o justificados.
- Evidencias completas.
- Resultados guardados.

Al cerrar:
- Orden pasa a Cerrada tecnicamente.
- Captura recibe notificacion.
- Se inicia proceso de certificados.

## 7. Captura y generacion de certificados

### 7.1 Validacion de captura

Captura debe revisar:
- Marca.
- Modelo.
- Serie.
- Identificacion interna.
- Fotos del tecnico.
- Patron usado.
- Tipo de servicio.
- Resultados.
- Trazabilidad.
- Motivos de equipos no realizados.

Reglas:
- Si existe duda, captura puede devolver al tecnico con comentario.
- La devolucion debe notificar al tecnico y al responsable de orden.
- No se puede generar certificado si faltan datos criticos.

### 7.2 Plantilla master

La plantilla master debe:
- Recibir datos desde hoja de campo.
- Contener calculos requeridos.
- Contener incertidumbres.
- Generar resultados de certificado.
- Estar asociada a tipo de servicio, magnitud, patron o familia de equipo.

Funciones:
- Cargar plantilla.
- Versionar plantilla.
- Activar/desactivar plantilla.
- Validar formulas.
- Probar plantilla con datos de ejemplo.

Reglas:
- Un certificado emitido debe guardar la version de plantilla utilizada.
- Cambios en plantilla no deben alterar certificados ya emitidos.

### 7.3 Generacion del certificado

Captura:
- Selecciona plantilla master.
- Valida incertidumbres.
- Confirma resultados.
- Genera certificado.
- Guarda certificado asociado al equipo.

Elementos de autenticacion:
- Folio de certificado.
- Codigo de barras con serie unica.
- Codigo QR con informacion general.
- Marca de agua con logo MYC y numero de acreditacion.
- Codigo visual codificado en esquinas o bordes segun reglas internas.
- Firma del tecnico.
- Firma de direccion MYC.

Datos QR sugeridos:
- Folio.
- Cliente.
- Equipo.
- Fecha de emision.
- Vigencia.
- Estado del certificado.
- URL de validacion.

Estados publicos del certificado:
- Activo.
- Cancelado.
- Suspendido.

### 7.4 Datos de acreditacion

Parametros configurables:
- Numero de acreditacion.
- Numero de certificado de acreditacion PJLA.
- Fecha de vigencia de acreditacion.
- Organismo acreditador.
- Logo o leyenda requerida.

Reglas:
- Estos valores se configuran manualmente por usuario autorizado.
- Deben aplicarse a plantillas que los requieran.
- Debe guardarse historial cuando cambien.

## 8. Calidad y documentacion

### 8.1 Revision de calidad

Calidad valida:
- Incertidumbres.
- Consistencia de resultados.
- Uso correcto de plantilla.
- Datos criticos.
- Estado documental.

Resultado:
- Autorizar.
- Rechazar con comentarios.
- Solicitar correccion.

Reglas:
- Un certificado no se libera sin autorizacion de calidad.
- Si el servicio tiene varios equipos, la documentacion final se cierra cuando todos los certificados requeridos esten autorizados.

### 8.2 Documentacion

Documentacion almacena:
- Certificados autorizados.
- Reportes de mantenimiento.
- Evidencias.
- Hoja de campo.
- Comprobantes de pago.
- Prefacturas.
- Facturas timbradas.
- Comunicaciones relevantes.

Reglas:
- El cliente no puede descargar certificados hasta que el pago este validado, salvo permiso especial.
- Documentos finales deben estar ligados a orden, cliente y equipo.

## 9. Finanzas, pago y facturacion

### 9.1 Aviso de cierre y solicitud de pago

Cuando certificados estan listos:
- Usuario recibe notificacion.
- Usuario informa al cliente que el servicio esta por terminar.
- Usuario solicita liquidacion.

### 9.2 Recepcion de pago

Flujo:
1. Cliente realiza pago.
2. Cliente comparte comprobante.
3. Usuario sube comprobante a documentacion.
4. Finanzas recibe notificacion.
5. Finanzas valida que el pago este reflejado.
6. Si es correcto, pago pasa a Validado.
7. Si no, pago pasa a Rechazado o Pendiente de aclaracion.

Reglas:
- Pago validado debe indicar monto, fecha, cuenta, referencia y usuario validador.
- Pagos parciales deben permitirse si la politica comercial lo acepta.
- El sistema debe calcular saldo pendiente.

### 9.3 Prefactura y timbrado

Flujo:
1. Finanzas genera prefactura sin timbrar.
2. Prefactura se comparte en documentacion.
3. Usuario confirma con cliente.
4. Cliente puede validar desde dashboard.
5. Usuario registra comentario de que esta listo para timbrar.
6. Finanzas timbra comprobante.
7. Factura timbrada queda disponible para cliente.

Reglas:
- No timbrar sin validacion de datos fiscales.
- La validacion puede ser directa del cliente o manual por usuario con comentario.
- Factura timbrada debe quedar en expediente.

### 9.4 Liberacion de certificados

Cuando pago esta validado:
- Certificados se liberan automaticamente.
- Cliente puede consultarlos en dashboard.
- Usuario puede enviarlos por correo desde el sistema.

Reglas:
- Si existe bloqueo financiero, documentacion permanece retenida.
- Liberaciones manuales requieren permiso especial y motivo.

## 10. Cierre, encuesta y reportes

### 10.1 Cierre comercial

El usuario:
- Confirma que certificados y factura fueron liberados.
- Cierra orden de venta.
- Marca servicio como finalizado.

### 10.2 Encuesta de satisfaccion

Al finalizar:
- Sistema envia encuesta por WhatsApp y correo.
- Cliente contesta.
- Sistema guarda resultado para auditoria.

Datos sugeridos:
- Calificacion general.
- Tiempo de atencion.
- Calidad tecnica.
- Comunicacion.
- Documentacion.
- Comentarios.
- Recomendaria el servicio.

### 10.3 Reporte final del servicio

El sistema debe consolidar:
- Tiempo desde lead a cotizacion.
- Tiempo desde cotizacion a aceptacion.
- Tiempo desde agenda a cierre tecnico.
- Tiempo de captura.
- Tiempo de revision de calidad.
- Tiempo de pago.
- Tiempo total del servicio.
- Ingreso total.
- Egresos por servicio.
- Costo estimado.
- Ganancia final.
- Equipos cotizados.
- Equipos realizados.
- Equipos no realizados.
- Equipos agregados.
- Responsable comercial.
- Tecnicos participantes.

## 11. Modulos definitivos del sistema

### 11.1 CRM y Leads

Funciones:
- Recibir leads.
- Gestionar conversaciones.
- Capturar datos fiscales.
- Crear cliente.
- Convertir a cotizacion.
- Seguimiento comercial.

Permisos:
- leads.ver
- leads.crear
- leads.editar
- leads.convertir
- leads.asignar

### 11.2 Clientes

Funciones:
- Alta de cliente.
- Contactos.
- Datos fiscales.
- Direcciones.
- Historial.
- Dashboard cliente.

Permisos:
- clientes.ver
- clientes.crear
- clientes.editar
- clientes.bloquear

### 11.3 Cotizaciones

Funciones:
- Crear.
- Versionar.
- Enviar.
- Reenviar.
- Revigentear.
- Aceptar.
- Rechazar.
- Cancelar.
- Convertir a agenda.

Permisos:
- cotizaciones.ver
- cotizaciones.crear
- cotizaciones.editar
- cotizaciones.enviar
- cotizaciones.revigorizar
- cotizaciones.confirmar_manual
- cotizaciones.cancelar

### 11.4 Agenda

Funciones:
- Programar servicio.
- Confirmar fecha.
- Ajustar datos documentales.
- Crear llamado.

Permisos:
- agenda.ver
- agenda.programar
- agenda.confirmar
- agenda.convertir_llamado

### 11.5 Llamados

Funciones:
- Alta de equipos.
- Solicitud de agregados.
- Firma de conformidad.
- Cierre de llamado.
- Conversion a orden de servicio.

Permisos:
- llamados.ver
- llamados.capturar
- llamados.solicitar_agregado
- llamados.cerrar

### 11.6 Ordenes de servicio

Funciones:
- Gestion de equipos.
- Hojas de campo.
- Evidencias.
- Resultados.
- Cierre tecnico.

Permisos:
- ordenes.ver
- ordenes.ejecutar
- ordenes.pausar
- ordenes.cerrar_tecnico
- ordenes.cancelar

### 11.7 Patrones

Funciones:
- Alta de patrones.
- Control de vigencia.
- Alcances.
- Incertidumbres.
- Certificados de patron.

Permisos:
- patrones.ver
- patrones.crear
- patrones.editar
- patrones.desactivar

### 11.8 Captura

Funciones:
- Validar datos de hoja de campo.
- Seleccionar plantilla master.
- Generar certificado.
- Devolver a tecnico.

Permisos:
- captura.ver
- captura.procesar
- captura.devolver
- captura.generar_certificado

### 11.9 Certificados

Funciones:
- Generar.
- Revisar.
- Autorizar.
- Liberar.
- Suspender.
- Cancelar.
- Reemitir.
- Validar por QR.

Permisos:
- certificados.ver
- certificados.generar
- certificados.autorizar
- certificados.liberar
- certificados.cancelar
- certificados.reemitir

### 11.10 Calidad

Funciones:
- Revision de certificados.
- Validacion de incertidumbres.
- Encuestas.
- Auditoria.

Permisos:
- calidad.ver
- calidad.revisar
- calidad.autorizar
- calidad.rechazar
- calidad.encuestas

### 11.11 Finanzas

Funciones:
- Validar pagos.
- Control de saldos.
- Prefacturas.
- Timbrado.
- Reporte mensual facturado.

Permisos:
- finanzas.ver
- finanzas.validar_pago
- finanzas.prefacturar
- finanzas.timbrar
- finanzas.liberar_excepcion

### 11.12 Documentacion

Funciones:
- Expediente documental.
- Control de archivos.
- Liberacion a cliente.
- Envio por correo.

Permisos:
- documentacion.ver
- documentacion.cargar
- documentacion.liberar
- documentacion.enviar

### 11.13 Reportes

Funciones:
- Tiempos de atencion.
- Rentabilidad.
- Egresos por servicio.
- Facturacion mensual.
- Servicios por tecnico.
- Cotizaciones por estado.
- Encuestas.

Permisos:
- reportes.ver
- reportes.exportar
- reportes.financieros
- reportes.calidad

## 12. Parametros configurables

### Comerciales

- dias_recordatorio_cotizacion_1 = 2
- dias_recordatorio_cotizacion_2 = 4
- dias_cancelacion_cotizacion = 6
- dias_vigencia_cotizacion_revigenteada = 15
- permitir_confirmacion_verbal = true
- requiere_evidencia_confirmacion_verbal = configurable

### Operativos

- permitir_equipo_no_realizado = true
- requiere_firma_cliente_cierre_llamado = true
- requiere_validacion_segundo_usuario_etiqueta = true
- permitir_cierre_servicio_con_etiquetas_pendientes = false
- permitir_patron_vencido = false
- permitir_patron_fuera_alcance = false

### Certificados

- numero_acreditacion
- numero_certificado_acreditacion_pjla
- organismo_acreditador
- vigencia_acreditacion
- url_validacion_certificado
- usar_codigo_barras = true
- usar_qr = true
- usar_marca_agua = true
- usar_codigo_visual_esquinas = true
- liberar_certificados_solo_con_pago_validado = true

### Finanzas

- permitir_pagos_parciales = configurable
- requerir_prefactura_cliente = true
- liberar_documentos_con_saldo = false
- dias_alerta_pago_vencido
- cuentas_bancarias_habilitadas

### Documentos

- tamano_maximo_archivo_mb
- tipos_archivo_permitidos
- retencion_documento_fiscal_original = false
- versionar_documentos = true

## 13. Funciones tecnicas principales

### Leads y clientes

```text
receive_lead(source, payload)
assign_lead(lead_id, user_id)
extract_tax_data(file_id)
delete_sensitive_source_file(file_id)
create_client_from_lead(lead_id)
link_client_to_dashboard_account(client_id, account_id, approved_by)
```

### Cotizaciones

```text
create_quote(client_id, user_id)
add_quote_service(quote_id, service_id, quantity)
send_quote(quote_id, channel)
run_quote_followup_rules()
revalidate_quote(quote_id)
accept_quote(quote_id, accepted_by, source)
reject_quote(quote_id, reason)
convert_quote_to_agenda(quote_id)
create_quote_version(quote_id, reason)
```

### Agenda y llamado

```text
create_agenda_from_quote(quote_id)
schedule_agenda(agenda_id, date, confirmed_by)
create_call_from_agenda(agenda_id)
generate_equipment_slots(call_id)
capture_equipment_data(call_id, equipment_payload)
request_added_equipment(call_id, payload)
approve_added_equipment(request_id, quote_version_id)
sign_equipment_conformity(call_id, signature_payload)
close_call(call_id)
convert_call_to_service_order(call_id)
```

### Orden y tecnico

```text
open_field_sheet(order_equipment_id)
save_field_sheet(order_equipment_id, payload)
attach_equipment_photos(order_equipment_id, files)
select_calibration_standard(order_equipment_id, standard_id)
mark_equipment_not_done(order_equipment_id, reason)
save_calibration_results(order_equipment_id, results)
generate_certificate_folio(order_equipment_id, service_type)
print_calibration_label(order_equipment_id)
submit_label_validation(order_equipment_id, photo_id)
approve_label(order_equipment_id, validator_id)
reject_label(order_equipment_id, validator_id, reason)
close_technical_service(order_id)
```

### Captura y certificados

```text
validate_capture_data(order_equipment_id)
return_to_technician(order_equipment_id, comments)
select_master_template(order_equipment_id, template_id)
calculate_certificate_results(order_equipment_id, template_id)
validate_uncertainty(certificate_id)
create_certificate(order_equipment_id)
generate_certificate_auth_assets(certificate_id)
submit_certificate_to_quality(certificate_id)
approve_certificate(certificate_id, quality_user_id)
reject_certificate(certificate_id, quality_user_id, reason)
release_certificate(certificate_id)
suspend_certificate(certificate_id, reason)
cancel_certificate(certificate_id, reason)
reissue_certificate(certificate_id, reason)
```

### Finanzas y documentacion

```text
upload_payment_receipt(order_id, file_id, uploaded_by)
validate_payment(payment_id, finance_user_id)
reject_payment(payment_id, reason)
create_prefactura(order_id)
approve_prefactura(order_id, approved_by, source)
mark_ready_to_stamp(order_id)
stamp_invoice(order_id)
release_order_documents(order_id)
send_certificates_by_email(order_id, recipients)
close_sales_order(order_id)
send_satisfaction_survey(order_id)
calculate_service_profitability(order_id)
```

## 14. Reglas de auditoria

Toda accion critica debe registrar:
- Usuario.
- Fecha y hora.
- Modulo.
- Entidad.
- ID de entidad.
- Accion.
- Estado anterior.
- Estado nuevo.
- Valor anterior.
- Valor nuevo.
- Comentario o motivo.

Acciones criticas:
- Enviar cotizacion.
- Revigentear cotizacion.
- Aceptar cotizacion.
- Confirmar verbalmente.
- Agregar equipos.
- Cerrar llamado.
- Marcar equipo no realizado.
- Seleccionar patron.
- Guardar resultados.
- Validar etiqueta.
- Cerrar servicio tecnico.
- Generar certificado.
- Autorizar certificado.
- Validar pago.
- Timbrar factura.
- Liberar certificados.
- Cancelar o suspender documentos.

## 15. Reglas de seguridad y control

- Un usuario no debe validar su propia etiqueta si existe otro validador disponible.
- Un tecnico no debe autorizar su propio certificado.
- Finanzas es la unica area que valida pagos.
- Calidad es la unica area que autoriza certificados.
- Comercial puede confirmar autorizacion verbal, pero debe dejar comentario obligatorio.
- Documentos fiscales cargados por cliente pueden eliminarse despues de extraer datos, salvo politica legal distinta.
- Certificados emitidos no se editan; se reemiten.
- Folios no se reutilizan.

## 16. Entidades de datos recomendadas

- users
- roles
- permissions
- audit_logs
- leads
- clients
- client_contacts
- client_tax_profiles
- quotes
- quote_versions
- quote_items
- quote_followups
- agendas
- service_calls
- service_call_equipment_slots
- added_equipment_requests
- service_orders
- service_order_equipment
- field_sheets
- equipment_photos
- calibration_standards
- calibration_results
- service_expenses
- labels
- label_validations
- master_templates
- certificates
- certificate_versions
- certificate_auth_assets
- quality_reviews
- documents
- payment_receipts
- payments
- prefacturas
- invoices
- surveys
- survey_answers
- notifications
- system_settings

## 17. Pantallas principales

- Dashboard por rol.
- Bandeja de leads.
- Chat/expediente comercial.
- Cliente 360.
- Editor de cotizacion.
- Seguimiento de cotizaciones.
- Agenda de servicios.
- Llamado y alta de equipos.
- Firma de conformidad.
- Orden de servicio.
- Lista de equipos de la orden.
- Hoja de campo.
- Validacion de etiqueta.
- Panel de captura.
- Editor/generador de certificados.
- Revision de calidad.
- Expediente documental.
- Validacion de pagos.
- Prefactura y timbrado.
- Dashboard del cliente.
- Encuestas.
- Reportes gerenciales.

## 18. Prioridad de desarrollo

### Fase 1 - Comercial y agenda

- Leads.
- Clientes.
- Cotizaciones.
- Automatizaciones de seguimiento.
- Aceptacion de cotizacion.
- Agenda.

### Fase 2 - Operacion tecnica

- Llamados.
- Alta de equipos.
- Agregados.
- Firma del cliente.
- Ordenes de servicio.
- Hoja de campo.
- Evidencias.
- Patrones.

### Fase 3 - Certificados y calidad

- Folios de certificado.
- Etiquetas.
- Validacion de etiqueta.
- Plantillas master.
- Captura.
- Certificados.
- Revision de calidad.
- Documentacion.

### Fase 4 - Finanzas y liberacion

- Pagos.
- Prefactura.
- Timbrado.
- Liberacion documental.
- Cierre comercial.

### Fase 5 - Encuestas y reportes

- Encuesta de satisfaccion.
- Auditoria.
- Reporte de tiempos.
- Rentabilidad.
- Egresos por servicio.
- Indicadores por area.

## 19. Pendientes para cerrar especificacion final

- Confirmar catalogo real de servicios.
- Confirmar familias de equipos y datos obligatorios por familia.
- Definir formato real de hoja de campo.
- Definir formato de etiqueta.
- Definir reglas exactas del codigo visual de esquinas.
- Definir plantillas master por magnitud.
- Confirmar si CFDI se timbrara dentro del sistema o mediante integracion externa.
- Confirmar proveedor de WhatsApp.
- Confirmar si el dashboard de cliente requiere login propio o acceso por enlace seguro.
- Confirmar usuarios y roles reales.
- Confirmar reglas de vigencia de certificados.
- Confirmar politica de retencion de constancias fiscales.
- Confirmar si habra operacion offline para tecnicos en campo.
