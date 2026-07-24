"""Identificadores y versiones estables para definiciones registrables."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import ClassVar, Self

from app.resolution_engine.domain.exceptions import InvalidResolutionValueError

_DOTTED_KEY_PATTERN = re.compile(
    r"^[a-z][a-z0-9_]*(?:\.[a-z][a-z0-9_]*)+$"
)
_VERSION_PATTERN = re.compile(
    r"^(?P<major>0|[1-9][0-9]*)\."
    r"(?P<minor>0|[1-9][0-9]*)"
    r"(?:\.(?P<patch>0|[1-9][0-9]*))?$"
)


@dataclass(frozen=True, slots=True)
class ResolutionType:
    """Clave namespaced, estable e independiente del nombre visible."""

    value: str
    max_length: ClassVar[int] = 160

    def __post_init__(self) -> None:
        if (
            not isinstance(self.value, str)
            or len(self.value) > self.max_length
            or _DOTTED_KEY_PATTERN.fullmatch(self.value) is None
        ):
            raise InvalidResolutionValueError(
                "resolution_type must be a dotted lowercase identifier"
            )

    @classmethod
    def parse(cls, value: Self | str) -> Self:
        if isinstance(value, cls):
            return value
        return cls(value)

    def __str__(self) -> str:
        return self.value


@dataclass(frozen=True, slots=True)
class ComponentKey:
    """Clave estable de un componente dentro del registro."""

    value: str
    max_length: ClassVar[int] = 200

    def __post_init__(self) -> None:
        if (
            not isinstance(self.value, str)
            or len(self.value) > self.max_length
            or _DOTTED_KEY_PATTERN.fullmatch(self.value) is None
        ):
            raise InvalidResolutionValueError(
                "component_key must be a dotted lowercase identifier"
            )

    @classmethod
    def parse(cls, value: Self | str) -> Self:
        if isinstance(value, cls):
            return value
        return cls(value)

    def __str__(self) -> str:
        return self.value


@dataclass(frozen=True, slots=True)
class DefinitionVersion:
    """Versión numérica explícita de una definición o componente."""

    value: str
    _parts: tuple[int, int, int] = field(init=False, repr=False, compare=False)

    def __post_init__(self) -> None:
        match = (
            _VERSION_PATTERN.fullmatch(self.value)
            if isinstance(self.value, str)
            else None
        )
        if match is None:
            raise InvalidResolutionValueError(
                "definition version must use major.minor or major.minor.patch"
            )
        object.__setattr__(
            self,
            "_parts",
            (
                int(match.group("major")),
                int(match.group("minor")),
                int(match.group("patch") or 0),
            ),
        )

    @classmethod
    def parse(cls, value: Self | str) -> Self:
        if isinstance(value, cls):
            return value
        return cls(value)

    @property
    def sort_key(self) -> tuple[int, int, int]:
        return self._parts

    def __str__(self) -> str:
        return self.value
