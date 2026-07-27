"""Harden Resolution Engine security evidence.

Revision ID: e7f9a1b3c5d7
Revises: d6e8f0a2b4c5
Create Date: 2026-07-27
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "e7f9a1b3c5d7"
down_revision: str | None = "d6e8f0a2b4c5"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

BIGINT_ID = sa.BigInteger().with_variant(sa.Integer(), "sqlite")


def upgrade() -> None:
    op.add_column(
        "resolution_security_decisions",
        sa.Column("revalidation_id", BIGINT_ID),
    )
    op.add_column(
        "resolution_security_decisions",
        sa.Column("revalidation_hash", sa.String(64)),
    )
    op.create_unique_constraint(
        "uq_resolution_security_decisions_id_resolution",
        "resolution_security_decisions",
        ["id", "resolution_id"],
    )
    op.create_foreign_key(
        "fk_resolution_security_decisions_revalidation",
        "resolution_security_decisions",
        "resolution_revalidations",
        ["revalidation_id", "plan_id", "resolution_id"],
        ["id", "plan_id", "resolution_id"],
        ondelete="RESTRICT",
    )
    op.create_check_constraint(
        "ck_resolution_security_decisions_revalidation_complete",
        "resolution_security_decisions",
        "(revalidation_id IS NULL AND revalidation_hash IS NULL) "
        "OR (revalidation_id IS NOT NULL "
        "AND revalidation_hash IS NOT NULL AND plan_id IS NOT NULL)",
    )

    op.add_column(
        "resolution_executions",
        sa.Column("security_decision_id", BIGINT_ID),
    )
    op.create_foreign_key(
        "fk_resolution_executions_security_decision",
        "resolution_executions",
        "resolution_security_decisions",
        ["security_decision_id", "resolution_id"],
        ["id", "resolution_id"],
        ondelete="RESTRICT",
    )
    op.create_index(
        "ix_resolution_executions_security_decision_id",
        "resolution_executions",
        ["security_decision_id"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_resolution_executions_security_decision_id",
        table_name="resolution_executions",
    )
    op.drop_constraint(
        "fk_resolution_executions_security_decision",
        "resolution_executions",
        type_="foreignkey",
    )
    op.drop_column("resolution_executions", "security_decision_id")

    op.drop_constraint(
        "ck_resolution_security_decisions_revalidation_complete",
        "resolution_security_decisions",
        type_="check",
    )
    op.drop_constraint(
        "fk_resolution_security_decisions_revalidation",
        "resolution_security_decisions",
        type_="foreignkey",
    )
    op.drop_constraint(
        "uq_resolution_security_decisions_id_resolution",
        "resolution_security_decisions",
        type_="unique",
    )
    op.drop_column(
        "resolution_security_decisions",
        "revalidation_hash",
    )
    op.drop_column(
        "resolution_security_decisions",
        "revalidation_id",
    )
