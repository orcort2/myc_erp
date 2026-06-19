INITIAL_ROLES = {
    "Administrador": "Acceso total al sistema.",
    "Comercial": "Gestion comercial, clientes y cotizaciones.",
    "Tecnico": "Gestion tecnica de equipos y hojas de campo.",
    "Captura": "Captura y generacion documental.",
    "Calidad": "Revision y aprobacion de certificados.",
    "Finanzas": "Pagos, facturacion y liberacion financiera.",
    "Cliente": "Acceso limitado para cliente externo.",
    "Desarrollador": "Acceso tecnico avanzado para desarrollo y soporte.",
}


ROLE_PERMISSIONS = {
    "Administrador": {"*"},
    "Comercial": {
        "clients.read",
        "clients.create",
        "clients.update",
        "quotations.read",
        "quotations.create",
        "quotations.update",
        "service_orders.read",
    },
    "Tecnico": {
        "equipment.read",
        "equipment.update",
        "field_sheets.read",
        "field_sheets.create",
        "field_sheets.update",
        "service_orders.read",
        "service_orders.update",
    },
    "Captura": {
        "clients.read",
        "quotations.read",
        "service_orders.read",
        "field_sheets.read",
        "certificates.read",
        "certificates.create",
        "certificates.generate",
    },
    "Calidad": {
        "certificates.read",
        "certificates.quality",
        "certificates.approve",
        "certificates.release",
        "field_sheets.read",
        "service_orders.read",
    },
    "Finanzas": {
        "clients.read",
        "quotations.read",
        "payments.read",
        "payments.manage",
        "invoices.read",
        "invoices.manage",
        "release.manage",
    },
    "Cliente": {
        "portal.read",
        "quotations.read_own",
        "certificates.read_own",
        "service_orders.read_own",
    },
    "Desarrollador": {
        "users.read",
        "users.manage",
        "settings.read",
        "settings.manage",
    },
}


PERMISSIONS = {
    "USERS_READ": "users.read",
    "USERS_MANAGE": "users.manage",
    "CLIENTS_READ": "clients.read",
    "CLIENTS_CREATE": "clients.create",
    "CLIENTS_UPDATE": "clients.update",
    "QUOTATIONS_READ": "quotations.read",
    "QUOTATIONS_CREATE": "quotations.create",
    "QUOTATIONS_UPDATE": "quotations.update",
    "CERTIFICATES_READ": "certificates.read",
    "CERTIFICATES_CREATE": "certificates.create",
    "CERTIFICATES_APPROVE": "certificates.approve",
}
