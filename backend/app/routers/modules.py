from fastapi import APIRouter

from app.schemas.module import ModuleSummary
from app.services.modules import list_modules


router = APIRouter(prefix="/modules", tags=["modules"])


@router.get("", response_model=list[ModuleSummary])
def get_modules() -> list[ModuleSummary]:
    return list_modules()

