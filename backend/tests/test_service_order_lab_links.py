"""Historical link invariants, HTTP authorization and real PostgreSQL races."""

import os
from concurrent.futures import ThreadPoolExecutor
from datetime import date, datetime, timezone
from threading import Barrier
from types import SimpleNamespace
from uuid import uuid4

import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, delete, event, func, insert, select, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

import app.models  # noqa: F401
from app.core.db import Base, get_db
from app.core.security import create_access_token
from app.main import app
from app.models.audit_log import AuditLog
from app.models.client import Client
from app.models.lab_work_order import LabWorkOrder, LabWorkOrderEquipment
from app.models.service_order import ServiceOrder
from app.models.service_order_lab_link import ServiceOrderLabLink
from app.models.user import Role, User
from app.security.api_access import AccessType, assert_all_routes_classified, classify_operation
from app.services import service_order_lab_links as service


def seed(db):
    actors = {}
    for key, role_name in (("writer", "Tecnico"), ("reader", "Captura"), ("denied", "Cliente")):
        role = Role(name=role_name)
        user = User(username=f"bridge-{key}", email=f"{key}@example.test",
                    full_name=f"Bridge {key}", hashed_password="unused", roles=[role])
        db.add(user)
        actors[key] = user
    client = Client(legal_name="ERP client, different from LAB snapshot")
    db.add(client)
    db.flush()
    orders = [ServiceOrder(folio=f"ETS-BRIDGE-{i}", work_order_number=9000+i,
                           client_id=client.id, status="scheduled") for i in range(2)]
    roots = [LabWorkOrder(folio=6400+i*10, sequence_number=1,
                          created_by_user_id=actors["writer"].id,
                          reception_date=date.today(), client_name="LAB snapshot", status="draft")
             for i in range(2)]
    db.add_all([*orders, *roots])
    db.flush()
    # Exercise the existing self-root convention as well as legacy NULL roots.
    roots[0].root_work_order_id = roots[0].id
    child = LabWorkOrder(folio=6401, root_work_order_id=roots[0].id, sequence_number=2,
                         created_by_user_id=actors["writer"].id,
                         reception_date=date.today(), client_name="LAB snapshot", status="draft")
    db.add(child)
    db.flush()
    for position, active in ((1, True), (2, False)):
        db.add(LabWorkOrderEquipment(work_order_id=child.id, position=position,
                                    instrument="Instrument", brand="Brand", identification=str(position),
                                    serial_number=str(position), is_good_condition=True, is_active=active))
    db.commit()
    return SimpleNamespace(actors=actors, orders=orders, roots=roots, child=child)


@pytest.fixture()
def ctx():
    engine = create_engine("sqlite+pysqlite:///:memory:",
                           connect_args={"check_same_thread": False}, poolclass=StaticPool)

    @event.listens_for(engine, "connect")
    def foreign_keys(connection, _):
        connection.execute("PRAGMA foreign_keys=ON")

    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine, expire_on_commit=False, autoflush=False)
    with factory() as db:
        context = seed(db)
        context.db = db
        context.factory = factory

        def override_db():
            with factory() as request_db:
                yield request_db

        previous_overrides = app.dependency_overrides.copy()
        app.dependency_overrides[get_db] = override_db
        context.client = TestClient(app)
        context.headers = {
            key: {"Authorization": f"Bearer {create_access_token(str(user.id))}"}
            for key, user in context.actors.items()
        }
        context.path = f"/api/service-orders/{context.orders[0].id}"
        try:
            yield context
        finally:
            context.client.close()
            app.dependency_overrides.clear()
            app.dependency_overrides.update(previous_overrides)
    engine.dispose()


def link(ctx, root=None, order=None):
    return service.link_lab_group(ctx.db, (order or ctx.orders[0]).id,
                                  (root or ctx.roots[0]).id, user_id=ctx.actors["writer"].id)


def audits(ctx):
    return list(ctx.db.scalars(select(AuditLog).order_by(AuditLog.id)))


