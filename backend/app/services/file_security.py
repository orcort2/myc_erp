"""Políticas institucionales para validar archivos antes de persistirlos.

Este módulo no decide permisos ni ownership. Su única responsabilidad es
rechazar contenido inseguro o incompatible con el perfil funcional solicitado.
"""

from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
from io import BytesIO
from pathlib import Path, PurePosixPath
import re
from typing import BinaryIO
from xml.etree import ElementTree
from zipfile import BadZipFile, ZipFile

from fastapi import HTTPException, UploadFile, status
from PIL import Image, UnidentifiedImageError
from pypdf import PdfReader

from app.core.config import settings


MIB = 1024 * 1024
GENERIC_MIME_TYPES = {"", "application/octet-stream"}
MAX_FILENAME_LENGTH = 180


@dataclass(frozen=True)
class UploadPolicy:
    name: str
    extensions: frozenset[str]
    mime_by_extension: dict[str, frozenset[str]]
    max_bytes: int
    archive_max_members: int = 0
    archive_max_uncompressed_bytes: int = 0
    archive_max_member_bytes: int = 0
    archive_max_ratio: float = 0
    archive_max_depth: int = 0


@dataclass(frozen=True)
class ValidatedUpload:
    original_filename: str
    extension: str
    declared_mime: str
    content: bytes
    checksum_sha256: str
    policy_name: str


OFFICE_MIME = {
    ".docx": frozenset({"application/vnd.openxmlformats-officedocument.wordprocessingml.document"}),
    ".xlsx": frozenset({"application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"}),
    ".xlsm": frozenset({"application/vnd.ms-excel.sheet.macroenabled.12"}),
    ".pptx": frozenset({"application/vnd.openxmlformats-officedocument.presentationml.presentation"}),
}

POLICIES: dict[str, UploadPolicy] = {
    "activity_attachment": UploadPolicy(
        name="activity_attachment",
        extensions=frozenset({".pdf", ".jpg", ".jpeg", ".png", ".webp", ".txt", ".md", ".csv", ".zip", ".docx", ".xlsx", ".pptx"}),
        mime_by_extension={
            ".pdf": frozenset({"application/pdf"}),
            ".jpg": frozenset({"image/jpeg"}), ".jpeg": frozenset({"image/jpeg"}),
            ".png": frozenset({"image/png"}), ".webp": frozenset({"image/webp"}),
            ".txt": frozenset({"text/plain"}), ".md": frozenset({"text/plain", "text/markdown"}),
            ".csv": frozenset({"text/plain", "text/csv"}),
            ".zip": frozenset({"application/zip", "application/x-zip-compressed"}),
            **OFFICE_MIME,
        },
        max_bytes=settings.upload_activity_max_bytes,
        archive_max_members=settings.upload_archive_max_members,
        archive_max_uncompressed_bytes=min(60 * MIB, settings.upload_archive_max_uncompressed_bytes),
        archive_max_member_bytes=min(20 * MIB, settings.upload_archive_max_member_bytes),
        archive_max_ratio=settings.upload_archive_max_ratio,
        archive_max_depth=settings.upload_archive_max_depth,
    ),
    "capture_package": UploadPolicy(
        name="capture_package",
        extensions=frozenset({".zip", ".xlsx", ".xlsm"}),
        mime_by_extension={
            ".zip": frozenset({"application/zip", "application/x-zip-compressed"}),
            ".xlsx": OFFICE_MIME[".xlsx"], ".xlsm": OFFICE_MIME[".xlsm"],
        },
        max_bytes=settings.upload_capture_max_bytes,
        archive_max_members=min(200, settings.upload_archive_max_members),
        archive_max_uncompressed_bytes=settings.upload_archive_max_uncompressed_bytes,
        archive_max_member_bytes=settings.upload_archive_max_member_bytes,
        archive_max_ratio=min(80, settings.upload_archive_max_ratio),
        archive_max_depth=settings.upload_archive_max_depth,
    ),
    "certificate_master": UploadPolicy(
        name="certificate_master", extensions=frozenset({".xlsx"}),
        mime_by_extension={".xlsx": OFFICE_MIME[".xlsx"]}, max_bytes=settings.upload_document_max_bytes,
        archive_max_members=2000, archive_max_uncompressed_bytes=80 * MIB,
        archive_max_member_bytes=25 * MIB, archive_max_ratio=100, archive_max_depth=12,
    ),
    "certificate_pdf": UploadPolicy(
        name="certificate_pdf", extensions=frozenset({".pdf"}),
        mime_by_extension={".pdf": frozenset({"application/pdf"})}, max_bytes=settings.upload_certificate_pdf_max_bytes,
    ),
    "tax_constancy": UploadPolicy(
        name="tax_constancy", extensions=frozenset({".pdf", ".png", ".jpg", ".jpeg"}),
        mime_by_extension={".pdf": frozenset({"application/pdf"}), ".png": frozenset({"image/png"}), ".jpg": frozenset({"image/jpeg"}), ".jpeg": frozenset({"image/jpeg"})},
        max_bytes=settings.upload_tax_constancy_max_bytes,
    ),
    "client_import": UploadPolicy(
        name="client_import", extensions=frozenset({".csv", ".xlsx", ".xlsm"}),
        mime_by_extension={".csv": frozenset({"text/csv", "text/plain", "application/vnd.ms-excel"}), ".xlsx": OFFICE_MIME[".xlsx"], ".xlsm": OFFICE_MIME[".xlsm"]},
        max_bytes=settings.upload_document_max_bytes,
        archive_max_members=2000, archive_max_uncompressed_bytes=80 * MIB,
        archive_max_member_bytes=25 * MIB, archive_max_ratio=100, archive_max_depth=12,
    ),
}


