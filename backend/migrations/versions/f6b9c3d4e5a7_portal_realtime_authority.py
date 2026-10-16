"""Notify realtime authority changes for client portal access.

Revision ID: f6b9c3d4e5a7
Revises: e5a8b2c3d4f6
"""

from alembic import op


revision = "f6b9c3d4e5a7"
down_revision = "e5a8b2c3d4f6"
branch_labels = None
depends_on = None


AUTHORITY_TABLES = {
    "client_portal_memberships": (
        "status",
        "client_id",
        "user_id",
    ),
    "client_portal_membership_roles": None,
    "client_portal_role_permissions": None,
    "client_portal_roles": ("is_active",),
    "client_portal_permissions": ("is_active",),
    "client_portals": (
        "is_enabled",
        "is_active",
        "client_id",
    ),
}

CLIENT_AUTHORITY_COLUMNS = ("is_active",)


def _create_triggers(table: str, columns: tuple[str, ...] | None):
    update_clause = (
        "UPDATE OF " + ", ".join(columns)
        if columns
        else "UPDATE"
    )

    op.execute(f"""
        CREATE TRIGGER myc_realtime_portal_authority_insert
        AFTER INSERT OR DELETE
        ON {table}
        FOR EACH STATEMENT
        EXECUTE FUNCTION myc_notify_resource_change(
            'portal_authority'
        );
    """)

    op.execute(f"""
        CREATE TRIGGER myc_realtime_portal_authority_update
        AFTER {update_clause}
        ON {table}
        FOR EACH STATEMENT
        EXECUTE FUNCTION myc_notify_resource_change(
            'portal_authority'
        );
    """)


def upgrade():
    for table, columns in AUTHORITY_TABLES.items():
        _create_triggers(table, columns)

    _create_triggers("clients", CLIENT_AUTHORITY_COLUMNS)


def downgrade():
    for table in (*AUTHORITY_TABLES, "clients"):
        op.execute(f"""
            DROP TRIGGER IF EXISTS
                myc_realtime_portal_authority_insert
            ON {table};
        """)

        op.execute(f"""
            DROP TRIGGER IF EXISTS
                myc_realtime_portal_authority_update
            ON {table};
        """)