def test_initial_link_child_resolution_idempotence_and_actor(ctx):
    row = link(ctx, ctx.child)
    again = link(ctx)
    assert row.id == again.id
    assert row.lab_root_work_order_id == ctx.roots[0].id
    assert row.status == "active"
    assert row.linked_by_user_id == ctx.actors["writer"].id
    assert row.linked_at and row.created_at and row.updated_at
    assert service.get_active_lab_link(ctx.db, ctx.orders[0].id).id == row.id
    history = service.list_lab_link_history(ctx.db, ctx.orders[0].id)
    assert [item.id for item in history] == [row.id]
    assert ctx.orders[0].lab_links == [row]
    audit, = audits(ctx)
    assert audit.action == "service_order.lab_group_linked"
    assert audit.user_id == row.linked_by_user_id
    assert audit.new_values["root_folio"] == 6400
    assert audit.new_values["link_id"] == row.id
    assert audit.new_values["service_order_id"] == ctx.orders[0].id


def test_ordinary_link_rejects_other_group(ctx):
    old = link(ctx)
    with pytest.raises(HTTPException) as exc:
        link(ctx, ctx.roots[1])
    assert exc.value.status_code == 409
    assert service.get_active_lab_link(ctx.db, ctx.orders[0].id).id == old.id
    assert len(audits(ctx)) == 1


def test_replace_preserves_history_pointer_and_audit(ctx):
    old = link(ctx)
    new = service.replace_lab_group(ctx.db, ctx.orders[0].id, ctx.roots[1].id,
                                    "  Correction  ", user_id=ctx.actors["writer"].id)
    ctx.db.refresh(old)
    assert new.id != old.id and new.status == "active"
    assert old.status == "replaced"
    assert old.replaced_by_link_id == new.id
    assert old.replaced_by_link.id == new.id
    assert old.unlinked_at and old.unlinked_by_user_id == ctx.actors["writer"].id
    assert old.unlink_reason == "Correction"
    assert service.get_active_lab_link(ctx.db, ctx.orders[0].id).id == new.id
    audit = audits(ctx)[-1]
    assert audit.action == "service_order.lab_group_replaced"
    assert audit.previous_values["link_id"] == old.id
    assert audit.previous_values["lab_root_work_order_id"] == ctx.roots[0].id
    assert audit.new_values["link_id"] == new.id
    assert audit.new_values["reason"] == "Correction"
    assert audit.comment == "Correction"


def test_replace_same_group_is_idempotent_even_with_child(ctx):
    old = link(ctx)
    new = service.replace_lab_group(ctx.db, ctx.orders[0].id, ctx.child.id,
                                    "same", user_id=ctx.actors["writer"].id)
    assert old.id == new.id and new.status == "active"
    assert new.unlinked_at is None
    assert len(audits(ctx)) == 1


def test_unlink_and_relink_create_new_history_without_lab_changes(ctx):
    before = ctx.db.execute(select(LabWorkOrder.__table__)).all()
    equipment_before = ctx.db.execute(select(LabWorkOrderEquipment.__table__)).all()
    old = link(ctx)
    closed = service.unlink_lab_group(ctx.db, ctx.orders[0].id, "detach", user_id=ctx.actors["writer"].id)
    assert closed.id == old.id and closed.status == "unlinked"
    assert closed.unlinked_at and closed.unlink_reason == "detach"
    assert closed.unlinked_by_user_id == ctx.actors["writer"].id
    assert closed.replaced_by_link_id is None
    assert service.get_active_lab_link(ctx.db, ctx.orders[0].id) is None
    new = link(ctx)
    assert new.id != old.id and new.status == "active"
    assert ctx.db.execute(select(LabWorkOrder.__table__)).all() == before
    assert ctx.db.execute(select(LabWorkOrderEquipment.__table__)).all() == equipment_before
    assert [a.action for a in audits(ctx)] == ["service_order.lab_group_linked",
                                               "service_order.lab_group_unlinked",
                                               "service_order.lab_group_linked"]
    assert all(a.user_id == ctx.actors["writer"].id for a in audits(ctx))


@pytest.mark.parametrize("operation", ["replace", "unlink"])
def test_missing_active_link_is_conflict(ctx, operation):
    kwargs = {"work_order_id": ctx.roots[0].id} if operation == "replace" else {}
    with pytest.raises(HTTPException) as exc:
        getattr(service, f"{operation}_lab_group")(
            ctx.db, ctx.orders[0].id, reason="missing", user_id=ctx.actors["writer"].id, **kwargs)
    assert exc.value.status_code == 409
    assert audits(ctx) == []


