from __future__ import annotations

import ast
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

import httpx
import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

import app.models  # noqa: F401
from app.core.db import Base, get_db
from app.main import app
from app.resolution_public_api.security import provision_consumer
from myc_resolution_contracts.v1 import CreateResolutionRequest
from myc_resolution_sdk import ResolutionApiError, ResolutionEngineClient


@pytest.fixture
def public_api(tmp_path):
    engine = create_engine(
        f"sqlite+pysqlite:///{tmp_path / 'phase10.sqlite'}",
        connect_args={"check_same_thread": False},
    )
    tables = [
        table
        for name, table in Base.metadata.tables.items()
        if not name.startswith("activity_")
    ]
    Base.metadata.create_all(engine, tables=tables)
    factory = sessionmaker(bind=engine, expire_on_commit=False)
    with factory.begin() as session:
        _, token = provision_consumer(
            session,
            consumer_key="phase10-client",
            name="Phase 10 client",
            organization_id="organization-1",
            permissions=("resolution.create", "resolution.audit.inspect"),
        )
        _, other_token = provision_consumer(
            session,
            consumer_key="other-client",
            name="Other client",
            organization_id="organization-2",
            permissions=("resolution.create", "resolution.audit.inspect"),
        )

    def override_db():
        with factory() as session:
            yield session

    app.dependency_overrides[get_db] = override_db
    try:
        yield TestClient(app), token, other_token
    finally:
        app.dependency_overrides.clear()
        engine.dispose()


def headers(token: str, organization: str = "organization-1") -> dict[str, str]:
    return {
        "Authorization": f"Bearer {token}",
        "X-MYC-Organization-ID": organization,
        "X-Correlation-ID": str(uuid4()),
    }


def payload(*, title: str = "Retiro controlado") -> dict:
    return {
        "resolution_type": "certificate.resolve_incorrect_release",
        "definition_version": "1.0",
        "subject_type": "certificate",
        "subject_id": "91",
        "title": title,
        "reason": "Liberación incorrecta",
        "problem": {
            "code": "certificate_incorrect_release",
            "summary": "El certificado fue liberado por error.",
            "detected_by": "quality",
            "detected_at": "2026-07-28T12:00:00Z",
        },
    }


def test_contract_v1_is_strict_and_timezone_aware():
    request = CreateResolutionRequest.model_validate(payload())
    assert request.definition_version == "1.0"
    with pytest.raises(ValidationError):
        CreateResolutionRequest.model_validate({**payload(), "internal_id": 7})
    naive = payload()
    naive["problem"]["detected_at"] = "2026-07-28T12:00:00"
    with pytest.raises(ValidationError):
        CreateResolutionRequest.model_validate(naive)


def test_api_requires_consumer_organization_correlation_and_idempotency(public_api):
    client, token, _ = public_api
    url = "/api/public/resolution-engine/v1/resolutions"
    assert client.post(url, json=payload()).status_code == 400
    mismatch = client.post(
        url,
        json=payload(),
        headers=headers(token, "organization-2")
        | {"Idempotency-Key": "create-1"},
    )
    assert mismatch.status_code == 403
    assert mismatch.json()["code"] == "organization_scope_mismatch"
    missing_key = client.post(url, json=payload(), headers=headers(token))
    assert missing_key.status_code == 400
    assert missing_key.json()["code"] == "idempotency_key_required"


