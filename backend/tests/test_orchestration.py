from __future__ import annotations

from datetime import datetime, timezone
import json
from pathlib import Path

from app.services.orchestration import (
    ChainOfCommandAgent,
    DryRunMutationDispatcher,
    OrchestrationDetector,
    OrchestrationService,
    PaperclipIssueFeedAdapter,
)
from app.services.orchestration.cli import _build_payload, _load_input
from app.services.orchestration.execution import AppliedMutation, MutationExecutor, MutationOperation


def _now() -> datetime:
    return datetime(2026, 4, 10, 12, 0, tzinfo=timezone.utc)


def test_detector_flags_blocked_stale() -> None:
    fixture = Path(__file__).parent / "data" / "orchestration" / "scanner_input.json"
    issues, comments_by_issue, _chain, now = _load_input(fixture)
    detector = OrchestrationDetector()

    detections = detector.scan(issues=issues, comments_by_issue=comments_by_issue, now=now)
    signal_types = {(item.issue_identifier, item.signal_type) for item in detections}

    assert ("SHAAA-200", "blocked_stale") in signal_types


def test_detector_flags_high_priority_unassigned() -> None:
    fixture = Path(__file__).parent / "data" / "orchestration" / "scanner_input.json"
    issues, comments_by_issue, _chain, now = _load_input(fixture)
    detector = OrchestrationDetector()

    detections = detector.scan(issues=issues, comments_by_issue=comments_by_issue, now=now)
    signal_types = {(item.issue_identifier, item.signal_type) for item in detections}

    assert ("SHAAA-201", "high_priority_unassigned") in signal_types


def test_detector_flags_in_progress_stale_progress() -> None:
    fixture = Path(__file__).parent / "data" / "orchestration" / "scanner_input.json"
    issues, comments_by_issue, _chain, now = _load_input(fixture)
    detector = OrchestrationDetector()

    detections = detector.scan(issues=issues, comments_by_issue=comments_by_issue, now=now)
    signal_types = {(item.issue_identifier, item.signal_type) for item in detections}

    assert ("SHAAA-202", "in_progress_stale_progress") in signal_types


def test_service_plans_actions_with_manager_recommendation() -> None:
    fixture = Path(__file__).parent / "data" / "orchestration" / "scanner_input.json"
    issues, comments_by_issue, chain, now = _load_input(fixture)
    service = OrchestrationService()

    result = service.plan_actions(
        issues=issues,
        comments_by_issue=comments_by_issue,
        chain_of_command=chain,
        now=now,
    )

    assert len(result.detections) == 3
    assert len(result.actions) == 3

    blocked_action = next(action for action in result.actions if action.issue_identifier == "SHAAA-200")
    assert blocked_action.action_type == "escalate_blocker"
    assert blocked_action.recommended_assignee_agent_id == "agent-cto"
    assert blocked_action.should_open_follow_up_issue is True
    assert "Orchestration Escalation Draft" in blocked_action.comment_draft
    assert blocked_action.dispatch_contract is not None
    assert blocked_action.dispatch_contract.source_issue.identifier == "SHAAA-200"
    assert blocked_action.dispatch_contract.follow_up_issue_intent is not None
    assert blocked_action.dispatch_contract.follow_up_issue_intent.source_issue_id == "i-blocked"


def test_cli_fixture_payload_has_valid_shape() -> None:
    fixture = Path(__file__).parent / "data" / "orchestration" / "scanner_input.json"
    payload = json.loads(fixture.read_text(encoding="utf-8"))

    assert payload["issues"]
    assert payload["comments_by_issue"]
    assert payload["chain_of_command"][0]["id"] == "agent-cto"
    assert _now().isoformat().startswith("2026-04-10")


def test_load_input_parses_iso_timestamps() -> None:
    fixture = Path(__file__).parent / "data" / "orchestration" / "scanner_input.json"
    issues, _comments_by_issue, chain, now = _load_input(fixture)

    assert now == _now()
    assert issues[0].updated_at.year == 2026
    assert chain[0] == ChainOfCommandAgent(id="agent-cto", name="CTO")


def test_live_adapter_maps_active_issues_and_edge_cases() -> None:
    fixture = Path(__file__).parent / "data" / "orchestration" / "live_api_snapshot.json"
    payload = json.loads(fixture.read_text(encoding="utf-8"))

    def fake_fetch(path: str) -> object:
        if path == "/api/companies/company-123/issues":
            return payload["issues"]
        if path == "/api/companies/company-123/agents":
            return payload["agents"]
        if path.startswith("/api/issues/") and path.endswith("/comments"):
            issue_id = path.split("/")[3]
            return payload["comments_by_issue"].get(issue_id, [])
        raise AssertionError(f"unexpected path: {path}")

    adapter = PaperclipIssueFeedAdapter(fetch_json=fake_fetch)
    issues, comments_by_issue, chain, now = adapter.load_company_snapshot(
        company_id="company-123",
        now=_now(),
    )

    assert now == _now()
    assert [item.identifier for item in issues] == ["SHAAA-301", "SHAAA-302", "SHAAA-303"]
    assert issues[0].assignee_agent_id is None
    assert issues[0].assignee_user_id is None
    assert len(comments_by_issue["issue-blocked"]) == 0
    assert comments_by_issue["issue-progress"][0].created_at < comments_by_issue["issue-progress"][1].created_at
    assert chain[0].id == "agent-cto"


