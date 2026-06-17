from pydantic import BaseModel


class ModuleSummary(BaseModel):
    key: str
    name: str
    description: str
    status: str

