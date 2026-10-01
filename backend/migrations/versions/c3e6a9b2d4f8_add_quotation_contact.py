"""add quotations.contact_id (main contact of a quotation, EMAIL-3)

Nullable for historical quotations. ON DELETE SET NULL: removing a contact
never removes the quotation.
"""

from alembic import op
import sqlalchemy as sa

revision = "c3e6a9b2d4f8"
down_revision = "b2d5f8a1c3e7"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("quotations") as batch:
        batch.add_column(sa.Column("contact_id", sa.Integer(), nullable=True))
        batch.create_foreign_key(
            "fk_quotations_contact_id_client_contacts",
            "client_contacts",
            ["contact_id"],
            ["id"],
            ondelete="SET NULL",
        )
        batch.create_index("ix_quotations_contact_id", ["contact_id"], unique=False)


def downgrade() -> None:
    with op.batch_alter_table("quotations") as batch:
        batch.drop_index("ix_quotations_contact_id")
        batch.drop_constraint("fk_quotations_contact_id_client_contacts", type_="foreignkey")
        batch.drop_column("contact_id")
