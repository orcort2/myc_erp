from __future__ import annotations

from datetime import datetime, timezone
from hashlib import sha256
from io import BytesIO
from pathlib import Path
import logging
import shutil
import subprocess
from tempfile import NamedTemporaryFile, TemporaryDirectory
from xml.etree import ElementTree
import zipfile

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.core.config import settings
from app.models.certificate import Certificate, CertificateCaptureFile, CertificatePdfVersion
from app.models.client import Client
from app.models.equipment import Equipment
from app.models.service_order import ServiceOrder
from app.schemas.certificate import CertificateVerificationRead
from app.services.audit_logs import write_audit_log
from app.services.activity import publish_event
from app.services.office_converter import resolve_office_converter
from app.services.storage_service import atomic_write, build_storage_path, relative_storage_path, resolve_storage_path


logger = logging.getLogger(__name__)


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


def _authenticated_target(certificate: Certificate, code: str, *, final_pdf_path: Path | None = None) -> Path:
    source = final_pdf_path or Path(certificate.final_pdf_path or "")
    directory = Path(relative_storage_path(source)).parent
    filename = f"{source.stem}_autenticado_lateral_{code}.pdf"
    return build_storage_path(directory=directory, filename=filename)


def _office_converter_binary() -> str:
    resolved = resolve_office_converter()
    if resolved:
        return resolved.executable
    raise HTTPException(
        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        detail="LibreOffice no está disponible para generar el PDF. Revise el diagnóstico del sistema o configure LIBREOFFICE_EXECUTABLE.",
    )


def _copy_master_for_pdf_export(source: Path, target: Path) -> None:
    """Hide auxiliary sheets in a temporary XLSX without rewriting workbook content."""
    main_namespace = "http://schemas.openxmlformats.org/spreadsheetml/2006/main"
    with zipfile.ZipFile(source, "r") as archive:
        workbook_xml = archive.read("xl/workbook.xml")
        root = ElementTree.fromstring(workbook_xml)
        printable_sheet_indexes = {
            int(item.attrib["localSheetId"])
            for item in root.findall(f".//{{{main_namespace}}}definedName")
            if item.attrib.get("name") == "_xlnm.Print_Area" and item.attrib.get("localSheetId", "").isdigit()
        }
        sheets = root.findall(f".//{{{main_namespace}}}sheet")
        if not printable_sheet_indexes and sheets:
            printable_sheet_indexes = {0}
        for index, sheet in enumerate(sheets):
            if index not in printable_sheet_indexes:
                sheet.set("state", "hidden")
        updated_workbook_xml = ElementTree.tostring(root, encoding="utf-8", xml_declaration=True)
        with zipfile.ZipFile(target, "w") as output:
            for info in archive.infolist():
                payload = updated_workbook_xml if info.filename == "xl/workbook.xml" else archive.read(info.filename)
                output.writestr(info, payload)