def test_create_replay_conflict_queries_and_tenant_isolation(public_api):
    client, token, other_token = public_api
    request_headers = headers(token) | {"Idempotency-Key": "stable-key"}
    created = client.post(
        "/api/public/resolution-engine/v1/resolutions",
        json=payload(),
        headers=request_headers,
    )
    assert created.status_code == 201, created.text
    resource = created.json()
    assert resource["status"] == "draft"
    assert resource["audit_valid"] is True
    assert resource["timeline"]

    replay = client.post(
        "/api/public/resolution-engine/v1/resolutions",
        json=payload(),
        headers=headers(token) | {"Idempotency-Key": "stable-key"},
    )
    assert replay.status_code == 201
    assert replay.json()["id"] == resource["id"]

    conflict = client.post(
        "/api/public/resolution-engine/v1/resolutions",
        json=payload(title="Otro payload"),
        headers=headers(token) | {"Idempotency-Key": "stable-key"},
    )
    assert conflict.status_code == 409
    assert conflict.json()["code"] == "idempotency_conflict"

    second = client.post(
        "/api/public/resolution-engine/v1/resolutions",
        json=payload(title="Segundo expediente"),
        headers=headers(token) | {"Idempotency-Key": "stable-key-2"},
    )
    assert second.status_code == 201

    listing = client.get(
        "/api/public/resolution-engine/v1/resolutions",
        params={"status": "draft", "limit": 1},
        headers=headers(token),
    )
    assert listing.status_code == 200
    assert listing.json()["next_cursor"]
    next_page = client.get(
        "/api/public/resolution-engine/v1/resolutions",
        params={
            "status": "draft",
            "limit": 1,
            "cursor": listing.json()["next_cursor"],
        },
        headers=headers(token),
    )
    assert next_page.status_code == 200
    assert {
        listing.json()["items"][0]["id"],
        next_page.json()["items"][0]["id"],
    } == {resource["id"], second.json()["id"]}
    hidden = client.get(
        f"/api/public/resolution-engine/v1/resolutions/{resource['id']}",
        headers=headers(other_token, "organization-2"),
    )
    assert hidden.status_code == 404


def test_sdk_uses_public_http_contract_only(public_api):
    client, token, _ = public_api

    def forward(request: httpx.Request) -> httpx.Response:
        response = client.request(
            request.method,
            request.url.raw_path.decode(),
            headers=dict(request.headers),
            content=request.content,
        )
        return httpx.Response(
            response.status_code,
            headers=response.headers,
            content=response.content,
        )

    transport = httpx.MockTransport(forward)
    with ResolutionEngineClient(
        base_url="http://testserver",
        token=token,
        organization_id="organization-1",
        transport=transport,
    ) as sdk:
        capabilities = sdk.capabilities()
        assert capabilities.contract_version == "1.0"
        created = sdk.create_resolution(
            CreateResolutionRequest.model_validate(payload()),
            idempotency_key="sdk-create",
        )
        assert sdk.get_resolution(created.id).id == created.id
        assert sdk.list_resolutions(subject_id="91").items[0].id == created.id


def test_sdk_maps_stable_errors():
    def handler(_request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            403,
            json={
                "code": "authorization_denied",
                "message": "Denied.",
                "correlation_id": "correlation",
                "details": {},
            },
        )

    with ResolutionEngineClient(
        base_url="https://example.test",
        token="consumer.secret",
        organization_id="organization",
        transport=httpx.MockTransport(handler),
    ) as sdk:
        with pytest.raises(ResolutionApiError) as raised:
            sdk.capabilities()
    assert raised.value.code == "authorization_denied"


def test_public_contract_and_sdk_have_no_internal_app_dependencies():
    backend = Path(__file__).parents[2]
    for package in ("myc_resolution_contracts", "myc_resolution_sdk"):
        for source_path in (backend / package).glob("*.py"):
            tree = ast.parse(source_path.read_text())
            imports = [
                node.module
                for node in ast.walk(tree)
                if isinstance(node, ast.ImportFrom) and node.module
            ]
            assert not any(name == "app" or name.startswith("app.") for name in imports)


def test_public_router_contains_no_orm_or_lifecycle_imports():
    path = Path(__file__).parents[2] / "app/routers/resolution_public_api.py"
    imports = [
        node.module
        for node in ast.walk(ast.parse(path.read_text()))
        if isinstance(node, ast.ImportFrom) and node.module
    ]
    assert not any("resolution_engine" in name for name in imports)
    assert not any("infrastructure.persistence" in name for name in imports)
