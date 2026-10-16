"""Notify resource changes for ERP live synchronization.

Revision ID: d4f7a1b2c3e5
Revises: c3e6a9b2d4f8
"""

from alembic import op

revision = "d4f7a1b2c3e5"
down_revision = "c3e6a9b2d4f8"
branch_labels = None
depends_on = None

TABLE_RESOURCES = {
    "users": "users",
    "roles": "users",
    "user_roles": "users",
    "clients": "clients",
    "quotations": "quotations",
    "service_orders": "service_orders",
    "invoices": "invoices",
    "lab_work_orders": "lab_work_orders",
}


def upgrade():
    op.execute("""
        CREATE OR REPLACE FUNCTION myc_notify_resource_change()
        RETURNS trigger
        LANGUAGE plpgsql
        AS $$
        BEGIN
            PERFORM pg_notify(
                'myc_erp_resource_changes_v1',
                json_build_object(
                    'version', 1,
                    'resource', TG_ARGV[0]
                )::text
            );

            RETURN NULL;
        END;
        $$;
    """)

    for table, resource in TABLE_RESOURCES.items():
        op.execute(f"""
            CREATE TRIGGER myc_realtime_invalidation
            AFTER INSERT OR UPDATE OR DELETE
            ON {table}
            FOR EACH STATEMENT
            EXECUTE FUNCTION myc_notify_resource_change('{resource}');
        """)


def downgrade():
    for table in TABLE_RESOURCES:
        op.execute(
            f"DROP TRIGGER IF EXISTS myc_realtime_invalidation ON {table}"
        )

    op.execute(
        "DROP FUNCTION IF EXISTS myc_notify_resource_change()"
    )
