from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.schemas.operational_engine import (
    CalculationRequest,
    CalculationResult,
    CertificatePreparationResult,
    DocumentSelectionResult,
    FolioSuggestionRequest,
    FolioSuggestionResult,
    LabelPreparationResult,
    OperationalFlowResult,
    StandardsValidationResult,
    TechnicalCaptureResult,
)
from app.services.calculation_engine import calculate_structured_results
from app.services.certificate_preparation_engine import prepare_certificate_from_field_sheet
from app.services.document_selection_engine import select_document_templates
from app.services.folio_engine import suggest_certificate_folio
from app.services.label_engine import prepare_label_payload
from app.services.operational_flow import evaluate_operational_flow
from app.services.standards_validation_engine import validate_reference_standards
from app.services.technical_capture_engine import build_technical_capture_checklist


router = APIRouter(prefix="/operational-engines", tags=["operational-engines"])


@router.get("/flow", response_model=OperationalFlowResult)
def get_operational_flow(
    service_order_id: int | None = Query(default=None),
    equipment_id: int | None = Query(default=None),
    field_sheet_id: int | None = Query(default=None),
    certificate_id: int | None = Query(default=None),
    db: Session = Depends(get_db),
) -> OperationalFlowResult:
    return evaluate_operational_flow(
        db,
        service_order_id=service_order_id,
        equipment_id=equipment_id,
        field_sheet_id=field_sheet_id,
        certificate_id=certificate_id,
    )


@router.get("/field-sheets/{field_sheet_id}/document-selection", response_model=DocumentSelectionResult)
def get_document_selection(
    field_sheet_id: int,
    db: Session = Depends(get_db),
) -> DocumentSelectionResult:
    return select_document_templates(db, field_sheet_id)


@router.post("/field-sheets/{field_sheet_id}/validate-standards", response_model=StandardsValidationResult)
def post_validate_standards(
    field_sheet_id: int,
    db: Session = Depends(get_db),
) -> StandardsValidationResult:
    return validate_reference_standards(db, field_sheet_id)


@router.post("/folios/certificates/suggest", response_model=FolioSuggestionResult)
def post_suggest_certificate_folio(
    payload: FolioSuggestionRequest,
    db: Session = Depends(get_db),
) -> FolioSuggestionResult:
    return suggest_certificate_folio(
        db,
        certificate_type=payload.certificate_type,
        issued_on=payload.issued_on,
        sequence=payload.sequence,
        manual_folio=payload.manual_folio,
        reason=payload.reason,
    )


@router.post("/field-sheets/{field_sheet_id}/prepare-certificate", response_model=CertificatePreparationResult)
def post_prepare_certificate(
    field_sheet_id: int,
    db: Session = Depends(get_db),
) -> CertificatePreparationResult:
    return prepare_certificate_from_field_sheet(db, field_sheet_id)


@router.get("/field-sheets/{field_sheet_id}/technical-capture", response_model=TechnicalCaptureResult)
def get_technical_capture(
    field_sheet_id: int,
    db: Session = Depends(get_db),
) -> TechnicalCaptureResult:
    return build_technical_capture_checklist(db, field_sheet_id)


@router.post("/calculation", response_model=CalculationResult)
def post_calculation(
    payload: CalculationRequest,
    db: Session = Depends(get_db),
) -> CalculationResult:
    return calculate_structured_results(
        db,
        profile_key=payload.profile_key,
        points=payload.points,
    )


@router.get("/certificates/{certificate_id}/label", response_model=LabelPreparationResult)
def get_label_payload(
    certificate_id: int,
    db: Session = Depends(get_db),
) -> LabelPreparationResult:
    return prepare_label_payload(db, certificate_id)