def _reject(detail: str, code: int = status.HTTP_422_UNPROCESSABLE_CONTENT) -> None:
    raise HTTPException(status_code=code, detail=detail)


def validate_filename(value: str) -> str:
    name = value.strip()
    if not name or len(name) > MAX_FILENAME_LENGTH or "\x00" in name:
        _reject("El nombre del archivo es inválido")
    if Path(name).name != name or "/" in name or "\\" in name or name in {".", ".."}:
        _reject("El nombre del archivo no puede contener rutas")
    if any(ord(character) < 32 for character in name):
        _reject("El nombre del archivo contiene caracteres de control")
    return name


def read_limited(stream: BinaryIO, max_bytes: int) -> bytes:
    content = stream.read(max_bytes + 1)
    if len(content) > max_bytes:
        _reject(f"El archivo supera el límite de {max_bytes // MIB} MB", status.HTTP_413_CONTENT_TOO_LARGE)
    if not content:
        _reject("El archivo está vacío")
    return content


def validate_upload(upload: UploadFile, policy_name: str) -> ValidatedUpload:
    policy = POLICIES[policy_name]
    original = validate_filename(upload.filename or "archivo")
    extension = Path(original).suffix.lower()
    if extension not in policy.extensions:
        _reject("La extensión no está permitida para esta operación", status.HTTP_415_UNSUPPORTED_MEDIA_TYPE)
    declared = (upload.content_type or "application/octet-stream").split(";", 1)[0].strip().lower()
    expected_mimes = policy.mime_by_extension.get(extension, frozenset())
    if declared not in GENERIC_MIME_TYPES and declared not in expected_mimes:
        _reject("El tipo declarado no coincide con la extensión", status.HTTP_415_UNSUPPORTED_MEDIA_TYPE)
    content = read_limited(upload.file, policy.max_bytes)
    validate_content(content, extension, policy)
    upload.file.seek(0)
    return ValidatedUpload(original, extension, declared, content, sha256(content).hexdigest(), policy.name)


