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


def test_inventory_has_only_the_32_governed_compatibility_gaps():
    catalog_permissions, *_ = validator.parse_catalog()
    current = validator.current_permissions()
    inventory = validator.inventory_permissions()

    # 33 = 32 (corte previo) + lab_work_orders.use, que entra al inventario
    # por primera vez con la clasificación real de
    # GET /api/communications/work-order-mentions/search (@OT, checkpoint
    # c7a7adb): un permiso LAB legítimo y ya gobernado por ROLE_PERMISSIONS
    # (ver test_captura_role_is_lab_read_only_despite_generic_field_sheets_permissions
    # más abajo), simplemente ausente del catálogo institucional congelado
    # v1.0 -- que es anterior a MYC Mobile/LAB -- igual que el resto de la
    # familia lab_work_order_groups.*/service_orders.sales.* ya listada aquí.
    assert len(inventory - catalog_permissions) == 33
    assert inventory <= current
    assert "portal.view" not in inventory
    assert "portal.read" in inventory & catalog_permissions & current
    assert "mobile.access" in inventory & current
    assert "mobile.access" not in catalog_permissions
    assert {
        "lab_work_order_groups.create",
        "lab_work_order_groups.requests.read",
        "lab_work_order_groups.requests.claim",
        "lab_work_order_groups.requests.decide",
        "service_orders.sales.manage",
        "service_orders.sales.deliver",
        "service_orders.sales.authorize",
        "lab_work_orders.use",
    } <= inventory - catalog_permissions
    assert PERMISSIONS["SERVICE_ORDERS_DELETE"] == "service_orders.delete"
    assert PERMISSIONS["LAB_WORK_ORDERS_DELETE"] == "lab_work_orders.delete"
    assert all(
        "service_orders.delete" not in permissions
        for role, permissions in ROLE_PERMISSIONS.items()
        if role != "Administrador"
    )
    assert all(
        "lab_work_orders.delete" not in permissions
        for role, permissions in ROLE_PERMISSIONS.items()
        if role != "Administrador"
    )


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


def test_captura_role_is_lab_read_only_despite_generic_field_sheets_permissions():
    """Captura holds generic field_sheets.create/update (productive ERP flows), but
    that must never translate into LAB edit/execute capabilities. The LAB routers
    gate on field_sheets.capture/lab_work_orders.use/etc., not on the generic codes."""
    captura = ROLE_PERMISSIONS["Captura"]
    assert "field_sheets.create" in captura
    assert "field_sheets.update" in captura
    assert all(
        permission not in captura
        for permission in {
            "lab_work_orders.use",
            "work_orders.execute",
            "work_orders.create",
            "equipment.write",
            "field_sheets.capture",
            "signatures.capture",
            "lab_work_order_groups.create",
            "lab_work_orders.cancel",
            "lab_work_orders.delete",
        }
    )
