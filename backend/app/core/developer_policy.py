"""DEV-0: canonical Developer authority policy.

Administrador ERP != Administrador de infraestructura. The generic permission
mechanism (``user_has_permission`` / ``require_*_permission``) treats ``"*"``
and ``"<prefix>.*"`` as "every permission"; that semantics stays untouched for
the ERP. Developer capabilities are deliberately NOT reachable through it:

    Developer permitido = actor interno AND capacidad Developer explícita

"Explicit" means the exact capability string (e.g. ``developer.access``) is
granted by an active role (today only ``Desarrollador`` carries them, see
``ROLE_PERMISSIONS``). Neither ``"*"`` nor the literal wildcard
``"developer.*"`` grants a Developer capability by itself, and no
email/username/user_id is ever consulted.

Every Developer gate -- opening a DeveloperSession, its live revalidation and
every future DEV-1+ operation guard -- must go through this module instead of
the generic helpers. See docs/architecture/MOBILE_DEVELOPER_AUTHORITY.md.
"""

from collections.abc import Iterable

from app.core.portal.constants import PortalAccountType, UserAccountStatus
from app.models.user import User
from app.services.auth import effective_user_permissions


DEVELOPER_ACCESS = "developer.access"
DEVELOPER_CAPABILITIES = frozenset({
    DEVELOPER_ACCESS,
    "developer.database.read",
    "developer.database.write",
    "developer.database.admin",
    "developer.shell.access",
    "developer.system.read",
    "developer.logs.read",
    "developer.services.execute",
    "developer.git.read",
})


def grants_developer_capability(permissions: Iterable[str], capability: str = DEVELOPER_ACCESS) -> bool:
    """Exact-match only: wildcards never open Developer."""
    if capability not in DEVELOPER_CAPABILITIES:
        raise ValueError(f"Capacidad Developer desconocida: {capability}")
    return capability in frozenset(permissions)


def user_has_developer_capability(user: User | None, capability: str = DEVELOPER_ACCESS) -> bool:
    """Live check against the user's CURRENT account state and roles."""
    return (
        user is not None
        and user.is_active
        and user.status == UserAccountStatus.ACTIVE.value
        and user.account_type == PortalAccountType.INTERNAL.value
        and grants_developer_capability(effective_user_permissions(user), capability)
    )


def actor_has_developer_capability(
    actor_type: str, user: User | None, capability: str = DEVELOPER_ACCESS
) -> bool:
    """For an authenticated Mobile actor: the actor itself must be internal
    (a client actor never reaches Developer, whatever strings it carries)."""
    return actor_type == "internal" and user_has_developer_capability(user, capability)
