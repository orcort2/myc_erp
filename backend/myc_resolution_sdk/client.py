"""Cliente HTTP; no importa servicios, ORM ni infraestructura del ERP."""

from __future__ import annotations

from typing import Any
from uuid import uuid4

import httpx

from myc_resolution_contracts.v1 import (
    ApiCapabilities,
    CreateResolutionRequest,
    ResolutionCollection,
    ResolutionResource,
)
from myc_resolution_sdk.errors import ResolutionApiError


class ResolutionEngineClient:
    def __init__(
        self,
        *,
        base_url: str,
        token: str,
        organization_id: str,
        timeout: float = 30,
        transport: httpx.BaseTransport | None = None,
    ) -> None:
        self._client = httpx.Client(
            base_url=base_url.rstrip("/"),
            timeout=timeout,
            transport=transport,
            headers={
                "Authorization": f"Bearer {token}",
                "X-MYC-Organization-ID": organization_id,
            },
        )

    def __enter__(self) -> "ResolutionEngineClient":
        return self

    def __exit__(self, *_args: object) -> None:
        self.close()

    def close(self) -> None:
        self._client.close()

    def capabilities(self) -> ApiCapabilities:
        return ApiCapabilities.model_validate(
            self._request(
                "GET",
                "/api/public/resolution-engine/v1/capabilities",
                headers={"X-Correlation-ID": str(uuid4())},
            )
        )

    def create_resolution(
        self,
        request: CreateResolutionRequest,
        *,
        idempotency_key: str,
        correlation_id: str | None = None,
    ) -> ResolutionResource:
        return ResolutionResource.model_validate(
            self._request(
                "POST",
                "/api/public/resolution-engine/v1/resolutions",
                json=request.model_dump(mode="json"),
                headers={
                    "Idempotency-Key": idempotency_key,
                    "X-Correlation-ID": correlation_id or str(uuid4()),
                },
            )
        )

    def get_resolution(
        self,
        resolution_id: str,
        *,
        correlation_id: str | None = None,
    ) -> ResolutionResource:
        return ResolutionResource.model_validate(
            self._request(
                "GET",
                f"/api/public/resolution-engine/v1/resolutions/{resolution_id}",
                headers={"X-Correlation-ID": correlation_id or str(uuid4())},
            )
        )

    def list_resolutions(
        self,
        *,
        status: str | None = None,
        resolution_type: str | None = None,
        subject_type: str | None = None,
        subject_id: str | None = None,
        cursor: str | None = None,
        limit: int = 50,
        correlation_id: str | None = None,
    ) -> ResolutionCollection:
        params = {
            key: value
            for key, value in {
                "status": status,
                "resolution_type": resolution_type,
                "subject_type": subject_type,
                "subject_id": subject_id,
                "cursor": cursor,
                "limit": limit,
            }.items()
            if value is not None
        }
        return ResolutionCollection.model_validate(
            self._request(
                "GET",
                "/api/public/resolution-engine/v1/resolutions",
                params=params,
                headers={"X-Correlation-ID": correlation_id or str(uuid4())},
            )
        )

    def _request(self, method: str, path: str, **kwargs: Any) -> Any:
        response = self._client.request(method, path, **kwargs)
        if response.is_error:
            try:
                payload = response.json()
            except ValueError:
                payload = {}
            raise ResolutionApiError(
                status_code=response.status_code,
                code=payload.get("code", "http_error"),
                message=payload.get("message", response.text),
                correlation_id=payload.get("correlation_id"),
            )
        return response.json()
