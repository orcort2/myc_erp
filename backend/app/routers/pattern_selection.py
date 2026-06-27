from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.models.user import User
from app.schemas.pattern_selection import PatternSelectionRequest, PatternSelectionResult
from app.services.auth import require_permission
from app.services.pattern_selection_engine import (
    generate_pattern_candidates,
    suggest_patterns_for_field_sheet,
    validate_selected_patterns_for_field_sheet,
)


router = APIRouter(tags=["pattern-selection"])


@router.post("/pattern-selection/candidates", response_model=PatternSelectionResult)
def post_pattern_selection_candidates(
    payload: PatternSelectionRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("pattern_selection.execute")),
) -> PatternSelectionResult:
    return generate_pattern_candidates(db, payload, user_id=current_user.id)


@router.post("/field-sheets/{field_sheet_id}/suggest-patterns", response_model=PatternSelectionResult)
def post_suggest_field_sheet_patterns(
    field_sheet_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("pattern_selection.execute")),
) -> PatternSelectionResult:
    return suggest_patterns_for_field_sheet(db, field_sheet_id, user_id=current_user.id)


@router.post("/field-sheets/{field_sheet_id}/validate-selected-patterns", response_model=PatternSelectionResult)
def post_validate_field_sheet_patterns(
    field_sheet_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("pattern_selection.execute")),
) -> PatternSelectionResult:
    return validate_selected_patterns_for_field_sheet(db, field_sheet_id, user_id=current_user.id)
