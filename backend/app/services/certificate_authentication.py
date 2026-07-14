from __future__ import annotations

from datetime import datetime, timezone
from hashlib import sha256
from io import BytesIO
from pathlib import Path
from tempfile import NamedTemporaryFile

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.core.config import settings
from app.models.certificate import Certificate
from app.models.client import Client
from app.models.equipment import Equipment
from app.models.service_order import ServiceOrder
from app.schemas.certificate import CertificateVerificationRead
from app.services.audit_logs import write_audit_log
from app.services.storage_service import build_storage_path, relative_storage_path, resolve_storage_path


def _verification_url(code: str) -> str:
    return f"{settings.public_verify_base_url.rstrip('/')}/verify/{code}"


def _authentication_code(certificate: Certificate, now: datetime) -> str:
    return certificate.authentication_code or f"MYC-AUTH-{now:%Y}-{certificate.id:06d}"


def _sha256_file(path: Path) -> str:
    digest = sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _authenticated_target(certificate: Certificate, code: str) -> Path:
    source = Path(certificate.final_pdf_path or "")
    directory = Path(relative_storage_path(source)).parent
    filename = f"{source.stem}_autenticado_lateral_{code}.pdf"
    return build_storage_path(directory=directory, filename=filename)


def _auth_band_width(page_width: float) -> float:
    try:
        from reportlab.lib.units import mm
    except ImportError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Dependencias PDF no instaladas para autenticar certificados",
        ) from exc
    return min(max(page_width * 0.055, 14 * mm), 18 * mm)


def _build_auth_overlay(
    width: float,
    height: float,
    *,
    code: str,
    folio: str,
    released_at: datetime,
    document_hash: str,
    url: str,
) -> BytesIO:
    try:
        import qrcode
        from reportlab.lib import colors
        from reportlab.lib.units import mm
        from reportlab.lib.utils import ImageReader
        from reportlab.pdfgen import canvas
        from reportlab.graphics.barcode import code128
    except ImportError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Dependencias PDF no instaladas para autenticar certificados",
        ) from exc

    buffer = BytesIO()
    pdf = canvas.Canvas(buffer, pagesize=(width, height))

    primary = colors.HexColor("#0B7A75")
    dark = colors.HexColor("#062A3A")
    soft = colors.HexColor("#FCFCFC")

    backend_dir = Path(__file__).resolve().parents[2]
    project_dir = backend_dir.parent

    logo_candidates = [
        backend_dir / "app" / "static" / "logo_myc.png",
        backend_dir / "app" / "static" / "logo-myc.png",
        backend_dir / "static" / "logo_myc.png",
        backend_dir / "static" / "logo-myc.png",
        project_dir / "frontend" / "src" / "assets" / "myc-logo.png",
        project_dir / "frontend" / "assets" / "Logo sin fondo MYC.png",
    ]

    logo_path = next((path for path in logo_candidates if path.exists()), None)

    band_width = _auth_band_width(width)
    band_x = width - band_width
    band_y = 0

    pdf.setFillColor(soft)
    pdf.setStrokeColor(primary)
    pdf.setLineWidth(0.6)
    pdf.rect(band_x, band_y, band_width, height, stroke=1, fill=1)

    pdf.setFillColor(primary)
    pdf.rect(band_x, band_y, 2.1, height, stroke=0, fill=1)

    center_x = band_x + band_width / 2
    top_y = height - 10 * mm

    if logo_path:
        logo_size = min(8 * mm, band_width - 4 * mm)
        pdf.drawImage(
            ImageReader(str(logo_path)),
            center_x - logo_size / 2,
            top_y - logo_size,
            logo_size,
            logo_size,
            preserveAspectRatio=True,
            mask="auto",
        )

    qr = qrcode.make(url)
    qr_size = min(9 * mm, band_width - 4 * mm)
    qr_y = height - 26 * mm
    with NamedTemporaryFile(suffix=".png") as qr_file:
        qr.save(qr_file.name)
        pdf.drawImage(
            ImageReader(qr_file.name),
            center_x - qr_size / 2,
            qr_y,
            qr_size,
            qr_size,
            preserveAspectRatio=True,
            mask="auto",
        )

    pdf.saveState()
    pdf.translate(center_x + 1.2 * mm, height / 2 + 18 * mm)
    pdf.rotate(90)
    pdf.setFillColor(dark)
    pdf.setFont("Helvetica-Bold", 6.5)
    pdf.drawCentredString(0, 0, "CERTIFICADO AUTENTICADO")
    pdf.setFont("Helvetica-Bold", 5.2)
    pdf.drawCentredString(0, -3.8 * mm, "MYC SYSTEM")
    pdf.setFont("Helvetica", 4.7)
    pdf.drawCentredString(0, -7.2 * mm, f"{code} | Folio {folio}")
    pdf.restoreState()

    barcode = code128.Code128(code, barHeight=band_width - 5 * mm, barWidth=0.24)
    pdf.saveState()
    pdf.translate(center_x + barcode.height / 2 - 1.5 * mm, height / 2 - 44 * mm)
    pdf.rotate(90)
    barcode.drawOn(pdf, 0, 0)
    pdf.restoreState()

    pdf.saveState()
    pdf.translate(center_x + 1.0 * mm, height / 2 - 68 * mm)
    pdf.rotate(90)
    pdf.setFillColor(primary)
    pdf.setFont("Helvetica", 4.1)
    pdf.drawCentredString(0, 0, code)
    pdf.restoreState()

    pdf.save()
    buffer.seek(0)

    return buffer

