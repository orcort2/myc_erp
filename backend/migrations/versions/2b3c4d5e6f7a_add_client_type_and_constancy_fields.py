"""add client type and constancy fields

Revision ID: 2b3c4d5e6f7a
Revises: 1a2c3e4f5a6b
Create Date: 2026-07-07 10:45:00.000000
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "2b3c4d5e6f7a"
down_revision: Union[str, None] = "1a2c3e4f5a6b"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("clients", sa.Column("client_type", sa.String(length=30), nullable=True))
    op.add_column("clients", sa.Column("curp", sa.String(length=18), nullable=True))
    op.add_column("clients", sa.Column("first_name", sa.String(length=120), nullable=True))
    op.add_column("clients", sa.Column("first_last_name", sa.String(length=120), nullable=True))
    op.add_column("clients", sa.Column("second_last_name", sa.String(length=120), nullable=True))
    op.add_column("clients", sa.Column("street_type", sa.String(length=80), nullable=True))
    op.add_column("clients", sa.Column("locality", sa.String(length=180), nullable=True))
    op.add_column("clients", sa.Column("municipality", sa.String(length=180), nullable=True))
    op.execute("UPDATE clients SET client_type = 'persona_moral' WHERE client_type IS NULL")
    op.execute("UPDATE clients SET municipality = COALESCE(municipality, city)")
    op.alter_column("clients", "client_type", nullable=False, server_default="persona_moral")
    op.create_index(op.f('ix_clients_client_type'), "clients", ["client_type"], unique=False)
    op.create_index(op.f('ix_clients_curp'), "clients", ["curp"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_clients_curp'), table_name="clients")
    op.drop_index(op.f('ix_clients_client_type'), table_name="clients")
    op.drop_column("clients", "municipality")
    op.drop_column("clients", "locality")
    op.drop_column("clients", "street_type")
    op.drop_column("clients", "second_last_name")
    op.drop_column("clients", "first_last_name")
    op.drop_column("clients", "first_name")
    op.drop_column("clients", "curp")
    op.drop_column("clients", "client_type")
