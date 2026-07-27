from dataclasses import replace
from datetime import datetime, timedelta, timezone

import pytest

from app.resolution_engine.application.audit import AuditQueryService
from app.resolution_engine.contracts.audit import AuditQuery
from app.resolution_engine.domain.audit import (
    AuditEngine,
    EvidenceIntegrity,
    EvidenceLink,
    EvidenceNode,
    ResolutionAuditSnapshot,
)
from app.resolution_engine.domain.canonical import canonical_sha256
from app.resolution_engine.domain.exceptions import (
    AuditAccessDeniedError,
    AuditRecordNotFoundError,
    InvalidAuditEvidenceError,
)
from app.resolution_engine.domain.security import (
    ActorContext,
    ActorIdentity,
    ActorType,
    AuthenticationContext,
)

NOW = datetime(2026, 7, 27, 16, tzinfo=timezone.utc)


def node(
    *,
    key: str,
    kind: str,
    payload: dict,
    occurred_at: datetime | None = NOW,
    stored_hash: str | None = None,
    hash_payload=None,
    links: tuple[EvidenceLink, ...] = (),
    resolution_id: int = 1,
    correlation_id: str | None = "correlation-1",
) -> EvidenceNode:
    return EvidenceNode(
        key=key,
        kind=kind,
        resolution_id=resolution_id,
        payload=payload,
        occurred_at=occurred_at,
        stored_hash=stored_hash,
        hash_payload=hash_payload,
        links=links,
        correlation_id=correlation_id,
    )


def valid_snapshot() -> ResolutionAuditSnapshot:
    created = {
        "sequence": 1,
        "event": "created",
        "event_type": "resolution.created",
        "previous_state": None,
        "new_state": "draft",
    }
    completed = {
        "sequence": 2,
        "event": "completed",
        "event_type": "resolution.lifecycle.complete",
        "previous_state": "draft",
        "new_state": "completed",
    }
    return ResolutionAuditSnapshot(
        resolution_id=1,
        public_id="resolution-1",
        status="completed",
        version=2,
        nodes=(
            node(
                key="resolution:1",
                kind="resolution",
                payload={"id": 1, "status": "completed"},
                stored_hash="a" * 64,
            ),
            node(
                key="audit_event:10",
                kind="audit_event",
                payload=created,
                stored_hash=canonical_sha256(created),
                hash_payload=created,
                links=(
                    EvidenceLink(
                        target_key="resolution:1",
                        relation="belongs_to",
                        expected_hash="a" * 64,
                    ),
                ),
            ),
            node(
                key="audit_event:11",
                kind="audit_event",
                payload=completed,
                occurred_at=NOW + timedelta(seconds=1),
                stored_hash=canonical_sha256(completed),
                hash_payload=completed,
                links=(
                    EvidenceLink(
                        target_key="resolution:1",
                        relation="belongs_to",
                    ),
                ),
            ),
        ),
    )


def test_audit_engine_verifies_hashes_links_timeline_and_replay():
    engine = AuditEngine()

    first = engine.verify(valid_snapshot())
    second = engine.verify(valid_snapshot())

    assert first.is_valid
    assert first.issues == ()
    assert first.record_hash == second.record_hash
    assert [entry.sequence for entry in first.timeline] == [1, 2, 3]
    assert [
        item.integrity for item in first.verifications
    ] == [
        EvidenceIntegrity.ASSERTED,
        EvidenceIntegrity.VERIFIED,
        EvidenceIntegrity.VERIFIED,
    ]


