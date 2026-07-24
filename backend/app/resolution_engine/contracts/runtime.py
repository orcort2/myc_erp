"""Puertos de runtime para tiempo e identificadores opacos."""

from __future__ import annotations

from datetime import datetime
from typing import Protocol


class Clock(Protocol):
    """Fuente inyectable de tiempo UTC."""

    def now(self) -> datetime:
        """Devuelve un ``datetime`` consciente de zona horaria."""


class IdentifierFactory(Protocol):
    """Genera IDs técnicos; nunca folios o números institucionales."""

    def new_id(self) -> str:
        """Devuelve un identificador opaco y globalmente único."""
