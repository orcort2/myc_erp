import importlib.util
from pathlib import Path

from app.core.permissions import PERMISSIONS, ROLE_PERMISSIONS
from app.core.portal.constants import PortalPermissionCode
from app.core.portal.security import PORTAL_PERMISSION_ALIASES
from app.security.api_access import classify_operation

VALIDATOR_PATH = Path(__file__).resolve().parents[2] / "scripts/validate_capability_catalog.py"
SPEC = importlib.util.spec_from_file_location("validate_capability_catalog", VALIDATOR_PATH)
assert SPEC and SPEC.loader
validator = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(validator)


def test_inventory_has_only_the_22_governed_compatibility_gaps():
    catalog_permissions, *_ = validator.parse_catalog()
    current = validator.current_permissions()
    inventory = validator.inventory_permissions()

    assert len(inventory - catalog_permissions) == 22
    assert inventory <= current
    assert "portal.view" not in inventory
    assert "portal.read" in inventory & catalog_permissions & current
    assert "service_orders.read_assigned" in inventory & current
    assert "service_orders.read_assigned" not in catalog_permissions
    assert {"lab_work_orders.use", "lab_work_orders.export"} <= inventory - catalog_permissions


def test_portal_uses_cataloged_read_and_normalizes_the_legacy_code():
    assert PortalPermissionCode.PORTAL_READ.value == "portal.read"
    assert PORTAL_PERMISSION_ALIASES == {"portal.view": "portal.read"}
    assert classify_operation("GET", "/api/client-portal/dashboard", ["client-portal-dashboard"]).permission == "portal.read"


def test_reference_standard_delete_is_explicit_and_least_privilege():
    permission = "reference_standard_certificates.delete"

    assert PERMISSIONS["REFERENCE_STANDARD_CERTIFICATES_DELETE"] == permission
    assert permission in ROLE_PERMISSIONS["Calidad"]
    assert permission in ROLE_PERMISSIONS["Desarrollador"]
    assert all(
        permission not in ROLE_PERMISSIONS[role]
        for role in {"Comercial", "Tecnico", "Captura", "Finanzas", "Cliente", "Operador", "Auditor"}
    )
    assert classify_operation(
        "DELETE",
        "/api/reference-standard-certificates/uncertainties/{uncertainty_id}",
        ["reference-standard-certificates"],
    ).permission == permission
