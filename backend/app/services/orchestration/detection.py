from __future__ import annotations

from collections.abc import Iterable
from datetime import datetime, timedelta
import re

from .models import CommentSnapshot, DetectionSignal, IssueSnapshot


_BLOCKER_HINT_RE = re.compile(r"\b(blocked|blocker|waiting on|needs unblock|stuck)\b", re.IGNORECASE)
_PROGRESS_HINT_RE = re.compile(r"\b(progress|status|working on|started|done|completed|ready for review)\b", re.IGNORECASE)
_ACTIVE_PRIORITIES = {"high", "critical"}


class OrchestrationDetector:
    def __init__(
        self,
        blocked_stale_after: timedelta = timedelta(hours=24),
        in_progress_stale_after: timedelta = timedelta(hours=12),
    ):
        self._blocked_stale_after = blocked_stale_after
        self._in_progress_stale_after = in_progress_stale_after

    def scan(
        self,
        issues: Iterable[IssueSnapshot],
        comments_by_issue: dict[str, list[CommentSnapshot]],
        now: datetime,
    ) -> list[DetectionSignal]:
        detections: list[DetectionSignal] = []
        for issue in issues:
            detections.extend(self._detect_blocked_stale(issue, comments_by_issue.get(issue.id, []), now))
            detections.extend(self._detect_high_priority_unassigned(issue))
            detections.extend(self._detect_in_progress_stale_progress(issue, comments_by_issue.get(issue.id, []), now))
        return detections

    def _detect_blocked_stale(
        self,
        issue: IssueSnapshot,
        comments: list[CommentSnapshot],
        now: datetime,
    ) -> list[DetectionSignal]:
        if issue.status != "blocked":
            return []
        stale_deadline = now - self._blocked_stale_after
        blocker_comment = self._latest_matching_comment(comments, _BLOCKER_HINT_RE)

        if blocker_comment is None:
            return [
                DetectionSignal(
                    issue_id=issue.id,
                    issue_identifier=issue.identifier,
                    signal_type="blocked_stale",
                    reason="Issue is blocked but has no blocker-status comment to track ownership.",
                )
            ]

        if blocker_comment.created_at <= stale_deadline:
            return [
                DetectionSignal(
                    issue_id=issue.id,
                    issue_identifier=issue.identifier,
                    signal_type="blocked_stale",
                    reason="Issue remains blocked and the latest blocker update is stale.",
                )
            ]
        return []

    def _detect_high_priority_unassigned(self, issue: IssueSnapshot) -> list[DetectionSignal]:
        if issue.priority not in _ACTIVE_PRIORITIES:
            return []
        if issue.status in {"done", "cancelled"}:
            return []
        if issue.assignee_agent_id or issue.assignee_user_id:
            return []

        return [
            DetectionSignal(
                issue_id=issue.id,
                issue_identifier=issue.identifier,
                signal_type="high_priority_unassigned",
                reason="High-priority issue has no assignee.",
            )
        ]

    def _detect_in_progress_stale_progress(
        self,
        issue: IssueSnapshot,
        comments: list[CommentSnapshot],
        now: datetime,
    ) -> list[DetectionSignal]:
        if issue.status != "in_progress":
            return []
        stale_deadline = now - self._in_progress_stale_after
        progress_comment = self._latest_matching_comment(comments, _PROGRESS_HINT_RE)

        if progress_comment is None:
            if issue.updated_at <= stale_deadline:
                return [
                    DetectionSignal(
                        issue_id=issue.id,
                        issue_identifier=issue.identifier,
                        signal_type="in_progress_stale_progress",
                        reason="In-progress issue has no progress comment and is stale.",
                    )
                ]
            return []

        if progress_comment.created_at <= stale_deadline:
            return [
                DetectionSignal(
                    issue_id=issue.id,
                    issue_identifier=issue.identifier,
                    signal_type="in_progress_stale_progress",
                    reason="In-progress issue has stale progress updates.",
                )
            ]
        return []

    def _latest_matching_comment(
        self,
        comments: list[CommentSnapshot],
        pattern: re.Pattern[str],
    ) -> CommentSnapshot | None:
        matching = [comment for comment in comments if pattern.search(comment.body)]
        if not matching:
            return None
        return max(matching, key=lambda comment: comment.created_at)
