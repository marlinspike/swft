from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from .actions import ChainOfCommandAgent, OrchestrationActionPlanner
from .detection import OrchestrationDetector
from .execution import MutationDispatcher, MutationExecutionReport, MutationExecutor
from .models import CommentSnapshot, DetectionSignal, IssueSnapshot, OrchestrationAction


@dataclass(frozen=True, slots=True)
class ScanResult:
    detections: list[DetectionSignal]
    actions: list[OrchestrationAction]


class OrchestrationService:
    def __init__(
        self,
        detector: OrchestrationDetector | None = None,
        action_planner: OrchestrationActionPlanner | None = None,
        mutation_executor: MutationExecutor | None = None,
    ):
        self._detector = detector or OrchestrationDetector()
        self._action_planner = action_planner or OrchestrationActionPlanner()
        self._mutation_executor = mutation_executor or MutationExecutor()

    def plan_actions(
        self,
        issues: list[IssueSnapshot],
        comments_by_issue: dict[str, list[CommentSnapshot]],
        chain_of_command: list[ChainOfCommandAgent],
        now: datetime,
    ) -> ScanResult:
        detections = self._detector.scan(issues=issues, comments_by_issue=comments_by_issue, now=now)
        issues_by_id = {issue.id: issue for issue in issues}
        actions = self._action_planner.build_actions(
            detections=detections,
            issues_by_id=issues_by_id,
            chain_of_command=chain_of_command,
        )
        return ScanResult(detections=detections, actions=actions)

    def execute_mutations(
        self,
        actions: list[OrchestrationAction],
        issues: list[IssueSnapshot],
        dispatcher: MutationDispatcher | None = None,
    ) -> MutationExecutionReport:
        issues_by_id = {issue.id: issue for issue in issues}
        return self._mutation_executor.execute(actions=actions, issues_by_id=issues_by_id, dispatcher=dispatcher)