@pytest.mark.parametrize("operation", ["replace", "unlink"])
@pytest.mark.parametrize("reason", [None, "", "   ", "\n\t"])
def test_reason_required_http_and_service(ctx, operation, reason):
    link(ctx)
    payload = {"work_order_id": ctx.roots[1].id} if operation == "replace" else {}
    if reason is not None:
        payload["reason"] = reason
    response = ctx.client.post(f"{ctx.path}/lab-link/{operation}", json=payload,
                               headers=ctx.headers["writer"])
    assert response.status_code == 422
    kwargs = {"work_order_id": ctx.roots[1].id} if operation == "replace" else {}
    with pytest.raises(HTTPException) as exc:
        getattr(service, f"{operation}_lab_group")(
            ctx.db, ctx.orders[0].id, reason=reason, user_id=ctx.actors["writer"].id, **kwargs)
    assert exc.value.status_code == 422
    assert len(audits(ctx)) == 1


def test_root_exclusivity_across_ets_for_link_and_replace(ctx):
    first = link(ctx)
    second = link(ctx, ctx.roots[1], ctx.orders[1])
    with pytest.raises(HTTPException) as exc:
        service.replace_lab_group(ctx.db, ctx.orders[1].id, ctx.child.id,
                                   "conflict", user_id=ctx.actors["writer"].id)
    assert exc.value.status_code == 409
    assert service.get_active_lab_link(ctx.db, ctx.orders[1].id).id == second.id
    service.unlink_lab_group(ctx.db, ctx.orders[1].id, "detach", user_id=ctx.actors["writer"].id)
    with pytest.raises(HTTPException) as exc:
        link(ctx, order=ctx.orders[1])
    assert exc.value.status_code == 409
    service.unlink_lab_group(ctx.db, ctx.orders[0].id, "release", user_id=ctx.actors["writer"].id)
    assert link(ctx, order=ctx.orders[1]).id != first.id


@pytest.mark.parametrize("same_ets", [True, False])
def test_partial_unique_constraints_reject_direct_duplicate_inserts(ctx, same_ets):
    link(ctx)
    with pytest.raises(IntegrityError):
        ctx.db.execute(insert(ServiceOrderLabLink).values(
            service_order_id=ctx.orders[0 if same_ets else 1].id,
            lab_root_work_order_id=ctx.roots[1 if same_ets else 0].id,
            status="active", linked_at=datetime.now(timezone.utc),
            linked_by_user_id=ctx.actors["writer"].id,
        ))
        ctx.db.commit()
    ctx.db.rollback()
    assert ctx.db.scalar(select(func.count(ServiceOrderLabLink.id))) == 1


@pytest.mark.parametrize("values", [
    {"status": "invalid"}, {"status": "unlinked"},
    {"status": "active", "unlink_reason": "invalid"},
    {"linked_by_user_id": None}, {"lab_root_work_order_id": 987654},
])
def test_db_checks_and_foreign_keys(ctx, values):
    data = dict(service_order_id=ctx.orders[0].id, lab_root_work_order_id=ctx.roots[0].id,
                status="active", linked_at=datetime.now(timezone.utc), linked_by_user_id=ctx.actors["writer"].id)
    data.update(values)
    with pytest.raises(IntegrityError):
        ctx.db.execute(insert(ServiceOrderLabLink).values(**data))
        ctx.db.commit()
    ctx.db.rollback()


@pytest.mark.parametrize("status,is_active", [("cancelled", True), ("closed", True), ("scheduled", False)])
@pytest.mark.parametrize("operation", ["link", "replace", "unlink"])
def test_terminal_or_inactive_ets_rejects_mutations_history_remains_readable(ctx, status, is_active, operation):
    old = link(ctx) if operation != "link" else None
    ctx.orders[0].status = status
    ctx.orders[0].is_active = is_active
    ctx.db.commit()
    args = [ctx.db, ctx.orders[0].id]
    if operation != "unlink":
        args.append(ctx.roots[1].id)
    if operation != "link":
        args.append("reason")
    with pytest.raises(HTTPException) as exc:
        getattr(service, f"{operation}_lab_group")(*args, user_id=ctx.actors["writer"].id)
    assert exc.value.status_code == 409
    assert len(service.list_lab_link_history(ctx.db, ctx.orders[0].id)) == bool(old)