def validate_content(content: bytes, extension: str, policy: UploadPolicy) -> None:
    extension = extension.lower()
    if extension == ".pdf":
        if not content.startswith(b"%PDF-") or b"%%EOF" not in content[-2048:]:
            _reject("El PDF está truncado o su firma es inválida", status.HTTP_415_UNSUPPORTED_MEDIA_TYPE)
        try:
            reader = PdfReader(BytesIO(content), strict=True)
            if reader.is_encrypted:
                _reject("No se aceptan archivos PDF cifrados")
            if len(reader.pages) < 1:
                _reject("El PDF no contiene páginas")
        except HTTPException:
            raise
        except Exception as exc:
            raise HTTPException(status_code=415, detail="La estructura interna del PDF no es válida") from exc
    elif extension in {".jpg", ".jpeg"}:
        if not content.startswith(b"\xff\xd8\xff") or not content.rstrip().endswith(b"\xff\xd9"):
            _reject("La imagen JPEG está truncada o no es válida", status.HTTP_415_UNSUPPORTED_MEDIA_TYPE)
    elif extension == ".png":
        if not content.startswith(b"\x89PNG\r\n\x1a\n") or b"IEND" not in content[-32:]:
            _reject("La imagen PNG está truncada o no es válida", status.HTTP_415_UNSUPPORTED_MEDIA_TYPE)
    elif extension == ".webp":
        if not (content.startswith(b"RIFF") and len(content) >= 12 and content[8:12] == b"WEBP"):
            _reject("La imagen WEBP no es válida", status.HTTP_415_UNSUPPORTED_MEDIA_TYPE)
    if extension in {".jpg", ".jpeg", ".png", ".webp"}:
        try:
            with Image.open(BytesIO(content)) as image:
                width, height = image.size
                if width <= 0 or height <= 0 or width * height > settings.upload_image_max_pixels:
                    _reject("Las dimensiones de la imagen superan el límite permitido")
                image.verify()
        except HTTPException:
            raise
        except (UnidentifiedImageError, OSError, ValueError) as exc:
            raise HTTPException(status_code=415, detail="La imagen está dañada o su estructura no es válida") from exc
    elif extension in {".txt", ".md", ".csv"}:
        try:
            content.decode("utf-8-sig")
        except UnicodeDecodeError as exc:
            _reject("El archivo de texto no usa una codificación UTF-8 válida", status.HTTP_415_UNSUPPORTED_MEDIA_TYPE)
    elif extension in {".zip", ".docx", ".xlsx", ".xlsm", ".pptx"}:
        validate_zip(content, policy, office_extension=None if extension == ".zip" else extension)


def _safe_archive_name(name: str, max_depth: int) -> bool:
    normalized = name.replace("\\", "/")
    path = PurePosixPath(normalized)
    return not (
        not normalized or normalized.startswith("/") or re.match(r"^[A-Za-z]:", normalized)
        or ".." in path.parts or len(path.parts) > max_depth or len(normalized) > 300
    )


def validate_zip(content: bytes, policy: UploadPolicy, *, office_extension: str | None = None) -> list:
    try:
        with ZipFile(BytesIO(content)) as archive:
            infos = archive.infolist()
            if not infos or len(infos) > policy.archive_max_members:
                _reject("El archivo comprimido está vacío o contiene demasiados elementos")
            names = set()
            total = 0
            for info in infos:
                if not _safe_archive_name(info.filename, policy.archive_max_depth):
                    _reject("El archivo comprimido contiene una ruta insegura")
                normalized = info.filename.replace("\\", "/").casefold()
                if normalized in names:
                    _reject("El archivo comprimido contiene nombres duplicados")
                names.add(normalized)
                if info.flag_bits & 0x1:
                    _reject("No se aceptan archivos comprimidos cifrados")
                unix_mode = (info.external_attr >> 16) & 0o170000
                if unix_mode in {0o120000, 0o060000, 0o020000}:
                    _reject("El archivo comprimido contiene enlaces o dispositivos no permitidos")
                if info.is_dir():
                    continue
                if info.file_size > policy.archive_max_member_bytes:
                    _reject("Un elemento comprimido supera el límite permitido")
                total += info.file_size
                if total > policy.archive_max_uncompressed_bytes:
                    _reject("El tamaño descomprimido supera el límite permitido")
                ratio = info.file_size / max(info.compress_size, 1)
                if ratio > policy.archive_max_ratio:
                    _reject("El archivo comprimido presenta una relación de expansión insegura")
            if office_extension:
                required_folder = {".docx": "word/", ".xlsx": "xl/", ".xlsm": "xl/", ".pptx": "ppt/"}[office_extension]
                actual_names = {info.filename for info in infos}
                if "[Content_Types].xml" not in actual_names or not any(name.startswith(required_folder) for name in actual_names):
                    _reject("La estructura del documento Office está incompleta", status.HTTP_415_UNSUPPORTED_MEDIA_TYPE)
            return infos
    except BadZipFile as exc:
        raise HTTPException(status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE, detail="El archivo comprimido no es válido") from exc


def validate_xml(content: bytes, *, max_bytes: int = 10 * MIB) -> None:
    if not content or len(content) > max_bytes:
        _reject("El XML está vacío o supera el límite permitido")
    upper = content[:4096].upper()
    if b"<!DOCTYPE" in upper or b"<!ENTITY" in upper:
        _reject("El XML contiene declaraciones externas no permitidas")
    try:
        ElementTree.fromstring(content)
    except ElementTree.ParseError as exc:
        raise HTTPException(status_code=422, detail="El XML no está bien formado") from exc
