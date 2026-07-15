"""Non-mutating Facturama connectivity check."""

from dataclasses import dataclass
from time import perf_counter

from app.core.config import Settings, get_settings
from app.services.facturama.client import FacturamaClient
from app.services.facturama.exceptions import (
    FacturamaApiError,
    FacturamaAuthenticationError,
    FacturamaConnectionError,
    FacturamaTimeoutError,
)


@dataclass(frozen=True)
class FacturamaHealthResult:
    status: str
    response_time_ms: float | None


class FacturamaHealthService:
    """Checks credentials through a read-only API resource; it never mutates Facturama."""

    def __init__(self, client: FacturamaClient | None = None, settings: Settings | None = None) -> None:
        self._settings = settings or get_settings()
        self._client = client
        self._close_client = False

    async def check(self) -> FacturamaHealthResult:
        if not self._settings.facturama_enabled:
            return FacturamaHealthResult("disabled", None)

        username = self._settings.facturama_username.get_secret_value().strip()
        password = self._settings.facturama_password.get_secret_value().strip()
        if not username or not password:
            return FacturamaHealthResult("misconfigured", None)

        started = perf_counter()
        if self._client is None:
            self._client = FacturamaClient(self._settings)
            self._close_client = True
        try:
            # Facturama documents this as a read-only list operation.
            await self._client.get("/api/Client", params={"page": 0})
            return FacturamaHealthResult(
                status="connected",
                response_time_ms=round((perf_counter() - started) * 1000, 2),
            )
        except FacturamaAuthenticationError:
            return FacturamaHealthResult("authentication_failed", round((perf_counter() - started) * 1000, 2))
        except FacturamaTimeoutError:
            return FacturamaHealthResult("timeout", round((perf_counter() - started) * 1000, 2))
        except FacturamaConnectionError:
            return FacturamaHealthResult("network_error", round((perf_counter() - started) * 1000, 2))
        except FacturamaApiError:
            return FacturamaHealthResult("api_error", round((perf_counter() - started) * 1000, 2))
        finally:
            if self._close_client and self._client is not None:
                await self._client.aclose()
