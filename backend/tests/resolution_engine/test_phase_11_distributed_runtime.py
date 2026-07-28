from __future__ import annotations

import ast
from datetime import datetime, timedelta, timezone
from pathlib import Path
from types import SimpleNamespace

import pytest
from sqlalchemy import create_engine, event, select
from sqlalchemy.orm import sessionmaker

import app.models  # noqa: F401
from app.core.db import Base
from app.resolution_engine.application.distribution import (
    CompensationExecutionWorkHandler,
    DistributedDispatcher,
    DistributedRecoveryService,
    DistributedWorker,
    ResolutionExecutionWorkHandler,
)
from app.resolution_engine.contracts.distribution import WorkerRegistration
from app.resolution_engine.domain.distribution import (
    DeterministicRetryPolicy,
    DistributedWorkKind,
    DistributedWorkRequest,
    DistributedWorkResult,
    DistributedWorkStatus,
)
from app.resolution_engine.domain.exceptions import (
    DistributedLeaseLostError,
    DistributedWorkConflictError,
    RetryableDistributedWorkError,
)
from app.resolution_engine.infrastructure.distribution import (
    SqlAlchemyDistributedWorkStore,
)
from app.resolution_engine.infrastructure.persistence import (
    Resolution,
    ResolutionWorkEvent,
    ResolutionWorkItem,
)

NOW = datetime(2026, 7, 28, 16, tzinfo=timezone.utc)
MIGRATION = (
    Path(__file__).resolve().parents[2]
    / "migrations"
    / "versions"
    / "c1e3f5a7b9d2_phase_11_distributed_runtime.py"
)


class Clock:
    def __init__(self, current: datetime = NOW) -> None:
        self.current = current

    def now(self) -> datetime:
        return self.current

    def advance(self, delta: timedelta) -> None:
        self.current += delta


class Identifiers:
    def __init__(self, prefix: str) -> None:
        self.prefix = prefix
        self.sequence = 0

    def new_id(self) -> str:
        self.sequence += 1
        return f"{self.prefix}-{self.sequence}"


class SuccessHandler:
    kind = DistributedWorkKind.EXECUTION

    def __init__(self) -> None:
        self.calls: list[int] = []

    def execute(self, item):
        self.calls.append(item.id)
        return DistributedWorkResult(
            {"execution_id": item.payload["execution_id"]}
        )


class RetryOnceHandler:
    kind = DistributedWorkKind.EXECUTION

    def __init__(self) -> None:
        self.calls = 0

    def execute(self, item):
        self.calls += 1
        if self.calls == 1:
            raise RetryableDistributedWorkError("database unavailable")
        return DistributedWorkResult({"recovered": True})


@pytest.fixture
def runtime():
    engine = create_engine("sqlite+pysqlite:///:memory:")

    @event.listens_for(engine, "connect")
    def enable_foreign_keys(connection, _):
        connection.execute("PRAGMA foreign_keys=ON")

    tables = [
        table
        for name, table in Base.metadata.tables.items()
        if name == "resolutions" or name.startswith("resolution_")
    ]
    Base.metadata.create_all(engine, tables=tables)
    factory = sessionmaker(bind=engine, expire_on_commit=False)
    with factory() as session, session.begin():
        for public_id in ("resolution-1", "resolution-2"):
            session.add(
                Resolution(
                    public_id=public_id,
                    resolution_type="test.distributed",
                    definition_version="1.0",
                    status="ready_for_execution",
                    priority="normal",
                    source="system",
                    subject_type="test",
                    subject_id=public_id,
                    organization_id="org-1",
                    correlation_id=f"corr-{public_id}",
                    title=public_id,
                    requires_authorization=False,
                    version=1,
                    metadata_json={},
                )
            )
    return factory, SqlAlchemyDistributedWorkStore(factory)


def request(
    resolution_id: int,
    *,
    suffix: str,
    available_at: datetime | None = None,
) -> DistributedWorkRequest:
    return DistributedWorkRequest(
        work_key=f"execution:{suffix}",
        resolution_id=resolution_id,
        organization_id="org-1",
        kind=DistributedWorkKind.EXECUTION,
        payload={"execution_id": suffix},
        correlation_id=f"corr-{suffix}",
        available_at=available_at,
        retry_policy=DeterministicRetryPolicy(
            max_attempts=3,
            base_delay=timedelta(seconds=5),
            maximum_delay=timedelta(seconds=20),
        ),
    )