@pytest.mark.parametrize(
    ("mutation", "expected_code"),
    [
        (
            lambda nodes: (
                nodes[0],
                replace(
                    nodes[1],
                    hash_payload={"sequence": 1, "event": "tampered"},
                ),
                nodes[2],
            ),
            "evidence_hash_mismatch",
        ),
        (
            lambda nodes: (
                nodes[0],
                nodes[1],
                node(
                    key="audit_event:11",
                    kind="audit_event",
                    payload={"sequence": 3},
                    stored_hash=canonical_sha256({"sequence": 3}),
                    hash_payload={"sequence": 3},
                ),
            ),
            "audit_sequence_gap",
        ),
        (
            lambda nodes: (
                nodes[0],
                node(
                    key="audit_event:10",
                    kind="audit_event",
                    payload=nodes[1].payload,
                    stored_hash=nodes[1].stored_hash,
                    hash_payload=nodes[1].hash_payload,
                    links=(
                        EvidenceLink(
                            target_key="plan:999",
                            relation="references_plan",
                        ),
                    ),
                ),
                nodes[2],
            ),
            "evidence_link_missing",
        ),
        (
            lambda nodes: (
                nodes[0],
                nodes[1],
                node(
                    key="audit_event:11",
                    kind="audit_event",
                    payload=nodes[2].payload,
                    stored_hash=nodes[2].stored_hash,
                    hash_payload=nodes[2].hash_payload,
                    resolution_id=2,
                ),
            ),
            "foreign_resolution_evidence",
        ),
        (
            lambda nodes: (
                nodes[0],
                nodes[1],
                replace(
                    nodes[2],
                    payload={
                        **dict(nodes[2].payload),
                        "previous_state": "unexpected",
                    },
                    stored_hash=canonical_sha256(
                        {
                            **dict(nodes[2].hash_payload),
                            "previous_state": "unexpected",
                        }
                    ),
                    hash_payload={
                        **dict(nodes[2].hash_payload),
                        "previous_state": "unexpected",
                    },
                ),
            ),
            "lifecycle_audit_chain_broken",
        ),
    ],
)
def test_audit_engine_reports_stable_integrity_errors(
    mutation,
    expected_code,
):
    source = valid_snapshot()
    snapshot = ResolutionAuditSnapshot(
        resolution_id=source.resolution_id,
        public_id=source.public_id,
        status=source.status,
        version=source.version,
        nodes=mutation(source.nodes),
    )

    report = AuditEngine().verify(snapshot)

    assert not report.is_valid
    assert expected_code in {issue.code for issue in report.issues}


def test_audit_engine_rejects_duplicate_keys_and_missing_history():
    root = node(
        key="resolution:1",
        kind="resolution",
        payload={"id": 1},
    )
    report = AuditEngine().verify(
        ResolutionAuditSnapshot(
            resolution_id=1,
            public_id="resolution-1",
            status="draft",
            version=1,
            nodes=(root, root),
        )
    )

    assert not report.is_valid
    assert {issue.code for issue in report.issues} == {
        "duplicate_evidence_key",
        "audit_history_missing",
    }


class MemoryAuditStore:
    def __init__(self, snapshot):
        self.snapshot = snapshot

    def load_audit_snapshot(self, resolution_id):
        if self.snapshot and self.snapshot.resolution_id == resolution_id:
            return self.snapshot
        return None


class MemoryAccessVerifier:
    def __init__(self, reasons=()):
        self.reasons = reasons

    def verify(self, query):
        return self.reasons


def query(resolution_id=1):
    return AuditQuery(
        resolution_id=resolution_id,
        security_decision_id=10,
        actor=ActorContext(
            identity=ActorIdentity(
                actor_id="auditor-1",
                actor_type=ActorType.HUMAN,
                principal="auditor@example.test",
                organization_id="organization-1",
            ),
            authentication=AuthenticationContext(
                authenticated_at=NOW - timedelta(minutes=1),
                method="test",
                session_id="audit-session",
                assurance_level="high",
                source="test",
                correlation_id="correlation-1",
            ),
        ),
        requested_at=NOW,
    )


def test_query_service_filters_without_weakening_full_verification():
    service = AuditQueryService(
        store=MemoryAuditStore(valid_snapshot()),
        access_verifier=MemoryAccessVerifier(),
    )

    events = service.evidence(query(), kinds=("audit_event",))
    timeline = service.timeline(
        query(),
        correlation_id="correlation-1",
    )

    assert len(events) == 2
    assert len(timeline) == 3
    with pytest.raises(AuditRecordNotFoundError):
        service.inspect(query(999))


def test_query_service_denies_before_loading_evidence():
    service = AuditQueryService(
        store=MemoryAuditStore(valid_snapshot()),
        access_verifier=MemoryAccessVerifier(("security_actor_mismatch",)),
    )

    with pytest.raises(AuditAccessDeniedError) as caught:
        service.inspect(query())

    assert caught.value.error_code == "audit_access_denied"
    assert caught.value.reasons == ("security_actor_mismatch",)


def test_audit_query_requires_timezone_aware_request_time():
    with pytest.raises(InvalidAuditEvidenceError):
        AuditQuery(
            resolution_id=1,
            security_decision_id=10,
            actor=query().actor,
            requested_at=NOW.replace(tzinfo=None),
        )
