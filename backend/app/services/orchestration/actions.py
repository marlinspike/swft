from __future__ import annotations

from dataclasses import dataclass

from .models import (
    ActionDispatchContract,
    DetectionSignal,
    FollowUpIssueIntent,
    IssueSnapshot,
    OrchestrationAction,
    SourceIssueMetadata,
)


@dataclass(frozen=True, slots=True)
class ChainOfCommandAgent:
    id: str
    name: str


class OrchestrationActionPlanner:
    def build_actions(
        self,
        detections: list[DetectionSignal],
        issues_by_id: dict[str, IssueSnapshot],
        chain_of_command: list[ChainOfCommandAgent],
    ) -> list[OrchestrationAction]:
        actions: list[OrchestrationAction] = []
        for detection in detections:
            issue = issues_by_id[detection.issue_id]
            owner = self._recommended_assignee(chain_of_command)
            follow_up = detection.signal_type == "blocked_stale"
            follow_up_intent = self._follow_up_issue_intent(issue, detection) if follow_up else None
            source_issue = SourceIssueMetadata(
                id=issue.id,
                identifier=issue.identifier,
                title=issue.title,
                status=issue.status,
                priority=issue.priority,
                updated_at=issue.updated_at,
                assignee_agent_id=issue.assignee_agent_id,
                assignee_user_id=issue.assignee_user_id,
            )
            comment_draft = self._comment_draft(issue, detection, owner)
            actions.append(
                OrchestrationAction(
                    issue_id=detection.issue_id,
                    issue_identifier=detection.issue_identifier,
                    action_type=self._action_type_for(detection.signal_type),
                    summary=detection.reason,
                    comment_draft=comment_draft,
                    recommended_assignee_agent_id=owner.id if owner else None,
                    recommended_assignee_name=owner.name if owner else None,
                    should_open_follow_up_issue=follow_up,
                    dispatch_contract=ActionDispatchContract(
                        comment_draft=comment_draft,
                        recommended_assignee_agent_id=owner.id if owner else None,
                        recommended_assignee_name=owner.name if owner else None,
                        source_issue=source_issue,
                        follow_up_issue_intent=follow_up_intent,
                    ),
                )
            )
        return actions

    def _recommended_assignee(
        self,
        chain_of_command: list[ChainOfCommandAgent],
    ) -> ChainOfCommandAgent | None:
        if not chain_of_command:
            return None
        return chain_of_command[0]

    def _action_type_for(self, signal_type: str) -> str:
        if signal_type == "blocked_stale":
            return "escalate_blocker"
        if signal_type == "high_priority_unassigned":
            return "assign_owner"
        if signal_type == "in_progress_stale_progress":
            return "request_progress_update"
        return "manual_review"

    def _follow_up_issue_intent(self, issue: IssueSnapshot, detection: DetectionSignal) -> FollowUpIssueIntent:
        return FollowUpIssueIntent(
            title=f"Unblock plan required for {issue.identifier}",
            description=(
                f"Auto-generated follow-up from orchestration scanner.\n\n"
                f"Source issue: {issue.identifier} ({issue.id})\n"
                f"Signal: {detection.signal_type}\n"
                f"Reason: {detection.reason}\n"
                "Request: post explicit unblock owner, dependency, and ETA."
            ),
            priority="high",
            source_issue_id=issue.id,
            labels=("orchestration", "blocker-follow-up"),
        )

    def _comment_draft(
        self,
        issue: IssueSnapshot,
        detection: DetectionSignal,
        owner: ChainOfCommandAgent | None,
    ) -> str:
        owner_line = "No recommended assignee available."
        if owner:
            owner_line = f"Recommended owner: {owner.name} ({owner.id})."

        return (
            "## Orchestration Escalation Draft\n\n"
            f"Issue `{issue.identifier}` triggered `{detection.signal_type}`.\n\n"
            f"- Reason: {detection.reason}\n"
            f"- {owner_line}\n"
            "- Next step: confirm ownership and post status update in-thread."
        )
