"""Public, capability-authorized quotation signing API.

All operations are feature gated. Tokens are submitted in request bodies to
avoid exposing them in URLs and access logs.
"""
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import Response
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.services.quotation_signing_authority import authorize_document_link
from app.services.quotation_signing import request_signing_code, verify_signing_code
from app.services.quotation_signing_acceptance import accept_signed_quotation, CONSENT_TEXT


router = APIRouter(prefix="/public/quotation-signing", tags=["quotation-signing-public"])


class TokenRequest(BaseModel):
    token: str = Field(min_length=16, max_length=4096)


class CodeRequest(TokenRequest):
    challenge_id: int = Field(gt=0)
    code: str = Field(pattern=r"^[0-9]{6}$")


class AcceptanceRequest(TokenRequest):
    challenge_id: int = Field(gt=0)
    signer_name: str = Field(min_length=2, max_length=180)
    consent: bool


@router.post("/document")
def document_info(payload: TokenRequest, db: Session = Depends(get_db)):
    document, _link = authorize_document_link(db, payload.token)
    return {
        "quotation_id": document.quotation_id,
        "snapshot_id": document.snapshot_id,
        "snapshot_sha256": document.snapshot_sha256,
        "pdf_sha256": document.pdf_sha256,
        "filename": document.filename,
        "consent_text": CONSENT_TEXT,
    }


@router.post("/pdf")
def document_pdf(payload: TokenRequest, db: Session = Depends(get_db)):
    document, _link = authorize_document_link(db, payload.token)
    return Response(
        content=document.pdf_bytes,
        media_type="application/pdf",
        headers={
            "Cache-Control": "no-store",
            "Content-Disposition": 'inline; filename="cotizacion-myc.pdf"',
            "X-Content-Type-Options": "nosniff",
        },
    )


@router.post("/otp/request")
def request_code(payload: TokenRequest, db: Session = Depends(get_db)):
    document, _link = authorize_document_link(db, payload.token)
    return request_signing_code(
        db, document.quotation_id, signing_token=payload.token
    )


@router.post("/otp/verify")
def verify_code(payload: CodeRequest, db: Session = Depends(get_db)):
    document, _link = authorize_document_link(db, payload.token)
    verified = verify_signing_code(
        db, document.quotation_id, payload.challenge_id, payload.code,
        signing_token=payload.token,
    )
    if not verified:
        raise HTTPException(status_code=422, detail="Código incorrecto")
    return {"verified": True}


@router.post("/accept")
def accept_quotation(payload: AcceptanceRequest, db: Session = Depends(get_db)):
    try:
        acceptance = accept_signed_quotation(
            db,
            signing_token=payload.token,
            challenge_id=payload.challenge_id,
            signer_name=payload.signer_name,
            consent=payload.consent,
        )
        db.commit()
    except Exception:
        db.rollback()
        raise
    return {
        "accepted": True,
        "quotation_id": acceptance.quotation_id,
        "snapshot_id": acceptance.snapshot_id,
        "acceptance_id": acceptance.id,
        "status": "accepted",
    }