def test_cancelled_root_rejects_child_and_replace(ctx):
    old = link(ctx, ctx.roots[1])
    ctx.roots[0].status = "cancelled"
    ctx.db.commit()
    with pytest.raises(HTTPException) as exc:
        service.replace_lab_group(ctx.db, ctx.orders[0].id, ctx.child.id,
                                   "cancelled root", user_id=ctx.actors["writer"].id)
    assert exc.value.status_code == 409
    assert service.get_active_lab_link(ctx.db, ctx.orders[0].id).id == old.id
    with pytest.raises(HTTPException) as exc:
        link(ctx, ctx.child, ctx.orders[1])
    assert exc.value.status_code == 409


def test_missing_ets_or_lab_and_malformed_root(ctx):
    for order_id, lab_id in ((99999, ctx.roots[0].id), (ctx.orders[0].id, 99999)):
        with pytest.raises(HTTPException) as exc:
            service.link_lab_group(ctx.db, order_id, lab_id, user_id=ctx.actors["writer"].id)
        assert exc.value.status_code == 404
    ctx.child.root_work_order_id = ctx.roots[1].id
    ctx.roots[0].root_work_order_id = ctx.child.id
    ctx.db.commit()
    with pytest.raises(HTTPException) as exc:
        link(ctx)
    assert exc.value.status_code == 409


def test_deterministic_history_with_equal_timestamps(ctx):
    old = link(ctx)
    service.unlink_lab_group(ctx.db, ctx.orders[0].id, "detach", user_id=ctx.actors["writer"].id)
    new = link(ctx)
    new.linked_at = old.linked_at
    ctx.db.commit()
    assert [row.id for row in service.list_lab_link_history(ctx.db, ctx.orders[0].id)] == [new.id, old.id]


@pytest.mark.parametrize("failure", ["insert", "audit", "commit"])
def test_replace_failure_rolls_back_entire_transaction(ctx, monkeypatch, failure):
    old = link(ctx)
    old_id = old.id

    def fail(*args, **kwargs):
        raise RuntimeError("injected failure")

    if failure == "insert":
        # Failure occurs AFTER the old link was closed/flushed.
        monkeypatch.setattr(service, "_new_link", fail)
    elif failure == "audit":
        monkeypatch.setattr(service, "write_audit_log", fail)
    else:
        monkeypatch.setattr(ctx.db, "commit", fail)
    with pytest.raises(RuntimeError, match="injected failure"):
        service.replace_lab_group(ctx.db, ctx.orders[0].id, ctx.roots[1].id,
                                   "atomicity", user_id=ctx.actors["writer"].id)
    with ctx.factory() as fresh:
        row = fresh.get(ServiceOrderLabLink, old_id)
        assert row.status == "active" and row.unlinked_at is None
        assert row.replaced_by_link_id is None and row.unlink_reason is None
        assert fresh.scalar(select(func.count(ServiceOrderLabLink.id))) == 1
        assert fresh.scalar(select(func.count(AuditLog.id))) == 1


def test_integrity_race_is_409_and_session_remains_usable(ctx, monkeypatch):
    old = link(ctx)
    create = service._new_link

    def duplicate(db, service_order_id, root_id, user_id):
        create(db, service_order_id, root_id, user_id)
        return create(db, service_order_id, root_id, user_id)

    monkeypatch.setattr(service, "_new_link", duplicate)
    with pytest.raises(HTTPException) as exc:
        service.replace_lab_group(ctx.db, ctx.orders[0].id, ctx.roots[1].id,
                                   "race", user_id=ctx.actors["writer"].id)
    assert exc.value.status_code == 409
    assert service.get_active_lab_link(ctx.db, ctx.orders[0].id).id == old.id
    assert len(audits(ctx)) == 1


def test_historical_ets_and_root_cannot_be_deleted(ctx):
    link(ctx, ctx.roots[1])
    service.unlink_lab_group(ctx.db, ctx.orders[0].id, "history", user_id=ctx.actors["writer"].id)
    for model, object_id in ((ServiceOrder, ctx.orders[0].id), (LabWorkOrder, ctx.roots[1].id)):
        with pytest.raises(IntegrityError):
            ctx.db.execute(delete(model).where(model.id == object_id))
            ctx.db.commit()
        ctx.db.rollback()