def _convert_master_to_pdf(source: Path, output_directory: Path) -> Path:
    binary = _office_converter_binary()
    profile_directory = output_directory / "libreoffice-profile"
    profile_directory.mkdir(parents=True, exist_ok=True)
    local_source = output_directory / source.name
    _copy_master_for_pdf_export(source, local_source)
    command = [
        binary,
        "--headless",
        "--nologo",
        "--nodefault",
        "--nolockcheck",
        "--norestore",
        f"-env:UserInstallation={profile_directory.as_uri()}",
        "--convert-to",
        "pdf",
        "--outdir",
        str(output_directory),
        str(local_source),
    ]
    logger.info(
        "Iniciando conversión XLSX a PDF executable=%s input=%s output_directory=%s",
        binary,
        source.name,
        output_directory,
    )
    try:
        result = subprocess.run(
            command,
            capture_output=True,
            check=False,
            text=True,
            timeout=settings.office_converter_timeout_seconds,
        )
    except subprocess.TimeoutExpired as exc:
        logger.error("La conversión XLSX a PDF excedió el timeout de %ss", settings.office_converter_timeout_seconds)
        raise HTTPException(status_code=504, detail="La generación del PDF desde el Master excedió el tiempo permitido") from exc
    except OSError as exc:
        logger.exception("No se pudo ejecutar el convertidor XLSX a PDF executable=%s", binary)
        raise HTTPException(
            status_code=503,
            detail="LibreOffice fue detectado pero no pudo ejecutarse. Revise el diagnóstico del sistema.",
        ) from exc
    if result.returncode != 0:
        logger.error(
            "Falló la conversión XLSX a PDF returncode=%s stdout=%r stderr=%r",
            result.returncode,
            (result.stdout or "")[-2000:],
            (result.stderr or "")[-2000:],
        )
        raise HTTPException(
            status_code=422,
            detail="No se pudo generar el PDF desde el Master. Consulte el diagnóstico técnico del servidor.",
        )
    generated = output_directory / f"{local_source.stem}.pdf"
    if not generated.is_file() or generated.stat().st_size == 0:
        logger.error("LibreOffice terminó sin producir un PDF válido expected=%s", generated)
        raise HTTPException(status_code=422, detail="El convertidor no produjo el PDF final del Master")
    logger.info("Conversión XLSX a PDF completada output=%s bytes=%s", generated.name, generated.stat().st_size)
    return generated


def _approved_capture_master(db: Session, certificate: Certificate) -> CertificateCaptureFile:
    capture_file = db.scalar(
        select(CertificateCaptureFile)
        .where(
            CertificateCaptureFile.certificate_id == certificate.id,
            CertificateCaptureFile.identification_status == "identified",
        )
        .order_by(CertificateCaptureFile.created_at.desc(), CertificateCaptureFile.id.desc())
        .limit(1)
    )
    if capture_file is None or not capture_file.stored_path:
        raise HTTPException(status_code=409, detail="El certificado aprobado no tiene un Master XLSX identificado")
    return capture_file


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