def registration(node: str) -> WorkerRegistration:
    return WorkerRegistration(
        node_id=node,
        instance_id=f"{node}-instance",
        capacity=1,
    )


def test_retry_policy_is_deterministic_and_bounded():
    policy = DeterministicRetryPolicy(
        max_attempts=5,
        base_delay=timedelta(seconds=3),
        maximum_delay=timedelta(seconds=10),
    )

    assert [policy.delay_after(attempt).total_seconds() for attempt in range(1, 5)] == [
        3,
        6,
        10,
        10,
    ]


def test_enqueue_is_idempotent_and_rejects_payload_collision(runtime):
    _, store = runtime
    first = store.enqueue(request(1, suffix="same"), occurred_at=NOW)
    replay = store.enqueue(request(1, suffix="same"), occurred_at=NOW)

    assert replay.id == first.id
    with pytest.raises(DistributedWorkConflictError):
        store.enqueue(
            DistributedWorkRequest(
                work_key="execution:same",
                resolution_id=1,
                organization_id="org-1",
                kind=DistributedWorkKind.EXECUTION,
                payload={"execution_id": "different"},
                correlation_id="corr-same",
            ),
            occurred_at=NOW,
        )


def test_nodes_balance_by_pull_and_never_claim_same_resolution(runtime):
    _, store = runtime
    node_a = registration("node-a")
    node_b = registration("node-b")
    store.register_node(
        node_a, occurred_at=NOW, lease_ttl=timedelta(minutes=1)
    )
    store.register_node(
        node_b, occurred_at=NOW, lease_ttl=timedelta(minutes=1)
    )
    store.enqueue(request(1, suffix="a"), occurred_at=NOW)
    store.enqueue(request(1, suffix="b"), occurred_at=NOW)
    store.enqueue(request(2, suffix="c"), occurred_at=NOW)

    lease_a = store.claim_next(
        node_a,
        occurred_at=NOW,
        lease_ttl=timedelta(minutes=1),
        lease_token="lease-a",
    )
    lease_b = store.claim_next(
        node_b,
        occurred_at=NOW,
        lease_ttl=timedelta(minutes=1),
        lease_token="lease-b",
    )

    assert lease_a is not None and lease_b is not None
    assert lease_a.item.resolution_id != lease_b.item.resolution_id
    assert store.snapshot().claimed == 2


def test_database_enforces_one_claimed_work_per_resolution():
    index = next(
        item
        for item in ResolutionWorkItem.__table__.indexes
        if item.name == "uq_resolution_work_items_claimed_resolution"
    )

    assert index.unique is True
    assert str(index.dialect_options["postgresql"]["where"]) == (
        "status = 'claimed'"
    )


def test_recovery_requeues_only_before_effect_and_fences_stale_owner(runtime):
    _, store = runtime
    node = registration("node-a")
    store.register_node(
        node, occurred_at=NOW, lease_ttl=timedelta(seconds=10)
    )
    store.enqueue(request(1, suffix="recover"), occurred_at=NOW)
    stale = store.claim_next(
        node,
        occurred_at=NOW,
        lease_ttl=timedelta(seconds=10),
        lease_token="stale",
    )
    assert stale is not None

    report = store.recover_expired(
        occurred_at=NOW + timedelta(seconds=11)
    )

    assert report.requeued == 1
    assert report.offline_nodes == 1
    with pytest.raises(DistributedLeaseLostError):
        store.complete(
            stale,
            DistributedWorkResult({"invalid": True}),
            occurred_at=NOW + timedelta(seconds=11),
        )


def test_recovery_blocks_work_if_effect_may_have_started(runtime):
    _, store = runtime
    node = registration("node-a")
    store.register_node(
        node, occurred_at=NOW, lease_ttl=timedelta(seconds=10)
    )
    store.enqueue(request(1, suffix="uncertain"), occurred_at=NOW)
    lease = store.claim_next(
        node,
        occurred_at=NOW,
        lease_ttl=timedelta(seconds=10),
        lease_token="uncertain",
    )
    assert lease is not None
    store.mark_effect_started(lease, occurred_at=NOW + timedelta(seconds=1))

    report = store.recover_expired(
        occurred_at=NOW + timedelta(seconds=11)
    )

    assert report.blocked_uncertain == 1
    assert store.snapshot().blocked == 1


