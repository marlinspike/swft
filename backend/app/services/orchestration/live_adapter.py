from __future__ import annotations

from collections.abc import Callable, Sequence
from datetime import datetime, timezone
import json
import os
from urllib import error, request

from .actions import ChainOfCommandAgent
from .models import CommentSnapshot, IssueSnapshot

_ACTIVE_STATUSES = {"todo", "in_progress", "blocked"}
_ROLE_PRIORITY = {"cto": 0, "ceo": 1, "manager": 2, "engineer": 3}


class PaperclipAdapterError(RuntimeError):
    """Raised when the live Paperclip adapter cannot fetch/marshal issue feed data."""


class PaperclipIssueFeedAdapter:
    def __init__(
        self,
        api_url: str | None = None,
        api_key: str | None = None,
        fetch_json: Callable[[str], object] | None = None,
    ):
        self._api_url = (api_url or os.getenv("PAPERCLIP_API_URL", "")).rstrip("/")
        self._api_key = api_key or os.getenv("PAPERCLIP_API_KEY", "")
        self._fetch_json = fetch_json
        if self._fetch_json is None:
            if not self._api_url:
                raise PaperclipAdapterError("PAPERCLIP_API_URL is required for live mode.")
            if not self._api_key:
                raise PaperclipAdapterError("PAPERCLIP_API_KEY is required for live mode.")

    def load_company_snapshot(
        self,
        company_id: str,
        now: datetime | None = None,
    ) -> tuple[list[IssueSnapshot], dict[str, list[CommentSnapshot]], list[ChainOfCommandAgent], datetime]:
        raw_issues = self._get_json(f"/api/companies/{company_id}/issues")
        if not isinstance(raw_issues, list):
            raise PaperclipAdapterError("Expected list response from /api/companies/{company_id}/issues")

        issues = [self._map_issue(item) for item in raw_issues if self._is_active_issue(item)]
        comments_by_issue: dict[str, list[CommentSnapshot]] = {}
        for issue in issues:
            raw_comments = self._get_json(f"/api/issues/{issue.id}/comments")
            if not isinstance(raw_comments, list):
                raise PaperclipAdapterError(f"Expected list response from /api/issues/{issue.id}/comments")
            comments_by_issue[issue.id] = self._map_comments(issue.id, raw_comments)

        chain_of_command = self._load_chain_of_command(company_id)
        return issues, comments_by_issue, chain_of_command, (now or datetime.now(tz=timezone.utc))

    def _load_chain_of_command(self, company_id: str) -> list[ChainOfCommandAgent]:
        raw_agents = self._get_json(f"/api/companies/{company_id}/agents")
        if not isinstance(raw_agents, list):
            raise PaperclipAdapterError("Expected list response from /api/companies/{company_id}/agents")

        agents: list[tuple[tuple[int, str], ChainOfCommandAgent]] = []
        for item in raw_agents:
            if not isinstance(item, dict):
                continue
            agent_id = _coalesce_string(item.get("id"))
            if not agent_id:
                continue
            name = _coalesce_string(item.get("name")) or agent_id
            role = (_coalesce_string(item.get("role")) or "").lower()
            rank = _ROLE_PRIORITY.get(role, 100)
            agents.append(((rank, name.lower()), ChainOfCommandAgent(id=agent_id, name=name)))

        agents.sort(key=lambda item: item[0])
        return [agent for _rank, agent in agents]

    def _map_issue(self, item: object) -> IssueSnapshot:
        if not isinstance(item, dict):
            raise PaperclipAdapterError("Issue payload item must be an object.")

        issue_id = _coalesce_string(item.get("id"))
        if not issue_id:
            raise PaperclipAdapterError("Issue payload missing id.")

        identifier = _coalesce_string(item.get("identifier")) or issue_id
        title = _coalesce_string(item.get("title")) or "(untitled issue)"
        status = (_coalesce_string(item.get("status")) or "todo").lower()
        priority = (_coalesce_string(item.get("priority")) or "medium").lower()
        updated_raw = item.get("updatedAt", item.get("updated_at"))

        return IssueSnapshot(
            id=issue_id,
            identifier=identifier,
            title=title,
            status=status,
            priority=priority,
            updated_at=_parse_datetime(updated_raw),
            assignee_agent_id=_coalesce_string(item.get("assigneeAgentId", item.get("assignee_agent_id"))),
            assignee_user_id=_coalesce_string(item.get("assigneeUserId", item.get("assignee_user_id"))),
        )

    def _map_comments(self, issue_id: str, comments: Sequence[object]) -> list[CommentSnapshot]:
        mapped: list[CommentSnapshot] = []
        for item in comments:
            if not isinstance(item, dict):
                continue
            comment_id = _coalesce_string(item.get("id"))
            if not comment_id:
                continue
            body = _coalesce_string(item.get("body")) or ""
            created_raw = item.get("createdAt", item.get("created_at"))
            mapped.append(
                CommentSnapshot(
                    id=comment_id,
                    issue_id=issue_id,
                    body=body,
                    created_at=_parse_datetime(created_raw),
                    author_agent_id=_coalesce_string(item.get("authorAgentId", item.get("author_agent_id"))),
                    author_user_id=_coalesce_string(item.get("authorUserId", item.get("author_user_id"))),
                )
            )
        mapped.sort(key=lambda item: item.created_at)
        return mapped

    def _is_active_issue(self, item: object) -> bool:
        if not isinstance(item, dict):
            return False
        status = (_coalesce_string(item.get("status")) or "").lower()
        return status in _ACTIVE_STATUSES

    def _get_json(self, path: str) -> object:
        if self._fetch_json is not None:
            return self._fetch_json(path)
        url = f"{self._api_url}{path}"
        req = request.Request(
            url=url,
            headers={
                "Authorization": f"Bearer {self._api_key}",
                "Accept": "application/json",
            },
            method="GET",
        )
        try:
            with request.urlopen(req, timeout=15) as response:
                payload = response.read().decode("utf-8")
        except error.HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="replace")
            raise PaperclipAdapterError(f"Paperclip API HTTP {exc.code} for {path}: {detail}") from exc
        except OSError as exc:
            raise PaperclipAdapterError(f"Paperclip API request failed for {path}: {exc}") from exc

        try:
            return json.loads(payload)
        except json.JSONDecodeError as exc:
            raise PaperclipAdapterError(f"Paperclip API returned invalid JSON for {path}") from exc


def _coalesce_string(value: object) -> str | None:
    if isinstance(value, str):
        cleaned = value.strip()
        return cleaned or None
    return None


def _parse_datetime(value: object) -> datetime:
    if isinstance(value, str):
        try:
            return datetime.fromisoformat(value.replace("Z", "+00:00"))
        except ValueError:
            pass
    return datetime.now(tz=timezone.utc)
