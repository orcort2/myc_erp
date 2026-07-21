> Estado: HISTÓRICO
>
> Tipo: Histórico
>
> Autoridad: Baja; mezcla reglas ratificadas y flujo antiguo
>
> Prevalece sobre: ninguno
>
> Fusionado y reemplazado por: `../../project/BUSINESS_RULES.md`; se conserva íntegro para trazabilidad

Fusionar y reemplazar.

Contiene reglas valiosas:

folios;
autorización de equipos;
certificado por equipo;
liberación con pago;
calidad antes de liberar.

Pero mezcla reglas vigentes con el flujo antiguo de Agenda/Llamado y una visión temprana de facturación.

Extraer cada regla vigente a:

docs/project/BUSINESS_RULES.md

con:

identificador;
módulo;
estado;
alcance;
evidencia;
fecha de decisión.

Después archivar el original.

# Reglas de negocio ERP MYC

## Folios

- Cotizacion: `MYC-MM-AA-XXXX`.
- Agenda: `AMYC-AA-MM-XXXX`.
- Llamado: `SMYC-AA-MM-XXXX`.
- Orden de servicio: `OSMYC-AA-MM-XXXX`.
- Certificado: `MYC{A|T}-MM-AAAA-XXXX`.
- Ningun folio se reutiliza.

## Cotizaciones

- Dia 2 sin respuesta: reenviar recordatorio.
- Dia 4 sin respuesta: enviar aviso de proximo vencimiento.
- Dia 6 sin respuesta: cancelar folio comercialmente y ofrecer revigencia.
- Cotizacion revigenteada: 15 dias de vigencia.
- Cotizacion aceptada crea agenda.

## Equipos

- El llamado crea espacios segun cantidad cotizada.
- Equipos agregados requieren autorizacion comercial.
- Equipos no realizados deben justificar motivo.
- La firma del cliente valida los equipos autorizados.

## Certificados

- El certificado se asocia a un equipo individual.
- Certificado emitido no se edita; se reemite.
- Calidad debe autorizar antes de liberar.
- Documentos se liberan al cliente solo con pago validado, salvo excepcion autorizada.

## Finanzas

- Finanzas valida pagos.
- Prefactura requiere validacion del cliente o comentario manual del usuario.
- Factura timbrada queda en expediente documental.
