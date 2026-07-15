"""HTTP client shared by all future Facturama operations."""

import logging
import re
from time import perf_counter
from typing import Any

import httpx

from app.core.config import Settings, get_settings
from app.services.facturama.exceptions import (
    FacturamaApiError,
    FacturamaAuthenticationError,
    FacturamaConnectionError,
    FacturamaTimeoutError,
)


logger = logging.getLogger(__name__)

_SENSITIVE_HEADER_MARKERS = ("authorization", "api-key", "apikey", "password", "secret", "token", "cookie")
_SENSITIVE_VALUE_MARKERS = ("authorization", "api_key", "apikey", "password", "secret", "token")


def _is_sensitive(name: str, markers: tuple[str, ...]) -> bool:
    normalized = name.lower().replace("-", "_")
    return any(marker.replace("-", "_") in normalized for marker in markers)


def _sanitize_headers(headers: httpx.Headers) -> dict[str, str]:
    return {
        name: "[REDACTED]" if _is_sensitive(name, _SENSITIVE_HEADER_MARKERS) else value
        for name, value in headers.items()
    }


def _sanitize_value(value: Any) -> Any:
    if isinstance(value, dict):
        return {
            key: "[REDACTED]" if _is_sensitive(str(key), _SENSITIVE_VALUE_MARKERS) else _sanitize_value(item)
            for key, item in value.items()
        }
    if isinstance(value, list):
        return [_sanitize_value(item) for item in value]
    return value


def _sanitize_plain_text(value: str) -> str:
    """Avoid persisting credentials if an upstream non-JSON error echoes them."""
    return re.sub(
        r"(?i)\b(authorization|x-api-key|api[_-]?key|password|secret|token)\b(\s*[:=]\s*)([^,;\s]+)",
        r"\1\2[REDACTED]",
        value,
    )


def response_diagnostics(response: httpx.Response) -> dict[str, Any]:
    """Return a response snapshot that can be stored without credentials."""
    try:
        parsed = _sanitize_value(response.json())
    except (ValueError, httpx.DecodingError):
        parsed = None
    text = _sanitize_plain_text(response.text)
    if parsed is not None:
        # JSON error bodies are stored in sanitized form; raw non-JSON text is retained.
        import json

        text = json.dumps(parsed, ensure_ascii=False)
    return {
        "status_code": response.status_code,
        "text": text,
        "headers": _sanitize_headers(response.headers),
        "json": parsed,
    }


class FacturamaClient:
    """Encapsulates environment selection, native Basic Auth and HTTP errors."""

    def __init__(self, settings: Settings | None = None, client: httpx.AsyncClient | None = None) -> None:
        self._settings = settings or get_settings()
        self._client = client
        self._owns_client = client is None

    @property
    def base_url(self) -> str:
        url = (
            self._settings.facturama_sandbox_url
            if self._settings.facturama_environment == "sandbox"
            else self._settings.facturama_production_url
        )
        if not url:
            raise FacturamaConnectionError("Facturama base URL is not configured")
        return url.rstrip("/")

    async def _get_client(self) -> httpx.AsyncClient:
        if self._client is None:
            # httpx generates the Authorization header; credentials are never logged or exposed.
            username = self._settings.facturama_username.get_secret_value()
            password = self._settings.facturama_password.get_secret_value()
            self._client = httpx.AsyncClient(
                base_url=self.base_url,
                auth=(username, password),
                timeout=httpx.Timeout(self._settings.facturama_timeout_seconds),
            )
        return self._client

    async def _request(self, method: str, path: str, *, params: dict[str, str | int] | None = None, json: dict | None = None) -> httpx.Response:
        """Execute an authenticated request without logging payloads or credentials."""
        client = await self._get_client()
        request_url = str(
            httpx.URL(f"{self.base_url}/{path.lstrip('/')}").copy_merge_params(params)
        )
        started = perf_counter()
        response: httpx.Response | None = None
        error_message: str | None = None
        try:
            response = await client.request(method, path, params=params, json=json)
            diagnostics = response_diagnostics(response)
            if response.status_code in (401, 403):
                error_message = "authentication failed"
                raise FacturamaAuthenticationError(
                    response.status_code,
                    error_message,
                    response_text=diagnostics["text"],
                    response_headers=diagnostics["headers"],
                    response_json=diagnostics["json"],
                )
            if response.is_error:
                error_message = "Facturama API returned an error"
                raise FacturamaApiError(
                    response.status_code,
                    error_message,
                    response_text=diagnostics["text"],
                    response_headers=diagnostics["headers"],
                    response_json=diagnostics["json"],
                )
            return response
        except httpx.TimeoutException as exc:
            error_message = "request timed out"
            raise FacturamaTimeoutError(error_message) from exc
        except httpx.RequestError as exc:
            error_message = "connection failed"
            raise FacturamaConnectionError(error_message) from exc
        finally:
            elapsed_ms = round((perf_counter() - started) * 1000, 2)
            logger.info(
                "Facturama request method=%s url=%s response_time_ms=%s status_code=%s error=%s",
                method,
                request_url,
                elapsed_ms,
                response.status_code if response is not None else None,
                error_message,
            )

    async def get(self, path: str, *, params: dict[str, str | int] | None = None) -> httpx.Response:
        return await self._request("GET", path, params=params)

    async def post(self, path: str, *, json: dict) -> httpx.Response:
        return await self._request("POST", path, json=json)

    async def aclose(self) -> None:
        if self._owns_client and self._client is not None:
            await self._client.aclose()
