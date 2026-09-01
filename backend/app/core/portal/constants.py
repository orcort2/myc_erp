from enum import StrEnum


class PortalAccountType(StrEnum):
    INTERNAL = "internal"
    CLIENT_PORTAL = "client_portal"


class UserAccountStatus(StrEnum):
    PENDING = "pending"
    ACTIVE = "active"
    SUSPENDED = "suspended"
    LOCKED = "locked"
    DISABLED = "disabled"


class PortalRegistrationStatus(StrEnum):
    PENDING_EMAIL_VERIFICATION = "pending_email_verification"
    PENDING_REVIEW = "pending_review"
    LINK_REQUESTED = "link_requested"
    LINKED = "linked"
    REJECTED = "rejected"
    CANCELLED = "cancelled"
    EXPIRED = "expired"


class ClientLinkRequestStatus(StrEnum):
    PENDING = "pending"
    UNDER_REVIEW = "under_review"
    APPROVED = "approved"
    REJECTED = "rejected"
    CANCELLED = "cancelled"
    EXPIRED = "expired"


class ClientPortalMembershipStatus(StrEnum):
    PENDING = "pending"
    ACTIVE = "active"
    SUSPENDED = "suspended"
    REVOKED = "revoked"
    REJECTED = "rejected"


class PortalInvitationStatus(StrEnum):
    PENDING = "pending"
    ACCEPTED = "accepted"
    EXPIRED = "expired"
    CANCELLED = "cancelled"
    REVOKED = "revoked"


class PortalRoleScope(StrEnum):
    SYSTEM = "system"
    CLIENT = "client"


class PortalPermissionCode(StrEnum):
    PORTAL_READ = "portal.read"

    MOBILE_ACCESS = "mobile.access"
    WORK_ORDERS_READ_ORGANIZATION = "work_orders.read_organization"
    WORK_ORDERS_CREATE = "work_orders.create"
    WORK_ORDERS_EXECUTE = "work_orders.execute"
    WORK_ORDERS_CLOSE = "work_orders.close"
    WORK_ORDERS_GROUP_REQUEST = "work_orders.group.request"
    EQUIPMENT_READ = "equipment.read"
    EQUIPMENT_WRITE = "equipment.write"
    FIELD_SHEETS_READ = "field_sheets.read"
    FIELD_SHEETS_CAPTURE = "field_sheets.capture"
    FIELD_SHEET_TEMPLATES_READ = "field_sheet_templates.read"
    LAB_CLIENTS_READ = "lab_clients.read"
    LAB_CLIENTS_CREATE = "lab_clients.create"
    SIGNATURES_CAPTURE = "signatures.capture"
    MOBILE_TICKETS_CREATE = "mobile_tickets.create"
    MOBILE_TICKETS_READ = "mobile_tickets.read"

    PROFILE_VIEW = "profile.view"
    PROFILE_UPDATE = "profile.update"

    CLIENT_VIEW = "client.view"

    USERS_VIEW = "users.view"
    USERS_INVITE = "users.invite"
    USERS_MANAGE = "users.manage"

    ROLES_VIEW = "roles.view"
    ROLES_MANAGE = "roles.manage"

    QUOTATIONS_VIEW = "quotations.view"
    QUOTATIONS_DOWNLOAD = "quotations.download"

    SERVICES_VIEW = "services.view"

    EQUIPMENT_VIEW = "equipment.view"

    CERTIFICATES_VIEW = "certificates.view"
    CERTIFICATES_DOWNLOAD = "certificates.download"

    INVOICES_VIEW = "invoices.view"
    INVOICES_DOWNLOAD = "invoices.download"

    PAYMENTS_VIEW = "payments.view"

    COMMUNICATIONS_VIEW = "communications.view"
    COMMUNICATIONS_CREATE = "communications.create"


SYSTEM_PORTAL_ROLE_CODES = frozenset(
    {
        "portal_administrator",
        "purchasing",
        "quality",
        "billing",
        "operations",
        "viewer",
        "external_viewer",
        "external_operator_jr",
        "external_operator_sr",
    }
)


DEFAULT_PORTAL_LANGUAGE = "es-MX"
DEFAULT_PORTAL_TIMEZONE = "America/Mexico_City"
DEFAULT_PORTAL_HOME_PAGE = "dashboard"
DEFAULT_PORTAL_SESSION_TIMEOUT_MINUTES = 480

DEFAULT_EMAIL_VERIFICATION_TOKEN_TTL_HOURS = 24
DEFAULT_INVITATION_TOKEN_TTL_HOURS = 72

MINIMUM_PORTAL_PASSWORD_LENGTH = 8
MAXIMUM_PORTAL_PASSWORD_LENGTH = 128
