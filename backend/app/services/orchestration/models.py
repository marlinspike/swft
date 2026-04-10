from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True, slots=True)
class CommentSnapshot:
    id: str
    issue_id: str
    body: str
    created_at: datetime
    author_agent_id: str | None = None
    author_user_id: str | None = None


@dataclass(frozen=True, slots=True)
class IssueSnapshot:
    id: str
    identifier: str
    title: str
    status: str
    priority: str
    updated_at: datetime
    assignee_agent_id: str | None = None
    assignee_user_id: str | None = None


@dataclass(frozen=True, slots=True)
class DetectionSignal:
    issue_id: str
    issue_identifier: str
    signal_type: str
    reason: str


@dataclass(frozen=True, slots=True)
class SourceIssueMetadata:
    id: str
    identifier: str
    title: str
    status: str
    priority: str
    updated_at: datetime
    assignee_agent_id: str | None = None
    assignee_user_id: str | None = None


@dataclass(frozen=True, slots=True)
class FollowUpIssueIntent:
    title: str
    description: str
    priority: str
    source_issue_id: str
    labels: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class ActionDispatchContract:
    comment_draft: str
    recommended_assignee_agent_id: str | None
    recommended_assignee_name: str | None
    source_issue: SourceIssueMetadata
    follow_up_issue_intent: FollowUpIssueIntent | None = None


@dataclass(frozen=True, slots=True)
class OrchestrationAction:
    issue_id: str
    issue_identifier: str
    action_type: str
    summary: str
    comment_draft: str
    recommended_assignee_agent_id: str | None = None
    recommended_assignee_name: str | None = None
    should_open_follow_up_issue: bool = False
    dispatch_contract: ActionDispatchContract | None = None