def test_live_mode_payload_matches_golden_fixture() -> None:
    input_fixture = Path(__file__).parent / "data" / "orchestration" / "live_api_snapshot.json"
    golden_fixture = Path(__file__).parent / "data" / "orchestration" / "live_mode_planning_output.json"
    payload = json.loads(input_fixture.read_text(encoding="utf-8"))

    def fake_fetch(path: str) -> object:
        if path == "/api/companies/company-123/issues":
            return payload["issues"]
        if path == "/api/companies/company-123/agents":
            return payload["agents"]
        if path.startswith("/api/issues/") and path.endswith("/comments"):
            issue_id = path.split("/")[3]
            return payload["comments_by_issue"].get(issue_id, [])
        raise AssertionError(f"unexpected path: {path}")

    adapter = PaperclipIssueFeedAdapter(fetch_json=fake_fetch)
    issues, comments_by_issue, chain, now = adapter.load_company_snapshot(company_id="company-123", now=_now())
    service = OrchestrationService()
    result = service.plan_actions(issues=issues, comments_by_issue=comments_by_issue, chain_of_command=chain, now=now)
    actual = _build_payload(result=result, mode="live", company_id="company-123")
    expected = json.loads(golden_fixture.read_text(encoding="utf-8"))

    assert actual == expected


def test_mutation_execution_blocked_trigger_success_path() -> None:
    fixture = Path(__file__).parent / "data" / "orchestration" / "scanner_input.json"
    issues, comments_by_issue, chain, now = _load_input(fixture)
    service = OrchestrationService()

    result = service.plan_actions(issues=issues, comments_by_issue=comments_by_issue, chain_of_command=chain, now=now)
    blocked_action = [item for item in result.actions if item.issue_identifier == "SHAAA-200"]
    report = service.execute_mutations(actions=blocked_action, issues=issues)

    operation_types = [item.operation.operation_type for item in report.applied]
    assert report.failed == []
    assert report.rejected == []
    assert report.dry_run is True
    assert operation_types == ["auto_comment", "reassign_suggestion", "escalation_flag"]


def test_mutation_execution_idle_trigger_success_path() -> None:
    fixture = Path(__file__).parent / "data" / "orchestration" / "scanner_input.json"
    issues, comments_by_issue, chain, now = _load_input(fixture)
    service = OrchestrationService()

    result = service.plan_actions(issues=issues, comments_by_issue=comments_by_issue, chain_of_command=chain, now=now)
    idle_action = [item for item in result.actions if item.issue_identifier == "SHAAA-201"]
    report = service.execute_mutations(actions=idle_action, issues=issues)

    operation_types = [item.operation.operation_type for item in report.applied]
    assert report.failed == []
    assert report.rejected == []
    assert operation_types == ["auto_comment", "reassign_suggestion"]


def test_mutation_execution_guardrail_rejects_done_issue() -> None:
    fixture = Path(__file__).parent / "data" / "orchestration" / "scanner_input.json"
    issues, comments_by_issue, chain, now = _load_input(fixture)
    service = OrchestrationService()

    result = service.plan_actions(issues=issues, comments_by_issue=comments_by_issue, chain_of_command=chain, now=now)
    done_issue = issues[0]
    done_override = done_issue.__class__(
        id=done_issue.id,
        identifier=done_issue.identifier,
        title=done_issue.title,
        status="done",
        priority=done_issue.priority,
        updated_at=done_issue.updated_at,
        assignee_agent_id=done_issue.assignee_agent_id,
        assignee_user_id=done_issue.assignee_user_id,
    )
    overridden_issues = [done_override, *issues[1:]]
    blocked_action = [item for item in result.actions if item.issue_identifier == "SHAAA-200"]
    report = service.execute_mutations(actions=blocked_action, issues=overridden_issues)

    assert report.applied == []
    assert report.failed == []
    assert len(report.rejected) == 1
    assert "immutable" in report.rejected[0].reason


class _FailingDispatcher(DryRunMutationDispatcher):
    def __init__(self, fail_on_call: int):
        super().__init__()
        self._fail_on_call = fail_on_call
        self._calls = 0
        self.rollback_calls: list[str] = []

    def apply(self, operation: MutationOperation) -> AppliedMutation:
        self._calls += 1
        if self._calls == self._fail_on_call:
            raise RuntimeError("simulated dispatcher failure")
        return super().apply(operation)

    def rollback(self, applied: AppliedMutation) -> None:
        self.rollback_calls.append(applied.operation.operation_type)
        super().rollback(applied)


def test_mutation_execution_failure_rolls_back_prior_operations() -> None:
    fixture = Path(__file__).parent / "data" / "orchestration" / "scanner_input.json"
    issues, comments_by_issue, chain, now = _load_input(fixture)
    service = OrchestrationService(mutation_executor=MutationExecutor())
    result = service.plan_actions(issues=issues, comments_by_issue=comments_by_issue, chain_of_command=chain, now=now)
    blocked_action = [item for item in result.actions if item.issue_identifier == "SHAAA-200"]
    dispatcher = _FailingDispatcher(fail_on_call=2)

    report = service.execute_mutations(actions=blocked_action, issues=issues, dispatcher=dispatcher)

    assert report.applied == []
    assert len(report.failed) == 1
    assert report.failed[0].reason == "simulated dispatcher failure"
    assert report.rolled_back_operations == 1
    assert dispatcher.rollback_calls == ["auto_comment"]