def test_worker_retries_confirmed_no_effect_with_exact_backoff(runtime):
    factory, store = runtime
    clock = Clock()
    handler = RetryOnceHandler()
    worker = DistributedWorker(
        store=store,
        handlers=(handler,),
        registration=registration("node-a"),
        clock=clock,
        identifiers=Identifiers("lease"),
        node_lease_ttl=timedelta(minutes=1),
        work_lease_ttl=timedelta(minutes=1),
    )
    worker.start()
    DistributedDispatcher(store=store, clock=clock).enqueue(
        request(1, suffix="retry")
    )

    assert worker.run_once() is None
    assert store.snapshot().retry_wait == 1
    clock.advance(timedelta(seconds=4))
    assert worker.run_once() is None
    clock.advance(timedelta(seconds=1))
    result = worker.run_once()

    assert result is not None
    assert result.payload == {"recovered": True}
    assert handler.calls == 2
    assert store.snapshot().succeeded == 1
    with factory() as session:
        event_types = session.scalars(
            select(ResolutionWorkEvent.event_type).order_by(
                ResolutionWorkEvent.sequence
            )
        ).all()
    assert event_types == [
        "work.enqueued",
        "work.claimed",
        "work.effect_started",
        "work.retry_scheduled",
        "work.claimed",
        "work.effect_started",
        "work.succeeded",
    ]


def test_recovery_service_and_snapshot_are_operational_surfaces(runtime):
    _, store = runtime
    clock = Clock()

    assert DistributedRecoveryService(store=store, clock=clock).recover().requeued == 0
    assert store.snapshot(organization_id="org-1").queued == 0


def test_canonical_handlers_delegate_without_reimplementing_execution():
    class Outcome:
        resolution_id = 1

        def snapshot(self):
            return {"execution_id": 41, "resolution_id": self.resolution_id}

    class Executor:
        def __init__(self):
            self.commands = []

        def execute(self, command):
            self.commands.append(command)
            return Outcome()

    item = SimpleNamespace(
        resolution_id=1,
        payload={"resolution_id": 1},
    )
    execution = Executor()
    execution_result = ResolutionExecutionWorkHandler(
        executor=execution,
        command_decoder=lambda payload: SimpleNamespace(
            resolution_id=payload["resolution_id"]
        ),
    ).execute(item)
    compensation = Executor()
    compensation_result = CompensationExecutionWorkHandler(
        executor=compensation,
        command_decoder=lambda payload: SimpleNamespace(
            compensation_plan_id=payload["resolution_id"]
        ),
    ).execute(item)

    assert execution_result.payload["execution_id"] == 41
    assert compensation_result.payload["resolution_id"] == 1
    assert len(execution.commands) == len(compensation.commands) == 1


def test_phase_11_migration_is_reversible_and_follows_phase_10():
    namespace: dict = {}
    source = MIGRATION.read_text(encoding="utf-8")
    exec(compile(source, str(MIGRATION), "exec"), namespace)
    tree = ast.parse(source)

    def calls(function_name: str, method: str) -> set[str]:
        function = next(
            node
            for node in tree.body
            if isinstance(node, ast.FunctionDef) and node.name == function_name
        )
        return {
            node.args[0].value
            for node in ast.walk(function)
            if isinstance(node, ast.Call)
            and isinstance(node.func, ast.Attribute)
            and node.func.attr == method
            and node.args
            and isinstance(node.args[0], ast.Constant)
        }

    assert namespace["down_revision"] == "a0d2f4b6c8e1"
    assert calls("upgrade", "create_table") == {
        "resolution_worker_nodes",
        "resolution_work_items",
        "resolution_work_events",
    }
    assert calls("upgrade", "create_table") == calls("downgrade", "drop_table")
    assert "trg_resolution_work_events_immutable" in source
    assert "skip_locked=True" not in source