ENDPOINTS = [("GET", "/lab-link"), ("GET", "/lab-link/history"), ("GET", "/lab-candidates"),
             ("POST", "/lab-link"), ("POST", "/lab-link/replace"), ("POST", "/lab-link/unlink")]


@pytest.mark.parametrize("method,suffix", ENDPOINTS)
def test_http_permissions_and_classification(ctx, method, suffix):
    path = f"{ctx.path}{suffix}"
    payload = {"work_order_id": ctx.roots[0].id, "reason": "test"}
    kwargs = {"json": payload} if method == "POST" else {}
    assert ctx.client.request(method, path, **kwargs).status_code == 401
    assert ctx.client.request(method, path, headers=ctx.headers["denied"], **kwargs).status_code == 403
    reader = ctx.client.request(method, path, headers=ctx.headers["reader"], **kwargs)
    assert reader.status_code == (200 if method == "GET" else 403)
    policy = classify_operation(method, path, ["service-orders"])
    assert policy.access_type == AccessType.PERMISSION
    assert policy.permission == ("service_orders.read" if method == "GET" else "service_orders.update")
    operations = assert_all_routes_classified(app)
    assert any(op.path == f"/api/service-orders/{{service_order_id}}{suffix}" and op.method == method
               for op in operations)


def test_http_lifecycle_and_minimal_read_schema(ctx):
    headers = ctx.headers["writer"]
    assert ctx.client.get(f"{ctx.path}/lab-link", headers=headers).json() is None
    response = ctx.client.post(f"{ctx.path}/lab-link", json={"work_order_id": ctx.child.id}, headers=headers)
    assert response.status_code == 200, response.text
    row = response.json()
    assert row["root_folio"] == 6400 and row["lab_root_work_order_id"] == ctx.roots[0].id
    assert row["linked_by_name"] == "Bridge writer" and row["unlinked_by_name"] is None
    assert "equipment" not in row and "signatures" not in row
    conflict = ctx.client.post(f"{ctx.path}/lab-link", json={"work_order_id": ctx.roots[1].id}, headers=headers)
    assert conflict.status_code == 409
    response = ctx.client.post(f"{ctx.path}/lab-link/replace",
                               json={"work_order_id": ctx.roots[1].id, "reason": "change"}, headers=headers)
    assert response.status_code == 200, response.text
    new = response.json()
    response = ctx.client.post(f"{ctx.path}/lab-link/unlink", json={"reason": "detach"}, headers=headers)
    assert response.status_code == 200 and response.json()["status"] == "unlinked"
    history = ctx.client.get(f"{ctx.path}/lab-link/history", headers=ctx.headers["reader"]).json()
    assert [item["id"] for item in history] == [new["id"], row["id"]]
    assert history[1]["replaced_by_link_id"] == new["id"]
    assert history[0]["unlinked_by_name"] == "Bridge writer"


def test_candidates_search_child_deduplicates_counts_active_equipment_and_other_ets(ctx):
    link(ctx, order=ctx.orders[1])
    rows = service.search_lab_candidates(ctx.db, ctx.orders[0].id, "640")
    row, = rows
    assert row.root_folio == 6400 and row.group_folios == [6400, 6401]
    assert row.work_order_count == 2 and row.equipment_count == 1
    assert row.client_name == "LAB snapshot"
    assert row.active_service_order_id == ctx.orders[1].id and row.linked_to_other_service_order
    response = ctx.client.get(f"{ctx.path}/lab-candidates?q=6401", headers=ctx.headers["reader"])
    assert response.status_code == 200 and response.json() == [row.model_dump()]
    assert len(service.search_lab_candidates(ctx.db, ctx.orders[0].id, "", limit=1)) == 1
    assert service.search_lab_candidates(ctx.db, ctx.orders[0].id, "%") == []
    assert service.search_lab_candidates(ctx.db, ctx.orders[1].id, "6401")[0].linked_to_other_service_order is False


def test_null_actor_rejected(ctx):
    with pytest.raises(ValueError, match="requieren un actor"):
        service.link_lab_group(ctx.db, ctx.orders[0].id, ctx.roots[0].id, user_id=None)


