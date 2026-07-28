"""Transporte HTTP v1; validación y delegación, sin lógica del Motor."""

from __future__ import annotations

from html import escape
from uuid import UUID

from fastapi import APIRouter, Depends, Header, Query
from fastapi.responses import HTMLResponse
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.resolution_public_api.application import ResolutionPublicApi
from app.resolution_public_api.errors import PublicApiError
from app.resolution_public_api.security import (
    PublicApiConsumerContext,
    authenticate_consumer,
)
from myc_resolution_contracts.v1 import (
    ApiCapabilities,
    CreateResolutionRequest,
    ResolutionCollection,
    ResolutionResource,
)

router = APIRouter(tags=["Resolution Engine Public API v1"])


def consumer_context(
    authorization: str | None = Header(default=None),
    organization_id: str | None = Header(
        default=None, alias="X-MYC-Organization-ID"
    ),
    correlation_id: str | None = Header(default=None, alias="X-Correlation-ID"),
    db: Session = Depends(get_db),
) -> PublicApiConsumerContext:
    if not correlation_id:
        raise PublicApiError(
            status_code=400,
            code="correlation_id_required",
            message="X-Correlation-ID is required.",
            correlation_id="missing",
        )
    try:
        UUID(correlation_id)
    except ValueError:
        raise PublicApiError(
            status_code=400,
            code="correlation_id_invalid",
            message="X-Correlation-ID must be a UUID.",
            correlation_id=correlation_id,
        ) from None
    return authenticate_consumer(
        db,
        authorization=authorization,
        organization_id=organization_id,
        correlation_id=correlation_id,
    )


@router.get(
    "/public/resolution-engine/v1/capabilities",
    response_model=ApiCapabilities,
)
def capabilities(
    context: PublicApiConsumerContext = Depends(consumer_context),
    db: Session = Depends(get_db),
) -> ApiCapabilities:
    del context
    return ResolutionPublicApi(db).capabilities()


@router.post(
    "/public/resolution-engine/v1/resolutions",
    response_model=ResolutionResource,
    status_code=201,
)
def create_resolution(
    request: CreateResolutionRequest,
    idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"),
    context: PublicApiConsumerContext = Depends(consumer_context),
    db: Session = Depends(get_db),
) -> ResolutionResource:
    if not idempotency_key or len(idempotency_key) > 160:
        raise PublicApiError(
            status_code=400,
            code="idempotency_key_required",
            message="Idempotency-Key is required and must not exceed 160 characters.",
            correlation_id=context.correlation_id,
        )
    return ResolutionPublicApi(db).create(
        request,
        context=context,
        idempotency_key=idempotency_key,
    )


@router.get(
    "/public/resolution-engine/v1/resolutions",
    response_model=ResolutionCollection,
)
def list_resolutions(
    status: str | None = Query(default=None, max_length=40),
    resolution_type: str | None = Query(default=None, max_length=160),
    subject_type: str | None = Query(default=None, max_length=100),
    subject_id: str | None = Query(default=None, max_length=160),
    cursor: str | None = Query(default=None, max_length=800),
    limit: int = Query(default=50, ge=1, le=100),
    context: PublicApiConsumerContext = Depends(consumer_context),
    db: Session = Depends(get_db),
) -> ResolutionCollection:
    return ResolutionPublicApi(db).list(
        context=context,
        status=status,
        resolution_type=resolution_type,
        subject_type=subject_type,
        subject_id=subject_id,
        cursor=cursor,
        limit=limit,
    )


@router.get(
    "/public/resolution-engine/v1/resolutions/{resolution_id}",
    response_model=ResolutionResource,
)
def get_resolution(
    resolution_id: str,
    context: PublicApiConsumerContext = Depends(consumer_context),
    db: Session = Depends(get_db),
) -> ResolutionResource:
    return ResolutionPublicApi(db).get(resolution_id, context=context)


@router.get(
    "/developers/resolution-engine",
    response_class=HTMLResponse,
    include_in_schema=False,
)
def developer_portal() -> str:
    base = "/api/public/resolution-engine/v1"
    return f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>MYC Resolution Engine API</title>
<style>
body{{font:16px system-ui;max-width:880px;margin:4rem auto;padding:0 1.5rem;color:#172033}}
code,pre{{background:#f2f5f8;border-radius:6px}}code{{padding:.15rem .35rem}}
pre{{padding:1rem;overflow:auto}}h1{{color:#075985}}.badge{{color:#fff;background:#075985;padding:.2rem .5rem;border-radius:1rem}}
</style></head><body>
<p><span class="badge">v1.0</span></p>
<h1>MYC Resolution Engine API</h1>
<p>Institutional, versioned interface to the deterministic Resolution Engine.</p>
<h2>Required headers</h2>
<pre>Authorization: Bearer consumer_key.secret
X-MYC-Organization-ID: organization-id
X-Correlation-ID: UUID
Idempotency-Key: required for POST</pre>
<h2>Resources</h2>
<ul>
<li><code>GET {escape(base)}/capabilities</code></li>
<li><code>POST {escape(base)}/resolutions</code></li>
<li><code>GET {escape(base)}/resolutions</code></li>
<li><code>GET {escape(base)}/resolutions/{{id}}</code></li>
</ul>
<p>The official Python SDK is <code>myc_resolution_sdk.ResolutionEngineClient</code>.
It communicates exclusively over this HTTP API.</p>
</body></html>"""
