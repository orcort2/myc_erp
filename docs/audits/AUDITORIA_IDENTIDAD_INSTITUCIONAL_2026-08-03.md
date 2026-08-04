# Mapa de fuentes de identidad institucional

## Dictamen

No existe una fuente única aplicada a todos los documentos. Hay al menos cuatro fuentes: `InstitutionalConfiguration`, `DocumentTemplate` de cotización, `InvoiceSettings`/snapshot fiscal y constantes/assets frontend/backend. Sólo Hojas de Campo aplican de forma clara el patrón configuración central + snapshot inmutable.

| Consumidor/documento | Fuente real | Fallback/hardcode | Snapshot | Cambio posterior | Riesgo |
| --- | --- | --- | --- | --- | --- |
| Hojas de Campo backend PDF | `field_sheet.institutional_snapshot_json`; si falta, `InstitutionalConfiguration` | defaults en `institutional_configurations.py` | Sí | Históricos con snapshot no cambian | Bajo/medio; contrato mejor cerrado |
| Hojas de Campo React | snapshot/contexto; asset `myc-logo.png` si ruta no resoluble | asset importado y objeto default | Parcial | Depende del payload | Divergencia renderer React/Jinja |
| Cotización PDF | `DocumentTemplate` de quotation | `quotation_pdfs.py::LOGO_PATH`; defaults de template | No snapshot institucional único; quotation snapshot conserva negocio | Cambiar template puede alterar regeneración | Alto documental |
| Editor/preview Cotización | estado `templateForm` | RFC `MYC000000XXX`, nombre/email/web en `QuotationsPage.jsx` | No | Preview y PDF pueden divergir | Alto |
| Orden de Trabajo PDF | datos de ETS/cliente + template HTML | `work_order_pdfs.py::LOGO_PATH` y textos fijos en HTML | Contexto operativo, no identidad integral | Regeneración usa código/asset actual | Alto histórico |
| Factura PDF MYC | `InstitutionalConfiguration`, `DocumentTemplate`, `InvoiceSettings`, emitter snapshot | búsqueda de 4 logos; nombre MYC literal | Snapshot fiscal del emisor/receptor parcial | Puede mezclar configuración vigente y snapshot | Alto fiscal/documental |
| XML/PDF PAC | `Invoice.fiscal_snapshot` + Facturama | InvoiceSettings/defaults | Sí, fiscal | Debe permanecer inmutable tras emisión | Correcto conceptualmente; producción no cerrada |
| Recibo de pago PDF | Invoice/Payment + template | estilos/textos del template | No identidad formal explícita | Regeneración puede variar | Medio |
| Certificado autenticado | Master XLSX aprobado + código/autenticación | logo/identidad dentro del Master y generación | Master/version/hash congelados | Histórico preservado por PDF/version | Medio; fuente no centralizada pero formal |
| Captura ZIP/XLSX | versión de Master controlado y snapshots de equipo | nombres generados por folio | Sí | No debe cambiar | Correcto |
| Login/BrandLockup/Dashboard | assets React + literales `MYC SYSTEM` | `frontend/src/assets/myc-logo.png` | No | Cambia con deploy | Bajo histórico, alto de consistencia |
| Correos | No se localizó mailer institucional activo dentro del repo auditado | NO VERIFICADO | No | N/A | Integración ausente/no confirmada |
| Settings Empresa | Componentes `CompanyIdentity/Brand/Documents/Locations/ErpIdentity` | Todos son placeholder visual | No | No persiste | Alto: UI promete configuración inexistente |
| Panel Plantillas Hojas | `/institutional-configuration` | defaults frontend y backend | Al crear hoja | Cambia fuente central | Es la única UI real de configuración, ubicada semánticamente mal |

## Campos y fuentes

| Campo | Fuente(s) encontradas | Divergencia |
| --- | --- | --- |
| Razón social | InstitutionalConfiguration, DocumentTemplate, InvoiceSettings/emitter, literales frontend | Sí |
| Nombre comercial | Template/Invoice settings/frontend | No existe campo central equivalente claro |
| RFC | DocumentTemplate, InvoiceSettings/emitter, `MYC000000XXX` preview | Crítica para emisión |
| Régimen fiscal | InvoiceSettings/snapshot fiscal | No está en InstitutionalConfiguration |
| Domicilio | InstitutionalConfiguration, DocumentTemplate, InvoiceSettings | Sí |
| Teléfono/correo/web | InstitutionalConfiguration (sin web), DocumentTemplate, frontend | Sí |
| Logotipo | `logo_path`, asset src, asset legacy, búsqueda múltiple invoice, Master XLSX | Sí |
| Código/revisión | InstitutionalConfiguration para hojas, DocumentTemplate/Master por familia | Contratos distintos no coordinados |
| Colores/leyendas | CSS/templates/masters/literales | No centralizados |

## Comportamiento histórico

- Hojas y equipos congelan configuración/plantilla: comportamiento correcto.
- Invoice congela datos fiscales, pero el PDF institucional resuelve también valores actuales/template; debe verificarse que un re-render de emitida sea idéntico.
- Cotizaciones y OT pueden regenerarse con asset/template vigente; no se demostró inmutabilidad de identidad formal.
- Certificados preservan PDF/version y Master, lo que reduce el riesgo de regeneración, aunque la identidad reside en el documento controlado y no en configuración central.

## Arquitectura futura recomendada — no implementada

```text
InstitutionalIdentity (vigente y versionada)
  ├─ razón social/RFC/régimen/domicilio/contacto/web
  ├─ branding y assets con hash/version
  └─ políticas por familia documental
       └─ DocumentIdentitySnapshot inmutable
            ├─ identity_version + datos renderizados
            ├─ logo_asset_id/hash
            ├─ template/version/hash
            └─ timezone/locale/código/revisión/leyendas
```

Cada documento formal debe generarse exclusivamente desde su snapshot. La configuración vigente sólo sirve al crear una nueva revisión/documento. No se recomienda reusar una sola tabla JSON sin versionado ni mezclar el snapshot fiscal de Invoice con la presentación institucional.