@pytest.fixture()
def postgres_ctx():
    url = os.getenv("ETS_LAB_POSTGRES_TEST_URL")
    if not url:
        pytest.skip("Set ETS_LAB_POSTGRES_TEST_URL for real row lock concurrency tests")
    schema = f"ets_lab_{uuid4().hex}"
    admin = create_engine(url)
    with admin.begin() as conn:
        conn.execute(text(f'CREATE SCHEMA "{schema}"'))
    engine = create_engine(url, connect_args={"options": f"-csearch_path={schema} -clock_timeout=5000"})
    try:
        Base.metadata.create_all(engine)
        factory = sessionmaker(bind=engine, expire_on_commit=False, autoflush=False)
        with factory() as db:
            context = seed(db)
            context.ids = ([x.id for x in context.orders], [x.id for x in context.roots], context.actors["writer"].id)
        context.factory = factory
        yield context
    finally:
        engine.dispose()
        with admin.begin() as conn:
            conn.execute(text(f'DROP SCHEMA "{schema}" CASCADE'))
        admin.dispose()


@pytest.mark.parametrize("scenario", ["same_ets_same_root", "same_ets_other_root", "other_ets_same_root", "replace"])
def test_postgres_concurrent_requests_preserve_invariants(postgres_ctx, scenario):
    factory = postgres_ctx.factory
    orders, roots, actor = postgres_ctx.ids
    if scenario == "replace":
        with factory() as db:
            old_id = service.link_lab_group(db, orders[0], roots[0], user_id=actor).id
    barrier = Barrier(2)

    def request(index):
        with factory() as db:
            barrier.wait(timeout=10)
            try:
                if scenario == "replace":
                    row = service.replace_lab_group(db, orders[0], roots[1], "concurrent", user_id=actor)
                else:
                    row = service.link_lab_group(
                        db, orders[index if scenario == "other_ets_same_root" else 0],
                        roots[index if scenario == "same_ets_other_root" else 0], user_id=actor)
                return 200, row.id
            except HTTPException as exc:
                return exc.status_code, None

    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(request, [0, 1]))
    expected = [200, 200] if scenario in {"same_ets_same_root", "replace"} else [200, 409]
    assert sorted(code for code, _ in results) == expected
    with factory() as db:
        rows = list(db.scalars(select(ServiceOrderLabLink)))
        assert sum(row.status == "active" for row in rows) == 1
        assert len(rows) == (2 if scenario == "replace" else 1)
        assert db.scalar(select(func.count(AuditLog.id))) == len(rows)
        if expected == [200, 200]:
            assert results[0][1] == results[1][1]
        if scenario == "replace":
            old = db.get(ServiceOrderLabLink, old_id)
            assert old.status == "replaced" and old.replaced_by_link_id == results[0][1]


def test_mobile_token_cannot_manage_erp_link(ctx):
    token = create_access_token(str(ctx.actors["writer"].id), extra_claims={"auth_context": "mobile_internal"})
    response = ctx.client.post(
        f"{ctx.path}/lab-link", json={"work_order_id": ctx.roots[0].id},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 401
    assert service.get_active_lab_link(ctx.db, ctx.orders[0].id) is None


def test_sqlite_migration_roundtrip_matches_model(ctx):
    import importlib.util
    from pathlib import Path

    from alembic.autogenerate import compare_metadata
    from alembic.migration import MigrationContext
    from alembic.operations import Operations

    path = Path(__file__).parents[1] / "migrations/versions/d7e9a1c3b5f0_add_service_order_lab_links.py"
    spec = importlib.util.spec_from_file_location("ets_lab_link_migration", path)
    migration = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(migration)
    with ctx.db.get_bind().begin() as conn:
        with Operations.context(MigrationContext.configure(conn)):
            migration.downgrade()
            migration.upgrade()
        def include_link_object(obj, name, type_, reflected, compare_to):
            table = obj if type_ == "table" else getattr(obj, "table", None)
            return table is not None and table.name == "service_order_lab_links"

        context = MigrationContext.configure(conn, opts={"include_object": include_link_object})
        diff = compare_metadata(context, Base.metadata)
        assert diff == []
    # Test constraints on the migrated table, not only create_all metadata.
    link(ctx)
    with pytest.raises(IntegrityError):
        ctx.db.execute(insert(ServiceOrderLabLink).values(
            service_order_id=ctx.orders[0].id, lab_root_work_order_id=ctx.roots[1].id,
            status="active", linked_at=datetime.now(timezone.utc), linked_by_user_id=ctx.actors["writer"].id,
        ))
    ctx.db.rollback()
