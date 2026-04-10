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
