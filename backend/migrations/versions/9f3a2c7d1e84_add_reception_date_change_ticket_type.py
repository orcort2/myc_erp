"""add reception date change ticket type

Revision ID: 9f3a2c7d1e84
Revises: b0b560e714db
Create Date: 2026-09-03 00:00:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "9f3a2c7d1e84"
down_revision: Union[str, None] = "b0b560e714db"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


_PREVIOUS_TYPES = (
    "reopen_work_order",
    "manual_myc_folio",
    "linked_folio",
    "partial_close",
    "certificate_folio_block",
    "field_sheet_template_request",
    "field_sheet_reopen",
)
_CURRENT_TYPES = (*_PREVIOUS_TYPES, "reception_date_change")


def _type_constraint(types: tuple[str, ...]) -> str:
    values = ", ".join(f"'{item}'" for item in types)
    return f"type IN ({values})"


def upgrade() -> None:
    op.drop_constraint(
        "ck_operational_ticket_type", "operational_tickets", type_="check"
    )
    op.create_check_constraint(
        "ck_operational_ticket_type",
        "operational_tickets",
        _type_constraint(_CURRENT_TYPES),
    )


def downgrade() -> None:
    connection = op.get_bind()
    used = connection.scalar(
        sa.text(
            "SELECT EXISTS ("
            "SELECT 1 FROM operational_tickets "
            "WHERE type = 'reception_date_change'"
            ")"
        )
    )
    if used:
        raise RuntimeError(
            "No se puede revertir 9f3a2c7d1e84: existen tickets "
            "reception_date_change; deben preservarse sin reinterpretar ni eliminar"
        )
    op.drop_constraint(
        "ck_operational_ticket_type", "operational_tickets", type_="check"
    )
    op.create_check_constraint(
        "ck_operational_ticket_type",
        "operational_tickets",
        _type_constraint(_PREVIOUS_TYPES),
    )
