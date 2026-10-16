"""Contrato SQL de la migración de autoridad del Portal del Cliente."""

import importlib.util
import re
from pathlib import Path
from unittest.mock import patch


MIGRATION_PATH = (
    Path(__file__).resolve().parents[1]
    / "migrations"
    / "versions"
    / "f6b9c3d4e5a7_portal_realtime_authority.py"
)

TABLES = {
    "client_portal_memberships": "UPDATE OF status, client_id, user_id",
    "client_portal_membership_roles": "UPDATE",
    "client_portal_role_permissions": "UPDATE",
    "client_portal_roles": "UPDATE OF is_active",
    "client_portal_permissions": "UPDATE OF is_active",
    "client_portals": "UPDATE OF is_enabled, is_active, client_id",
    "clients": "UPDATE OF is_active",
}

TRIGGERS = {
    "myc_realtime_portal_authority_insert",
    "myc_realtime_portal_authority_update",
}


def load_migration():
    spec = importlib.util.spec_from_file_location(
        "portal_authority_migration_test",
        MIGRATION_PATH,
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def normalize(sql):
    return " ".join(str(sql).split())


def capture_sql(operation):
    migration = load_migration()

    with patch.object(migration.op, "execute") as execute:
        getattr(migration, operation)()

    return [normalize(call.args[0]) for call in execute.call_args_list]


def extract_trigger(sql, operation):
    match = re.search(
        rf"{operation} TRIGGER(?: IF EXISTS)? "
        rf"(\w+) (?:AFTER .*? ON |ON )(\w+)",
        sql,
    )
    assert match is not None, sql
    return match.group(1), match.group(2)


def test_upgrade_creates_exactly_two_triggers_per_table():
    statements = capture_sql("upgrade")

    assert len(statements) == 14

    actual = {
        extract_trigger(sql, "CREATE")
        for sql in statements
    }

    expected = {
        (trigger, table)
        for table in TABLES
        for trigger in TRIGGERS
    }

    assert actual == expected
    assert len(actual) == len(statements)

    for sql in statements:
        assert (
            "EXECUTE FUNCTION "
            "myc_notify_resource_change( 'portal_authority' )"
        ) in sql


def test_update_triggers_use_expected_columns():
    statements = capture_sql("upgrade")

    for table, update_clause in TABLES.items():
        matches = [
            sql
            for sql in statements
            if (
                "CREATE TRIGGER "
                "myc_realtime_portal_authority_update"
            ) in sql
            and f"ON {table} " in sql
        ]

        assert len(matches) == 1
        assert f"AFTER {update_clause} ON {table}" in matches[0]


def test_insert_delete_triggers_cover_both_operations():
    statements = capture_sql("upgrade")

    for table in TABLES:
        matches = [
            sql
            for sql in statements
            if (
                "CREATE TRIGGER "
                "myc_realtime_portal_authority_insert"
            ) in sql
            and f"ON {table} " in sql
        ]

        assert len(matches) == 1
        assert f"AFTER INSERT OR DELETE ON {table}" in matches[0]


def test_downgrade_removes_exactly_created_triggers():
    created = {
        extract_trigger(sql, "CREATE")
        for sql in capture_sql("upgrade")
    }

    dropped = {
        extract_trigger(sql, "DROP")
        for sql in capture_sql("downgrade")
    }

    assert created == dropped
    assert len(dropped) == 14


def test_migration_revision_chain():
    migration = load_migration()

    assert migration.revision == "f6b9c3d4e5a7"
    assert migration.down_revision == "e5a8b2c3d4f6"
