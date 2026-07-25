"""resolution engine phase 3 security

Revision ID: b4c6d8e0f2a3
Revises: 9d3e5f7a1b2c
Create Date: 2026-07-24 23:30:00.000000
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "b4c6d8e0f2a3"
down_revision: Union[str, None] = "9d3e5f7a1b2c"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

ACTOR_COLUMNS = (
    (
        "resolutions",
        "requested_by_user_id",
        "requested_by_actor_id",
        "resolutions_requested_by_user_id_fkey",
    ),
    (
        "resolutions",
        "assigned_to_user_id",
        "assigned_to_actor_id",
        "resolutions_assigned_to_user_id_fkey",
    ),
    (
        "resolution_problems",
        "reported_by_user_id",
        "reported_by_actor_id",
        "resolution_problems_reported_by_user_id_fkey",
    ),
    (
        "resolution_context_snapshots",
        "captured_by_user_id",
        "captured_by_actor_id",
        "resolution_context_snapshots_captured_by_user_id_fkey",
    ),
    (
        "resolution_strategy_selections",
        "selected_by_user_id",
        "selected_by_actor_id",
        "resolution_strategy_selections_selected_by_user_id_fkey",
    ),
    (
        "resolution_plans",
        "created_by_user_id",
        "created_by_actor_id",
        "resolution_plans_created_by_user_id_fkey",
    ),
    (
        "resolution_authorization_requests",
        "requested_by_user_id",
        "requested_by_actor_id",
        "resolution_authorization_requests_requested_by_user_id_fkey",
    ),
    (
        "resolution_authorization_decisions",
        "approver_user_id",
        "approver_actor_id",
        "resolution_authorization_decisions_approver_user_id_fkey",
    ),
    (
        "resolution_executions",
        "executed_by_user_id",
        "executed_by_actor_id",
        "resolution_executions_executed_by_user_id_fkey",
    ),
    (
        "resolution_results",
        "completed_by_user_id",
        "completed_by_actor_id",
        "resolution_results_completed_by_user_id_fkey",
    ),
    (
        "resolution_evidence_references",
        "uploaded_by_user_id",
        "uploaded_by_actor_id",
        "resolution_evidence_references_uploaded_by_user_id_fkey",
    ),
)


def _to_actor_columns() -> None:
    op.drop_index(
        "ix_resolutions_requested_by_user_id",
        table_name="resolutions",
    )
    op.drop_index(
        "ix_resolutions_assigned_to_user_id",
        table_name="resolutions",
    )
    op.drop_index(
        "ix_resolution_authorization_decisions_request_approver",
        table_name="resolution_authorization_decisions",
    )
    for table, old_name, new_name, constraint_name in ACTOR_COLUMNS:
        op.drop_constraint(constraint_name, table, type_="foreignkey")
        op.alter_column(
            table,
            old_name,
            new_column_name=new_name,
            type_=sa.String(length=160),
            postgresql_using=f"{old_name}::text",
            existing_nullable=(table != "resolution_authorization_decisions"),
        )

    op.alter_column(
        "resolutions",
        "assigned_role",
        new_column_name="assigned_function",
        existing_type=sa.String(length=100),
    )
    op.alter_column(
        "resolution_audit_events",
        "actor_role",
        new_column_name="actor_function",
        existing_type=sa.String(length=100),
    )
    op.alter_column(
        "resolution_authorization_decisions",
        "approver_role",
        new_column_name="approver_function",
        existing_type=sa.String(length=100),
    )
    op.add_column(
        "resolution_authorization_requests",
        sa.Column(
            "requester_actor_snapshot",
            sa.JSON().with_variant(postgresql.JSONB(), "postgresql"),
            server_default=sa.text("'{}'"),
            nullable=False,
        ),
    )
    op.execute(
        """
        UPDATE resolution_authorization_requests
           SET requested_by_actor_id = 'legacy:unknown'
         WHERE requested_by_actor_id IS NULL
        """
    )
    op.alter_column(
        "resolution_authorization_requests",
        "requested_by_actor_id",
        nullable=False,
        existing_type=sa.String(length=160),
    )
    op.add_column(
        "resolution_authorization_decisions",
        sa.Column(
            "approver_actor_type",
            sa.String(length=40),
            server_default="human",
            nullable=False,
        ),
    )
    op.add_column(
        "resolution_authorization_decisions",
        sa.Column(
            "actor_snapshot",
            sa.JSON().with_variant(postgresql.JSONB(), "postgresql"),
            server_default=sa.text("'{}'"),
            nullable=False,
        ),
    )
    op.create_index(
        "ix_resolutions_requested_by_actor_id",
        "resolutions",
        ["requested_by_actor_id"],
    )
    op.create_index(
        "ix_resolutions_assigned_to_actor_id",
        "resolutions",
        ["assigned_to_actor_id"],
    )
    op.create_index(
        "ix_resolution_authorization_decisions_request_approver",
        "resolution_authorization_decisions",
        ["authorization_request_id", "approver_actor_id"],
    )


def _create_security_decisions() -> None:
    op.create_table(
        "resolution_security_decisions",
        sa.Column(
            "resolution_id",
            sa.BigInteger().with_variant(sa.Integer(), "sqlite"),
            nullable=True,
        ),
        sa.Column(
            "authorization_request_id",
            sa.BigInteger().with_variant(sa.Integer(), "sqlite"),
            nullable=True,
        ),
        sa.Column(
            "plan_id",
            sa.BigInteger().with_variant(sa.Integer(), "sqlite"),
            nullable=True,
        ),
        sa.Column("plan_version", sa.Integer(), nullable=True),
        sa.Column("plan_hash", sa.String(length=64), nullable=True),
        sa.Column(
            "simulation_id",
            sa.BigInteger().with_variant(sa.Integer(), "sqlite"),
            nullable=True,
        ),
        sa.Column("simulation_hash", sa.String(length=64), nullable=True),
        sa.Column("actor_id", sa.String(length=160), nullable=False),
        sa.Column("actor_type", sa.String(length=40), nullable=False),
        sa.Column("organization_id", sa.String(length=160), nullable=False),
        sa.Column("action", sa.String(length=200), nullable=False),
        sa.Column("resource_type", sa.String(length=100), nullable=False),
        sa.Column("resource_id", sa.String(length=200), nullable=False),
        sa.Column("outcome", sa.String(length=20), nullable=False),
        sa.Column(
            "policy_results",
            sa.JSON().with_variant(postgresql.JSONB(), "postgresql"),
            nullable=False,
        ),
        sa.Column(
            "required_permissions",
            sa.JSON().with_variant(postgresql.JSONB(), "postgresql"),
            nullable=False,
        ),
        sa.Column(
            "reason_codes",
            sa.JSON().with_variant(postgresql.JSONB(), "postgresql"),
            nullable=False,
        ),
        sa.Column(
            "actor_snapshot",
            sa.JSON().with_variant(postgresql.JSONB(), "postgresql"),
            nullable=False,
        ),
        sa.Column(
            "authentication_snapshot",
            sa.JSON().with_variant(postgresql.JSONB(), "postgresql"),
            nullable=False,
        ),
        sa.Column(
            "context_snapshot",
            sa.JSON().with_variant(postgresql.JSONB(), "postgresql"),
            nullable=False,
        ),
        sa.Column("evaluated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("correlation_id", sa.String(length=120), nullable=False),
        sa.Column("evidence_hash", sa.String(length=64), nullable=False),
        sa.Column(
            "id",
            sa.BigInteger().with_variant(sa.Integer(), "sqlite"),
            autoincrement=True,
            nullable=False,
        ),
        sa.CheckConstraint(
            "outcome IN ('allowed','denied')",
            name="ck_resolution_security_decisions_outcome",
        ),
        sa.CheckConstraint(
            "actor_type IN ('human','service','worker','integration',"
            "'mobile_app','system')",
            name="ck_resolution_security_decisions_actor_type",
        ),
        sa.CheckConstraint(
            "length(evidence_hash) = 64",
            name="ck_resolution_security_decisions_evidence_hash",
        ),
        sa.CheckConstraint(
            "(plan_id IS NULL AND plan_version IS NULL AND plan_hash IS NULL) "
            "OR (plan_id IS NOT NULL AND plan_version IS NOT NULL "
            "AND plan_hash IS NOT NULL)",
            name="ck_resolution_security_decisions_plan_complete",
        ),
        sa.CheckConstraint(
            "(simulation_id IS NULL AND simulation_hash IS NULL) "
            "OR (simulation_id IS NOT NULL AND simulation_hash IS NOT NULL "
            "AND plan_id IS NOT NULL)",
            name="ck_resolution_security_decisions_simulation_complete",
        ),
        sa.ForeignKeyConstraint(
            ["authorization_request_id", "resolution_id"],
            [
                "resolution_authorization_requests.id",
                "resolution_authorization_requests.resolution_id",
            ],
            name="fk_resolution_security_decisions_authorization",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["plan_id", "resolution_id", "plan_hash"],
            [
                "resolution_plans.id",
                "resolution_plans.resolution_id",
                "resolution_plans.plan_hash",
            ],
            name="fk_resolution_security_decisions_exact_plan",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["resolution_id"],
            ["resolutions.id"],
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["simulation_id", "plan_id", "resolution_id"],
            [
                "resolution_simulations.id",
                "resolution_simulations.plan_id",
                "resolution_simulations.resolution_id",
            ],
            name="fk_resolution_security_decisions_exact_simulation",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["simulation_id", "resolution_id", "simulation_hash"],
            [
                "resolution_simulations.id",
                "resolution_simulations.resolution_id",
                "resolution_simulations.simulation_hash",
            ],
            name="fk_resolution_security_decisions_simulation_hash",
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_resolution_security_decisions_actor_time",
        "resolution_security_decisions",
        ["actor_id", "evaluated_at"],
    )
    op.create_index(
        "ix_resolution_security_decisions_correlation_id",
        "resolution_security_decisions",
        ["correlation_id"],
    )
    op.create_index(
        "ix_resolution_security_decisions_outcome",
        "resolution_security_decisions",
        ["outcome"],
    )
    op.create_index(
        "ix_resolution_security_decisions_resolution_time",
        "resolution_security_decisions",
        ["resolution_id", "evaluated_at"],
    )
    op.execute(
        """
        CREATE TRIGGER trg_resolution_security_decisions_immutable
        BEFORE UPDATE OR DELETE ON resolution_security_decisions
        FOR EACH ROW EXECUTE FUNCTION resolution_engine_prevent_mutation()
        """
    )


def upgrade() -> None:
    _to_actor_columns()
    _create_security_decisions()


def downgrade() -> None:
    op.execute(
        "DROP TRIGGER IF EXISTS "
        "trg_resolution_security_decisions_immutable "
        "ON resolution_security_decisions"
    )
    op.drop_table("resolution_security_decisions")
    op.drop_index(
        "ix_resolution_authorization_decisions_request_approver",
        table_name="resolution_authorization_decisions",
    )
    op.drop_index(
        "ix_resolutions_assigned_to_actor_id",
        table_name="resolutions",
    )
    op.drop_index(
        "ix_resolutions_requested_by_actor_id",
        table_name="resolutions",
    )
    op.drop_column("resolution_authorization_decisions", "actor_snapshot")
    op.drop_column(
        "resolution_authorization_decisions",
        "approver_actor_type",
    )
    op.drop_column(
        "resolution_authorization_requests",
        "requester_actor_snapshot",
    )
    op.alter_column(
        "resolution_authorization_decisions",
        "approver_function",
        new_column_name="approver_role",
        existing_type=sa.String(length=100),
    )
    op.alter_column(
        "resolution_audit_events",
        "actor_function",
        new_column_name="actor_role",
        existing_type=sa.String(length=100),
    )
    op.alter_column(
        "resolutions",
        "assigned_function",
        new_column_name="assigned_role",
        existing_type=sa.String(length=100),
    )
    for table, old_name, new_name, constraint_name in reversed(ACTOR_COLUMNS):
        if table == "resolution_authorization_requests":
            op.alter_column(
                table,
                new_name,
                nullable=True,
                existing_type=sa.String(length=160),
            )
        op.alter_column(
            table,
            new_name,
            new_column_name=old_name,
            type_=sa.Integer(),
            postgresql_using=(
                f"NULLIF(regexp_replace({new_name}, '[^0-9]', '', 'g'), '')"
                "::integer"
            ),
            existing_nullable=(table != "resolution_authorization_decisions"),
        )
        op.create_foreign_key(
            constraint_name,
            table,
            "users",
            [old_name],
            ["id"],
            ondelete="RESTRICT",
        )
    op.create_index(
        "ix_resolution_authorization_decisions_request_approver",
        "resolution_authorization_decisions",
        ["authorization_request_id", "approver_user_id"],
    )
    op.create_index(
        "ix_resolutions_assigned_to_user_id",
        "resolutions",
        ["assigned_to_user_id"],
    )
    op.create_index(
        "ix_resolutions_requested_by_user_id",
        "resolutions",
        ["requested_by_user_id"],
    )
