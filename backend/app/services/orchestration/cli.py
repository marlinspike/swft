from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
import os
from pathlib import Path

from .actions import ChainOfCommandAgent
from .live_adapter import PaperclipIssueFeedAdapter
from .models import CommentSnapshot, IssueSnapshot
from .service import OrchestrationService


def _parse_datetime(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def _load_input(path: Path) -> tuple[list[IssueSnapshot], dict[str, list[CommentSnapshot]], list[ChainOfCommandAgent], datetime]:
    raw = json.loads(path.read_text(encoding="utf-8"))

    issues = [
        IssueSnapshot(
            id=item["id"],
            identifier=item["identifier"],
            title=item["title"],
            status=item["status"],
            priority=item["priority"],
            updated_at=_parse_datetime(item["updated_at"]),
            assignee_agent_id=item.get("assignee_agent_id"),
            assignee_user_id=item.get("assignee_user_id"),
        )
        for item in raw["issues"]
    ]

    comments_by_issue: dict[str, list[CommentSnapshot]] = {}
    for issue_id, items in raw.get("comments_by_issue", {}).items():
        comments_by_issue[issue_id] = [
            CommentSnapshot(
                id=item["id"],
                issue_id=issue_id,
                body=item["body"],
                created_at=_parse_datetime(item["created_at"]),
                author_agent_id=item.get("author_agent_id"),
                author_user_id=item.get("author_user_id"),
            )
            for item in items
        ]

    chain = [
        ChainOfCommandAgent(id=item["id"], name=item["name"])
        for item in raw.get("chain_of_command", [])
    ]
    now = _parse_datetime(raw.get("now", datetime.now(tz=timezone.utc).isoformat()))
    return issues, comments_by_issue, chain, now


def _build_payload(result: object, mode: str, company_id: str | None) -> dict[str, object]:
    payload = {
        "mode": mode,
        "company_id": company_id,
        "detections": [
            {
                "issue_id": d.issue_id,
                "issue_identifier": d.issue_identifier,
                "signal_type": d.signal_type,
                "reason": d.reason,
            }
            for d in result.detections
        ],
        "actions": [],
    }

    for action in result.actions:
        dispatch = action.dispatch_contract
        dispatch_payload = None
        if dispatch is not None:
            source = dispatch.source_issue
            follow_up = dispatch.follow_up_issue_intent
            dispatch_payload = {
                "comment_draft": dispatch.comment_draft,
                "recommended_assignee": {
                    "agent_id": dispatch.recommended_assignee_agent_id,
                    "name": dispatch.recommended_assignee_name,
                },
                "source_issue": {
                    "id": source.id,
                    "identifier": source.identifier,
                    "title": source.title,
                    "status": source.status,
                    "priority": source.priority,
                    "updated_at": source.updated_at.isoformat(),
                    "assignee_agent_id": source.assignee_agent_id,
                    "assignee_user_id": source.assignee_user_id,
                },
                "follow_up_issue_intent": None
                if follow_up is None
                else {
                    "title": follow_up.title,
                    "description": follow_up.description,
                    "priority": follow_up.priority,
                    "source_issue_id": follow_up.source_issue_id,
                    "labels": list(follow_up.labels),
                },
            }

        payload["actions"].append(
            {
                "issue_id": action.issue_id,
                "issue_identifier": action.issue_identifier,
                "action_type": action.action_type,
                "summary": action.summary,
                "recommended_assignee_agent_id": action.recommended_assignee_agent_id,
                "recommended_assignee_name": action.recommended_assignee_name,
                "should_open_follow_up_issue": action.should_open_follow_up_issue,
                "comment_draft": action.comment_draft,
                "dispatch_contract": dispatch_payload,
            }
        )

    return payload


def main() -> int:
    parser = argparse.ArgumentParser(description="Orchestration scanner for active issues (dry-run or live mode).")
    parser.add_argument("--input", help="Path to JSON payload with issues/comments/chain_of_command")
    parser.add_argument("--company-id", help="Paperclip company ID for live issue feed scan")
    parser.add_argument("--api-url", default=os.getenv("PAPERCLIP_API_URL"), help="Paperclip API base URL for live mode")
    parser.add_argument("--api-key", default=os.getenv("PAPERCLIP_API_KEY"), help="Paperclip API bearer token for live mode")
    parser.add_argument("--now", help="Optional ISO timestamp to make live scans deterministic")
    args = parser.parse_args()

    if bool(args.input) == bool(args.company_id):
        parser.error("Provide exactly one of --input (dry-run) or --company-id (live mode).")

    mode = "dry_run"
    company_id: str | None = None
    if args.input:
        issues, comments_by_issue, chain, now = _load_input(Path(args.input))
    else:
        mode = "live"
        company_id = str(args.company_id)
        now = _parse_datetime(args.now) if args.now else datetime.now(tz=timezone.utc)
        adapter = PaperclipIssueFeedAdapter(api_url=args.api_url, api_key=args.api_key)
        issues, comments_by_issue, chain, _snapshot_now = adapter.load_company_snapshot(company_id=company_id, now=now)

    service = OrchestrationService()
    result = service.plan_actions(issues=issues, comments_by_issue=comments_by_issue, chain_of_command=chain, now=now)
    payload = _build_payload(result=result, mode=mode, company_id=company_id)
    print(json.dumps(payload, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
