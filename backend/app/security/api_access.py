"""Registro canónico y guard transversal deny-by-default para la API HTTP."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from typing import Callable, Iterable

from fastapi import Depends, HTTPException, Request, status
from fastapi.routing import APIRoute
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.db import get_db
from app.models.user import User
from app.services.auth import (
    get_optional_bearer_token,
    resolve_access_token_user,
    user_has_permission,
)


class AccessType(StrEnum):
    PUBLIC = "public_intentional"
    PUBLIC_SIGNED = "public_signed_token"
    PUBLIC_ENVIRONMENT = "public_environment_controlled"
    AUTHENTICATED = "authenticated"
    PERMISSION = "authenticated_permission"
    OWNERSHIP = "authenticated_ownership"
    CONSUMER = "resolution_engine_consumer"
    PORTAL = "client_portal_ownership"
    ADMINISTRATIVE = "administrative"


@dataclass(frozen=True, slots=True)
class AccessPolicy:
    access_type: AccessType
    identity_dependency: str
    permission: str | None = None
    ownership: str | None = None
    actor: str = "internal_user"
    public_intentional: bool = False
    finding: str | None = None


PUBLIC_OPERATIONS = {
    ("GET", "/"),
    ("GET", "/api/health"),
    ("GET", "/api/auth/registration-status"),
    ("POST", "/api/auth/register"),
    ("POST", "/api/auth/login"),
    ("POST", "/api/auth/refresh"),
}

SIGNED_PUBLIC_OPERATIONS = {
    ("GET", "/verify/{authentication_code}"),
}

ENVIRONMENT_PUBLIC_OPERATIONS = {
    ("GET", "/api/developers/resolution-engine"),
}


def _permission(permission: str, *, administrative: bool = False) -> AccessPolicy:
    return AccessPolicy(
        access_type=AccessType.ADMINISTRATIVE if administrative else AccessType.PERMISSION,
        identity_dependency="access_jwt",
        permission=permission,
        actor="internal_user",
        finding="AUD-001/AUD-011",
    )


def _method_permission(method: str, read: str, create: str, update: str, delete: str | None = None) -> str:
    if method == "GET":
        return read
    if method == "POST":
        return create
    if method in {"PATCH", "PUT"}:
        return update
    if method == "DELETE":
        return delete or update
    raise KeyError(method)


def _client_policy(method: str, path: str) -> AccessPolicy:
    if method == "POST" and path == "/api/clients":
        return _permission("clients.create")
    if method == "GET":
        return _permission("clients.read")
    return _permission("clients.update")


def _catalog_policy(method: str, path: str) -> AccessPolicy:
    if path == "/api/catalog-items/linked-companies":
        return _permission("catalog_items.read" if method == "GET" else "services.manage_linked_company")
    return _permission(
        _method_permission(
            method,
            "catalog_items.read",
            "catalog_items.create",
            "catalog_items.update",
            "catalog_items.delete",
        )
    )


def _quotation_policy(method: str, _path: str) -> AccessPolicy:
    return _permission(
        _method_permission(
            method,
            "quotations.read",
            "quotations.create",
            "quotations.update",
            "quotations.update",
        )
    )


def _service_order_policy(method: str, path: str) -> AccessPolicy:
    if "capture-package" in path or path.endswith("/capture-files"):
        permission = "certificates.upload_pdf" if method == "POST" else "certificates.read"
        return _permission(permission)
    if path.endswith("/confirm-signatures"):
        return _permission("service_orders.sign")
    if "/certificates/authenticate-approved" in path:
        return _permission("certificates.approve")
    if "/certificates/release-authenticated" in path:
        return _permission("release.manage")
    if path.endswith("/certificate-pdfs"):
        return _permission("certificates.upload_pdf")
    if method == "GET":
        return _permission("service_orders.read")
    if method == "POST" and path == "/api/service-orders":
        return _permission("service_orders.create")
    return _permission("service_orders.update")


def _certificate_policy(method: str, path: str) -> AccessPolicy:
    if method == "GET":
        return _permission("certificates.read")
    if method == "DELETE" or (method == "POST" and path == "/api/certificates"):
        return _permission("certificates.create")
    if path.endswith(("/quality", "/quality-reject", "/return-to-technician", "/request-correction", "/suspend")):
        return _permission("certificates.quality")
    if path.endswith(("/quality-approve", "/authenticate", "/approve")):
        return _permission("certificates.approve")
    if path.endswith(("/release-to-client", "/release")):
        return _permission("release.manage")
    if path.endswith("/manual-accept-match"):
        return _permission("certificates.match_override")
    if path.endswith("/upload-pdf"):
        return _permission("certificates.upload_pdf")
    return _permission("certificates.capture")


def _invoice_policy(method: str, path: str) -> AccessPolicy:
    if path.startswith("/api/invoice-payments"):
        return _permission("payments.read")
    if path.endswith("/payments"):
        return _permission("payments.manage")
    return _permission("invoices.read" if method == "GET" else "invoices.manage")


def _settings_policy(method: str, _path: str) -> AccessPolicy:
    return _permission(
        "settings.institutional.read" if method == "GET" else "settings.institutional.update",
        administrative=True,
    )


def _generic_resource_policy(resource: str) -> Callable[[str, str], AccessPolicy]:
    def build(method: str, _path: str) -> AccessPolicy:
        return _permission(
            _method_permission(
                method,
                f"{resource}.read",
                f"{resource}.create",
                f"{resource}.update",
                f"{resource}.delete",
            )
        )

    return build


POLICY_BY_TAG: dict[str, Callable[[str, str], AccessPolicy]] = {
    "activity": lambda _method, _path: _permission("activity.read"),
    "notifications": lambda _method, _path: AccessPolicy(AccessType.AUTHENTICATED, "access_jwt"),
    "audit_logs": lambda _method, _path: _permission("audit_logs.read", administrative=True),
    "modules": lambda _method, _path: AccessPolicy(AccessType.AUTHENTICATED, "access_jwt"),
    "clients": _client_policy,
    "catalog-items": _catalog_policy,
    "documents": _generic_resource_policy("documents"),
    "document-interpretations": _generic_resource_policy("document_interpretations"),
    "document-templates": lambda method, _path: _permission("quotations.read" if method == "GET" else "quotations.update"),
    "reference-standards": _generic_resource_policy("standards"),
    "reference-standard-certificates": _generic_resource_policy("reference_standard_certificates"),
    "resolution-center": lambda _method, _path: _permission("resolution_center.read"),
    "calibration-procedures": _generic_resource_policy("procedures"),
    "quotations": _quotation_policy,
    "sales-exceptions": lambda _method, _path: _permission("quotations.exceptions.inspect"),
    "service-orders": _service_order_policy,
    "technical-profiles": _generic_resource_policy("technical_profiles"),
    "equipment": _generic_resource_policy("equipment"),
    "field-sheets": lambda method, _path: _permission("field_sheets.read" if method == "GET" else "field_sheets.update"),
    "certificates": _certificate_policy,
    "communications": lambda _method, _path: AccessPolicy(
        AccessType.OWNERSHIP,
        "access_jwt+conversation_context",
        ownership="conversation_participant",
    ),
    "invoices": _invoice_policy,
    "integrations": lambda _method, _path: _permission("integrations.facturama.status"),
    "sat-catalogs": lambda method, _path: _permission("sat_catalogs.read" if method == "GET" else "sat_catalogs.manage"),
    "institutional-configuration": _settings_policy,
    "metrology": lambda _method, _path: _permission("metrology.execute"),
    "operational-engines": lambda _method, _path: _permission("operational_engines.execute"),
    "pattern-selection": lambda _method, _path: _permission("pattern_selection.execute"),
    "uncertainty": lambda method, _path: _permission("uncertainty_models.read" if method == "GET" else "uncertainty_models.update"),
    "users": lambda _method, _path: _permission("users.manage", administrative=True),
    "Field Sheet Templates": lambda method, _path: _permission("field_sheet_templates.read" if method == "GET" else "field_sheet_templates.update"),
}


def classify_operation(method: str, path: str, tags: Iterable[str]) -> AccessPolicy | None:
    key = (method.upper(), path)
    if key in PUBLIC_OPERATIONS:
        return AccessPolicy(AccessType.PUBLIC, "none", actor="anonymous", public_intentional=True)
    if key in SIGNED_PUBLIC_OPERATIONS or (
        method.upper() == "GET" and path.startswith("/verify/")
    ):
        return AccessPolicy(
            AccessType.PUBLIC_SIGNED,
            "authentication_code",
            actor="anonymous",
            public_intentional=True,
        )
    if key in ENVIRONMENT_PUBLIC_OPERATIONS:
        return AccessPolicy(
            AccessType.PUBLIC_ENVIRONMENT,
            "environment_flag",
            actor="anonymous",
            public_intentional=True,
            finding="AUD-030",
        )
    if path.startswith("/api/public/resolution-engine/v1/"):
        return AccessPolicy(
            AccessType.CONSUMER,
            "consumer_context",
            ownership="organization_id",
            actor="api_consumer",
            public_intentional=True,
        )
    if path.startswith("/api/client-portal/"):
        return AccessPolicy(
            AccessType.PORTAL,
            "access_jwt+portal_client_context",
            permission="portal.read",
            ownership="client_id_derived_from_identity",
            actor="portal_user",
            finding="AUD-002",
        )
    if key == ("GET", "/api/auth/me"):
        return AccessPolicy(AccessType.AUTHENTICATED, "access_jwt")

    tag_list = list(tags)
    if len(tag_list) != 1:
        return None
    builder = POLICY_BY_TAG.get(tag_list[0])
    if builder is None:
        return None
    try:
        return builder(method.upper(), path)
    except KeyError:
        return None


def _scope_route_metadata(request: Request) -> tuple[str, list[str]]:
    route = request.scope.get("route")
    tags = list(getattr(route, "tags", []))
    return request.url.path, tags


def _unauthorized(detail: str = "Autenticación requerida") -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail=detail,
        headers={"WWW-Authenticate": "Bearer"},
    )


def enforce_api_access(
    request: Request,
    token: str | None = Depends(get_optional_bearer_token),
    db: Session = Depends(get_db),
) -> None:
    path, tags = _scope_route_metadata(request)
    policy = classify_operation(request.method, path, tags)
    if policy is None:
        raise HTTPException(status_code=500, detail="Ruta sin clasificación de acceso")
    if policy.access_type in {AccessType.PUBLIC, AccessType.PUBLIC_SIGNED, AccessType.CONSUMER}:
        return
    if policy.access_type == AccessType.PUBLIC_ENVIRONMENT:
        if not settings.enable_developer_portal:
            raise HTTPException(status_code=404, detail="Recurso no encontrado")
        return
    if not token:
        raise _unauthorized()

    user = resolve_access_token_user(db, token)
    if policy.permission and not user_has_permission(user, policy.permission):
        raise HTTPException(status_code=403, detail="Permiso insuficiente")
    request.state.current_user = user


@dataclass(frozen=True, slots=True)
class RouteOperation:
    method: str
    path: str
    router: str
    function: str
    tags: tuple[str, ...]


def iter_route_operations(app) -> list[RouteOperation]:
    operations: list[RouteOperation] = []

    def visit(route, prefix: str = "", inherited_tags: tuple[str, ...] = ()) -> None:
        if isinstance(route, APIRoute):
            path = f"{prefix}{route.path}"
            tags = tuple(dict.fromkeys((*inherited_tags, *route.tags)))
            for method in sorted(route.methods - {"HEAD", "OPTIONS"}):
                operations.append(
                    RouteOperation(method, path, tags[0] if tags else "root", route.name, tags)
                )
            return

        original_router = getattr(route, "original_router", None)
        context = getattr(route, "include_context", None)
        if original_router is None or context is None:
            return
        next_prefix = f"{prefix}{context.prefix}"
        next_tags = tuple((*inherited_tags, *context.tags))
        for child in original_router.routes:
            visit(child, next_prefix, next_tags)

    for registered in app.routes:
        visit(registered)
    return sorted(operations, key=lambda item: (item.path, item.method, item.function))


def assert_all_routes_classified(app) -> list[RouteOperation]:
    operations = iter_route_operations(app)
    missing = [
        operation
        for operation in operations
        if classify_operation(operation.method, operation.path, operation.tags) is None
    ]
    if missing:
        labels = ", ".join(f"{item.method} {item.path}" for item in missing)
        raise RuntimeError(f"Operaciones HTTP sin clasificación de acceso: {labels}")
    return operations


def build_endpoint_inventory(app) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for operation in assert_all_routes_classified(app):
        policy = classify_operation(operation.method, operation.path, operation.tags)
        assert policy is not None
        protected = policy.access_type not in {
            AccessType.PUBLIC,
            AccessType.PUBLIC_SIGNED,
            AccessType.PUBLIC_ENVIRONMENT,
        }
        rows.append(
            {
                "method": operation.method,
                "path": operation.path,
                "router": operation.router,
                "function": operation.function,
                "access_type": policy.access_type.value,
                "identity_dependency": policy.identity_dependency,
                "permission": policy.permission or "",
                "ownership": policy.ownership or "",
                "actor": policy.actor,
                "public_intentional": "yes" if policy.public_intentional else "no",
                "test_401": "required" if protected else "not_applicable",
                "test_403": "required" if policy.permission else "not_applicable",
                "test_ownership": "required" if policy.ownership else "not_applicable",
                "finding": policy.finding or "",
            }
        )
    return rows
