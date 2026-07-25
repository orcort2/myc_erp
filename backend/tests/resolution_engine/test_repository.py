from datetime import datetime, timezone

from sqlalchemy import create_engine, event
from sqlalchemy.orm import Session

import app.models  # noqa: F401
from app.core.db import Base
from app.resolution_engine.infrastructure.persistence import (
    Resolution,
    ResolutionProblem,
)
from app.resolution_engine.infrastructure.repositories import (
    ResolutionRepository,
)


def sqlite_engine():
    engine = create_engine("sqlite+pysqlite:///:memory:")

    @event.listens_for(engine, "connect")
    def enable_foreign_keys(connection, _):
        connection.execute("PRAGMA foreign_keys=ON")

    tables = [
        table
        for name, table in Base.metadata.tables.items()
        if name == "resolutions"
        or name.startswith("resolution_")
        or name in {"users", "controlled_documents"}
    ]
    Base.metadata.create_all(engine, tables=tables)
    return engine


def test_repository_loads_a_reconstructible_record_without_domain_logic():
    engine = sqlite_engine()
    now = datetime(2026, 7, 24, tzinfo=timezone.utc)

    with Session(engine) as session:
        repository = ResolutionRepository(session)
        resolution = Resolution(
            public_id="resolution-test-1",
            resolution_type="example.resolve_case",
            definition_version="1.0",
            source="system",
            subject_type="example",
            subject_id="42",
            title="Caso persistente",
        )
        repository.add(resolution)
        session.flush()
        repository.add(
            ResolutionProblem(
                resolution_id=resolution.id,
                problem_code="example_problem",
                summary="Problema original",
                detected_by="test",
                detected_at=now,
            )
        )
        session.commit()

        record = repository.load_record(resolution.id)

        assert record is not None
        assert record.resolution.public_id == "resolution-test-1"
        assert record.problem is not None
        assert record.problem.problem_code == "example_problem"
        assert record.plans == ()
        assert record.audit_events == ()


def test_repository_supports_public_and_idempotent_request_lookup():
    engine = sqlite_engine()

    with Session(engine) as session:
        repository = ResolutionRepository(session)
        resolution = Resolution(
            public_id="resolution-test-2",
            resolution_type="example.resolve_case",
            definition_version="1.0",
            source="module",
            subject_type="example",
            subject_id="84",
            request_key="request-test-2",
            title="Lookup",
        )
        repository.add(resolution)
        session.commit()

        assert repository.get_by_public_id("resolution-test-2") is not None
        assert repository.get_by_request_key("request-test-2") is not None
        assert repository.load_record(999999) is None
