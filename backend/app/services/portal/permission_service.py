"""Catálogo estable de permisos y roles base del portal."""

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.portal.constants import PortalPermissionCode
from app.models.client_portal_permission import ClientPortalPermission
from app.models.client_portal_role import ClientPortalRole
from app.models.client_portal_role_permission import ClientPortalRolePermission

ROLE_PERMISSIONS = {
    "portal_administrator": {item.value for item in PortalPermissionCode},
    "purchasing": {"portal.view", "profile.view", "profile.update", "client.view", "quotations.view", "quotations.download", "services.view", "communications.view", "communications.create"},
    "quality": {"portal.view", "profile.view", "profile.update", "client.view", "services.view", "equipment.view", "certificates.view", "certificates.download", "communications.view", "communications.create"},
    "billing": {"portal.view", "profile.view", "profile.update", "client.view", "invoices.view", "invoices.download", "payments.view", "communications.view", "communications.create"},
    "operations": {"portal.view", "profile.view", "profile.update", "client.view", "services.view", "equipment.view", "certificates.view", "communications.view", "communications.create"},
    "viewer": {"portal.view", "profile.view", "client.view", "quotations.view", "services.view", "equipment.view", "certificates.view", "invoices.view", "payments.view", "communications.view"},
}


def ensure_portal_catalog(db: Session) -> None:
    permissions = {item.code: item for item in db.scalars(select(ClientPortalPermission)).all()}
    for code in PortalPermissionCode:
        if code.value not in permissions:
            permission = ClientPortalPermission(code=code.value, name=code.value.replace(".", " ").title(), description=f"Capacidad {code.value} del Portal del Cliente", module=code.value.split(".", 1)[0])
            db.add(permission)
            db.flush()
            permissions[code.value] = permission
    roles = {item.code: item for item in db.scalars(select(ClientPortalRole).where(ClientPortalRole.client_id.is_(None))).all()}
    for code, permission_codes in ROLE_PERMISSIONS.items():
        role = roles.get(code)
        if role is None:
            role = ClientPortalRole(code=code, name=code.replace("_", " ").title(), description="Rol base institucional del Portal del Cliente", is_system=True, client_id=None)
            db.add(role)
            db.flush()
            roles[code] = role
        existing = {item.permission_id for item in db.scalars(select(ClientPortalRolePermission).where(ClientPortalRolePermission.role_id == role.id)).all()}
        for permission_code in permission_codes:
            permission = permissions[permission_code]
            if permission.id not in existing:
                db.add(ClientPortalRolePermission(role_id=role.id, permission_id=permission.id))
    db.commit()
