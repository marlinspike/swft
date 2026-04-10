# Orchestration Scanner

This package provides deterministic detection and action planning for task orchestration.
It supports both fixture-driven dry runs and live read-only scans of one Paperclip company.

## Detection Rules

- `blocked_stale`: blocked issues with stale (or missing) blocker comments.
- `high_priority_unassigned`: `high`/`critical` issues without assignees.
- `in_progress_stale_progress`: in-progress issues with stale (or missing) progress updates.

## Dry Run

Run the scanner against one company snapshot payload:

```bash
cd backend
python -m app.services.orchestration.cli --input tests/data/orchestration/scanner_input.json
```

## Live Run (Read-Only)

Run the scanner directly against the Paperclip API:

```bash
cd backend
PAPERCLIP_API_URL=http://127.0.0.1:3100 \
PAPERCLIP_API_KEY=<redacted-token> \
python -m app.services.orchestration.cli --company-id <company-id>
```

Required environment variables (or matching CLI args):

- `PAPERCLIP_API_URL`
- `PAPERCLIP_API_KEY`

Notes:

- Live mode is read-only for this milestone and performs only `GET` requests.
- Use `--input` for deterministic dry-run planning and CI-safe testing.
- Optional `--now` can pin the live scan clock for deterministic outputs.

The command prints structured JSON payloads for detections and planned actions, including dispatch contracts (`comment_draft`, recommended assignee, follow-up issue intent, and source issue metadata).

## Mutation Execution (Guarded)

Run guarded execution actions in dry-run mode:

```bash
cd backend
python -m app.services.orchestration.cli --input tests/data/orchestration/scanner_input.json --execute-mutations
```

Controlled live-pilot execution example (live issue feed + strict allowlist + dry-run-first):

```bash
cd backend
PAPERCLIP_API_URL=http://127.0.0.1:3100 \
PAPERCLIP_API_KEY=<redacted-token> \
python -m app.services.orchestration.cli \
  --company-id <company-id> \
  --execute-mutations \
  --pilot-issue-identifiers SHAAA-33 \
  --pilot-action-types escalate_blocker \
  --max-operations-per-run 3
```

Supported mutation action types:

- `auto_comment`
- `reassign_suggestion`
- `escalation_flag`

Guardrails:

- Rejects mutations for `done`/`cancelled` issues.
- Rejects empty/oversized comment drafts.
- Deduplicates repeated issue/action combinations per run.
- Enforces operation budget per execution run.
- Rolls back already-applied operations for an action if a downstream operation fails.
- Enforces pilot issue/action allowlists when provided.
- Supports hard kill-switch (`--pilot-kill-switch` or `ORCHESTRATION_PILOT_KILL_SWITCH=1`).
- Enforces dry-run-first dispatcher policy unless explicitly disabled with `--allow-live-dispatch`.

Rollout and safe-disable note:

- Recommended rollout path: keep execution in dry-run telemetry mode first (`--execute-mutations`).
- Fallback path: omit `--execute-mutations` to revert to planning-only output.
- Disable path: remove the runtime flag from scheduler/invocation config; planning output remains available.

The `mutation_execution.summary` payload includes pilot observability fields:

- Action counts by action type.
- Applied operation counts by operation type.
- Rejected operation counts and rejection reasons.
- Rollback count and failed-operation count.
- Runtime duration and effective pilot control settings.

## Operator Runbook: Rollback Drill

Use this runbook for pilot windows before any broader rollout.

1. Start from dry-run-first pilot scope:
   - Define explicit issue and action allowlists.
   - Keep `--allow-live-dispatch` unset.
   - Keep mutation cap low (`--max-operations-per-run 1..5`).
2. Execute a pilot run and capture `mutation_execution.summary` plus rejected/applied details.
3. Drill rollback behavior with the existing test harness:
   - `cd backend && ../.venv/bin/python -m pytest tests/test_orchestration.py::test_mutation_execution_failure_rolls_back_prior_operations`
4. Validate expected drill outcome:
   - Failure is surfaced in report.
   - Prior operation in same action is rolled back.
   - `rolled_back_operations` increments.
5. Incident response steps if production behavior diverges:
   - Trigger hard stop immediately: set `ORCHESTRATION_PILOT_KILL_SWITCH=1` (or pass `--pilot-kill-switch`).
   - Re-run scanner without `--execute-mutations` for planning-only visibility.
   - Post incident note with run id, issue identifiers, rejection/failure summary, and rollback count.
   - Escalate to CTO with go/no-go recommendation and required corrective action before re-enable.
