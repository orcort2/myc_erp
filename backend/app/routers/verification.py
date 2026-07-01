from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.schemas.certificate import CertificateVerificationRead
from app.services.certificate_authentication import get_certificate_verification


router = APIRouter(tags=["verification"])


@router.get("/verify/{authentication_code}", response_model=CertificateVerificationRead)
def verify_certificate(
    authentication_code: str,
    db: Session = Depends(get_db),
) -> CertificateVerificationRead:
    return get_certificate_verification(db, authentication_code)
