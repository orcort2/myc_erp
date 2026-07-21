> Estado: HISTÓRICO
>
> Tipo: Histórico
>
> Autoridad: Baja; patrón y lista inicial no auditados contra la matriz vigente
>
> Prevalece sobre: ninguno
>
> Reemplazado por: `../../architecture/PERMISSIONS_MATRIX.md`; se conserva íntegro para trazabilidad

El documento actual es muy pequeño y no representa la matriz real.

Debe sustituirse por una matriz generada o auditada contra core/permissions.py:


# Permisos ERP MYC

## Patron

Cada modulo debe seguir este patron:

- `modulo.ver`
- `modulo.crear`
- `modulo.editar`
- `modulo.cancelar`
- `modulo.aprobar`
- `modulo.exportar`
- `modulo.administrar`

## Permisos iniciales

- `leads.ver`
- `leads.crear`
- `leads.editar`
- `leads.convertir`
- `clientes.ver`
- `clientes.crear`
- `clientes.editar`
- `cotizaciones.ver`
- `cotizaciones.crear`
- `cotizaciones.editar`
- `cotizaciones.enviar`
- `cotizaciones.confirmar_manual`
- `agenda.ver`
- `agenda.programar`
- `llamados.ver`
- `llamados.capturar`
- `llamados.solicitar_agregado`
- `ordenes.ver`
- `ordenes.ejecutar`
- `ordenes.cerrar_tecnico`
- `patrones.ver`
- `patrones.editar`
- `captura.procesar`
- `certificados.generar`
- `calidad.autorizar`
- `finanzas.validar_pago`
- `finanzas.timbrar`
- `documentacion.liberar`
- `reportes.ver`
- `reportes.exportar`
