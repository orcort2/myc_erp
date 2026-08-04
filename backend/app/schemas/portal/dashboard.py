from pydantic import BaseModel


class PortalDashboardRead(BaseModel):
    client_id: int
    client_name: str
    quotations: int
    services: int
    certificates: int
    invoices: int
