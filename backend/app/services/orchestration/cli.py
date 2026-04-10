from __future__ import annotations

import argparse
from collections import Counter
from datetime import datetime, timezone
import json
import os
from pathlib import Path

from .actions import ChainOfCommandAgent
from .execution import DispatcherErrorClass, MutationExecutor
from .live_adapter import PaperclipIssueFeedAdapter
from .models import CommentSnapshot, IssueSnapshot
from .service import OrchestrationService


def _parse_datetime(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def _parse_csv_set(value: str | None) -> set[str] | None:
    if not value:
        return None
    parsed = {item.strip() for item in value.split(",") if item.strip()}
    return parsed or None


def _classify_failure_reason(reason: str, classification: str | None = None) -> str:
    if classification == "non_retryable_policy":
        return "guardrail_policy"
    if classification == "retry_exhausted":
        return "retry_exhausted"
    if classification == "non_retryable_dispatcher":
        return "non_retryable_dispatcher"
    normalized = reason.lower()
    if "dry-run-first" in normalized:
        return "dispatch_policy"
    return "unknown"


def _routing_action_for_error_class(error_class: str) -> str:
    if error_class == DispatcherErrorClass.NETWORK.value:
        return "retry_with_backoff"
    if error_class == DispatcherErrorClass.RATE_LIMIT.value:
        return "throttle_and_retry"
    if error_class == DispatcherErrorClass.AUTH.value:
        return "refresh_credentials"
    if error_class == DispatcherErrorClass.POLICY.value:
        return "policy_review"
    if error_class == DispatcherErrorClass.VALIDATION.value:
        return "fix_input_payload"
    return "escalate_internal"


def _build_triage_report(result: object, mutation_report: object | None) -> dict[str, object]:
    blocked_reason_counts = Counter(
        detection.reason for detection in result.detections if detection.signal_type == "blocked_stale"
    )
    signal_type_counts = Counter(detection.signal_type for detection in result.detections)
    failed_category_counts: Counter[str] = Counter()
    failed_reason_counts: Counter[str] = Counter()
    action_index = {(action.issue_id, action.action_type): action for action in result.actions}
    retry_exhausted_routes: list[dict[str, object]] = []
    non_retryable_policy_routes: list[dict[str, object]] = []
    by_error_class_routes: dict[str, list[dict[str, object]]] | None = None
    if mutation_report is not None:
        by_error_class_routes = {item.value: [] for item in DispatcherErrorClass}
        failed_reason_counts.update(item.reason for item in mutation_report.failed)
        failed_category_counts.update(
            _classify_failure_reason(item.reason, classification=item.classification) for item in mutation_report.failed
        )
        failed_reason_counts.update(item.reason for item in mutation_report.rejected)
        failed_category_counts.update(
            _classify_failure_reason(item.reason, classification=item.classification) for item in mutation_report.rejected
        )
        for item in mutation_report.failed:
            action = action_index.get((item.issue_id, item.action_type))
            if by_error_class_routes is not None and item.error_class in by_error_class_routes:
                by_error_class_routes[item.error_class].append(
                    {
                        "issue_identifier": item.issue_identifier,
                        "action_type": item.action_type,
                        "owner_agent_id": None if action is None else action.recommended_assignee_agent_id,
                        "owner_name": "Unassigned" if action is None else action.recommended_assignee_name,
                        "error_class": item.error_class,
                        "routing_action": _routing_action_for_error_class(item.error_class),
                        "attempts": item.attempts,
                        "max_attempts": item.max_attempts,
                        "backoff_schedule_ms": item.backoff_schedule_ms,
                        "reason": item.reason,
                    }
                )
            if item.classification != "retry_exhausted":
                continue
            retry_exhausted_routes.append(
                {
                    "issue_identifier": item.issue_identifier,
                    "action_type": item.action_type,
                    "owner_agent_id": None if action is None else action.recommended_assignee_agent_id,
                    "owner_name": "Unassigned" if action is None else action.recommended_assignee_name,
                    "error_class": item.error_class,
                    "routing_action": _routing_action_for_error_class(item.error_class or DispatcherErrorClass.INTERNAL.value),
                    "attempts": item.attempts,
                    "max_attempts": item.max_attempts,
                    "backoff_schedule_ms": item.backoff_schedule_ms,
                    "reason": item.reason,
                }
            )
        for item in mutation_report.rejected:
            if item.classification != "non_retryable_policy":
                continue
            action = action_index.get((item.issue_id, item.action_type))
            non_retryable_policy_routes.append(
                {
                    "issue_identifier": item.issue_identifier,
                    "action_type": item.action_type,
                    "owner_agent_id": None if action is None else action.recommended_assignee_agent_id,
                    "owner_name": "Unassigned" if action is None else action.recommended_assignee_name,
                    "reason": item.reason,
                    "routing_action": "policy_review",
                }
            )

    owner_routing: dict[str, dict[str, object]] = {}
    for action in result.actions:
        owner_id = action.recommended_assignee_agent_id or "unassigned"
        owner_name = action.recommended_assignee_name or "Unassigned"
        key = f"{owner_id}:{owner_name}"
        if key not in owner_routing:
            owner_routing[key] = {
                "owner_agent_id": action.recommended_assignee_agent_id,
                "owner_name": owner_name,
                "action_count": 0,
                "action_types": Counter(),
            }
        owner_routing[key]["action_count"] += 1
        owner_routing[key]["action_types"][action.action_type] += 1

    owner_routes = []
    for entry in owner_routing.values():
        owner_routes.append(
            {
                "owner_agent_id": entry["owner_agent_id"],
                "owner_name": entry["owner_name"],
                "action_count": entry["action_count"],
                "action_types": dict(entry["action_types"]),
            }
        )
    owner_routes.sort(key=lambda item: item["action_count"], reverse=True)

    top_blocked = [
        {"category": reason, "count": count}
        for reason, count in blocked_reason_counts.most_common(5)
    ]
    top_failed = [
        {"category": category, "count": count}
        for category, count in failed_category_counts.most_common(5)
    ]
    failed_reasons = [
        {"reason": reason, "count": count}
        for reason, count in failed_reason_counts.most_common(5)
    ]

    failure_routes: dict[str, object] = {
        "retry_exhausted": retry_exhausted_routes,
        "non_retryable_policy": non_retryable_policy_routes,
    }
    if by_error_class_routes is not None:
        failure_routes["by_error_class"] = by_error_class_routes

    return {
        "signal_counts": dict(signal_type_counts),
        "top_blocked_categories": top_blocked,
        "top_failed_categories": top_failed,
        "top_failure_reasons": failed_reasons,
        "failure_routes": failure_routes,
        "owner_routing": owner_routes,
    }


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


def _build_payload(
    result: object,
    mode: str,
    company_id: str | None,
    mutation_report: object | None = None,
) -> dict[str, object]:
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
        "triage_report": _build_triage_report(result=result, mutation_report=mutation_report),
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

    if mutation_report is not None:
        payload["mutation_execution"] = {
            "dry_run": mutation_report.dry_run,
            "rolled_back_operations": mutation_report.rolled_back_operations,
            "summary": mutation_report.summary,
            "applied": [
                {
                    "operation_id": item.operation_id,
                    "issue_id": item.operation.issue_id,
                    "issue_identifier": item.operation.issue_identifier,
                    "action_type": item.operation.action_type,
                    "operation_type": item.operation.operation_type,
                    "payload": item.operation.payload,
                }
                for item in mutation_report.applied
            ],
            "rejected": [
                {
                    "issue_id": item.issue_id,
                    "issue_identifier": item.issue_identifier,
                    "action_type": item.action_type,
                    "reason": item.reason,
                    "classification": item.classification,
                }
                for item in mutation_report.rejected
            ],
            "failed": [
                {
                    "issue_id": item.issue_id,
                    "issue_identifier": item.issue_identifier,
                    "action_type": item.action_type,
                    "reason": item.reason,
                    "attempts": item.attempts,
                    "max_attempts": item.max_attempts,
                    "backoff_schedule_ms": item.backoff_schedule_ms,
                    "classification": item.classification,
                    "error_class": item.error_class,
                    "downgraded_from_legacy": item.downgraded_from_legacy,
                }
                for item in mutation_report.failed
            ],
            "attempt_metadata": [
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
                for item in mutation_report.attempt_metadata
            ],
        }

    return payload


def main() -> int:
    parser = argparse.ArgumentParser(description="Orchestration scanner for active issues (dry-run or live mode).")
    parser.add_argument("--input", help="Path to JSON payload with issues/comments/chain_of_command")
    parser.add_argument("--company-id", help="Paperclip company ID for live issue feed scan")
    parser.add_argument("--api-url", default=os.getenv("PAPERCLIP_API_URL"), help="Paperclip API base URL for live mode")
    parser.add_argument("--api-key", default=os.getenv("PAPERCLIP_API_KEY"), help="Paperclip API bearer token for live mode")
    parser.add_argument("--now", help="Optional ISO timestamp to make live scans deterministic")
    parser.add_argument(
        "--execute-mutations",
        action="store_true",
        help="Execute mutation operations through the guarded in-process execution layer.",
    )
    parser.add_argument(
        "--max-operations-per-run",
        type=int,
        default=20,
        help="Mutation operation budget cap for a single run (default: 20).",
    )
    parser.add_argument(
        "--pilot-issue-identifiers",
        help="Comma-separated issue identifier allowlist for pilot mutations (example: SHAAA-1,SHAAA-2).",
    )
    parser.add_argument(
        "--pilot-issue-ids",
        help="Comma-separated issue ID allowlist for pilot mutations.",
    )
    parser.add_argument(
        "--pilot-action-types",
        help="Comma-separated action-type allowlist for pilot mutations.",
    )
    parser.add_argument(
        "--pilot-kill-switch",
        action="store_true",
        help="Hard-disable all mutation execution paths.",
    )
    parser.add_argument(
        "--allow-live-dispatch",
        action="store_true",
        help="Disable dry-run-first policy for dispatcher checks (not recommended for pilot runs).",
    )
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

    kill_switch_env = os.getenv("ORCHESTRATION_PILOT_KILL_SWITCH", "").strip().lower()
    pilot_kill_switch = args.pilot_kill_switch or kill_switch_env in {"1", "true", "yes", "on"}
    mutation_executor = MutationExecutor(
        max_operations_per_run=max(args.max_operations_per_run, 0),
        pilot_issue_identifier_allowlist=_parse_csv_set(args.pilot_issue_identifiers),
        pilot_issue_id_allowlist=_parse_csv_set(args.pilot_issue_ids),
        pilot_action_type_allowlist=_parse_csv_set(args.pilot_action_types),
        pilot_kill_switch_enabled=pilot_kill_switch,
        require_dry_run_first=not args.allow_live_dispatch,
    )
    service = OrchestrationService(mutation_executor=mutation_executor)
    result = service.plan_actions(issues=issues, comments_by_issue=comments_by_issue, chain_of_command=chain, now=now)
    mutation_report = service.execute_mutations(actions=result.actions, issues=issues) if args.execute_mutations else None
    payload = _build_payload(result=result, mode=mode, company_id=company_id, mutation_report=mutation_report)
    print(json.dumps(payload, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
