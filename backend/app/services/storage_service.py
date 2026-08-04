from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from hashlib import sha256
import os
from tempfile import NamedTemporaryFile

from fastapi import HTTPException
from sqlalchemy import Text, func, select
from sqlalchemy.orm import Session
from sqlalchemy.sql.sqltypes import String

from app.core.config import settings
from app.core.db import Base
import app.models  # noqa: F401  # Ensure all ORM mappers are registered.
from app.services.audit_logs import write_audit_log


REFERENCE_COLUMN_NAMES = {
    "file_path",
    "certificate_file_path",
    "tax_constancy_path",
    "final_pdf_path",
    "authenticated_pdf_path",
}

IGNORED_STORAGE_FILES = {".DS_Store", ".gitkeep"}


@dataclass(frozen=True)
class StoredFile:
    absolute_path: Path
    relative_path: str
    original_filename: str
    checksum_sha256: str | None = None
    size_bytes: int | None = None


def storage_root() -> Path:
    root = Path(settings.storage_root)
    if not root.is_absolute():
        root = Path(__file__).resolve().parents[3] / root
    return root.resolve()


def safe_filename(name: str, *, fallback: str = "archivo") -> str:
    cleaned = "".join(char if char.isalnum() or char in ".-_" else "_" for char in name).strip("._")
    return cleaned or fallback


def resolve_storage_path(path_value: str | Path | None) -> Path | None:
    if not path_value:
        return None

    root = storage_root()
    candidate = Path(path_value)
    resolved = candidate.resolve() if candidate.is_absolute() else (root / candidate).resolve()

    try:
        resolved.relative_to(root)
    except ValueError:
        return None

    return resolved


def require_deliverable_file(path_value: str | Path | None, *, not_found_detail: str = "Archivo no disponible") -> Path:
    """Resolve only a regular, non-symlink file below the institutional root.

    Domain services must complete identity, permission and ownership checks
    before calling this final delivery boundary.
    """
    resolved = resolve_storage_path(path_value)
    if resolved is None or resolved.is_symlink() or not resolved.is_file():
        raise HTTPException(status_code=404, detail=not_found_detail)
    return resolved


def relative_storage_path(path: str | Path) -> str:
    resolved = resolve_storage_path(path)
    if resolved is None:
        raise ValueError(f"La ruta no pertenece al almacenamiento del ERP: {path}")
    return resolved.relative_to(storage_root()).as_posix()


def atomic_write(target: Path, content: bytes) -> None:
    """Write beside the target and atomically replace only after fsync."""
    resolved = resolve_storage_path(target)
    if resolved is None:
        raise HTTPException(status_code=400, detail="Ruta de almacenamiento inválida")
    resolved.parent.mkdir(parents=True, exist_ok=True)
    temporary_name: str | None = None
    try:
        with NamedTemporaryFile(mode="wb", dir=resolved.parent, prefix=".upload-", delete=False) as temporary:
            temporary_name = temporary.name
            temporary.write(content)
            temporary.flush()
            os.fsync(temporary.fileno())
        os.replace(temporary_name, resolved)
    finally:
        if temporary_name:
            Path(temporary_name).unlink(missing_ok=True)


def save_validated_content(*, directory: str | Path, filename: str, content: bytes, original_filename: str) -> StoredFile:
    target = build_storage_path(directory=directory, filename=filename)
    atomic_write(target, content)
    return StoredFile(
        absolute_path=target,
        relative_path=relative_storage_path(target),
        original_filename=original_filename,
        checksum_sha256=sha256(content).hexdigest(),
        size_bytes=len(content),
    )


def build_storage_path(*, directory: str | Path, filename: str) -> Path:
    root = storage_root()
    target_dir = (root / directory).resolve()
    try:
        target_dir.relative_to(root)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail="Directorio de almacenamiento invalido") from exc

    target_dir.mkdir(parents=True, exist_ok=True)
    target = target_dir / safe_filename(filename, fallback="archivo")
    return target


def _storage_path_variants(path_value: str | Path) -> set[str]:
    resolved = resolve_storage_path(path_value)
    if resolved is None:
        return set()

    relative = resolved.relative_to(storage_root()).as_posix()
    return {relative, str(resolved), resolved.as_posix()}


def _reference_columns():
    for mapper in Base.registry.mappers:
        model = mapper.class_
        for column in mapper.columns:
            is_text = isinstance(column.type, (String, Text))
            if not is_text:
                continue
            name = column.key
            if name in REFERENCE_COLUMN_NAMES or name.endswith("_path"):
                yield model, getattr(model, name)


def count_active_references(db: Session, path_value: str | Path | None) -> int:
    if not path_value:
        return 0

    variants = _storage_path_variants(path_value)
    if not variants:
        return 0

    total = 0
    for model, column in _reference_columns():
        query = select(func.count()).select_from(model).where(column.in_(variants))
        if hasattr(model, "is_active"):
            query = query.where(getattr(model, "is_active").is_(True))
        if hasattr(model, "deleted_at"):
            query = query.where(getattr(model, "deleted_at").is_(None))
        total += int(db.scalar(query) or 0)
    return total


def delete_if_unreferenced(
    db: Session,
    path_value: str | Path | None,
    *,
    user_id: int | None = None,
    module: str,
    entity: str,
    entity_id: int | None,
    filename: str | None = None,
    reason: str = "Archivo eliminado automaticamente por quedar sin referencias.",
) -> bool:
    resolved = resolve_storage_path(path_value)
    if resolved is None:
        return False

    db.flush()
    if count_active_references(db, resolved) > 0:
        return False

    if not resolved.exists() or not resolved.is_file():
        return False

    resolved.unlink()
    _cleanup_empty_parents(resolved.parent)
    write_audit_log(
        db,
        action="storage.file_deleted",
        entity=entity,
        entity_id=entity_id,
        user_id=user_id,
        new_values={
            "module": module,
            "filename": filename or resolved.name,
            "path": resolved.relative_to(storage_root()).as_posix(),
            "reason": reason,
        },
        comment=reason,
    )
    return True


def _cleanup_empty_parents(start: Path) -> None:
    root = storage_root()
    current = start.resolve()
    while current != root:
        try:
            current.rmdir()
        except OSError:
            break
        current = current.parent


def delete_orphaned_files(
    db: Session,
    *,
    user_id: int | None = None,
    subdirectory: str | Path | None = None,
    reason: str = "Archivo eliminado automaticamente por quedar sin referencias.",
) -> list[str]:
    root = storage_root()
    start = root if subdirectory is None else (root / subdirectory).resolve()
    try:
        start.relative_to(root)
    except ValueError as exc:
        raise ValueError("El barrido de huerfanos solo puede ejecutarse dentro de storage") from exc

    deleted: list[str] = []
    if not start.exists():
        return deleted

    for path in sorted(item for item in start.rglob("*") if item.is_file()):
        if path.name in IGNORED_STORAGE_FILES:
            continue
        if delete_if_unreferenced(
            db,
            path,
            user_id=user_id,
            module="storage",
            entity="storage_files",
            entity_id=None,
            filename=path.name,
            reason=reason,
        ):
            deleted.append(path.relative_to(root).as_posix())
    return deleted
