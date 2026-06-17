from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.routers import clients, equipment, health, modules, quotations, service_orders


app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description="API base para el sistema ERP MYC.",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health.router, prefix="/api")
app.include_router(modules.router, prefix="/api")
app.include_router(clients.router, prefix="/api")
app.include_router(quotations.router, prefix="/api")
app.include_router(service_orders.router, prefix="/api")
app.include_router(equipment.router, prefix="/api")


@app.get("/")
def root() -> dict[str, str]:
    return {
        "name": settings.app_name,
        "version": settings.app_version,
        "status": "ready",
    }
