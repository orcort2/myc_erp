"""Proyección explícita del expediente SQL a evidencia pura."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Iterable

from sqlalchemy import inspect
from app.resolution_engine.domain.audit import (
    EvidenceLink,
    EvidenceNode,
    ResolutionAuditSnapshot,
)
from app.resolution_engine.infrastructure.repositories import (
    ResolutionRecord,
)


class AuditProjector:
    """Mantiene localizable la traducción entre relaciones SQL y evidencia."""

    def __init__(self, record: ResolutionRecord) -> None:
        self.record = record
        self.resolution_id = int(record.resolution.id)
        self.nodes: list[EvidenceNode] = []

    def project(self) -> ResolutionAuditSnapshot:
        self._root()
        self._planning()
        self._governance()
        self._execution()
        self._security_and_operations()
        self._compensation()
        root = self.record.resolution
        return ResolutionAuditSnapshot(
            resolution_id=self.resolution_id,
            public_id=root.public_id,
            status=root.status,
            version=root.version,
            nodes=tuple(self.nodes),
        )

    def _root(self) -> None:
        row = self.record.resolution
        links = [
            self._link("problem", row.id, "describes", required=False),
        ]
        if row.current_context_snapshot_id is not None:
            links.append(
                self._link(
                    "context_snapshot",
                    row.current_context_snapshot_id,
                    "current_context",
                )
            )
        if row.current_strategy_selection_id is not None:
            links.append(
                self._link(
                    "strategy_selection",
                    row.current_strategy_selection_id,
                    "current_strategy",
                )
            )
        if row.current_plan_id is not None:
            links.append(
                self._link("plan", row.current_plan_id, "current_plan")
            )
        self._add(
            "resolution",
            row,
            occurred_at=self._time(row, "created_at"),
            actor_id=row.requested_by_actor_id,
            correlation_id=row.correlation_id,
            links=links,
            summary=f"resolution {row.public_id} created",
        )
        if self.record.problem is not None:
            problem = self.record.problem
            self._add(
                "problem",
                problem,
                occurred_at=self._time(problem, "detected_at", "created_at"),
                actor_id=problem.reported_by_actor_id,
                links=(self._link("resolution", row.id, "belongs_to"),),
                summary=problem.summary,
                key_id=row.id,
            )

    def _planning(self) -> None:
        for row in self.record.context_snapshots:
            self._add(
                "context_snapshot",
                row,
                occurred_at=self._time(row, "captured_at"),
                actor_id=row.captured_by_actor_id,
                stored_hash=row.context_hash,
                links=(self._root_link(),),
                summary=f"context {row.sequence}:{row.snapshot_type}",
            )
        for row in self.record.analyses:
            self._add(
                "analysis",
                row,
                occurred_at=self._time(row, "analyzed_at"),
                actor_id=row.analyzed_by,
                stored_hash=row.analysis_hash,
                links=(
                    self._root_link(),
                    self._link(
                        "context_snapshot",
                        row.context_snapshot_id,
                        "analyzes_context",
                    ),
                ),
                summary=f"analysis {row.analysis_version}:{row.status}",
            )
        for row in self.record.strategy_selections:
            self._add(
                "strategy_selection",
                row,
                occurred_at=self._time(row, "selected_at"),
                actor_id=row.selected_by_actor_id,
                links=(
                    self._root_link(),
                    self._link("analysis", row.analysis_id, "selected_from"),
                ),
                summary=f"strategy {row.strategy_key}@{row.strategy_version}",
            )
        for row in self.record.plans:
            self._add(
                "plan",
                row,
                occurred_at=self._time(row, "created_at", "activated_at"),
                actor_id=row.created_by_actor_id,
                stored_hash=row.plan_hash,
                links=(
                    self._root_link(),
                    self._link(
                        "strategy_selection",
                        row.strategy_selection_id,
                        "uses_strategy",
                    ),
                    self._link(
                        "context_snapshot",
                        row.context_snapshot_id,
                        "uses_context",
                    ),
                ),
                summary=f"plan v{row.version}:{row.status}",
            )
        for row in self.record.plan_steps:
            self._add(
                "plan_step",
                row,
                occurred_at=self._time(row, "created_at"),
                stored_hash=row.step_hash,
                links=(self._link("plan", row.plan_id, "belongs_to"),),
                summary=f"plan step {row.sequence}:{row.step_key}",
            )
        for row in self.record.plan_step_dependencies:
            self._add(
                "plan_step_dependency",
                row,
                links=(
                    self._link("plan", row.plan_id, "belongs_to"),
                    self._link("plan_step", row.step_id, "dependent_step"),
                    self._link(
                        "plan_step",
                        row.depends_on_step_id,
                        "depends_on",
                    ),
                ),
                summary="plan step dependency",
            )
        plan_hashes = {row.id: row.plan_hash for row in self.record.plans}
        for row in self.record.simulations:
            self._add(
                "simulation",
                row,
                occurred_at=self._time(row, "simulated_at"),
                actor_id=row.simulated_by,
                stored_hash=row.simulation_hash,
                links=(
                    self._root_link(),
                    self._link(
                        "plan",
                        row.plan_id,
                        "simulates_plan",
                        expected_hash=plan_hashes.get(row.plan_id),
                    ),
                    self._link(
                        "context_snapshot",
                        row.context_snapshot_id,
                        "simulates_context",
                    ),
                ),
                summary=f"simulation {row.simulation_version}:{row.status}",
            )

    def _governance(self) -> None:
        for row in self.record.authorization_requests:
            self._add(
                "authorization_request",
                row,
                occurred_at=self._time(row, "requested_at"),
                actor_id=row.requested_by_actor_id,
                stored_hash=None,
                links=(
                    self._root_link(),
                    self._link(
                        "plan",
                        row.plan_id,
                        "authorizes_plan",
                        expected_hash=row.plan_hash,
                    ),
                    self._link(
                        "simulation",
                        row.simulation_id,
                        "authorizes_simulation",
                        expected_hash=row.simulation_hash,
                    ),
                ),
                summary=f"authorization request:{row.status}",
            )
        request_ids = {
            row.id: row for row in self.record.authorization_requests
        }
        for row in self.record.authorization_decisions:
            request = request_ids.get(row.authorization_request_id)
            self._add(
                "authorization_decision",
                row,
                occurred_at=self._time(row, "decided_at"),
                actor_id=row.approver_actor_id,
                links=(
                    self._link(
                        "authorization_request",
                        row.authorization_request_id,
                        "decides",
                    ),
                    self._root_link(),
                ),
                summary=f"authorization decision:{row.decision}",
                resolution_id=(
                    request.resolution_id
                    if request is not None
                    else self.resolution_id
                ),
            )
        for row in self.record.revalidations:
            self._add(
                "revalidation",
                row,
                occurred_at=self._time(row, "revalidated_at"),
                actor_id=row.revalidated_by,
                stored_hash=row.revalidation_hash,
                links=(
                    self._root_link(),
                    self._link("plan", row.plan_id, "revalidates_plan"),
                    self._link(
                        "context_snapshot",
                        row.previous_context_snapshot_id,
                        "previous_context",
                    ),
                    self._link(
                        "context_snapshot",
                        row.current_context_snapshot_id,
                        "current_context",
                    ),
                ),
                summary=f"revalidation:{row.status}",
            )

    def _execution(self) -> None:
        for row in self.record.executions:
            self._add(
                "execution",
                row,
                occurred_at=self._time(
                    row,
                    "started_at",
                    "created_at",
                    "completed_at",
                ),
                actor_id=row.executed_by_actor_id,
                correlation_id=row.correlation_id,
                links=(
                    self._root_link(),
                    self._link("plan", row.plan_id, "executes_plan"),
                    self._link(
                        "revalidation",
                        row.revalidation_id,
                        "uses_revalidation",
                    ),
                ),
                summary=f"execution {row.attempt_number}:{row.status}",
            )
        execution_by_id = {
            row.id: row for row in self.record.executions
        }
        for row in self.record.step_executions:
            execution = execution_by_id.get(row.execution_id)
            self._add(
                "step_execution",
                row,
                occurred_at=self._time(
                    row,
                    "started_at",
                    "created_at",
                    "completed_at",
                ),
                correlation_id=(
                    execution.correlation_id if execution else None
                ),
                links=(
                    self._link("execution", row.execution_id, "belongs_to"),
                    self._link("plan", row.plan_id, "uses_plan"),
                    self._link(
                        "plan_step",
                        row.plan_step_id,
                        "executes_step",
                    ),
                ),
                summary=f"step execution:{row.status}",
            )
        for row in self.record.entity_references:
            links = [self._root_link()]
            if row.execution_id is not None:
                links.append(
                    self._link(
                        "execution",
                        row.execution_id,
                        "produced_by_execution",
                    )
                )
            if row.step_execution_id is not None:
                links.append(
                    self._link(
                        "step_execution",
                        row.step_execution_id,
                        "produced_by_step",
                    )
                )
            self._add(
                "entity_reference",
                row,
                occurred_at=self._time(row, "created_at"),
                links=links,
                summary=(
                    f"{row.relationship_type}:{row.entity_type}:"
                    f"{row.entity_id}"
                ),
            )
        if self.record.result is not None:
            row = self.record.result
            links = [self._root_link()]
            if row.execution_id is not None:
                links.append(
                    self._link(
                        "execution",
                        row.execution_id,
                        "concludes_execution",
                    )
                )
            if row.final_context_snapshot_id is not None:
                links.append(
                    self._link(
                        "context_snapshot",
                        row.final_context_snapshot_id,
                        "final_context",
                    )
                )
            self._add(
                "result",
                row,
                occurred_at=self._time(row, "completed_at"),
                actor_id=row.completed_by_actor_id,
                stored_hash=row.result_hash,
                links=links,
                summary=f"result:{row.status}",
                key_id=self.resolution_id,
            )

    def _security_and_operations(self) -> None:
        for row in self.record.audit_events:
            links = [self._root_link()]
            if row.plan_id is not None:
                links.append(
                    self._link("plan", row.plan_id, "references_plan")
                )
            if row.execution_id is not None:
                links.append(
                    self._link(
                        "execution",
                        row.execution_id,
                        "references_execution",
                    )
                )
            self._add(
                "audit_event",
                row,
                occurred_at=self._time(row, "occurred_at"),
                actor_id=row.actor_id,
                correlation_id=row.correlation_id,
                stored_hash=row.payload_hash,
                hash_payload=row.payload,
                links=links,
                summary=row.event_type,
            )
        for row in self.record.security_decisions:
            links = [self._root_link()]
            if row.plan_id is not None:
                links.append(
                    self._link(
                        "plan",
                        row.plan_id,
                        "security_plan",
                        expected_hash=row.plan_hash,
                    )
                )
            if row.simulation_id is not None:
                links.append(
                    self._link(
                        "simulation",
                        row.simulation_id,
                        "security_simulation",
                        expected_hash=row.simulation_hash,
                    )
                )
            if row.authorization_request_id is not None:
                links.append(
                    self._link(
                        "authorization_request",
                        row.authorization_request_id,
                        "security_authorization",
                    )
                )
            self._add(
                "security_decision",
                row,
                occurred_at=self._time(row, "evaluated_at"),
                actor_id=row.actor_id,
                correlation_id=row.correlation_id,
                stored_hash=row.evidence_hash,
                hash_payload=row.context_snapshot.get("evidence_payload"),
                links=links,
                summary=f"security {row.action}:{row.outcome}",
            )
        for row in self.record.idempotency_records:
            links = [self._root_link()]
            if row.execution_id is not None:
                links.append(
                    self._link(
                        "execution",
                        row.execution_id,
                        "idempotency_execution",
                    )
                )
            if row.step_execution_id is not None:
                links.append(
                    self._link(
                        "step_execution",
                        row.step_execution_id,
                        "idempotency_step",
                    )
                )
            self._add(
                "idempotency_record",
                row,
                occurred_at=self._time(row, "created_at", "completed_at"),
                stored_hash=row.request_hash,
                links=links,
                summary=f"idempotency {row.scope}:{row.status}",
            )
        for row in self.record.locks:
            self._add(
                "lock",
                row,
                occurred_at=self._time(row, "acquired_at"),
                links=(self._root_link(),),
                summary=f"lock {row.lock_type}:{row.lock_key}",
            )
        for row in self.record.outbox_events:
            self._add(
                "outbox_event",
                row,
                occurred_at=self._time(row, "occurred_at"),
                correlation_id=row.correlation_id,
                stored_hash=row.payload_hash,
                hash_payload=row.payload,
                links=(self._root_link(),),
                summary=f"outbox {row.event_type}:{row.status}",
            )
        for row in self.record.evidence_references:
            self._add(
                "evidence_reference",
                row,
                occurred_at=self._time(row, "uploaded_at"),
                actor_id=row.uploaded_by_actor_id,
                stored_hash=row.checksum,
                links=(self._root_link(),),
                summary=f"evidence reference:{row.evidence_type}",
            )

    def _compensation(self) -> None:
        steps_by_plan: dict[int, list[Any]] = {}
        for step in self.record.compensation_plan_steps:
            steps_by_plan.setdefault(step.plan_id, []).append(step)
        for row in self.record.compensation_plans:
            ordered_steps = sorted(
                steps_by_plan.get(row.id, ()),
                key=lambda item: item.sequence,
            )
            hash_payload = {
                "resolution_id": row.resolution_id,
                "source_execution_id": row.source_execution_id,
                "strategy": row.strategy,
                "reason": row.reason,
                "steps": [
                    self._compensation_step_snapshot(step)
                    for step in ordered_steps
                ],
            }
            self._add(
                "compensation_plan",
                row,
                occurred_at=self._time(row, "created_at"),
                actor_id=row.created_by_actor_id,
                correlation_id=row.correlation_id,
                stored_hash=row.plan_hash,
                hash_payload=hash_payload,
                links=(
                    self._root_link(),
                    self._link(
                        "execution",
                        row.source_execution_id,
                        "compensates_execution",
                    ),
                    self._link(
                        "security_decision",
                        row.security_decision_id,
                        "authorized_by",
                    ),
                ),
                summary=f"compensation plan:{row.strategy}",
            )
        for row in self.record.compensation_plan_steps:
            self._add(
                "compensation_plan_step",
                row,
                occurred_at=self._time(row, "created_at"),
                stored_hash=row.step_hash,
                hash_payload=self._compensation_step_snapshot(row),
                links=(
                    self._link(
                        "compensation_plan",
                        row.plan_id,
                        "belongs_to",
                    ),
                    self._link(
                        "execution",
                        row.source_execution_id,
                        "source_execution",
                    ),
                    self._link(
                        "plan_step",
                        row.source_plan_step_id,
                        "source_plan_step",
                    ),
                    self._link(
                        "step_execution",
                        row.source_step_execution_id,
                        "source_effect",
                    ),
                ),
                summary=(
                    f"compensation step {row.sequence}:"
                    f"{row.source_step_key}"
                ),
            )
        for row in self.record.compensation_executions:
            self._add(
                "compensation_execution",
                row,
                occurred_at=self._time(row, "started_at"),
                actor_id=row.executed_by_actor_id,
                correlation_id=row.correlation_id,
                stored_hash=row.request_hash,
                links=(
                    self._root_link(),
                    self._link(
                        "compensation_plan",
                        row.plan_id,
                        "executes_compensation_plan",
                    ),
                    self._link(
                        "execution",
                        row.source_execution_id,
                        "source_execution",
                    ),
                ),
                summary=f"compensation execution:{row.status}",
            )
        for row in self.record.compensation_step_executions:
            self._add(
                "compensation_step_execution",
                row,
                occurred_at=self._time(
                    row,
                    "started_at",
                    "created_at",
                    "completed_at",
                ),
                stored_hash=row.request_hash,
                links=(
                    self._link(
                        "compensation_execution",
                        row.execution_id,
                        "belongs_to",
                    ),
                    self._link(
                        "compensation_plan_step",
                        row.plan_step_id,
                        "executes_compensation_step",
                    ),
                    self._link(
                        "step_execution",
                        row.source_step_execution_id,
                        "compensates_effect",
                    ),
                ),
                summary=f"compensation step execution:{row.status}",
            )

    def _add(
        self,
        kind: str,
        row: Any,
        *,
        occurred_at: datetime | None = None,
        actor_id: str | None = None,
        correlation_id: str | None = None,
        stored_hash: str | None = None,
        hash_payload: Any | None = None,
        links: Iterable[EvidenceLink] = (),
        summary: str | None = None,
        key_id: int | None = None,
        resolution_id: int | None = None,
    ) -> None:
        self.nodes.append(
            EvidenceNode(
                key=f"{kind}:{key_id if key_id is not None else row.id}",
                kind=kind,
                resolution_id=(
                    int(resolution_id)
                    if resolution_id is not None
                    else int(
                        getattr(row, "resolution_id", self.resolution_id)
                    )
                ),
                payload=self._payload(row),
                occurred_at=occurred_at,
                actor_id=actor_id,
                correlation_id=correlation_id,
                stored_hash=stored_hash,
                hash_payload=hash_payload,
                links=tuple(links),
                summary=summary,
            )
        )

    def _root_link(self) -> EvidenceLink:
        return self._link(
            "resolution",
            self.resolution_id,
            "belongs_to",
        )

    @staticmethod
    def _link(
        kind: str,
        identifier: int,
        relation: str,
        *,
        expected_hash: str | None = None,
        required: bool = True,
    ) -> EvidenceLink:
        return EvidenceLink(
            target_key=f"{kind}:{identifier}",
            relation=relation,
            expected_hash=expected_hash,
            required=required,
        )

    @staticmethod
    def _payload(row: Any) -> dict[str, Any]:
        return {
            attribute.key: _normalize_persisted_value(
                getattr(row, attribute.key)
            )
            for attribute in inspect(row.__class__).column_attrs
        }

    @staticmethod
    def _time(row: Any, *names: str) -> datetime | None:
        for name in names:
            value = getattr(row, name, None)
            if value is None:
                continue
            if value.tzinfo is None or value.utcoffset() is None:
                return value.replace(tzinfo=timezone.utc)
            return value
        return None

    @staticmethod
    def _compensation_step_snapshot(row: Any) -> dict[str, Any]:
        return {
            "sequence": row.sequence,
            "source_plan_step_id": row.source_plan_step_id,
            "source_step_execution_id": row.source_step_execution_id,
            "source_step_key": row.source_step_key,
            "operation_key": row.operation_key,
            "owner_module": row.owner_module,
            "input_payload": row.input_payload,
            "dependency_source_step_ids": (
                row.dependency_source_step_ids
            ),
        }


def _normalize_persisted_value(value: Any) -> Any:
    """Normaliza la pérdida de timezone de SQLite en el borde SQL."""

    if isinstance(value, datetime):
        if value.tzinfo is None or value.utcoffset() is None:
            return value.replace(tzinfo=timezone.utc)
        return value
    if isinstance(value, dict):
        return {
            key: _normalize_persisted_value(item)
            for key, item in value.items()
        }
    if isinstance(value, (list, tuple)):
        return [_normalize_persisted_value(item) for item in value]
    return value
