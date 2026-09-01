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
    "external_viewer": {
        "mobile.access",
        "work_orders.read_organization",
        "equipment.read",
        "field_sheets.read",
    },
    "external_operator_jr": {
        "mobile.access",
        "work_orders.read_organization",
        "work_orders.execute",
        "equipment.read",
        "equipment.write",
        "field_sheets.read",
        "field_sheets.capture",
        "field_sheet_templates.read",
        "lab_clients.read",
        "lab_clients.create",
        "signatures.capture",
        "mobile_tickets.create",
        "mobile_tickets.read",
    },
    "external_operator_sr": {
        "mobile.access",
        "work_orders.read_organization",
        "work_orders.execute",
        "work_orders.close",
        "work_orders.group.request",
        "communications.view",
        "communications.create",
        "equipment.read",
        "equipment.write",
        "field_sheets.read",
        "field_sheets.capture",
        "field_sheet_templates.read",
        "lab_clients.read",
        "lab_clients.create",
        "signatures.capture",
        "mobile_tickets.create",
        "mobile_tickets.read",
    },
}

ROLE_PRESENTATION = {
    "external_viewer": (
        "Viewer externo",
        "Lectura Mobile limitada a la organización vinculada.",
    ),
    "external_operator_jr": (
        "Operativo Jr",
        "Operación Mobile dentro de la organización, sin facultades de folios.",
    ),
    "external_operator_sr": (
        "Operativo Sr",
        "Operación Mobile senior con autoridad de cierre técnico de OT; folios permanecen fuera de alcance.",
    ),
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
            name, description = ROLE_PRESENTATION.get(
                code,
                (code.replace("_", " ").title(), "Rol base institucional del Portal del Cliente"),
            )
            role = ClientPortalRole(code=code, name=name, description=description, is_system=True, client_id=None)
            db.add(role)
            db.flush()
            roles[code] = role
        elif code in ROLE_PRESENTATION:
            role.name, role.description = ROLE_PRESENTATION[code]
        existing = {item.permission_id for item in db.scalars(select(ClientPortalRolePermission).where(ClientPortalRolePermission.role_id == role.id)).all()}
        if code in {"external_operator_jr", "external_operator_sr"}:
            obsolete = permissions["work_orders.create"].id
            stale_link = db.scalar(select(ClientPortalRolePermission).where(
                ClientPortalRolePermission.role_id == role.id,
                ClientPortalRolePermission.permission_id == obsolete,
            ))
            if stale_link is not None:
                db.delete(stale_link)
                existing.discard(obsolete)
        for permission_code in permission_codes:
            permission = permissions[permission_code]
            if permission.id not in existing:
                db.add(ClientPortalRolePermission(role_id=role.id, permission_id=permission.id))
    db.commit()
