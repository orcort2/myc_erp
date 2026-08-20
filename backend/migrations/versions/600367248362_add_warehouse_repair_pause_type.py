"""add warehouse repair pause type

Revision ID: 600367248362
Revises: f3a8c1d7e5b0
Create Date: 2026-08-20 13:20:03.191399
"""

from typing import Sequence, Union

from alembic import op


revision: str = "600367248362"
down_revision: Union[str, None] = "f3a8c1d7e5b0"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


OLD_PAUSE_TYPE_CHECK = (
    "pause_type IN ("
    "'spare_part',"
    "'authorization',"
    "'client_decision',"
    "'administrative_investigation'"
    ")"
)

NEW_PAUSE_TYPE_CHECK = (
    "pause_type IN ("
    "'spare_part',"
    "'authorization',"
    "'client_decision',"
    "'administrative_investigation',"
    "'warehouse'"
    ")"
)


def upgrade() -> None:
    op.drop_constraint(
        "ck_repair_pause_type",
        "repair_pauses",
        type_="check",
    )

    op.create_check_constraint(
        "ck_repair_pause_type",
        "repair_pauses",
        NEW_PAUSE_TYPE_CHECK,
    )


def downgrade() -> None:
    op.drop_constraint(
        "ck_repair_pause_type",
        "repair_pauses",
        type_="check",
    )

    op.create_check_constraint(
        "ck_repair_pause_type",
        "repair_pauses",
        OLD_PAUSE_TYPE_CHECK,
    )