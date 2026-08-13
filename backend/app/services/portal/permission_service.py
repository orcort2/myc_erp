"""Catálogo estable de permisos y roles base del portal."""

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.portal.constants import PortalPermissionCode
from app.models.client_portal_permission import ClientPortalPermission
from app.models.client_portal_role import ClientPortalRole
from app.models.client_portal_role_permission import ClientPortalRolePermission

ROLE_PERMISSIONS = {
    "portal_administrator": {item.value for item in PortalPermissionCode},
    "purchasing": {"portal.read", "profile.view", "profile.update", "client.view", "quotations.view", "quotations.download", "services.view", "communications.view", "communications.create"},
    "quality": {"portal.read", "profile.view", "profile.update", "client.view", "services.view", "equipment.view", "certificates.view", "certificates.download", "communications.view", "communications.create"},
    "billing": {"portal.read", "profile.view", "profile.update", "client.view", "invoices.view", "invoices.download", "payments.view", "communications.view", "communications.create"},
    "operations": {"portal.read", "profile.view", "profile.update", "client.view", "services.view", "equipment.view", "certificates.view", "communications.view", "communications.create"},
    "viewer": {"portal.read", "profile.view", "client.view", "quotations.view", "services.view", "equipment.view", "certificates.view", "invoices.view", "payments.view", "communications.view"},
}


def _reconcile_legacy_portal_read(
    db: Session,
    permissions: dict[str, ClientPortalPermission],
) -> None:
    legacy = permissions.get("portal.view")
    if legacy is None:
        return

    canonical = permissions.get("portal.read")
    if canonical is None:
        legacy.code = "portal.read"
        legacy.name = "Portal Read"
        legacy.description = "Capacidad portal.read del Portal del Cliente"
        legacy.module = "portal"
        permissions.pop("portal.view")
        permissions["portal.read"] = legacy
        db.flush()
        return

    canonical_role_ids = set(
        db.scalars(
            select(ClientPortalRolePermission.role_id).where(
                ClientPortalRolePermission.permission_id == canonical.id
            )
        ).all()
    )
    legacy_links = list(
        db.scalars(
            select(ClientPortalRolePermission).where(
                ClientPortalRolePermission.permission_id == legacy.id
            )
        ).all()
    )
    for link in legacy_links:
        if link.role_id not in canonical_role_ids:
            db.add(
                ClientPortalRolePermission(
                    role_id=link.role_id,
                    permission_id=canonical.id,
                )
            )
            canonical_role_ids.add(link.role_id)
        db.delete(link)
    legacy.is_active = False
    db.flush()


def ensure_portal_catalog(db: Session) -> None:
    permissions = {item.code: item for item in db.scalars(select(ClientPortalPermission)).all()}
    _reconcile_legacy_portal_read(db, permissions)
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
