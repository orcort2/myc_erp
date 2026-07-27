"""Add Resolution Engine Phase 6 compensation model.

Revision ID: d6e8f0a2b4c5
Revises: c5d7e9f1a3b4
Create Date: 2026-07-28
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "d6e8f0a2b4c5"
down_revision: str | None = "c5d7e9f1a3b4"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

BIGINT_ID = sa.BigInteger().with_variant(sa.Integer(), "sqlite")
JSON_DOCUMENT = sa.JSON().with_variant(
    postgresql.JSONB(astext_type=sa.Text()),
    "postgresql",
)


def upgrade() -> None:
    op.drop_constraint(
        "ck_resolutions_status",
        "resolutions",
        type_="check",
    )
    op.create_check_constraint(
        "ck_resolutions_status",
        "resolutions",
        "status IN ('draft','context_ready','analyzed','plan_ready',"
        "'simulated','pending_authorization','authorized','revalidating',"
        "'ready_for_execution','executing','completed',"
        "'partially_completed','failed','blocked','rejected','cancelled',"
        "'superseded','no_action_required','compensating','compensated',"
        "'partially_compensated','compensation_failed')",
    )

    op.create_table(
        "resolution_compensation_plans",
        sa.Column("resolution_id", BIGINT_ID, nullable=False),
        sa.Column("source_execution_id", BIGINT_ID, nullable=False),
        sa.Column("security_decision_id", BIGINT_ID, nullable=False),
        sa.Column("strategy", sa.String(32), nullable=False),
        sa.Column("reason", sa.Text(), nullable=False),
        sa.Column("plan_key", sa.String(240), nullable=False),
        sa.Column("plan_hash", sa.String(64), nullable=False),
        sa.Column("created_by_actor_id", sa.String(160), nullable=False),
        sa.Column("correlation_id", sa.String(120), nullable=False),
        sa.Column(
            "metadata",
            JSON_DOCUMENT,
            server_default=sa.text("'{}'"),
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column("id", BIGINT_ID, primary_key=True, autoincrement=True),
        sa.CheckConstraint(
            "strategy IN ('total','partial')",
            name="ck_resolution_compensation_plans_strategy",
        ),
        sa.CheckConstraint(
            "length(plan_hash) = 64",
            name="ck_resolution_compensation_plans_hash",
        ),
        sa.ForeignKeyConstraint(
            ["resolution_id"],
            ["resolutions.id"],
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["security_decision_id"],
            ["resolution_security_decisions.id"],
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["source_execution_id", "resolution_id"],
            ["resolution_executions.id", "resolution_executions.resolution_id"],
            name="fk_resolution_compensation_plans_source",
            ondelete="RESTRICT",
        ),
        sa.UniqueConstraint(
            "id",
            "resolution_id",
            name="uq_resolution_compensation_plans_id_resolution",
        ),
        sa.UniqueConstraint(
            "plan_key",
            name="uq_resolution_compensation_plans_key",
        ),
    )
    op.create_index(
        "ix_resolution_compensation_plans_source",
        "resolution_compensation_plans",
        ["source_execution_id", "id"],
    )

    op.create_table(
        "resolution_compensation_plan_steps",
        sa.Column("plan_id", BIGINT_ID, nullable=False),
        sa.Column("source_execution_id", BIGINT_ID, nullable=False),
        sa.Column("source_plan_step_id", BIGINT_ID, nullable=False),
        sa.Column("source_step_execution_id", BIGINT_ID, nullable=False),
        sa.Column("source_step_key", sa.String(160), nullable=False),
        sa.Column("sequence", sa.Integer(), nullable=False),
        sa.Column("operation_key", sa.String(200), nullable=False),
        sa.Column("owner_module", sa.String(100), nullable=False),
        sa.Column("input_payload", JSON_DOCUMENT, nullable=False),
        sa.Column(
            "dependency_source_step_ids",
            JSON_DOCUMENT,
            server_default=sa.text("'[]'"),
            nullable=False,
        ),
        sa.Column("step_hash", sa.String(64), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column("id", BIGINT_ID, primary_key=True, autoincrement=True),
        sa.CheckConstraint(
            "sequence >= 1",
            name="ck_resolution_compensation_plan_steps_sequence",
        ),
        sa.CheckConstraint(
            "length(step_hash) = 64",
            name="ck_resolution_compensation_plan_steps_hash",
        ),
        sa.ForeignKeyConstraint(
            ["plan_id"],
            ["resolution_compensation_plans.id"],
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["source_plan_step_id"],
            ["resolution_plan_steps.id"],
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["source_step_execution_id", "source_execution_id"],
            ["resolution_step_executions.id", "resolution_step_executions.execution_id"],
            name="fk_resolution_compensation_steps_source",
            ondelete="RESTRICT",
        ),
        sa.UniqueConstraint(
            "id",
            "plan_id",
            name="uq_resolution_compensation_plan_steps_id_plan",
        ),
        sa.UniqueConstraint(
            "plan_id",
            "sequence",
            name="uq_resolution_compensation_plan_steps_sequence",
        ),
        sa.UniqueConstraint(
            "source_step_execution_id",
            name="uq_resolution_compensation_source_step_once",
        ),
    )

    op.create_table(
        "resolution_compensation_executions",
        sa.Column("resolution_id", BIGINT_ID, nullable=False),
        sa.Column("plan_id", BIGINT_ID, nullable=False),
        sa.Column("source_execution_id", BIGINT_ID, nullable=False),
        sa.Column("status", sa.String(32), nullable=False),
        sa.Column("execution_key", sa.String(240), nullable=False),
        sa.Column("request_hash", sa.String(64), nullable=False),
        sa.Column("lock_token", sa.String(160), nullable=False),
        sa.Column("executed_by_actor_id", sa.String(160), nullable=False),
        sa.Column("executed_by_actor_type", sa.String(40), nullable=False),
        sa.Column("actor_source", sa.String(40), nullable=False),
        sa.Column("correlation_id", sa.String(120), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True)),
        sa.Column("outcome_payload", JSON_DOCUMENT),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column("id", BIGINT_ID, primary_key=True, autoincrement=True),
        sa.CheckConstraint(
            "status IN ('running','compensated','partially_compensated',"
            "'failed','blocked')",
            name="ck_resolution_compensation_executions_status",
        ),
        sa.ForeignKeyConstraint(
            ["resolution_id"],
            ["resolutions.id"],
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["source_execution_id"],
            ["resolution_executions.id"],
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["plan_id", "resolution_id"],
            ["resolution_compensation_plans.id", "resolution_compensation_plans.resolution_id"],
            name="fk_resolution_compensation_executions_plan",
            ondelete="RESTRICT",
        ),
        sa.UniqueConstraint(
            "id",
            "resolution_id",
            name="uq_resolution_compensation_executions_id_resolution",
        ),
        sa.UniqueConstraint(
            "id",
            "plan_id",
            name="uq_resolution_compensation_executions_id_plan",
        ),
        sa.UniqueConstraint(
            "plan_id",
            name="uq_resolution_compensation_executions_plan",
        ),
        sa.UniqueConstraint(
            "execution_key",
            name="uq_resolution_compensation_executions_key",
        ),
    )
    op.create_index(
        "ix_resolution_compensation_executions_status",
        "resolution_compensation_executions",
        ["status", "id"],
    )

    op.create_table(
        "resolution_compensation_step_executions",
        sa.Column("execution_id", BIGINT_ID, nullable=False),
        sa.Column("plan_id", BIGINT_ID, nullable=False),
        sa.Column("plan_step_id", BIGINT_ID, nullable=False),
        sa.Column("source_step_execution_id", BIGINT_ID, nullable=False),
        sa.Column("status", sa.String(24), server_default="pending", nullable=False),
        sa.Column("step_execution_key", sa.String(240), nullable=False),
        sa.Column("request_hash", sa.String(64)),
        sa.Column(
            "request_payload",
            JSON_DOCUMENT,
            server_default=sa.text("'{}'"),
            nullable=False,
        ),
        sa.Column("result_payload", JSON_DOCUMENT),
        sa.Column("domain_transaction_reference", sa.String(240)),
        sa.Column("error_code", sa.String(160)),
        sa.Column("error_message", sa.Text()),
        sa.Column("started_at", sa.DateTime(timezone=True)),
        sa.Column("completed_at", sa.DateTime(timezone=True)),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column("id", BIGINT_ID, primary_key=True, autoincrement=True),
        sa.CheckConstraint(
            "status IN ('pending','running','compensated','failed','blocked')",
            name="ck_resolution_compensation_step_executions_status",
        ),
        sa.ForeignKeyConstraint(
            ["source_step_execution_id"],
            ["resolution_step_executions.id"],
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["execution_id", "plan_id"],
            ["resolution_compensation_executions.id", "resolution_compensation_executions.plan_id"],
            name="fk_resolution_compensation_step_execution",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["plan_step_id", "plan_id"],
            ["resolution_compensation_plan_steps.id", "resolution_compensation_plan_steps.plan_id"],
            name="fk_resolution_compensation_step_plan",
            ondelete="RESTRICT",
        ),
        sa.UniqueConstraint(
            "execution_id",
            "plan_step_id",
            name="uq_resolution_compensation_step_executions_step",
        ),
        sa.UniqueConstraint(
            "step_execution_key",
            name="uq_resolution_compensation_step_executions_key",
        ),
    )
    op.create_index(
        "ix_resolution_compensation_steps_execution_status",
        "resolution_compensation_step_executions",
        ["execution_id", "status"],
    )

    for table_name in (
        "resolution_compensation_plans",
        "resolution_compensation_plan_steps",
    ):
        op.execute(
            f"""
            CREATE TRIGGER trg_{table_name}_immutable
            BEFORE UPDATE OR DELETE ON {table_name}
            FOR EACH ROW EXECUTE FUNCTION resolution_engine_prevent_mutation()
            """
        )
    for table_name in (
        "resolution_compensation_executions",
        "resolution_compensation_step_executions",
    ):
        op.execute(
            f"""
            CREATE TRIGGER trg_{table_name}_prevent_delete
            BEFORE DELETE ON {table_name}
            FOR EACH ROW EXECUTE FUNCTION resolution_engine_prevent_delete()
            """
        )


def downgrade() -> None:
    for table_name in (
        "resolution_compensation_step_executions",
        "resolution_compensation_executions",
    ):
        op.execute(
            f"DROP TRIGGER IF EXISTS trg_{table_name}_prevent_delete "
            f"ON {table_name}"
        )
    for table_name in (
        "resolution_compensation_plan_steps",
        "resolution_compensation_plans",
    ):
        op.execute(
            f"DROP TRIGGER IF EXISTS trg_{table_name}_immutable "
            f"ON {table_name}"
        )
    op.drop_index(
        "ix_resolution_compensation_steps_execution_status",
        table_name="resolution_compensation_step_executions",
    )
    op.drop_table("resolution_compensation_step_executions")
    op.drop_index(
        "ix_resolution_compensation_executions_status",
        table_name="resolution_compensation_executions",
    )
    op.drop_table("resolution_compensation_executions")
    op.drop_table("resolution_compensation_plan_steps")
    op.drop_index(
        "ix_resolution_compensation_plans_source",
        table_name="resolution_compensation_plans",
    )
    op.drop_table("resolution_compensation_plans")
    op.drop_constraint(
        "ck_resolutions_status",
        "resolutions",
        type_="check",
    )
    op.create_check_constraint(
        "ck_resolutions_status",
        "resolutions",
        "status IN ('draft','context_ready','analyzed','plan_ready',"
        "'simulated','pending_authorization','authorized','revalidating',"
        "'ready_for_execution','executing','completed',"
        "'partially_completed','failed','blocked','rejected','cancelled',"
        "'superseded','no_action_required')",
    )
