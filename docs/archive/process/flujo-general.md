> Estado: HISTÓRICO
>
> Tipo: Histórico
>
> Autoridad: Baja; flujo objetivo inicial
>
> Prevalece sobre: ninguno
>
> Reemplazado por: `../../project/CURRENT_PROCESS_FLOW.md`

# Flujo general ERP MYC

```text
Lead -> Cotizacion -> Agenda -> Llamado -> Orden de servicio -> Hoja de campo -> Certificado -> Calidad -> Pago -> Factura -> Liberacion -> Encuesta
```

## Flujo base

1. Comercial recibe lead desde pagina, landing, chat o captura manual.
2. Comercial crea cliente o prospecto y genera cotizacion.
3. Sistema aplica seguimiento automatico de cotizacion.
4. Cliente acepta cotizacion.
5. Sistema crea agenda.
6. Agenda confirmada crea llamado.
7. Llamado da de alta equipos y recibe firma de conformidad.
8. Cierre de llamado crea orden de servicio.
9. Tecnico llena hoja de campo por equipo.
10. Sistema genera folio de certificado al completar resultados.
11. Tecnico imprime etiqueta y solicita validacion.
12. Captura genera certificado desde plantilla master.
13. Calidad autoriza certificado.
14. Finanzas valida pago y timbra.
15. Sistema libera certificados y documentos.
16. Comercial cierra servicio y sistema envia encuesta.
