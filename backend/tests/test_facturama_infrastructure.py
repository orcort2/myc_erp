import asyncio
import inspect
import unittest
from unittest.mock import patch

import httpx
from fastapi.testclient import TestClient

from app.core.config import Settings
from app.main import app
from app.routers.integrations import get_facturama_status
from app.services.facturama.client import FacturamaClient
from app.services.facturama.exceptions import FacturamaApiError
from app.services.facturama.health import FacturamaHealthService


def facturama_settings(**values) -> Settings:
    configuration = {
        "facturama_enabled": True,
        "facturama_username": "user",
        "facturama_password": "password",
        "facturama_sandbox_url": "https://sandbox.example.test",
        "facturama_production_url": "https://production.example.test",
    }
    configuration.update(values)
    return Settings(_env_file=None, **configuration)


class FacturamaInfrastructureTests(unittest.TestCase):
    def test_disabled_check_does_not_create_or_use_http_client(self):
        async def run_test():
            with patch("app.services.facturama.health.FacturamaClient") as client_class:
                result = await FacturamaHealthService(
                    settings=facturama_settings(facturama_enabled=False)
                ).check()

            self.assertEqual(result.status, "disabled")
            self.assertIsNone(result.response_time_ms)
            client_class.assert_not_called()

        asyncio.run(run_test())

    def test_missing_credentials_does_not_create_or_use_http_client(self):
        async def run_test():
            with patch("app.services.facturama.health.FacturamaClient") as client_class:
                result = await FacturamaHealthService(
                    settings=facturama_settings(facturama_username="", facturama_password=" ")
                ).check()

            self.assertEqual(result.status, "misconfigured")
            self.assertIsNone(result.response_time_ms)
            client_class.assert_not_called()

        asyncio.run(run_test())

    def test_status_endpoint_reports_disabled_without_contacting_facturama(self):
        permission_dependency = inspect.signature(get_facturama_status).parameters[
            "current_user"
        ].default.dependency
        app.dependency_overrides[permission_dependency] = lambda: object()
        try:
            with patch(
                "app.routers.integrations.get_settings",
                return_value=facturama_settings(facturama_enabled=False),
            ):
                with TestClient(app) as test_client:
                    response = test_client.get("/api/integrations/facturama/status")
        finally:
            app.dependency_overrides.clear()

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["status"], "disabled")
        self.assertFalse(response.json()["connected"])

    def test_selects_sandbox_or_production_from_settings(self):
        self.assertEqual(
            FacturamaClient(facturama_settings(facturama_environment="sandbox")).base_url,
            facturama_settings(facturama_environment="sandbox").facturama_sandbox_url,
        )
        self.assertEqual(
            FacturamaClient(facturama_settings(facturama_environment="production")).base_url,
            facturama_settings(facturama_environment="production").facturama_production_url,
        )

    def test_read_only_check_uses_native_httpx_basic_auth(self):
        async def run_test():
            seen = {}

            async def handler(request: httpx.Request) -> httpx.Response:
                seen["url"] = str(request.url)
                seen["authorization"] = request.headers.get("Authorization")
                return httpx.Response(200, json=[])

            settings = facturama_settings()
            async with httpx.AsyncClient(
                base_url=settings.facturama_sandbox_url,
                auth=(
                    settings.facturama_username.get_secret_value(),
                    settings.facturama_password.get_secret_value(),
                ),
                transport=httpx.MockTransport(handler),
            ) as http_client:
                result = await FacturamaHealthService(
                    FacturamaClient(settings, client=http_client), settings
                ).check()

            self.assertEqual(result.status, "connected")
            self.assertTrue(seen["authorization"].startswith("Basic "))
            self.assertEqual(seen["url"], f"{settings.facturama_sandbox_url}/api/Client?page=0")

        asyncio.run(run_test())

    def test_unauthorized_response_is_reported_without_exception(self):
        async def run_test():
            async def handler(request: httpx.Request) -> httpx.Response:
                return httpx.Response(401)

            settings = facturama_settings()
            async with httpx.AsyncClient(
                base_url=settings.facturama_sandbox_url,
                transport=httpx.MockTransport(handler),
            ) as http_client:
                result = await FacturamaHealthService(
                    FacturamaClient(settings, client=http_client), settings
                ).check()

            self.assertEqual(result.status, "authentication_failed")

        asyncio.run(run_test())

    def test_timeout_is_reported_without_exception(self):
        async def run_test():
            async def handler(request: httpx.Request) -> httpx.Response:
                raise httpx.ReadTimeout("test timeout", request=request)

            settings = facturama_settings()
            async with httpx.AsyncClient(
                base_url=settings.facturama_sandbox_url,
                transport=httpx.MockTransport(handler),
            ) as http_client:
                result = await FacturamaHealthService(
                    FacturamaClient(settings, client=http_client), settings
                ).check()

            self.assertEqual(result.status, "timeout")

        asyncio.run(run_test())

    def test_api_error_retains_sanitized_provider_diagnostics(self):
        async def run_test():
            async def handler(request: httpx.Request) -> httpx.Response:
                return httpx.Response(
                    400,
                    headers={"X-Request-Id": "request-123", "X-Api-Key": "must-not-persist"},
                    json={"Message": "RFC del emisor inválido", "api_key": "must-not-persist"},
                )

            settings = facturama_settings()
            async with httpx.AsyncClient(
                base_url=settings.facturama_sandbox_url,
                transport=httpx.MockTransport(handler),
            ) as http_client:
                with self.assertRaises(FacturamaApiError) as captured:
                    await FacturamaClient(settings, client=http_client).post("/3/cfdis", json={"CfdiType": "I"})

            error = captured.exception
            self.assertEqual(error.status_code, 400)
            self.assertEqual(error.response_headers["x-request-id"], "request-123")
            self.assertEqual(error.response_headers["x-api-key"], "[REDACTED]")
            self.assertEqual(error.response_json["Message"], "RFC del emisor inválido")
            self.assertEqual(error.response_json["api_key"], "[REDACTED]")
            self.assertNotIn("must-not-persist", error.response_text)

        asyncio.run(run_test())

    def test_non_json_provider_error_redacts_sensitive_text(self):
        async def run_test():
            async def handler(request: httpx.Request) -> httpx.Response:
                return httpx.Response(400, text="Message: rejected; api_key=must-not-persist")

            settings = facturama_settings()
            async with httpx.AsyncClient(
                base_url=settings.facturama_sandbox_url,
                transport=httpx.MockTransport(handler),
            ) as http_client:
                with self.assertRaises(FacturamaApiError) as captured:
                    await FacturamaClient(settings, client=http_client).post("/3/cfdis", json={"CfdiType": "I"})

            self.assertEqual(captured.exception.response_text, "Message: rejected; api_key=[REDACTED]")

        asyncio.run(run_test())
