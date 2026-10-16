"""Contrato de invalidaciones operativas para PostgreSQL LISTEN/NOTIFY."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from typing import Any
from uuid import UUID, uuid4

INVALIDATION_CHANNEL = "myc_erp_invalidation_v1"
INVALIDATION_VERSION = 1

_RESOURCE_PATTERN = re.compile(r"^[a-z][a-z0-9_]{0,63}$")
_MAX_RESOURCES = 32
_MAX_PAYLOAD_BYTES = 7900


@dataclass(frozen=True, slots=True)
class ResourceInvalidation:
    event_id: str
    resources: tuple[str, ...]
    user_ids: tuple[int, ...]


def build_invalidation_payload(
    resources: list[str] | tuple[str, ...],
    *,
    user_ids: list[int] | tuple[int, ...],
) -> str:
    """Construye un aviso dirigido exclusivamente a usuarios autorizados."""

    normalized_resources = tuple(sorted(set(resources)))
    normalized_users = tuple(sorted(set(user_ids)))

    if not normalized_resources or len(normalized_resources) > _MAX_RESOURCES:
        raise ValueError("Cantidad de recursos inválida")

    if not all(
        isinstance(resource, str)
        and _RESOURCE_PATTERN.fullmatch(resource)
        for resource in normalized_resources
    ):
        raise ValueError("Nombre de recurso inválido")

    if not normalized_users or not all(
        type(user_id) is int and user_id > 0
        for user_id in normalized_users
    ):
        raise ValueError("Destinatarios inválidos")

    payload = json.dumps(
        {
            "version": INVALIDATION_VERSION,
            "event_id": str(uuid4()),
            "resources": normalized_resources,
            "user_ids": normalized_users,
        },
        separators=(",", ":"),
    )

    if len(payload.encode("utf-8")) > _MAX_PAYLOAD_BYTES:
        raise ValueError("La invalidación supera el tamaño permitido")

    return payload


def parse_invalidation_payload(raw: str) -> ResourceInvalidation:
    """Valida mensajes recibidos desde PostgreSQL sin confiar en su contenido."""

    if not isinstance(raw, str):
        raise ValueError("La invalidación debe ser texto")

    if len(raw.encode("utf-8")) > _MAX_PAYLOAD_BYTES:
        raise ValueError("La invalidación supera el tamaño permitido")

    try:
        payload: Any = json.loads(raw)
    except ValueError as exc:
        raise ValueError("JSON de invalidación inválido") from exc

    if not isinstance(payload, dict):
        raise ValueError("La invalidación debe ser un objeto")

    if set(payload) != {"version", "event_id", "resources", "user_ids"}:
        raise ValueError("Estructura de invalidación no soportada")

    if type(payload["version"]) is not int or payload["version"] != INVALIDATION_VERSION:
        raise ValueError("Versión de invalidación no soportada")

    event_id = payload["event_id"]
    resources = payload["resources"]
    user_ids = payload["user_ids"]

    try:
        if not isinstance(event_id, str):
            raise ValueError
        parsed_id = UUID(event_id)
        if str(parsed_id) != event_id:
            raise ValueError
    except ValueError as exc:
        raise ValueError("Identificador de evento inválido") from exc

    if not isinstance(resources, list) or not isinstance(user_ids, list):
        raise ValueError("Estructura de invalidación inválida")

    if len(resources) != len(set(map(str, resources))):
        raise ValueError("Recursos duplicados")

    if len(user_ids) != len(set(map(str, user_ids))):
        raise ValueError("Destinatarios duplicados")

    # Valida nombres, cantidad y destinatarios con el mismo contrato
    # utilizado por los productores de eventos.
    build_invalidation_payload(resources, user_ids=user_ids)

    return ResourceInvalidation(
        event_id=event_id,
        resources=tuple(resources),
        user_ids=tuple(user_ids),
    )
