"""Typed errors for the Facturama integration boundary."""

from typing import Any


class FacturamaError(Exception):
    """Base class for errors returned by the Facturama integration."""


class FacturamaProviderResponseError(FacturamaError):
    """A Facturama HTTP response, retaining only sanitized diagnostic data."""

    def __init__(
        self,
        status_code: int,
        message: str = "Unexpected Facturama API response",
        *,
        response_text: str = "",
        response_headers: dict[str, str] | None = None,
        response_json: Any = None,
    ) -> None:
        super().__init__(message)
        self.status_code = status_code
        self.response_text = response_text
        self.response_headers = response_headers or {}
        self.response_json = response_json


class FacturamaAuthenticationError(FacturamaProviderResponseError):
    """Facturama rejected the configured credentials."""


class FacturamaConnectionError(FacturamaError):
    """Facturama could not be reached."""


class FacturamaTimeoutError(FacturamaConnectionError):
    """Facturama did not respond before the configured timeout."""


class FacturamaApiError(FacturamaProviderResponseError):
    """Facturama answered with an unexpected HTTP error."""