def _authenticate_certificate_pdf(
    db: Session,
    certificate: Certificate,
    *,
    user_id: int,
    origin: str,
) -> Certificate:
    if user_id is None:
        raise ValueError("La autenticación de certificado requiere un actor")
    if certificate.status not in {"quality_approved", "approved"}:
        raise HTTPException(
            status_code=409,
            detail="Solo certificados aprobados por calidad pueden autenticarse",
        )
    capture_file = _approved_capture_master(db, certificate)
    master_source = resolve_storage_path(capture_file.stored_path)
    if master_source is None or not master_source.is_file():
        raise HTTPException(status_code=404, detail="Master XLSX aprobado no encontrado")
    if master_source.suffix.lower() not in {".xlsx", ".xlsm"}:
        raise HTTPException(status_code=422, detail="El Master aprobado no es un XLSX compatible")

    now = datetime.now(timezone.utc)
    previous_final_pdf_path = certificate.final_pdf_path
    previous_authenticated_pdf_path = certificate.authenticated_pdf_path
    code = _authentication_code(certificate, now)
    url = _verification_url(code)
    relative_master = Path(relative_storage_path(master_source))
    final_pdf_target = build_storage_path(
        directory=relative_master.parent,
        filename=f"{master_source.stem}.pdf",
    )
    authenticated_target = _authenticated_target(certificate, code, final_pdf_path=final_pdf_target)
    with TemporaryDirectory(prefix="myc-certificate-auth-") as temporary:
        temporary_directory = Path(temporary)
        generated_pdf = _convert_master_to_pdf(master_source, temporary_directory)
        document_hash = _sha256_file(generated_pdf)
        temporary_authenticated = temporary_directory / authenticated_target.name
        _stamp_pdf(
            generated_pdf,
            temporary_authenticated,
            code=code,
            folio=certificate.expected_folio or certificate.folio,
            released_at=now,
            document_hash=document_hash,
            url=url,
        )
        atomic_write(final_pdf_target, generated_pdf.read_bytes())
        atomic_write(authenticated_target, temporary_authenticated.read_bytes())

    for version in certificate.pdf_versions:
        version.is_current = False
    if previous_final_pdf_path and not certificate.pdf_versions:
        db.add(CertificatePdfVersion(
            certificate_id=certificate.id,
            version_number=1,
            file_path=previous_final_pdf_path,
            original_filename=certificate.final_pdf_original_filename,
            uploaded_at=certificate.final_pdf_uploaded_at or certificate.updated_at or now,
            uploaded_by_id=certificate.final_pdf_uploaded_by_id,
            source_status=certificate.status,
            change_reason="PDF previo conservado al migrar la autenticación a generación desde Master",
            is_current=False,
        ))
    next_version = max((item.version_number for item in certificate.pdf_versions), default=0) + 1
    if previous_final_pdf_path and not certificate.pdf_versions:
        next_version = 2
    generated_filename = f"{master_source.stem}.pdf"
    db.add(CertificatePdfVersion(
        certificate_id=certificate.id,
        version_number=next_version,
        file_path=str(final_pdf_target),
        original_filename=generated_filename,
        uploaded_at=now,
        uploaded_by_id=user_id,
        source_status=certificate.status,
        change_reason=f"Generado durante autenticación desde Master XLSX #{capture_file.id}",
        is_current=True,
    ))

    certificate.final_pdf_path = str(final_pdf_target)
    certificate.final_pdf_original_filename = generated_filename
    certificate.final_pdf_uploaded_at = now
    certificate.final_pdf_uploaded_by_id = user_id
    certificate.authentication_code = code
    certificate.authentication_hash = document_hash
    certificate.authenticated_pdf_path = str(authenticated_target)
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
        previous_values={
            "status": previous_status,
            "final_pdf_path": previous_final_pdf_path,
            "authenticated_pdf_path": previous_authenticated_pdf_path,
        },
        new_values={
            "status": certificate.status,
            "authentication_code": code,
            "authentication_hash": document_hash,
            "final_pdf_path": str(final_pdf_target),
            "authenticated_pdf_path": str(authenticated_target),
            "capture_master_file_id": capture_file.id,
            "capture_master_filename": capture_file.original_filename,
            "match_status": certificate.match_status,
            "origin": origin,
        },
        comment="PDF final generado y autenticado desde el Master XLSX aprobado",
    )
    return certificate


def authenticate_certificate(
    db: Session,
    certificate_id: int,
    *,
    user_id: int,
    origin: str,
) -> Certificate:
    """Autoridad transaccional única para autenticar un certificado."""

    if user_id is None:
        raise ValueError("La autenticación de certificado requiere un actor")
    if origin != "quality":
        raise ValueError("El origen institucional de autenticación debe ser Calidad")

    certificate = db.scalar(
        select(Certificate)
        .where(
            Certificate.id == certificate_id,
            Certificate.is_active.is_(True),
        )
        .options(selectinload(Certificate.pdf_versions))
        .with_for_update()
    )
    if certificate is None:
        raise HTTPException(status_code=404, detail="Certificado no encontrado")
    if (
        certificate.status == "authenticated"
        or certificate.authenticated_pdf_path
    ):
        raise HTTPException(status_code=409, detail="El certificado ya fue autenticado")

    previous_status = certificate.status
    authenticated = _authenticate_certificate_pdf(
        db,
        certificate,
        user_id=user_id,
        origin=origin,
    )
    publish_event(
        db,
        entity_type="certificate",
        entity_id=authenticated.id,
        event_code="certificate.authenticated",
        idempotency_key=f"certificate:{authenticated.id}:authenticated",
        body=f"Certificado {authenticated.expected_folio or authenticated.folio} autenticado por Calidad.",
        actor_id=user_id,
        metadata={
            "previous_status": previous_status,
            "status": authenticated.status,
            "origin": origin,
            "authentication_code": authenticated.authentication_code,
            "service_order_id": authenticated.service_order_id,
        },
    )
    db.commit()
    db.refresh(authenticated)
    return authenticated


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
