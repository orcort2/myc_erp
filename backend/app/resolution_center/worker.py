"""Proceso operativo independiente para trabajos del Centro de Resoluciones."""

from __future__ import annotations

import os
import signal
import socket
from datetime import datetime, timedelta
from threading import Event
from uuid import uuid4

from app.core.db import SessionLocal
from app.resolution_engine.application.action_runner import ActionRunner
from app.resolution_engine.application.distribution import (
    DistributedRecoveryService,
    DistributedWorker,
    ResolutionExecutionWorkHandler,
)
from app.resolution_engine.application.execution import ResolutionExecutor
from app.resolution_engine.contracts.distribution import WorkerRegistration
from app.resolution_engine.contracts.execution import ExecuteResolutionCommand
from app.resolution_engine.domain.execution import ExecutionEngine
from app.resolution_engine.domain.lifecycle import ResolutionStateMachine
from app.resolution_engine.domain.security import (
    ActorContext,
    ActorIdentity,
    AuthenticationContext,
    PermissionGrant,
)
from app.resolution_engine.infrastructure.distribution import (
    SqlAlchemyDistributedWorkStore,
)
from app.resolution_engine.infrastructure.execution import (
    SqlAlchemyExecutionStore,
)
from app.resolution_engine.infrastructure.runtime import (
    SystemClock,
    UuidIdentifierFactory,
)
from app.resolution_integrations.certificates import (
    build_certificate_resolution_integration,
)


def decode_execution_command(payload) -> ExecuteResolutionCommand:
    actor_payload = payload["actor"]
    identity = actor_payload["identity"]
    authentication = actor_payload["authentication"]
    actor = ActorContext(
        identity=ActorIdentity(**identity),
        authentication=AuthenticationContext(
            authenticated_at=datetime.fromisoformat(
                authentication["authenticated_at"]
            ),
            expires_at=(
                datetime.fromisoformat(authentication["expires_at"])
                if authentication.get("expires_at")
                else None
            ),
            method=authentication["method"],
            session_id=authentication["session_id"],
            assurance_level=authentication["assurance_level"],
            source=authentication["source"],
            correlation_id=authentication["correlation_id"],
            delegated_by_actor_id=authentication.get(
                "delegated_by_actor_id"
            ),
            metadata=authentication.get("metadata", {}),
        ),
        permissions=tuple(
            PermissionGrant(
                permission=item["permission"],
                valid_from=(
                    datetime.fromisoformat(item["valid_from"])
                    if item.get("valid_from")
                    else None
                ),
                valid_until=(
                    datetime.fromisoformat(item["valid_until"])
                    if item.get("valid_until")
                    else None
                ),
                resource_type=item.get("resource_type"),
                resource_id=item.get("resource_id"),
                constraints=item.get("constraints", {}),
            )
            for item in actor_payload.get("permissions", ())
        ),
    )
    return ExecuteResolutionCommand(
        resolution_id=int(payload["resolution_id"]),
        idempotency_key=str(payload["idempotency_key"]),
        security_decision_id=int(payload["security_decision_id"]),
        actor=actor,
        lock_owner=str(payload["lock_owner"]),
        lock_ttl=timedelta(
            seconds=int(payload.get("lock_ttl_seconds", 300))
        ),
    )


def build_worker(
    *,
    node_id: str | None = None,
    instance_id: str | None = None,
    capacity: int = 1,
) -> DistributedWorker:
    integration = build_certificate_resolution_integration(SessionLocal)
    clock = SystemClock()
    executor = ResolutionExecutor(
        store=SqlAlchemyExecutionStore(SessionLocal),
        action_runner=ActionRunner(integration.action_handlers),
        engine=ExecutionEngine(),
        state_machine=ResolutionStateMachine(),
        clock=clock,
        identifiers=UuidIdentifierFactory(),
    )
    return DistributedWorker(
        store=SqlAlchemyDistributedWorkStore(SessionLocal),
        handlers=(
            ResolutionExecutionWorkHandler(
                executor=executor,
                command_decoder=decode_execution_command,
            ),
        ),
        registration=WorkerRegistration(
            node_id=node_id
            or f"resolution-center-{socket.gethostname()}-{os.getpid()}",
            instance_id=instance_id or str(uuid4()),
            capacity=capacity,
        ),
        clock=clock,
        identifiers=UuidIdentifierFactory(),
    )


def run_forever() -> None:
    stop = Event()
    for signal_number in (signal.SIGINT, signal.SIGTERM):
        signal.signal(signal_number, lambda *_: stop.set())
    worker = build_worker(
        node_id=os.getenv("MYC_RESOLUTION_WORKER_NODE_ID"),
        instance_id=os.getenv("MYC_RESOLUTION_WORKER_INSTANCE_ID"),
        capacity=max(
            1,
            int(os.getenv("MYC_RESOLUTION_WORKER_CAPACITY", "1")),
        ),
    )
    recovery = DistributedRecoveryService(
        store=SqlAlchemyDistributedWorkStore(SessionLocal),
        clock=SystemClock(),
    )
    worker.start()
    try:
        while not stop.is_set():
            recovery.recover()
            result = worker.run_once()
            if result is None:
                stop.wait(1)
    finally:
        worker.drain()


if __name__ == "__main__":
    run_forever()
