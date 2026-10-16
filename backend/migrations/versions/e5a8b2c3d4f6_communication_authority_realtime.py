"""Notify communication authority changes.

Revision ID: e5a8b2c3d4f6
Revises: d4f7a1b2c3e5
"""

from alembic import op

revision = "e5a8b2c3d4f6"
down_revision = "d4f7a1b2c3e5"
branch_labels = None
depends_on = None

TABLES = (
    "communication_participants",
    "communication_conversations",
)


def upgrade():
    for table in TABLES:
        op.execute(f"""
            CREATE TRIGGER myc_realtime_communication_authority
            AFTER INSERT OR UPDATE OR DELETE
            ON {table}
            FOR EACH STATEMENT
            EXECUTE FUNCTION myc_notify_resource_change(
                'communication_authority'
            );
        """)


def downgrade():
    for table in TABLES:
        op.execute(f"""
            DROP TRIGGER IF EXISTS
                myc_realtime_communication_authority
            ON {table};
        """)
