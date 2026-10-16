from app.core.permissions import ROLE_PERMISSIONS
from app.realtime.resource_changes import RESOURCE_READ_PERMISSIONS


def test_resource_permissions_exist_in_role_catalog():
    known_permissions = {
        permission
        for permissions in ROLE_PERMISSIONS.values()
        for permission in permissions
    }

    missing = {
        resource: permission
        for resource, permission in RESOURCE_READ_PERMISSIONS.items()
        if permission not in known_permissions
    }

    assert not missing, (
        f"Recursos realtime con permisos inexistentes: {missing}"
    )


def test_lab_resource_uses_existing_authority():
    assert (
        RESOURCE_READ_PERMISSIONS["lab_work_orders"]
        == "lab_work_orders.use"
    )
