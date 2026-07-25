"""Catálogos normativos del Motor de Resoluciones."""

from enum import StrEnum


class ResolutionStatus(StrEnum):
    DRAFT = "draft"
    CONTEXT_READY = "context_ready"
    ANALYZED = "analyzed"
    PLAN_READY = "plan_ready"
    SIMULATED = "simulated"
    PENDING_AUTHORIZATION = "pending_authorization"
    AUTHORIZED = "authorized"
    REVALIDATING = "revalidating"
    READY_FOR_EXECUTION = "ready_for_execution"
    EXECUTING = "executing"
    COMPLETED = "completed"
    PARTIALLY_COMPLETED = "partially_completed"
    FAILED = "failed"
    BLOCKED = "blocked"
    REJECTED = "rejected"
    CANCELLED = "cancelled"
    SUPERSEDED = "superseded"
    NO_ACTION_REQUIRED = "no_action_required"


class ResolutionPriority(StrEnum):
    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
    CRITICAL = "critical"


class ResolutionSource(StrEnum):
    USER = "user"
    MODULE = "module"
    SYSTEM = "system"
    SYNC = "sync"
    MOBILE_APP = "mobile_app"
    SCHEDULED_PROCESS = "scheduled_process"
    ADMINISTRATOR = "administrator"


class AnalysisStatus(StrEnum):
    RESOLVABLE = "resolvable"
    NOT_RESOLVABLE = "not_resolvable"
    REQUIRES_INFORMATION = "requires_information"
    BLOCKED = "blocked"
    ALREADY_RESOLVED = "already_resolved"


class StrategySelectionMode(StrEnum):
    AUTOMATIC = "automatic"
    USER_SELECTED = "user_selected"
    POLICY_SELECTED = "policy_selected"
    SYSTEM_RECOMMENDED = "system_recommended"


class PlanStatus(StrEnum):
    DRAFT = "draft"
    READY = "ready"
    SIMULATED = "simulated"
    PENDING_AUTHORIZATION = "pending_authorization"
    AUTHORIZED = "authorized"
    INVALIDATED = "invalidated"
    EXECUTING = "executing"
    EXECUTED = "executed"
    FAILED = "failed"
    SUPERSEDED = "superseded"
    CANCELLED = "cancelled"


class SimulationStatus(StrEnum):
    VALID = "valid"
    VALID_WITH_WARNINGS = "valid_with_warnings"
    INVALID = "invalid"
    BLOCKED = "blocked"
    EXPIRED = "expired"


class AuthorizationRequestStatus(StrEnum):
    PENDING = "pending"
    PARTIALLY_APPROVED = "partially_approved"
    APPROVED = "approved"
    REJECTED = "rejected"
    EXPIRED = "expired"
    CANCELLED = "cancelled"
    INVALIDATED = "invalidated"


class AuthorizationDecision(StrEnum):
    APPROVED = "approved"
    REJECTED = "rejected"
    ABSTAINED = "abstained"
    REVOKED = "revoked"


class RevalidationStatus(StrEnum):
    VALID = "valid"
    VALID_WITH_WARNINGS = "valid_with_warnings"
    REQUIRES_NEW_PLAN = "requires_new_plan"
    NO_LONGER_RESOLVABLE = "no_longer_resolvable"
    BLOCKED = "blocked"


class ExecutionStatus(StrEnum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    PARTIALLY_COMPLETED = "partially_completed"
    FAILED = "failed"
    BLOCKED = "blocked"
    CANCELLED = "cancelled"
    COMPENSATING = "compensating"
    COMPENSATED = "compensated"


class StepExecutionStatus(StrEnum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    SKIPPED = "skipped"
    FAILED = "failed"
    BLOCKED = "blocked"
    COMPENSATING = "compensating"
    COMPENSATED = "compensated"
    COMPENSATION_FAILED = "compensation_failed"


class ResolutionResult(StrEnum):
    SUCCESS = "success"
    PARTIAL_SUCCESS = "partial_success"
    FAILED = "failed"
    CANCELLED = "cancelled"
    SUPERSEDED = "superseded"
    NO_ACTION_REQUIRED = "no_action_required"


class StepCriticality(StrEnum):
    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
    IRREVERSIBLE = "irreversible"


class ComponentKind(StrEnum):
    CONTEXT_PROVIDER = "context_provider"
    ANALYZER = "analyzer"
    STRATEGY_SELECTOR = "strategy_selector"
    PLAN_BUILDER = "plan_builder"
    SIMULATOR = "simulator"
    AUTHORIZATION_POLICY = "authorization_policy"
    PERMISSION_POLICY = "permission_policy"
    REVALIDATOR = "revalidator"
    EXECUTOR = "executor"


class ContextSnapshotType(StrEnum):
    INITIAL = "initial"
    ANALYSIS = "analysis"
    SIMULATION = "simulation"
    AUTHORIZATION = "authorization"
    REVALIDATION = "revalidation"
    PRE_EXECUTION = "pre_execution"
    POST_EXECUTION = "post_execution"
    FINAL = "final"


class EntityRelationshipType(StrEnum):
    SUBJECT = "subject"
    INPUT = "input"
    CREATED = "created"
    MODIFIED = "modified"
    PRESERVED = "preserved"
    CANCELLED = "cancelled"
    SUPERSEDED = "superseded"
    LINKED = "linked"
    REFERENCED = "referenced"


class IdempotencyScope(StrEnum):
    RESOLUTION_REQUEST = "resolution_request"
    RESOLUTION_EXECUTION = "resolution_execution"
    STEP_EXECUTION = "step_execution"
    DOMAIN_OPERATION = "domain_operation"
    OFFLINE_SYNC = "offline_sync"


class IdempotencyStatus(StrEnum):
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    EXPIRED = "expired"


class ResolutionLockType(StrEnum):
    PLANNING = "planning"
    AUTHORIZATION = "authorization"
    EXECUTION = "execution"
    COMPENSATION = "compensation"
    SUBJECT_ENTITY = "subject_entity"


class OutboxStatus(StrEnum):
    PENDING = "pending"
    PUBLISHED = "published"
    FAILED = "failed"
