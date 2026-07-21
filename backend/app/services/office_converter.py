from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import platform
import shutil
import subprocess

from app.core.config import settings


@dataclass(frozen=True)
class ResolvedOfficeConverter:
    executable: str
    source: str


@dataclass(frozen=True)
class OfficeConverterDiagnostic:
    available: bool
    executable: str | None
    version: str | None
    source: str | None
    configured_value: str | None
    error: str | None


COMMON_PATHS: dict[str, tuple[str, ...]] = {
    "Darwin": (
        "/Applications/LibreOffice.app/Contents/MacOS/soffice",
        "/Applications/LibreOfficeDev.app/Contents/MacOS/soffice",
    ),
    "Windows": (
        r"C:\Program Files\LibreOffice\program\soffice.exe",
        r"C:\Program Files (x86)\LibreOffice\program\soffice.exe",
    ),
    "Linux": (
        "/usr/bin/soffice",
        "/usr/bin/libreoffice",
    ),
}


def _configured_candidate(value: str) -> ResolvedOfficeConverter | None:
    candidate = value.strip().strip('"').strip("'")
    if not candidate:
        return None
    path = Path(candidate).expanduser()
    if path.is_file():
        return ResolvedOfficeConverter(executable=str(path.resolve()), source="configured_path")
    resolved = shutil.which(candidate)
    if resolved:
        return ResolvedOfficeConverter(executable=str(Path(resolved).resolve()), source="configured_command")
    return None


def resolve_office_converter(configured_value: str | None = None) -> ResolvedOfficeConverter | None:
    configured = settings.libreoffice_executable if configured_value is None else configured_value
    explicit = _configured_candidate(configured)
    if explicit:
        return explicit

    for command in ("soffice", "libreoffice"):
        resolved = shutil.which(command)
        if resolved:
            return ResolvedOfficeConverter(executable=str(Path(resolved).resolve()), source=f"path:{command}")

    for candidate in COMMON_PATHS.get(platform.system(), ()):
        path = Path(candidate)
        if path.is_file():
            return ResolvedOfficeConverter(executable=str(path.resolve()), source="system_path")
    return None


def diagnose_office_converter(configured_value: str | None = None) -> OfficeConverterDiagnostic:
    configured = settings.libreoffice_executable if configured_value is None else configured_value
    resolved = resolve_office_converter(configured)
    if resolved is None:
        configured_note = f"; configuración no resuelta: {configured}" if configured.strip() else ""
        return OfficeConverterDiagnostic(
            available=False,
            executable=None,
            version=None,
            source=None,
            configured_value=configured or None,
            error=f"No se encontró LibreOffice por configuración, PATH ni rutas comunes{configured_note}",
        )
    try:
        result = subprocess.run(
            [resolved.executable, "--version"],
            capture_output=True,
            check=False,
            text=True,
            timeout=min(settings.office_converter_timeout_seconds, 10),
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        return OfficeConverterDiagnostic(
            available=False,
            executable=resolved.executable,
            version=None,
            source=resolved.source,
            configured_value=configured or None,
            error=f"El ejecutable fue localizado pero no respondió correctamente: {type(exc).__name__}",
        )
    version = (result.stdout or result.stderr).strip().splitlines()
    version_text = version[0] if version else None
    if result.returncode != 0:
        return OfficeConverterDiagnostic(
            available=False,
            executable=resolved.executable,
            version=version_text,
            source=resolved.source,
            configured_value=configured or None,
            error=f"La consulta de versión terminó con código {result.returncode}",
        )
    return OfficeConverterDiagnostic(
        available=True,
        executable=resolved.executable,
        version=version_text,
        source=resolved.source,
        configured_value=configured or None,
        error=None,
    )
