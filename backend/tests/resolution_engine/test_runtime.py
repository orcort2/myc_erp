from datetime import datetime, timezone
from uuid import UUID

from app.resolution_engine.contracts.runtime import Clock, IdentifierFactory
from app.resolution_engine.infrastructure.runtime import (
    SystemClock,
    UuidIdentifierFactory,
)


class FixedClock:
    def now(self) -> datetime:
        return datetime(2026, 7, 24, tzinfo=timezone.utc)


class SequentialIdentifierFactory:
    def __init__(self) -> None:
        self._next = 0

    def new_id(self) -> str:
        self._next += 1
        return f"test-{self._next}"


def use_clock(clock: Clock) -> datetime:
    return clock.now()


def use_identifier_factory(factory: IdentifierFactory) -> str:
    return factory.new_id()


def test_clock_is_injectable_and_system_clock_returns_aware_utc():
    assert use_clock(FixedClock()) == datetime(
        2026, 7, 24, tzinfo=timezone.utc
    )

    current = SystemClock().now()
    assert current.tzinfo is not None
    assert current.utcoffset() == timezone.utc.utcoffset(current)


def test_identifier_factory_is_injectable_and_uuid_adapter_is_opaque():
    sequential = SequentialIdentifierFactory()

    assert use_identifier_factory(sequential) == "test-1"
    generated = UuidIdentifierFactory().new_id()
    assert str(UUID(generated)) == generated
