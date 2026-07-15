"""optimize SAT catalog search and internal metadata

Revision ID: f8a9b0c1d2e3
Revises: f6a7b8c9d0e1
Create Date: 2026-07-14 14:00:00.000000
"""

from alembic import op
import sqlalchemy as sa


revision = "f8a9b0c1d2e3"
down_revision = "f6a7b8c9d0e1"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("sat_catalog_records", sa.Column("normalized_code", sa.String(length=120), server_default="", nullable=False))
    op.add_column("sat_catalog_records", sa.Column("normalized_name", sa.String(length=600), server_default="", nullable=False))
    op.add_column("sat_catalog_records", sa.Column("search_text", sa.Text(), server_default="", nullable=False))
    op.execute("""
        UPDATE sat_catalog_records
        SET normalized_code = translate(lower(code), 'áéíóúüñ', 'aeiouun'),
            normalized_name = translate(lower(coalesce(name, '')), 'áéíóúüñ', 'aeiouun'),
            search_text = translate(lower(concat_ws(' ', code, name)), 'áéíóúüñ', 'aeiouun')
    """)
    op.create_index(op.f("ix_sat_catalog_records_normalized_code"), "sat_catalog_records", ["normalized_code"], unique=False)
    op.create_index(op.f("ix_sat_catalog_records_normalized_name"), "sat_catalog_records", ["normalized_name"], unique=False)
    op.create_index("ix_sat_catalog_records_version_validity", "sat_catalog_records", ["catalog_version_id", "is_active", "valid_from", "valid_until"], unique=False)
    op.create_table(
        "sat_catalog_favorites",
        sa.Column("catalog_record_id", sa.Integer(), nullable=False),
        sa.Column("created_by_id", sa.Integer(), nullable=False),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["catalog_record_id"], ["sat_catalog_records.id"]),
        sa.ForeignKeyConstraint(["created_by_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("catalog_record_id", "created_by_id", name="uq_sat_catalog_favorite_user_record"),
    )
    op.create_index(op.f("ix_sat_catalog_favorites_id"), "sat_catalog_favorites", ["id"], unique=False)
    op.create_index(op.f("ix_sat_catalog_favorites_catalog_record_id"), "sat_catalog_favorites", ["catalog_record_id"], unique=False)
    op.create_index(op.f("ix_sat_catalog_favorites_created_by_id"), "sat_catalog_favorites", ["created_by_id"], unique=False)
    op.create_table(
        "sat_catalog_aliases",
        sa.Column("catalog_record_id", sa.Integer(), nullable=False),
        sa.Column("alias", sa.String(length=500), nullable=False),
        sa.Column("normalized_alias", sa.String(length=600), nullable=False),
        sa.Column("created_by_id", sa.Integer(), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["catalog_record_id"], ["sat_catalog_records.id"]),
        sa.ForeignKeyConstraint(["created_by_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("catalog_record_id", "normalized_alias", name="uq_sat_catalog_alias_record_normalized"),
    )
    op.create_index(op.f("ix_sat_catalog_aliases_id"), "sat_catalog_aliases", ["id"], unique=False)
    op.create_index(op.f("ix_sat_catalog_aliases_catalog_record_id"), "sat_catalog_aliases", ["catalog_record_id"], unique=False)
    op.create_index(op.f("ix_sat_catalog_aliases_normalized_alias"), "sat_catalog_aliases", ["normalized_alias"], unique=False)
    op.create_index(op.f("ix_sat_catalog_aliases_created_by_id"), "sat_catalog_aliases", ["created_by_id"], unique=False)
    op.create_index(op.f("ix_sat_catalog_aliases_is_active"), "sat_catalog_aliases", ["is_active"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_sat_catalog_aliases_is_active"), table_name="sat_catalog_aliases")
    op.drop_index(op.f("ix_sat_catalog_aliases_created_by_id"), table_name="sat_catalog_aliases")
    op.drop_index(op.f("ix_sat_catalog_aliases_normalized_alias"), table_name="sat_catalog_aliases")
    op.drop_index(op.f("ix_sat_catalog_aliases_catalog_record_id"), table_name="sat_catalog_aliases")
    op.drop_index(op.f("ix_sat_catalog_aliases_id"), table_name="sat_catalog_aliases")
    op.drop_table("sat_catalog_aliases")
    op.drop_index(op.f("ix_sat_catalog_favorites_created_by_id"), table_name="sat_catalog_favorites")
    op.drop_index(op.f("ix_sat_catalog_favorites_catalog_record_id"), table_name="sat_catalog_favorites")
    op.drop_index(op.f("ix_sat_catalog_favorites_id"), table_name="sat_catalog_favorites")
    op.drop_table("sat_catalog_favorites")
    op.drop_index("ix_sat_catalog_records_version_validity", table_name="sat_catalog_records")
    op.drop_index(op.f("ix_sat_catalog_records_normalized_name"), table_name="sat_catalog_records")
    op.drop_index(op.f("ix_sat_catalog_records_normalized_code"), table_name="sat_catalog_records")
    op.drop_column("sat_catalog_records", "search_text")
    op.drop_column("sat_catalog_records", "normalized_name")
    op.drop_column("sat_catalog_records", "normalized_code")
