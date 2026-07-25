from sqlalchemy import CheckConstraint, ForeignKeyConstraint

import app.models  # noqa: F401
from app.core.db import Base
from app.resolution_engine.infrastructure.persistence import (
    Resolution,
    ResolutionAuthorizationRequest,
    ResolutionPlan,
    ResolutionPlanStepDependency,
    ResolutionSecurityDecision,
)

EXPECTED_TABLES = {
    "resolutions",
    "resolution_problems",
    "resolution_context_snapshots",
    "resolution_analyses",
    "resolution_strategy_selections",
    "resolution_plans",
    "resolution_plan_steps",
    "resolution_plan_step_dependencies",
    "resolution_simulations",
    "resolution_authorization_requests",
    "resolution_authorization_decisions",
    "resolution_revalidations",
    "resolution_executions",
    "resolution_step_executions",
    "resolution_entity_references",
    "resolution_results",
    "resolution_security_decisions",
    "resolution_audit_events",
    "resolution_idempotency_records",
    "resolution_locks",
    "resolution_outbox_events",
    "resolution_evidence_references",
}


def resolution_tables():
    return {
        name: table
        for name, table in Base.metadata.tables.items()
        if name == "resolutions" or name.startswith("resolution_")
    }


def test_complete_persistence_model_is_registered_in_metadata():
    assert set(resolution_tables()) == EXPECTED_TABLES


def test_schema_is_generic_and_does_not_embed_first_use_case():
    forbidden_columns = {
        "service_order_id",
        "equipment_id",
        "invoice_id",
        "certificate_id",
        "quotation_id",
    }

    for table in resolution_tables().values():
        assert forbidden_columns.isdisjoint(table.c.keys())

    assert {"subject_type", "subject_id"}.issubset(Resolution.__table__.c.keys())


def test_resolution_engine_does_not_reference_erp_user_table():
    violations = []
    for table in resolution_tables().values():
        for constraint in table.foreign_key_constraints:
            for element in constraint.elements:
                if element.target_fullname.startswith("users."):
                    violations.append(
                        f"{table.name}.{element.parent.name}"
                    )

    assert violations == []


def test_historical_tables_do_not_support_soft_delete():
    for table in resolution_tables().values():
        assert "deleted_at" not in table.c
        assert "deleted_by" not in table.c


def test_plan_dependencies_are_relational_not_json():
    columns = ResolutionPlanStepDependency.__table__.c

    assert {"plan_id", "step_id", "depends_on_step_id"} == set(columns.keys()) - {
        "id"
    }
    assert any(
        constraint.name == "uq_resolution_plan_step_dependencies_edge"
        for constraint in ResolutionPlanStepDependency.__table__.constraints
    )


def test_authorization_references_exact_plan_and_simulation_hashes():
    constraints = [
        constraint
        for constraint in ResolutionAuthorizationRequest.__table__.constraints
        if isinstance(constraint, ForeignKeyConstraint)
    ]
    constrained_sets = {
        tuple(column.name for column in constraint.columns)
        for constraint in constraints
    }

    assert ("plan_id", "resolution_id", "plan_hash") in constrained_sets
    assert ("simulation_id", "resolution_id", "simulation_hash") in constrained_sets
    assert ("simulation_id", "plan_id", "resolution_id") in constrained_sets


def test_security_decisions_reference_exact_authorization_evidence():
    constraints = [
        constraint
        for constraint in ResolutionSecurityDecision.__table__.constraints
        if isinstance(constraint, ForeignKeyConstraint)
    ]
    constrained_sets = {
        tuple(column.name for column in constraint.columns)
        for constraint in constraints
    }

    assert ("authorization_request_id", "resolution_id") in constrained_sets
    assert ("plan_id", "resolution_id", "plan_hash") in constrained_sets
    assert ("simulation_id", "resolution_id", "simulation_hash") in constrained_sets
    assert ("simulation_id", "plan_id", "resolution_id") in constrained_sets


def test_plan_identity_and_hash_have_stable_unique_targets():
    unique_names = {
        constraint.name for constraint in ResolutionPlan.__table__.constraints
    }

    assert "uq_resolution_plans_version" in unique_names
    assert "uq_resolution_plans_id_resolution_hash" in unique_names


def test_root_has_optimistic_version_and_controlled_status():
    assert Resolution.__table__.c.version.nullable is False
    checks = {
        constraint.name: str(constraint.sqltext)
        for constraint in Resolution.__table__.constraints
        if isinstance(constraint, CheckConstraint)
    }

    assert "ck_resolutions_status" in checks
    assert "ck_resolutions_version_positive" in checks


def test_every_internal_foreign_key_has_an_explicit_deletion_policy():
    violations = []
    for table in resolution_tables().values():
        for constraint in table.constraints:
            if not isinstance(constraint, ForeignKeyConstraint):
                continue
            if constraint.ondelete != "RESTRICT":
                violations.append(
                    f"{table.name}.{constraint.name or 'unnamed'}"
                )

    assert violations == []
