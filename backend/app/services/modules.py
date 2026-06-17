from app.schemas.module import ModuleSummary


def list_modules() -> list[ModuleSummary]:
    return [
        ModuleSummary(
            key="crm",
            name="CRM y Leads",
            description="Captacion, seguimiento comercial y conversion a cotizacion.",
            status="planned",
        ),
        ModuleSummary(
            key="cotizaciones",
            name="Cotizaciones",
            description="Folios MYC, versiones, seguimiento automatico y aceptacion.",
            status="planned",
        ),
        ModuleSummary(
            key="agenda",
            name="Agenda",
            description="Pre-servicios creados desde cotizaciones aceptadas.",
            status="planned",
        ),
        ModuleSummary(
            key="llamados",
            name="Llamados",
            description="Alta de equipos, agregados y firma de conformidad.",
            status="planned",
        ),
        ModuleSummary(
            key="ordenes",
            name="Ordenes de servicio",
            description="Hojas de campo, evidencias, patrones y cierre tecnico.",
            status="planned",
        ),
        ModuleSummary(
            key="certificados",
            name="Certificados",
            description="Captura, calidad, autorizacion y liberacion documental.",
            status="planned",
        ),
        ModuleSummary(
            key="finanzas",
            name="Finanzas",
            description="Pagos, prefacturas, timbrado y liberacion por cobranza.",
            status="planned",
        ),
    ]

