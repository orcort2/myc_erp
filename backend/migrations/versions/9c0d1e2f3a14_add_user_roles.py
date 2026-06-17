"""add user roles

Revision ID: 9c0d1e2f3a14
Revises: 8b9c0d1e2f13
Create Date: 2026-06-17 14:35:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "9c0d1e2f3a14"
down_revision: Union[str, None] = "8b9c0d1e2f13"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


INITIAL_ROLES = [
    ("Administrador", "Acceso total al sistema."),
    ("Comercial", "Gestion comercial, clientes y cotizaciones."),
    ("Tecnico", "Gestion tecnica de equipos y hojas de campo."),
    ("Captura", "Captura y generacion documental."),
    ("Calidad", "Revision y aprobacion de certificados."),
    ("Finanzas", "Pagos, facturacion y liberacion financiera."),
    ("Cliente", "Acceso limitado para cliente externo."),
]


def upgrade() -> None:
    op.create_table(
        "user_roles",
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("role_id", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(["role_id"], ["roles.id"]),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("user_id", "role_id"),
    )

    # Use raw SQL for portable "insert if missing" behavior on PostgreSQL.
    for name, description in INITIAL_ROLES:
        safe_name = name.replace("'", "''")
        safe_description = description.replace("'", "''")
        op.execute(
            "INSERT INTO roles (name, description, is_active) "
            f"SELECT '{safe_name}', '{safe_description}', true "
            f"WHERE NOT EXISTS (SELECT 1 FROM roles WHERE name = '{safe_name}')"
        )

    op.execute(
        "INSERT INTO user_roles (user_id, role_id) "
        "SELECT users.id, users.role_id FROM users "
        "WHERE users.role_id IS NOT NULL "
        "ON CONFLICT DO NOTHING"
    )


def downgrade() -> None:
    op.drop_table("user_roles")
