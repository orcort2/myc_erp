"""Implementaciones de runtime sin dependencias del ERP."""

from datetime import datetime, timezone
from uuid import uuid4


class SystemClock:
    """Reloj de producción en UTC."""

    def now(self) -> datetime:
        return datetime.now(timezone.utc)


class UuidIdentifierFactory:
    """IDs técnicos UUID4; no sustituye folios de módulos propietarios."""

    def new_id(self) -> str:
        return str(uuid4())
