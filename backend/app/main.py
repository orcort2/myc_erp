from contextlib import asynccontextmanager
import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.services.facturama.client import FacturamaClient
from app.services.office_converter import diagnose_office_converter
from app.routers import (
    audit_logs,
    auth,
    calibration_procedures,
    catalog_items,
    certificates,
    client_portal,
    clients,
    document_interpretations,
    document_templates,
    documents,
    equipment,
    field_sheets,
    health,
    invoices,
    integrations,
    institutional_configurations,
    metrology,
    modules,
    operational_engines,
    pattern_selection,
    quotations,
    reference_standards,
    reference_standard_certificates,
    sat_catalogs,
    service_orders,
    technical_profiles,
    uncertainty,
    users,
    verification,
)
from app.routers import field_sheet_templates


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Keep reusable external clients alive for the whole application lifetime."""
    app.state.facturama_client = FacturamaClient(settings)
    office_diagnostic = diagnose_office_converter()
    office_logger = logging.getLogger("app.startup.office_converter")
    if office_diagnostic.available:
        office_logger.info(
            "LibreOffice disponible executable=%s source=%s version=%s",
            office_diagnostic.executable,
            office_diagnostic.source,
            office_diagnostic.version,
        )
    else:
        office_logger.warning("LibreOffice no disponible: %s", office_diagnostic.error)
    yield
    await app.state.facturama_client.aclose()


app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description="API base para el sistema ERP MYC.",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "https://erp.mycmetrology.com.mx",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health.router, prefix="/api")
app.include_router(auth.router, prefix="/api")
app.include_router(audit_logs.router, prefix="/api")
app.include_router(modules.router, prefix="/api")
app.include_router(clients.router, prefix="/api")
app.include_router(catalog_items.router, prefix="/api")
app.include_router(documents.router, prefix="/api")
app.include_router(document_interpretations.router, prefix="/api")
app.include_router(document_templates.router, prefix="/api")
app.include_router(reference_standards.router, prefix="/api")
app.include_router(reference_standard_certificates.router, prefix="/api")
app.include_router(calibration_procedures.router, prefix="/api")
app.include_router(quotations.router, prefix="/api")
app.include_router(service_orders.router, prefix="/api")
app.include_router(technical_profiles.router, prefix="/api")
app.include_router(equipment.router, prefix="/api")
app.include_router(field_sheets.router, prefix="/api")
app.include_router(certificates.router, prefix="/api")
app.include_router(invoices.router, prefix="/api")
app.include_router(integrations.router, prefix="/api")
app.include_router(sat_catalogs.router, prefix="/api")
app.include_router(institutional_configurations.router, prefix="/api")
app.include_router(client_portal.router, prefix="/api")
app.include_router(metrology.router, prefix="/api")
app.include_router(operational_engines.router, prefix="/api")
app.include_router(pattern_selection.router, prefix="/api")
app.include_router(uncertainty.router, prefix="/api")
app.include_router(users.router, prefix="/api")
app.include_router(verification.router)
app.include_router(field_sheet_templates.router, prefix="/api")


@app.get("/")
def root() -> dict[str, str]:
    return {
        "name": settings.app_name,
        "version": settings.app_version,
        "status": "ready",
    }
