from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from time import perf_counter
from time import sleep
from typing import Callable, Protocol

from .models import IssueSnapshot, OrchestrationAction


@dataclass(frozen=True, slots=True)
class MutationOperation:
    issue_id: str
    issue_identifier: str
    action_type: str
    operation_type: str
    payload: dict[str, object]


@dataclass(frozen=True, slots=True)
class AppliedMutation:
    operation_id: str
    operation: MutationOperation


@dataclass(frozen=True, slots=True)
class RejectedMutation:
    issue_id: str
    issue_identifier: str
    action_type: str
    reason: str
    classification: str


@dataclass(frozen=True, slots=True)
class FailedMutation:
    issue_id: str
    issue_identifier: str
    action_type: str
    reason: str
    attempts: int
    max_attempts: int
    backoff_schedule_ms: list[int]
    classification: str
    error_class: str | None
    downgraded_from_legacy: bool


@dataclass(frozen=True, slots=True)
class MutationAttemptMetadata:
    issue_id: str
    issue_identifier: str
    action_type: str
    operation_type: str
    attempts: int
    max_attempts: int
    backoff_schedule_ms: list[int]
    outcome: str
    failure_reason: str | None
    error_class: str | None
    downgraded_from_legacy: bool


@dataclass(frozen=True, slots=True)
class MutationExecutionReport:
    applied: list[AppliedMutation]
    rejected: list[RejectedMutation]
    failed: list[FailedMutation]
    rolled_back_operations: int
    dry_run: bool
    summary: dict[str, object]
    attempt_metadata: list[MutationAttemptMetadata]


@dataclass(frozen=True, slots=True)
class _RetryOutcome:
    applied: AppliedMutation
    attempts: int
    backoff_schedule_ms: list[int]
    recovered_after_retry: bool


@dataclass(frozen=True, slots=True)
class _RetryExhaustedError(Exception):
    operation: MutationOperation
    last_error: DispatcherExecutionError
    error_class: DispatcherErrorClass
    attempts: int
    max_attempts: int
    backoff_schedule_ms: list[int]
    downgraded_from_legacy: bool


@dataclass(frozen=True, slots=True)
class _NonRetryableDispatcherError(Exception):
    operation: MutationOperation
    error: DispatcherExecutionError
    error_class: DispatcherErrorClass
    attempts: int
    max_attempts: int
    backoff_schedule_ms: list[int]
    downgraded_from_legacy: bool


@dataclass(frozen=True, slots=True)
class _NormalizedDispatcherError:
    error: DispatcherExecutionError
    downgraded_from_legacy: bool


class DispatcherErrorClass(str, Enum):
    NETWORK = "network"
    AUTH = "auth"
    RATE_LIMIT = "rate_limit"
    POLICY = "policy"
    VALIDATION = "validation"
    INTERNAL = "internal"


class DispatcherExecutionError(RuntimeError):
    def __init__(self, *, error_class: DispatcherErrorClass, message: str):
        super().__init__(message)
        self.error_class = error_class


class MutationDispatcher(Protocol):
    def apply(self, operation: MutationOperation) -> AppliedMutation: ...

    def rollback(self, applied: AppliedMutation) -> None: ...


class DryRunMutationDispatcher:
    def __init__(self):
        self._counter = 0

    def apply(self, operation: MutationOperation) -> AppliedMutation:
        self._counter += 1
        return AppliedMutation(operation_id=f"dryrun-{self._counter}", operation=operation)

    def rollback(self, applied: AppliedMutation) -> None:
        _ = applied