def _stamp_pdf(source: Path, target: Path, *, code: str, folio: str, released_at: datetime, document_hash: str, url: str) -> None:
    try:
        from pypdf import PageObject, PdfReader, PdfWriter
    except ImportError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Dependencias PDF no instaladas para autenticar certificados",
        ) from exc

    reader = PdfReader(str(source))
    if not reader.pages:
        raise HTTPException(status_code=422, detail="El PDF no contiene paginas")

    writer = PdfWriter()

    for page in reader.pages:
        width = float(page.mediabox.width)
        height = float(page.mediabox.height)
        expanded_width = width + _auth_band_width(width)

        overlay = PdfReader(
            _build_auth_overlay(
                expanded_width,
                height,
                code=code,
                folio=folio,
                released_at=released_at,
                document_hash=document_hash,
                url=url,
            )
        )

        stamped_page = PageObject.create_blank_page(width=expanded_width, height=height)
        stamped_page.merge_page(page)
        stamped_page.merge_page(overlay.pages[0])
        writer.add_page(stamped_page)

    target.parent.mkdir(parents=True, exist_ok=True)
    with target.open("wb") as output:
        writer.write(output)


def authenticate_certificate_pdf(
    db: Session,
    certificate: Certificate,
    *,
    user_id: int | None = None,
) -> Certificate:
    if certificate.status not in {"quality_approved", "approved", "pdf_pending", "pdf_uploaded"}:
        raise HTTPException(
            status_code=409,
            detail="Solo certificados aprobados por calidad pueden autenticarse",
        )
    if not certificate.final_pdf_path:
        raise HTTPException(status_code=409, detail="No se puede autenticar sin PDF original")
    if certificate.match_status not in {"matched", "warning", "manual_accepted"}:
        raise HTTPException(status_code=409, detail="No se puede autenticar sin un match validado o aceptado por Calidad")
    source = resolve_storage_path(certificate.final_pdf_path)
    if source is None or not source.exists():
        raise HTTPException(status_code=404, detail="PDF original no encontrado")

    now = datetime.now(timezone.utc)
    code = _authentication_code(certificate, now)
    url = _verification_url(code)
    document_hash = _sha256_file(source)
    target = _authenticated_target(certificate, code)
    _stamp_pdf(
        source,
        target,
        code=code,
        folio=certificate.expected_folio or certificate.folio,
        released_at=now,
        document_hash=document_hash,
        url=url,
    )

    certificate.authentication_code = code
    certificate.authentication_hash = document_hash
    certificate.authenticated_pdf_path = str(target)
    certificate.authenticated_pdf_generated_at = now
    certificate.authenticated_by_id = user_id
    certificate.verification_url = url
    previous_status = certificate.status
    certificate.status = "authenticated"
    write_audit_log(
        db,
        action="certificate.pdf_authenticated",
        entity="certificates",
        entity_id=certificate.id,
        user_id=user_id,
        new_values={
            "previous_status": previous_status,
            "status": certificate.status,
            "authentication_code": code,
            "authentication_hash": document_hash,
            "authenticated_pdf_path": str(target),
        },
    )
    return certificate


def get_certificate_verification(db: Session, code: str) -> CertificateVerificationRead:
    certificate = db.scalar(
        select(Certificate)
        .where(Certificate.authentication_code == code)
        .options(
            selectinload(Certificate.equipment),
            selectinload(Certificate.service_order).selectinload(ServiceOrder.client).selectinload(Client.contacts),
        )
    )
    if certificate is None or not certificate.is_active:
        return CertificateVerificationRead(valid=False, authentication_code=code)

    client = certificate.service_order.client if certificate.service_order else None
    equipment = certificate.equipment
    client_name = client.commercial_name or client.legal_name if client else None
    return CertificateVerificationRead(
        valid=certificate.status == "released_to_client" and certificate.client_visible,
        authentication_code=code,
        folio=certificate.expected_folio or certificate.folio,
        client=client_name,
        equipment=equipment.name if isinstance(equipment, Equipment) else None,
        serial_number=equipment.serial_number if isinstance(equipment, Equipment) else None,
        status=certificate.status,
        authenticated_at=certificate.authenticated_pdf_generated_at,
        document_hash=certificate.authentication_hash,
    )
