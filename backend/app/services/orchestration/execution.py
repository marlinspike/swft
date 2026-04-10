from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

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


@dataclass(frozen=True, slots=True)
class FailedMutation:
    issue_id: str
    issue_identifier: str
    action_type: str
    reason: str


@dataclass(frozen=True, slots=True)
class MutationExecutionReport:
    applied: list[AppliedMutation]
    rejected: list[RejectedMutation]
    failed: list[FailedMutation]
    rolled_back_operations: int
    dry_run: bool


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
    ):
        self._max_operations_per_run = max_operations_per_run
        self._enable_auto_comment = enable_auto_comment
        self._enable_reassign_suggestion = enable_reassign_suggestion
        self._enable_escalation_flag = enable_escalation_flag

    def execute(
        self,
        actions: list[OrchestrationAction],
        issues_by_id: dict[str, IssueSnapshot],
        dispatcher: MutationDispatcher | None = None,
    ) -> MutationExecutionReport:
        dispatch = dispatcher or DryRunMutationDispatcher()
        applied: list[AppliedMutation] = []
        rejected: list[RejectedMutation] = []
        failed: list[FailedMutation] = []
        rolled_back = 0
        seen_issue_action_keys: set[tuple[str, str]] = set()

        for action in actions:
            issue = issues_by_id.get(action.issue_id)
            if issue is None:
                rejected.append(
                    RejectedMutation(
                        issue_id=action.issue_id,
                        issue_identifier=action.issue_identifier,
                        action_type=action.action_type,
                        reason="Source issue is missing from execution context.",
                    )
                )
                continue

            reject_reason = self._guardrail_rejection_reason(
                issue=issue,
                action=action,
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
                    )
                )
                continue

            operations = self._build_operations(issue=issue, action=action)
            if not operations:
                rejected.append(
                    RejectedMutation(
                        issue_id=issue.id,
                        issue_identifier=issue.identifier,
                        action_type=action.action_type,
                        reason="No operations generated for action under active feature flags.",
                    )
                )
                continue

            seen_issue_action_keys.add((issue.id, action.action_type))
            applied_for_action: list[AppliedMutation] = []
            try:
                for operation in operations:
                    applied_mutation = dispatch.apply(operation)
                    applied_for_action.append(applied_mutation)
                    applied.append(applied_mutation)
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
                    )
                )

        return MutationExecutionReport(
            applied=applied,
            rejected=rejected,
            failed=failed,
            rolled_back_operations=rolled_back,
            dry_run=isinstance(dispatch, DryRunMutationDispatcher),
        )

    def _guardrail_rejection_reason(
        self,
        issue: IssueSnapshot,
        action: OrchestrationAction,
        seen_issue_action_keys: set[tuple[str, str]],
        applied_count: int,
    ) -> str | None:
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