class MutationExecutor:
    def __init__(
        self,
        max_operations_per_run: int = 20,
        enable_auto_comment: bool = True,
        enable_reassign_suggestion: bool = True,
        enable_escalation_flag: bool = True,
        pilot_issue_identifier_allowlist: set[str] | None = None,
        pilot_issue_id_allowlist: set[str] | None = None,
        pilot_action_type_allowlist: set[str] | None = None,
        pilot_kill_switch_enabled: bool = False,
        require_dry_run_first: bool = True,
        retry_max_attempts: int = 3,
        retry_initial_backoff_ms: int = 100,
        retry_backoff_multiplier: float = 2.0,
        retryable_error_classes: tuple[DispatcherErrorClass, ...] | None = None,
        sleep_fn: Callable[[float], None] = sleep,
    ):
        self._max_operations_per_run = max_operations_per_run
        self._enable_auto_comment = enable_auto_comment
        self._enable_reassign_suggestion = enable_reassign_suggestion
        self._enable_escalation_flag = enable_escalation_flag
        self._pilot_issue_identifier_allowlist = pilot_issue_identifier_allowlist
        self._pilot_issue_id_allowlist = pilot_issue_id_allowlist
        self._pilot_action_type_allowlist = pilot_action_type_allowlist
        self._pilot_kill_switch_enabled = pilot_kill_switch_enabled
        self._require_dry_run_first = require_dry_run_first
        self._retry_max_attempts = max(1, retry_max_attempts)
        self._retry_initial_backoff_ms = max(0, retry_initial_backoff_ms)
        self._retry_backoff_multiplier = max(1.0, retry_backoff_multiplier)
        self._retryable_error_classes = retryable_error_classes or (
            DispatcherErrorClass.NETWORK,
            DispatcherErrorClass.RATE_LIMIT,
        )
        self._sleep_fn = sleep_fn

    def execute(
        self,
        actions: list[OrchestrationAction],
        issues_by_id: dict[str, IssueSnapshot],
        dispatcher: MutationDispatcher | None = None,
    ) -> MutationExecutionReport:
        started = perf_counter()
        dispatch = dispatcher or DryRunMutationDispatcher()
        applied: list[AppliedMutation] = []
        rejected: list[RejectedMutation] = []
        failed: list[FailedMutation] = []
        rolled_back = 0
        transient_recovered = 0
        retry_exhausted = 0
        non_retryable_policy = 0
        downgraded_legacy_dispatcher_errors = 0
        dispatcher_error_classification = {item.value: 0 for item in DispatcherErrorClass}
        seen_issue_action_keys: set[tuple[str, str]] = set()
        actions_by_type: dict[str, int] = {}
        operations_by_type: dict[str, int] = {}
        rejected_by_reason: dict[str, int] = {}
        failed_by_reason: dict[str, int] = {}
        attempt_metadata: list[MutationAttemptMetadata] = []

        for action in actions:
            actions_by_type[action.action_type] = actions_by_type.get(action.action_type, 0) + 1
            issue = issues_by_id.get(action.issue_id)
            if issue is None:
                reason = "Source issue is missing from execution context."
                rejected.append(
                    RejectedMutation(
                        issue_id=action.issue_id,
                        issue_identifier=action.issue_identifier,
                        action_type=action.action_type,
                        reason=reason,
                        classification="non_retryable_policy",
                    )
                )
                rejected_by_reason[reason] = rejected_by_reason.get(reason, 0) + 1
                non_retryable_policy += 1
                continue

            reject_reason = self._guardrail_rejection_reason(
                issue=issue,
                action=action,
                dispatcher=dispatch,
                seen_issue_action_keys=seen_issue_action_keys,
                applied_count=len(applied),
            )
            if reject_reason is not None:
                rejected.append(
                    RejectedMutation(
                        issue_id=issue.id,
                        issue_identifier=issue.identifier,
                        action_type=action.action_type,
                        reason=reject_reason,
                        classification=self._classify_rejection_reason(reject_reason),
                    )
                )
                rejected_by_reason[reject_reason] = rejected_by_reason.get(reject_reason, 0) + 1
                non_retryable_policy += 1
                continue

            operations = self._build_operations(issue=issue, action=action)
            if not operations:
                reason = "No operations generated for action under active feature flags."
                rejected.append(
                    RejectedMutation(
                        issue_id=issue.id,
                        issue_identifier=issue.identifier,
                        action_type=action.action_type,
                        reason=reason,
                        classification="non_retryable_policy",
                    )
                )
                rejected_by_reason[reason] = rejected_by_reason.get(reason, 0) + 1
                non_retryable_policy += 1
                continue

            seen_issue_action_keys.add((issue.id, action.action_type))
            applied_for_action: list[AppliedMutation] = []
            try:
                for operation in operations:
                    operations_by_type[operation.operation_type] = operations_by_type.get(operation.operation_type, 0) + 1
                    retry_outcome = self._apply_with_retries(operation=operation, dispatcher=dispatch)
                    applied_for_action.append(retry_outcome.applied)
                    applied.append(retry_outcome.applied)
                    if retry_outcome.recovered_after_retry:
                        transient_recovered += 1
                    attempt_metadata.append(
                        MutationAttemptMetadata(
                            issue_id=operation.issue_id,
                            issue_identifier=operation.issue_identifier,
                            action_type=operation.action_type,
                            operation_type=operation.operation_type,
                            attempts=retry_outcome.attempts,
                            max_attempts=self._retry_max_attempts,
                            backoff_schedule_ms=retry_outcome.backoff_schedule_ms,
                            outcome="transient_recovered" if retry_outcome.recovered_after_retry else "success",
                            failure_reason=None,
                            error_class=None,
                            downgraded_from_legacy=False,
                        )
                    )
            except _RetryExhaustedError as exc:
                failed.append(
                    FailedMutation(
                        issue_id=issue.id,
                        issue_identifier=issue.identifier,
                        action_type=action.action_type,
                        reason=str(exc.last_error),
                        attempts=exc.attempts,
                        max_attempts=exc.max_attempts,
                        backoff_schedule_ms=exc.backoff_schedule_ms,
                        classification="retry_exhausted",
                        error_class=exc.error_class.value,
                        downgraded_from_legacy=exc.downgraded_from_legacy,
                    )
                )
                failed_by_reason[str(exc.last_error)] = failed_by_reason.get(str(exc.last_error), 0) + 1
                retry_exhausted += 1
                if exc.downgraded_from_legacy:
                    downgraded_legacy_dispatcher_errors += 1
                dispatcher_error_classification[exc.error_class.value] += 1
                attempt_metadata.append(
                    MutationAttemptMetadata(
                        issue_id=exc.operation.issue_id,
                        issue_identifier=exc.operation.issue_identifier,
                        action_type=exc.operation.action_type,
                        operation_type=exc.operation.operation_type,
                        attempts=exc.attempts,
                        max_attempts=exc.max_attempts,
                        backoff_schedule_ms=exc.backoff_schedule_ms,
                        outcome="retry_exhausted",
                        failure_reason=str(exc.last_error),
                        error_class=exc.error_class.value,
                        downgraded_from_legacy=exc.downgraded_from_legacy,
                    )
                )
                for item in reversed(applied_for_action):
                    try:
                        dispatch.rollback(item)
                        rolled_back += 1
                    except Exception:
                        pass
                    if item in applied:
                        applied.remove(item)
            except _NonRetryableDispatcherError as exc:
                failed.append(
                    FailedMutation(
                        issue_id=issue.id,
                        issue_identifier=issue.identifier,
                        action_type=action.action_type,
                        reason=str(exc.error),
                        attempts=exc.attempts,
                        max_attempts=exc.max_attempts,
                        backoff_schedule_ms=exc.backoff_schedule_ms,
                        classification="non_retryable_dispatcher",
                        error_class=exc.error_class.value,
                        downgraded_from_legacy=exc.downgraded_from_legacy,
                    )
                )
                failed_by_reason[str(exc.error)] = failed_by_reason.get(str(exc.error), 0) + 1
                if exc.downgraded_from_legacy:
                    downgraded_legacy_dispatcher_errors += 1
                dispatcher_error_classification[exc.error_class.value] += 1
                attempt_metadata.append(
                    MutationAttemptMetadata(
                        issue_id=exc.operation.issue_id,
                        issue_identifier=exc.operation.issue_identifier,
                        action_type=exc.operation.action_type,
                        operation_type=exc.operation.operation_type,
                        attempts=exc.attempts,
                        max_attempts=exc.max_attempts,
                        backoff_schedule_ms=exc.backoff_schedule_ms,
                        outcome="non_retryable_dispatcher",
                        failure_reason=str(exc.error),
                        error_class=exc.error_class.value,
                        downgraded_from_legacy=exc.downgraded_from_legacy,
                    )
                )
                for item in reversed(applied_for_action):
                    try:
                        dispatch.rollback(item)
                        rolled_back += 1
                    except Exception:
                        pass
                    if item in applied:
                        applied.remove(item)
            except Exception as exc:  # pragma: no cover - exercised in tests with a fake dispatcher
                for item in reversed(applied_for_action):
                    try:
                        dispatch.rollback(item)
                        rolled_back += 1
                    except Exception:
                        # Rollback errors are intentionally swallowed to keep progress observable.
                        pass
                    if item in applied:
                        applied.remove(item)

                failed.append(
                    FailedMutation(
                        issue_id=issue.id,
                        issue_identifier=issue.identifier,
                        action_type=action.action_type,
                        reason=str(exc),
                        attempts=1,
                        max_attempts=1,
                        backoff_schedule_ms=[],
                        classification="dispatcher_failure",
                        error_class=DispatcherErrorClass.INTERNAL.value,
                        downgraded_from_legacy=True,
                    )
                )
                failed_by_reason[str(exc)] = failed_by_reason.get(str(exc), 0) + 1
                downgraded_legacy_dispatcher_errors += 1
                dispatcher_error_classification[DispatcherErrorClass.INTERNAL.value] += 1

        duration_ms = int((perf_counter() - started) * 1000)
        total_retry_attempts = sum(max(0, item.attempts - 1) for item in attempt_metadata)
        return MutationExecutionReport(
            applied=applied,
            rejected=rejected,
            failed=failed,
            rolled_back_operations=rolled_back,
            dry_run=isinstance(dispatch, DryRunMutationDispatcher),
            summary={
                "status_transitions": {
                    "planned": len(actions),
                    "applied": len(applied),
                    "rejected": len(rejected),
                    "failed": len(failed),
                    "rolled_back": rolled_back,
                },
                "error_classification": {
                    "guardrail_rejection": len(rejected),
                    "dispatcher_failure": len(failed),
                    "transient_recovered": transient_recovered,
                    "retry_exhausted": retry_exhausted,
                    "non_retryable_policy": non_retryable_policy,
                },
                "dispatcher_error_classes": dispatcher_error_classification,
                "compatibility": {
                    "downgraded_legacy_dispatcher_errors": downgraded_legacy_dispatcher_errors,
                },
                "latency_timings_ms": {
                    "run_total": duration_ms,
                },
                "retry_state": {
                    "attempt": 1,
                    "max_attempts": self._retry_max_attempts,
                    "retryable_failures": retry_exhausted,
                    "total_retry_attempts": total_retry_attempts,
                    "initial_backoff_ms": self._retry_initial_backoff_ms,
                    "backoff_multiplier": self._retry_backoff_multiplier,
                },
                "mutation_outcomes": {
                    "applied": len(applied),
                    "rejected": len(rejected),
                    "failed": len(failed),
                    "rolled_back": rolled_back,
                    "transient_recovered": transient_recovered,
                    "retry_exhausted": retry_exhausted,
                    "non_retryable_policy": non_retryable_policy,
                },
                "runtime_ms": duration_ms,
                "total_actions": len(actions),
                "actions_by_type": actions_by_type,
                "applied_operations": len(applied),
                "operations_by_type": operations_by_type,
                "rejected_operations": len(rejected),
                "rejected_by_reason": rejected_by_reason,
                "failed_operations": len(failed),
                "failed_by_reason": failed_by_reason,
                "rolled_back_operations": rolled_back,
                "dry_run": isinstance(dispatch, DryRunMutationDispatcher),
                "attempt_backoff_metadata": [
                    {
                        "issue_id": item.issue_id,
                        "issue_identifier": item.issue_identifier,
                        "action_type": item.action_type,
                        "operation_type": item.operation_type,
                        "attempts": item.attempts,
                        "max_attempts": item.max_attempts,
                        "backoff_schedule_ms": item.backoff_schedule_ms,
                        "outcome": item.outcome,
                        "failure_reason": item.failure_reason,
                        "error_class": item.error_class,
                        "downgraded_from_legacy": item.downgraded_from_legacy,
                    }
                    for item in attempt_metadata
                ],
                "pilot_controls": {
                    "kill_switch_enabled": self._pilot_kill_switch_enabled,
                    "require_dry_run_first": self._require_dry_run_first,
                    "issue_identifier_allowlist_size": (
                        len(self._pilot_issue_identifier_allowlist) if self._pilot_issue_identifier_allowlist else 0
                    ),
                    "issue_id_allowlist_size": len(self._pilot_issue_id_allowlist) if self._pilot_issue_id_allowlist else 0,
                    "action_type_allowlist_size": (
                        len(self._pilot_action_type_allowlist) if self._pilot_action_type_allowlist else 0
                    ),
                },
            },
            attempt_metadata=attempt_metadata,
        )

    def _classify_rejection_reason(self, reason: str) -> str:
        normalized = reason.lower()
        if "guardrail" in normalized or "allowlist" in normalized or "policy" in normalized or "immutable" in normalized:
            return "non_retryable_policy"
        return "non_retryable"

    def _is_retryable_error(self, error_class: DispatcherErrorClass) -> bool:
        return error_class in self._retryable_error_classes

    def _normalize_dispatcher_error(self, exc: Exception) -> _NormalizedDispatcherError:
        if isinstance(exc, DispatcherExecutionError):
            return _NormalizedDispatcherError(error=exc, downgraded_from_legacy=False)
        message = str(exc).strip() or exc.__class__.__name__
        return _NormalizedDispatcherError(
            error=DispatcherExecutionError(error_class=DispatcherErrorClass.INTERNAL, message=message),
            downgraded_from_legacy=True,
        )

    def _apply_with_retries(self, operation: MutationOperation, dispatcher: MutationDispatcher) -> _RetryOutcome:
        attempt = 0
        backoff_schedule_ms: list[int] = []

        while True:
            attempt += 1
            try:
                applied = dispatcher.apply(operation)
                return _RetryOutcome(
                    applied=applied,
                    attempts=attempt,
                    backoff_schedule_ms=backoff_schedule_ms,
                    recovered_after_retry=attempt > 1,
                )
            except Exception as exc:
                normalized_error = self._normalize_dispatcher_error(exc)
                dispatcher_error = normalized_error.error
                if not self._is_retryable_error(dispatcher_error.error_class):
                    raise _NonRetryableDispatcherError(
                        operation=operation,
                        error=dispatcher_error,
                        error_class=dispatcher_error.error_class,
                        attempts=attempt,
                        max_attempts=self._retry_max_attempts,
                        backoff_schedule_ms=backoff_schedule_ms,
                        downgraded_from_legacy=normalized_error.downgraded_from_legacy,
                    ) from exc
                if attempt >= self._retry_max_attempts:
                    raise _RetryExhaustedError(
                        operation=operation,
                        last_error=dispatcher_error,
                        error_class=dispatcher_error.error_class,
                        attempts=attempt,
                        max_attempts=self._retry_max_attempts,
                        backoff_schedule_ms=backoff_schedule_ms,
                        downgraded_from_legacy=normalized_error.downgraded_from_legacy,
                    ) from exc

                backoff_ms = int(self._retry_initial_backoff_ms * (self._retry_backoff_multiplier ** (attempt - 1)))
                backoff_schedule_ms.append(backoff_ms)
                self._sleep_fn(backoff_ms / 1000)

    def _guardrail_rejection_reason(
        self,
        issue: IssueSnapshot,
        action: OrchestrationAction,
        dispatcher: MutationDispatcher,
        seen_issue_action_keys: set[tuple[str, str]],
        applied_count: int,
    ) -> str | None:
        pilot_rejection = self._pilot_rejection_reason(issue=issue, action=action, dispatcher=dispatcher)
        if pilot_rejection is not None:
            return pilot_rejection
        if issue.status in {"done", "cancelled"}:
            return f"Issue status '{issue.status}' is immutable for mutation execution."
        if not action.comment_draft.strip():
            return "Auto-comment operation requires non-empty comment_draft."
        if len(action.comment_draft) > 6000:
            return "Auto-comment operation exceeds maximum comment length guardrail."
        if (issue.id, action.action_type) in seen_issue_action_keys:
            return "Duplicate action for issue rejected by dedupe guardrail."
        if applied_count >= self._max_operations_per_run:
            return "Mutation budget exceeded for this run."
        return None

    def _pilot_rejection_reason(
        self,
        issue: IssueSnapshot,
        action: OrchestrationAction,
        dispatcher: MutationDispatcher,
    ) -> str | None:
        if self._pilot_kill_switch_enabled:
            return "Pilot kill-switch is enabled; no mutations are allowed."
        if self._require_dry_run_first and not isinstance(dispatcher, DryRunMutationDispatcher):
            return "Dry-run-first policy rejected non-dry-run dispatcher."
        if self._pilot_issue_identifier_allowlist and issue.identifier not in self._pilot_issue_identifier_allowlist:
            return "Issue identifier is outside pilot allowlist."
        if self._pilot_issue_id_allowlist and issue.id not in self._pilot_issue_id_allowlist:
            return "Issue id is outside pilot allowlist."
        if self._pilot_action_type_allowlist and action.action_type not in self._pilot_action_type_allowlist:
            return "Action type is outside pilot allowlist."
        return None

    def _build_operations(self, issue: IssueSnapshot, action: OrchestrationAction) -> list[MutationOperation]:
        operations: list[MutationOperation] = []

        if self._enable_auto_comment:
            operations.append(
                MutationOperation(
                    issue_id=issue.id,
                    issue_identifier=issue.identifier,
                    action_type=action.action_type,
                    operation_type="auto_comment",
                    payload={"comment": action.comment_draft},
                )
            )

        if self._enable_reassign_suggestion and action.recommended_assignee_agent_id:
            operations.append(
                MutationOperation(
                    issue_id=issue.id,
                    issue_identifier=issue.identifier,
                    action_type=action.action_type,
                    operation_type="reassign_suggestion",
                    payload={
                        "recommended_assignee_agent_id": action.recommended_assignee_agent_id,
                        "recommended_assignee_name": action.recommended_assignee_name,
                    },
                )
            )

        if self._enable_escalation_flag and action.should_open_follow_up_issue:
            operations.append(
                MutationOperation(
                    issue_id=issue.id,
                    issue_identifier=issue.identifier,
                    action_type=action.action_type,
                    operation_type="escalation_flag",
                    payload={"flag": "requires_follow_up_issue"},
                )
            )

        return operations
