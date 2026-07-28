"""Bind security decisions to canonical operations.

Revision ID: f8a0b2c4d6e8
Revises: fabc2cd495ef
Create Date: 2026-07-28
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "f8a0b2c4d6e8"
down_revision: str | None = "fabc2cd495ef"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

BIGINT_ID = sa.BigInteger().with_variant(sa.Integer(), "sqlite")
JSON_DOCUMENT = sa.JSON().with_variant(
    postgresql.JSONB(astext_type=sa.Text()),
    "postgresql",
)


def upgrade() -> None:
    op.add_column(
        "resolution_security_decisions",
        sa.Column("use_mode", sa.String(32)),
    )
    op.add_column(
        "resolution_security_decisions",
        sa.Column("operation_id", sa.String(240)),
    )
    op.add_column(
        "resolution_security_decisions",
        sa.Column("operation_hash", sa.String(64)),
    )
    op.add_column(
        "resolution_security_decisions",
        sa.Column("operation_payload", JSON_DOCUMENT),
    )
    empty_json = (
        "CAST('{}' AS JSONB)"
        if op.get_bind().dialect.name == "postgresql"
        else "'{}'"
    )
    op.execute(
        sa.text(
            "UPDATE resolution_security_decisions "
            "SET use_mode = CASE "
            "WHEN action = 'resolution.audit.inspect' "
            "THEN 'reusable_read' ELSE 'single_operation' END, "
            "operation_id = 'legacy-decision:' || id, "
            "operation_hash = evidence_hash, "
            f"operation_payload = {empty_json}"
        )
    )
    for column in (
        "use_mode",
        "operation_id",
        "operation_hash",
        "operation_payload",
    ):
        op.alter_column(
            "resolution_security_decisions",
            column,
            nullable=False,
        )
    op.create_check_constraint(
        "ck_resolution_security_decisions_use_mode",
        "resolution_security_decisions",
        "use_mode IN ('single_operation','reusable_read')",
    )
    op.create_check_constraint(
        "ck_resolution_security_decisions_operation_hash",
        "resolution_security_decisions",
        "length(operation_hash) = 64",
    )

    op.create_table(
        "resolution_security_decision_uses",
        sa.Column("security_decision_id", BIGINT_ID, nullable=False),
        sa.Column("resolution_id", BIGINT_ID),
        sa.Column("organization_id", sa.String(160), nullable=False),
        sa.Column("action", sa.String(200), nullable=False),
        sa.Column("operation_id", sa.String(240), nullable=False),
        sa.Column("operation_hash", sa.String(64), nullable=False),
        sa.Column("operation_context", JSON_DOCUMENT, nullable=False),
        sa.Column(
            "id",
            BIGINT_ID,
            autoincrement=True,
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "length(operation_hash) = 64",
            name="ck_resolution_security_decision_uses_hash",
        ),
        sa.ForeignKeyConstraint(
            ["resolution_id"],
            ["resolutions.id"],
            name="fk_resolution_security_decision_uses_resolution_id",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["security_decision_id"],
            ["resolution_security_decisions.id"],
            name="fk_resolution_security_decision_uses_decision_id",
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "security_decision_id",
            name="uq_resolution_security_decision_uses_decision",
        ),
        sa.UniqueConstraint(
            "organization_id",
            "action",
            "operation_id",
            name="uq_resolution_security_decision_uses_operation",
        ),
    )
    op.create_index(
        "ix_resolution_security_decision_uses_resolution",
        "resolution_security_decision_uses",
        ["resolution_id", "created_at"],
    )
    if op.get_bind().dialect.name == "postgresql":
        op.execute(
            """
            CREATE TRIGGER trg_resolution_security_decision_uses_immutable
            BEFORE UPDATE OR DELETE
            ON resolution_security_decision_uses
            FOR EACH ROW
            EXECUTE FUNCTION resolution_engine_prevent_mutation()
            """
        )

    op.add_column(
        "resolution_outbox_events",
        sa.Column("publication_operation_id", sa.String(240)),
    )
    op.create_index(
        "ix_resolution_outbox_events_publication_operation",
        "resolution_outbox_events",
        ["publication_operation_id"],
    )


def downgrade() -> None:
    if op.get_bind().dialect.name == "postgresql":
        op.execute(
            "DROP TRIGGER IF EXISTS "
            "trg_resolution_security_decision_uses_immutable "
            "ON resolution_security_decision_uses"
        )
    op.drop_index(
        "ix_resolution_outbox_events_publication_operation",
        table_name="resolution_outbox_events",
    )
    op.drop_column(
        "resolution_outbox_events",
        "publication_operation_id",
    )

    op.drop_index(
        "ix_resolution_security_decision_uses_resolution",
        table_name="resolution_security_decision_uses",
    )
    op.drop_table("resolution_security_decision_uses")

    op.drop_constraint(
        "ck_resolution_security_decisions_operation_hash",
        "resolution_security_decisions",
        type_="check",
    )
    op.drop_constraint(
        "ck_resolution_security_decisions_use_mode",
        "resolution_security_decisions",
        type_="check",
    )
    for column in (
        "operation_payload",
        "operation_hash",
        "operation_id",
        "use_mode",
    ):
        op.drop_column("resolution_security_decisions", column)
