"""Despacho y consumo coordinado sin reinterpretar el Motor existente."""

from __future__ import annotations

from datetime import timedelta
from threading import Event, Thread
from collections.abc import Callable, Mapping
from typing import Any

from app.resolution_engine.contracts.distribution import (
    DistributedWorkHandler,
    DistributedWorkStore,
    WorkerRegistration,
    WorkLease,
)
from app.resolution_engine.contracts.runtime import Clock, IdentifierFactory
from app.resolution_engine.contracts.execution import ExecuteResolutionCommand
from app.resolution_engine.contracts.compensation import (
    ExecuteCompensationCommand,
)
from app.resolution_engine.domain.distribution import (
    DistributedWorkKind,
    DistributedWorkRequest,
    DistributedWorkResult,
    RecoveryReport,
    WorkFailureCertainty,
)
from app.resolution_engine.domain.exceptions import (
    DistributedHandlerNotFoundError,
    DistributedLeaseLostError,
    DistributedWorkUncertainError,
    RetryableDistributedWorkError,
)


class ResolutionExecutionWorkHandler:
    """Adaptador de worker hacia el Executor aprobado; no reconstruye reglas."""

    kind = DistributedWorkKind.EXECUTION

    def __init__(
        self,
        *,
        executor,
        command_decoder: Callable[
            [Mapping[str, Any]], ExecuteResolutionCommand
        ],
    ) -> None:
        self._executor = executor
        self._command_decoder = command_decoder

    def execute(
        self,
        item,
        /,
    ) -> DistributedWorkResult:
        command = self._command_decoder(item.payload)
        if command.resolution_id != item.resolution_id:
            raise DistributedWorkUncertainError(
                "execution command does not belong to claimed resolution"
            )
        return DistributedWorkResult(self._executor.execute(command).snapshot())


class CompensationExecutionWorkHandler:
    """Adaptador de worker hacia CompensationExecutor sin flujo paralelo."""

    kind = DistributedWorkKind.COMPENSATION

    def __init__(
        self,
        *,
        executor,
        command_decoder: Callable[
            [Mapping[str, Any]], ExecuteCompensationCommand
        ],
    ) -> None:
        self._executor = executor
        self._command_decoder = command_decoder

    def execute(
        self,
        item,
        /,
    ) -> DistributedWorkResult:
        command = self._command_decoder(item.payload)
        outcome = self._executor.execute(command)
        if outcome.resolution_id != item.resolution_id:
            raise DistributedWorkUncertainError(
                "compensation outcome does not belong to claimed resolution"
            )
        return DistributedWorkResult(outcome.snapshot())


class DistributedDispatcher:
    def __init__(self, *, store: DistributedWorkStore, clock: Clock) -> None:
        self._store = store
        self._clock = clock

    def enqueue(self, request: DistributedWorkRequest, /):
        return self._store.enqueue(request, occurred_at=self._clock.now())


class DistributedRecoveryService:
    def __init__(self, *, store: DistributedWorkStore, clock: Clock) -> None:
        self._store = store
        self._clock = clock

    def recover(self) -> RecoveryReport:
        return self._store.recover_expired(occurred_at=self._clock.now())


