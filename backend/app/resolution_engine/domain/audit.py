"""Modelo puro de auditoría, evidencia y reconstrucción verificable."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import StrEnum
from types import MappingProxyType
from typing import Any, Mapping

from app.resolution_engine.domain.canonical import canonical_sha256
from app.resolution_engine.domain.exceptions import InvalidAuditEvidenceError


class EvidenceIntegrity(StrEnum):
    """Resultado estable de verificar una pieza de evidencia."""

    VERIFIED = "verified"
    ASSERTED = "asserted"
    NOT_HASHED = "not_hashed"
    INVALID = "invalid"


class IntegritySeverity(StrEnum):
    ERROR = "error"
    WARNING = "warning"


@dataclass(frozen=True, slots=True)
class EvidenceLink:
    """Relación explícita entre dos piezas del mismo expediente."""

    target_key: str
    relation: str
    expected_hash: str | None = None
    required: bool = True

    def __post_init__(self) -> None:
        if not self.target_key.strip() or not self.relation.strip():
            raise InvalidAuditEvidenceError(
                "evidence links require target_key and relation"
            )
        if self.expected_hash is not None and len(self.expected_hash) != 64:
            raise InvalidAuditEvidenceError(
                "expected evidence hash must be SHA-256"
            )


@dataclass(frozen=True, slots=True)
class EvidenceNode:
    """Proyección inmutable de una fila o hecho auditable."""

    key: str
    kind: str
    resolution_id: int
    payload: Mapping[str, Any]
    occurred_at: datetime | None = None
    actor_id: str | None = None
    correlation_id: str | None = None
    stored_hash: str | None = None
    hash_payload: Any | None = None
    links: tuple[EvidenceLink, ...] = ()
    summary: str | None = None

    def __post_init__(self) -> None:
        if not self.key.strip() or not self.kind.strip():
            raise InvalidAuditEvidenceError(
                "evidence nodes require key and kind"
            )
        if self.resolution_id <= 0:
            raise InvalidAuditEvidenceError(
                "evidence resolution_id must be positive"
            )
        if self.occurred_at is not None and (
            self.occurred_at.tzinfo is None
            or self.occurred_at.utcoffset() is None
        ):
            raise InvalidAuditEvidenceError(
                "evidence occurred_at must include timezone"
            )
        if self.stored_hash is not None and len(self.stored_hash) != 64:
            raise InvalidAuditEvidenceError(
                "stored evidence hash must be SHA-256"
            )
        object.__setattr__(
            self,
            "payload",
            MappingProxyType(dict(self.payload)),
        )
        object.__setattr__(self, "links", tuple(self.links))

    def snapshot(self) -> dict[str, Any]:
        return {
            "key": self.key,
            "kind": self.kind,
            "resolution_id": self.resolution_id,
            "payload": dict(self.payload),
            "occurred_at": self.occurred_at,
            "actor_id": self.actor_id,
            "correlation_id": self.correlation_id,
            "stored_hash": self.stored_hash,
            "links": [
                {
                    "target_key": link.target_key,
                    "relation": link.relation,
                    "expected_hash": link.expected_hash,
                    "required": link.required,
                }
                for link in self.links
            ],
        }


@dataclass(frozen=True, slots=True)
class ResolutionAuditSnapshot:
    """Expediente normalizado entregado al dominio por un adaptador."""

    resolution_id: int
    public_id: str
    status: str
    version: int
    nodes: tuple[EvidenceNode, ...]

    def __post_init__(self) -> None:
        if self.resolution_id <= 0 or not self.public_id.strip():
            raise InvalidAuditEvidenceError(
                "audit snapshot requires resolution identity"
            )
        if self.version <= 0 or not self.status.strip():
            raise InvalidAuditEvidenceError(
                "audit snapshot requires status and positive version"
            )
        object.__setattr__(self, "nodes", tuple(self.nodes))


@dataclass(frozen=True, slots=True)
class IntegrityIssue:
    code: str
    node_key: str
    relation: str | None = None
    expected: str | None = None
    actual: str | None = None
    severity: IntegritySeverity = IntegritySeverity.ERROR


@dataclass(frozen=True, slots=True)
class EvidenceVerification:
    node_key: str
    integrity: EvidenceIntegrity
    calculated_hash: str | None = None


@dataclass(frozen=True, slots=True)
class TimelineEntry:
    sequence: int
    node_key: str
    kind: str
    occurred_at: datetime
    actor_id: str | None
    correlation_id: str | None
    summary: str
    integrity: EvidenceIntegrity


@dataclass(frozen=True, slots=True)
class AuditReport:
    resolution_id: int
    public_id: str
    status: str
    version: int
    is_valid: bool
    record_hash: str
    verifications: tuple[EvidenceVerification, ...]
    issues: tuple[IntegrityIssue, ...]
    timeline: tuple[TimelineEntry, ...]
    nodes: tuple[EvidenceNode, ...] = field(repr=False)

    def evidence(
        self,
        *,
        kinds: tuple[str, ...] = (),
        correlation_id: str | None = None,
    ) -> tuple[EvidenceNode, ...]:
        """Consulta evidencia sin alterar el conjunto verificado."""

        allowed = set(kinds)
        return tuple(
            node
            for node in self.nodes
            if (not allowed or node.kind in allowed)
            and (
                correlation_id is None
                or node.correlation_id == correlation_id
            )
        )


class EvidenceRegistry:
    """Índice local de evidencia; no persiste ni consulta infraestructura."""

    def __init__(self, nodes: tuple[EvidenceNode, ...]) -> None:
        self._nodes = tuple(nodes)
        grouped: dict[str, list[EvidenceNode]] = {}
        for node in self._nodes:
            grouped.setdefault(node.key, []).append(node)
        self._grouped = grouped

    @property
    def duplicate_keys(self) -> tuple[str, ...]:
        return tuple(
            sorted(
                key
                for key, nodes in self._grouped.items()
                if len(nodes) > 1
            )
        )

    def get(self, key: str) -> EvidenceNode | None:
        nodes = self._grouped.get(key, ())
        return nodes[0] if len(nodes) == 1 else None


class ResolutionTimeline:
    """Construye una cronología estable a partir de hechos persistidos."""

    @staticmethod
    def build(
        nodes: tuple[EvidenceNode, ...],
        verifications: Mapping[str, EvidenceIntegrity],
    ) -> tuple[TimelineEntry, ...]:
        ordered = sorted(
            (node for node in nodes if node.occurred_at is not None),
            key=lambda node: (
                node.occurred_at,
                int(node.payload.get("sequence", 0)),
                node.kind,
                node.key,
            ),
        )
        return tuple(
            TimelineEntry(
                sequence=index,
                node_key=node.key,
                kind=node.kind,
                occurred_at=node.occurred_at,
                actor_id=node.actor_id,
                correlation_id=node.correlation_id,
                summary=node.summary or node.kind,
                integrity=verifications[node.key],
            )
            for index, node in enumerate(ordered, start=1)
            if node.occurred_at is not None
        )


class AuditEngine:
    """Verifica hashes, alcance, secuencia y correlaciones del expediente."""

    def verify(self, snapshot: ResolutionAuditSnapshot) -> AuditReport:
        registry = EvidenceRegistry(snapshot.nodes)
        issues: list[IntegrityIssue] = []
        for key in registry.duplicate_keys:
            issues.append(
                IntegrityIssue(
                    code="duplicate_evidence_key",
                    node_key=key,
                )
            )

        verifications: list[EvidenceVerification] = []
        integrity_by_key: dict[str, EvidenceIntegrity] = {}
        for node in snapshot.nodes:
            integrity, calculated_hash = self._verify_hash(node)
            if node.key not in integrity_by_key:
                integrity_by_key[node.key] = integrity
            verifications.append(
                EvidenceVerification(
                    node_key=node.key,
                    integrity=integrity,
                    calculated_hash=calculated_hash,
                )
            )
            if node.resolution_id != snapshot.resolution_id:
                issues.append(
                    IntegrityIssue(
                        code="foreign_resolution_evidence",
                        node_key=node.key,
                        expected=str(snapshot.resolution_id),
                        actual=str(node.resolution_id),
                    )
                )
            if integrity is EvidenceIntegrity.INVALID:
                issues.append(
                    IntegrityIssue(
                        code="evidence_hash_mismatch",
                        node_key=node.key,
                        expected=node.stored_hash,
                        actual=calculated_hash,
                    )
                )

        self._verify_links(snapshot, registry, issues)
        self._verify_audit_sequence(snapshot.nodes, issues)
        self._verify_lifecycle_chain(snapshot, issues)
        if not any(node.kind == "audit_event" for node in snapshot.nodes):
            issues.append(
                IntegrityIssue(
                    code="audit_history_missing",
                    node_key=f"resolution:{snapshot.resolution_id}",
                )
            )

        record_hash = canonical_sha256(
            {
                "resolution_id": snapshot.resolution_id,
                "public_id": snapshot.public_id,
                "status": snapshot.status,
                "version": snapshot.version,
                "nodes": [
                    node.snapshot()
                    for node in sorted(
                        snapshot.nodes,
                        key=lambda item: item.key,
                    )
                ],
            }
        )
        timeline = ResolutionTimeline.build(
            snapshot.nodes,
            integrity_by_key,
        )
        return AuditReport(
            resolution_id=snapshot.resolution_id,
            public_id=snapshot.public_id,
            status=snapshot.status,
            version=snapshot.version,
            is_valid=not any(
                issue.severity is IntegritySeverity.ERROR
                for issue in issues
            ),
            record_hash=record_hash,
            verifications=tuple(verifications),
            issues=tuple(issues),
            timeline=timeline,
            nodes=snapshot.nodes,
        )

    @staticmethod
    def _verify_hash(
        node: EvidenceNode,
    ) -> tuple[EvidenceIntegrity, str | None]:
        if node.stored_hash is None:
            return EvidenceIntegrity.NOT_HASHED, None
        if node.hash_payload is None:
            return EvidenceIntegrity.ASSERTED, None
        calculated = canonical_sha256(node.hash_payload)
        return (
            (
                EvidenceIntegrity.VERIFIED
                if calculated == node.stored_hash
                else EvidenceIntegrity.INVALID
            ),
            calculated,
        )

    @staticmethod
    def _verify_links(
        snapshot: ResolutionAuditSnapshot,
        registry: EvidenceRegistry,
        issues: list[IntegrityIssue],
    ) -> None:
        for node in snapshot.nodes:
            for link in node.links:
                target = registry.get(link.target_key)
                if target is None:
                    if link.required:
                        issues.append(
                            IntegrityIssue(
                                code="evidence_link_missing",
                                node_key=node.key,
                                relation=link.relation,
                                expected=link.target_key,
                            )
                        )
                    continue
                if target.resolution_id != snapshot.resolution_id:
                    issues.append(
                        IntegrityIssue(
                            code="evidence_link_crosses_resolution",
                            node_key=node.key,
                            relation=link.relation,
                            expected=str(snapshot.resolution_id),
                            actual=str(target.resolution_id),
                        )
                    )
                if (
                    link.expected_hash is not None
                    and target.stored_hash != link.expected_hash
                ):
                    issues.append(
                        IntegrityIssue(
                            code="evidence_link_hash_mismatch",
                            node_key=node.key,
                            relation=link.relation,
                            expected=link.expected_hash,
                            actual=target.stored_hash,
                        )
                    )

    @staticmethod
    def _verify_audit_sequence(
        nodes: tuple[EvidenceNode, ...],
        issues: list[IntegrityIssue],
    ) -> None:
        events = sorted(
            (
                node
                for node in nodes
                if node.kind == "audit_event"
            ),
            key=lambda node: int(node.payload["sequence"]),
        )
        for expected, node in enumerate(events, start=1):
            actual = int(node.payload["sequence"])
            if actual != expected:
                issues.append(
                    IntegrityIssue(
                        code="audit_sequence_gap",
                        node_key=node.key,
                        expected=str(expected),
                        actual=str(actual),
                    )
                )

    @staticmethod
    def _verify_lifecycle_chain(
        snapshot: ResolutionAuditSnapshot,
        issues: list[IntegrityIssue],
    ) -> None:
        events = sorted(
            (
                node
                for node in snapshot.nodes
                if node.kind == "audit_event"
                and node.payload.get("new_state") is not None
                and (
                    node.payload.get("event_type") == "resolution.created"
                    or str(node.payload.get("event_type", "")).startswith(
                        "resolution.lifecycle."
                    )
                )
            ),
            key=lambda node: int(node.payload["sequence"]),
        )
        if not events:
            return
        complete_prefix = events[0].payload.get("previous_state") is None
        if not complete_prefix:
            issues.append(
                IntegrityIssue(
                    code="lifecycle_audit_prefix_unavailable",
                    node_key=events[0].key,
                    actual=str(events[0].payload.get("previous_state")),
                )
            )
        previous_state: str | None = None
        for index, node in enumerate(events):
            actual_previous = node.payload.get("previous_state")
            if index and actual_previous != previous_state:
                issues.append(
                    IntegrityIssue(
                        code="lifecycle_audit_chain_broken",
                        node_key=node.key,
                        expected=previous_state,
                        actual=actual_previous,
                    )
                )
            previous_state = str(node.payload["new_state"])
        if previous_state != snapshot.status:
            issues.append(
                IntegrityIssue(
                    code="lifecycle_audit_state_mismatch",
                    node_key=events[-1].key,
                    expected=snapshot.status,
                    actual=previous_state,
                )
            )
        if complete_prefix and len(events) != snapshot.version:
            issues.append(
                IntegrityIssue(
                    code="lifecycle_audit_version_mismatch",
                    node_key=events[-1].key,
                    expected=str(snapshot.version),
                    actual=str(len(events)),
                )
            )
