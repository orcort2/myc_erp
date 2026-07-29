from contextlib import asynccontextmanager
import logging

from fastapi import FastAPI
from fastapi import Request
from fastapi.exception_handlers import request_validation_exception_handler
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.core.config import settings
from app.services.facturama.client import FacturamaClient
from app.services.office_converter import diagnose_office_converter
from app.routers import (
    activity,
    audit_logs,
    auth,
    calibration_procedures,
    catalog_items,
    certificates,
    communications,
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
    notifications,
    operational_engines,
    pattern_selection,
    quotations,
    reference_standards,
    reference_standard_certificates,
    resolution_center,
    resolution_public_api,
    sat_catalogs,
    service_orders,
    technical_profiles,
    uncertainty,
    users,
    verification,
)
from app.routers import field_sheet_templates
from app.resolution_public_api.errors import PublicApiError


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


@app.middleware("http")
async def public_contract_headers(request: Request, call_next):
    response = await call_next(request)
    if request.url.path.startswith("/api/public/resolution-engine/v1/"):
        response.headers["X-MYC-Contract-Version"] = "1.0"
        correlation_id = request.headers.get("X-Correlation-ID")
        if correlation_id:
            response.headers["X-Correlation-ID"] = correlation_id
    return response

app.include_router(health.router, prefix="/api")
app.include_router(auth.router, prefix="/api")
app.include_router(activity.router, prefix="/api")
app.include_router(notifications.router, prefix="/api")
app.include_router(audit_logs.router, prefix="/api")
app.include_router(modules.router, prefix="/api")
app.include_router(clients.router, prefix="/api")
app.include_router(catalog_items.router, prefix="/api")
app.include_router(documents.router, prefix="/api")
app.include_router(document_interpretations.router, prefix="/api")
app.include_router(document_templates.router, prefix="/api")
app.include_router(reference_standards.router, prefix="/api")
app.include_router(reference_standard_certificates.router, prefix="/api")
app.include_router(resolution_center.router, prefix="/api")
app.include_router(resolution_public_api.router, prefix="/api")
app.include_router(calibration_procedures.router, prefix="/api")
app.include_router(quotations.router, prefix="/api")
app.include_router(service_orders.router, prefix="/api")
app.include_router(technical_profiles.router, prefix="/api")
app.include_router(equipment.router, prefix="/api")
app.include_router(field_sheets.router, prefix="/api")
app.include_router(certificates.router, prefix="/api")
app.include_router(communications.router, prefix="/api")
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


@app.exception_handler(PublicApiError)
def public_api_error_handler(
    _request: Request,
    exc: PublicApiError,
) -> JSONResponse:
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "code": exc.code,
            "category": exc.category,
            "message": exc.message,
            "correlation_id": exc.correlation_id,
            "details": exc.details,
        },
        headers={"X-Correlation-ID": exc.correlation_id},
    )


@app.exception_handler(RequestValidationError)
async def public_api_validation_error_handler(
    request: Request,
    exc: RequestValidationError,
):
    if not request.url.path.startswith("/api/public/resolution-engine/v1/"):
        return await request_validation_exception_handler(request, exc)
    correlation_id = request.headers.get("X-Correlation-ID", "missing")
    return JSONResponse(
        status_code=422,
        content={
            "code": "contract_validation_failed",
            "category": "validation",
            "message": "The public v1 request does not satisfy the contract.",
            "correlation_id": correlation_id,
            "details": {
                "violations": [
                    {
                        "location": ".".join(str(item) for item in error["loc"]),
                        "type": error["type"],
                    }
                    for error in exc.errors()
                ]
            },
        },
        headers={
            "X-Correlation-ID": correlation_id,
            "X-MYC-Contract-Version": "1.0",
        },
    )


@app.get("/")
def root() -> dict[str, str]:
    return {
        "name": settings.app_name,
        "version": settings.app_version,
        "status": "ready",
    }