class DistributedWorker:
    """Worker pull de una unidad; el supervisor decide el ciclo de proceso."""

    def __init__(
        self,
        *,
        store: DistributedWorkStore,
        handlers: tuple[DistributedWorkHandler, ...],
        registration: WorkerRegistration,
        clock: Clock,
        identifiers: IdentifierFactory,
        node_lease_ttl: timedelta = timedelta(seconds=30),
        work_lease_ttl: timedelta = timedelta(minutes=5),
    ) -> None:
        self._store = store
        self._registration = registration
        self._clock = clock
        self._identifiers = identifiers
        self._node_lease_ttl = node_lease_ttl
        self._work_lease_ttl = work_lease_ttl
        self._handlers: dict[DistributedWorkKind, DistributedWorkHandler] = {}
        for handler in handlers:
            kind = DistributedWorkKind(handler.kind)
            if kind in self._handlers:
                raise ValueError(f"duplicate distributed handler: {kind.value}")
            self._handlers[kind] = handler

    def start(self) -> None:
        self._store.register_node(
            self._registration,
            occurred_at=self._clock.now(),
            lease_ttl=self._node_lease_ttl,
        )

    def drain(self) -> None:
        self._store.drain_node(
            self._registration,
            occurred_at=self._clock.now(),
        )

    def run_once(self) -> DistributedWorkResult | None:
        now = self._clock.now()
        self._store.heartbeat_node(
            self._registration,
            occurred_at=now,
            lease_ttl=self._node_lease_ttl,
        )
        lease = self._store.claim_next(
            self._registration,
            occurred_at=now,
            lease_ttl=self._work_lease_ttl,
            lease_token=self._identifiers.new_id(),
        )
        if lease is None:
            return None
        handler = self._handlers.get(lease.item.kind)
        if handler is None:
            error = DistributedHandlerNotFoundError(
                f"no handler for distributed work kind {lease.item.kind.value}"
            )
            self._fail_terminal(lease, error)
            raise error
        try:
            lease = self._store.mark_effect_started(
                lease,
                occurred_at=self._clock.now(),
            )
            result = self._execute_with_heartbeats(handler, lease)
            self._store.complete(
                lease,
                result,
                occurred_at=self._clock.now(),
            )
            return result
        except DistributedLeaseLostError:
            # Otro proceso será el único autorizado para reconciliar el lease
            # expirado. Si el efecto inició, recovery lo bloqueará como incierto.
            raise
        except RetryableDistributedWorkError as exc:
            self._store.fail(
                lease,
                error_code=exc.error_code,
                error_message=str(exc),
                certainty=WorkFailureCertainty.NO_EFFECT,
                retryable=True,
                occurred_at=self._clock.now(),
            )
            return None
        except DistributedWorkUncertainError as exc:
            self._store.fail(
                lease,
                error_code=exc.error_code,
                error_message=str(exc),
                certainty=WorkFailureCertainty.UNCERTAIN,
                retryable=False,
                occurred_at=self._clock.now(),
            )
            return None
        except Exception as exc:
            self._store.fail(
                lease,
                error_code="distributed_handler_failed",
                error_message=str(exc),
                certainty=WorkFailureCertainty.UNCERTAIN,
                retryable=False,
                occurred_at=self._clock.now(),
            )
            raise

    def renew(self, lease: WorkLease) -> WorkLease:
        return self._store.renew_lease(
            lease,
            occurred_at=self._clock.now(),
            lease_ttl=self._work_lease_ttl,
        )

    def _fail_terminal(self, lease: WorkLease, exc: Exception) -> None:
        self._store.fail(
            lease,
            error_code="distributed_handler_not_found",
            error_message=str(exc),
            certainty=WorkFailureCertainty.NO_EFFECT,
            retryable=False,
            occurred_at=self._clock.now(),
        )

    def _execute_with_heartbeats(
        self,
        handler: DistributedWorkHandler,
        lease: WorkLease,
    ) -> DistributedWorkResult:
        stop = Event()
        lease_errors: list[Exception] = []
        interval = max(
            0.1,
            min(
                self._work_lease_ttl.total_seconds(),
                self._node_lease_ttl.total_seconds(),
            )
            / 3,
        )

        def maintain_leases() -> None:
            while not stop.wait(interval):
                try:
                    now = self._clock.now()
                    self._store.renew_lease(
                        lease,
                        occurred_at=now,
                        lease_ttl=self._work_lease_ttl,
                    )
                    self._store.heartbeat_node(
                        self._registration,
                        occurred_at=now,
                        lease_ttl=self._node_lease_ttl,
                    )
                except Exception as exc:
                    lease_errors.append(exc)
                    return

        heartbeat = Thread(
            target=maintain_leases,
            name=f"resolution-worker-heartbeat-{self._registration.node_id}",
            daemon=True,
        )
        heartbeat.start()
        try:
            result = handler.execute(lease.item)
        finally:
            stop.set()
            heartbeat.join(timeout=interval + 1)
        if lease_errors:
            raise DistributedLeaseLostError(
                f"distributed lease heartbeat failed for work {lease.item.id}"
            ) from lease_errors[0]
        return result
